import os
from typing import Dict, List, Optional
import matplotlib.pyplot as plt


# Set high quality plotting defaults
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#333333"
plt.rcParams["axes.linewidth"] = 0.8


def ensure_plot_dir(output_dir: str = "plots") -> str:
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def plot_simulation_vs_theory(
    x_vals: List[float],
    sim_means: List[float],
    sim_ci_halfs: List[float],
    theory_vals: List[float],
    x_label: str = "Traffic Intensity (rho)",
    y_label: str = "Average Response Time W (seconds)",
    title: str = "Validation: Simulation vs Analytical Theory (95% CI)",
    filename: str = "validation_plot.png",
    output_dir: str = "plots"
) -> str:
    """Generates comparison plot with theory curve and simulation confidence intervals."""
    ensure_plot_dir(output_dir)
    filepath = os.path.join(output_dir, filename)

    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)

    # Plot continuous theoretical curve
    ax.plot(x_vals, theory_vals, label="Analytical (Theory)", color="#1f77b4", linewidth=2.0)

    # Plot discrete simulation points with Student's t 95% error bars
    ax.errorbar(
        x_vals,
        sim_means,
        yerr=sim_ci_halfs,
        fmt="o",
        color="#d62728",
        ecolor="#d62728",
        elinewidth=1.5,
        capsize=4,
        capthick=1.2,
        label="Simulation (Mean +/- 95% CI)",
        markersize=6
    )

    ax.set_xlabel(x_label, fontsize=12, fontweight="bold")
    ax.set_ylabel(y_label, fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(frameon=True, facecolor="white", edgecolor="#cccccc", fontsize=10)

    plt.tight_layout()
    fig.savefig(filepath, dpi=300)
    plt.close(fig)
    return filepath


def plot_sensitivity_buffer(
    k_vals: List[int],
    drop_rates: List[float],
    wait_times: List[float],
    title: str = "Sensitivity Analysis: Buffer Capacity K Trade-off",
    filename: str = "sensitivity_buffer.png",
    output_dir: str = "plots"
) -> str:
    """Plots the dual-axis trade-off curve between drop rate (Pb) and latency as K varies."""
    ensure_plot_dir(output_dir)
    filepath = os.path.join(output_dir, filename)

    fig, ax1 = plt.subplots(figsize=(8, 5), dpi=300)

    color1 = "#d62728"
    ax1.set_xlabel("Buffer Capacity (K)", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Drop Probability (Pb)", color=color1, fontsize=12, fontweight="bold")
    line1 = ax1.plot(k_vals, drop_rates, "o-", color=color1, linewidth=2, label="Drop Rate (Pb)")
    ax1.tick_params(axis="y", labelcolor=color1)
    ax1.grid(True, linestyle="--", alpha=0.5)

    ax2 = ax1.twinx()
    color2 = "#1f77b4"
    ax2.set_ylabel("Average Waiting Time Wq (s)", color=color2, fontsize=12, fontweight="bold")
    line2 = ax2.plot(k_vals, wait_times, "s--", color=color2, linewidth=2, label="Waiting Time (Wq)")
    ax2.tick_params(axis="y", labelcolor=color2)

    # Combined legend
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc="center right", facecolor="white", edgecolor="#cccccc")

    plt.title(title, fontsize=13, fontweight="bold", pad=12)
    plt.tight_layout()
    fig.savefig(filepath, dpi=300)
    plt.close(fig)
    return filepath


def plot_network_bottleneck(
    node_names: List[str],
    utilizations: List[float],
    title: str = "Queuing Network: Resource Utilization & Bottleneck Identification",
    filename: str = "network_bottleneck.png",
    output_dir: str = "plots"
) -> str:
    """Generates bar chart highlighting the highest utilization bottleneck node."""
    ensure_plot_dir(output_dir)
    filepath = os.path.join(output_dir, filename)

    fig, ax = plt.subplots(figsize=(8, 4.8), dpi=300)

    max_util = max(utilizations) if utilizations else 0.0
    colors = ["#d62728" if u == max_util else "#1f77b4" for u in utilizations]

    bars = ax.bar(node_names, utilizations, color=colors, width=0.55, edgecolor="#222222")

    # Add text labels on top of bars
    for bar, u in zip(bars, utilizations):
        height = bar.get_height()
        ax.annotate(
            f"{u*100:.1f}%",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold"
        )

    ax.axhline(1.0, color="gray", linestyle=":", label="100% Saturation limit")
    ax.set_ylabel("Utilization (rho)", fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    ax.set_ylim(0, max(1.15, max_util * 1.25))
    ax.grid(axis="y", linestyle="--", alpha=0.6)
    ax.legend(loc="upper left")

    plt.tight_layout()
    fig.savefig(filepath, dpi=300)
    plt.close(fig)
    return filepath
