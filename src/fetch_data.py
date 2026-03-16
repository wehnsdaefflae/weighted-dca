#!/usr/bin/env python3
"""Fetch historical price data for the 70/30 portfolio ETFs.

Uses iShares MSCI World (IWDA) and iShares MSCI EM IMI (EIMI) as proxies
with the longest available UCITS history for their respective indices.
"""

import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

DATA_DIR = Path(__file__).parent.parent / "data"

# Tickers to try in order of preference (longest history first)
ASSETS = {
    "msci_world": [
        ("IWDA.L", "iShares Core MSCI World (London)"),
        ("IWDA.AS", "iShares Core MSCI World (Amsterdam)"),
        ("SWRD.L", "SPDR MSCI World (London)"),
        ("URTH", "iShares MSCI World (US-listed)"),
    ],
    "msci_em": [
        ("EIMI.L", "iShares Core MSCI EM IMI (London)"),
        ("EMIM.L", "iShares Core MSCI EM IMI (London alt)"),
        ("IEMA.L", "iShares MSCI EM (London)"),
        ("EEM", "iShares MSCI EM (US-listed)"),
    ],
}


def fetch(ticker: str, name: str) -> pd.DataFrame | None:
    print(f"  Trying {ticker} ({name})...", end=" ")
    try:
        data = yf.download(ticker, period="max", auto_adjust=True, progress=False)
        if data.empty or len(data) < 100:
            print("insufficient data")
            return None
        # Handle multi-level columns from yfinance
        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"].iloc[:, 0]
        else:
            close = data["Close"]
        df = close.to_frame("close").dropna()
        df.index.name = "date"
        print(f"OK ({len(df)} rows, {df.index[0].date()} to {df.index[-1].date()})")
        return df
    except Exception as e:
        print(f"error: {e}")
        return None


def main():
    DATA_DIR.mkdir(exist_ok=True)

    for asset_name, tickers in ASSETS.items():
        print(f"\nFetching {asset_name}:")
        for ticker, desc in tickers:
            df = fetch(ticker, desc)
            if df is not None:
                path = DATA_DIR / f"{asset_name}.csv"
                df.to_csv(path)
                print(f"  -> Saved to {path}")
                break
        else:
            print(f"  ERROR: Could not fetch data for {asset_name}")
            sys.exit(1)

    print("\nData files:")
    for f in sorted(DATA_DIR.glob("*.csv")):
        df = pd.read_csv(f, parse_dates=["date"])
        print(f"  {f.name}: {df['date'].min().date()} to {df['date'].max().date()} ({len(df)} rows)")


if __name__ == "__main__":
    main()
