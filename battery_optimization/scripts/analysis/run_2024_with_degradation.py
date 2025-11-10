"""
Run 2024 simulation with 30 kWh battery and LFP degradation

Uses existing run_yearly_lp.py infrastructure but with:
- 30 kWh battery, 15 kW power
- LFP degradation enabled
- Real 2024 data
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import BatteryOptimizationConfig, DegradationConfig
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.price_fetcher import ENTSOEPriceFetcher
from core.pvgis_solar import PVGISProduction
import numpy as np
import pandas as pd


def load_real_2024_data():
    """Load real 2024 data"""
    print("\nLoading real 2024 data...")
    print("="*70)

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

    print(f"✓ Loaded {len(data)} hours of 2024 data")
    print(f"  Prices: {prices.mean():.3f} NOK/kWh avg")
    print(f"  Solar: {pv.sum()/1000:.1f} MWh annual")
    print(f"  Load: {load.sum()/1000:.1f} MWh annual")

    return data


def run_monthly_optimizations(data, battery_kwh=30, battery_kw=15):
    """Run 12 monthly optimizations with degradation"""

    print("\n" + "="*70)
    print(f"YEARLY OPTIMIZATION - {battery_kwh} kWh, {battery_kw} kW")
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
    total_deg = 0
    total_cyclic = 0
    total_calendar = 0

    for month in range(1, 13):
        month_data = data[data['month'] == month]

        print(f"\nMonth {month:2d}: {len(month_data)} hours...", end=" ")

        result = optimizer.optimize_month(
            month_idx=month,
            pv_production=month_data['pv_production'].values,
            load_consumption=month_data['load'].values,
            spot_prices=month_data['spot_price'].values,
            timestamps=month_data.index.values,
            E_initial=E_initial
        )

        if not result.success:
            print(f"❌ FAILED")
            continue

        results.append(result)

        # Accumulate
        total_energy_cost += result.energy_cost
        total_power_cost += result.power_cost
        total_degradation_cost += result.degradation_cost

        month_deg = np.sum(result.DP_total)
        month_cyclic = np.sum(result.DP_cyc)
        month_calendar = result.DP_cal * len(month_data)

        total_deg += month_deg
        total_cyclic += month_cyclic
        total_calendar += month_calendar

        E_initial = result.E_battery_final

        print(f"✓ Cost: {result.objective_value:,.0f} NOK, Deg: {month_deg:.4f}%")

    # Print results
    print("\n" + "="*70)
    print("ANNUAL RESULTS - 2024")
    print("="*70)

    print(f"\nCosts:")
    print(f"  Energy:       {total_energy_cost:>12,.2f} NOK")
    print(f"  Power:        {total_power_cost:>12,.2f} NOK")
    print(f"  Degradation:  {total_degradation_cost:>12,.2f} NOK")
    print(f"  {'─'*40}")
    print(f"  Total:        {total_energy_cost + total_power_cost + total_degradation_cost:>12,.2f} NOK")

    print(f"\nDegradation:")
    print(f"  Total:        {total_deg:.4f}%")
    print(f"  Cyclic:       {total_cyclic:.4f}%")
    print(f"  Calendar:     {total_calendar:.4f}%")
    print(f"  Ratio:        {total_cyclic/total_calendar:.2f}× (cyclic/calendar)")

    equiv_cycles = total_cyclic / (20.0 / 5000)
    print(f"  Equiv cycles: {equiv_cycles:.1f}")

    remaining = 100 - total_deg
    years_to_80 = 20.0 / total_deg if total_deg > 0 else 0
    print(f"  Remaining:    {remaining:.2f}% capacity")
    print(f"  Lifetime:     {years_to_80:.1f} years (to 80% SOH)")

    # Economics
    print(f"\nEconomics (30 kWh battery):")
    system_cost = config.battery.get_system_cost_per_kwh(battery_kwh)
    total_investment = system_cost * battery_kwh
    print(f"  System cost:     {system_cost:,.0f} NOK/kWh")
    print(f"  Investment:      {total_investment:,.0f} NOK")
    print(f"  Cell cost:       {config.battery.battery_cell_cost_nok_per_kwh * battery_kwh:,.0f} NOK")
    print(f"  Annual deg cost: {total_degradation_cost:,.2f} NOK")

    return results


def main():
    data = load_real_2024_data()
    results = run_monthly_optimizations(data, battery_kwh=30, battery_kw=15)

    print("\n" + "="*70)
    print("✓ SIMULATION COMPLETE")
    print("="*70)
    return results


if __name__ == "__main__":
    main()
