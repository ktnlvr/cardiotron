from array import array

class Ringbuffer:
    def __init__(self, size, typecode):
        self.start = 0
        self.end = 0
        self.data = array(typecode)
        self.size = size
        for i in range(size):
            self.data.append(0)

    def __len__(self):
        return self.size

    def __iter__(self):
        return iter(self.data)

    def append(self, value):
        print(value)
        if (self.end + 1) % self.size == self.start:
            self.start = (self.start + 1) % self.size
        self.data[self.end] = value
        self.end = (self.end + 1) % self.size

    def get(self):
        if self.start == self.end:
            return None
        else:
            value = self.data[self.start]
            self.start = (self.start + 1) % self.size
            return value

    def __repr__(self):
        out = ''
        for i, v in enumerate(self.data):
            if i == self.start:
                out += '| '
            if i == self.end:
                out += '> '
            out += str(v) +' '
        return out
