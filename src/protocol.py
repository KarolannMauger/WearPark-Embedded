import struct
import time
from dataclasses import dataclass

_ENDIAN = ">"

TYPE_AUTH = 0
TYPE_SINGLE = 1
TYPE_PACKED = 2

# Type 1
_SINGLE_FMT = _ENDIAN + "B I 6f"
_SINGLE_SIZE = struct.calcsize(_SINGLE_FMT)

# Type 2
_PACKED_HDR_FMT = _ENDIAN + "B I"
_PACKED_HDR_SIZE = struct.calcsize(_PACKED_HDR_FMT)

_PACKED_ITEM_FMT = _ENDIAN + "I 6f"
_PACKED_ITEM_SIZE = struct.calcsize(_PACKED_ITEM_FMT)

def epoch_ms() -> int:
    return int(time.time() * 1000)

def encode_auth_frame(jwt_token: str, timestamp_ms: int | None = None) -> bytes:
    if timestamp_ms is None:
        timestamp_ms = epoch_ms()

    jwt_bytes = (jwt_token or "").encode("utf-8") + b"\x00"
    header = struct.pack(_ENDIAN + "B q", TYPE_AUTH, int(timestamp_ms))
    return header + jwt_bytes

def encode_single_frame(ms_offset: int, ax: float, ay: float, az: float, gx: float, gy: float, gz: float) -> bytes:
    return struct.pack(
        _SINGLE_FMT, 
        TYPE_SINGLE, 
        int(ms_offset), float(ax), float(ay), float(az), float(gx), float(gy), float(gz))

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
    if not samples:
        raise ValueError("Packed frame requires at least 1 sample")
    
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