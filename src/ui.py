from constants import (
    UI_OPTION_GAP,
    CHAR_SIZE_WIDTH,
    UI_MARGIN,
    CHAR_SIZE_HEIGHT,
    UI_MARGIN,
)
from math import exp


class Ui:
    def __init__(self, hal, options=[], fallback=None):
        self.hal = hal

        self.options = options
        self.fallback = fallback

        self.selected_option = 0

    @property
    def display(self):
        return self.hal.display

    def tick(self):
        if self.hal.button_long():
            if self.fallback:
                self.fallback()
                return

        self.display.fill(0)

        if self.selected_option:
            self.selected_option %= len(self.options)

        rotary_motion = self.hal.pull_rotary()

        max_chars_in_option = max(map(lambda o: len(o[0]), self.options))
        option_label_width = (max_chars_in_option + 1) * CHAR_SIZE_WIDTH

        for i, (name, _) in enumerate(self.options):
            text_x = UI_MARGIN
            text_y = UI_MARGIN + i * (CHAR_SIZE_HEIGHT + UI_OPTION_GAP)

            color = 1
            if i == self.selected_option:
                self.display.fill_rect(
                    text_x,
                    text_y - UI_OPTION_GAP // 2,
                    option_label_width,
                    CHAR_SIZE_HEIGHT + UI_OPTION_GAP // 2,
                    color,
                )
                color ^= 1

            self.display.text(
                name,
                text_x,
                text_y,
                color,
            )

        if rotary_motion:
            self.selected_option = (
                len(self.options) + self.selected_option + rotary_motion
            ) % len(self.options)

        if self.hal.button_short():
            self.options[self.selected_option][1]()
