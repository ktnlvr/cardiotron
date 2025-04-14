from hal import HAL
from ui import Ui
import time
from heart import (
    low_pass_filter,
    min_max_scaling,
    compute_corrected_mean,
    is_sample_peak,
    draw_graph,
    draw_heart_rate_counter,
)
from bench import span_begin, span_end
from constants import (
    SAMPLE_RATE,
    TIMESTAMP_DIFFERENCE_SENSOR,
    ALPHA,
    SAMPLES_PROCESSED_PER_COLLECTED,
    SAMPLE_SIZE,
    DISPLAY_HEIGHT_PX,
    DISPLAY_WIDTH_PX,
    MEAN_WINDOW_PERCENT,
    MEAN_WINDOW_SIZE,
    MIN_PEAK_INTERVAL,
    MAX_PEAK_INTERVAL,
    SAMPLES_ON_SCREEN_SIZE,
    UI_MARGIN,
    CHAR_SIZE_HEIGHT_PX,
    UI_OPTION_GAP,
    UI_CLOCK_HOUR_ARROW_LENGTH_PX,
    UI_CLOCK_MINUTE_ARROW_LENGTH_PX,
    UI_CLOCK_SECOND_ARROW_LENGTH_PX,
    HEART_SAMPLES_BUFFER_SIZE,
    PPI_SIZE,
)
from time import localtime
from math import tau, sin, cos
from ringbuffer import Ringbuffer
from machine import Timer


class Machine(HAL):
    def go_to_state(self, state):
        return lambda: self.state(state)

    def __init__(self):
        super().__init__(self.main_menu)

        s = self.go_to_state

        self.brightness_slider_b = 0xFF
        self.settings_ui = Ui(
            self,
            [
                ("Brightness", s(self.brightness)),
                ("Invert", self.invert_display),
                ("Clock", s(self.clock)),
            ],
            s(self.main_menu),
        )
        self.first_frame = True
        self.previous_clock_second = 0

        self.main_menu_ui = Ui(
            self,
            [
                ("Measure", s(self.measure_heart_rate)),
                ("History", s(self.toast)),
                ("Setup", s(self.toast)),
                ("Settings", s(self.settings)),
            ],
        )

        self.heart_rate = 0
        self.heart_rate_graph_y = DISPLAY_HEIGHT_PX - 1
        self.heart_rate_mean_window = Ringbuffer(MEAN_WINDOW_SIZE, "f")
        self.heart_rate_screen_samples = Ringbuffer(SAMPLES_ON_SCREEN_SIZE, "f")
        self.filtered_samples = Ringbuffer(SAMPLE_SIZE, "f")

        self.heart_rate_samples = Ringbuffer(HEART_SAMPLES_BUFFER_SIZE, "H")
        self.heart_rate_sample_timer = Timer()

        self.last_peak_ms = None
        self.ppis_ms = []
        self.heart_rate = 0

        self.last_filtered_sample = 0
        self.last_dy = 0

    def main_menu(self):
        self.main_menu_ui.tick()

    def _reset_heart_measurements(self):
        self.heart_rate_graph_y = DISPLAY_HEIGHT_PX - 1

    def set_heart_sensor_active(self, active):
        if active:
            self.heart_rate_sample_timer.init(
                period=round(1000 / SAMPLE_RATE),
                callback=lambda _: self.heart_rate_samples.append(
                    self.sensor_pin_adc.read_u16()
                ),
            )
        else:
            self.heart_rate_sample_timer.deinit()

    def measure_heart_rate(self):
        if self.button_long():
            self.set_heart_sensor_active(False)
            self.state(self.main_menu)
            self._reset_heart_measurements()
            return

        if self.is_first_frame:
            self.set_heart_sensor_active(True)

        value = self.heart_rate_samples.get()
        if not value:
            return

        mean_window = self.heart_rate_mean_window

        self.display.fill(0)
        mean = sum(mean_window) / len(mean_window) if len(mean_window) else 0
        corrected_mean = compute_corrected_mean(mean_window, mean)

        filtered_sample = float(value)

        dy = filtered_sample - self.last_filtered_sample

        self.filtered_samples.append(filtered_sample)
        self.heart_rate_screen_samples.append(filtered_sample)

        if self.filtered_samples:
            filtered_sample = low_pass_filter(
                self.last_filtered_sample, filtered_sample
            )
        mean_window.append(filtered_sample)

        current_time_ms = time.ticks_ms()
        is_peak = is_sample_peak(
            filtered_sample,
            dy - self.last_dy,
            corrected_mean,
        )

        if is_peak:
            # NOTE(Artur): Candidate for a new peak sequence, possibly can
            # break out of bad PPIs
            self.last_peak_ms = current_time_ms

            if MIN_PEAK_INTERVAL < time_since_peak_ms < MAX_PEAK_INTERVAL:
                # the two last peaks had sensible intervals, start measuring heart rate
                time_since_peak_ms = current_time_ms - (self.last_peak_ms or current_time_ms - 1)
                self.ppis_ms.append(time_since_peak_ms)
                mean_peak = (
                    sum(self.ppis_ms[-PPI_SIZE:]) / len(self.ppis_ms[-PPI_SIZE:])
                    if self.ppis_ms
                    else 0
                )
                self.heart_rate = int(60000 / mean_peak if mean_peak else 0)

        if time.ticks_diff(current_time_ms, self.last_peak_ms) > 3000:
            self.ppis_ms = []
            self.heart_rate = 0

        mi = min(self.heart_rate_screen_samples)
        ma = max(self.heart_rate_screen_samples)

        prev_x = 0
        for screen_x in range(len(self.heart_rate_screen_samples)):
            screen_y = min_max_scaling(
                ma, mi, self.heart_rate_screen_samples.data[screen_x]
            )
            self.display.pixel(screen_x, screen_y, 1)
            self.display.line(prev_x, self.heart_rate_graph_y, screen_x, screen_y, 1)
            prev_x, self.heart_rate_graph_y = screen_x, screen_y

        screen_mean = min_max_scaling(ma, mi, corrected_mean)
        self.display.line(0, screen_mean, SAMPLES_ON_SCREEN_SIZE, screen_mean, 1)

        draw_heart_rate_counter(self.display, self.heart_rate)

        self.display.show()

        self.last_filtered_sample = filtered_sample
        self.last_dy = dy

    @HAL.always_redraw
    def toast(self):
        if self.button():
            self.state(self.main_menu)

        self.display.fill(0)
        self.display.text("Toast", 0, 0)

    def settings(self):
        self.settings_ui.tick()

    def brightness(self):
        if self.button():
            self.state(self.settings)
            return

        self.display.fill(0)

        speed = 8
        rotation = self.pull_rotary()
        rotation *= speed

        if rotation or self.is_first_frame:
            self.brightness_slider_b = min(
                0xFF, max(self.brightness_slider_b + rotation, 0)
            )
            self.display.contrast(self.brightness_slider_b)

        # NOTE(Artur): All the +1 -2 pixel offsets have to do with the width of a
        # rectangles outline being 1. It can't really be controlled
        # and are just direct pixel offsets. Open to suggestions.

        width = DISPLAY_WIDTH_PX - 2 * UI_MARGIN

        # Since 0 width doesn't mean that the display is turned off, displaying just 1
        # pixel of brightness would clarify that the minimum is actually not 0
        width_filled_in = max(int((width - 2) * (self.brightness_slider_b / 0xFF)), 1)

        self.display.rect(UI_MARGIN, UI_MARGIN, width, CHAR_SIZE_HEIGHT_PX, 1)
        self.display.fill_rect(
            UI_MARGIN + 1,
            UI_MARGIN + 1,
            width_filled_in,
            CHAR_SIZE_HEIGHT_PX - 2,
            1,
        )

        self.display.text(
            "Rotate the knob",
            UI_MARGIN,
            UI_MARGIN + CHAR_SIZE_HEIGHT_PX + UI_OPTION_GAP,
            1,
        )

        self.request_redraw()

    @HAL.always_redraw
    def clock(self):
        if self.is_first_frame:
            self.previous_clock_second = 0

        if self.button_long():
            self.state(self.settings)
            return

        time_tuple = list(localtime())
        _, _, _, h, m, s, *_ = time_tuple

        if s != self.previous_clock_second:
            self.onboard_led.toggle()
            self.previous_clock_second = s

        self.display.fill(0)

        self.display.text(f"{h:0>2}:{m:0>2}:{s:0>2}", UI_MARGIN, UI_MARGIN)

        # 3 2-digit numbers and 2 colons inbetween
        text_width = CHAR_SIZE_HEIGHT_PX * (3 * 2 + 2)
        clock_width = DISPLAY_WIDTH_PX - text_width
        clock_center_x = text_width + clock_width // 2
        clock_center_y = DISPLAY_HEIGHT_PX // 2

        h_angle = tau * (h % 12) / 12
        m_angle = tau * m / 60
        s_angle = tau * s / 60

        arrows = [
            (UI_CLOCK_HOUR_ARROW_LENGTH_PX, h_angle),
            (UI_CLOCK_MINUTE_ARROW_LENGTH_PX, m_angle),
            (UI_CLOCK_SECOND_ARROW_LENGTH_PX, s_angle),
        ]

        CLOCK_00_OFFSET = -tau / 4

        clock_radius = max(map(lambda t: t[0], arrows))
        steps = 32
        for i in range(0, steps):
            step = tau / steps
            angle = i * step + CLOCK_00_OFFSET

            x1 = int(round(clock_radius * cos(angle)))
            y1 = int(round(clock_radius * sin(angle)))

            x2 = int(round(clock_radius * cos(angle + step)))
            y2 = int(round(clock_radius * sin(angle + step)))

            self.display.line(
                clock_center_x + x1,
                clock_center_y + y1,
                clock_center_x + x2,
                clock_center_y + y2,
                1,
            )

        for length, angle in arrows:
            angle += CLOCK_00_OFFSET

            y = int(round(length * sin(angle)))
            x = int(round(length * cos(angle)))

            self.display.line(
                clock_center_x,
                clock_center_y,
                clock_center_x + x,
                clock_center_y + y,
                1,
            )
