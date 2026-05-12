"""
Scenario runner — applies config overrides and re-runs the simulation.

Usage:
    python run_scenario.py                   # lists available scenarios
    python run_scenario.py baseline
    python run_scenario.py high_demand
    python run_scenario.py disruption --days 180
"""

import sys
import argparse
import random
import math
import statistics
from collections import defaultdict

from config import SCENARIOS, ScenarioOverrides
from simulation import RetailSupplyChainSimulation, NodeConfig


def apply_overrides(cfg: NodeConfig, overrides: dict) -> NodeConfig:
    for k, v in overrides.items():
        if hasattr(cfg, k):
            object.__setattr__(cfg, k, v)
    return cfg


def build_sim_with_scenario(scenario: ScenarioOverrides, num_days: int, seed: int) -> RetailSupplyChainSimulation:
    sim = RetailSupplyChainSimulation(num_days=num_days, seed=seed)

    # Apply warehouse overrides
    apply_overrides(sim.warehouse.cfg, scenario.warehouse_overrides)
    sim.warehouse.inventory = sim.warehouse.cfg.initial_inventory

    # Apply DC overrides
    for dc in sim.dcs.values():
        apply_overrides(dc.cfg, scenario.dc_overrides)
        dc.inventory = dc.cfg.initial_inventory

    # Apply store overrides
    for store in sim.stores.values():
        apply_overrides(store.cfg, scenario.store_overrides)
        store.inventory = store.cfg.initial_inventory

    # Patch demand multiplier
    if scenario.demand_multiplier != 1.0:
        m = scenario.demand_multiplier
        sim.demand_params = {
            k: (int(v[0] * m), v[1], v[2])
            for k, v in sim.demand_params.items()
        }

    # Patch disruption: override _step to skip warehouse ordering during outage
    if scenario.disruption_days:
        start, end = scenario.disruption_days
        original_step = sim._step

        def disrupted_step(day: int):
            original_step(day)
            if start <= day <= end:
                # cancel any order placed today by the warehouse
                sim.warehouse.pending = [
                    o for o in sim.warehouse.pending if o.arrival_day != day + 1
                ]

        sim._step = disrupted_step
        print(f"  [scenario] Warehouse disruption active: days {start}-{end}")

    return sim


def compare_scenarios(scenario_names: list, num_days: int = 365):
    """Run multiple scenarios and print a side-by-side comparison."""
    results = {}
    for name in scenario_names:
        sc = SCENARIOS[name]
        sim = build_sim_with_scenario(sc, num_days=num_days, seed=42)
        print(f"\n─── Running scenario: {name} ───")
        print(f"    {sc.description}")
        sim.run()

        total_demand = sum(s.total_demand for s in sim.stores.values())
        total_filled = sum(s.total_filled for s in sim.stores.values())
        total_lost = sum(s.total_lost for s in sim.stores.values())
        total_cost = sum(
            sum(snap.holding_cost + snap.ordering_cost + snap.shortage_cost for snap in n.history)
            for n in {**sim.stores, **sim.dcs, "Warehouse": sim.warehouse}.values()
        )
        results[name] = {
            "fill_rate": total_filled / total_demand * 100 if total_demand else 100,
            "total_demand": total_demand,
            "lost_sales": total_lost,
            "total_cost": total_cost,
        }

    print(f"\n{'='*70}")
    print("  SCENARIO COMPARISON SUMMARY")
    print(f"{'='*70}")
    print(f"{'Scenario':<18} {'Fill Rate':>10} {'Demand':>9} {'Lost Sales':>11} {'Total Cost':>13}")
    print("-" * 65)
    for name, r in results.items():
        print(f"{name:<18} {r['fill_rate']:>9.1f}% {r['total_demand']:>9,} "
              f"{r['lost_sales']:>11,} ${r['total_cost']:>12,.2f}")


def main():
    parser = argparse.ArgumentParser(description="Retail Supply Chain Scenario Runner")
    parser.add_argument("scenario", nargs="?", help="Scenario name (omit to list all)")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--compare-all", action="store_true", help="Run and compare all scenarios")
    args = parser.parse_args()

    if args.compare_all:
        compare_scenarios(list(SCENARIOS.keys()), num_days=args.days)
        return

    if not args.scenario:
        print("\nAvailable scenarios:")
        for name, sc in SCENARIOS.items():
            print(f"  {name:<20} — {sc.description}")
        print("\nUsage: python run_scenario.py <scenario> [--days N] [--seed N]")
        print("       python run_scenario.py --compare-all")
        return

    if args.scenario not in SCENARIOS:
        print(f"Unknown scenario '{args.scenario}'. Run without args to list available scenarios.")
        sys.exit(1)

    sc = SCENARIOS[args.scenario]
    print(f"\nScenario  : {sc.name}")
    print(f"Details   : {sc.description}")
    sim = build_sim_with_scenario(sc, num_days=args.days, seed=args.seed)
    sim.run()


if __name__ == "__main__":
    main()
