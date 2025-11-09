# Quick Answer: Can Step Function Tariff Be Formulated as LP?

## Your Question
> Can we reformulate the Lnett power tariff step function to match exact behavior while keeping it a LINEAR program?

## Direct Answer
**NO.** Mathematically impossible.

## Why?
```
Step function:  f(x) = c_i if a_i ≤ x < a_{i+1}  ← DISCONTINUOUS (jumps)
LP requirement: f(x) = Σ a_i × x_i              ← CONTINUOUS (smooth)
```

**Discontinuities violate linearity.**

## What Your Progressive LP Does
Creates a **RAMP** (continuous increase) instead of **STEPS** (flat plateaus with jumps).

**Example:** 45 kW peak demand
- **Actual step function**: 1,772 NOK (flat fee for bracket 6: 25-50 kW)
- **Progressive LP**: 1,612 NOK (accumulated incremental costs)
- **Error**: -160 NOK (-9.0% underestimate)

**Worst case:** 25 kW → -800 NOK (-45% error at bracket boundary)

## Solutions

### Option 1: MILP (Exact)
```python
# Binary variables δ[i] ∈ {0,1} for each bracket
# Exactly one bracket active: Σ δ[i] = 1
# Cost = Σ c_flat[i] × δ[i]

from scipy.optimize import milp
# Use scipy.optimize.milp() with binary indicators
```

**Pros:** Exact solution
**Cons:** 10-100x slower, requires MILP solver

### Option 2: LP + Post-Processing (RECOMMENDED)
```python
# Step 1: Solve LP with progressive approximation (fast)
lp_result = optimize_battery()

# Step 2: Calculate EXACT cost in post-processing
def exact_tariff(p_max):
    for low, high, cost in TARIFF_BRACKETS:
        if low <= p_max < high:
            return cost

monthly_peaks = extract_peaks(lp_result)
actual_cost = sum(exact_tariff(p) for p in monthly_peaks)

# Step 3: Use actual_cost in NPV/IRR analysis
```

**Pros:** Fast, simple, exact final costs
**Cons:** LP uses approximate cost signal (but conservative)

## Recommendation
**Use Option 2** (LP + post-processing) for your battery optimization:
- Keep your current LP optimizer
- Add exact tariff calculation to final economic analysis
- Gets you speed + accuracy where it matters

## Key Insight
Progressive LP always **underestimates** tariff → conservative investment analysis (better to underestimate returns than overestimate).

## Files Created
1. `TARIFF_FORMULATION_SUMMARY.md` - Complete analysis
2. `TARIFF_MILP_IMPLEMENTATION_GUIDE.md` - Implementation details
3. `milp_tariff_demonstration.py` - Working Python demo
4. `results/tariff_comparison_step_vs_progressive.png` - Visualization
