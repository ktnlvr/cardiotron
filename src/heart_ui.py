import math
import time
from constants import DISPLAY_WIDTH_PX, DISPLAY_HEIGHT_PX

# Heart animation parameters
HEART_SIZE = 18  # Base size of the heart in pixels
HEART_PULSE_SPEED = 0.8  # Seconds per heartbeat
HEART_PULSE_MIN = 0.7  # Minimum scale (70%)
HEART_PULSE_MAX = 1.3  # Maximum scale (130%)

# Calculate maximum size at largest scale
MAX_HEART_SIZE = int(HEART_SIZE * HEART_PULSE_MAX)

# Position the heart to stay on-screen even at max size (with a small margin)
MARGIN = 2
HEART_X = max(0, DISPLAY_WIDTH_PX - MAX_HEART_SIZE - MARGIN)  # Right corner
HEART_Y = MARGIN  # Top corner (moved slightly down to avoid top edge)

# Heart shape coordinates (normalized to 1.0)
HEART_SHAPE = [
    (0.50, 0.10),  # Top center (cleft)
    (0.35, 0.05),  # Left lobe top start
    (0.20, 0.10),  # Left lobe peak
    (0.10, 0.25),  # Left lobe curve
    (0.05, 0.40),  # Left side
    (0.10, 0.60),  # Left bottom curve start
    (0.30, 0.80),  # Left bottom curve
    (0.50, 1.00),  # Bottom point
    (0.70, 0.80),  # Right bottom curve
    (0.90, 0.60),  # Right bottom curve start
    (0.95, 0.40),  # Right side
    (0.90, 0.25),  # Right lobe curve
    (0.80, 0.10),  # Right lobe peak
    (0.65, 0.05),  # Right lobe top start
]


def draw_heart(display, scale=1.0):
    """
    Draw a heart shape on the display with the given scale, ensuring it stays on-screen.

    Args:
        display: The display object to draw on
        scale: Scale factor for the heart size (1.0 is normal size)
    """
    size = HEART_SIZE * scale
    pixels = set()  # Track filled pixels to avoid duplicates

    # Draw the heart outline
    for i in range(len(HEART_SHAPE)):
        x1, y1 = HEART_SHAPE[i]
        x2, y2 = HEART_SHAPE[(i + 1) % len(HEART_SHAPE)]

        x1_pos = HEART_X + int(x1 * size)
        y1_pos = HEART_Y + int(y1 * size)
        x2_pos = HEART_X + int(x2 * size)
        y2_pos = HEART_Y + int(y2 * size)

        # Draw line between points using a simple Bresenham-like approach
        dx = abs(x2_pos - x1_pos)
        dy = abs(y2_pos - y1_pos)
        steps = max(dx, dy)
        if steps == 0:
            # Clip coordinates to stay on-screen
            x = min(max(x1_pos, 0), DISPLAY_WIDTH_PX - 1)
            y = min(max(y1_pos, 0), DISPLAY_HEIGHT_PX - 1)
            display.pixel(x, y, 1)
            pixels.add((x, y))
            continue

        x_step = (x2_pos - x1_pos) / steps
        y_step = (y2_pos - y1_pos) / steps
        for step in range(int(steps) + 1):
            x = int(x1_pos + step * x_step)
            y = int(y1_pos + step * y_step)
            # Clip coordinates to stay on-screen
            x = min(max(x, 0), DISPLAY_WIDTH_PX - 1)
            y = min(max(y, 0), DISPLAY_HEIGHT_PX - 1)
            display.pixel(x, y, 1)
            pixels.add((x, y))

    # Scanline fill the heart
    min_y = max(HEART_Y, 0)
    max_y = min(HEART_Y + int(size), DISPLAY_HEIGHT_PX - 1)
    for y in range(min_y, max_y + 1):
        intersections = []
        for i in range(len(HEART_SHAPE)):
            x1, y1 = HEART_SHAPE[i]
            x2, y2 = HEART_SHAPE[(i + 1) % len(HEART_SHAPE)]

            y1_pos = HEART_Y + y1 * size
            y2_pos = HEART_Y + y2 * size
            if (y1_pos <= y < y2_pos) or (y2_pos <= y < y1_pos):
                x1_pos = HEART_X + x1 * size
                x2_pos = HEART_X + x2 * size
                t = (y - y1_pos) / (y2_pos - y1_pos) if y2_pos != y1_pos else 0
                x = x1_pos + t * (x2_pos - x1_pos)
                intersections.append(int(x))

        # Sort intersections and fill between pairs
        intersections.sort()
        for i in range(0, len(intersections), 2):
            if i + 1 < len(intersections):
                x_start = max(intersections[i], 0)
                x_end = min(intersections[i + 1], DISPLAY_WIDTH_PX - 1)
                for x in range(x_start, x_end + 1):
                    if (x, y) not in pixels:
                        display.pixel(x, y, 1)
                        pixels.add((x, y))


def update_heart_animation(display, last_update_time):
    """
    Update the heart animation to mimic a realistic heartbeat.

    Args:
        display: The display object to draw on
        last_update_time: The time of the last update

    Returns:
        The new last_update_time
    """
    current_time = time.time()
    elapsed = current_time - last_update_time

    # Calculate phase of the heartbeat (0 to 1)
    phase = (elapsed % HEART_PULSE_SPEED) / HEART_PULSE_SPEED

    # Simulate a realistic heartbeat:
    # - Quick expansion (systolic phase)
    # - Slower relaxation (diastolic phase)
    if phase < 0.3:  # Systolic phase (quick bump)
        t = phase / 0.3
        scale = HEART_PULSE_MIN + (HEART_PULSE_MAX - HEART_PULSE_MIN) * (
            1 - math.exp(-5 * t)
        )
    else:  # Diastolic phase (slower relaxation)
        t = (phase - 0.3) / 0.7
        scale = HEART_PULSE_MAX - (HEART_PULSE_MAX - HEART_PULSE_MIN) * (
            1 - math.exp(-3 * (1 - t))
        )

    # Clear the previous heart area (use MAX_HEART_SIZE to cover the largest possible area)
    display.fill_rect(HEART_X, HEART_Y, MAX_HEART_SIZE, MAX_HEART_SIZE, 0)

    # Draw the heart with the current scale
    draw_heart(display, scale)

    return current_time
