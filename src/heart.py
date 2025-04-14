from constants import (
    ALPHA,
    DISPLAY_HEIGHT_PX,
    MEAN_WINDOW_PERCENT,
    MIN_PEAK_INTERVAL,
    MAX_PEAK_INTERVAL,
    PPI_SIZE,
    SAMPLES_ON_SCREEN_SIZE,
)
import time


def low_pass_filter(previous_value: float, next_value: float):
    return ALPHA * previous_value + (1 - ALPHA) * next_value


def min_max_scaling(max_value: int, min_value: int, value: int):
    return (DISPLAY_HEIGHT_PX - 1) - int(
        (value - min_value) / (max_value - min_value) * (DISPLAY_HEIGHT_PX - 1)
        if max_value != min_value
        else 0
    )


def compute_corrected_mean(mean_window, mean):
    if mean == 0:
        return 0

    min_window = min(mean_window)
    max_window = max(mean_window)
    return MEAN_WINDOW_PERCENT * (mean - min_window) + min_window


# obj for last_peak_ms
def is_sample_peak(
    sample: float,
    ddy: float,
    corrected_mean: float,
):
    return (
        ddy < 0
        and sample > corrected_mean
    )


def draw_graph(display, samples_on_screen, prev_y):
    max_value = max(samples_on_screen)
    min_value = min(samples_on_screen)
    if max_value == min_value:
        max_value += 1
    prev_x = 0
    for screen_x in range(len(samples_on_screen)):
        screen_y = min_max_scaling(max_value, min_value, samples_on_screen[screen_x])
        display.pixel(screen_x, screen_y, 1)
        display.line(prev_x, prev_y, screen_x, screen_y, 1)
        prev_x, prev_y = screen_x, screen_y


def draw_heart_rate_counter(display, heart_rate):
    display.text(str(int(heart_rate)), SAMPLES_ON_SCREEN_SIZE + 16, 32, 1)
