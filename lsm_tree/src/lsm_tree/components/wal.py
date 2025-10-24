"""Write-Ahead Log implementation.

Provides durable, crash-safe append-only log with CRC32 checksums.
"""

from __future__ import annotations
import os
import struct
import zlib
import logging
from pathlib import Path
from typing import Iterator
from ..core.types import Key, Value, Timestamp, Record
from ..core.errors import WALCorruptionError

logger = logging.getLogger(__name__)

# WAL record format:
# [magic (4B)] [key_len (8B)] [key bytes] [value_len (8B)] [value bytes] [ts (8B)] [op (1B)] [crc32 (4B)]
MAGIC = 0x4C534D01  # "LSM" + version
OP_PUT = 0
OP_DELETE = 1


class SimpleWAL:
    """Simple append-only Write-Ahead Log with CRC32 checksums.
    
    Args:
        path: Path to WAL file
        rotate_bytes: File size threshold for rotation
        flush_every_write: Whether to fsync after each append
    
    Invariants:
        - Records are written atomically with checksums
        - Partial records at EOF are skipped during replay
        - Records are returned in append order
    """
    
    def __init__(self, path: str | Path, rotate_bytes: int = 64 * 1024 * 1024, flush_every_write: bool = True):
        self.path = Path(path)
        self.rotate_bytes = rotate_bytes
        self.flush_every_write = flush_every_write
        self.sequence = 0
        self._fd = None
        self._open_for_write()
    
    def _open_for_write(self) -> None:
        """Open WAL file for appending."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = open(self.path, 'ab')
        # Determine sequence from file size
        self._fd.seek(0, os.SEEK_END)
        pos = self._fd.tell()
        logger.debug(f"Opened WAL {self.path} at offset {pos}")
    
    def append(self, key: Key, value: Value | None, ts: Timestamp) -> int:
        """Append a record to WAL.
        
        Args:
            key: Binary key
            value: Binary value or None for tombstone
            ts: Monotonic timestamp
        
        Returns:
            WAL sequence number
        """
        if self._fd is None:
            raise RuntimeError("WAL is closed")
        
        op_code = OP_DELETE if value is None else OP_PUT
        value_bytes = value if value is not None else b''
        
        # Build record
        key_len = len(key)
        value_len = len(value_bytes)
        
        # Pack payload (without CRC)
        payload = struct.pack('<I', MAGIC)
        payload += struct.pack('<Q', key_len)
        payload += key
        payload += struct.pack('<Q', value_len)
        payload += value_bytes
        payload += struct.pack('<Q', ts)
        payload += struct.pack('<B', op_code)
        
        # Calculate CRC32 of payload
        crc = zlib.crc32(payload)
        record = payload + struct.pack('<I', crc)
        
        # Write to file
        self._fd.write(record)
        if self.flush_every_write:
            self._fd.flush()
            os.fsync(self._fd.fileno())
        
        self.sequence += 1
        logger.debug(f"Appended record seq={self.sequence}, key_len={key_len}, ts={ts}")
        
        return self.sequence
    
    def sync(self) -> None:
        """Force data to disk (fsync)."""
        if self._fd:
            self._fd.flush()
            os.fsync(self._fd.fileno())
    
    def close(self) -> None:
        """Close writer and release resources."""
        if self._fd:
            self.sync()
            self._fd.close()
            self._fd = None
            logger.info(f"Closed WAL {self.path}")
    
    def __iter__(self) -> Iterator[Record]:
        """Iterate records in WAL in append order.
        
        Skips partial records at EOF.
        """
        with open(self.path, 'rb') as f:
            while True:
                # Read magic
                magic_bytes = f.read(4)
                if len(magic_bytes) == 0:
                    break  # EOF
                if len(magic_bytes) < 4:
                    logger.warning(f"Partial record at EOF, skipping")
                    break
                
                magic = struct.unpack('<I', magic_bytes)[0]
                if magic != MAGIC:
                    raise WALCorruptionError(f"Invalid magic: {magic:x}")
                
                # Read key length
                key_len_bytes = f.read(8)
                if len(key_len_bytes) < 8:
                    logger.warning(f"Partial key_len at EOF, skipping")
                    break
                key_len = struct.unpack('<Q', key_len_bytes)[0]
                
                # Read key
                key = f.read(key_len)
                if len(key) < key_len:
                    logger.warning(f"Partial key at EOF, skipping")
                    break
                
                # Read value length
                value_len_bytes = f.read(8)
                if len(value_len_bytes) < 8:
                    logger.warning(f"Partial value_len at EOF, skipping")
                    break
                value_len = struct.unpack('<Q', value_len_bytes)[0]
                
                # Read value
                value_bytes = f.read(value_len)
                if len(value_bytes) < value_len:
                    logger.warning(f"Partial value at EOF, skipping")
                    break
                
                # Read timestamp
                ts_bytes = f.read(8)
                if len(ts_bytes) < 8:
                    logger.warning(f"Partial timestamp at EOF, skipping")
                    break
                ts = struct.unpack('<Q', ts_bytes)[0]
                
                # Read op code
                op_bytes = f.read(1)
                if len(op_bytes) < 1:
                    logger.warning(f"Partial op_code at EOF, skipping")
                    break
                op_code = struct.unpack('<B', op_bytes)[0]
                
                # Read CRC
                crc_bytes = f.read(4)
                if len(crc_bytes) < 4:
                    logger.warning(f"Partial CRC at EOF, skipping")
                    break
                stored_crc = struct.unpack('<I', crc_bytes)[0]
                
                # Verify CRC
                payload = magic_bytes + key_len_bytes + key + value_len_bytes + value_bytes + ts_bytes + op_bytes
                computed_crc = zlib.crc32(payload)
                if stored_crc != computed_crc:
                    raise WALCorruptionError(f"CRC mismatch: expected {computed_crc:x}, got {stored_crc:x}")
                
                # Yield record
                value = value_bytes if op_code == OP_PUT else None
                yield (key, value, ts)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
