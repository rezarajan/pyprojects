"""In-memory sorted memtable implementation.

Uses sortedcontainers.SortedDict for efficient sorted operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sortedcontainers import SortedDict

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from ..core.types import Key, Record, Timestamp, Value


class SimpleMemtable:
    """In-memory sorted structure holding recent writes.

    Maintains key-value pairs with timestamps in sorted order.
    Supports efficient range queries and size tracking.

    Invariants:
        - Keys are always maintained in sorted order
        - Most recent value per key (by timestamp) is accessible
        - Size includes approximate overhead of data structures
    """

    def __init__(self):
        """Initialize empty memtable."""
        self._data: SortedDict = SortedDict()
        self._size_bytes: int = 0

    def put(self, key: Key, value: Value, ts: Timestamp) -> None:
        """Insert or update key with value and timestamp."""
        # Track size delta
        if key in self._data:
            old_value, _old_ts = self._data[key]
            old_size = len(key) + (len(old_value) if old_value else 0) + 8
            self._size_bytes -= old_size

        self._data[key] = (value, ts)
        new_size = len(key) + len(value) + 8  # key + value + timestamp
        self._size_bytes += new_size

    def delete(self, key: Key, ts: Timestamp) -> None:
        """Mark key as tombstone with timestamp."""
        # Track size delta
        if key in self._data:
            old_value, _old_ts = self._data[key]
            old_size = len(key) + (len(old_value) if old_value else 0) + 8
            self._size_bytes -= old_size

        self._data[key] = (None, ts)
        new_size = len(key) + 8  # key + timestamp (no value)
        self._size_bytes += new_size

    def get(self, key: Key) -> tuple[Value | None, Timestamp] | None:
        """Return (value_or_none, timestamp) if key found; else None.

        If value_or_none is None, it is a tombstone.
        """
        return self._data.get(key)

    def iter_range(self, start: Key | None, end: Key | None) -> Iterator[Record]:
        """Iterate records in key order between start and end.

        Args:
            start: Start key (inclusive), or None for beginning
            end: End key (exclusive), or None for end
        """
        if start is None and end is None:
            # All keys
            for key, (value, ts) in self._data.items():
                yield (key, value, ts)
        elif start is None:
            # Up to end
            for key, (value, ts) in self._data.items():
                if key >= end:
                    break
                yield (key, value, ts)
        elif end is None:
            # From start onward
            for key, (value, ts) in self._data.items():
                if key >= start:
                    yield (key, value, ts)
        else:
            # Range
            for key, (value, ts) in self._data.items():
                if key < start:
                    continue
                if key >= end:
                    break
                yield (key, value, ts)

    def size_bytes(self) -> int:
        """Return approximate memory usage in bytes."""
        # Add overhead for SortedDict structure (rough estimate)
        overhead = len(self._data) * 32  # approximate per-entry overhead
        return self._size_bytes + overhead

    def clear(self) -> None:
        """Clear all entries (used after flush)."""
        self._data.clear()
        self._size_bytes = 0

    def items(self) -> Iterable[Record]:
        """Return iterator of all records in sorted key order."""
        for key, (value, ts) in self._data.items():
            yield (key, value, ts)
