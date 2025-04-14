from constants import (
    UI_OPTION_GAP,
    CHAR_SIZE_WIDTH_PX,
    UI_MARGIN,
    CHAR_SIZE_HEIGHT_PX,
    UI_MARGIN,
)


class Ui:
    def __init__(self, hal, options=[], fallback=None):
        self.hal = hal

        self.options = options
        self.fallback = fallback

        self.selected_option = 0
        self.first_frame = True

    @property
    def display(self):
        return self.hal.display

    def tick(self):
        if self.hal.button_long():
            if self.fallback:
                self.fallback()
                return

        if self.hal.button_short():
            self.options[self.selected_option][1]()
            return

        rotary_motion = self.hal.pull_rotary()

        if not rotary_motion and not self.hal.is_first_frame:
            return

        self.is_first_frame = False

        self.selected_option = (
            len(self.options) + self.selected_option + rotary_motion
        ) % len(self.options)

        self.display.fill(0)

        max_chars_in_option = max(map(lambda o: len(o[0]), self.options))
        option_label_width = (max_chars_in_option + 1) * CHAR_SIZE_WIDTH_PX

        for i, (name, _) in enumerate(self.options):
            text_x = UI_MARGIN
            text_y = UI_MARGIN + i * (CHAR_SIZE_HEIGHT_PX + UI_OPTION_GAP)

            color = 1
            if i == self.selected_option:
                self.display.fill_rect(
                    text_x,
                    text_y - UI_OPTION_GAP // 2,
                    option_label_width,
                    CHAR_SIZE_HEIGHT_PX + UI_OPTION_GAP // 2,
                    color,
                )
                color ^= 1

            self.display.text(
                name,
                text_x,
                text_y,
                color,
            )

        self.hal.request_redraw()
