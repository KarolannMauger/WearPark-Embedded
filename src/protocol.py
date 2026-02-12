import struct
import time
from dataclasses import dataclass

_ENDIAN = ">"

TYPE_AUTH = 0
TYPE_PACKED = 2

_PACKED_HDR_FMT = _ENDIAN + "B I"
_PACKED_ITEM_FMT = _ENDIAN + "I 6f"

def epoch_ms() -> int:
    return int(time.time() * 1000)

def encode_auth_frame(jwt_token: str, timestamp_ms: int | None = None) -> bytes:
    if timestamp_ms is None:
        timestamp_ms = epoch_ms()
    jwt_bytes = (jwt_token or "").encode("utf-8") + b"\x00"
    header = struct.pack(_ENDIAN + "B q", TYPE_AUTH, int(timestamp_ms))
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

def encode_packed_frame(samples: list[Sample]) -> bytes:
    out = bytearray()
    out += struct.pack(_PACKED_HDR_FMT, TYPE_PACKED, len(samples))
    for s in samples:
        out += struct.pack(
            _PACKED_ITEM_FMT,
            int(s.ms_offset),
            float(s.ax), float(s.ay), float(s.az),
            float(s.gx), float(s.gy), float(s.gz),
        )
    return bytes(out)
