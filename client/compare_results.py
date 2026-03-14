#!/usr/bin/env python3
"""
Compare latency results across all three scenarios.
Reads CSV files from the results directory and generates a comparison report.

Usage:
    python3 compare_results.py [--results-dir DIR]
"""

import argparse
import csv
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


SCENARIOS = [
    ("bare-metal", "Bare Metal"),
    ("k8s-pod-to-pod", "K8s Pod-to-Pod"),
    ("external-to-k8s", "External → K8s IOC"),
]


def load_latency_csv(filepath: str) -> np.ndarray:
    """Load RTT values from a latency CSV file."""
    rtts = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rtts.append(float(row["rtt_ms"]))
    return np.array(rtts)


def print_comparison_table(data: dict[str, np.ndarray]) -> str:
    """Print a formatted comparison table and return as string."""
    header = f"{'Scenario':<25} {'Avg RTT':>10} {'Median':>10} {'Min':>10} {'Max':>10} {'StdDev':>10} {'P95':>10} {'P99':>10}"
    sep = "-" * len(header)
    lines = [sep, header, sep]

    for key, label in SCENARIOS:
        if key not in data:
            continue
        arr = data[key]
        lines.append(
            f"{label:<25} "
            f"{np.mean(arr):>9.3f}  "
            f"{np.median(arr):>9.3f}  "
            f"{np.min(arr):>9.3f}  "
            f"{np.max(arr):>9.3f}  "
            f"{np.std(arr):>9.3f}  "
            f"{np.percentile(arr, 95):>9.3f}  "
            f"{np.percentile(arr, 99):>9.3f}"
        )
    lines.append(sep)
    table = "\n".join(lines)
    print(table)
    return table


def plot_comparison_histogram(data: dict[str, np.ndarray], output: str) -> None:
    """Overlay histograms for all scenarios."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    colors = ["#4CAF50", "#2196F3", "#FF9800"]

    for (key, label), color in zip(SCENARIOS, colors):
        if key not in data:
            continue
        ax.hist(data[key], bins=50, alpha=0.5, label=label,
                edgecolor="black", linewidth=0.5, color=color)

    ax.set_xlabel("Round-Trip Time (ms)")
    ax.set_ylabel("Frequency")
    ax.set_title("EPICS CA Latency Comparison — All Scenarios")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"Comparison histogram saved to {output}")


def plot_comparison_boxplot(data: dict[str, np.ndarray], output: str) -> None:
    """Boxplot comparing all scenarios."""
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))

    plot_data = []
    labels = []
    for key, label in SCENARIOS:
        if key in data:
            plot_data.append(data[key])
            labels.append(label)

    bp = ax.boxplot(plot_data, labels=labels, patch_artist=True,
                    showfliers=True, flierprops=dict(markersize=2))

    colors = ["#4CAF50", "#2196F3", "#FF9800"]
    for patch, color in zip(bp["boxes"], colors[:len(plot_data)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set_ylabel("Round-Trip Time (ms)")
    ax.set_title("EPICS CA Latency — Box Plot Comparison")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"Comparison boxplot saved to {output}")


def plot_comparison_bar(data: dict[str, np.ndarray], output: str) -> None:
    """Bar chart of average latencies with error bars (std dev)."""
    fig, ax = plt.subplots(1, 1, figsize=(8, 5))

    names = []
    avgs = []
    stds = []
    colors = ["#4CAF50", "#2196F3", "#FF9800"]
    bar_colors = []

    for (key, label), color in zip(SCENARIOS, colors):
        if key in data:
            names.append(label)
            avgs.append(np.mean(data[key]))
            stds.append(np.std(data[key]))
            bar_colors.append(color)

    bars = ax.bar(names, avgs, yerr=stds, capsize=5, color=bar_colors,
                  alpha=0.7, edgecolor="black")

    for bar, avg in zip(bars, avgs):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                f"{avg:.3f} ms", ha="center", va="bottom", fontweight="bold")

    ax.set_ylabel("Average RTT (ms)")
    ax.set_title("EPICS CA Latency — Average Comparison")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    print(f"Comparison bar chart saved to {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Compare EPICS CA latency across scenarios")
    parser.add_argument("--results-dir", "-d", type=str, default="./results",
                        help="Directory containing scenario result CSVs")
    args = parser.parse_args()

    data = {}
    for key, label in SCENARIOS:
        filepath = os.path.join(args.results_dir, f"{key}_latency.csv")
        if os.path.exists(filepath):
            data[key] = load_latency_csv(filepath)
            print(f"Loaded {len(data[key])} measurements from {filepath}")
        else:
            print(f"WARNING: {filepath} not found — skipping {label}")

    if not data:
        print("ERROR: No result files found. Run latency tests first.")
        sys.exit(1)

    print()
    table = print_comparison_table(data)

    # Save comparison report
    report_path = os.path.join(args.results_dir, "comparison_report.txt")
    with open(report_path, "w") as f:
        f.write("EPICS CA Latency Comparison Report\n")
        f.write(f"Scenarios loaded: {len(data)}\n\n")
        f.write(table + "\n")
    print(f"\nReport saved to {report_path}")

    # Generate comparison plots
    plot_comparison_histogram(
        data, os.path.join(args.results_dir, "comparison_histogram.png"))
    plot_comparison_boxplot(
        data, os.path.join(args.results_dir, "comparison_boxplot.png"))
    plot_comparison_bar(
        data, os.path.join(args.results_dir, "comparison_bar.png"))

    print("\nDone.")


if __name__ == "__main__":
    main()
