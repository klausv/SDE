#!/usr/bin/env python3
"""
Yearly simulation with WeeklyOptimizer (168h horizon, PT60M resolution).

- 52 weeks sequential optimization
- 168-hour horizon (1 week lookahead)
- PT60M (1-hour) resolution
- 30 kWh / 15 kW battery
- Real data: ENTSO-E + PVGIS
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
import time
from datetime import datetime

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.optimization.weekly_optimizer import WeeklyOptimizer
from core.price_fetcher import ENTSOEPriceFetcher
from core.pvgis_solar import PVGISProduction
from src.operational.state_manager import BatterySystemState
from core.consumption_profiles import ConsumptionProfile

print('='*70)
print('YEARLY SIMULATION: Weekly 168h Horizon, PT60M Resolution')
print('='*70)
print('  Optimizer: WeeklyOptimizer')
print('  Battery: 30 kWh, 15 kW')
print('  Horizon: 168 hours (1 week lookahead)')
print('  Windows: 52 weeks')
print('  Resolution: PT60M (1 hour)')
print('  Year: 2024')
print()

# Load data
print('Loading data...')
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

# Generate realistic commercial office consumption profile (90,000 kWh/year)
print('Generating realistic commercial office consumption profile...')
consumption_profile = ConsumptionProfile.generate_annual_profile(
    profile_type='commercial_office',
    annual_kwh=90000,
    year=2024
)

# Align consumption with price timestamps
load = np.zeros(len(timestamps))
for i, ts in enumerate(timestamps):
    matching = consumption_profile[
        (consumption_profile.index.month == ts.month) &
        (consumption_profile.index.day == ts.day) &
        (consumption_profile.index.hour == ts.hour)
    ]
    if len(matching) > 0:
        load[i] = matching.values[0]

print(f'  Timesteps: {len(timestamps)}')
print(f'  Price range: {spot_prices.min():.3f} - {spot_prices.max():.3f} NOK/kWh')
print(f'  PV production: {pv_production.sum():.0f} kWh')
print(f'  Load: {load.sum():.0f} kWh ({load.sum()/1000:.1f} MWh)')
print(f'  Load avg: {load.mean():.1f} kW, max: {load.max():.1f} kW, min: {load.min():.1f} kW')
print()

# Create WeeklyOptimizer
print('Creating WeeklyOptimizer...')
optimizer = WeeklyOptimizer(
    battery_kwh=30.0,
    battery_kw=15.0,
    battery_efficiency=0.90,
    min_soc_percent=10.0,
    max_soc_percent=90.0,
    resolution='PT60M',
    horizon_hours=168,
    use_global_config=True
)

# Run weekly optimization (52 weeks)
print('Running weekly optimization (52 weeks, 168h horizon each)...')
weekly_timesteps = 168  # 1 week @ hourly
n_timesteps = len(timestamps)
n_weeks = n_timesteps // weekly_timesteps

print(f'  Total timesteps: {n_timesteps}')
print(f'  Weekly timesteps: {weekly_timesteps}')
print(f'  Weeks to optimize: {n_weeks}')
print()

# Storage for results
full_results = {
    'P_charge': [],
    'P_discharge': [],
    'P_grid_import': [],
    'P_grid_export': [],
    'E_battery': [],
    'P_curtail': [],
    'weekly_costs': [],
    'weekly_solve_times': []
}

state = BatterySystemState()

for week in range(n_weeks):
    t_start = week * weekly_timesteps
    t_end = min(t_start + weekly_timesteps, n_timesteps)

    # Optimize week
    start_time = time.time()
    result = optimizer.optimize(
        timestamps=timestamps[t_start:t_end],
        pv_production=pv_production[t_start:t_end],
        consumption=load[t_start:t_end],
        spot_prices=spot_prices[t_start:t_end],
        battery_state=state
    )
    solve_time = time.time() - start_time

    if not result.success:
        print(f"  ❌ Week {week} optimization failed: {result.message}")
        break

    # Store results (access arrays directly from OptimizationResult)
    full_results['P_charge'].extend(result.P_charge)
    full_results['P_discharge'].extend(result.P_discharge)
    full_results['P_grid_import'].extend(result.P_grid_import)
    full_results['P_grid_export'].extend(result.P_grid_export)
    full_results['E_battery'].extend(result.E_battery)
    full_results['P_curtail'].extend(result.P_curtail)

    full_results['weekly_costs'].append(result.objective_value)
    full_results['weekly_solve_times'].append(solve_time)

    # Update state for next week
    state.update_from_measurement(
        timestamp=timestamps[t_end - 1],
        soc_kwh=result.E_battery[-1],
        grid_import_power_kw=result.P_grid_import[-1]
    )

    # Progress reporting
    if week % 10 == 0:
        print(f'  Week {week}: Cost={result.objective_value:.2f} NOK, Solve={solve_time:.3f}s')

print(f'\n✓ Optimization complete - {n_weeks} weeks')
print(f'  Annual cost: {sum(full_results["weekly_costs"]):.0f} NOK')
print(f'  Avg solve time: {np.mean(full_results["weekly_solve_times"]):.3f}s/week')
print()

# Create trajectory DataFrame
trajectory_data = {
    'P_charge_kw': full_results['P_charge'],
    'P_discharge_kw': full_results['P_discharge'],
    'P_grid_import_kw': full_results['P_grid_import'],
    'P_grid_export_kw': full_results['P_grid_export'],
    'E_battery_kwh': full_results['E_battery'],
    'P_curtail_kw': full_results['P_curtail'],
    'pv_production_kw': pv_production[:len(full_results['P_charge'])],
    'consumption_kw': load[:len(full_results['P_charge'])],
    'spot_price_nok_per_kwh': spot_prices[:len(full_results['P_charge'])]
}

trajectory = pd.DataFrame(trajectory_data, index=timestamps[:len(full_results['P_charge'])])

# Calculate costs per timestep
trajectory['energy_cost_nok'] = (trajectory['P_grid_import_kw'] * trajectory['spot_price_nok_per_kwh'])
trajectory['total_cost_nok'] = trajectory['energy_cost_nok']

# Create output directory
output_dir = Path('results/yearly_2024_weekly_168h_15kW_30kWh_PT60M')
output_dir.mkdir(parents=True, exist_ok=True)

# Save trajectory
trajectory_path = output_dir / 'trajectory.csv'
trajectory.to_csv(trajectory_path)
print(f'Saved trajectory: {trajectory_path} ({len(trajectory)} timesteps)')

# Save metadata
metadata = {
    'optimizer': 'WeeklyOptimizer',
    'battery_capacity_kwh': 30,
    'battery_power_kw': 15,
    'horizon_hours': 168,
    'window_type': 'weekly',
    'resolution': 'PT60M',
    'year': 2024,
    'timesteps': len(trajectory),
    'weeks_optimized': n_weeks,
    'timestamp': datetime.now().isoformat()
}
metadata_path = output_dir / 'metadata.csv'
pd.DataFrame([metadata]).to_csv(metadata_path, index=False)
print(f'Saved metadata: {metadata_path}')

# Save summary
summary = {
    'total_cost_nok': float(sum(full_results['weekly_costs'])),
    'avg_solve_time_s': float(np.mean(full_results['weekly_solve_times'])),
    'total_solve_time_s': float(sum(full_results['weekly_solve_times']))
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
print(f'  Annual cost:     {summary["total_cost_nok"]:,.0f} NOK')
print(f'  Total solve time: {summary["total_solve_time_s"]:.1f}s ({summary["total_solve_time_s"]/60:.1f} min)')
print()
