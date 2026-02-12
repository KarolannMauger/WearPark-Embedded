import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("TCP_HOST", "127.0.0.1")
    port: int = int(os.getenv("TCP_PORT", 9000))

    jwt_token: str = os.getenv("JWT_TOKEN", "")

    sample_rate_hz: int = int(os.getenv("SAMPLE_RATE_HZ", "50"))

    packed_mode: bool = os.getenv("PACKED_MODE", "true").lower() in ("1", "true", "yes")
    packed_items: int = int(os.getenv("PACKED_ITEMS", "10"))

    connect_timeout_s: float = float(os.getenv("CONNECT_TIMEOUT_S", "5"))
    io_timeout_s: float = float(os.getenv("IO_TIMEOUT_S", "5"))