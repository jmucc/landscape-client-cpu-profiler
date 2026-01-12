"""
Plot profiling data from a results directory.
Loads CPU usage, database size, and package counts.
"""

import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd


def load_single_value_file(filepath):
    """Load a file where each line contains a single numeric value."""
    values = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    values.append(float(line))
                except ValueError:
                    continue
    return values


def load_comma_delimited_file(filepath):
    """Load a file where each line contains comma-delimited values and sum them."""
    values = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line == "(0rows)":
                values.append(0.0)
                continue

            try:
                nums = [float(n.strip()) for n in line.split(",")]
                values.append(sum(nums))
            except ValueError:
                continue

    return values


def load_results_directory(results_dir):
    """Load all log files from a results directory into a pandas DataFrame."""
    results_path = Path(results_dir)

    files = {
        "cpu_usage": ("cpu_usage.log", load_single_value_file),
        "db_size": ("db_size.log", load_single_value_file),
        "package_counts": ("package_counts.log", load_comma_delimited_file),
        "package_buffer_counts": (
            "package_buffer_counts.log",
            load_comma_delimited_file,
        ),
    }

    data = {}
    for column_name, (filename, loader_func) in files.items():
        filepath = results_path / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Expected file not found: {filepath}")
        data[column_name] = loader_func(filepath)

    return pd.DataFrame(data)


def normalize_series(series):
    """Normalize a pandas Series to [0, 1] range."""
    min_val = series.min()
    max_val = series.max()

    if max_val - min_val > 0:
        return (series - min_val) / (max_val - min_val)
    else:
        return series


def plot_dataframe(df, output_file="plot.png"):
    """Plot CPU usage, package counts, and database size on separate subplots with shared x-axis."""
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 14), sharex=True)

    # Top plot: CPU usage (raw percentage)
    ax1.plot(
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

    # Middle plot: Package counts
    ax2.plot(
        df["package_counts"],
        linestyle="-",
        linewidth=1.5,
        alpha=0.7,
        label="Package Counts",
        color="tab:green",
    )
    ax2.plot(
        df["package_buffer_counts"],
        linestyle="-",
        linewidth=1.5,
        alpha=0.7,
        label="Package Buffer Counts",
        color="tab:orange",
    )
    ax2.set_ylabel("Package Count")
    ax2.set_title("Package Counts Over Time")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Bottom plot: Database size
    ax3.plot(
        df["db_size"],
        linestyle="-",
        linewidth=1.5,
        alpha=0.7,
        label="DB Size",
        color="tab:blue",
    )
    ax3.set_xlabel("Iteration")
    ax3.set_ylabel("Client database Size")
    ax3.set_title("Client database Size Over Time")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

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
