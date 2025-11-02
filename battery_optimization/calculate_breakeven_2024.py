"""
Calculate break-even cost for battery system based on 2024 simulation results.

Compares:
- Reference case (no battery): Grid costs without battery
- Battery case: Grid costs with 30 kWh battery

Calculates:
- Annual savings
- NPV over battery lifetime
- Break-even cost per kWh
- Comparison with market prices
"""

import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from config import BatteryOptimizationConfig, DegradationConfig
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.price_fetcher import ENTSOEPriceFetcher
from core.pvgis_solar import PVGISProduction


def load_real_2024_data():
    """Load real 2024 data"""
    print("\nLoading 2024 data...")

    # Prices
    fetcher = ENTSOEPriceFetcher(resolution='PT60M')
    prices = fetcher.fetch_prices(year=2024, area='NO2')

    # Solar
    pvgis = PVGISProduction(lat=58.97, lon=5.73, pv_capacity_kwp=138.55, tilt=30.0, azimuth=173.0)
    pv_series = pvgis.fetch_hourly_production(year=2024)

    # Load
    timestamps = prices.index
    load = np.zeros(len(timestamps))
    avg_load = 300000 / 8760
    base = avg_load * 0.6

    for i, ts in enumerate(timestamps):
        ts = pd.Timestamp(ts)
        if ts.weekday() < 5 and 6 <= ts.hour < 18:
            load[i] = base * 1.8
        elif 18 <= ts.hour < 22:
            load[i] = base * 1.3
        else:
            load[i] = base

    # Match PV to price timestamps
    pv = np.zeros(len(timestamps))
    for i, ts in enumerate(timestamps):
        ts = pd.Timestamp(ts)
        matching = pv_series.index[
            (pv_series.index.month == ts.month) &
            (pv_series.index.day == ts.day) &
            (pv_series.index.hour == ts.hour)
        ]
        if len(matching) > 0:
            pv[i] = pv_series.loc[matching[0]]

    # Create DataFrame
    data = pd.DataFrame({
        'spot_price': prices.values,
        'pv_production': pv,
        'load': load
    }, index=timestamps)

    return data


def calculate_reference_case(data, config):
    """Calculate costs without battery (reference case)"""
    print("\n" + "="*70)
    print("REFERENCE CASE (NO BATTERY)")
    print("="*70)

    # Simple energy balance: no battery
    # Grid import = max(0, load - pv)
    # Grid export = max(0, pv - load), capped at grid limit

    net = data['pv_production'] - data['load']
    grid_import = np.maximum(0, -net)
    grid_export_uncapped = np.maximum(0, net)
    grid_export = np.minimum(grid_export_uncapped, config.solar.grid_export_limit_kw)
    curtailment = grid_export_uncapped - grid_export

    # Calculate costs
    # Energy cost
    import_cost = grid_import * data['spot_price']
    export_revenue = grid_export * data['spot_price'] * 0.9  # 90% of spot price for export
    energy_cost = np.sum(import_cost) - np.sum(export_revenue)

    # Power tariff (based on monthly peak import)
    data_copy = data.copy()
    data_copy['grid_import'] = grid_import
    data_copy['month'] = data_copy.index.month

    # Calculate monthly peak and power cost
    power_cost = 0
    for month in range(1, 13):
        month_data = data_copy[data_copy['month'] == month]
        peak = month_data['grid_import'].max()

        # Apply power tariff brackets (simplified)
        if peak <= 2:
            power_cost += 136
        elif peak <= 5:
            power_cost += 136 + 96
        elif peak <= 15:
            power_cost += 136 + 96 + 140 * 3
        elif peak <= 50:
            power_cost += 136 + 96 + 140 * 3 + 200 * 5
        elif peak <= 100:
            power_cost += 136 + 96 + 140 * 3 + 200 * 5 + 800 * 3
        else:
            power_cost += 136 + 96 + 140 * 3 + 200 * 5 + 800 * 3 + 2228

    total_cost = energy_cost + power_cost

    print(f"Grid import: {grid_import.sum():,.0f} kWh")
    print(f"Grid export: {grid_export.sum():,.0f} kWh")
    print(f"Curtailment: {curtailment.sum():,.0f} kWh")
    print(f"Peak import: {grid_import.max():.2f} kW")
    print(f"\nCosts:")
    print(f"  Energy cost:  {energy_cost:>12,.2f} NOK")
    print(f"  Power tariff: {power_cost:>12,.2f} NOK")
    print(f"  Total:        {total_cost:>12,.2f} NOK")

    return {
        'energy_cost': energy_cost,
        'power_cost': power_cost,
        'total_cost': total_cost,
        'grid_import_kwh': grid_import.sum(),
        'grid_export_kwh': grid_export.sum(),
        'curtailment_kwh': curtailment.sum(),
        'peak_kw': grid_import.max()
    }


def calculate_battery_case(data, battery_kwh=30, battery_kw=15):
    """Calculate costs with battery"""
    print("\n" + "="*70)
    print(f"BATTERY CASE ({battery_kwh} kWh, {battery_kw} kW)")
    print("="*70)

    # Config with degradation
    config = BatteryOptimizationConfig()
    config.battery.degradation = DegradationConfig(
        enabled=True,
        cycle_life_full_dod=5000,
        calendar_life_years=28.0
    )

    optimizer = MonthlyLPOptimizer(config, resolution='PT60M',
                                   battery_kwh=battery_kwh, battery_kw=battery_kw)

    # Split by month
    data['month'] = data.index.month

    E_initial = battery_kwh * 0.5
    results = []

    total_energy_cost = 0
    total_power_cost = 0
    total_degradation_cost = 0
    total_curtailment_kwh = 0

    for month in range(1, 13):
        month_data = data[data['month'] == month]

        result = optimizer.optimize_month(
            month_idx=month,
            pv_production=month_data['pv_production'].values,
            load_consumption=month_data['load'].values,
            spot_prices=month_data['spot_price'].values,
            timestamps=month_data.index.values,
            E_initial=E_initial
        )

        if not result.success:
            print(f"Month {month}: FAILED")
            continue

        results.append(result)

        # Accumulate
        total_energy_cost += result.energy_cost
        total_power_cost += result.power_cost
        total_degradation_cost += result.degradation_cost
        total_curtailment_kwh += np.sum(result.P_curtail)

        E_initial = result.E_battery_final

    total_cost = total_energy_cost + total_power_cost + total_degradation_cost

    print(f"\nCosts:")
    print(f"  Energy cost:      {total_energy_cost:>12,.2f} NOK")
    print(f"  Power tariff:     {total_power_cost:>12,.2f} NOK")
    print(f"  Degradation cost: {total_degradation_cost:>12,.2f} NOK")
    print(f"  Total:            {total_cost:>12,.2f} NOK")
    print(f"\nCurtailment: {total_curtailment_kwh:,.0f} kWh")

    return {
        'energy_cost': total_energy_cost,
        'power_cost': total_power_cost,
        'degradation_cost': total_degradation_cost,
        'total_cost': total_cost,
        'curtailment_kwh': total_curtailment_kwh,
        'monthly_results': results
    }


def calculate_breakeven(annual_savings, battery_kwh, lifetime_years=15, discount_rate=0.05):
    """
    Calculate break-even battery cost where NPV = 0.

    NPV = -Initial_Cost + Σ(t=1..T) [Annual_Savings / (1+r)^t] = 0

    Solving for Initial_Cost:
    Initial_Cost = Annual_Savings * [(1 - (1+r)^-T) / r]
    """
    if annual_savings <= 0:
        # Return zero or negative break-even cost with proper structure
        annuity_factor = (1 - (1 + discount_rate)**(-lifetime_years)) / discount_rate
        pv_savings = annual_savings * annuity_factor
        breakeven_cost_per_kwh = pv_savings / battery_kwh
        return breakeven_cost_per_kwh, pv_savings, annuity_factor

    # Annuity factor
    annuity_factor = (1 - (1 + discount_rate)**(-lifetime_years)) / discount_rate

    # Total NPV of savings
    pv_savings = annual_savings * annuity_factor

    # Break-even cost per kWh
    breakeven_cost_per_kwh = pv_savings / battery_kwh

    return breakeven_cost_per_kwh, pv_savings, annuity_factor


def main():
    print("\n" + "="*70)
    print("BREAK-EVEN ANALYSIS - 2024")
    print("="*70)

    # Load data
    data = load_real_2024_data()

    # Create config
    config = BatteryOptimizationConfig()

    # 1. Calculate reference case (no battery)
    ref_results = calculate_reference_case(data, config)

    # 2. Calculate battery case (30 kWh, 15 kW)
    battery_kwh = 30
    battery_kw = 15
    batt_results = calculate_battery_case(data, battery_kwh, battery_kw)

    # 3. Calculate savings and break-even
    annual_savings = ref_results['total_cost'] - batt_results['total_cost']

    print("\n" + "="*70)
    print("SAVINGS ANALYSIS")
    print("="*70)
    print(f"\nReference case (no battery):  {ref_results['total_cost']:>12,.2f} NOK")
    print(f"Battery case (30 kWh):        {batt_results['total_cost']:>12,.2f} NOK")
    print(f"Annual savings:               {annual_savings:>12,.2f} NOK")
    print(f"  Energy savings:             {ref_results['energy_cost'] - batt_results['energy_cost']:>12,.2f} NOK")
    print(f"  Power tariff savings:       {ref_results['power_cost'] - batt_results['power_cost']:>12,.2f} NOK")
    print(f"  Degradation cost:           {-batt_results['degradation_cost']:>12,.2f} NOK")

    # Break-even analysis
    lifetime_years = 15
    discount_rate = 0.05

    breakeven_cost, pv_savings, annuity_factor = calculate_breakeven(
        annual_savings, battery_kwh, lifetime_years, discount_rate
    )

    print("\n" + "="*70)
    print("BREAK-EVEN ANALYSIS")
    print("="*70)
    print(f"\nEconomic Parameters:")
    print(f"  Battery size:     {battery_kwh} kWh")
    print(f"  Lifetime:         {lifetime_years} years")
    print(f"  Discount rate:    {discount_rate*100:.0f}%")
    print(f"  Annual savings:   {annual_savings:>12,.2f} NOK/year")
    print(f"  Annuity factor:   {annuity_factor:.4f}")
    print(f"  PV of savings:    {pv_savings:>12,.2f} NOK")

    print(f"\nBreak-Even Analysis:")
    print(f"  Break-even cost:           {breakeven_cost:>8,.0f} NOK/kWh")
    print(f"  Market cost (2025):        {5000:>8,.0f} NOK/kWh")
    print(f"  Cost reduction needed:     {max(0, 5000 - breakeven_cost):>8,.0f} NOK/kWh ({max(0, (1-breakeven_cost/5000)*100):.1f}%)")

    if breakeven_cost >= 5000:
        print(f"\n✅ Battery is economically viable at current market prices!")
        print(f"   NPV at 5000 NOK/kWh: {pv_savings - 5000*battery_kwh:,.0f} NOK")
    else:
        required_reduction = 5000 - breakeven_cost
        print(f"\n⚠ Battery requires {required_reduction:,.0f} NOK/kWh cost reduction for viability")
        print(f"   NPV at 5000 NOK/kWh: {pv_savings - 5000*battery_kwh:,.0f} NOK")

    # System cost analysis
    system_cost = config.battery.get_system_cost_per_kwh(battery_kwh)
    total_investment = system_cost * battery_kwh

    print(f"\nSystem Cost Analysis:")
    print(f"  Battery cells:    {config.battery.battery_cell_cost_nok_per_kwh:>8,.0f} NOK/kWh → {config.battery.battery_cell_cost_nok_per_kwh * battery_kwh:>10,.0f} NOK")
    print(f"  System cost:      {system_cost:>8,.0f} NOK/kWh → {total_investment:>10,.0f} NOK")
    print(f"  Break-even:       {breakeven_cost:>8,.0f} NOK/kWh → {breakeven_cost * battery_kwh:>10,.0f} NOK")

    # Save results to JSON
    results_file = Path(__file__).parent / "results" / "breakeven_analysis_2024.json"
    results_file.parent.mkdir(exist_ok=True)

    results_data = {
        'timestamp': datetime.now().isoformat(),
        'battery': {
            'capacity_kwh': battery_kwh,
            'power_kw': battery_kw
        },
        'reference_case': ref_results,
        'battery_case': {
            'energy_cost': batt_results['energy_cost'],
            'power_cost': batt_results['power_cost'],
            'degradation_cost': batt_results['degradation_cost'],
            'total_cost': batt_results['total_cost'],
            'curtailment_kwh': batt_results['curtailment_kwh']
        },
        'savings': {
            'annual_savings_nok': annual_savings,
            'energy_savings': ref_results['energy_cost'] - batt_results['energy_cost'],
            'power_savings': ref_results['power_cost'] - batt_results['power_cost']
        },
        'breakeven': {
            'lifetime_years': lifetime_years,
            'discount_rate': discount_rate,
            'annuity_factor': annuity_factor,
            'pv_savings_nok': pv_savings,
            'breakeven_cost_per_kwh': breakeven_cost,
            'breakeven_total_cost': breakeven_cost * battery_kwh,
            'market_cost_per_kwh': 5000,
            'market_total_cost': 5000 * battery_kwh,
            'npv_at_market_price': pv_savings - 5000*battery_kwh,
            'viable': breakeven_cost >= 5000
        },
        'system_costs': {
            'battery_cell_cost_per_kwh': config.battery.battery_cell_cost_nok_per_kwh,
            'system_cost_per_kwh': system_cost,
            'total_investment': total_investment
        }
    }

    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)

    print(f"\n✓ Results saved to: {results_file}")

    print("\n" + "="*70)
    print("✓ BREAK-EVEN ANALYSIS COMPLETE")
    print("="*70)

    return results_data


if __name__ == "__main__":
    main()
