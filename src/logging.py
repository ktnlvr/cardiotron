import os
from errno import EEXIST
from utils import localtime_string

active_log = None
log_number = 0


def init_logs():
    global log_number, active_log

    try:
        os.mkdir("logs")
    except OSError as e:
        if e.errno == EEXIST:
            pass
        else:
            raise

    logfiles = os.listdir("logs")
    print(f"{len(logfiles)} past logs found!")

    localtime = localtime_string()
    log_name = f"log-{localtime}.txt"
    active_log = open(f"logs/{log_name}", "a+")


def eth_log(*args):
    string = f"[{localtime_string()}] " + " ".join(map(str, args))
    print(string)
    return string


def log(*args):
    if not active_log:
        init_logs()
    string = eth_log(*args) + "\n"
    active_log.write(string.encode("utf-8"))  # type: ignore
    active_log.flush()  # type: ignore
    return string
