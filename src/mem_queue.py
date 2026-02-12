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

    def peek_many(self, n: int) -> list[Sample]:
        n = max(0, int(n))
        if n <= 0:
            return []
        out: List[Sample] = []
        it = iter(self._q)
        for _ in range(min(n, len(self._q))):
            out.append(next(it))
        return out

    def drop_many(self, n: int) -> None:
        n = max(0, int(n))
        for _ in range(min(n, len(self._q))):
            self._q.popleft()

    def __len__(self) -> int:
        return len(self._q)
