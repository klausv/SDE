# Resolution Comparison Script Migration Summary

**File**: `visualize_resolution_comparison.py`
**Migration Date**: 2025-11-10
**Status**: ✅ COMPLETED

## Migration Overview

Migrated from **MonthlyLPOptimizer** (single monthly optimization) to **RollingHorizonOptimizer** with **weekly sequential optimization** (52 weeks).

## Key Changes

### 1. Optimizer Architecture

**Before** (MonthlyLPOptimizer):
```python
optimizer = MonthlyLPOptimizer(config, resolution=resolution,
                               battery_kwh=battery_kwh, battery_kw=battery_kw)
result = optimizer.optimize_month(
    month_idx=10,
    pv_production=pv_vals,
    load_consumption=consumption_vals,
    spot_prices=price_vals,
    timestamps=timestamps,
    E_initial=battery_kwh * 0.5
)
```

**After** (RollingHorizonOptimizer):
```python
# Separate optimizer for each resolution
optimizer_60m = RollingHorizonOptimizer(
    config=config,
    battery_kwh=battery_kwh,
    battery_kw=battery_kw,
    horizon_hours=168  # Weekly optimization (7 days)
)

# Run 52 weekly optimizations sequentially
for week in range(52):
    t_start = week * weekly_timesteps
    t_end = min(t_start + weekly_timesteps, n_timesteps)

    result = optimizer.optimize_window(
        current_state=state,
        pv_production=pv_production[t_start:t_end],
        load_consumption=load[t_start:t_end],
        spot_prices=spot_prices[t_start:t_end],
        timestamps=timestamps[t_start:t_end],
        verbose=False
    )

    # Update state for next week
    state.update_from_measurement(
        timestamp=timestamps[t_end - 1],
        soc_kwh=result.E_battery_final,
        grid_import_power_kw=result.P_grid_import[-1]
    )
```

### 2. Data Handling

**Before**:
- 3-day sample (Oct 10-12) for fast testing
- Hourly resolution: 72 timesteps
- 15-minute resolution: 288 timesteps

**After**:
- Full year analysis (52 weeks)
- Hourly resolution: 8,736 timesteps (52 × 168)
- 15-minute resolution: 34,944 timesteps (52 × 672)

### 3. State Management

**Added**:
- BatterySystemState for tracking SOC, monthly peak, power tariff
- Month boundary detection with peak reset
- State carryover between weeks using `update_from_measurement()`

```python
# Initialize state
state = BatterySystemState(
    battery_capacity_kwh=battery_kwh,
    current_soc_kwh=0.5 * battery_kwh,
    current_monthly_peak_kw=0.0,
    month_start_date=timestamps[0].replace(day=1, hour=0, minute=0, second=0, microsecond=0),
    power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(config.tariff)
)

# Check for month boundary
current_month = timestamps[t_start].month
if current_month != prev_month:
    state._reset_monthly_peak(timestamps[t_start])
    print(f"  Week {week}: Month boundary {prev_month} → {current_month}, peak reset")
    prev_month = current_month
```

### 4. Data Loading

**Before**:
- Simple synthetic PV profile (parabolic)
- Random consumption pattern

**After**:
- Real PVGIS solar production data
- Realistic commercial load profile (300 MWh/year)
- ENTSOEPriceFetcher for spot prices at both resolutions

```python
def load_data_at_resolution(year=2024, resolution='PT60M'):
    # Real spot prices
    fetcher = ENTSOEPriceFetcher(resolution=resolution)
    prices_series = fetcher.fetch_prices(year=year, area='NO2', resolution=resolution)

    # Real solar production from PVGIS
    pvgis = PVGISProduction(
        lat=58.97, lon=5.73,
        pv_capacity_kwp=138.55,
        tilt=30.0, azimuth=173.0
    )
    pvgis_series = pvgis.fetch_hourly_production(year=year)

    # Realistic commercial load
    load = create_synthetic_load(timestamps, annual_kwh=300000)

    return timestamps, spot_prices, pv_production, load
```

### 5. Metrics Tracking

**New Metrics**:
- Weekly solve times (52 data points per resolution)
- Weekly costs breakdown (energy, power tariff, degradation)
- Annual aggregates with statistical analysis
- Solve time ratio (PT15M / PT60M)

```python
full_results = {
    'P_charge': [],
    'P_discharge': [],
    'P_grid_import': [],
    'P_grid_export': [],
    'E_battery': [],
    'P_curtail': [],
    'DP_cyc': [],
    'DP_total': [],
    'weekly_costs': [],
    'weekly_energy_costs': [],
    'weekly_power_costs': [],
    'weekly_degradation_costs': [],
    'weekly_solve_times': []  # NEW: Track computational performance
}
```

### 6. Visualization Enhancements

**Figure 1: Full Year Overview** (NEW)
- SOC comparison across full year (PT60M vs PT15M overlaid)
- Weekly solve times bar chart showing computational cost
- Weekly optimization costs trend

**Figure 2: Detailed 3-Day View** (Enhanced)
- Same 4×2 subplot layout as before
- Now uses real PVGIS data instead of synthetic
- Proper timestamp handling for both resolutions

**Figure 3: Comparison Summary Metrics** (NEW)
- Annual cost breakdown by category
- Total annual cost comparison with percentage difference
- Solve time comparison with speedup ratio annotation
- Comprehensive metrics table with:
  - Battery utilization (cycles)
  - Solar curtailment comparison
  - Computational performance statistics

### 7. Degradation Model Integration

**Added**:
- LFP degradation model with realistic parameters
- Calendar degradation: 28-year life
- Cyclic degradation: 5000 full-DOD cycles
- Per-timestep degradation tracking (DP_cyc, DP_total)

```python
config.battery.degradation = DegradationConfig(
    enabled=True,
    cycle_life_full_dod=5000,
    calendar_life_years=28.0
)
```

## Expected Performance Characteristics

### Computational Performance

| Resolution | Timesteps/Week | Expected Solve Time | Speedup Ratio |
|-----------|----------------|---------------------|---------------|
| PT60M     | 168            | ~0.05-0.15s         | 1.0× (baseline) |
| PT15M     | 672            | ~0.15-0.50s         | 3-4× slower |

**Reason**: PT15M has 4× more decision variables (672 vs 168 timesteps), leading to ~3-4× longer solve times.

### Optimization Quality

**Expected Differences**:
- Annual costs should differ by <5% between resolutions
- PT15M captures intra-hour price variations better
- PT15M may show slightly higher curtailment (better captures short-duration peaks)
- SOC patterns should be similar but PT15M shows more granular transitions

### Weekly Sequential Benefits

**Advantages over old monthly approach**:
1. **Consistent solve times**: Each week is 168-hour horizon (predictable)
2. **Better scalability**: 52 small problems instead of 12 large problems
3. **Realistic state carryover**: Proper SOC and peak tracking between weeks
4. **Month boundary handling**: Automatic peak reset on month transitions

## Output Files

The script generates 3 PNG files in `results/figures/`:

1. **resolution_comparison_overview_year2024.png**
   - Full year SOC comparison
   - Weekly solve times bar chart
   - Weekly costs trend

2. **resolution_comparison_detail_year2024.png**
   - 3-day detailed view (Oct 10-12)
   - 4×2 subplot comparison (SOC, battery power, grid power, curtailment)

3. **resolution_comparison_metrics_year2024.png**
   - Annual cost breakdown
   - Total cost comparison
   - Solve time comparison
   - Comprehensive metrics table

## Testing Recommendations

### Before Running

1. Ensure ENTSO-E API key is configured in `.env` file
2. Verify PVGIS data cache exists or can be fetched
3. Check that battery configuration is realistic (default: 100 kWh / 50 kW)

### Execution

```bash
# Navigate to project root
cd /mnt/c/Users/klaus/klauspython/SDE/battery_optimization

# Run comparison script
python scripts/visualization/visualize_resolution_comparison.py
```

**Expected Runtime**:
- PT60M: ~5-10 seconds (52 weeks @ ~0.1s each)
- PT15M: ~20-30 seconds (52 weeks @ ~0.4s each)
- Visualization: ~5-10 seconds
- **Total**: ~40-50 seconds

### Validation Checklist

- [ ] Both resolutions complete 52 weekly optimizations
- [ ] No optimization failures (all weeks succeed)
- [ ] Annual costs are reasonable (positive values)
- [ ] PT15M is 3-4× slower than PT60M
- [ ] Cost difference between resolutions is <5%
- [ ] SOC stays within bounds (0-100%)
- [ ] Month boundaries show peak resets (12 times)
- [ ] All 3 visualization files generated successfully

## Code Quality Improvements

1. **Removed dependencies on deprecated classes**:
   - ❌ `MonthlyLPOptimizer` (removed)
   - ❌ `upsample_hourly_to_15min()` (removed)
   - ✅ `RollingHorizonOptimizer` (new)
   - ✅ `BatterySystemState` (new)

2. **Better data handling**:
   - Real PVGIS data instead of synthetic profiles
   - Proper timezone handling for Oslo timestamps
   - Realistic commercial load patterns

3. **Enhanced error handling**:
   - Check optimization success for each week
   - Return None on failure with clear error message
   - Validate data lengths before visualization

4. **Improved modularity**:
   - Separate functions for data loading, optimization, visualization
   - Reusable `run_weekly_sequential_optimization()` function
   - Clean separation of concerns

## Backward Compatibility

**Breaking Changes**:
- Script no longer accepts 3-day samples (always runs full year)
- Output format changed (3 files instead of 1)
- Removed `prepare_data()` function (replaced with `load_data_at_resolution()`)
- Removed `run_optimization()` function (replaced with `run_weekly_sequential_optimization()`)

**Migration Path**:
- Old result files from MonthlyLPOptimizer are NOT compatible
- Need to re-run analysis to generate new results
- Old visualizations can be archived

## Known Limitations

1. **Fixed horizon**: Always 168 hours (7 days), not configurable
2. **Fixed battery size**: Default 100 kWh / 50 kW (configurable in main())
3. **Synthetic load**: Uses simple pattern, not real building data
4. **Single year**: Only analyzes 2024 (configurable)
5. **No sensitivity analysis**: Single battery configuration per run

## Future Enhancements

1. **Variable horizon**: Allow configurable optimization horizons (24h, 168h, 720h)
2. **Battery sizing sweep**: Compare multiple battery sizes in single run
3. **Real load data**: Integrate actual building consumption profiles
4. **Multi-year analysis**: Compare 2023, 2024, 2025 spot prices
5. **Uncertainty analysis**: Add price forecast uncertainty bands
6. **Parallel optimization**: Run PT60M and PT15M in parallel threads

## References

- **Original Script**: Legacy `visualize_resolution_comparison.py` (archived)
- **Reference Implementation**: `visualize_battery_management.py` (recently migrated)
- **Optimizer Documentation**: `core/rolling_horizon_optimizer.py`
- **State Management**: `src/operational/state_manager.py`

## Conclusion

The migration successfully replaces the outdated MonthlyLPOptimizer with the modern RollingHorizonOptimizer using weekly sequential optimization. The new implementation:

✅ Provides more realistic annual analysis (52 weeks vs 1 month)
✅ Tracks computational performance across resolutions
✅ Includes proper state management and degradation modeling
✅ Generates comprehensive comparison visualizations
✅ Maintains code quality and modularity

**Status**: Ready for production use and validation testing.
