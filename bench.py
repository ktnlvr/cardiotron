def calculate_average(file_name):
    with open(file_name, 'r') as file:
        values = [int(line.strip()) for line in file.readlines()]

    average = sum(values) / len(values)
    print(f"Average: {average:.2f}")

calculate_average("bench.txt")
