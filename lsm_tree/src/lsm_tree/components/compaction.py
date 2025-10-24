"""Compaction implementation.

Merges SSTables across levels, removing duplicates and expired tombstones.
"""

from __future__ import annotations

import heapq
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from ..core.config import LSMConfig
    from ..core.types import Record, SSTableMeta, Timestamp

from .sstable import SimpleSSTableReader, SimpleSSTableWriter

logger = logging.getLogger(__name__)


class SimpleCompactor:
    """Simple compaction strategy for LSM Tree.

    Args:
        config: LSM configuration
        data_dir: Root directory for data files
    """

    def __init__(self, config: LSMConfig, data_dir: str | Path):
        """Initialize compactor with config and data directory."""
        self.config: LSMConfig = config
        self.data_dir: Path = Path(data_dir)
        self._sstable_counter: int = 0

    def compact(
        self, input_tables: Sequence[SSTableMeta], target_level: int
    ) -> Sequence[SSTableMeta]:
        """Perform merge compaction and write output SSTables.

        Args:
            input_tables: SSTables to compact
            target_level: Target level for output

        Returns:
            List of produced SSTable metadata
        """
        if not input_tables:
            return []

        logger.info(f"Compacting {len(input_tables)} SSTables to level {target_level}")

        # Open all input SSTables
        readers = []
        for meta in input_tables:
            reader = SimpleSSTableReader(meta["data_path"], meta["meta_path"])
            readers.append(reader)

        try:
            # Merge all iterators
            merged = self._merge_iterators(readers)

            # Write to output SSTables
            output_metas = self._write_output(merged, target_level)

            logger.info(f"Compaction produced {len(output_metas)} SSTables")
            return output_metas

        finally:
            # Close all readers
            for reader in readers:
                reader.close()

    def _merge_iterators(self, readers: Sequence[SimpleSSTableReader]) -> Iterator[Record]:
        """Merge multiple sorted iterators, keeping newest by timestamp."""
        # Build heap of (key, -ts, value, reader_idx, iterator)
        heap = []
        iterators = [reader.iter_range(None, None) for reader in readers]

        # Initialize heap
        for idx, it in enumerate(iterators):
            try:
                key, value, ts = next(it)
                heapq.heappush(heap, (key, -ts, value, idx, it))
            except StopIteration:  # noqa: PERF203
                pass

        last_key = None
        last_value = None
        last_ts = None

        while heap:
            key, neg_ts, value, idx, it = heapq.heappop(heap)
            ts = -neg_ts

            # Advance iterator
            try:
                next_key, next_value, next_ts = next(it)
                heapq.heappush(heap, (next_key, -next_ts, next_value, idx, it))
            except StopIteration:
                pass

            # Emit if key changed and we have a value to emit
            if last_key is not None and key != last_key:
                # Check if tombstone should be kept
                assert last_ts is not None
                if last_value is not None or self._should_keep_tombstone(last_ts):
                    yield (last_key, last_value, last_ts)
                last_key = None

            # Update last seen (highest timestamp wins)
            if last_key is None or key != last_key:
                last_key = key
                last_value = value
                last_ts = ts
            elif ts > last_ts:
                last_value = value
                last_ts = ts

        # Emit final record
        if (
            last_key is not None
            and (
                last_value is not None
                or (last_ts is not None and self._should_keep_tombstone(last_ts))
            )
        ):
            assert last_ts is not None
            yield (last_key, last_value, last_ts)

    def _should_keep_tombstone(self, ts: Timestamp) -> bool:
        """Determine if tombstone should be retained."""
        current_time = int(time.time() * 1000)  # milliseconds
        age_seconds = (current_time - ts) / 1000
        return age_seconds < self.config.tombstone_retention_seconds

    def _write_output(self, records: Iterator[Record], level: int) -> Sequence[SSTableMeta]:
        """Write merged records to output SSTables."""
        output_metas = []
        current_writer = None
        current_size = 0

        for key, value, ts in records:
            # Start new SSTable if needed
            if current_writer is None or current_size >= self.config.sstable_max_bytes:
                if current_writer is not None:
                    meta = current_writer.finalize()
                    output_metas.append(meta)

                # Create new writer
                self._sstable_counter += 1
                data_path = self.data_dir / f"sst-{level}-{self._sstable_counter}.data"
                meta_path = self.data_dir / f"sst-{level}-{self._sstable_counter}.meta"
                current_writer = SimpleSSTableWriter(
                    data_path, meta_path, self.config.bloom_false_positive_rate
                )
                current_size = 0

            # Add record
            current_writer.add(key, value, ts)
            current_size += len(key) + (len(value) if value else 0) + 24  # Approximate

        # Finalize last writer
        if current_writer is not None:
            meta = current_writer.finalize()
            output_metas.append(meta)

        return output_metas

    def schedule(self, level: int) -> None:
        """Schedule background compaction for a level.

        Not implemented in this simple version - compaction is manual.
        """
        logger.info(f"Background compaction not implemented, level={level}")
