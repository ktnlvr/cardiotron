from hal import HAL
from ui import Ui


class Machine(HAL):
    def __init__(self):
        super().__init__(self.main_menu)
        self.main_menu_ui = Ui(self, [
            ("Measure", self._main_menu_measure),
            ("History", self._main_menu_history)
        ])

    def _main_menu_measure(self):
        self.state = self.toast

    def _main_menu_history(self):
        self.state = self.toast

    def main_menu(self):
        self.main_menu_ui.tick()
    
    def toast(self):
        self.display.fill(0)
        self.display.text("Toast", 0, 0)
