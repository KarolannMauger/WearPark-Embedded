import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# This class holds the configuration settings for the application, which are loaded from environment variables.
@dataclass(frozen=True)
# The @dataclass decorator is used to automatically generate special methods __init__, and frozen=True makes the instance immutable.
class Settings:
    host: str = os.getenv("TCP_HOST", "127.0.0.1")
    port: int = int(os.getenv("TCP_PORT", "9000"))
    sample_rate_hz: int = int(os.getenv("SAMPLE_RATE_HZ", "50"))
    packed_items: int = int(os.getenv("PACKED_ITEMS", "25"))
    send_loop_sleep_s: float = float(os.getenv("SEND_LOOP_SLEEP_S", "0.01"))
    connect_timeout_s: float = float(os.getenv("CONNECT_TIMEOUT_S", "5"))
    io_timeout_s: float = float(os.getenv("IO_TIMEOUT_S", "5"))
    reconnect_backoff_s: float = float(os.getenv("RECONNECT_BACKOFF_S", "2"))
    max_queue_samples: int = int(os.getenv("MAX_QUEUE_SAMPLES", "200000"))
    tls_enabled: bool = os.getenv("TLS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    tls_ca_cert_path: str = os.getenv("TLS_CA_CERT_PATH", "")
    tls_client_cert_path: str = os.getenv("TLS_CLIENT_CERT_PATH", "")
    tls_client_key_path: str = os.getenv("TLS_CLIENT_KEY_PATH", "")
    tls_client_key_password: str = os.getenv("TLS_CLIENT_KEY_PASSWORD", "")
    tls_require_client_cert: bool = os.getenv("TLS_REQUIRE_CLIENT_CERT", "false").strip().lower() in {"1", "true", "yes", "on"}
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "logs/wearpark.log")
    log_max_bytes: int = int(os.getenv("LOG_MAX_BYTES", "10485760"))
    log_backup_count: int = int(os.getenv("LOG_BACKUP_COUNT", "3"))
