# LSM Tree - Usage Guide

## Installation

```bash
uv pip install -e .
```

## Quick Start

```python
from lsm_tree import SimpleLSMStore, LSMConfig

# Configure and initialize store
config = LSMConfig(
    data_dir="/path/to/data",
    memtable_max_bytes=64 * 1024 * 1024,  # 64 MB
    wal_flush_every_write=True,  # Durability
    bloom_false_positive_rate=0.01,  # 1% FPR
)

store = SimpleLSMStore(config)

# Basic operations
store.put(b'user:1', b'{"name": "Alice", "age": 30}')
store.put(b'user:2', b'{"name": "Bob", "age": 25}')

# Read
value = store.get(b'user:1')
print(value)  # b'{"name": "Alice", "age": 30}'

# Update
store.put(b'user:1', b'{"name": "Alice", "age": 31}')

# Delete
store.delete(b'user:2')

# Range query
for key, value in store.range(b'user:', b'user:~'):
    print(f"{key}: {value}")

# Manual flush
store.flush_memtable()

# Manual compaction
store.compact_level(0)

# Close
store.close()
```

## Context Manager

```python
with SimpleLSMStore(config) as store:
    store.put(b'key', b'value')
    result = store.get(b'key')
# Automatically closed
```

## Crash Recovery

The store automatically recovers from crashes by replaying the Write-Ahead Log (WAL):

```python
# First run
config = LSMConfig(data_dir="/tmp/lsm_data")
store = SimpleLSMStore(config)
store.put(b'key1', b'value1')
store.close()  # or crash here

# After restart - data is recovered
store = SimpleLSMStore(config)
value = store.get(b'key1')  # Returns b'value1'
```

## Features Implemented

✅ **Core Operations**
- Put (insert/update)
- Get (point lookup)
- Delete (tombstone)
- Range scans

✅ **Durability**
- Write-Ahead Log (WAL) with CRC32 checksums
- Configurable fsync on every write
- Automatic recovery from crashes

✅ **Performance Optimizations**
- In-memory memtable with sorted structure
- Bloom filters for efficient lookups
- Sparse indexes for SSTables
- Multi-level compaction

✅ **Data Integrity**
- Atomic file operations
- Timestamp-based conflict resolution
- Tombstone handling
- Compaction with duplicate removal

## Architecture

```
Write Path: User → WAL → Memtable → SSTable (on flush)
Read Path: User → Memtable → Level 0 → Level 1 → ... → Level N
```

### Components

- **WAL**: Append-only log for durability
- **Memtable**: In-memory sorted structure (SortedDict)
- **SSTable**: Immutable sorted files with bloom filters
- **Catalog**: JSON manifest tracking SSTables per level
- **Compactor**: Merges SSTables, removes duplicates/tombstones

## Testing

Run all tests:
```bash
pytest tests/ -v
```

Run integration tests:
```bash
pytest tests/test_lsm_integration.py -v
```

## Configuration Options

```python
LSMConfig(
    data_dir: str,                          # Root directory
    memtable_max_bytes: int = 64MB,         # Flush threshold
    wal_flush_every_write: bool = True,     # Durability vs performance
    bloom_false_positive_rate: float = 0.01,# Bloom filter accuracy
    compaction_threshold_bytes: int = 256MB,# Compaction trigger
    tombstone_retention_seconds: int = 86400,# Keep tombstones for 1 day
    sstable_max_bytes: int = 64MB,          # Max SSTable size
    max_levels: int = 6,                    # LSM tree depth
    wal_file_rotate_bytes: int = 64MB,      # WAL rotation size
)
```

## Acceptance Criteria Status

✅ **Data Durability**: All acknowledged writes survive crashes  
✅ **Data Consistency**: Latest timestamp wins for conflicts  
✅ **Read Correctness**: Tombstones respected, range queries work  
✅ **Compaction Validity**: Duplicates removed, tombstones purged  
✅ **Recovery**: WAL replay reconstructs memtable correctly  
✅ **Bloom Filter Accuracy**: False positive rate ≤ configured threshold

## Performance Characteristics

- **Writes**: O(1) amortized (memtable + WAL append)
- **Point Reads**: O(log N) with bloom filter pruning
- **Range Scans**: O(N + M) where M is result size
- **Compaction**: O(N log N) per level

## Limitations

This is a minimal, educational implementation. Production use would require:
- Background compaction scheduler
- LRU cache for hot SSTables
- Compression
- Multi-threaded compaction
- Better error handling and monitoring
