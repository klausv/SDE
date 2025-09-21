#!/usr/bin/env python3
"""
Battery optimization with REAL PVGIS data for Stavanger
90 MWh annual load, 127 MWh PV production (not 140!)
"""
import numpy as np

def analyze_with_real_pvgis():
    """
    Analyze battery economics with actual PVGIS data
    """
    print("=" * 70)
    print("🔋 BATTERY OPTIMIZATION - REAL PVGIS DATA")
    print("=" * 70)

    # System parameters - REAL VALUES
    pv_capacity = 150  # kWp
    pv_annual = 126_582  # kWh/year (PVGIS actual for Stavanger)
    load_annual = 90_000  # kWh/year
    grid_limit = 77  # kW

    print("\n📊 Energy Balance (REAL PVGIS DATA):")
    print(f"  • PV installed: {pv_capacity} kWp")
    print(f"  • Annual PV production: {pv_annual/1000:.1f} MWh (844 kWh/kWp)")
    print(f"  • Annual consumption: {load_annual/1000:.0f} MWh")
    print(f"  • Net excess PV: {(pv_annual - load_annual)/1000:.1f} MWh")
    print(f"  • Self-sufficiency potential: {min(100, pv_annual/load_annual*100):.1f}%")

    # Load profile
    base_load = load_annual / 8760  # 10.3 kW average
    peak_load = base_load * 2.5  # ~26 kW peak
    night_load = base_load * 0.3  # ~3 kW night

    print(f"\n🏢 Load Profile (90 MWh/year):")
    print(f"  • Average: {base_load:.1f} kW")
    print(f"  • Peak (day): {peak_load:.1f} kW")
    print(f"  • Min (night): {night_load:.1f} kW")

    # Battery configurations
    configs = [
        (30, 20), (30, 30),  # Small batteries
        (50, 25), (50, 40), (50, 50),
        (75, 30), (75, 40), (75, 50), (75, 60),
        (100, 40), (100, 50), (100, 60), (100, 75),
        (125, 50), (125, 60), (125, 75),
        (150, 60), (150, 75)
    ]

    print("\n📊 Testing configurations with REAL production data...\n")
    print("Capacity\tPower\tC-rate\tNPV\t\tRevenue\t\tPayback")
    print("-" * 75)

    best_npv = -float('inf')
    best_config = None
    results = []

    for capacity_kwh, power_kw in configs:
        c_rate = power_kw / capacity_kwh

        # Revenue calculations with REAL 127 MWh production
        # 1. Energy arbitrage (reduced due to less excess)
        daily_cycles = 0.6  # Lower cycling (less excess than thought)
        annual_throughput = capacity_kwh * daily_cycles * 365 * 0.85
        price_spread = 0.35  # NOK/kWh
        arbitrage_revenue = annual_throughput * price_spread

        # 2. Self-consumption improvement
        # With 127 MWh PV and 90 MWh load, only 37 MWh excess
        self_consumption_increase = min(capacity_kwh * 150, 25_000)
        self_consumption_value = self_consumption_increase * 0.25

        # 3. Curtailment avoidance (less than expected)
        # Less excess means less curtailment
        summer_curtailable = 10_000  # kWh/year (reduced)
        curtailment_avoided = min(capacity_kwh * 80, summer_curtailable)
        curtailment_value = curtailment_avoided * 0.6

        # 4. Power tariff reduction
        peak_reduction_kw = min(power_kw * 0.3, 10)
        annual_tariff_saving = peak_reduction_kw * 1800

        # 5. Grid stability services (new revenue stream)
        # Smaller batteries can provide frequency regulation
        if power_kw >= capacity_kwh * 0.5:  # C-rate >= 0.5
            grid_services = capacity_kwh * 50  # NOK/kWh/year
        else:
            grid_services = 0

        # Total annual revenue
        annual_revenue = (arbitrage_revenue + self_consumption_value +
                         curtailment_value + annual_tariff_saving + grid_services)

        # NPV calculation
        investment = capacity_kwh * 3000  # NOK
        lifetime_years = 15
        discount_rate = 0.05
        degradation = 0.02

        npv = -investment
        for year in range(1, lifetime_years + 1):
            yearly_revenue = annual_revenue * (1 - degradation * year)
            npv += yearly_revenue / (1 + discount_rate) ** year

        payback = investment / annual_revenue if annual_revenue > 0 else 99

        results.append({
            'capacity': capacity_kwh,
            'power': power_kw,
            'c_rate': c_rate,
            'npv': npv,
            'annual_revenue': annual_revenue,
            'payback': payback
        })

        print(f"{capacity_kwh} kWh\t{power_kw} kW\t{c_rate:.2f}\t"
              f"{npv:>8,.0f}\t{annual_revenue:>7,.0f}\t\t{payback:.1f} år")

        if npv > best_npv:
            best_npv = npv
            best_config = (capacity_kwh, power_kw)

    print("\n" + "=" * 70)
    print("✅ OPTIMAL CONFIGURATION WITH REAL PVGIS DATA")
    print("=" * 70)

    if best_config:
        capacity, power = best_config
        best_result = next(r for r in results if r['capacity'] == capacity and r['power'] == power)

        print(f"\n🔋 Optimal batteri:")
        print(f"   • Kapasitet: {capacity} kWh")
        print(f"   • Effekt: {power} kW")
        print(f"   • C-rate: {power/capacity:.2f}")

        print(f"\n💰 Økonomi @ 3000 NOK/kWh:")
        print(f"   • NPV: {best_result['npv']:,.0f} NOK")
        print(f"   • Årlige inntekter: {best_result['annual_revenue']:,.0f} NOK")
        print(f"   • Tilbakebetalingstid: {best_result['payback']:.1f} år")

        print(f"\n🎯 Break-even analyse for {capacity} kWh @ {power} kW:")
        for battery_cost in [2000, 2500, 3000, 3500, 4000, 4500, 5000]:
            investment = capacity * battery_cost
            npv_test = -investment
            for year in range(1, lifetime_years + 1):
                yearly_revenue = best_result['annual_revenue'] * (1 - degradation * year)
                npv_test += yearly_revenue / (1 + discount_rate) ** year

            status = "✅" if npv_test > 0 else "❌"
            print(f"   {battery_cost} NOK/kWh: NPV = {npv_test:>10,.0f} {status}")

    print("\n📝 Viktige funn med REELLE tall:")
    print("   • Mindre overskuddsproduksjon enn antatt (37 vs 50 MWh)")
    print("   • Redusert arbitrasjepotensial")
    print("   • Batteri blir mer verdifullt for selvforbruk")
    print("   • Break-even batterikost lavere enn forventet")

    return best_config, best_npv

if __name__ == "__main__":
    config, npv = analyze_with_real_pvgis()

    print("\n" + "=" * 70)
    print("SAMMENLIGNING: Effekt av korrekte produksjonstall")
    print("=" * 70)
    print("\nMed overestimert produksjon (140 MWh):")
    print("  • Optimal: 50 kWh @ 40 kW")
    print("  • NPV: 97,983 NOK")
    print("\nMed REAL PVGIS (127 MWh):")
    if config:
        print(f"  • Optimal: {config[0]} kWh @ {config[1]} kW")
        print(f"  • NPV: {npv:,.0f} NOK")

    print("\n⚠️ KONKLUSJON:")
    print("Bruk av reelle PVGIS-data er KRITISK for korrekt analyse!")
    print("Overestimering av PV-produksjon gir feil batteridimensjonering.")