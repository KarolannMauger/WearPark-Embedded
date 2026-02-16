import socket
from typing import Optional
from .config import Settings

# The TcpClient class is a simple wrapper around a TCP socket that provides methods for connecting to a server, sending data, and receiving data until a newline character is encountered. 
# It also handles socket timeouts and ensures that the socket is properly closed when needed.
class TcpClient:
    # The constructor initializes the TcpClient with the provided settings, creates an instance of the sensor, TCP client, and in-memory queue, and sets up a variable to track the session start time.
    def __init__(self, settings: Settings):
        self.s = settings
        self.sock: Optional[socket.socket] = None

    # The connect method establishes a TCP connection to the server using the host and port specified in the settings. 
    # It also sets the socket timeouts for connecting and I/O operations, and attempts to enable TCP keepalive if supported by the platform.
    def connect(self) -> None:
        sock = socket.create_connection((self.s.host, self.s.port), timeout=self.s.connect_timeout_s)
        sock.settimeout(self.s.io_timeout_s)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except OSError:
            pass
        self.sock = sock
    
    # The close method closes the socket if it is currently open and sets the socket attribute to None to indicate that there is no active connection.
    def close(self) -> None:
        try:
            if self.sock:
                self.sock.close()
        finally:
            self.sock = None

    # The sendall method sends the provided byte data to the server using the socket's sendall method. If the socket is not connected, it raises a RuntimeError.
    def sendall(self, data: bytes) -> None:
        if not self.sock:
            raise RuntimeError("Socket not connected")
        self.sock.sendall(data)

    # The recv_until_newline method reads data from the socket one byte at a time until it encounters a newline character or reaches the maximum number of bytes specified by max_bytes.
    def recv_until_newline(self, max_bytes: int = 4096) -> bytes:
        if not self.sock:
            raise RuntimeError("Socket not connected")
        buf = bytearray()
        while len(buf) < max_bytes:
            b = self.sock.recv(1)
            if not b:
                break
            buf += b
            if b == b"\n":
                break
        return bytes(buf)
