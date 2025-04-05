from hal import HAL
from ui import Ui
from constants import (
    UI_MARGIN,
    DISPLAY_WIDTH,
    CHAR_SIZE_HEIGHT,
)


class Machine(HAL):
    def go_to_state(self, state):
        return lambda: self.state(state)

    def __init__(self):
        super().__init__(self.main_menu)
        s = self.go_to_state

        self.brightness_slider_b = 0xFF
        self.settings_ui = Ui(
            self, [("Brigtness", s(self.brightness))], s(self.main_menu)
        )

        self.main_menu_ui = Ui(
            self,
            [
                ("Measure", s(self.toast)),
                ("History", s(self.toast)),
                ("Setup", s(self.toast)),
                ("Settings", s(self.settings)),
            ],
        )

    def main_menu(self):
        self.main_menu_ui.tick()

    def toast(self):
        if self.button():
            self.state(self.main_menu)

        self.display.fill(0)
        self.display.text("Toast", 0, 0)

    def settings(self):
        self.settings_ui.tick()

    def brightness(self):
        if self.button_long():
            self.state(self.settings)
            return

        self.display.fill(0)

        speed = 8
        rotation = self.pull_rotary()
        rotation *= speed

        if rotation:
            self.brightness_slider_b = min(
                0xFF, max(self.brightness_slider_b + rotation, 0)
            )
            self.display.contrast(self.brightness_slider_b)

        # NOTE(Artur): All the +1 -2 pixel offsets have to do with the width of a
        # rectangles outline being 1. It can't really be controlled
        # and are just direct pixel offsets. Open to suggestions.

        width = DISPLAY_WIDTH - 2 * UI_MARGIN

        # Since 0 width doesn't mean that the display is turned off, displaying just 1
        # pixel of brightness would clarify that the minimum is actually not 0
        width_filled_in = max(int((width - 2) * (self.brightness_slider_b / 0xFF)), 1)

        self.display.rect(UI_MARGIN, UI_MARGIN, width, CHAR_SIZE_HEIGHT, 1)
        self.display.fill_rect(
            UI_MARGIN + 1,
            UI_MARGIN + 1,
            width_filled_in,
            CHAR_SIZE_HEIGHT - 1,
            1,
        )
