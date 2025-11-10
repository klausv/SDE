# Real Data Usage Guide

Comprehensive guide for using real-world data with the battery optimization system.

## Table of Contents

- [Overview](#overview)
- [Data Requirements](#data-requirements)
- [CSV Format Specifications](#csv-format-specifications)
- [Timezone Handling](#timezone-handling)
- [Data Preparation Workflow](#data-preparation-workflow)
- [Common Issues & Solutions](#common-issues--solutions)
- [Examples](#examples)

---

## Overview

The battery optimization system requires three types of time-series data:

1. **Electricity Prices** - Hourly spot prices (NOK/kWh)
2. **PV Production** - Solar generation profiles (kW)
3. **Consumption** - Load profiles (kW)

All data sources are automatically aligned to a common time grid, handling timezone differences, DST transitions, and different time resolutions.

---

## Data Requirements

### Minimum Requirements

| Data Type | Resolution | Coverage | Format |
|-----------|-----------|----------|---------|
| Prices | Hourly (PT60M) | ≥7 days | CSV with timestamp + price |
| Production | Hourly (PT60M) | ≥7 days | CSV with timestamp + power |
| Consumption | Hourly (PT60M) | ≥7 days | CSV with timestamp + power |

### Recommended for Analysis

- **Full month** (720 hours) for meaningful economic analysis
- **Full year** (8760 hours) for seasonal patterns and annual projections
- **Leap years** are automatically handled (2024 has 8783 hours due to DST)

---

## CSV Format Specifications

### 1. Electricity Prices

**File**: `data/spot_prices/NO2_2024_60min_real.csv`

```csv
cet_cest_timestamp,NOK/MWh
2024-01-01 00:00:00+01:00,895.23
2024-01-01 01:00:00+01:00,876.45
2024-01-01 02:00:00+01:00,862.11
...
```

**Requirements**:
- First column: Timestamp (any timezone accepted)
- Second column: Price (NOK/MWh will be converted to NOK/kWh)
- Timezone info optional (system converts to `Europe/Oslo` then naive)
- **Negative prices are valid** (surplus production scenarios)

**System Handling**:
- ✅ Converts any timezone to `Europe/Oslo` → naive
- ✅ Removes DST duplicate hours (fall transition)
- ✅ Handles missing hour during spring DST transition
- ✅ Converts MWh to kWh automatically

### 2. PV Production

**File**: `data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv`

```csv
time,P
20200101:0011,0.0
20200101:0111,0.0
20200101:0211,0.0
...
```

**Requirements**:
- First column: Timestamp (YYYYMMDD:HHMM format or ISO 8601)
- Second column: Power (kW)
- **Representative year data** (e.g., 2020) is automatically mapped to simulation year (2024)
- **Minute offsets** (e.g., `:11`) are resampled to `:00`

**PVGIS-Specific Handling**:
- ✅ Maps representative year (2020) → simulation year (2024)
- ✅ Removes `:11` minute offset via hourly resampling
- ✅ Preserves total energy during resampling
- ✅ Maintains seasonal patterns after year mapping

### 3. Consumption

**File**: `data/consumption/commercial_2024.csv`

```csv
timestamp,consumption_kw
2024-01-01 00:00:00,32.5
2024-01-01 01:00:00,28.3
2024-01-01 02:00:00,25.7
...
```

**Requirements**:
- First column: Timestamp
- Second column: Load (kW)
- Always positive values (no negative consumption)
- Should have realistic base load (>0 kW at all times)

**System Handling**:
- ✅ Validates consumption is always positive
- ✅ Checks for unrealistic patterns (e.g., extended zero consumption)
- ✅ Aligns with other data sources

---

## Timezone Handling

### The Problem

Real-world data comes with timezone complexity:
- Price data: `2024-03-31 02:00:00+01:00` (CET)
- During DST: `2024-03-31 03:00:00+02:00` (CEST)
- Fall DST: Creates duplicate `02:00:00` hour
- Spring DST: Skips `02:00:00` hour entirely

### The Solution (Automatic)

The system applies a **two-step conversion**:

```python
# Step 1: Convert to UTC
df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)

# Step 2: Convert to Europe/Oslo, then remove timezone info
df.index = df.index.tz_convert('Europe/Oslo').tz_localize(None)

# Step 3: Remove DST duplicates
df = df[~df.index.duplicated(keep='first')]
```

**Result**: Timezone-naive local timestamps (Europe/Oslo) with DST handled correctly.

### DST Transitions Explained

| Transition | Date | What Happens | System Handling |
|------------|------|--------------|-----------------|
| Spring (forward) | March 31, 2024 02:00 → 03:00 | Hour 02:00 missing | Accepts 23-hour day |
| Fall (backward) | October 27, 2024 03:00 → 02:00 | Hour 02:00 duplicated | Keeps first occurrence |

**2024 Specifics**:
- Leap year: 366 days = 8784 hours
- Spring DST: -1 hour = 8783 hours total
- Tests verify: `len(timestamps_2024) ≈ 8783`

---

## Data Preparation Workflow

### Step 1: Prepare CSV Files

Place files in appropriate directories:

```
data/
├── spot_prices/
│   └── NO2_2024_60min_real.csv
├── pv_profiles/
│   └── pvgis_58.97_5.73_138.55kWp.csv
└── consumption/
    └── commercial_2024.csv
```

### Step 2: Verify Format

Quick checks before running:

```python
import pandas as pd

# Check price data
df_price = pd.read_csv('data/spot_prices/NO2_2024_60min_real.csv')
print(f"Price data: {len(df_price)} rows")
print(f"Columns: {df_price.columns.tolist()}")
print(f"Date range: {df_price.iloc[0, 0]} to {df_price.iloc[-1, 0]}")

# Check for negative prices (valid for spot markets)
prices = df_price.iloc[:, 1]
print(f"Price range: {prices.min():.2f} to {prices.max():.2f} NOK/MWh")
print(f"Negative prices: {(prices < 0).sum()} hours ({(prices < 0).sum()/len(prices)*100:.1f}%)")
```

### Step 3: Run with Config File

Create/update `configs/working_config.yaml`:

```yaml
simulation_period:
  start_date: "2024-06-01"
  end_date: "2024-06-30"
  resolution: "PT60M"

data_sources:
  price_file: "data/spot_prices/NO2_2024_60min_real.csv"
  production_file: "data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv"
  consumption_file: "data/consumption/commercial_2024.csv"

battery:
  capacity_kwh: 80
  power_kw: 60
  initial_soc_percent: 50
  min_soc_percent: 10
  max_soc_percent: 90
```

### Step 4: Run Simulation

```python
from src.simulation.battery_simulation import BatterySimulation

# Load and run
sim = BatterySimulation.from_config('configs/working_config.yaml')
results = sim.run()

# Check results
print(f"Simulation completed: {len(results.trajectory)} timesteps")
print(f"Final SOC: {results.trajectory['soc_percent'].iloc[-1]:.1f}%")
```

---

## Common Issues & Solutions

### Issue 1: Timezone Conversion Error

**Error**: `ValueError: Tz-aware datetime.datetime cannot be converted to datetime64 unless utc=True`

**Cause**: Price CSV has timezone info but pandas operations expect naive timestamps.

**Solution**: Automatic! The system converts:
```python
# CET/CEST → UTC → Europe/Oslo → naive
df.index = df.index.tz_convert('Europe/Oslo').tz_localize(None)
```

**Verify Fix**:
```python
from src.data.file_loaders import load_price_data
timestamps, prices = load_price_data('data/spot_prices/NO2_2024_60min_real.csv')
print(f"Timezone: {timestamps.tz}")  # Should print: None
```

### Issue 2: DST Duplicate Timestamps

**Error**: `ValueError: cannot reindex on an axis with duplicate labels`

**Cause**: Fall DST creates two `02:00:00` hours (CEST → CET transition).

**Solution**: Automatic! Duplicates removed during loading.

**Verify Fix**:
```python
timestamps, _ = load_price_data('data/spot_prices/NO2_2024_60min_real.csv')
duplicates = timestamps[timestamps.duplicated()]
print(f"Duplicates: {len(duplicates)}")  # Should be 0
```

### Issue 3: PVGIS Minute Offset

**Error**: Timestamps don't align between price and production data.

**Cause**: PVGIS data has `:11` minute offset (`01:11`, `02:11`, etc.).

**Solution**: Automatic resampling to `:00` minutes.

**Verify Fix**:
```python
from src.data.file_loaders import load_production_data
timestamps, production = load_production_data('data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv')
unique_minutes = timestamps.minute.unique()
print(f"Minutes: {unique_minutes}")  # Should be [0]
```

### Issue 4: Year Mismatch

**Error**: No overlapping data when aligning sources.

**Cause**: PVGIS uses representative year (2020) but simulation is for 2024.

**Solution**: Automatic year mapping preserves month/day/hour.

**Verify Fix**:
```python
timestamps, _ = load_production_data('data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv')
print(f"Year: {timestamps[0].year}")  # Should be 2024
```

### Issue 5: Negative Prices Rejected

**Error**: `AssertionError: Found negative prices`

**Cause**: Using old validation code that didn't allow negative prices.

**Solution**: System now accepts negative prices (realistic for surplus scenarios).

**Valid Range**:
- Minimum: -2.0 NOK/kWh (rare but possible)
- Maximum: 10.0 NOK/kWh (high but plausible)
- Typical: 0.5-2.0 NOK/kWh

### Issue 6: Missing Data After Alignment

**Symptom**: `len(common_timestamps) == 0` after alignment.

**Causes**:
1. No overlapping date ranges between files
2. Different time resolutions that don't align
3. One file has only NaN values

**Solution**:
```python
from src.data.file_loaders import load_price_data, load_production_data, align_timeseries

# Load each source separately to check ranges
timestamps_price, prices = load_price_data('data/spot_prices/...')
timestamps_prod, production = load_production_data('data/pv_profiles/...')

print(f"Price range: {timestamps_price[0]} to {timestamps_price[-1]}")
print(f"Production range: {timestamps_prod[0]} to {timestamps_prod[-1]}")

# Find overlap
overlap_start = max(timestamps_price[0], timestamps_prod[0])
overlap_end = min(timestamps_price[-1], timestamps_prod[-1])
print(f"Overlap: {overlap_start} to {overlap_end}")
```

---

## Examples

### Example 1: Load and Inspect Real Data

```python
from src.data.file_loaders import load_price_data, load_production_data, load_consumption_data
import pandas as pd
import numpy as np

# Load all three sources
timestamps_price, prices = load_price_data('data/spot_prices/NO2_2024_60min_real.csv')
timestamps_prod, production = load_production_data('data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv')
timestamps_cons, consumption = load_consumption_data('data/consumption/commercial_2024.csv')

# Inspect each source
print(f"Price data: {len(timestamps_price)} hours")
print(f"  Range: {timestamps_price[0]} to {timestamps_price[-1]}")
print(f"  Price range: {prices.min():.3f} to {prices.max():.3f} NOK/kWh")
print(f"  Negative hours: {(prices < 0).sum()}")

print(f"\nProduction data: {len(timestamps_prod)} hours")
print(f"  Range: {timestamps_prod[0]} to {timestamps_prod[-1]}")
print(f"  Peak production: {production.max():.1f} kW")
print(f"  Annual energy: {production.sum():.0f} kWh")

print(f"\nConsumption data: {len(timestamps_cons)} hours")
print(f"  Range: {timestamps_cons[0]} to {timestamps_cons[-1]}")
print(f"  Average load: {consumption.mean():.1f} kW")
print(f"  Base load: {consumption.min():.1f} kW")
```

### Example 2: Align and Filter Data

```python
from src.data.file_loaders import align_timeseries

# Align all three sources
common_timestamps, aligned_values = align_timeseries(
    [timestamps_price, timestamps_prod, timestamps_cons],
    [prices, production, consumption]
)

print(f"Aligned data: {len(common_timestamps)} hours")
print(f"Range: {common_timestamps[0]} to {common_timestamps[-1]}")

# Filter to specific month (June 2024)
mask = (common_timestamps >= '2024-06-01') & (common_timestamps < '2024-07-01')
june_timestamps = common_timestamps[mask]
june_prices = aligned_values[0][mask]
june_production = aligned_values[1][mask]
june_consumption = aligned_values[2][mask]

print(f"\nJune 2024: {len(june_timestamps)} hours")
print(f"Average price: {june_prices.mean():.3f} NOK/kWh")
print(f"Total production: {june_production.sum():.0f} kWh")
print(f"Total consumption: {june_consumption.sum():.0f} kWh")
```

### Example 3: Run Simulation with Real Data

```python
from src.simulation.battery_simulation import BatterySimulation

# Option A: File-based (YAML config)
sim = BatterySimulation.from_config('configs/working_config.yaml')
results = sim.run()

# Option B: DataFrame-based (after alignment)
df = pd.DataFrame({
    'price_nok_per_kwh': june_prices,
    'pv_production_kw': june_production,
    'consumption_kw': june_consumption
}, index=june_timestamps)

sim = BatterySimulation.from_dataframe(df, battery_kwh=80, battery_kw=60)
results = sim.run()

# Option C: Array-based (most flexible)
sim = BatterySimulation.from_arrays(
    timestamps=june_timestamps,
    prices=june_prices,
    production=june_production,
    consumption=june_consumption,
    battery_kwh=80,
    battery_kw=60
)
results = sim.run()

# Analyze results
trajectory = results.trajectory
print(f"Final SOC: {trajectory['soc_percent'].iloc[-1]:.1f}%")
print(f"Total charge: {trajectory['P_charge_kw'].sum():.0f} kWh")
print(f"Total discharge: {trajectory['P_discharge_kw'].sum():.0f} kWh")
print(f"Grid import: {trajectory['P_grid_import_kw'].sum():.0f} kWh")
print(f"Grid export: {trajectory['P_grid_export_kw'].sum():.0f} kWh")
```

### Example 4: Validate Data Quality

```python
# Check for common data issues
def validate_data_quality(timestamps, values, name):
    print(f"\n=== {name} Validation ===")

    # 1. Check for NaN values
    nan_count = np.sum(np.isnan(values))
    print(f"NaN values: {nan_count} ({nan_count/len(values)*100:.2f}%)")

    # 2. Check for infinite values
    inf_count = np.sum(np.isinf(values))
    print(f"Infinite values: {inf_count}")

    # 3. Check time resolution
    diffs = pd.Series(timestamps[1:]).reset_index(drop=True) - pd.Series(timestamps[:-1]).reset_index(drop=True)
    diff_hours = diffs.dt.total_seconds() / 3600
    most_common = diff_hours.mode()[0]
    print(f"Resolution: {most_common:.2f} hours (most common)")

    # 4. Check for gaps
    gaps = diff_hours[diff_hours > most_common * 1.5]
    print(f"Large gaps: {len(gaps)} (>{most_common*1.5:.1f} hours)")

    # 5. Check value range
    print(f"Value range: {values.min():.2f} to {values.max():.2f}")
    print(f"Mean: {values.mean():.2f}, Std: {values.std():.2f}")

    # 6. Check for duplicates
    dup_count = timestamps[timestamps.duplicated()].size
    print(f"Duplicate timestamps: {dup_count}")

    return nan_count == 0 and inf_count == 0 and dup_count == 0

# Validate all sources
valid_price = validate_data_quality(timestamps_price, prices, "Price Data")
valid_prod = validate_data_quality(timestamps_prod, production, "Production Data")
valid_cons = validate_data_quality(timestamps_cons, consumption, "Consumption Data")

if valid_price and valid_prod and valid_cons:
    print("\n✅ All data sources passed validation")
else:
    print("\n❌ Some data sources have quality issues")
```

---

## Best Practices

### Data Preparation

1. **Always use real data for final analysis** - Mock data passes tests but doesn't capture real-world complexity
2. **Validate data before simulation** - Check for NaN, Inf, duplicates, gaps
3. **Use full months or years** - Partial periods can give misleading economic results
4. **Keep original files** - Don't modify source data, let the system handle conversions

### Timezone Management

1. **Let the system handle timezones** - Don't pre-convert to naive timestamps
2. **Keep timezone info in CSVs** - The two-step conversion is robust
3. **Document your timezone** - Note if data is CET, UTC, or local time

### Testing with Real Data

1. **Run tests before production** - `python -m pytest tests/real_data/ -v`
2. **Check edge cases** - Verify DST transitions, leap years work correctly
3. **Validate alignment** - Ensure all sources have overlapping periods
4. **Test small periods first** - Use 1 week before running full year

### Performance

1. **Use caching for expensive operations** - PVGIS fetches, alignment
2. **Filter before simulation** - Don't load full year if analyzing one month
3. **Profile long simulations** - Check where time is spent

---

## Troubleshooting Decision Tree

```
Data won't load?
├─ Timezone error → Check CSV has timestamp in first column
├─ Duplicate error → Check for DST transitions, system should handle automatically
├─ Year mismatch → Check if PVGIS data is from different year (auto-mapped)
└─ File not found → Verify path in config matches actual file location

Simulation fails?
├─ No overlap after alignment → Check date ranges overlap between sources
├─ NaN in results → Check input data has no NaN values
├─ Battery state error → Check battery config has valid SOC bounds
└─ Optimizer error → Check that data has sufficient length (≥24 hours)

Results look wrong?
├─ SOC always 50% → Check that battery size is reasonable vs. load
├─ No charging → Check prices are realistic (not all same value)
├─ Grid export = 0 → Check grid_export_limit_kw is set correctly
└─ Very high costs → Check price units (should be NOK/kWh, not MWh)
```

---

## Getting Help

If you encounter issues not covered here:

1. **Check test results**: `python -m pytest tests/real_data/ -v` - Do the real data tests pass?
2. **Review quality reports**: `/tmp/phase4_spawn_quality_report.md` and `/tmp/phase4_chatgpt_code_review.md`
3. **Inspect intermediate data**: Print timestamps, prices, production at each stage
4. **Enable debug logging**: Set `logging.DEBUG` to see detailed processing steps

**Common fix**: 90% of real data issues are timezone or date range mismatches. Use the validation script in Example 4 to diagnose.
