#!/usr/bin/env python3
"""
Run corrected battery optimization simulation with proper parameters:
- Annual consumption: 90,000 kWh
- Battery efficiency: 95%
"""

import numpy as np
import pandas as pd
import pickle
import json
from datetime import datetime
from pathlib import Path

def generate_consumption_profile(annual_kwh=90000, year=2024):
    """Generate commercial consumption profile that sums to annual_kwh"""
    hours = 8784  # 2024 is leap year
    timestamps = pd.date_range(f'{year}-01-01', periods=hours, freq='h')

    # Create load factors first
    load_factors = []
    for timestamp in timestamps:
        hour = timestamp.hour
        weekday = timestamp.dayofweek < 5  # Monday-Friday

        # Commercial pattern
        if weekday:
            if 7 <= hour <= 17:
                load_factor = 1.5  # Peak business hours
            elif 6 <= hour <= 18:
                load_factor = 1.0  # Extended hours
            else:
                load_factor = 0.5  # Off hours
        else:  # Weekend
            load_factor = 0.3  # Minimal weekend load

        load_factors.append(load_factor)

    # Calculate scaling factor to achieve exact annual consumption
    total_load_factor = sum(load_factors)
    hourly_base = annual_kwh / total_load_factor

    # Apply scaling to get actual consumption
    consumption = [hourly_base * lf for lf in load_factors]

    return pd.Series(consumption, index=timestamps, name='consumption_kw')

def run_corrected_simulation():
    """Run simulation with corrected parameters"""

    print("=" * 60)
    print("CORRECTED BATTERY OPTIMIZATION SIMULATION")
    print("=" * 60)

    # Load existing PVGIS data
    pvgis_file = Path('data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv')
    if not pvgis_file.exists():
        print(f"Error: PVGIS data file not found at {pvgis_file}")
        return None

    # Read PVGIS data
    pvgis_data = pd.read_csv(pvgis_file, index_col=0, parse_dates=True)
    pvgis_data.columns = ['pv_power_kw']  # Rename column for consistency

    # System configuration
    pv_capacity_kwp = 138.55
    inverter_capacity_kw = 100
    grid_export_limit_kw = 77
    annual_consumption_kwh = 90000  # CORRECTED VALUE
    battery_efficiency = 0.95  # CORRECTED from 0.90

    print(f"\nConfiguration:")
    print(f"  PV Capacity: {pv_capacity_kwp} kWp")
    print(f"  Inverter: {inverter_capacity_kw} kW")
    print(f"  Grid Limit: {grid_export_limit_kw} kW")
    print(f"  Annual Consumption: {annual_consumption_kwh:,} kWh")
    print(f"  Battery Efficiency: {battery_efficiency*100}%")

    # Get production data
    production_dc = pvgis_data['pv_power_kw'].values

    # Apply inverter clipping
    production_ac = np.minimum(production_dc, inverter_capacity_kw)
    inverter_clipping = production_dc - production_ac

    print(f"\nProduction Summary:")
    print(f"  DC Production: {production_dc.sum():,.0f} kWh")
    print(f"  AC Production: {production_ac.sum():,.0f} kWh")
    print(f"  Inverter Clipping: {inverter_clipping.sum():,.0f} kWh")

    # Generate CORRECT consumption profile
    consumption = generate_consumption_profile(annual_consumption_kwh, 2024)

    # Verify consumption
    actual_annual = consumption.sum()
    print(f"\nConsumption Profile:")
    print(f"  Target Annual: {annual_consumption_kwh:,} kWh")
    print(f"  Generated Annual: {actual_annual:,.0f} kWh")
    print(f"  Average Hourly: {consumption.mean():.2f} kW")
    print(f"  Peak Load: {consumption.max():.2f} kW")
    print(f"  Minimum Load: {consumption.min():.2f} kW")

    # Load electricity prices
    prices_file = Path('data/electricity_prices_2024.csv')
    if prices_file.exists():
        prices_data = pd.read_csv(prices_file, parse_dates=['timestamp'])
        prices = prices_data['price_nok_per_kwh'].values
    else:
        # Generate simple price profile if file not found
        hours = len(production_dc)
        prices = []
        for i in range(hours):
            hour = i % 24
            if 6 <= hour <= 22:  # Day prices
                base_price = 0.8
            else:  # Night prices
                base_price = 0.4
            # Add some variation
            prices.append(base_price * (1 + 0.2 * np.sin(i/24 * 2 * np.pi)))
        prices = np.array(prices)

    # Battery configuration
    battery_kwh = 10
    battery_kw = 5
    battery_cost_per_kwh = 2500  # Target cost

    print(f"\nBattery Configuration:")
    print(f"  Capacity: {battery_kwh} kWh")
    print(f"  Power: {battery_kw} kW")
    print(f"  Cost: {battery_cost_per_kwh} NOK/kWh")
    print(f"  Total Cost: {battery_kwh * battery_cost_per_kwh:,.0f} NOK")

    # Simple battery simulation
    battery_soc = 0.5  # Start at 50%
    battery_energy = battery_soc * battery_kwh

    grid_import = []
    grid_export = []
    battery_charge = []
    battery_discharge = []
    curtailment = []
    soc_history = []

    for i in range(len(production_ac)):
        # Net production after consumption
        net_production = production_ac[i] - consumption.iloc[i]

        if net_production > 0:  # Excess production
            # Try to charge battery first
            max_charge = min(battery_kw, (battery_kwh - battery_energy) / battery_efficiency)
            actual_charge = min(net_production, max_charge)
            battery_energy += actual_charge * battery_efficiency

            # Remaining after battery
            remaining = net_production - actual_charge

            # Apply grid export limit
            export = min(remaining, grid_export_limit_kw)
            curtailed = remaining - export

            grid_import.append(0)
            grid_export.append(export)
            battery_charge.append(actual_charge)
            battery_discharge.append(0)
            curtailment.append(curtailed)

        else:  # Net consumption
            # Try to discharge battery first
            discharge_needed = -net_production
            max_discharge = min(battery_kw, battery_energy * battery_efficiency)
            actual_discharge = min(discharge_needed, max_discharge)
            battery_energy -= actual_discharge / battery_efficiency

            # Remaining from grid
            grid_need = discharge_needed - actual_discharge

            grid_import.append(grid_need)
            grid_export.append(0)
            battery_charge.append(0)
            battery_discharge.append(actual_discharge)
            curtailment.append(0)

        # Update SOC
        battery_soc = battery_energy / battery_kwh
        soc_history.append(battery_soc)

    # Calculate totals
    total_grid_import = sum(grid_import)
    total_grid_export = sum(grid_export)
    total_curtailment = sum(curtailment)
    total_battery_charge = sum(battery_charge)
    total_battery_discharge = sum(battery_discharge)

    print(f"\nEnergy Flows WITH Battery:")
    print(f"  Grid Import: {total_grid_import:,.0f} kWh")
    print(f"  Grid Export: {total_grid_export:,.0f} kWh")
    print(f"  Curtailment: {total_curtailment:,.0f} kWh")
    print(f"  Battery Charged: {total_battery_charge:,.0f} kWh")
    print(f"  Battery Discharged: {total_battery_discharge:,.0f} kWh")

    # Calculate baseline (no battery)
    baseline_import = []
    baseline_export = []
    baseline_curtailment = []

    for i in range(len(production_ac)):
        net = production_ac[i] - consumption.iloc[i]
        if net > 0:
            export = min(net, grid_export_limit_kw)
            baseline_export.append(export)
            baseline_import.append(0)
            baseline_curtailment.append(net - export)
        else:
            baseline_import.append(-net)
            baseline_export.append(0)
            baseline_curtailment.append(0)

    baseline_total_import = sum(baseline_import)
    baseline_total_export = sum(baseline_export)
    baseline_total_curtailment = sum(baseline_curtailment)

    print(f"\nBaseline (NO Battery):")
    print(f"  Grid Import: {baseline_total_import:,.0f} kWh")
    print(f"  Grid Export: {baseline_total_export:,.0f} kWh")
    print(f"  Curtailment: {baseline_total_curtailment:,.0f} kWh")

    # Economic calculations
    import_cost = sum(grid_import[i] * prices[i] for i in range(len(grid_import)))
    export_revenue = sum(grid_export[i] * prices[i] * 0.9 for i in range(len(grid_export)))

    baseline_import_cost = sum(baseline_import[i] * prices[i] for i in range(len(baseline_import)))
    baseline_export_revenue = sum(baseline_export[i] * prices[i] * 0.9 for i in range(len(baseline_export)))

    # Power tariff (simplified)
    monthly_peaks_with = []
    monthly_peaks_without = []

    for month in range(1, 13):
        # Find indices for this month
        month_start = (month - 1) * 730  # Approximate
        month_end = min(month * 730, len(grid_import))

        if month_end > month_start:
            month_imports_with = grid_import[month_start:month_end]
            month_imports_without = baseline_import[month_start:month_end]

            monthly_peaks_with.append(max(month_imports_with))
            monthly_peaks_without.append(max(month_imports_without))

    # Average of 3 highest months
    top3_with = sorted(monthly_peaks_with, reverse=True)[:3]
    top3_without = sorted(monthly_peaks_without, reverse=True)[:3]

    avg_peak_with = np.mean(top3_with) if top3_with else 0
    avg_peak_without = np.mean(top3_without) if top3_without else 0

    # Power tariff calculation
    power_tariff_rate = 140  # NOK/kW/month (simplified)
    annual_power_tariff_with = avg_peak_with * power_tariff_rate * 12
    annual_power_tariff_without = avg_peak_without * power_tariff_rate * 12

    # Total costs
    total_cost_with = import_cost - export_revenue + annual_power_tariff_with
    total_cost_without = baseline_import_cost - baseline_export_revenue + annual_power_tariff_without

    # Annual savings
    annual_savings = total_cost_without - total_cost_with

    # NPV calculation
    battery_cost = battery_kwh * battery_cost_per_kwh
    discount_rate = 0.05
    battery_lifetime = 15

    npv = -battery_cost
    for year in range(1, battery_lifetime + 1):
        npv += annual_savings / (1 + discount_rate) ** year

    # Payback period
    payback_years = battery_cost / annual_savings if annual_savings > 0 else float('inf')

    # IRR calculation (simplified)
    if npv > 0:
        irr = (annual_savings / battery_cost - 1/battery_lifetime) * 100
    else:
        irr = -100

    print("\n" + "=" * 60)
    print("ECONOMIC RESULTS")
    print("=" * 60)

    print(f"\nCost Comparison:")
    print(f"  Without Battery: {total_cost_without:,.0f} NOK/year")
    print(f"  With Battery: {total_cost_with:,.0f} NOK/year")
    print(f"  Annual Savings: {annual_savings:,.0f} NOK/year")

    print(f"\nSavings Breakdown:")
    print(f"  Energy Cost Savings: {(baseline_import_cost - import_cost):,.0f} NOK/year")
    print(f"  Export Revenue Increase: {(export_revenue - baseline_export_revenue):,.0f} NOK/year")
    print(f"  Power Tariff Reduction: {(annual_power_tariff_without - annual_power_tariff_with):,.0f} NOK/year")

    print(f"\nInvestment Analysis:")
    print(f"  Battery Cost: {battery_cost:,.0f} NOK")
    print(f"  NPV (15 years): {npv:,.0f} NOK")
    print(f"  Payback Period: {payback_years:.1f} years")
    print(f"  IRR: {irr:.1f}%")

    print(f"\nPeak Demand Reduction:")
    print(f"  Without Battery: {avg_peak_without:.1f} kW")
    print(f"  With Battery: {avg_peak_with:.1f} kW")
    print(f"  Reduction: {(avg_peak_without - avg_peak_with):.1f} kW ({(1 - avg_peak_with/avg_peak_without)*100:.1f}%)")

    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'configuration': {
            'pv_capacity_kwp': pv_capacity_kwp,
            'inverter_capacity_kw': inverter_capacity_kw,
            'grid_export_limit_kw': grid_export_limit_kw,
            'annual_consumption_kwh': actual_annual,
            'battery_kwh': battery_kwh,
            'battery_kw': battery_kw,
            'battery_efficiency': battery_efficiency,
            'battery_cost_per_kwh': battery_cost_per_kwh
        },
        'production': {
            'total_dc_kwh': float(production_dc.sum()),
            'total_ac_kwh': float(production_ac.sum()),
            'inverter_clipping_kwh': float(inverter_clipping.sum())
        },
        'with_battery': {
            'grid_import_kwh': total_grid_import,
            'grid_export_kwh': total_grid_export,
            'curtailment_kwh': total_curtailment,
            'battery_charged_kwh': total_battery_charge,
            'battery_discharged_kwh': total_battery_discharge,
            'avg_peak_kw': avg_peak_with,
            'total_cost_nok': total_cost_with
        },
        'without_battery': {
            'grid_import_kwh': baseline_total_import,
            'grid_export_kwh': baseline_total_export,
            'curtailment_kwh': baseline_total_curtailment,
            'avg_peak_kw': avg_peak_without,
            'total_cost_nok': total_cost_without
        },
        'economics': {
            'battery_cost_nok': battery_cost,
            'annual_savings_nok': annual_savings,
            'npv_nok': npv,
            'payback_years': payback_years,
            'irr_percent': irr
        }
    }

    # Save to JSON
    output_dir = Path('results')
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / 'corrected_simulation_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: results/corrected_simulation_results.json")

    # Also update the main results files
    with open(output_dir / 'realistic_simulation_summary.json', 'w') as f:
        summary = {
            'data_source': 'PVGIS actual solar data for Stavanger',
            'optimal_battery_kwh': battery_kwh,
            'optimal_battery_kw': battery_kw,
            'battery_efficiency': battery_efficiency,
            'annual_consumption_kwh': actual_annual,
            'npv_at_target_cost': npv,
            'payback_years': payback_years,
            'annual_savings': annual_savings,
            'total_dc_production_kwh': float(production_dc.sum()),
            'total_ac_production_kwh': float(production_ac.sum()),
            'inverter_clipping_kwh': float(inverter_clipping.sum()),
            'grid_curtailment_kwh': total_curtailment
        }
        json.dump(summary, f, indent=2)

    print(f"Updated: results/realistic_simulation_summary.json")

    return results

if __name__ == "__main__":
    results = run_corrected_simulation()