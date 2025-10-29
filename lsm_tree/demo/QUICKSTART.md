# LSM Tree Demo - Quick Start

## Prerequisites

This project uses `uv` for dependency management. The demo requires:
- `sortedcontainers` (LSM Tree dependency)
- `matplotlib` (visualization)

Both are already specified in `pyproject.toml` and will be installed automatically by `uv`.

## Fastest Way to Run

Use the convenience script with default settings:

```bash
./demo/run_demo.sh
```

This runs a 60-second demo with 5000 writes/sec and generates `/tmp/lsm_metrics.csv`.

## Customize the Run

Override defaults via environment variables:

```bash
# Short 30-second demo with high write rate
DURATION=30 WRITE_RATE=8000 ./demo/run_demo.sh

# Mixed workload
WRITE_RATE=3000 READ_RATE=2000 ./demo/run_demo.sh

# Custom memtable size to force frequent flushes
MEMTABLE_SIZE=100000 ./demo/run_demo.sh
```

Available environment variables:
- `DURATION` (default: 60)
- `WRITE_RATE` (default: 5000)
- `READ_RATE` (default: 0)
- `DELETE_RATE` (default: 0)
- `MEMTABLE_SIZE` (default: 200000)
- `SSTABLE_SIZE` (default: 1000000)
- `SAMPLE_MS` (default: 250)
- `DATA_DIR` (default: /tmp/lsm_demo)
- `CSV_FILE` (default: /tmp/lsm_metrics.csv)

## Visualize Results

### Static plot (after demo completes):

```bash
uv run python demo/lsm_live_visualizer.py --csv /tmp/lsm_metrics.csv
```

### Save to file:

```bash
uv run python demo/lsm_live_visualizer.py --csv /tmp/lsm_metrics.csv --output lsm_plot.png
```

### Live updating plot (while demo runs):

Terminal 1:
```bash
uv run python demo/lsm_demo_driver.py --write-rate 5000 --duration-seconds 90
```

Terminal 2 (start immediately):
```bash
uv run python demo/lsm_live_visualizer.py --csv /tmp/lsm_metrics.csv --live
```

### Save animated video:

Create an animated video showing the LSM tree behavior over time:

```bash
uv run python demo/lsm_live_visualizer.py --csv /tmp/lsm_metrics.csv --save-video lsm_demo.gif --fps 4
```

Or as MP4 (requires ffmpeg):

```bash
uv run python demo/lsm_live_visualizer.py --csv /tmp/lsm_metrics.csv --save-video lsm_demo.mp4 --fps 4
```

The video shows lines being drawn progressively over time, matching the actual operation timeline.

## Direct Driver Usage

For full control, run the driver directly:

```bash
uv run python demo/lsm_demo_driver.py \
    --write-rate 5000 \
    --read-rate 1000 \
    --duration-seconds 60 \
    --memtable-max-bytes 200000 \
    --sstable-max-bytes 1000000 \
    --sample-ms 250
```

Run `uv run python demo/lsm_demo_driver.py --help` for all options.

## What You'll See

The visualizer shows three plots:

1. **Throughput** - ops/sec over time (put, get, delete)
2. **Memtable Size** - memory usage with flush events marked (red dashed lines)
3. **SSTables per Level** - stacked area chart showing distribution across L0-L5

## Troubleshooting

**Missing dependencies:**
```bash
uv sync
```

**Old data interfering:**
```bash
rm -rf /tmp/lsm_demo /tmp/lsm_metrics.csv
```

**Plot window doesn't appear:**
- Ensure you have a display (X11/Wayland)
- Use `--output file.png` to save instead of displaying
- For headless systems, use a non-interactive backend

## Example Scenarios

### Force multiple flushes (small memtable):
```bash
MEMTABLE_SIZE=100000 WRITE_RATE=8000 DURATION=30 ./demo/run_demo.sh
```

### Steady state with compaction:
```bash
DURATION=120 WRITE_RATE=5000 ./demo/run_demo.sh
```

### Mixed read/write:
```bash
WRITE_RATE=3000 READ_RATE=2000 DURATION=60 ./demo/run_demo.sh
```

See `demo/README.md` for more detailed information.
