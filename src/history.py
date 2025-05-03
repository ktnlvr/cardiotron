import uos
import ujson
import urandom
import time
from logging import log, eth_log
from constants import (
    HISTORY_DATA_FILENAME,
    HISTORY_DATA_FOLDER,
    HISTORY_ENTRY_DATA_SEPARATOR,
    HISTORY_ENTRY_KEY_VALUE_SEPARATOR,
    HISTORY_NUMERIC_FIELDS,
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
        "ID": raw["id"],
        "TIMESTAMP": timestamp,
        "MEAN HR": mean_hr,
        "MEAN PPI": mean_ppi,
        "RMSSD": rmssd,
        "SDNN": sdnn,
        "SNS": sns,
        "PNS": pns,
    }

    return out


def init_history_file():
    try:
        uos.listdir(HISTORY_DATA_FOLDER)
    except OSError:
        uos.mkdir(HISTORY_DATA_FOLDER)
        f = open(HISTORY_DATA_FILENAME, "w")
        f.close()
        log("History file created")


def push_data(data):
    """
    Push a single bit of data to be stored
    """

    init_history_file()

    for field in HISTORY_NUMERIC_FIELDS:
        if field not in data:
            continue

        if not isinstance(data[field], (int, float)):
            raise ValueError(f"Invalid numeric value for {field}")

    data["TIMESTAMP"] = data["TIMESTAMP"].replace("-", "/")

    existing_data = read_data()

    existing_ids = {entry["ID"] for entry in existing_data}
    if data["ID"] not in existing_ids:
        existing_data.append(data)

    existing_data.sort(key=lambda x: x["TIMESTAMP"], reverse=True)

    with open(HISTORY_DATA_FILENAME, "w") as f:
        for entry in existing_data:
            line = HISTORY_ENTRY_DATA_SEPARATOR.join(
                f"{field}{HISTORY_ENTRY_KEY_VALUE_SEPARATOR}{str(entry[field])}"
                for field in entry
            )
            f.write(line + "\n")


def read_data():
    """
    Read and parse data from hr_data/data.txt into a list of dictionaries.
    """
    data = []

    init_history_file()

    with open(HISTORY_DATA_FILENAME, "r") as f:
        for line in f.readlines():
            values = line.strip().split(HISTORY_ENTRY_DATA_SEPARATOR)

            entry = {
                p[0]: p[1]
                for p in map(
                    lambda s: s.split(HISTORY_ENTRY_KEY_VALUE_SEPARATOR),
                    values,
                )
            }

            for k, v in entry.items():
                if k == "ID":
                    entry[k] = int(v)
                    continue
                if k in HISTORY_NUMERIC_FIELDS:
                    entry[k] = float(v)

            data.append(entry)

    return data


# random integer generator
def randrange(a, b):
    return a + urandom.getrandbits(8) % (b - a + 1)
