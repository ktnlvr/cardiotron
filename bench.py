from time import time_ns

spans = {}


def span_begin(name):
    spans[name] = time_ns()


def span_end(name):
    dt = time_ns() - spans[name]
    print(dt / 10000)

def calculate_average(file_name):
    with open(file_name, 'r') as file:
        values = [float(line.strip()) for line in file.readlines()]
    average = sum(values) / len(values)
    print(f"Average: {average:.2f}")

calculate_average("bench.txt")