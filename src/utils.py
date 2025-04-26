from time import localtime


def localtime_string() -> str:
    Y, M, D, H, m, s, *_ = localtime()
    return f"{Y:04}-{M:02}-{D:02}T{H:02}:{m:02}:{s:02}"
