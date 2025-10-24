"""Comprehensive integration tests for LSM Tree implementation.

Tests cover the acceptance criteria from the requirements document:
1. Data durability
2. Data consistency
3. Read correctness
4. Compaction validity
5. Recovery
"""

import shutil
import tempfile

import pytest

from lsm_tree import LSMConfig, SimpleLSMStore


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def store(temp_dir):
    """Create LSM store for tests."""
    config = LSMConfig(
        data_dir=temp_dir,
        memtable_max_bytes=1024,  # Small for testing
        wal_flush_every_write=True,
    )
    store = SimpleLSMStore(config)
    yield store
    store.close()


def test_basic_put_get(store):
    """Test basic put and get operations."""
    store.put(b"key1", b"value1")
    store.put(b"key2", b"value2")

    assert store.get(b"key1") == b"value1"
    assert store.get(b"key2") == b"value2"
    assert store.get(b"nonexistent") is None


def test_update_overwrites(store):
    """Test that updates overwrite previous values."""
    store.put(b"key1", b"value1")
    store.put(b"key1", b"value2")

    assert store.get(b"key1") == b"value2"


def test_delete_tombstone(store):
    """Test deletion creates tombstone."""
    store.put(b"key1", b"value1")
    assert store.get(b"key1") == b"value1"

    store.delete(b"key1")
    assert store.get(b"key1") is None


def test_range_query(store):
    """Test range queries return sorted results."""
    store.put(b"key3", b"value3")
    store.put(b"key1", b"value1")
    store.put(b"key2", b"value2")

    results = list(store.range(None, None))
    assert len(results) == 3
    assert results[0] == (b"key1", b"value1")
    assert results[1] == (b"key2", b"value2")
    assert results[2] == (b"key3", b"value3")


def test_range_with_bounds(store):
    """Test range queries with start/end bounds."""
    for i in range(10):
        store.put(f"key{i:02d}".encode(), f"value{i}".encode())

    results = list(store.range(b"key03", b"key07"))
    assert len(results) == 4
    assert results[0][0] == b"key03"
    assert results[-1][0] == b"key06"


def test_range_excludes_tombstones(store):
    """Test that range queries exclude deleted keys."""
    store.put(b"key1", b"value1")
    store.put(b"key2", b"value2")
    store.put(b"key3", b"value3")

    store.delete(b"key2")

    results = list(store.range(None, None))
    assert len(results) == 2
    assert all(k != b"key2" for k, v in results)


def test_memtable_flush(store):
    """Test memtable flush to SSTable."""
    # Write enough data to trigger flush
    for i in range(100):
        store.put(f"key{i:03d}".encode(), (f"value{i}" * 10).encode())

    # Force flush
    store.flush_memtable()

    # Verify data is still readable
    assert store.get(b"key000") == b"value0" * 10
    assert store.get(b"key099") == b"value99" * 10


def test_recovery_from_wal(temp_dir):
    """Test recovery after restart (Acceptance Criterion 1 & 6)."""
    config = LSMConfig(data_dir=temp_dir, memtable_max_bytes=64 * 1024)

    # Write some data
    store1 = SimpleLSMStore(config)
    store1.put(b"key1", b"value1")
    store1.put(b"key2", b"value2")
    store1.delete(b"key3")
    store1.close()

    # Reopen and verify data is recovered
    store2 = SimpleLSMStore(config)
    assert store2.get(b"key1") == b"value1"
    assert store2.get(b"key2") == b"value2"
    assert store2.get(b"key3") is None
    store2.close()


def test_timestamp_ordering(store):
    """Test that latest timestamp wins (Acceptance Criterion 2)."""
    store.put(b"key1", b"value1")
    store.put(b"key1", b"value2")
    store.put(b"key1", b"value3")

    assert store.get(b"key1") == b"value3"


def test_compaction_removes_duplicates(temp_dir):
    """Test compaction removes duplicate keys (Acceptance Criterion 5)."""
    config = LSMConfig(data_dir=temp_dir, memtable_max_bytes=512)
    store = SimpleLSMStore(config)

    # Write data that will create multiple SSTables
    for i in range(50):
        store.put(b"key1", f"value{i}".encode())
        store.put(b"key2", f"value{i}".encode())

    # Force flush to create SSTables
    store.flush_memtable()

    # Compact level 0
    store.compact_level(0)

    # Verify we still get the correct (latest) values
    assert store.get(b"key1") == b"value49"
    assert store.get(b"key2") == b"value49"

    store.close()


def test_empty_value_not_tombstone(store):
    """Test that empty value (b'') is not treated as tombstone."""
    store.put(b"key1", b"")

    # Empty value should be stored, not deleted
    assert store.get(b"key1") == b""


def test_multiple_levels(temp_dir):
    """Test reading across multiple levels."""
    config = LSMConfig(data_dir=temp_dir, memtable_max_bytes=256)
    store = SimpleLSMStore(config)

    # Write to memtable
    store.put(b"mem_key", b"mem_value")

    # Write and flush to L0
    store.put(b"l0_key", b"l0_value")
    store.flush_memtable()

    # Write more and flush again
    store.put(b"l0_key2", b"l0_value2")
    store.flush_memtable()

    # Verify reads work from all levels
    assert store.get(b"mem_key") == b"mem_value"
    assert store.get(b"l0_key") == b"l0_value"
    assert store.get(b"l0_key2") == b"l0_value2"

    store.close()


def test_large_keys_and_values(store):
    """Test handling of large keys and values."""
    large_key = b"k" * 1000
    large_value = b"v" * 10000

    store.put(large_key, large_value)
    assert store.get(large_key) == large_value


def test_concurrent_reads_after_flush(temp_dir):
    """Test that reads work correctly during/after flush."""
    config = LSMConfig(data_dir=temp_dir, memtable_max_bytes=512)
    store = SimpleLSMStore(config)

    # Write data
    for i in range(20):
        store.put(f"key{i:02d}".encode(), f"value{i}".encode())

    # Flush
    store.flush_memtable()

    # Verify all data is still readable
    for i in range(20):
        assert store.get(f"key{i:02d}".encode()) == f"value{i}".encode()

    store.close()


def test_get_with_meta(store):
    """Test get_with_meta returns timestamp."""
    store.put(b"key1", b"value1")

    result = store.get_with_meta(b"key1")
    assert result is not None
    value, ts = result
    assert value == b"value1"
    assert ts > 0


def test_binary_key_ordering(store):
    """Test that binary keys are sorted correctly."""
    keys = [b"\x00", b"\x01", b"\xff", b"\x80", b"\x7f"]

    for key in keys:
        store.put(key, b"value")

    results = list(store.range(None, None))
    result_keys = [k for k, v in results]

    assert result_keys == sorted(keys)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
