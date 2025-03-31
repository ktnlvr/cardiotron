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
)


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

    def main_menu(self):
        self.main_menu_ui.tick()

    def low_pass_filter(self, previous_value: float, next_value: float):
        return ALPHA * previous_value + (1 - ALPHA) * next_value

    def min_max_scaling(self, max_value: int, min_value: int, value: int):
        return (DISPLAY_HEIGHT - 1) - int(
            (value - min_value) / (max_value - min_value) * (DISPLAY_HEIGHT - 1)
        )

    def heart_rate(self):
        prev_x = 0
        prev_y = DISPLAY_HEIGHT - 1
        samples_on_screen = []
        corrected_mean = 0
        while True:
            self.display.fill(0)
            new_samples = []
            for i in range(SAMPLES_PER_PIXEL):
                new_sample = self.sensor_pin_adc.read_u16()
                new_samples.append(new_sample)
            self.samples.append(sum(new_samples) / len(new_samples))
            if len(self.samples) > SAMPLE_SIZE:
                self.samples = self.samples[-SAMPLE_SIZE:]
            samples_on_screen = (
                self.samples[-DISPLAY_WIDTH:]
                if len(self.samples) > DISPLAY_WIDTH
                else self.samples
            )
            max_value = max(samples_on_screen)
            min_value = min(samples_on_screen)
            if max_value == min_value:
                max_value += 1
            for screen_x in range(len(samples_on_screen)):
                screen_y = self.min_max_scaling(
                    max_value, min_value, samples_on_screen[screen_x]
                )
                self.display.pixel(screen_x, screen_y, 1)
                self.display.line(prev_x, prev_y, screen_x, screen_y, 1)
                self.display.show()
                prev_x = screen_x
                prev_y = screen_y
            prev_x = 0
            if len(self.samples) >= 2:
                prev_y = self.min_max_scaling(
                    max_value, min_value, samples_on_screen[1]
                )
            peaks_t = []
            mean_window = []
            for i in range(1, len(self.samples)):
                self.samples[i] = self.low_pass_filter(
                    self.samples[i - 1], self.samples[i]
                )
            for i in range(1, len(self.samples) - 1):
                mean = (sum(mean_window) / len(mean_window)) if len(mean_window) else 0
                if mean != 0:
                    mi = min(mean_window)
                    ma = max(mean_window)
                    corrected_mean = MEAN_WINDOW_PERCENT * (mean - mi) + mi
                if (
                    self.samples[i - 1] <= self.samples[i]
                    and self.samples[i + 1] < self.samples[i]
                    and self.samples[i] > corrected_mean
                ):
                    peaks_t.append((i + 1) * 0.004)
                mean_window.append(
                    self.low_pass_filter(self.samples[i], corrected_mean)
                )
                if len(mean_window) >= MEAN_WINDOW_SIZE:
                    mean_window.pop(0)
            if len(peaks_t) > 1:
                for i in range(0, len(peaks_t) - 1):
                    peaks_t[i] = peaks_t[i + 1] - peaks_t[i]
                peaks_t = peaks_t[:-1]
                mean_peaks = sum(peaks_t) / len(peaks_t)
                print(f"The current heart rate is {60 / mean_peaks} and {peaks_t}")

    def toast(self):
        if self.button():
            self.state(self.main_menu)

        self.display.fill(0)
        self.display.text("Toast", 0, 0)
