from constants import (
    UI_OPTION_GAP,
    CHAR_SIZE_WIDTH_PX,
    UI_MARGIN,
    CHAR_SIZE_HEIGHT_PX,
    DISPLAY_WIDTH_PX,
    DISPLAY_HEIGHT_PX,
)


class HistoryUi:
    def __init__(self, hal, history_data, history_count=0):
        self.hal = hal
        self.history_data = history_data
        self.history_count = history_count
        self.selected_row = 0
        self.entries_per_screen = 4
        self.first_frame = True

    @property
    def display(self):
        return self.hal.display

    def history_tick(self):
        if self.hal.button_long():
            return self.hal.main_menu

        if self.hal.button_short():
            return self.hal._history_entry(self.history_count)

        rotary_motion = self.hal.pull_rotary()

        data_len = len(self.history_data)
        if data_len == 0:
            self._update_display(0, 0)
            return None

        start_idx = max(0, self.history_count - self.selected_row)
        end_idx = min(data_len, start_idx + self.entries_per_screen)

        if not rotary_motion and not self.hal.is_first_frame:
            self._update_display(start_idx, end_idx)
            return None

        self.hal.is_first_frame = False

        if rotary_motion > 0:
            if self.history_count < data_len - 1:
                if self.selected_row < 3:
                    self.selected_row += 1
                else:
                    self.history_count += 1
                    self.selected_row = min(3, self.history_count)
                start_idx = max(0, self.history_count - self.selected_row)

        elif rotary_motion < 0:
            if self.selected_row > 0:
                self.selected_row -= 1
                self.history_count = start_idx + self.selected_row
            elif self.history_count > 0:
                self.history_count -= 1
                self.selected_row = 0
                start_idx = max(0, self.history_count - self.selected_row)

        end_idx = min(data_len, start_idx + self.entries_per_screen)

        self.history_count = max(0, min(self.history_count, data_len - 1))

        self._update_display(start_idx, end_idx)

        return None

    def _update_display(self, start_idx, end_idx):
        self.display.fill(0)

        self.display.text("History:", 0, 0, 1)

        data_len = len(self.history_data)
        if data_len > 0:
            current_page = self.history_count + 1
            page_text = f"{current_page}/{data_len}"
            page_width = len(page_text) * 8
            self.display.text(page_text, DISPLAY_WIDTH_PX - page_width, 0, 1)
        else:
            self.display.text("0/0", 0, 0, 1)

        for i, idx in enumerate(range(start_idx, end_idx)):
            entry = self.history_data[idx]
            timestamp = entry["TIMESTAMP"]

            y_pos = 12 + (i * 12)

            if idx == self.history_count:
                self.display.fill_rect(0, y_pos, DISPLAY_WIDTH_PX, 10, 1)
                self.display.text(timestamp, 8, y_pos, 0)
            else:
                self.display.text(timestamp, 8, y_pos, 1)

        self.display.show()
