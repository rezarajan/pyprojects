"""Protocol definitions for SSTable."""

from __future__ import annotations
from typing import Protocol, Iterator
from ..core.types import Key, Value, Timestamp, SSTableMeta


class SSTableReader(Protocol):
    """Protocol for reading from immutable SSTables."""
    
    meta: SSTableMeta
    
    def may_contain(self, key: Key) -> bool:
        """Use Bloom filter to test potential presence."""
        ...
    
    def get(self, key: Key) -> tuple[Value | None, Timestamp] | None:
        """Return (value_or_none, ts) or None if key definitely not present."""
        ...
    
    def iter_range(self, start: Key | None, end: Key | None) -> Iterator[tuple[Key, Value | None, Timestamp]]:
        """Iterate key-ordered records from start to end."""
        ...
    
    def close(self) -> None:
        """Release file descriptors / mmaps."""
        ...


class SSTableWriter(Protocol):
    """Protocol for writing to SSTables."""
    
    def add(self, key: Key, value: Value | None, ts: Timestamp) -> None:
        """Append record to the writer (must be added in sorted order)."""
        ...
    
    def finalize(self) -> SSTableMeta:
        """Flush and write index/filter/footer. Return metadata for registry."""
        ...
