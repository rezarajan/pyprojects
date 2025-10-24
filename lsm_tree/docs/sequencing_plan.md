LSM tree minimal sequencing plan (to acceptance)

0) Bootstrap
- Create package layout: lsm/ {config.py, errors.py, types.py, wal.py, memtable.py, sstable.py, bloom.py, index.py, catalog.py, compaction.py, store.py}
- Implement types: Key/Value/Timestamp/Record; LSMConfig; exceptions.
- Init data_dir; subdirs: wal/, sst/, meta/.

1) WAL (durable write path)
- Implement SimpleWAL: append(key, val|None, ts), sync, iterate; length-prefixed frames + crc32; rotate by size.
- Tests: partial-record at EOF skipped; durability across reopen; ordering preserved.
- DoD: After put returns + process restart → replay yields same records.

2) Memtable (in-memory sorted)
- Implement SimpleMemtable: put/delete/get/iter_range/items/size_bytes/clear. Use SortedDict or list+bisect for minimal.
- Tests: in-order iteration; tombstone handling; size threshold check.
- DoD: Correct most-recent value by ts; range returns key-ordered items incl. tombstones.

3) SSTable writer + minimal bloom/index + catalog (Level 0 only)
- Writer: add(sorted), finalize() writes data (.data), meta/index/filter (.meta). Bloom: fixed m,k by expected n and fpr; Index: sample per-block first key → offset.
- Catalog: JSON manifest per level with atomic os.replace; register new SSTable.
- Tests: writer/read-back of serialized keys; meta min/max keys; manifest atomicity.
- DoD: Flush Memtable to single SSTable with bloom+index; files immutable.

4) SSTable reader
- may_contain via bloom; get via index seek + local scan; iter_range(start,end).
- Tests: may_contain false ⇒ get None; get returns exact (value, ts); range over overlaps of min/max.
- DoD: Point lookups and ranges from one SSTable pass.

5) LSMStore core API (no background yet)
- put/delete: assign monotonic ts, WAL.append → Memtable.{put|delete}; optional per-write fsync from config.
- get/range: check Memtable, then Level 0 SSTables newest→oldest using bloom/index; merge by highest ts, drop tombstones.
- flush_memtable: if memtable_max_bytes exceeded, rotate to new Memtable and flush old to L0 SSTable writer.
- Tests: correctness of get/range with overlapping memtable+L0; tombstone masks; manual flush.
- DoD: Public API usable; acceptance 2–4 satisfied for single level.

6) Recovery path
- On open: scan WALs newest→oldest, replay complete frames; rebuild Memtable; load catalog.
- Tests: inject partial WAL frame; verify skipped; acknowledge writes reappear after restart.
- DoD: Acceptance 1 and 6 satisfied.

7) Manual compaction (L0→L1 minimal)
- Merge iterator across selected L0 SSTables: by key, keep max ts; drop tombstones older than retention; write new L1 SSTables; atomic catalog swap; remove inputs.
- Locking: per-level write lock; readers rely on immutable files + catalog swap.
- Tests: duplicates removed, tombstones purged by policy; interrupted compaction leaves temps cleaned on next open.
- DoD: Acceptance 5 satisfied; readers unaffected during compaction.

8) Bloom accuracy validation
- Measure FP rate on sample dataset; assert ≤ 2× configured rate.
- DoD: Acceptance 7 satisfied.

9) Minimal benchmarks and tooling
- Microbench: sequential inserts vs naive B-Tree baseline (e.g., Python dict on disk or sqlite btree), report throughput; range scan O(n) sanity.
- Admin helpers: list levels, sstables, active WAL.

Milestones and integration order
- M1: Types/Config/Errors + WAL (1) + Memtable (2) [unit tests green]
- M2: SSTable Writer+Catalog (3) + Reader (4) [flush/read integration]
- M3: LSMStore API (5) + Recovery (6) [acceptance 1–4,6]
- M4: Compaction (7) [acceptance 5] + Bloom validation (8)
- M5: Benchmarks/ops (9)

Verification matrix (acceptance → tests)
- Durability (1): WAL replay tests + restart integration.
- Consistency (2): multi-write same key with ts ordering across memtable/L0/L1.
- Read correctness (3): tombstone behavior, latest ts wins, range excludes deleted.
- Performance (4): baseline scripts; document results.
- Compaction validity (5): no dup keys post-compact; expired tombstones gone.
- Recovery (6): out-of-order WAL segments, partial frames.
- Bloom accuracy (7): measured FP ≤ 2× configured.

Out-of-scope now
- Background compaction scheduler, compression, LRU index cache; add after M4 if time.
