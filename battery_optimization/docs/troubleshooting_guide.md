# Troubleshooting Guide

Comprehensive troubleshooting guide for common issues with the battery optimization system.

## Table of Contents

- [Quick Diagnostic Checklist](#quick-diagnostic-checklist)
- [Data Loading Issues](#data-loading-issues)
- [Simulation Failures](#simulation-failures)
- [Configuration Problems](#configuration-problems)
- [Performance Issues](#performance-issues)
- [Test Failures](#test-failures)
- [Environment Setup Issues](#environment-setup-issues)

---

## Quick Diagnostic Checklist

Before diving into specific issues, run this quick diagnostic:

```python
# Diagnostic script - run in IPython
import sys
import pandas as pd
import numpy as np
from pathlib import Path

print("="*60)
print("BATTERY OPTIMIZATION SYSTEM DIAGNOSTICS")
print("="*60)

# 1. Check Python version
print(f"\n1. Python version: {sys.version}")
assert sys.version_info >= (3, 8), "❌ Requires Python 3.8+"

# 2. Check key packages
try:
    import scipy
    print(f"2. scipy version: {scipy.__version__}")
except ImportError:
    print("❌ scipy not installed")

try:
    import pulp
    print(f"3. pulp version: {pulp.__version__}")
except ImportError:
    print("❌ pulp not installed")

# 4. Check data files exist
data_dir = Path("data")
files_to_check = [
    "spot_prices/NO2_2024_60min_real.csv",
    "pv_profiles/pvgis_58.97_5.73_138.55kWp.csv",
    "consumption/commercial_2024.csv",
]

print("\n4. Data files:")
for file_path in files_to_check:
    full_path = data_dir / file_path
    if full_path.exists():
        print(f"   ✅ {file_path}")
    else:
        print(f"   ❌ {file_path} - NOT FOUND")

# 5. Check config files
config_dir = Path("configs")
if (config_dir / "working_config.yaml").exists():
    print(f"\n5. Config: ✅ working_config.yaml found")
else:
    print(f"\n5. Config: ❌ working_config.yaml NOT FOUND")

# 6. Quick module import test
print("\n6. Module imports:")
try:
    from src.simulation.battery_simulation import BatterySimulation
    print("   ✅ BatterySimulation")
except ImportError as e:
    print(f"   ❌ BatterySimulation: {e}")

try:
    from src.data.file_loaders import load_price_data
    print("   ✅ file_loaders")
except ImportError as e:
    print(f"   ❌ file_loaders: {e}")

print("\n" + "="*60)
print("DIAGNOSTICS COMPLETE")
print("="*60)
```

---

## Data Loading Issues

### Issue 1: Timezone Conversion Error

**Symptoms**:
```
ValueError: Tz-aware datetime.datetime cannot be converted to datetime64 unless utc=True
```

**Cause**: Price CSV has timezone info (`+01:00` or `+02:00`) but pandas operations expect timezone-naive timestamps.

**Solution**: This should be handled automatically by the system. If you see this error:

```python
# Verify the fix is applied in file_loaders.py:
from src.data.file_loaders import load_price_data

timestamps, prices = load_price_data('data/spot_prices/NO2_2024_60min_real.csv')
print(f"Timezone: {timestamps.tz}")  # Should print: None

# If still failing, check file_loaders.py line ~40 has:
# df.index = df.index.tz_convert('Europe/Oslo').tz_localize(None)
```

**Manual Fix** (if automatic handling broken):
```python
import pandas as pd

df = pd.read_csv('data/spot_prices/NO2_2024_60min_real.csv')
df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0], utc=True)
df.set_index(df.columns[0], inplace=True)

# Two-step conversion: UTC → Europe/Oslo → naive
df.index = df.index.tz_convert('Europe/Oslo').tz_localize(None)

# Remove DST duplicates
df = df[~df.index.duplicated(keep='first')]
```

### Issue 2: DST Duplicate Timestamps

**Symptoms**:
```
ValueError: cannot reindex on an axis with duplicate labels
ValueError: Index contains duplicate entries, cannot reshape
```

**Cause**: Fall DST transition (October 27, 2024) creates two `02:00:00` hours when clocks go back.

**Check for duplicates**:
```python
from src.data.file_loaders import load_price_data

timestamps, prices = load_price_data('data/spot_prices/NO2_2024_60min_real.csv')

# Should be 0 after automatic handling
duplicates = timestamps[timestamps.duplicated()]
print(f"Duplicates found: {len(duplicates)}")

if len(duplicates) > 0:
    print("❌ DST duplicates not removed!")
    print(duplicates)
else:
    print("✅ No duplicates - DST handled correctly")
```

**Manual Fix**:
```python
# Remove duplicates (keep first occurrence)
df = df[~df.index.duplicated(keep='first')]
```

### Issue 3: PVGIS Minute Offset

**Symptoms**:
- Timestamps don't align between price and production data
- `ValueError: cannot reindex` when aligning time series
- PVGIS timestamps like `2020-01-01 01:11:00`, `2020-01-01 02:11:00`

**Cause**: PVGIS representative year data has `:11` minute offset.

**Verify Fix**:
```python
from src.data.file_loaders import load_production_data

timestamps, production = load_production_data('data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv')

# All minutes should be :00 after automatic resampling
unique_minutes = timestamps.minute.unique()
print(f"Unique minutes: {unique_minutes}")  # Should be [0]

if len(unique_minutes) == 1 and unique_minutes[0] == 0:
    print("✅ Minute offset corrected")
else:
    print("❌ Minute offset not handled")
```

**Manual Fix**:
```python
# Resample to hourly :00 minutes
df.index = pd.DatetimeIndex(timestamps)
df_hourly = df.resample('h').mean()
timestamps = pd.DatetimeIndex(df_hourly.index)
values = df_hourly.iloc[:, 0].values
```

### Issue 4: Year Mismatch

**Symptoms**:
- `len(common_timestamps) == 0` after alignment
- "No overlapping data" errors
- PVGIS data from 2020 but simulation is 2024

**Cause**: PVGIS provides representative year data (e.g., 2020) that needs mapping to simulation year (2024).

**Verify Year Mapping**:
```python
from src.data.file_loaders import load_production_data

timestamps, production = load_production_data('data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv')

print(f"Production data year: {timestamps[0].year}")  # Should be 2024
print(f"Date range: {timestamps[0]} to {timestamps[-1]}")

# Check seasonal pattern preserved
import pandas as pd
monthly_avg = pd.Series(production, index=timestamps).resample('ME').mean()
print(f"\nSeasonal pattern:")
print(f"  January avg: {monthly_avg[monthly_avg.index.month == 1].values[0]:.1f} kW")
print(f"  June avg: {monthly_avg[monthly_avg.index.month == 6].values[0]:.1f} kW")
print(f"  Ratio: {monthly_avg[monthly_avg.index.month == 6].values[0] / monthly_avg[monthly_avg.index.month == 1].values[0]:.1f}x")
```

**Manual Year Mapping**:
```python
import pandas as pd

# Shift years while preserving month/day/hour
target_year = 2024
if timestamps[0].year != target_year:
    year_diff = target_year - timestamps[0].year
    timestamps = timestamps + pd.DateOffset(years=year_diff)
```

### Issue 5: Negative Prices Rejected

**Symptoms**:
```
AssertionError: Found negative prices: min=-0.15
ValueError: Prices must be non-negative
```

**Cause**: Old validation code didn't allow negative prices, but they're realistic in spot markets with surplus production.

**Expected Behavior**: System should accept negative prices within reasonable bounds.

**Verify**:
```python
from src.data.file_loaders import load_price_data
import numpy as np

timestamps, prices = load_price_data('data/spot_prices/NO2_2024_60min_real.csv')

print(f"Price range: {prices.min():.3f} to {prices.max():.3f} NOK/kWh")
print(f"Negative prices: {(prices < 0).sum()} hours ({(prices < 0).sum()/len(prices)*100:.1f}%)")

# Valid ranges:
assert prices.min() > -2.0, "Extremely negative prices (< -2 NOK/kWh)"
assert prices.max() < 10.0, "Extremely high prices (> 10 NOK/kWh)"
positive_ratio = (prices > 0).sum() / len(prices)
assert positive_ratio > 0.80, f"Too many negative prices (only {positive_ratio:.1%} positive)"

print("✅ Price range is realistic")
```

### Issue 6: No Data After Alignment

**Symptoms**:
```
AssertionError: No common timestamps after alignment
ValueError: align_timeseries returned empty result
```

**Cause**: No overlapping date ranges between data sources.

**Diagnostic Script**:
```python
from src.data.file_loaders import load_price_data, load_production_data, load_consumption_data

# Load all sources
timestamps_price, prices = load_price_data('data/spot_prices/NO2_2024_60min_real.csv')
timestamps_prod, production = load_production_data('data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv')
timestamps_cons, consumption = load_consumption_data('data/consumption/commercial_2024.csv')

# Check individual ranges
print("Data Source Ranges:")
print(f"  Price:       {timestamps_price[0]} to {timestamps_price[-1]} ({len(timestamps_price)} hours)")
print(f"  Production:  {timestamps_prod[0]} to {timestamps_prod[-1]} ({len(timestamps_prod)} hours)")
print(f"  Consumption: {timestamps_cons[0]} to {timestamps_cons[-1]} ({len(timestamps_cons)} hours)")

# Find overlap
overlap_start = max(timestamps_price[0], timestamps_prod[0], timestamps_cons[0])
overlap_end = min(timestamps_price[-1], timestamps_prod[-1], timestamps_cons[-1])

print(f"\nOverlap: {overlap_start} to {overlap_end}")

if overlap_start > overlap_end:
    print("❌ NO OVERLAP - Data sources don't have common time period")
else:
    duration_days = (overlap_end - overlap_start).days
    print(f"✅ Overlap duration: {duration_days} days")
```

**Solutions**:
1. **Update simulation period** in config to match overlap
2. **Extend data sources** to cover required period
3. **Use subset** of available overlap for analysis

---

## Simulation Failures

### Issue 7: Battery State Initialization Error

**Symptoms**:
```
AttributeError: 'NoneType' object has no attribute 'month'
TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'
```

**Location**: `src/simulation/rolling_horizon_orchestrator.py` line ~70

**Cause**: `battery_state.month_start_date` not initialized before first optimization window.

**Verify Fix**:
```python
# Check orchestrator initialization
from src.simulation.rolling_horizon_orchestrator import RollingHorizonOrchestrator
from src.config.simulation_config import SimulationConfig

config = SimulationConfig.from_yaml('configs/working_config.yaml')
orchestrator = RollingHorizonOrchestrator(config)

# This should work without errors
data = orchestrator.data_manager.load_data()
print(f"✅ Data loaded: {len(data)} timesteps")
```

**Manual Fix** (if error persists):
```python
# In rolling_horizon_orchestrator.py, ensure battery_state initialization includes:

from datetime import datetime

start_datetime = data.timestamps[0].to_pydatetime()
self.battery_state = BatterySystemState(
    current_soc_kwh=initial_soc_kwh,
    battery_capacity_kwh=self.config.battery.capacity_kwh,
    month_start_date=start_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
    last_update=start_datetime,
)
```

### Issue 8: Optimizer Infeasibility

**Symptoms**:
```
PulpSolverError: Solution status: Infeasible
RuntimeError: Optimization failed - no feasible solution found
```

**Common Causes**:
1. **Battery constraints too tight** (min_soc > max_soc)
2. **Power limits impossible** (grid limits < consumption peak)
3. **Insufficient battery capacity** for required operation

**Diagnostic**:
```python
from src.config.simulation_config import SimulationConfig

config = SimulationConfig.from_yaml('configs/working_config.yaml')

# Check battery constraints
print("Battery Configuration:")
print(f"  Capacity: {config.battery.capacity_kwh} kWh")
print(f"  Power: {config.battery.power_kw} kW")
print(f"  SOC range: {config.battery.min_soc_percent}% to {config.battery.max_soc_percent}%")
print(f"  Usable capacity: {config.battery.capacity_kwh * (config.battery.max_soc_percent - config.battery.min_soc_percent) / 100:.1f} kWh")

# Check grid constraints
print("\nGrid Configuration:")
print(f"  Import limit: {config.solar_system.grid_import_limit_kw} kW")
print(f"  Export limit: {config.solar_system.grid_export_limit_kw} kW")

# Check against consumption peak
from src.data.file_loaders import load_consumption_data
timestamps, consumption = load_consumption_data(config.data_sources.consumption_file)
print(f"\nConsumption:")
print(f"  Peak: {consumption.max():.1f} kW")
print(f"  Average: {consumption.mean():.1f} kW")

if consumption.max() > config.solar_system.grid_import_limit_kw:
    print(f"⚠️  WARNING: Peak consumption ({consumption.max():.1f} kW) exceeds grid import limit ({config.solar_system.grid_import_limit_kw} kW)")
```

**Solutions**:
1. **Widen SOC range**: Change min_soc to 10%, max_soc to 90%
2. **Increase grid limits**: Set to at least peak consumption/production
3. **Increase battery capacity**: Ensure sufficient capacity for energy shifting

### Issue 9: Results Have NaN Values

**Symptoms**:
```
Warning: Results contain NaN values in trajectory
ValueError: cannot convert float NaN to integer
```

**Diagnostic**:
```python
from src.simulation.battery_simulation import BatterySimulation

sim = BatterySimulation.from_config('configs/working_config.yaml')
results = sim.run()

traj = results.trajectory

# Check for NaN
print("NaN Check:")
for col in traj.columns:
    nan_count = traj[col].isna().sum()
    if nan_count > 0:
        print(f"  ❌ {col}: {nan_count} NaN values")
    else:
        print(f"  ✅ {col}: no NaN")

# Check for Inf
print("\nInfinity Check:")
for col in traj.columns:
    if traj[col].dtype in ['float64', 'float32']:
        inf_count = np.isinf(traj[col]).sum()
        if inf_count > 0:
            print(f"  ❌ {col}: {inf_count} Inf values")
```

**Common Causes**:
1. **Input data has NaN** - Check source CSVs
2. **Division by zero** - Check battery capacity > 0
3. **Optimizer failure** - Check solver status in output

**Solution**:
```python
# Validate input data first
from src.data.file_loaders import load_price_data
import numpy as np

timestamps, prices = load_price_data('data/spot_prices/NO2_2024_60min_real.csv')

assert not np.any(np.isnan(prices)), "❌ Price data contains NaN"
assert not np.any(np.isinf(prices)), "❌ Price data contains Inf"
print("✅ Input data is clean")
```

---

## Configuration Problems

### Issue 10: Missing Config Attributes

**Symptoms**:
```
AttributeError: 'BatteryConfig' object has no attribute 'efficiency_roundtrip'
AttributeError: 'GridTariffConfig' object has no attribute 'get_power_cost'
```

**Cause**: Legacy adapter incomplete or config file missing required fields.

**Verify Required Attributes**:
```python
from src.config.simulation_config import SimulationConfig

config = SimulationConfig.from_yaml('configs/working_config.yaml')

# Check battery config
required_battery_attrs = [
    'capacity_kwh', 'power_kw', 'initial_soc_percent',
    'min_soc_percent', 'max_soc_percent', 'efficiency_roundtrip'
]

print("Battery Config:")
for attr in required_battery_attrs:
    if hasattr(config.battery, attr):
        print(f"  ✅ {attr}: {getattr(config.battery, attr)}")
    else:
        print(f"  ❌ {attr}: MISSING")

# Check grid tariff config
from src.config.legacy_config_adapter import create_legacy_config

legacy = create_legacy_config(config)

if hasattr(legacy.grid_tariff, 'get_power_cost'):
    print("✅ get_power_cost() method exists")
    test_cost = legacy.grid_tariff.get_power_cost(75.0)
    print(f"  Test: 75 kW peak → {test_cost:.2f} NOK/month")
else:
    print("❌ get_power_cost() method MISSING")
```

**Manual Fix**: Add missing attributes to config file or legacy adapter.

### Issue 11: Invalid YAML Syntax

**Symptoms**:
```
yaml.scanner.ScannerError: while scanning a simple key
yaml.parser.ParserError: while parsing a block mapping
```

**Common Mistakes**:
1. **Inconsistent indentation** (mixing spaces/tabs)
2. **Missing colons** after keys
3. **Unquoted special characters** in strings
4. **Invalid date format**

**Validation Script**:
```python
import yaml
from pathlib import Path

config_file = 'configs/working_config.yaml'

try:
    with open(config_file) as f:
        config = yaml.safe_load(f)
    print(f"✅ {config_file} is valid YAML")
    print(f"   Top-level keys: {list(config.keys())}")
except yaml.YAMLError as e:
    print(f"❌ YAML syntax error:")
    print(f"   {e}")
```

**Fix**: Use YAML linter or check indentation carefully (2 spaces per level).

---

## Performance Issues

### Issue 12: Slow Simulation

**Symptoms**:
- Simulation takes >5 minutes for single month
- CPU usage very high
- Memory usage growing

**Diagnostic**:
```python
import time
from src.simulation.battery_simulation import BatterySimulation

# Profile simulation
start = time.time()
sim = BatterySimulation.from_config('configs/working_config.yaml')
load_time = time.time() - start

start = time.time()
results = sim.run()
run_time = time.time() - start

print(f"Load time: {load_time:.2f} seconds")
print(f"Run time: {run_time:.2f} seconds")
print(f"Timesteps: {len(results.trajectory)}")
print(f"Time per timestep: {run_time / len(results.trajectory) * 1000:.1f} ms")

# Expected performance:
# - Load: <5 seconds for year of data
# - Run: 1-2 minutes for full year (8760 hours)
# - ~10 ms per timestep optimization
```

**Common Causes**:
1. **Too many optimization variables** - Reduce horizon length
2. **Inefficient solver** - Switch from CBC to HiGHS
3. **Data not aligned** - Excessive resampling operations

**Solutions**:
```python
# 1. Reduce optimization horizon (in config)
rolling_horizon:
  horizon_hours: 24      # Default - good balance
  # horizon_hours: 48    # Slower but better optimization

# 2. Check solver (should use HiGHS if scipy >= 1.9)
import scipy
print(f"scipy version: {scipy.__version__}")
if scipy.__version__ >= "1.9.0":
    print("✅ Can use HiGHS solver (fastest)")
else:
    print("⚠️  Using older solver - consider upgrading scipy")

# 3. Pre-align data to avoid repeated alignment
from src.data.file_loaders import align_timeseries, load_price_data, load_production_data, load_consumption_data

# Load once
timestamps_price, prices = load_price_data('...')
timestamps_prod, production = load_production_data('...')
timestamps_cons, consumption = load_consumption_data('...')

# Align once
common_timestamps, aligned_values = align_timeseries(
    [timestamps_price, timestamps_prod, timestamps_cons],
    [prices, production, consumption]
)

# Reuse for multiple simulations
import pandas as pd
df = pd.DataFrame({
    'price_nok_per_kwh': aligned_values[0],
    'pv_production_kw': aligned_values[1],
    'consumption_kw': aligned_values[2]
}, index=common_timestamps)

# Run multiple scenarios without re-aligning
for battery_size in [60, 80, 100]:
    sim = BatterySimulation.from_dataframe(df, battery_kwh=battery_size, battery_kw=battery_size*0.75)
    results = sim.run()
```

### Issue 13: Memory Errors

**Symptoms**:
```
MemoryError: Unable to allocate array
RuntimeError: Out of memory
```

**Diagnostic**:
```python
import psutil
import numpy as np

# Check system memory
mem = psutil.virtual_memory()
print(f"System Memory:")
print(f"  Total: {mem.total / 1e9:.1f} GB")
print(f"  Available: {mem.available / 1e9:.1f} GB")
print(f"  Used: {mem.percent:.1f}%")

# Estimate data size
hours = 8760  # Full year
bytes_per_hour = 8 * 10  # ~10 float64 values per timestep
estimated_mb = (hours * bytes_per_hour) / 1e6
print(f"\nEstimated data size for year: {estimated_mb:.1f} MB")
```

**Solutions**:
1. **Reduce simulation period** - Analyze smaller chunks
2. **Use float32 instead of float64** - Half memory usage
3. **Delete unused variables** - Free memory between runs

---

## Test Failures

### Issue 14: Tests Fail with Real Data

**Run Test Suite**:
```bash
# All fast tests (should complete in ~10 seconds)
python -m pytest tests/real_data/ -v -m "not slow"

# Specific test file
python -m pytest tests/real_data/test_data_loading.py -v

# Include slow tests (full integration tests)
python -m pytest tests/real_data/ -v
```

**Common Test Failures**:

#### A. Timezone Test Failure
```
AssertionError: Timestamps should be timezone-naive after processing
```
**Fix**: Verify `file_loaders.py` applies `.tz_localize(None)` after timezone conversion.

#### B. DST Test Failure
```
AssertionError: Expected 23 hours on DST spring day, got 24
```
**Fix**: Check that spring DST (March 31) correctly has 23 hours (02:00 missing).

#### C. Negative Price Test Failure
```
AssertionError: Found negative prices
```
**Fix**: Update test to allow negative prices within bounds (-2 to +10 NOK/kWh).

#### D. Integration Test Failure
```
AssertionError: Expected ≥600 timesteps for June, got 122
```
**Fix**: Check config simulation period matches test expectations (full June = ~720 hours).

### Issue 15: Import Errors in Tests

**Symptoms**:
```
ImportError: cannot import name 'BatteryConfig' from 'src.config.simulation_config'
ModuleNotFoundError: No module named 'src'
```

**Solutions**:
```bash
# 1. Run tests from project root
cd /mnt/c/Users/klaus/klauspython/SDE/battery_optimization
python -m pytest tests/real_data/ -v

# 2. Verify PYTHONPATH includes project root
export PYTHONPATH=/mnt/c/Users/klaus/klauspython/SDE/battery_optimization:$PYTHONPATH

# 3. Check conda environment active
conda activate battery_opt
which python  # Should point to battery_opt environment
```

---

## Environment Setup Issues

### Issue 16: Conda Environment Problems

**Symptoms**:
```
ModuleNotFoundError: No module named 'scipy'
ImportError: cannot import name 'linprog' from 'scipy.optimize'
```

**Recreate Environment**:
```bash
# Remove old environment
conda env remove -n battery_opt

# Create fresh environment
conda env create -f environment.yml

# Activate
conda activate battery_opt

# Verify packages
conda list | grep scipy
conda list | grep pulp
conda list | grep pandas

# Test imports
python -c "import scipy; import pulp; import pandas; print('✅ All packages imported')"
```

### Issue 17: Solver Not Found

**Symptoms**:
```
PulpSolverError: Pulp: Error while executing cmd
RuntimeError: No solver available
```

**Diagnostic**:
```python
import pulp

# Check available solvers
print("Available solvers:")
for solver in pulp.listSolvers(onlyAvailable=True):
    print(f"  ✅ {solver}")

# Try each solver
for solver_name in ['PULP_CBC_CMD', 'COIN_CMD', 'GLPK_CMD']:
    try:
        solver = pulp.getSolver(solver_name, msg=0)
        print(f"✅ {solver_name} works")
    except Exception as e:
        print(f"❌ {solver_name}: {e}")
```

**Solutions**:
```bash
# Install CBC solver
conda install -c conda-forge coincbc

# Or install GLPK
conda install -c conda-forge glpk

# Verify
python -c "from pulp import COIN_CMD; print('✅ CBC solver available')"
```

---

## Advanced Troubleshooting

### Enable Debug Logging

```python
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Run simulation with detailed logging
from src.simulation.battery_simulation import BatterySimulation

sim = BatterySimulation.from_config('configs/working_config.yaml')
results = sim.run()
```

### Validate Complete Pipeline

```python
# Complete validation script - tests entire pipeline
import sys
from pathlib import Path

def validate_pipeline():
    """Comprehensive pipeline validation."""

    print("="*60)
    print("BATTERY OPTIMIZATION PIPELINE VALIDATION")
    print("="*60)

    # 1. Environment
    print("\n1. ENVIRONMENT:")
    import scipy, pulp, pandas as pd, numpy as np
    print(f"   ✅ scipy {scipy.__version__}")
    print(f"   ✅ pulp {pulp.__version__}")
    print(f"   ✅ pandas {pd.__version__}")
    print(f"   ✅ numpy {np.__version__}")

    # 2. Data Loading
    print("\n2. DATA LOADING:")
    from src.data.file_loaders import load_price_data, load_production_data, load_consumption_data

    try:
        timestamps_price, prices = load_price_data('data/spot_prices/NO2_2024_60min_real.csv')
        print(f"   ✅ Prices: {len(timestamps_price)} hours")
    except Exception as e:
        print(f"   ❌ Prices: {e}")
        return False

    try:
        timestamps_prod, production = load_production_data('data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv')
        print(f"   ✅ Production: {len(timestamps_prod)} hours")
    except Exception as e:
        print(f"   ❌ Production: {e}")
        return False

    try:
        timestamps_cons, consumption = load_consumption_data('data/consumption/commercial_2024.csv')
        print(f"   ✅ Consumption: {len(timestamps_cons)} hours")
    except Exception as e:
        print(f"   ❌ Consumption: {e}")
        return False

    # 3. Data Alignment
    print("\n3. DATA ALIGNMENT:")
    from src.data.file_loaders import align_timeseries

    try:
        common_timestamps, aligned_values = align_timeseries(
            [timestamps_price, timestamps_prod, timestamps_cons],
            [prices, production, consumption]
        )
        print(f"   ✅ Aligned: {len(common_timestamps)} hours")
    except Exception as e:
        print(f"   ❌ Alignment: {e}")
        return False

    # 4. Configuration
    print("\n4. CONFIGURATION:")
    from src.config.simulation_config import SimulationConfig

    try:
        config = SimulationConfig.from_yaml('configs/working_config.yaml')
        print(f"   ✅ Config loaded")
        print(f"      Battery: {config.battery.capacity_kwh} kWh / {config.battery.power_kw} kW")
    except Exception as e:
        print(f"   ❌ Config: {e}")
        return False

    # 5. Simulation (small test)
    print("\n5. SIMULATION (1 week test):")
    from src.simulation.battery_simulation import BatterySimulation

    try:
        # Filter to 1 week for fast test
        mask = (common_timestamps >= '2024-06-01') & (common_timestamps < '2024-06-08')
        df_test = pd.DataFrame({
            'price_nok_per_kwh': aligned_values[0][mask],
            'pv_production_kw': aligned_values[1][mask],
            'consumption_kw': aligned_values[2][mask]
        }, index=common_timestamps[mask])

        sim = BatterySimulation.from_dataframe(df_test, battery_kwh=80, battery_kw=60)
        results = sim.run()
        print(f"   ✅ Simulation completed: {len(results.trajectory)} timesteps")
    except Exception as e:
        print(f"   ❌ Simulation: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 6. Results Validation
    print("\n6. RESULTS VALIDATION:")
    traj = results.trajectory
    required_cols = ['P_charge_kw', 'P_discharge_kw', 'soc_percent']

    for col in required_cols:
        if col in traj.columns:
            print(f"   ✅ {col} present")
        else:
            print(f"   ❌ {col} MISSING")
            return False

    # Check for NaN
    nan_count = traj.isna().sum().sum()
    if nan_count == 0:
        print(f"   ✅ No NaN values")
    else:
        print(f"   ❌ {nan_count} NaN values found")
        return False

    print("\n" + "="*60)
    print("✅ VALIDATION PASSED - SYSTEM OPERATIONAL")
    print("="*60)
    return True

# Run validation
if __name__ == "__main__":
    success = validate_pipeline()
    sys.exit(0 if success else 1)
```

---

## Getting Help

If issues persist after troubleshooting:

1. **Check documentation**:
   - Real Data Usage Guide (`docs/real_data_usage_guide.md`)
   - Pythonic API Guide (`docs/pythonic_api_guide.md`)

2. **Review quality reports**:
   - SuperClaude report: `/tmp/phase4_spawn_quality_report.md`
   - ChatGPT review: `/tmp/phase4_chatgpt_code_review.md`

3. **Run diagnostics**:
   - Quick diagnostic checklist (top of this guide)
   - Complete validation script (above)
   - Test suite: `python -m pytest tests/real_data/ -v`

4. **Check logs**:
   - Enable debug logging
   - Review error stack traces
   - Check solver output

5. **Verify environment**:
   - Conda environment correct
   - All packages installed
   - Solvers available

---

## Summary: Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| Timezone error | Automatic - verify `file_loaders.py` line ~40 |
| DST duplicates | Automatic - check no duplicates after loading |
| PVGIS offset | Automatic - verify all minutes are `:00` |
| Year mismatch | Automatic - check production year is 2024 |
| Negative prices | Valid - system accepts -2 to +10 NOK/kWh |
| No alignment | Check date ranges overlap |
| Battery state | Verify `month_start_date` initialized |
| Slow simulation | Reduce horizon, use HiGHS solver |
| Import errors | Run from project root, check PYTHONPATH |
| Test failures | Run `pytest tests/real_data/ -v` |

**90% of issues are data-related (timezone, DST, alignment) and should be handled automatically. If you see these errors, the automatic handling may be broken.**
