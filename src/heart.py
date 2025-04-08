from constants import (
    ALPHA,
    DISPLAY_HEIGHT,
    MEAN_WINDOW_PERCENT,
    MIN_PEAK_INTERVAL,
    MAX_PEAK_INTERVAL,
    PPI_SIZE,
)
import time


def low_pass_filter(previous_value: float, next_value: float):
    return ALPHA * previous_value + (1 - ALPHA) * next_value


def min_max_scaling(max_value: int, min_value: int, value: int):
    return (DISPLAY_HEIGHT - 1) - int(
        (value - min_value) / (max_value - min_value) * (DISPLAY_HEIGHT - 1)
    )


def compute_corrected_mean(mean_window, mean):
    if mean == 0:
        return 0

    min_window = min(mean_window)
    max_window = max(mean_window)
    return MEAN_WINDOW_PERCENT * (mean - min_window) + min_window


# obj for last_peak_ms
def detect_peaks(
    samples: list[float],
    corrected_mean: float,
    current_time_ms: float,
    peak_diffs_ms: list[float],
    obj: Machine,
):
    if len(samples) < 3:
        return
    prev_value, current_value, next_value = samples[-3], samples[-2], samples[-1]

    if (
        current_value > prev_value
        and current_value > next_value
        and current_value > corrected_mean
    ):
        if obj.last_peak_ms is not None:
            peak_diff = time.ticks_diff(current_time_ms, obj.last_peak_ms)

            if peak_diff >= MIN_PEAK_INTERVAL and peak_diff <= MAX_PEAK_INTERVAL:
                mean_peak = (
                    sum(peak_diffs_ms) / len(peak_diffs_ms) if peak_diffs_ms else 0
                )
                peak_diffs_ms.append(peak_diff)
                # print(f"{60000 / mean_peak if mean_peak else 0:.2f}")
                if len(peak_diffs_ms) > PPI_SIZE:
                    peak_diffs_ms = peak_diffs_ms[-PPI_SIZE:]
        obj.last_peak_ms = current_time_ms


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
