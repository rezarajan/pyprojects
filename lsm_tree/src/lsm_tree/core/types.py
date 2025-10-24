"""Common type definitions for LSM Tree implementation.

Defines fundamental types used across all components.
"""

from __future__ import annotations

from typing import TypedDict

# Core primitive types
Key = bytes
Value = bytes
Timestamp = int
Record = tuple[Key, Value | None, Timestamp]


class SSTableMeta(TypedDict):
    """Typed metadata describing an SSTable on disk."""
    data_path: str
    meta_path: str
    min_key: str | None
    max_key: str | None
    min_ts: Timestamp | None
    max_ts: Timestamp | None
    count: int
    data_size: int
    index: list[tuple[str, int]]
