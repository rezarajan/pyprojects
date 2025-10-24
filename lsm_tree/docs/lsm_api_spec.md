
# LSM Tree Python Implementation — API & Modular Interface Specification

_Last updated: 2025-10-24_

## Purpose

This document extends the technical requirements with **concrete, modular API specifications** for each major component of the LSM Tree: WAL, Memtable, SSTable, Compactor, Indexing, Bloom filter, and the Read Engine.  
It is written to be **used by AI agents or developers** to generate code, tests, and alternative backends. Each section provides:

- A short description of responsibility.
- A Pythonic interface (abstract base class / protocol) with method signatures and types.
- I/O contracts, persistence formats, and expected invariants.
- Extension points for alternate implementations.

> Target runtime: **Python 3.10+** (type hints use `typing` standard library)
---

## Conventions & Types

Common typing imports assumed for the signatures:

```py
from __future__ import annotations
from typing import Protocol, Iterable, Iterator, Optional, Tuple, Mapping, Sequence, Any, Dict
from dataclasses import dataclass
```

Common primitive types used in signatures:

- `Key = bytes` — canonical binary key representation.
- `Value = bytes` — canonical binary value representation.
- `Timestamp = int` — monotonic or wall-clock integer (e.g., UNIX epoch ms).
- `Record = Tuple[Key, Optional[Value], Timestamp]` — `Optional[Value]` is `None` for tombstones.
- `SSTableMeta = Mapping[str, Any]` — metadata dictionary for SSTable.

File naming conventions (recommended):
- WAL files: `wal-{sequence}.wal`
- SSTable data: `sst-{level}-{id}.data`
- SSTable index/meta: `sst-{level}-{id}.meta`
- Checksum: appended or embedded in `.meta`

All bytes persisted should be encoded with explicit framing/length-prefixing (e.g., struct pack with 64-bit lengths) for robust WAL/SST parsing.

---

## 1. Configuration & Errors

### Config dataclass (example)

```py
@dataclass
class LSMConfig:
    data_dir: str
    memtable_max_bytes: int = 64 * 1024 * 1024
    wal_flush_every_write: bool = True
    bloom_false_positive_rate: float = 0.01
    compaction_threshold_bytes: int = 256 * 1024 * 1024
    tombstone_retention_seconds: int = 86400
    sstable_max_bytes: int = 64 * 1024 * 1024
    max_levels: int = 6
    wal_file_rotate_bytes: int = 64 * 1024 * 1024
```

### Errors

Define a consistent exception hierarchy:

```py
class LSMError(Exception): pass
class WALCorruptionError(LSMError): pass
class SSTableError(LSMError): pass
class RecoveryError(LSMError): pass
class CompactionError(LSMError): pass
```

---

## 2. WAL (Write-Ahead Log)

### Responsibility
Durably append mutation records (INSERT/UPDATE/DELETE). Support crash-safe replay to rebuild Memtable.

### WAL Protocol / Interface

```py
class WALWriter(Protocol):
    def append(self, key: Key, value: Optional[Value], ts: Timestamp) -> int:
        """
        Append a record to WAL. Returns a monotonically increasing WAL sequence/offset.
        Must be durable on return if `wal_flush_every_write` is True.
        """

    def sync(self) -> None:
        """Force data to disk (fsync)."""

    def close(self) -> None:
        """Close writer and release resources."""

class WALReader(Protocol):
    def __iter__(self) -> Iterator[Record]:
        """Iterate records in WAL in append order."""

class WALManager(Protocol):
    def open_writer(self) -> WALWriter:
        ...

    def rotate(self) -> None:
        """Rotate WAL (e.g., when file grows too large)."""
```

### Persistence Format (I/O contract)
- Each record: `[magic (4B)] [length_key (4 or 8B)] [key bytes] [length_value (8B)] [value bytes or zero-length] [ts (8B)] [op code (1B)] [crc32 (4B)]`
- `op code`: `0=INSERT/UPDATE`, `1=DELETE`
- Each file ends with a small footer with file sequence and checksum.
- Reader must skip any partial record at EOF (treat as incomplete) and raise `WALCorruptionError` only if checksum/footer invalid.

### Extension Points
- Implementations may choose memory-mapped files, plain append files, or a wrapper that batches writes.

---

## 3. Memtable

### Responsibility
In-memory sorted structure holding recent writes. Efficient for point and range lookups.

### Interface

```py
class Memtable(Protocol):
    def put(self, key: Key, value: Value, ts: Timestamp) -> None:
        """Insert or update key with value and timestamp."""

    def delete(self, key: Key, ts: Timestamp) -> None:
        """Mark key as tombstone with timestamp."""

    def get(self, key: Key) -> Optional[Tuple[Optional[Value], Timestamp]]:
        """
        Return (value_or_none, timestamp) if key found in memtable; else None.
        If value_or_none is None, it is a tombstone.
        """

    def iter_range(self, start: Optional[Key], end: Optional[Key]) -> Iterator[Record]:
        """
        Iterate records in key order between start and end (inclusive/exclusive semantics documented).
        """

    def size_bytes(self) -> int:
        """Return approximate memory usage in bytes."""

    def clear(self) -> None:
        """Clear all entries (used after flush)."""

    def items(self) -> Iterable[Record]:
        """Return iterator of all records in sorted key order (key, value_or_none, ts)."""
```

### Implementation notes
- Backing structures: `sortedcontainers.SortedDict` (if allowed), `bisect` on list of keys + parallel lists, or custom skiplist.
- Must provide predictable iteration order by key.
- Must be thread-safe at API boundary (lock internally if concurrent writers/readers exist).

### Flush contract
- When `size_bytes()` > `memtable_max_bytes`, caller triggers `Memtable.items()` to create new SSTable and then `clear()`.

---

## 4. SSTable

### Responsibility
Immutable sorted file on disk with data blocks, index, filter, and metadata. Support point lookups and range scans with efficient I/O.

### On-disk layout (recommended)
- Data blocks: concatenated key-value records in sorted order, framed with per-record length. May be grouped into block pages (e.g., 4KB) with optional compression.
- Index block: list of (key, file_offset) sampled at block boundaries to enable binary search.
- Bloom filter: serialized bitset with parameters.
- Footer / meta: min_key, max_key, sstable_id, level, checksum, timestamp range.

### Interface

```py
class SSTableReader(Protocol):
    meta: SSTableMeta

    def may_contain(self, key: Key) -> bool:
        """Use Bloom filter to test potential presence."""

    def get(self, key: Key) -> Optional[Tuple[Optional[Value], Timestamp]]:
        """Return (value_or_none, ts) or None if key definitely not present."""

    def iter_range(self, start: Optional[Key], end: Optional[Key]) -> Iterator[Record]:
        """Iterate key-ordered records from start to end."""

    def close(self) -> None:
        """Release file descriptors / mmaps."""

class SSTableWriter(Protocol):
    def add(self, key: Key, value: Optional[Value], ts: Timestamp) -> None:
        """Append record to the writer (must be added in sorted order)."""

    def finalize(self) -> SSTableMeta:
        """Flush and write index/filter/footer. Return metadata for registry."""
```

### Invariants
- Files are immutable after finalize.
- Keys added to writer must be strictly non-decreasing.
- `may_contain` false implies `get` must return `None`.
- `get` must return the exact stored `value` and `ts` read from disk.

### Metadata registry
A lightweight metadata registry (e.g., JSON or SQLite) maps level → list of SSTables and their meta. Must be atomic when updated (write temp + rename).

---

## 5. Bloom Filter

### Responsibility
Low-cost probabilistic presence test per SSTable.

### Interface

```py
class BloomFilter(Protocol):
    def add(self, key: Key) -> None:
        ...

    def __contains__(self, key: Key) -> bool:
        """Return True if key may be present; False if definitely absent."""

    def serialize(self) -> bytes:
        ...

    @classmethod
    def deserialize(cls, data: bytes) -> "BloomFilter":
        ...
```

### Notes
- Must be constructed with expected number of elements and target false-positive rate.
- Serialization must be space-efficient (bit array + k parameter).

---

## 6. Index (In-memory)

### Responsibility
Provide quick mapping from key → file offset for active SSTables to speed point lookups.

### Interface

```py
class SSTableIndex(Protocol):
    def find_block_offset(self, key: Key) -> Optional[int]:
        """
        Return best-guess file offset to start reading for this key (block-aligned),
        or None if key out of SSTable range.
        """
    def load_to_memory(self) -> None:
        """Materialize index structures in memory for faster lookups."""
```

### Loading policy
- Keep index blocks in memory for hot SSTables. Provide eviction / LRU for memory control.

---

## 7. Compaction / Merge

### Responsibility
Merge SSTables to reduce overlap, remove tombstones older than retention, and maintain level invariants.

### Interface

```py
class Compactor(Protocol):
    def compact(self, input_tables: Sequence[SSTableMeta], target_level: int) -> Sequence[SSTableMeta]:
        """
        Given a set of SSTables (meta), perform merge compaction and write output SSTables
        at target_level. Returns metadata of produced SSTables.
        """
    def schedule(self, level: int) -> None:
        """Schedule background compaction for a level (optional)."""
```

### Merge semantics
- Merge iterators in key order; for duplicate keys pick record with greatest `ts`.
- If resulting record is tombstone and tombstone age > retention window, do not emit it.
- Compaction should write to temporary files then atomically register outputs and delete inputs.

### Concurrency
- Compaction must coordinate with readers and ongoing flushes; file renames/registry updates must be atomic.
- Compaction should hold per-sstable or per-level locks, not global locks for read/write.

---

## 8. Read Engine

### Responsibility
Expose public API for point and range queries; orchestrate reading from Memtable, Level 0..N SSTables, using Bloom filters and indexes to prune reads and merging results.

### Interface / Public API

```py
class LSMStore(Protocol):
    def put(self, key: Key, value: Value) -> None:
        """Client-facing put; generates timestamp internally and ensures durability."""

    def delete(self, key: Key) -> None:
        """Client-facing delete; produce tombstone."""

    def get(self, key: Key) -> Optional[Value]:
        """Return latest value for key or None if not present."""

    def get_with_meta(self, key: Key) -> Optional[Tuple[Optional[Value], Timestamp]]:
        """Return (value_or_none, timestamp)."""

    def range(self, start: Optional[Key], end: Optional[Key]) -> Iterator[Tuple[Key, Optional[Value]]]:
        """Ordered iterator over keys in the range."""

    def compact_level(self, level: int) -> None:
        """Trigger synchronous compaction for a level (administrative)."""

    def flush_memtable(self) -> None:
        """Force memtable flush to SSTable."""
```

### Query Flow (I/O contract)
1. Check Memtable.get.
2. If not found or tombstone, consult Level 0 SSTables in descending recency order:
   - Use `may_contain` (bloom) to skip.
   - Use index to seek into file and read adjacent block.
3. Continue to Level 1..N until found or exhausted.
4. Merge results ensuring the record with highest `ts` returned; tombstones hide older values.
5. For range queries:
   - Build sorted iterators from Memtable and each SSTable that intersects the requested key range.
   - Merge-join the iterators, emitting the most recent non-deleted value per key.

---

## 9. SSTable Registry / Catalog

### Responsibility
Maintain the authoritative list of SSTables per level with metadata.

### Interface

```py
class SSTableCatalog(Protocol):
    def list_level(self, level: int) -> Sequence[SSTableMeta]:
        ...

    def add_sstable(self, level: int, meta: SSTableMeta) -> None:
        """Atomically register a new SSTable in level."""

    def remove_sstables(self, metas: Sequence[SSTableMeta]) -> None:
        """Atomically remove sstables after compaction."""
```

### Atomicity
Use write-to-temp-file + `os.replace()` to atomically update on POSIX filesystems. Alternatively, use a SQLite index with transactions.

---

## 10. Testing & Validation Contracts

Design tests assert the following contracts:

- Durability: After `put(k, v)` returns and a restart occurs, `get(k)` returns `v`.
- Ordering: Range iterators produce records strictly ordered by key.
- Compaction correctness: After compaction, the highest-timestamped value for each key is present; expired tombstones are removed.
- Crash consistency: Simulate partial WAL and partial SSTable writes, then recover — must not return partial/corrupted records.
- Bloom filter false positive: measured false-positive rate ≤ configured rate under representative workloads.

---

## 11. Extension Points & Backends

This design intentionally defines `Protocol`s / abstract interfaces so you may supply alternate implementations:

- WAL: local append-only files (default) or an append service (networked) implementing `WALWriter`.
- Memtable: `SortedDict`-backed or skiplist-backed.
- SSTable: plain binary file writer/reader, SQLite-backed SSTable, or RocksDB-compatible file layout adapter.
- BloomFilter: Standard bitset, or probabilistic counting Bloom filter for better deletion handling.
- Catalog: File-based JSON vs SQLite registry vs etcd for distributed coordination.

---

## 12. Example Minimal Implementation Sketch (signatures only)

```py
class SimpleWAL:
    def __init__(self, path: str, rotate_bytes: int): ...
    def append(self, key: Key, value: Optional[Value], ts: Timestamp) -> int: ...
    def sync(self): ...
    def close(self): ...
    def __iter__(self) -> Iterator[Record]: ...

class SimpleMemtable:
    def __init__(self): ...
    def put(self, key: Key, value: Value, ts: Timestamp): ...
    def delete(self, key: Key, ts: Timestamp): ...
    def get(self, key: Key): ...
    def iter_range(self, start, end): ...
    def items(self): ...
    def size_bytes(self): ...
    def clear(self): ...

class SimpleSSTableWriter:
    def __init__(self, target_path: str, bloom_rate: float): ...
    def add(self, key: Key, value: Optional[Value], ts: Timestamp): ...
    def finalize(self) -> SSTableMeta: ...

class SimpleSSTableReader:
    def __init__(self, path: str): ...
    def may_contain(self, key: Key) -> bool: ...
    def get(self, key: Key): ...
    def iter_range(self, start, end): ...
```

---

## 13. Operational Notes & Best Practices

- Use explicit versions in metadata so readers/writers can evolve format safely.
- Maintain checksums for WAL frames and SSTable files; prefer CRC32 for frames and SHA256 for file-level manifests.
- Favor append-only writes and atomic rename for metadata updates.
- Provide administrative tooling for inspecting levels, SSTable count, and active WALs.
- Document upgrade path for on-disk formats and include backward-compatibility helpers in metadata readers.

---

## 14. Deliverables for Agents

When an AI agent is assigned to implement a component, require the following deliverables:

1. Interface-conforming implementation with docstrings and type hints.
2. Unit tests covering edge cases and invariants.
3. Integration test demonstrating interaction with at least one other real component (e.g., WAL + Memtable + SSTableWriter).
4. Small benchmark/throughput measurement script (optional).

---

## 15. Quick Reference: Key Methods to Implement First

- `WALWriter.append`, `WALReader.__iter__`
- `Memtable.put`, `Memtable.get`, `Memtable.items`
- `SSTableWriter.add`, `SSTableWriter.finalize`
- `SSTableReader.may_contain`, `SSTableReader.get`, `SSTableReader.iter_range`
- `LSMStore.put`, `LSMStore.get`, `LSMStore.range`

---

## Appendix A — Example Record Serialization (WAL)

A minimal framing:

```
struct WAL_RECORD {
  uint32 MAGIC = 0x4C534D01
  uint64 key_len
  byte[key_len] key
  uint64 value_len
  byte[value_len] value  # value_len=0 -> tombstone
  uint64 timestamp_ms
  uint8  op_code  # 0=PUT 1=DELETE
  uint32 crc32_of_record_payload
}
```

---

## Appendix B — Glossary

- **Tombstone**: Marker for a deleted key; retains timestamp so compaction can remove old deletes.
- **Memtable**: In-memory, sorted map of recent updates.
- **SSTable**: Sorted string table (immutable file on disk).
- **Compaction**: Process merging SSTables across levels.
- **Bloom filter**: Probabilistic set membership test to avoid unnecessary I/O.

---

_End of specification._
