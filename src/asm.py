from hal import HAL
from ui import Ui
from constants import (
    UI_MARGIN,
    DISPLAY_WIDTH,
    CHAR_SIZE_HEIGHT,
    UI_OPTION_GAP,
    UI_CLOCK_HOUR_ARROW_LENGTH_PX,
    UI_CLOCK_MINUTE_ARROW_LENGTH_PX,
    UI_CLOCK_SECOND_ARROW_LENGTH_PX,
    DISPLAY_WIDTH,
    DISPLAY_HEIGHT,
)
from time import localtime
from math import tau, sin, cos


class Machine(HAL):
    def go_to_state(self, state):
        return lambda: self.state(state)

    def __init__(self):
        super().__init__(self.main_menu)
        s = self.go_to_state

        self.brightness_slider_b = 0xFF
        self.settings_ui = Ui(
            self,
            [
                ("Brightness", s(self.brightness)),
                ("Invert", self.invert_display),
                ("Clock", s(self.clock)),
            ],
            s(self.main_menu),
        )
        self.first_frame = True
        self.previous_clock_second = 0

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

    @HAL.always_redraw
    def toast(self):
        if self.button():
            self.state(self.main_menu)

        self.display.fill(0)
        self.display.text("Toast", 0, 0)

    def settings(self):
        self.settings_ui.tick()

    def brightness(self):
        if self.button():
            self.state(self.settings)
            return

        self.display.fill(0)

        speed = 8
        rotation = self.pull_rotary()
        rotation *= speed

        if rotation or self.is_first_frame:
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
            CHAR_SIZE_HEIGHT - 2,
            1,
        )

        self.display.text(
            "Rotate the knob",
            UI_MARGIN,
            UI_MARGIN + CHAR_SIZE_HEIGHT + UI_OPTION_GAP,
            1,
        )

        self.request_redraw()

    @HAL.always_redraw
    def clock(self):
        if self.is_first_frame:
            self.previous_clock_second = 0

        if self.button_long():
            self.state(self.settings)
            return

        time_tuple = list(localtime())
        _, _, _, h, m, s, *_ = time_tuple

        if s != self.previous_clock_second:
            self.onboard_led.toggle()
            self.previous_clock_second = s

        self.display.fill(0)

        self.display.text(f"{h:0>2}:{m:0>2}:{s:0>2}", UI_MARGIN, UI_MARGIN)

        # 3 2-digit numbers and 2 colons inbetween
        text_width = CHAR_SIZE_HEIGHT * (3 * 2 + 2)
        clock_width = DISPLAY_WIDTH - text_width
        clock_center_x = text_width + clock_width // 2
        clock_center_y = DISPLAY_HEIGHT // 2

        h_angle = tau * h / 24
        m_angle = tau * m / 60
        s_angle = tau * s / 60

        arrows = [
            (UI_CLOCK_HOUR_ARROW_LENGTH_PX, h_angle),
            (UI_CLOCK_MINUTE_ARROW_LENGTH_PX, m_angle),
            (UI_CLOCK_SECOND_ARROW_LENGTH_PX, s_angle),
        ]

        CLOCK_00_OFFSET = -tau / 4

        clock_radius = max(map(lambda t: t[0], arrows))
        steps = 32
        for i in range(0, steps):
            step = tau / steps
            angle = i * step + CLOCK_00_OFFSET

            x1 = int(round(clock_radius * cos(angle)))
            y1 = int(round(clock_radius * sin(angle)))

            y2 = int(round(clock_radius * sin(angle + step)))
            x2 = int(round(clock_radius * cos(angle + step)))

            self.display.line(
                clock_center_x + x1,
                clock_center_y + y1,
                clock_center_x + x2,
                clock_center_y + y2,
                1,
            )

        for length, angle in arrows:
            angle += CLOCK_00_OFFSET

            y = int(round(length * sin(angle)))
            x = int(round(length * cos(angle)))

            self.display.line(
                clock_center_x,
                clock_center_y,
                clock_center_x + x,
                clock_center_y + y,
                1,
            )
