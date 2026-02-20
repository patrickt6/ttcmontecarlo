"""
Plot Travel Time Histogram.

Generates a publication-quality matplotlib histogram of Monte Carlo
simulation results, with threshold line and on-time probability annotation.

Usage:
    from src.viz.plot_histogram import plot_travel_time_histogram
    plot_travel_time_histogram(travel_times, threshold=35, route_info={...}, output_path="out.png")
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for saving PNGs
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


def plot_travel_time_histogram(
    travel_times: np.ndarray,
    threshold: float,
    route_info: dict,
    output_path: str,
) -> None:
    """
    Plot and save a histogram of simulated travel times.

    Args:
        travel_times: Array of simulated travel times (minutes).
        threshold: On-time threshold (minutes) — shown as vertical dashed line.
        route_info: Dict with keys: origin, destination, hour, day_type, runs.
        output_path: File path to save the PNG.
    """
    origin = route_info.get("origin", "?")
    destination = route_info.get("destination", "?")
    hour = route_info.get("hour", 0)
    day_type = route_info.get("day_type", "Weekday")
    runs = route_info.get("runs", len(travel_times))

    p_on_time = float(np.mean(travel_times <= threshold)) * 100
    mean_time = float(np.mean(travel_times))
    median_time = float(np.median(travel_times))

    # --- Figure setup ---
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    # --- Histogram ---
    # Color bins: on-time = teal, late = coral
    bin_edges = np.linspace(
        max(0, travel_times.min() - 2),
        travel_times.max() + 2,
        60,
    )
    n, bins, patches = ax.hist(
        travel_times, bins=bin_edges, density=True,
        edgecolor="none", alpha=0.9,
    )

    # Color patches based on threshold
    for patch, left_edge in zip(patches, bins[:-1]):
        if left_edge + (bins[1] - bins[0]) / 2 <= threshold:
            patch.set_facecolor("#00d2ff")  # teal for on-time
            patch.set_alpha(0.8)
        else:
            patch.set_facecolor("#ff6b6b")  # coral for late
            patch.set_alpha(0.8)

    # --- Threshold line ---
    ax.axvline(
        x=threshold, color="#ffd93d", linewidth=2.5,
        linestyle="--", label=f"Threshold ({threshold:.0f} min)",
        zorder=5,
    )

    # --- Mean line ---
    ax.axvline(
        x=mean_time, color="#6bcb77", linewidth=2,
        linestyle="-.", alpha=0.8, label=f"Mean ({mean_time:.1f} min)",
        zorder=5,
    )

    # --- Annotations ---
    # P(on-time) annotation
    y_max = ax.get_ylim()[1]
    if p_on_time >= 80:
        label = "ON-TIME"
        color = "#6bcb77"
    elif p_on_time >= 60:
        label = "CAUTION"
        color = "#ffd93d"
    else:
        label = "AT RISK"
        color = "#ff6b6b"

    ax.annotate(
        f"P(on-time) = {p_on_time:.1f}%  [{label}]",
        xy=(threshold, y_max * 0.85),
        xytext=(threshold + (travel_times.max() - threshold) * 0.3, y_max * 0.9),
        fontsize=14, fontweight="bold", color=color,
        arrowprops=dict(arrowstyle="->", color=color, lw=2),
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#1a1a2e", edgecolor=color, alpha=0.9),
    )

    # Stats box
    p5 = float(np.percentile(travel_times, 5))
    p95 = float(np.percentile(travel_times, 95))
    stats_text = (
        f"Median: {median_time:.1f} min\n"
        f"P5: {p5:.1f} min\n"
        f"P95: {p95:.1f} min\n"
        f"Runs: {runs:,}"
    )
    ax.text(
        0.02, 0.95, stats_text,
        transform=ax.transAxes, fontsize=11,
        verticalalignment="top", color="#e0e0e0",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#1a1a2e", edgecolor="#444", alpha=0.9),
        fontfamily="monospace",
    )

    # --- Labels and title ---
    ax.set_xlabel("Total Travel Time (minutes)", fontsize=13, color="#e0e0e0", labelpad=10)
    ax.set_ylabel("Density", fontsize=13, color="#e0e0e0", labelpad=10)
    ax.set_title(
        f"{origin}  -->  {destination}  |  {hour:02d}:00 {day_type}  |  Monte Carlo Distribution",
        fontsize=16, fontweight="bold", color="white", pad=15,
    )

    # --- Styling ---
    ax.tick_params(colors="#b0b0b0", labelsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#444")
    ax.spines["bottom"].set_color("#444")
    ax.legend(
        loc="upper right", fontsize=11,
        facecolor="#1a1a2e", edgecolor="#444",
        labelcolor="#e0e0e0",
    )
    ax.grid(axis="y", alpha=0.15, color="#666")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"[plot] Histogram saved to {output_path}")
