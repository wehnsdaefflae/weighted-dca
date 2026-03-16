#!/usr/bin/env python3
"""Generate a self-contained interactive HTML report.

Embeds price data + optimal parameters. All strategy logic runs in-browser
via JavaScript so users can tweak parameters and see results instantly.
"""

import json
from pathlib import Path

REPORT_DIR = Path(__file__).parent.parent / "report"


def main():
    with open(REPORT_DIR / "results.json") as f:
        results = json.load(f)
    with open(REPORT_DIR / "prices.json") as f:
        prices = json.load(f)

    params = results["params"]
    train_end = results["train_end"]
    val_start = results["validation_start"]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Weighted DCA Optimizer</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  :root {{
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
    --green: #3fb950; --red: #f85149; --yellow: #d29922;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg); color: var(--text); padding: 24px; line-height: 1.5;
  }}
  h1 {{ font-size: 1.6rem; margin-bottom: 4px; }}
  h2 {{ font-size: 1.15rem; color: var(--accent); margin: 24px 0 12px; }}
  .subtitle {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 20px; }}
  .grid {{ display: grid; grid-template-columns: 320px 1fr; gap: 24px; }}
  @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}

  .panel {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 16px;
  }}
  .controls label {{
    display: flex; justify-content: space-between; align-items: center;
    font-size: 0.85rem; margin-bottom: 2px; color: var(--muted);
  }}
  .controls label span.val {{ color: var(--text); font-weight: 600; font-family: monospace; }}
  .controls input[type=range] {{
    width: 100%; accent-color: var(--accent); margin-bottom: 10px;
  }}
  .controls select {{
    width: 100%; background: var(--bg); color: var(--text);
    border: 1px solid var(--border); border-radius: 4px;
    padding: 4px 8px; margin-bottom: 10px; font-size: 0.85rem;
  }}
  .controls .sep {{
    border-top: 1px solid var(--border); margin: 12px 0;
  }}
  .controls button {{
    width: 100%; padding: 8px; border: 1px solid var(--accent);
    background: transparent; color: var(--accent); border-radius: 6px;
    cursor: pointer; font-size: 0.85rem; margin-top: 4px;
  }}
  .controls button:hover {{ background: var(--accent); color: var(--bg); }}

  .kpi-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }}
  .kpi {{
    flex: 1; min-width: 140px; background: var(--surface);
    border: 1px solid var(--border); border-radius: 8px; padding: 12px;
    text-align: center;
  }}
  .kpi .label {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; }}
  .kpi .val {{ font-size: 1.3rem; font-weight: 700; margin-top: 4px; }}
  .kpi .sub {{ font-size: 0.75rem; color: var(--muted); }}
  .positive {{ color: var(--green); }}
  .negative {{ color: var(--red); }}

  .chart {{ width: 100%; height: 370px; margin-bottom: 16px; }}
  .period-info {{
    font-size: 0.8rem; color: var(--muted); padding: 8px 0;
    border-top: 1px solid var(--border); margin-top: 8px;
  }}
  .period-info b {{ color: var(--yellow); }}
</style>
</head>
<body>

<h1>Weighted DCA Strategy Report</h1>
<p class="subtitle">70% MSCI World / 30% MSCI EM IMI &mdash; percentage-based buy-the-dip strategy</p>

<div class="grid">
  <!-- LEFT: Controls -->
  <div>
    <div class="panel controls">
      <h2 style="margin-top:0">Strategy Parameters</h2>

      <label>Reference type
        <select id="ctrl-reftype">
          <option value="rolling">Rolling window</option>
          <option value="ath">All-time high</option>
        </select>
      </label>

      <label>Window (months) <span class="val" id="v-window"></span></label>
      <input type="range" id="ctrl-window" min="3" max="36" step="1">

      <div class="sep"></div>

      <label>Base % of cash <span class="val" id="v-basepct"></span></label>
      <input type="range" id="ctrl-basepct" min="0.01" max="0.25" step="0.005">

      <label>Drop threshold <span class="val" id="v-dropth"></span></label>
      <input type="range" id="ctrl-dropth" min="0.01" max="0.40" step="0.01">

      <label>Rise threshold <span class="val" id="v-riseth"></span></label>
      <input type="range" id="ctrl-riseth" min="0.01" max="0.40" step="0.01">

      <label>Drop factor <span class="val" id="v-dropf"></span></label>
      <input type="range" id="ctrl-dropf" min="0.5" max="15" step="0.1">

      <label>Rise factor <span class="val" id="v-risef"></span></label>
      <input type="range" id="ctrl-risef" min="0.5" max="10" step="0.1">

      <div class="sep"></div>

      <label>Min multiplier <span class="val" id="v-minmult"></span></label>
      <input type="range" id="ctrl-minmult" min="0" max="1" step="0.01">

      <label>Max multiplier <span class="val" id="v-maxmult"></span></label>
      <input type="range" id="ctrl-maxmult" min="1" max="8" step="0.1">

      <label>Cooldown (months) <span class="val" id="v-cooldown"></span></label>
      <input type="range" id="ctrl-cooldown" min="0" max="12" step="1">

      <div class="sep"></div>

      <label>Initial cash (&euro;) <span class="val" id="v-cash"></span></label>
      <input type="range" id="ctrl-cash" min="10000" max="1000000" step="10000">

      <label>Simulation window (months) <span class="val" id="v-simwindow"></span></label>
      <input type="range" id="ctrl-simwindow" min="12" max="120" step="1">

      <div class="sep"></div>

      <label>Time period
        <select id="ctrl-period">
          <option value="full">Full history</option>
          <option value="train">Training only</option>
          <option value="validation">Validation only</option>
        </select>
      </label>

      <label>Start from month #
        <select id="ctrl-startmonth"></select>
      </label>

      <div class="sep"></div>
      <button id="btn-reset">Reset to Optimal</button>
    </div>

    <div class="period-info">
      Training ends: <b>{train_end}</b><br>
      Validation starts: <b>{val_start}</b><br>
      Optimization score: <b>{results['optimization_score']:.4%}</b> mean outperf.
    </div>
  </div>

  <!-- RIGHT: Results -->
  <div>
    <div class="kpi-row">
      <div class="kpi"><div class="label">Weighted DCA</div><div class="val" id="kpi-wroi">-</div><div class="sub" id="kpi-wval"></div></div>
      <div class="kpi"><div class="label">Fixed-% DCA</div><div class="val" id="kpi-droi">-</div><div class="sub" id="kpi-dval"></div></div>
      <div class="kpi"><div class="label">Lump Sum</div><div class="val" id="kpi-lroi">-</div><div class="sub" id="kpi-lval"></div></div>
      <div class="kpi"><div class="label">Outperformance</div><div class="val" id="kpi-delta">-</div><div class="sub">vs fixed-% DCA</div></div>
    </div>

    <div class="chart" id="chart-value"></div>
    <div class="chart" id="chart-invest"></div>
    <div class="chart" id="chart-drop"></div>
  </div>
</div>

<script>
// === EMBEDDED DATA ===
const ALL_PRICES = {json.dumps(prices)};
const OPTIMAL = {json.dumps(params)};
const TRAIN_END = "{train_end}";
const VAL_START = "{val_start}";
const DEFAULT_CASH = 200000;

// === STRATEGY (percentage-based, mirrors Python exactly) ===
function runWeightedDCA(prices, p, initialCash) {{
  const n = Math.min(prices.length, p._simWindow || 24);
  let cash = initialCash, cumUnits = 0, cumInvested = 0, cooldown = 0;
  const rows = [];

  for (let i = 0; i < n; i++) {{
    const price = prices[i].price;
    const date = prices[i].date;

    let ref;
    if (p.reference_type === "ath") {{
      ref = Math.max(...prices.slice(0, i + 1).map(d => d.price));
    }} else {{
      const lb = Math.max(0, i - p.window_months);
      ref = Math.max(...prices.slice(lb, i + 1).map(d => d.price));
    }}

    const dropPct = (ref - price) / ref;

    let mult;
    if (dropPct > p.drop_threshold) {{
      mult = 1 + p.drop_factor * (dropPct - p.drop_threshold);
    }} else if (dropPct < -p.rise_threshold) {{
      mult = Math.max(0, 1 - p.rise_factor * (-dropPct - p.rise_threshold));
    }} else {{
      mult = 1;
    }}

    if (cooldown > 0) {{ mult = Math.min(mult, 1); cooldown--; }}
    mult = Math.max(p.min_mult, Math.min(p.max_mult, mult));

    let inv = cash * p.base_pct * mult;
    inv = Math.min(inv, cash);

    if (mult >= p.max_mult * 0.95) cooldown = p.cooldown_months;

    const units = price > 0 ? inv / price : 0;
    cumUnits += units; cumInvested += inv; cash -= inv;

    rows.push({{ date, price, ref, dropPct, mult, inv, units, cumUnits, cumInvested, cash, value: cumUnits * price }});
  }}
  return rows;
}}

function runRegularDCA(prices, basePct, initialCash, simWindow) {{
  const n = Math.min(prices.length, simWindow || 24);
  let cash = initialCash, cumUnits = 0, cumInvested = 0;
  const rows = [];
  for (let i = 0; i < n; i++) {{
    const price = prices[i].price;
    let inv = cash * basePct;
    inv = Math.min(inv, cash);
    cumUnits += price > 0 ? inv / price : 0;
    cumInvested += inv; cash -= inv;
    rows.push({{ date: prices[i].date, price, inv, cumUnits, cumInvested, cash, value: cumUnits * price }});
  }}
  return rows;
}}

function runLumpSum(prices, initialCash, simWindow) {{
  const n = Math.min(prices.length, simWindow || 24);
  const units = prices[0].price > 0 ? initialCash / prices[0].price : 0;
  return prices.slice(0, n).map((d) => ({{
    date: d.date, price: d.price, value: units * d.price, cumInvested: initialCash, cash: 0,
  }}));
}}

// === CONTROLS ===
const C = {{
  reftype: document.getElementById('ctrl-reftype'),
  window: document.getElementById('ctrl-window'),
  basepct: document.getElementById('ctrl-basepct'),
  dropth: document.getElementById('ctrl-dropth'),
  riseth: document.getElementById('ctrl-riseth'),
  dropf: document.getElementById('ctrl-dropf'),
  risef: document.getElementById('ctrl-risef'),
  minmult: document.getElementById('ctrl-minmult'),
  maxmult: document.getElementById('ctrl-maxmult'),
  cooldown: document.getElementById('ctrl-cooldown'),
  cash: document.getElementById('ctrl-cash'),
  simwindow: document.getElementById('ctrl-simwindow'),
  period: document.getElementById('ctrl-period'),
  startmonth: document.getElementById('ctrl-startmonth'),
}};

function setOptimal() {{
  C.reftype.value = OPTIMAL.reference_type;
  C.window.value = OPTIMAL.window_months;
  C.basepct.value = OPTIMAL.base_pct;
  C.dropth.value = OPTIMAL.drop_threshold;
  C.riseth.value = OPTIMAL.rise_threshold;
  C.dropf.value = OPTIMAL.drop_factor;
  C.risef.value = OPTIMAL.rise_factor;
  C.minmult.value = OPTIMAL.min_mult;
  C.maxmult.value = OPTIMAL.max_mult;
  C.cooldown.value = OPTIMAL.cooldown_months;
  C.cash.value = DEFAULT_CASH;
  C.simwindow.value = 24;
  C.period.value = "full";
}}

function readParams() {{
  return {{
    reference_type: C.reftype.value,
    window_months: +C.window.value,
    base_pct: +C.basepct.value,
    drop_threshold: +C.dropth.value,
    rise_threshold: +C.riseth.value,
    drop_factor: +C.dropf.value,
    rise_factor: +C.risef.value,
    min_mult: +C.minmult.value,
    max_mult: +C.maxmult.value,
    cooldown_months: +C.cooldown.value,
    _simWindow: +C.simwindow.value,
  }};
}}

function updateLabels() {{
  document.getElementById('v-window').textContent = C.window.value;
  document.getElementById('v-basepct').textContent = (C.basepct.value * 100).toFixed(1) + '%';
  document.getElementById('v-dropth').textContent = (C.dropth.value * 100).toFixed(0) + '%';
  document.getElementById('v-riseth').textContent = (C.riseth.value * 100).toFixed(0) + '%';
  document.getElementById('v-dropf').textContent = (+C.dropf.value).toFixed(1) + 'x';
  document.getElementById('v-risef').textContent = (+C.risef.value).toFixed(1) + 'x';
  document.getElementById('v-minmult').textContent = (+C.minmult.value).toFixed(2) + 'x';
  document.getElementById('v-maxmult').textContent = (+C.maxmult.value).toFixed(1) + 'x';
  document.getElementById('v-cooldown').textContent = C.cooldown.value;
  document.getElementById('v-cash').textContent = '\\u20ac' + (+C.cash.value).toLocaleString();
  document.getElementById('v-simwindow').textContent = C.simwindow.value;
}}

function populateStartMonths() {{
  const sel = C.startmonth;
  sel.innerHTML = '';
  ALL_PRICES.forEach((d, i) => {{
    if (i % 6 === 0) {{
      const opt = document.createElement('option');
      opt.value = i; opt.textContent = d.date;
      sel.appendChild(opt);
    }}
  }});
}}

function getActivePrices() {{
  const period = C.period.value;
  let prices = ALL_PRICES;

  if (period === 'train') {{
    prices = ALL_PRICES.filter(d => d.date <= TRAIN_END);
  }} else if (period === 'validation') {{
    prices = ALL_PRICES.filter(d => d.date >= VAL_START);
  }}

  const startIdx = +C.startmonth.value;
  const globalStart = ALL_PRICES[startIdx]?.date;
  if (globalStart) {{
    const idx = prices.findIndex(d => d.date >= globalStart);
    if (idx > 0) prices = prices.slice(idx);
  }}

  return prices;
}}

// === PLOTTING ===
const plotLayout = (title) => ({{
  title: {{ text: title, font: {{ size: 14, color: '#e6edf3' }} }},
  paper_bgcolor: '#0d1117', plot_bgcolor: '#161b22',
  font: {{ color: '#8b949e', size: 11 }},
  xaxis: {{ gridcolor: '#30363d', linecolor: '#30363d' }},
  yaxis: {{ gridcolor: '#30363d', linecolor: '#30363d' }},
  margin: {{ l: 60, r: 20, t: 40, b: 40 }},
  legend: {{ orientation: 'h', y: -0.15, font: {{ size: 11 }} }},
  hovermode: 'x unified',
}});

const plotConfig = {{ responsive: true, displayModeBar: false }};

function fmtPct(v) {{ return (v >= 0 ? '+' : '') + (v * 100).toFixed(2) + '%'; }}
function fmtEur(v) {{ return '\\u20ac' + v.toLocaleString(undefined, {{maximumFractionDigits: 0}}); }}

function update() {{
  updateLabels();
  const p = readParams();
  const prices = getActivePrices();
  const initialCash = +C.cash.value;
  const simWindow = +C.simwindow.value;

  if (prices.length < 2) return;

  const w = runWeightedDCA(prices, p, initialCash);
  const d = runRegularDCA(prices, p.base_pct, initialCash, simWindow);
  const l = runLumpSum(prices, initialCash, simWindow);

  const last = (arr) => arr[arr.length - 1];

  // KPIs: total wealth = portfolio value + remaining cash
  const wLast = last(w), dLast = last(d), lLast = last(l);
  const wWealth = wLast.value + wLast.cash;
  const dWealth = dLast.value + dLast.cash;
  const lWealth = lLast.value + (lLast.cash || 0);
  const wRoi = wWealth / initialCash - 1;
  const dRoi = dWealth / initialCash - 1;
  const lRoi = lWealth / initialCash - 1;
  const delta = wRoi - dRoi;

  const kpiW = document.getElementById('kpi-wroi');
  const kpiD = document.getElementById('kpi-droi');
  const kpiL = document.getElementById('kpi-lroi');
  const kpiDelta = document.getElementById('kpi-delta');

  kpiW.textContent = fmtPct(wRoi);
  kpiW.className = 'val ' + (wRoi >= 0 ? 'positive' : 'negative');
  document.getElementById('kpi-wval').textContent = fmtEur(wWealth);

  kpiD.textContent = fmtPct(dRoi);
  kpiD.className = 'val ' + (dRoi >= 0 ? 'positive' : 'negative');
  document.getElementById('kpi-dval').textContent = fmtEur(dWealth);

  kpiL.textContent = fmtPct(lRoi);
  kpiL.className = 'val ' + (lRoi >= 0 ? 'positive' : 'negative');
  document.getElementById('kpi-lval').textContent = fmtEur(lWealth);

  kpiDelta.textContent = fmtPct(delta);
  kpiDelta.className = 'val ' + (delta >= 0 ? 'positive' : 'negative');

  // Chart 1: Total wealth over time
  Plotly.react('chart-value', [
    {{ x: w.map(r => r.date), y: w.map(r => r.value + r.cash), name: 'Weighted DCA', line: {{ color: '#58a6ff', width: 2 }} }},
    {{ x: d.map(r => r.date), y: d.map(r => r.value + r.cash), name: 'Fixed-% DCA', line: {{ color: '#8b949e', width: 2 }} }},
    {{ x: l.map(r => r.date), y: l.map(r => r.value), name: 'Lump Sum', line: {{ color: '#d29922', width: 1.5, dash: 'dot' }} }},
    {{ x: w.map(r => r.date), y: w.map(r => r.cumInvested), name: 'Deployed', line: {{ color: '#f85149', width: 1, dash: 'dash' }} }},
  ], plotLayout('Total Wealth (&euro;)'), plotConfig);

  // Chart 2: Monthly investment amounts
  Plotly.react('chart-invest', [
    {{ x: w.map(r => r.date), y: w.map(r => r.inv), type: 'bar', name: 'Weighted', marker: {{ color: w.map(r => r.mult > 1 ? '#3fb950' : r.mult < 1 ? '#f85149' : '#58a6ff') }} }},
    {{ x: d.map(r => r.date), y: d.map(r => r.inv), name: 'Fixed-%', line: {{ color: '#8b949e', width: 1.5, dash: 'dash' }} }},
  ], {{...plotLayout('Monthly Investment (&euro;)'), barmode: 'overlay'}}, plotConfig);

  // Chart 3: Drop from reference + multiplier
  Plotly.react('chart-drop', [
    {{ x: w.map(r => r.date), y: w.map(r => r.dropPct * 100), name: 'Drop from ref (%)', line: {{ color: '#f85149', width: 1.5 }}, yaxis: 'y' }},
    {{ x: w.map(r => r.date), y: w.map(r => r.mult), name: 'Multiplier', line: {{ color: '#3fb950', width: 1.5 }}, yaxis: 'y2' }},
  ], {{
    ...plotLayout('Market Drop & Investment Multiplier'),
    yaxis: {{ title: 'Drop %', gridcolor: '#30363d', linecolor: '#30363d', side: 'left' }},
    yaxis2: {{ title: 'Multiplier', overlaying: 'y', side: 'right', gridcolor: 'transparent' }},
  }}, plotConfig);
}}

// === INIT ===
populateStartMonths();
setOptimal();
update();

Object.values(C).forEach(el => el.addEventListener('input', update));
document.getElementById('btn-reset').addEventListener('click', () => {{ setOptimal(); update(); }});
</script>
</body>
</html>"""

    out = REPORT_DIR / "index.html"
    out.write_text(html)
    print(f"Report written to {out} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
