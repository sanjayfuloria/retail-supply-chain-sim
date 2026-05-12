"""
Retail Supply Chain Simulation
================================
Multi-echelon supply chain: Suppliers → Warehouse → Distribution Centers → Retail Stores → Customers

Simulates:
  - Stochastic customer demand (Poisson)
  - Inventory management with (s, S) reorder policies
  - Variable lead times from suppliers
  - Backorder tracking and lost sales
  - Cost accounting: holding, ordering, shortage, transportation
  - KPIs: fill rate, service level, inventory turnover, total cost
"""

import random
import math
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import defaultdict


# ─────────────────────────── Data structures ────────────────────────────────

@dataclass
class PendingOrder:
    quantity: int
    arrival_day: int
    from_node: str


@dataclass
class DailySnapshot:
    day: int
    node: str
    opening_stock: int
    demand: int
    units_filled: int
    units_backordered: int
    units_lost: int
    orders_placed: int
    receipts: int
    closing_stock: int
    holding_cost: float
    ordering_cost: float
    shortage_cost: float


@dataclass
class NodeConfig:
    name: str
    initial_inventory: int
    reorder_point: int          # s — trigger a replenishment when stock ≤ s
    order_up_to: int            # S — order enough to bring stock up to S
    lead_time_min: int          # days
    lead_time_max: int
    holding_cost_per_unit: float
    ordering_cost_fixed: float
    shortage_cost_per_unit: float   # per unit per day
    allow_backorders: bool = True
    supplier: Optional[str] = None  # name of upstream node / external supplier


# ─────────────────────────── Supply chain nodes ─────────────────────────────

class SupplyChainNode:
    def __init__(self, config: NodeConfig):
        self.cfg = config
        self.name = config.name
        self.inventory = config.initial_inventory
        self.backorders: int = 0
        self.pending: List[PendingOrder] = []
        self.history: List[DailySnapshot] = []
        self.total_demand = 0
        self.total_filled = 0
        self.total_lost = 0

    def receive_shipments(self, day: int) -> int:
        arriving = [o for o in self.pending if o.arrival_day <= day]
        received = sum(o.quantity for o in arriving)
        self.pending = [o for o in self.pending if o.arrival_day > day]
        self.inventory += received
        return received

    def place_order(self, day: int, quantity: int) -> None:
        if quantity <= 0:
            return
        lead = random.randint(self.cfg.lead_time_min, self.cfg.lead_time_max)
        self.pending.append(PendingOrder(quantity, day + lead, self.cfg.supplier or "external"))

    def process_demand(self, demand: int) -> tuple[int, int, int]:
        """Returns (filled, backordered, lost)."""
        available = self.inventory + self.backorders  # backorders from prev days reduce available
        # first satisfy any outstanding backorders
        bo_fill = min(self.backorders, self.inventory)
        self.inventory -= bo_fill
        self.backorders -= bo_fill

        # now serve today's demand
        can_fill = min(demand, self.inventory)
        self.inventory -= can_fill
        unmet = demand - can_fill

        if unmet > 0:
            if self.cfg.allow_backorders:
                self.backorders += unmet
                return can_fill, unmet, 0
            else:
                return can_fill, 0, unmet
        return can_fill, 0, 0

    def review_and_order(self, day: int) -> int:
        """Periodic review (s, S) policy. Returns quantity ordered."""
        on_hand_plus_pipeline = self.inventory + sum(o.quantity for o in self.pending)
        if on_hand_plus_pipeline <= self.cfg.reorder_point:
            qty = self.cfg.order_up_to - on_hand_plus_pipeline
            if qty > 0:
                self.place_order(day, qty)
                return qty
        return 0

    def record(self, day: int, opening: int, demand: int,
               filled: int, bo: int, lost: int, ordered: int, received: int):
        holding = max(0, self.inventory) * self.cfg.holding_cost_per_unit
        ordering = self.cfg.ordering_cost_fixed if ordered > 0 else 0.0
        shortage = (bo + lost) * self.cfg.shortage_cost_per_unit
        self.history.append(DailySnapshot(
            day=day, node=self.name,
            opening_stock=opening, demand=demand,
            units_filled=filled, units_backordered=bo, units_lost=lost,
            orders_placed=ordered, receipts=received,
            closing_stock=self.inventory,
            holding_cost=holding, ordering_cost=ordering, shortage_cost=shortage
        ))
        self.total_demand += demand
        self.total_filled += filled
        self.total_lost += lost


# ─────────────────────────── Simulation engine ──────────────────────────────

class RetailSupplyChainSimulation:
    """
    Network topology (default):

        External Suppliers (infinite)
               │  (lead 7-14 days)
           Warehouse
               │  (lead 2-4 days)
        ┌──────┴──────┐
      DC-North      DC-South   (Distribution Centers)
        │               │
      ┌─┴─┐          ┌──┴──┐
    S1  S2  S3      S4   S5     (Retail Stores)
    """

    def __init__(self, num_days: int = 365, seed: int = 42):
        self.num_days = num_days
        random.seed(seed)

        # ── warehouse ────────────────────────────────────────────────────────
        self.warehouse = SupplyChainNode(NodeConfig(
            name="Warehouse",
            initial_inventory=5000,
            reorder_point=1500,
            order_up_to=6000,
            lead_time_min=7,
            lead_time_max=14,
            holding_cost_per_unit=0.05,
            ordering_cost_fixed=500.0,
            shortage_cost_per_unit=1.50,
            allow_backorders=True,
            supplier="external",
        ))

        # ── distribution centers ─────────────────────────────────────────────
        dc_configs = [
            NodeConfig("DC-North", 1500, 400, 2000, 2, 4, 0.08, 200.0, 2.00, True, "Warehouse"),
            NodeConfig("DC-South", 1500, 400, 2000, 2, 4, 0.08, 200.0, 2.00, True, "Warehouse"),
        ]
        self.dcs: Dict[str, SupplyChainNode] = {c.name: SupplyChainNode(c) for c in dc_configs}

        # ── retail stores ────────────────────────────────────────────────────
        store_configs = [
            NodeConfig("Store-1", 300, 80, 400, 1, 2, 0.15, 50.0, 5.00, False, "DC-North"),
            NodeConfig("Store-2", 300, 80, 400, 1, 2, 0.15, 50.0, 5.00, False, "DC-North"),
            NodeConfig("Store-3", 250, 60, 350, 1, 3, 0.15, 50.0, 5.00, False, "DC-North"),
            NodeConfig("Store-4", 300, 80, 400, 1, 2, 0.15, 50.0, 5.00, False, "DC-South"),
            NodeConfig("Store-5", 300, 80, 400, 1, 2, 0.15, 50.0, 5.00, False, "DC-South"),
        ]
        self.stores: Dict[str, SupplyChainNode] = {c.name: SupplyChainNode(c) for c in store_configs}

        # demand parameters per store: (mean_daily, seasonal_peak_factor, peak_weeks)
        self.demand_params = {
            "Store-1": (30, 1.6, [48, 49, 50, 51, 52]),
            "Store-2": (25, 1.5, [48, 49, 50, 51, 52]),
            "Store-3": (20, 1.4, [48, 49, 50, 51, 52]),
            "Store-4": (28, 1.6, [48, 49, 50, 51, 52]),
            "Store-5": (22, 1.5, [48, 49, 50, 51, 52]),
        }

        self.results: Dict[str, List] = defaultdict(list)

    # ── demand generation ────────────────────────────────────────────────────

    def _generate_demand(self, store_name: str, day: int) -> int:
        mean, peak_factor, peak_weeks = self.demand_params[store_name]
        week = ((day - 1) // 7) % 52 + 1
        is_weekend = (day % 7) in (0, 6)
        effective_mean = mean * (peak_factor if week in peak_weeks else 1.0)
        effective_mean *= (1.3 if is_weekend else 1.0)
        return random.randint(0, 2 * int(effective_mean))  # uniform ± mean

    # ── aggregate demand from downstream ─────────────────────────────────────

    def _aggregate_store_orders(self, dc_name: str) -> int:
        """Sum of all orders placed by stores that source from this DC today."""
        return sum(
            sum(o.quantity for o in s.pending if o.arrival_day == -1)  # sentinel: same-day
            for s in self.stores.values()
            if s.cfg.supplier == dc_name
        )

    # ── single-day step ───────────────────────────────────────────────────────

    def _step(self, day: int):
        # 1. Receive inbound shipments at all echelons
        for node in [self.warehouse, *self.dcs.values(), *self.stores.values()]:
            node.receive_shipments(day)

        # 2. Retail stores serve customers, then reorder from DCs
        store_dc_demand: Dict[str, int] = defaultdict(int)
        for name, store in self.stores.items():
            opening = store.inventory
            demand = self._generate_demand(name, day)
            filled, bo, lost = store.process_demand(demand)
            ordered = store.review_and_order(day)
            if ordered:
                store_dc_demand[store.cfg.supplier] += ordered
            store.record(day, opening, demand, filled, bo, lost, ordered, 0)

        # 3. Distribution centers serve store replenishment orders, then reorder from warehouse
        dc_wh_demand: int = 0
        for name, dc in self.dcs.items():
            opening = dc.inventory
            demand = store_dc_demand.get(name, 0)
            filled, bo, lost = dc.process_demand(demand)
            ordered = dc.review_and_order(day)
            if ordered:
                dc_wh_demand += ordered
            dc.record(day, opening, demand, filled, bo, lost, ordered, 0)

        # 4. Warehouse serves DC replenishment, then orders from external suppliers
        wh = self.warehouse
        opening = wh.inventory
        demand = dc_wh_demand
        filled, bo, lost = wh.process_demand(demand)
        ordered = wh.review_and_order(day)
        wh.record(day, opening, demand, filled, bo, lost, ordered, 0)

    # ── run ───────────────────────────────────────────────────────────────────

    def run(self):
        print(f"\n{'='*60}")
        print("  RETAIL SUPPLY CHAIN SIMULATION")
        print(f"  Simulation period: {self.num_days} days")
        print(f"{'='*60}\n")

        for day in range(1, self.num_days + 1):
            self._step(day)

        self._report()

    # ── reporting ─────────────────────────────────────────────────────────────

    def _node_kpis(self, node: SupplyChainNode) -> Dict:
        h = node.history
        total_holding = sum(s.holding_cost for s in h)
        total_ordering = sum(s.ordering_cost for s in h)
        total_shortage = sum(s.shortage_cost for s in h)
        total_cost = total_holding + total_ordering + total_shortage
        fill_rate = (node.total_filled / node.total_demand * 100) if node.total_demand else 100
        avg_inv = statistics.mean(s.closing_stock for s in h) if h else 0
        num_orders = sum(1 for s in h if s.orders_placed > 0)
        return {
            "fill_rate_%": round(fill_rate, 2),
            "total_demand": node.total_demand,
            "total_filled": node.total_filled,
            "total_lost": node.total_lost,
            "avg_inventory": round(avg_inv, 1),
            "num_replenishment_orders": num_orders,
            "holding_cost": round(total_holding, 2),
            "ordering_cost": round(total_ordering, 2),
            "shortage_cost": round(total_shortage, 2),
            "total_cost": round(total_cost, 2),
        }

    def _report(self):
        all_nodes = {"Warehouse": self.warehouse, **self.dcs, **self.stores}

        print(f"{'Node':<12} {'Fill%':>7} {'Demand':>8} {'Lost':>6} "
              f"{'AvgInv':>8} {'Orders':>7} {'HoldCost':>10} {'ShortCost':>10} {'TotalCost':>11}")
        print("-" * 90)

        grand_total_cost = 0.0
        grand_demand = 0
        grand_filled = 0

        for node_name, node in all_nodes.items():
            k = self._node_kpis(node)
            grand_total_cost += k["total_cost"]
            grand_demand += k["total_demand"]
            grand_filled += k["total_filled"]
            print(f"{node_name:<12} {k['fill_rate_%']:>7.1f}% {k['total_demand']:>8,} "
                  f"{k['total_lost']:>6,} {k['avg_inventory']:>8.0f} "
                  f"{k['num_replenishment_orders']:>7} "
                  f"${k['holding_cost']:>9,.2f} ${k['shortage_cost']:>9,.2f} "
                  f"${k['total_cost']:>10,.2f}")

        overall_fill = grand_filled / grand_demand * 100 if grand_demand else 100
        print("-" * 90)
        print(f"\n  Overall customer fill rate : {overall_fill:.2f}%")
        print(f"  Total supply chain cost    : ${grand_total_cost:,.2f}")
        print(f"  Simulation days            : {self.num_days}")
        print()

        self._inventory_trend_summary(all_nodes)
        self._seasonal_analysis()

    def _inventory_trend_summary(self, nodes: Dict[str, SupplyChainNode]):
        print(f"\n{'─'*60}")
        print("  MONTHLY AVERAGE INVENTORY LEVELS")
        print(f"{'─'*60}")
        months = {m: [] for m in range(1, 13)}
        for name, node in nodes.items():
            for snap in node.history:
                month = math.ceil(snap.day / 30.44)
                month = min(month, 12)
                months[month].append((name, snap.closing_stock))

        node_names = list(nodes.keys())
        header = f"{'Month':<8}" + "".join(f"{n[:9]:>10}" for n in node_names)
        print(header)
        for m in range(1, 13):
            snaps = months[m]
            row = f"Month {m:<3}"
            for name in node_names:
                vals = [s for n, s in snaps if n == name]
                avg = statistics.mean(vals) if vals else 0
                row += f"{avg:>10.0f}"
            print(row)

    def _seasonal_analysis(self):
        print(f"\n{'─'*60}")
        print("  SEASONAL DEMAND ANALYSIS (Retail Stores)")
        print(f"{'─'*60}")
        print(f"{'Week':>6} {'Total Demand':>14} {'Units Filled':>13} {'Fill Rate':>10}")
        weekly: Dict[int, Dict] = defaultdict(lambda: {"demand": 0, "filled": 0})
        for store in self.stores.values():
            for snap in store.history:
                week = ((snap.day - 1) // 7) % 52 + 1
                weekly[week]["demand"] += snap.demand
                weekly[week]["filled"] += snap.units_filled

        for week in sorted(weekly):
            d = weekly[week]["demand"]
            f = weekly[week]["filled"]
            rate = f / d * 100 if d else 100
            marker = " ◄ PEAK" if week >= 48 else ""
            print(f"{week:>6} {d:>14,} {f:>13,} {rate:>9.1f}%{marker}")


# ─────────────────────────── Entry point ─────────────────────────────────────

if __name__ == "__main__":
    sim = RetailSupplyChainSimulation(num_days=365, seed=42)
    sim.run()
