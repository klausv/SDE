# Dual Variable Attribution - Complete Guide

## Executive Summary

**Problem**: How to allocate battery economic value into stakeholder-friendly categories (peak shaving, arbitrage, self-consumption, curtailment)?

**Solution**: Use dual variables (shadow prices) from LP optimization to mathematically attribute value based on which constraints bind when.

**Key Insight**: Shadow price tells you the marginal value of relaxing a constraint → binding constraints reveal where value comes from.

---

## 1. Theory Foundation

### What Are Dual Variables?

For LP problem:
```
Minimize: c^T x
Subject to: Ax ≤ b
            x ≥ 0
```

The **dual variable** λ for constraint `Ax ≤ b` represents:
```
λ = ∂(Objective)/∂b
```

**Economic interpretation**:
- λ = Marginal cost reduction from relaxing constraint by 1 unit
- If λ > 0: Constraint is binding (limiting savings)
- If λ = 0: Constraint has slack (not limiting)

### Complementary Slackness

Key principle connecting primal and dual:
```
λ_i × slack_i = 0  ∀i
```

Either:
1. Constraint is binding (slack = 0) AND dual > 0 → Value attribution here!
2. Constraint has slack (slack > 0) AND dual = 0 → No value attribution

---

## 2. Constraint-to-Value Mapping

For battery optimization LP, map constraints to economic categories:

### A. Peak Shaving Value

**Constraint**:
```
peak_month ≥ P_import[t]  ∀t
```

**Dual Variable**: λ_peak[t]

**Economic Meaning**:
- If λ_peak[t] > 0: This hour determines monthly peak → battery actively limiting it
- Value = λ_peak[t] × power_tariff_rate × months_per_year

**Why it works**:
- Binding peak constraint → battery preventing higher peak
- Dual tells you marginal value of 1 kW peak reduction
- Multiply by tariff to get NOK value

**Implementation**:
```python
peak_value = sum(
    constraint.pi for constraint in peak_constraints
    if constraint.pi > 0
) * power_tariff_rate
```

---

### B. Curtailment Avoidance Value

**Constraint**:
```
P_export[t] ≤ Grid_limit  (77 kW)
```

**Dual Variable**: λ_curtail[t]

**Economic Meaning**:
- If λ_curtail[t] > 0: Export hitting grid limit → PV being curtailed
- If battery charging during this hour → storing curtailed energy
- Value = Energy stored × spot price (recovered revenue)

**Why it works**:
- Binding export limit → curtailment happening
- Battery charging → storing energy that would be lost
- Dual tells you value of increasing export limit by 1 kW
- But we can't increase grid limit → battery stores instead

**Implementation**:
```python
curtailment_value = 0
for t, dual in enumerate(export_limit_duals):
    if dual > 0 and P_charge[t] > 0:
        # Grid limit binding AND battery charging = curtailment avoided
        curtailment_value += P_charge[t] * spot_price[t]
```

---

### C. Arbitrage Value

**Constraint**:
```
SOC[t+1] = SOC[t] + η×P_charge[t] - P_discharge[t]/η
```

**Dual Variable**: μ_soc[t] (energy opportunity cost)

**Economic Meaning**:
- μ_soc[t] = Shadow price of having 1 kWh stored at hour t
- If μ_soc[t+1] > μ_soc[t]: Future value higher → store now
- If price[t+1] > price[t] AND μ[t+1] > μ[t]: Arbitrage opportunity

**Detection Logic**:
```python
for t in range(T-1):
    price_spread = price[t+1] - price[t]
    dual_spread = mu_soc[t+1] - mu_soc[t]

    if sign(price_spread) == sign(dual_spread):
        # Battery is time-shifting for price arbitrage

        if P_charge[t] > 0:
            # Charging during low price (buying low)
            # BUT: Exclude PV charging (that's self-consumption)
            grid_charge = P_charge[t] - min(P_charge[t], PV[t])
            arbitrage_value += grid_charge × dual_spread

        elif P_discharge[t] > 0:
            # Discharging during high price (selling high)
            arbitrage_value += P_discharge[t] × dual_spread
```

**Why price vs dual spread?**
- Pure arbitrage: Battery responds to price signals
- If duals move with prices → battery doing time-shifting for economic gain
- If duals move opposite to prices → battery serving other constraints (peak, curtailment)

---

### D. Self-Consumption Value

**Challenge**: Not directly observable from one constraint!

Self-consumption = Battery stores PV energy → discharges later to avoid import

**Separation from Arbitrage**:
- Arbitrage: Grid → Battery → Grid (charge from grid during low prices)
- Self-consumption: PV → Battery → Load (charge from PV, discharge to avoid import)

**Method 1: Source Tracing** (Recommended)
```python
def trace_soc_source(t, charge_history, pv_history):
    """Determine if SOC at time t came from PV or grid."""

    lookback = 24  # hours

    # Sum recent PV vs grid charging
    pv_charge = sum(
        min(charge_history[t-i], pv_history[t-i])
        for i in range(lookback)
    )
    grid_charge = sum(
        charge_history[t-i] - min(charge_history[t-i], pv_history[t-i])
        for i in range(lookback)
    )

    # Fraction from PV
    pv_fraction = pv_charge / (pv_charge + grid_charge + 1e-9)

    return pv_fraction

# When discharging:
if P_discharge[t] > 0:
    pv_fraction = trace_soc_source(t, P_charge, PV)

    # Self-consumption portion
    self_consumption = P_discharge[t] × pv_fraction
    self_consumption_value += self_consumption × (spot[t] + tariff[t])

    # Arbitrage portion (if any came from grid)
    arbitrage_portion = P_discharge[t] × (1 - pv_fraction)
    # (Already counted in arbitrage calculation above)
```

**Method 2: Residual Allocation**
```python
# After calculating peak, curtailment, and arbitrage:
total_value = baseline_cost - optimized_cost
known_values = peak_value + curtailment_value + arbitrage_value

# Remainder is self-consumption
self_consumption_value = total_value - known_values - degradation_cost
```

**Which method?**
- Source tracing: More theoretically rigorous, harder to implement
- Residual: Simpler, but lumps all "other" value into self-consumption
- **Recommendation**: Use residual for first version, refine with source tracing

---

### E. Battery Degradation Cost

**Not from LP constraints** (degradation is ex-post calculation).

**Method**:
```python
# Calculate equivalent full cycles
total_throughput = sum(P_charge) + sum(P_discharge)  # kWh
cycles = total_throughput / (2 × battery_capacity_kwh)

# Degradation cost
cost_per_cycle = (battery_cost_per_kwh × 0.02)  # 2% per cycle assumption
degradation_cost = cycles × battery_capacity_kwh × cost_per_cycle
```

**Allocation to categories**:
- Option 1: Don't allocate → report as separate line item
- Option 2: Allocate proportionally to positive values
  ```python
  for category in [peak, arbitrage, curtailment, self_consumption]:
      category_net = category - (degradation_cost × category / total_value)
  ```

**Recommendation**: Option 1 (separate line item) for transparency

---

## 3. Implementation Steps

### Step 1: Extract Duals from PuLP

```python
def extract_duals(prob):
    """Extract dual variables after solving."""

    duals = {
        'peak': [],
        'soc_dynamics': [],
        'export_limit': [],
        # ... other constraint types
    }

    for name, constraint in prob.constraints.items():
        dual = constraint.pi  # Shadow price

        # Categorize by name pattern
        if 'peak' in name.lower():
            duals['peak'].append((name, dual))
        elif 'soc' in name.lower():
            duals['soc_dynamics'].append((name, dual))
        # ... etc

    return duals
```

**Important**:
- Duals only available AFTER solving: `prob.solve(solver)`
- HiGHS and CBC both provide duals
- Check `prob.status == 'Optimal'` before extracting

### Step 2: Attribute Value by Constraint

```python
def attribute_value(prob, solution):
    """Decompose total value using duals."""

    duals = extract_duals(prob)

    # 1. Peak shaving
    peak_value = sum(d for _, d in duals['peak'] if d > 0) × power_tariff

    # 2. Curtailment
    curtailment_value = 0
    for t, (_, dual) in enumerate(duals['export_limit']):
        if dual > 0 and solution['P_charge'][t] > 0:
            curtailment_value += solution['P_charge'][t] × spot_price[t]

    # 3. Arbitrage (from SOC duals + price spreads)
    arbitrage_value = calculate_arbitrage(duals['soc_dynamics'], solution, prices)

    # 4. Self-consumption (residual method)
    total_value = baseline_cost - optimized_cost
    self_consumption = total_value - peak_value - curtailment_value - arbitrage_value

    # 5. Degradation
    degradation = -calculate_degradation(solution, battery_kwh)

    return {
        'peak_shaving': peak_value,
        'curtailment': curtailment_value,
        'arbitrage': arbitrage_value,
        'self_consumption': self_consumption,
        'degradation': degradation
    }
```

### Step 3: Aggregate Across 52 Weeks

```python
def annual_attribution(weekly_results):
    """Aggregate weekly duals to annual totals."""

    annual = {
        'peak_shaving': 0,
        'arbitrage': 0,
        'curtailment': 0,
        'self_consumption': 0,
        'degradation': 0
    }

    for week in weekly_results:
        week_values = attribute_value(week['prob'], week['solution'])
        for key in annual:
            annual[key] += week_values[key]

    return annual
```

---

## 4. Validation & Sanity Checks

### Check 1: Value Conservation
```python
assert abs(sum(values.values()) - total_savings) < 0.01  # Allow 1% rounding
```

All attributed values must sum to total savings (baseline - optimized).

### Check 2: No Negative Categories (Except Degradation)
```python
assert peak_value >= 0
assert curtailment_value >= 0
assert arbitrage_value >= 0
# self_consumption can be negative if residual method and miscategorization
# degradation should be negative
```

### Check 3: Physical Consistency
```python
# Curtailment value can't exceed total curtailed energy
max_curtailment = sum(max(0, PV[t] - Grid_limit) for t in hours)
assert curtailment_value <= max_curtailment × max(spot_prices)

# Arbitrage can't exceed battery throughput × price spread
max_arbitrage = sum(P_discharge) × (max(prices) - min(prices))
assert arbitrage_value <= max_arbitrage
```

### Check 4: Compare Methods
```python
# Try both source-tracing and residual for self-consumption
# They should be within 10% if attribution is working
method1 = trace_source_self_consumption(...)
method2 = residual_self_consumption(...)
assert abs(method1 - method2) / max(method1, method2) < 0.10
```

---

## 5. Limitations & Edge Cases

### Limitation 1: Non-Binding Constraints

**Problem**: If constraint never binds, dual = 0, but value may still exist.

**Example**:
- Peak constraint binds in Week 1 (winter)
- Never binds in Week 26 (summer, low demand)
- But battery still provides value → not captured by duals

**Solution**:
- Aggregate across full year (52 weeks)
- Value appears in binding weeks, zero in non-binding
- Annual sum is correct

### Limitation 2: Tight Coupling of Constraints

**Problem**: Multiple constraints bind simultaneously → hard to separate value.

**Example**:
- Hour 12: Export limit binds (curtailment) AND peak tracking binds
- Battery charging → is this curtailment storage or peak shaving?

**Solution**:
- Dual decomposition: Value = Σ (dual[i] × slack[i])
- Distribute value proportionally to dual magnitudes
  ```python
  if export_dual > 0 and peak_dual > 0:
      total_dual = export_dual + peak_dual
      curtailment_fraction = export_dual / total_dual
      peak_fraction = peak_dual / total_dual

      curtailment_value += P_charge[t] × price[t] × curtailment_fraction
      peak_value += P_charge[t] × power_tariff × peak_fraction
  ```

### Limitation 3: Self-Consumption vs Arbitrage Boundary

**Problem**: Battery stores PV at noon, discharges at 8 PM.
- Is this self-consumption? (PV → load)
- Or arbitrage? (noon price low, 8 PM high)

**Answer**: **Both!** It's self-consumption-driven arbitrage.

**Solution**:
- Primary classification by energy source (PV vs grid charging)
- If PV → self-consumption
- If grid → arbitrage
- Don't try to separate temporal aspects

### Limitation 4: Degradation Allocation

**Problem**: Degradation is physical (cycles), not constraint-based.

**Solution**:
- Calculate separately from duals
- Report as standalone cost (don't allocate)
- OR allocate proportionally to usage drivers:
  ```python
  degradation_by_category = {
      'peak': degradation × (peak_cycles / total_cycles),
      'arbitrage': degradation × (arbitrage_cycles / total_cycles),
      # etc.
  }
  ```

---

## 6. Advanced Topics

### Dual Decomposition Method

For fully rigorous attribution:
```
Total Value = Σ_i (dual[i] × (b[i] - Ax[i]))
            = Σ_i (dual[i] × slack[i])
```

Where:
- dual[i] = shadow price of constraint i
- slack[i] = constraint slack (≥0 for inequality)

Categorize constraints → sum their contributions:
```python
value_decomposition = {}

for constraint_type in ['peak', 'curtailment', 'soc', ...]:
    value_decomposition[constraint_type] = sum(
        dual[i] × slack[i]
        for i in constraints_of_type(constraint_type)
    )
```

**Advantage**: Mathematically rigorous, no arbitrary allocation

**Disadvantage**: Requires slack values, not just duals

### Sensitivity Analysis with Duals

Use duals for "what-if" scenarios:

**Q**: What if battery capacity was 120 kWh instead of 100?

**A**:
```python
# Dual on SOC_max constraint = marginal value of capacity
capacity_dual = mean(duals['soc_upper'])  # NOK/kWh

value_increase = (120 - 100) × capacity_dual  # NOK/year
```

**Q**: What if grid limit was 80 kW instead of 77?

**A**:
```python
export_limit_dual = mean(duals['export_limit'][duals['export_limit'] > 0])
curtailment_reduction = (80 - 77) × export_limit_dual  # NOK/year
```

### Multi-Period Coupling

For rolling horizon optimization:
- Week 1 SOC_end = Week 2 SOC_start (coupling constraint)
- Dual on coupling constraint = value of inter-week storage
- Helps attribute seasonal shifting (summer → winter storage)

---

## 7. Comparison to Manual Allocation

### Manual Method (Current):
```python
# Peak shaving
peak_manual = (baseline_peak - optimized_peak) × power_tariff

# Arbitrage
price_high_hours = hours where price > threshold
arbitrage_manual = sum(discharge[t] × price[t] for t in price_high_hours)
```

**Problems**:
- Arbitrary thresholds ("high price" = what?)
- Double counting (peak hour may also be high price)
- Negative values (if threshold wrong)

### Dual Method:
```python
# Peak shaving
peak_dual = sum(dual[t] for t in peak_constraints if dual[t] > 0)

# Arbitrage
arbitrage_dual = sum based on SOC dual spreads
```

**Advantages**:
- No arbitrary thresholds
- No double counting (complementary slackness ensures mutual exclusion)
- Always positive (duals ≥ 0 for minimization)
- Mathematically rigorous

---

## 8. Practical Recommendations

### For Your Stavanger Analysis:

1. **Start Simple**:
   - Extract duals from existing WeeklyOptimizer
   - Calculate peak + curtailment (easiest categories)
   - Use residual for self-consumption

2. **Validate**:
   - Check value conservation (sum = total savings)
   - Compare to manual method for peak shaving
   - Plot dual time series to understand patterns

3. **Refine**:
   - Add arbitrage calculation (SOC dual spreads)
   - Implement source tracing for self-consumption
   - Allocate degradation proportionally

4. **Report**:
   - Annual breakdown table:
     ```
     Peak Shaving:           15,000 kr  (40%)
     Curtailment Avoidance:   8,000 kr  (21%)
     Arbitrage:               5,000 kr  (13%)
     Self-Consumption:       10,000 kr  (26%)
     -------------------------------
     Gross Value:            38,000 kr (100%)
     Degradation:           - 3,000 kr
     -------------------------------
     Net Value:              35,000 kr
     ```

5. **Sensitivity**:
   - Use duals for "what-if" scenarios
   - Report marginal values (e.g., "1 kWh more capacity → +50 kr/year")

---

## 9. Code Integration Points

### Modify WeeklyOptimizer:

```python
class WeeklyOptimizer:
    def solve_week(self, week_num):
        # ... existing code ...

        self.prob.solve(PULP_CBC_CMD())

        # NEW: Extract duals
        self.duals = self.extract_duals()

        # NEW: Attribute value
        self.value_attribution = self.attribute_value()

        return self.get_results()

    def extract_duals(self):
        """Extract dual variables from solved problem."""
        duals = {}
        for name, constraint in self.prob.constraints.items():
            duals[name] = constraint.pi
        return duals

    def attribute_value(self):
        """Use duals to attribute value by category."""
        attributor = DualValueAttributor()
        return attributor.attribute_weekly_value(
            duals=self.duals,
            solution_data=self.get_results(),
            spot_prices=self.spot_prices,
            # ... other inputs
        )
```

### Add to Economic Model:

```python
class EconomicModel:
    def calculate_npv(self, annual_results):
        # ... existing NPV calculation ...

        # NEW: Aggregate dual-based attribution
        annual_attribution = aggregate_weekly_attributions(
            [week['value_attribution'] for week in annual_results]
        )

        return {
            'NPV': npv,
            'IRR': irr,
            'payback': payback,
            'value_breakdown': annual_attribution  # NEW!
        }
```

---

## 10. Example Output

After implementation, your analysis should produce:

```
========================================
Battery Value Attribution (Dual-Based)
========================================

100 kWh Battery @ 50 kW Power

Annual Value Breakdown:
------------------------
Peak Power Tariff Savings:     18,500 kr  (45.2%)
  → Monthly peak reduced from 82 kW to 68 kW avg
  → Saves 14 kW × 60 kr/kW/month × 12 months

Curtailment Avoidance:          6,200 kr  (15.1%)
  → 280 hours with grid export limit binding
  → Stored 1,240 kWh that would be curtailed

Energy Arbitrage:               4,800 kr  (11.7%)
  → 156 charge cycles from grid (low prices)
  → Avg price spread: 0.31 kr/kWh

PV Self-Consumption:           11,500 kr  (28.0%)
  → 2,340 kWh PV stored → discharged
  → Avoided import cost: 0.49 kr/kWh avg

--------------------------------------------
Gross Annual Value:            41,000 kr (100.0%)

Battery Degradation:           -3,100 kr
  → 85 equivalent full cycles
  → Degradation: 0.05 kr/kWh/cycle

============================================
Net Annual Value:              37,900 kr
============================================

Marginal Values (from duals):
------------------------------
+1 kWh capacity  → +62 kr/year
+1 kW power      → +105 kr/year
+1 kW grid limit → -48 kr/year (less curtailment value)
```

This gives stakeholders clear, mathematically rigorous understanding of where value comes from!

---

## References

1. **Linear Programming Theory**: Bertsimas & Tsitsiklis, "Introduction to Linear Optimization"
2. **Energy Systems**: Sioshansi & Conejo, "Optimization in Engineering"
3. **Battery Economics**: NREL reports on energy storage valuation
4. **Dual Decomposition**: Boyd et al., "Distributed Optimization and Statistical Learning via ADMM"
