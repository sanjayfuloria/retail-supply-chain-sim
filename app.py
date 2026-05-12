"""
Retail Supply Chain Simulation — Web Interface (Vercel entry point)

Roles
  student  — can run simulations; sees their own results
  faculty  — full access + admin dashboard (user management, all run logs)
"""

import functools
import io
import os
import sys

from flask import Flask, jsonify, redirect, render_template_string, request, url_for
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)

import auth
from config import SCENARIOS
from simulation import RetailSupplyChainSimulation

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

# ── Flask-Login setup ─────────────────────────────────────────────────────────

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."


@login_manager.user_loader
def load_user(user_id):
    return auth.get_user(user_id)


def faculty_required(f):
    """Decorator: 403 for non-faculty users."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_faculty:
            return jsonify({"error": "Faculty access required."}), 403
        return f(*args, **kwargs)
    return wrapped


@app.before_request
def _init():
    auth.init_db()


# ── HTML templates ────────────────────────────────────────────────────────────

_BASE_CSS = """
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f0f4f8; color: #1a202c; }

/* ── top nav ── */
.topnav { background: #1a365d; color: white; display: flex; align-items: center;
          justify-content: space-between; padding: .75rem 2rem; }
.topnav .brand { font-size: 1rem; font-weight: 700; letter-spacing: .02em; }
.topnav .brand span { color: #90cdf4; }
.topnav .user-info { display: flex; align-items: center; gap: .75rem; font-size: .85rem; }
.topnav .avatar { width: 32px; height: 32px; border-radius: 50%;
                  background: #2b6cb0; display: flex; align-items: center;
                  justify-content: center; font-weight: 700; font-size: .75rem; }
.topnav .role-badge { background: #2b6cb0; padding: .15rem .5rem; border-radius: 20px;
                      font-size: .7rem; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
.topnav .role-badge.faculty { background: #744210; }
.topnav a { color: #90cdf4; text-decoration: none; font-size: .82rem; }
.topnav a:hover { text-decoration: underline; }
.topnav .sep { color: #4a6fa5; }

/* ── cards ── */
main { max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }
.card { background: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,.08);
        padding: 1.5rem; margin-bottom: 1.5rem; }
.card h2 { font-size: 1rem; font-weight: 600; color: #2d3748; margin-bottom: 1rem;
           border-bottom: 1px solid #e2e8f0; padding-bottom: .5rem; }

/* ── forms ── */
.form-row { display: flex; gap: 1rem; flex-wrap: wrap; align-items: flex-end; }
.form-group { display: flex; flex-direction: column; gap: .3rem; flex: 1; min-width: 140px; }
label { font-size: .8rem; font-weight: 500; color: #4a5568; }
select, input[type=number], input[type=text], input[type=email], input[type=password] {
  padding: .45rem .65rem; border: 1px solid #cbd5e0; border-radius: 6px; font-size: .9rem; }
select:focus, input:focus { outline: 2px solid #3182ce; border-color: transparent; }

/* ── buttons ── */
.btn { display: inline-block; padding: .5rem 1.2rem; border: none; border-radius: 6px;
       font-size: .88rem; font-weight: 600; cursor: pointer; text-decoration: none; }
.btn-primary  { background: #2b6cb0; color: white; }
.btn-primary:hover { background: #2c5282; }
.btn-danger   { background: #e53e3e; color: white; }
.btn-danger:hover  { background: #c53030; }
.btn-sm { padding: .3rem .75rem; font-size: .78rem; }
.btn:disabled { background: #a0aec0; cursor: not-allowed; }

/* ── tables ── */
table { width: 100%; border-collapse: collapse; font-size: .85rem; }
th { background: #2d3748; color: white; padding: .55rem .75rem; text-align: left; }
th.r, td.r { text-align: right; }
td { padding: .5rem .75rem; border-bottom: 1px solid #e2e8f0; }
tr:nth-child(even) td { background: #f7fafc; }
tr.total td { background: #ebf8ff; font-weight: 700; border-top: 2px solid #3182ce; }

/* ── badges ── */
.badge { display: inline-block; padding: .15rem .5rem; border-radius: 20px;
         font-size: .72rem; font-weight: 600; }
.badge-faculty { background: #fefcbf; color: #744210; }
.badge-student { background: #bee3f8; color: #2c5282; }

/* ── fill bar ── */
.fill-bar { display: inline-block; background: #e2e8f0; border-radius: 4px;
            width: 60px; height: 7px; vertical-align: middle; margin-right: 5px; }
.fill-bar span { display: block; height: 100%; border-radius: 4px; }

/* ── kpi grid ── */
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; }
.kpi { background: #ebf8ff; border-left: 4px solid #3182ce; border-radius: 6px; padding: .85rem 1rem; }
.kpi .label { font-size: .72rem; color: #4a5568; text-transform: uppercase; letter-spacing: .05em; }
.kpi .value { font-size: 1.5rem; font-weight: 700; color: #1a365d; margin-top: .15rem; }
.kpi .sub   { font-size: .72rem; color: #718096; margin-top: .1rem; }

/* ── alert ── */
.alert { padding: .75rem 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: .875rem; }
.alert-error { background: #fed7d7; color: #c53030; border: 1px solid #feb2b2; }
.alert-success { background: #c6f6d5; color: #276749; border: 1px solid #9ae6b4; }

/* ── spinner ── */
#spinner { display: none; align-items: center; gap: .5rem; color: #4a5568;
           font-size: .88rem; padding: .5rem 0; }
.spin { width: 16px; height: 16px; border: 3px solid #cbd5e0; border-top-color: #2b6cb0;
        border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── observations ── */
.observations { list-style: none; }
.observations li { padding: .4rem 0; border-bottom: 1px solid #e2e8f0;
                   font-size: .875rem; color: #2d3748; }
.observations li::before { content: "▸ "; color: #3182ce; font-weight: bold; }
.tag { display: inline-block; font-size: .7rem; font-weight: 600; border-radius: 3px;
       padding: .1rem .35rem; margin-left: .3rem; vertical-align: middle; }
.tag-warn { background: #fed7d7; color: #c53030; }
.tag-ok   { background: #c6f6d5; color: #276749; }

/* ── seasonal grid ── */
.seasonal-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(62px, 1fr)); gap: .35rem; }
.week-cell { border-radius: 5px; padding: .35rem .4rem; text-align: center; font-size: .75rem; }
.week-cell .wk  { font-weight: 600; color: #4a5568; }
.week-cell .pct { font-weight: 700; }

/* ── monthly table ── */
.monthly-table th, .monthly-table td { font-size: .78rem; padding: .4rem .55rem; }

/* ── modal ── */
.modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.5);
                 z-index: 100; align-items: center; justify-content: center; }
.modal-overlay.open { display: flex; }
.modal { background: white; border-radius: 10px; padding: 2rem; width: 100%;
         max-width: 460px; box-shadow: 0 8px 32px rgba(0,0,0,.2); }
.modal h3 { margin-bottom: 1.25rem; font-size: 1.05rem; }
.modal .form-group { margin-bottom: .85rem; }
.modal-actions { display: flex; justify-content: flex-end; gap: .75rem; margin-top: 1.25rem; }
</style>
"""

_NAV = """
<nav class="topnav">
  <span class="brand">Supply Chain <span>Simulation</span></span>
  <div class="user-info">
    {% if current_user.is_faculty %}
      <a href="{{ url_for('admin') }}">Admin Dashboard</a>
      <span class="sep">|</span>
    {% endif %}
    <div class="avatar">{{ current_user.initials }}</div>
    <span>{{ current_user.name }}</span>
    <span class="role-badge {{ current_user.role }}">{{ current_user.role }}</span>
    <span class="sep">|</span>
    <a href="{{ url_for('logout') }}">Log out</a>
  </div>
</nav>
"""

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Sign In — Supply Chain Simulation</title>
  """ + _BASE_CSS + """
  <style>
    body { display: flex; align-items: center; justify-content: center;
           min-height: 100vh; background: linear-gradient(135deg, #1a365d 0%, #2b6cb0 100%); }
    .login-wrap { background: white; border-radius: 12px; padding: 2.5rem 2rem;
                  width: 100%; max-width: 400px; box-shadow: 0 12px 40px rgba(0,0,0,.25); }
    .login-wrap h1 { font-size: 1.3rem; color: #1a365d; margin-bottom: .25rem; }
    .login-wrap p  { font-size: .82rem; color: #718096; margin-bottom: 1.75rem; }
    .tabs { display: flex; border-bottom: 2px solid #e2e8f0; margin-bottom: 1.5rem; }
    .tab { flex: 1; text-align: center; padding: .6rem; font-size: .875rem; font-weight: 600;
           cursor: pointer; color: #718096; border-bottom: 3px solid transparent; margin-bottom: -2px; }
    .tab.active { color: #2b6cb0; border-color: #2b6cb0; }
    .form-group { margin-bottom: 1rem; }
    .login-wrap label { margin-bottom: .35rem; }
    .login-wrap input { width: 100%; }
    .btn-login { width: 100%; padding: .65rem; font-size: .95rem; margin-top: .5rem; }
    .demo-hint { background: #ebf8ff; border: 1px solid #bee3f8; border-radius: 6px;
                 padding: .75rem; margin-top: 1.5rem; font-size: .78rem; color: #2c5282; }
    .demo-hint strong { display: block; margin-bottom: .35rem; }
    .demo-hint code { background: #bee3f8; padding: .1rem .3rem; border-radius: 3px; }
  </style>
</head>
<body>
<div class="login-wrap">
  <h1>Supply Chain Simulation</h1>
  <p>Retail industry multi-echelon model</p>

  <div class="tabs">
    <div class="tab active" id="tab-student" onclick="switchTab('student')">Student</div>
    <div class="tab"        id="tab-faculty" onclick="switchTab('faculty')">Faculty</div>
  </div>

  {% if error %}
  <div class="alert alert-error">{{ error }}</div>
  {% endif %}

  <form method="POST">
    <input type="hidden" name="expected_role" id="expected_role" value="student"/>
    <div class="form-group">
      <label for="email">Email address</label>
      <input type="email" id="email" name="email" required
             placeholder="you@university.edu" value="{{ email or '' }}"/>
    </div>
    <div class="form-group">
      <label for="password">Password</label>
      <input type="password" id="password" name="password" required placeholder="••••••••"/>
    </div>
    <button type="submit" class="btn btn-primary btn-login">Sign In</button>
  </form>

  <div class="demo-hint">
    <strong>Demo credentials</strong>
    <b>Faculty:</b> <code>faculty@university.edu</code> / <code>faculty123</code><br/>
    <b>Student:</b> <code>student1@university.edu</code> / <code>student123</code>
  </div>
</div>

<script>
function switchTab(role) {
  document.getElementById('tab-student').classList.toggle('active', role === 'student');
  document.getElementById('tab-faculty').classList.toggle('active', role === 'faculty');
  document.getElementById('expected_role').value = role;
  document.getElementById('email').placeholder =
    role === 'faculty' ? 'faculty@university.edu' : 'student@university.edu';
}
</script>
</body>
</html>"""

SIM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Simulation — Supply Chain</title>
  """ + _BASE_CSS + """
</head>
<body>
""" + _NAV + """
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
        <input type="number" id="days" value="365" min="30" max="1095"/>
      </div>
      <div class="form-group" style="max-width:110px">
        <label for="seed">Random seed</label>
        <input type="number" id="seed" value="42" min="0" max="99999"/>
      </div>
      <button class="btn btn-primary" id="runBtn" onclick="runSim()">Run Simulation</button>
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
      <table>
        <thead><tr>
          <th>Node</th><th>Fill Rate</th><th class="r">Demand</th>
          <th class="r">Lost Sales</th><th class="r">Avg Inventory</th>
          <th class="r">Replen. Orders</th><th class="r">Holding Cost</th>
          <th class="r">Shortage Cost</th><th class="r">Total Cost</th>
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
  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        scenario: document.getElementById('scenario').value,
        days: parseInt(document.getElementById('days').value),
        seed: parseInt(document.getElementById('seed').value),
      }),
    });
    if (res.status === 401) { location.href = '/login'; return; }
    const data = await res.json();
    if (data.error) { alert('Error: ' + data.error); return; }
    render(data);
    document.getElementById('results').style.display = 'block';
  } catch(e) { alert('Request failed: ' + e); }
  finally { btn.disabled = false; document.getElementById('spinner').style.display = 'none'; }
}

const fmt  = n => n.toLocaleString();
const fmtC = n => '$' + n.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
const fillColor = p => p >= 99 ? '#38a169' : p >= 95 ? '#d69e2e' : '#e53e3e';

function render(d) {
  // KPIs
  const kpis = [
    {label:'Overall Fill Rate',        value: d.summary.fill_rate.toFixed(2)+'%', sub:'customer service level'},
    {label:'Total Supply Chain Cost',  value: fmtC(d.summary.total_cost),         sub:'holding + ordering + shortage'},
    {label:'Total Units Demanded',     value: fmt(d.summary.total_demand),         sub:'all retail stores'},
    {label:'Total Lost Sales',         value: fmt(d.summary.total_lost),           sub:'units at store level'},
    {label:'Simulation Period',        value: d.summary.days+' days',              sub:d.summary.scenario+' scenario'},
  ];
  document.getElementById('kpiGrid').innerHTML = kpis.map(k =>
    `<div class="kpi"><div class="label">${k.label}</div><div class="value">${k.value}</div><div class="sub">${k.sub}</div></div>`
  ).join('');

  // Node table
  document.getElementById('nodeBody').innerHTML = d.nodes.map(n => {
    const p = n.fill_rate;
    const bar = `<div class="fill-bar"><span style="width:${p}%;background:${fillColor(p)}"></span></div>`;
    return `<tr>
      <td>${n.name}</td>
      <td>${bar}${p.toFixed(1)}%</td>
      <td class="r">${fmt(n.total_demand)}</td>
      <td class="r">${fmt(n.total_lost)}</td>
      <td class="r">${fmt(Math.round(n.avg_inventory))}</td>
      <td class="r">${fmt(n.num_orders)}</td>
      <td class="r">${fmtC(n.holding_cost)}</td>
      <td class="r">${fmtC(n.shortage_cost)}</td>
      <td class="r">${fmtC(n.total_cost)}</td>
    </tr>`;
  }).join('') + `<tr class="total">
    <td>TOTAL</td><td></td><td class="r"></td><td class="r"></td><td class="r"></td><td class="r"></td>
    <td class="r">${fmtC(d.nodes.reduce((s,n)=>s+n.holding_cost,0))}</td>
    <td class="r">${fmtC(d.nodes.reduce((s,n)=>s+n.shortage_cost,0))}</td>
    <td class="r">${fmtC(d.summary.total_cost)}</td>
  </tr>`;

  // Monthly inventory
  const nodeNames = d.nodes.map(n => n.name);
  document.getElementById('monthlyTable').innerHTML =
    `<thead><tr><th>Month</th>${nodeNames.map(n=>`<th class="r">${n}</th>`).join('')}</tr></thead>` +
    `<tbody>${d.monthly.map((row,i) =>
      `<tr><td>Month ${i+1}</td>${nodeNames.map(n=>`<td class="r">${fmt(Math.round(row[n]||0))}</td>`).join('')}</tr>`
    ).join('')}</tbody>`;

  // Weekly grid
  document.getElementById('weekGrid').innerHTML = d.weekly.map(w => {
    const p = w.fill_rate;
    const bg = p>=99?'#c6f6d5':p>=95?'#fefcbf':'#fed7d7';
    const tc = p>=99?'#276749':p>=95?'#744210':'#c53030';
    return `<div class="week-cell" style="background:${bg}">
      <div class="wk">Wk ${w.week}${w.week>=48?' 🎄':''}</div>
      <div class="pct" style="color:${tc}">${p.toFixed(1)}%</div>
    </div>`;
  }).join('');

  // Observations
  document.getElementById('obsList').innerHTML = d.observations.map(o =>
    `<li>${o.text}${o.flag?`<span class="tag tag-${o.flag}">${o.flag.toUpperCase()}</span>`:''}</li>`
  ).join('');
}

window.onload = () => runSim();
</script>
</body>
</html>"""

ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Admin Dashboard — Supply Chain</title>
  """ + _BASE_CSS + """
  <style>
    .section-tabs { display: flex; gap: .5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
    .stab { padding: .5rem 1.1rem; border-radius: 6px; font-size: .875rem; font-weight: 600;
            cursor: pointer; background: #e2e8f0; color: #4a5568; border: none; }
    .stab.active { background: #2b6cb0; color: white; }
    .section { display: none; }
    .section.active { display: block; }
    .actions-cell { white-space: nowrap; display: flex; gap: .4rem; }
    .btn-outline { background: transparent; border: 1.5px solid currentColor;
                   color: #2b6cb0; padding: .28rem .7rem; border-radius: 5px;
                   font-size: .75rem; font-weight: 600; cursor: pointer; }
    .btn-outline:hover { background: #ebf8ff; }
    .btn-outline.danger { color: #e53e3e; }
    .btn-outline.danger:hover { background: #fff5f5; }
    .empty-state { text-align: center; padding: 2.5rem; color: #a0aec0; font-size: .9rem; }
    .search-bar { display: flex; gap: .5rem; margin-bottom: 1rem; }
    .search-bar input { flex: 1; }
  </style>
</head>
<body>
""" + _NAV + """
<main>

  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem">
    <div>
      <h1 style="font-size:1.3rem;color:#1a365d">Faculty Admin Dashboard</h1>
      <p style="font-size:.82rem;color:#718096;margin-top:.2rem">Manage users and monitor simulation activity</p>
    </div>
    <button class="btn btn-primary" onclick="openModal()">+ Add User</button>
  </div>

  <!-- KPI cards -->
  <div class="kpi-grid" id="statsGrid" style="margin-bottom:1.5rem"></div>

  <!-- section tabs -->
  <div class="section-tabs">
    <button class="stab active" onclick="showSection('users',this)">Users</button>
    <button class="stab"        onclick="showSection('runs',this)">Simulation Runs</button>
  </div>

  <!-- Users section -->
  <div id="section-users" class="section active">
    <div class="card">
      <h2>All Users</h2>
      <div class="search-bar">
        <input type="text" id="userSearch" placeholder="Search by name or email…" oninput="filterUsers()"/>
      </div>
      <table id="usersTable">
        <thead><tr>
          <th>Name</th><th>Email</th><th>Role</th><th>Joined</th><th>Actions</th>
        </tr></thead>
        <tbody id="usersBody"></tbody>
      </table>
    </div>
  </div>

  <!-- Simulation runs section -->
  <div id="section-runs" class="section">
    <div class="card">
      <h2>Recent Simulation Runs</h2>
      <table id="runsTable">
        <thead><tr>
          <th>User</th><th>Role</th><th>Scenario</th>
          <th class="r">Days</th><th class="r">Fill Rate</th>
          <th class="r">Total Cost</th><th>Run At</th>
        </tr></thead>
        <tbody id="runsBody"></tbody>
      </table>
      <div id="runsEmpty" class="empty-state" style="display:none">No simulation runs yet.</div>
    </div>
  </div>

</main>

<!-- Add User modal -->
<div class="modal-overlay" id="addModal" onclick="closeModalOnBg(event)">
  <div class="modal">
    <h3>Add New User</h3>
    <div id="modalAlert"></div>
    <div class="form-group">
      <label>Full Name</label>
      <input type="text" id="newName" placeholder="Jane Smith"/>
    </div>
    <div class="form-group">
      <label>Email Address</label>
      <input type="email" id="newEmail" placeholder="jane@university.edu"/>
    </div>
    <div class="form-group">
      <label>Password</label>
      <input type="password" id="newPassword" placeholder="Min. 6 characters"/>
    </div>
    <div class="form-group">
      <label>Role</label>
      <select id="newRole">
        <option value="student">Student</option>
        <option value="faculty">Faculty</option>
      </select>
    </div>
    <div class="modal-actions">
      <button class="btn" style="background:#e2e8f0;color:#4a5568" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="addUser()">Create User</button>
    </div>
  </div>
</div>

<script>
let allUsers = [];

async function loadAll() {
  const [statsRes, usersRes, runsRes] = await Promise.all([
    fetch('/admin/api/stats'),
    fetch('/admin/api/users'),
    fetch('/admin/api/runs'),
  ]);
  const stats = await statsRes.json();
  const users = await usersRes.json();
  const runs  = await runsRes.json();
  renderStats(stats);
  allUsers = users;
  renderUsers(users);
  renderRuns(runs);
}

function renderStats(s) {
  document.getElementById('statsGrid').innerHTML = [
    {label:'Total Users',       value: s.total_users,                 sub:'registered accounts'},
    {label:'Faculty Members',   value: s.faculty_count,               sub:'admin access'},
    {label:'Students',          value: s.student_count,               sub:'simulation access'},
    {label:'Simulation Runs',   value: s.total_runs,                  sub:'all time'},
    {label:'Avg. Fill Rate',    value: (s.avg_fill_rate||0).toFixed(1)+'%', sub:'across all runs'},
  ].map(k=>
    `<div class="kpi"><div class="label">${k.label}</div><div class="value">${k.value}</div><div class="sub">${k.sub}</div></div>`
  ).join('');
}

function renderUsers(users) {
  const tbody = document.getElementById('usersBody');
  if (!users.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No users found.</td></tr>';
    return;
  }
  tbody.innerHTML = users.map(u => {
    const badge = `<span class="badge badge-${u.role}">${u.role}</span>`;
    const date  = new Date(u.created_at).toLocaleDateString('en-US', {year:'numeric',month:'short',day:'numeric'});
    const otherRole = u.role === 'faculty' ? 'student' : 'faculty';
    const otherLabel = u.role === 'faculty' ? 'Make Student' : 'Make Faculty';
    return `<tr id="user-row-${u.id}">
      <td><strong>${esc(u.name)}</strong></td>
      <td>${esc(u.email)}</td>
      <td>${badge}</td>
      <td>${date}</td>
      <td><div class="actions-cell">
        <button class="btn-outline" onclick="changeRole(${u.id},'${otherRole}')">${otherLabel}</button>
        <button class="btn-outline danger" onclick="deleteUser(${u.id},'${esc(u.name)}')">Delete</button>
      </div></td>
    </tr>`;
  }).join('');
}

function filterUsers() {
  const q = document.getElementById('userSearch').value.toLowerCase();
  const filtered = allUsers.filter(u =>
    u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
  );
  renderUsers(filtered);
}

function renderRuns(runs) {
  const tbody = document.getElementById('runsBody');
  const empty = document.getElementById('runsEmpty');
  if (!runs.length) { tbody.innerHTML = ''; empty.style.display = 'block'; return; }
  empty.style.display = 'none';
  const fmtC = n => '$' + n.toLocaleString('en-US', {minimumFractionDigits:2,maximumFractionDigits:2});
  tbody.innerHTML = runs.map(r => {
    const p    = r.fill_rate || 0;
    const fc   = p>=99?'#276749':p>=95?'#744210':'#c53030';
    const date = new Date(r.ran_at).toLocaleString('en-US', {dateStyle:'medium',timeStyle:'short'});
    return `<tr>
      <td><strong>${esc(r.user_name)}</strong><br/><small style="color:#718096">${esc(r.email)}</small></td>
      <td><span class="badge badge-${r.role}">${r.role}</span></td>
      <td>${esc(r.scenario)}</td>
      <td class="r">${r.days}</td>
      <td class="r" style="color:${fc};font-weight:600">${p.toFixed(2)}%</td>
      <td class="r">${fmtC(r.total_cost||0)}</td>
      <td style="font-size:.8rem;color:#718096">${date}</td>
    </tr>`;
  }).join('');
}

async function changeRole(id, role) {
  if (!confirm(`Change this user to ${role}?`)) return;
  const res = await fetch(`/admin/api/users/${id}/role`, {
    method: 'PUT',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({role}),
  });
  if (res.ok) loadAll(); else alert('Failed to update role.');
}

async function deleteUser(id, name) {
  if (!confirm(`Delete ${name}? This cannot be undone.`)) return;
  const res = await fetch(`/admin/api/users/${id}`, {method:'DELETE'});
  if (res.ok) loadAll(); else alert('Failed to delete user.');
}

function openModal() {
  document.getElementById('addModal').classList.add('open');
  document.getElementById('modalAlert').innerHTML = '';
  ['newName','newEmail','newPassword'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('newRole').value = 'student';
}
function closeModal() { document.getElementById('addModal').classList.remove('open'); }
function closeModalOnBg(e) { if (e.target === document.getElementById('addModal')) closeModal(); }

async function addUser() {
  const payload = {
    name:     document.getElementById('newName').value.trim(),
    email:    document.getElementById('newEmail').value.trim(),
    password: document.getElementById('newPassword').value,
    role:     document.getElementById('newRole').value,
  };
  if (!payload.name || !payload.email || !payload.password) {
    showModalAlert('All fields are required.', 'error'); return;
  }
  if (payload.password.length < 6) {
    showModalAlert('Password must be at least 6 characters.', 'error'); return;
  }
  const res = await fetch('/admin/api/users', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (res.ok) { closeModal(); loadAll(); }
  else showModalAlert(data.error || 'Failed to create user.', 'error');
}

function showModalAlert(msg, type) {
  document.getElementById('modalAlert').innerHTML =
    `<div class="alert alert-${type}">${msg}</div>`;
}

function showSection(name, el) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.stab').forEach(b => b.classList.remove('active'));
  document.getElementById('section-' + name).classList.add('active');
  el.classList.add('active');
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

loadAll();
</script>
</body>
</html>"""


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin") if current_user.is_faculty else url_for("index"))

    error = None
    email = None

    if request.method == "POST":
        email         = request.form.get("email", "").strip().lower()
        password      = request.form.get("password", "")
        expected_role = request.form.get("expected_role", "student")

        user = auth.authenticate(email, password)
        if user is None:
            error = "Invalid email or password."
        elif user.role != expected_role:
            error = f"That account is not a {expected_role} account. Please select the correct role tab."
        else:
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or (url_for("admin") if user.is_faculty else url_for("index")))

    return render_template_string(LOGIN_HTML, error=error, email=email)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ── Simulation route ──────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template_string(SIM_HTML, scenarios=SCENARIOS)


@app.route("/api/run", methods=["POST"])
@login_required
def api_run():
    try:
        body     = request.get_json(force=True)
        scenario = body.get("scenario", "baseline")
        num_days = min(max(int(body.get("days", 365)), 30), 1095)
        seed     = int(body.get("seed", 42))

        if scenario not in SCENARIOS:
            return jsonify({"error": f"Unknown scenario '{scenario}'"}), 400

        from run_scenario import build_sim_with_scenario
        sc  = SCENARIOS[scenario]
        sim = build_sim_with_scenario(sc, num_days=num_days, seed=seed)

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

        auth.log_simulation(current_user.id, scenario, num_days,
                            round(fill_rate, 2), round(total_cost, 2))

        weekly  = _weekly_fill(sim.stores)
        monthly = _monthly_inventory(all_nodes, num_days)
        summary = {
            "fill_rate":    round(fill_rate, 2),
            "total_demand": total_demand,
            "total_lost":   total_lost,
            "total_cost":   round(total_cost, 2),
            "days":         num_days,
            "scenario":     scenario,
        }
        return jsonify({
            "summary": summary,
            "nodes":   node_kpis,
            "monthly": monthly,
            "weekly":  weekly,
            "observations": _observations(node_kpis, weekly, summary),
        })

    except Exception as e:
        sys.stdout = sys.__stdout__
        return jsonify({"error": str(e)}), 500


# ── Admin routes (faculty only) ───────────────────────────────────────────────

@app.route("/admin")
@login_required
@faculty_required
def admin():
    return render_template_string(ADMIN_HTML)


@app.route("/admin/api/stats")
@login_required
@faculty_required
def admin_stats():
    return jsonify(auth.stats())


@app.route("/admin/api/users", methods=["GET"])
@login_required
@faculty_required
def admin_users():
    return jsonify(auth.all_users())


@app.route("/admin/api/users", methods=["POST"])
@login_required
@faculty_required
def admin_create_user():
    body = request.get_json(force=True)
    name     = body.get("name", "").strip()
    email    = body.get("email", "").strip().lower()
    password = body.get("password", "")
    role     = body.get("role", "student")
    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required."}), 400
    if role not in ("faculty", "student"):
        return jsonify({"error": "Role must be 'faculty' or 'student'."}), 400
    ok, err = auth.create_user(name, email, password, role)
    if not ok:
        return jsonify({"error": err}), 409
    return jsonify({"ok": True}), 201


@app.route("/admin/api/users/<int:user_id>/role", methods=["PUT"])
@login_required
@faculty_required
def admin_update_role(user_id):
    body = request.get_json(force=True)
    role = body.get("role")
    if role not in ("faculty", "student"):
        return jsonify({"error": "Invalid role."}), 400
    if str(user_id) == current_user.id and role == "student":
        return jsonify({"error": "You cannot demote yourself."}), 400
    auth.update_role(str(user_id), role)
    return jsonify({"ok": True})


@app.route("/admin/api/users/<int:user_id>", methods=["DELETE"])
@login_required
@faculty_required
def admin_delete_user(user_id):
    if str(user_id) == current_user.id:
        return jsonify({"error": "You cannot delete your own account."}), 400
    auth.delete_user(str(user_id))
    return jsonify({"ok": True})


@app.route("/admin/api/runs")
@login_required
@faculty_required
def admin_runs():
    return jsonify(auth.recent_simulations(limit=50))


# ── Shared helpers ────────────────────────────────────────────────────────────

def _node_kpis(node):
    h        = node.history
    holding  = sum(s.holding_cost  for s in h)
    ordering = sum(s.ordering_cost for s in h)
    shortage = sum(s.shortage_cost for s in h)
    avg_inv  = sum(s.closing_stock for s in h) / len(h) if h else 0
    num_ord  = sum(1 for s in h if s.orders_placed > 0)
    fill     = node.total_filled / node.total_demand * 100 if node.total_demand else 100
    return {
        "name":          node.name,
        "fill_rate":     round(fill, 2),
        "total_demand":  node.total_demand,
        "total_lost":    node.total_lost,
        "avg_inventory": round(avg_inv, 1),
        "num_orders":    num_ord,
        "holding_cost":  round(holding, 2),
        "ordering_cost": round(ordering, 2),
        "shortage_cost": round(shortage, 2),
        "total_cost":    round(holding + ordering + shortage, 2),
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
    worst = min(node_kpis, key=lambda n: n["fill_rate"])
    obs.append({"text": f"{worst['name']} has the lowest fill rate ({worst['fill_rate']:.1f}%) — "
                        "consider raising its reorder point or order-up-to level.",
                "flag": "warn" if worst["fill_rate"] < 95 else None})
    costliest = max(node_kpis, key=lambda n: n["total_cost"])
    obs.append({"text": f"{costliest['name']} drives the highest cost (${costliest['total_cost']:,.2f}), "
                        "mainly holding costs from large safety stock.", "flag": None})
    if summary["total_lost"] > 0:
        obs.append({"text": f"{summary['total_lost']:,} units lost as stockouts at retail stores. "
                            "Tighter pipeline management or higher store safety stock could recover these.",
                    "flag": "warn"})
    else:
        obs.append({"text": "Zero lost sales across all retail stores — excellent service level.", "flag": "ok"})
    peak = [w for w in weekly if w["week"] >= 48]
    if peak:
        min_peak = min(peak, key=lambda w: w["fill_rate"])
        obs.append({"text": f"Peak-season fill rate dips to {min_peak['fill_rate']:.1f}% in week {min_peak['week']}. "
                            "Pre-building inventory before week 46 would reduce shortfalls.",
                    "flag": "warn" if min_peak["fill_rate"] < 98 else None})
    if summary["fill_rate"] >= 98:
        obs.append({"text": f"Overall fill rate of {summary['fill_rate']:.2f}% exceeds the 98% industry benchmark.", "flag": "ok"})
    elif summary["fill_rate"] >= 95:
        obs.append({"text": f"Overall fill rate of {summary['fill_rate']:.2f}% is acceptable but below the 98% benchmark.", "flag": "warn"})
    else:
        obs.append({"text": f"Overall fill rate of {summary['fill_rate']:.2f}% is below the 95% minimum threshold.", "flag": "warn"})
    return obs


if __name__ == "__main__":
    app.run(debug=True, port=5000)
