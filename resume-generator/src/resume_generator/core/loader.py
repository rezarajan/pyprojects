"""
Load TOML file and return python dict. Use tomllib (py3.11+) or fall back to tomli if not available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import tomllib  # Python 3.11+


def load_toml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    raw = path.read_text(encoding="utf-8")
    data = tomllib.loads(raw)
    return data
