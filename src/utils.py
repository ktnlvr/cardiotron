from time import localtime


def localtime_string() -> str:
    Y, M, D, H, m, s, *_ = localtime()
    return f"{Y:04}-{M:02}-{D:02}T{H:02}:{m:02}:{s:02}"


def hash_int_list(ls) -> int:
    # polynomial hash X coordinate compression
    unique = sorted(set(ls))
    compressed = {v: i for i, v in enumerate(unique)}
    hashed = 0
    mod = 1000000007

    for x in ls:
        y = compressed[x]
        hashed = (hashed * len(unique) + y) % mod
    return hashed
