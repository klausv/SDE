#!/usr/bin/env python3
"""
Simplified battery optimization with 90 MWh annual load
"""
import numpy as np

def analyze_90mwh_load():
    """
    Analyze battery economics with 90 MWh annual load
    Using simplified calculation similar to run_test_simple.py
    """
    print("=" * 70)
    print("🔋 BATTERY OPTIMIZATION - 90 MWH ANNUAL LOAD")
    print("=" * 70)

    # System parameters
    pv_capacity = 150  # kWp
    pv_annual = 140_000  # kWh/year (Stavanger)
    load_annual = 90_000  # kWh/year (target)
    grid_limit = 77  # kW

    print("\n📊 Energy Balance:")
    print(f"  • Annual PV production: {pv_annual/1000:.0f} MWh")
    print(f"  • Annual consumption: {load_annual/1000:.0f} MWh")
    print(f"  • Net excess PV: {(pv_annual - load_annual)/1000:.0f} MWh")

    # Load profile parameters
    # Commercial pattern: low at night, peak during day
    base_load = load_annual / 8760  # 10.3 kW average
    peak_load = base_load * 2.5  # ~26 kW peak (business hours)
    night_load = base_load * 0.3  # ~3 kW (night minimum)

    print(f"\n🏢 Load Profile:")
    print(f"  • Average: {base_load:.1f} kW")
    print(f"  • Peak (day): {peak_load:.1f} kW")
    print(f"  • Min (night): {night_load:.1f} kW")
    print(f"  • Load factor: {base_load/peak_load:.1%}")

    # Battery configurations to test
    configs = [
        (50, 25), (50, 40), (50, 50),
        (75, 25), (75, 40), (75, 50), (75, 60), (75, 75),
        (100, 40), (100, 50), (100, 60), (100, 75), (100, 100),
        (125, 40), (125, 50), (125, 60), (125, 75), (125, 100),
        (150, 50), (150, 60), (150, 75), (150, 100)
    ]

    print("\n📊 Testing battery configurations with 90 MWh load...\n")
    print("Capacity\tPower\tC-rate\tNPV\t\tAnnual Revenue")
    print("-" * 60)

    best_npv = -float('inf')
    best_config = None
    results = []

    for capacity_kwh, power_kw in configs:
        c_rate = power_kw / capacity_kwh

        # Annual revenue calculations with 90 MWh load
        # 1. Energy arbitrage (adjusted for lower load)
        daily_cycles = 0.8  # Slightly higher cycling due to excess PV
        annual_throughput = capacity_kwh * daily_cycles * 365 * 0.85  # efficiency
        price_spread = 0.35  # NOK/kWh average spread
        arbitrage_revenue = annual_throughput * price_spread

        # 2. Self-consumption value (more important with lower load)
        # With 90 MWh load and 140 MWh PV, we have 50 MWh excess
        # Battery helps shift this excess to evening/night consumption
        self_consumption_increase = min(capacity_kwh * 200, 30_000)  # kWh/year
        self_consumption_value = self_consumption_increase * 0.25  # value vs grid

        # 3. Peak shaving (less curtailment needed due to lower base load)
        # Curtailment mainly happens in summer midday when load is low
        summer_curtailable = 15_000  # kWh/year (estimate)
        curtailment_avoided = min(capacity_kwh * 100, summer_curtailable)
        curtailment_value = curtailment_avoided * 0.6

        # 4. Power tariff reduction (smaller due to lower base demand)
        # With 90 MWh/year, peak is around 25-30 kW
        peak_reduction_kw = min(power_kw * 0.3, 10)  # Less reduction potential
        annual_tariff_saving = peak_reduction_kw * 1800  # NOK/kW/year

        # Total annual revenue
        annual_revenue = (arbitrage_revenue + self_consumption_value +
                         curtailment_value + annual_tariff_saving)

        # NPV calculation
        investment = capacity_kwh * 3000  # NOK
        lifetime_years = 15
        discount_rate = 0.05
        degradation = 0.02

        npv = -investment
        for year in range(1, lifetime_years + 1):
            yearly_revenue = annual_revenue * (1 - degradation * year)
            npv += yearly_revenue / (1 + discount_rate) ** year

        results.append({
            'capacity': capacity_kwh,
            'power': power_kw,
            'c_rate': c_rate,
            'npv': npv,
            'annual_revenue': annual_revenue
        })

        print(f"{capacity_kwh} kWh\t{power_kw} kW\t{c_rate:.2f}\t"
              f"{npv:,.0f}\t{annual_revenue:,.0f}")

        if npv > best_npv:
            best_npv = npv
            best_config = (capacity_kwh, power_kw)

    print("\n" + "=" * 70)
    print("✅ OPTIMAL CONFIGURATION WITH 90 MWH LOAD")
    print("=" * 70)

    if best_config:
        capacity, power = best_config
        print(f"\n🔋 Battery sizing:")
        print(f"   • Capacity: {capacity} kWh")
        print(f"   • Power: {power} kW")
        print(f"   • C-rate: {power/capacity:.2f}")

        # Find the best result
        best_result = next(r for r in results if r['capacity'] == capacity and r['power'] == power)

        print(f"\n💰 Economics:")
        print(f"   • NPV @ 3000 NOK/kWh: {best_result['npv']:,.0f} NOK")
        print(f"   • Annual revenue: {best_result['annual_revenue']:,.0f} NOK")
        print(f"   • Simple payback: {capacity * 3000 / best_result['annual_revenue']:.1f} years")

        # Break-even analysis
        print(f"\n🎯 Break-even analysis for {capacity} kWh @ {power} kW:")
        for battery_cost in [2500, 3000, 3500, 4000, 4500, 5000]:
            investment = capacity * battery_cost
            npv = -investment
            for year in range(1, lifetime_years + 1):
                yearly_revenue = best_result['annual_revenue'] * (1 - degradation * year)
                npv += yearly_revenue / (1 + discount_rate) ** year

            status = "✅" if npv > 0 else "❌"
            print(f"   {battery_cost} NOK/kWh: NPV = {npv:>10,.0f} {status}")

    print("\n📝 Key insights with 90 MWh load (vs higher load):")
    print("   • More excess PV available for arbitrage")
    print("   • Lower self-consumption baseline")
    print("   • Higher cycling potential due to excess energy")
    print("   • Smaller peak shaving benefit")
    print("   • Battery value shifts from self-consumption to arbitrage")

    return best_config, best_npv

if __name__ == "__main__":
    config, npv = analyze_90mwh_load()

    print("\n" + "=" * 70)
    print("COMPARISON: Impact of Load Reduction")
    print("=" * 70)
    print("\nOriginal analysis (~160 MWh load):")
    print("  • Optimal: 50 kWh @ 40 kW")
    print("  • NPV: ~131,000 NOK")
    print("\nWith 90 MWh load:")
    if config:
        print(f"  • Optimal: {config[0]} kWh @ {config[1]} kW")
        print(f"  • NPV: {npv:,.0f} NOK")
    print("\nConclusion: Lower load changes optimal battery size")
    print("due to different energy flow patterns and arbitrage opportunities.")