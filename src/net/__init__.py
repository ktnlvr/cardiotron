"""
Network utilities
"""
import io
from typing import Union

def encode(input: Union[str, bytes]) -> bytes:
    """Convert string or bytes to bytes"""
    return input.encode() if isinstance(input, str) else input

def decode(input: Union[str, bytes]) -> str:
    """Convert string or bytes to string"""
    return input.decode() if isinstance(input, bytes) else input

def unquote(string: Union[str, bytes]) -> str:
    """URL-decode a string"""
    bits = encode(string).split(b'%')
    result = bits[0].decode()
    for bit in bits[1:]:
        hex_char = bytes([int(bit[:2], 16)])
        remaining = bit[2:]
        result += hex_char.decode() + remaining.decode()
    return result

class defaulter_dict(dict):
    """Dictionary with default value generator"""
    def __init__(self, *r, **k):
        super().__init__(*r, **k)

    def get(self, key, defaulter=None):
        value = super().get(key)
        if value is None and defaulter:
            value = defaulter(key)
            self[key] = value
        return value

class enumstr:
    """String enum class"""
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        if isinstance(self.value, tuple):
            return tuple(x.decode() if isinstance(x, (bytes, bytearray)) else x for x in self.value)
        return self.value.decode() if isinstance(self.value, (bytes, bytearray)) else self.value
