# Coding Standards

## Principles

- **Python >= 3.10** with comprehensive type hints
- **Modular design**: Small, single-purpose modules
- **Protocol-based interfaces**: Enable pluggability
- **Immutability preferred**: Reduce side effects
- **Explicit contracts**: Document invariants and I/O behavior

## Architecture

### Module Organization

```
src/lsm_tree/
├── core/           # Orchestration and public API
│   ├── config.py   # LSMConfig dataclass
│   ├── errors.py   # Exception hierarchy
│   ├── types.py    # Common types (Key, Value, Timestamp, Record)
│   └── store.py    # LSMStore (public API)
├── interfaces/     # Protocol definitions (abstract contracts)
│   ├── wal.py
│   ├── memtable.py
│   ├── sstable.py
│   ├── bloom.py
│   ├── index.py
│   ├── catalog.py
│   └── store.py
└── components/     # Concrete implementations
    ├── wal.py
    ├── memtable.py
    ├── sstable.py
    ├── bloom.py
    ├── index.py
    ├── catalog.py
    └── compaction.py
```

## Code Style

### Type Hints

```python
from __future__ import annotations
from typing import Protocol, Optional, Iterator

Key = bytes
Value = bytes
Timestamp = int
Record = tuple[Key, Optional[Value], Timestamp]
```

### Docstrings

Include:
- Purpose and responsibility
- Parameters and return types
- Invariants and contracts
- Edge cases

```python
def append(self, key: Key, value: Optional[Value], ts: Timestamp) -> int:
    """Append a record to WAL.
    
    Args:
        key: Binary key
        value: Binary value or None for tombstone
        ts: Monotonic timestamp
    
    Returns:
        WAL sequence number
    
    Invariants:
        - Must be durable on return if config.wal_flush_every_write is True
        - Records are appended in strictly increasing sequence order
    """
```

### Error Handling

- Use specific exception types from `core.errors`
- Log errors; don't silently swallow
- Fail fast on corruption

```python
try:
    self._validate_checksum(data)
except ChecksumError as e:
    raise WALCorruptionError(f"Invalid checksum at offset {offset}") from e
```

### Logging

- Use `logging` module, not `print`
- Include context (file names, offsets, keys)
- Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)

```python
import logging

logger = logging.getLogger(__name__)
logger.info("Flushing memtable: %d entries, %d bytes", count, size)
```

### Testing

- **Arrange-Act-Assert** pattern
- Cover edge cases from requirements doc
- Use fixtures for setup/teardown
- Parametrize tests for variations

```python
def test_wal_replay_skips_partial_record(tmp_path):
    # Arrange: create WAL with partial record at EOF
    wal_path = tmp_path / "test.wal"
    write_partial_record(wal_path)
    
    # Act: replay WAL
    wal = SimpleWAL(wal_path)
    records = list(wal)
    
    # Assert: partial record skipped
    assert len(records) == 0
```

## Performance Guidelines

- Prefer sequential I/O over random I/O
- Batch operations where possible
- Use append-only writes
- Minimize memory allocations in hot paths
- Profile before optimizing

## Safety Guidelines

- Atomic file operations (`os.replace`)
- Checksums for persistence (CRC32 for frames, SHA256 for files)
- fsync when durability required
- Lock ordering to prevent deadlocks

## Dependencies

Minimize external dependencies:
- **sortedcontainers**: For sorted memtable
- **pytest**: Testing only
- **pdoc**: Documentation only

Avoid heavy frameworks.
