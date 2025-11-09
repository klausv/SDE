# Power Tariff Step Function: LP Formulation Analysis

## Direct Answer to Your Question

> **Can we reformulate the step function tariff to match exact behavior while keeping it a LINEAR program?**

**NO.** This is mathematically impossible.

---

## Why LP Cannot Represent Step Functions

### Mathematical Incompatibility

**Step Function:**
```
f(P) = c_i  if  a_i ≤ P < a_i+1

Example: Lnett bracket 6 (25-50 kW) → 1772 NOK (flat fee)
  P = 24.9 kW → 972 NOK
  P = 25.0 kW → 1772 NOK  (+800 NOK jump!)
  P = 45.0 kW → 1772 NOK  (still flat)
```

**LP Requirement:**
```
Objective = Σ c_i × x_i  (must be CONTINUOUS linear combination)

• No discontinuous jumps allowed
• Linear functions are smooth, continuous everywhere
```

**Fundamental conflict:** Step functions have discontinuities, LP requires continuity.

---

## What Your Progressive LP Actually Does

### Current Formulation
```python
Variables: z[i] ∈ [0, 1]  # Fraction of bracket i filled
Widths:    p_trinn = [2, 3, 5, 5, 5, 5, 25, 25, 25, 100] kW
Costs:     c_trinn = [136, 96, 140, 200, 200, 200, 800, 800, 800, 2228] NOK

Constraints:
  P_max = Σ p_trinn[i] × z[i]
  z[i] ≤ z[i-1]  (ordered filling)

Objective:
  minimize Σ c_trinn[i] × z[i]
```

### What It Creates: A RAMP, Not Steps

**Example: P_max = 45 kW**
```
z[0] = 1.0 → fill bracket 0 (0-2 kW) fully     → +136 NOK
z[1] = 1.0 → fill bracket 1 (2-5 kW) fully     → +96 NOK
z[2] = 1.0 → fill bracket 2 (5-10 kW) fully    → +140 NOK
z[3] = 1.0 → fill bracket 3 (10-15 kW) fully   → +200 NOK
z[4] = 1.0 → fill bracket 4 (15-20 kW) fully   → +200 NOK
z[5] = 1.0 → fill bracket 5 (20-25 kW) fully   → +200 NOK
z[6] = 0.8 → fill bracket 6 (25-50 kW) at 80%  → +640 NOK (0.8 × 800)
                                          Total = 1612 NOK

Actual step function: 1772 NOK (flat fee for bracket 6)
Error: -160 NOK (-9.0%)
```

**Behavior:** Progressive LP creates a **continuous ramp** that accumulates costs incrementally. This is fundamentally different from the **discrete jumps** of the step function.

---

## Error Analysis: Progressive LP vs Step Function

| Peak (kW) | Step (NOK) | Progressive (NOK) | Error (NOK) | Error (%) |
|-----------|------------|-------------------|-------------|-----------|
| 1.5       | 136        | 102               | -34         | -25.0%    |
| 10        | 572        | 372               | -200        | -35.0%    |
| **25**    | **1772**   | **972**           | **-800**    | **-45.1%** |
| 45        | 1772       | 1612              | -160        | -9.0%     |
| **50**    | **2572**   | **1772**          | **-800**    | **-31.1%** |
| 75        | 3372       | 2572              | -800        | -23.7%    |
| 100       | 5600       | 3372              | -2228       | -39.8%    |

**Key Finding:** Progressive LP **always underestimates** actual tariff, worst at bracket boundaries.

---

## Solution Options

### Option 1: MILP (Exact, Recommended for Accuracy)

**Formulation:**
```python
Variables:
  P_max : continuous (monthly peak demand, kW)
  δ[i] ∈ {0, 1} : binary indicator (bracket i active?)

Parameters:
  p_low[i], p_high[i] : bracket boundaries
  c_flat[i] : flat monthly costs

Constraints:
  1. Σ δ[i] = 1  (exactly one bracket)
  2. P_max ≥ p_low[i] - M(1-δ[i])  (lower bound if δ[i]=1)
  3. P_max ≤ p_high[i] + M(1-δ[i])  (upper bound if δ[i]=1)

Objective:
  minimize Σ c_flat[i] × δ[i]

Solver:
  scipy.optimize.milp()  (scipy ≥ 1.9)
```

**Pros:**
- ✅ EXACT solution (matches step function perfectly)
- ✅ Correct cost signal for optimization

**Cons:**
- ❌ Slower than LP (10-100x)
- ❌ More complex implementation
- ❌ Binary variables → MILP solver required

---

### Option 2: LP + Post-Processing (Recommended for Speed)

**Approach:**
```python
# Phase 1: Solve LP with progressive approximation (fast)
lp_result = optimize_battery_lp()

# Phase 2: Extract monthly peak demands
monthly_peaks = extract_monthly_peaks(lp_result)

# Phase 3: Calculate EXACT tariff costs using step function
def step_function_cost(p_max):
    for low, high, cost in TARIFF_BRACKETS:
        if low <= p_max < high:
            return cost
    return TARIFF_BRACKETS[-1][2]

actual_costs = [step_function_cost(p) for p in monthly_peaks]

# Phase 4: Use in final economic analysis (NPV, IRR, break-even)
total_tariff = sum(actual_costs)  # Exact cost!
```

**Pros:**
- ✅ Fast LP optimization
- ✅ Simple implementation
- ✅ Exact final cost calculations

**Cons:**
- ⚠️ LP uses wrong cost signal (may miss optimal battery strategy)
- ⚠️ Conservative bias (underestimates savings during optimization)

---

### Option 3: Piecewise Linear Approximation (Not Recommended)

**Idea:** Add small transition zones at bracket boundaries.
```
Example: P ∈ [24.95, 25.05] → linear ramp from 972 to 1772 NOK
```

**Pros:**
- ✅ Pure LP (no MILP needed)
- ✅ Smooth optimization

**Cons:**
- ❌ Arbitrary transition width
- ❌ Violates actual tariff structure
- ❌ Not exact anywhere near boundaries

---

## Impact on Battery Optimization

### Conservative Bias in Progressive LP

**Example: Peak Reduction 50 kW → 45 kW**
```
Actual savings (step function):
  50 kW: 2572 NOK
  45 kW: 1772 NOK
  Savings: 800 NOK/month

LP estimate (progressive):
  50 kW: 1772 NOK
  45 kW: 1612 NOK
  Savings: 160 NOK/month  (80% UNDERESTIMATE!)
```

**Consequence:**
- Battery economics appear WORSE than reality
- May undersize battery (misses profitable strategies)
- Break-even analysis too pessimistic

**BUT:**
- Conservative = safer investment analysis
- No risk of overestimating returns

---

## Recommendation for Your Project

### Best Approach: **Option 2 (LP + Post-Processing)**

**Rationale:**
1. Your LP solver is fast and works well
2. Post-processing is simple to add
3. Final costs will be exact
4. Conservative optimization bias is acceptable

**Implementation Checklist:**
```python
# 1. Keep current LP optimizer (no changes needed)
# 2. Add post-processing function
def calculate_exact_power_tariff(monthly_peaks):
    """Calculate actual Lnett tariff from monthly peak demands."""
    TARIFF_BRACKETS = [
        (0, 2, 136), (2, 5, 232), (5, 10, 372), (10, 15, 572),
        (15, 20, 772), (20, 25, 972), (25, 50, 1772), (50, 75, 2572),
        (75, 100, 3372), (100, float('inf'), 5600)
    ]

    total_cost = 0
    for p_max in monthly_peaks:
        for low, high, cost in TARIFF_BRACKETS:
            if low <= p_max < high:
                total_cost += cost
                break
        else:  # p_max >= 100 kW
            total_cost += TARIFF_BRACKETS[-1][2]

    return total_cost

# 3. Update economic analysis
monthly_peaks = extract_monthly_peaks(lp_solution)
actual_tariff = calculate_exact_power_tariff(monthly_peaks)

# 4. Use in NPV/IRR calculations
true_savings = baseline_tariff - actual_tariff
npv = calculate_npv(true_savings, battery_cost, ...)
```

---

## When to Consider MILP

**Use MILP if:**
- Battery strategy is highly sensitive to tariff boundaries (e.g., 49 kW vs 50 kW)
- You need to prove theoretically optimal solution
- Computational time is not critical

**Otherwise:** Stick with LP + post-processing (99% of cases).

---

## Key Takeaways

1. **Step functions are FUNDAMENTALLY INCOMPATIBLE with LP** (discontinuities violate linearity)

2. **Progressive LP is a RAMP approximation** that always underestimates actual tariff

3. **MILP gives EXACT solution** but requires binary variables and slower solver

4. **Best practical approach:** LP optimization + post-processing with exact step function

5. **Your current implementation:** Add exact tariff calculation to final cost analysis, keep LP optimizer as-is

---

## Files Created

1. `milp_tariff_demonstration.py` - Python demonstration of MILP vs LP
2. `TARIFF_MILP_IMPLEMENTATION_GUIDE.md` - Detailed implementation guide
3. `TARIFF_FORMULATION_SUMMARY.md` - This summary document
4. `results/tariff_comparison_step_vs_progressive.png` - Visual comparison plot
5. `results/TARIFF_LP_vs_MILP_COMPREHENSIVE.png` - Comprehensive analysis visualization

---

## References

- **scipy.optimize.milp()**: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html
- **Big-M formulation**: Standard MILP technique for logical constraints
- **HiGHS solver**: Open-source MILP solver (default in scipy.milp, excellent performance)

---

**Bottom line:** Use LP for optimization speed, calculate exact costs in post-processing. This gives you the best of both worlds.
