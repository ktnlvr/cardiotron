from hal import HAL
from ui import Ui
import time
from heart import (
    low_pass_filter,
    min_max_scaling,
    compute_corrected_mean,
    is_sample_peak,
    draw_heart_rate_counter,
)
from constants import (
    SAMPLE_RATE,
    SAMPLE_SIZE,
    DISPLAY_HEIGHT_PX,
    DISPLAY_WIDTH_PX,
    MEAN_WINDOW_SIZE,
    MIN_PEAK_INTERVAL_MS,
    MAX_PEAK_INTERVAL_MS,
    SAMPLES_ON_SCREEN_SIZE,
    UI_MARGIN,
    CHAR_SIZE_HEIGHT_PX,
    UI_OPTION_GAP,
    UI_CLOCK_HOUR_ARROW_LENGTH_PX,
    UI_CLOCK_MINUTE_ARROW_LENGTH_PX,
    UI_CLOCK_SECOND_ARROW_LENGTH_PX,
    HEART_SAMPLES_BUFFER_SIZE,
    MAX_NO_PEAK_INTERVAL_MS,
    PPI_SIZE,
    DEFAULT_MQTT_SERVER_ADDR,
)
from time import localtime
from math import tau, sin, cos
from ringbuffer import Ringbuffer
from machine import Timer
import math
from collections import OrderedDict
from wifi import connect_ap
from network import (
    STAT_CONNECTING,
    STAT_NO_AP_FOUND,
    STAT_GOT_IP,
    STAT_WRONG_PASSWORD,
    STAT_CONNECT_FAIL,
)
from secrets import secrets


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
                ("History", s(self.toast("History"))),
                ("Setup", s(self.connecting_wifi)),
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

        self.heart_rate_last_peak_ms = None
        self.heart_rate_ppis_ms = []
        self.heart_rate = 0

        self.heart_rate_first_sane_peak_ms = 0

        self.last_filtered_sample = 0
        self.last_dy = 0

        self.wlan_connecting_ongoing = None

    def main_menu(self):
        self.main_menu_ui.tick()

    def _reset_heart_measurements(self):
        self.heart_rate_graph_y = DISPLAY_HEIGHT_PX - 1
        self.heart_rate_mean_window.clear()
        self.heart_rate_screen_samples.clear()
        self.heart_rate_samples.clear()
        self.heart_rate_last_peak_ms = None
        self.heart_rate_ppis_ms = []

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

        if self.button_short():
            self.set_heart_sensor_active(False)
            self.state(self.display_heart_rate_analysis)

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
            if self.heart_rate_last_peak_ms is not None:
                # We start considering measurements starting from now
                if not self.heart_rate_first_sane_peak_ms:
                    self.heart_rate_first_sane_peak_ms = current_time_ms

                time_since_peak_ms = current_time_ms - self.heart_rate_last_peak_ms
                if MIN_PEAK_INTERVAL_MS < time_since_peak_ms < MAX_PEAK_INTERVAL_MS:
                    self.heart_rate_ppis_ms.append(time_since_peak_ms)
                    mean_peak = (
                        sum(self.heart_rate_ppis_ms[-PPI_SIZE:])
                        / len(self.heart_rate_ppis_ms[-PPI_SIZE:])
                        if self.heart_rate_ppis_ms
                        else 0
                    )
                    self.heart_rate = int(60000 / mean_peak if mean_peak else 0)
            self.heart_rate_last_peak_ms = current_time_ms

        if (
            time.ticks_diff(current_time_ms, self.heart_rate_last_peak_ms)
            > MAX_NO_PEAK_INTERVAL_MS
        ):
            self.heart_rate_first_sane_peak_ms = 0
            self.heart_rate_ppis_ms = []
            self.heart_rate = 0

        mi = min(self.heart_rate_screen_samples)
        ma = max(self.heart_rate_screen_samples)

        TIMER_SIZE_Y = CHAR_SIZE_HEIGHT_PX
        GRAPH_SIZE_Y = DISPLAY_HEIGHT_PX - 1 - TIMER_SIZE_Y
        prev_x = 0
        for screen_x in range(len(self.heart_rate_screen_samples)):
            screen_y = (
                min_max_scaling(
                    ma, mi, self.heart_rate_screen_samples.data[screen_x], GRAPH_SIZE_Y
                )
                + TIMER_SIZE_Y
            )
            self.display.pixel(screen_x, screen_y, 1)
            self.display.line(prev_x, self.heart_rate_graph_y, screen_x, screen_y, 1)
            prev_x, self.heart_rate_graph_y = screen_x, screen_y

        screen_mean = (
            min_max_scaling(ma, mi, corrected_mean, GRAPH_SIZE_Y) + TIMER_SIZE_Y
        )

        # Show a small dot at the bottom indicating the currently read value
        self.display.pixel(self.heart_rate_screen_samples.end, DISPLAY_HEIGHT_PX - 1, 1)

        self.display.line(0, screen_mean, SAMPLES_ON_SCREEN_SIZE, screen_mean, 1)

        draw_heart_rate_counter(self.display, self.heart_rate)

        if self.heart_rate_first_sane_peak_ms:
            # Display how long the measurement has been going
            time_since_measurement_started_s = round(
                (current_time_ms - self.heart_rate_first_sane_peak_ms) / 1000
            )

            timer_str = f"{time_since_measurement_started_s}s"
            if time_since_measurement_started_s >= 60:
                m = time_since_measurement_started_s // 60
                s = time_since_measurement_started_s % 60
                timer_str = f"{m}:{s:02}"
            self.display.text(timer_str, 0, 0, 1)

        self.display.show()

        self.last_filtered_sample = filtered_sample
        self.last_dy = dy

    def display_heart_rate_analysis(self):
        if self.button_short():
            self.state(self.main_menu)
            return

        if self.button_long():
            self.state(self.measure_heart_rate)
            return

        if not self.is_first_frame:
            return

        self.set_heart_sensor_active(False)
        self.display.fill(0)

        mean_ppi = (
            sum(self.heart_rate_ppis_ms) / len(self.heart_rate_ppis_ms)
            if len(self.heart_rate_ppis_ms) != 0
            else 0
        )

        mean_hr = 60000 / mean_ppi if mean_ppi != 0 else 0

        sdnn = (
            math.sqrt(
                sum((ppi - mean_ppi) ** 2 for ppi in self.heart_rate_ppis_ms)
                / len(self.heart_rate_ppis_ms)
            )
            if len(self.heart_rate_ppis_ms) != 0
            else 0
        )

        successive_diffs = [
            self.heart_rate_ppis_ms[i + 1] - self.heart_rate_ppis_ms[i]
            for i in range(len(self.heart_rate_ppis_ms) - 1)
        ]

        rmssd = (
            math.sqrt(sum(diff**2 for diff in successive_diffs) / len(successive_diffs))
            if successive_diffs
            else 0
        )

        measurements = OrderedDict(
            [
                ("Mean HR", f"{round(mean_hr)}"),
                ("Mean PPI", f"{round(mean_ppi)}"),
                ("SDNN", f"{sdnn:.2f}"),
                ("rMSSD", f"{rmssd:.2f}"),
            ]
        )

        for i, (name, value) in enumerate(measurements.items()):
            self.display.text(
                f"{name}: {value}",
                UI_MARGIN,
                (CHAR_SIZE_HEIGHT_PX + UI_OPTION_GAP) * i,
                1,
            )

        self.display.show()

    def toast(self, message, previous_state=None, next_state=None):
        lines = message.split("\n")

        def _toast_state_machine():
            if self.button_long():
                self.state(previous_state if previous_state else self.main_menu)
                return

            if self.button_short():
                self.state(next_state if next_state else self.main_menu)
                return

            self.display.fill(0)
            for i, line in enumerate(lines):
                self.display.text(line, 0, CHAR_SIZE_HEIGHT_PX * i)
            self.request_redraw()

        return _toast_state_machine

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

    def connecting_wifi(self):
        ssid = secrets["ssid"]
        if not self.wlan_connecting_ongoing:
            self.wlan_connecting_ongoing = connect_ap(self.wlan, ssid)

        wlan_status = None
        try:
            wlan_status = next(self.wlan_connecting_ongoing)
        except StopIteration:
            pass

        if self.button():
            self.state(self.main_menu)

        text = "Connecting..."

        self.display.fill(0)
        self.display.text(text, 0, 0, 1)
        self.request_redraw()

        if wlan_status != STAT_CONNECTING:
            self.wlan_connecting_ongoing = None

        if wlan_status == STAT_GOT_IP:
            self.state(self.wifi_connected)
            return
        elif wlan_status == STAT_NO_AP_FOUND:
            self.state(self.toast(f"Couldn't\nconnect to\n{ssid}"))
            return
        elif wlan_status == STAT_WRONG_PASSWORD:
            self.state(self.toast(f"Wrong password!"))
            return
        elif wlan_status == STAT_CONNECTING:
            text = "Connecting..."
        elif wlan_status == STAT_CONNECT_FAIL:
            self.state(self.toast("Connection\nfailed, check\ncredentials"))
            return
        else:
            self.wlan_connecting_ongoing = None
            raise Exception("Unhandled WLAN status!")

        time.sleep(1)

        self.display.text(text, 0, 0, 1)
        self.request_redraw()

    def wifi_connected(self):
        if self.button():
            self.state(self.main_menu)

        if not self.is_first_frame:
            return

        self.display.fill(0)
        ipv4, *_ = self.wlan.ifconfig()

        self.display.text("Connected!", 0, 0, 1)
        self.display.text(ipv4, 0, CHAR_SIZE_HEIGHT_PX, 1)
        self.request_redraw()

        self.connect_mqtt(DEFAULT_MQTT_SERVER_ADDR)
