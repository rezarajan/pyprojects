"""SSTable catalog implementation.

Provides atomic registry of SSTables per level using JSON manifest.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from collections.abc import Sequence
from pathlib import Path

from ..core.types import SSTableMeta

logger = logging.getLogger(__name__)


class SimpleSSTableCatalog:
    """Registry of SSTables per level with atomic updates.

    Args:
        catalog_path: Path to catalog JSON file
        max_levels: Maximum number of levels

    Invariants:
        - Updates are atomic via write-temp-then-rename
        - Catalog is loaded from disk on init
        - Thread-safe via lock
    """

    def __init__(self, catalog_path: str | Path, max_levels: int = 6):
        self.catalog_path = Path(catalog_path)
        self.max_levels = max_levels
        self._lock = threading.Lock()

        # In-memory state: level -> list of SSTableMeta
        self._levels: dict[int, list[SSTableMeta]] = {i: [] for i in range(max_levels)}

        # Load existing catalog
        self._load()

    def _load(self) -> None:
        """Load catalog from disk."""
        if not self.catalog_path.exists():
            logger.info(f"No existing catalog at {self.catalog_path}, starting fresh")
            return

        try:
            with open(self.catalog_path) as f:
                data = json.load(f)
                for level_str, metas in data.items():
                    level = int(level_str)
                    if 0 <= level < self.max_levels:
                        self._levels[level] = metas
            logger.info(f"Loaded catalog from {self.catalog_path}")
        except Exception as e:
            logger.error(f"Failed to load catalog: {e}")
            raise

    def _save(self) -> None:
        """Save catalog to disk atomically."""
        # Write to temp file
        temp_path = self.catalog_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(self._levels, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        # Atomic rename
        os.replace(temp_path, self.catalog_path)
        logger.debug(f"Saved catalog to {self.catalog_path}")

    def list_level(self, level: int) -> Sequence[SSTableMeta]:
        """Return list of SSTables at the given level."""
        with self._lock:
            if 0 <= level < self.max_levels:
                return list(self._levels[level])  # Return copy
            return []

    def add_sstable(self, level: int, meta: SSTableMeta) -> None:
        """Atomically register a new SSTable in level."""
        with self._lock:
            if not (0 <= level < self.max_levels):
                raise ValueError(f"Invalid level: {level}")

            self._levels[level].append(meta)
            self._save()
            logger.info(f"Added SSTable to level {level}: {meta.get('data_path', 'unknown')}")

    def remove_sstables(self, metas: Sequence[SSTableMeta]) -> None:
        """Atomically remove sstables after compaction."""
        with self._lock:
            # Build set of paths to remove
            paths_to_remove = {meta.get("data_path") for meta in metas}

            # Remove from all levels
            for level in range(self.max_levels):
                self._levels[level] = [
                    m for m in self._levels[level] if m.get("data_path") not in paths_to_remove
                ]

            self._save()
            logger.info(f"Removed {len(metas)} SSTables from catalog")

    def get_all_sstables(self) -> list[tuple[int, SSTableMeta]]:
        """Return all SSTables across all levels."""
        with self._lock:
            result = []
            for level in range(self.max_levels):
                for meta in self._levels[level]:
                    result.append((level, meta))
            return result
