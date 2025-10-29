# SimpleLSMStore — Asynchronous WAL-first Writes (Minimal Design)

Goal
- Ensure put/delete never block on memtable/flush/compaction.
- After WAL append succeeds, the operation is considered recorded (durable).
- Keep implementation simple and compatible with the existing Simple backend.

Principles
- Durability is provided by WAL append + fsync policy.
- Memtable application is best-effort and may lag; recovery replays the WAL.
- Optional: expose a fence (WAL sequence) for callers who need read-your-write.

Minimal Design (no major refactor)
1) Separate timestamp contention from the memtable/catalog lock
- Use a dedicated `_timestamp_lock` (already applied) so timestamp generation never contends with flush/compaction.

2) Try-lock memtable application, else enqueue
- On put/delete:
  - Get timestamp
  - Append to WAL (durable)
  - Try to acquire `_lock` with a non-blocking attempt
    - If acquired: apply to memtable, trigger flush if needed, release lock
    - If not acquired: enqueue the mutation to a thread-safe queue and return immediately

3) Background applier thread
- A single daemon thread drains the queue and applies queued mutations when `_lock` becomes available.
- This preserves WAL order in the memtable on best-effort basis; strict order isn’t required for correctness because timestamps resolve conflicts.

4) Optional fence for read-your-write
- WAL append returns a sequence/offset; expose `wait_for_seq(seq)` which blocks until the applier has advanced to at least `seq`.
- Default: non-blocking semantics; clients that need linearizability can opt in.

Write Path (Resulting Behavior)
- Caller latency = WAL append + (very short) timestamp cost.
- No waiting for memtable/flush/compaction.
- If memtable is momentarily unavailable (flush, compaction), the op is queued for the applier.

Read Path Implication
- A subsequent `get()` might not see the most recent write if it is still in the apply queue.
- If the client needs read-your-write, call `wait_for_seq(wal_seq)` or do a `get_with_meta()` after the fence.

Crash Consistency
- WAL has a superset of applied mutations; on restart, recovery replays missing entries into a fresh memtable.

Bounded Queue and Backpressure (simple)
- Use a bounded queue (configurable, e.g., 100k entries).
- If the queue is full, block the writer until space frees, or (preferable) perform a synchronous apply by waiting for `_lock` briefly (configurable short wait) to avoid unbounded memory growth.

Pseudocode
```python path=null start=null
class SimpleLSMStore:
    def __init__(...):
        self._apply_queue: queue.Queue[Record] = queue.Queue(maxsize=config.apply_queue_max)
        self._applier = Thread(target=self._apply_worker, daemon=True)
        self._last_applied_seq = 0  # WAL sequence watermark
        self._applier.start()

    def put(self, key: Key, value: Value) -> int:
        ts = self._next_ts()                     # uses _timestamp_lock only
        seq = self._wal.append(key, value, ts)   # durable on return (per config)
        if self._try_apply_memtable((key, value, ts, seq)):
            return seq
        self._enqueue_or_sync((key, value, ts, seq))
        return seq

    def delete(self, key: Key) -> int:
        ts = self._next_ts()
        seq = self._wal.append(key, None, ts)
        if self._try_apply_memtable((key, None, ts, seq)):
            return seq
        self._enqueue_or_sync((key, None, ts, seq))
        return seq

    def _try_apply_memtable(self, rec) -> bool:
        if self._lock.acquire(blocking=False):
            try:
                key, val, ts, seq = rec
                if val is not None:
                    self._memtable.put(key, val, ts)
                else:
                    self._memtable.delete(key, ts)
                if self._memtable.size_bytes() > self.config.memtable_max_bytes:
                    self._flush_memtable_locked()
                self._last_applied_seq = max(self._last_applied_seq, seq)
                return True
            finally:
                self._lock.release()
        return False

    def _enqueue_or_sync(self, rec) -> None:
        try:
            self._apply_queue.put_nowait(rec)
        except queue.Full:
            # Fallback: short wait to acquire and apply synchronously
            acquired = self._lock.acquire(timeout=0.005)
            if acquired:
                try:
                    self._try_apply_memtable(rec)
                finally:
                    self._lock.release()
            else:
                # As a last resort, block on queue to preserve durability→apply progress
                self._apply_queue.put(rec)

    def _apply_worker(self):
        while True:
            rec = self._apply_queue.get()
            if rec is None:  # shutdown
                break
            # Apply with normal locking; retries if lock is busy
            applied = self._try_apply_memtable(rec)
            if not applied:
                # If still busy, requeue with small sleep to avoid spin
                time.sleep(0.001)
                self._apply_queue.put(rec)

    def wait_for_seq(self, seq: int, timeout: float | None = None) -> bool:
        """Wait until memtable has applied up to WAL sequence `seq`."""
        deadline = time.time() + (timeout or 0)
        while True:
            if self._last_applied_seq >= seq:
                return True
            if timeout is not None and time.time() >= deadline:
                return False
            time.sleep(0.001)
```

API Notes
- `put/delete` return WAL sequence numbers; callers may ignore or use them for fencing.
- `wait_for_seq` provides optional read-your-write semantics.

Complexity vs. Simplicity
- No double-buffered memtables, no immutables required.
- Single background applier thread + small queue.
- Writes never block on memtable or flush, only on WAL append and (rarely) full queue fallback.

Configuration (add to LSMConfig)
- `apply_queue_max: int = 100_000` (default)
- `apply_lock_timeout_ms: int = 5` (try-lock timeout in fallback path)

Behavioral Summary
- High throughput maintained: caller returns after WAL append.
- Minimal extra code and no invasive refactor.
- Correct under failures due to WAL-first durability; recovery fills any lag.
- Optional linearizability via sequence fence.

Compatibility & Limitations
- Reads might briefly miss most recent writes unless `wait_for_seq` is used.
- Backpressure only if apply queue is saturated; fallback path softens this.
- Timestamp order is preserved; last-writer-wins by timestamp in compaction.

Testing Checklist
- Writes don’t stall during explicit flush/compaction
- Recovery replay applies any queued-but-unapplied records
- `wait_for_seq` unblocks after background applier catches up
- Queue full conditions handled without deadlocks
