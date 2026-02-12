from collections import deque
from typing import Deque, List
from .protocol import Sample

class MemQueue:
    def __init__(self, maxlen: int):
        self._q: Deque[Sample] = deque()
        self._maxlen = max(1, int(maxlen))

    def push(self, s: Sample) -> None:
        self._q.append(s)
        overflow = len(self._q) - self._maxlen
        if overflow > 0:
            for _ in range(overflow):
                self._q.popleft()

    def pop(self) -> Sample | None:
        if not self._q:
            return None
        return self._q.popleft()

    def __len__(self) -> int:
        return len(self._q)