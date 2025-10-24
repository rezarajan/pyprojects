"""Performance benchmarks for LSM Tree implementation."""

import shutil
import tempfile
import time

import pytest

from lsm_tree import LSMConfig, SimpleLSMStore


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def benchmark_store(temp_dir):
    """Create store optimized for benchmarks."""
    config = LSMConfig(
        data_dir=temp_dir,
        memtable_max_bytes=1024 * 1024,  # 1MB
        wal_flush_every_write=False,  # Faster writes
        bloom_false_positive_rate=0.01,
    )
    store = SimpleLSMStore(config)
    yield store
    store.close()


def test_sequential_write_performance(benchmark_store):
    """Benchmark sequential write performance."""
    num_records = 10000
    key_size = 16
    value_size = 100

    keys = [f"key{i:08d}".encode().ljust(key_size, b"0") for i in range(num_records)]
    values = [f"value{i}".encode().ljust(value_size, b"x") for i in range(num_records)]

    start_time = time.time()

    for key, value in zip(keys, values, strict=True):
        benchmark_store.put(key, value)

    # Force flush to measure disk write time
    benchmark_store.flush_memtable()
    benchmark_store._wal.sync()

    end_time = time.time()
    duration = end_time - start_time

    writes_per_second = num_records / duration if duration > 0 else float("inf")

    print(f"\nSequential writes: {writes_per_second:.0f} ops/sec")
    print(f"Total time: {duration:.3f}s for {num_records} records")

    # Should achieve reasonable throughput
    assert writes_per_second > 1000  # At least 1K ops/sec


def test_random_read_performance(benchmark_store):
    """Benchmark random read performance."""
    num_records = 1000

    # Prepare data
    keys = [f"key{i:08d}".encode() for i in range(num_records)]
    values = [f"value{i}".encode() * 10 for i in range(num_records)]

    for key, value in zip(keys, values, strict=True):
        benchmark_store.put(key, value)

    # Force flush to test reading from SSTables
    benchmark_store.flush_memtable()

    # Random read test
    import random

    random_keys = random.sample(keys, min(500, num_records))

    start_time = time.time()

    for key in random_keys:
        result = benchmark_store.get(key)
        assert result is not None

    end_time = time.time()
    duration = end_time - start_time

    reads_per_second = len(random_keys) / duration if duration > 0 else float("inf")

    print(f"\nRandom reads: {reads_per_second:.0f} ops/sec")
    print(f"Total time: {duration:.3f}s for {len(random_keys)} reads")

    # Should achieve reasonable read throughput
    assert reads_per_second > 500  # At least 500 ops/sec


def test_range_scan_performance(benchmark_store):
    """Benchmark range scan performance."""
    num_records = 5000

    # Prepare sorted data
    keys = [f"key{i:08d}".encode() for i in range(num_records)]
    values = [f"value{i}".encode() for i in range(num_records)]

    for key, value in zip(keys, values, strict=True):
        benchmark_store.put(key, value)

    benchmark_store.flush_memtable()

    # Range scan test - scan 10% of data
    scan_size = num_records // 10
    start_key = f"key{num_records // 4:08d}".encode()
    end_key = f"key{num_records // 4 + scan_size:08d}".encode()

    start_time = time.time()

    results = list(benchmark_store.range(start_key, end_key))

    end_time = time.time()
    duration = end_time - start_time

    scans_per_second = len(results) / duration if duration > 0 else float("inf")

    print(f"\nRange scan: {scans_per_second:.0f} records/sec")
    print(f"Scanned {len(results)} records in {duration:.3f}s")

    assert len(results) > 0
    assert scans_per_second > 1000  # Should scan at least 1K records/sec


def test_mixed_workload_performance(benchmark_store):
    """Benchmark mixed read/write workload."""
    num_operations = 2000

    import random

    keys = [f"key{i:08d}".encode() for i in range(num_operations)]
    values = [f"value{i}".encode() * 5 for i in range(num_operations)]

    # Pre-populate with some data
    for i in range(0, num_operations // 2):
        benchmark_store.put(keys[i], values[i])

    benchmark_store.flush_memtable()

    # Mixed workload: 70% reads, 30% writes
    operations = []
    for i in range(num_operations):
        if random.random() < 0.7:  # Read
            key = random.choice(keys[: num_operations // 2])  # Read existing
            operations.append(("read", key, None))
        else:  # Write
            operations.append(("write", keys[i], values[i]))

    start_time = time.time()

    for op_type, key, value in operations:
        if op_type == "read":
            benchmark_store.get(key)
        else:
            benchmark_store.put(key, value)

    end_time = time.time()
    duration = end_time - start_time

    ops_per_second = len(operations) / duration if duration > 0 else float("inf")

    print(f"\nMixed workload: {ops_per_second:.0f} ops/sec")
    print(f"Total time: {duration:.3f}s for {len(operations)} operations")

    assert ops_per_second > 500  # Mixed workload should still be fast


def test_compaction_performance(benchmark_store):
    """Benchmark compaction performance."""
    num_records = 2000

    # Create data that will need compaction
    keys = [f"key{i:04d}".encode() for i in range(num_records)]

    # Write same keys multiple times to create duplicates
    for iteration in range(3):
        for i, key in enumerate(keys):
            value = f"value{iteration}_{i}".encode()
            benchmark_store.put(key, value)

    # Force multiple flushes
    benchmark_store.flush_memtable()

    # Measure compaction time
    start_time = time.time()

    benchmark_store.compact_level(0)

    end_time = time.time()
    duration = end_time - start_time

    print(f"\nCompaction time: {duration:.3f}s for {num_records * 3} input records")

    # Verify data is still correct after compaction
    for key in keys[:10]:  # Sample check
        result = benchmark_store.get(key)
        assert result is not None
        assert result.startswith(b"value2_")  # Latest value


def test_recovery_performance(temp_dir):
    """Benchmark recovery performance."""
    num_records = 5000

    config = LSMConfig(
        data_dir=temp_dir,
        memtable_max_bytes=2 * 1024 * 1024,  # Larger memtable
        wal_flush_every_write=True,  # Ensure durability
    )

    # Write data
    store1 = SimpleLSMStore(config)

    keys = [f"key{i:06d}".encode() for i in range(num_records)]
    values = [f"value{i}".encode() * 3 for i in range(num_records)]

    for key, value in zip(keys, values, strict=True):
        store1.put(key, value)

    store1.close()

    # Measure recovery time
    start_time = time.time()

    store2 = SimpleLSMStore(config)

    end_time = time.time()
    duration = end_time - start_time

    recovery_rate = num_records / duration if duration > 0 else float("inf")

    print(f"\nRecovery: {recovery_rate:.0f} records/sec")
    print(f"Recovered {num_records} records in {duration:.3f}s")

    # Verify data is recovered correctly
    sample_keys = keys[::100]  # Every 100th key
    for key in sample_keys:
        result = store2.get(key)
        assert result is not None

    store2.close()

    assert recovery_rate > 1000  # Should recover quickly


@pytest.mark.slow
def test_large_dataset_performance(temp_dir):
    """Benchmark with larger dataset (marked as slow)."""
    num_records = 50000

    config = LSMConfig(
        data_dir=temp_dir,
        memtable_max_bytes=4 * 1024 * 1024,  # 4MB
        wal_flush_every_write=False,
    )

    store = SimpleLSMStore(config)

    # Generate data
    keys = [f"key{i:08d}".encode() for i in range(num_records)]
    values = [f"value{i}".encode() * 5 for i in range(num_records)]

    print(f"\nTesting with {num_records} records...")

    # Measure write performance
    start_time = time.time()

    for i, (key, value) in enumerate(zip(keys, values, strict=True)):
        store.put(key, value)

        # Progress indicator
        if i % 10000 == 0 and i > 0:
            elapsed = time.time() - start_time
            rate = i / elapsed
            print(f"Written {i} records ({rate:.0f} ops/sec)")

    store.flush_memtable()
    store._wal.sync()

    write_end_time = time.time()
    write_duration = write_end_time - start_time
    write_rate = num_records / write_duration

    print(f"Write performance: {write_rate:.0f} ops/sec")

    # Measure read performance on subset
    read_keys = keys[::100]  # Every 100th key

    read_start_time = time.time()

    for key in read_keys:
        result = store.get(key)
        assert result is not None

    read_end_time = time.time()
    read_duration = read_end_time - read_start_time
    read_rate = len(read_keys) / read_duration

    print(f"Read performance: {read_rate:.0f} ops/sec")

    store.close()

    # Performance should be reasonable even with large datasets
    assert write_rate > 500
    assert read_rate > 200


if __name__ == "__main__":
    # Run benchmarks with output
    pytest.main([__file__, "-v", "-s"])
