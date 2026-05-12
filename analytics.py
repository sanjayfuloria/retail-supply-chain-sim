"""
Supply Chain Analytics
=======================
Runs the simulation and produces charts:
  1. Inventory levels over time per node
  2. Fill rate by week (retail stores)
  3. Daily demand vs filled — Store-1
  4. Cost breakdown per node (stacked bar)

Requires: matplotlib
"""

import sys
import statistics
import math
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from simulation import RetailSupplyChainSimulation


def run_and_plot(num_days: int = 365, seed: int = 42):
    sim = RetailSupplyChainSimulation(num_days=num_days, seed=seed)
    sim.run()

    if not HAS_MPL:
        print("\n[analytics] matplotlib not found — skipping charts. Install with: pip install matplotlib")
        return

    all_nodes = {"Warehouse": sim.warehouse, **sim.dcs, **sim.stores}
    days = list(range(1, num_days + 1))
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle("Retail Supply Chain Simulation — Analytics Dashboard", fontsize=14, fontweight="bold")

    # ── Chart 1: Inventory over time ─────────────────────────────────────────
    ax = axes[0, 0]
    for i, (name, node) in enumerate(all_nodes.items()):
        inv = [s.closing_stock for s in node.history]
        ax.plot(days, inv, label=name, linewidth=1.2, color=colors[i % len(colors)])
    ax.set_title("Inventory Levels Over Time")
    ax.set_xlabel("Day")
    ax.set_ylabel("Units On Hand")
    ax.legend(fontsize=7, loc="upper right")
    ax.grid(True, alpha=0.3)

    # ── Chart 2: Weekly fill rate (stores only) ───────────────────────────────
    ax = axes[0, 1]
    weekly: Dict = defaultdict(lambda: {"d": 0, "f": 0})
    for store in sim.stores.values():
        for snap in store.history:
            week = ((snap.day - 1) // 7) % 52 + 1
            weekly[week]["d"] += snap.demand
            weekly[week]["f"] += snap.units_filled

    weeks = sorted(weekly)
    rates = [weekly[w]["f"] / weekly[w]["d"] * 100 if weekly[w]["d"] else 100 for w in weeks]
    bar_colors = ["#e74c3c" if w >= 48 else "#3498db" for w in weeks]
    ax.bar(weeks, rates, color=bar_colors, width=0.8)
    ax.axhline(95, color="green", linestyle="--", linewidth=1, label="95% target")
    ax.set_title("Weekly Customer Fill Rate — All Retail Stores")
    ax.set_xlabel("Week of Year")
    ax.set_ylabel("Fill Rate (%)")
    ax.set_ylim(0, 105)
    peak_patch = mpatches.Patch(color="#e74c3c", label="Peak season (wks 48-52)")
    norm_patch = mpatches.Patch(color="#3498db", label="Normal weeks")
    ax.legend(handles=[peak_patch, norm_patch, ax.get_lines()[0]], fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)

    # ── Chart 3: Demand vs filled — Store-1 ──────────────────────────────────
    ax = axes[1, 0]
    s1 = sim.stores["Store-1"].history
    s1_days = [s.day for s in s1]
    s1_demand = [s.demand for s in s1]
    s1_filled = [s.units_filled for s in s1]
    ax.fill_between(s1_days, s1_demand, s1_filled, alpha=0.4, color="red", label="Unfulfilled demand")
    ax.plot(s1_days, s1_demand, linewidth=0.8, color="steelblue", label="Demand")
    ax.plot(s1_days, s1_filled, linewidth=0.8, color="green", label="Filled")
    ax.set_title("Store-1: Daily Demand vs Units Filled")
    ax.set_xlabel("Day")
    ax.set_ylabel("Units")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── Chart 4: Cost breakdown per node ─────────────────────────────────────
    ax = axes[1, 1]
    node_names = list(all_nodes.keys())
    holding = [sum(s.holding_cost for s in n.history) for n in all_nodes.values()]
    ordering = [sum(s.ordering_cost for s in n.history) for n in all_nodes.values()]
    shortage = [sum(s.shortage_cost for s in n.history) for n in all_nodes.values()]
    x = range(len(node_names))
    w = 0.5
    ax.bar(x, holding, w, label="Holding", color="#2ecc71")
    ax.bar(x, ordering, w, bottom=holding, label="Ordering", color="#3498db")
    ax.bar(x, shortage, w,
           bottom=[h + o for h, o in zip(holding, ordering)],
           label="Shortage", color="#e74c3c")
    ax.set_xticks(list(x))
    ax.set_xticklabels(node_names, rotation=30, ha="right", fontsize=8)
    ax.set_title("Annual Cost Breakdown by Node")
    ax.set_ylabel("Cost ($)")
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    out = "supply_chain_analytics.png"
    plt.savefig(out, dpi=150)
    print(f"\n[analytics] Chart saved to {out}")
    plt.close()


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 365
    run_and_plot(num_days=days)
