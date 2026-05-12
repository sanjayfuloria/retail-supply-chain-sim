"""
Configuration overrides for custom simulation scenarios.

Usage:
    python run_scenario.py <scenario_name>

Available scenarios:
    baseline       — default parameters
    high_demand    — 2× mean demand at all stores
    long_lead_time — supplier lead time 14-21 days
    lean_inventory — low reorder points and order-up-to levels
    disruption     — warehouse goes offline days 100-120 (no replenishment)
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ScenarioOverrides:
    name: str
    description: str
    warehouse_overrides: Dict[str, Any]
    dc_overrides: Dict[str, Any]
    store_overrides: Dict[str, Any]
    demand_multiplier: float = 1.0
    disruption_days: tuple = ()         # (start, end) — warehouse paused


SCENARIOS: Dict[str, ScenarioOverrides] = {
    "baseline": ScenarioOverrides(
        name="baseline",
        description="Default parameters — balanced inventory policy",
        warehouse_overrides={},
        dc_overrides={},
        store_overrides={},
    ),
    "high_demand": ScenarioOverrides(
        name="high_demand",
        description="2× mean demand — stress-tests stockout resilience",
        warehouse_overrides={"initial_inventory": 8000, "order_up_to": 10000},
        dc_overrides={"initial_inventory": 2500, "order_up_to": 3500},
        store_overrides={"initial_inventory": 500, "order_up_to": 700},
        demand_multiplier=2.0,
    ),
    "long_lead_time": ScenarioOverrides(
        name="long_lead_time",
        description="Supplier lead time 14-21 days (port congestion scenario)",
        warehouse_overrides={"lead_time_min": 14, "lead_time_max": 21,
                             "reorder_point": 2500, "order_up_to": 8000},
        dc_overrides={},
        store_overrides={},
    ),
    "lean_inventory": ScenarioOverrides(
        name="lean_inventory",
        description="Lean / just-in-time — low safety stock, high shortage risk",
        warehouse_overrides={"initial_inventory": 2000, "reorder_point": 500, "order_up_to": 3000},
        dc_overrides={"initial_inventory": 500, "reorder_point": 150, "order_up_to": 1000},
        store_overrides={"initial_inventory": 100, "reorder_point": 30, "order_up_to": 200},
    ),
    "disruption": ScenarioOverrides(
        name="disruption",
        description="Warehouse disruption days 100-120 (e.g. natural disaster)",
        warehouse_overrides={},
        dc_overrides={},
        store_overrides={},
        disruption_days=(100, 120),
    ),
}
