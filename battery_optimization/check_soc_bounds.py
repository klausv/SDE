#!/usr/bin/env python3
"""
Sjekk SOC-grensene i LP-optimeringsresultatet.
"""

import numpy as np
import pandas as pd
from core.price_fetcher import fetch_prices
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.time_aggregation import upsample_hourly_to_15min
from config import config

def test_soc_bounds():
    """Test SOC bounds i LP-optimering."""
    print("\n" + "="*80)
    print("SOC BOUNDS TEST")
    print("="*80)

    battery_kwh = 30
    battery_kw = 30

    # Prepare test data
    start_date = pd.Timestamp('2025-10-10', tz='Europe/Oslo')
    end_date = pd.Timestamp('2025-10-12 23:59', tz='Europe/Oslo')

    # Hourly test
    print("\n📊 Testing HOURLY resolution...")
    prices_h = fetch_prices(2025, 'NO2', resolution='PT60M')
    prices_h = prices_h.loc[start_date:end_date]
    timestamps_h = prices_h.index

    # Simple PV/consumption
    pv_pattern = [0]*6 + [50]*12 + [0]*6
    pv_h = np.array([pv_pattern for _ in range(3)]).flatten()[:len(timestamps_h)]
    consumption_h = np.ones(len(timestamps_h)) * 20

    optimizer_h = MonthlyLPOptimizer(config, resolution='PT60M')
    result_h = optimizer_h.optimize_month(
        month_idx=10,
        pv_production=pv_h,
        load_consumption=consumption_h,
        spot_prices=prices_h.values,
        timestamps=timestamps_h,
        E_initial=battery_kwh * 0.5
    )

    if result_h.success:
        soc_h = result_h.E_battery / battery_kwh * 100
        print(f"\n✅ Optimization successful")
        print(f"   SOC min: {soc_h.min():.2f}%")
        print(f"   SOC max: {soc_h.max():.2f}%")
        print(f"   SOC mean: {soc_h.mean():.2f}%")

        # Check if bounds are violated
        if soc_h.min() < 10.0:
            print(f"   ⚠️  WARNING: SOC goes below 10%!")
        if soc_h.max() > 90.0:
            print(f"   ⚠️  WARNING: SOC goes above 90%!")

        # Show actual E_battery values
        print(f"\n   Energy bounds set in LP:")
        print(f"   E_min = {optimizer_h.SOC_min} * {battery_kwh} = {optimizer_h.SOC_min * battery_kwh:.2f} kWh")
        print(f"   E_max = {optimizer_h.SOC_max} * {battery_kwh} = {optimizer_h.SOC_max * battery_kwh:.2f} kWh")

        print(f"\n   Actual E_battery from result:")
        print(f"   E_min = {result_h.E_battery.min():.2f} kWh ({result_h.E_battery.min()/battery_kwh*100:.2f}%)")
        print(f"   E_max = {result_h.E_battery.max():.2f} kWh ({result_h.E_battery.max()/battery_kwh*100:.2f}%)")

        # Print first 10 values
        print(f"\n   First 10 SOC values: {soc_h[:10]}")
        print(f"   Last 10 SOC values: {soc_h[-10:]}")

        # Check for violations
        violations_low = np.sum(result_h.E_battery < optimizer_h.SOC_min * battery_kwh)
        violations_high = np.sum(result_h.E_battery > optimizer_h.SOC_max * battery_kwh)

        print(f"\n   Constraint violations:")
        print(f"   Below 10% SOC: {violations_low} timesteps")
        print(f"   Above 90% SOC: {violations_high} timesteps")

    # 15-minute test
    print("\n" + "="*80)
    print("📊 Testing 15-MINUTE resolution...")
    prices_15 = fetch_prices(2025, 'NO2', resolution='PT15M')
    prices_15 = prices_15.loc[start_date:end_date]
    timestamps_15 = prices_15.index

    # Upsample PV/consumption
    pv_15_arr = np.repeat(pv_h, 4)[:len(timestamps_15)]
    consumption_15 = np.ones(len(timestamps_15)) * 20

    optimizer_15 = MonthlyLPOptimizer(config, resolution='PT15M')
    result_15 = optimizer_15.optimize_month(
        month_idx=10,
        pv_production=pv_15_arr,
        load_consumption=consumption_15,
        spot_prices=prices_15.values,
        timestamps=timestamps_15,
        E_initial=battery_kwh * 0.5
    )

    if result_15.success:
        soc_15 = result_15.E_battery / battery_kwh * 100
        print(f"\n✅ Optimization successful")
        print(f"   SOC min: {soc_15.min():.2f}%")
        print(f"   SOC max: {soc_15.max():.2f}%")
        print(f"   SOC mean: {soc_15.mean():.2f}%")

        if soc_15.min() < 10.0:
            print(f"   ⚠️  WARNING: SOC goes below 10%!")
        if soc_15.max() > 90.0:
            print(f"   ⚠️  WARNING: SOC goes above 90%!")

        print(f"\n   Energy bounds set in LP:")
        print(f"   E_min = {optimizer_15.SOC_min} * {battery_kwh} = {optimizer_15.SOC_min * battery_kwh:.2f} kWh")
        print(f"   E_max = {optimizer_15.SOC_max} * {battery_kwh} = {optimizer_15.SOC_max * battery_kwh:.2f} kWh")

        print(f"\n   Actual E_battery from result:")
        print(f"   E_min = {result_15.E_battery.min():.2f} kWh ({result_15.E_battery.min()/battery_kwh*100:.2f}%)")
        print(f"   E_max = {result_15.E_battery.max():.2f} kWh ({result_15.E_battery.max()/battery_kwh*100:.2f}%)")

        violations_low = np.sum(result_15.E_battery < optimizer_15.SOC_min * battery_kwh)
        violations_high = np.sum(result_15.E_battery > optimizer_15.SOC_max * battery_kwh)

        print(f"\n   Constraint violations:")
        print(f"   Below 10% SOC: {violations_low} timesteps")
        print(f"   Above 90% SOC: {violations_high} timesteps")


if __name__ == "__main__":
    test_soc_bounds()
