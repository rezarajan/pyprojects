"""Protocol definition for LSM Store."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from ..core.types import Key, Timestamp, Value


class LSMStore(Protocol):
    """Public API for LSM Tree storage engine."""

    def put(self, key: Key, value: Value) -> None:
        """Client-facing put; generates timestamp internally and ensures durability."""
        ...

    def delete(self, key: Key) -> None:
        """Client-facing delete; produce tombstone."""
        ...

    def get(self, key: Key) -> Value | None:
        """Return latest value for key or None if not present."""
        ...

    def get_with_meta(self, key: Key) -> tuple[Value | None, Timestamp] | None:
        """Return (value_or_none, timestamp)."""
        ...

    def range(self, start: Key | None, end: Key | None) -> Iterator[tuple[Key, Value | None]]:
        """Ordered iterator over keys in the range."""
        ...

    def compact_level(self, level: int) -> None:
        """Trigger synchronous compaction for a level (administrative)."""
        ...

    def flush_memtable(self) -> None:
        """Force memtable flush to SSTable."""
        ...
