"""Configuration for LSM Tree.

Defines all tunable parameters for the LSM storage engine.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LSMConfig:
    """Configuration parameters for LSM Tree storage engine.

    Attributes:
        data_dir: Root directory for all persistent data
        memtable_max_bytes: Maximum size of memtable before flush
        wal_flush_every_write: Whether to fsync after each write
        bloom_false_positive_rate: Target FP rate for bloom filters
        compaction_threshold_bytes: Size threshold to trigger compaction
        tombstone_retention_seconds: How long to retain tombstones
        sstable_max_bytes: Maximum size of a single SSTable
        max_levels: Maximum number of LSM tree levels
        wal_file_rotate_bytes: Size threshold for WAL rotation
        apply_queue_max: Maximum size of background apply queue
        apply_lock_timeout_ms: Timeout for try-lock in apply fallback (ms)
    """

    data_dir: str
    memtable_max_bytes: int = 64 * 1024 * 1024  # 64 MB
    wal_flush_every_write: bool = True
    bloom_false_positive_rate: float = 0.01
    compaction_threshold_bytes: int = 256 * 1024 * 1024  # 256 MB
    tombstone_retention_seconds: int = 86400  # 1 day
    sstable_max_bytes: int = 64 * 1024 * 1024  # 64 MB
    max_levels: int = 6
    wal_file_rotate_bytes: int = 64 * 1024 * 1024  # 64 MB
    apply_queue_max: int = 100_000  # Background apply queue size
    apply_lock_timeout_ms: int = 5  # Timeout for fallback sync apply
