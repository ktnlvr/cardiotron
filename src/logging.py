import os
from errno import EEXIST

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
    for file in logfiles:
        new_log_number = file[len("log-") : -len(".txt")]
        log_number = max(log_number, int(new_log_number)) + 1
    print(f"{log_number} past logs found")
    active_log = open(f"logs/log-{log_number}.txt", "a")


def log(*args):
    if not active_log:
        init_logs()
    string = " ".join(map(str, args))
    print(string)

    active_log.write(string.encode("utf-8"))  # type: ignore
    active_log.flush()  # type: ignore
