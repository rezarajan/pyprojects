# LSM Tree — Demo Visualization Plan

Purpose
- Provide a reproducible way to visualize runtime behavior during a demo.
- Plots: (1) throughput over time, (2) memtable space usage over time, (3) SSTable counts per level (and optionally total bytes per level).
- Inputs must be tunable (workload shape and engine knobs) so the audience can see cause → effect.

What to visualize
- Throughput
  - Write ops/sec and Read ops/sec in 1s intervals (or sliding window).
  - Optional: Delete ops/sec.
- Memtable space
  - Memtable size in bytes over time via `memtable.size_bytes()`.
  - Annotate flush events.
- SSTables and levels
  - Count of SSTables per level over time (L0..N).
  - Optional: bytes per level (sum of `meta.data_size`).
  - Mark compaction events (L0→L1→...).

Data collection strategy
- Driver program periodically samples the store and records CSV rows: `ts_ms, ops_total, ops_put, ops_get, ops_del, memtable_bytes, sstable_count_L0, ..., sstable_count_Ln, bytes_L0, ..., bytes_Ln`.
- Sampling interval: 200–1000 ms (trade-off between smoothness and overhead).
- For demo simplicity, access internals (read-only) on the running store:
  - Memtable size: `store._memtable.size_bytes()`
  - Per-level SSTables: `store._catalog.list_level(i)`
- Workload loop emits operations at a controlled rate; counters are incremented per op and reset each sampling tick to compute ops/sec.

Recommended workflow
- Phase A: Run a workload + sampler → write CSV.
- Phase B: Render live charts during the run or generate a static HTML/PNG after.

Tunable inputs (CLI for the driver)
- Engine knobs (wired to LSMConfig)
  - `--data-dir`
  - `--async-compaction` (use AsyncLSMStore with background compaction)
  - `--memtable-max-bytes`
  - `--sstable-max-bytes`
  - `--bloom-fpr`
  - `--max-levels`
  - `--wal-flush-every-write`
  - `--tombstone-retention-seconds`
- Workload knobs
  - `--duration-seconds`
  - `--write-rate` (ops/sec target)
  - `--read-rate` (ops/sec target)
  - `--delete-rate` (ops/sec target)
  - `--key-space-size` (e.g., 1e6 distinct keys)
  - `--value-size-bytes` (payload size)
  - `--key-dist` = uniform|zipf, `--zipf-skew`
  - `--range-reads` percent and span (optional)
- Visualization knobs
  - `--sample-ms` (sampling interval)
  - `--live` (render live) or `--out-csv`, `--out-html/png`

Driver skeleton (illustrative)
```python path=null start=null
import argparse, csv, os, random, time
from collections import defaultdict
from lsm_tree.core.config import LSMConfig
from lsm_tree.core.store import SimpleLSMStore

# Simplified token-bucket loop + periodic sampler

def run_demo(args):
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
    last_sample = time.time()
    next_sample = last_sample + args.sample_ms / 1000.0

    with SimpleLSMStore(cfg) as db, open(args.out_csv, "w", newline="") as f:
        w = csv.writer(f)
        header = [
            "ts_ms","ops_total","ops_put","ops_get","ops_del","memtable_bytes",
        ] + [f"sst_count_L{i}" for i in range(args.max_levels)] \
          + [f"sst_bytes_L{i}" for i in range(args.max_levels)]
        w.writerow(header)

        t_end = time.time() + args.duration_seconds
        while time.time() < t_end:
            # Emit operations at target rates (very rough pacing)
            maybe_do(args.write_rate, lambda: do_put(db, key_space, val, counters))
            maybe_do(args.read_rate,  lambda: do_get(db, key_space, counters))
            maybe_do(args.delete_rate,lambda: do_del(db, key_space, counters))

            now = time.time()
            if now >= next_sample:
                row = sample_row(db, counters, now, args.max_levels)
                w.writerow(row)
                counters.clear()
                next_sample = now + args.sample_ms / 1000.0


def maybe_do(rate_per_sec, fn):
    if rate_per_sec <= 0: return
    # Probability of 1 op per tick at 1 KHz pacing; adjust as needed
    if random.random() < min(1.0, rate_per_sec / 1000.0):
        fn()


def rand_key(key_space):
    return str(random.randrange(key_space)).encode()


def do_put(db, key_space, val, counters):
    db.put(rand_key(key_space), val)
    counters["put"] += 1
    counters["total"] += 1


def do_get(db, key_space, counters):
    _ = db.get(rand_key(key_space))
    counters["get"] += 1
    counters["total"] += 1


def do_del(db, key_space, counters):
    db.delete(rand_key(key_space))
    counters["del"] += 1
    counters["total"] += 1


def sample_row(db, counters, now, max_levels):
    ts_ms = int(now * 1000)
    # Internals are used read-only for demo metrics
    mem_bytes = db._memtable.size_bytes()
    counts = []
    sizes = []
    for L in range(max_levels):
        metas = db._catalog.list_level(L)
        counts.append(len(metas))
        sizes.append(sum(m.get("data_size", 0) for m in metas))
    return [
        ts_ms,
        counters.get("total",0), counters.get("put",0), counters.get("get",0), counters.get("del",0),
        mem_bytes,
        *counts,
        *sizes,
    ]

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", default="/tmp/lsm_demo")
    p.add_argument("--duration-seconds", type=int, default=60)
    p.add_argument("--write-rate", type=float, default=2000)
    p.add_argument("--read-rate", type=float, default=0)
    p.add_argument("--delete-rate", type=float, default=0)
    p.add_argument("--key-space-size", type=int, default=100000)
    p.add_argument("--value-size-bytes", type=int, default=128)
    p.add_argument("--memtable-max-bytes", type=int, default=1_000_000)
    p.add_argument("--sstable-max-bytes", type=int, default=8_000_000)
    p.add_argument("--bloom-fpr", type=float, default=0.01)
    p.add_argument("--max-levels", type=int, default=6)
    p.add_argument("--wal-flush-every-write", action="store_true")
    p.add_argument("--tombstone-retention-seconds", type=int, default=86400)
    p.add_argument("--sample-ms", type=int, default=500)
    p.add_argument("--out-csv", default="/tmp/lsm_metrics.csv")
    args = p.parse_args()
    os.makedirs(args.data_dir, exist_ok=True)
    run_demo(args)
```

Plotting (matplotlib; offline)
```python path=null start=null
import csv, matplotlib.pyplot as plt

rows = []
with open("/tmp/lsm_metrics.csv") as f:
    r = csv.DictReader(f)
    rows = list(r)

# Convert fields
for row in rows:
    row["ts_ms"] = int(row["ts_ms"]) 
    row["ops_total"] = int(row["ops_total"]) 
    row["ops_put"] = int(row["ops_put"]) 
    row["ops_get"] = int(row["ops_get"]) 
    row["memtable_bytes"] = int(row["memtable_bytes"])

# X-axis in seconds
t = [(row["ts_ms"] - rows[0]["ts_ms"]) / 1000.0 for row in rows]

fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

# (1) Throughput per sampling window
axes[0].plot(t, [row["ops_put"] for row in rows], label="put/s")
axes[0].plot(t, [row["ops_get"] for row in rows], label="get/s")
axes[0].set_ylabel("ops/s")
axes[0].legend(loc="upper right")
axes[0].set_title("Throughput")

# (2) Memtable size
axes[1].plot(t, [row["memtable_bytes"] for row in rows], color="tab:orange")
axes[1].set_ylabel("bytes")
axes[1].set_title("Memtable size")

# (3) SSTable counts per level (stacked)
levels = [k for k in rows[0].keys() if k.startswith("sst_count_L")]
stack = [ [int(row[L]) for row in rows] for L in levels ]
base = [0]*len(rows)
for i, series in enumerate(stack):
    axes[2].fill_between(t, base, [b+s for b,s in zip(base, series)], alpha=0.3, label=levels[i])
    base = [b+s for b,s in zip(base, series)]
axes[2].set_ylabel("SSTable count (stacked)")
axes[2].set_xlabel("time (s)")
axes[2].legend(loc="upper left", ncol=2)
axes[2].set_title("SSTables per level")

plt.tight_layout(); plt.show()
```

Live visualization option
- Use `matplotlib.animation.FuncAnimation` or `plotly.express` to refresh from the CSV every sampling tick.
- Alternative: terminal UI with `rich` to print compact gauges and per-level counts.

Saving real-time plots to a video
- MP4 (preferred, requires ffmpeg on PATH):
  - Install ffmpeg (Linux): `sudo pacman -S ffmpeg`
  - Then run a small script to render frames and save:

```python path=null start=null
# save_video.py — saves a video of the evolving charts from the CSV
from lsm_tree.demo.lsm_live_visualizer import load_csv_data
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter, PillowWriter

CSV = "/tmp/lsm_metrics.csv"      # path produced by the demo driver
INTERVAL_MS = 500                  # match sampling interval for smoothness
OUT = "lsm_demo.mp4"               # use .gif to save as GIF instead
FPS = max(1, 1000 // INTERVAL_MS)  # simple mapping interval → fps

fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
fig.suptitle("LSM Tree Live Metrics", fontsize=14, fontweight="bold")
(line_put,) = axes[0].plot([], [], label="put/s", linewidth=2)
(line_get,) = axes[0].plot([], [], label="get/s", linewidth=2)
(line_del,) = axes[0].plot([], [], label="delete/s", linewidth=2)
axes[0].legend(loc="upper right"); axes[0].grid(True, alpha=0.3)
(line_mem,) = axes[1].plot([], [], color="tab:orange", linewidth=2)
axes[1].grid(True, alpha=0.3)
axes[2].grid(True, alpha=0.3)

level_cols_cache = None

def update(_frame):
    global level_cols_cache
    rows, level_cols = load_csv_data(CSV)
    if not rows:
        return (line_put, line_get, line_del, line_mem)
    if level_cols_cache is None:
        level_cols_cache = level_cols
    t = [(r["ts_ms"] - rows[0]["ts_ms"]) / 1000.0 for r in rows]
    # Throughput
    line_put.set_data(t, [r["ops_put"] for r in rows])
    line_get.set_data(t, [r["ops_get"] for r in rows])
    line_del.set_data(t, [r["ops_del"] for r in rows])
    axes[0].relim(); axes[0].autoscale_view()
    # Memtable
    line_mem.set_data(t, [r["memtable_bytes"] for r in rows])
    axes[1].relim(); axes[1].autoscale_view()
    # SSTable counts stacked
    axes[2].clear(); axes[2].grid(True, alpha=0.3)
    stack = [[int(r[L]) for r in rows] for L in level_cols_cache]
    base = [0]*len(rows)
    colors = plt.cm.tab10.colors
    for i, series in enumerate(stack):
        axes[2].fill_between(t, base, [b+s for b,s in zip(base, series)], alpha=0.6,
                             label=level_cols_cache[i], color=colors[i % len(colors)])
        base = [b+s for b,s in zip(base, series)]
    axes[2].legend(loc="upper left", ncol=3, fontsize=9)
    return (line_put, line_get, line_del, line_mem)

ani = FuncAnimation(fig, update, interval=INTERVAL_MS, blit=False, cache_frame_data=False)

# Choose writer based on output extension
if OUT.lower().endswith(".mp4"):
    writer = FFMpegWriter(fps=FPS, bitrate=1800)
else:
    writer = PillowWriter(fps=FPS)  # saves GIF, no ffmpeg required

ani.save(OUT, writer=writer, dpi=150)
print("Saved:", OUT)
```

- Run it with uv:

```bash
uv run python save_video.py
```

- Alternate (record your screen window):
  - `ffmpeg -video_size 1280x800 -framerate 30 -f x11grab -i :0.0 -codec:v libx264 -preset veryfast lsm_demo_screen.mp4`
  - Start this while the live visualizer window is running.

Demo script recipe
- Run the driver for 60–90 seconds with an aggressive write rate and small memtable to force several flushes and at least one compaction:
  - `--write-rate 5000 --memtable-max-bytes 200_000 --sstable-max-bytes 1_000_000 --sample-ms 250`
- To compare modes, enable background compaction with `--async-compaction` (or set `ASYNC=1 ./demo/run_demo.sh`).
- Show the effects of tuning: increase `--bloom-fpr` → expect slightly fewer index/bloom skips; increase value size → larger memtable and fewer keys/flush.

Annotations to add during the talk
- Vertical markers on plots at `flush_memtable()` invocation or after visible drops in memtable size.
- Mark compaction start/end if the driver triggers `compact_level(0)` periodically (e.g., every X SSTables in L0).

Artifacts
- CSV: `/tmp/lsm_metrics.csv`
- Optional: HTML plot via Plotly for sharing post-demo.

Notes
- This plan reads private attributes for convenience during demos; for production, expose a read-only metrics API or Prometheus exporters.
- Sampling and pacing loops are intentionally simple to keep the demo robust; you can replace them with asyncio, dedicated worker threads, or a proper rate limiter if needed.
