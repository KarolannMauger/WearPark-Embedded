import socket
from typing import Optional
from .config import Settings

class TcpClient:
    def __init__(self, settings: Settings):
        self.s = settings
        self.sock: Optional[socket.socket] = None

    def connect(self) -> None:
        sock = socket.create_connection((self.s.host, self.s.port), timeout=self.s.connect_timeout_s)
        sock.settimeout(self.s.io_timeout_s)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except OSError:
            pass
        self.sock = sock

    def close(self) -> None:
        try:
            if self.sock:
                self.sock.close()
        finally:
            self.sock = None

    def sendall(self, data: bytes) -> None:
        if not self.sock:
            raise RuntimeError("Socket not connected")
        self.sock.sendall(data)

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
