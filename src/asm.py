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
from time import ticks_ms
from bench import span_begin, span_end

from heart import low_pass_filter, min_max_scaling, HeartMeasurements


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
        self.heart = HeartMeasurements()

    def main_menu(self):
        self.main_menu_ui.tick()

    # samples stores the values to show on screen
    # mean_window stores the smoothed out values
    # peak_diffs would store the difference between the peaks
    def heart_rate(self):
        mean_window = []

        measurements = self.heart

        prev_y = DISPLAY_HEIGHT - 1
        while True:
            self.display.fill(0)

            span_begin("heart_processing")

            measurements.sample(self.sensor_pin_adc)
            measurements.detect_peak()

            span_begin("reset")
            if time.ticks_diff(ticks_ms(), measurements.last_peak_ms) > 2000:
                measurements.reset()
            span_begin("reset")

            span_end("heart_processing")

            samples_on_screen = measurements.samples[-DISPLAY_WIDTH:]

            max_value = max(samples_on_screen)
            min_value = min(samples_on_screen)
            if max_value == min_value:
                max_value += 1
            prev_x = 0
            for screen_x in range(len(samples_on_screen)):
                screen_y = min_max_scaling(
                    max_value, min_value, samples_on_screen[screen_x]
                )
                self.display.pixel(screen_x, screen_y, 1)
                self.display.line(prev_x, prev_y, screen_x, screen_y, 1)
                prev_x, prev_y = screen_x, screen_y
            self.display.show()
            if len(measurements.samples) >= 2:
                prev_y = min_max_scaling(max_value, min_value, samples_on_screen[1])

    def toast(self):
        if self.button():
            self.state(self.main_menu)

        self.display.fill(0)
        self.display.text("Toast", 0, 0)
