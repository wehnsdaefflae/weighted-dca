"""Weighted DCA strategy implementation and comparison baselines."""

import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict


@dataclass
class Params:
    """All tunable parameters for the weighted DCA strategy.

    The strategy returns a multiplier based on market conditions.
    Investment each month = available_cash × base_pct × multiplier.
    """
    # How to measure the "reference high" for computing drops
    reference_type: str = "rolling"  # "ath" or "rolling"
    window_months: int = 12          # lookback for rolling high

    # Thresholds: ignore drops/rises smaller than these
    drop_threshold: float = 0.05     # 5% drop before we start buying more
    rise_threshold: float = 0.05     # 5% rise before we start buying less

    # Scaling factors: how aggressively to scale investment
    drop_factor: float = 2.0         # multiplier per unit drop beyond threshold
    rise_factor: float = 1.0         # multiplier per unit rise beyond threshold

    # Hard limits on the multiplier
    min_mult: float = 0.0
    max_mult: float = 3.0

    # Cooldown: after hitting max, how many months to revert to base
    cooldown_months: int = 0

    # Base monthly investment as fraction of available cash
    base_pct: float = 0.05

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_vector(cls, x):
        """Construct from optimizer vector [ref_type, window, drop_th, rise_th,
        drop_f, rise_f, min_mult, max_mult, cooldown, base_pct]."""
        return cls(
            reference_type="rolling" if x[0] < 0.5 else "ath",
            window_months=int(round(x[1])),
            drop_threshold=x[2],
            rise_threshold=x[3],
            drop_factor=x[4],
            rise_factor=x[5],
            min_mult=x[6],
            max_mult=x[7],
            cooldown_months=int(round(x[8])),
            base_pct=x[9],
        )

    def to_vector(self):
        return [
            0.0 if self.reference_type == "rolling" else 1.0,
            float(self.window_months),
            self.drop_threshold,
            self.rise_threshold,
            self.drop_factor,
            self.rise_factor,
            self.min_mult,
            self.max_mult,
            float(self.cooldown_months),
            self.base_pct,
        ]


def portfolio_monthly(world_csv: str, em_csv: str,
                      world_w: float = 0.7, em_w: float = 0.3) -> pd.Series:
    """Load CSVs and return a monthly 70/30 portfolio index."""
    world = pd.read_csv(world_csv, parse_dates=["date"], index_col="date")["close"]
    em = pd.read_csv(em_csv, parse_dates=["date"], index_col="date")["close"]

    # Align on common trading days
    common = world.index.intersection(em.index)
    world, em = world.loc[common], em.loc[common]

    # Normalize each to 100
    port = world_w * (world / world.iloc[0] * 100) + em_w * (em / em.iloc[0] * 100)
    monthly = port.resample("ME").last().dropna()
    monthly.name = "price"
    return monthly


def run_weighted_dca(prices: pd.Series, p: Params,
                     initial_cash: float) -> pd.DataFrame:
    """Execute the weighted DCA strategy on monthly prices.

    Each month: invest available_cash × base_pct × multiplier.
    Returns DataFrame with per-month details.
    """
    n = len(prices)
    cash = initial_cash
    cum_units = cum_invested = 0.0
    cooldown = 0
    rows = []

    for i in range(n):
        price = prices.iloc[i]
        date = prices.index[i]

        # Reference high
        if p.reference_type == "ath":
            ref = prices.iloc[: i + 1].max()
        else:
            lb = max(0, i - p.window_months)
            ref = prices.iloc[lb : i + 1].max()

        drop_pct = (ref - price) / ref  # positive = dropped

        # Multiplier
        if drop_pct > p.drop_threshold:
            mult = 1.0 + p.drop_factor * (drop_pct - p.drop_threshold)
        elif drop_pct < -p.rise_threshold:
            mult = max(0.0, 1.0 - p.rise_factor * (-drop_pct - p.rise_threshold))
        else:
            mult = 1.0

        # Cooldown suppresses over-investment
        if cooldown > 0:
            mult = min(mult, 1.0)
            cooldown -= 1

        # Clamp multiplier
        mult = float(np.clip(mult, p.min_mult, p.max_mult))

        # Investment = cash × base_pct × multiplier
        inv = cash * p.base_pct * mult
        inv = min(inv, max(0.0, cash))

        if mult >= p.max_mult * 0.95:
            cooldown = p.cooldown_months

        units = inv / price if price > 0 else 0
        cum_units += units
        cum_invested += inv
        cash -= inv

        rows.append(dict(
            date=date, price=price, ref_high=ref, drop_pct=drop_pct,
            multiplier=mult, investment=inv, units=units,
            cum_units=cum_units, cum_invested=cum_invested,
            remaining=cash, value=cum_units * price,
        ))

    return pd.DataFrame(rows)


def run_regular_dca(prices: pd.Series, initial_cash: float,
                    base_pct: float) -> pd.DataFrame:
    """Fixed-percentage DCA: invest base_pct of remaining cash each month."""
    n = len(prices)
    cash = initial_cash
    cum_units = cum_invested = 0.0
    rows = []
    for i in range(n):
        price = prices.iloc[i]
        inv = cash * base_pct
        inv = min(inv, cash)
        units = inv / price if price > 0 else 0
        cum_units += units
        cum_invested += inv
        cash -= inv
        rows.append(dict(
            date=prices.index[i], price=price, investment=inv,
            cum_units=cum_units, cum_invested=cum_invested,
            remaining=cash, value=cum_units * price,
        ))
    return pd.DataFrame(rows)


def run_lump_sum(prices: pd.Series, budget: float) -> pd.DataFrame:
    n = len(prices)
    units = budget / prices.iloc[0] if prices.iloc[0] > 0 else 0
    rows = []
    for i in range(n):
        rows.append(dict(
            date=prices.index[i], price=prices.iloc[i],
            investment=budget if i == 0 else 0,
            cum_invested=budget, remaining=0.0,
            value=units * prices.iloc[i],
        ))
    return pd.DataFrame(rows)
