"""Append-only per-job event log that live subscribers can wait on."""

from __future__ import annotations

import asyncio
import contextlib

from vectron.domain.jobs import JobEvent


class EventLog:
    """Events are addressed by ``seq`` (their index), so clients can resume from any point."""

    def __init__(self) -> None:
        self._events: list[JobEvent] = []
        self._changed = asyncio.Event()
        self.closed = False

    def __len__(self) -> int:
        return len(self._events)

    def append(self, event: JobEvent) -> None:
        self._events.append(event)
        self._notify()

    def close(self) -> None:
        """Mark the log complete; waiters wake up and see no further events will come."""
        self.closed = True
        self._notify()

    def since(self, seq: int) -> list[JobEvent]:
        """Events with ``event.seq > seq``."""
        return self._events[max(seq + 1, 0) :]

    async def wait(self, after_seq: int, timeout: float) -> list[JobEvent]:
        """Return events after ``after_seq``, waiting up to ``timeout`` seconds for new ones."""
        if len(self._events) - 1 <= after_seq and not self.closed:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._changed.wait(), timeout)
        return self.since(after_seq)

    def _notify(self) -> None:
        # Wake everyone waiting on the current event object, then arm a fresh one.
        self._changed.set()
        self._changed = asyncio.Event()
