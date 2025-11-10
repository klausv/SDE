# Pythonic API Guide

Complete guide to using the battery optimization system in IPython with the new Pythonic API.

## Table of Contents

- [Overview](#overview)
- [Three Usage Patterns](#three-usage-patterns)
- [Pattern 1: File-Based (YAML + CSV)](#pattern-1-file-based-yaml--csv)
- [Pattern 2: DataFrame-Based](#pattern-2-dataframe-based)
- [Pattern 3: Array-Based](#pattern-3-array-based)
- [Advanced Usage](#advanced-usage)
- [API Reference](#api-reference)
- [Migration from Old API](#migration-from-old-api)

---

## Overview

The **Pythonic API** provides three flexible ways to run battery optimization simulations:

| Pattern | Best For | Input Type | Complexity |
|---------|----------|------------|------------|
| **File-Based** | Production runs, reproducible analysis | YAML + CSV files | Low |
| **DataFrame-Based** | Pandas workflows, data exploration | `pd.DataFrame` | Medium |
| **Array-Based** | NumPy workflows, custom data sources | `np.ndarray` | High |

All patterns use the same **`BatterySimulation`** facade class with different constructors:

```python
from src.simulation.battery_simulation import BatterySimulation

# Pattern 1: from_config()
sim = BatterySimulation.from_config('configs/working_config.yaml')

# Pattern 2: from_dataframe()
sim = BatterySimulation.from_dataframe(df, battery_kwh=80, battery_kw=60)

# Pattern 3: from_arrays()
sim = BatterySimulation.from_arrays(timestamps, prices, production, consumption, ...)

# All patterns use the same run() method
results = sim.run()
```

---

## Three Usage Patterns

### Quick Comparison

```python
# ═══════════════════════════════════════════════════════════
# Pattern 1: File-Based (Recommended for production)
# ═══════════════════════════════════════════════════════════

from src.simulation.battery_simulation import BatterySimulation

# Config file specifies everything
sim = BatterySimulation.from_config('configs/working_config.yaml')
results = sim.run()

# ✅ Pros: Reproducible, version-controlled, clear configuration
# ❌ Cons: Requires creating YAML file, less flexible for exploration


# ═══════════════════════════════════════════════════════════
# Pattern 2: DataFrame-Based (Best for IPython/Pandas users)
# ═══════════════════════════════════════════════════════════

import pandas as pd

# Load data into DataFrame
df = pd.read_csv('data/combined_data.csv', index_col=0, parse_dates=True)

# Create simulation directly from DataFrame
sim = BatterySimulation.from_dataframe(
    df,
    battery_kwh=80,
    battery_kw=60,
    price_col='price_nok_per_kwh',         # Optional: column names
    production_col='pv_production_kw',      # Default names work
    consumption_col='consumption_kw'
)
results = sim.run()

# ✅ Pros: Natural for pandas workflows, easy data manipulation
# ❌ Cons: Need to prepare DataFrame correctly


# ═══════════════════════════════════════════════════════════
# Pattern 3: Array-Based (Maximum flexibility)
# ═══════════════════════════════════════════════════════════

import numpy as np

# Create or load arrays directly
timestamps = pd.date_range('2024-06-01', periods=720, freq='h')
prices = np.random.uniform(0.5, 1.5, 720)
production = np.random.uniform(0, 100, 720)
consumption = np.random.uniform(20, 50, 720)

# Create simulation from arrays
sim = BatterySimulation.from_arrays(
    timestamps=timestamps,
    prices=prices,
    production=production,
    consumption=consumption,
    battery_kwh=80,
    battery_kw=60
)
results = sim.run()

# ✅ Pros: Maximum control, works with any data source
# ❌ Cons: More manual work, need to handle data preparation
```

---

## Pattern 1: File-Based (YAML + CSV)

### Use Case

- **Production runs** with reproducible configurations
- **Version-controlled** analysis (config files in git)
- **Batch processing** multiple scenarios
- **Sharing work** with collaborators

### Quick Start

**Step 1**: Create config file `configs/my_analysis.yaml`

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
  efficiency_roundtrip: 0.90

solar_system:
  capacity_kwp: 138.55
  grid_import_limit_kw: 77
  grid_export_limit_kw: 77

grid_tariff:
  variable_nok_per_kwh: 0.25
  fixed_nok_per_month: 500
```

**Step 2**: Run simulation in IPython

```python
from src.simulation.battery_simulation import BatterySimulation

# Load config and run
sim = BatterySimulation.from_config('configs/my_analysis.yaml')
results = sim.run()

# Access results
print(f"Timesteps: {len(results.trajectory)}")
print(f"Final SOC: {results.trajectory['soc_percent'].iloc[-1]:.1f}%")
```

### Complete Example

```python
# Multiple scenario analysis with file-based configs

scenarios = [
    ('configs/battery_60kwh.yaml', '60 kWh battery'),
    ('configs/battery_80kwh.yaml', '80 kWh battery'),
    ('configs/battery_100kwh.yaml', '100 kWh battery'),
]

results_dict = {}

for config_file, name in scenarios:
    print(f"\n{'='*60}")
    print(f"Running scenario: {name}")
    print(f"{'='*60}")

    sim = BatterySimulation.from_config(config_file)
    results = sim.run()

    results_dict[name] = results

    # Quick summary
    traj = results.trajectory
    print(f"Total charge: {traj['P_charge_kw'].sum():.0f} kWh")
    print(f"Total discharge: {traj['P_discharge_kw'].sum():.0f} kWh")
    print(f"Grid import: {traj['P_grid_import_kw'].sum():.0f} kWh")
    print(f"Grid export: {traj['P_grid_export_kw'].sum():.0f} kWh")

# Compare scenarios
import pandas as pd
comparison = pd.DataFrame({
    name: {
        'Charge (kWh)': res.trajectory['P_charge_kw'].sum(),
        'Discharge (kWh)': res.trajectory['P_discharge_kw'].sum(),
        'Grid Import (kWh)': res.trajectory['P_grid_import_kw'].sum(),
        'Grid Export (kWh)': res.trajectory['P_grid_export_kw'].sum(),
    }
    for name, res in results_dict.items()
}).T

print("\n" + "="*60)
print("SCENARIO COMPARISON")
print("="*60)
print(comparison)
```

---

## Pattern 2: DataFrame-Based

### Use Case

- **IPython interactive analysis** with pandas
- **Data exploration** and cleaning before simulation
- **Custom data sources** easily converted to DataFrame
- **Quick experiments** without creating config files

### Quick Start

```python
import pandas as pd
from src.simulation.battery_simulation import BatterySimulation

# Create or load DataFrame with required columns
df = pd.DataFrame({
    'price_nok_per_kwh': [0.8, 0.7, 0.6, ...],
    'pv_production_kw': [0, 5, 20, ...],
    'consumption_kw': [30, 28, 25, ...]
}, index=pd.date_range('2024-06-01', periods=720, freq='h'))

# Run simulation
sim = BatterySimulation.from_dataframe(df, battery_kwh=80, battery_kw=60)
results = sim.run()
```

### Complete Example: Load Real Data

```python
# ═══════════════════════════════════════════════════════════
# Load and Align Real Data into DataFrame
# ═══════════════════════════════════════════════════════════

from src.data.file_loaders import load_price_data, load_production_data, load_consumption_data, align_timeseries
import pandas as pd

# Load three sources
timestamps_price, prices = load_price_data('data/spot_prices/NO2_2024_60min_real.csv')
timestamps_prod, production = load_production_data('data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv')
timestamps_cons, consumption = load_consumption_data('data/consumption/commercial_2024.csv')

# Align to common time grid
common_timestamps, aligned_values = align_timeseries(
    [timestamps_price, timestamps_prod, timestamps_cons],
    [prices, production, consumption]
)

# Create DataFrame
df = pd.DataFrame({
    'price_nok_per_kwh': aligned_values[0],
    'pv_production_kw': aligned_values[1],
    'consumption_kw': aligned_values[2]
}, index=common_timestamps)

print(f"Aligned data: {len(df)} hours")
print(f"Date range: {df.index[0]} to {df.index[-1]}")

# ═══════════════════════════════════════════════════════════
# Filter and Modify Data (Pandas Power!)
# ═══════════════════════════════════════════════════════════

# Filter to specific month
june_df = df[(df.index >= '2024-06-01') & (df.index < '2024-07-01')]

# Adjust prices (e.g., simulate 20% price increase)
june_df_high_price = june_df.copy()
june_df_high_price['price_nok_per_kwh'] *= 1.2

# Adjust production (e.g., simulate 10% degradation)
june_df_degraded = june_df.copy()
june_df_degraded['pv_production_kw'] *= 0.9

# ═══════════════════════════════════════════════════════════
# Run Simulations on Modified Data
# ═══════════════════════════════════════════════════════════

scenarios = {
    'Baseline': june_df,
    'High Prices (+20%)': june_df_high_price,
    'Degraded PV (-10%)': june_df_degraded,
}

for name, scenario_df in scenarios.items():
    print(f"\n{'='*60}")
    print(f"Scenario: {name}")
    print(f"{'='*60}")

    sim = BatterySimulation.from_dataframe(
        scenario_df,
        battery_kwh=80,
        battery_kw=60
    )
    results = sim.run()

    traj = results.trajectory
    print(f"Grid import: {traj['P_grid_import_kw'].sum():.0f} kWh")
    print(f"Grid export: {traj['P_grid_export_kw'].sum():.0f} kWh")
    print(f"Battery cycles: {traj['P_charge_kw'].sum() / 80:.1f}")
```

### Custom Column Names

```python
# If your DataFrame has different column names
df_custom = pd.DataFrame({
    'spot_price': [0.8, 0.7, 0.6, ...],
    'solar_output': [0, 5, 20, ...],
    'building_load': [30, 28, 25, ...]
}, index=pd.date_range('2024-06-01', periods=720, freq='h'))

# Specify column mapping
sim = BatterySimulation.from_dataframe(
    df_custom,
    battery_kwh=80,
    battery_kw=60,
    price_col='spot_price',
    production_col='solar_output',
    consumption_col='building_load'
)
results = sim.run()
```

---

## Pattern 3: Array-Based

### Use Case

- **NumPy workflows** with array processing
- **Custom data generators** (synthetic profiles, scenarios)
- **Integration with other tools** (optimization loops, ML models)
- **Maximum control** over data preparation

### Quick Start

```python
import numpy as np
import pandas as pd
from src.simulation.battery_simulation import BatterySimulation

# Create synthetic data
timestamps = pd.date_range('2024-06-01', periods=720, freq='h')
prices = np.random.uniform(0.5, 1.5, 720)
production = np.random.uniform(0, 100, 720)
consumption = np.random.uniform(20, 50, 720)

# Run simulation
sim = BatterySimulation.from_arrays(
    timestamps=timestamps,
    prices=prices,
    production=production,
    consumption=consumption,
    battery_kwh=80,
    battery_kw=60
)
results = sim.run()
```

### Complete Example: Synthetic Profiles

```python
# ═══════════════════════════════════════════════════════════
# Generate Realistic Synthetic Profiles
# ═══════════════════════════════════════════════════════════

import numpy as np
import pandas as pd

def generate_price_profile(hours=720, base=0.8, volatility=0.3):
    """Generate realistic price profile with peak/off-peak patterns."""
    timestamps = pd.date_range('2024-06-01', periods=hours, freq='h')

    # Base price with daily pattern
    hour_of_day = timestamps.hour
    daily_factor = np.where(
        (hour_of_day >= 6) & (hour_of_day < 22),
        1.2,  # Peak hours (06:00-22:00)
        0.8   # Off-peak
    )

    # Add random noise
    noise = np.random.normal(0, volatility, hours)
    prices = base * daily_factor * (1 + noise)

    # Ensure positive
    prices = np.maximum(prices, 0.1)

    return timestamps, prices

def generate_solar_profile(hours=720, peak_kw=100):
    """Generate realistic solar production profile."""
    timestamps = pd.date_range('2024-06-01', periods=hours, freq='h')

    hour_of_day = timestamps.hour
    day_of_year = timestamps.dayofyear

    # Solar curve (0 at night, peak at noon)
    solar_curve = np.maximum(0, np.sin(np.pi * (hour_of_day - 6) / 12))

    # Seasonal variation (higher in summer)
    seasonal_factor = 0.8 + 0.2 * np.sin(2 * np.pi * (day_of_year - 80) / 365)

    # Add cloud variability
    cloud_factor = np.random.beta(8, 2, hours)  # Mostly sunny, occasional clouds

    production = peak_kw * solar_curve * seasonal_factor * cloud_factor

    return timestamps, production

def generate_consumption_profile(hours=720, base_kw=30, peak_kw=50):
    """Generate realistic consumption profile."""
    timestamps = pd.date_range('2024-06-01', periods=hours, freq='h')

    hour_of_day = timestamps.hour
    weekday = timestamps.weekday

    # Commercial profile (high during business hours)
    daily_factor = np.where(
        (hour_of_day >= 8) & (hour_of_day < 18),
        1.5,  # Business hours
        0.6   # Off-hours
    )

    # Weekday vs weekend
    weekly_factor = np.where(weekday < 5, 1.0, 0.4)

    # Random variation
    noise = np.random.normal(1, 0.1, hours)

    consumption = base_kw + (peak_kw - base_kw) * daily_factor * weekly_factor * noise

    return timestamps, consumption

# ═══════════════════════════════════════════════════════════
# Generate Profiles and Run Simulation
# ═══════════════════════════════════════════════════════════

# Generate data
timestamps, prices = generate_price_profile(hours=720, base=0.8, volatility=0.3)
_, production = generate_solar_profile(hours=720, peak_kw=100)
_, consumption = generate_consumption_profile(hours=720, base_kw=30, peak_kw=50)

# Quick validation
print("Generated Profiles:")
print(f"Prices: {prices.min():.2f} to {prices.max():.2f} NOK/kWh")
print(f"Production: {production.min():.1f} to {production.max():.1f} kW")
print(f"Consumption: {consumption.min():.1f} to {consumption.max():.1f} kW")

# Run simulation
sim = BatterySimulation.from_arrays(
    timestamps=timestamps,
    prices=prices,
    production=production,
    consumption=consumption,
    battery_kwh=80,
    battery_kw=60
)

results = sim.run()

# Analyze results
traj = results.trajectory
print(f"\nSimulation Results:")
print(f"Battery cycles: {traj['P_charge_kw'].sum() / 80:.1f}")
print(f"Self-consumption: {(production.sum() - traj['P_grid_export_kw'].sum()) / production.sum() * 100:.1f}%")
```

### Example: Optimization Loop

```python
# ═══════════════════════════════════════════════════════════
# Battery Sizing Optimization with Array-Based API
# ═══════════════════════════════════════════════════════════

import numpy as np

# Fixed data (load real data here)
timestamps, prices = generate_price_profile(hours=8760)  # Full year
_, production = generate_solar_profile(hours=8760)
_, consumption = generate_consumption_profile(hours=8760)

# Battery sizes to test
battery_sizes_kwh = np.arange(20, 121, 20)  # 20, 40, 60, 80, 100, 120 kWh
power_ratios = [0.5, 1.0, 1.5]  # Power to capacity ratio

results_matrix = []

for capacity_kwh in battery_sizes_kwh:
    for power_ratio in power_ratios:
        power_kw = capacity_kwh * power_ratio

        print(f"Testing: {capacity_kwh} kWh / {power_kw:.0f} kW")

        sim = BatterySimulation.from_arrays(
            timestamps=timestamps,
            prices=prices,
            production=production,
            consumption=consumption,
            battery_kwh=capacity_kwh,
            battery_kw=power_kw
        )

        results = sim.run()
        traj = results.trajectory

        # Calculate metrics
        grid_import = traj['P_grid_import_kw'].sum()
        grid_export = traj['P_grid_export_kw'].sum()
        cycles = traj['P_charge_kw'].sum() / capacity_kwh

        results_matrix.append({
            'capacity_kwh': capacity_kwh,
            'power_kw': power_kw,
            'grid_import_kwh': grid_import,
            'grid_export_kwh': grid_export,
            'cycles': cycles
        })

# Convert to DataFrame for analysis
import pandas as pd
results_df = pd.DataFrame(results_matrix)

print("\n" + "="*80)
print("OPTIMIZATION RESULTS")
print("="*80)
print(results_df.to_string())

# Find optimal size (minimize grid import)
optimal = results_df.loc[results_df['grid_import_kwh'].idxmin()]
print(f"\nOptimal battery: {optimal['capacity_kwh']:.0f} kWh / {optimal['power_kw']:.0f} kW")
print(f"Grid import: {optimal['grid_import_kwh']:.0f} kWh")
print(f"Cycles: {optimal['cycles']:.1f}")
```

---

## Advanced Usage

### Combining Patterns

```python
# Start with file-based config, override specific parameters

from src.config.simulation_config import SimulationConfig
from src.simulation.battery_simulation import BatterySimulation

# Load base config
config = SimulationConfig.from_yaml('configs/base.yaml')

# Modify battery size programmatically
config.battery.capacity_kwh = 100
config.battery.power_kw = 80

# Create simulation with modified config
sim = BatterySimulation(config=config, data=None)
results = sim.run()
```

### Custom Data with Config

```python
# Use custom data arrays but keep other config parameters

import pandas as pd
import numpy as np
from src.data.data_manager import TimeSeriesData
from src.config.simulation_config import SimulationConfig
from src.simulation.battery_simulation import BatterySimulation

# Load config for battery/tariff parameters
config = SimulationConfig.from_yaml('configs/working_config.yaml')

# Create custom data
timestamps = pd.date_range('2024-06-01', periods=720, freq='h')
prices = np.random.uniform(0.5, 1.5, 720)
production = np.random.uniform(0, 100, 720)
consumption = np.random.uniform(20, 50, 720)

# Wrap in TimeSeriesData
data = TimeSeriesData.from_arrays(
    timestamps=timestamps,
    prices=prices,
    production=production,
    consumption=consumption
)

# Create simulation with config + custom data
sim = BatterySimulation(config=config, data=data)
results = sim.run()
```

### Results Analysis Helpers

```python
# Helper functions for common result analyses

def analyze_battery_usage(results):
    """Calculate battery usage statistics."""
    traj = results.trajectory

    capacity_kwh = traj['E_battery_kwh'].max()  # Approximate from max SOC
    total_charge = traj['P_charge_kw'].sum()
    total_discharge = traj['P_discharge_kw'].sum()
    cycles = total_discharge / capacity_kwh

    return {
        'total_charge_kwh': total_charge,
        'total_discharge_kwh': total_discharge,
        'cycles': cycles,
        'roundtrip_efficiency': total_discharge / total_charge if total_charge > 0 else 0,
        'avg_soc_percent': traj['soc_percent'].mean(),
    }

def analyze_grid_interaction(results):
    """Calculate grid import/export statistics."""
    traj = results.trajectory

    return {
        'total_import_kwh': traj['P_grid_import_kw'].sum(),
        'total_export_kwh': traj['P_grid_export_kw'].sum(),
        'peak_import_kw': traj['P_grid_import_kw'].max(),
        'peak_export_kw': traj['P_grid_export_kw'].max(),
        'net_import_kwh': traj['P_grid_import_kw'].sum() - traj['P_grid_export_kw'].sum(),
    }

def analyze_self_consumption(results, production_total):
    """Calculate self-consumption and self-sufficiency."""
    traj = results.trajectory

    total_export = traj['P_grid_export_kw'].sum()
    self_consumed_pv = production_total - total_export

    total_consumption = traj['consumption_kw'].sum() if 'consumption_kw' in traj else 0
    total_import = traj['P_grid_import_kw'].sum()
    self_supply = total_consumption - total_import if total_consumption > 0 else 0

    return {
        'self_consumption_kwh': self_consumed_pv,
        'self_consumption_rate': self_consumed_pv / production_total if production_total > 0 else 0,
        'self_sufficiency_kwh': self_supply,
        'self_sufficiency_rate': self_supply / total_consumption if total_consumption > 0 else 0,
    }

# Usage
results = sim.run()

battery_stats = analyze_battery_usage(results)
grid_stats = analyze_grid_interaction(results)

print("Battery Usage:")
for key, value in battery_stats.items():
    print(f"  {key}: {value:.2f}")

print("\nGrid Interaction:")
for key, value in grid_stats.items():
    print(f"  {key}: {value:.2f}")
```

---

## API Reference

### BatterySimulation Class

```python
class BatterySimulation:
    """Facade for battery optimization simulations."""

    # ═══════════════════════════════════════════════════════
    # Constructors
    # ═══════════════════════════════════════════════════════

    @classmethod
    def from_config(cls, config_path: str) -> "BatterySimulation":
        """
        Create simulation from YAML config file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            BatterySimulation instance ready to run()
        """

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        battery_kwh: float,
        battery_kw: float,
        price_col: str = 'price_nok_per_kwh',
        production_col: str = 'pv_production_kw',
        consumption_col: str = 'consumption_kw',
        initial_soc_percent: float = 50.0,
        min_soc_percent: float = 10.0,
        max_soc_percent: float = 90.0,
        efficiency_roundtrip: float = 0.90,
        grid_import_limit_kw: Optional[float] = None,
        grid_export_limit_kw: Optional[float] = None,
    ) -> "BatterySimulation":
        """
        Create simulation from pandas DataFrame.

        Args:
            df: DataFrame with DatetimeIndex and columns for price, production, consumption
            battery_kwh: Battery capacity (kWh)
            battery_kw: Battery power (kW)
            price_col: Name of price column (NOK/kWh)
            production_col: Name of PV production column (kW)
            consumption_col: Name of consumption column (kW)
            initial_soc_percent: Starting SOC (%)
            min_soc_percent: Minimum SOC constraint (%)
            max_soc_percent: Maximum SOC constraint (%)
            efficiency_roundtrip: Round-trip efficiency (0-1)
            grid_import_limit_kw: Maximum grid import power (kW)
            grid_export_limit_kw: Maximum grid export power (kW)

        Returns:
            BatterySimulation instance
        """

    @classmethod
    def from_arrays(
        cls,
        timestamps: pd.DatetimeIndex,
        prices: np.ndarray,
        production: np.ndarray,
        consumption: np.ndarray,
        battery_kwh: float,
        battery_kw: float,
        initial_soc_percent: float = 50.0,
        min_soc_percent: float = 10.0,
        max_soc_percent: float = 90.0,
        efficiency_roundtrip: float = 0.90,
        grid_import_limit_kw: Optional[float] = None,
        grid_export_limit_kw: Optional[float] = None,
    ) -> "BatterySimulation":
        """
        Create simulation from numpy arrays.

        Args:
            timestamps: DatetimeIndex or array-like timestamps
            prices: Array of electricity prices (NOK/kWh)
            production: Array of PV production (kW)
            consumption: Array of load consumption (kW)
            battery_kwh: Battery capacity (kWh)
            battery_kw: Battery power (kW)
            ... (same optional parameters as from_dataframe)

        Returns:
            BatterySimulation instance
        """

    # ═══════════════════════════════════════════════════════
    # Methods
    # ═══════════════════════════════════════════════════════

    def run(self) -> SimulationResults:
        """
        Run the battery optimization simulation.

        Returns:
            SimulationResults with trajectory DataFrame and metadata
        """

    def get_results(self) -> Optional[SimulationResults]:
        """Get results from last run (None if not run yet)."""

    def summary(self) -> str:
        """Generate text summary of simulation setup and results."""
```

### TimeSeriesData Class

```python
@dataclass
class TimeSeriesData:
    """Container for time-series simulation data."""

    timestamps: pd.DatetimeIndex
    prices_nok_per_kwh: np.ndarray
    pv_production_kw: np.ndarray
    consumption_kw: np.ndarray
    resolution: str

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        price_col: str = 'price_nok_per_kwh',
        production_col: str = 'pv_production_kw',
        consumption_col: str = 'consumption_kw',
        resolution: Optional[str] = None
    ) -> "TimeSeriesData":
        """Create from DataFrame with auto-detected resolution."""

    @classmethod
    def from_arrays(
        cls,
        timestamps: pd.DatetimeIndex,
        prices: np.ndarray,
        production: np.ndarray,
        consumption: np.ndarray,
        resolution: Optional[str] = None
    ) -> "TimeSeriesData":
        """Create from numpy arrays with auto-detected resolution."""

    def __len__(self) -> int:
        """Return number of timesteps."""
```

---

## Migration from Old API

### Old API (Legacy)

```python
# Old way: Direct orchestrator usage
from src.config.simulation_config import SimulationConfig
from src.simulation.rolling_horizon_orchestrator import RollingHorizonOrchestrator

config = SimulationConfig.from_yaml('configs/working_config.yaml')
orchestrator = RollingHorizonOrchestrator(config)
results = orchestrator.run()
```

### New API (Recommended)

```python
# New way: BatterySimulation facade
from src.simulation.battery_simulation import BatterySimulation

# Exact same config file works
sim = BatterySimulation.from_config('configs/working_config.yaml')
results = sim.run()
```

### Why Migrate?

| Aspect | Old API | New API |
|--------|---------|---------|
| **Entry point** | `RollingHorizonOrchestrator` | `BatterySimulation` |
| **Config only** | ✅ Yes | ✅ Yes |
| **DataFrame support** | ❌ No | ✅ Yes |
| **Array support** | ❌ No | ✅ Yes |
| **IPython friendly** | ⚠️ Verbose | ✅ Concise |
| **Error messages** | Technical | User-friendly |
| **Documentation** | Sparse | Complete |

**Migration is optional** - Old API still works, but new API is recommended for IPython usage.

---

## Best Practices

### Performance

1. **Use file-based for large datasets** - Efficient data loading
2. **Filter DataFrames before simulation** - Don't load full year if analyzing one month
3. **Reuse aligned data** - Align once, run multiple scenarios
4. **Pre-allocate arrays** - When generating synthetic data

### Code Quality

1. **Version control configs** - Keep YAML files in git
2. **Document assumptions** - Comment synthetic profile parameters
3. **Validate inputs** - Check timestamps, values before running
4. **Save results** - Store trajectory DataFrames for later analysis

### IPython Workflow

```python
# Recommended IPython session pattern

# 1. Import once at start
from src.simulation.battery_simulation import BatterySimulation
import pandas as pd
import numpy as np

# 2. Load and prepare data
df = pd.read_csv('data/aligned_data.csv', index_col=0, parse_dates=True)

# 3. Quick validation
print(f"Data: {len(df)} hours, {df.index[0]} to {df.index[-1]}")
print(f"Prices: {df['price_nok_per_kwh'].describe()}")

# 4. Run simulation
sim = BatterySimulation.from_dataframe(df, battery_kwh=80, battery_kw=60)
results = sim.run()

# 5. Interactive analysis
traj = results.trajectory
traj['P_charge_kw'].plot(label='Charge')
traj['P_discharge_kw'].plot(label='Discharge')
plt.legend()
plt.show()

# 6. Iterate and refine
# Modify df, re-run simulation, compare results
```

---

## Summary

**Three Patterns, One Interface**:

```python
# Pattern 1: Production-ready, reproducible
sim = BatterySimulation.from_config('config.yaml')

# Pattern 2: IPython-friendly, pandas workflows
sim = BatterySimulation.from_dataframe(df, battery_kwh=80, battery_kw=60)

# Pattern 3: Maximum flexibility, custom data
sim = BatterySimulation.from_arrays(timestamps, prices, production, consumption, ...)

# Always the same
results = sim.run()
```

Choose the pattern that fits your workflow. All three use the same battle-tested optimizer underneath.
