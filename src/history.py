import uos
import ujson
import urequests
from time import localtime
from logging import log, eth_log
from constants import (
    HISTORY_DATA_FILENAME,
    HISTORY_DATA_FOLDER,
    KUBIOS_FIELDS,
    NUMERIC_FIELDS,
)


def fetch_kubios_data(api_url, headers):
    """
    Fetch data from Kubios API
    """
    try:
        log(f"Fetching data from Kubios API: {api_url}")
        response = urequests.get(api_url, headers=headers)

        if response.status_code == 200:
            log("Successfully fetched data from Kubios API")
            return response.text
        else:
            eth_log(f"Kubios API request failed: {response.status_code}")
            return None

    except Exception as e:
        eth_log(f"Error fetching data from Kubios API: {str(e)}")
        return None


def store_data(json_data):
    """
    Parse JSON data from Kubios and store it in hr_data/data.txt.
    Each line is a comma-separated entry with newest data at the top.
    """
    try:
        data = ujson.loads(json_data)
        if not isinstance(data, list):
            raise ValueError("Expected JSON array")

        # Validate data structure
        for entry in data:
            if not all(field in entry for field in KUBIOS_FIELDS):
                raise ValueError("Missing required fields")

            # Validate numeric fields
            for field in NUMERIC_FIELDS:
                if not isinstance(entry[field], (int, float)):
                    raise ValueError(f"Invalid numeric value for {field}")

        existing_data = read_data()

        # Merge new data with existing data (avoid duplicates)
        existing_timestamps = {entry["TIMESTAMP"] for entry in existing_data}
        for entry in data:
            if entry["TIMESTAMP"] not in existing_timestamps:
                existing_data.append(entry)

        # Sort by timestamp (newest first)
        existing_data.sort(key=lambda x: x[KUBIOS_FIELDS[0]], reverse=True)

        # Ensure hr_data folder exists
        try:
            uos.listdir(HISTORY_DATA_FOLDER)
        except OSError:
            uos.mkdir(HISTORY_DATA_FOLDER)
            log("Created hr_data directory")

        # Write data to file, assuming JSON data is newest-first
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


def test_store_mock_data():
    """
    Temporary test function to store mock Kubios response data.
    This function reads a mock JSON file and passes it to store_data().
    """
    try:
        # Ensure the history directory exists
        try:
            uos.listdir(HISTORY_DATA_FOLDER)
        except OSError:
            uos.mkdir(HISTORY_DATA_FOLDER)
            log("Created history directory")

        # Create a mock Kubios response file if it doesn't exist
        mock_file_path = "./examples/measurements.txt"
        try:
            with open(mock_file_path, "r") as f:
                mock_data = f.read()
        except OSError:
            # Create mock data if file doesn't exist
            mock_data = """[
                {
                    "TIMESTAMP": "2023-04-18 14:30:00",
                    "TIMEZONE": "UTC",
                    "MEAN HR": 75,
                    "MEAN PPI": 800,
                    "RMSSD": 45,
                    "SDNN": 65,
                    "SNS": 30,
                    "PNS": 70
                },
            ]"""
            with open(mock_file_path, "w") as f:
                f.write(mock_data)
            log("Created mock Kubios response file")

        # Store the mock data
        result = store_data(mock_data)
        if result:
            log("Successfully stored mock Kubios data")
        else:
            eth_log("Failed to store mock Kubios data")

        return result
    except Exception as e:
        eth_log(f"Error in test_store_mock_data: {str(e)}")
        return False
