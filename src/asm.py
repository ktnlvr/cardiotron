from hal import HAL
from ui import Ui



class Machine(HAL):
    def go_to_state(self, state):
        return lambda: self.state(state)

    def __init__(self):
        super().__init__(self.main_menu)
        self.main_menu_ui = Ui(self, [
            ("Measure", self.go_to_state(self.toast)),
            ("History", self.go_to_state(self.toast)),
            ("Setup", self.go_to_state(self.toast))
        ])

    def main_menu(self):
        self.main_menu_ui.tick()
    
    def toast(self):
        if self.button():
            self.state(self.main_menu)

        self.display.fill(0)
        self.display.text("Toast", 0, 0)
