# Battery Optimization Analysis Summary
**Date**: 2025-10-30
**Location**: Stavanger, Norway (58.97°N, 5.73°E)
**System**: 150 kWp Solar PV + Battery Storage

---

## Executive Summary

Current heuristic battery strategy provides **minimal economic benefit** (1,185 NOK/year, 0.48% savings). Break-even battery cost is **458 NOK/kWh**, requiring **90.8% reduction** from current market prices (5,000 NOK/kWh) for economic viability.

**ROOT CAUSE**: Battery is idle 96.3% of the time and fails to exploit price arbitrage opportunities effectively.

---

## System Configuration

### Solar PV System
- **Capacity**: 138.55 kWp (installed), 150 kWp (nameplate)
- **Orientation**: 173° azimuth (south-facing), 30° tilt
- **System losses**: 14%
- **Annual production**: 127.3 MWh
- **Solar inverter**: 110 kW (oversizing ratio 1.36)
- **Grid export limit**: 77 kW (70% of inverter capacity)

### Battery System (Current Analysis)
- **Capacity**: 20 kWh (usable: 16 kWh with 10-90% SOC range)
- **Power**: 10 kW charge/discharge
- **Efficiency**: 90% roundtrip
- **Battery inverter**: 98% efficiency

### Load Profile
- **Annual consumption**: 300,000 kWh
- **Profile type**: Commercial office
- **Peak demand**: ~80 kW (winter), ~50 kW (summer)

---

## Economic Analysis Results

### Reference Case (No Battery)
| **Metric** | **Value** |
|------------|-----------|
| Total annual cost | 246,864 NOK |
| Energy charges | 216,137 NOK (87.5%) |
| Peak power charges | 30,727 NOK (12.5%) |
| Grid import | 221,851 kWh |
| Grid export | 38,421 kWh |

### Heuristic Strategy (20 kWh / 10 kW Battery)
| **Metric** | **Value** |
|------------|-----------|
| Total annual cost | 245,679 NOK |
| Energy charges | 215,024 NOK |
| Peak power charges | 30,655 NOK |
| **Annual savings** | **1,185 NOK (0.48%)** |
| Grid import | 221,054 kWh (-797 kWh) |
| Grid export | 37,550 kWh (-871 kWh) |

### Battery Performance Metrics
| **Metric** | **Value** |
|------------|-----------|
| Energy charged (AC) | 1,062 kWh/year |
| Energy discharged (AC) | 913 kWh/year |
| Roundtrip efficiency | 86.0% (apparent) |
| Equivalent cycles | 45.7 cycles/year |
| Operating time | 3.7% of hours |
| **Idle time** | **96.3% of hours** ⚠️ |

---

## Break-Even Analysis

### NPV Calculation (10-year lifetime, 5% discount rate)
| **Parameter** | **Value** |
|---------------|-----------|
| Annual savings | 1,185 NOK |
| Annuity factor (10 years, 5%) | 7.7217 |
| Present value of savings | 9,153 NOK |
| Battery capacity | 20 kWh |
| **Break-even cost** | **458 NOK/kWh** |

### Market Comparison
| **Scenario** | **Value** |
|--------------|-----------|
| Current market price | 5,000 NOK/kWh |
| Market battery cost (20 kWh) | 100,000 NOK |
| **Required price reduction** | **4,542 NOK/kWh (90.8%)** |
| NPV at market prices | -90,847 NOK |
| **Investment viability** | **NOT VIABLE** ❌ |

### Sensitivity Analysis
| **Lifetime** | **Discount Rate** | **Break-even (NOK/kWh)** |
|--------------|-------------------|--------------------------|
| 5 years | 5% | 257 |
| 10 years | 5% | **458** (base case) |
| 15 years | 5% | 609 |
| 20 years | 5% | 739 |
| 10 years | 3% | 506 |
| 10 years | 7% | 415 |
| 10 years | 10% | 364 |

---

## Root Cause Analysis: Why Is Performance So Poor?

### 1. Battery Utilization Problems ⚠️

**CRITICAL FINDING**: Battery operates only **3.7%** of the year
- **Charging**: 199 hours (2.3%)
- **Discharging**: 127 hours (1.4%)
- **Idle**: 8,458 hours (96.3%)

**State of Charge Statistics**:
- Average SOC: 12.26 kWh (61%)
- Hours at minimum SOC (2 kWh): 2,740 (31.2%)
- Hours at maximum SOC (18 kWh): 5,122 (58.3%)
- **Battery spends most time at extremes**, not cycling actively

### 2. Ineffective Price Arbitrage ⚠️

**Achieved Performance**:
- Average charging price: 0.584 NOK/kWh
- Average discharge price: 1.050 NOK/kWh
- **Price differential: 0.466 NOK/kWh**

**Optimal Potential**:
- Optimal charging price (bottom 25%): 0.240 NOK/kWh
- Optimal discharge price (top 25%): 0.972 NOK/kWh
- **Optimal differential: 0.732 NOK/kWh**
- **→ Missed opportunity: 57% improvement potential**

**Operation During Extreme Prices**:
- During **cheapest 10% of hours** (avg 0.064 NOK/kWh):
  - Battery charging only **3.2%** of the time ❌
- During **most expensive 10% of hours** (avg 1.310 NOK/kWh):
  - Battery discharging only **9.6%** of the time ❌

### 3. Zero Peak Shaving Benefits ⚠️

**All 12 months show 0.00 kW peak reduction**
- Monthly peaks range from 47-79 kW
- Battery never operates to reduce peak demand
- Missing power tariff optimization opportunity (~12.5% of costs)

### 4. Minimal Curtailment Prevention

- Export reduction: 871 kWh (2.3%)
- Small contribution to storing surplus solar

---

## PV Value Analysis

### Average Obtained Price of PV
| **Scenario** | **Self-Consumption** | **Avg PV Price** |
|--------------|---------------------|------------------|
| Reference (no battery) | 69.7% | 0.623 NOK/kWh |
| Heuristic (20 kWh) | 70.4% | 0.630 NOK/kWh |
| **Improvement** | **+0.7 pp** | **+0.007 NOK/kWh (+1.1%)** |

**PV Value Breakdown**:
- Self-consumed PV valued at: 0.843 NOK/kWh (spot + tariff + tax)
- Exported PV valued at: 0.040 NOK/kWh (feed-in tariff)
- Average spot price: 0.577 NOK/kWh
- **PV premium over spot**: 1.08x (due to avoided tariffs)

---

## Price Market Characteristics

### 2024 NO2 Price Statistics
| **Metric** | **Value** |
|------------|-----------|
| Mean price | 0.577 NOK/kWh |
| Standard deviation | 0.393 NOK/kWh |
| Coefficient of variation | 68.1% (high volatility) |
| Price range | 11.02 NOK/kWh |
| Minimum | -0.690 NOK/kWh |
| Maximum | 10.330 NOK/kWh |

**High price volatility suggests strong arbitrage potential**, but current strategy fails to exploit it.

---

## Norwegian Grid Tariff Structure (Lnett Commercial)

### Energy Tariff (Time-of-Use)
| **Period** | **Rate** |
|------------|----------|
| Day (06:00-22:00 weekdays) | 0.296 NOK/kWh |
| Night (22:00-06:00 + weekends) | 0.176 NOK/kWh |

### Consumption Tax (Seasonal)
| **Period** | **Rate** |
|------------|----------|
| Winter (Jan-Mar) | 0.0979 NOK/kWh |
| Summer (Apr-Sep) | 0.1693 NOK/kWh |
| Fall (Oct-Dec) | 0.1253 NOK/kWh |

### Power Tariff (Monthly Peak, Progressive Brackets)
| **Peak Power (kW)** | **Monthly Charge (NOK)** |
|---------------------|--------------------------|
| 0-2 | 136 |
| 2-5 | 232 |
| 5-10 | 372 |
| 10-15 | 572 |
| 15-20 | 772 |
| 20-25 | 972 |
| 25-50 | 1,772 |
| 50-75 | 2,572 |
| 75-100 | 3,372 |
| 100+ | 5,600 |

**Current system peaks**: 50-80 kW → 2,572-3,372 NOK/month

---

## Critical Limitations of Heuristic Strategy

### SimpleRule Strategy Logic
```python
# Current heuristic rules:
1. Charge on solar surplus (when production > consumption)
2. Charge at night (00:00-06:00) when prices < 0.3 quantile
3. Discharge when deficit AND prices > 0.8 quantile
```

### Why This Fails
1. **Fixed thresholds don't adapt** to actual price distribution
   - 0.3 quantile ≠ actually cheap prices
   - 0.8 quantile ≠ actually expensive prices

2. **No look-ahead capability**
   - Cannot anticipate upcoming cheap/expensive periods
   - Cannot plan charging/discharging cycles

3. **No peak tariff optimization**
   - Doesn't track or minimize monthly peaks
   - Missing 12.5% of cost reduction opportunity

4. **Conservative operation**
   - Battery stays idle most of the time
   - Underutilizes available capacity

---

## Recommended Path Forward

### Phase 1: Implement LP Optimization Model ⭐ **PRIORITY**

**Objective**: Maximize annual savings through perfect foresight optimization

**Model formulation**:
```
Minimize: Total_Cost = Energy_Cost + Peak_Cost

Subject to:
- Battery SOC dynamics (charge/discharge balance)
- Power limits (10 kW charge/discharge)
- SOC limits (10-90% of capacity)
- Monthly peak tracking
- Grid export limit (77 kW)
- Energy conservation

Decision variables:
- Battery charge/discharge power each hour
- Grid import/export power each hour
- Monthly peak power levels
```

**Expected benefits**:
- Optimal arbitrage: Buy at 0.24 NOK/kWh, sell at 0.97 NOK/kWh
- Peak shaving: Reduce monthly peaks by 5-10 kW
- Increased utilization: 20-30% active time vs current 3.7%
- **Estimated savings: 5,000-10,000 NOK/year** (4-8x improvement)

### Phase 2: Battery Sizing Optimization

**Current analysis**: 20 kWh @ 10 kW is undersized

**Recommended analysis**:
- Test range: 40-120 kWh capacity
- Test range: 20-60 kW power
- Find optimal size/cost trade-off
- Run LP optimization for each size

**Expected optimal**: 80-100 kWh @ 40-50 kW

### Phase 3: Advanced Strategies

1. **Predictive optimization** with forecasted prices
   - Rolling horizon optimization
   - Price prediction models
   - Update hourly based on latest forecasts

2. **Multi-objective optimization**
   - Balance arbitrage vs peak shaving
   - Include grid service revenues (if available)
   - Consider battery degradation explicitly

3. **Stochastic optimization**
   - Handle forecast uncertainty
   - Robust optimization approach
   - Risk-adjusted decision making

---

## Investment Viability Scenarios

### Scenario A: Current Heuristic Strategy
- Annual savings: 1,185 NOK
- Break-even cost: 458 NOK/kWh
- **Required market price reduction: 90.8%**
- **Viability: NOT VIABLE** ❌

### Scenario B: LP Optimization (Conservative)
- Estimated savings: 5,000 NOK/year (4.2x)
- Break-even cost: 1,930 NOK/kWh
- Required market price reduction: 61.4%
- **Viability: MARGINAL** ⚠️

### Scenario C: LP Optimization (Optimistic)
- Estimated savings: 10,000 NOK/year (8.4x)
- Break-even cost: 3,861 NOK/kWh
- Required market price reduction: 22.8%
- **Viability: APPROACHING** 📈

### Scenario D: Larger Battery (80 kWh) + LP
- Estimated savings: 15,000-20,000 NOK/year
- Break-even cost: 4,500-6,000 NOK/kWh
- **Viability: LIKELY VIABLE** ✅

---

## Conclusions

1. **Current heuristic strategy is ineffective**
   - Only 3.7% battery utilization
   - Missing 57% of arbitrage potential
   - Zero peak shaving benefit
   - Annual savings too low for economic viability

2. **Root cause: Strategy limitations**
   - No optimization or planning capability
   - Fixed thresholds don't match price patterns
   - Conservative operation leaves money on table

3. **Path to viability requires**:
   - ✅ **Implement LP optimization** (4-8x savings improvement)
   - ✅ **Increase battery size** to 80-100 kWh
   - ✅ Monitor battery market prices (need 20-60% reduction)
   - ✅ Consider additional revenue streams (grid services)

4. **Next steps**:
   - Develop LP optimization model (Korpås formulation)
   - Run optimization with perfect foresight
   - Perform battery sizing sensitivity analysis
   - Update economic viability assessment

---

## Technical Implementation Files

### Core Economic Model
- `core/economic_cost.py` - Cost function (Korpås Eq. 5)
- `core/pv_value_metrics.py` - PV value calculation
- `core/strategies.py` - Battery control strategies
- `core/simulator.py` - Annual simulation engine

### Analysis Scripts
- `calculate_breakeven.py` - NPV and break-even analysis
- `compare_heuristic.py` - Strategy comparison
- `diagnose_battery_strategy.py` - Root cause diagnostics
- `analyze_pv_value.py` - PV economics analysis

### Results
- `results/comparison_heuristic_3weeks.png` - Visual comparison
- `results/costs_3weeks_june.png` - Reference case costs
- `results/ANALYSIS_SUMMARY.md` - This document

---

**Document Version**: 1.0
**Last Updated**: 2025-10-30
**Author**: Battery Optimization Analysis System
