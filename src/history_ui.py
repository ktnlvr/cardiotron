from constants import DISPLAY_WIDTH_PX


class HistoryUi:
    def __init__(self, hal, history_data, history_count=0):
        self.hal = hal
        self.history_data = history_data
        self.history_count = history_count
        self.selected_row = 0  # 0-3 for rows 1-4
        self.entries_per_screen = 4  # Show 4 entries at a time
        self.first_frame = True

    @property
    def display(self):
        return self.hal.display

    def history_tick(self):
        """
        Handle rotary input and button presses for history navigation
        Returns:
            - None: Continue in history view
            - function: State to transition to
        """
        if self.hal.button_long():
            return self.hal.main_menu

        if self.hal.button_short():
            return self.hal._history_entry(self.history_count)

        # Handle rotary input
        rotary_motion = self.hal.pull_rotary()

        data_len = len(self.history_data)
        if data_len == 0:
            self._update_display(0, 0)  # Display empty state
            return None

        # Calculate the current window of entries to show
        start_idx = max(0, self.history_count - self.selected_row)
        end_idx = min(data_len, start_idx + self.entries_per_screen)

        if not rotary_motion and not self.hal.is_first_frame:
            self._update_display(start_idx, end_idx)
            return None

        self.hal.is_first_frame = False

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

        return None

    def _update_display(self, start_idx, end_idx):
        """Update the display with the current history entries"""
        self.display.fill(0)

        self.display.text("History:", 0, 0, 1)

        # Display data number (current/total)
        data_len = len(self.history_data)
        if data_len > 0:
            current_page = self.history_count + 1
            page_text = f"{current_page}/{data_len}"
            # Position the number at the top right
            page_width = len(page_text) * 8  # Approximate width of text
            self.display.text(page_text, DISPLAY_WIDTH_PX - page_width, 0, 1)
        else:
            self.display.text("0/0", DISPLAY_WIDTH_PX - page_width, 0, 1)

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
