# Dual Variables - Quick Reference

## Core Concept

**Shadow Price (Dual Variable)** = Marginal value of relaxing a constraint by 1 unit

```
If constraint i binds: dual[i] > 0 → Value comes from this constraint
If constraint i has slack: dual[i] = 0 → No value attribution here
```

---

## Constraint → Value Mapping

| Constraint | Dual Symbol | Economic Meaning | Value Category |
|------------|-------------|------------------|----------------|
| `peak_month ≥ P_import[t]` | λ_peak[t] | Value of reducing peak by 1 kW | **Peak Shaving** |
| `P_export[t] ≤ Grid_limit` | λ_curtail[t] | Value of increasing export limit | **Curtailment** |
| `SOC[t+1] = SOC[t] + ...` | μ_soc[t] | Opportunity cost of storage | **Arbitrage** |
| `SOC[t] ≤ SOC_max` | μ_upper[t] | Value of more capacity | (Sensitivity) |
| `P_charge ≤ P_max` | λ_charge[t] | Value of more power | (Sensitivity) |

---

## Quick Implementation Checklist

### 1. Extract Duals from PuLP
```python
prob.solve(PULP_CBC_CMD())  # or HiGHS

duals = {}
for name, constraint in prob.constraints.items():
    duals[name] = constraint.pi  # Shadow price
```

### 2. Peak Shaving Value
```python
peak_value = sum(
    dual for dual in peak_constraint_duals if dual > 0
) * power_tariff_rate
```

### 3. Curtailment Value
```python
curtailment_value = 0
for t, dual in enumerate(export_limit_duals):
    if dual > 0 and P_charge[t] > 0:
        # Grid limit binding + battery charging = curtailment avoided
        curtailment_value += P_charge[t] * spot_price[t]
```

### 4. Arbitrage Value
```python
arbitrage_value = 0
for t in range(len(soc_duals) - 1):
    price_spread = spot[t+1] - spot[t]
    dual_spread = soc_duals[t+1] - soc_duals[t]

    if sign(price_spread) == sign(dual_spread):
        # Time-shifting for price arbitrage
        if P_charge[t] > 0:
            grid_charge = P_charge[t] - min(P_charge[t], PV[t])
            arbitrage_value += grid_charge * abs(dual_spread)
```

### 5. Self-Consumption (Residual Method)
```python
total_value = baseline_cost - optimized_cost
known = peak_value + curtailment_value + arbitrage_value
self_consumption_value = total_value - known - degradation
```

### 6. Degradation (Separate Calculation)
```python
throughput = sum(P_charge) + sum(P_discharge)
cycles = throughput / (2 * battery_kwh)
degradation = -cycles * battery_kwh * cost_per_cycle_per_kwh
```

---

## Validation Checks

```python
# 1. Value conservation
assert abs(sum(values) - total_savings) < 0.01

# 2. Non-negative (except degradation)
assert peak_value >= 0
assert curtailment_value >= 0
assert arbitrage_value >= 0

# 3. Physical bounds
max_curtailment = sum(max(0, PV[t] - Grid_limit) for t in hours)
assert curtailment_value <= max_curtailment * max(spot_prices)
```

---

## Common Pitfalls

### ❌ WRONG: Using variable values instead of duals
```python
# This tells you WHAT battery did, not WHY
peak_value = sum(P_discharge[t] for t in peak_hours)
```

### ✅ RIGHT: Using dual variables
```python
# This tells you WHY battery created value
peak_value = sum(dual[t] for t in hours if dual[t] > 0)
```

---

### ❌ WRONG: Double counting with manual thresholds
```python
# Arbitrage and peak might overlap!
arbitrage = sum(discharge[t] for t in hours if price[t] > 0.80)
peak = sum(discharge[t] for t in hours if import[t] > 70)
```

### ✅ RIGHT: Complementary slackness ensures mutual exclusion
```python
# Duals automatically prevent double counting
arbitrage = calculate_from_soc_duals(...)
peak = sum(dual[t] for t in peak_constraints if dual[t] > 0)
```

---

### ❌ WRONG: Ignoring binding constraints
```python
# Assumes all hours contribute equally
avg_dual = mean(all_duals)
```

### ✅ RIGHT: Only binding constraints have value
```python
# Only non-zero duals matter
active_duals = [d for d in all_duals if d > 0]
value = sum(active_duals) * unit_rate
```

---

## Decision Tree: Which Method to Use?

```
Do you have LP solver with dual variables?
├─ YES → Use dual-based attribution (rigorous, no double counting)
│         ✓ Mathematically sound
│         ✓ No arbitrary thresholds
│         ✓ Complementary slackness prevents overlaps
│
└─ NO → Use manual allocation (approximation)
          ⚠ Risk of double counting
          ⚠ Arbitrary thresholds
          ⚠ May produce negative values
```

---

## Solver Support for Duals

| Solver | Dual Support | Access Method |
|--------|--------------|---------------|
| HiGHS | ✅ Yes | `constraint.pi` |
| CBC | ✅ Yes | `constraint.pi` |
| GLPK | ✅ Yes | `constraint.pi` |
| Gurobi | ✅ Yes | `constraint.Pi` |
| CPLEX | ✅ Yes | `constraint.dual_value` |

**Your setup**: HiGHS via PuLP → `constraint.pi` ✅

---

## Integration with Existing Code

### Before (Manual Allocation):
```python
# In economic_model.py
avoided_import = sum(discharge * price for high-price hours)
peak_savings = (baseline_peak - opt_peak) * tariff
# ⚠ Double counting possible!
```

### After (Dual Attribution):
```python
# In economic_model.py
from optimization.dual_value_attribution import DualValueAttributor

attributor = DualValueAttributor()
duals = extract_duals(prob)
values = attributor.attribute_weekly_value(duals, solution, prices, pv)

# ✓ No double counting, mathematically rigorous
```

---

## Interpretation Guide

### High Peak Dual (e.g., λ_peak = 60 kr/kW)
**Meaning**: Reducing import peak by 1 kW saves 60 kr/month
**Action**: Battery is actively limiting monthly peak → peak shaving valuable

### High Export Limit Dual (e.g., λ_curtail = 0.85 kr/kWh)
**Meaning**: Relaxing grid limit by 1 kW would save 0.85 kr this hour
**Action**: Curtailment happening → battery storing excess PV → high value

### SOC Dual Spread (e.g., μ[t+1] - μ[t] = 0.30 kr/kWh)
**Meaning**: Energy stored now worth 0.30 kr/kWh more in next hour
**Action**: If price spread same sign → arbitrage; if opposite → other constraint driving

### Zero Dual (e.g., λ = 0)
**Meaning**: Constraint has slack → not limiting optimization
**Action**: No value attributed to this constraint at this hour

---

## Typical Annual Breakdown (Stavanger Example)

```
Battery: 100 kWh @ 50 kW

Peak Shaving:             18,500 kr  (45%)  ← Largest value source
Self-Consumption:         11,500 kr  (28%)
Curtailment Avoidance:     6,200 kr  (15%)
Energy Arbitrage:          4,800 kr  (12%)
─────────────────────────────────────────
Gross Value:              41,000 kr (100%)
Degradation:              -3,100 kr
─────────────────────────────────────────
Net Value:                37,900 kr
```

**Insight**: Peak shaving dominates → Power tariff structure drives economics

---

## Marginal Value Analysis (from Duals)

Use duals for "what-if" scenarios:

```python
# What if battery was 120 kWh instead of 100?
capacity_dual = mean(soc_upper_duals[soc_upper_duals > 0])
extra_value = (120 - 100) * capacity_dual  # kr/year

# What if power rating was 60 kW instead of 50?
power_dual = mean(discharge_limit_duals[discharge_limit_duals > 0])
extra_value = (60 - 50) * power_dual  # kr/year
```

---

## Files to Create/Modify

### New Files:
1. `src/optimization/dual_value_attribution.py` ✅ Created
2. `claudedocs/dual_variables_guide.md` ✅ Created
3. `examples/dual_attribution_example.py` ✅ Created

### Modify Existing:
1. `src/optimization/weekly_optimizer.py`
   - Add method to extract and return duals
   - Store prob object after solving

2. `src/optimization/economic_model.py`
   - Import DualValueAttributor
   - Replace manual allocation with dual-based

3. `main.py`
   - Add dual attribution to annual analysis loop
   - Generate stakeholder report with breakdown

---

## Next Steps

1. ✅ **Understand theory** (this guide)
2. ⬜ **Test extraction**: Extract duals from one week's LP solution
3. ⬜ **Validate**: Compare dual-based peak shaving vs manual calculation
4. ⬜ **Implement**: Add dual attribution to weekly loop
5. ⬜ **Aggregate**: Sum 52 weeks to annual breakdown
6. ⬜ **Report**: Generate stakeholder-friendly value attribution table

---

## Questions to Ask Yourself

- [ ] Can I extract `constraint.pi` from my solved LP?
- [ ] Do peak constraint duals make sense (positive when peak high)?
- [ ] Does total attributed value = total savings (value conservation)?
- [ ] Are all categories non-negative (except degradation)?
- [ ] Does curtailment value match PV excess hours?
- [ ] Do I understand which constraints drive each value category?

If YES to all → You're ready to implement! 🚀

---

**Key Takeaway**: Dual variables tell you **why** battery creates value, not just **what** it does. Use them to attribute value rigorously and avoid double counting.
