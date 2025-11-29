#!/usr/bin/env python3
"""
Run yearly simulation with 24h horizon, 30kWh/15kW battery, 1-hour resolution.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import BatteryOptimizationConfig
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
import pandas as pd
import json
from datetime import datetime

print('='*70)
print('YEARLY SIMULATION: 24h Horizon Sequential')
print('='*70)
print()
print('Configuration:')
print('  Battery: 30 kWh, 15 kW')
print('  Horizon: 24 hours (1 day)')
print('  Resolution: PT60M (1 hour)')
print('  Year: 2024')
print()

# Load configuration
config = BatteryOptimizationConfig.from_yaml('config.yaml')

# Create optimizer with config and battery override parameters
print('Creating optimizer...')
optimizer = RollingHorizonOptimizer(
    config=config,
    battery_kwh=30.0,
    battery_kw=15.0,
    horizon_hours=24
)

print()
print('Running optimization...')
print(f'  This will optimize {24*365} hours in 24-hour windows')
print()

# Run sequential optimization (year 2024)
trajectory = optimizer.optimize_24h(year=2024)

# Create output directory
output_dir = Path('results/yearly_2024_24h_15kW_30kWh')
output_dir.mkdir(parents=True, exist_ok=True)

# Save results
print()
print('Saving results...')

# Save trajectory
trajectory_path = output_dir / 'trajectory.csv'
trajectory.to_csv(trajectory_path)
print(f'  ✓ Trajectory: {trajectory_path} ({len(trajectory)} timesteps)')

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
print(f'  ✓ Metadata: {metadata_path}')

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
print(f'  ✓ Summary: {summary_path}')

print()
print('='*70)
print('SIMULATION COMPLETE')
print('='*70)
print()
print(f'Results directory: {output_dir}')
print(f'  Annual cost: {summary["total_cost_nok"]:,.0f} NOK')
print(f'    Energy:    {summary["energy_cost_nok"]:,.0f} NOK')
print(f'    Power:     {summary["power_cost_nok"]:,.0f} NOK')
print(f'    Degradation: {summary["degradation_cost_nok"]:,.0f} NOK')
print()
print('To generate reports, use:')
print(f'  python -c "from core.reporting import ReportFactory; report = ReportFactory.create(\'battery_operation\', ...)"')
print()
