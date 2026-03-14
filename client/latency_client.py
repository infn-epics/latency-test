#!/usr/bin/env python3
"""
EPICS CA Latency Measurement Client

Measures round-trip latency of caput/caget operations for three scenarios:
  1. Kubernetes Pod-to-Pod
  2. Bare Metal
  3. External Client to Kubernetes IOC

Usage:
    python3 latency_client.py [--iterations N] [--scenario NAME] [--output DIR]
"""

import argparse
import csv
import os
import sys
import time

import epics
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def wait_for_pv(pv_name: str, timeout: float = 30.0) -> epics.PV:
    """Connect to a PV and wait until it is connected."""
    pv = epics.PV(pv_name)
    pv.wait_for_connection(timeout=timeout)
    if not pv.connected:
        print(f"ERROR: Cannot connect to {pv_name} within {timeout}s")
        sys.exit(1)
    print(f"Connected to {pv_name}")
    return pv


def measure_latency(pv_set: epics.PV, pv_read: epics.PV,
                    iterations: int = 1000) -> list[float]:
    """
    Measure round-trip latency: caput(SET) then caget(READ).
    Returns list of RTT values in milliseconds.
    """
    rtts = []

    # Warm-up: a few cycles to stabilize connections
    for i in range(5):
        pv_set.put(float(i), wait=True)
        pv_read.get(use_monitor=False)

    print(f"Running {iterations} iterations...")
    for i in range(iterations):
        value = float(i % 10000)

        t_start = time.perf_counter()
        pv_set.put(value, wait=True)
        readback = pv_read.get(use_monitor=False)
        t_end = time.perf_counter()

        rtt_ms = (t_end - t_start) * 1000.0
        rtts.append(rtt_ms)

        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{iterations} completed "
                  f"(last RTT: {rtt_ms:.3f} ms)")

    return rtts


def compute_statistics(rtts: list[float]) -> dict:
    """Compute summary statistics from RTT measurements."""
    arr = np.array(rtts)
    return {
        "count": len(arr),
        "avg_ms": float(np.mean(arr)),
        "median_ms": float(np.median(arr)),
        "min_ms": float(np.min(arr)),
        "max_ms": float(np.max(arr)),
        "std_ms": float(np.std(arr)),
        "p95_ms": float(np.percentile(arr, 95)),
        "p99_ms": float(np.percentile(arr, 99)),
    }


def save_csv(rtts: list[float], filepath: str) -> None:
    """Save raw RTT measurements to CSV."""
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["iteration", "rtt_ms"])
        for i, rtt in enumerate(rtts):
            writer.writerow([i + 1, f"{rtt:.6f}"])
    print(f"Results saved to {filepath}")


def save_statistics(stats: dict, filepath: str) -> None:
    """Save summary statistics to CSV."""
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for key, val in stats.items():
            writer.writerow([key, f"{val:.6f}" if isinstance(val, float) else val])
    print(f"Statistics saved to {filepath}")


def plot_histogram(rtts: list[float], scenario: str, filepath: str) -> None:
    """Generate a latency histogram."""
    arr = np.array(rtts)

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.hist(arr, bins=50, edgecolor="black", alpha=0.7, color="#2196F3")
    ax.axvline(np.mean(arr), color="red", linestyle="--",
               label=f"Mean: {np.mean(arr):.3f} ms")
    ax.axvline(np.median(arr), color="green", linestyle="--",
               label=f"Median: {np.median(arr):.3f} ms")
    ax.axvline(np.percentile(arr, 95), color="orange", linestyle="--",
               label=f"P95: {np.percentile(arr, 95):.3f} ms")

    ax.set_xlabel("Round-Trip Time (ms)")
    ax.set_ylabel("Frequency")
    ax.set_title(f"EPICS CA Latency — {scenario}")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(filepath, dpi=150)
    plt.close(fig)
    print(f"Histogram saved to {filepath}")


def plot_timeseries(rtts: list[float], scenario: str, filepath: str) -> None:
    """Generate a time-series plot of RTTs."""
    arr = np.array(rtts)

    fig, ax = plt.subplots(1, 1, figsize=(12, 4))
    ax.plot(arr, linewidth=0.5, alpha=0.7, color="#2196F3")
    ax.axhline(np.mean(arr), color="red", linestyle="--", linewidth=1,
               label=f"Mean: {np.mean(arr):.3f} ms")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("RTT (ms)")
    ax.set_title(f"EPICS CA Latency Over Time — {scenario}")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(filepath, dpi=150)
    plt.close(fig)
    print(f"Time-series plot saved to {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="EPICS CA Round-Trip Latency Measurement")
    parser.add_argument("--iterations", "-n", type=int, default=1000,
                        help="Number of test iterations (default: 1000)")
    parser.add_argument("--scenario", "-s", type=str,
                        default="unknown",
                        choices=["bare-metal", "k8s-pod-to-pod",
                                 "external-to-k8s", "unknown"],
                        help="Scenario label for results")
    parser.add_argument("--output", "-o", type=str, default="./results",
                        help="Output directory for results")
    parser.add_argument("--set-pv", type=str, default="TEST:SET",
                        help="Setpoint PV name")
    parser.add_argument("--read-pv", type=str, default="TEST:READ",
                        help="Readback PV name")
    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    print("=" * 60)
    print(f"EPICS CA Latency Test — Scenario: {args.scenario}")
    print(f"  Iterations: {args.iterations}")
    print(f"  SET PV:     {args.set_pv}")
    print(f"  READ PV:    {args.read_pv}")
    print(f"  Output:     {args.output}")
    print("=" * 60)

    # Connect to PVs
    pv_set = wait_for_pv(args.set_pv)
    pv_read = wait_for_pv(args.read_pv)

    # Run measurement
    rtts = measure_latency(pv_set, pv_read, args.iterations)

    # Statistics
    stats = compute_statistics(rtts)
    print("\n" + "=" * 60)
    print("Results Summary:")
    print(f"  Average RTT:  {stats['avg_ms']:.3f} ms")
    print(f"  Median RTT:   {stats['median_ms']:.3f} ms")
    print(f"  Min RTT:      {stats['min_ms']:.3f} ms")
    print(f"  Max RTT:      {stats['max_ms']:.3f} ms")
    print(f"  Std Dev:      {stats['std_ms']:.3f} ms")
    print(f"  P95 RTT:      {stats['p95_ms']:.3f} ms")
    print(f"  P99 RTT:      {stats['p99_ms']:.3f} ms")
    print("=" * 60)

    # Save outputs
    prefix = args.scenario
    save_csv(rtts, os.path.join(args.output, f"{prefix}_latency.csv"))
    save_statistics(stats, os.path.join(args.output, f"{prefix}_stats.csv"))
    plot_histogram(rtts, args.scenario, os.path.join(args.output, f"{prefix}_histogram.png"))
    plot_timeseries(rtts, args.scenario, os.path.join(args.output, f"{prefix}_timeseries.png"))

    print("\nDone.")


if __name__ == "__main__":
    main()
