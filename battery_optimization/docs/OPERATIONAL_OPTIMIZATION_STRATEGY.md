# Operational Optimization Strategy
## From Static Planning to Dynamic Real-Time Control

## Current State: Static Monthly Optimization
- **Horizon**: 1 month (720-744 hours)
- **Resolution**: 60 minutes
- **Inputs**: Deterministic historical data (2024 prices, PVGIS solar)
- **Purpose**: Battery sizing (investment decision)
- **Update frequency**: Never (static analysis)

## Proposed State: Rolling Horizon Optimization
- **Purpose**: Real-time battery dispatch
- **Challenge**: Uncertainty in PV production and demand
- **Strategy**: Frequent re-optimization with updated forecasts

---

## Uncertainty Sources

### 1. Solar PV Production Uncertainty
**Deterministic components** (highly predictable):
- Solar geometry (sun angle, day length) - **100% accurate**
- Seasonal variation - **>95% accurate**
- Time of day - **100% accurate**

**Stochastic components** (uncertain):
- Cloud cover - **dominant short-term uncertainty**
- Temperature effects on panel efficiency - **±5-10%**
- Soiling, snow, shading - **seasonal/irregular**

**Prediction accuracy vs. horizon**:
| Horizon | Accuracy | Method |
|---------|----------|---------|
| 5-15 min | 95-98% | Persistence (current = future) |
| 1 hour | 85-90% | Satellite imagery + persistence |
| 6 hours | 70-80% | Numerical weather prediction (NWP) |
| 24 hours | 60-75% | NWP models (ECMWF, GFS) |
| 48+ hours | 50-70% | NWP with increasing uncertainty |

### 2. Demand Uncertainty
**Deterministic components**:
- Daily cycle (morning/afternoon peaks) - **70-80% predictable**
- Weekly cycle (weekday vs weekend) - **80-90% predictable**
- Seasonal baseline - **85-95% predictable**
- Holiday calendar - **100% known**

**Stochastic components**:
- Process variations (industrial site) - **±10-20%**
- Temperature-dependent loads (HVAC) - **±15-25%**
- Occupancy variations - **±10-15%**

**Prediction accuracy vs. horizon**:
| Horizon | Accuracy | Method |
|---------|----------|---------|
| 5-15 min | 90-95% | Persistence + historical patterns |
| 1 hour | 85-90% | Time series (ARIMA, exponential smoothing) |
| 6 hours | 75-85% | ML models (LSTM, XGBoost) with weather |
| 24 hours | 70-80% | Day-ahead patterns + weather forecast |
| 48+ hours | 65-75% | Weekly patterns + temperature forecast |

### 3. Price Uncertainty
**For day-ahead market** (current case):
- **Known**: Prices published at 13:00 CET for next day
- **Uncertainty horizon**: 11-35 hours ahead (known when optimization runs)

**For intraday/balancing** (future enhancement):
- 5-minute to 1-hour ahead prices
- Higher volatility than day-ahead

---

## Optimization Horizon Trade-offs

### Key Principle: Horizon Length vs. Forecast Accuracy
```
Longer horizon → More future info → Better global optimization
Longer horizon → Lower forecast accuracy → Worse decisions

Shorter horizon → Less future info → Myopic decisions
Shorter horizon → Higher forecast accuracy → Better near-term execution
```

### Analysis of Different Horizons

#### 1. **1-month horizon** (current)
**Pros**:
- Captures full monthly power tariff cycle
- Optimizes seasonal storage patterns
- Good for sizing/planning

**Cons**:
- Forecast accuracy degrades severely beyond 48 hours
- Optimization based on incorrect assumptions 90% of time
- Not suitable for real-time operation

**Use case**: Battery sizing, investment analysis ✅ (current use)

---

#### 2. **24-hour (day-ahead) horizon**
**Pros**:
- Aligns with electricity market structure (day-ahead prices known at 13:00)
- PV forecast accuracy: 60-75% (acceptable)
- Demand forecast accuracy: 70-80% (acceptable)
- Captures daily price patterns
- Can optimize morning vs. evening peaks

**Cons**:
- Cannot optimize multi-day storage strategies
- Misses weekend→weekday power tariff opportunities
- Limited ability to pre-charge before weather events

**Computational cost**: 24 timesteps × 15-min = 96 variables
- Solve time: ~0.1-1 second (HiGHS LP)
- Feasible for **5-15 minute updates**

**Use case**: Day-ahead scheduling ✅ **RECOMMENDED PRIMARY**

---

#### 3. **48-72 hour horizon**
**Pros**:
- Captures weekend→Monday transition (power tariff optimization)
- Better multi-day storage strategies
- Can pre-position battery before forecast events
- PV forecast: 50-70% (degraded but usable)
- Demand forecast: 65-75%

**Cons**:
- Increased forecast uncertainty
- More complex optimization
- Diminishing returns beyond 48h

**Computational cost**: 72h × 4 (15-min) = 288 variables
- Solve time: ~0.5-3 seconds
- Feasible for **15-30 minute updates**

**Use case**: Weekly optimization with day-ahead refinement ✅ **RECOMMENDED SECONDARY**

---

#### 4. **6-hour horizon** (short-term)
**Pros**:
- High forecast accuracy (75-85% for both PV and demand)
- Very responsive to real-time conditions
- Can handle sudden cloud events

**Cons**:
- **CRITICAL FLAW**: Misses evening peak optimization
  - If optimizing at 10:00 with 6h horizon → only sees until 16:00
  - Evening peak (18:00-20:00) invisible → suboptimal charging decisions
- Cannot optimize daily tariff structure (peak 06:00-22:00)
- Myopic behavior (may discharge too early)

**Computational cost**: 6h × 4 = 24 variables
- Solve time: <0.1 second
- Feasible for **1-5 minute updates**

**Use case**: Real-time corrections only (NOT primary scheduler) ⚠️

---

#### 5. **1-hour horizon** (very short-term)
**Pros**:
- Highest forecast accuracy (85-90%)
- Extremely responsive

**Cons**:
- **FATAL FLAW**: Completely myopic
  - Cannot see price peaks 2-6 hours ahead
  - Will miss optimal charge timing
  - No awareness of daily tariff patterns
- Essentially reduced to reactive control

**Computational cost**: Minimal (4 variables for 15-min resolution)

**Use case**: Emergency overrides only ❌ **NOT RECOMMENDED for primary control**

---

## Recommended Multi-Horizon Strategy

### Hierarchical Control Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: Weekly Optimization (48-72h horizon)              │
│  - Update: Daily at 13:00 (after day-ahead prices released)│
│  - Purpose: Multi-day storage strategy, weekend planning    │
│  - Output: High-level SOC targets for next 3 days          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: Day-Ahead Optimization (24h horizon) ✅ PRIMARY   │
│  - Update: Every 15-30 minutes                             │
│  - Purpose: Detailed dispatch schedule                      │
│  - Input: Latest PV/demand forecasts + day-ahead prices    │
│  - Output: Charge/discharge setpoints for next 24h         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: Real-Time Correction (5-15min updates)            │
│  - Update: Every 5 minutes                                  │
│  - Purpose: React to forecast errors                        │
│  - Method: Adjust Layer 2 setpoints based on:              │
│    * Actual vs. forecast PV deviation                      │
│    * Actual vs. forecast demand deviation                  │
│    * Grid constraint violations                            │
│  - Constraint: Stay within ±20% of Layer 2 plan            │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Details

#### Layer 2: Day-Ahead Optimization (CORE)
```python
# Run every 15-30 minutes
def day_ahead_optimization():
    # 1. Fetch latest forecasts
    pv_forecast_24h = get_pv_forecast(horizon_hours=24)  # From weather service
    demand_forecast_24h = get_demand_forecast(horizon_hours=24)  # From ML model
    prices_24h = get_day_ahead_prices()  # Known from 13:00 CET

    # 2. Run 24-hour LP optimization
    result = optimize_battery_dispatch(
        horizon_hours=24,
        resolution_minutes=15,  # 96 timesteps
        pv_forecast=pv_forecast_24h,
        demand_forecast=demand_forecast_24h,
        prices=prices_24h,
        current_soc=get_current_battery_soc()
    )

    # 3. Extract next 15-minute action
    next_action = result['P_battery'][0]  # First timestep

    # 4. Send setpoint to battery controller
    set_battery_power(next_action)

    # 5. Log planned trajectory (for Layer 3 comparison)
    save_planned_trajectory(result['P_battery'], result['SOC'])
```

**Why 24-hour horizon is optimal**:
1. ✅ Sees full daily cycle (morning + evening peaks)
2. ✅ Aligns with electricity market (day-ahead prices)
3. ✅ Forecast accuracy acceptable (70-80%)
4. ✅ Fast computation (<1 second) → enables frequent updates
5. ✅ Can handle 15-minute updates without computational burden

**Why NOT shorter (6h)**:
- ❌ Misses evening peak when optimizing in morning
- ❌ Cannot optimize peak vs. off-peak tariffs effectively

**Why NOT longer (week/month)**:
- ❌ Forecast accuracy too poor beyond 48h
- ❌ Optimization based on wrong assumptions

---

## Forecast Requirements

### PV Forecast Service
**Recommended approach**: Hybrid model
1. **Clearsky model** (deterministic baseline)
   - Use PVGIS/PVLib for geometric component
   - Assumes clear sky → upper bound on production

2. **Cloud forecast** (stochastic component)
   - **Satellite nowcasting** (0-6h): Current cloud movement
   - **NWP models** (6-48h): ECMWF/GFS weather forecasts
   - **ML correction**: LSTM trained on historical forecast errors

**Data sources**:
- **Solcast API**: 30-min resolution PV forecasts (commercial)
- **Météo-France AROME**: 1h resolution, 42h horizon (free for Norway equivalent: MET Norway)
- **MET Norway API**: Free weather forecasts for Norway
- **Open-Meteo**: Free weather API with solar radiation forecasts

### Demand Forecast Model
**Recommended approach**: Time series + ML

1. **Baseline model** (captures deterministic patterns):
   ```python
   # Seasonal decomposition
   demand = trend + daily_cycle + weekly_cycle + holiday_effect
   ```

2. **ML refinement** (captures stochastic variations):
   - **Features**:
     - Time of day, day of week, month
     - Temperature forecast (from weather API)
     - Historical demand (lag features)
     - Holiday indicator
   - **Model**: XGBoost or LSTM
   - **Training**: 6-12 months historical data

3. **Persistence correction** (very short-term):
   - For next 15-30 min: use current demand + small adjustment

**Data requirements**:
- Historical demand data (15-min resolution, ≥6 months)
- Weather forecasts (temperature)
- Holiday calendar

---

## Update Frequency Recommendation

### Optimal: **15-minute updates**

**Rationale**:
1. **Matches electricity market resolution**: 15-min is Norwegian market standard
2. **Forecast improvement justifies re-optimization**:
   - New weather data available every 15-30 min
   - Actual measurements reveal forecast errors
3. **Computational feasibility**:
   - 24h horizon @ 15-min resolution = 96 variables
   - HiGHS solves in <1 second
   - Can run on edge device (Raspberry Pi, industrial PC)
4. **Battery response time**:
   - Batteries can adjust power within seconds
   - 15-min updates provide smooth control

**Implementation**:
```python
# Cron job: */15 * * * * (every 15 minutes)
while True:
    # 1. Measure current state
    current_soc = read_battery_soc()
    current_pv = read_pv_production()
    current_demand = read_building_demand()

    # 2. Update forecasts (only if new data available)
    if new_forecast_available():
        update_forecasts()

    # 3. Re-optimize
    optimal_setpoint = day_ahead_optimization()

    # 4. Execute
    set_battery_power(optimal_setpoint)

    # 5. Wait 15 minutes
    time.sleep(15 * 60)
```

---

## Handling the Monthly Power Tariff

**Challenge**: Power tariff based on **monthly peak demand**
- Current: Must optimize over full month to capture peak
- Proposed: 24h horizon cannot see next month's peak

**Solution: Peak Tracking with Penalty**

Instead of optimizing full month, track monthly peak in real-time:

```python
def day_ahead_optimization_with_peak_penalty():
    # 1. Get current monthly peak
    current_monthly_peak = get_month_peak_so_far()  # kW
    days_remaining = get_days_remaining_in_month()

    # 2. Estimate peak reduction value
    # If we can avoid new peak, save: (new_peak - old_peak) × tariff × remaining_days
    peak_penalty_per_kw = estimate_peak_cost(days_remaining)

    # 3. Add peak penalty to LP objective
    # Penalize grid import above current monthly peak
    for t in range(96):  # 24h horizon
        if P_grid[t] > current_monthly_peak:
            objective += peak_penalty_per_kw * (P_grid[t] - current_monthly_peak)

    # 4. Solve LP with modified objective
    result = solve_lp(objective)
```

**Effect**:
- 24h optimization now "aware" of monthly peak constraint
- Will avoid creating new monthly peak unless arbitrage value exceeds penalty
- No need to see full month ahead

---

## Computational Performance

### Current Implementation (Monthly)
- Variables: ~2,200 (744h × 3 vars/timestep)
- Solve time: 2-5 seconds per month × 12 months = **24-60 seconds per battery config**
- Grid search (36 configs): **14-36 minutes** (sequential)
- With 12 CPU parallelization: **~2-3 minutes** ✅

### Proposed Implementation (24h Rolling)
- Variables: ~96 (24h × 4 timesteps/h × 1 var)  [Much smaller!]
- Solve time: **<0.5 seconds** (typically 0.1-0.2s)
- Update frequency: Every 15 minutes
- Daily optimizations: 96 solves × 0.2s = **19 seconds/day** of computation
- **Easily runs on Raspberry Pi or industrial PC**

### Scalability
Even with 5-minute updates:
- 24h = 288 updates
- 288 × 0.2s = **58 seconds/day** of computation
- Still feasible for edge deployment

---

## Transition Plan: From Planning to Operations

### Phase 1: Current (Investment Analysis) ✅
- **Tool**: Monthly static optimization
- **Purpose**: Battery sizing
- **Status**: Complete

### Phase 2: Day-Ahead Scheduler (Next Step)
- **Horizon**: 24 hours
- **Update**: Every 15-30 minutes
- **Requirements**:
  1. PV forecast API integration (Solcast or MET Norway)
  2. Demand forecasting model (train on historical data)
  3. Real-time data acquisition (battery SOC, PV, demand)
  4. Control interface to battery system

### Phase 3: Real-Time Correction Layer
- **Horizon**: 5-15 minutes (Layer 3)
- **Purpose**: Handle forecast errors
- **Method**: Simple adjustment rules, not full re-optimization

### Phase 4: Market Integration
- **Intraday trading**: Sell excess arbitrage capacity
- **Balancing services**: Fast frequency response

---

## Summary: Recommended Configuration

| Parameter | Value | Justification |
|-----------|-------|---------------|
| **Primary horizon** | 24 hours | Optimal trade-off: sees daily cycle, good forecasts |
| **Update frequency** | 15 minutes | Matches market resolution, computationally feasible |
| **Time resolution** | 15 minutes | Standard for Norwegian electricity market |
| **Forecast method** | Hybrid (statistical + ML) | Deterministic patterns + stochastic correction |
| **Control architecture** | 3-layer (weekly/daily/real-time) | Captures multi-timescale effects |
| **Peak handling** | Dynamic penalty in objective | Avoids need for monthly horizon |

**Key insight**: Don't try to predict 30 days ahead. Instead:
1. Predict 24 hours ahead (where forecasts are good)
2. Re-optimize every 15 minutes (as new information arrives)
3. Use penalty functions to represent long-term constraints (monthly peak)

This approach is **standard in real-world battery systems** (Tesla, Sonnen, Fluence).
