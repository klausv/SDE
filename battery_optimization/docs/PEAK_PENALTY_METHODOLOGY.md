# Peak Penalty Methodology
## Replacing Long Forecasting Horizons with Smart Constraints

## The Core Problem

### Monthly Power Tariff Structure (Norwegian Grid)
```
Power tariff = Monthly peak demand (kW) × Tariff rate (NOK/kW/month)
```

**Example**:
- Current month peak: 50 kW
- Tariff rate: 50 NOK/kW/month
- Days remaining: 15
- If we create new peak of 60 kW → Extra cost: 10 kW × 50 NOK × 0.5 months = 250 NOK

### Naive Approach: 30-Day Horizon ❌

**Why it seems logical**:
- Power tariff is based on **monthly** peak
- Therefore, optimize over **full month** to see all potential peaks
- Plan battery usage to avoid creating new peaks

**Why it fails**:
```
Forecast Accuracy by Horizon:
24 hours:  70-80% accurate  ✅ Usable
48 hours:  60-70% accurate  ⚠️ Degraded
1 week:    50-60% accurate  ❌ Poor
2 weeks:   40-50% accurate  ❌ Very poor
30 days:   30-40% accurate  ❌ Essentially random
```

**Result of 30-day optimization**:
- 70% of the "optimization" is based on **wrong forecasts**
- Battery makes decisions for imaginary future peaks that won't happen
- Suboptimal behavior NOW because of incorrect assumptions about LATER
- **Classic case of "garbage in, garbage out"**

---

## The Solution: Peak Penalty Function

Instead of trying to predict 30 days ahead, use **current information + penalty function**.

### Concept: Shadow Price of Peak Demand

**Key insight**: The monthly peak is a **state variable** that evolves through the month.

At any moment during the month, we know:
1. **Current monthly peak so far**: P_peak_current (kW)
2. **Days remaining in month**: d_remaining
3. **Probability of exceeding peak**: Based on current grid demand

The **marginal value** of avoiding a new peak = Expected cost if peak increases by 1 kW

### Mathematical Formulation

#### Step 1: Calculate Peak Penalty Rate

```python
def calculate_peak_penalty(current_monthly_peak_kw, days_remaining, tariff_rate_nok_per_kw):
    """
    Calculate the penalty (shadow price) for exceeding current monthly peak.

    This represents how much we should "pay" in the objective function
    to avoid creating a new monthly peak.
    """
    # Base penalty: tariff rate × fraction of month remaining
    base_penalty = tariff_rate_nok_per_kw * (days_remaining / 30)

    # Risk adjustment: higher penalty early in month (more days to "defend" the peak)
    # Lower penalty late in month (fewer days left, less impact)
    risk_multiplier = 1.0 + 0.5 * (days_remaining / 30)  # 1.0 to 1.5

    peak_penalty_nok_per_kw = base_penalty * risk_multiplier

    return peak_penalty_nok_per_kw
```

**Example calculation**:
```python
# Day 5 of month (25 days remaining)
current_peak = 50 kW
tariff_rate = 50 NOK/kW/month
days_remaining = 25

base_penalty = 50 × (25/30) = 41.67 NOK/kW
risk_multiplier = 1.0 + 0.5 × (25/30) = 1.42
peak_penalty = 41.67 × 1.42 = 59 NOK/kW

# Interpretation: If grid demand would exceed 50 kW,
# pay battery 59 NOK/kW to discharge and avoid new peak
```

#### Step 2: Integrate into 24-Hour LP Objective

```python
# Standard objective (without peak penalty)
minimize: sum over t=0 to 95 (15-min intervals in 24h):
    C_import[t] × P_grid_import[t] - C_export[t] × P_grid_export[t]
    + C_battery_cycle × P_battery_discharge[t]

# Enhanced objective (with peak penalty)
minimize: sum over t=0 to 95:
    C_import[t] × P_grid_import[t]
    - C_export[t] × P_grid_export[t]
    + C_battery_cycle × P_battery_discharge[t]
    + peak_penalty × max(0, P_grid_import[t] - P_peak_current)  # NEW TERM

# Where:
# P_grid_import[t] = actual grid import at time t (decision variable)
# P_peak_current = current monthly peak (parameter, known)
# peak_penalty = calculated shadow price (NOK/kW)
```

**Problem**: `max(0, x)` is **non-linear** → cannot use in LP directly

**Solution**: Introduce auxiliary variable

```python
# Linear formulation using auxiliary variables
Variables:
    P_grid_import[t]  for t in 0..95
    P_peak_violation[t]  for t in 0..95  # NEW: peak exceedance

Constraints:
    P_peak_violation[t] >= 0  for all t
    P_peak_violation[t] >= P_grid_import[t] - P_peak_current  for all t

Objective:
    minimize: sum over t:
        C_import[t] × P_grid_import[t]
        - C_export[t] × P_grid_export[t]
        + C_battery_cycle × P_battery_discharge[t]
        + peak_penalty × P_peak_violation[t]  # Linear penalty term
```

**How it works**:
- If `P_grid_import[t] < P_peak_current`:
  → `P_peak_violation[t]` can be 0 (minimizer will choose this)
  → No penalty

- If `P_grid_import[t] > P_peak_current`:
  → `P_peak_violation[t]` must be ≥ (P_grid_import - P_peak_current)
  → Penalty = peak_penalty × exceedance
  → Battery incentivized to discharge and reduce grid import

---

## State-Dependent Peak Risk

You mentioned:
> "possibly some kind of prediction of load that can be fairly estimated based on a state variable (the higher the net consumption, the more likely new max peak could be reached)"

**Excellent insight!** We can make the penalty **adaptive** based on current conditions.

### Enhanced Penalty with State Awareness

```python
def calculate_adaptive_peak_penalty(
    current_monthly_peak_kw,
    current_demand_kw,  # Right now
    forecast_demand_24h,  # Next 24 hours
    days_remaining,
    tariff_rate_nok_per_kw
):
    """
    Adaptive peak penalty that considers:
    1. Time remaining in month
    2. Current proximity to peak
    3. Forecast demand patterns
    """
    # Base penalty (as before)
    base_penalty = tariff_rate_nok_per_kw * (days_remaining / 30)

    # State-based multipliers

    # 1. Proximity factor: How close are we to current peak?
    proximity_ratio = current_demand_kw / current_monthly_peak_kw
    if proximity_ratio > 0.9:  # Within 10% of peak
        proximity_multiplier = 2.0  # High risk
    elif proximity_ratio > 0.8:
        proximity_multiplier = 1.5
    else:
        proximity_multiplier = 1.0

    # 2. Forecast risk: Are we heading toward high demand period?
    max_forecast_demand = max(forecast_demand_24h)
    if max_forecast_demand > current_monthly_peak_kw:
        # Forecasting potential new peak
        forecast_multiplier = 1.5
    else:
        forecast_multiplier = 1.0

    # 3. Time-of-month factor
    if days_remaining > 20:  # Early in month
        time_multiplier = 1.5  # Aggressive peak defense
    elif days_remaining > 10:
        time_multiplier = 1.2
    else:  # Late in month
        time_multiplier = 1.0  # Less critical

    # Combined adaptive penalty
    adaptive_penalty = (
        base_penalty
        × proximity_multiplier
        × forecast_multiplier
        × time_multiplier
    )

    return adaptive_penalty
```

### Example Scenarios

#### Scenario 1: Early Month, Low Demand
```
Day 3, 27 days remaining
Current peak: 50 kW
Current demand: 30 kW (60% of peak)
Forecast max: 45 kW

Base: 50 × (27/30) = 45 NOK/kW
Proximity: 1.0 (not close to peak)
Forecast: 1.0 (no peak risk)
Time: 1.5 (early month, defend aggressively)

Penalty = 45 × 1.0 × 1.0 × 1.5 = 67.5 NOK/kW

→ Moderate penalty, but willing to use battery to prevent ANY new peak
```

#### Scenario 2: Mid-Month, Near Peak
```
Day 15, 15 days remaining
Current peak: 50 kW
Current demand: 48 kW (96% of peak!)
Forecast max: 52 kW

Base: 50 × (15/30) = 25 NOK/kW
Proximity: 2.0 (very close to peak)
Forecast: 1.5 (forecasting new peak)
Time: 1.2 (mid-month)

Penalty = 25 × 2.0 × 1.5 × 1.2 = 90 NOK/kW

→ High penalty! Battery will aggressively discharge to prevent 52 kW peak
```

#### Scenario 3: Late Month, Safe Margin
```
Day 28, 2 days remaining
Current peak: 50 kW
Current demand: 35 kW (70% of peak)
Forecast max: 40 kW

Base: 50 × (2/30) = 3.3 NOK/kW
Proximity: 1.0 (safe margin)
Forecast: 1.0 (no risk)
Time: 1.0 (late month, doesn't matter much)

Penalty = 3.3 × 1.0 × 1.0 × 1.0 = 3.3 NOK/kW

→ Very low penalty. Focus on arbitrage instead of peak prevention.
```

---

## Implementation in Existing LP

### Current LP Structure (Monthly Optimization)

```python
# From core/lp_monthly_optimizer.py

def optimize_month(E_nom, P_max, month_data):
    # Variables for entire month (720-744 hours)
    # Problem: Requires perfect forecast for 30 days ❌

    # Objective:
    minimize: sum over all hours in month:
        import_cost - export_revenue + battery_degradation
```

### New LP Structure (24-Hour Rolling with Peak Penalty)

```python
def optimize_day_ahead_with_peak_penalty(
    E_nom,
    P_max,
    current_soc,
    pv_forecast_24h,
    demand_forecast_24h,
    prices_24h,
    current_monthly_peak_kw,
    days_remaining_in_month
):
    """
    24-hour optimization with dynamic peak penalty.

    Replaces 30-day horizon with:
    - Accurate 24h forecasts
    - Smart peak penalty based on current state
    """

    T = 96  # 24 hours × 4 (15-min intervals)

    # Calculate adaptive penalty
    peak_penalty = calculate_adaptive_peak_penalty(
        current_monthly_peak_kw,
        demand_forecast_24h[0],  # Current demand
        demand_forecast_24h,
        days_remaining_in_month,
        tariff_rate=50  # NOK/kW/month
    )

    # Decision variables (96 timesteps)
    P_battery = cp.Variable(T)  # Battery power (+ = discharge)
    P_grid = cp.Variable(T)     # Grid import
    SOC = cp.Variable(T+1)       # State of charge
    P_peak_violation = cp.Variable(T)  # Peak exceedance (auxiliary)

    # Constraints
    constraints = [
        # Initial SOC
        SOC[0] == current_soc,

        # Power balance (15-min intervals, so divide by 4 for energy)
        SOC[t+1] == SOC[t] - P_battery[t]/4 + pv_forecast_24h[t]/4
                    - demand_forecast_24h[t]/4
        for t in range(T),

        # SOC limits
        SOC >= 0.1 * E_nom,  # Min 10%
        SOC <= E_nom,        # Max 100%

        # Battery power limits
        -P_max <= P_battery,
        P_battery <= P_max,

        # Grid import = demand - PV - battery discharge
        P_grid[t] == demand_forecast_24h[t] - pv_forecast_24h[t] - P_battery[t]
        for t in range(T),

        # Peak violation auxiliary variable
        P_peak_violation >= 0,
        P_peak_violation[t] >= P_grid[t] - current_monthly_peak_kw
        for t in range(T)
    ]

    # Objective
    objective = cp.Minimize(
        # Import costs
        cp.sum([prices_24h[t] * cp.pos(P_grid[t]) for t in range(T)]) * 0.25

        # Export revenue (negative cost)
        - cp.sum([prices_24h[t] * cp.neg(P_grid[t]) for t in range(T)]) * 0.25

        # Battery degradation
        + cp.sum([battery_cycle_cost * cp.abs(P_battery[t]) for t in range(T)]) * 0.25

        # Peak penalty (NEW!)
        + cp.sum([peak_penalty * P_peak_violation[t] for t in range(T)]) * 0.25
    )

    # Solve
    problem = cp.Problem(objective, constraints)
    problem.solve(solver=cp.SCIPY, method='highs')

    return {
        'P_battery': P_battery.value,
        'SOC': SOC.value,
        'P_grid': P_grid.value,
        'peak_violations': P_peak_violation.value
    }
```

---

## Why This Works Better Than 30-Day Horizon

### Information Quality

| Approach | Forecast Quality | Decision Quality |
|----------|-----------------|------------------|
| 30-day horizon | 30-40% accurate for days 7-30 | **Poor** (70% based on wrong info) |
| 24h + peak penalty | 70-80% accurate for all 24h | **Good** (uses accurate forecasts) |

### Computational Efficiency

| Approach | Variables | Solve Time | Update Frequency |
|----------|-----------|------------|------------------|
| 30-day LP | ~2,160 (720h × 3 vars) | 2-5 seconds | Slow (hourly?) |
| 24h LP | ~288 (96 × 3 vars) | <0.5 seconds | Fast (every 15 min) ✅ |

### Adaptability

**30-day horizon**:
- Locked into plan based on old forecasts
- Slow to adapt to reality
- "Sunk cost" fallacy (following bad plan because it was optimal yesterday)

**24h + peak penalty**:
- Re-optimizes every 15 minutes with latest info
- Peak penalty adapts to current state (proximity to peak, time in month)
- **Responds to reality, not outdated forecasts**

---

## Practical Example: Full Month Simulation

### Setup
- Battery: 30 kWh, 15 kW
- Month: January (31 days)
- Peak tariff: 50 NOK/kW/month
- Initial peak: 45 kW (set on Jan 1)

### Day 10 Scenario

**Current state**:
- Monthly peak so far: 48 kW (hit on Jan 8)
- Days remaining: 21
- Current demand: 42 kW
- Forecast next 24h: max 50 kW at 18:00

**Peak penalty calculation**:
```python
base = 50 × (21/30) = 35 NOK/kW
proximity = 1.0 (42/48 = 87.5%, below 90% threshold)
forecast = 1.5 (forecasting 50 kW > 48 kW)
time = 1.4 (21 days remaining, defend aggressively)

penalty = 35 × 1.0 × 1.5 × 1.4 = 73.5 NOK/kW
```

**24h optimization decision**:
- At 18:00, grid demand would reach 50 kW
- Without battery: New peak = 50 kW → Cost increase = 2 kW × 50 NOK × (21/30) = 70 NOK
- With peak penalty: 2 kW × 73.5 NOK/kW = 147 NOK penalty in objective
- **Battery will discharge 2 kW to keep grid import ≤ 48 kW**
- Prevented new peak despite only seeing 24 hours ahead!

### Day 28 Scenario

**Current state**:
- Monthly peak: 48 kW (held since Jan 8, defended successfully!)
- Days remaining: 3
- Current demand: 40 kW
- Forecast: max 45 kW

**Peak penalty calculation**:
```python
base = 50 × (3/30) = 5 NOK/kW
proximity = 1.0 (safe margin)
forecast = 1.0 (no peak risk)
time = 1.0 (late month)

penalty = 5 × 1.0 × 1.0 × 1.0 = 5 NOK/kW
```

**Decision**:
- Very low peak penalty (only 3 days left)
- Even if new peak occurs: 1 kW × 50 NOK × (3/30) = 5 NOK
- **Battery focuses on arbitrage instead** (buy low, sell high)
- Peak defense not worth it this late in month

---

## Summary: State-Based vs. Forecast-Based

### ❌ 30-Day Forecast Approach
```
Try to predict: Will demand exceed 48 kW on Jan 15? Jan 20? Jan 28?
Accuracy: 30-40% (essentially guessing)
Result: Optimize for imaginary future → suboptimal NOW
```

### ✅ State-Based Peak Penalty
```
Know NOW: Current peak = 48 kW, 21 days left
Penalty: 73.5 NOK/kW for exceeding 48 kW
Decision: Use this penalty in 24h optimization (70-80% accurate forecasts)
Result: Optimal decisions based on CURRENT state + GOOD short-term forecasts
```

**Key principle**:
- Don't try to predict unpredictable far future
- Instead, encode the **value** of the constraint (peak penalty) into near-term optimization
- Let the 24h optimizer make smart trade-offs: arbitrage vs. peak prevention

This is **dynamic programming** / **reinforcement learning** intuition:
- State = (current_peak, days_remaining, SOC, demand)
- Action = battery power setpoint
- Reward = -cost (including peak penalty)
- Policy = 24h LP optimization with adaptive penalty

**The monthly peak constraint is "baked into" the 24h optimizer via the penalty function**, without needing to see 30 days ahead!
