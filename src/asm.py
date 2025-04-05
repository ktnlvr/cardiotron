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
        self.last_peak = None
        self.peak_diffs = []

    def main_menu(self):
        self.main_menu_ui.tick()

    def low_pass_filter(self, previous_value: float, next_value: float):
        return ALPHA * previous_value + (1 - ALPHA) * next_value

    def min_max_scaling(self, max_value: int, min_value: int, value: int):
        return (DISPLAY_HEIGHT - 1) - int(
            (value - min_value) / (max_value - min_value) * (DISPLAY_HEIGHT - 1)
        )

    #samples stores the values to show on screen
    #mean_window stores the smoothed out values
    #peak_diffs would store the difference between the peaks
    def heart_rate(self):
        prev_y = DISPLAY_HEIGHT - 1
        samples_on_screen = []
        mean_window = []
        while True:
            self.display.fill(0)
            mean = sum(mean_window) / len(mean_window) if len(mean_window) else 0
            corrected_mean = 0
            if mean != 0:
                min_window = min(mean_window)
                max_window = max(mean_window)
                corrected_mean = MEAN_WINDOW_PERCENT * (mean - min_window) + min_window
            new_samples = []
            new_samples = [self.sensor_pin_adc.read_u16() for _ in range(SAMPLES_PER_PIXEL)]
            filtered_sample = sum(new_samples) / len(new_samples)
            self.samples.append(filtered_sample)
            if len(self.samples) > SAMPLE_SIZE:
                self.samples = self.samples[-SAMPLE_SIZE:]
            if self.samples:
                filtered_sample = self.low_pass_filter(self.samples[-1], filtered_sample)
            mean_window.append(filtered_sample)
            if len(mean_window) > SAMPLE_SIZE:
                mean_window = mean_window[-SAMPLE_SIZE:]
            current_time = time.ticks_ms()
            if len(self.samples) > 2:
                next = self.samples[-1]
                current = self.samples[-2]
                prev = self.samples[-3]
                if current > next and current > prev and current > corrected_mean:
                    if self.last_peak is not None:
                        peak_dif = time.ticks_diff(current_time, self.last_peak)
                        if peak_dif >= MIN_PEAK_INTERVAL and peak_dif <= MAX_PEAK_INTERVAL:
                            print("PEAK DETECTED")
                            print(f"The current heart rate is {60000 / mean_peak if mean_peak != 0 else 0}")
                            self.peak_diffs.append(peak_dif)
                            if len(self.peak_diffs) > SAMPLE_SIZE:
                                self.peak_diffs = self.peak_diffs[-SAMPLE_SIZE:]
                    self.last_peak = current_time
            if time.ticks_diff(current_time, self.last_peak) > 5000:
                self.peak_diffs = []
                heart_rate = 0

            samples_on_screen = (
                self.samples[-DISPLAY_WIDTH:]
                if len(self.samples) > DISPLAY_WIDTH
                else self.samples
            )
            max_value = max(samples_on_screen)
            min_value = min(samples_on_screen)
            if max_value == min_value:
                max_value += 1
            prev_x = 0
            for screen_x in range(len(samples_on_screen)):
                screen_y = self.min_max_scaling(
                    max_value, min_value, samples_on_screen[screen_x]
                )
                self.display.pixel(screen_x, screen_y, 1)
                self.display.line(prev_x, prev_y, screen_x, screen_y, 1)
                prev_x, prev_y = screen_x, screen_y
            self.display.show()
            if len(self.samples) >= 2:
                prev_y = self.min_max_scaling(max_value, min_value, samples_on_screen[1])
            mean_peak = sum(self.peak_diffs) / len(self.peak_diffs) if len(self.peak_diffs) != 0 else 0

    def toast(self):
        if self.button():
            self.state(self.main_menu)

        self.display.fill(0)
        self.display.text("Toast", 0, 0)
