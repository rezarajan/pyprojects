"""SSTable implementation with bloom filter and sparse index.

Provides immutable sorted string table with efficient lookups.
"""

from __future__ import annotations

import json
import logging
import os
import struct
from collections.abc import Iterator
from pathlib import Path

from ..core.errors import SSTableError
from ..core.types import Key, Record, SSTableMeta, Timestamp, Value
from .bloom import SimpleBloomFilter

logger = logging.getLogger(__name__)

# Record format: [key_len(8B)][key][value_len(8B)][value][ts(8B)]


class SimpleSSTableWriter:
    """Write sorted records to immutable SSTable file.

    Args:
        data_path: Path for .data file
        meta_path: Path for .meta file
        bloom_fpr: False positive rate for bloom filter
        index_interval: Sample every N records for sparse index

    Invariants:
        - Records must be added in sorted key order
        - Files are written atomically on finalize
    """

    def __init__(
        self,
        data_path: str | Path,
        meta_path: str | Path,
        bloom_fpr: float = 0.01,
        index_interval: int = 100,
    ):
        self.data_path = Path(data_path)
        self.meta_path = Path(meta_path)
        self.bloom_fpr = bloom_fpr
        self.index_interval = index_interval

        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = open(self.data_path, "wb")

        self._min_key: Key | None = None
        self._max_key: Key | None = None
        self._min_ts: Timestamp | None = None
        self._max_ts: Timestamp | None = None
        self._count = 0
        self._last_key: Key | None = None

        # Index: list of (key, offset)
        self._index: list[tuple[Key, int]] = []

        # Bloom filter (will be created on finalize)
        self._keys_for_bloom: list[Key] = []

    def add(self, key: Key, value: Value | None, ts: Timestamp) -> None:
        """Append record to the writer (must be added in sorted order)."""
        # Verify sorted order
        if self._last_key is not None and key <= self._last_key:
            raise SSTableError(f"Keys must be added in sorted order: {self._last_key} >= {key}")

        # Record current offset
        offset = self._fd.tell()

        # Update metadata
        if self._min_key is None:
            self._min_key = key
        self._max_key = key

        if self._min_ts is None:
            self._min_ts = ts
            self._max_ts = ts
        else:
            self._min_ts = min(self._min_ts, ts)
            self._max_ts = max(self._max_ts, ts)

        # Sample for sparse index
        if self._count % self.index_interval == 0:
            self._index.append((key, offset))

        # Collect for bloom filter
        self._keys_for_bloom.append(key)

        # Write record
        value_bytes = value if value is not None else b""
        key_len = len(key)
        value_len = len(value_bytes)

        self._fd.write(struct.pack("<Q", key_len))
        self._fd.write(key)
        self._fd.write(struct.pack("<Q", value_len))
        self._fd.write(value_bytes)
        self._fd.write(struct.pack("<Q", ts))

        self._count += 1
        self._last_key = key

    def finalize(self) -> SSTableMeta:
        """Flush and write index/filter/footer. Return metadata for registry."""
        if self._fd is None:
            raise SSTableError("Writer already finalized")

        # Close data file
        self._fd.close()
        self._fd = None

        data_size = self.data_path.stat().st_size

        # Build bloom filter
        bloom = SimpleBloomFilter(max(1, len(self._keys_for_bloom)), self.bloom_fpr)
        for key in self._keys_for_bloom:
            bloom.add(key)
        bloom_data = bloom.serialize()

        # Build metadata
        meta: SSTableMeta = {
            "data_path": str(self.data_path),
            "meta_path": str(self.meta_path),
            "min_key": self._min_key.hex() if self._min_key else None,
            "max_key": self._max_key.hex() if self._max_key else None,
            "min_ts": self._min_ts,
            "max_ts": self._max_ts,
            "count": self._count,
            "data_size": data_size,
            "index": [(k.hex(), offset) for k, offset in self._index],
        }

        # Write meta file (JSON + bloom filter)
        with open(self.meta_path, "wb") as f:
            json_bytes = json.dumps(meta).encode("utf-8")
            f.write(struct.pack("<I", len(json_bytes)))
            f.write(json_bytes)
            f.write(bloom_data)

        logger.info(f"Finalized SSTable: {self._count} records, {data_size} bytes")
        return meta


class SimpleSSTableReader:
    """Read from immutable SSTable file.

    Args:
        data_path: Path to .data file
        meta_path: Path to .meta file

    Invariants:
        - Files are immutable after creation
        - Bloom filter false negatives are impossible
    """

    def __init__(self, data_path: str | Path, meta_path: str | Path):
        self.data_path = Path(data_path)
        self.meta_path = Path(meta_path)

        # Load metadata and bloom filter
        with open(self.meta_path, "rb") as f:
            json_len = struct.unpack("<I", f.read(4))[0]
            json_bytes = f.read(json_len)
            self.meta = json.loads(json_bytes.decode("utf-8"))
            bloom_data = f.read()
            self._bloom = SimpleBloomFilter.deserialize(bloom_data)

        # Decode index
        self._index = [(bytes.fromhex(k), offset) for k, offset in self.meta["index"]]

        # Decode min/max keys
        self._min_key = bytes.fromhex(self.meta["min_key"]) if self.meta["min_key"] else None
        self._max_key = bytes.fromhex(self.meta["max_key"]) if self.meta["max_key"] else None

        self._fd = None

    def _ensure_open(self) -> None:
        """Lazily open data file."""
        if self._fd is None:
            self._fd = open(self.data_path, "rb")

    def may_contain(self, key: Key) -> bool:
        """Use Bloom filter to test potential presence."""
        # Check key range first
        if self._min_key and key < self._min_key:
            return False
        if self._max_key and key > self._max_key:
            return False
        return key in self._bloom

    def get(self, key: Key) -> tuple[Value | None, Timestamp] | None:
        """Return (value_or_none, ts) or None if key definitely not present."""
        if not self.may_contain(key):
            return None

        self._ensure_open()

        # Binary search in sparse index
        offset = self._find_block_offset(key)
        if offset is None:
            return None

        # Scan from offset
        self._fd.seek(offset)

        while True:
            # Try to read a record
            key_len_bytes = self._fd.read(8)
            if len(key_len_bytes) < 8:
                break  # EOF

            record_key_len = struct.unpack("<Q", key_len_bytes)[0]
            record_key = self._fd.read(record_key_len)

            if len(record_key) < record_key_len:
                break  # Corrupted

            # If we've passed the key, it doesn't exist
            if record_key > key:
                break

            # Read value and timestamp
            value_len = struct.unpack("<Q", self._fd.read(8))[0]
            value_bytes = self._fd.read(value_len)
            ts = struct.unpack("<Q", self._fd.read(8))[0]

            if record_key == key:
                value = value_bytes if value_len > 0 else None
                return (value, ts)

        return None

    def _find_block_offset(self, key: Key) -> int | None:
        """Find starting offset for scanning."""
        if not self._index:
            return 0

        # Binary search in index
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

    def iter_range(self, start: Key | None, end: Key | None) -> Iterator[Record]:
        """Iterate key-ordered records from start to end."""
        self._ensure_open()

        # Find starting offset
        if start is not None:
            offset = self._find_block_offset(start)
        else:
            offset = 0

        self._fd.seek(offset)

        while True:
            key_len_bytes = self._fd.read(8)
            if len(key_len_bytes) < 8:
                break

            key_len = struct.unpack("<Q", key_len_bytes)[0]
            key = self._fd.read(key_len)

            if len(key) < key_len:
                break

            # Check range
            if start is not None and key < start:
                # Skip this record
                value_len = struct.unpack("<Q", self._fd.read(8))[0]
                self._fd.seek(value_len + 8, os.SEEK_CUR)  # Skip value + ts
                continue

            if end is not None and key >= end:
                break

            # Read value and timestamp
            value_len = struct.unpack("<Q", self._fd.read(8))[0]
            value_bytes = self._fd.read(value_len)
            ts = struct.unpack("<Q", self._fd.read(8))[0]

            value = value_bytes if value_len > 0 else None
            yield (key, value, ts)

    def close(self) -> None:
        """Release file descriptors."""
        if self._fd:
            self._fd.close()
            self._fd = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
