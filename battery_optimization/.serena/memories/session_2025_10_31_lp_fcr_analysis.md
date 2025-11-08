# Session 2025-10-31: LP Optimization + FCR-N Market Analysis

## Major Work Completed

### 1. LP Battery Optimization Implementation
- **Main script**: `run_lp_with_real_data.py`
- **Optimizer**: `core/lp_monthly_optimizer.py` (12-month rolling horizon)
- **Solver**: HiGHS via scipy.optimize.linprog
- **Critical fix**: Export pricing corrected to spot + 0.04 NOK/kWh (Norwegian plusskunde)

### 2. Economic Model Correction
**File**: `core/economic_cost.py` lines 171-174

**BEFORE (WRONG)**:
```python
export_revenues[t] = grid_export_power[t] * FEED_IN_TARIFF * timestep_hours
```

**AFTER (CORRECT)**:
```python
total_price_export = spot_prices[t] + FEED_IN_TARIFF  # spot + 0.04
export_revenues[t] = grid_export_power[t] * total_price_export * timestep_hours
```

**Impact**: Reference case costs dropped from ~60k to ~24k NOK, making economics more realistic.

### 3. Results - 20 kWh / 10 kW Battery
```
Annual costs:
  Reference: 23,977 NOK (17,113 energy + 6,864 peak)
  With battery: 18,098 NOK (12,234 energy + 5,864 peak)
  Savings: 5,880 NOK/year (24.5%)

Break-even: 3,051 NOK/kWh
Market price: 5,000 NOK/kWh
Gap: 39% price reduction needed

Battery cycling: 396.2 cycles/year
```

### 4. Revenue Stream Breakdown
1. **Peak shaving**: 1,000 NOK/year (17.0%)
2. **Energy cost reduction**: 4,880 NOK/year (83.0%)
   - Arbitrage: ~3,929 NOK
   - Self-consumption: ~-229 NOK (negative!)
   - **Curtailment recovery**: ~5,656 NOK (LARGEST!)

### 5. Solar Power Value Analysis
**Without battery**:
- Average price: 0.731 NOK/kWh
- Curtailment: 5,532 kWh lost (4.3%)

**With battery**:
- Average price: 0.742 NOK/kWh (+1.5%)
- Curtailment: 0 kWh (eliminated!)

### 6. FCR-N Market Research (NO2 - Stavanger/Agder)
**From Statnett "Batteries in Nordic Reserve Markets" April 2025**:

**FCR-N Characteristics**:
- Symmetric product (up + down regulation)
- Minimum bid: 0.1 MW
- Activation: 63% within 60s, 95% within 3 min
- Endurance: 1 hour at 100% in each direction
- Power reservation: 34% extra required

**Pricing NO2 (current)**:
- Day-ahead market: 12-25 EUR/MW/hour (~138-289 NOK/MW/hour)
- Average: ~17.5 EUR/MW/hour (~201 NOK/MW/hour)
- Weekly market: 3.78-7.00 EUR/MW/hour (~43-80 NOK/MW/hour) - MUCH LOWER

**Potential income (20 kWh / 10 kW = 0.01 MW)**:
- Optimistic (D-1, 90% acceptance): 14,500 NOK/year
- Realistic (weekly market): 6,100 NOK/year
- Uncertain due to bid acceptance rate

**CRITICAL INSIGHTS**:
1. You DON'T get paid for all 8760 hours automatically
2. Only paid for hours where bid is accepted in capacity market
3. Additional payment if activated (energy market)
4. Weekly market prices are 70-80% lower than day-ahead

**Challenges for small batteries**:
- 20 kWh battery too small for 1-hour FCR-N requirement
- 34% power reservation conflicts with energy optimization
- Frequent activations increase degradation
- Complex control system required
- May need aggregator for market access

### 7. Repository Cleanup
**Removed** (22 files):
- 7 outdated plots (pre-export correction)
- 13 obsolete markdown reports
- 5 old data files (JSON/PKL)
- Duplicate reports and simulations

**Kept**:
- `lp_january_detail_20kWh_10kW.png`
- `lp_may_detail_20kWh_10kW.png`
- `lp_yearly_comprehensive_20kWh_10kW.png`
- All with corrected export economics

### 8. Git Commit
**Commit**: `4c30a03`
**Message**: "feat: implement LP-based battery optimization with HiGHS solver"
**Files changed**: 58 files, 31,615 insertions, 2,355 deletions
**Pushed to**: origin/master

## Key Technical Decisions

1. **Export pricing model**: Norwegian plusskunde gets spot + 0.04 NOK/kWh (not just 0.04)
2. **Curtailment is largest value**: 5,656 NOK/year from recovering lost PV
3. **LP over heuristics**: Deterministic optimization, no degradation modeling yet
4. **Commercial tariff**: <100 MWh/year category only (changes for >100 MWh)

## Outstanding Limitations

1. Battery degradation NOT included
2. Deterministic simulation (no uncertainty)
3. Power tariff only for <100 MWh/year commercial customers
4. FCR-N integration NOT implemented (research only)

## Next Steps Considerations

1. Implement battery degradation modeling
2. Test larger battery sizes (50-100 kWh)
3. Hybrid FCR-N + energy optimization strategy
4. Uncertainty analysis with price/production variations
5. Compare against 100 kWh battery results

## Important Battery Cost Context

Market batteries cost ~5,000 NOK/kWh, but analysis shows break-even at 3,051 NOK/kWh for 20 kWh battery. This means battery costs need to drop 39% to become economically viable for pure energy optimization strategy.

However, user noted that market batteries actually cost closer to 5,000 NOK/kWh (example: Skanbatt Lithium Heat rack battery 30-72 kWh from Hyttetorget), and the model analysis requires break-even cost of ~2,500 NOK/kWh to justify investment.

## Key User Corrections During Session

1. **Location**: Stavanger/Agder is in NO2, not NO3 (bidding zone)
2. **FCR-N payment model**: Questioned automatic payment for 8760 hours - correctly identified that you only get paid for accepted bids, not all hours
3. **Battery market price**: Real market batteries cost 5,000 NOK/kWh, requiring break-even around 2,500 NOK/kWh
