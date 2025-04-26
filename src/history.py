import uos
import ujson
import urandom
import time
from logging import log, eth_log
from constants import (
    HISTORY_DATA_FILENAME,
    HISTORY_DATA_FOLDER,
    KUBIOS_FIELDS,
    NUMERIC_FIELDS,
)


def fetch_kubios_data(file_path=None):
    """
    Read Kubios data from a local JSON file.
    """
    try:
        # Use default path if none provided
        if file_path is None:
            file_path = "kubios_data.json"

        log(f"Reading Kubios data from file: {file_path}")

        # Check if the file exists
        try:
            with open(file_path, "r") as f:
                json_data = f.read()

            log("Successfully read Kubios data from file")
            return json_data
        except OSError:
            eth_log(f"File not found: {file_path}")
            return None

    except Exception as e:
        eth_log(f"Error reading Kubios data from file: {str(e)}")
        return None


def store_data(json_data):
    """
    Parse JSON data from Kubios and store it in hr_data/data.txt.
    Each line is a comma-separated entry with newest data at the top.
    Timestamps are formatted as "dd/mm/yy hh:mm".
    """
    try:
        data = ujson.loads(json_data)
        if not isinstance(data, list):
            raise ValueError("Expected JSON array")

        # Validate data structure and format timestamps
        for entry in data:
            if not all(field in entry for field in KUBIOS_FIELDS):
                raise ValueError("Missing required fields")

            # Validate numeric fields
            for field in NUMERIC_FIELDS:
                if not isinstance(entry[field], (int, float)):
                    raise ValueError(f"Invalid numeric value for {field}")

            # Format timestamp to "dd/mm/yy hh:mm"
            if "TIMESTAMP" in entry:
                timestamp_parts = entry["TIMESTAMP"].split()
                if len(timestamp_parts) >= 2:
                    date_parts = timestamp_parts[0].split("-")
                    time_parts = timestamp_parts[1].split(":")
                    if len(date_parts) >= 3 and len(time_parts) >= 2:
                        # Format as "dd/mm/yy hh:mm"
                        formatted_date = (
                            f"{date_parts[2]}/{date_parts[1]}/{date_parts[0][2:]}"
                        )
                        formatted_time = f"{time_parts[0]}:{time_parts[1]}"
                        entry["TIMESTAMP"] = f"{formatted_date} {formatted_time}"

        existing_data = read_data()

        # Merge new data with existing data (avoid duplicates)
        existing_timestamps = {entry["TIMESTAMP"] for entry in existing_data}
        for entry in data:
            if entry["TIMESTAMP"] not in existing_timestamps:
                existing_data.append(entry)

        # Sort by timestamp (newest first)
        existing_data.sort(key=lambda x: x["TIMESTAMP"], reverse=True)

        # Ensure hr_data folder exists
        try:
            uos.listdir(HISTORY_DATA_FOLDER)
        except OSError:
            uos.mkdir(HISTORY_DATA_FOLDER)
            log("Created hr_data directory")

        # Write data to file as newest-first
        with open(HISTORY_DATA_FILENAME, "w") as f:
            for entry in existing_data:
                line = ",".join(str(entry[field]) for field in KUBIOS_FIELDS)
                f.write(line + "\n")

        log(
            f"Successfully stored {len(data)} new entries, total {len(existing_data)} entries"
        )
        return True

    except ValueError as e:
        eth_log(f"Data validation error: {str(e)}")
        return False
    except Exception as e:
        eth_log(f"Error storing data: {str(e)}")
        return False


def read_data():
    """
    Read and parse data from hr_data/data.txt into a list of dictionaries.
    """
    data = []
    try:
        # Check if the directory exists first
        try:
            uos.listdir(HISTORY_DATA_FOLDER)
        except OSError:
            # Directory doesn't exist, return empty list
            log("History directory doesn't exist yet")
            return data

        # Check if the file exists
        try:
            with open(HISTORY_DATA_FILENAME, "r") as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        values = line.strip().split(",")
                        if len(values) != len(KUBIOS_FIELDS):
                            eth_log(
                                f"Skipping malformed line {line_num} in history file: {line.strip()}"
                            )
                            continue

                        entry = {}
                        for i, field in enumerate(KUBIOS_FIELDS):
                            if field in NUMERIC_FIELDS:
                                entry[field] = float(values[i])
                            else:
                                entry[field] = values[i]

                        data.append(entry)
                    except (ValueError, IndexError):
                        eth_log(
                            f"Skipping malformed line {line_num} in history file: {line.strip()}"
                        )
                        continue
        except OSError:
            # File doesn't exist, return empty list
            log("History file doesn't exist yet")
            return data

        log(f"Successfully read {len(data)} entries from history")
    except Exception as e:
        eth_log(f"Error reading history file: {str(e)}")

    return data


# random integer generator
def randrange(a, b):
    return a + urandom.getrandbits(8) % (b - a + 1)


def test_store_mock_data(start_tuple, days=5, hours_per_day=8):
    """
    Temporary test function to store mock Kubios response data.
    if data is already stored, it will not be overwritten.
    """
    mock_data = []
    try:
        for day in range(days):
            for hour in range(9, 9 + hours_per_day):
                t = (
                    start_tuple[0],
                    start_tuple[1],
                    start_tuple[2] + day,
                    hour,
                    0,
                    0,
                    0,
                    0,
                )
                seconds = time.mktime(t)
                local_time = time.localtime(seconds)
                timestamp = "{:04d}-{:02d}-{:02d} {:02d}:00:00".format(
                    local_time[0], local_time[1], local_time[2], local_time[3]
                )
                entry = {
                    "TIMESTAMP": timestamp,
                    "TIMEZONE": "UTC",
                    "MEAN HR": randrange(65, 85),
                    "MEAN PPI": randrange(750, 950),
                    "RMSSD": randrange(35, 55),
                    "SDNN": randrange(50, 75),
                    "SNS": randrange(25, 35),
                    "PNS": randrange(60, 80),
                }
                mock_data.append(entry)

        # Convert the list to a JSON string
        json_data = ujson.dumps(mock_data)

        # Store the mock data
        result = store_data(json_data)
        if result:
            log("Successfully stored mock Kubios data")
        else:
            eth_log("Failed to store mock Kubios data")

        return result
    except Exception as e:
        eth_log(f"Error in test_store_mock_data: {str(e)}")
        return False
