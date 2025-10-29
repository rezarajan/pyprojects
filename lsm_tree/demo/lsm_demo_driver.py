#!/usr/bin/env python3
"""LSM Tree Live Demo Driver

Runs a configurable workload against the LSM store and samples metrics
for visualization.

Usage:
    python demo/lsm_demo_driver.py --write-rate 5000 --duration-seconds 60
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import time
from collections import defaultdict
from pathlib import Path

from lsm_tree.core.async_store import AsyncLSMStore
from lsm_tree.core.config import LSMConfig
from lsm_tree.core.store import SimpleLSMStore


def run_demo(args: argparse.Namespace) -> None:
    """Run the demo workload and collect metrics."""
    cfg = LSMConfig(
        data_dir=args.data_dir,
        memtable_max_bytes=args.memtable_max_bytes,
        sstable_max_bytes=args.sstable_max_bytes,
        bloom_false_positive_rate=args.bloom_fpr,
        max_levels=args.max_levels,
        wal_flush_every_write=args.wal_flush_every_write,
        tombstone_retention_seconds=args.tombstone_retention_seconds,
    )

    key_space = args.key_space_size
    val = b"x" * args.value_size_bytes

    counters = defaultdict(int)
    event_log = []  # Track flush and compaction events
    last_sample = time.time()
    next_sample = last_sample + args.sample_ms / 1000.0
    prev_level_counts = [0] * args.max_levels
    
    # Compaction thresholds per level (when level N reaches threshold, compact to N+1)
    compaction_thresholds = {
        0: 4,   # L0 → L1 when L0 has 4+ SSTables
        1: 6,   # L1 → L2 when L1 has 6+ SSTables
        2: 8,   # L2 → L3 when L2 has 8+ SSTables
        3: 10,  # L3 → L4 when L3 has 10+ SSTables
        4: 12,  # L4 → L5 when L4 has 12+ SSTables
    }

    print(f"Starting LSM demo for {args.duration_seconds}s...")
    print(f"Store type: {'Async' if args.async_compaction else 'Sync'}")
    print(f"Config: memtable={args.memtable_max_bytes}, sstable={args.sstable_max_bytes}")
    print(f"Workload: write={args.write_rate}/s, read={args.read_rate}/s, delete={args.delete_rate}/s")
    print(f"Compaction thresholds: {compaction_thresholds}")
    print(f"Output: {args.out_csv}")

    # Choose store type based on flag
    store_class = AsyncLSMStore if args.async_compaction else SimpleLSMStore
    
    with store_class(cfg) as db, open(args.out_csv, "w", newline="") as f:
        w = csv.writer(f)
        header = [
            "ts_ms",
            "ops_total",
            "ops_put",
            "ops_get",
            "ops_del",
            "memtable_bytes",
        ] + [f"sst_count_L{i}" for i in range(args.max_levels)] + [
            f"sst_bytes_L{i}" for i in range(args.max_levels)
        ] + ["event"]
        w.writerow(header)

        t_start = time.time()
        t_end = t_start + args.duration_seconds
        tick_count = 0

        while time.time() < t_end:
            # Emit operations at target rates
            maybe_do(args.write_rate, lambda: do_put(db, key_space, val, counters))
            maybe_do(args.read_rate, lambda: do_get(db, key_space, counters))
            maybe_do(args.delete_rate, lambda: do_del(db, key_space, counters))

            now = time.time()
            if now >= next_sample:
                elapsed = now - t_start
                
                # Get current level counts
                current_level_counts = [len(db._catalog.list_level(i)) for i in range(args.max_levels)]
                event = ""
                
                # Detect flush (L0 count increased)
                if tick_count > 0 and current_level_counts[0] > prev_level_counts[0]:
                    event = "flush"
                    print(f"  [{elapsed:.1f}s] FLUSH: Memtable → L0")
                
                # Check each level for compaction (L0-L4)
                for level in range(args.max_levels - 1):  # Don't compact L5 (last level)
                    level_count = current_level_counts[level]
                    threshold = compaction_thresholds.get(level)
                    
                    if threshold and level_count >= threshold:
                        try:
                            print(f"  [{elapsed:.1f}s] COMPACTION: L{level} → L{level+1} (L{level} count={level_count})")
                            
                            if args.async_compaction:
                                # Schedule background compaction (non-blocking)
                                job_id = db.schedule_compaction(level, wait=False)
                                event = f"compact_L{level}_L{level+1}_scheduled"
                                print(f"    Scheduled async compaction job {job_id}")
                            else:
                                # Synchronous compaction (blocks)
                                db.compact_level(level)
                                event = f"compact_L{level}_L{level+1}"
                            
                            # Update counts after compaction
                            current_level_counts = [len(db._catalog.list_level(i)) for i in range(args.max_levels)]
                        except Exception as e:
                            print(f"  Compaction L{level}→L{level+1} failed: {e}")
                
                prev_level_counts = current_level_counts
                
                row = sample_row(db, counters, now, args.max_levels, event)
                w.writerow(row)
                f.flush()  # Ensure data is written for live plotting
                counters.clear()
                next_sample = now + args.sample_ms / 1000.0
                tick_count += 1

                # Progress indicator
                if tick_count % 10 == 0:
                    print(f"  {elapsed:.1f}s / {args.duration_seconds}s")

            # Small sleep to avoid spinning
            time.sleep(0.001)

    print(f"Demo complete. Metrics written to {args.out_csv}")


def maybe_do(rate_per_sec: float, fn: callable) -> None:
    """Probabilistically execute fn based on rate_per_sec."""
    if rate_per_sec <= 0:
        return
    # Probability of 1 op per tick at ~1 KHz pacing
    if random.random() < min(1.0, rate_per_sec / 1000.0):
        fn()


def rand_key(key_space: int) -> bytes:
    """Generate a random key."""
    return str(random.randrange(key_space)).encode()


def do_put(db: SimpleLSMStore, key_space: int, val: bytes, counters: dict) -> None:
    """Perform a put operation."""
    db.put(rand_key(key_space), val)
    counters["put"] += 1
    counters["total"] += 1


def do_get(db: SimpleLSMStore, key_space: int, counters: dict) -> None:
    """Perform a get operation."""
    _ = db.get(rand_key(key_space))
    counters["get"] += 1
    counters["total"] += 1


def do_del(db: SimpleLSMStore, key_space: int, counters: dict) -> None:
    """Perform a delete operation."""
    db.delete(rand_key(key_space))
    counters["del"] += 1
    counters["total"] += 1


def sample_row(
    db: SimpleLSMStore, counters: dict, now: float, max_levels: int, event: str = ""
) -> list:
    """Sample current metrics from the store."""
    ts_ms = int(now * 1000)
    # Access internals for demo metrics (read-only)
    mem_bytes = db._memtable.size_bytes()
    counts = []
    sizes = []
    for level in range(max_levels):
        metas = db._catalog.list_level(level)
        counts.append(len(metas))
        sizes.append(sum(m.get("data_size", 0) for m in metas))
    return [
        ts_ms,
        counters.get("total", 0),
        counters.get("put", 0),
        counters.get("get", 0),
        counters.get("del", 0),
        mem_bytes,
        *counts,
        *sizes,
        event,
    ]


def main() -> None:
    """Parse arguments and run demo."""
    p = argparse.ArgumentParser(description="LSM Tree live demo driver")

    # Engine configuration
    p.add_argument("--data-dir", default="/tmp/lsm_demo", help="Data directory")
    p.add_argument(
        "--async-compaction",
        action="store_true",
        help="Use AsyncLSMStore with background compaction",
    )
    p.add_argument(
        "--memtable-max-bytes",
        type=int,
        default=1_000_000,
        help="Memtable size threshold",
    )
    p.add_argument(
        "--sstable-max-bytes", type=int, default=8_000_000, help="SSTable size limit"
    )
    p.add_argument(
        "--bloom-fpr", type=float, default=0.01, help="Bloom filter false positive rate"
    )
    p.add_argument("--max-levels", type=int, default=6, help="Max LSM levels")
    p.add_argument(
        "--wal-flush-every-write",
        action="store_true",
        help="Fsync after every write",
    )
    p.add_argument(
        "--tombstone-retention-seconds",
        type=int,
        default=86400,
        help="Tombstone retention in seconds",
    )

    # Workload configuration
    p.add_argument(
        "--duration-seconds", type=int, default=60, help="Duration of the demo"
    )
    p.add_argument("--write-rate", type=float, default=2000, help="Write ops/sec")
    p.add_argument("--read-rate", type=float, default=0, help="Read ops/sec")
    p.add_argument("--delete-rate", type=float, default=0, help="Delete ops/sec")
    p.add_argument(
        "--key-space-size", type=int, default=100000, help="Number of distinct keys"
    )
    p.add_argument(
        "--value-size-bytes", type=int, default=128, help="Size of values in bytes"
    )

    # Sampling configuration
    p.add_argument(
        "--sample-ms", type=int, default=500, help="Sampling interval in ms"
    )
    p.add_argument(
        "--out-csv", default="/tmp/lsm_metrics.csv", help="Output CSV file"
    )

    args = p.parse_args()
    os.makedirs(args.data_dir, exist_ok=True)

    run_demo(args)


if __name__ == "__main__":
    main()
