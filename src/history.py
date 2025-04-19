import uos
import ujson
import urequests
from time import localtime
from logging import log, eth_log
from constants import HISTORY_DATA_FILENAME, HISTORY_DATA_FOLDER

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
            eth_log(
                f"Kubios API request failed: {response.status_code}"
            )
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

        required_fields = [
            "TIMESTAMP",
            "TIMEZONE",
            "MEAN HR",
            "MEAN PPI",
            "RMSSD",
            "SDNN",
            "SNS",
            "PNS",
        ]

        # Validate data structure
        for entry in data:
            if not all(field in entry for field in required_fields):
                raise ValueError("Missing required fields")

            # Validate numeric fields
            for field in ["MEAN HR", "MEAN PPI", "RMSSD", "SDNN", "SNS", "PNS"]:
                if not isinstance(entry[field], (int, float)):
                    raise ValueError(f"Invalid numeric value for {field}")

        # Ensure hr_data folder exists
        try:
            uos.listdir(HISTORY_DATA_FOLDER)
        except OSError:
            uos.mkdir(HISTORY_DATA_FOLDER)
            log("Created hr_data directory")

        # Write data to file, assuming JSON data is newest-first
        with open(HISTORY_DATA_FILENAME, "w") as f:
            for entry in data:
                line = ",".join(
                    [
                        entry["TIMESTAMP"],
                        entry["TIMEZONE"],
                        str(entry["MEAN HR"]),
                        str(entry["MEAN PPI"]),
                        str(entry["RMSSD"]),
                        str(entry["SDNN"]),
                        str(entry["SNS"]),
                        str(entry["PNS"]),
                    ]
                )
                f.write(line + "\n")

        log(f"Successfully stored {len(data)} entries in history")
        return True

    except ujson.JSONDecodeError as e:
        eth_log(f"JSON parsing error: {str(e)}")
        return False
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
        with open(HISTORY_DATA_FILENAME, "r") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    values = line.strip().split(",")
                    if len(values) != 8:
                        eth_log(
                            f"Skipping malformed line {line_num}: incorrect number of fields"
                        )
                        continue

                    entry = {
                        "TIMESTAMP": values[0],
                        "TIMEZONE": values[1],
                        "MEAN HR": float(values[2]),
                        "MEAN PPI": float(values[3]),
                        "RMSSD": float(values[4]),
                        "SDNN": float(values[5]),
                        "SNS": float(values[6]),
                        "PNS": float(values[7]),
                    }
                    data.append(entry)
                except (ValueError, IndexError) as e:
                    eth_log(f"Error parsing line {line_num}: {str(e)}")
                    continue

        log(f"Successfully read {len(data)} entries from history")
    except OSError as e:
        eth_log(f"Error reading history file: {str(e)}")

    return data
