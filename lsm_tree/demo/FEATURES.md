# LSM Tree Demo - Features Summary

## Overview

The LSM Tree demo system provides a complete visualization pipeline for understanding LSM Tree behavior in real-time or through post-run analysis. It demonstrates:

- Write/read/delete workload generation
- Automatic memtable flushing
- Multi-level compaction (L0 → L1)
- Event tracking and visualization
- Performance metrics

## Key Features

### 1. Workload Driver (`lsm_demo_driver.py`)

**Configurable Workload**
- Write, read, and delete operation rates (ops/sec)
- Adjustable key space size
- Variable value sizes
- Duration control

**Automatic LSM Operations**
- Memtable flushing when size threshold exceeded
- Automatic L0 → L1 compaction when L0 has ≥4 SSTables
- Real-time event logging (flush/compaction)

**Metrics Collection**
- Throughput (put/get/delete ops per sampling window)
- Memtable size in bytes
- SSTable counts per level (L0-L5)
- SSTable total bytes per level
- Event markers (flush, compaction)

**Sample Output**
```
[1.2s] FLUSH: Memtable → L0
[5.1s] COMPACTION: L0 → L1 (L0 count=4)
```

### 2. Visualization (`lsm_live_visualizer.py`)

**Three Visualization Modes**

1. **Static Plots** - Generate PNG/PDF/SVG from completed runs
2. **Live Plots** - Real-time updating during demo execution
3. **Video Export** - Animated GIF or MP4 showing progressive buildup

**Three Plot Panels**

1. **Throughput** (top)
   - Put/get/delete ops/sec over time
   - Running average write throughput (text box)
   - Lines drawn progressively

2. **Memtable Size** (middle)
   - Memory usage in bytes over time
   - Red dashed vertical lines mark flush events
   - "FLUSH" labels at event times

3. **SSTables per Level** (bottom)
   - Stacked area chart showing L0-L5
   - Blue dash-dot lines mark compaction events
   - "COMPACT" labels at event times
   - Different colors per level

**Event Annotations**
- **FLUSH** markers (red, dashed) on memtable plot when data moves to L0
- **COMPACT** markers (blue, dash-dot) on SSTable plot during L0→L1 merge
- Running average throughput displayed continuously

### 3. Video Generation

**Progressive Animation**
- Shows data building up over time (not just final state)
- Each frame shows data up to that point in time
- Frame rate configurable (default: 2-5 fps)

**Formats**
- **GIF** - No external dependencies (uses Pillow)
- **MP4** - Requires ffmpeg, smaller file size

**Usage**
```bash
uv run python demo/lsm_live_visualizer.py \
    --csv /tmp/lsm_metrics.csv \
    --save-video output.gif \
    --fps 5
```

## What the Demo Shows

### Write Path
1. Operations accumulate in memtable
2. Memtable size grows until threshold (default: 200KB)
3. **FLUSH** event: Memtable → new L0 SSTable
4. Memtable size drops to near-zero
5. Process repeats

### Compaction Path
1. Multiple flushes create SSTables at L0
2. When L0 count reaches 4, compaction triggers
3. **COMPACT** event: L0 SSTables merge into L1
4. L0 count drops, L1 count increases
5. Duplicate keys removed, tombstones purged

### Performance Metrics
- Throughput varies during flushes/compactions (visible dips)
- Running average shows sustained write rate
- Memtable oscillates between 0 and threshold
- L0 saw-tooth pattern (grows then drops on compaction)
- L1 grows steadily as data migrates

## Sample Workflow

### Quick Demo
```bash
# 30-second run with high write rate
DURATION=30 WRITE_RATE=6000 ./demo/run_demo.sh

# Create animated GIF
uv run python demo/lsm_live_visualizer.py \
    --csv /tmp/lsm_metrics.csv \
    --save-video lsm_demo.gif \
    --fps 5
```

### Expected Results
- ~25-30 flush events (every 1-2 seconds)
- 5-6 compaction events (every 5 seconds)
- L0 oscillates between 0-4 SSTables
- L1 accumulates 4-6 SSTables
- Avg write throughput: ~5000-6000 ops/s

## Tuning for Presentation

### More Flushes
```bash
MEMTABLE_SIZE=100000 WRITE_RATE=8000 DURATION=20 ./demo/run_demo.sh
```

### More Compactions
```bash
MEMTABLE_SIZE=150000 WRITE_RATE=8000 DURATION=60 ./demo/run_demo.sh
```

### Smoother Animation
```bash
# Sample every 200ms, render at 5 fps
SAMPLE_MS=200 ./demo/run_demo.sh
uv run python demo/lsm_live_visualizer.py \
    --csv /tmp/lsm_metrics.csv \
    --save-video smooth.gif \
    --fps 5
```

## Technical Details

### CSV Format
```
ts_ms,ops_total,ops_put,ops_get,ops_del,memtable_bytes,
sst_count_L0,sst_count_L1,...,sst_count_L5,
sst_bytes_L0,sst_bytes_L1,...,sst_bytes_L5,
event
```

### Event Types
- `flush` - Memtable flushed to L0
- `compact_L0_L1` - L0 compacted to L1
- `` (empty) - No event

### Compaction Policy
- Threshold: 4 SSTables in L0
- Strategy: Merge all L0 into L1
- Triggered synchronously in sampling loop
- Future: Can extend to L1→L2, L2→L3, etc.

## Limitations & Future Enhancements

### Current Scope
- Single-level compaction (L0 → L1 only)
- Manual compaction triggers (no background thread)
- Simple threshold policy

### Possible Extensions
1. **Multi-level compaction** - L1→L2, L2→L3, etc.
2. **Tiered compaction** - Different policies per level
3. **Background compaction** - Async thread with scheduler
4. **Read visualization** - Show cache hits, bloom filter usage
5. **Resource metrics** - CPU, I/O wait, disk usage
6. **Comparative runs** - Side-by-side different configurations

## Dependencies

- **Core**: sortedcontainers (LSM implementation)
- **Visualization**: matplotlib (plots)
- **Video (optional)**: ffmpeg (MP4 encoding)
- **Environment**: uv (Python package management)

## File Outputs

- **CSV**: `/tmp/lsm_metrics.csv` (configurable)
- **Static plots**: `lsm_plot.png` (or PDF/SVG)
- **Videos**: `lsm_demo.gif` or `lsm_demo.mp4`
- **Data directory**: `/tmp/lsm_demo/` (WAL, SSTables, catalog)

## Performance Notes

- GIF encoding is slow for long videos (>100 frames)
- MP4 requires ffmpeg but is much faster to encode
- Large videos (>10MB) may need higher compression
- Sampling interval affects smoothness vs. overhead
