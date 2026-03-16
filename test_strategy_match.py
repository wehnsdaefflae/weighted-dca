#!/usr/bin/env python3
"""Verify the website's recommendations match the Python strategy.

Runs headed so you can watch the browser.
"""

import json
import sys
import numpy as np
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))
from strategy import Params, portfolio_monthly

BASE = "http://localhost:8080"
DATA_DIR = Path(__file__).parent / "data"
SITE_DIR = Path(__file__).parent / "site"


def load_data():
    """Load the same data the website uses."""
    portfolio = portfolio_monthly(
        str(DATA_DIR / "msci_world.csv"),
        str(DATA_DIR / "msci_em.csv"),
    )
    prices = [float(p) for p in portfolio.values]

    with open(SITE_DIR / "data" / "config.json") as f:
        config = json.load(f)

    with open(Path(__file__).parent / "report" / "results.json") as f:
        results = json.load(f)

    params = Params(**{k: v for k, v in results["params"].items()})
    return prices, config, params


def python_recommend(prices, params, swrd, eimi, config, cash):
    """Compute recommendation using the same logic as Python strategy."""
    # Bridge: convert SWRD/EIMI to portfolio index
    iwda_eff = swrd / config["swrdRatio"]
    w_norm = iwda_eff / config["firstIWDA"] * 100
    e_norm = eimi / config["firstEIMI"] * 100
    portfolio_price = 0.7 * w_norm + 0.3 * e_norm

    all_prices = prices + [portfolio_price]

    # Rolling window reference high
    window = params.window_months
    window_start = max(0, len(all_prices) - window)
    ref = max(all_prices[window_start:])

    current = all_prices[-1]
    drop_pct = (ref - current) / ref

    # Multiplier
    if drop_pct > params.drop_threshold:
        mult = 1.0 + params.drop_factor * (drop_pct - params.drop_threshold)
    elif drop_pct < -params.rise_threshold:
        mult = max(0.0, 1.0 - params.rise_factor * (-drop_pct - params.rise_threshold))
    else:
        mult = 1.0

    # Clamp multiplier
    mult = float(np.clip(mult, params.min_mult, params.max_mult))

    # Investment = cash * base_pct * multiplier
    inv = cash * params.base_pct * mult
    inv = min(inv, max(0.0, cash))

    effective_pct = params.base_pct * mult

    return {
        "portfolio_price": portfolio_price,
        "ref_high": ref,
        "current": current,
        "drop_pct": drop_pct,
        "multiplier": mult,
        "investment": round(inv * 100) / 100,
        "world_amount": round(inv * 0.7 * 100) / 100,
        "em_amount": round(inv * 0.3 * 100) / 100,
        "effective_pct": effective_pct,
    }


def parse_website_float(text):
    """Parse a float from website text like '1.65x' or '+3.2%' or '€8,333'."""
    s = text.replace("€", "").replace(",", "").replace("x", "").replace("%", "").replace("+", "").strip()
    # Handle German-style thousands separators (e.g., €13.775 = 13775)
    parts = s.split(".")
    if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) >= 1:
        s = s.replace(".", "")
    return float(s)


def get_website_rec(page):
    """Extract recommendation values from the page."""
    return {
        "drop_pct_text": page.locator("#rec-drop").text_content(),
        "multiplier_text": page.locator("#rec-mult").text_content(),
        "ref_high_text": page.locator("#rec-ref").text_content(),
        "current_text": page.locator("#rec-cur").text_content(),
        "amount_text": page.locator("#rec-amount").text_content(),
        "pct_text": page.locator("#rec-pct").text_content(),
        "split_text": page.locator("#rec-split").text_content(),
        "drop_pct": float(page.locator("#rec-drop").text_content().replace("+", "").replace("%", "")) / 100,
        "multiplier": float(page.locator("#rec-mult").text_content().replace("x", "")),
        "ref_high": float(page.locator("#rec-ref").text_content()),
        "current": float(page.locator("#rec-cur").text_content()),
        "investment": parse_website_float(page.locator("#rec-amount").text_content()),
    }


def assert_close(name, expected, actual, tol=0.02):
    """Assert two values are close (relative or absolute tolerance)."""
    if abs(expected) < 0.01:
        ok = abs(actual - expected) < tol
    else:
        ok = abs(actual - expected) / abs(expected) < tol
    status = "OK" if ok else "MISMATCH"
    print(f"    {name}: Python={expected:.4f}, Website={actual:.4f} [{status}]")
    if not ok:
        raise AssertionError(f"{name} mismatch: Python={expected}, Website={actual}")


def test_scenario(page, label, swrd, eimi, prices, params, config, cash):
    """Test one scenario: compute Python expected, compare with website."""
    print(f"\n  Scenario: {label}")

    expected = python_recommend(prices, params, swrd, eimi, config, cash)

    print(f"    Python: drop={expected['drop_pct']:.4f}, mult={expected['multiplier']:.4f}, "
          f"inv={expected['investment']:.2f}, pct={expected['effective_pct']:.4f}")

    # Reset state
    page.request.post(f"{BASE}/api/state.php",
        data=json.dumps({"params": None, "log": []}),
        headers={"Content-Type": "application/json"})

    page.goto(BASE)

    # Wait for auto-fetch + optimization to complete
    page.wait_for_function(
        "!document.getElementById('btn-calc').disabled", timeout=60000
    )

    # Set prices (hidden inputs) and cash, then calculate
    page.evaluate(f"document.getElementById('in-world').value = '{swrd:.2f}'")
    page.evaluate(f"document.getElementById('in-em').value = '{eimi:.2f}'")
    page.evaluate("UI.showRecommendation()")
    page.fill("#in-cash", str(cash))
    page.click("#btn-calc")

    page.wait_for_selector("#rec-amount-section:not(.hidden)", timeout=5000)
    page.wait_for_timeout(300)  # Let rendering settle

    web = get_website_rec(page)
    print(f"    Website: drop={web['drop_pct']:.4f}, mult={web['multiplier']:.4f}, "
          f"inv={web['investment']:.2f}")

    # Compare
    assert_close("drop_pct", expected["drop_pct"], web["drop_pct"])
    assert_close("multiplier", expected["multiplier"], web["multiplier"])
    assert_close("ref_high", expected["ref_high"], web["ref_high"], tol=0.005)
    assert_close("current", expected["current"], web["current"], tol=0.005)
    assert_close("investment", expected["investment"], web["investment"], tol=0.01)
    print(f"    PASS")


def main():
    prices, config, params = load_data()

    print(f"Data: {len(prices)} months")
    print(f"Params: window={params.window_months}, drop_th={params.drop_threshold}, "
          f"drop_f={params.drop_factor}, rise_th={params.rise_threshold}, "
          f"rise_f={params.rise_factor}")
    print(f"  min_mult={params.min_mult}x, max_mult={params.max_mult}x, "
          f"base_pct={params.base_pct}, cooldown={params.cooldown_months}mo")

    # Get the latest portfolio price for reference
    latest = prices[-1]
    rolling_high = max(prices[-params.window_months:])
    print(f"Latest portfolio: {latest:.2f}, rolling {params.window_months}mo high: {rolling_high:.2f}")

    ratio = config["swrdRatio"]
    first_iwda = config["firstIWDA"]
    first_eimi = config["firstEIMI"]

    # Current real prices (approximate from Yahoo)
    real_swrd = 46.78
    real_eimi = 46.60

    # For testing drops/rises, scale both prices proportionally
    def make_prices(scale):
        return round(real_swrd * scale, 2), round(real_eimi * scale, 2)

    def portfolio_for(swrd, eimi):
        iwda_eff = swrd / ratio
        return 0.7 * (iwda_eff / first_iwda * 100) + 0.3 * (eimi / first_eimi * 100)

    current_port = portfolio_for(real_swrd, real_eimi)
    print(f"Current portfolio index for SWRD={real_swrd}, EIMI={real_eimi}: {current_port:.2f}")
    current_drop = (rolling_high - current_port) / rolling_high
    print(f"Current drop from rolling high: {current_drop:.4f} ({current_drop*100:.2f}%)")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        passed = failed = 0

        scenarios = [
            # (label, swrd, eimi, cash)
            ("Current prices, full cash",
             real_swrd, real_eimi, 200000),

            ("Current prices, partial cash",
             real_swrd, real_eimi, 120000),

            ("10% crash scenario",
             *make_prices(0.90), 200000),

            ("20% crash scenario",
             *make_prices(0.80), 200000),

            ("25% crash (near max multiplier)",
             *make_prices(0.75), 200000),

            ("Small cash",
             real_swrd, real_eimi, 15000),

            ("Large cash, 10% crash",
             *make_prices(0.90), 500000),

            ("Prices at rolling high",
             *make_prices(rolling_high / current_port), 200000),

            ("Small crash, small cash",
             *make_prices(0.95), 50000),
        ]

        for label, swrd, eimi, cash in scenarios:
            try:
                test_scenario(page, label, swrd, eimi,
                              prices, params, config, cash)
                passed += 1
            except Exception as e:
                print(f"    FAIL: {e}")
                failed += 1

        print(f"\n{'='*60}")
        print(f"Strategy verification: {passed} passed, {failed} failed out of {passed+failed}")

        if failed == 0:
            print("All website recommendations match the Python strategy!")

        try:
            input("\nPress Enter to close the browser...")
        except EOFError:
            pass
        browser.close()

    return 1 if failed else 0


if __name__ == "__main__":
    exit(main())
