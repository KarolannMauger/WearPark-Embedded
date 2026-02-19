from enum import IntEnum

# This module defines error codes and a custom exception class for the WearPark application.
class ErrorCode(IntEnum):
    OK = 1000
    CONFIG_ERROR = 1400
    AUTH_TOKEN_MISSING = 1401
    AUTH_FAILED = 1402
    TLS_CONFIG_ERROR = 1403
    TLS_HANDSHAKE_FAILED = 1404
    SENSOR_INIT_FAILED = 2000
    SENSOR_READ_FAILED = 2001
    # OS/Socket error codes (Linux errno)
    EAGAIN = 11
    EWOULDBLOCK = 11
    EACCES = 13
    EINVAL = 22
    EADDRINUSE = 98
    EADDRNOTAVAIL = 99
    ENETDOWN = 100
    ENETUNREACH = 101
    ECONNRESET = 104
    ENOBUFS = 105
    ENOTCONN = 107
    ETIMEDOUT = 110
    ECONNREFUSED = 111
    EHOSTUNREACH = 113

# The ERROR_MESSAGES dictionary maps each error code to a human-readable error message that can be used when raising exceptions or logging errors.
ERROR_MESSAGES = {
    ErrorCode.OK: "OK",
    ErrorCode.CONFIG_ERROR: "Invalid or missing configuration",
    ErrorCode.AUTH_TOKEN_MISSING: "JWT token missing",
    ErrorCode.AUTH_FAILED: "Authentication failed",
    ErrorCode.TLS_CONFIG_ERROR: "TLS configuration error",
    ErrorCode.TLS_HANDSHAKE_FAILED: "TLS handshake failed",
    ErrorCode.SENSOR_INIT_FAILED: "Sensor initialization failed",
    ErrorCode.SENSOR_READ_FAILED: "Sensor read failed",
    ErrorCode.EAGAIN: "Resource temporarily unavailable",
    ErrorCode.EACCES: "Permission denied",
    ErrorCode.EINVAL: "Invalid argument",
    ErrorCode.EADDRINUSE: "Address already in use",
    ErrorCode.EADDRNOTAVAIL: "Address not available",
    ErrorCode.ENETDOWN: "Network is down",
    ErrorCode.ENETUNREACH: "Network unreachable",
    ErrorCode.ECONNRESET: "Connection reset by peer",
    ErrorCode.ENOBUFS: "No buffer space available",
    ErrorCode.ENOTCONN: "Socket not connected",
    ErrorCode.ETIMEDOUT: "Connection timed out",
    ErrorCode.ECONNREFUSED: "Connection refused",
    ErrorCode.EHOSTUNREACH: "No route to host",
}

# The WearParkError class is a custom exception that extends RuntimeError and includes an error code from the ErrorCode enum. 
# It also allows for an optional detail message that can provide additional context about the error. 
# When the exception is raised, it constructs a message based on the error code and detail.
class WearParkError(RuntimeError):
    def __init__(self, code: ErrorCode, detail: str | None = None):
        self.code = code
        msg = ERROR_MESSAGES.get(code, "Unknown error")
        if detail:
            msg = f"{msg}: {detail}"
        super().__init__(msg)
