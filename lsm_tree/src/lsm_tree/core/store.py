"""LSM Store implementation - main public API.

Orchestrates WAL, Memtable, SSTables, and Compaction.
"""

from __future__ import annotations
import os
import time
import logging
import threading
from pathlib import Path
from typing import Iterator
from .types import Key, Value, Timestamp, Record
from .config import LSMConfig
from .errors import LSMError, RecoveryError
from ..components.wal import SimpleWAL
from ..components.memtable import SimpleMemtable
from ..components.sstable import SimpleSSTableWriter, SimpleSSTableReader
from ..components.catalog import SimpleSSTableCatalog
from ..components.compaction import SimpleCompactor

logger = logging.getLogger(__name__)


class SimpleLSMStore:
    """LSM Tree storage engine with durability and crash recovery.
    
    Args:
        config: LSM configuration
    
    Public API:
        - put(key, value): Insert or update
        - delete(key): Mark for deletion
        - get(key): Retrieve latest value
        - range(start, end): Range scan
        - flush_memtable(): Force flush to disk
        - compact_level(level): Manual compaction
    
    Invariants:
        - All writes go to WAL before memtable
        - Reads check memtable first, then SSTables by recency
        - Timestamps are monotonically increasing
    """
    
    def __init__(self, config: LSMConfig):
        self.config = config
        self.data_dir = Path(config.data_dir)
        self._lock = threading.Lock()
        self._timestamp_counter = int(time.time() * 1000)  # milliseconds
        
        # Initialize directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.wal_dir = self.data_dir / "wal"
        self.sst_dir = self.data_dir / "sst"
        self.meta_dir = self.data_dir / "meta"
        
        for d in [self.wal_dir, self.sst_dir, self.meta_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self._memtable = SimpleMemtable()
        self._wal = SimpleWAL(
            self.wal_dir / "wal-current.wal",
            rotate_bytes=config.wal_file_rotate_bytes,
            flush_every_write=config.wal_flush_every_write
        )
        self._catalog = SimpleSSTableCatalog(
            self.meta_dir / "catalog.json",
            max_levels=config.max_levels
        )
        self._compactor = SimpleCompactor(config, self.sst_dir)
        self._sstable_counter = 0
        
        # Recovery
        self._recover()
        
        logger.info(f"Initialized LSM Store at {self.data_dir}")
    
    def _recover(self) -> None:
        """Recover state from WAL."""
        logger.info("Starting recovery from WAL...")
        
        try:
            count = 0
            for key, value, ts in self._wal:
                if value is not None:
                    self._memtable.put(key, value, ts)
                else:
                    self._memtable.delete(key, ts)
                count += 1
                # Update timestamp counter
                self._timestamp_counter = max(self._timestamp_counter, ts + 1)
            
            logger.info(f"Recovered {count} records from WAL")
        except Exception as e:
            raise RecoveryError(f"Failed to recover from WAL: {e}") from e
    
    def _get_timestamp(self) -> Timestamp:
        """Generate monotonically increasing timestamp."""
        with self._lock:
            self._timestamp_counter += 1
            return self._timestamp_counter
    
    def put(self, key: Key, value: Value) -> None:
        """Insert or update key with value."""
        ts = self._get_timestamp()
        
        # Write to WAL
        self._wal.append(key, value, ts)
        
        # Write to memtable
        with self._lock:
            self._memtable.put(key, value, ts)
            
            # Check if flush needed
            if self._memtable.size_bytes() > self.config.memtable_max_bytes:
                self._flush_memtable_locked()
    
    def delete(self, key: Key) -> None:
        """Mark key for deletion (tombstone)."""
        ts = self._get_timestamp()
        
        # Write tombstone to WAL
        self._wal.append(key, None, ts)
        
        # Write to memtable
        with self._lock:
            self._memtable.delete(key, ts)
            
            # Check if flush needed
            if self._memtable.size_bytes() > self.config.memtable_max_bytes:
                self._flush_memtable_locked()
    
    def get(self, key: Key) -> Value | None:
        """Retrieve latest value for key."""
        # Check memtable first
        result = self._memtable.get(key)
        if result is not None:
            value, ts = result
            return value
        
        # Check SSTables
        for level in range(self.config.max_levels):
            sstables = self._catalog.list_level(level)
            for meta in reversed(sstables):
                reader = SimpleSSTableReader(meta['data_path'], meta['meta_path'])
                try:
                    result = reader.get(key)
                    if result is not None:
                        value, ts = result
                        return value
                finally:
                    reader.close()
        
        return None
    
    def get_with_meta(self, key: Key) -> tuple[Value | None, Timestamp] | None:
        """Retrieve latest value and timestamp for key."""
        result = self._memtable.get(key)
        if result is not None:
            return result
        
        for level in range(self.config.max_levels):
            sstables = self._catalog.list_level(level)
            for meta in reversed(sstables):
                reader = SimpleSSTableReader(meta['data_path'], meta['meta_path'])
                try:
                    result = reader.get(key)
                    if result is not None:
                        return result
                finally:
                    reader.close()
        
        return None
    
    def range(self, start: Key | None, end: Key | None) -> Iterator[tuple[Key, Value | None]]:
        """Range scan over keys."""
        all_records: dict[Key, tuple[Value | None, Timestamp]] = {}
        
        # Memtable
        for key, value, ts in self._memtable.iter_range(start, end):
            if key not in all_records or ts > all_records[key][1]:
                all_records[key] = (value, ts)
        
        # SSTables
        for level in range(self.config.max_levels):
            sstables = self._catalog.list_level(level)
            for meta in sstables:
                reader = SimpleSSTableReader(meta['data_path'], meta['meta_path'])
                try:
                    for key, value, ts in reader.iter_range(start, end):
                        if key not in all_records or ts > all_records[key][1]:
                            all_records[key] = (value, ts)
                finally:
                    reader.close()
        
        # Sort and yield non-deleted
        for key in sorted(all_records.keys()):
            value, ts = all_records[key]
            if value is not None:
                yield (key, value)
    
    def flush_memtable(self) -> None:
        """Force flush of memtable to SSTable."""
        with self._lock:
            self._flush_memtable_locked()
    
    def _flush_memtable_locked(self) -> None:
        """Internal flush (must hold lock)."""
        if self._memtable.size_bytes() == 0:
            return
        
        logger.info(f"Flushing memtable ({self._memtable.size_bytes()} bytes)")
        
        # Create new SSTable
        self._sstable_counter += 1
        data_path = self.sst_dir / f"sst-0-{self._sstable_counter}.data"
        meta_path = self.sst_dir / f"sst-0-{self._sstable_counter}.meta"
        
        writer = SimpleSSTableWriter(data_path, meta_path, self.config.bloom_false_positive_rate)
        
        # Write all memtable records
        for key, value, ts in self._memtable.items():
            writer.add(key, value, ts)
        
        # Finalize
        meta = writer.finalize()
        
        # Register in catalog
        self._catalog.add_sstable(0, meta)
        
        # Clear memtable and rotate WAL
        self._memtable.clear()
        self._wal.close()
        
        # Open new WAL
        self._wal = SimpleWAL(
            self.wal_dir / f"wal-{self._sstable_counter}.wal",
            rotate_bytes=self.config.wal_file_rotate_bytes,
            flush_every_write=self.config.wal_flush_every_write
        )
        
        logger.info(f"Flushed memtable to {data_path}")
    
    def compact_level(self, level: int) -> None:
        """Trigger synchronous compaction for a level."""
        if level >= self.config.max_levels - 1:
            logger.warning(f"Cannot compact level {level}, at max level")
            return
        
        with self._lock:
            input_tables = self._catalog.list_level(level)
            
            if not input_tables:
                logger.info(f"No SSTables at level {level}, skipping compaction")
                return
            
            logger.info(f"Compacting level {level} -> {level + 1}")
            
            output_metas = self._compactor.compact(input_tables, level + 1)
            
            self._catalog.remove_sstables(input_tables)
            for meta in output_metas:
                self._catalog.add_sstable(level + 1, meta)
            
            # Delete input files
            for meta in input_tables:
                try:
                    os.unlink(meta['data_path'])
                    os.unlink(meta['meta_path'])
                except Exception as e:
                    logger.warning(f"Failed to delete old SSTable: {e}")
    
    def close(self) -> None:
        """Close store and release resources."""
        logger.info("Closing LSM Store")
        with self._lock:
            self._wal.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
