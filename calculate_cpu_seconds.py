#!/usr/bin/env python3
"""
Calculate CPU-seconds metric by integrating area under CPU usage curve.
Uses the trapezoidal rule for numerical integration.
"""

import argparse
import sys
from pathlib import Path

import numpy as np


def load_cpu_usage_data(filepath):
    """Load CPU usage data from a log file with 'timestamp,cpu_percentage' format."""
    timestamps = []
    cpu_values = []

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                parts = line.split(",")
                timestamp = float(parts[0])
                cpu_percent = float(parts[1])
                timestamps.append(timestamp)
                cpu_values.append(cpu_percent)
            except (ValueError, IndexError) as e:
                print(f"Warning: Skipping malformed line: {line}", file=sys.stderr)
                continue

    return np.array(timestamps), np.array(cpu_values)


def calculate_cpu_seconds(timestamps, cpu_values):
    """
    Calculate CPU-seconds using trapezoidal rule integration.

    CPU-seconds = integral of CPU% over time
    This gives a measure of total CPU work done, comparable across different runs.

    Args:
        timestamps: Array of time points (seconds)
        cpu_values: Array of CPU usage percentages at each time point

    Returns:
        float: Total CPU-seconds (percentage-seconds)
    """
    if len(timestamps) < 2:
        raise ValueError("Need at least 2 data points to calculate area under curve")

    cpu_seconds = np.trapezoid(cpu_values, timestamps)

    return cpu_seconds


def get_most_recent_results_dir():
    """Find the most recent results directory."""
    results_base = Path("results")

    if not results_base.exists():
        raise FileNotFoundError("No 'results/' directory found")

    subdirs = [d for d in results_base.iterdir() if d.is_dir()]

    if not subdirs:
        raise FileNotFoundError("No results directories found in 'results/'")

    # Sort by modification time, most recent first
    most_recent = max(subdirs, key=lambda d: d.stat().st_mtime)

    return most_recent


def main():
    parser = argparse.ArgumentParser(
        description="Calculate CPU-seconds from profiling results using area under the curve"
    )
    parser.add_argument(
        "results_dir",
        nargs="?",
        default=None,
        help="Path to results directory containing cpu_usage.log (default: most recent in results/)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed information about the calculation",
    )

    args = parser.parse_args()

    # Determine results directory
    if args.results_dir is None:
        results_dir = get_most_recent_results_dir()
        if args.verbose:
            print(f"Using most recent results: {results_dir}")
    else:
        results_dir = Path(args.results_dir)
        if not results_dir.exists():
            print(f"Error: Directory not found: {results_dir}", file=sys.stderr)
            sys.exit(1)

    # Load CPU usage data
    cpu_usage_file = results_dir / "cpu_usage.log"
    if not cpu_usage_file.exists():
        print(f"Error: CPU usage file not found: {cpu_usage_file}", file=sys.stderr)
        sys.exit(1)

    try:
        timestamps, cpu_values = load_cpu_usage_data(cpu_usage_file)
    except Exception as e:
        print(f"Error loading CPU usage data: {e}", file=sys.stderr)
        sys.exit(1)

    if len(timestamps) == 0:
        print("Error: No valid data points found in cpu_usage.log", file=sys.stderr)
        sys.exit(1)

    # Calculate CPU-seconds
    try:
        cpu_seconds = calculate_cpu_seconds(timestamps, cpu_values)
    except Exception as e:
        print(f"Error calculating CPU-seconds: {e}", file=sys.stderr)
        sys.exit(1)

    # Display results
    if args.verbose:
        print(f"\n{'='*60}")
        print(f"CPU-Seconds Calculation Results")
        print(f"{'='*60}")
        print(f"Results directory: {results_dir}")
        print(f"Data points: {len(timestamps)}")
        print(f"Time range: {timestamps[0]:.2f}s to {timestamps[-1]:.2f}s")
        print(f"Duration: {timestamps[-1] - timestamps[0]:.2f}s")
        print(f"Average CPU%: {np.mean(cpu_values):.2f}%")
        print(f"Max CPU%: {np.max(cpu_values):.2f}%")
        print(f"Min CPU%: {np.min(cpu_values):.2f}%")
        print(f"\nCPU-seconds (area under curve): {cpu_seconds:.2f} %-s")
        print(f"{'='*60}")
    else:
        print(f"{cpu_seconds:.2f}")


if __name__ == "__main__":
    main()
