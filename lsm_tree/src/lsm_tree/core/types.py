"""Common type definitions for LSM Tree implementation.

Defines fundamental types used across all components.
"""

from __future__ import annotations
from typing import Optional

# Core primitive types
Key = bytes
Value = bytes
Timestamp = int
Record = tuple[Key, Optional[Value], Timestamp]

# Metadata types
SSTableMeta = dict[str, any]
