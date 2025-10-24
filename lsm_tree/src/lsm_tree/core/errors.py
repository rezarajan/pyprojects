"""Exception hierarchy for LSM Tree.

Defines all custom exceptions used throughout the implementation.
"""

from __future__ import annotations


class LSMError(Exception):
    """Base exception for all LSM Tree errors."""
    pass


class WALCorruptionError(LSMError):
    """Raised when WAL data is corrupted or invalid."""
    pass


class SSTableError(LSMError):
    """Raised when SSTable operations fail."""
    pass


class RecoveryError(LSMError):
    """Raised when recovery from persistent state fails."""
    pass


class CompactionError(LSMError):
    """Raised when compaction operations fail."""
    pass
