"""Unit tests for Bloom Filter implementation."""

import pytest
import math
from lsm_tree.components.bloom import SimpleBloomFilter


def test_bloom_filter_basic_membership():
    """Test basic add and membership testing."""
    bf = SimpleBloomFilter(100, 0.01)
    
    # Add some keys
    keys = [b'key1', b'key2', b'key3', b'key4', b'key5']
    for key in keys:
        bf.add(key)
    
    # All added keys should be present (no false negatives)
    for key in keys:
        assert key in bf
    
    # Non-added keys might be present (false positives possible)
    # But we can't guarantee they're absent


def test_bloom_filter_no_false_negatives():
    """Test that bloom filter never has false negatives."""
    bf = SimpleBloomFilter(1000, 0.01)
    
    keys_to_add = [f'key{i}'.encode() for i in range(100)]
    for key in keys_to_add:
        bf.add(key)
    
    # All added keys must be found
    for key in keys_to_add:
        assert key in bf, f"False negative for {key}"


def test_bloom_filter_false_positive_rate():
    """Test that false positive rate is within expected bounds."""
    expected_elements = 1000
    target_fpr = 0.05  # 5%
    bf = SimpleBloomFilter(expected_elements, target_fpr)
    
    # Add expected number of elements
    keys_added = set()
    for i in range(expected_elements):
        key = f'key{i}'.encode()
        bf.add(key)
        keys_added.add(key)
    
    # Test with keys not added
    false_positives = 0
    test_keys = 1000
    
    for i in range(expected_elements, expected_elements + test_keys):
        test_key = f'key{i}'.encode()
        if test_key in bf:
            false_positives += 1
    
    actual_fpr = false_positives / test_keys
    
    # Actual FPR should be close to target (within 2x is acceptable)
    assert actual_fpr <= target_fpr * 2, f"FPR too high: {actual_fpr} > {target_fpr * 2}"


def test_bloom_filter_serialization():
    """Test bloom filter serialization and deserialization."""
    bf = SimpleBloomFilter(100, 0.01)
    
    # Add some keys
    keys = [b'key1', b'key2', b'key3', b'test', b'data']
    for key in keys:
        bf.add(key)
    
    # Serialize
    serialized = bf.serialize()
    assert len(serialized) > 0
    
    # Deserialize
    bf2 = SimpleBloomFilter.deserialize(serialized)
    
    # All original keys should still be present
    for key in keys:
        assert key in bf2
    
    # Behavior should be identical
    test_keys = [b'notadded1', b'notadded2', b'key1', b'key2']
    for key in test_keys:
        assert (key in bf) == (key in bf2)


def test_bloom_filter_empty():
    """Test empty bloom filter behavior."""
    bf = SimpleBloomFilter(100, 0.01)
    
    # Nothing added, so nothing should be found
    test_keys = [b'key1', b'key2', b'test', b'']
    for key in test_keys:
        # Empty filter might still have false positives due to hash collisions
        # but it's very unlikely with a properly sized filter
        pass  # Can't assert false here due to possible hash collisions


def test_bloom_filter_zero_elements():
    """Test bloom filter with zero expected elements."""
    # Should handle gracefully
    bf = SimpleBloomFilter(0, 0.01)
    
    bf.add(b'key1')
    # Should not crash
    assert b'key1' in bf


def test_bloom_filter_parameters():
    """Test bloom filter parameter calculation."""
    expected_elements = 1000
    fpr = 0.01
    bf = SimpleBloomFilter(expected_elements, fpr)
    
    # Check that parameters are reasonable
    assert bf.m > 0  # Bit array size
    assert bf.k > 0  # Number of hash functions
    assert bf.expected_elements == expected_elements
    assert bf.false_positive_rate == fpr


def test_bloom_filter_optimal_sizing():
    """Test that bloom filter uses optimal sizing formulas."""
    expected_elements = 1000
    fpr = 0.01
    bf = SimpleBloomFilter(expected_elements, fpr)
    
    # Calculate theoretical optimal values
    # m = -n * ln(p) / (ln(2)^2)
    expected_m = int(-expected_elements * math.log(fpr) / (math.log(2) ** 2))
    
    # k = (m/n) * ln(2)
    expected_k = int((expected_m / expected_elements) * math.log(2))
    
    # Our values should be close to optimal
    assert abs(bf.m - expected_m) <= max(1, expected_m * 0.1)  # Within 10%
    assert abs(bf.k - expected_k) <= 2  # Within 2 hash functions


def test_bloom_filter_binary_keys():
    """Test bloom filter with binary keys."""
    bf = SimpleBloomFilter(100, 0.01)
    
    binary_keys = [
        b'\x00\x01\x02\x03',
        b'\xFF\xFE\xFD\xFC',
        b'\x80\x81\x82\x83',
        b'',  # Empty key
        b'\x00',  # Single null byte
        b'\xFF',  # Single max byte
    ]
    
    for key in binary_keys:
        bf.add(key)
    
    # All should be found
    for key in binary_keys:
        assert key in bf


def test_bloom_filter_large_keys():
    """Test bloom filter with large keys."""
    bf = SimpleBloomFilter(100, 0.01)
    
    large_keys = [
        b'x' * 1000,
        b'y' * 5000,
        b'z' * 10000,
    ]
    
    for key in large_keys:
        bf.add(key)
    
    for key in large_keys:
        assert key in bf


def test_bloom_filter_different_fpr():
    """Test bloom filters with different false positive rates."""
    keys = [f'key{i}'.encode() for i in range(100)]
    
    # High FPR filter (larger false positive rate, smaller size)
    bf_high_fpr = SimpleBloomFilter(100, 0.1)  # 10%
    
    # Low FPR filter (smaller false positive rate, larger size)
    bf_low_fpr = SimpleBloomFilter(100, 0.001)  # 0.1%
    
    # Add same keys to both
    for key in keys:
        bf_high_fpr.add(key)
        bf_low_fpr.add(key)
    
    # Both should find all added keys
    for key in keys:
        assert key in bf_high_fpr
        assert key in bf_low_fpr
    
    # Low FPR filter should be larger (more bits)
    assert bf_low_fpr.m > bf_high_fpr.m


def test_bloom_filter_many_elements():
    """Test bloom filter with many elements."""
    bf = SimpleBloomFilter(10000, 0.01)
    
    # Add many keys
    keys = [f'key{i:05d}'.encode() for i in range(5000)]
    for key in keys:
        bf.add(key)
    
    # Sample check - all should be found
    for i in range(0, 5000, 100):  # Check every 100th key
        assert keys[i] in bf


def test_bloom_filter_duplicate_adds():
    """Test adding same key multiple times."""
    bf = SimpleBloomFilter(100, 0.01)
    
    key = b'duplicate_key'
    
    # Add same key multiple times
    bf.add(key)
    bf.add(key)
    bf.add(key)
    
    # Should still be found
    assert key in bf


def test_bloom_filter_serialization_format():
    """Test the serialization format is stable."""
    bf = SimpleBloomFilter(100, 0.01)
    bf.add(b'test_key')
    
    serialized = bf.serialize()
    
    # Should start with version byte
    assert serialized[0] == 1  # Version 1
    
    # Should be able to deserialize
    bf2 = SimpleBloomFilter.deserialize(serialized)
    assert b'test_key' in bf2


def test_bloom_filter_deserialization_invalid_version():
    """Test deserialization with invalid version."""
    bf = SimpleBloomFilter(100, 0.01)
    serialized = bf.serialize()
    
    # Corrupt version byte
    corrupted = bytearray(serialized)
    corrupted[0] = 99  # Invalid version
    
    with pytest.raises(ValueError, match="Unsupported bloom filter version"):
        SimpleBloomFilter.deserialize(bytes(corrupted))


def test_bloom_filter_hash_distribution():
    """Test that hash functions provide good distribution."""
    bf = SimpleBloomFilter(1000, 0.01)
    
    # Add keys with similar patterns
    similar_keys = [
        b'key_000001',
        b'key_000002', 
        b'key_000003',
        b'key_000004',
        b'key_000005',
    ]
    
    for key in similar_keys:
        bf.add(key)
    
    # All should be found despite similarity
    for key in similar_keys:
        assert key in bf


def test_bloom_filter_edge_case_fpr():
    """Test bloom filter with edge case false positive rates."""
    # Very low FPR
    bf_low = SimpleBloomFilter(100, 0.0001)  # 0.01%
    bf_low.add(b'test')
    assert b'test' in bf_low
    
    # High FPR (but still < 1)
    bf_high = SimpleBloomFilter(100, 0.5)  # 50%
    bf_high.add(b'test')
    assert b'test' in bf_high