import socket
import ssl
import time
from pathlib import Path
from typing import Optional
from .config import Settings
from .errors import ErrorCode, WearParkError

# The TcpClient class is a simple wrapper around a TCP socket that provides methods for connecting to a server, sending data, and receiving data until a newline character is encountered. 
# It also handles socket timeouts and ensures that the socket is properly closed when needed.
class TcpClient:
    # The constructor initializes the TcpClient with the provided settings, creates an instance of the sensor, TCP client, and in-memory queue, and sets up a variable to track the session start time.
    def __init__(self, settings: Settings):
        self.s = settings
        self.sock: Optional[socket.socket] = None
    
    def _validate_file(self, path: str, label: str) -> None:
        if not path:
            raise WearParkError(ErrorCode.TLS_CONFIG_ERROR, f"{label} is required")
        print(path)
        if not Path(path).is_file():
            raise WearParkError(ErrorCode.TLS_CONFIG_ERROR, f"{label} not found: {path}")
    
    def _build_ssl_context(self) -> ssl.SSLContext:
        print("[TLS] Building SSL context for mTLS...")
        cafile = self.s.tls_ca_cert_path or None
        if cafile:
            self._validate_file(cafile, "TLS_CA_CERT_PATH")
            print(f"[TLS] CA certificate: {cafile}")
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=cafile)
        context.check_hostname = False
        print("[TLS] Hostname verification disabled (mTLS mode)")

        if self.s.tls_require_client_cert:
            self._validate_file(self.s.tls_client_cert_path, "TLS_CLIENT_CERT_PATH")
            self._validate_file(self.s.tls_client_key_path, "TLS_CLIENT_KEY_PATH")

        if self.s.tls_client_cert_path or self.s.tls_client_key_path:
            if not self.s.tls_client_cert_path or not self.s.tls_client_key_path:
                raise WearParkError(ErrorCode.TLS_CONFIG_ERROR, "TLS client certificate and key must both be provided")
            self._validate_file(self.s.tls_client_cert_path, "TLS_CLIENT_CERT_PATH")
            self._validate_file(self.s.tls_client_key_path, "TLS_CLIENT_KEY_PATH")
            print(f"[TLS] Client certificate: {self.s.tls_client_cert_path}")
            print(f"[TLS] Client key: {self.s.tls_client_key_path}")
            context.load_cert_chain(certfile=self.s.tls_client_cert_path, 
                                    keyfile=self.s.tls_client_key_path, 
                                    password=(self.s.tls_client_key_password or None),
                                    )
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        print("[TLS] Minimum TLS version: TLSv1.2")
        return context

    # The connect method establishes a TCP connection to the server using the host and port specified in the settings. 
    # It also sets the socket timeouts for connecting and I/O operations, and attempts to enable TCP keepalive if supported by the platform.
    def connect(self) -> None:
        try:
            print(f"[TCP] Connecting to {self.s.host}:{self.s.port}...")
            sock = socket.create_connection((self.s.host, self.s.port), timeout=self.s.connect_timeout_s)
            sock.settimeout(self.s.io_timeout_s)
            print(f"[TCP] Connected! Setting timeout to {self.s.io_timeout_s}s")
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                print("[TCP] TCP keepalive enabled")
            except OSError:
                print("[TCP] TCP keepalive not supported on this platform")

            if self.s.tls_enabled:
                print("[TLS] TLS enabled, starting handshake...")
                context = self._build_ssl_context()
                sock = context.wrap_socket(sock, server_hostname=None)
                cipher = sock.cipher()
                print(f"[TLS] Handshake successful! Cipher: {cipher[0]} (TLS {cipher[1]})")
                print(f"[TLS] Peer certificate: {sock.getpeercert()}")

            self.sock = sock
            print("[TCP] Connection established successfully")
        except WearParkError:
            raise
        except ssl.SSLError as e:
            print(f"[TLS] SSL handshake failed: {e}")
            raise WearParkError(ErrorCode.TLS_HANDSHAKE_FAILED, str(e)) from e
        except Exception as e:
            print(f"[TCP] Connection failed: {e}")
            raise WearParkError(ErrorCode.ECONNREFUSED, str(e)) from e
    
    # The close method closes the socket if it is currently open and sets the socket attribute to None to indicate that there is no active connection.
    def close(self) -> None:
        try:
            if self.sock:
                print("[TCP] Closing connection...")
                self.sock.close()
                print("[TCP] Connection closed")
        finally:
            self.sock = None

    # The sendall method sends the provided byte data to the server using the socket's sendall method. If the socket is not connected, it raises a RuntimeError.
    def sendall(self, data: bytes) -> None:
        if not self.sock:
            raise WearParkError(ErrorCode.ENOTCONN)
        try:
            self.sock.sendall(data)
            print(f"[TCP] Sent {len(data)} bytes")
        except socket.timeout:
            print("[TCP] Send timeout - closing connection")
            self.close()
            raise WearParkError(ErrorCode.ENOTCONN, "Backend timeout on send") from None
        except Exception as e:
            print(f"[TCP] Send error: {e} - closing connection")
            self.close()
            raise WearParkError(ErrorCode.ENOTCONN, str(e)) from e

    # The recv_until_newline method reads data from the socket one byte at a time until it encounters a newline character or reaches the maximum number of bytes specified by max_bytes.
    def recv_until_newline(self, max_bytes: int = 4096) -> bytes:
        if not self.sock:
            raise WearParkError(ErrorCode.ENOTCONN)
        buf = bytearray()
        start_time = time.time()
        print(f"[TCP] Receiving data (timeout: {self.s.io_timeout_s}s)...")
        try:
            while len(buf) < max_bytes:
                # Check overall timeout
                if time.time() - start_time > self.s.io_timeout_s:
                    print(f"[TCP] Receive timeout after {time.time() - start_time:.2f}s")
                    self.close()
                    raise WearParkError(ErrorCode.ECONNRESET, "No response from backend (timeout)")
                
                b = self.sock.recv(1)
                if not b:
                    print("[TCP] Connection closed by backend")
                    self.close()
                    raise WearParkError(ErrorCode.ECONNRESET, "Connection closed by backend")
                buf += b
                if b == b"\n":
                    break
            result = bytes(buf)
            print(f"[TCP] Received {len(result)} bytes: {result.decode('utf-8', errors='replace').strip()}")
            return result
        except socket.timeout:
            self.close()
            raise WearParkError(ErrorCode.ECONNRESET, "No response from backend (timeout)") from None
        except WearParkError:
            raise
        except Exception as e:
            self.close()
            raise WearParkError(ErrorCode.ECONNRESET, str(e)) from e
