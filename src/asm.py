from hal import HAL


class Machine(HAL):
    def __init__(self):
        self.a = 0
        super().__init__(self.read_fifo)

    def read_fifo(self):
        while True:
            b = self.pull_rotary()
            if not b:
                break
            self.a += b
            print(self.a)
