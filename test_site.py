#!/usr/bin/env python3
"""End-to-end tests for the Weighted DCA site using Playwright."""

import json
from playwright.sync_api import sync_playwright, expect

BASE = "http://localhost:8080"


def test_page_loads(page):
    """Page loads, embedded data parsed, charts rendered."""
    page.goto(BASE)
    expect(page.locator("h1")).to_have_text("Weighted DCA Monthly Advisor")
    # Charts should render (Plotly creates .plot-container inside .chart divs)
    expect(page.locator("#chart-portfolio .plot-container")).to_be_attached(timeout=5000)
    expect(page.locator("#chart-drop .plot-container")).to_be_attached(timeout=5000)
    print("  PASS: page loads correctly")


def parse_eur(text):
    """Parse €1,234 or €1.234 or €1234 to float."""
    s = text.replace("€", "").replace(",", "").replace(".", "").strip()
    return float(s) if s else 0


def wait_ready(page):
    """Wait for auto-fetch + optimization to complete and recommendation to show."""
    page.wait_for_function(
        "!document.getElementById('btn-calc').disabled && "
        "!document.getElementById('rec-card').classList.contains('hidden')",
        timeout=60000
    )


def test_auto_recommendation(page):
    """Page load shows percentage recommendation automatically."""
    page.goto(BASE)
    wait_ready(page)

    # Recommendation card should be visible without any user input
    expect(page.locator("#rec-card")).to_be_visible(timeout=5000)

    # Should show percentage
    pct_text = page.locator("#rec-pct").text_content()
    assert "%" in pct_text, f"Expected percentage, got: {pct_text}"

    # Multiplier should be shown
    mult = page.locator("#rec-mult").text_content()
    assert "x" in mult, f"Bad multiplier: {mult}"

    # Amount section should NOT be visible yet (no cash entered)
    expect(page.locator("#rec-amount-section")).not_to_be_visible()

    print(f"  PASS: auto-recommendation shown ({pct_text}, mult={mult})")


def test_calculate_amount(page):
    """Entering cash and clicking Calculate shows euro amount."""
    page.goto(BASE)
    wait_ready(page)

    page.fill("#in-cash", "200000")
    page.click("#btn-calc")

    expect(page.locator("#rec-amount-section")).to_be_visible(timeout=3000)
    amount_text = page.locator("#rec-amount").text_content()
    assert amount_text.startswith("€"), f"Expected €amount, got: {amount_text}"
    amount = parse_eur(amount_text)
    assert 0 < amount <= 200000, f"Amount out of range: {amount}"

    # Split should show World + EM
    split = page.locator("#rec-split").text_content()
    assert "World" in split and "EM" in split, f"Bad split: {split}"

    print(f"  PASS: amount calculated = {amount_text}")


def test_multiplier_range(page):
    """Multiplier should be clamped to [min_mult, max_mult]."""
    page.goto(BASE)
    wait_ready(page)
    expect(page.locator("#rec-card")).to_be_visible()
    mult = float(page.locator("#rec-mult").text_content().replace("x", ""))
    # min_mult ~0.04, max_mult ~4.68 from optimization
    assert 0 <= mult <= 5.0, f"Multiplier out of range: {mult}"
    print(f"  PASS: multiplier in range (mult={mult:.2f}x)")


def test_record_investment(page):
    """Record an investment and verify it appears in the log."""
    page.goto(BASE)
    wait_ready(page)
    page.fill("#in-cash", "200000")
    page.click("#btn-calc")
    expect(page.locator("#rec-amount-section")).to_be_visible(timeout=3000)

    # Get recommended amount
    amount = parse_eur(page.locator("#rec-amount").text_content())

    page.click("#btn-record")
    # Log should have one row
    rows = page.locator("#log-body tr")
    expect(rows).to_have_count(1, timeout=3000)
    # Cash input should auto-update (subtract invested amount)
    new_cash = float(page.locator("#in-cash").input_value())
    assert new_cash < 200000, f"Cash not updated: {new_cash}"
    assert abs(new_cash - (200000 - amount)) < 1, f"Cash mismatch: {new_cash} vs expected {200000 - amount}"
    print(f"  PASS: recorded investment, cash=€{new_cash:.0f}")


def test_api_data(page):
    """API endpoints return valid data."""
    page.goto(BASE)
    # Check data endpoint
    resp = page.request.get(f"{BASE}/api/data.php")
    assert resp.ok, f"data.php failed: {resp.status}"
    data = resp.json()
    assert len(data) > 100, f"Expected 100+ months, got {len(data)}"
    assert "d" in data[0] and "p" in data[0], "Bad data format"

    # Check state endpoint
    resp = page.request.get(f"{BASE}/api/state.php")
    assert resp.ok, f"state.php failed: {resp.status}"

    # Check prices endpoint
    resp = page.request.get(f"{BASE}/api/prices.php")
    assert resp.ok, f"prices.php failed: {resp.status}"
    prices = resp.json()
    assert "SWRD.L" in prices and "EIMI.L" in prices, f"Bad prices: {prices}"
    print(f"  PASS: APIs working ({len(data)} months, SWRD={prices['SWRD.L']}, EIMI={prices['EIMI.L']})")


def test_auto_optimization_on_load(page):
    """Page load auto-fetches prices, optimizes, and shows recommendation."""
    page.goto(BASE)
    # Optimization runs automatically - wait for results
    expect(page.locator("#health-results")).to_be_visible(timeout=60000)
    # Top status bar should show completion
    top_status = page.locator("#top-status-text").text_content()
    assert "ready" in top_status.lower() or "confirmed" in top_status.lower() \
        or "updated" in top_status.lower(), f"Top status not done: {top_status}"
    # Health section should show badge
    badge_text = page.locator("#health-status").text_content()
    assert "confirmed" in badge_text.lower() or "updated" in badge_text.lower(), \
        f"Unexpected badge: {badge_text}"
    # Should show folds info
    folds = page.locator("#health-folds").text_content()
    assert "folds" in folds, f"No folds info: {folds}"
    # Parameter bars should be rendered
    bars = page.locator(".health-bar")
    assert bars.count() >= 5, f"Expected 5+ param bars, got {bars.count()}"
    # Recommendation should already be visible
    expect(page.locator("#rec-card")).to_be_visible()
    print(f"  PASS: auto-optimization on load: {badge_text}, {folds}")


def test_state_persistence(page):
    """State persists across page reloads via backend."""
    page.goto(BASE)
    wait_ready(page)
    # Record an investment
    page.fill("#in-cash", "180000")
    page.click("#btn-calc")
    expect(page.locator("#rec-amount-section")).to_be_visible(timeout=3000)
    page.click("#btn-record")
    expect(page.locator("#log-body tr")).to_have_count(1, timeout=3000)

    # Reload and check
    page.reload()
    page.wait_for_load_state("networkidle")
    rows = page.locator("#log-body tr")
    expect(rows).to_have_count(1, timeout=5000)
    print("  PASS: state persists across reload")

    # Clean up
    page.click("#btn-reset")
    page.on("dialog", lambda d: d.accept())
    page.click("#btn-reset")


def test_export_import(page):
    """Export and import JSON round-trip."""
    page.goto(BASE)
    wait_ready(page)
    # Record something first
    page.fill("#in-cash", "200000")
    page.click("#btn-calc")
    expect(page.locator("#rec-amount-section")).to_be_visible(timeout=3000)
    page.click("#btn-record")
    expect(page.locator("#log-body tr")).to_have_count(1, timeout=3000)

    # Export
    with page.expect_download() as dl_info:
        page.click("#btn-export")
    download = dl_info.value
    path = download.path()
    with open(path) as f:
        exported = json.load(f)
    assert "params" in exported and "log" in exported, "Bad export format"
    assert len(exported["log"]) == 1, "Expected 1 log entry"
    print(f"  PASS: export works ({len(exported['log'])} entries)")


def test_params_table(page):
    """Parameters table renders correctly."""
    page.goto(BASE)
    table = page.locator("#params-table")
    rows = table.locator("tr")
    assert rows.count() >= 7, f"Expected 7+ param rows, got {rows.count()}"
    text = table.text_content()
    assert "rolling" in text.lower() or "ath" in text.lower(), f"No ref type in params"
    assert "base" in text.lower() or "%" in text, "No base_pct in params"
    print(f"  PASS: params table ({rows.count()} rows)")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()

        tests = [
            test_page_loads,
            test_auto_recommendation,
            test_calculate_amount,
            test_multiplier_range,
            test_params_table,
            test_api_data,
            test_record_investment,
            test_state_persistence,
            test_export_import,
            test_auto_optimization_on_load,
        ]

        passed = failed = 0
        for test in tests:
            name = test.__name__
            print(f"\n{name}:")
            page = context.new_page()
            # Collect console errors
            errors = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            try:
                # Reset state before each test
                page.request.post(f"{BASE}/api/state.php",
                    data=json.dumps({"params": None, "log": []}),
                    headers={"Content-Type": "application/json"})
                test(page)
                if errors:
                    print(f"  WARN: console errors: {errors[:3]}")
                passed += 1
            except Exception as e:
                print(f"  FAIL: {e}")
                # Take screenshot on failure
                page.screenshot(path=f"test_fail_{name}.png")
                failed += 1
            finally:
                page.close()

        browser.close()
        print(f"\n{'='*50}")
        print(f"Results: {passed} passed, {failed} failed out of {passed+failed}")
        return 1 if failed else 0


if __name__ == "__main__":
    exit(main())
