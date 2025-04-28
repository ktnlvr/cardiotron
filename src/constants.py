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

DISPLAY_WIDTH_PX = 128
DISPLAY_HEIGHT_PX = 64
CAT_SIZE_WIDTH_PX = 32
CAT_SIZE_HEIGTH_PX = 32
CHAR_SIZE_WIDTH_PX = 8
CHAR_SIZE_HEIGHT_PX = 8

# Options for usability and control

ROTARY_BUTTON_DEBOUNCE_MS = 20
# How many rotations need to be registered to change the selected option
ROTARY_ROTATION_SENSETIVITY = 1
# How long to wait before resetting accumulating options
ROTARY_ROTATION_RESET_TIMEOUT_MS = 250
# How long does a long press take, everything below is a short press
LONG_PRESS_MS = 200

# The free space between the options in a UI menu
UI_OPTION_GAP = 6
UI_MARGIN = 4

# XXX: the UI transitions are non-linear, so they take some time to execute
# Modify this as you see fit and test by feel.
_UI_LERP_RATE = 0.5
UI_LERP_RATE = log(_UI_LERP_RATE)

# The sample rate of the heart beat sensor (in Hz)
SAMPLE_RATE = 15
# Time difference between each sample taken(in ms)
TIMESTAMP_DIFFERENCE_SENSOR = 0.004
# Alpha value for the low pass filter
ALPHA = 0.5
# Samples per pixel
SAMPLES_PROCESSED_PER_COLLECTED = 3
# Pin number of the heart beat sensor
PIN_SENSOR = 27
# Total samples to take in account when calculating heart beat measurements
# Note: The total samples would be SAMPLE_SIZE * SAMPLES_PER_PIXEL
SAMPLE_SIZE = 200
# Last n values taken in consideration when the heart rate is calculated
MEAN_WINDOW_SIZE = 50
PPI_SIZE = 50

# Scaling factor for the next peak
MEAN_WINDOW_PERCENT = 1.35
MIN_PEAK_INTERVAL_MS = 500
MAX_PEAK_INTERVAL_MS = 1000
MAX_NO_PEAK_INTERVAL_MS = 2500

# Samples to display on screen
SAMPLES_ON_SCREEN_SIZE = DISPLAY_WIDTH_PX - 40
# The amount of samples to be collected from the ADC
HEART_SAMPLES_BUFFER_SIZE = 256

UI_CLOCK_HOUR_ARROW_LENGTH_PX = 10
UI_CLOCK_MINUTE_ARROW_LENGTH_PX = 16
UI_CLOCK_SECOND_ARROW_LENGTH_PX = 20

DEFAULT_MQTT_SERVER_ADDR = "meow11.asuscomm.com"
DEFAULT_MQTT_PORT = 1883

MQTT_TOPIC_KUBIOS_RESPONSE = "kubios-response"
MQTT_TOPICS = [MQTT_TOPIC_KUBIOS_RESPONSE]

# History and data storage constants
HISTORY_ENTRIES_PER_PAGE = 5
HISTORY_DATA_FILENAME = "hr_data/data.txt"
HISTORY_DATA_FOLDER = "hr_data"
KUBIOS_FIELDS = [
    "TIMESTAMP",
    "TIMEZONE",
    "MEAN HR",
    "MEAN PPI",
    "RMSSD",
    "SDNN",
    "SNS",
    "PNS",
]
NUMERIC_FIELDS = ["MEAN HR", "MEAN PPI", "RMSSD", "SDNN", "SNS", "PNS"]