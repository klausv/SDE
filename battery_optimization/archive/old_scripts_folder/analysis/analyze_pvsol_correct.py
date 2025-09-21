#!/usr/bin/env python3
"""
Battery optimization with CORRECT PVsol data
Based on actual simulation from Snødevegen 122
"""
import numpy as np

def analyze_with_pvsol_data():
    """
    Analyze battery economics with actual PVsol simulation data
    """
    print("=" * 70)
    print("🔋 BATTERIOPTIMALISERING - KORREKTE PARAMETERE")
    print("=" * 70)

    # KORREKTE systemparametere
    pv_capacity = 138.55  # kWp (installert effekt)
    pv_annual = 133_017  # kWh/år (PVsol resultat med 30° takvinkel)
    load_annual = 90_000  # kWh/år (spesifisert av bruker)
    grid_limit = 70  # kW (70% av 100 kW inverter)
    inverter_capacity = 100  # kW (MAX 100KTL3-X LV)
    tilt_angle = 30  # grader (KORREKT takvinkel)

    print("\n📊 Energibalanse (korrekte parametere):")
    print(f"  • PV installert: {pv_capacity:.2f} kWp")
    print(f"  • Årlig PV-produksjon: {pv_annual/1000:.1f} MWh")
    print(f"  • Spesifikk ytelse: {pv_annual/pv_capacity:.0f} kWh/kWp")
    print(f"  • Takvinkel: {tilt_angle}°")
    print(f"  • Performance Ratio: 92.62%")
    print(f"  • Annual consumption: {load_annual/1000:.0f} MWh")

    # Calculate actual energy flows with 90 MWh load
    self_consumption = min(pv_annual, load_annual)  # Max possible self-consumption
    grid_export = max(0, pv_annual - load_annual)  # Excess PV
    grid_import = max(0, load_annual - self_consumption)  # Additional need from grid
    self_sufficiency = (self_consumption / load_annual) * 100 if load_annual > 0 else 0

    print(f"  • Self-consumption: {self_consumption/1000:.1f} MWh")
    print(f"  • Grid export: {grid_export/1000:.1f} MWh")
    print(f"  • Grid import: {grid_import/1000:.1f} MWh")
    print(f"  • Self-sufficiency: {self_sufficiency:.1f}%")

    # Load profile (commercial building)
    base_load = load_annual / 8760  # ~10.3 kW average for 90 MWh
    peak_load = base_load * 2.5  # ~26 kW peak
    night_load = base_load * 0.3  # ~3 kW night

    print(f"\n🏢 Load Profile ({load_annual/1000:.0f} MWh/year):")
    print(f"  • Average: {base_load:.1f} kW")
    print(f"  • Peak (day): {peak_load:.1f} kW")
    print(f"  • Min (night): {night_load:.1f} kW")
    print(f"  • Grid limit: {grid_limit} kW")

    # Battery configurations to test
    configs = [
        (30, 20), (30, 30),
        (50, 30), (50, 40), (50, 50),
        (75, 40), (75, 50), (75, 60),
        (100, 50), (100, 60), (100, 75), (100, 100),
        (125, 60), (125, 75), (125, 100),
        (150, 75), (150, 100), (150, 120),
        (200, 100), (200, 150)
    ]

    print("\n📊 Testing battery configurations...\n")
    print("Capacity\tPower\tC-rate\tNPV\t\tRevenue\t\tPayback")
    print("-" * 75)

    best_npv = -float('inf')
    best_config = None
    results = []

    for capacity_kwh, power_kw in configs:
        c_rate = power_kw / capacity_kwh

        # Revenue calculations with 90 MWh load, 133 MWh PV

        # 1. Energy arbitrage (limited due to excess PV)
        daily_cycles = 0.8  # Moderate cycling with 90 MWh load and excess PV
        annual_throughput = capacity_kwh * daily_cycles * 365 * 0.85
        price_spread = 0.35  # NOK/kWh average spread
        arbitrage_revenue = annual_throughput * price_spread

        # 2. Increased self-consumption (important with 43 MWh excess PV)
        # With 90 MWh load and 133 MWh PV, we have significant excess
        max_additional_self = min(capacity_kwh * 200, 30_000)  # kWh/year
        self_consumption_value = max_additional_self * 0.25  # value vs grid

        # 3. Peak shaving (less important with 26 kW peaks, well below 70 kW limit)
        peak_reduction_kw = min(power_kw * 0.3, 10)  # Limited peak reduction potential
        annual_tariff_saving = peak_reduction_kw * 2000  # NOK/kW/year

        # 4. Grid services (with 100 kW inverter capacity)
        if power_kw >= capacity_kwh * 0.5 and power_kw <= 100:
            grid_services = capacity_kwh * 60  # NOK/kWh/year
        else:
            grid_services = 0

        # 5. Avoided curtailment (important with 43 MWh excess PV)
        # With 133 MWh PV and 90 MWh load, we have 43 MWh excess that could be curtailed
        curtailable_kwh = min(capacity_kwh * 100, 20_000)  # kWh/year that could be saved
        curtailment_value = curtailable_kwh * 0.6  # Value of avoided curtailment

        # Total annual revenue
        annual_revenue = (arbitrage_revenue + self_consumption_value +
                         annual_tariff_saving + grid_services + curtailment_value)

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

        if npv > 0:  # Only show profitable configs
            print(f"{capacity_kwh} kWh\t{power_kw} kW\t{c_rate:.2f}\t"
                  f"{npv:>8,.0f}\t{annual_revenue:>7,.0f}\t\t{payback:.1f} år")

        if npv > best_npv:
            best_npv = npv
            best_config = (capacity_kwh, power_kw)

    print("\n" + "=" * 70)
    print("✅ OPTIMAL CONFIGURATION WITH PVSOL DATA")
    print("=" * 70)

    if best_config:
        capacity, power = best_config
        best_result = next(r for r in results if r['capacity'] == capacity and r['power'] == power)

        print(f"\n🔋 Optimal batteri:")
        print(f"   • Kapasitet: {capacity} kWh")
        print(f"   • Effekt: {power} kW")
        print(f"   • C-rate: {power/capacity:.2f}")
        print(f"   • Inverter limit: {min(power, 100)} kW")

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

    print(f"\n📝 Viktige funn med PVsol data ({load_annual/1000:.0f} MWh forbruk):")
    print("   • Overskuddsproduksjon (43 MWh) gir curtailment-muligheter")
    print("   • Moderat forbruk begrenser arbitrasjepotensial")
    print("   • Inverterkapasitet (100 kW) begrenser batterieffekt")
    print("   • Grid limit 70 kW gir peak shaving muligheter")

    return best_config, best_npv

if __name__ == "__main__":
    config, npv = analyze_with_pvsol_data()

    print("\n" + "=" * 70)
    print("KONKLUSJON")
    print("=" * 70)
    print("\nMed korrekte PVsol-tall:")
    print(f"  • PV: 138.55 kWp → 133 MWh/år")
    print(f"  • Forbruk: 90 MWh/år")
    print(f"  • Netteksport: 43 MWh/år")
    print(f"  • Grid limit: 70 kW")
    if config:
        print(f"\nOptimal batteristørrelse: {config[0]} kWh @ {config[1]} kW")
        print(f"NPV: {npv:,.0f} NOK")

    print("\n⚠️ MERK: Med 90 MWh forbruk er Lnett-tariffen standard")
    print("for bedrifter <100 MWh/år.")