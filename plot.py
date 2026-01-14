"""
Plot profiling data from a results directory.
Loads CPU usage, database size, and package counts.
"""

import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd


def load_single_value_file(filepath):
    """Load a file where each line contains 'timestamp,value' format."""
    timestamps = []
    values = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    parts = line.split(",")
                    timestamps.append(float(parts[0]))
                    values.append(float(parts[1]))
                except (ValueError, IndexError):
                    continue
    return timestamps, values


def load_comma_delimited_file(filepath):
    """Load a file where each line contains 'timestamp,value1,value2,...' format and sum the values."""
    timestamps = []
    values = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line == "(0rows)":
                continue

            try:
                parts = line.split(",")
                timestamp = float(parts[0])
                # Sum all values after the timestamp
                value_sum = sum(float(n.strip()) for n in parts[1:])
                timestamps.append(timestamp)
                values.append(value_sum)
            except (ValueError, IndexError):
                continue

    return timestamps, values


def load_cpu_time_file(filepath):
    """Load cpu_time.log and calculate cumulative CPU-seconds over time.

    Format: timestamp,pid,utime_seconds,stime_seconds
    Returns cumulative total CPU time (user + system) for all process instances.

    Strategy: Track the maximum CPU time for each PID (its final state before exit),
    then sum those max values across all PIDs to get total cumulative CPU consumption.
    """
    from collections import defaultdict

    # Track all measurements for each PID
    pid_data = defaultdict(lambda: {"timestamps": [], "total_cpu": []})

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                parts = line.split(",")
                timestamp = float(parts[0])
                pid = int(parts[1])
                utime = float(parts[2])
                stime = float(parts[3])
                total_cpu = utime + stime

                pid_data[pid]["timestamps"].append(timestamp)
                pid_data[pid]["total_cpu"].append(total_cpu)
            except (ValueError, IndexError):
                continue

    # Get all unique timestamps
    all_timestamps = set()
    for pid_info in pid_data.values():
        all_timestamps.update(pid_info["timestamps"])

    timestamps = sorted(all_timestamps)
    cumulative_cpu_time = []

    # For each timestamp, calculate cumulative CPU time
    for ts in timestamps:
        total = 0.0
        # For each PID, sum the max CPU time seen so far (up to and including ts)
        for pid, pid_info in pid_data.items():
            max_cpu_for_pid = 0.0
            for i, pid_ts in enumerate(pid_info["timestamps"]):
                if pid_ts <= ts:
                    max_cpu_for_pid = max(max_cpu_for_pid, pid_info["total_cpu"][i])
            total += max_cpu_for_pid

        cumulative_cpu_time.append(total)

    return timestamps, cumulative_cpu_time


def load_results_directory(results_dir):
    """Load all log files from a results directory into a pandas DataFrame with timestamps as index."""
    results_path = Path(results_dir)

    files = {
        "cpu_usage": ("cpu_usage.log", load_single_value_file),
        "cpu_time": ("cpu_time.log", load_cpu_time_file),
        "db_size": ("db_size.log", load_single_value_file),
        "package_counts": ("package_counts.log", load_comma_delimited_file),
        "package_buffer_counts": (
            "package_buffer_counts.log",
            load_comma_delimited_file,
        ),
    }

    # Load all data with timestamps
    all_data = {}
    for column_name, (filename, loader_func) in files.items():
        filepath = results_path / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Expected file not found: {filepath}")
        timestamps, values = loader_func(filepath)
        all_data[column_name] = {"timestamps": timestamps, "values": values}

    # Find a common timestamp set (use cpu_usage as reference)
    if not all_data["cpu_usage"]["timestamps"]:
        raise ValueError("No data found in cpu_usage.log")

    # Create DataFrame with timestamps as index
    data_dict = {}
    reference_timestamps = all_data["cpu_usage"]["timestamps"]

    for column_name in files.keys():
        # Create a series indexed by timestamp
        series = pd.Series(
            all_data[column_name]["values"],
            index=all_data[column_name]["timestamps"],
            name=column_name,
        )
        data_dict[column_name] = series

    # Create DataFrame and reindex to common timestamps
    df = pd.DataFrame(data_dict)

    return df


def normalize_series(series):
    """Normalize a pandas Series to [0, 1] range."""
    min_val = series.min()
    max_val = series.max()

    if max_val - min_val > 0:
        return (series - min_val) / (max_val - min_val)
    else:
        return series


def plot_dataframe(df, output_file="plot.png"):
    """Plot CPU usage, CPU time, package counts, and database size on separate subplots with shared x-axis."""
    fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(16, 18), sharex=True)

    # Top plot: CPU usage (raw percentage)
    ax1.plot(
        df.index,
        df["cpu_usage"],
        linestyle="-",
        linewidth=1.5,
        alpha=0.7,
        label="CPU Usage",
        color="tab:red",
    )
    ax1.set_ylabel("CPU Usage (%)")
    ax1.set_title("CPU Usage Over Time")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Second plot: Cumulative CPU time (CPU-seconds)
    ax2.plot(
        df.index,
        df["cpu_time"],
        linestyle="-",
        linewidth=1.5,
        alpha=0.7,
        label="Cumulative CPU Time",
        color="tab:purple",
    )
    ax2.set_ylabel("CPU Time (seconds)")
    ax2.set_title("Cumulative CPU Time (User + System)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Third plot: Package counts
    ax3.plot(
        df.index,
        df["package_counts"],
        linestyle="-",
        linewidth=1.5,
        alpha=0.7,
        label="Package Counts",
        color="tab:green",
    )
    ax3.plot(
        df.index,
        df["package_buffer_counts"],
        linestyle="-",
        linewidth=1.5,
        alpha=0.7,
        label="Package Buffer Counts",
        color="tab:orange",
    )
    ax3.set_ylabel("Package Count")
    ax3.set_title("Package Counts Over Time")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Bottom plot: Database size
    ax4.plot(
        df.index,
        df["db_size"],
        linestyle="-",
        linewidth=1.5,
        alpha=0.7,
        label="DB Size",
        color="tab:blue",
    )
    ax4.set_xlabel("Time (seconds)")
    ax4.set_ylabel("Client database Size")
    ax4.set_title("Client database Size Over Time")
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_file)


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
        description="Plot profiling data from a results directory"
    )
    parser.add_argument(
        "results_dir",
        nargs="?",
        default=None,
        help="Path to the results directory containing log files (default: most recent in results/)",
    )

    args = parser.parse_args()

    # If no directory specified, use the most recent one
    if args.results_dir is None:
        results_dir = get_most_recent_results_dir()
        print(f"Using most recent results: {results_dir}")
    else:
        results_dir = args.results_dir

    df = load_results_directory(results_dir)
    plot_dataframe(df)


if __name__ == "__main__":
    main()
