"""
Calculate annual break-even battery cost.

Runs optimization for all 12 months with and without battery to determine
the maximum battery cost (NOK/kWh) that makes economic sense given the
annual savings from battery operation.
"""

import numpy as np
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import BatteryOptimizationConfig, DegradationConfig
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.price_fetcher import ENTSOEPriceFetcher
from core.pvgis_solar import PVGISProduction


def create_synthetic_load(timestamps, annual_kwh=300000):
    """Create realistic commercial load profile"""
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

    return load


def optimize_month(month, year, battery_kwh, battery_kw, config):
    """Run optimization for one month"""

    # Load data
    fetcher = ENTSOEPriceFetcher(resolution='PT60M')
    prices_series = fetcher.fetch_prices(year=year, area='NO2', resolution='PT60M')
    prices_df = prices_series.to_frame('price_nok_per_kwh')
    prices_df['month'] = prices_df.index.month
    month_data = prices_df[prices_df['month'] == month].copy()

    timestamps = month_data.index
    spot_prices = month_data['price_nok_per_kwh'].values

    # Solar production
    pvgis = PVGISProduction(lat=58.97, lon=5.73, pv_capacity_kwp=138.55, tilt=30.0, azimuth=173.0)
    pvgis_series = pvgis.fetch_hourly_production(year=year)
    pvgis_data = pvgis_series.to_frame('production_kw')
    pvgis_data.rename(columns={'production_kw': 'pv_power_kw'}, inplace=True)
    pvgis_data['month'] = pvgis_data.index.month
    solar_month = pvgis_data[pvgis_data['month'] == month].copy()

    pv_production = np.zeros(len(timestamps))
    for i, ts in enumerate(timestamps):
        matching = solar_month[
            (solar_month.index.month == ts.month) &
            (solar_month.index.day == ts.day) &
            (solar_month.index.hour == ts.hour)
        ]
        if len(matching) > 0:
            pv_production[i] = matching['pv_power_kw'].values[0]

    # Load profile
    load = create_synthetic_load(timestamps, annual_kwh=300000)

    # Run optimization
    optimizer = MonthlyLPOptimizer(
        config,
        resolution='PT60M',
        battery_kwh=battery_kwh,
        battery_kw=battery_kw
    )

    result = optimizer.optimize_month(
        month_idx=month,
        pv_production=pv_production,
        load_consumption=load,
        spot_prices=spot_prices,
        timestamps=timestamps,
        E_initial=battery_kwh * 0.5 if battery_kwh > 0 else 0
    )

    return result


def calculate_annual_breakeven(battery_kwh=100, battery_kw=50, year=2024, discount_rate=0.05, lifetime_years=15):
    """Calculate break-even battery cost for the full year"""

    print("\n" + "="*70)
    print("ANNUAL BREAK-EVEN BATTERY COST CALCULATION")
    print("="*70)
    print(f"Battery size: {battery_kwh} kWh / {battery_kw} kW")
    print(f"Analysis year: {year}")
    print(f"Discount rate: {discount_rate*100:.1f}%")
    print(f"Battery lifetime: {lifetime_years} years")
    print()

    # Create configs
    config_with_battery = BatteryOptimizationConfig()
    config_with_battery.battery.degradation = DegradationConfig(
        enabled=True,
        cycle_life_full_dod=5000,
        calendar_life_years=28.0
    )

    config_no_battery = BatteryOptimizationConfig()
    config_no_battery.battery.degradation = DegradationConfig(enabled=False)

    # Run all 12 months
    monthly_results = []

    for month in range(1, 13):
        print(f"Optimizing Month {month:2d}... ", end="", flush=True)

        # With battery
        result_with = optimize_month(month, year, battery_kwh, battery_kw, config_with_battery)

        # Without battery (0 kWh battery)
        result_without = optimize_month(month, year, 0, 0, config_no_battery)

        if result_with.success and result_without.success:
            monthly_saving = result_without.objective_value - result_with.objective_value
            monthly_results.append({
                'month': month,
                'cost_with_battery': result_with.objective_value,
                'cost_without_battery': result_without.objective_value,
                'monthly_saving': monthly_saving,
                'energy_cost': result_with.energy_cost,
                'power_cost': result_with.power_cost,
                'degradation_cost': result_with.degradation_cost,
                'total_degradation': np.sum(result_with.DP_total) if result_with.DP_total is not None else 0
            })
            print(f"✓ Saving: {monthly_saving:>8,.0f} NOK")
        else:
            print("✗ FAILED")

    # Calculate annual metrics
    df = pd.DataFrame(monthly_results)

    annual_saving = df['monthly_saving'].sum()
    annual_energy_cost = df['energy_cost'].sum()
    annual_power_cost = df['power_cost'].sum()
    annual_degradation_cost = df['degradation_cost'].sum()
    annual_cost_with = df['cost_with_battery'].sum()
    annual_cost_without = df['cost_without_battery'].sum()

    print("\n" + "="*70)
    print("ANNUAL RESULTS")
    print("="*70)
    print(f"\nWithout Battery:")
    print(f"  Annual cost:          {annual_cost_without:>12,.0f} NOK")

    print(f"\nWith Battery ({battery_kwh} kWh / {battery_kw} kW):")
    print(f"  Energy cost:          {annual_energy_cost:>12,.0f} NOK")
    print(f"  Power tariff:         {annual_power_cost:>12,.0f} NOK")
    print(f"  Degradation cost:     {annual_degradation_cost:>12,.0f} NOK")
    print(f"  {'─'*45}")
    print(f"  Annual cost:          {annual_cost_with:>12,.0f} NOK")

    print(f"\nAnnual Savings:")
    print(f"  Gross saving:         {annual_saving:>12,.0f} NOK/year")

    # Calculate NPV of savings over lifetime
    pv_factor = sum([1 / (1 + discount_rate)**t for t in range(1, lifetime_years + 1)])
    npv_savings = annual_saving * pv_factor

    print(f"\nPresent Value Analysis ({lifetime_years} years @ {discount_rate*100:.1f}%):")
    print(f"  PV factor:            {pv_factor:>12.2f}")
    print(f"  NPV of savings:       {npv_savings:>12,.0f} NOK")

    # Break-even battery cost
    # NPV_savings = Battery_cost → Battery_cost = NPV_savings
    # Battery_cost = battery_kwh * cost_per_kwh
    breakeven_per_kwh = npv_savings / battery_kwh

    print(f"\n{'='*70}")
    print("BREAK-EVEN BATTERY COST")
    print(f"{'='*70}")
    print(f"\n  Maximum battery cost: {breakeven_per_kwh:>12,.0f} NOK/kWh")
    print(f"  Total investment:     {npv_savings:>12,.0f} NOK ({battery_kwh} kWh)")
    print()
    print(f"Market Comparison:")
    print(f"  Current market price: ~5,000 NOK/kWh")
    print(f"  Break-even price:      {breakeven_per_kwh:>6,.0f} NOK/kWh")
    print(f"  Required reduction:    {((5000 - breakeven_per_kwh) / 5000 * 100):>6.1f}%")

    # Monthly breakdown
    print(f"\n{'='*70}")
    print("MONTHLY BREAKDOWN")
    print(f"{'='*70}")
    print(f"\n{'Month':>6} {'Cost w/o':>12} {'Cost w/':>12} {'Saving':>12} {'Degrad%':>10}")
    print("─" * 70)
    for _, row in df.iterrows():
        print(f"{row['month']:>6.0f} {row['cost_without_battery']:>12,.0f} "
              f"{row['cost_with_battery']:>12,.0f} {row['monthly_saving']:>12,.0f} "
              f"{row['total_degradation']:>9.3f}%")

    print("─" * 70)
    print(f"{'Annual':>6} {annual_cost_without:>12,.0f} {annual_cost_with:>12,.0f} "
          f"{annual_saving:>12,.0f}")

    # Save results
    output_file = Path(__file__).parent / 'results' / 'annual_breakeven_analysis.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    results_dict = {
        'battery_kwh': battery_kwh,
        'battery_kw': battery_kw,
        'year': year,
        'discount_rate': discount_rate,
        'lifetime_years': lifetime_years,
        'annual_cost_without_battery': float(annual_cost_without),
        'annual_cost_with_battery': float(annual_cost_with),
        'annual_saving': float(annual_saving),
        'npv_savings': float(npv_savings),
        'breakeven_cost_per_kwh': float(breakeven_per_kwh),
        'market_price_per_kwh': 5000,
        'required_reduction_pct': float((5000 - breakeven_per_kwh) / 5000 * 100),
        'monthly_results': df.to_dict('records')
    }

    import json
    with open(output_file, 'w') as f:
        json.dump(results_dict, f, indent=2)

    print(f"\n✓ Results saved to: {output_file}")

    return results_dict


def main():
    """Run annual break-even analysis"""

    results = calculate_annual_breakeven(
        battery_kwh=100,
        battery_kw=50,
        year=2024,
        discount_rate=0.05,
        lifetime_years=15
    )

    print("\n" + "="*70)
    print("✓ ANALYSIS COMPLETE")
    print("="*70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
