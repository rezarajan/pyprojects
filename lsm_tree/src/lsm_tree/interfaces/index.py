"""Protocol definition for SSTable Index."""

from __future__ import annotations
from typing import Protocol
from ..core.types import Key


class SSTableIndex(Protocol):
    """In-memory index for quick key lookups."""
    
    def find_block_offset(self, key: Key) -> int | None:
        """Return best-guess file offset for this key.
        
        Returns None if key is out of SSTable range.
        """
        ...
    
    def load_to_memory(self) -> None:
        """Materialize index structures in memory for faster lookups."""
        ...
