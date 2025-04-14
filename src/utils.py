from time import localtime


def localtime_string() -> str:
    Y, M, D, H, m, s, *_ = localtime()
    return f"{Y}-{M}-{D}T{H}:{m}:{s}"
