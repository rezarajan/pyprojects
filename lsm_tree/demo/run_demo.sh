#!/bin/bash
# Quick demo launcher with sensible defaults

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default settings (can be overridden by environment variables)
DURATION=${DURATION:-60}
WRITE_RATE=${WRITE_RATE:-5000}
READ_RATE=${READ_RATE:-0}
DELETE_RATE=${DELETE_RATE:-0}
MEMTABLE_SIZE=${MEMTABLE_SIZE:-200000}
SSTABLE_SIZE=${SSTABLE_SIZE:-1000000}
SAMPLE_MS=${SAMPLE_MS:-250}
DATA_DIR=${DATA_DIR:-/tmp/lsm_demo}
CSV_FILE=${CSV_FILE:-/tmp/lsm_metrics.csv}

echo "================================================"
echo "LSM Tree Demo"
echo "================================================"
echo "Duration: ${DURATION}s"
echo "Write rate: ${WRITE_RATE} ops/s"
echo "Read rate: ${READ_RATE} ops/s"
echo "Delete rate: ${DELETE_RATE} ops/s"
echo "Memtable size: ${MEMTABLE_SIZE} bytes"
echo "SSTable size: ${SSTABLE_SIZE} bytes"
echo "Sampling: every ${SAMPLE_MS}ms"
echo "Data dir: ${DATA_DIR}"
echo "CSV output: ${CSV_FILE}"
echo "================================================"
echo ""

# Clean up old data
if [ -d "$DATA_DIR" ]; then
    echo "Cleaning up old data directory..."
    rm -rf "$DATA_DIR"
fi

if [ -f "$CSV_FILE" ]; then
    echo "Removing old CSV file..."
    rm -f "$CSV_FILE"
fi

# Run the demo driver
echo "Starting demo driver..."
cd "$PROJECT_ROOT"
uv run python "$SCRIPT_DIR/lsm_demo_driver.py" \
    --duration-seconds "$DURATION" \
    --write-rate "$WRITE_RATE" \
    --read-rate "$READ_RATE" \
    --delete-rate "$DELETE_RATE" \
    --memtable-max-bytes "$MEMTABLE_SIZE" \
    --sstable-max-bytes "$SSTABLE_SIZE" \
    --sample-ms "$SAMPLE_MS" \
    --data-dir "$DATA_DIR" \
    --out-csv "$CSV_FILE"

echo ""
echo "================================================"
echo "Demo complete!"
echo "================================================"
echo "CSV file: $CSV_FILE"
echo ""
echo "To visualize:"
echo "  uv run python $SCRIPT_DIR/lsm_live_visualizer.py --csv $CSV_FILE"
echo ""
echo "To save as PNG:"
echo "  uv run python $SCRIPT_DIR/lsm_live_visualizer.py --csv $CSV_FILE --output lsm_plot.png"
echo "================================================"
