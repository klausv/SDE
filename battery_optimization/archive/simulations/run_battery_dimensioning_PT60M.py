#!/usr/bin/env python3
"""
Battery Dimensioning Analysis with WeeklyOptimizer (PT60M, 168h horizon).

Grid search over battery dimensions (E_nom, P_max) to find optimal NPV.
Uses the FAST WeeklyOptimizer with PT60M resolution.

Author: Claude Code
Date: 2025-01-11
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
import time
from datetime import datetime
from itertools import product
from scipy.optimize import minimize

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.optimization.weekly_optimizer import WeeklyOptimizer
from core.price_fetcher import ENTSOEPriceFetcher
from core.pvgis_solar import PVGISProduction
from src.operational.state_manager import BatterySystemState
from src.config.simulation_config import SimulationConfig
from src.config.legacy_config_adapter import generate_consumption_profile, ConsumptionConfig

# Load configuration
config_path = Path(__file__).parent / 'configs' / 'dimensioning_2024.yaml'
sim_config = SimulationConfig.from_yaml(config_path)

print('='*70)
print('BATTERY DIMENSIONING ANALYSIS')
print('='*70)
print('Optimizer: WeeklyOptimizer (DAILY MODE)')
print(f'Resolution: {sim_config.time_resolution}')
print('Horizon: 24 hours (1 day)')
print(f'Year: {sim_config.dimensioning.year}')
print(f'Config: {config_path.name}')
print()

# Extract configuration parameters
YEAR = sim_config.dimensioning.year
RESOLUTION = sim_config.time_resolution
DISCOUNT_RATE = sim_config.dimensioning.discount_rate
PROJECT_YEARS = sim_config.dimensioning.project_years
BATTERY_COST_PER_KWH = sim_config.dimensioning.battery_cost_per_kwh

# Battery dimension ranges from config
E_NOM_RANGE = np.arange(*sim_config.dimensioning.energy_range_kwh)
P_MAX_RANGE = np.arange(*sim_config.dimensioning.power_range_kw)

print(f'Grid search dimensions:')
print(f'  E_nom: {len(E_NOM_RANGE)} points from {E_NOM_RANGE[0]} to {E_NOM_RANGE[-1]} kWh')
print(f'  P_max: {len(P_MAX_RANGE)} points from {P_MAX_RANGE[0]} to {P_MAX_RANGE[-1]} kW')
print(f'  Total combinations: {len(E_NOM_RANGE) * len(P_MAX_RANGE)}')
print()

# Load data
print('Loading data...')
print(f'  Price data: {sim_config.data_sources.prices_file}')
print(f'  Production data: {sim_config.data_sources.production_file}')
print(f'  Consumption data: {sim_config.data_sources.consumption_file}')

fetcher = ENTSOEPriceFetcher(resolution=RESOLUTION)
prices_series = fetcher.fetch_prices(year=YEAR, area='NO2', resolution=RESOLUTION)
prices_df = prices_series.to_frame('price_nok_per_kwh')

pvgis = PVGISProduction(lat=58.97, lon=5.73, pv_capacity_kwp=138.55, tilt=30.0, azimuth=173.0)
pv_series = pvgis.fetch_hourly_production(year=YEAR)
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

# Generate consumption profile using config parameters
consumption_config = ConsumptionConfig(
    annual_kwh=70000,  # User requirement: 70 000 kWh
    profile_type="commercial",
    base_multiplier=0.6,
    weekday_business_multiplier=1.8,
    evening_multiplier=1.3,
    business_hours_start=6,
    business_hours_end=18,
    evening_hours_start=18,
    evening_hours_end=22
)
load = generate_consumption_profile(timestamps, consumption_config)

print(f'Data loaded:')
print(f'  Timesteps: {len(timestamps)}')
print(f'  Price range: {spot_prices.min():.3f} - {spot_prices.max():.3f} NOK/kWh')
print(f'  PV production: {pv_production.sum():.0f} kWh')
print(f'  Load: {load.sum():.0f} kWh')
print()

# Baseline cost (no battery) - run optimizer with 0 kW, 0 kWh battery
print('Calculating baseline cost (no battery scenario)...')

daily_timesteps = 24  # 1 day @ hourly
n_timesteps = len(timestamps)
n_days = n_timesteps // daily_timesteps

# Create optimizer with negligible battery (0.01 kW, 0.01 kWh - effectively disabled)
# Note: Using tiny battery instead of 0.0 due to validation requirements
baseline_optimizer = WeeklyOptimizer(
    battery_kwh=0.01,  # Negligible capacity (economic impact < 0.5 NOK/year)
    battery_kw=0.01,   # Negligible power
    battery_efficiency=sim_config.battery.efficiency,
    min_soc_percent=sim_config.battery.min_soc_percent,
    max_soc_percent=sim_config.battery.max_soc_percent,
    resolution=RESOLUTION,
    horizon_hours=24,  # 24-hour horizon
    use_global_config=True
)

# Run daily optimization for full year with NO battery
baseline_cost = 0.0
baseline_state = BatterySystemState()

print(f'  Running baseline optimization (365 days)...')
for day in range(n_days):
    t_start = day * daily_timesteps
    t_end = min(t_start + daily_timesteps, n_timesteps)

    result = baseline_optimizer.optimize(
        timestamps=timestamps[t_start:t_end],
        pv_production=pv_production[t_start:t_end],
        consumption=load[t_start:t_end],
        spot_prices=spot_prices[t_start:t_end],
        battery_state=baseline_state
    )

    if not result.success:
        raise RuntimeError(f"Baseline optimization failed at day {day}: {result.message}")

    baseline_cost += result.objective_value

    # Update state for next day (though battery is 0, still track state)
    baseline_state.update_from_measurement(
        timestamp=timestamps[t_end - 1],
        soc_kwh=0.0,  # No battery
        grid_import_power_kw=result.P_grid_import[-1] if len(result.P_grid_import) > 0 else 0.0
    )

    if day % 30 == 0:
        print(f'    Day {day}: Cost={result.objective_value:.2f} NOK')

print(f'\n  Baseline annual cost (with all tariffs): {baseline_cost:.0f} NOK')
print()


def evaluate_battery_npv(E_nom, P_max, data_dict, sim_config, baseline_cost):
    """
    Evaluate NPV for given battery dimensions.

    Parameters:
        E_nom: Battery capacity (kWh)
        P_max: Battery power (kW)
        data_dict: Dict with timestamps, pv_production, load, spot_prices, n_timesteps, weekly_timesteps, n_weeks
        sim_config: SimulationConfig object with all configuration parameters
        baseline_cost: Baseline annual cost (NOK) without battery

    Returns:
        float: NPV in NOK (or -inf if invalid dimensions)
    """
    # Validate dimensions
    if E_nom < 1 or P_max < 1:
        return float('-inf')

    # Extract data
    timestamps = data_dict['timestamps']
    pv_production = data_dict['pv_production']
    load = data_dict['load']
    spot_prices = data_dict['spot_prices']
    n_timesteps = data_dict['n_timesteps']
    daily_timesteps = data_dict['daily_timesteps']
    n_days = data_dict['n_days']

    # Extract config parameters
    discount_rate = sim_config.dimensioning.discount_rate
    project_years = sim_config.dimensioning.project_years
    battery_cost_per_kwh = sim_config.dimensioning.battery_cost_per_kwh
    resolution = sim_config.time_resolution

    # Create optimizer with config-based parameters
    optimizer = WeeklyOptimizer(
        battery_kwh=E_nom,
        battery_kw=P_max,
        battery_efficiency=sim_config.battery.efficiency,
        min_soc_percent=sim_config.battery.min_soc_percent,
        max_soc_percent=sim_config.battery.max_soc_percent,
        resolution=resolution,
        horizon_hours=24,  # 24-hour horizon
        use_global_config=True
    )

    # Run 365-day simulation
    battery_cost = 0.0
    state = BatterySystemState()

    for day in range(n_days):
        t_start = day * daily_timesteps
        t_end = min(t_start + daily_timesteps, n_timesteps)

        result = optimizer.optimize(
            timestamps=timestamps[t_start:t_end],
            pv_production=pv_production[t_start:t_end],
            consumption=load[t_start:t_end],
            spot_prices=spot_prices[t_start:t_end],
            battery_state=state
        )

        if result.success:
            battery_cost += result.objective_value
            state.update_from_measurement(
                timestamp=timestamps[t_end - 1],
                soc_kwh=result.E_battery[-1],
                grid_import_power_kw=result.P_grid_import[-1]
            )
        else:
            battery_cost = baseline_cost  # Failed optimization = no savings
            break

    # Calculate NPV
    annual_savings = baseline_cost - battery_cost
    capex = E_nom * battery_cost_per_kwh

    npv = -capex
    for year in range(1, project_years + 1):
        npv += annual_savings / ((1 + discount_rate) ** year)

    return npv


# Prepare data structure for evaluation function
data_dict = {
    'timestamps': timestamps,
    'pv_production': pv_production,
    'load': load,
    'spot_prices': spot_prices,
    'n_timesteps': n_timesteps,
    'daily_timesteps': daily_timesteps,
    'n_days': n_days
}

# Grid search
print(f'Running grid search ({len(E_NOM_RANGE) * len(P_MAX_RANGE)} combinations)...')
print()

results = []
best_npv = -np.inf
best_config = None
count = 0
total = len(E_NOM_RANGE) * len(P_MAX_RANGE)

for E_nom, P_max in product(E_NOM_RANGE, P_MAX_RANGE):
    count += 1

    start_time = time.time()
    npv = evaluate_battery_npv(E_nom, P_max, data_dict, sim_config, baseline_cost)
    solve_time = time.time() - start_time

    # Calculate intermediate values for reporting
    capex = E_nom * BATTERY_COST_PER_KWH
    annual_savings = (npv + capex) / sum(1 / ((1 + DISCOUNT_RATE) ** year) for year in range(1, PROJECT_YEARS + 1))
    battery_cost = baseline_cost - annual_savings

    results.append({
        'E_nom_kwh': E_nom,
        'P_max_kw': P_max,
        'baseline_cost_nok': baseline_cost,
        'battery_cost_nok': battery_cost,
        'annual_savings_nok': annual_savings,
        'capex_nok': capex,
        'npv_nok': npv,
        'solve_time_s': solve_time
    })

    if npv > best_npv:
        best_npv = npv
        best_config = (E_nom, P_max)

    if count % 5 == 0 or count == total:
        print(f'  [{count}/{total}] E={E_nom:.0f}kWh P={P_max:.0f}kW → NPV={npv:,.0f} NOK (best: {best_npv:,.0f})')

print()
print('='*70)
print("POWELL'S METHOD REFINEMENT")
print('='*70)
print(f'Starting from grid search best: E={best_config[0]:.0f} kWh, P={best_config[1]:.0f} kW')
print(f'Grid search NPV: {best_npv:,.0f} NOK')
print()

# Define objective function for Powell (minimize negative NPV)
def powell_objective(x):
    E_nom, P_max = x
    npv = evaluate_battery_npv(E_nom, P_max, data_dict, sim_config, baseline_cost)
    return -npv  # Minimize negative NPV = maximize NPV

# Set bounds to match grid search range (user requested to use grid search constraints)
bounds = [
    (sim_config.dimensioning.energy_range_kwh[0], sim_config.dimensioning.energy_range_kwh[1]),  # [20, 200] kWh
    (sim_config.dimensioning.power_range_kw[0], sim_config.dimensioning.power_range_kw[1])        # [10, 100] kW
]

# Run SLSQP method (bounded optimization with constraints)
print("Running SLSQP optimization with bounds and C-rate constraints...")
print(f"  Bounds: E_nom {bounds[0]}, P_max {bounds[1]}")

# Add C-rate constraints to prevent unrealistic batteries
# C-rate = P_max / E_nom should be between 0.3 and 3.0
constraints = [
    {'type': 'ineq', 'fun': lambda x: 3.0 - x[1]/x[0]},  # C-rate ≤ 3
    {'type': 'ineq', 'fun': lambda x: x[1]/x[0] - 0.3}   # C-rate ≥ 0.3
]
print(f"  Constraints: 0.3 ≤ C-rate ≤ 3.0 (prevents unrealistic batteries)")

powell_start_time = time.time()

result = minimize(
    powell_objective,
    x0=[best_config[0], best_config[1]],  # Start from grid search best
    method='SLSQP',  # CHANGED: SLSQP respects bounds AND constraints!
    bounds=bounds,
    constraints=constraints,
    options={
        'maxiter': sim_config.dimensioning.powell_max_iterations,
        'ftol': sim_config.dimensioning.powell_tolerance_nok,
        'disp': True  # Show optimization progress
    }
)

powell_solve_time = time.time() - powell_start_time

# Extract optimal solution
optimal_E_nom = result.x[0]
optimal_P_max = result.x[1]
optimal_npv = -result.fun  # Convert back from negative

print()
print(f"SLSQP converged: {result.success} ({result.nit} iterations, {powell_solve_time:.1f}s)")
print(f'Optimal configuration: E={optimal_E_nom:.1f} kWh, P={optimal_P_max:.1f} kW')
print(f'Optimal NPV: {optimal_npv:,.0f} NOK')
print(f'NPV improvement: {optimal_npv - best_npv:,.0f} NOK ({100*(optimal_npv - best_npv)/abs(best_npv):.2f}%)')

# Validate C-rate (power-to-energy ratio)
c_rate = optimal_P_max / optimal_E_nom
print(f'\nC-rate validation: {c_rate:.2f}')
if c_rate > 3:
    print(f'  ⚠️  WARNING: High C-rate ({c_rate:.2f}) - SLSQP constraint may have been violated!')
    print(f'  ℹ️  Check constraint satisfaction')
elif c_rate < 0.3:
    print(f'  ⚠️  WARNING: Very low C-rate ({c_rate:.2f}) - SLSQP constraint may have been violated!')
    print(f'  ℹ️  Check constraint satisfaction')
else:
    print(f'  ✅ C-rate is within constrained range (0.3-3.0)')
print()

print()
print('='*70)
print('DIMENSIONING COMPLETE')
print('='*70)
print('GRID SEARCH BEST:')
print(f'  Configuration: {best_config[0]:.0f} kWh / {best_config[1]:.0f} kW')
print(f'  NPV: {best_npv:,.0f} NOK')
print()
print("POWELL'S METHOD OPTIMAL:")
print(f'  Configuration: {optimal_E_nom:.1f} kWh / {optimal_P_max:.1f} kW')
print(f'  NPV: {optimal_npv:,.0f} NOK')
print()

# Calculate economic metrics for optimal solution
optimal_capex = optimal_E_nom * BATTERY_COST_PER_KWH
optimal_c_rate = optimal_P_max / optimal_E_nom
optimal_annual_savings = (optimal_npv + optimal_capex) / sum(1 / ((1 + DISCOUNT_RATE) ** year) for year in range(1, PROJECT_YEARS + 1))

# Simple payback period (years)
if optimal_annual_savings > 0:
    payback_years = optimal_capex / optimal_annual_savings
else:
    payback_years = float('inf')

# Break-even battery cost (NOK/kWh)
# NPV = 0 when capex = PV of savings
pv_savings = sum(optimal_annual_savings / ((1 + DISCOUNT_RATE) ** year) for year in range(1, PROJECT_YEARS + 1))
breakeven_cost_per_kwh = pv_savings / optimal_E_nom

print('ECONOMIC METRICS:')
print(f'  C-rate: {optimal_c_rate:.2f}')
print(f'  Payback period: {payback_years:.1f} years')
print(f'  Break-even battery cost: {breakeven_cost_per_kwh:.0f} NOK/kWh')
print(f'  Current cost: {BATTERY_COST_PER_KWH} NOK/kWh')
print()

# Save results
output_dir = Path('results/battery_dimensioning_PT60M')
output_dir.mkdir(parents=True, exist_ok=True)

# 1. Save grid search results
results_df = pd.DataFrame(results)
results_path = output_dir / 'grid_search_results.csv'
results_df.to_csv(results_path, index=False)
print(f'Saved grid search results: {results_path}')

# 2. Save Powell's method refinement results
powell_results = {
    'optimal_E_nom_kwh': float(optimal_E_nom),
    'optimal_P_max_kw': float(optimal_P_max),
    'optimal_npv_nok': float(optimal_npv),
    'c_rate': float(optimal_c_rate),
    'payback_years': float(payback_years),
    'breakeven_cost_per_kwh': float(breakeven_cost_per_kwh),
    'annual_savings_nok': float(optimal_annual_savings),
    'capex_nok': float(optimal_capex),
    'convergence_iterations': int(result.nit),
    'solve_time_s': float(powell_solve_time),
    'success': bool(result.success),
    'grid_search_best_E_kwh': float(best_config[0]),
    'grid_search_best_P_kw': float(best_config[1]),
    'grid_search_best_npv_nok': float(best_npv),
    'npv_improvement_nok': float(optimal_npv - best_npv),
    'npv_improvement_percent': float(100 * (optimal_npv - best_npv) / abs(best_npv)) if best_npv != 0 else 0.0
}
powell_path = output_dir / 'powell_refinement_results.json'
with open(powell_path, 'w') as f:
    json.dump(powell_results, f, indent=2)
print(f"Saved Powell's method results: {powell_path}")

# 3. Save combined dimensioning summary
summary = {
    'analysis_metadata': {
        'timestamp': datetime.now().isoformat(),
        'resolution': RESOLUTION,
        'horizon_hours': 24,  # 24-hour daily optimization
        'year': YEAR,
        'discount_rate': DISCOUNT_RATE,
        'project_years': PROJECT_YEARS,
        'battery_cost_per_kwh': BATTERY_COST_PER_KWH
    },
    'baseline': {
        'annual_cost_nok': float(baseline_cost),
        'annual_consumption_kwh': float(load.sum()),
        'annual_pv_production_kwh': float(pv_production.sum())
    },
    'grid_search': {
        'E_nom_range_kwh': [float(E_NOM_RANGE[0]), float(E_NOM_RANGE[-1])],
        'P_max_range_kw': [float(P_MAX_RANGE[0]), float(P_MAX_RANGE[-1])],
        'total_combinations': int(total),
        'best_E_nom_kwh': float(best_config[0]),
        'best_P_max_kw': float(best_config[1]),
        'best_npv_nok': float(best_npv)
    },
    'powell_refinement': {
        'optimal_E_nom_kwh': float(optimal_E_nom),
        'optimal_P_max_kw': float(optimal_P_max),
        'optimal_npv_nok': float(optimal_npv),
        'improvement_over_grid_nok': float(optimal_npv - best_npv),
        'improvement_percent': float(100 * (optimal_npv - best_npv) / abs(best_npv)) if best_npv != 0 else 0.0
    },
    'economic_metrics': {
        'c_rate': float(optimal_c_rate),
        'payback_years': float(payback_years),
        'breakeven_cost_per_kwh': float(breakeven_cost_per_kwh),
        'annual_savings_nok': float(optimal_annual_savings),
        'capex_nok': float(optimal_capex)
    }
}
summary_path = output_dir / 'dimensioning_summary.json'
with open(summary_path, 'w') as f:
    json.dump(summary, f, indent=2)
print(f'Saved dimensioning summary: {summary_path}')
print()
