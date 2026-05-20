import time
import threading
import logging
from .config import Settings
from .protocol import Sample, encode_auth_frame, encode_single_frame, epoch_ms
from .sensor import ICM20948Sensor
from .tcp_client import TcpClient
from .mem_queue import MemQueue
from .errors import ErrorCode, WearParkError

logger = logging.getLogger(__name__)

# The Streamer class is responsible for managing the data collection from the sensor, queuing the samples, and sending them to a server over TCP. 
# It handles authentication, reconnection logic, and ensures that samples are sent at the configured sample rate.
class Streamer:
    # The constructor initializes the Streamer with the provided settings, creates an instance of the sensor, TCP client, and in-memory queue, and sets up a variable to track the session start time.
    def __init__(self, settings: Settings):
        self.s = settings
        self.sensor = ICM20948Sensor()
        self.client = TcpClient(settings)
        self.queue = MemQueue(settings.max_queue_samples)
        self.session_start_ms: int | None = None

    # The _ensure_session_start method checks if the session start time has been set. If not, it sets it to the current time in milliseconds. 
    # It returns the session start time, which is used to calculate the timestamp offsets for the samples.
    def _ensure_session_start(self) -> int:
        if self.session_start_ms is None:
            self.session_start_ms = epoch_ms()
        return self.session_start_ms

    # The _handshake method performs the authentication handshake with the server by sending an authentication frame containing the JWT token and waiting for a response.
    def _handshake(self) -> None:
        # if not self.s.jwt_token:
        #     raise WearParkError(ErrorCode.AUTH_TOKEN_MISSING)
        print("[TIME] Waiting for server response...")
        resp = self.client.recv_until_newline()
        if not resp.startswith(b"OK"):
            print(f"[TIME] Authentication failed: {resp.decode(errors='ignore')}")
            raise WearParkError(ErrorCode.AUTH_FAILED, resp.decode(errors="ignore"))
        
        print("[TIME] Sending timestamp frame...")
        time_frame = encode_auth_frame(timestamp_ms=epoch_ms())
        # print(f"[TIME] Timestamp frame size: {len(time_frame)} bytes")
        self.client.sendall(time_frame)

        print("[TIME] Waiting for server response...")
        resp = self.client.recv_until_newline()
        if not resp.startswith(b"OK"):
            print(f"[TIME] Authentication failed: {resp.decode(errors='ignore')}")
            raise WearParkError(ErrorCode.AUTH_FAILED, resp.decode(errors="ignore"))
        # elif not resp.startswith(b"no_user") or not resp.startswith(b"no_device"):
        #     print(f"[TIME] Unexpected authentication response: {resp.decode(errors='ignore')}")
        #     raise WearParkError(ErrorCode.AUTH_FAILED, f"Unexpected authentication response: {resp.decode(errors='ignore')}")
        
        # print("[TIME] Authentication successful!")

    # The _producer_forever method runs in a loop, reading data from the sensor at the configured sample rate, calculating the timestamp offset, and pushing the samples into the in-memory queue.
    def _producer_forever(self) -> None:
        period = 1.0 / max(1, self.s.sample_rate_hz)
        print(f"[PRODUCER] Starting sensor data collection at {self.s.sample_rate_hz} Hz")
        # sample_count = 0
        while True:
            t0 = time.perf_counter()
            start = self._ensure_session_start()
            ax, ay, az, gx, gy, gz = self.sensor.read()
            ms_offset = int(epoch_ms() - start)
            self.queue.push(Sample(ms_offset, ax, ay, az, gx, gy, gz))
            # sample_count += 1
            # if sample_count % 100 == 0:
            #     print(f"[PRODUCER] Collected {sample_count} samples, queue size: {len(self.queue)}")
            elapsed = time.perf_counter() - t0
            sleep_s = period - elapsed
            if sleep_s > 0:
                time.sleep(sleep_s)

    # The _connect_loop method attempts to connect to the server and perform the handshake. 
    # If it fails, it closes the client and waits for a backoff period before retrying. This loop continues until a successful connection and handshake are made.
    def _connect_loop(self) -> None:
        attempt = 0
        while True:
            try:
                attempt += 1
                print(f"[CONNECTION] Connection attempt #{attempt}")
                self.session_start_ms = None
                self.client.connect()
                self._handshake()
                print("[CONNECTION] Successfully connected and authenticated!")
                return
            except Exception as e:
                # print(f"[CONNECTION] Failed: {e}")
                self.client.close()
                logger.error("Connection attempt failed: %s", e)
                print(f"[CONNECTION] Retrying in {self.s.reconnect_backoff_s}s...")
                time.sleep(max(0.1, self.s.reconnect_backoff_s))

    # The _sender_forever method runs in a loop, checking if the client is connected. If not, it calls the _connect_loop to establish a connection and perform the handshake.
    def _sender_forever(self) -> None:
        # sent_count = 0
        # print("[SENDER] Starting data transmission loop")
        while True:
            if self.client.sock is None:
                self._connect_loop()
            try:
                frames = bytearray()
                while len(self.queue) > 0:
                    sample = self.queue.pop()
                    frames += encode_single_frame(sample)
                if frames:
                    self.client.sendall(frames) # Send the encoded frames to the server using the TCP client.
                    # sent_count += 1
                    # if sent_count % 50 == 0:
                    #     print(f"[SENDER] Sent {sent_count} samples, queue remaining: {len(self.queue)}")
                else:
                    time.sleep(self.s.send_loop_sleep_s)
            except Exception as e:
                # print(f"[SENDER] Error: {e}")
                self.client.close()
                logger.error("Sender error: %s", e)
                print(f"[SENDER] Reconnecting in {self.s.reconnect_backoff_s}s...")
                time.sleep(max(0.1, self.s.reconnect_backoff_s))

    # The run method starts the producer thread that collects sensor data and pushes it into the queue, and then runs the sender loop in the main thread to send the samples to the server.
    def run(self) -> None:
        print("="*60)
        print("WearPark Embedded Data Streamer")
        print("="*60)
        print(f"Server: {self.s.host}:{self.s.port}")
        print(f"TLS: {'Enabled (mTLS)' if self.s.tls_enabled else 'Disabled'}")
        print(f"Sample Rate: {self.s.sample_rate_hz} Hz")
        print(f"Max Queue Size: {self.s.max_queue_samples} samples")
        print("="*60)
        threading.Thread(target=self._producer_forever, daemon=True).start()
        self._sender_forever()
