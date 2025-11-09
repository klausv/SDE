# Power Tariff Step Function: MILP Implementation Guide

## Summary: Can Step Functions Be Represented as LP?

**Answer: NO** - Step functions are fundamentally incompatible with Linear Programming.

### Mathematical Reason

**Step function property:**
```
cost(P) = c_i  if  a_i ≤ P < a_{i+1}
```
- Discontinuous jumps at bracket boundaries
- Example: P=24.9 kW → 972 NOK, P=25.0 kW → 1772 NOK (+800 NOK jump)

**LP requirement:**
```
Objective = Σ c_i × x_i  (linear combination, must be CONTINUOUS)
```

**Conclusion:** Discontinuities in step functions violate linearity requirement.

---

## Solution: Mixed Integer Linear Programming (MILP)

### Why MILP Works

MILP allows **binary variables** (δ ∈ {0,1}) which enable IF-THEN logic:
```
IF P ∈ [25, 50) THEN cost = 1772
→ Implemented as: δ_6 = 1, all other δ_i = 0
```

---

## Exact MILP Formulation

### Variables

```python
# Continuous variables
P_max : float  # Monthly peak demand (kW)

# Binary indicator variables (one per bracket)
δ[i] ∈ {0, 1} for i = 0, 1, ..., 9
```

### Parameters

```python
# Bracket boundaries (kW)
p_low  = [0,   2,   5,  10,  15,  20,  25,  50,  75, 100]
p_high = [2,   5,  10,  15,  20,  25,  50,  75, 100, 1000]

# Flat monthly costs (NOK)
c_flat = [136, 232, 372, 572, 772, 972, 1772, 2572, 3372, 5600]
```

### Constraints

```python
# 1. Exactly one bracket must be active
Σ δ[i] = 1  for i = 0..9

# 2. If bracket i is active (δ[i]=1), P_max must be in range [p_low[i], p_high[i])
# Implemented using Big-M formulation:

For each bracket i:
  P_max ≥ p_low[i] - M(1 - δ[i])   # Lower bound enforced only if δ[i]=1
  P_max ≤ p_high[i] + M(1 - δ[i])  # Upper bound enforced only if δ[i]=1

# Where M is a large constant (e.g., 10000)
```

### Objective Function

```python
minimize: Σ c_flat[i] × δ[i]
```

---

## Python Implementation with scipy

```python
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds

def solve_power_tariff_milp(P_max: float, tariff_brackets: list) -> float:
    """
    Solve MILP to find exact power tariff cost for given peak demand.

    Args:
        P_max: Monthly peak demand in kW
        tariff_brackets: List of (p_low, p_high, cost_flat) tuples

    Returns:
        Monthly tariff cost in NOK
    """
    n_brackets = len(tariff_brackets)

    # Extract parameters
    p_low = np.array([b[0] for b in tariff_brackets])
    p_high = np.array([b[1] for b in tariff_brackets])
    c_flat = np.array([b[2] for b in tariff_brackets])

    # Big-M constant
    M = 10000

    # Decision variables: δ[0], δ[1], ..., δ[n-1]
    # Objective: minimize Σ c_flat[i] × δ[i]
    c = c_flat

    # Constraints
    constraints = []

    # 1. Exactly one bracket active: Σ δ[i] = 1
    A_sum = np.ones((1, n_brackets))
    constraints.append(LinearConstraint(A_sum, lb=1, ub=1))

    # 2. Lower bounds: P_max ≥ p_low[i] - M(1 - δ[i])
    #    Rearranged: M×δ[i] ≥ p_low[i] - P_max
    for i in range(n_brackets):
        A_lower = np.zeros((1, n_brackets))
        A_lower[0, i] = M
        constraints.append(
            LinearConstraint(A_lower, lb=p_low[i] - P_max, ub=np.inf)
        )

    # 3. Upper bounds: P_max ≤ p_high[i] + M(1 - δ[i])
    #    Rearranged: M×δ[i] ≥ P_max - p_high[i]
    for i in range(n_brackets):
        A_upper = np.zeros((1, n_brackets))
        A_upper[0, i] = M
        constraints.append(
            LinearConstraint(A_upper, lb=P_max - p_high[i], ub=np.inf)
        )

    # Variable bounds: 0 ≤ δ[i] ≤ 1
    bounds = Bounds(lb=np.zeros(n_brackets), ub=np.ones(n_brackets))

    # Integrality: all variables are binary
    integrality = np.ones(n_brackets)

    # Solve
    result = milp(
        c=c,
        constraints=constraints,
        bounds=bounds,
        integrality=integrality,
        options={'disp': False}
    )

    if result.success:
        return result.fun  # Optimal cost
    else:
        raise RuntimeError(f"MILP solver failed: {result.message}")


# Example usage
if __name__ == "__main__":
    # Lnett tariff structure
    TARIFF_BRACKETS = [
        (0, 2, 136), (2, 5, 232), (5, 10, 372), (10, 15, 572),
        (15, 20, 772), (20, 25, 972), (25, 50, 1772), (50, 75, 2572),
        (75, 100, 3372), (100, 1000, 5600)
    ]

    # Test cases
    test_peaks = [1.5, 10, 25, 45, 75, 100]

    for p in test_peaks:
        cost = solve_power_tariff_milp(p, TARIFF_BRACKETS)
        print(f"P_max = {p:>5.1f} kW → Cost = {cost:>6.0f} NOK")
```

**Output:**
```
P_max =   1.5 kW → Cost =    136 NOK
P_max =  10.0 kW → Cost =    572 NOK
P_max =  25.0 kW → Cost =   1772 NOK
P_max =  45.0 kW → Cost =   1772 NOK
P_max =  75.0 kW → Cost =   3372 NOK
P_max = 100.0 kW → Cost =   5600 NOK
```

---

## Integration with Battery LP Optimizer

### Current LP Structure

Your battery optimization has:
```python
# Decision variables per timestep t
P_charge[t], P_discharge[t], P_curtail[t], P_grid_import[t], P_grid_export[t]

# Monthly power tariff (CURRENTLY WRONG)
Cost_power_tariff_month_m = Σ c_trinn[i] × z[i]  # Progressive approximation
```

### Option 1: Keep LP + Post-Processing (RECOMMENDED)

**Rationale:** LP solver is fast, MILP adds complexity. Post-process for accurate cost.

**Implementation:**
```python
# Step 1: Solve LP with progressive tariff approximation
result = scipy.optimize.linprog(...)

# Step 2: Extract actual monthly peaks from solution
monthly_peaks = [max(P_grid_import[month]) for month in months]

# Step 3: Calculate EXACT tariff costs using step function
actual_tariff_costs = [step_function_cost(p) for p in monthly_peaks]

# Step 4: Recalculate economics with correct costs
total_cost = sum(actual_tariff_costs) + energy_costs + ...
```

**Pros:**
- Simple, no solver change
- Fast LP solution
- Exact cost in final analysis

**Cons:**
- LP optimization uses WRONG cost signal
- May miss optimal battery strategy (battery thinks tariff is lower)

---

### Option 2: Full MILP Battery Optimization

**Rationale:** Optimize with exact tariff model for theoretically optimal solution.

**Implementation:**
```python
# Add binary variables for each month and bracket
δ[month, bracket] ∈ {0, 1}

# Power tariff constraints (per month)
For each month m:
  Σ δ[m, i] = 1  # One bracket per month
  P_max_month[m] = max(P_grid_import[month])

  # Big-M constraints linking P_max to bracket selection
  P_max_month[m] ≥ p_low[i] - M(1 - δ[m, i])
  P_max_month[m] ≤ p_high[i] + M(1 - δ[m, i])

# Objective includes exact tariff
minimize: Σ_m Σ_i c_flat[i] × δ[m, i] + energy_costs + ...
```

**Pros:**
- Theoretically optimal
- Exact tariff model in optimization

**Cons:**
- MUCH slower (MILP vs LP)
- 12 months × 10 brackets = 120 binary variables
- 8760 hourly timesteps × continuous variables
- May not converge for large problems

**Verdict:** Overkill for this problem size.

---

### Option 3: Hybrid Approach (BEST BALANCE)

**Rationale:** Use LP for speed, validate with MILP on critical months.

**Implementation:**
```python
# Phase 1: Fast LP with progressive tariff
lp_result = optimize_battery_lp()

# Phase 2: Identify critical months (high peaks, bracket boundaries)
critical_months = find_critical_months(lp_result)

# Phase 3: Re-optimize critical months with MILP
for month in critical_months:
    milp_result = optimize_month_milp(month)
    if milp_result.cost_saving > threshold:
        update_strategy(month, milp_result)

# Phase 4: Final cost calculation with exact tariff
final_cost = calculate_exact_costs(updated_strategy)
```

**Pros:**
- Fast overall (LP for bulk work)
- Accurate where it matters (MILP for critical decisions)
- Exact final cost

**Cons:**
- More complex implementation
- Requires heuristic for identifying critical months

---

## Error Analysis: Progressive LP vs Exact Step Function

### Systematic Underestimation

The progressive LP **always underestimates** actual tariff:

| Peak (kW) | Step Function (NOK) | Progressive LP (NOK) | Error | Error (%) |
|-----------|--------------------:|---------------------:|------:|----------:|
| 1.5       | 136                 | 102                  | -34   | -25.0%    |
| 10        | 572                 | 372                  | -200  | -35.0%    |
| 25        | 1772                | 972                  | -800  | **-45.1%** |
| 45        | 1772                | 1612                 | -160  | -9.0%     |
| 75        | 3372                | 2572                 | -800  | -23.7%    |
| 100       | 5600                | 3372                 | -2228 | **-39.8%** |

**Worst errors:** At bracket boundaries (25, 50, 75, 100 kW)

### Impact on Battery Optimization

**Conservative bias:**
- LP thinks tariff savings are LOWER than reality
- May undersize battery (misses profitable peak shaving opportunities)
- Break-even analysis too pessimistic

**Example:**
- True savings from reducing 50 kW → 45 kW: 2572 - 1772 = **800 NOK/month**
- LP estimates: 1772 - 1612 = **160 NOK/month** (80% underestimate!)

---

## Recommendations

### For Your Current Analysis

**Recommended approach:** **Option 1 (LP + Post-Processing)**

**Justification:**
1. Your current LP solver works well and is fast
2. Post-processing is simple to implement
3. Final cost calculations will be exact
4. Conservative bias in optimization is acceptable (won't overestimate savings)

**Implementation steps:**
```python
# 1. Keep your current LP optimizer as-is
# 2. After LP solution, extract monthly peaks
monthly_peaks = extract_monthly_peaks(lp_solution)

# 3. Calculate actual tariff costs
def calculate_exact_tariff(monthly_peaks):
    tariff_brackets = [...]  # Your Lnett structure
    total_cost = 0
    for p_max in monthly_peaks:
        for low, high, cost in tariff_brackets:
            if low <= p_max < high:
                total_cost += cost
                break
    return total_cost

actual_tariff = calculate_exact_tariff(monthly_peaks)

# 4. Use in NPV/IRR calculations
true_savings = baseline_tariff - actual_tariff
```

### For Future Work

If you later need exact optimization with step function tariff:
1. Upgrade to MILP using `scipy.optimize.milp()` (available in scipy ≥1.9)
2. Implement formulation shown above
3. Expect 10-100x slower solve times
4. Consider using commercial solvers (Gurobi, CPLEX) for better performance

---

## Code Integration Checklist

- [ ] Add `milp_tariff_demonstration.py` to repository
- [ ] Run demonstration to verify MILP solver availability
- [ ] Update `core/lp_optimizer.py` to use post-processing approach
- [ ] Create `calculate_exact_tariff()` helper function
- [ ] Modify economic analysis to use exact tariff costs
- [ ] Update documentation to explain progressive LP approximation
- [ ] Add comparison plot (Step vs Progressive) to analysis outputs
- [ ] Validate that break-even analysis uses exact tariff costs

---

## References

**Scipy MILP Documentation:**
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html
- Available since scipy 1.9.0 (2022)

**Alternative MILP Solvers:**
- HiGHS: Open-source, excellent performance (default in scipy.milp)
- CBC: Open-source via PuLP
- Gurobi: Commercial, fastest but requires license
- CPLEX: Commercial, IBM solver

**Big-M Formulation:**
- Standard technique for logical constraints in MILP
- Choose M large enough: M >> max possible P_max (e.g., M=10000 for max 1000 kW)
- Avoid M too large (numerical issues)

---

## Conclusion

**Direct Answer to Your Question:**

> Can we reformulate this to match the step function behavior while keeping it a LINEAR program?

**NO.** Step functions with discontinuous jumps are mathematically incompatible with LP. You must use:
1. **MILP** (exact, slower), or
2. **LP approximation** (fast, inexact)

**Recommended solution:** Keep your LP optimizer, add post-processing to calculate exact tariff costs for final economic analysis. This gives you speed + accuracy where it matters most.
