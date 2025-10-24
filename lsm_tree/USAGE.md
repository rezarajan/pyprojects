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

The project includes a comprehensive test suite organized into three categories:
- **Unit Tests**: Component-level testing (WAL, Memtable, Bloom Filter)
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Benchmarks and stress testing

### Test Scripts

**Quick Testing (Recommended):**
```bash
# Run all fast tests (unit + integration)
./tools/scripts/run_tests.sh fast

# Run with verbose output
./tools/scripts/run_tests.sh fast -v
```

**Specific Test Categories:**
```bash
# Unit tests only (49 tests)
./tools/scripts/run_tests.sh unit

# Integration tests only (16 tests)
./tools/scripts/run_tests.sh integration

# Performance benchmarks (7 tests)
./tools/scripts/run_tests.sh performance

# All tests including slow performance tests
./tools/scripts/run_tests.sh all
```

**Comprehensive Validation:**
```bash
# Complete implementation validation
# Includes: linting, type checking, all tests, component validation,
# acceptance criteria verification, and performance benchmarks
./tools/scripts/validate_implementation.sh
```

### Direct pytest Usage

You can also run tests directly with pytest:

```bash
# All fast tests
pytest tests/unit/ tests/integration/ -v

# Specific test files
pytest tests/unit/test_wal.py -v
pytest tests/integration/test_lsm_integration.py -v

# Performance tests with output
pytest tests/performance/ -v -s

# Run tests with coverage
pytest tests/ --cov=lsm_tree --cov-report=html
```

### Test Structure

```
tests/
├── unit/                     # Component unit tests (49 tests)
│   ├── test_wal.py          # Write-Ahead Log tests (13 tests)
│   ├── test_memtable.py     # Memtable tests (19 tests)
│   └── test_bloom.py        # Bloom Filter tests (17 tests)
├── integration/              # End-to-end tests (16 tests)
│   └── test_lsm_integration.py
└── performance/              # Benchmarks (7 tests)
    └── test_benchmarks.py
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

## Development Scripts

The project includes several utility scripts in `tools/scripts/`:

### Test Runner (`run_tests.sh`)

Comprehensive test runner with multiple modes:

```bash
./tools/scripts/run_tests.sh [unit|integration|performance|fast|all] [-v|--verbose]
```

**Options:**
- `unit` - Run unit tests only (49 tests)
- `integration` - Run integration tests only (16 tests)  
- `performance` - Run performance tests only (7 tests)
- `fast` - Run unit + integration tests (recommended for development)
- `all` - Run all tests including slow performance tests
- `-v`, `--verbose` - Enable verbose output

**Examples:**
```bash
# Quick development testing
./tools/scripts/run_tests.sh fast

# Detailed unit test output
./tools/scripts/run_tests.sh unit -v

# Full test suite
./tools/scripts/run_tests.sh all
```

### Implementation Validator (`validate_implementation.sh`)

Comprehensive validation script that runs:
- Dependency checks
- Code linting (if `ruff` available)
- Type checking (if `mypy` available)
- Test structure validation
- Complete test suite
- Component API validation
- Acceptance criteria verification
- Performance benchmarks

```bash
./tools/scripts/validate_implementation.sh
```

**Sample Output:**
```
🔍 LSM Tree Implementation Validation
=====================================
📦 Checking dependencies...
📁 Validating test structure...
✅ Test structure validated

🧪 Running Test Suite
======================
1️⃣  Unit Tests...
📋 Running unit tests only...
================================================ test session starts ================================================
.................................................                                             [100%]
49 passed in 0.05s
✅ Tests completed!

🏗️  Component Validation
=======================
🔧 Testing LSM Store API...
✅ LSM Store API validation passed
💾 Testing WAL durability...
✅ WAL durability validation passed
...

🎉 Implementation Validation Summary
====================================
✅ All tests passed
✅ Component APIs validated
✅ Acceptance criteria met
🚀 LSM Tree implementation is ready for use!
```

### Other Available Scripts

```bash
# Generate documentation (if available)
./tools/scripts/gen_docs.sh

# Bootstrap development environment
./tools/scripts/bootstrap.sh
```

## Development Workflow

**Recommended development cycle:**

1. **Make changes** to implementation
2. **Quick validation:**
   ```bash
   ./tools/scripts/run_tests.sh fast
   ```
3. **Full validation before commit:**
   ```bash
   ./tools/scripts/validate_implementation.sh
   ```
4. **Performance testing** (if needed):
   ```bash
   ./tools/scripts/run_tests.sh performance
   ```

**CI/CD Integration:**

The scripts are designed for CI/CD integration:

```yaml
# Example GitHub Actions usage
- name: Run fast tests
  run: ./tools/scripts/run_tests.sh fast

- name: Full validation
  run: ./tools/scripts/validate_implementation.sh
```

## Limitations

This is a minimal, educational implementation. Production use would require:
- Background compaction scheduler
- LRU cache for hot SSTables
- Compression
- Multi-threaded compaction
- Better error handling and monitoring
