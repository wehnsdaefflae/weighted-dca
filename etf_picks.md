# Critical Evaluation: 70/30 DCA Portfolio

## Your Picks

| Allocation | ETF | ISIN | TER | Replication | Domicile | Index |
|---|---|---|---|---|---|---|
| 70% | UBS Core MSCI World UCITS USD Acc | IE00BD4TXV59 | 0.06% | Physical (full) | Ireland | MSCI World |
| 30% | Amundi Core MSCI EM Swap UCITS Acc | LU2573967036 | 0.14% | Synthetic (swap) | Luxembourg | MSCI EM |

**Blended TER: 0.084%** — very low.

---

## Verdict on Each ETF

### UBS Core MSCI World — Strong pick, with one caveat

At 0.06% TER, this is the cheapest MSCI World UCITS ETF available. It's Ireland-domiciled (US dividend withholding tax reduced from 30% to 15%), accumulating, and uses full physical replication. Fund size is ~5.3bn EUR — large enough to be safe from closure.

**The caveat: TER is not total cost.** Tracking difference (TD) matters more. UBS has a TD of +0.03% — meaning your actual annual cost is ~0.03%, which is good. But competitors with higher TERs achieve *negative* tracking differences (they outperform the index after fees, typically via securities lending revenue):

| ETF | TER | Avg TD | Effective cost | AUM |
|---|---|---|---|---|
| **UBS Core MSCI World** | 0.06% | +0.03% | ~0.03% | 5.3bn |
| SPDR MSCI World | 0.12% | -0.13% | **-0.13%** | 13.8bn |
| Vanguard FTSE Dev. World | 0.12% | -0.15% | **-0.15%** | 4.8bn |
| Xtrackers MSCI World 1C | 0.12% | -0.05% | **-0.05%** | 16.2bn |
| iShares Core MSCI World | 0.20% | +0.03% | ~0.03% | 108.7bn |

The SPDR and Vanguard funds effectively *pay you* 0.13-0.15% per year to hold them. On a 100k portfolio that's ~130-150 EUR/year better than a fund with +0.03% TD, despite the higher stated TER. Over 20+ years of compounding, this adds up.

**Better alternative: SPDR MSCI World UCITS ETF (IE00BFY0GT14)** — 0.12% TER but -0.13% TD, Ireland-domiciled, 13.8bn AUM. Best effective cost among proven MSCI World trackers.

Runner-up: **Xtrackers MSCI World 1C (IE00BJ0KDQ92)** — 0.12% TER, -0.05% TD, 16.2bn AUM. Excellent balance of cost, size, and tracking.

UBS is still a *good* pick — the difference is small in absolute terms. But if you're optimizing, TD-based analysis favors SPDR or Xtrackers.

### Amundi Core MSCI EM Swap — Decent, but not the best option

At 0.14% TER with swap-based replication, this fund has theoretical advantages: swaps can avoid dividend withholding taxes in key EM countries (India, Taiwan, South Korea, Brazil — collectively >50% of MSCI EM), which should improve net returns.

**Problems:**

1. **Luxembourg domicile** — less tax-efficient than Irish-domiciled funds for US dividend withholding (less relevant for EM, but still a structural disadvantage for any US-listed holdings in the index).
2. **Limited track record** — launched Dec 2020 with ISIN change in 2022. Not enough years of TD data to verify whether the swap advantage materializes in practice. The older Amundi EM swap fund (LU1681045370, TER 0.20%) has a *terrible* TD of +0.45%.
3. **Counterparty risk** — UCITS limits this to 10% NAV and requires daily collateralisation, but in a crisis, the substitute basket collateral may diverge from EM index behavior.
4. **No small-cap exposure** — tracks MSCI EM standard (large+mid only, ~1,400 stocks).

**Better alternative: iShares Core MSCI EM IMI (IE00BKM4GZ66)** — the gold standard for EM:

| ETF | TER | Avg TD | Replication | AUM | Holdings | Domicile |
|---|---|---|---|---|---|---|
| **Amundi Core EM Swap** | 0.14% | N/A (limited data) | Synthetic | 4.1bn | ~1,400 | Luxembourg |
| **iShares Core MSCI EM IMI** | 0.18% | **+0.05%** | Physical | **32.3bn** | **~3,400** | **Ireland** |
| Xtrackers MSCI EM 1C | 0.18% | +0.14% | Physical | 9.8bn | ~1,400 | Ireland |
| HSBC MSCI EM | 0.15% | N/A (new) | Physical | 4.7bn | ~1,400 | Ireland |

iShares EM IMI achieves a TD of just +0.05% on a 0.18% TER — meaning its effective cost is only 0.05%. It includes small caps (IMI = Investable Market Index, ~3,400 stocks vs ~1,400), is Ireland-domiciled, and has 32bn EUR AUM making it by far the most liquid EM ETF. The 0.04% higher TER vs Amundi is more than offset by proven tracking quality, broader diversification, and structural advantages.

---

## Challenge: The 70/30 Split Itself

This deserves scrutiny. Market-cap weighting for developed vs emerging is currently **~88/12**, not 70/30. Your 30% EM allocation is a **2.5x overweight** on emerging markets.

**Why this has been costly:**
- MSCI EM returned ~3.8% p.a. over the last decade vs ~10.4% for MSCI World.
- A 70/30 portfolio has underperformed both pure MSCI World and the market-cap weighted MSCI ACWI over 10 and 15 year periods.
- The thesis (EM GDP ~41% of global vs ~12% market cap = undervalued) has not played out due to structural factors: state-owned enterprises, capital controls, weaker shareholder protections, currency depreciation.

**Arguments for keeping some EM overweight:**
- Mean reversion: EM valuations are historically cheap (P/E ~11 vs ~22 for developed).
- Reduces US concentration (~70% of MSCI World is US stocks).
- If you have a 20+ year horizon, EM underperformance may reverse.

**Consider:** If you want EM overweight but 30% feels aggressive, **80/20** is a more moderate tilt that still expresses your conviction without as much drag risk.

**Simplest alternative:** A single all-world ETF eliminates rebalancing entirely:
- **Vanguard FTSE All-World UCITS ETF Acc (VWCE)** — IE00BK5BQT80, TER 0.19%, ~31bn AUM, ~3,700 holdings, Ireland-domiciled. EM weight floats at market cap (~12%). "VWCE and chill" is the current community consensus.
- **SPDR MSCI ACWI IMI UCITS ETF (SPYI)** — IE00B3YLTY66, TER 0.17%, ~4.4bn AUM, includes small caps (~8,200 holdings).

---

## Final Recommendation

| Allocation | ETF | ISIN | TER | Effective Cost (TD) | Why |
|---|---|---|---|---|---|
| **70%** | **SPDR MSCI World UCITS ETF** | IE00BFY0GT14 | 0.12% | **-0.13%** | Lowest effective cost among proven MSCI World trackers; Ireland-domiciled; 13.8bn AUM |
| **30%** | **iShares Core MSCI EM IMI** | IE00BKM4GZ66 | 0.18% | **+0.05%** | Gold standard for EM; includes small caps (3,400 holdings); 32bn AUM; Ireland-domiciled; proven TD |

Keep the 70/30 split. The professional consensus has shifted toward EM outperformance over the next decade (JPMorgan 7.8% vs 6.7% US, BlackRock actively overweighting EM, valuations at a ~38% forward P/E discount). The 30% EM tilt is an aggressive but well-supported active bet given current conditions. Including full China weight is fine — the deflation discount is already priced in, and missing a recovery on CAPE 17.7 valuations would be costly.

---

---

## Addendum: Is EM Underrepresented, and Does the 2026 Outlook Change Things?

### The GDP vs Market Cap gap

EM is ~40% of global GDP but only ~11-12% of MSCI ACWI / VWCE. That gap is real, but roughly half of it is explained by structural factors rather than "undervaluation":

- **Free float adjustment** — governments and founding families hold large blocks of EM shares that aren't tradable; indices only count free float
- **State-owned enterprises** — ~26% of EM market cap is SOEs with suppressed valuations due to governance concerns and non-commercial objectives
- **Capital controls** — China A-shares are only partially included; India has FPI limits; several countries restrict foreign ownership
- **Market maturity** — many EM firms remain private/unlisted; capital markets are less developed relative to economic size

The remaining gap *is* partly opportunity. EM's share of global market cap is projected to rise from ~27% (2023) to ~35% by 2030. Institutional investors are currently 600-700 bps underweight EM relative to benchmarks — potential reallocation tailwind.

**Bottom line:** VWCE's ~12% EM weight reflects investable market cap, not economic reality. Whether that's "wrong" depends on whether you think the structural discount will narrow.

### What the major firms project (10-year horizon)

| Firm | EM Expected Return | US Expected Return | Spread |
|---|---|---|---|
| JPMorgan | **7.8%** | 6.7% | +1.1% |
| Research Affiliates | **~7.5%** | lower | significant |
| Fidelity | **8.1%** (20yr nominal) | — | — |
| Goldman Sachs | **~16%** (2026 alone) | ~10% | — |
| BlackRock | Overweight EM | Neutral US | — |
| Vanguard | Ex-US: 4.9-6.9% | US: 4.0-5.0% | +0.9-1.9% |
| GMO | ~1% real (broad EM) | — | muted |

Near-consensus: **EM is expected to outperform US equities over 10 years**, driven by valuations (EM forward P/E ~13.4 vs US ~21.7, a ~40% discount) and superior earnings growth. BlackRock and Cambridge Associates have actively increased EM overweights in model portfolios.

### Current valuations support a tilt

| Metric | MSCI EM | S&P 500 | Discount |
|---|---|---|---|
| Forward P/E | 13.4 | 21.7 | **38%** |
| Price-to-Book | — | — | **61% cheaper** |
| CAPE (China) | 17.7 | 34.7 (US) | **49%** |

The US CAPE of ~35 is in the top historical decile. EM valuations have recovered from 2022 lows but remain cheap relative to developed markets by historical standards.

### Key risks that temper the bull case

1. **China (~25-30% of MSCI EM) is in a deflation trap** — 5th year of property crisis, ~80M unsold homes, three consecutive years of producer price deflation. Eurasia Group ranks it a top 2026 risk.
2. **EM has been the "obvious value play" for a decade and chronically disappointed.** Research Affiliates' own model showed EM "should have led the pack" but ended up ranked 6th in actual 10-year performance.
3. **Governance and dilution** — aggressive share issuance, SOE interference, and weak shareholder protections erode theoretical value.
4. **US structural advantages** (AI dominance — 79% of global AI investment, rule of law, deep capital markets) may justify premium valuations longer than mean-reversion models predict.
5. **Trade policy remains volatile** — SCOTUS struck down IEEPA tariffs in Feb 2026 but Trump reimposed ~10-15% global tariffs under different authority within days.

### Revised weighting view

The 70/30 split is more defensible than it was 2 years ago. The professional consensus has shifted toward EM, valuations are compelling, and US concentration risk in market-cap indices is a legitimate concern (~70% US in MSCI World). With a long horizon, 30% EM is a reasonable active bet supported by near-consensus forecasts from major firms.

*Data sourced from justETF, trackingdifferences.com, Morningstar, ETF Stream, fund provider factsheets, JPMorgan LTCMA, Research Affiliates, Goldman Sachs Research, BlackRock, Vanguard, GMO, Fidelity, Cambridge Associates, Dodge & Cox, Eastspring, AQR, and Eurasia Group. Figures as of early 2026. This is not financial advice.*
