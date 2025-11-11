#!/usr/bin/env python3
"""
Run yearly simulation: WEEKLY optimization with 24h horizon.
- 52 weeks (7-day windows)
- 24-hour lookahead horizon within each week
- 30kWh/15kW battery
- 1-hour resolution (PT60M)
- Real data: ENTSO-E prices + PVGIS solar
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

from config import BatteryOptimizationConfig
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from core.price_fetcher import ENTSOEPriceFetcher
from core.pvgis_solar import PVGISProduction
from operational import BatterySystemState

print('='*70)
print('YEARLY SIMULATION: Weekly with 24h Horizon')
print('='*70)
print('  Battery: 30 kWh, 15 kW')
print('  Horizon: 24 hours (1 day lookahead)')
print('  Windows: 52 weeks (7 days each)')
print('  Resolution: PT15M (15 minutes) - optimizer internal resolution')
print('  Year: 2024')
print()

# Load data
print('Loading data...')
config = BatteryOptimizationConfig.from_yaml('config.yaml')

fetcher = ENTSOEPriceFetcher(resolution='PT15M')
prices_series = fetcher.fetch_prices(year=2024, area='NO2', resolution='PT15M')
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
print(f'  PV production: {pv_production.sum():.0f} kWh')
print(f'  Load: {load.sum():.0f} kWh')
print()

# Create optimizer with 24h horizon
print('Creating optimizer...')
optimizer = RollingHorizonOptimizer(
    config=config,
    battery_kwh=30.0,
    battery_kw=15.0,
    horizon_hours=24  # 24-hour lookahead
)

# Run weekly optimization
print('Running weekly optimization (52 weeks, 24h horizon each)...')
weekly_timesteps = 168  # 7 days @ hourly = 168 timesteps
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
    'DP_cyc': [],
    'DP_total': [],
    'weekly_costs': [],
    'weekly_energy_costs': [],
    'weekly_power_costs': [],
    'weekly_degradation_costs': [],
    'weekly_solve_times': []
}

state = BatterySystemState()
prev_month = 1

for week in range(n_weeks):
    t_start = week * weekly_timesteps
    t_end = min(t_start + weekly_timesteps, n_timesteps)

    # Check for month boundaries (reset peak tracking)
    current_month = timestamps[t_start].month
    if current_month != prev_month and week > 0:
        print(f"  Week {week}: Month boundary {prev_month} → {current_month}, peak reset")
        prev_month = current_month

    # Optimize week
    start_time = time.time()
    result = optimizer.optimize_window(
        current_state=state,
        pv_production=pv_production[t_start:t_end],
        load_consumption=load[t_start:t_end],
        spot_prices=spot_prices[t_start:t_end],
        timestamps=timestamps[t_start:t_end],
        verbose=False
    )
    solve_time = time.time() - start_time

    if not result.success:
        print(f"  ❌ Week {week} optimization failed: {result.message}")
        break

    # Store results
    full_results['P_charge'].extend(result.P_charge)
    full_results['P_discharge'].extend(result.P_discharge)
    full_results['P_grid_import'].extend(result.P_grid_import)
    full_results['P_grid_export'].extend(result.P_grid_export)
    full_results['E_battery'].extend(result.E_battery)
    full_results['P_curtail'].extend(result.P_curtail)
    full_results['DP_cyc'].extend(result.DP_cyc)
    full_results['DP_total'].extend(result.DP_total)

    full_results['weekly_costs'].append(result.objective_value)
    full_results['weekly_energy_costs'].append(result.energy_cost)
    full_results['weekly_power_costs'].append(result.peak_penalty_actual)
    full_results['weekly_degradation_costs'].append(result.degradation_cost)
    full_results['weekly_solve_times'].append(solve_time)

    # Update state for next week
    state.update_from_measurement(
        timestamp=timestamps[t_end - 1],
        soc_kwh=result.E_battery_final,
        grid_import_power_kw=result.P_grid_import[-1] if len(result.P_grid_import) > 0 else 0.0
    )

    # Progress reporting
    if week % 10 == 0:
        print(f'  Week {week}: Cost={result.objective_value:.2f} NOK, Solve={solve_time:.3f}s')

print(f'\n✓ Optimization complete - {n_weeks} weeks')
print(f'  Annual cost: {sum(full_results["weekly_costs"]):.0f} NOK')
print(f'  Energy cost: {sum(full_results["weekly_energy_costs"]):.0f} NOK')
print(f'  Power cost: {sum(full_results["weekly_power_costs"]):.0f} NOK')
print(f'  Degradation cost: {sum(full_results["weekly_degradation_costs"]):.0f} NOK')
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
    'degradation_cycle_pct': full_results['DP_cyc'],
    'degradation_total_pct': full_results['DP_total'],
    'pv_production_kw': pv_production[:len(full_results['P_charge'])],
    'consumption_kw': load[:len(full_results['P_charge'])],
    'spot_price_nok_per_kwh': spot_prices[:len(full_results['P_charge'])]
}

trajectory = pd.DataFrame(trajectory_data, index=timestamps[:len(full_results['P_charge'])])

# Calculate costs per timestep (simplified)
trajectory['energy_cost_nok'] = (trajectory['P_grid_import_kw'] * trajectory['spot_price_nok_per_kwh'])
trajectory['total_cost_nok'] = trajectory['energy_cost_nok']  # Simplified

# Create output directory
output_dir = Path('results/yearly_2024_weekly_24h_15kW_30kWh_PT15M')
output_dir.mkdir(parents=True, exist_ok=True)

# Save trajectory
trajectory_path = output_dir / 'trajectory.csv'
trajectory.to_csv(trajectory_path)
print(f'Saved trajectory: {trajectory_path} ({len(trajectory)} timesteps)')

# Save metadata
metadata = {
    'battery_capacity_kwh': 30,
    'battery_power_kw': 15,
    'horizon_hours': 24,
    'window_type': 'weekly',
    'window_hours': 168,
    'resolution': 'PT15M',
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
    'energy_cost_nok': float(sum(full_results['weekly_energy_costs'])),
    'power_cost_nok': float(sum(full_results['weekly_power_costs'])),
    'degradation_cost_nok': float(sum(full_results['weekly_degradation_costs'])),
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
print(f'  Energy:          {summary["energy_cost_nok"]:,.0f} NOK')
print(f'  Power tariff:    {summary["power_cost_nok"]:,.0f} NOK')
print(f'  Degradation:     {summary["degradation_cost_nok"]:,.0f} NOK')
print(f'  Total solve time: {summary["total_solve_time_s"]:.1f}s ({summary["total_solve_time_s"]/60:.1f} min)')
print()
