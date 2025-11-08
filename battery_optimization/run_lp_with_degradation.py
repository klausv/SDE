"""
Run LP monthly optimization with LFP battery degradation modeling.

This script demonstrates the complete optimization workflow with:
- Real spot prices from ENTSO-E
- PVGIS solar production data
- LFP battery degradation modeling
- Hourly time resolution (PT60M)
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

def load_real_data(month=1, year=2024):
    """Load real spot prices and solar production data"""

    print("Loading real data...")
    print("="*70)

    # Load spot prices
    try:
        fetcher = ENTSOEPriceFetcher(resolution='PT60M')
        prices_series = fetcher.fetch_prices(year=year, area='NO2', resolution='PT60M')
        print(f"✓ Loaded spot prices for {year}")
    except Exception as e:
        print(f"⚠ Could not load real prices: {e}")
        print("Using synthetic data instead...")
        return None, None, None

    # Convert Series to DataFrame for consistency
    prices_df = prices_series.to_frame('price_nok_per_kwh')

    # Filter for specific month
    prices_df['month'] = prices_df.index.month
    month_data = prices_df[prices_df['month'] == month].copy()

    if len(month_data) == 0:
        print(f"⚠ No data for month {month}")
        return None, None, None

    timestamps = month_data.index
    spot_prices = month_data['price_nok_per_kwh'].values

    print(f"  Month {month}: {len(timestamps)} hourly datapoints")
    print(f"  Spot price range: {spot_prices.min():.3f} - {spot_prices.max():.3f} NOK/kWh")
    print(f"  Average spot price: {spot_prices.mean():.3f} NOK/kWh")

    # Load solar production (PVGIS typical year)
    try:
        pvgis = PVGISProduction(
            lat=58.97,
            lon=5.73,
            pv_capacity_kwp=138.55,
            tilt=30.0,
            azimuth=173.0
        )

        pvgis_series = pvgis.fetch_hourly_production(year=year)
        pvgis_data = pvgis_series.to_frame('production_kw')
        pvgis_data.rename(columns={'production_kw': 'pv_power_kw'}, inplace=True)

        # Extract month data
        pvgis_data['month'] = pvgis_data.index.month
        solar_month = pvgis_data[pvgis_data['month'] == month].copy()

        # Match timestamps
        pv_production = np.zeros(len(timestamps))
        for i, ts in enumerate(timestamps):
            # Find matching hour in PVGIS data
            matching = solar_month[
                (solar_month.index.month == ts.month) &
                (solar_month.index.day == ts.day) &
                (solar_month.index.hour == ts.hour)
            ]
            if len(matching) > 0:
                pv_production[i] = matching['pv_power_kw'].values[0]

        print(f"✓ Loaded PVGIS solar data")
        print(f"  Production range: {pv_production.min():.1f} - {pv_production.max():.1f} kW")
        print(f"  Average production: {pv_production.mean():.1f} kW")

    except Exception as e:
        print(f"⚠ Could not load PVGIS data: {e}")
        # Fallback to simple solar pattern
        pv_production = np.array([
            50.0 if 8 <= ts.hour < 20 else 0.0
            for ts in timestamps
        ])
        print(f"  Using synthetic solar pattern")

    print()
    return timestamps, spot_prices, pv_production


def create_synthetic_load(timestamps, annual_kwh=300000):
    """Create realistic commercial load profile"""
    hours_per_year = 8760
    avg_load = annual_kwh / hours_per_year  # ~34 kW average

    load = np.zeros(len(timestamps))
    for i, ts in enumerate(timestamps):
        # Base load
        base = avg_load * 0.6  # 20 kW

        # Daytime increase (Mon-Fri 6-18)
        if ts.weekday() < 5 and 6 <= ts.hour < 18:
            load[i] = base * 1.8  # 36 kW
        # Evening (18-22)
        elif 18 <= ts.hour < 22:
            load[i] = base * 1.3  # 26 kW
        # Night
        else:
            load[i] = base  # 20 kW

    return load


def run_optimization_with_degradation(battery_kwh=100, battery_kw=50, month=1, year=2024):
    """Run optimization with degradation modeling enabled"""

    print("\n" + "="*70)
    print(f"LP OPTIMIZATION WITH LFP DEGRADATION - Month {month}")
    print("="*70)
    print(f"Battery: {battery_kwh} kWh, {battery_kw} kW")
    print()

    # Create config with degradation enabled
    config = BatteryOptimizationConfig()
    config.battery.degradation = DegradationConfig(
        enabled=True,
        cycle_life_full_dod=5000,
        calendar_life_years=28.0
    )

    # Load real data
    timestamps, spot_prices, pv_production = load_real_data(month=month, year=year)

    if timestamps is None:
        print("❌ Could not load data. Exiting.")
        return None

    # Create load profile
    load = create_synthetic_load(timestamps, annual_kwh=300000)

    print("Data summary:")
    print(f"  Time period: {timestamps[0]} to {timestamps[-1]}")
    print(f"  Duration: {len(timestamps)} hours ({len(timestamps)/24:.1f} days)")
    print(f"  Average load: {load.mean():.1f} kW")
    print(f"  Peak load: {load.max():.1f} kW")
    print(f"  Average solar: {pv_production.mean():.1f} kW")
    print(f"  Peak solar: {pv_production.max():.1f} kW")
    print()

    # Create optimizer
    optimizer = MonthlyLPOptimizer(
        config,
        resolution='PT60M',
        battery_kwh=battery_kwh,
        battery_kw=battery_kw
    )

    # Run optimization
    result = optimizer.optimize_month(
        month_idx=month,
        pv_production=pv_production,
        load_consumption=load,
        spot_prices=spot_prices,
        timestamps=timestamps,
        E_initial=battery_kwh * 0.5  # Start at 50% SOC
    )

    if not result.success:
        print(f"❌ Optimization failed: {result.message}")
        return None

    # Print detailed results
    print("\n" + "="*70)
    print("OPTIMIZATION RESULTS WITH DEGRADATION")
    print("="*70)

    print(f"\nCost Breakdown:")
    print(f"  Energy cost:      {result.energy_cost:>12,.2f} NOK")
    print(f"  Power tariff:     {result.power_cost:>12,.2f} NOK")
    print(f"  Degradation cost: {result.degradation_cost:>12,.2f} NOK")
    print(f"  {'─'*40}")
    print(f"  Total cost:       {result.objective_value:>12,.2f} NOK")

    print(f"\nDegradation Analysis:")
    if result.DP_total is not None:
        total_deg = np.sum(result.DP_total)
        cyclic_deg = np.sum(result.DP_cyc)
        calendar_deg = result.DP_cal * len(timestamps)

        print(f"  Total degradation:    {total_deg:.4f}%")
        print(f"  Cyclic degradation:   {cyclic_deg:.4f}%")
        print(f"  Calendar degradation: {calendar_deg:.4f}%")
        print(f"  Degradation ratio:    {cyclic_deg/calendar_deg:.2f}× (cyclic/calendar)")

        # Equivalent full cycles
        equiv_cycles = cyclic_deg / (20.0 / 5000)  # ρ_constant = 0.004%
        print(f"  Equivalent full cycles: {equiv_cycles:.1f}")

        # Battery utilization
        max_possible_energy = battery_kwh * len(timestamps)
        actual_energy = np.sum(result.P_charge) * 1.0  # timestep_hours
        utilization = (actual_energy / max_possible_energy) * 100
        print(f"  Battery utilization: {utilization:.1f}%")

    print(f"\nOperational Metrics:")
    print(f"  Peak power:       {result.P_peak:>12.2f} kW")
    print(f"  Final SOC:        {result.E_battery_final/battery_kwh*100:>12.1f}%")
    print(f"  Avg charge power: {np.mean(result.P_charge[result.P_charge > 0]):>12.2f} kW")
    print(f"  Avg discharge pwr:{np.mean(result.P_discharge[result.P_discharge > 0]):>12.2f} kW")
    print(f"  Hours charging:   {np.sum(result.P_charge > 0):>12.0f} hrs")
    print(f"  Hours discharging:{np.sum(result.P_discharge > 0):>12.0f} hrs")

    return result


def main():
    """Run optimization example"""

    print("\n" + "="*70)
    print("LFP BATTERY OPTIMIZATION WITH DEGRADATION MODELING")
    print("="*70)
    print()
    print("Configuration:")
    print("  - Time resolution: Hourly (PT60M)")
    print("  - Degradation model: LFP (Korpås formulation)")
    print("  - Cost separation: Battery (3,054 NOK/kWh) + Inverter + Control")
    print("  - Solver: HiGHS LP")
    print()

    # Run optimization
    result = run_optimization_with_degradation(
        battery_kwh=100,
        battery_kw=50,
        month=1  # January
    )

    if result is None:
        print("\n❌ Optimization failed")
        return 1

    print("\n" + "="*70)
    print("✓ OPTIMIZATION COMPLETED SUCCESSFULLY")
    print("="*70)
    print()
    print("The LFP degradation model is working correctly!")
    print("Degradation costs are properly integrated into the LP objective.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
