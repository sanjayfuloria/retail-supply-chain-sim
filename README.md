# Retail Supply Chain Simulation

A discrete-event simulation of a multi-echelon retail supply chain modelling inventory management, stochastic demand, supplier lead times, seasonal peaks, and supply disruptions.

## Network Topology

```
External Suppliers (infinite capacity)
         │  lead time: 7–14 days
      Warehouse
         │  lead time: 2–4 days
   ┌─────┴─────┐
DC-North    DC-South        ← Distribution Centres
   │               │        lead time: 1–2 days
 ┌─┴─┐         ┌──┴──┐
S1  S2  S3    S4   S5        ← Retail Stores
```

## Features

| Feature | Details |
|---|---|
| Inventory policy | (s, S) periodic review — reorder point / order-up-to |
| Demand model | Uniform random with seasonal peak (weeks 48–52, 1.5–1.6× uplift) + weekend uplift |
| Lead times | Stochastic (uniform min–max) at every echelon |
| Unfulfilled demand | Backorders at warehouse & DCs; lost sales at stores |
| Costs tracked | Holding · Ordering (fixed) · Shortage |
| KPIs reported | Fill rate · Avg inventory · Replenishment orders · Cost breakdown |

## Quick Start

```bash
# clone and install
git clone <repo-url>
cd retail-supply-chain-sim
pip install -r requirements.txt

# run the baseline simulation (365 days)
python simulation.py

# generate analytics charts  →  supply_chain_analytics.png
python analytics.py

# run a specific scenario
python run_scenario.py lean_inventory --days 365

# compare all scenarios side-by-side
python run_scenario.py --compare-all
```

## Scenarios

| Name | Description |
|---|---|
| `baseline` | Default balanced inventory policy |
| `high_demand` | 2× mean demand — stress-tests stockout resilience |
| `long_lead_time` | Supplier lead time 14–21 days (port congestion) |
| `lean_inventory` | Low safety stock — just-in-time policy |
| `disruption` | Warehouse outage days 100–120 |

## Output

`simulation.py` prints a KPI table to the terminal:

```
Node         Fill%   Demand   Lost   AvgInv  Orders   HoldCost  ShortCost   TotalCost
──────────────────────────────────────────────────────────────────────────────────────
Warehouse    98.3%    9,240     12    4,821      14    $8,810     $108      $9,418
DC-North     97.1%    4,830     38    1,603      24    $2,970     $228      $3,798
...
```

`analytics.py` saves a 4-panel chart (`supply_chain_analytics.png`):
- Inventory levels over time
- Weekly customer fill rate
- Store-1 daily demand vs. fulfilled units
- Annual cost breakdown per node

## Project Structure

```
simulation.py       Core simulation engine (nodes, policies, step loop)
analytics.py        Matplotlib charts
config.py           Scenario definitions
run_scenario.py     CLI for running / comparing scenarios
requirements.txt    Python dependencies
```

## Extending the Simulation

- **Add a new store**: add a `NodeConfig` entry in `RetailSupplyChainSimulation.__init__` and a matching entry in `demand_params`.
- **Change inventory policy**: modify `review_and_order()` in `SupplyChainNode` (e.g. EOQ, min-max, base-stock).
- **Add a product SKU**: run separate `RetailSupplyChainSimulation` instances per SKU and aggregate results.
- **Add a new scenario**: add a `ScenarioOverrides` entry to `SCENARIOS` in `config.py`.
