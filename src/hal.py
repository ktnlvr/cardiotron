from machine import Pin, I2C
from time import sleep
from gc import collect as gc_collect
from fifo import Fifo
import ssd1306

from pins import PIN_ROTARY_A, PIN_SIGNAL_LED, PIN_ROTARY_B, PIN_I2C_CLOCK, PIN_I2C_DATA

DISPLAY_H = 128
DISPLAY_V = 64
CAT_SIZE_H = 32
CAT_SIZE_V = 32


# Hardware abstraction layer over the Pico W
class HAL:
    def __init__(self, initial_state=lambda: None):
        self._state = initial_state
        self.onboard_led = Pin(PIN_SIGNAL_LED, Pin.OUT)

        self.rotary_a = Pin(PIN_ROTARY_A, Pin.IN, Pin.PULL_UP)
        self.rotary_b = Pin(PIN_ROTARY_B, Pin.IN, Pin.PULL_UP)
        self.rotary_fifo = Fifo(32, "b")
        self.rotary_a.irq(
            handler=self._rotary_interrupt_handler, trigger=Pin.IRQ_RISING, hard=True
        )

        self.i2c = I2C(1, sda=Pin(PIN_I2C_DATA), scl=Pin(PIN_I2C_CLOCK))
        self.display = ssd1306.SSD1306_I2C(128, 64, self.i2c)

    def _rotary_interrupt_handler(self, pin):
        self.rotary_fifo.put(-1 if self.rotary_b() else 1)

    def pull_rotary(self):
        if self.rotary_fifo.has_data():
            self.onboard_led.toggle()
            return self.rotary_fifo.get()

    @property
    def state(self):
        return self._state

    @state.setter
    def _state_set(self, new_state):
        if self._state is new_state:
            return
        gc_collect()
        self.onboard_led.toggle()
        self._state = new_state

    def execute(self):
        self.display.show()
        self._state()
        
        # TODO: just for testing purposes
        # this is where the cat will be
        self.display.fill_rect(
            DISPLAY_H - CAT_SIZE_H, DISPLAY_V - CAT_SIZE_V, DISPLAY_H, DISPLAY_V, 1
        )
