#!/usr/bin/env python3
"""
Run corrected battery optimization simulation with proper parameters:
- Annual consumption: 90,000 kWh
- Battery efficiency: 95%
- Correct consumption profile generation
"""

import numpy as np
import pandas as pd
import pickle
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.append('/mnt/c/Users/klaus/klauspython/offgrid2/battery_optimization')

# Import core modules
from core.pvgis_solar import fetch_pvgis_data
from core.data_generators import generate_consumption_profile, generate_electricity_prices
from core.battery import BatterySimulator

def run_corrected_simulation():
    """Run simulation with corrected parameters"""

    print("Starting corrected simulation...")
    print("-" * 50)

    # System configuration
    system_config = {
        'pv_capacity_kwp': 138.55,  # Actual rated capacity
        'inverter_capacity_kw': 100,
        'grid_export_limit_kw': 77,
        'annual_consumption_kwh': 90000,  # CORRECTED
        'battery_efficiency': 0.95,  # CORRECTED from 0.90 to 0.95
    }

    # Location
    latitude = 58.97
    longitude = 5.73

    print(f"Configuration:")
    print(f"  PV Capacity: {system_config['pv_capacity_kwp']} kWp")
    print(f"  Annual Consumption: {system_config['annual_consumption_kwh']:,} kWh")
    print(f"  Battery Efficiency: {system_config['battery_efficiency']*100}%")

    # 1. Fetch PVGIS data
    print("\n1. Fetching PVGIS solar data...")
    pvgis_data = fetch_pvgis_data(
        latitude=latitude,
        longitude=longitude,
        peakpower=system_config['pv_capacity_kwp']
    )

    # Extract production data
    production_dc = pvgis_data['pv_power_kw'].values  # DC power in kW

    # Apply inverter clipping
    production_ac = np.minimum(production_dc, system_config['inverter_capacity_kw'])
    inverter_clipping = production_dc - production_ac

    print(f"  Total DC Production: {production_dc.sum():,.0f} kWh")
    print(f"  Total AC Production: {production_ac.sum():,.0f} kWh")
    print(f"  Inverter Clipping: {inverter_clipping.sum():,.0f} kWh")

    # 2. Generate consumption profile
    print("\n2. Generating consumption profile...")
    consumption = generate_consumption_profile(
        annual_consumption_kwh=system_config['annual_consumption_kwh'],
        profile_type='commercial',
        year=2024
    )

    # Verify consumption is correct
    actual_annual = consumption.sum()
    print(f"  Generated annual consumption: {actual_annual:,.0f} kWh")
    print(f"  Average hourly consumption: {consumption.mean():.2f} kW")

    # 3. Get electricity prices
    print("\n3. Fetching electricity prices...")
    prices = generate_electricity_prices(year=2024)

    # 4. Run battery optimization
    print("\n4. Running battery optimization...")

    # Test with target cost battery
    battery_kwh = 10
    battery_kw = 5
    battery_cost_per_kwh = 2500

    print(f"  Battery size: {battery_kwh} kWh / {battery_kw} kW")
    print(f"  Cost assumption: {battery_cost_per_kwh} NOK/kWh")

    # Initialize battery simulator
    battery_sim = BatterySimulator(
        capacity_kwh=battery_kwh,
        max_power_kw=battery_kw,
        efficiency=system_config['battery_efficiency'],  # Use 95%
        initial_soc=0.5
    )

    # Run simulation
    grid_import = []
    grid_export = []
    battery_soc = []
    curtailment = []

    for i in range(len(production_ac)):
        # Net production after consumption
        net_production = production_ac[i] - consumption.iloc[i]

        if net_production > 0:  # Excess production
            # Try to charge battery first
            charge_power = min(net_production, battery_kw)
            actual_charge = battery_sim.charge(charge_power, duration_hours=1)

            # Remaining after battery charging
            remaining = net_production - actual_charge

            # Apply grid export limit
            export = min(remaining, system_config['grid_export_limit_kw'])
            curtailed = remaining - export

            grid_export.append(export)
            grid_import.append(0)
            curtailment.append(curtailed)

        else:  # Net consumption
            # Try to discharge battery first
            discharge_needed = -net_production
            discharge_power = min(discharge_needed, battery_kw)
            actual_discharge = battery_sim.discharge(discharge_power, duration_hours=1)

            # Remaining need from grid
            grid_need = discharge_needed - actual_discharge

            grid_import.append(grid_need)
            grid_export.append(0)
            curtailment.append(0)

        battery_soc.append(battery_sim.soc)

    # Calculate economics
    print("\n5. Calculating economics...")

    # Annual values
    total_grid_import = sum(grid_import)
    total_grid_export = sum(grid_export)
    total_curtailment = sum(curtailment)

    # Calculate costs and revenues
    import_cost = sum(grid_import[i] * prices.iloc[i] for i in range(len(grid_import)))
    export_revenue = sum(grid_export[i] * prices.iloc[i] * 0.9 for i in range(len(grid_export)))  # 90% of spot price

    # Power tariff calculation (simplified)
    monthly_peaks = []
    for month in range(1, 13):
        month_mask = pd.DatetimeIndex(consumption.index).month == month
        month_imports = [grid_import[i] for i in range(len(grid_import)) if month_mask[i]]
        if month_imports:
            monthly_peaks.append(max(month_imports))

    avg_monthly_peak = np.mean(monthly_peaks[-3:]) if len(monthly_peaks) >= 3 else np.mean(monthly_peaks)

    # Power tariff brackets (NOK/kW/month)
    if avg_monthly_peak <= 10:
        power_tariff_rate = 150
    elif avg_monthly_peak <= 50:
        power_tariff_rate = 145
    elif avg_monthly_peak <= 200:
        power_tariff_rate = 140
    else:
        power_tariff_rate = 135

    annual_power_tariff = avg_monthly_peak * power_tariff_rate * 12

    # Total annual cost with battery
    total_annual_cost = import_cost - export_revenue + annual_power_tariff

    # Calculate baseline (no battery)
    baseline_import = []
    baseline_export = []
    baseline_curtailment = []

    for i in range(len(production_ac)):
        net = production_ac[i] - consumption.iloc[i]
        if net > 0:
            export = min(net, system_config['grid_export_limit_kw'])
            baseline_export.append(export)
            baseline_import.append(0)
            baseline_curtailment.append(net - export)
        else:
            baseline_import.append(-net)
            baseline_export.append(0)
            baseline_curtailment.append(0)

    baseline_import_cost = sum(baseline_import[i] * prices.iloc[i] for i in range(len(baseline_import)))
    baseline_export_revenue = sum(baseline_export[i] * prices.iloc[i] * 0.9 for i in range(len(baseline_export)))

    # Baseline power tariff
    baseline_monthly_peaks = []
    for month in range(1, 13):
        month_mask = pd.DatetimeIndex(consumption.index).month == month
        month_imports = [baseline_import[i] for i in range(len(baseline_import)) if month_mask[i]]
        if month_imports:
            baseline_monthly_peaks.append(max(month_imports))

    baseline_avg_peak = np.mean(baseline_monthly_peaks[-3:]) if len(baseline_monthly_peaks) >= 3 else np.mean(baseline_monthly_peaks)
    baseline_power_tariff = baseline_avg_peak * power_tariff_rate * 12
    baseline_total_cost = baseline_import_cost - baseline_export_revenue + baseline_power_tariff

    # Annual savings
    annual_savings = baseline_total_cost - total_annual_cost

    # NPV calculation
    battery_cost = battery_kwh * battery_cost_per_kwh
    discount_rate = 0.05
    battery_lifetime = 15

    npv = -battery_cost
    for year in range(1, battery_lifetime + 1):
        discounted_savings = annual_savings / (1 + discount_rate) ** year
        npv += discounted_savings

    # Payback period
    if annual_savings > 0:
        payback_years = battery_cost / annual_savings
    else:
        payback_years = float('inf')

    # Results summary
    results = {
        'data_source': 'PVGIS actual solar data for Stavanger',
        'optimal_battery_kwh': battery_kwh,
        'optimal_battery_kw': battery_kw,
        'battery_efficiency': system_config['battery_efficiency'],
        'annual_consumption_kwh': actual_annual,
        'npv_at_target_cost': npv,
        'payback_years': payback_years,
        'annual_savings': annual_savings,
        'total_dc_production_kwh': production_dc.sum(),
        'total_ac_production_kwh': production_ac.sum(),
        'inverter_clipping_kwh': inverter_clipping.sum(),
        'grid_curtailment_kwh': total_curtailment,
        'total_grid_import_kwh': total_grid_import,
        'total_grid_export_kwh': total_grid_export,
        'baseline_import_kwh': sum(baseline_import),
        'baseline_export_kwh': sum(baseline_export),
        'baseline_curtailment_kwh': sum(baseline_curtailment),
        'avg_monthly_peak_kw': avg_monthly_peak,
        'baseline_avg_peak_kw': baseline_avg_peak,
        'battery_cost_nok': battery_cost,
        'import_cost_reduction': baseline_import_cost - import_cost,
        'export_revenue_increase': export_revenue - baseline_export_revenue,
        'power_tariff_reduction': baseline_power_tariff - annual_power_tariff
    }

    print("\n" + "="*50)
    print("SIMULATION RESULTS")
    print("="*50)
    print(f"\nSystem Performance:")
    print(f"  Annual Consumption: {actual_annual:,.0f} kWh (verified)")
    print(f"  DC Production: {results['total_dc_production_kwh']:,.0f} kWh")
    print(f"  AC Production: {results['total_ac_production_kwh']:,.0f} kWh")
    print(f"  Grid Curtailment: {results['grid_curtailment_kwh']:,.0f} kWh")

    print(f"\nBattery Configuration:")
    print(f"  Size: {battery_kwh} kWh / {battery_kw} kW")
    print(f"  Efficiency: {system_config['battery_efficiency']*100}%")
    print(f"  Cost: {battery_cost_per_kwh:,} NOK/kWh")
    print(f"  Total Cost: {battery_cost:,.0f} NOK")

    print(f"\nEconomic Results:")
    print(f"  NPV: {npv:,.0f} NOK")
    print(f"  Payback Period: {payback_years:.1f} years")
    print(f"  Annual Savings: {annual_savings:,.0f} NOK")

    print(f"\nSavings Breakdown:")
    print(f"  Import Cost Reduction: {results['import_cost_reduction']:,.0f} NOK/year")
    print(f"  Export Revenue Increase: {results['export_revenue_increase']:,.0f} NOK/year")
    print(f"  Power Tariff Reduction: {results['power_tariff_reduction']:,.0f} NOK/year")

    # Save results
    output_dir = Path('results')
    output_dir.mkdir(exist_ok=True)

    # Save summary JSON
    with open(output_dir / 'corrected_simulation_summary.json', 'w') as f:
        # Convert numpy values to Python types for JSON serialization
        json_results = {k: float(v) if isinstance(v, (np.integer, np.floating)) else v
                       for k, v in results.items()}
        json.dump(json_results, f, indent=2)

    # Save detailed results
    detailed_results = {
        'system_config': system_config,
        'results': results,
        'production_dc': production_dc,
        'production_ac': production_ac,
        'consumption': consumption.values,
        'grid_import': grid_import,
        'grid_export': grid_export,
        'battery_soc': battery_soc,
        'curtailment': curtailment,
        'prices': prices.values,
        'timestamp': datetime.now().isoformat()
    }

    with open(output_dir / 'corrected_simulation_results.pkl', 'wb') as f:
        pickle.dump(detailed_results, f)

    print(f"\nResults saved to:")
    print(f"  - results/corrected_simulation_summary.json")
    print(f"  - results/corrected_simulation_results.pkl")

    return results

if __name__ == "__main__":
    results = run_corrected_simulation()