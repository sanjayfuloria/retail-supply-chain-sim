"""
Retail Supply Chain Simulation — Web Interface (Vercel entry point)
"""

import io
import sys
from flask import Flask, request, jsonify, render_template_string
from config import SCENARIOS
from simulation import RetailSupplyChainSimulation

app = Flask(__name__)

# ── HTML template ─────────────────────────────────────────────────────────────

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Retail Supply Chain Simulation</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f0f4f8; color: #1a202c; }
    header { background: #1a365d; color: white; padding: 1.5rem 2rem; }
    header h1 { font-size: 1.5rem; }
    header p  { font-size: 0.875rem; color: #90cdf4; margin-top: 0.25rem; }
    main { max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }

    .card { background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,.08); padding: 1.5rem; margin-bottom: 1.5rem; }
    .card h2 { font-size: 1rem; font-weight: 600; color: #2d3748; margin-bottom: 1rem; border-bottom: 1px solid #e2e8f0; padding-bottom: .5rem; }

    .form-row { display: flex; gap: 1rem; flex-wrap: wrap; align-items: flex-end; }
    .form-group { display: flex; flex-direction: column; gap: .3rem; flex: 1; min-width: 140px; }
    label { font-size: .8rem; font-weight: 500; color: #4a5568; }
    select, input[type=number] { padding: .45rem .65rem; border: 1px solid #cbd5e0; border-radius: 6px; font-size: .9rem; }
    button { padding: .55rem 1.4rem; background: #2b6cb0; color: white; border: none; border-radius: 6px; font-size: .9rem; font-weight: 600; cursor: pointer; white-space: nowrap; }
    button:hover { background: #2c5282; }
    button:disabled { background: #a0aec0; cursor: not-allowed; }

    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; }
    .kpi { background: #ebf8ff; border-left: 4px solid #3182ce; border-radius: 6px; padding: .85rem 1rem; }
    .kpi .label { font-size: .75rem; color: #4a5568; text-transform: uppercase; letter-spacing: .05em; }
    .kpi .value { font-size: 1.5rem; font-weight: 700; color: #1a365d; margin-top: .15rem; }
    .kpi .sub   { font-size: .75rem; color: #718096; margin-top: .1rem; }

    table { width: 100%; border-collapse: collapse; font-size: .85rem; }
    th { background: #2d3748; color: white; padding: .55rem .75rem; text-align: right; }
    th:first-child { text-align: left; }
    td { padding: .5rem .75rem; border-bottom: 1px solid #e2e8f0; text-align: right; }
    td:first-child { text-align: left; font-weight: 500; }
    tr:nth-child(even) td { background: #f7fafc; }
    tr.total td { background: #ebf8ff; font-weight: 700; border-top: 2px solid #3182ce; }

    .fill-bar { display: inline-block; background: #e2e8f0; border-radius: 4px; width: 80px; height: 8px; vertical-align: middle; margin-right: 6px; }
    .fill-bar span { display: block; height: 100%; border-radius: 4px; }

    .monthly-table th, .monthly-table td { font-size: .78rem; padding: .4rem .55rem; }

    .seasonal-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(62px, 1fr)); gap: .35rem; }
    .week-cell { border-radius: 5px; padding: .35rem .4rem; text-align: center; font-size: .75rem; }
    .week-cell .wk  { font-weight: 600; color: #4a5568; }
    .week-cell .pct { font-weight: 700; }

    #spinner { display: none; align-items: center; gap: .5rem; color: #4a5568; font-size: .9rem; padding: .5rem 0; }
    .spin { width: 18px; height: 18px; border: 3px solid #cbd5e0; border-top-color: #2b6cb0; border-radius: 50%; animation: spin .7s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .observations { list-style: none; }
    .observations li { padding: .4rem 0; border-bottom: 1px solid #e2e8f0; font-size: .875rem; color: #2d3748; }
    .observations li::before { content: "▸ "; color: #3182ce; font-weight: bold; }
    .tag { display: inline-block; background: #fed7d7; color: #c53030; font-size: .7rem; font-weight: 600; border-radius: 3px; padding: .1rem .35rem; margin-left: .3rem; vertical-align: middle; }
    .tag.ok { background: #c6f6d5; color: #276749; }
  </style>
</head>
<body>
<header>
  <h1>Retail Supply Chain Simulation</h1>
  <p>Multi-echelon model · Suppliers → Warehouse → Distribution Centres → Retail Stores</p>
</header>
<main>

  <div class="card">
    <h2>Configure &amp; Run</h2>
    <div class="form-row">
      <div class="form-group">
        <label for="scenario">Scenario</label>
        <select id="scenario">
          {% for name, sc in scenarios.items() %}
          <option value="{{ name }}">{{ name }} — {{ sc.description }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="form-group" style="max-width:130px">
        <label for="days">Simulation days</label>
        <input type="number" id="days" value="365" min="30" max="1095" />
      </div>
      <div class="form-group" style="max-width:110px">
        <label for="seed">Random seed</label>
        <input type="number" id="seed" value="42" min="0" max="99999" />
      </div>
      <button id="runBtn" onclick="runSim()">Run Simulation</button>
    </div>
    <div id="spinner" style="margin-top:.75rem"><div class="spin"></div> Running simulation…</div>
  </div>

  <div id="results" style="display:none">

    <div class="card">
      <h2>Overall KPIs</h2>
      <div class="kpi-grid" id="kpiGrid"></div>
    </div>

    <div class="card">
      <h2>Node-Level Results</h2>
      <table id="nodeTable">
        <thead><tr>
          <th>Node</th><th>Fill Rate</th><th>Demand</th><th>Lost Sales</th>
          <th>Avg Inventory</th><th>Replen. Orders</th>
          <th>Holding Cost</th><th>Shortage Cost</th><th>Total Cost</th>
        </tr></thead>
        <tbody id="nodeBody"></tbody>
      </table>
    </div>

    <div class="card">
      <h2>Monthly Average Inventory</h2>
      <div style="overflow-x:auto">
        <table class="monthly-table" id="monthlyTable"></table>
      </div>
    </div>

    <div class="card">
      <h2>Weekly Fill Rate — Retail Stores</h2>
      <div class="seasonal-grid" id="weekGrid"></div>
    </div>

    <div class="card">
      <h2>Key Observations</h2>
      <ul class="observations" id="obsList"></ul>
    </div>

  </div>
</main>

<script>
async function runSim() {
  const btn = document.getElementById('runBtn');
  btn.disabled = true;
  document.getElementById('spinner').style.display = 'flex';
  document.getElementById('results').style.display = 'none';

  const payload = {
    scenario: document.getElementById('scenario').value,
    days: parseInt(document.getElementById('days').value),
    seed: parseInt(document.getElementById('seed').value),
  };

  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.error) { alert('Simulation error: ' + data.error); return; }
    render(data);
    document.getElementById('results').style.display = 'block';
  } catch(e) {
    alert('Request failed: ' + e);
  } finally {
    btn.disabled = false;
    document.getElementById('spinner').style.display = 'none';
  }
}

function fmt(n)  { return n.toLocaleString(); }
function fmtC(n) { return '$' + n.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2}); }

function fillColor(pct) {
  if (pct >= 99) return '#38a169';
  if (pct >= 95) return '#d69e2e';
  return '#e53e3e';
}

function render(d) {
  // KPIs
  const kpis = [
    { label:'Overall Fill Rate', value: d.summary.fill_rate.toFixed(2) + '%', sub: 'customer service level' },
    { label:'Total Supply Chain Cost', value: fmtC(d.summary.total_cost), sub: 'holding + ordering + shortage' },
    { label:'Total Units Demanded', value: fmt(d.summary.total_demand), sub: 'all retail stores' },
    { label:'Total Lost Sales', value: fmt(d.summary.total_lost), sub: 'units, store level' },
    { label:'Simulation Period', value: d.summary.days + ' days', sub: d.summary.scenario + ' scenario' },
  ];
  document.getElementById('kpiGrid').innerHTML = kpis.map(k =>
    `<div class="kpi"><div class="label">${k.label}</div><div class="value">${k.value}</div><div class="sub">${k.sub}</div></div>`
  ).join('');

  // Node table
  const tbody = document.getElementById('nodeBody');
  tbody.innerHTML = d.nodes.map(n => {
    const pct = n.fill_rate;
    const bar = `<div class="fill-bar"><span style="width:${pct}%;background:${fillColor(pct)}"></span></div>`;
    return `<tr>
      <td>${n.name}</td>
      <td>${bar}${pct.toFixed(1)}%</td>
      <td>${fmt(n.total_demand)}</td>
      <td>${fmt(n.total_lost)}</td>
      <td>${fmt(Math.round(n.avg_inventory))}</td>
      <td>${fmt(n.num_orders)}</td>
      <td>${fmtC(n.holding_cost)}</td>
      <td>${fmtC(n.shortage_cost)}</td>
      <td>${fmtC(n.total_cost)}</td>
    </tr>`;
  }).join('') +
  `<tr class="total">
    <td>TOTAL</td><td></td><td></td><td></td><td></td><td></td>
    <td>${fmtC(d.nodes.reduce((s,n)=>s+n.holding_cost,0))}</td>
    <td>${fmtC(d.nodes.reduce((s,n)=>s+n.shortage_cost,0))}</td>
    <td>${fmtC(d.summary.total_cost)}</td>
  </tr>`;

  // Monthly inventory
  const mt = document.getElementById('monthlyTable');
  const nodeNames = d.nodes.map(n => n.name);
  mt.innerHTML =
    `<thead><tr><th>Month</th>${nodeNames.map(n=>`<th>${n}</th>`).join('')}</tr></thead>` +
    `<tbody>${d.monthly.map((row,i) =>
      `<tr><td>Month ${i+1}</td>${nodeNames.map(n => `<td>${fmt(Math.round(row[n]||0))}</td>`).join('')}</tr>`
    ).join('')}</tbody>`;

  // Weekly fill rate
  const wg = document.getElementById('weekGrid');
  wg.innerHTML = d.weekly.map(w => {
    const pct = w.fill_rate;
    const bg = pct >= 99 ? '#c6f6d5' : pct >= 95 ? '#fefcbf' : '#fed7d7';
    const tc = pct >= 99 ? '#276749' : pct >= 95 ? '#744210' : '#c53030';
    const peak = w.week >= 48 ? ' 🎄' : '';
    return `<div class="week-cell" style="background:${bg}">
      <div class="wk">Wk ${w.week}${peak}</div>
      <div class="pct" style="color:${tc}">${pct.toFixed(1)}%</div>
    </div>`;
  }).join('');

  // Observations
  document.getElementById('obsList').innerHTML = d.observations.map(o =>
    `<li>${o.text}${o.flag ? `<span class="tag ${o.flag}">${o.flag.toUpperCase()}</span>` : ''}</li>`
  ).join('');
}

// Auto-run on load
window.onload = () => runSim();
</script>
</body>
</html>
"""

# ── API helpers ───────────────────────────────────────────────────────────────

def _node_kpis(node):
    h = node.history
    holding  = sum(s.holding_cost  for s in h)
    ordering = sum(s.ordering_cost for s in h)
    shortage = sum(s.shortage_cost for s in h)
    avg_inv  = sum(s.closing_stock for s in h) / len(h) if h else 0
    num_ord  = sum(1 for s in h if s.orders_placed > 0)
    fill     = node.total_filled / node.total_demand * 100 if node.total_demand else 100
    return {
        "name": node.name,
        "fill_rate": round(fill, 2),
        "total_demand": node.total_demand,
        "total_lost": node.total_lost,
        "avg_inventory": round(avg_inv, 1),
        "num_orders": num_ord,
        "holding_cost": round(holding, 2),
        "ordering_cost": round(ordering, 2),
        "shortage_cost": round(shortage, 2),
        "total_cost": round(holding + ordering + shortage, 2),
    }


def _monthly_inventory(all_nodes, num_days):
    import math
    months = [{} for _ in range(12)]
    counts = [{} for _ in range(12)]
    for name, node in all_nodes.items():
        for snap in node.history:
            m = min(math.ceil(snap.day / 30.44), 12) - 1
            months[m][name] = months[m].get(name, 0) + snap.closing_stock
            counts[m][name] = counts[m].get(name, 0) + 1
    return [
        {name: months[m].get(name, 0) / counts[m].get(name, 1) for name in all_nodes}
        for m in range(12)
    ]


def _weekly_fill(stores):
    from collections import defaultdict
    weekly = defaultdict(lambda: {"d": 0, "f": 0})
    for store in stores.values():
        for snap in store.history:
            w = ((snap.day - 1) // 7) % 52 + 1
            weekly[w]["d"] += snap.demand
            weekly[w]["f"] += snap.units_filled
    return [
        {"week": w, "demand": weekly[w]["d"], "filled": weekly[w]["f"],
         "fill_rate": weekly[w]["f"] / weekly[w]["d"] * 100 if weekly[w]["d"] else 100}
        for w in sorted(weekly)
    ]


def _observations(node_kpis, weekly, summary):
    obs = []
    # Weakest node
    worst = min(node_kpis, key=lambda n: n["fill_rate"])
    obs.append({"text": f"{worst['name']} has the lowest fill rate ({worst['fill_rate']:.1f}%) — "
                        "consider raising its reorder point or order-up-to level.",
                "flag": "warn" if worst["fill_rate"] < 95 else None})
    # Highest cost node
    costliest = max(node_kpis, key=lambda n: n["total_cost"])
    obs.append({"text": f"{costliest['name']} drives the highest cost (${costliest['total_cost']:,.2f}), "
                        "mainly holding costs from large safety stock.", "flag": None})
    # Lost sales
    if summary["total_lost"] > 0:
        obs.append({"text": f"{summary['total_lost']:,} units lost as stockouts at retail stores. "
                            "Tighter pipeline management or higher store safety stock could recover these.",
                    "flag": "warn"})
    else:
        obs.append({"text": "Zero lost sales across all retail stores — excellent service level.", "flag": "ok"})
    # Peak season
    peak = [w for w in weekly if w["week"] >= 48]
    if peak:
        min_peak = min(peak, key=lambda w: w["fill_rate"])
        obs.append({"text": f"Peak-season fill rate dips to {min_peak['fill_rate']:.1f}% in week {min_peak['week']}. "
                            "Pre-building inventory before week 46 would reduce shortfalls.",
                    "flag": "warn" if min_peak["fill_rate"] < 98 else None})
    # Overall fill
    if summary["fill_rate"] >= 98:
        obs.append({"text": f"Overall fill rate of {summary['fill_rate']:.2f}% exceeds the 98% industry benchmark.", "flag": "ok"})
    elif summary["fill_rate"] >= 95:
        obs.append({"text": f"Overall fill rate of {summary['fill_rate']:.2f}% is acceptable but below the 98% benchmark.", "flag": "warn"})
    else:
        obs.append({"text": f"Overall fill rate of {summary['fill_rate']:.2f}% is below the 95% minimum threshold.", "flag": "warn"})
    return obs


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML, scenarios=SCENARIOS)


@app.route("/api/run", methods=["POST"])
def api_run():
    try:
        body     = request.get_json(force=True)
        scenario = body.get("scenario", "baseline")
        num_days = min(max(int(body.get("days", 365)), 30), 1095)
        seed     = int(body.get("seed", 42))

        if scenario not in SCENARIOS:
            return jsonify({"error": f"Unknown scenario '{scenario}'"}), 400

        # Build and run simulation with scenario overrides
        from run_scenario import build_sim_with_scenario
        sc  = SCENARIOS[scenario]
        sim = build_sim_with_scenario(sc, num_days=num_days, seed=seed)

        # Suppress stdout from sim.run()
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        sim.run()
        sys.stdout = old_stdout

        all_nodes = {"Warehouse": sim.warehouse, **sim.dcs, **sim.stores}
        node_kpis = [_node_kpis(n) for n in all_nodes.values()]

        total_demand = sum(s.total_demand for s in sim.stores.values())
        total_filled = sum(s.total_filled for s in sim.stores.values())
        total_lost   = sum(s.total_lost   for s in sim.stores.values())
        total_cost   = sum(n["total_cost"] for n in node_kpis)
        fill_rate    = total_filled / total_demand * 100 if total_demand else 100

        weekly  = _weekly_fill(sim.stores)
        monthly = _monthly_inventory(all_nodes, num_days)
        summary = {
            "fill_rate": round(fill_rate, 2),
            "total_demand": total_demand,
            "total_lost": total_lost,
            "total_cost": round(total_cost, 2),
            "days": num_days,
            "scenario": scenario,
        }

        return jsonify({
            "summary": summary,
            "nodes": node_kpis,
            "monthly": monthly,
            "weekly": weekly,
            "observations": _observations(node_kpis, weekly, summary),
        })

    except Exception as e:
        sys.stdout = sys.__stdout__
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
