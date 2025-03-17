from fifo import Fifo

class Ui:
    def __init__(self, hal, options = []):
        self.hal = hal
        self.options = options
        self.selected_option = 0
    
    @property
    def display(self):
        return self.hal.display

    def tick(self):
        self.display.fill(0)

        if self.selected_option:
            self.selected_option %= len(self.options)

        motion = 0
        while True:
            value = self.hal.pull_rotary()
            if not value:
                break
            motion += value
            print(motion)

        OPTION_GAP = 4
        for i, (name, callback) in enumerate(self.options):
            color = 1
            if i == self.selected_option:
                self.display.fill_rect(4, i * (8 + OPTION_GAP) - 1, 80, 8 + 2, color)
                color ^= 1
            self.display.text(name, 4, i * (8 + OPTION_GAP), color)

        self.selected_option = (self.selected_option + motion) % len(self.options)