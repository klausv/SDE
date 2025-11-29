#!/usr/bin/env python3
"""
Battery dimensioning with SLSQP (bounds + C-rate constraints)

This version uses SLSQP instead of Powell to properly handle:
1. Bounds on battery size (E_nom, P_max)
2. Explicit C-rate constraints (P_max/E_nom must be realistic)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
import time
import json
from scipy.optimize import minimize
from datetime import datetime

from src.optimization.weekly_optimizer import WeeklyOptimizer
from core.price_fetcher import ENTSOEPriceFetcher
from core.pvgis_solar import PVGISProduction
from src.operational.state_manager import BatterySystemState
from src.config.simulation_config import SimulationConfig

# Load config
sim_config = SimulationConfig.from_yaml('configs/dimensioning_2024.yaml')

print("="*70)
print("BATTERY DIMENSIONING WITH SLSQP (Constrained Optimization)")
print("="*70)
print(f"Year: {sim_config.base.year}")
print(f"Resolution: {sim_config.base.resolution}")
print(f"Location: {sim_config.location.name}")
print(f"Battery cost: {sim_config.economics.battery_cost_per_kwh_nok:,.0f} NOK/kWh")
print("="*70)

# Load data (same as original script)
print("\nLoading data...")
year = sim_config.base.year
resolution = sim_config.base.resolution

# Prices
price_fetcher = ENTSOEPriceFetcher(resolution=resolution)
prices_series = price_fetcher.fetch_prices(year=year, area='NO2', resolution=resolution)
prices_df = prices_series.to_frame('price_nok_per_kwh')
timestamps = prices_df.index
spot_prices = prices_df['price_nok_per_kwh'].values

# Solar production
pvgis = PVGISProduction(
    lat=sim_config.location.latitude,
    lon=sim_config.location.longitude,
    pv_capacity_kwp=sim_config.pv.capacity_kwp,
    tilt=sim_config.pv.tilt,
    azimuth=sim_config.pv.azimuth
)
pvgis_series = pvgis.fetch_hourly_production(year=year)
pv_production = np.zeros(len(timestamps))
for i, ts in enumerate(timestamps):
    matching = pvgis_series[
        (pvgis_series.index.month == ts.month) &
        (pvgis_series.index.day == ts.day) &
        (pvgis_series.index.hour == ts.hour)
    ]
    if len(matching) > 0:
        pv_production[i] = matching.values[0]

# Consumption
consumption = generate_commercial_consumption_profile(
    timestamps=timestamps,
    annual_consumption_kwh=sim_config.load.annual_consumption_kwh
)

print(f"  Loaded {len(timestamps)} timesteps")
print(f"  PV production: {pv_production.sum():.0f} kW·h")
print(f"  Consumption: {consumption.sum():.0f} kW·h")

# Calculate baseline cost (no battery)
print("\nCalculating baseline (no battery)...")
optimizer_baseline = RollingHorizonOptimizer(
    config=sim_config,
    battery_kwh=0.0,
    battery_kw=0.0,
    horizon_hours=sim_config.optimization.horizon_hours
)

baseline_state = BatterySystemState(
    battery_capacity_kwh=0.0,
    current_soc_kwh=0.0,
    current_monthly_peak_kw=0.0,
    month_start_date=timestamps[0],
    power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(sim_config.tariff)
)

baseline_cost = 0.0
for month in range(1, 13):
    month_mask = timestamps.month == month
    month_data = {
        'timestamps': timestamps[month_mask],
        'spot_prices': spot_prices[month_mask],
        'pv_production': pv_production[month_mask],
        'load_consumption': consumption[month_mask]
    }

    result = optimizer_baseline.optimize_window(
        current_state=baseline_state,
        pv_production=month_data['pv_production'],
        load_consumption=month_data['load_consumption'],
        spot_prices=month_data['spot_prices'],
        timestamps=month_data['timestamps'],
        verbose=False
    )

    if result.success:
        baseline_cost += result.objective_value
        baseline_state.update_from_measurement(
            timestamp=month_data['timestamps'][-1],
            soc_kwh=0.0,
            grid_import_power_kw=0.0
        )

print(f"Baseline annual cost (no battery): {baseline_cost:,.0f} NOK")

# Grid search (same as before)
print("\n" + "="*70)
print("GRID SEARCH")
print("="*70)

# Use grid search parameters from config (should match dimensioning_2024.yaml)
# energy_range_kwh: [20, 201, 30] means start=20, stop=201, step=30
# This gives: 20, 50, 80, 110, 140, 170, 200 (7 points)
E_range = np.arange(
    sim_config.dimensioning.grid_energy_range_kwh[0],
    sim_config.dimensioning.grid_energy_range_kwh[1],
    sim_config.dimensioning.grid_energy_range_kwh[2]
)
P_range = np.arange(
    sim_config.dimensioning.grid_power_range_kw[0],
    sim_config.dimensioning.grid_power_range_kw[1],
    sim_config.dimensioning.grid_power_range_kw[2]
)

print(f"E_nom: {E_range[0]:.0f} - {E_range[-1]:.0f} kWh ({len(E_range)} points)")
print(f"P_max: {P_range[0]:.0f} - {P_range[-1]:.0f} kW ({len(P_range)} points)")
print(f"Total: {len(E_range) * len(P_range)} configurations")

grid_results = []
best_npv = -np.inf
best_config = None

for E_nom in E_range:
    for P_max in P_range:
        optimizer = RollingHorizonOptimizer(
            config=sim_config,
            battery_kwh=E_nom,
            battery_kw=P_max,
            horizon_hours=sim_config.optimization.horizon_hours
        )

        state = BatterySystemState(
            battery_capacity_kwh=E_nom,
            current_soc_kwh=E_nom * 0.5,
            current_monthly_peak_kw=0.0,
            month_start_date=timestamps[0],
            power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(sim_config.tariff)
        )

        battery_cost = 0.0
        for month in range(1, 13):
            month_mask = timestamps.month == month
            month_data = {
                'timestamps': timestamps[month_mask],
                'spot_prices': spot_prices[month_mask],
                'pv_production': pv_production[month_mask],
                'load_consumption': consumption[month_mask]
            }

            result = optimizer.optimize_window(
                current_state=state,
                pv_production=month_data['pv_production'],
                load_consumption=month_data['load_consumption'],
                spot_prices=month_data['spot_prices'],
                timestamps=month_data['timestamps'],
                verbose=False
            )

            if not result.success:
                battery_cost = np.inf
                break

            battery_cost += result.objective_value
            state.update_from_measurement(
                timestamp=month_data['timestamps'][-1],
                soc_kwh=result.E_battery_final,
                grid_import_power_kw=result.P_grid_import[-1] if len(result.P_grid_import) > 0 else 0.0
            )

        annual_savings = baseline_cost - battery_cost
        capex = E_nom * sim_config.economics.battery_cost_per_kwh_nok

        # Calculate NPV
        discount_rate = sim_config.economics.discount_rate
        project_years = sim_config.economics.project_lifetime_years
        npv = -capex
        for year in range(1, project_years + 1):
            npv += annual_savings / (1 + discount_rate) ** year

        grid_results.append({
            'E_nom_kwh': E_nom,
            'P_max_kw': P_max,
            'annual_savings_nok': annual_savings,
            'capex_nok': capex,
            'npv_nok': npv
        })

        if npv > best_npv:
            best_npv = npv
            best_config = (E_nom, P_max)

print(f"\nGrid search complete!")
print(f"Best configuration: E={best_config[0]:.0f} kWh, P={best_config[1]:.0f} kW")
print(f"Best NPV: {best_npv:,.0f} NOK")

# SLSQP refinement with constraints
print("\n" + "="*70)
print("SLSQP REFINEMENT (With C-rate Constraints)")
print("="*70)

# Define objective function
def objective(x):
    E_nom, P_max = x

    optimizer = RollingHorizonOptimizer(
        config=sim_config,
        battery_kwh=E_nom,
        battery_kw=P_max,
        horizon_hours=sim_config.optimization.horizon_hours
    )

    state = BatterySystemState(
        battery_capacity_kwh=E_nom,
        current_soc_kwh=E_nom * 0.5,
        current_monthly_peak_kw=0.0,
        month_start_date=timestamps[0],
        power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(sim_config.tariff)
    )

    battery_cost = 0.0
    for month in range(1, 13):
        month_mask = timestamps.month == month
        month_data = {
            'timestamps': timestamps[month_mask],
            'spot_prices': spot_prices[month_mask],
            'pv_production': pv_production[month_mask],
            'load_consumption': consumption[month_mask]
        }

        result = optimizer.optimize_window(
            current_state=state,
            pv_production=month_data['pv_production'],
            load_consumption=month_data['load_consumption'],
            spot_prices=month_data['spot_prices'],
            timestamps=month_data['timestamps'],
            verbose=False
        )

        if not result.success:
            return 1e10  # Large penalty for infeasible

        battery_cost += result.objective_value
        state.update_from_measurement(
            timestamp=month_data['timestamps'][-1],
            soc_kwh=result.E_battery_final,
            grid_import_power_kw=result.P_grid_import[-1] if len(result.P_grid_import) > 0 else 0.0
        )

    annual_savings = baseline_cost - battery_cost
    capex = E_nom * sim_config.economics.battery_cost_per_kwh_nok

    discount_rate = sim_config.economics.discount_rate
    project_years = sim_config.economics.project_lifetime_years
    npv = -capex
    for year in range(1, project_years + 1):
        npv += annual_savings / (1 + discount_rate) ** year

    return -npv  # Minimize negative NPV

# Define bounds - USE GRID SEARCH BOUNDS (not Powell bounds)
bounds = [
    (sim_config.dimensioning.grid_energy_range_kwh[0],   # 20 kWh minimum
     sim_config.dimensioning.grid_energy_range_kwh[1]),  # 200 kWh maximum
    (sim_config.dimensioning.grid_power_range_kw[0],     # 10 kW minimum
     sim_config.dimensioning.grid_power_range_kw[1])     # 100 kW maximum
]

# Define C-rate constraints
constraints = [
    {'type': 'ineq', 'fun': lambda x: 3.0 - x[1]/x[0]},  # C-rate ≤ 3
    {'type': 'ineq', 'fun': lambda x: x[1]/x[0] - 0.3}   # C-rate ≥ 0.3
]

print(f"Bounds: E_nom {bounds[0]}, P_max {bounds[1]}")
print(f"Constraints:")
print(f"  C-rate ≥ 0.3 (prevent oversized battery)")
print(f"  C-rate ≤ 3.0 (prevent unrealistic power)")
print(f"\nStarting from grid search best: E={best_config[0]:.0f} kWh, P={best_config[1]:.0f} kW")

slsqp_start = time.time()

result = minimize(
    objective,
    x0=[best_config[0], best_config[1]],
    method='SLSQP',
    bounds=bounds,
    constraints=constraints,
    options={
        'maxiter': 100,
        'ftol': 1e-6,
        'disp': True
    }
)

slsqp_time = time.time() - slsqp_start

optimal_E = result.x[0]
optimal_P = result.x[1]
optimal_npv = -result.fun
c_rate = optimal_P / optimal_E

print("\n" + "="*70)
print("SLSQP RESULTS")
print("="*70)
print(f"Converged: {result.success}")
print(f"Iterations: {result.nit}")
print(f"Time: {slsqp_time:.1f}s")
print(f"\nOptimal configuration:")
print(f"  E_nom: {optimal_E:.2f} kWh")
print(f"  P_max: {optimal_P:.2f} kW")
print(f"  C-rate: {c_rate:.2f}")
print(f"  NPV: {optimal_npv:,.0f} NOK")
print(f"\nImprovement over grid search:")
print(f"  NPV: {optimal_npv - best_npv:+,.0f} NOK ({100*(optimal_npv - best_npv)/abs(best_npv):+.2f}%)")

# C-rate validation
print(f"\nC-rate validation:")
if c_rate > 3:
    print(f"  ❌ C-rate {c_rate:.2f} exceeds constraint (should be ≤3.0)")
elif c_rate < 0.3:
    print(f"  ❌ C-rate {c_rate:.2f} below constraint (should be ≥0.3)")
else:
    print(f"  ✅ C-rate {c_rate:.2f} is within acceptable range [0.3, 3.0]")

# Save results
output_dir = Path('results/battery_dimensioning_SLSQP')
output_dir.mkdir(parents=True, exist_ok=True)

results = {
    'timestamp': datetime.now().isoformat(),
    'method': 'SLSQP',
    'baseline_cost_nok': baseline_cost,
    'grid_search': {
        'best_E_kwh': best_config[0],
        'best_P_kw': best_config[1],
        'best_npv_nok': best_npv
    },
    'slsqp_refinement': {
        'optimal_E_kwh': optimal_E,
        'optimal_P_kw': optimal_P,
        'optimal_npv_nok': optimal_npv,
        'c_rate': c_rate,
        'converged': result.success,
        'iterations': result.nit,
        'solve_time_s': slsqp_time
    },
    'improvement': {
        'npv_nok': optimal_npv - best_npv,
        'npv_percent': 100 * (optimal_npv - best_npv) / abs(best_npv)
    }
}

with open(output_dir / 'slsqp_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n✓ Results saved to: {output_dir / 'slsqp_results.json'}")
print("="*70)
