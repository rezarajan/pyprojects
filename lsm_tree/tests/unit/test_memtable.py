"""Unit tests for Memtable implementation."""

import pytest
from lsm_tree.components.memtable import SimpleMemtable


@pytest.fixture
def memtable():
    """Create empty memtable for tests."""
    return SimpleMemtable()


def test_memtable_basic_put_get(memtable):
    """Test basic put and get operations."""
    memtable.put(b'key1', b'value1', 1000)
    memtable.put(b'key2', b'value2', 1001)
    
    result1 = memtable.get(b'key1')
    result2 = memtable.get(b'key2')
    result3 = memtable.get(b'nonexistent')
    
    assert result1 == (b'value1', 1000)
    assert result2 == (b'value2', 1001)
    assert result3 is None


def test_memtable_update_overwrites(memtable):
    """Test that put operations overwrite existing keys."""
    memtable.put(b'key1', b'value1', 1000)
    memtable.put(b'key1', b'value2', 1001)
    
    result = memtable.get(b'key1')
    assert result == (b'value2', 1001)


def test_memtable_delete_creates_tombstone(memtable):
    """Test that delete creates tombstone entries."""
    memtable.put(b'key1', b'value1', 1000)
    memtable.delete(b'key1', 1001)
    
    result = memtable.get(b'key1')
    assert result == (None, 1001)  # Tombstone


def test_memtable_delete_nonexistent_key(memtable):
    """Test deleting non-existent key creates tombstone."""
    memtable.delete(b'nonexistent', 1000)
    
    result = memtable.get(b'nonexistent')
    assert result == (None, 1000)  # Tombstone


def test_memtable_items_sorted_order(memtable):
    """Test that items() returns records in sorted key order."""
    # Insert in random order
    keys_values = [
        (b'key3', b'value3', 1002),
        (b'key1', b'value1', 1000),
        (b'key2', b'value2', 1001),
        (b'key5', b'value5', 1004),
        (b'key4', b'value4', 1003),
    ]
    
    for key, value, ts in keys_values:
        memtable.put(key, value, ts)
    
    items = list(memtable.items())
    
    # Should be sorted by key
    expected = [
        (b'key1', b'value1', 1000),
        (b'key2', b'value2', 1001),
        (b'key3', b'value3', 1002),
        (b'key4', b'value4', 1003),
        (b'key5', b'value5', 1004),
    ]
    
    assert items == expected


def test_memtable_iter_range_all(memtable):
    """Test range iteration over all keys."""
    keys_values = [
        (b'key1', b'value1', 1000),
        (b'key2', b'value2', 1001),
        (b'key3', b'value3', 1002),
    ]
    
    for key, value, ts in keys_values:
        memtable.put(key, value, ts)
    
    # Range over all keys
    results = list(memtable.iter_range(None, None))
    assert results == keys_values


def test_memtable_iter_range_with_bounds(memtable):
    """Test range iteration with start and end bounds."""
    for i in range(10):
        key = f'key{i:02d}'.encode()
        value = f'value{i}'.encode()
        memtable.put(key, value, i + 1000)
    
    # Range from key03 to key07 (exclusive)
    results = list(memtable.iter_range(b'key03', b'key07'))
    
    expected = [
        (b'key03', b'value3', 1003),
        (b'key04', b'value4', 1004),
        (b'key05', b'value5', 1005),
        (b'key06', b'value6', 1006),
    ]
    
    assert results == expected


def test_memtable_iter_range_start_only(memtable):
    """Test range iteration with only start bound."""
    for i in range(5):
        key = f'key{i}'.encode()
        value = f'value{i}'.encode()
        memtable.put(key, value, i + 1000)
    
    # From key2 onwards
    results = list(memtable.iter_range(b'key2', None))
    
    expected = [
        (b'key2', b'value2', 1002),
        (b'key3', b'value3', 1003),
        (b'key4', b'value4', 1004),
    ]
    
    assert results == expected


def test_memtable_iter_range_end_only(memtable):
    """Test range iteration with only end bound."""
    for i in range(5):
        key = f'key{i}'.encode()
        value = f'value{i}'.encode()
        memtable.put(key, value, i + 1000)
    
    # Up to key3 (exclusive)
    results = list(memtable.iter_range(None, b'key3'))
    
    expected = [
        (b'key0', b'value0', 1000),
        (b'key1', b'value1', 1001),
        (b'key2', b'value2', 1002),
    ]
    
    assert results == expected


def test_memtable_iter_range_includes_tombstones(memtable):
    """Test that range iteration includes tombstones."""
    memtable.put(b'key1', b'value1', 1000)
    memtable.put(b'key2', b'value2', 1001)
    memtable.delete(b'key2', 1002)  # Create tombstone
    memtable.put(b'key3', b'value3', 1003)
    
    results = list(memtable.iter_range(None, None))
    
    expected = [
        (b'key1', b'value1', 1000),
        (b'key2', None, 1002),  # Tombstone
        (b'key3', b'value3', 1003),
    ]
    
    assert results == expected


def test_memtable_size_bytes_tracking(memtable):
    """Test that size_bytes tracks memory usage correctly."""
    initial_size = memtable.size_bytes()
    
    # Add some data
    memtable.put(b'key1', b'value1', 1000)
    size_after_first = memtable.size_bytes()
    
    memtable.put(b'key2', b'value2', 1001)
    size_after_second = memtable.size_bytes()
    
    # Size should increase
    assert size_after_first > initial_size
    assert size_after_second > size_after_first
    
    # Update existing key
    memtable.put(b'key1', b'new_value', 1002)
    size_after_update = memtable.size_bytes()
    
    # Size should account for the change
    assert size_after_update != size_after_second


def test_memtable_size_bytes_with_tombstones(memtable):
    """Test size tracking with tombstones."""
    memtable.put(b'key1', b'value1', 1000)
    size_with_value = memtable.size_bytes()
    
    # Delete creates tombstone
    memtable.delete(b'key1', 1001)
    size_with_tombstone = memtable.size_bytes()
    
    # Tombstone should be smaller than value
    assert size_with_tombstone < size_with_value
    assert size_with_tombstone > 0  # But not zero


def test_memtable_clear(memtable):
    """Test that clear removes all entries and resets size."""
    # Add some data
    for i in range(10):
        memtable.put(f'key{i}'.encode(), f'value{i}'.encode(), i + 1000)
    
    assert memtable.size_bytes() > 0
    assert len(list(memtable.items())) == 10
    
    # Clear
    memtable.clear()
    
    assert memtable.size_bytes() == 0
    assert len(list(memtable.items())) == 0
    assert memtable.get(b'key0') is None


def test_memtable_empty_keys_and_values(memtable):
    """Test memtable with empty keys and values."""
    # Empty key
    memtable.put(b'', b'value_for_empty_key', 1000)
    
    # Empty value
    memtable.put(b'key_with_empty_value', b'', 1001)
    
    # Both empty
    memtable.put(b'', b'', 1002)  # Overwrites first
    
    result1 = memtable.get(b'')
    result2 = memtable.get(b'key_with_empty_value')
    
    assert result1 == (b'', 1002)
    assert result2 == (b'', 1001)


def test_memtable_binary_keys_and_values(memtable):
    """Test memtable with binary keys and values."""
    binary_data = [
        (b'\x00\x01\x02', b'\xFF\xFE\xFD', 1000),
        (b'\x80\x81\x82', b'\x7F\x7E\x7D', 1001),
        (b'\xFF\xFF', b'\x00\x00', 1002),
    ]
    
    for key, value, ts in binary_data:
        memtable.put(key, value, ts)
    
    # Verify all data
    for key, value, ts in binary_data:
        result = memtable.get(key)
        assert result == (value, ts)
    
    # Check sorted order (lexicographic)
    items = list(memtable.items())
    keys = [key for key, value, ts in items]
    assert keys == sorted(keys)


def test_memtable_large_data(memtable):
    """Test memtable with large keys and values."""
    large_key = b'k' * 1000
    large_value = b'v' * 10000
    
    memtable.put(large_key, large_value, 1000)
    
    result = memtable.get(large_key)
    assert result == (large_value, 1000)
    
    # Size should reflect large data
    size = memtable.size_bytes()
    assert size > 11000  # At least key + value + overhead


def test_memtable_timestamp_ordering(memtable):
    """Test that latest timestamp is kept for same key."""
    key = b'test_key'
    
    # Add multiple values with different timestamps
    memtable.put(key, b'value1', 1000)
    memtable.put(key, b'value2', 1001)
    memtable.put(key, b'value3', 999)   # Earlier timestamp
    memtable.put(key, b'value4', 1002)  # Latest timestamp
    
    result = memtable.get(key)
    assert result == (b'value4', 1002)  # Latest wins


def test_memtable_mixed_operations(memtable):
    """Test mixed put/delete operations."""
    # Put, delete, put again
    memtable.put(b'key1', b'value1', 1000)
    memtable.delete(b'key1', 1001)
    memtable.put(b'key1', b'value2', 1002)
    
    result = memtable.get(b'key1')
    assert result == (b'value2', 1002)  # Latest put wins
    
    # Delete after put
    memtable.delete(b'key1', 1003)
    result = memtable.get(b'key1')
    assert result == (None, 1003)  # Now it's a tombstone


def test_memtable_key_ordering_edge_cases(memtable):
    """Test key ordering with edge case keys."""
    keys = [
        b'',           # Empty key
        b'\x00',       # Null byte
        b'\x00\x00',   # Double null
        b'\x00\x01',   # Null then one
        b'\x01',       # Single byte
        b'\xFF',       # Max byte
        b'a',          # ASCII
        b'z',          # ASCII
    ]
    
    # Insert in reverse order
    for i, key in enumerate(reversed(keys)):
        memtable.put(key, f'value{i}'.encode(), i + 1000)
    
    # Get all items - should be in sorted order
    items = list(memtable.items())
    result_keys = [key for key, value, ts in items]
    
    assert result_keys == sorted(keys)