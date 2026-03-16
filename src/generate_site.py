#!/usr/bin/env python3
"""Generate the self-contained DCA advisor website.

Reads historical price data and optimal parameters, produces a single
deployable HTML file at site/index.html with all logic running client-side.
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd

from strategy import portfolio_monthly

DATA_DIR = Path(__file__).parent.parent / "data"
REPORT_DIR = Path(__file__).parent.parent / "report"
SITE_DIR = Path(__file__).parent.parent / "site"


def main():
    # Load optimization results
    with open(REPORT_DIR / "results.json") as f:
        results = json.load(f)

    # Compute monthly portfolio index
    portfolio = portfolio_monthly(
        str(DATA_DIR / "msci_world.csv"),
        str(DATA_DIR / "msci_em.csv"),
    )
    monthly_data = [
        {"d": d.strftime("%Y-%m-%d"), "p": round(float(p), 4)}
        for d, p in portfolio.items()
    ]

    # Get reference prices for bridging
    world = pd.read_csv(DATA_DIR / "msci_world.csv", parse_dates=["date"], index_col="date")
    em = pd.read_csv(DATA_DIR / "msci_em.csv", parse_dates=["date"], index_col="date")

    meta = {
        "generated": date.today().isoformat(),
        "lastIWDA": round(float(world["close"].iloc[-1]), 4),
        "lastIWDADate": world.index[-1].strftime("%Y-%m-%d"),
        "lastEIMI": round(float(em["close"].iloc[-1]), 4),
        "lastEIMIDate": em.index[-1].strftime("%Y-%m-%d"),
        "firstIWDA": round(float(world.loc[world.index >= em.index[0], "close"].iloc[0]), 6),
        "firstEIMI": round(float(em["close"].iloc[0]), 6),
        "trainEnd": results["train_end"],
        "valStart": results["validation_start"],
        "optScore": results["optimization_score"],
    }

    # Try to get SWRD.L cross-ratio
    try:
        import yfinance as yf
        swrd = yf.download("SWRD.L", period="5d", auto_adjust=True, progress=False)
        if isinstance(swrd.columns, pd.MultiIndex):
            last_swrd = float(swrd["Close"].iloc[-1].iloc[0])
        else:
            last_swrd = float(swrd["Close"].iloc[-1])
        meta["swrdRatio"] = round(last_swrd / meta["lastIWDA"], 6)
        meta["lastSWRD"] = round(last_swrd, 4)
    except Exception:
        meta["swrdRatio"] = None
        meta["lastSWRD"] = None

    params_json = json.dumps(results["params"])
    monthly_json = json.dumps(monthly_data)
    meta_json = json.dumps(meta)

    html = _build_html(params_json, monthly_json, meta_json)

    SITE_DIR.mkdir(exist_ok=True)
    (SITE_DIR / "data").mkdir(exist_ok=True)
    (SITE_DIR / "api").mkdir(exist_ok=True)

    out = SITE_DIR / "index.html"
    out.write_text(html)
    print(f"Site written to {out} ({len(html):,} bytes)")

    # Seed data/prices.json (historical portfolio prices)
    prices_out = SITE_DIR / "data" / "prices.json"
    with open(prices_out, "w") as f:
        json.dump(monthly_data, f)
    print(f"Seed prices: {prices_out} ({len(monthly_data)} months)")

    # Write data/config.json (normalization values for PHP price updates)
    config = {
        "firstIWDA": meta["firstIWDA"],
        "firstEIMI": meta["firstEIMI"],
        "swrdRatio": meta.get("swrdRatio"),
        "defaults": results["params"],
    }
    config_out = SITE_DIR / "data" / "config.json"
    with open(config_out, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Config: {config_out}")


def _build_html(params_json, monthly_json, meta_json):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Weighted DCA Advisor</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root {{
  --bg:#0d1117; --sf:#161b22; --sf2:#1c2129; --bd:#30363d;
  --tx:#e6edf3; --mt:#8b949e; --ac:#58a6ff; --gn:#3fb950;
  --rd:#f85149; --yl:#d29922; --or:#db6d28;
}}
*{{ margin:0; padding:0; box-sizing:border-box; }}
body{{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
  background:var(--bg); color:var(--tx); line-height:1.5; }}
.wrap{{ max-width:1100px; margin:0 auto; padding:20px; }}
h1{{ font-size:1.5rem; }}
h2{{ font-size:1.1rem; color:var(--ac); margin:0 0 12px; }}
.sub{{ color:var(--mt); font-size:.85rem; margin-bottom:16px; }}
.panel{{ background:var(--sf); border:1px solid var(--bd); border-radius:8px; padding:16px; margin-bottom:16px; }}
.row{{ display:flex; gap:16px; flex-wrap:wrap; }}
.row>*{{ flex:1; min-width:280px; }}
label{{ display:block; font-size:.82rem; color:var(--mt); margin-bottom:2px; }}
input,select{{ width:100%; background:var(--bg); color:var(--tx); border:1px solid var(--bd);
  border-radius:4px; padding:6px 10px; font-size:.9rem; margin-bottom:10px; }}
input:focus{{ border-color:var(--ac); outline:none; }}
button{{ padding:8px 16px; border:1px solid var(--ac); background:transparent; color:var(--ac);
  border-radius:6px; cursor:pointer; font-size:.85rem; }}
button:hover{{ background:var(--ac); color:var(--bg); }}
button.secondary{{ border-color:var(--bd); color:var(--mt); }}
button.secondary:hover{{ background:var(--bd); color:var(--tx); }}
button.danger{{ border-color:var(--rd); color:var(--rd); }}
button.danger:hover{{ background:var(--rd); color:var(--bg); }}

.rec-card{{
  background:linear-gradient(135deg,#1a2332,#162028); border:2px solid var(--ac);
  border-radius:12px; padding:24px; text-align:center; margin:12px 0;
}}
.rec-card .amount{{ font-size:2.2rem; font-weight:800; color:var(--gn); }}
.rec-card .pct{{ font-size:1.1rem; color:var(--ac); margin-top:2px; }}
.rec-card .split{{ font-size:.95rem; color:var(--mt); margin-top:4px; }}
.rec-card .reason{{ font-size:.85rem; margin-top:12px; display:flex; justify-content:center;
  gap:24px; flex-wrap:wrap; }}
.rec-card .reason div{{ text-align:center; }}
.rec-card .reason .val{{ font-size:1.1rem; font-weight:700; }}
.rec-card .reason .lbl{{ font-size:.72rem; color:var(--mt); text-transform:uppercase; }}

.status{{ display:inline-block; padding:2px 8px; border-radius:10px; font-size:.75rem;
  font-weight:600; }}
.status.green{{ background:#0d331a; color:var(--gn); }}
.status.amber{{ background:#332200; color:var(--yl); }}
.status.red{{ background:#330d0d; color:var(--rd); }}

.chart{{ width:100%; height:320px; margin-bottom:12px; }}

table{{ width:100%; border-collapse:collapse; font-size:.82rem; }}
th{{ text-align:left; color:var(--mt); font-weight:600; padding:6px 8px;
  border-bottom:1px solid var(--bd); }}
td{{ padding:6px 8px; border-bottom:1px solid var(--bd); }}
tr:hover td{{ background:var(--sf2); }}
.num{{ text-align:right; font-family:monospace; }}
.positive{{ color:var(--gn); }}
.negative{{ color:var(--rd); }}

.health-bar{{ display:flex; gap:4px; align-items:center; margin:4px 0; }}
.health-bar .bar{{ flex:1; height:6px; background:var(--bd); border-radius:3px; overflow:hidden; }}
.health-bar .fill{{ height:100%; border-radius:3px; }}
.health-bar .label{{ font-size:.78rem; min-width:120px; color:var(--mt); }}
.health-bar .score{{ font-size:.78rem; min-width:60px; text-align:right; font-family:monospace; }}

.progress{{ width:100%; height:4px; background:var(--bd); border-radius:2px; margin:8px 0;
  overflow:hidden; display:none; }}
.progress .bar{{ height:100%; background:var(--ac); transition:width .2s; }}

.actions{{ display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }}
.hidden{{ display:none !important; }}

.top-status{{ background:var(--bg2); border:1px solid var(--bd); border-radius:8px;
  padding:8px 14px; margin-bottom:16px; font-size:.82rem; }}
.top-status .progress{{ margin:4px 0 0; }}
.top-status.done .progress{{ display:none; }}
.top-status.done{{ border-color:var(--gn); }}
.toast{{
  position:fixed; bottom:20px; right:20px; background:var(--sf); border:1px solid var(--gn);
  color:var(--gn); padding:10px 16px; border-radius:8px; font-size:.85rem;
  animation:fadeout 3s forwards; z-index:999;
}}
@keyframes fadeout{{ 0%,70%{{ opacity:1; }} 100%{{ opacity:0; }} }}
</style>
</head>
<body>
<div class="wrap">

<!-- HEADER -->
<h1>Weighted DCA Monthly Advisor</h1>
<p class="sub">70% SPDR MSCI World (IE00BFY0GT14 / A2N6CW) / 30% iShares MSCI EM IMI (IE00BKM4GZ66 / A111X9) &mdash; buy-the-dip strategy</p>
<div id="top-status" class="top-status">
  <span id="top-status-text">Loading...</span>
  <div class="progress" id="top-progress"><div class="bar" id="top-bar"></div></div>
</div>

<!-- SECTION 1: RECOMMENDATION -->
<div class="panel">
  <h2>This Month&rsquo;s Recommendation</h2>
  <div id="rec-empty" class="sub">Loading prices and optimizing parameters&hellip;</div>
  <div id="rec-card" class="rec-card hidden">
    <div class="pct" id="rec-pct" style="font-size:1.6rem;font-weight:700;"></div>
    <div class="reason">
      <div><div class="val" id="rec-drop"></div><div class="lbl">Drop from ref</div></div>
      <div><div class="val" id="rec-mult"></div><div class="lbl">Multiplier</div></div>
      <div><div class="val" id="rec-ref"></div><div class="lbl">Rolling high</div></div>
      <div><div class="val" id="rec-cur"></div><div class="lbl">Current</div></div>
    </div>
    <hr style="border-color:var(--bd);margin:14px 0;">
    <div class="row" style="align-items:end;">
      <div style="flex:1;"><label for="in-cash">Available cash (&euro;)</label>
        <input type="number" id="in-cash" step="1000" placeholder="e.g. 200000"></div>
      <div><button id="btn-calc" style="margin-top:0;">Calculate Amount</button></div>
    </div>
    <div id="rec-amount-section" class="hidden" style="margin-top:12px;">
      <div class="amount" id="rec-amount"></div>
      <div class="split" id="rec-split"></div>
      <div class="actions" style="margin-top:10px;">
        <button id="btn-record">Record This Investment</button>
      </div>
    </div>
  </div>
</div>

<!-- Hidden inputs for auto-fetched prices -->
<input type="hidden" id="in-world">
<input type="hidden" id="in-em">
<input type="hidden" id="in-date">
<div id="fetch-status" class="hidden"></div>

<!-- SECTION 2: CHARTS -->
<div class="panel">
  <h2>Visual Analysis</h2>
  <div class="chart" id="chart-portfolio"></div>
  <div class="chart" id="chart-drop"></div>
  <div class="chart" id="chart-investments"></div>
</div>

<!-- SECTION 3: INVESTMENT LOG -->
<div class="panel">
  <h2>Investment Log</h2>
  <div style="overflow-x:auto;">
    <table id="log-table">
      <thead><tr>
        <th>Date</th><th class="num">SWRD</th><th class="num">EIMI</th>
        <th class="num">Drop%</th><th class="num">Mult</th>
        <th class="num">Investment</th><th class="num">World</th><th class="num">EM</th>
        <th></th>
      </tr></thead>
      <tbody id="log-body"></tbody>
    </table>
  </div>
  <div id="log-empty" class="sub" style="margin-top:8px;">No investments recorded yet.</div>
  <div class="actions" style="margin-top:8px;">
    <button class="secondary" id="btn-export">Export JSON</button>
    <button class="secondary" id="btn-import">Import JSON</button>
    <input type="file" id="import-file" accept=".json" class="hidden">
  </div>
</div>

<!-- SECTION 4: PARAMETER HEALTH CHECK -->
<div class="panel">
  <h2>Parameter Health Check</h2>
  <p class="sub">Runs automatically after fetching prices. Tests parameter variations via walk-forward
  cross-validation and auto-applies improvements. You can also trigger it manually.</p>
  <button id="btn-health">Run Health Check</button>
  <div class="sub hidden" id="health-eta" style="margin-top:6px;"></div>
  <div class="progress" id="health-progress"><div class="bar" id="health-bar"></div></div>
  <div id="health-results" class="hidden" style="margin-top:12px;">
    <div style="margin-bottom:10px;">
      Overall: <span class="status" id="health-status"></span>
      &nbsp; Median outperformance: <b id="health-score"></b>
      &nbsp; <span class="sub" id="health-folds"></span>
    </div>
    <div id="health-params"></div>
    <div id="health-suggestions" class="hidden" style="margin-top:10px;"></div>
  </div>
</div>

<!-- SECTION 5: SETTINGS -->
<div class="panel">
  <h2>Settings &amp; Parameters</h2>
  <table id="params-table" style="font-size:.78rem;"></table>
  <div class="actions" style="margin-top:10px;">
    <button class="danger" id="btn-reset">Reset All Data</button>
  </div>
</div>

</div><!-- /wrap -->

<script>
// ======================= EMBEDDED DATA (seed / fallback) =======================
let P = {monthly_json};
const DEFAULTS = {params_json};
const META = {meta_json};
const BACKTEST_CASH = 200000;  // initial cash for backtest comparisons

// ======================= API HELPERS =======================
const API = {{
  async get(url) {{
    try {{
      const r = await fetch(url);
      if (r.ok) return await r.json();
    }} catch {{}}
    return null;
  }},
  async post(url, body) {{
    try {{
      const r = await fetch(url, {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(body),
      }});
      if (r.ok) return await r.json();
    }} catch {{}}
    return null;
  }},
}};

// ======================= STATE =======================
const State = {{
  params: null,
  log: [],
  _hasBackend: false,
  async load() {{
    const remote = await API.get('api/state.php');
    if (remote) {{
      this._hasBackend = true;
      this.params = remote.params || {{...DEFAULTS}};
      this.log = remote.log || [];
      localStorage.setItem('wdca_state', JSON.stringify({{params: this.params, log: this.log}}));
      return;
    }}
    try {{
      const s = localStorage.getItem('wdca_state');
      if (s) {{
        const d = JSON.parse(s);
        this.params = d.params || {{...DEFAULTS}};
        this.log = d.log || [];
      }} else {{
        this.params = {{...DEFAULTS}};
        this.log = [];
      }}
    }} catch {{ this.params = {{...DEFAULTS}}; this.log = []; }}
  }},
  async save() {{
    localStorage.setItem('wdca_state', JSON.stringify({{params: this.params, log: this.log}}));
    if (this._hasBackend) {{
      await API.post('api/state.php', {{params: this.params, log: this.log}});
    }}
  }},
  async reset() {{
    this.params = {{...DEFAULTS}};
    this.log = [];
    await this.save();
  }},
}};

// ======================= PRICE BRIDGE =======================
const Bridge = {{
  toPortfolio(swrd, eimi) {{
    let iwdaEff;
    if (META.swrdRatio) {{
      iwdaEff = swrd / META.swrdRatio;
    }} else {{
      const prev = this._lastRef();
      const chgW = (swrd - prev.swrd) / prev.swrd;
      const chgE = (eimi - prev.eimi) / prev.eimi;
      return prev.portfolio * (1 + 0.7 * chgW + 0.3 * chgE);
    }}
    const wNorm = iwdaEff / META.firstIWDA * 100;
    const eNorm = eimi / META.firstEIMI * 100;
    return 0.7 * wNorm + 0.3 * eNorm;
  }},
  _lastRef() {{
    if (State.log.length > 0) {{
      const last = State.log[State.log.length - 1];
      return {{ swrd: last.swrd, eimi: last.eimi, portfolio: last.portfolioPrice }};
    }}
    return {{ swrd: META.lastSWRD || META.lastIWDA, eimi: META.lastEIMI,
             portfolio: P[P.length - 1].p }};
  }},
}};

// ======================= STRATEGY =======================
const Strategy = {{
  recommend(allPrices, params, cash) {{
    // Percentage-based: invest cash * base_pct * multiplier
    const current = allPrices[allPrices.length - 1];
    let ref;
    if (params.reference_type === 'ath') {{
      ref = Math.max(...allPrices);
    }} else {{
      const windowSize = params.window_months || 19;
      const windowStart = Math.max(0, allPrices.length - windowSize);
      ref = Math.max(...allPrices.slice(windowStart));
    }}
    const dropPct = (ref - current) / ref;

    // Raw multiplier
    let mult;
    if (dropPct > params.drop_threshold) {{
      mult = 1 + params.drop_factor * (dropPct - params.drop_threshold);
    }} else if (dropPct < -params.rise_threshold) {{
      mult = Math.max(0, 1 - params.rise_factor * (-dropPct - params.rise_threshold));
    }} else {{
      mult = 1;
    }}

    // Check cooldown from recent log entries
    let cooldown = 0;
    for (let i = State.log.length - 1; i >= 0; i--) {{
      if (State.log[i].cooldownTriggered) {{
        cooldown = params.cooldown_months - (State.log.length - 1 - i);
        if (cooldown < 0) cooldown = 0;
        break;
      }}
    }}
    if (cooldown > 0) mult = Math.min(mult, 1.0);

    // Clamp multiplier
    mult = Math.max(params.min_mult, Math.min(params.max_mult, mult));

    // Investment = cash * base_pct * multiplier
    const basePct = params.base_pct || 0.05;
    let inv = cash * basePct * mult;
    inv = Math.min(inv, Math.max(0, cash));

    const effectivePct = basePct * mult;
    const cooldownTriggered = mult >= params.max_mult * 0.95;

    return {{
      refHigh: ref, current, dropPct, multiplier: mult,
      investment: Math.round(inv * 100) / 100,
      worldAmount: Math.round(inv * 0.7 * 100) / 100,
      emAmount: Math.round(inv * 0.3 * 100) / 100,
      effectivePct,
      cooldownTriggered,
    }};
  }},

  // Full backtest (for health check): percentage-based weighted DCA
  backtest(prices, params, initialCash) {{
    const n = prices.length;
    const basePct = params.base_pct || 0.05;
    let cash = initialCash, cumUnits = 0, cd = 0;

    for (let i = 0; i < n; i++) {{
      const price = prices[i];
      let ref;
      if (params.reference_type === 'ath') {{
        ref = prices.slice(0, i + 1).reduce((a, b) => Math.max(a, b), 0);
      }} else {{
        const lb = Math.max(0, i - (params.window_months || 19));
        ref = prices.slice(lb, i + 1).reduce((a, b) => Math.max(a, b), 0);
      }}
      const drop = (ref - price) / ref;

      let mult;
      if (drop > params.drop_threshold) mult = 1 + params.drop_factor * (drop - params.drop_threshold);
      else if (drop < -params.rise_threshold) mult = Math.max(0, 1 - params.rise_factor * (-drop - params.rise_threshold));
      else mult = 1;

      if (cd > 0) {{ mult = Math.min(mult, 1); cd--; }}
      mult = Math.max(params.min_mult, Math.min(params.max_mult, mult));

      let inv = cash * basePct * mult;
      inv = Math.min(inv, cash);

      if (mult >= params.max_mult * 0.95) cd = params.cooldown_months;

      cumUnits += price > 0 ? inv / price : 0;
      cash -= inv;
    }}
    // Total wealth ROI
    const wealth = cumUnits * prices[n - 1] + cash;
    return wealth / initialCash - 1;
  }},

  backtestRegular(prices, basePct, initialCash) {{
    const n = prices.length;
    let cash = initialCash, cumUnits = 0;
    for (let i = 0; i < n; i++) {{
      let inv = cash * basePct;
      inv = Math.min(inv, cash);
      cumUnits += prices[i] > 0 ? inv / prices[i] : 0;
      cash -= inv;
    }}
    const wealth = cumUnits * prices[n - 1] + cash;
    return wealth / initialCash - 1;
  }},
}};

// ======================= OPTIMIZER =======================
// Three-phase optimization:
//   Phase 1: Coordinate-wise grid search (wide exploration)
//   Phase 2: Random neighborhood search (global exploration)
//   Phase 3: Coordinate-wise refinement (fine-tuning around best)
const Optimizer = {{
  BOUNDS: {{
    window_months:  [3, 36],
    drop_threshold: [0.01, 0.30],
    rise_threshold: [0.02, 0.30],
    drop_factor:    [0.5, 15],
    rise_factor:    [0.5, 10],
    min_mult:       [0, 0.5],
    max_mult:       [1.5, 6],
    cooldown_months:[0, 9],
    base_pct:       [0.02, 0.25],
  }},

  GRIDS: {{
    window_months:  [3, 6, 9, 12, 15, 18, 21, 24, 28, 32, 36],
    drop_threshold: [0.01, 0.02, 0.03, 0.05, 0.07, 0.09, 0.12, 0.15, 0.18, 0.22, 0.27],
    rise_threshold: [0.02, 0.04, 0.07, 0.10, 0.13, 0.16, 0.20, 0.25, 0.30],
    drop_factor:    [0.5, 1, 2, 4, 6, 8, 10, 12, 14, 15],
    rise_factor:    [0.5, 1, 2, 3, 5, 7, 8, 10],
    min_mult:       [0, 0.02, 0.04, 0.08, 0.12, 0.2, 0.3, 0.5],
    max_mult:       [1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6],
    cooldown_months:[0, 1, 2, 3, 4, 5, 6, 9],
    base_pct:       [0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.13, 0.16, 0.20, 0.25],
  }},

  RANDOM_SAMPLES: 5000,

  generateFolds(prices) {{
    const folds = [];
    const windowSize = 24;
    const step = 8;
    for (let end = prices.length; end >= windowSize; end -= step) {{
      const start = end - windowSize;
      if (start < 0) break;
      folds.push(prices.slice(start, end));
    }}
    return folds.length > 0 ? folds : [prices.slice(-24)];
  }},

  scoreParams(folds, params) {{
    const scores = folds.map(f => {{
      const w = Strategy.backtest(f, params, BACKTEST_CASH);
      const d = Strategy.backtestRegular(f, params.base_pct || 0.05, BACKTEST_CASH);
      return w - d;
    }});
    return {{ scores, median: this.median(scores) }};
  }},

  median(arr) {{
    const s = [...arr].sort((a, b) => a - b);
    const m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  }},

  linspace(lo, hi, n) {{
    const arr = [];
    for (let i = 0; i < n; i++) arr.push(lo + (hi - lo) * i / (n - 1));
    return arr;
  }},

  clamp(v, lo, hi) {{ return Math.max(lo, Math.min(hi, v)); }},

  async run(onProgress) {{
    const prices = P.map(d => d.p);
    const params = {{...State.params}};
    const folds = this.generateFolds(prices);
    const paramNames = Object.keys(this.GRIDS);

    // Estimate total work: phase1 + phase2 + phase3
    const phase1Steps = paramNames.reduce((s, k) => s + this.GRIDS[k].length, 0) * folds.length;
    const phase2Steps = this.RANDOM_SAMPLES * folds.length;
    const phase3Steps = paramNames.length * 20 * folds.length;
    const totalSteps = phase1Steps + phase2Steps + phase3Steps;
    let step = 0;
    const t0 = performance.now();

    const report = async () => {{
      if (step % (folds.length * 3) === 0) {{
        const elapsed = (performance.now() - t0) / 1000;
        const rate = step / elapsed;
        const eta = rate > 0 ? Math.ceil((totalSteps - step) / rate) : 0;
        onProgress(step / totalSteps, eta);
        await new Promise(r => setTimeout(r, 0));
      }}
    }};

    // Current baseline
    const current = this.scoreParams(folds, params);
    const currentMedian = current.median;
    const currentScores = current.scores;

    // ---- PHASE 1: Coordinate-wise grid search ----
    let best = {{...params}};
    let bestMedian = currentMedian;
    const results = {{}};

    for (const name of paramNames) {{
      let bestVal = best[name];
      let bestMed = -Infinity;
      const details = [];

      for (const candidate of this.GRIDS[name]) {{
        const testParams = {{...best, [name]: candidate}};
        const {{ scores, median: med }} = this.scoreParams(folds, testParams);
        const winsCount = scores.filter((s, i) => s > currentScores[i]).length;
        details.push({{ value: candidate, median: med, wins: winsCount, total: folds.length }});
        if (med > bestMed) {{ bestMed = med; bestVal = candidate; }}
        step += folds.length;
        await report();
      }}

      results[name] = {{ current: params[name], best: bestVal, bestMedian: bestMed, details }};
      // Apply best for this param (greedy coordinate descent)
      if (bestMed > bestMedian) {{
        best[name] = bestVal;
        bestMedian = bestMed;
      }}
    }}

    // ---- PHASE 2: Random neighborhood search ----
    // Generate random parameter sets around the current best
    const rng = (lo, hi) => lo + Math.random() * (hi - lo);

    for (let i = 0; i < this.RANDOM_SAMPLES; i++) {{
      const candidate = {{}};
      for (const name of paramNames) {{
        const [lo, hi] = this.BOUNDS[name];
        const cur = best[name];
        const range = hi - lo;
        // Random perturbation: ±40% of full range, centered on current best
        const spread = range * 0.4;
        let v = cur + (Math.random() - 0.5) * 2 * spread;
        v = this.clamp(v, lo, hi);
        if (name === 'window_months' || name === 'cooldown_months') v = Math.round(v);
        candidate[name] = v;
      }}
      const {{ median: med }} = this.scoreParams(folds, candidate);
      if (med > bestMedian) {{
        for (const k of paramNames) best[k] = candidate[k];
        bestMedian = med;
      }}
      step += folds.length;
      await report();
    }}

    // ---- PHASE 3: Coordinate-wise refinement around best ----
    const suggestions = {{}};

    for (const name of paramNames) {{
      const [lo, hi] = this.BOUNDS[name];
      const cur = best[name];
      const range = hi - lo;
      // Fine grid: 20 values centered around best, ±15% of range
      const spread = range * 0.15;
      const fineLo = this.clamp(cur - spread, lo, hi);
      const fineHi = this.clamp(cur + spread, lo, hi);
      const grid = this.linspace(fineLo, fineHi, 20);

      let bestVal = best[name];
      let bestMed = -Infinity;

      for (let g of grid) {{
        if (name === 'window_months' || name === 'cooldown_months') g = Math.round(g);
        const testParams = {{...best, [name]: g}};
        const {{ scores, median: med }} = this.scoreParams(folds, testParams);
        if (med > bestMed) {{ bestMed = med; bestVal = g; }}
        step += folds.length;
        await report();
      }}

      if (bestMed > bestMedian) {{
        best[name] = bestVal;
        bestMedian = bestMed;
      }}

      // Track changes from original params
      const orig = params[name];
      const changed = (name === 'window_months' || name === 'cooldown_months')
        ? best[name] !== orig
        : Math.abs(best[name] - orig) > 0.001;
      if (changed) {{
        // Verify improvement: must win >50% of folds vs original
        const {{ scores: bestScores }} = this.scoreParams(folds, best);
        const winsCount = bestScores.filter((s, i) => s > currentScores[i]).length;
        if (bestMedian - currentMedian > 0.002 && winsCount > folds.length / 2) {{
          suggestions[name] = {{
            current: orig,
            suggested: best[name],
            improvement: bestMedian - currentMedian,
          }};
        }}
      }}

      // Update results details for display
      if (!results[name]) results[name] = {{ current: params[name], best: best[name], bestMedian, details: [] }};
      results[name].best = best[name];
      results[name].bestMedian = bestMedian;
    }}

    const elapsed = ((performance.now() - t0) / 1000).toFixed(1);
    onProgress(1, 0);
    return {{
      currentMedian, foldCount: folds.length,
      dataMonths: prices.length, results, suggestions,
      healthy: Object.keys(suggestions).length === 0,
      elapsed,
    }};
  }},
}};

// ======================= PRICE FETCHER =======================
const Fetcher = {{
  async fetch() {{
    const data = await API.get('api/prices.php?update=1');
    if (data && data['SWRD.L'] && data['EIMI.L']) return data;

    const tickers = ['SWRD.L', 'EIMI.L'];
    const results = {{}};
    for (const ticker of tickers) {{
      try {{
        const url = `https://query1.finance.yahoo.com/v8/finance/chart/${{ticker}}?range=5d&interval=1d`;
        const r = await fetch(url, {{ signal: AbortSignal.timeout(5000) }});
        if (!r.ok) continue;
        const d = await r.json();
        const price = d?.chart?.result?.[0]?.meta?.regularMarketPrice;
        if (price) results[ticker] = price;
      }} catch {{}}
    }}
    return (results['SWRD.L'] && results['EIMI.L']) ? results : null;
  }},
}};

// ======================= CHARTS =======================
const Charts = {{
  layout(title, extra) {{
    return {{
      title: {{ text: title, font: {{ size: 13, color: '#e6edf3' }} }},
      paper_bgcolor: '#161b22', plot_bgcolor: '#0d1117',
      font: {{ color: '#8b949e', size: 10 }},
      xaxis: {{ gridcolor: '#30363d', linecolor: '#30363d' }},
      yaxis: {{ gridcolor: '#30363d', linecolor: '#30363d' }},
      margin: {{ l: 55, r: 20, t: 36, b: 36 }},
      legend: {{ orientation: 'h', y: -0.18, font: {{ size: 10 }} }},
      hovermode: 'x unified', ...extra,
    }};
  }},
  cfg: {{ responsive: true, displayModeBar: false }},

  update() {{
    const dates = P.map(d => d.d);
    const prices = P.map(d => d.p);
    const windowSize = State.params.window_months || 19;
    const rollingHigh = prices.map((p, i) => {{
      if (State.params.reference_type === 'ath') {{
        return Math.max(...prices.slice(0, i + 1));
      }}
      const start = Math.max(0, i - windowSize);
      return Math.max(...prices.slice(start, i + 1));
    }});

    const logDates = State.log.map(e => e.date);
    const logPrices = State.log.map(e => e.portfolioPrice);

    const refLabel = State.params.reference_type === 'ath' ? 'ATH' : windowSize + 'mo Rolling High';
    const traces1 = [
      {{ x: dates, y: prices, name: 'Portfolio', line: {{ color: '#58a6ff', width: 2 }} }},
      {{ x: dates, y: rollingHigh, name: refLabel, line: {{ color: '#8b949e', width: 1, dash: 'dot' }} }},
    ];
    if (logDates.length) {{
      traces1.push({{ x: logDates, y: logPrices, name: 'Your entries', mode: 'markers',
        marker: {{ color: '#3fb950', size: 8, symbol: 'diamond' }} }});
    }}
    Plotly.react('chart-portfolio', traces1, this.layout('Portfolio Index vs ' + refLabel), this.cfg);

    const drops = prices.map((p, i) => ((rollingHigh[i] - p) / rollingHigh[i]) * 100);
    const thLine = Array(dates.length).fill(State.params.drop_threshold * 100);
    Plotly.react('chart-drop', [
      {{ x: dates, y: drops, name: 'Drop from ' + refLabel, fill: 'tozeroy',
        fillcolor: 'rgba(248,81,73,0.1)', line: {{ color: '#f85149', width: 1.5 }} }},
      {{ x: dates, y: thLine, name: 'Threshold (' + (State.params.drop_threshold * 100).toFixed(0) + '%)',
        line: {{ color: '#d29922', width: 1, dash: 'dash' }} }},
    ], this.layout('Drop from ' + refLabel + ' (%)'), this.cfg);

    if (State.log.length) {{
      const invDates = State.log.map(e => e.date);
      const invAmts = State.log.map(e => e.investment);
      const avg = invAmts.reduce((a, b) => a + b, 0) / invAmts.length;
      Plotly.react('chart-investments', [
        {{ x: invDates, y: invAmts, type: 'bar', name: 'Monthly investment',
          marker: {{ color: invAmts.map(a => a > avg * 1.2 ? '#3fb950' : a < avg * 0.8 ? '#f85149' : '#58a6ff') }} }},
        {{ x: invDates, y: Array(invDates.length).fill(avg), name: 'Average',
          line: {{ color: '#8b949e', width: 1.5, dash: 'dash' }} }},
      ], this.layout('Monthly Investments (&euro;)'), this.cfg);
    }} else {{
      Plotly.react('chart-investments', [], this.layout('Monthly Investments (no data yet)'), this.cfg);
    }}
  }},
}};

// ======================= UI =======================
const UI = {{
  async init() {{
    const remoteP = await API.get('api/data.php');
    if (remoteP && remoteP.length > 0) P = remoteP;

    await State.load();

    const now = new Date();
    $('in-date').value = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');

    this.bindEvents();
    this.renderLog();
    this.renderParams();
    Charts.update();

    // Auto-fetch prices and run optimization on every page load
    this.onFetch();
  }},

  bindEvents() {{
    $('btn-calc').onclick = () => this.onCalc();
    $('in-cash').onkeydown = (e) => {{ if (e.key === 'Enter') this.onCalc(); }};
    $('btn-record').onclick = () => this.onRecord();
    $('btn-health').onclick = () => this.onHealth();
    $('btn-export').onclick = () => this.onExport();
    $('btn-import').onclick = () => $('import-file').click();
    $('import-file').onchange = (e) => this.onImport(e);
    $('btn-reset').onclick = () => this.onReset();
  }},

  _lastRec: null,
  _ready: false,

  showRecommendation() {{
    const swrd = parseFloat($('in-world').value);
    const eimi = parseFloat($('in-em').value);
    if (!swrd || !eimi || swrd <= 0 || eimi <= 0) return;

    const portfolioPrice = Bridge.toPortfolio(swrd, eimi);
    const allPrices = P.map(d => d.p);
    State.log.forEach(e => allPrices.push(e.portfolioPrice));
    allPrices.push(portfolioPrice);

    // Compute recommendation with cash=1 to get percentage and market stats
    const rec = Strategy.recommend(allPrices, State.params, 1);
    rec.swrd = swrd;
    rec.eimi = eimi;
    rec.portfolioPrice = portfolioPrice;
    rec.date = $('in-date').value;

    // Show percentage recommendation
    $('rec-empty').classList.add('hidden');
    $('rec-card').classList.remove('hidden');

    const color = rec.dropPct > State.params.drop_threshold ? 'var(--gn)' :
                  rec.dropPct < -State.params.rise_threshold ? 'var(--yl)' : 'var(--ac)';
    $('rec-pct').textContent = 'Invest ' + (rec.effectivePct * 100).toFixed(1) + '% of your cash';
    $('rec-pct').style.color = color;
    $('rec-drop').textContent = pct(rec.dropPct);
    $('rec-drop').className = 'val ' + (rec.dropPct > 0 ? 'negative' : 'positive');
    $('rec-mult').textContent = rec.multiplier.toFixed(2) + 'x';
    $('rec-ref').textContent = rec.refHigh.toFixed(1);
    $('rec-cur').textContent = rec.current.toFixed(1);

    // Store partial rec for amount calculation
    this._lastRec = rec;
    $('rec-amount-section').classList.add('hidden');

    // If cash is already filled, auto-calculate
    const cash = parseFloat($('in-cash').value) || 0;
    if (cash > 0) this.onCalc();
  }},

  onCalc() {{
    if (!this._lastRec) return;
    const cash = parseFloat($('in-cash').value) || 0;
    if (cash <= 0) return;

    const rec = this._lastRec;
    const basePct = State.params.base_pct || 0.05;
    let inv = cash * basePct * rec.multiplier;
    inv = Math.min(inv, Math.max(0, cash));
    rec.cash = cash;
    rec.investment = Math.round(inv * 100) / 100;
    rec.worldAmount = Math.round(inv * 0.7 * 100) / 100;
    rec.emAmount = Math.round(inv * 0.3 * 100) / 100;

    const color = rec.dropPct > State.params.drop_threshold ? 'var(--gn)' :
                  rec.dropPct < -State.params.rise_threshold ? 'var(--yl)' : 'var(--ac)';
    $('rec-amount').textContent = eur(rec.investment);
    $('rec-amount').style.color = color;
    $('rec-split').textContent = eur(rec.worldAmount) + ' World + ' + eur(rec.emAmount) + ' EM';
    $('rec-amount-section').classList.remove('hidden');
  }},

  async onRecord() {{
    if (!this._lastRec || !this._lastRec.cash) return;
    const r = this._lastRec;
    const cumInv = State.log.reduce((s, e) => s + e.investment, 0) + r.investment;
    State.log.push({{
      date: r.date,
      swrd: r.swrd,
      eimi: r.eimi,
      portfolioPrice: r.portfolioPrice,
      dropPct: r.dropPct,
      multiplier: r.multiplier,
      investment: r.investment,
      worldAmount: r.worldAmount,
      emAmount: r.emAmount,
      cooldownTriggered: r.cooldownTriggered,
      cumInvested: cumInv,
    }});
    await State.save();

    // Update cash input (subtract invested amount)
    const newCash = Math.max(0, r.cash - r.investment);
    $('in-cash').value = Math.round(newCash);

    // Append portfolio price to historical dataset
    const dateStr = r.date.length === 7 ? r.date + '-28' : r.date;
    API.post('api/data.php', {{ d: dateStr, p: r.portfolioPrice }}).then(res => {{
      if (res && !res.replaced) {{
        API.get('api/data.php').then(d => {{ if (d && d.length > 0) P = d; }});
      }}
    }});

    this._lastRec = null;

    $('rec-amount-section').classList.add('hidden');

    // Re-show recommendation with updated cash
    this.showRecommendation();

    this.renderLog();
    Charts.update();
    toast('Investment recorded');
  }},

  async onFetch() {{
    const ts = $('top-status');
    const tt = $('top-status-text');
    ts.classList.remove('done');
    tt.textContent = 'Fetching latest prices...';
    $('top-progress').style.display = 'block';
    $('top-bar').style.width = '0%';
    try {{
      const prices = await Fetcher.fetch();
      if (prices) {{
        $('in-world').value = prices['SWRD.L'].toFixed(2);
        $('in-em').value = prices['EIMI.L'].toFixed(2);
        if (prices.newMonths > 0) {{
          const fresh = await API.get('api/data.php');
          if (fresh && fresh.length > 0) {{ P = fresh; Charts.update(); }}
        }}
        $('fetch-status').textContent = 'Prices updated.';
        this.runOptimization();
      }} else {{
        $('fetch-status').textContent = 'Enter prices manually.';
        tt.textContent = 'Auto-fetch unavailable. Running parameter check...';
        this.runOptimization();
      }}
    }} catch {{
      $('fetch-status').textContent = 'Enter prices manually.';
      tt.textContent = 'Auto-fetch failed. Running parameter check...';
      this.runOptimization();
    }}
  }},

  async runOptimization() {{
    const ts = $('top-status');
    const tt = $('top-status-text');
    ts.classList.remove('done');
    $('top-progress').style.display = 'block';

    $('btn-health').disabled = true;
    $('health-progress').style.display = 'block';
    $('health-results').classList.add('hidden');
    $('health-eta').textContent = 'Starting...';
    $('health-eta').classList.remove('hidden');

    const result = await Optimizer.run((pct, eta) => {{
      const pctW = (pct * 100) + '%';
      $('health-bar').style.width = pctW;
      $('top-bar').style.width = pctW;
      if (pct >= 1) {{
        $('health-eta').textContent = '';
        tt.textContent = 'Finishing...';
      }} else {{
        const phase = pct < 0.15 ? 'Grid search' : pct < 0.85 ? 'Random exploration' : 'Refinement';
        const etaText = eta > 0 ? ` (~${{eta}}s remaining)` : '';
        const msg = `${{phase}}... ${{Math.round(pct * 100)}}%${{etaText}}`;
        $('health-eta').textContent = msg;
        tt.textContent = 'Optimizing parameters: ' + msg;
      }}
    }});

    $('health-progress').style.display = 'none';
    $('health-eta').classList.add('hidden');
    $('health-results').classList.remove('hidden');
    $('btn-health').disabled = false;
    $('top-progress').style.display = 'none';
    ts.classList.add('done');

    const sug = result.suggestions;
    const applied = [];
    for (const [name, s] of Object.entries(sug)) {{
      State.params[name] = s.suggested;
      applied.push(name);
    }}
    if (applied.length > 0) {{
      await State.save();
      this.renderParams();
    }}

    const badge = $('health-status');
    if (result.healthy) {{
      badge.textContent = 'Parameters confirmed'; badge.className = 'status green';
      tt.textContent = '\u2713 Parameters confirmed \u2014 ready to calculate.';
    }} else {{
      badge.textContent = applied.length + ' parameter(s) updated'; badge.className = 'status amber';
      tt.textContent = '\u2713 ' + applied.length + ' parameter(s) auto-updated \u2014 ready to calculate.';
    }}

    this._ready = true;
    $('btn-calc').disabled = false;
    this.showRecommendation();

    $('health-score').textContent = pct(result.currentMedian);
    $('health-folds').textContent = `(${{result.foldCount}} folds, ${{result.dataMonths}} months, ${{result.elapsed}}s)`;

    let html = '';
    for (const [name, data] of Object.entries(result.results)) {{
      const wasUpdated = sug[name] != null;
      const isCurrent = data.best === data.current && !wasUpdated;
      const max = Math.max(...data.details.map(d => d.median), 0.001);
      const curMed = data.details.find(d => d.value === (wasUpdated ? sug[name].suggested : data.current))?.median || 0;
      const fillPct = Math.max(0, Math.min(100, (curMed / max) * 100));
      const color = wasUpdated ? 'var(--yl)' : isCurrent ? 'var(--gn)' : 'var(--ac)';
      const label = name.replace(/_/g, ' ');
      const valText = wasUpdated
        ? `${{fmtVal(name, sug[name].current)}} &rarr; ${{fmtVal(name, sug[name].suggested)}}`
        : fmtVal(name, data.current);
      html += `<div class="health-bar">
        <span class="label">${{label}}</span>
        <div class="bar"><div class="fill" style="width:${{fillPct}}%;background:${{color}}"></div></div>
        <span class="score">${{valText}}</span>
      </div>`;
    }}
    $('health-params').innerHTML = html;

    const sugDiv = $('health-suggestions');
    if (applied.length > 0) {{
      sugDiv.classList.remove('hidden');
      sugDiv.innerHTML = `<p style="color:var(--gn);font-size:.85rem;">
        Auto-updated ${{applied.length}} parameter(s) based on ${{result.dataMonths}} months of data
        across ${{result.foldCount}} walk-forward folds.</p>`;
    }} else {{
      sugDiv.classList.remove('hidden');
      sugDiv.innerHTML = `<p style="color:var(--gn);font-size:.85rem;">
        All parameters confirmed optimal across ${{result.foldCount}} walk-forward folds (${{result.dataMonths}} months of data).</p>`;
    }}
  }},

  async onHealth() {{
    this.runOptimization();
  }},

  renderLog() {{
    const body = $('log-body');
    if (State.log.length === 0) {{
      body.innerHTML = '';
      $('log-empty').classList.remove('hidden');
      return;
    }}
    $('log-empty').classList.add('hidden');
    body.innerHTML = State.log.map((e, i) => `<tr>
      <td>${{e.date}}</td>
      <td class="num">${{e.swrd.toFixed(2)}}</td>
      <td class="num">${{e.eimi.toFixed(2)}}</td>
      <td class="num ${{e.dropPct > 0 ? 'negative' : 'positive'}}">${{pct(e.dropPct)}}</td>
      <td class="num">${{e.multiplier.toFixed(2)}}x</td>
      <td class="num"><b>${{eur(e.investment)}}</b></td>
      <td class="num">${{eur(e.worldAmount)}}</td>
      <td class="num">${{eur(e.emAmount)}}</td>
      <td><button class="secondary" style="padding:1px 6px;font-size:.7rem;"
        onclick="UI.deleteEntry(${{i}})">x</button></td>
    </tr>`).join('');
  }},

  async deleteEntry(idx) {{
    if (!confirm('Delete this entry?')) return;
    State.log.splice(idx, 1);
    await State.save();
    this.renderLog();
    Charts.update();
  }},

  renderParams() {{
    const p = State.params;
    const rows = [
      ['Reference', p.reference_type],
      ['Window', p.window_months + ' months'],
      ['Base %', ((p.base_pct || 0.05) * 100).toFixed(1) + '% of cash'],
      ['Drop threshold', (p.drop_threshold * 100).toFixed(0) + '%'],
      ['Drop factor', p.drop_factor.toFixed(1) + 'x'],
      ['Rise threshold', (p.rise_threshold * 100).toFixed(0) + '%'],
      ['Rise factor', p.rise_factor.toFixed(1) + 'x'],
      ['Min multiplier', (p.min_mult || 0).toFixed(2) + 'x'],
      ['Max multiplier', (p.max_mult || 3).toFixed(1) + 'x'],
      ['Cooldown', p.cooldown_months + ' months'],
    ];
    $('params-table').innerHTML = rows.map(([k, v]) =>
      `<tr><td style="color:var(--mt)">${{k}}</td><td style="font-family:monospace">${{v}}</td></tr>`
    ).join('');
  }},

  onExport() {{
    const blob = new Blob([JSON.stringify({{ params: State.params, log: State.log }}, null, 2)],
      {{ type: 'application/json' }});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'wdca_data_' + new Date().toISOString().slice(0, 10) + '.json';
    a.click();
  }},

  onImport(e) {{
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async () => {{
      try {{
        const data = JSON.parse(reader.result);
        if (data.params) State.params = data.params;
        if (data.log) State.log = data.log;
        await State.save();
        this.renderLog();
        this.renderParams();
        Charts.update();
        toast('Data imported');
      }} catch {{ alert('Invalid JSON file.'); }}
    }};
    reader.readAsText(file);
    e.target.value = '';
  }},

  async onReset() {{
    if (!confirm('This will delete all investment records and reset parameters. Continue?')) return;
    await State.reset();
    this.renderLog();
    this.renderParams();
    Charts.update();
    $('rec-card').classList.add('hidden');
    $('rec-amount-section').classList.add('hidden');
    $('rec-empty').classList.remove('hidden');
    $('rec-empty').textContent = 'Recommendation will appear after prices are fetched and parameters optimized.';
    $('in-cash').value = '';
    toast('All data reset');
    // Re-fetch and re-optimize
    this.onFetch();
  }},
}};

// ======================= HELPERS =======================
function $(id) {{ return document.getElementById(id); }}
function eur(v) {{ return '\\u20ac' + Math.round(v).toLocaleString(); }}
function pct(v) {{ return (v >= 0 ? '+' : '') + (v * 100).toFixed(1) + '%'; }}
function fmtVal(name, v) {{
  if (name.includes('threshold')) return (v * 100).toFixed(0) + '%';
  if (name.includes('factor')) return v.toFixed(1) + 'x';
  if (name.includes('mult')) return v.toFixed(2) + 'x';
  if (name.includes('base_pct')) return (v * 100).toFixed(1) + '%';
  if (name.includes('cooldown')) return v + 'mo';
  return v;
}}
function toast(msg) {{
  const el = document.createElement('div');
  el.className = 'toast'; el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}}

// ======================= INIT =======================
document.addEventListener('DOMContentLoaded', () => UI.init());
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
