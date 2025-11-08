# Critical Fix: Degradation Cost Formula Correction

**Date**: 2025-11-08
**Issue**: Degradation cost undervalued by 5× due to incorrect end-of-life threshold
**Impact**: Optimizer incentivized excessive cycling (900 cycles/year) vs. sustainable operation
**Status**: ✅ FIXED

---

## Problem Identified

### Original (Incorrect) Formula

```python
# lp_monthly_optimizer.py line 307 (OLD)
c[9*T:10*T] = self.C_bat * self.E_nom / 100.0
```

**Issue**: Divides by **100%**, assuming battery can degrade from 0% → 100%

**Reality**: Battery is **end-of-life at 20% degradation** (80% SOH), not 100%!

### Economic Impact

**What happens over battery lifetime**:
```
Battery cost: 91,620 NOK (30 kWh @ 3,054 NOK/kWh)
Usable degradation range: 0% → 20% (then battery must be replaced)

OLD formula:
  Cost per 1% degradation: 91,620 / 100 = 916 NOK
  Total cost at EOL (20%): 916 × 20 = 18,324 NOK
  → Only 20% of battery cost recovered!
  → 80% residual value "disappears" at replacement
  → Creates hidden subsidy for high cycling

NEW formula:
  Cost per 1% degradation: 91,620 / 20 = 4,581 NOK
  Total cost at EOL (20%): 4,581 × 20 = 91,620 NOK
  → 100% of battery cost properly amortized ✓
```

**Multiplier**: New degradation cost is **5.0× higher**

---

## Impact on Optimization Results

### At 900 cycles/year (Current Model Prediction)

| Metric | OLD (Wrong) | NEW (Correct) | Change |
|--------|-------------|---------------|---------|
| Annual degradation | 3.6% | 3.6% | - |
| Degradation cost | 3,298 NOK/year | **16,492 NOK/year** | **+13,193** |
| Gross savings | 17,583 NOK/year | 17,583 NOK/year | - |
| **Net savings** | **14,285 NOK/year** | **1,091 NOK/year** | **-13,193** |
| Profitability | ✓ Highly profitable | ⚠️ Barely profitable | Critical |

### Expected Optimizer Behavior Change

**OLD (wrong) formula**:
- Degradation cost artificially low
- Aggressive cycling (900/year) appeared economically optimal
- Net savings: 14,285 NOK/year
- Result: **Short battery lifetime (~5.5 years), frequent replacements**

**NEW (correct) formula**:
- Degradation cost properly valued
- At 900 cycles/year: Only 1,091 NOK/year net savings (barely worth it)
- **Optimizer will self-regulate to lower cycle rates**
- Expected new behavior: **300-500 cycles/year** (sustainable)
- Result: **Longer battery lifetime (~10-12 years), better economics**

**This is EXACTLY what the degradation function should do**: Tell us the economically optimal balance between revenue and battery wear!

---

## Changes Made

### 1. config.py

Added explicit EOL degradation threshold:

```python
@dataclass
class DegradationConfig:
    # ... existing fields ...

    # End-of-life degradation threshold (80% SOH = 20% capacity loss)
    eol_degradation_percent: float = 20.0    # Battery unusable after 20% degradation
```

Updated `__post_init__` to use this constant:

```python
def __post_init__(self):
    # Uses eol_degradation_percent instead of hardcoded 20.0
    self.rho_constant = self.eol_degradation_percent / self.cycle_life_full_dod
    self.dp_cal_per_hour = self.eol_degradation_percent / hours_per_lifetime
```

### 2. lp_monthly_optimizer.py

**Stored EOL threshold** (line 134):
```python
self.eol_degradation = degradation_config.eol_degradation_percent  # End-of-life threshold (20%)
```

**Fixed cost coefficient** (line 312):
```python
# OLD (WRONG):
# c[9*T:10*T] = self.C_bat * self.E_nom / 100.0

# NEW (CORRECT):
c[9*T:10*T] = self.C_bat * self.E_nom / self.eol_degradation
```

**Fixed cost calculation in results** (line 384):
```python
# OLD (WRONG):
# degradation_cost = np.sum(DP * self.C_bat * self.E_nom / 100.0)

# NEW (CORRECT):
degradation_cost = np.sum(DP * self.C_bat * self.E_nom / self.eol_degradation)
```

**Added diagnostic output** (line 142):
```python
print(f"  EOL threshold: {self.eol_degradation:.1f}% degradation (80% SOH)")
```

---

## Validation

Created `test_degradation_fix.py` to verify the correction:

**Test Results**:
```
Cost per 1% degradation:
  OLD: 916 NOK  → Total at EOL: 18,324 NOK (20% recovery)
  NEW: 4,581 NOK → Total at EOL: 91,620 NOK (100% recovery) ✓

Annual degradation cost (at 900 cycles/year):
  OLD: 3,298 NOK/year
  NEW: 16,492 NOK/year (5.0× higher) ✓

Net savings:
  OLD: 14,285 NOK/year (seemed highly profitable)
  NEW: 1,091 NOK/year (barely profitable - optimizer will reduce cycling) ✓
```

---

## Expected Changes in Next Optimization Run

With corrected degradation costs, the optimizer will **self-optimize** to sustainable operation:

1. **Lower cycle rate**: Expected 300-500 cycles/year (down from 900)
2. **Longer battery lifetime**: ~10-12 years (up from ~5.5 years)
3. **Lower annual degradation cost**: ~8,000-10,000 NOK/year (down from 16,492)
4. **Still profitable**: Net savings ~7,000-10,000 NOK/year
5. **More realistic economics**: Proper trade-off between revenue and battery wear

**This validates the third-party QA review findings**: The degradation function should guide the optimizer to economically rational cycling behavior, not just maximize short-term revenue.

---

## Next Steps

1. ✅ Fix applied to config.py and lp_monthly_optimizer.py
2. ⏳ Re-run annual LP optimization with corrected degradation costs
3. ⏳ Observe new optimal cycle rate (expected: 300-500/year)
4. ⏳ Calculate endogenous battery lifetime from cumulative degradation
5. ⏳ Update break-even analysis with corrected economics
6. ⏳ Document new results and compare to current findings

---

## References

**Related to QA Review**: This fix addresses the critical issue identified by both ChatGPT and Gemini reviewers:

> "The model should tell us the economically optimal cycle rate. High cycling might be profitable in the short term, but degradation costs must properly account for full battery replacement at 80% SOH."

See: `docs/DEGRADATION_MODEL_QA_REVIEW.md`

**Session Context**: Previous results showed 900 cycles/year with 14,242 NOK/year net savings. These were based on incorrect degradation costs and will change significantly.

See: `SESSION_2025_11_03_COMPLETE.md`

---

**Conclusion**: This fix ensures degradation costs correctly reflect the economic reality of battery replacement at 80% SOH. The optimizer can now make properly informed decisions about cycling intensity vs. battery lifetime, leading to sustainable and economically optimal operation.
