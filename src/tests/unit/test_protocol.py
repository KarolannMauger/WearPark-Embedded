import struct
from wearpark import protocol


def test_encode_auth_frame_sets_type():
    ts = 123456789
    data = protocol.encode_auth_frame(timestamp_ms=ts)
    msg_type, timestamp = struct.unpack(protocol._AUTH_FMT, data)
    assert msg_type == protocol.TYPE_AUTH


def test_encode_auth_frame_sets_timestamp():
    ts = 123456789
    data = protocol.encode_auth_frame(timestamp_ms=ts)
    msg_type, timestamp = struct.unpack(protocol._AUTH_FMT, data)
    assert timestamp == ts


def test_encode_single_frame_sets_type():
    sample = protocol.Sample(10, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
    data = protocol.encode_single_frame(sample)
    unpacked = struct.unpack(protocol._SINGLE_FMT, data)
    assert unpacked[0] == protocol.TYPE_SINGLE


def test_encode_single_frame_sets_ms_offset():
    sample = protocol.Sample(10, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
    data = protocol.encode_single_frame(sample)
    unpacked = struct.unpack(protocol._SINGLE_FMT, data)
    assert unpacked[1] == 10


def test_encode_single_frame_sets_values():
    sample = protocol.Sample(10, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
    data = protocol.encode_single_frame(sample)
    unpacked = struct.unpack(protocol._SINGLE_FMT, data)
    assert unpacked[2:] == (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)


def test_epoch_ms_returns_int():
    value = protocol.epoch_ms()
    assert isinstance(value, int)