from machine import Pin, I2C
from time import sleep_ms, ticks_ms
from gc import collect as gc_collect
import ssd1306

from pins import (
    PIN_ROTARY_A,
    PIN_SIGNAL_LED,
    PIN_ROTARY_B,
    PIN_I2C_CLOCK,
    PIN_I2C_DATA,
    PIN_ROTARY_BUTTON,
)

DISPLAY_H = 128
DISPLAY_V = 64
CAT_SIZE_H = 32
CAT_SIZE_V = 32
ROTARY_BUTTON_DEBOUNCE_MS = 100
LONG_PRESS_MS = 250


# Hardware abstraction layer over the Pico W
class HAL:
    def __init__(self, initial_state=lambda: None):
        self._state = initial_state
        self.onboard_led = Pin(PIN_SIGNAL_LED, Pin.OUT)

        self.rotary_button = Pin(PIN_ROTARY_BUTTON, Pin.IN, Pin.PULL_UP)

        self.rotary_button.irq(self._rotary_knob_press, trigger=Pin.IRQ_FALLING)

        self.rotary_debounce_timer_ms = 0

        self.rotary_a = Pin(PIN_ROTARY_A, Pin.IN, Pin.PULL_UP)
        self.rotary_b = Pin(PIN_ROTARY_B, Pin.IN, Pin.PULL_UP)

        self.rotary_a.irq(self._rotary_knob_rotate, Pin.IRQ_RISING, hard=True)

        self.rotary_motion = 0

        self.i2c = I2C(1, sda=Pin(PIN_I2C_DATA), scl=Pin(PIN_I2C_CLOCK))
        self.display = ssd1306.SSD1306_I2C(128, 64, self.i2c)

        self.button_pressed_timer_running = False
        self.button_pressed_timer = 0
        self.long_button_press = False
        self.short_button_press = False

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
        self.rotary_motion += 1 if self.rotary_b() else -1

    def pull_rotary(self):
        motion = self.rotary_motion
        self.rotary_motion = 0
        return motion

    def state(self, new_state=None):
        if new_state:
            if self._state is new_state:
                return
            gc_collect()
            self.onboard_led.toggle()
            self._state = new_state
        return self._state

    def button_held(self) -> bool:
        # TODO: potentially catastrophic
        # rewrite me to use better timers
        if self.rotary_button.value() == 0:
            sleep_ms(50)
            self.onboard_led.toggle()
            return self.rotary_button.value() == 0
        return False

    def button_long(self) -> bool:
        if self.long_button_press:
            self.long_button_press = False
            return True
        return False

    def button_short(self) -> bool:
        if self.short_button_press:
            self.short_button_press = False
            return True
        return False

    def execute(self):
        self._state()
        self.display.show()

        # TODO: just for testing purposes
        # this is where the cat will be
        self.display.fill_rect(
            DISPLAY_H - CAT_SIZE_H, DISPLAY_V - CAT_SIZE_V, DISPLAY_H, DISPLAY_V, 1
        )
