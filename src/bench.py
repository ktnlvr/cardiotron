from time import time_ns

spans = {}


def span_begin(name):
    spans[name] = time_ns()


def span_end(name):
    dt = time_ns() - spans[name]
    print(name, dt / 10000)


def span(name):
    def wrapper(f):
        def wrapped(*args, **kwargs):
            span_begin(name)
            ret = f(*args, **kwargs)
            span_end(name)
            return ret

        return wrapped

    return wrapper
