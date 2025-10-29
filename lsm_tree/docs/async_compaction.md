# Async Compaction Design

## Overview

The `AsyncLSMStore` extends `SimpleLSMStore` to provide non-blocking background compaction. This allows write operations to continue without being stalled by long-running compaction operations.

## Architecture

### Design Principles

1. **Inheritance-based**: `AsyncLSMStore` extends `SimpleLSMStore`, inheriting all core functionality
2. **Background worker**: Single daemon thread processes compaction jobs from a queue
3. **Per-level locking**: Only one compaction can run per level at a time
4. **Brief critical sections**: Main lock (`_lock`) is held only for catalog updates, not I/O
5. **Job tracking**: All compaction jobs are tracked with status and can be queried

### Components

#### Compaction Job Queue
- Unbounded `queue.Queue` holds pending `CompactionJob` objects
- Jobs processed sequentially by background worker thread
- Jobs can be scheduled with `schedule_compaction(level, wait=False)`

#### Per-Level Locking
- Each level has its own `threading.Lock` in `_level_locks` dict
- Prevents concurrent compactions on the same level
- If level is locked, job is requeued with small delay

#### Job Status Tracking
- `_active_jobs`: Dict of jobs currently pending or running
- `_completed_jobs`: Dict of finished jobs (success or failure)
- `CompactionStatus` enum: PENDING, RUNNING, COMPLETED, FAILED

#### Background Worker Thread
- Daemon thread runs `_compaction_worker()` method
- Polls queue every 100ms for new jobs
- Exits cleanly on shutdown signal (None in queue)

## Key Methods

### Public API

```python
# Schedule a compaction job
job_id = store.schedule_compaction(level, wait=False)

# Wait for a specific job to complete
success = store.wait_for_compaction(job_id, timeout=5.0)

# Query job status
job = store.get_compaction_status(job_id)
if job.status == CompactionStatus.COMPLETED:
    print(f"Compaction took {job.completed_at - job.started_at:.2f}s")

# List pending jobs
pending = store.list_pending_compactions()
```

### Backward Compatibility

The synchronous `compact_level()` method is preserved for compatibility:

```python
# Equivalent to schedule_compaction(level, wait=True)
store.compact_level(level)
```

## Concurrency Control

### Critical Section Pattern

Compaction I/O (reading/writing SSTables) happens **outside** the main lock:

```python
# 1. Read catalog (fast, under lock)
input_tables = self._catalog.list_level(level)

# 2. Run compaction (slow, NO LOCK)
output_metas = self._compactor.compact(input_tables, level + 1)

# 3. Update catalog (fast, under lock)
with self._lock:
    self._catalog.remove_sstables(input_tables)
    for meta in output_metas:
        self._catalog.add_sstable(level + 1, meta)

# 4. Delete old files (outside lock)
for meta in input_tables:
    Path(meta["data_path"]).unlink()
```

### Race Conditions

**Known issue**: Concurrent reads may encounter `FileNotFoundError` if compaction deletes an SSTable mid-read. This is expected behavior in the current implementation.

**Mitigation options** (not yet implemented):
1. Reference counting on SSTables (delay deletion until no readers)
2. MVCC/snapshot isolation (readers see consistent snapshot)
3. Retry logic in read path

## Usage Examples

### Basic Usage

```python
from lsm_tree.core.async_store import AsyncLSMStore
from lsm_tree.core.config import LSMConfig

config = LSMConfig(data_dir="/tmp/lsm_data")
store = AsyncLSMStore(config)

# Writes never block on compaction
for i in range(10000):
    store.put(f"key{i}".encode(), f"value{i}".encode())

# Schedule background compaction
job_id = store.schedule_compaction(0)

# Continue writing while compaction runs
for i in range(10000, 20000):
    store.put(f"key{i}".encode(), f"value{i}".encode())

# Wait for compaction before shutdown
store.wait_for_compaction(job_id)
store.close()
```

### With Demo Driver

```bash
# Synchronous compaction (blocks writes)
python demo/lsm_demo_driver.py --duration-seconds 60 --write-rate 5000

# Async compaction (non-blocking)
python demo/lsm_demo_driver.py --async-compaction --duration-seconds 60 --write-rate 5000
```

## Performance Characteristics

### Synchronous Compaction (`SimpleLSMStore`)
- **Writes**: Blocked during compaction (can take seconds)
- **Latency**: Spikes during compaction
- **Throughput**: Drops to zero during compaction

### Async Compaction (`AsyncLSMStore`)
- **Writes**: Never blocked by compaction
- **Latency**: Consistent, no spikes
- **Throughput**: Sustained even during compaction

### Tradeoffs

**Pros**:
- Predictable write latency
- Higher sustained throughput
- Better for latency-sensitive workloads

**Cons**:
- More complex concurrency model
- Potential for transient read errors (FileNotFoundError)
- Memory overhead from job tracking

## Implementation Details

### Shutdown Process

```python
def close(self):
    # 1. Set shutdown flag
    self._shutdown = True
    
    # 2. Send shutdown signal to worker
    self._compaction_queue.put(None)
    
    # 3. Wait for worker to finish (5s timeout)
    self._worker_thread.join(timeout=5.0)
    
    # 4. Close parent (SimpleLSMStore)
    super().close()
```

### Error Handling

Compaction failures are captured and stored in the job status:

```python
try:
    output_metas = self._compactor.compact(input_tables, level + 1)
except Exception as e:
    job.status = CompactionStatus.FAILED
    job.error = e
    self._completed_jobs[job.job_id] = job
```

## Testing

Comprehensive test suite in `tests/unit/test_async_store.py`:

- Initialization and shutdown
- Job scheduling and tracking
- Non-blocking writes during compaction
- Multiple concurrent jobs (different levels)
- Per-level compaction gating
- Backward compatibility with `compact_level()`
- Error handling and edge cases

Run tests:
```bash
uv run pytest tests/unit/test_async_store.py -v
```

## Future Enhancements

1. **Reference Counting**: Delay SSTable deletion until all readers finish
2. **MVCC**: Snapshot isolation for consistent reads
3. **Parallel Compaction**: Multiple workers for different levels
4. **Priority Queue**: Prioritize critical compactions
5. **Compaction Metrics**: Track job duration, throughput, I/O stats
6. **Adaptive Scheduling**: Automatically trigger compactions based on level sizes
