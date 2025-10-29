# LSM Tree Demo Tools

Live demonstration and visualization tools for the LSM Tree implementation.

## Overview

This directory contains:
- **lsm_demo_driver.py**: Generates workload and collects metrics
- **lsm_live_visualizer.py**: Visualizes metrics in real-time or post-run

## Quick Start

### 1. Run a demo workload

Generate metrics with an aggressive write workload (synchronous compaction):

```bash
uv run python demo/lsm_demo_driver.py \
    --write-rate 5000 \
    --duration-seconds 60 \
    --memtable-max-bytes 200000 \
    --sstable-max-bytes 1000000 \
    --sample-ms 250
```

Enable non-blocking background compaction with the async flag:

```bash
uv run python demo/lsm_demo_driver.py \
    --async-compaction \
    --write-rate 5000 \
    --duration-seconds 60 \
    --memtable-max-bytes 200000 \
    --sstable-max-bytes 1000000 \
    --sample-ms 250
```

Using the convenience script with async compaction:

```bash
ASYNC=1 ./demo/run_demo.sh
```

This will:
- Write at ~5000 ops/sec for 60 seconds
- Use a small memtable (200KB) to force frequent flushes
- Sample metrics every 250ms
- Output to `/tmp/lsm_metrics.csv`

### 2. Visualize (static plot after run)

```bash
uv run python demo/lsm_live_visualizer.py --csv /tmp/lsm_metrics.csv
```

Save to file:

```bash
uv run python demo/lsm_live_visualizer.py --csv /tmp/lsm_metrics.csv --output lsm_plot.png
```

### 3. Visualize (live during run)

In one terminal:

```bash
uv run python demo/lsm_demo_driver.py --write-rate 5000 --duration-seconds 90
```

In another terminal (immediately):

```bash
uv run python demo/lsm_live_visualizer.py --csv /tmp/lsm_metrics.csv --live
```

The plot will update every second as new data is written.

### 4. Save to video (MP4 or GIF)

Create an animated video from completed demo data:

```bash
uv run python demo/lsm_live_visualizer.py --csv /tmp/lsm_metrics.csv --save-video lsm_demo.mp4
```

Or save as GIF (no ffmpeg required):

```bash
uv run python demo/lsm_live_visualizer.py --csv /tmp/lsm_metrics.csv --save-video lsm_demo.gif
```

Adjust frame rate:

```bash
uv run python demo/lsm_live_visualizer.py --csv /tmp/lsm_metrics.csv --save-video lsm_demo.mp4 --fps 4
```

**Note:** MP4 output requires `ffmpeg` installed on your system:
```bash
sudo pacman -S ffmpeg  # Arch Linux
```

## Driver Options

### Engine Configuration

- `--data-dir`: Data directory (default: `/tmp/lsm_demo`)
- `--async-compaction`: Use AsyncLSMStore with background compaction (non-blocking writes)
- `--memtable-max-bytes`: Memtable size threshold (default: 1,000,000)
- `--sstable-max-bytes`: SSTable size limit (default: 8,000,000)
- `--bloom-fpr`: Bloom filter false positive rate (default: 0.01)
- `--max-levels`: Maximum LSM levels (default: 6)
- `--wal-flush-every-write`: Fsync after every write (default: false)
- `--tombstone-retention-seconds`: Tombstone retention (default: 86400)

Tip: When using `run_demo.sh`, set `ASYNC=1` to enable background compaction.

### Workload Configuration

- `--duration-seconds`: Duration of the demo (default: 60)
- `--write-rate`: Write ops/sec (default: 2000)
- `--read-rate`: Read ops/sec (default: 0)
- `--delete-rate`: Delete ops/sec (default: 0)
- `--key-space-size`: Number of distinct keys (default: 100,000)
- `--value-size-bytes`: Size of values in bytes (default: 128)

### Sampling Configuration

- `--sample-ms`: Sampling interval in ms (default: 500)
- `--out-csv`: Output CSV file (default: `/tmp/lsm_metrics.csv`)

## Visualizer Options

- `--csv`: Path to metrics CSV file (default: `/tmp/lsm_metrics.csv`)
- `--live`: Display live updating plots (default: static)
- `--interval-ms`: Update interval for live plots in ms (default: 1000)
- `--output`: Save static plot to file (PNG/PDF/SVG)
- `--save-video`: Save animated video to file (MP4/GIF)
- `--fps`: Frames per second for video output (default: 2)

## Example Scenarios

### Scenario 1: Force multiple flushes

Small memtable with high write rate:

```bash
uv run python demo/lsm_demo_driver.py \
    --write-rate 8000 \
    --memtable-max-bytes 100000 \
    --duration-seconds 30
```

Watch memtable size oscillate as flushes occur.

### Scenario 2: Mixed workload

Write and read simultaneously:

```bash
uv run python demo/lsm_demo_driver.py \
    --write-rate 3000 \
    --read-rate 2000 \
    --duration-seconds 60
```

### Scenario 3: Delete-heavy workload

Test tombstone behavior:

```bash
uv run python demo/lsm_demo_driver.py \
    --write-rate 2000 \
    --delete-rate 1000 \
    --duration-seconds 60
```

### Scenario 4: Large values

Test with larger payloads:

```bash
uv run python demo/lsm_demo_driver.py \
    --write-rate 1000 \
    --value-size-bytes 4096 \
    --memtable-max-bytes 500000 \
    --duration-seconds 60
```

## Metrics Collected

The CSV file contains the following columns:

- `ts_ms`: Timestamp in milliseconds
- `ops_total`: Total operations in the sampling window
- `ops_put`: Put operations
- `ops_get`: Get operations
- `ops_del`: Delete operations
- `memtable_bytes`: Current memtable size in bytes
- `sst_count_L0` ... `sst_count_L5`: SSTable count per level
- `sst_bytes_L0` ... `sst_bytes_L5`: Total bytes per level

## Visualizations

The visualizer generates three plots:

1. **Throughput**: ops/sec over time (put, get, delete)
2. **Memtable Size**: bytes over time, with flush events marked
3. **SSTables per Level**: Stacked area chart showing count per level

## Dependencies

The visualization tool requires matplotlib. Install with:

```bash
uv add matplotlib
```

The demo driver uses only standard library + the LSM Tree implementation (which depends on sortedcontainers).

## Notes

- The driver accesses internal store attributes (`_memtable`, `_catalog`) for demo purposes. In production, expose a read-only metrics API.
- The workload pacing is probabilistic and approximate; actual rates may vary slightly.
- For presentation demos, use `--sample-ms 250` for smoother animations.
- Clean up old data directories between runs to avoid recovery overhead.

## Troubleshooting

**CSV file not found:**

Make sure the driver has finished writing at least one sample. For live visualization, the file must exist before starting the visualizer.

**Low throughput:**

- Disable `--wal-flush-every-write` to avoid fsync overhead
- Increase memtable and SSTable sizes
- Reduce sampling frequency (`--sample-ms 1000`)

**Plot not updating in live mode:**

- Ensure the driver is still running and writing to the CSV
- Check that both processes are using the same CSV path
- If you see "non-interactive backend" warning, install tk: `sudo pacman -S tk`
- Alternative: use `--save-video` instead of `--live` to create an animation file
