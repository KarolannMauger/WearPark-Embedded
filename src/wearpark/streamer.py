import time
import threading
from .config import Settings
from .protocol import Sample, encode_auth_frame, encode_single_frame, epoch_ms
from .sensor import ICM20948Sensor
from .tcp_client import TcpClient
from .mem_queue import MemQueue

class Streamer:
    def __init__(self, settings: Settings):
        self.s = settings
        self.sensor = ICM20948Sensor()
        self.client = TcpClient(settings)
        self.queue = MemQueue(settings.max_queue_samples)
        self.session_start_ms: int | None = None

    def _ensure_session_start(self) -> int:
        if self.session_start_ms is None:
            self.session_start_ms = epoch_ms()
        return self.session_start_ms

    def _handshake(self) -> None:
        if not self.s.jwt_token:
            raise RuntimeError("JWT_TOKEN missing")
        self.client.sendall(encode_auth_frame(self.s.jwt_token, timestamp_ms=epoch_ms()))
        print("Sent auth frame, waiting for response...")
        resp = self.client.recv_until_newline()
        print(resp)
        if not resp.startswith(b"OK"):
            raise RuntimeError(resp.decode(errors="ignore"))

    def _producer_forever(self) -> None:
        period = 1.0 / max(1, self.s.sample_rate_hz)
        while True:
            t0 = time.perf_counter()
            start = self._ensure_session_start()
            ax, ay, az, gx, gy, gz = self.sensor.read()
            ms_offset = int(epoch_ms() - start)
            self.queue.push(Sample(ms_offset, ax, ay, az, gx, gy, gz))
            elapsed = time.perf_counter() - t0
            sleep_s = period - elapsed
            if sleep_s > 0:
                time.sleep(sleep_s)

    def _connect_loop(self) -> None:
        while True:
            try:
                self.client.connect()
                self._handshake()
                return
            except Exception:
                self.client.close()
                time.sleep(max(0.1, self.s.reconnect_backoff_s))

    def _sender_forever(self) -> None:
        while True:
            if self.client.sock is None:
                self._connect_loop()
            try:
                
                sample = self.queue.pop()
                if sample is None:
                    time.sleep(0.01)
                    continue
                frame = encode_single_frame(sample)
                self.client.sendall(frame)
            except Exception:
                self.client.close()
                time.sleep(max(0.1, self.s.reconnect_backoff_s))

    def run(self) -> None:
        threading.Thread(target=self._producer_forever, daemon=True).start()
        self._sender_forever()