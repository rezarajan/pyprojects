#!/usr/bin/env python3
"""AI Agent for LSM Tree code generation.

Reads specs from docs/, scaffolds modules, and optionally uses LLM to suggest tasks.
"""
from __future__ import annotations
import os
import sys
import time
import logging
import pathlib
from typing import Optional, Dict, Any, List

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

# Optional OpenAI client
OPENAI_AVAILABLE = False
try:
    from openai import OpenAI  # type: ignore
    OPENAI_AVAILABLE = True
except ImportError:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
SRC_DIR = ROOT / "src" / "lsm_tree"
TESTS_DIR = ROOT / "tests"
LOG_DIR = ROOT / "ai" / "logs"
PROMPTS_DIR = ROOT / "ai" / "prompts"
CONFIG_PATH = ROOT / "ai" / "agent_config.yaml"


def setup_logging() -> None:
    """Setup logging to file and console."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    log_path = LOG_DIR / f"agent-{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info("Agent log: %s", log_path)


def load_text(path: pathlib.Path) -> str:
    """Load text file content, return empty string on error."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def load_docs() -> Dict[str, str]:
    """Load all markdown docs from docs/ directory."""
    docs = {}
    if DOCS_DIR.exists():
        for p in sorted(DOCS_DIR.glob("*.md")):
            docs[p.name] = load_text(p)
    return docs


def load_config() -> Dict[str, Any]:
    """Load agent configuration from YAML."""
    cfg: Dict[str, Any] = {
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_output_tokens": 2000,
    }
    if yaml and CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                user = yaml.safe_load(f) or {}
                cfg.update(user)
        except Exception as e:
            logging.warning("Failed to read config: %s", e)
    return cfg


def ensure_scaffold() -> None:
    """Create directory structure and placeholder files."""
    # Create expected directory structure
    (SRC_DIR / "components").mkdir(parents=True, exist_ok=True)
    (SRC_DIR / "interfaces").mkdir(parents=True, exist_ok=True)
    (SRC_DIR / "core").mkdir(parents=True, exist_ok=True)
    TESTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py files
    for sub in (SRC_DIR, SRC_DIR / "components", SRC_DIR / "interfaces", SRC_DIR / "core"):
        init = sub / "__init__.py"
        if not init.exists():
            init.write_text('"""LSM Tree package."""\n__all__ = []\n', encoding="utf-8")

    # Module files to create
    files = [
        SRC_DIR / "core" / "config.py",
        SRC_DIR / "core" / "errors.py",
        SRC_DIR / "core" / "types.py",
        SRC_DIR / "core" / "store.py",
        SRC_DIR / "components" / "wal.py",
        SRC_DIR / "components" / "memtable.py",
        SRC_DIR / "components" / "sstable.py",
        SRC_DIR / "components" / "bloom.py",
        SRC_DIR / "components" / "index.py",
        SRC_DIR / "components" / "catalog.py",
        SRC_DIR / "components" / "compaction.py",
        SRC_DIR / "interfaces" / "wal.py",
        SRC_DIR / "interfaces" / "memtable.py",
        SRC_DIR / "interfaces" / "sstable.py",
        SRC_DIR / "interfaces" / "bloom.py",
        SRC_DIR / "interfaces" / "index.py",
        SRC_DIR / "interfaces" / "catalog.py",
        SRC_DIR / "interfaces" / "store.py",
    ]
    
    for f in files:
        if not f.exists():
            f.write_text(
                f'"""\nAuto-generated placeholder: {f.name}\n\n'
                f'Refer to docs/ and implement according to specs.\n"""\n',
                encoding="utf-8",
            )

    # Create smoke test
    smoke = TESTS_DIR / "test_smoke.py"
    if not smoke.exists():
        smoke.write_text(
            '"""Smoke test to verify package imports."""\n'
            'import importlib\n\n'
            'def test_import():\n'
            '    assert importlib.import_module("lsm_tree")\n',
            encoding="utf-8",
        )


def generate_interface_skeletons(docs: Dict[str, str]) -> None:
    """Generate Protocol interface skeletons based on API spec."""
    interfaces = {
        "wal.py": '''"""WAL (Write-Ahead Log) interface protocols."""
from __future__ import annotations
from typing import Protocol, Iterator, Optional

Key = bytes
Value = bytes
Timestamp = int
Record = tuple[Key, Optional[Value], Timestamp]


class WALWriter(Protocol):
    def append(self, key: Key, value: Optional[Value], ts: Timestamp) -> int: ...
    def sync(self) -> None: ...
    def close(self) -> None: ...


class WALReader(Protocol):
    def __iter__(self) -> Iterator[Record]: ...


class WALManager(Protocol):
    def open_writer(self) -> WALWriter: ...
    def rotate(self) -> None: ...
''',
        "memtable.py": '''"""Memtable interface protocol."""
from __future__ import annotations
from typing import Protocol, Optional, Iterator

Key = bytes
Value = bytes
Timestamp = int
Record = tuple[Key, Optional[Value], Timestamp]


class Memtable(Protocol):
    def put(self, key: Key, value: Value, ts: Timestamp) -> None: ...
    def delete(self, key: Key, ts: Timestamp) -> None: ...
    def get(self, key: Key) -> Optional[tuple[Optional[Value], Timestamp]]: ...
    def iter_range(self, start: Optional[Key], end: Optional[Key]) -> Iterator[Record]: ...
    def size_bytes(self) -> int: ...
    def clear(self) -> None: ...
    def items(self) -> Iterator[Record]: ...
''',
        "sstable.py": '''"""SSTable interface protocols."""
from __future__ import annotations
from typing import Protocol, Optional, Iterator, Mapping, Any

Key = bytes
Value = bytes
Timestamp = int
Record = tuple[Key, Optional[Value], Timestamp]
SSTableMeta = Mapping[str, Any]


class SSTableReader(Protocol):
    meta: SSTableMeta
    
    def may_contain(self, key: Key) -> bool: ...
    def get(self, key: Key) -> Optional[tuple[Optional[Value], Timestamp]]: ...
    def iter_range(self, start: Optional[Key], end: Optional[Key]) -> Iterator[Record]: ...
    def close(self) -> None: ...


class SSTableWriter(Protocol):
    def add(self, key: Key, value: Optional[Value], ts: Timestamp) -> None: ...
    def finalize(self) -> SSTableMeta: ...
''',
        "bloom.py": '''"""Bloom filter interface protocol."""
from __future__ import annotations
from typing import Protocol

Key = bytes


class BloomFilter(Protocol):
    def add(self, key: Key) -> None: ...
    def __contains__(self, key: Key) -> bool: ...
    def serialize(self) -> bytes: ...
    
    @classmethod
    def deserialize(cls, data: bytes) -> "BloomFilter": ...
''',
        "index.py": '''"""SSTable index interface protocol."""
from __future__ import annotations
from typing import Protocol, Optional

Key = bytes


class SSTableIndex(Protocol):
    def find_block_offset(self, key: Key) -> Optional[int]: ...
    def load_to_memory(self) -> None: ...
''',
        "catalog.py": '''"""SSTable catalog interface protocol."""
from __future__ import annotations
from typing import Protocol, Sequence, Mapping, Any

SSTableMeta = Mapping[str, Any]


class SSTableCatalog(Protocol):
    def list_level(self, level: int) -> Sequence[SSTableMeta]: ...
    def add_sstable(self, level: int, meta: SSTableMeta) -> None: ...
    def remove_sstables(self, metas: Sequence[SSTableMeta]) -> None: ...
''',
        "store.py": '''"""LSM Store public API interface protocol."""
from __future__ import annotations
from typing import Protocol, Optional, Iterator

Key = bytes
Value = bytes
Timestamp = int


class LSMStore(Protocol):
    def put(self, key: Key, value: Value) -> None: ...
    def delete(self, key: Key) -> None: ...
    def get(self, key: Key) -> Optional[Value]: ...
    def get_with_meta(self, key: Key) -> Optional[tuple[Optional[Value], Timestamp]]: ...
    def range(self, start: Optional[Key], end: Optional[Key]) -> Iterator[tuple[Key, Optional[Value]]]: ...
    def compact_level(self, level: int) -> None: ...
    def flush_memtable(self) -> None: ...
''',
    }
    
    for name, content in interfaces.items():
        path = SRC_DIR / "interfaces" / name
        if not path.exists() or len(path.read_text(encoding="utf-8").strip()) < 50:
            path.write_text(content, encoding="utf-8")
            logging.info("Generated interface: %s", name)


def generate_core_modules() -> None:
    """Generate core module implementations."""
    # config.py
    config_path = SRC_DIR / "core" / "config.py"
    if not config_path.exists() or len(config_path.read_text().strip()) < 50:
        config_path.write_text('''"""Configuration dataclass for LSM Tree."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class LSMConfig:
    """LSM Tree configuration."""
    data_dir: str
    memtable_max_bytes: int = 64 * 1024 * 1024
    wal_flush_every_write: bool = True
    bloom_false_positive_rate: float = 0.01
    compaction_threshold_bytes: int = 256 * 1024 * 1024
    tombstone_retention_seconds: int = 86400
    sstable_max_bytes: int = 64 * 1024 * 1024
    max_levels: int = 6
    wal_file_rotate_bytes: int = 64 * 1024 * 1024
''', encoding="utf-8")
        logging.info("Generated core/config.py")

    # errors.py
    errors_path = SRC_DIR / "core" / "errors.py"
    if not errors_path.exists() or len(errors_path.read_text().strip()) < 50:
        errors_path.write_text('''"""Error hierarchy for LSM Tree."""


class LSMError(Exception):
    """Base exception for LSM Tree errors."""
    pass


class WALCorruptionError(LSMError):
    """WAL file corruption detected."""
    pass


class SSTableError(LSMError):
    """SSTable operation error."""
    pass


class RecoveryError(LSMError):
    """Error during recovery process."""
    pass


class CompactionError(LSMError):
    """Error during compaction."""
    pass
''', encoding="utf-8")
        logging.info("Generated core/errors.py")

    # types.py
    types_path = SRC_DIR / "core" / "types.py"
    if not types_path.exists() or len(types_path.read_text().strip()) < 50:
        types_path.write_text('''"""Common type definitions for LSM Tree."""
from __future__ import annotations
from typing import Optional

Key = bytes
Value = bytes
Timestamp = int
Record = tuple[Key, Optional[Value], Timestamp]
''', encoding="utf-8")
        logging.info("Generated core/types.py")


def generate_test_placeholders() -> None:
    """Generate test file placeholders."""
    test_files = {
        "test_wal.py": '''"""Tests for WAL components."""
import pytest


def test_wal_placeholder():
    """Placeholder for WAL tests."""
    # TODO: Implement WAL tests per sequencing_plan.md
    pass
''',
        "test_memtable.py": '''"""Tests for Memtable components."""
import pytest


def test_memtable_placeholder():
    """Placeholder for Memtable tests."""
    # TODO: Implement Memtable tests per sequencing_plan.md
    pass
''',
        "test_sstable.py": '''"""Tests for SSTable components."""
import pytest


def test_sstable_placeholder():
    """Placeholder for SSTable tests."""
    # TODO: Implement SSTable tests per sequencing_plan.md
    pass
''',
        "test_integration.py": '''"""Integration tests."""
import pytest


def test_integration_placeholder():
    """Placeholder for integration tests."""
    # TODO: Implement integration tests per acceptance criteria
    pass
''',
    }
    
    for name, content in test_files.items():
        path = TESTS_DIR / name
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            logging.info("Generated test: %s", name)


def llm_suggest_tasks(docs: Dict[str, str], cfg: Dict[str, Any]) -> Optional[str]:
    """Use LLM to suggest next implementation tasks."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not (OPENAI_AVAILABLE and api_key):
        logging.info("LLM unavailable (no OpenAI API key or library); skipping suggestions.")
        return None
    
    try:
        client = OpenAI()
        combined = "\n\n".join([f"# {name}\n\n{content}" for name, content in docs.items()])
        system_prompt = load_text(PROMPTS_DIR / "system.md") or "You are a careful Python engineer."
        
        prompt = (
            "Based on the LSM Tree specs below, suggest the next 3 concrete implementation tasks. "
            "Include specific file paths under src/lsm_tree/ and tests under tests/. "
            "Be concise (bullet points).\n\n" + combined
        )
        
        resp = client.chat.completions.create(
            model=cfg.get("model", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=float(cfg.get("temperature", 0.2)),
            max_tokens=int(cfg.get("max_output_tokens", 1200)),
        )
        return resp.choices[0].message.content  # type: ignore
    except Exception as e:
        logging.warning("LLM call failed: %s", e)
        return None


def main() -> int:
    """Main agent entry point."""
    setup_logging()
    logging.info("=" * 60)
    logging.info("LSM Tree AI Agent")
    logging.info("=" * 60)
    
    cfg = load_config()
    logging.info("Config: model=%s, temp=%.2f", cfg.get("model"), cfg.get("temperature", 0.2))
    
    docs = load_docs()
    if not docs:
        logging.warning("No docs found under %s", DOCS_DIR)
    else:
        logging.info("Loaded %d doc files", len(docs))
    
    logging.info("Scaffolding project structure...")
    ensure_scaffold()
    generate_core_modules()
    generate_interface_skeletons(docs)
    generate_test_placeholders()
    
    logging.info("Requesting LLM task suggestions...")
    suggestion = llm_suggest_tasks(docs, cfg)
    if suggestion:
        task_file = LOG_DIR / "next_tasks.txt"
        task_file.write_text(suggestion, encoding="utf-8")
        logging.info("LLM suggestions written to: %s", task_file)
        print("\n" + "=" * 60)
        print("SUGGESTED NEXT TASKS:")
        print("=" * 60)
        print(suggestion)
        print("=" * 60)
    else:
        logging.info("No LLM suggestions (API unavailable or failed)")
    
    logging.info("=" * 60)
    logging.info("Agent complete. Files scaffolded.")
    logging.info("Next: Implement components following docs/sequencing_plan.md")
    logging.info("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
