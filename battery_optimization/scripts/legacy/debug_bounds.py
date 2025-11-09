#!/usr/bin/env python3
"""
Debug bounds issue - print out the actual bounds being sent to linprog.
"""

import numpy as np
import pandas as pd
from core.price_fetcher import fetch_prices
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from config import config

# Monkey patch the optimize_month to print bounds
original_optimize = MonthlyLPOptimizer.optimize_month

def debug_optimize(self, month_idx, pv_production, load_consumption, spot_prices, timestamps, E_initial):
    """Wrapper that prints bounds before optimization."""
    T = len(timestamps)

    print(f"\n🔍 DEBUG: Bounds Analysis")
    print(f"   T = {T}")
    print(f"   Battery capacity: {self.E_nom} kWh")
    print(f"   SOC_min: {self.SOC_min} ({self.SOC_min * 100}%)")
    print(f"   SOC_max: {self.SOC_max} ({self.SOC_max * 100}%)")
    print(f"   E_min: {self.SOC_min * self.E_nom} kWh")
    print(f"   E_max: {self.SOC_max * self.E_nom} kWh")

    # Call original
    result = original_optimize(self, month_idx, pv_production, load_consumption, spot_prices, timestamps, E_initial)

    if result.success:
        print(f"\n🔍 DEBUG: Result Analysis")
        print(f"   E_battery min: {result.E_battery.min():.2f} kWh ({result.E_battery.min()/self.E_nom*100:.1f}%)")
        print(f"   E_battery max: {result.E_battery.max():.2f} kWh ({result.E_battery.max()/self.E_nom*100:.1f}%)")

        # Check violations
        violations_low = np.sum(result.E_battery < self.SOC_min * self.E_nom - 0.01)  # 0.01 tolerance
        violations_high = np.sum(result.E_battery > self.SOC_max * self.E_nom + 0.01)

        print(f"   Violations below {self.SOC_min*100}%: {violations_low}")
        print(f"   Violations above {self.SOC_max*100}%: {violations_high}")

        if violations_high > 0:
            print(f"\n   ⚠️ BOUNDS VIOLATION DETECTED!")
            print(f"   Indices where E > {self.SOC_max * self.E_nom} kWh:")
            violation_indices = np.where(result.E_battery > self.SOC_max * self.E_nom)[0]
            for idx in violation_indices[:5]:  # Show first 5
                print(f"      t={idx}: E={result.E_battery[idx]:.2f} kWh ({result.E_battery[idx]/self.E_nom*100:.1f}%)")

    return result

MonthlyLPOptimizer.optimize_month = debug_optimize

# Run test
battery_kwh = 30
battery_kw = 30

start_date = pd.Timestamp('2025-10-10', tz='Europe/Oslo')
end_date = pd.Timestamp('2025-10-10 23:59', tz='Europe/Oslo')  # Just 1 day

print("="*80)
print("BOUNDS DEBUG TEST")
print("="*80)

prices = fetch_prices(2025, 'NO2', resolution='PT60M')
prices = prices.loc[start_date:end_date]
timestamps = prices.index

pv_pattern = [0]*6 + [50]*12 + [0]*6
pv = np.array(pv_pattern[:len(timestamps)])
consumption = np.ones(len(timestamps)) * 20

optimizer = MonthlyLPOptimizer(config, resolution='PT60M')
result = optimizer.optimize_month(
    month_idx=10,
    pv_production=pv,
    load_consumption=consumption,
    spot_prices=prices.values,
    timestamps=timestamps,
    E_initial=battery_kwh * 0.5
)

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

if result.success:
    if result.E_battery.max() > optimizer.SOC_max * battery_kwh:
        print(f"❌ BOUNDS ARE NOT BEING RESPECTED BY LP SOLVER!")
        print(f"   This is a critical bug in the LP formulation.")
    else:
        print(f"✅ Bounds are correctly respected.")
