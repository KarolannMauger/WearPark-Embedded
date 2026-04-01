import pytest
import time
from unittest.mock import Mock, patch
import wearpark.streamer as streamer_module
from wearpark.config import Settings
from wearpark.errors import ErrorCode, WearParkError
from wearpark.streamer import Streamer


class FakeSensor:
    def read(self):
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.sent = []
        self.connected = False

    def recv_until_newline(self):
        return self.responses.pop(0)

    def sendall(self, data):
        self.sent.append(data)
    
    def connect(self):
        self.connected = True
    
    def close(self):
        self.connected = False


def test_streamer_ensure_session_start_sets_value(monkeypatch):
    monkeypatch.setattr(streamer_module, "ICM20948Sensor", FakeSensor)
    s = Streamer(Settings())
    value = s._ensure_session_start()
    assert isinstance(value, int)


def test_streamer_ensure_session_start_returns_same_value(monkeypatch):
    monkeypatch.setattr(streamer_module, "ICM20948Sensor", FakeSensor)
    s = Streamer(Settings())
    first = s._ensure_session_start()
    second = s._ensure_session_start()
    assert second == first


def test_streamer_handshake_sends_auth_frame(monkeypatch):
    monkeypatch.setattr(streamer_module, "ICM20948Sensor", FakeSensor)
    s = Streamer(Settings())
    s.client = FakeClient([b"OK\n", b"OK\n"])
    s._handshake()
    assert len(s.client.sent) == 1


def test_streamer_handshake_raises_on_first_bad_response(monkeypatch):
    monkeypatch.setattr(streamer_module, "ICM20948Sensor", FakeSensor)
    s = Streamer(Settings())
    s.client = FakeClient([b"NO\n"])
    with pytest.raises(WearParkError) as exc:
        s._handshake()
    assert exc.value.code == ErrorCode.AUTH_FAILED


def test_streamer_handshake_raises_on_second_bad_response(monkeypatch):
    monkeypatch.setattr(streamer_module, "ICM20948Sensor", FakeSensor)
    s = Streamer(Settings())
    s.client = FakeClient([b"OK\n", b"NO\n"])
    with pytest.raises(WearParkError) as exc:
        s._handshake()
    assert exc.value.code == ErrorCode.AUTH_FAILED


def test_streamer_producer_collects_samples(monkeypatch):
    """Test que le producer collecte les samples."""
    monkeypatch.setattr(streamer_module, "ICM20948Sensor", FakeSensor)
    
    s = Streamer(Settings(sample_rate_hz=100))
    
    call_count = [0]
    original_read = s.sensor.read
    
    def read_with_limit():
        call_count[0] += 1
        if call_count[0] > 3:
            raise KeyboardInterrupt()
        return original_read()
    
    s.sensor.read = read_with_limit
    
    try:
        s._producer_forever()
    except KeyboardInterrupt:
        pass
    
    assert len(s.queue) == 3


def test_streamer_connect_loop_success(monkeypatch):
    """Test que _connect_loop réussit à se connecter."""
    monkeypatch.setattr(streamer_module, "ICM20948Sensor", FakeSensor)
    
    s = Streamer(Settings())
    s.client = FakeClient([b"OK\n", b"OK\n"])
    
    s._connect_loop()
    
    assert s.client.connected
    assert len(s.client.sent) == 1


def test_streamer_connect_loop_retries_on_failure(monkeypatch):
    """Test que _connect_loop réessaye en cas d'échec."""
    monkeypatch.setattr(streamer_module, "ICM20948Sensor", FakeSensor)

    s = Streamer(Settings(reconnect_backoff_s=0.001))

    attempt = [0]

    def fake_connect():
        attempt[0] += 1
        if attempt[0] == 1:
            raise Exception("Connection failed")
        s.client.connected = True

    s.client = FakeClient([b"OK\n", b"OK\n"])
    s.client.connect = fake_connect

    s._connect_loop()

    assert attempt[0] == 2
    assert s.client.connected


def test_streamer_connect_loop_resets_session_start_on_reconnect(monkeypatch):
    monkeypatch.setattr(streamer_module, "ICM20948Sensor", FakeSensor)

    s = Streamer(Settings(reconnect_backoff_s=0.001))
    s.client = FakeClient([b"OK\n", b"OK\n"])

    s.session_start_ms = 1_000_000

    s._connect_loop()

    assert s.session_start_ms is None
