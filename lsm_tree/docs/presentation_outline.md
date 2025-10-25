# LSM Tree — 15-Minute Presentation Outline

Target duration: ~15 minutes
Audience: Engineers familiar with storage or systems fundamentals

Agenda (time budget)
- 0:00–1:00 — Opening, motivation
- 1:00–4:00 — What is an LSM Tree? The problem it solves
- 4:00–8:00 — Architecture in this project (write/read paths, on-disk layout)
- 8:00–10:00 — API protocol contracts and “Simple” backend
- 10:00–12:00 — Complexity, scope, and limitations
- 12:00–13:30 — Improvements and future backends
- 13:30–15:00 — Demo and closing

1) Motivation: the problem LSM trees solve
- Random-write amplification on disks/SSDs; B-Tree update costs
- Need high-throughput, write-optimized KV store with good range scans
- LSM approach: absorb writes in memory, flush sequentially to disk; merge later (compaction)

2) LSM Tree overview (concept)
- Components: WAL, Memtable, SSTables (leveled), Bloom filters, Indexes, Compaction
- Write path: WAL append → Memtable update → periodic flush to SSTable Level 0
- Read path: check Memtable → consult Bloom + index on SSTables (newest first) → merge by newest timestamp; tombstones respected
- Compaction (leveled): merge/compact L0→L1→… to reduce overlap, purge old tombstones
- Visual: reuse diagram from docs/lsm_requirements.md (Mermaid)

3) Project architecture (as implemented)
- Modules
  - core: config, types, errors, store (orchestration)
  - components: wal, memtable, sstable, bloom, index, catalog, compaction
  - interfaces: Protocols for each component to enable pluggable backends
- Data layout
  - WAL: framed records with CRC; append-only files, rotation on flush/size
  - SSTable: sorted records; sparse index (sampled keys→offset), per-file Bloom, JSON meta+footer
  - Catalog: atomic JSON manifest per level
- Orchestration
  - SimpleLSMStore ensures WAL-before-memtable; range merges memtable + all levels; manual compaction

4) API protocol contracts (reflecting the architecture)
- WAL: WALWriter.append/sync/close; WALReader.__iter__; durable on return if configured
- Memtable: put/delete/get/iter_range/items/size_bytes/clear; sorted iteration contract
- SSTable: Writer.add (sorted), Writer.finalize → meta; Reader.may_contain/get/iter_range
- BloomFilter: add, contains, serialize/deserialize
- Index: find_block_offset(key), load_to_memory
- Compactor: compact(input_meta[], target_level) → output_meta[]; schedule(optional)
- Catalog: list_level/add_sstable/remove_sstables (atomic updates)
- Store: put/delete/get/get_with_meta/range/flush_memtable/compact_level
- References: docs/lsm_api_spec.md for signatures, I/O invariants, persistence formats

5) “Simple” backend implementation
- SimpleWAL: binary frame, magic + lengths + ts + op + CRC32; skip partial frames on replay; optional fsync per write
- SimpleMemtable: SortedDict-backed; stores (value|tombstone, ts); tracks approximate size
- SimpleSSTableWriter/Reader: record framing, sparse index (every N records), per-file Bloom; JSON meta prefix + serialized Bloom in .meta
- SimpleBloomFilter: bit-array, SHA256-based k-hash; fixed m,k from expected n and fpr
- SimpleSSTableCatalog: per-level lists in JSON; atomic write via temp+rename; thread-safe
- SimpleCompactor: k-way merge of iterators; newest ts wins; drops old tombstones beyond retention; splits outputs by size budget
- SimpleLSMStore: orchestrates; recovers from WAL on startup; manual compaction; per-call readers opened/closed

6) Big-O costs (major operations)
- put/delete: O(1) amortized to WAL append + memtable update; flush is O(n) for n memtable items
- get (point): O(1) memtable + per-SSTable O(log I) index seek + small local scan; with Bloom, expected few SSTables; worst-case sum over levels
- range(start,end): O(T + R) where T = total keys examined across memtable+SSTables intersecting range; merge cost linear in emitted records R
- compaction: O(K log K) merge of total K input records; output write linear in K
- bloom: add/contains O(k) ≈ O(1); index lookup O(log I)
- catalog ops: O(1) per add/remove; list_level O(L) to copy list

7) Scope and limitations
- LSM scope (general)
  - Optimized for high write throughput; reads may touch multiple SSTables until compaction
  - Deletes are tombstones until compacted; space/time trade-offs
- “Simple” backend limitations (performance/operational)
  - Reader lifecycle: opens .meta/.data per call; no persistent caches or mmaps → extra I/O
  - Sparse index: coarse sampling; in-block linear scans can be non-trivial on large blocks
  - No background compaction scheduler; manual compaction only
  - No block cache/page cache hints; no compression; no checksum at SSTable file level (only per WAL frame and implicit OS correctness)
  - Catalog is JSON; multi-writer scaling limited; no crash-safe multi-update transactions beyond atomic rename
  - Memtable uses SortedDict (Python-level overhead); GC and object allocation overheads
  - Global store lock around flush/compaction critical regions → reduced concurrency

8) Improvements and alternate backends
- Near-term improvements
  - Persistent reader pool; mmap data; keep Bloom and index resident; LRU block cache
  - Denser/two-level index (fence pointers per block + binary search inside block)
  - Asynchronous/background compaction with rate limiting; compaction picking policies
  - WAL batching and group commit; checksummed file-level manifest; periodic snapshots
  - Compression (block-level), checksums for SSTable segments
  - Concurrent read/write locks; finer-grained locking; metrics and tracing
- Alternate backends (via interfaces)
  - SSTable via SQLite/LMDB (B-Tree on-disk), RocksDB-compatible table formats, Zstandard-compressed blocks
  - Counting Bloom or quotient filters; tiered vs leveled compaction strategies
  - Catalog via SQLite (transactional) or etcd (if distributed later)
  - WAL via memory-mapped ring buffer or networked append service

9) Demo plan (scripted)
- Goal: show put/get/delete, flush, compaction, range
- Steps
  1) Initialize store with small memtable and SSTable sizes for quick flush/compact
  2) put/delete a few keys; show get and get_with_meta
  3) Force flush; inspect generated files; perform a point read that hits SSTable
  4) Insert overlapping updates; run compact_level(0); verify dedup and tombstone purge policy
  5) Run a range query and print results
- Example snippet

```python path=null start=null
from lsm_tree.core.config import LSMConfig
from lsm_tree.core.store import SimpleLSMStore

cfg = LSMConfig(
    data_dir="/tmp/lsm_demo",
    memtable_max_bytes=1024,  # force quick flush
    sstable_max_bytes=4096,
    wal_flush_every_write=True,
)

with SimpleLSMStore(cfg) as db:
    db.put(b"a", b"1")
    db.put(b"b", b"2")
    db.delete(b"a")
    print("get(b):", db.get(b"b"))

    db.flush_memtable()  # force SSTable

    db.put(b"a", b"3")
    print("get(a):", db.get(b"a"))

    print("range(a,z):", list(db.range(b"a", b"z")))
    db.compact_level(0)
    print("post-compact range:", list(db.range(b"a", b"z")))
```

- Optional: run tests/benchmarks to complement demo
  - pytest -q
  - Highlight performance test harness in tests/performance/test_benchmarks.py

10) Closing remarks
- Key takeaways: write-optimized design; modular interfaces enable experimentation; current backend is educational baseline
- Next steps: caching/index improvements, background compaction, compressed blocks, transactional catalog; explore alternate backends
- Q&A
