from hal import HAL
from ui import Ui
from constants import (
    SAMPLE_RATE,
    TIMESTAMP_DIFFERENCE_SENSOR,
    ALPHA,
    SAMPLES_PER_PIXEL,
    SAMPLE_SIZE,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    MEAN_WINDOW_PERCENT,
    MEAN_WINDOW_SIZE,
    MIN_PEAK_INTERVAL,
    MAX_PEAK_INTERVAL,
)
import time
from heart import (
    low_pass_filter,
    min_max_scaling,
    compute_corrected_mean,
    detect_peaks,
    draw_graph,
)
from bench import span_begin, span_end


class Machine(HAL):
    def go_to_state(self, state):
        return lambda: self.state(state)

    def __init__(self):
        super().__init__(self.main_menu)
        self.main_menu_ui = Ui(
            self,
            [
                ("Measure", self.go_to_state(self.heart_rate)),
                ("History", self.go_to_state(self.toast)),
                ("Setup", self.go_to_state(self.toast)),
            ],
        )
        self.samples = []
        self.last_peak_ms = None
        self.peak_diffs_ms = []

    def main_menu(self):
        self.main_menu_ui.tick()

    def heart_rate(self):
        prev_y = DISPLAY_HEIGHT - 1
        samples_on_screen = []
        mean_window = []

        while True:
            self.display.fill(0)
            # span_begin("GG")
            mean = sum(mean_window) / len(mean_window) if len(mean_window) else 0
            corrected_mean = compute_corrected_mean(mean_window, mean)

            new_samples = [
                self.sensor_pin_adc.read_u16() for _ in range(SAMPLES_PER_PIXEL)
            ]
            filtered_sample = sum(new_samples) / len(new_samples)
            self.samples.append(filtered_sample)
            if len(self.samples) > SAMPLE_SIZE:
                self.samples = self.samples[-SAMPLE_SIZE:]

            if self.samples:
                filtered_sample = low_pass_filter(self.samples[-1], filtered_sample)
            mean_window.append(filtered_sample)
            if len(mean_window) > MEAN_WINDOW_SIZE:
                mean_window = mean_window[-MEAN_WINDOW_SIZE:]

            current_time = time.ticks_ms()
            detect_peaks(
                self.samples, corrected_mean, current_time, self.peak_diffs_ms, self
            )
            if time.ticks_diff(current_time, self.last_peak_ms) > 5000:
                self.peak_diffs_ms = []
                heart_rate = 0
            # span_end("GG")

            samples_on_screen = (
                self.samples[-DISPLAY_WIDTH:]
                if len(self.samples) > DISPLAY_WIDTH
                else self.samples
            )
            draw_graph(self.display, samples_on_screen, prev_y)
            self.display.show()

            if len(self.samples) >= 2:
                prev_y = min_max_scaling(
                    max(self.samples[-DISPLAY_WIDTH:]),
                    min(self.samples[-DISPLAY_WIDTH:]),
                    samples_on_screen[1],
                )

    def toast(self):
        if self.button():
            self.state(self.main_menu)

        self.display.fill(0)
        self.display.text("Toast", 0, 0)
