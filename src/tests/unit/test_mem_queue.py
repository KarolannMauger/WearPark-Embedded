from wearpark.mem_queue import MemQueue
from wearpark.protocol import Sample


def test_mem_queue_overflow_keeps_maxlen():
    q = MemQueue(maxlen=2)
    q.push(Sample(0, 0, 0, 0, 0, 0, 0))
    q.push(Sample(1, 1, 1, 1, 1, 1, 1))
    q.push(Sample(2, 2, 2, 2, 2, 2, 2))
    assert len(q) == 2


def test_mem_queue_pop_returns_oldest_after_overflow():
    q = MemQueue(maxlen=2)
    q.push(Sample(0, 0, 0, 0, 0, 0, 0))
    q.push(Sample(1, 1, 1, 1, 1, 1, 1))
    q.push(Sample(2, 2, 2, 2, 2, 2, 2))
    first = q.pop()
    assert first.ms_offset == 1


def test_mem_queue_pop_returns_second_after_overflow():
    q = MemQueue(maxlen=2)
    q.push(Sample(0, 0, 0, 0, 0, 0, 0))
    q.push(Sample(1, 1, 1, 1, 1, 1, 1))
    q.push(Sample(2, 2, 2, 2, 2, 2, 2))
    q.pop()
    second = q.pop()
    assert second.ms_offset == 2


def test_mem_queue_pop_on_empty_returns_none():
    q = MemQueue(maxlen=1)
    assert q.pop() is None