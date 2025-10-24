"""Protocol definition for SSTable Catalog."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..core.types import SSTableMeta


class SSTableCatalog(Protocol):
    """Registry of SSTables per level."""

    def list_level(self, level: int) -> Sequence[SSTableMeta]:
        """Return list of SSTables at the given level."""
        ...

    def add_sstable(self, level: int, meta: SSTableMeta) -> None:
        """Atomically register a new SSTable in level."""
        ...

    def remove_sstables(self, metas: Sequence[SSTableMeta]) -> None:
        """Atomically remove sstables after compaction."""
        ...
