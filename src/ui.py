from constants import (
    UI_OPTION_GAP,
    CHAR_SIZE_WIDTH,
    UI_LEFT_MARGIN,
    CHAR_SIZE_HEIGHT,
    UI_TOP_MARGIN,
    UI_LERP_RATE,
)
from math import exp
from time import ticks_ms


def stable_lerp(x, y, r, dt):
    return (y - x) * exp(r * dt) + y


class Ui:
    def __init__(self, hal, options=[]):
        self.hal = hal
        self.options = options
        self.selected_option = 0
        self.selection_highlight_y = 0

        self.last_time_ms = ticks_ms()
        self.dt = 0

    @property
    def display(self):
        return self.hal.display

    def tick(self):
        time_ms = ticks_ms()
        self.dt = time_ms - self.last_time_ms
        self.last_time_ms = time_ms

        self.display.fill(0)

        if self.selected_option:
            self.selected_option %= len(self.options)

        rotary_motion = self.hal.pull_rotary()

        max_chars_in_option = max(map(lambda o: len(o[0]), self.options))
        option_label_width = (max_chars_in_option + 1) * CHAR_SIZE_WIDTH

        # XXX: kinda ugly, rewrite me?
        for i, (name, _) in enumerate(self.options):
            text_x = UI_LEFT_MARGIN
            text_y = UI_TOP_MARGIN + i * (CHAR_SIZE_HEIGHT + UI_OPTION_GAP)

            color = 1
            if i == self.selected_option:
                selection_highlight_dy = (
                    UI_OPTION_GAP * self.hal.rotary_motion_percentage()
                )

                target_selection_y = (
                    text_y + selection_highlight_dy - UI_OPTION_GAP // 2
                )

                self.selection_highlight_y = stable_lerp(
                    self.selection_highlight_y,
                    target_selection_y,
                    UI_LERP_RATE,
                    self.dt,
                )

                self.display.fill_rect(
                    text_x,
                    round(self.selection_highlight_y),
                    option_label_width,
                    CHAR_SIZE_HEIGHT + UI_OPTION_GAP,
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
