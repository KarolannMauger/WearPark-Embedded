import struct
import time
from dataclasses import dataclass

_ENDIAN = "<"

TYPE_AUTH = 0
TYPE_SINGLE = 1

_AUTH_FMT = _ENDIAN + "B q"
_SINGLE_FMT = _ENDIAN + "B I 6f"

def epoch_ms() -> int:
    return int(time.time() * 1000)

def encode_auth_frame(jwt_token: str, timestamp_ms: int | None = None) -> bytes:
    if timestamp_ms is None:
        timestamp_ms = epoch_ms()
    jwt_bytes = (jwt_token or "").encode("utf-8") + b"\x00"
    header = struct.pack(_AUTH_FMT, TYPE_AUTH, int(timestamp_ms))
    return header + jwt_bytes

@dataclass(frozen=True)
class Sample:
    ms_offset: int
    ax: float
    ay: float
    az: float
    gx: float
    gy: float
    gz: float

def encode_single_frame(sample: Sample) -> bytes:
    return struct.pack(
        _SINGLE_FMT,
        TYPE_SINGLE,
        int(sample.ms_offset),
        float(sample.ax),
        float(sample.ay),
        float(sample.az),
        float(sample.gx),
        float(sample.gy),
        float(sample.gz),
    )