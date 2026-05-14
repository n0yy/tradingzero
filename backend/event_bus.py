from __future__ import annotations

from queue import Empty, Full, Queue
from threading import Lock


class TrainingEventBus:
    def __init__(self) -> None:
        self._subscribers: set[Queue] = set()
        self._lock = Lock()

    def subscribe(self) -> Queue:
        queue: Queue = Queue(maxsize=100)
        with self._lock:
            self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: Queue) -> None:
        with self._lock:
            self._subscribers.discard(queue)

    def publish(self, event: dict) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            if queue.full():
                try:
                    queue.get_nowait()
                except Empty:
                    pass
            try:
                queue.put_nowait(event)
            except Full:
                pass
