"""
Tilpassbar batterisimulering - ENDRE PARAMETERE HER!
"""
import sys
import pandas as pd
from analysis.data_generators import generate_complete_dataset
from analysis.value_drivers import calculate_all_value_drivers
from analysis.economic_analysis import analyze_battery_economics

# ============================================
# 📝 JUSTERBARE PARAMETERE - ENDRE DISSE!
# ============================================

# Solcelleanlegg
PV_CAPACITY_KWP = 138.55        # Endre meg! (standard: 138.55)
INVERTER_LIMIT_KW = 110          # Endre meg! (standard: 110) - Maks effekt fra inverter

# Forbruk
ANNUAL_CONSUMPTION_KWH = 90000   # Endre meg! (standard: 90000)

# Nettbegrensning
GRID_LIMIT_KW = 77               # Endre meg! (standard: 77) - Maks eksport til nett

# BATTERI - HOVEDPARAMETERE
BATTERY_CAPACITY_KWH = 50        # Endre meg! Prøv: 50, 80, 100, 150, 200
BATTERY_POWER_KW = 25            # Endre meg! Prøv: 25, 40, 50, 75, 100

# ØKONOMI
BATTERY_COST_NOK_PER_KWH = 5000  # Endre meg! Prøv: 2000, 3000, 4000, 5000
DISCOUNT_RATE = 0.05             # Endre meg! (5% standard)
PROJECT_YEARS = 15               # Endre meg! (15 år standard)

# ============================================
# KJØR SIMULERING (ikke endre under her)
# ============================================

def run_custom_analysis():
    print("\n" + "="*60)
    print("🔋 TILPASSET BATTERIANALYSE")
    print("="*60)

    print(f"\n📊 DINE VALGTE PARAMETERE:")
    print(f"   • Batteri: {BATTERY_CAPACITY_KWH} kWh / {BATTERY_POWER_KW} kW")
    print(f"   • Kostnad: {BATTERY_COST_NOK_PER_KWH:,} NOK/kWh")
    print(f"   • Solceller: {PV_CAPACITY_KWP} kWp")
    print(f"   • Inverter: {INVERTER_LIMIT_KW} kW")
    print(f"   • Forbruk: {ANNUAL_CONSUMPTION_KWH:,} kWh/år")
    print(f"   • Nettgrense: {GRID_LIMIT_KW} kW")

    # Generer data
    print("\n⏳ Genererer data...")
    data = generate_complete_dataset(
        year=2024,
        pv_capacity_kwp=PV_CAPACITY_KWP,
        inverter_limit_kw=INVERTER_LIMIT_KW,
        annual_consumption_kwh=ANNUAL_CONSUMPTION_KWH,
        profile_type='commercial'
    )

    # Beregn verdidrivere
    print("⏳ Beregner verdidrivere...")
    value_drivers = calculate_all_value_drivers(
        data=data,
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        battery_power_kw=BATTERY_POWER_KW,
        grid_limit_kw=GRID_LIMIT_KW
    )

    # Økonomisk analyse
    print("⏳ Kjører økonomisk analyse...")
    economics = analyze_battery_economics(
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        battery_cost_per_kwh=BATTERY_COST_NOK_PER_KWH,
        annual_value=value_drivers['total_annual_value_nok'],
        project_years=PROJECT_YEARS,
        discount_rate=DISCOUNT_RATE
    )

    # ============================================
    # VIS RESULTATER
    # ============================================

    print("\n" + "="*60)
    print("📊 RESULTATER")
    print("="*60)

    print(f"\n💰 VERDIDRIVERE:")
    print(f"   • Avkortning: {value_drivers['curtailment']['annual_value_nok']:,.0f} NOK/år")
    print(f"     ({value_drivers['curtailment']['total_kwh']:,.0f} kWh/år)")
    print(f"   • Arbitrasje: {value_drivers['arbitrage']['annual_value_nok']:,.0f} NOK/år")
    print(f"   • Effekttariff: {value_drivers['demand_charge']['annual_value_nok']:,.0f} NOK/år")
    print(f"   • Selvforsyning: {value_drivers['self_consumption']['annual_value_nok']:,.0f} NOK/år")
    print(f"   ────────────────────────────────")
    print(f"   TOTAL: {value_drivers['total_annual_value_nok']:,.0f} NOK/år")

    print(f"\n📈 ØKONOMI:")
    print(f"   • Investeringskostnad: {economics['initial_investment']:,.0f} NOK")
    print(f"   • NPV: {economics['npv']:,.0f} NOK")
    if economics['irr']:
        print(f"   • IRR: {economics['irr']:.1%}")
    print(f"   • Tilbakebetalingstid: {economics['payback_years']:.1f} år")

    print(f"\n🎯 KONKLUSJON:")
    if economics['npv'] > 0:
        print(f"   ✅ LØNNSOMT! NPV er positiv ({economics['npv']:,.0f} NOK)")
        print(f"   → Investeringen gir {economics['irr']:.1%} årlig avkastning")
    else:
        print(f"   ❌ ULØNNSOMT! NPV er negativ ({economics['npv']:,.0f} NOK)")
        print(f"   → Batterikostnaden må ned for lønnsomhet")

    # Break-even beregning
    from analysis.economic_analysis import find_break_even_cost
    break_even = find_break_even_cost(
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        annual_value=value_drivers['total_annual_value_nok']
    )

    print(f"\n💡 BREAK-EVEN:")
    print(f"   Maksimal batterikostnad for lønnsomhet: {break_even:,.0f} NOK/kWh")
    if BATTERY_COST_NOK_PER_KWH > break_even:
        print(f"   → Du betaler {BATTERY_COST_NOK_PER_KWH - break_even:,.0f} NOK/kWh for mye")
    else:
        print(f"   → Du har {break_even - BATTERY_COST_NOK_PER_KWH:,.0f} NOK/kWh margin")

    return economics

if __name__ == "__main__":
    # Kjør analyse
    results = run_custom_analysis()

    # Tips til bruker
    print("\n" + "="*60)
    print("💡 TIPS: Rediger parametrene øverst i filen og kjør på nytt!")
    print("="*60)