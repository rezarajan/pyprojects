#!/usr/bin/env python3
"""LSM Tree Live Visualizer

Reads metrics CSV and displays live updating plots.

Usage:
    # In one terminal:
    python demo/lsm_demo_driver.py --write-rate 5000 --duration-seconds 90

    # In another terminal (or after):
    python demo/lsm_live_visualizer.py --csv /tmp/lsm_metrics.csv --live
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import matplotlib

# Set backend before importing pyplot
try:
    matplotlib.use('TkAgg')  # Try TkAgg first
except ImportError:
    try:
        matplotlib.use('Qt5Agg')  # Fallback to Qt5
    except ImportError:
        pass  # Use default backend

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter, PillowWriter


def load_csv_data(csv_path: str) -> tuple[list[dict], list[str]]:
    """Load CSV data and return rows and level column names."""
    rows = []
    level_cols = []

    try:
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric fields
                row["ts_ms"] = int(row["ts_ms"])
                row["ops_total"] = int(row["ops_total"])
                row["ops_put"] = int(row["ops_put"])
                row["ops_get"] = int(row["ops_get"])
                row["ops_del"] = int(row["ops_del"])
                row["memtable_bytes"] = int(row["memtable_bytes"])

                # Convert level counts and sizes
                for key in row:
                    if key.startswith("sst_count_L") or key.startswith("sst_bytes_L"):
                        row[key] = int(row[key])
                
                # Event field (string, may not exist in older CSVs)
                if "event" not in row:
                    row["event"] = ""

                rows.append(row)

            if rows:
                level_cols = [k for k in rows[0].keys() if k.startswith("sst_count_L")]

    except FileNotFoundError:
        pass

    return rows, level_cols


def plot_static(csv_path: str, output_path: str | None = None) -> None:
    """Generate static plots from CSV data."""
    rows, level_cols = load_csv_data(csv_path)

    if not rows:
        print(f"No data found in {csv_path}")
        return

    # X-axis in seconds relative to start
    t = [(row["ts_ms"] - rows[0]["ts_ms"]) / 1000.0 for row in rows]

    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)

    # (1) Throughput per sampling window
    axes[0].plot(t, [row["ops_put"] for row in rows], label="put/s", linewidth=2)
    axes[0].plot(t, [row["ops_get"] for row in rows], label="get/s", linewidth=2)
    axes[0].plot(t, [row["ops_del"] for row in rows], label="delete/s", linewidth=2)
    axes[0].set_ylabel("ops/s", fontsize=11)
    axes[0].legend(loc="upper right")
    axes[0].set_title("Throughput", fontsize=12, fontweight="bold")
    axes[0].grid(True, alpha=0.3)

    # (2) Memtable size
    mem_bytes = [row["memtable_bytes"] for row in rows]
    axes[1].plot(t, mem_bytes, color="tab:orange", linewidth=2)
    axes[1].set_ylabel("bytes", fontsize=11)
    axes[1].set_title("Memtable Size", fontsize=12, fontweight="bold")
    axes[1].grid(True, alpha=0.3)

    # Mark flush events (sharp drops in memtable size)
    for i in range(1, len(mem_bytes)):
        if mem_bytes[i] < mem_bytes[i - 1] * 0.5:  # Significant drop
            axes[1].axvline(t[i], color="red", linestyle="--", alpha=0.5, linewidth=1)

    # (3) SSTable counts per level (stacked area)
    if level_cols:
        stack = [[int(row[L]) for row in rows] for L in level_cols]
        base = [0] * len(rows)
        colors = plt.cm.tab10.colors

        for i, series in enumerate(stack):
            axes[2].fill_between(
                t,
                base,
                [b + s for b, s in zip(base, series)],
                alpha=0.6,
                label=level_cols[i],
                color=colors[i % len(colors)],
            )
            base = [b + s for b, s in zip(base, series)]

        axes[2].set_ylabel("SSTable count (stacked)", fontsize=11)
        axes[2].set_xlabel("time (s)", fontsize=11)
        axes[2].legend(loc="upper left", ncol=3, fontsize=9)
        axes[2].set_title("SSTables per Level", fontsize=12, fontweight="bold")
        axes[2].grid(True, alpha=0.3)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150)
        print(f"Plot saved to {output_path}")
    else:
        plt.show()


def save_video(csv_path: str, output_path: str, interval_ms: int = 500, fps: int = 2) -> None:
    """Save animated plots to video file.
    
    Args:
        csv_path: Path to CSV metrics file
        output_path: Output video file (.mp4 or .gif)
        interval_ms: Interval between frames in milliseconds
        fps: Frames per second for output video
    """
    print(f"Generating video from {csv_path}...")
    print(f"Output: {output_path}")
    
    # Use non-interactive backend for video rendering
    matplotlib.use('Agg')
    
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    fig.suptitle("LSM Tree Live Metrics", fontsize=14, fontweight="bold")

    # Initialize empty line objects
    (line_put,) = axes[0].plot([], [], label="put/s", linewidth=2)
    (line_get,) = axes[0].plot([], [], label="get/s", linewidth=2)
    (line_del,) = axes[0].plot([], [], label="delete/s", linewidth=2)
    axes[0].set_ylabel("ops/s", fontsize=11)
    axes[0].legend(loc="upper right")
    axes[0].set_title("Throughput", fontsize=12)
    axes[0].grid(True, alpha=0.3)

    (line_mem,) = axes[1].plot([], [], color="tab:orange", linewidth=2)
    axes[1].set_ylabel("bytes", fontsize=11)
    axes[1].set_title("Memtable Size", fontsize=12)
    axes[1].grid(True, alpha=0.3)

    axes[2].set_ylabel("SSTable count", fontsize=11)
    axes[2].set_xlabel("time (s)", fontsize=11)
    axes[2].set_title("SSTables per Level", fontsize=12)
    axes[2].grid(True, alpha=0.3)
    
    # Load all data once
    all_rows, level_cols = load_csv_data(csv_path)
    if not all_rows:
        print("Error: No data in CSV file")
        return
    
    level_cols_cache = level_cols
    
    # Track event annotations
    event_texts = []

    def update(frame: int) -> tuple:
        """Update function called by animation - shows data up to current frame."""
        nonlocal event_texts
        
        # Show data up to this frame (progressive buildup)
        rows = all_rows[:frame + 1]
        
        if not rows:
            return (line_put, line_get, line_del, line_mem)

        # X-axis (relative time in seconds)
        t = [(row["ts_ms"] - all_rows[0]["ts_ms"]) / 1000.0 for row in rows]
        
        # Calculate running average write throughput
        if len(rows) > 1:
            total_ops = sum(row["ops_put"] for row in rows)
            elapsed = t[-1]
            avg_throughput = total_ops / elapsed if elapsed > 0 else 0
        else:
            avg_throughput = 0

        # Update throughput lines
        line_put.set_data(t, [row["ops_put"] for row in rows])
        line_get.set_data(t, [row["ops_get"] for row in rows])
        line_del.set_data(t, [row["ops_del"] for row in rows])
        axes[0].relim()
        axes[0].autoscale_view()
        
        # Clear old event texts
        for txt in event_texts:
            txt.remove()
        event_texts.clear()
        
        # Add running average text to throughput plot
        event_texts.append(axes[0].text(0.02, 0.98, f"Avg Write: {avg_throughput:.0f} ops/s",
                                       transform=axes[0].transAxes, fontsize=10,
                                       verticalalignment='top', bbox=dict(boxstyle='round', 
                                       facecolor='wheat', alpha=0.5)))

        # Update memtable line
        line_mem.set_data(t, [row["memtable_bytes"] for row in rows])
        axes[1].relim()
        axes[1].autoscale_view()

        # Update SSTable counts (stacked)
        axes[2].clear()
        axes[2].grid(True, alpha=0.3)
        if level_cols_cache:
            stack = [[int(row[L]) for row in rows] for L in level_cols_cache]
            base = [0] * len(rows)
            colors = plt.cm.tab10.colors

            for i, series in enumerate(stack):
                axes[2].fill_between(
                    t,
                    base,
                    [b + s for b, s in zip(base, series)],
                    alpha=0.6,
                    label=level_cols_cache[i],
                    color=colors[i % len(colors)],
                )
                base = [b + s for b, s in zip(base, series)]

            axes[2].legend(loc="upper left", ncol=3, fontsize=9)

        axes[2].set_ylabel("SSTable count", fontsize=11)
        axes[2].set_xlabel("time (s)", fontsize=11)
        
        # Add event markers after axes are updated
        for i, row in enumerate(rows):
            if row.get("event") == "flush" and len(rows) > 1:
                # Mark flush events on memtable plot
                ylim = axes[1].get_ylim()
                if ylim[1] > 0:
                    axes[1].axvline(t[i], color="red", linestyle="--", alpha=0.6, linewidth=1.5)
                    event_texts.append(axes[1].text(t[i], ylim[1] * 0.85, "FLUSH", 
                                                   rotation=90, fontsize=8, color="red", alpha=0.8))
            elif row.get("event", "").startswith("compact") and len(rows) > 1:
                # Mark compaction events on SSTable plot
                ylim = axes[2].get_ylim()
                if ylim[1] > 0:
                    axes[2].axvline(t[i], color="blue", linestyle="-.", alpha=0.6, linewidth=1.5)
                    event_texts.append(axes[2].text(t[i], ylim[1] * 0.85, "COMPACT", 
                                                   rotation=90, fontsize=8, color="blue", alpha=0.8))

        return (line_put, line_get, line_del, line_mem)

    # Create animation with all frames (data already loaded)
    frames = len(all_rows)
    print(f"Rendering {frames} frames at {fps} fps...")
    
    ani = FuncAnimation(
        fig, update, frames=frames, interval=interval_ms, blit=False, repeat=False
    )

    plt.tight_layout()

    # Choose writer based on output extension
    if output_path.lower().endswith(".mp4"):
        try:
            writer = FFMpegWriter(fps=fps, bitrate=1800)
            ani.save(output_path, writer=writer, dpi=150)
        except Exception as e:
            print(f"Error saving MP4 (is ffmpeg installed?): {e}")
            print("Trying GIF format instead...")
            output_path = output_path.replace(".mp4", ".gif")
            writer = PillowWriter(fps=fps)
            ani.save(output_path, writer=writer, dpi=150)
    else:
        writer = PillowWriter(fps=fps)
        ani.save(output_path, writer=writer, dpi=150)

    print(f"Video saved: {output_path}")
    plt.close(fig)


def plot_live(csv_path: str, interval_ms: int = 1000) -> None:
    """Display live updating plots."""
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    fig.suptitle("LSM Tree Live Metrics", fontsize=14, fontweight="bold")

    # Initialize empty line objects
    (line_put,) = axes[0].plot([], [], label="put/s", linewidth=2)
    (line_get,) = axes[0].plot([], [], label="get/s", linewidth=2)
    (line_del,) = axes[0].plot([], [], label="delete/s", linewidth=2)
    axes[0].set_ylabel("ops/s", fontsize=11)
    axes[0].legend(loc="upper right")
    axes[0].set_title("Throughput", fontsize=12)
    axes[0].grid(True, alpha=0.3)

    (line_mem,) = axes[1].plot([], [], color="tab:orange", linewidth=2)
    axes[1].set_ylabel("bytes", fontsize=11)
    axes[1].set_title("Memtable Size", fontsize=12)
    axes[1].grid(True, alpha=0.3)

    axes[2].set_ylabel("SSTable count", fontsize=11)
    axes[2].set_xlabel("time (s)", fontsize=11)
    axes[2].set_title("SSTables per Level", fontsize=12)
    axes[2].grid(True, alpha=0.3)

    def update(frame: int) -> tuple:
        """Update function called by animation."""
        rows, level_cols = load_csv_data(csv_path)

        if not rows:
            return (line_put, line_get, line_del, line_mem)

        # X-axis
        t = [(row["ts_ms"] - rows[0]["ts_ms"]) / 1000.0 for row in rows]

        # Update throughput lines
        line_put.set_data(t, [row["ops_put"] for row in rows])
        line_get.set_data(t, [row["ops_get"] for row in rows])
        line_del.set_data(t, [row["ops_del"] for row in rows])
        axes[0].relim()
        axes[0].autoscale_view()

        # Update memtable line
        line_mem.set_data(t, [row["memtable_bytes"] for row in rows])
        axes[1].relim()
        axes[1].autoscale_view()

        # Update SSTable counts (stacked)
        axes[2].clear()
        if level_cols:
            stack = [[int(row[L]) for row in rows] for L in level_cols]
            base = [0] * len(rows)
            colors = plt.cm.tab10.colors

            for i, series in enumerate(stack):
                axes[2].fill_between(
                    t,
                    base,
                    [b + s for b, s in zip(base, series)],
                    alpha=0.6,
                    label=level_cols[i],
                    color=colors[i % len(colors)],
                )
                base = [b + s for b, s in zip(base, series)]

            axes[2].legend(loc="upper left", ncol=3, fontsize=9)

        axes[2].set_ylabel("SSTable count", fontsize=11)
        axes[2].set_xlabel("time (s)", fontsize=11)
        axes[2].grid(True, alpha=0.3)

        return (line_put, line_get, line_del, line_mem)

    ani = FuncAnimation(
        fig, update, interval=interval_ms, blit=False, cache_frame_data=False
    )

    plt.tight_layout()
    plt.show()


def main() -> None:
    """Parse arguments and run visualizer."""
    p = argparse.ArgumentParser(description="LSM Tree metrics visualizer")
    p.add_argument(
        "--csv", default="/tmp/lsm_metrics.csv", help="Path to metrics CSV file"
    )
    p.add_argument(
        "--live",
        action="store_true",
        help="Display live updating plots (default: static)",
    )
    p.add_argument(
        "--interval-ms",
        type=int,
        default=1000,
        help="Update interval for live plots (ms)",
    )
    p.add_argument(
        "--output",
        help="Save static plot to file (PNG/PDF/SVG)",
    )
    p.add_argument(
        "--save-video",
        help="Save animated video to file (MP4/GIF)",
    )
    p.add_argument(
        "--fps",
        type=int,
        default=2,
        help="Frames per second for video output (default: 2)",
    )

    args = p.parse_args()

    csv_path = Path(args.csv)

    if not csv_path.exists() and not args.live:
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)

    if args.save_video:
        # Video mode
        if not csv_path.exists():
            print(f"Error: CSV file not found: {csv_path}")
            sys.exit(1)
        save_video(str(csv_path), args.save_video, args.interval_ms, args.fps)
    elif args.live:
        # Live mode
        print(f"Starting live visualization of {csv_path}")
        print(f"Using backend: {matplotlib.get_backend()}")
        print("Press Ctrl+C to stop")
        if matplotlib.get_backend() == 'agg':
            print("\nWarning: Non-interactive backend detected.")
            print("Live plotting may not work. Consider:")
            print("  - Installing tk: sudo pacman -S tk")
            print("  - Or use --save-video to create an animation file")
            print()
        try:
            plot_live(str(csv_path), args.interval_ms)
        except KeyboardInterrupt:
            print("\nStopped")
    else:
        # Static mode
        print(f"Generating static plot from {csv_path}")
        plot_static(str(csv_path), args.output)


if __name__ == "__main__":
    main()
