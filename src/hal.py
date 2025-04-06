from machine import Pin, I2C
from time import ticks_ms
from gc import collect as gc_collect
from constants import (
    ROTARY_BUTTON_DEBOUNCE_MS,
    LONG_PRESS_MS,
    DISPLAY_WIDTH_PX,
    DISPLAY_HEIGHT_PX,
    CAT_SIZE_WIDTH_PX,
    CAT_SIZE_HEIGTH_PX,
    PIN_ROTARY_A,
    PIN_SIGNAL_LED,
    PIN_ROTARY_B,
    PIN_I2C_CLOCK,
    PIN_I2C_DATA,
    PIN_ROTARY_BUTTON,
    ROTARY_ROTATION_RESET_TIMEOUT_MS,
    ROTARY_ROTATION_SENSETIVITY,
)
import ssd1306
import os


# Hardware abstraction layer over the Pico W
class HAL:
    def __init__(self, initial_state=lambda: None):
        self._state = initial_state
        self.onboard_led = Pin(PIN_SIGNAL_LED, Pin.OUT)

        self.rotary_debounce_timer_ms = 0
        self.rotary_button = Pin(PIN_ROTARY_BUTTON, Pin.IN, Pin.PULL_UP)
        self.rotary_button.irq(self._rotary_knob_press, trigger=Pin.IRQ_FALLING)

        self.rotary_a = Pin(PIN_ROTARY_A, Pin.IN, Pin.PULL_UP)
        self.rotary_b = Pin(PIN_ROTARY_B, Pin.IN, Pin.PULL_UP)
        self.rotary_a.irq(self._rotary_knob_rotate, Pin.IRQ_RISING, hard=True)
        self.rotary_accumulator = 0
        self.rotary_motion_queue = 0

        self.i2c = I2C(1, sda=Pin(PIN_I2C_DATA), scl=Pin(PIN_I2C_CLOCK))
        self.display = ssd1306.SSD1306_I2C(128, 64, self.i2c)

        self.button_pressed_timer_running = False
        self.button_pressed_timer = 0
        self.long_button_press = False
        self.short_button_press = False

        self.rotary_reset_timer_ms = 0

        self.is_first_frame = True

        self.is_display_inverted = False
        self.is_display_flipped = False

    def _rotary_knob_press(self, _):
        if self.rotary_debounce_timer_ms + ROTARY_BUTTON_DEBOUNCE_MS >= ticks_ms():
            return

        self.long_button_press = False
        self.short_button_press = False

        self.rotary_debounce_timer_ms = ticks_ms()
        self.button_pressed_timer_running = True
        self.rotary_button.irq(self._rotary_knob_release, trigger=Pin.IRQ_RISING)

    def _rotary_knob_release(self, _):
        ticks_now_ms = ticks_ms()
        if self.rotary_debounce_timer_ms + ROTARY_BUTTON_DEBOUNCE_MS >= ticks_now_ms:
            return

        dt_ms = ticks_now_ms - self.rotary_debounce_timer_ms
        if dt_ms > LONG_PRESS_MS:
            self.long_button_press = True
        else:
            self.short_button_press = True

        self.rotary_debounce_timer_ms = ticks_now_ms
        self.button_pressed_timer_running = False
        self.rotary_button.irq(self._rotary_knob_press, trigger=Pin.IRQ_FALLING)

    def _rotary_knob_rotate(self, _):
        self.rotary_reset_timer_ms = ticks_ms()
        self.rotary_accumulator += 1 if self.rotary_b() else -1

        increment = False
        threshold_hit = abs(self.rotary_accumulator) > ROTARY_ROTATION_SENSETIVITY
        increment |= threshold_hit

        if increment:
            self.rotary_motion_queue += -1 if self.rotary_accumulator > 0 else 1

            rotary_accumulator = self.rotary_accumulator
            rotary_accumulator = (
                abs(self.rotary_accumulator) - ROTARY_ROTATION_SENSETIVITY
            )
            if self.rotary_accumulator < 0:
                rotary_accumulator *= -1
            self.rotary_accumulator = rotary_accumulator

    def rotary_motion_percentage(self):
        """
        Returns a value from 0 to 1, representing how much rotation is done.
        """
        return self.rotary_accumulator / ROTARY_ROTATION_SENSETIVITY

    def pull_rotary(self):
        """
        Resets the state of the rotary knob and returns the accumulated motions.
        """
        if self.rotary_motion_queue:
            motion = self.rotary_motion_queue
            self.rotary_motion_queue = 0
            return motion
        return 0

    def state(self, new_state=None):
        """
        Retrieve or set the current state.
        Triggers state cleanup such as garbage collection.
        """
        if new_state:
            if self._state is new_state:
                return
            gc_collect()
            self.flush_files()
            self.onboard_led.toggle()
            self._state = new_state
        return self._state

    def button_held(self) -> bool:
        """
        `True` if the button is currently being pressed, `False` otherwise.
        """
        return self.button_pressed_timer_running

    def button(self) -> bool:
        """
        `True` if button was generally pressed, `False` otherwise.
        Resets the value of the button.
        """
        return self.button_long() or self.button_short()

    def button_long(self) -> bool:
        """
        `True` if the last press lasted for `LONG_PRESS_MS` or longer, `False` otherwise.
        Resets the value of the button.
        """
        if self.long_button_press:
            self.long_button_press = False
            return True
        return False

    def button_short(self) -> bool:
        """
        `True` if the button press lasted for less than `LONG_PRESS_MS`, `False` otherwise.
        Resets the value of the button.
        """
        if self.short_button_press:
            self.short_button_press = False
            return True
        return False

    def execute(self):
        """
        Run the current state once and update the display.
        """
        if ticks_ms() - self.rotary_reset_timer_ms > ROTARY_ROTATION_RESET_TIMEOUT_MS:
            if self.rotary_accumulator:
                self.rotary_accumulator = 0
                self.rotary_reset_timer_ms = 0

        running_state = self._state
        running_state()

        # If the state was changed it will be the new state's
        # first frame, otherwise we reset it
        self.is_first_frame = not (self._state is running_state)

    @staticmethod
    def always_redraw(f):
        def wrapper(self):
            ret = f(self)
            self.display.show()
            return ret

        return wrapper

    def request_redraw(self):
        # TODO: just for testing purposes
        # this is where the cat will be
        self.display.fill_rect(
            DISPLAY_WIDTH_PX - CAT_SIZE_WIDTH_PX,
            DISPLAY_HEIGHT_PX - CAT_SIZE_HEIGTH_PX,
            DISPLAY_WIDTH_PX,
            DISPLAY_HEIGHT_PX,
            1,
        )

        self.display.show()

    def invert_display(self):
        self.is_display_inverted = not self.is_display_inverted
        self.display.invert(self.is_display_inverted)

    @staticmethod
    def flush_files():
        # Micropython-specific function
        os.sync()  # type: ignore
