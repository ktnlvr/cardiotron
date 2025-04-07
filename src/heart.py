from constants import DISPLAY_HEIGHT, ALPHA, SAMPLE_SIZE, SAMPLES_PER_PIXEL, MEAN_WINDOW_PERCENT, MIN_PEAK_INTERVAL, MAX_PEAK_INTERVAL
from array import array
import time

class HeartMeasurements:
    def __init__(self):
        self.last_peak_ms = None
        self.ppis = array('f')
        self.samples = array('H')
        self.filtered_samples = array('f')

    @property
    def mean(self):
        return sum(self.filtered_samples) / len(self.filtered_samples) if self.filtered_samples else 0
    
    @property
    def min(self):
        return min(self.filtered_samples)

    @property
    def max(self):
        return max(self.filtered_samples)

    @property
    def threshold(self):
        if not self.filtered_samples:
            return 0
        return MEAN_WINDOW_PERCENT * (self.mean - self.min) + self.min

    def sample(self, adc_pin):
        new_sample = sum(adc_pin.read_u16() for _ in range(SAMPLES_PER_PIXEL)) // SAMPLES_PER_PIXEL

        if self.samples:
            new_filtered_sample = low_pass_filter(self.samples[- 1], new_sample)
            roll_append(self.filtered_samples, new_filtered_sample, SAMPLE_SIZE)

        roll_append(self.samples, new_sample, SAMPLE_SIZE)

    def detect_peak(self):
        if len(self.samples) <= 2:
            return
        
        next = self.samples[-1]
        current = self.samples[-2]
        prev = self.samples[-3]

        is_possible_peak = current > next and current > prev and current > self.threshold

        if not is_possible_peak:
            return
        
        current_time_ms = time.ticks_ms()
        if self.last_peak_ms:
            ppi = time.ticks_diff(current_time_ms, self.last_peak_ms)
            is_ppi_sane = MIN_PEAK_INTERVAL <= ppi <= MAX_PEAK_INTERVAL
            if not is_ppi_sane:
                return

            roll_append(self.ppis, ppi, SAMPLE_SIZE)
            print(self.heart_rate)

        self.last_peak_ms = current_time_ms

    @property
    def heart_rate(self):
        if not self.ppis:
            return 0
        few_ppis = self.ppis[-10:]
        mean_ppi = sum(few_ppis) / len(few_ppis)
        return 60000 / mean_ppi if mean_ppi else 0

    def reset(self):
        self.ppis = array('f')
        self.last_peak_ms = None

def low_pass_filter(previous_value: float, next_value: float):
    return ALPHA * previous_value + (1 - ALPHA) * next_value

def min_max_scaling(max_value: int, min_value: int, value: int):
    return (DISPLAY_HEIGHT - 1) - int(
        (value - min_value) / (max_value - min_value) * (DISPLAY_HEIGHT - 1)
    )

def roll_append(array, value, limit):
    if len(array) >= limit:
        roll_array(array)
        array[- 1] = value
    else:
        array.append(value)

def roll_array(array):
    for i in range(len(array) - 1):
        array[i] = array[i +1]
