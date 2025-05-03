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
import re


def kubios_response_to_data(raw: dict) -> dict:
    data = raw["data"]
    assert data["status"] == "ok"

    analysis = data["analysis"]
    mean_hr = analysis["mean_hr_bpm"]
    sdnn = analysis["sdnn_ms"]
    rmssd = analysis["rmssd_ms"]
    mean_ppi = analysis["mean_rr_ms"]
    timestamp = analysis["create_timestamp"]
    sns = analysis["sns_index"]
    pns = analysis["pns_index"]

    timestamp = f"0/0/0 20:30"

    """
    Convert the raw kubios response to the data format apt
    for storage
    """
    out = {
        "TIMESTAMP": timestamp,
        "MEAN HR": mean_hr,
        "MEAN PPI": mean_ppi,
        "RMSSD": rmssd,
        "SDNN": sdnn,
        "SNS": sns,
        "PNS": pns,
    }

    return out


def push_data(data):
    """
    Push a single bit of data to be stored
    """

    for field in NUMERIC_FIELDS:
        if field not in data:
            continue

        if not isinstance(data[field], (int, float)):
            raise ValueError(f"Invalid numeric value for {field}")

    data["TIMESTAMP"] = data["TIMESTAMP"].replace("-", "/")

    existing_data = read_data()

    existing_timestamps = {entry["TIMESTAMP"] for entry in existing_data}
    if data["TIMESTAMP"] not in existing_timestamps:
        existing_data.append(data)

    existing_data.sort(key=lambda x: x["TIMESTAMP"], reverse=True)

    try:
        uos.listdir(HISTORY_DATA_FOLDER)
    except OSError:
        uos.mkdir(HISTORY_DATA_FOLDER)
        log("Created hr_data directory")

    with open(HISTORY_DATA_FILENAME, "w") as f:
        for entry in existing_data:
            line = ",".join(str(entry[field]) for field in KUBIOS_FIELDS)
            f.write(line + "\n")

    log(
        f"Successfully stored {len(data)} new entries, total {len(existing_data)} entries"
    )


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
