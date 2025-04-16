"""
Network utilities
"""

import io


def encode(input):
    """Convert string or bytes to bytes"""
    return input.encode() if isinstance(input, str) else input


def decode(input):
    """Convert string or bytes to string"""
    return input.decode() if isinstance(input, bytes) else input


def unquote(string):
    """URL decode string or bytes to string"""
    string = decode(string)
    return string.replace("%20", " ").replace("%2F", "/")


class defaulter_dict(dict):
    """Dictionary with default value generator"""

    def __init__(self, *r, **k):
        super().__init__(*r, **k)

    def get(self, key, default=None):
        if key not in self:
            if default is not None:
                self[key] = default() if callable(default) else default
            return default
        return super().get(key)


class enumstr:
    """String enum class"""

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return self.value
