from constants import (
    CHAR_SIZE_HEIGHT_PX,
    DISPLAY_HEIGHT_PX,
    DISPLAY_WIDTH_PX,
    CHAR_SIZE_WIDTH_PX,
    UI_MARGIN,
)
from heart_ui import update_heart_animation
from history import read_data
import time

from logging import log


class HistoryUi:
    def __init__(self, hal, history_count=0):
        self.asm = hal
        self.history_data = read_data()
        self.history_count = history_count
        self.selected_row = 0  # 0-3 for rows 1-4
        self.entries_per_screen = 4  # Show 4 entries at a time
        self.heart_animation_time = time.time()

    @property
    def display(self):
        return self.asm.display

    def history_entry_tick(self, index):
        """
        Handle display and navigation for a single history entry
        Args:
            index: Index of the entry to display
        Returns:
            int: Next index to display, or None to stay in current state
        """
        if self.asm.button_long():
            self.asm.state(self.asm.main_menu)
            return

        if self.asm.button_short():
            # FIXME(Artur): after refactoring does not keep track of the selected index
            self.asm.state(
                self.asm.history,
            )

        self.display.fill(0)

        # Get the entry and reformat timestamp to dd/mm hh:mm
        entry = self.history_data[index]
        timestamp_parts = entry["TIMESTAMP"].split()
        if len(timestamp_parts) >= 2:
            date_parts = timestamp_parts[0].split("/")
            time_parts = timestamp_parts[1].split(":")
            if len(date_parts) >= 2 and len(time_parts) >= 2:
                # Format as "dd/mm hh:mm"
                formatted_date = f"{date_parts[0]}/{date_parts[1]}"
                formatted_time = f"{time_parts[0]}:{time_parts[1]}"
                timestamp = f"{formatted_date} {formatted_time}"
                self.display.text(timestamp, 0, 0, 1)
            else:
                self.display.text(entry["TIMESTAMP"], 0, 0, 1)
        else:
            self.display.text(entry["TIMESTAMP"], 0, 0, 1)

        hr = f"HR: {round(entry['MEAN HR'])} BPM"
        ppi = f"PPI: {round(entry['MEAN PPI'])} ms"
        rmssd = f"RMSSD: {entry['RMSSD']:.3f} ms"
        sdnn = f"SDNN: {entry['SDNN']:.3f} ms"
        output = [hr, ppi, rmssd, sdnn]

        if "SNS" in entry:
            output.append(f"SNS: {entry['SNS']:.3f}")
        elif "PNS" in entry:
            output.append(f"PNS: {entry['PNS']:.3f}")

        log(entry)

        MICRO_UI_GAP_PX = 1

        for i, string in enumerate(output):
            y = (i + 1) * (CHAR_SIZE_HEIGHT_PX + MICRO_UI_GAP_PX) + UI_MARGIN
            self.display.text(
                string,
                0,
                y,
                1,
            )

        self.heart_animation_time = update_heart_animation(
            self.display, self.heart_animation_time
        )

        self.display.show()
        return None

    def history_tick(self):
        """
        Handle rotary input and button presses for history navigation
        Returns:
            - None: Continue in history view
            - function: State to transition to
        """
        if self.asm.button_long():
            self.asm.state(self.asm.main_menu)
            return

        if self.asm.button_short() and self.history_data:
            self.asm.state(self.asm._history_entry, self.history_count)
            return

        # Handle rotary input
        rotary_motion = self.asm.pull_rotary()

        data_len = len(self.history_data)
        if data_len == 0:
            self._update_display(0, 0)  # Display empty state

        # Calculate the current window of entries to show
        start_idx = max(0, self.history_count - self.selected_row)
        end_idx = min(data_len, start_idx + self.entries_per_screen)

        if not rotary_motion and not self.asm.is_first_frame:
            self._update_display(start_idx, end_idx)
            return

        self.history_data = read_data()

        # Handle rotary navigation
        if rotary_motion > 0:  # Clockwise rotation
            if self.history_count < data_len - 1:  # Not at the last entry
                if self.selected_row < 3:  # Not at the last row
                    # Move down
                    self.selected_row += 1
                else:
                    # At the last row
                    self.history_count += 1
                    # Keep the highlight on the last row
                    self.selected_row = min(3, self.history_count)
                # Recalculate start_idx after navigation
                start_idx = max(0, self.history_count - self.selected_row)

        elif rotary_motion < 0:  # Counter-clockwise rotation
            if self.selected_row > 0:  # Not at the first row
                # Move up
                self.selected_row -= 1
                # Update history_count to match the new selected row
                self.history_count = start_idx + self.selected_row
            elif self.history_count > 0:  # At the first row
                # Move to previous entry
                self.history_count -= 1
                # Keep the highlight on the first row
                self.selected_row = 0
                # Recalculate start_idx to reflect the scroll
                start_idx = max(0, self.history_count - self.selected_row)

        # Calculate end_idx based on the updated start_idx
        end_idx = min(data_len, start_idx + self.entries_per_screen)

        # Ensure history_count stays within bounds
        self.history_count = max(0, min(self.history_count, data_len - 1))

        # Update the display with the calculated indices
        self._update_display(start_idx, end_idx)

    def _update_display(self, start_idx, end_idx):
        """Update the display with the current history entries"""
        self.display.fill(0)

        self.display.text("History", 0, 0, 1)

        data_len = len(self.history_data)
        if data_len == 0:
            empty_text = "Nothing yet..."
            text_size_x_px = len(empty_text) * CHAR_SIZE_WIDTH_PX
            horizontal_center = DISPLAY_WIDTH_PX // 2 - text_size_x_px // 2
            vertical_center = DISPLAY_HEIGHT_PX // 2
            self.display.text(empty_text, horizontal_center, vertical_center, 1)

        current_page_number = self.history_count + 1
        page_text = f"{current_page_number}/{data_len}"

        if data_len > 0:
            # Position the number at the top right
            page_width = len(page_text) * CHAR_SIZE_WIDTH_PX
            self.display.text(page_text, DISPLAY_WIDTH_PX - page_width, 0, 1)
        else:
            self.display.text("0/0", DISPLAY_WIDTH_PX, 0, 1)

        # Display the entries
        for i, idx in enumerate(range(start_idx, end_idx)):
            entry = self.history_data[idx]
            timestamp = entry["TIMESTAMP"]  # Already formatted in read_data

            # Calculate position for this entry
            y_pos = 12 + (i * 12)  # Spacing of 12 pixels

            # Draw the entry
            if idx == self.history_count:
                # For selected entry, draw inverted background
                self.display.fill_rect(0, y_pos - 1, DISPLAY_WIDTH_PX, 10, 1)
                # Draw text in inverted color
                self.display.text(timestamp, 8, y_pos, 0)
            else:
                # For non-selected entries, draw normal text
                self.display.text(timestamp, 8, y_pos, 1)

        self.display.show()
