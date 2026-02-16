from collections import deque
from typing import Deque, List
from .protocol import Sample

# This class implements a simple in-memory queue to store samples, with a maximum length to prevent unbounded growth.
class MemQueue:
    # The constructor initializes the queue and sets the maximum length based on the provided argument.
    def __init__(self, maxlen: int):
        self._q: Deque[Sample] = deque()
        self._maxlen = max(1, int(maxlen))

    # The push method adds a sample to the queue and ensures that the queue does not exceed the maximum length by removing the oldest samples if necessary.
    def push(self, s: Sample) -> None:
        self._q.append(s)
        overflow = len(self._q) - self._maxlen
        if overflow > 0:
            for _ in range(overflow):
                self._q.popleft() # Remove the oldest sample to maintain the maximum length of the queue.
    
    # The pop method retrieves and removes the oldest sample from the queue. If the queue is empty, it returns None.
    def pop(self) -> Sample | None:
        if not self._q:
            return None
        return self._q.popleft()
    
    # The __len__ method returns the current number of samples in the queue, allowing the use of len() on an instance of MemQueue to get its size.
    def __len__(self) -> int:
        return len(self._q)