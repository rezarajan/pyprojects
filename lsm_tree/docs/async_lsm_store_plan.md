# AsyncLSMStore — Implementation Plan

Objective
- Introduce AsyncLSMStore that provides WAL-first, non-blocking writes and non-blocking compaction scheduling.
- Keep SimpleLSMStore synchronous and minimal (baseline), as per last committed version.

Deliverables
1) New module `src/lsm_tree/core/async_store.py` with `AsyncLSMStore`:
   - Async WAL-first writes with background applier (from current async SimpleLSMStore code)
   - Optional fencing via `wait_for_seq(seq, timeout)`
   - Same read/flush/compaction APIs as SimpleLSMStore
2) Revert `src/lsm_tree/core/store.py` to synchronous baseline.
3) Keep `LSMConfig` additions (apply queue config) for AsyncLSMStore; SimpleLSMStore ignores them.

Scope
- Writes: WAL append returns immediately; memtable apply is try-lock or queued.
- Flush: remains synchronous (triggered under lock) in both stores.
- Compaction: keep synchronous in Simple; plan separate PR to add background coordinator to Async.

Steps
- [x] Document minimal async design (docs/simple_async_writes.md)
- [x] Implement async in SimpleLSMStore (temporary to prove correctness)
- [x] Extract async version → `AsyncLSMStore` in `core/async_store.py`
- [x] Revert `SimpleLSMStore` in `core/store.py` to synchronous baseline
- [ ] (Next) Add non-blocking compaction scheduler to `AsyncLSMStore`:
      - API: schedule_compaction(level) → Job; compact_level(level, wait=True/False)
      - Coordinator thread + bounded queue; catalog swap under lock, I/O outside

Compatibility
- Demo and tests continue to import `SimpleLSMStore` (synchronous semantics)
- Advanced users can import `AsyncLSMStore` for high-throughput workloads

Testing Plan
- Unit: async write returns before memtable applies; `wait_for_seq` fences
- Integration: sustained throughput during flush/compaction
- Recovery: restart replays WAL superset into empty memtable

Risks & Mitigations
- Queue saturation: bounded queue + short fallback lock timeout + final blocking enqueue
- Read-your-write: optional `wait_for_seq` to ensure visibility
- Shutdown: sentinel + join with timeout; WAL closed safely

Timeline
- This PR: create AsyncLSMStore, revert SimpleLSMStore
- Next PR: add non-blocking compaction scheduler to AsyncLSMStore
