from machine import Pin, I2C
from time import sleep_ms, ticks_ms
from gc import collect as gc_collect
from fifo import Fifo
import ssd1306

from pins import PIN_ROTARY_A, PIN_SIGNAL_LED, PIN_ROTARY_B, PIN_I2C_CLOCK, PIN_I2C_DATA, PIN_ROTARY_BUTTON

DISPLAY_H = 128
DISPLAY_V = 64
CAT_SIZE_H = 32
CAT_SIZE_V = 32
LONG_PRESS_MS = 1000


# Hardware abstraction layer over the Pico W
class HAL:
    def __init__(self, initial_state=lambda: None):
        self._state = initial_state
        self.onboard_led = Pin(PIN_SIGNAL_LED, Pin.OUT)

        self.rotary_button = Pin(PIN_ROTARY_BUTTON, Pin.IN, Pin.PULL_UP)
        self.rotary_a = Pin(PIN_ROTARY_A, Pin.IN, Pin.PULL_UP)
        self.rotary_b = Pin(PIN_ROTARY_B, Pin.IN, Pin.PULL_UP)
        self.rotary_fifo = Fifo(32, "b")
        self.rotary_a.irq(
            handler=self._rotary_interrupt_handler, trigger=Pin.IRQ_RISING, hard=True
        )

        self.i2c = I2C(1, sda=Pin(PIN_I2C_DATA), scl=Pin(PIN_I2C_CLOCK))
        self.display = ssd1306.SSD1306_I2C(128, 64, self.i2c)

        self.ticks_ms = ticks_ms()
        self.dt_ms = 0

        self.button_pressed_timer_running = False
        self.button_pressed_timer = 0
        self.long_button_press = False
        self.short_button_press = True

    def _rotary_interrupt_handler(self, pin):
        self.rotary_fifo.put(-1 if self.rotary_b() else 1)

    def pull_rotary(self):
        if self.rotary_fifo.has_data():
            self.onboard_led.toggle()
            return self.rotary_fifo.get()

    def state(self, new_state = None):
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
        ticks_now_ms = ticks_ms()
        self.dt_ms = max(ticks_now_ms - self.ticks_ms, 1)
        self.ticks_ms = ticks_now_ms

        if self.button_pressed_timer > LONG_PRESS_MS:
            self.onboard_led.value((self.button_pressed_timer // 30) % 2 == 1)

        if self.rotary_button.value() == 1:
            if self.button_pressed_timer_running:
                sleep_ms(5)
                if self.rotary_button.value() == 1:
                    if self.button_pressed_timer > LONG_PRESS_MS:
                        self.long_button_press = True
                    else:
                        self.short_button_press = True
                    self.button_pressed_timer = 0
                    self.button_pressed_timer_running = False
        if self.rotary_button.value() == 0:
            self.button_pressed_timer_running = True
        if self.button_pressed_timer_running:
            self.button_pressed_timer += self.dt_ms

        self._state()
        self.display.show()
        
        # TODO: just for testing purposes
        # this is where the cat will be
        self.display.fill_rect(
            DISPLAY_H - CAT_SIZE_H, DISPLAY_V - CAT_SIZE_V, DISPLAY_H, DISPLAY_V, 1
        )
