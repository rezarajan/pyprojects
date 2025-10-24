"""SSTable index implementation.

Provides in-memory index for efficient key lookups in SSTables.
"""

from __future__ import annotations

from ..core.types import Key


class SimpleSSTableIndex:
    """In-memory sparse index for SSTable.

    Args:
        index_entries: List of (key, offset) tuples in sorted order
    """

    def __init__(self, index_entries: list[tuple[Key, int]]):
        self._index = sorted(index_entries, key=lambda x: x[0])

    def find_block_offset(self, key: Key) -> int | None:
        """Return best-guess file offset for this key.

        Returns the offset of the largest index key <= search key.
        Returns 0 if key is before all indexed keys.
        Returns None if index is empty.
        """
        if not self._index:
            return 0

        # Binary search
        left, right = 0, len(self._index) - 1
        result_offset = 0

        while left <= right:
            mid = (left + right) // 2
            idx_key, idx_offset = self._index[mid]

            if idx_key <= key:
                result_offset = idx_offset
                left = mid + 1
            else:
                right = mid - 1

        return result_offset

    def load_to_memory(self) -> None:
        """Materialize index structures in memory.

        In this simple implementation, index is already in memory.
        """
        pass  # Already in memory
