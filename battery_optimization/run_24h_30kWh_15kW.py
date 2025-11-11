#!/usr/bin/env python3
"""
Run yearly simulation: 24h horizon, 30kWh/15kW battery, 2024.
Based on visualize_resolution_comparison.py pattern.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
from datetime import datetime

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import BatteryOptimizationConfig
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from core.price_fetcher import ENTSOEPriceFetcher
from core.pvgis_solar import PVGISProduction
from operational import BatterySystemState

print('='*70)
print('YEARLY SIMULATION: 24h Horizon, 30kWh/15kW Battery')
print('='*70)
print()

# Load data
print('Loading data...')
config = BatteryOptimizationConfig.from_yaml('config.yaml')

fetcher = ENTSOEPriceFetcher(resolution='PT60M')
prices_series = fetcher.fetch_prices(year=2024, area='NO2', resolution='PT60M')
prices_df = prices_series.to_frame('price_nok_per_kwh')

pvgis = PVGISProduction(lat=58.97, lon=5.73, pv_capacity_kwp=138.55, tilt=30.0, azimuth=173.0)
pv_series = pvgis.fetch_hourly_production(year=2024)
pv_df = pv_series.to_frame('pv_power_kw')

timestamps = prices_df.index
spot_prices = prices_df['price_nok_per_kwh'].values

# Match PV to prices timestamps
pv_production = np.zeros(len(timestamps))
for i, ts in enumerate(timestamps):
    matching = pv_df[
        (pv_df.index.month == ts.month) &
        (pv_df.index.day == ts.day) &
        (pv_df.index.hour == ts.hour)
    ]
    if len(matching) > 0:
        pv_production[i] = matching['pv_power_kw'].values[0]

# Simple load profile
annual_kwh = 300000
hours_per_year = 8760
avg_load = annual_kwh / hours_per_year
load = np.zeros(len(timestamps))
for i, ts in enumerate(timestamps):
    base = avg_load * 0.6
    if ts.weekday() < 5 and 6 <= ts.hour < 18:
        load[i] = base * 1.8
    elif 18 <= ts.hour < 22:
        load[i] = base * 1.3
    else:
        load[i] = base

print(f'  Timesteps: {len(timestamps)}')
print(f'  Price range: {spot_prices.min():.3f} - {spot_prices.max():.3f} NOK/kWh')
print(f'  PV production: {pv_production.sum():.0f} kW·h')
print(f'  Load: {load.sum():.0f} kW·h')
print()

# Create optimizer
print('Creating optimizer (24h horizon, 30kWh, 15kW)...')
optimizer = RollingHorizonOptimizer(
    config=config,
    battery_kwh=30.0,
    battery_kw=15.0,
    horizon_hours=24
)

# Run optimization (loop through year in 24h windows)
print('Running 24h sequential optimization...')
daily_timesteps = 24  # 1 hour resolution = 24 timesteps per day
n_timesteps = len(timestamps)
n_days = n_timesteps // daily_timesteps

print(f'  Days to optimize: {n_days}')
print()

# Storage for results
all_results = []
state = BatterySystemState()  # Initial state

for day in range(n_days):
    t_start = day * daily_timesteps
    t_end = min(t_start + daily_timesteps, n_timesteps)

    if day % 10 == 0:
        print(f'  Day {day}/{n_days}...')

    result = optimizer.optimize_window(
        current_state=state,
        pv_production=pv_production[t_start:t_end],
        load_consumption=load[t_start:t_end],
        spot_prices=spot_prices[t_start:t_end],
        timestamps=timestamps[t_start:t_end]
    )

    all_results.append(result.trajectory)
    state = result.final_state

# Combine results
trajectory = pd.concat(all_results, ignore_index=False)

print(f'\n✓ Optimization complete - {n_days} days')
print(f'  Total timesteps: {len(trajectory)}')
print()

# Create output directory
output_dir = Path('results/yearly_2024_24h_15kW_30kWh')
output_dir.mkdir(parents=True, exist_ok=True)

# Save trajectory
trajectory_path = output_dir / 'trajectory.csv'
trajectory.to_csv(trajectory_path)
print(f'Saved trajectory: {trajectory_path}')

# Save metadata
metadata = {
    'battery_capacity_kwh': 30,
    'battery_power_kw': 15,
    'horizon_hours': 24,
    'resolution': 'PT60M',
    'year': 2024,
    'timesteps': len(trajectory),
    'timestamp': datetime.now().isoformat()
}
metadata_path = output_dir / 'metadata.csv'
pd.DataFrame([metadata]).to_csv(metadata_path, index=False)
print(f'Saved metadata: {metadata_path}')

# Calculate summary
summary = {
    'total_cost_nok': float(trajectory['total_cost_nok'].sum()) if 'total_cost_nok' in trajectory.columns else 0,
    'energy_cost_nok': float(trajectory['energy_cost_nok'].sum()) if 'energy_cost_nok' in trajectory.columns else 0,
    'power_cost_nok': float(trajectory['power_cost_nok'].sum()) if 'power_cost_nok' in trajectory.columns else 0,
    'degradation_cost_nok': float(trajectory['degradation_cost_nok'].sum()) if 'degradation_cost_nok' in trajectory.columns else 0,
}
summary_path = output_dir / 'summary.json'
with open(summary_path, 'w') as f:
    json.dump(summary, f, indent=2)
print(f'Saved summary: {summary_path}')

print()
print('='*70)
print('SIMULATION COMPLETE')
print('='*70)
print(f'\nResults: {output_dir}')
print(f'  Annual cost: {summary["total_cost_nok"]:,.0f} NOK')
print(f'    Energy:        {summary["energy_cost_nok"]:,.0f} NOK')
print(f'    Power tariff:  {summary["power_cost_nok"]:,.0f} NOK')
print(f'    Degradation:   {summary["degradation_cost_nok"]:,.0f} NOK')
print()
