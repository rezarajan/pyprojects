"""Protocol definition for Memtable."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from ..core.types import Key, Record, Timestamp, Value


class Memtable(Protocol):
    """In-memory sorted structure holding recent writes."""

    def put(self, key: Key, value: Value, ts: Timestamp) -> None:
        """Insert or update key with value and timestamp."""
        ...

    def delete(self, key: Key, ts: Timestamp) -> None:
        """Mark key as tombstone with timestamp."""
        ...

    def get(self, key: Key) -> tuple[Value | None, Timestamp] | None:
        """Return (value_or_none, timestamp) if key found; else None.

        If value_or_none is None, it is a tombstone.
        """
        ...

    def iter_range(self, start: Key | None, end: Key | None) -> Iterator[Record]:
        """Iterate records in key order between start and end."""
        ...

    def size_bytes(self) -> int:
        """Return approximate memory usage in bytes."""
        ...

    def clear(self) -> None:
        """Clear all entries (used after flush)."""
        ...

    def items(self) -> Iterable[Record]:
        """Return iterator of all records in sorted key order."""
        ...
