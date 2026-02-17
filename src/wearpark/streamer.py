import time
import threading
from .config import Settings
from .protocol import Sample, encode_auth_frame, encode_single_frame, epoch_ms
from .sensor import ICM20948Sensor
from .tcp_client import TcpClient
from .mem_queue import MemQueue
from .errors import ErrorCode, WearParkError

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
        if not self.s.jwt_token:
            raise WearParkError(ErrorCode.AUTH_TOKEN_MISSING)
        self.client.sendall(encode_auth_frame(self.s.jwt_token, timestamp_ms=epoch_ms()))
        print("Sent auth frame, waiting for response...")
        resp = self.client.recv_until_newline()
        print(resp)
        if not resp.startswith(b"OK"):
            raise WearParkError(ErrorCode.AUTH_FAILED, resp.decode(errors="ignore"))

    # The _producer_forever method runs in a loop, reading data from the sensor at the configured sample rate, calculating the timestamp offset, and pushing the samples into the in-memory queue.
    def _producer_forever(self) -> None:
        period = 1.0 / max(1, self.s.sample_rate_hz)
        while True:
            t0 = time.perf_counter()
            start = self._ensure_session_start() # Get the session start time to calculate the timestamp offset for the sample.
            ax, ay, az, gx, gy, gz = self.sensor.read() # Read the current sensor values for acceleration and gyroscope.
            ms_offset = int(epoch_ms() - start)
            self.queue.push(Sample(ms_offset, ax, ay, az, gx, gy, gz)) # Create a Sample instance with the timestamp offset and sensor readings, and push it into the queue for sending.
            elapsed = time.perf_counter() - t0
            sleep_s = period - elapsed
            if sleep_s > 0:
                time.sleep(sleep_s)

    # The _connect_loop method attempts to connect to the server and perform the handshake. 
    # If it fails, it closes the client and waits for a backoff period before retrying. This loop continues until a successful connection and handshake are made.
    def _connect_loop(self) -> None:
        while True:
            try:
                self.client.connect()
                self._handshake()
                return
            except Exception:
                self.client.close()
                time.sleep(max(0.1, self.s.reconnect_backoff_s))

    # The _sender_forever method runs in a loop, checking if the client is connected. If not, it calls the _connect_loop to establish a connection and perform the handshake.
    def _sender_forever(self) -> None:
        while True:
            if self.client.sock is None:
                self._connect_loop()
            try:
                sample = self.queue.pop()
                if sample is None:
                    time.sleep(0.01)
                    continue
                frame = encode_single_frame(sample) # Encode the sample into a byte frame using the protocol's encoding function.
                self.client.sendall(frame) # Send the encoded frame to the server using the TCP client.
            except Exception:
                self.client.close()
                time.sleep(max(0.1, self.s.reconnect_backoff_s))

    # The run method starts the producer thread that collects sensor data and pushes it into the queue, and then runs the sender loop in the main thread to send the samples to the server.
    def run(self) -> None:
        threading.Thread(target=self._producer_forever, daemon=True).start()
        self._sender_forever()
