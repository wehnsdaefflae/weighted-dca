# Weighted DCA Strategy

## Overview

A percentage-based dollar-cost averaging strategy that invests a variable fraction of your available cash each month. When markets dip, invest a larger percentage; when markets rally, invest less. The strategy naturally front-loads investment (investing more when cash is plentiful) while adapting to market conditions.

## Portfolio

| Allocation | ETF | ISIN |
|---|---|---|
| 70% | SPDR MSCI World UCITS ETF | IE00BFY0GT14 |
| 30% | iShares Core MSCI EM IMI UCITS ETF | IE00BKM4GZ66 |

---

## How It Works

### 1. Find the reference high

Look at the highest portfolio price over the **last 19 months** (rolling window). This is your reference price.

### 2. Calculate the drop

```
drop = (reference high − current price) / reference high
```

### 3. Determine the multiplier

**Market dropped more than 2% from the rolling high:**

```
multiplier = 1 + 15 × (drop − 0.02)
```

| Drop | Multiplier | Effective % of cash |
|---|---|---|
| 0% (at high) | 1.00x | 5.17% |
| 5% | 1.45x | 7.50% |
| 10% | 2.20x | 11.37% |
| 15% | 2.95x | 15.25% |
| 20% | 3.70x | 19.12% |
| 25%+ | 4.68x (capped) | 24.19% |

**Market rose more than 17.5% above the rolling high** (rare):

```
multiplier = max(0, 1 − 1.75 × (rise − 0.175))
```

**Otherwise:** multiplier = 1.0

### 4. Apply limits

- **Minimum multiplier:** 0.04x → effective ~0.2% of cash
- **Maximum multiplier:** 4.68x → effective ~24.2% of cash

### 5. Calculate investment

```
investment = available_cash × base_pct × multiplier
investment = available_cash × 0.0517 × multiplier
```

### 6. Cooldown

After investing at or near the maximum, revert to base for **3 months**. This prevents burning through cash during a prolonged crash.

### 7. Buy the ETFs

Split the calculated amount: **70% SPDR World**, **30% iShares EM IMI**.

---

## Quick Reference

| Parameter | Value |
|---|---|
| Reference point | Rolling 19-month high |
| Base percentage | 5.17% of available cash |
| Drop threshold | 2% |
| Drop factor | 15x |
| Rise threshold | 17.5% |
| Rise factor | 1.75x |
| Min multiplier | 0.04x |
| Max multiplier | 4.68x |
| Cooldown | 3 months after max |

---

## Practical Example

**Starting cash: €200,000**

**Month 1:** Portfolio at rolling high. Multiplier = 1.0x. Invest 5.17% × €200,000 = **€10,340** (€7,238 World + €3,102 EM). Remaining: €189,660.

**Month 2:** Market drops 10%. Multiplier = 2.2x. Invest 11.37% × €189,660 = **€21,564** (€15,095 World + €6,469 EM). Remaining: €168,096.

**Month 6:** Market still down 8%. Multiplier = 1.9x. Cash is now €120,000. Invest 9.82% × €120,000 = **€11,789**. The percentage stays the same but the absolute amount naturally decreases as cash depletes.

**Month 12:** Cash is now €60,000. Market recovered to rolling high. Multiplier = 1.0x. Invest 5.17% × €60,000 = **€3,102**.

Notice how the strategy naturally front-loads: larger amounts early (when cash is plentiful), smaller amounts later. A market crash amplifies this effect — exactly when you want to be buying more.

---

## Key Properties

- **Always invest something.** Minimum multiplier is 0.04x — the strategy never says sit out entirely.
- **Exponential decay.** Investing a fixed percentage of remaining cash means each month's investment is slightly smaller than the last (absent market moves), naturally deploying the bulk of cash in the first ~12 months.
- **The rolling window adapts.** Unlike an all-time high reference, a 19-month rolling window resets after prolonged drawdowns, so you aren't stuck comparing to a peak from years ago.
- **Works at any scale.** Whether you have €10,000 or €500,000, the percentage-based approach scales naturally.
- **Rebalance each purchase.** Split 70/30 on every buy. No need to rebalance existing holdings.
- **Parameters are optimized.** All values above come from walk-forward cross-validation on historical MSCI World + EM data, optimized to maximize total wealth vs. regular DCA.
