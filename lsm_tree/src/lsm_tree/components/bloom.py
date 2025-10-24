"""Bloom filter implementation.

Simple bit-array based bloom filter with configurable false-positive rate.
"""

from __future__ import annotations
import math
import struct
import hashlib
from ..core.types import Key


class SimpleBloomFilter:
    """Probabilistic set membership test using bit array.
    
    Args:
        expected_elements: Number of elements expected to be inserted
        false_positive_rate: Target false positive rate (0 < rate < 1)
    
    Invariants:
        - False positives are possible
        - False negatives are not possible
        - Filter size is fixed at creation time
    """
    
    def __init__(self, expected_elements: int, false_positive_rate: float = 0.01):
        # Calculate optimal bit array size and hash count
        # m = -n * ln(p) / (ln(2)^2)
        # k = (m/n) * ln(2)
        self.expected_elements = expected_elements
        self.false_positive_rate = false_positive_rate
        
        if expected_elements <= 0:
            expected_elements = 1
        
        # Calculate bit array size
        self.m = max(1, int(-expected_elements * math.log(false_positive_rate) / (math.log(2) ** 2)))
        
        # Calculate number of hash functions
        self.k = max(1, int((self.m / expected_elements) * math.log(2)))
        
        # Bit array
        self.bits = bytearray((self.m + 7) // 8)
    
    def _hash(self, key: Key, seed: int) -> int:
        """Generate hash for key with seed."""
        h = hashlib.sha256()
        h.update(struct.pack('<I', seed))
        h.update(key)
        digest = h.digest()
        return int.from_bytes(digest[:4], 'little') % self.m
    
    def add(self, key: Key) -> None:
        """Add key to the filter."""
        for i in range(self.k):
            bit_pos = self._hash(key, i)
            byte_pos = bit_pos // 8
            bit_offset = bit_pos % 8
            self.bits[byte_pos] |= (1 << bit_offset)
    
    def __contains__(self, key: Key) -> bool:
        """Return True if key may be present; False if definitely absent."""
        for i in range(self.k):
            bit_pos = self._hash(key, i)
            byte_pos = bit_pos // 8
            bit_offset = bit_pos % 8
            if not (self.bits[byte_pos] & (1 << bit_offset)):
                return False
        return True
    
    def serialize(self) -> bytes:
        """Serialize filter to bytes."""
        # Format: [version(1B)][expected_n(4B)][fpr(8B)][m(4B)][k(4B)][bits]
        header = struct.pack('<BIQII', 1, self.expected_elements, 
                           int(self.false_positive_rate * 1e9), self.m, self.k)
        return header + bytes(self.bits)
    
    @classmethod
    def deserialize(cls, data: bytes) -> SimpleBloomFilter:
        """Deserialize filter from bytes."""
        # Unpack header
        version, expected_n, fpr_int, m, k = struct.unpack('<BIQII', data[:21])
        if version != 1:
            raise ValueError(f"Unsupported bloom filter version: {version}")
        
        fpr = fpr_int / 1e9
        bits = bytearray(data[21:])
        
        # Create filter and populate
        bf = cls(expected_n, fpr)
        bf.m = m
        bf.k = k
        bf.bits = bits
        return bf
