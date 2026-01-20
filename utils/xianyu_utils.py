import hashlib
import random
import struct
import base64
import json
from typing import Any, Dict, List

def generate_sign(t: str, token: str, data: str) -> str:
    app_key = "34839810"
    msg = f"{token}&{t}&{app_key}&{data}"
    return hashlib.md5(msg.encode('utf-8')).hexdigest()

def generate_device_id(user_id: str = "guest") -> str:
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    res = [chars[int(16 * random.random())] for _ in range(36)]
    for i in [8, 13, 18, 23]: res[i] = "-"
    res[14] = "4"
    return "".join(res) + "-" + user_id

class MessagePackDecoder:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
    def read_byte(self):
        b = self.data[self.pos]; self.pos += 1; return b
    def read_bytes(self, n):
        res = self.data[self.pos:self.pos+n]; self.pos += n; return res
    def decode_value(self) -> Any:
        fb = self.read_byte()
        if fb <= 0x7f: return fb
        elif 0x80 <= fb <= 0x8f: return {self.decode_value(): self.decode_value() for _ in range(fb & 0x0f)}
        elif 0x90 <= fb <= 0x9f: return [self.decode_value() for _ in range(fb & 0x0f)]
        elif 0xa0 <= fb <= 0xbf: return self.read_bytes(fb & 0x1f).decode('utf-8', 'ignore')
        elif fb == 0xc0: return None
        elif fb == 0xc2: return False
        elif fb == 0xc3: return True
        elif fb == 0xcc: return self.read_byte()
        elif fb == 0xcd: return struct.unpack('>H', self.read_bytes(2))[0]
        elif fb == 0xce: return struct.unpack('>I', self.read_bytes(4))[0]
        elif fb >= 0xe0: return fb - 256
        return None
    def decode(self):
        try: return self.decode_value()
        except: return None