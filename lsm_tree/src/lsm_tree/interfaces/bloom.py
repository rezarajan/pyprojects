"""Protocol definition for Bloom Filter."""

from __future__ import annotations

from typing import Protocol

from ..core.types import Key


class BloomFilter(Protocol):
    """Probabilistic set membership test."""

    def add(self, key: Key) -> None:
        """Add key to the filter."""
        ...

    def __contains__(self, key: Key) -> bool:
        """Return True if key may be present; False if definitely absent."""
        ...

    def serialize(self) -> bytes:
        """Serialize filter to bytes."""
        ...

    @classmethod
    def deserialize(cls, data: bytes) -> BloomFilter:
        """Deserialize filter from bytes."""
        ...
