"""Protocol definitions for Write-Ahead Log."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from ..core.types import Key, Record, Timestamp, Value


class WALWriter(Protocol):
    """Protocol for writing to WAL."""

    def append(self, key: Key, value: Value | None, ts: Timestamp) -> int:
        """Append a record to WAL.

        Args:
            key: Binary key
            value: Binary value or None for tombstone
            ts: Monotonic timestamp

        Returns:
            WAL sequence number

        Invariants:
            - Must be durable on return if config.wal_flush_every_write is True
            - Records are appended in strictly increasing sequence order
        """
        ...

    def sync(self) -> None:
        """Force data to disk (fsync)."""
        ...

    def close(self) -> None:
        """Close writer and release resources."""
        ...


class WALReader(Protocol):
    """Protocol for reading from WAL."""

    def __iter__(self) -> Iterator[Record]:
        """Iterate records in WAL in append order."""
        ...


class WALManager(Protocol):
    """Protocol for managing WAL lifecycle."""

    def open_writer(self) -> WALWriter:
        """Open a new WAL writer."""
        ...

    def rotate(self) -> None:
        """Rotate WAL (e.g., when file grows too large)."""
        ...
