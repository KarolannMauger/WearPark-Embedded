import struct
import time
from dataclasses import dataclass

_ENDIAN = "<"

TYPE_AUTH = 0
TYPE_SINGLE = 1

_AUTH_FMT = _ENDIAN + "B q"
_SINGLE_FMT = _ENDIAN + "B I 6f"

# The epoch_ms function returns the current time in milliseconds since the Unix epoch.
def epoch_ms() -> int:
    return int(time.time() * 1000)

# The encode_auth_frame function takes a JWT token and an optional timestamp in milliseconds, and constructs a byte frame for authentication. 
# If the timestamp is not provided, it uses the current time. The frame consists of a header with the type and timestamp, followed by the JWT token as a null-terminated string.
def encode_auth_frame(timestamp_ms: int | None = None) -> bytes:
    if timestamp_ms is None:
        timestamp_ms = epoch_ms()
    header = struct.pack(_AUTH_FMT, TYPE_AUTH, int(timestamp_ms)) # Pack the type and timestamp into a binary format using struct.
    return header

# The Sample class is a data structure that represents a single sample of sensor data, including a timestamp offset and the values of accelerometer and gyroscope readings. 
@dataclass(frozen=True)
# The @dataclass decorator is used to automatically generate initialization, and frozen=True makes instances of this class immutable.
class Sample:
    ms_offset: int
    ax: float
    ay: float
    az: float
    gx: float
    gy: float
    gz: float

# The encode_single_frame function takes a Sample instance and encodes it into a byte frame using struct. 
# The frame includes a header with the type and timestamp offset, followed by the accelerometer and gyroscope values as floats.
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