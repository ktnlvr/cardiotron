from math import log

# The options below refer to the pinout of the board
# and are unlikely to change

PIN_SIGNAL_LED = "LED"
PIN_ROTARY_A = 10
PIN_ROTARY_B = 11
PIN_ROTARY_BUTTON = 12
PIN_I2C_DATA = 14
PIN_I2C_CLOCK = 15

# Options tat are specific to the modules being used

DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
CAT_SIZE_WIDTH = 32
CAT_SIZE_HEIGTH = 32
CHAR_SIZE_WIDTH = 8
CHAR_SIZE_HEIGHT = 8

# Options for usability and control

ROTARY_BUTTON_DEBOUNCE_MS = 60
# How many rotations need to be registered to change the selected option
ROTARY_ROTATION_SENSETIVITY = 1
# How long to wait before resetting accumulating options
ROTARY_ROTATION_RESET_TIMEOUT_MS = 250
# How long does a long press take, everything below is a short press
LONG_PRESS_MS = 200

# The free space between the options in a UI menu
UI_OPTION_GAP = 6
UI_MARGIN = 4

UI_CLOCK_HOUR_ARROW_LENGTH_PX = 10
UI_CLOCK_MINUTE_ARROW_LENGTH_PX = 16
UI_CLOCK_SECOND_ARROW_LENGTH_PX = 20
