"""Unit tests for Write-Ahead Log (WAL) implementation."""

import shutil
import struct
import tempfile
from pathlib import Path

import pytest

from lsm_tree.components.wal import SimpleWAL
from lsm_tree.core.errors import WALCorruptionError


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def wal_path(temp_dir):
    """Create WAL file path."""
    return Path(temp_dir) / "test.wal"


def test_wal_append_and_read(wal_path):
    """Test basic WAL append and read functionality."""
    wal = SimpleWAL(wal_path, flush_every_write=True)

    # Append records
    seq1 = wal.append(b"key1", b"value1", 1000)
    seq2 = wal.append(b"key2", b"value2", 1001)
    seq3 = wal.append(b"key3", None, 1002)  # Tombstone

    assert seq1 == 1
    assert seq2 == 2
    assert seq3 == 3

    wal.close()

    # Read back records
    wal = SimpleWAL(wal_path)
    records = list(wal)

    assert len(records) == 3
    assert records[0] == (b"key1", b"value1", 1000)
    assert records[1] == (b"key2", b"value2", 1001)
    assert records[2] == (b"key3", None, 1002)

    wal.close()


def test_wal_empty_values(wal_path):
    """Test WAL with empty values (not tombstones)."""
    wal = SimpleWAL(wal_path)

    wal.append(b"key1", b"", 1000)  # Empty value
    wal.append(b"key2", None, 1001)  # Tombstone

    wal.close()

    # Read back
    wal = SimpleWAL(wal_path)
    records = list(wal)

    assert len(records) == 2
    assert records[0] == (b"key1", b"", 1000)
    assert records[1] == (b"key2", None, 1001)

    wal.close()


def test_wal_large_records(wal_path):
    """Test WAL with large keys and values."""
    wal = SimpleWAL(wal_path)

    large_key = b"k" * 1000
    large_value = b"v" * 10000

    wal.append(large_key, large_value, 1000)
    wal.close()

    # Read back
    wal = SimpleWAL(wal_path)
    records = list(wal)

    assert len(records) == 1
    assert records[0] == (large_key, large_value, 1000)

    wal.close()


def test_wal_sync_operations(wal_path):
    """Test WAL sync operations."""
    wal = SimpleWAL(wal_path, flush_every_write=False)

    wal.append(b"key1", b"value1", 1000)
    wal.append(b"key2", b"value2", 1001)

    # Manual sync
    wal.sync()

    wal.close()

    # Verify data is persisted
    wal = SimpleWAL(wal_path)
    records = list(wal)
    assert len(records) == 2
    wal.close()


def test_wal_recovery_skips_partial_records(wal_path):
    """Test that WAL recovery skips partial records at EOF."""
    # Create a WAL with complete records
    wal = SimpleWAL(wal_path)
    wal.append(b"key1", b"value1", 1000)
    wal.append(b"key2", b"value2", 1001)
    wal.close()

    # Truncate file to create partial record
    with open(wal_path, "r+b") as f:
        f.seek(0, 2)  # Go to end
        size = f.tell()
        f.truncate(size - 10)  # Remove last 10 bytes

    # Recovery should skip partial record
    wal = SimpleWAL(wal_path)
    records = list(wal)

    # Should only have first complete record
    assert len(records) == 1
    assert records[0] == (b"key1", b"value1", 1000)

    wal.close()


def test_wal_corruption_detection(wal_path):
    """Test that WAL detects corruption via CRC mismatch."""
    wal = SimpleWAL(wal_path)
    wal.append(b"key1", b"value1", 1000)
    wal.close()

    # Corrupt the file by changing a byte in the value area (not magic)
    with open(wal_path, "r+b") as f:
        f.seek(25)  # Seek to value area
        f.write(b"\xff")  # Corrupt one byte

    # Reading should raise WALCorruptionError
    wal = SimpleWAL(wal_path)
    with pytest.raises(WALCorruptionError, match="CRC mismatch|Invalid magic"):
        list(wal)

    wal.close()


def test_wal_invalid_magic(wal_path):
    """Test that WAL detects invalid magic numbers."""
    wal = SimpleWAL(wal_path)
    wal.append(b"key1", b"value1", 1000)
    wal.close()

    # Corrupt magic number
    with open(wal_path, "r+b") as f:
        f.seek(0)
        f.write(struct.pack("<I", 0xDEADBEEF))  # Wrong magic

    # Reading should raise WALCorruptionError
    wal = SimpleWAL(wal_path)
    with pytest.raises(WALCorruptionError, match="Invalid magic"):
        list(wal)

    wal.close()


def test_wal_ordering_preserved(wal_path):
    """Test that WAL preserves record ordering."""
    wal = SimpleWAL(wal_path)

    # Append records in specific order
    records_to_write = [
        (b"key1", b"value1", 1000),
        (b"key2", b"value2", 1001),
        (b"key3", b"value3", 1002),
        (b"key1", b"updated_value1", 1003),  # Update
        (b"key4", None, 1004),  # Delete
    ]

    for key, value, ts in records_to_write:
        wal.append(key, value, ts)

    wal.close()

    # Read back and verify order
    wal = SimpleWAL(wal_path)
    records_read = list(wal)

    assert records_read == records_to_write
    wal.close()


def test_wal_durability_across_reopen(wal_path):
    """Test durability guarantee across WAL reopen."""
    # Write some data
    wal1 = SimpleWAL(wal_path, flush_every_write=True)
    wal1.append(b"key1", b"value1", 1000)
    wal1.append(b"key2", b"value2", 1001)
    wal1.close()  # Simulate process restart

    # Reopen and add more data
    wal2 = SimpleWAL(wal_path, flush_every_write=True)
    wal2.append(b"key3", b"value3", 1002)
    wal2.close()

    # Read all data
    wal3 = SimpleWAL(wal_path)
    records = list(wal3)

    assert len(records) == 3
    assert records[0] == (b"key1", b"value1", 1000)
    assert records[1] == (b"key2", b"value2", 1001)
    assert records[2] == (b"key3", b"value3", 1002)

    wal3.close()


def test_wal_binary_keys_and_values(wal_path):
    """Test WAL with binary keys and values."""
    wal = SimpleWAL(wal_path)

    # Test with various binary data
    binary_data = [
        (b"\x00\x01\x02", b"\xff\xfe\xfd", 1000),
        (b"\x80\x81\x82", b"\x7f\x7e\x7d", 1001),
        (b"", b"\x00", 1002),  # Empty key
        (b"\x00", b"", 1003),  # Empty value
    ]

    for key, value, ts in binary_data:
        wal.append(key, value, ts)

    wal.close()

    # Read back
    wal = SimpleWAL(wal_path)
    records = list(wal)

    assert records == binary_data
    wal.close()


def test_wal_context_manager(wal_path):
    """Test WAL as context manager."""
    records_to_write = [
        (b"key1", b"value1", 1000),
        (b"key2", b"value2", 1001),
    ]

    # Write using context manager
    with SimpleWAL(wal_path) as wal:
        for key, value, ts in records_to_write:
            wal.append(key, value, ts)

    # Read back
    with SimpleWAL(wal_path) as wal:
        records = list(wal)

    assert records == records_to_write


def test_wal_closed_operations(wal_path):
    """Test operations on closed WAL."""
    wal = SimpleWAL(wal_path)
    wal.close()

    # Append should raise error
    with pytest.raises(RuntimeError, match="WAL is closed"):
        wal.append(b"key1", b"value1", 1000)


def test_wal_sequence_numbers(wal_path):
    """Test that sequence numbers are monotonic."""
    wal = SimpleWAL(wal_path)

    seq1 = wal.append(b"key1", b"value1", 1000)
    seq2 = wal.append(b"key2", b"value2", 1001)
    seq3 = wal.append(b"key3", b"value3", 1002)

    assert seq1 < seq2 < seq3
    assert seq1 == 1
    assert seq2 == 2
    assert seq3 == 3

    wal.close()
