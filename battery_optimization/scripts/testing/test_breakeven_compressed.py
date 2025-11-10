"""
Test break-even battery cost calculation using compressed representative dataset.

Compares:
- Reference scenario (no battery)
- Battery scenario with compressed representation

Goal: Verify break-even cost is reasonable (~2500-4000 NOK/kWh expected)
"""

import pandas as pd
import numpy as np
from datetime import datetime

from config import config
from core.price_fetcher import fetch_prices
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.representative_dataset import RepresentativeDatasetGenerator


def test_breakeven_with_compression():
    """
    Calculate break-even battery cost using compressed dataset for full year.

    Steps:
    1. Load full year 2025 data (PT60M)
    2. Create compressed representative dataset (16 days)
    3. Run LP optimization: reference (no battery) vs battery scenario
    4. Calculate annual savings
    5. Calculate break-even cost
    """

    print("=" * 80)
    print("BREAK-EVEN ANALYSE MED KOMPRIMERT DATASET")
    print("=" * 80)
    print()

    # Battery configuration to test
    battery_kwh = 80
    battery_kw = 50

    print(f"Batteri: {battery_kwh} kWh / {battery_kw} kW")
    print(f"Oppløsning: PT60M (time)")
    print(f"Periode: Hele 2025")
    print()

    # =========================================================================
    # STEP 1: Load full year 2025 data
    # =========================================================================
    print("=" * 80)
    print("LASTER HELE ÅRET 2025 (PT60M)")
    print("=" * 80)

    spot_prices_full = fetch_prices(2025, 'NO2', resolution='PT60M')
    timestamps_full = spot_prices_full.index

    print(f"Timestamps: {len(timestamps_full)}")
    print(f"Spot avg: {spot_prices_full.mean():.3f} kr/kWh")
    print()

    # Generate PV production for full year
    pv_full = []
    for ts in timestamps_full:
        hour = ts.hour
        day_of_year = ts.dayofyear

        # Summer: higher production, Winter: lower production
        season_factor = 0.3 + 0.7 * np.sin((day_of_year - 80) * 2 * np.pi / 365)

        # Daily curve (6am-8pm solar window)
        if 6 <= hour <= 20:
            hour_factor = np.sin((hour - 6) * np.pi / 14)
            pv_kw = config.solar.pv_capacity_kwp * season_factor * hour_factor * 0.8
        else:
            pv_kw = 0

        pv_full.append(pv_kw)

    pv_full = pd.Series(pv_full, index=timestamps_full)

    # Generate consumption
    load_full = []
    for ts in timestamps_full:
        hour = ts.hour
        is_weekday = ts.weekday() < 5
        day_of_year = ts.dayofyear

        # Seasonal factor (higher in winter)
        season_factor = 1.2 - 0.4 * np.sin((day_of_year - 80) * 2 * np.pi / 365)

        if is_weekday:
            if 7 <= hour <= 16:
                base_load = 25 * season_factor
            elif 17 <= hour <= 22:
                base_load = 18 * season_factor
            else:
                base_load = 12 * season_factor
        else:
            base_load = 12 * season_factor

        load_full.append(base_load * (0.95 + 0.1 * np.random.random()))

    load_full = pd.Series(load_full, index=timestamps_full)

    print(f"PV total: {pv_full.sum():.1f} kWh")
    print(f"Load total: {load_full.sum():.1f} kWh")
    print()

    # =========================================================================
    # STEP 2: Create compressed representative dataset
    # =========================================================================
    print("=" * 80)
    print("KOMPRIMERER TIL REPRESENTATIVE DAGER")
    print("=" * 80)

    generator = RepresentativeDatasetGenerator(n_typical_days=12, n_extreme_days=4)

    repr_timestamps, repr_pv, repr_load, repr_spot, metadata = generator.select_representative_days(
        timestamps_full,
        pv_full.values,
        load_full.values,
        spot_prices_full.values
    )

    print(f"Komprimert: {len(timestamps_full)} timer → {len(repr_timestamps)} timer")
    print(f"Kompresjonsfaktor: {metadata['compression_ratio']:.1f}x")
    print()

    # =========================================================================
    # STEP 3: Run LP optimization - REFERENCE (no battery)
    # =========================================================================
    print("=" * 80)
    print("REFERANSE: UTEN BATTERI")
    print("=" * 80)

    optimizer_ref = MonthlyLPOptimizer(
        config,
        resolution='PT60M',
        battery_kwh=0,  # NO BATTERY
        battery_kw=0
    )

    # Run on compressed dataset
    result_ref = optimizer_ref.optimize_month(
        month_idx=1,  # Dummy month (we use full year compressed data)
        pv_production=repr_pv,
        load_consumption=repr_load,
        spot_prices=repr_spot,
        timestamps=repr_timestamps,
        E_initial=0
    )

    # Scale to annual
    scale_factor = len(timestamps_full) / len(repr_timestamps)
    ref_annual_cost = result_ref.energy_cost * scale_factor + result_ref.power_cost * 12

    print(f"Årlig kostnad (referanse):")
    print(f"  Energi: {result_ref.energy_cost * scale_factor:,.0f} kr")
    print(f"  Effekt: {result_ref.power_cost * 12:,.0f} kr (månedlig * 12)")
    print(f"  Total: {ref_annual_cost:,.0f} kr")
    print()

    # =========================================================================
    # STEP 4: Run LP optimization - WITH BATTERY
    # =========================================================================
    print("=" * 80)
    print(f"MED BATTERI: {battery_kwh} kWh / {battery_kw} kW")
    print("=" * 80)

    optimizer_battery = MonthlyLPOptimizer(
        config,
        resolution='PT60M',
        battery_kwh=battery_kwh,
        battery_kw=battery_kw
    )

    result_battery = optimizer_battery.optimize_month(
        month_idx=1,
        pv_production=repr_pv,
        load_consumption=repr_load,
        spot_prices=repr_spot,
        timestamps=repr_timestamps,
        E_initial=battery_kwh * 0.5
    )

    # Scale to annual
    battery_annual_cost = result_battery.energy_cost * scale_factor + result_battery.power_cost * 12

    print(f"Årlig kostnad (med batteri):")
    print(f"  Energi: {result_battery.energy_cost * scale_factor:,.0f} kr")
    print(f"  Effekt: {result_battery.power_cost * 12:,.0f} kr (månedlig * 12)")
    print(f"  Total: {battery_annual_cost:,.0f} kr")
    print()

    # =========================================================================
    # STEP 5: Calculate break-even cost
    # =========================================================================
    print("=" * 80)
    print("BREAK-EVEN ANALYSE")
    print("=" * 80)
    print()

    annual_savings = ref_annual_cost - battery_annual_cost

    print(f"Årlige besparelser: {annual_savings:,.0f} kr")
    print()

    # Economic parameters
    lifetime_years = config.battery.lifetime_years
    discount_rate = config.economics.discount_rate

    # Calculate NPV of savings
    npv_savings = sum([
        annual_savings / ((1 + discount_rate) ** year)
        for year in range(1, lifetime_years + 1)
    ])

    print(f"Nåverdi av besparelser ({lifetime_years} år, {discount_rate*100}% diskontering):")
    print(f"  NPV: {npv_savings:,.0f} kr")
    print()

    # Break-even cost per kWh
    breakeven_cost_per_kwh = npv_savings / battery_kwh

    print(f"BREAK-EVEN KOSTNAD:")
    print(f"  {breakeven_cost_per_kwh:,.0f} kr/kWh")
    print()

    # Compare with market
    market_cost = config.battery.market_cost_nok_per_kwh
    target_cost = config.battery.target_cost_nok_per_kwh

    print(f"Sammenligning:")
    print(f"  Break-even: {breakeven_cost_per_kwh:,.0f} kr/kWh")
    print(f"  Markedspris: {market_cost:,.0f} kr/kWh")
    print(f"  Målpris: {target_cost:,.0f} kr/kWh")
    print()

    if breakeven_cost_per_kwh >= market_cost:
        print(f"✅ LØNNSOMT: Break-even ({breakeven_cost_per_kwh:.0f}) > markedspris ({market_cost:.0f})")
    elif breakeven_cost_per_kwh >= target_cost:
        print(f"⚠️  POTENSIELT: Break-even ({breakeven_cost_per_kwh:.0f}) > målpris ({target_cost:.0f})")
        print(f"   Batterikostnad må reduseres til {breakeven_cost_per_kwh:.0f} kr/kWh")
    else:
        print(f"❌ ULØNNSOMT: Break-even ({breakeven_cost_per_kwh:.0f}) < målpris ({target_cost:.0f})")
        print(f"   Krever {((market_cost / breakeven_cost_per_kwh - 1) * 100):.0f}% kostnadsreduksjon")

    print()
    print("=" * 80)

    return {
        'battery_kwh': battery_kwh,
        'battery_kw': battery_kw,
        'annual_savings': annual_savings,
        'npv_savings': npv_savings,
        'breakeven_cost_per_kwh': breakeven_cost_per_kwh,
        'compression_ratio': metadata['compression_ratio']
    }


if __name__ == "__main__":
    result = test_breakeven_with_compression()

    print("\nRESULTAT:")
    print(f"  Break-even: {result['breakeven_cost_per_kwh']:,.0f} kr/kWh")
    print(f"  Kompresjon: {result['compression_ratio']:.1f}x")
