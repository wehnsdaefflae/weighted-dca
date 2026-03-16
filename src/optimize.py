#!/usr/bin/env python3
"""Optimize weighted DCA parameters via differential evolution.

Trains on historical data, holds out the most recent period for validation.
Outputs optimal parameters + monthly price data for the HTML report.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution

from strategy import Params, portfolio_monthly, run_weighted_dca, run_regular_dca

DATA_DIR = Path(__file__).parent.parent / "data"
REPORT_DIR = Path(__file__).parent.parent / "report"

# --- configuration ---
INITIAL_CASH = 200_000          # starting available cash for backtests
WINDOW_SIZE = 24                # months per simulation window
VALIDATION_MONTHS = 24          # hold out last 2 years
WINDOW_STEP_DIVISOR = 4         # overlap sliding windows by 1/4

# --- progress tracking ---
_eval_count = 0
_best_score = float("inf")
_start_time = None


def load_prices() -> pd.Series:
    return portfolio_monthly(
        str(DATA_DIR / "msci_world.csv"),
        str(DATA_DIR / "msci_em.csv"),
    )


def score_params(x, train_prices, initial_cash):
    """Negative mean outperformance vs fixed-pct DCA across sliding windows.

    Compares total wealth (portfolio value + remaining cash) for weighted
    vs fixed-percentage DCA using the same base_pct.
    """
    global _eval_count, _best_score
    _eval_count += 1

    p = Params.from_vector(x)
    step = max(1, WINDOW_SIZE // WINDOW_STEP_DIVISOR)
    deltas = []

    for start in range(0, len(train_prices) - WINDOW_SIZE, step):
        window = train_prices.iloc[start : start + WINDOW_SIZE]
        if len(window) < WINDOW_SIZE:
            break

        w = run_weighted_dca(window, p, initial_cash)
        d = run_regular_dca(window, initial_cash, p.base_pct)

        # Total wealth = portfolio value + remaining cash
        w_wealth = w["value"].iloc[-1] + w["remaining"].iloc[-1]
        d_wealth = d["value"].iloc[-1] + d["remaining"].iloc[-1]

        w_roi = w_wealth / initial_cash - 1
        d_roi = d_wealth / initial_cash - 1
        deltas.append(w_roi - d_roi)

    if not deltas:
        return 0.0
    score = -float(np.mean(deltas))

    if score < _best_score:
        _best_score = score
    if _eval_count % 100 == 0:
        elapsed = time.time() - _start_time
        print(f"  eval #{_eval_count:,d} | best outperf: {-_best_score:.4%} | "
              f"elapsed: {elapsed:.0f}s", flush=True)

    return score


# Parameter bounds: [ref_type, window, drop_th, rise_th,
#                     drop_f, rise_f, min_mult, max_mult, cooldown, base_pct]
BOUNDS = [
    (0, 1),         # reference_type: <0.5 = rolling, >=0.5 = ath
    (3, 36),        # window_months
    (0.02, 0.30),   # drop_threshold
    (0.02, 0.30),   # rise_threshold
    (0.5, 15.0),    # drop_factor
    (0.5, 10.0),    # rise_factor
    (0.0, 0.5),     # min_mult
    (1.5, 5.0),     # max_mult
    (0, 6),         # cooldown_months
    (0.02, 0.25),   # base_pct: 2% to 25% of cash per month
]


def main():
    prices = load_prices()
    print(f"Portfolio data: {prices.index[0].date()} to {prices.index[-1].date()} "
          f"({len(prices)} months)")

    train = prices.iloc[:-VALIDATION_MONTHS]
    val_start_idx = len(prices) - VALIDATION_MONTHS - WINDOW_SIZE
    val_prices = prices.iloc[max(0, val_start_idx):]

    print(f"Training:   {train.index[0].date()} to {train.index[-1].date()} "
          f"({len(train)} months)")
    print(f"Validation: last {VALIDATION_MONTHS} months "
          f"(from {prices.index[-VALIDATION_MONTHS].date()})")
    print(f"Sliding windows: {WINDOW_SIZE}mo, step {WINDOW_SIZE // WINDOW_STEP_DIVISOR}mo")

    n_windows = len(range(0, len(train) - WINDOW_SIZE, max(1, WINDOW_SIZE // WINDOW_STEP_DIVISOR)))
    print(f"Training windows: {n_windows}")
    print(f"Initial cash: €{INITIAL_CASH:,.0f}")
    print()

    global _start_time, _eval_count, _best_score
    _start_time = time.time()
    _eval_count = 0
    _best_score = float("inf")

    pop = 15  # 15 × 10 params = 150 individuals per generation
    max_it = 150
    est_evals = pop * len(BOUNDS) * (max_it + 1)
    print(f"Running differential evolution (pop={pop}, maxiter={max_it}, "
          f"~{est_evals:,d} max evaluations)...")
    print(flush=True)

    result = differential_evolution(
        score_params,
        BOUNDS,
        args=(train, INITIAL_CASH),
        seed=42,
        maxiter=max_it,
        tol=1e-6,
        popsize=pop,
        mutation=(0.5, 1.5),
        recombination=0.8,
    )

    optimal = Params.from_vector(result.x)
    print(f"\nOptimization converged: {result.success} (iterations: {result.nit})")
    print(f"Mean outperformance vs fixed-pct DCA: {-result.fun:.4%}")
    print(f"\nOptimal parameters:")
    for k, v in optimal.to_dict().items():
        print(f"  {k}: {v}")

    # --- Evaluate on training (last window) and validation ---
    def evaluate(label, data):
        window = data.iloc[-WINDOW_SIZE:] if len(data) >= WINDOW_SIZE else data
        w = run_weighted_dca(window, optimal, INITIAL_CASH)
        d = run_regular_dca(window, INITIAL_CASH, optimal.base_pct)

        w_wealth = w["value"].iloc[-1] + w["remaining"].iloc[-1]
        d_wealth = d["value"].iloc[-1] + d["remaining"].iloc[-1]
        w_roi = w_wealth / INITIAL_CASH - 1
        d_roi = d_wealth / INITIAL_CASH - 1

        print(f"\n{label}:")
        print(f"  Weighted DCA: ROI {w_roi:+.2%}, total wealth €{w_wealth:,.0f}")
        print(f"  Fixed-pct DCA: ROI {d_roi:+.2%}, total wealth €{d_wealth:,.0f}")
        print(f"  Outperformance: {w_roi - d_roi:+.2%} (€{w_wealth - d_wealth:+,.0f})")

        # Also show deployment stats
        w_deployed = w["cum_invested"].iloc[-1]
        d_deployed = d["cum_invested"].iloc[-1]
        print(f"  Deployed: weighted €{w_deployed:,.0f} ({w_deployed/INITIAL_CASH:.0%}), "
              f"fixed €{d_deployed:,.0f} ({d_deployed/INITIAL_CASH:.0%})")
        return {"weighted_roi": w_roi, "dca_roi": d_roi, "delta": w_roi - d_roi}

    train_stats = evaluate("Training (last window)", train)
    val_stats = evaluate("Validation (last window)", val_prices)

    # --- Export for report ---
    REPORT_DIR.mkdir(exist_ok=True)

    # Round floats in params for cleanliness
    params_dict = optimal.to_dict()
    for k, v in params_dict.items():
        if isinstance(v, float):
            params_dict[k] = round(v, 4)

    output = {
        "params": params_dict,
        "train_end": str(train.index[-1].date()),
        "validation_start": str(prices.index[-VALIDATION_MONTHS].date()),
        "optimization_score": round(-result.fun, 6),
        "train_stats": {k: round(v, 6) for k, v in train_stats.items()},
        "val_stats": {k: round(v, 6) for k, v in val_stats.items()},
    }

    with open(REPORT_DIR / "results.json", "w") as f:
        json.dump(output, f, indent=2)

    # Export monthly prices as JSON array for the HTML report
    price_data = [
        {"date": d.strftime("%Y-%m-%d"), "price": round(float(p), 4)}
        for d, p in prices.items()
    ]
    with open(REPORT_DIR / "prices.json", "w") as f:
        json.dump(price_data, f)

    elapsed = time.time() - _start_time
    print(f"\nTotal time: {elapsed:.0f}s ({_eval_count:,d} evaluations)")
    print(f"Results saved to {REPORT_DIR}/")


if __name__ == "__main__":
    main()
