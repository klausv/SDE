"""
Clean, modular battery analysis
"""
import pandas as pd
from analysis.data_generators import generate_complete_dataset
from analysis.value_drivers import calculate_all_value_drivers
from analysis.economic_analysis import (
    analyze_battery_economics,
    sensitivity_analysis,
    find_break_even_cost
)


def main():
    """Run complete battery analysis with clean, modular code"""

    print("\n" + "="*60)
    print("BATTERIANALYSE - MODULÆR VERSJON")
    print("="*60)

    # ========================================
    # 1. GENERER DATA
    # ========================================
    print("\n1️⃣ GENERERER TIDSSERIEDATA...")
    print("-" * 40)

    # Anleggsparametere
    PV_CAPACITY_KWP = 138.55
    INVERTER_LIMIT_KW = 110  # Inverter begrenser maks produksjon
    ANNUAL_CONSUMPTION_KWH = 90000
    GRID_LIMIT_KW = 77  # Nett-eksport begrensning (70% av inverter)
    BATTERY_CAPACITY_KWH = 50
    BATTERY_POWER_KW = 25

    # Generer komplett datasett
    data = generate_complete_dataset(
        year=2024,
        pv_capacity_kwp=PV_CAPACITY_KWP,
        inverter_limit_kw=INVERTER_LIMIT_KW,
        annual_consumption_kwh=ANNUAL_CONSUMPTION_KWH,
        profile_type='commercial'
    )

    print(f"✅ Generert {len(data)} timer med data")
    print(f"✅ Årsproduksjon: {data['production_kw'].sum()/1000:.1f} MWh")
    print(f"✅ Årsforbruk: {data['consumption_kw'].sum()/1000:.1f} MWh")
    print(f"✅ Gjennomsnittspris: {data['spot_price_nok'].mean():.2f} NOK/kWh")

    # ========================================
    # 2. BEREGN VERDIDRIVERE
    # ========================================
    print("\n2️⃣ BEREGNER VERDIDRIVERE...")
    print("-" * 40)

    value_drivers = calculate_all_value_drivers(
        data=data,
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        battery_power_kw=BATTERY_POWER_KW,
        grid_limit_kw=GRID_LIMIT_KW
    )

    # Vis resultater
    print(f"\n📊 VERDIDRIVERE ({BATTERY_CAPACITY_KWH} kWh batteri):")
    print("-" * 40)

    for driver_name in ['curtailment', 'arbitrage', 'demand_charge', 'self_consumption']:
        driver = value_drivers[driver_name]
        print(f"{driver_name.upper():20} {driver['annual_value_nok']:8,.0f} NOK ({driver['percentage_of_total']:4.0f}%)")

    print("-" * 40)
    print(f"{'TOTAL':20} {value_drivers['total_annual_value_nok']:8,.0f} NOK/år")

    # Detaljer om avkortning
    print(f"\n📈 AVKORTNINGSDETALJER:")
    print(f"   • Total avkortet: {value_drivers['curtailment']['total_kwh']:,.0f} kWh/år")
    print(f"   • Timer med avkortning: {value_drivers['curtailment']['hours']}")
    print(f"   • Andel av produksjon: {value_drivers['curtailment']['percentage_of_production']:.1f}%")

    # ========================================
    # 3. ØKONOMISK ANALYSE
    # ========================================
    print("\n3️⃣ ØKONOMISK ANALYSE...")
    print("-" * 40)

    # Test forskjellige batterikostnader
    BATTERY_COST_CURRENT = 5000  # NOK/kWh dagens pris
    BATTERY_COST_TARGET = 3000   # NOK/kWh målpris

    # Analyse med dagens kostnad
    economics_current = analyze_battery_economics(
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        battery_cost_per_kwh=BATTERY_COST_CURRENT,
        annual_value=value_drivers['total_annual_value_nok']
    )

    # Analyse med målkostnad
    economics_target = analyze_battery_economics(
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        battery_cost_per_kwh=BATTERY_COST_TARGET,
        annual_value=value_drivers['total_annual_value_nok']
    )

    print(f"\n💰 LØNNSOMHET VED FORSKJELLIGE KOSTNADER:")
    print("-" * 40)
    print(f"Ved {BATTERY_COST_CURRENT:,} NOK/kWh (dagens pris):")
    print(f"   • NPV: {economics_current['npv']:,.0f} NOK")
    print(f"   • IRR: {economics_current['irr']:.1%}" if economics_current['irr'] else "   • IRR: N/A")
    print(f"   • Status: {'✅ LØNNSOMT' if economics_current['profitable'] else '❌ ULØNNSOMT'}")

    print(f"\nVed {BATTERY_COST_TARGET:,} NOK/kWh (målpris):")
    print(f"   • NPV: {economics_target['npv']:,.0f} NOK")
    print(f"   • IRR: {economics_target['irr']:.1%}" if economics_target['irr'] else "   • IRR: N/A")
    print(f"   • Tilbakebetalingstid: {economics_target['payback_years']:.1f} år")
    print(f"   • Status: {'✅ LØNNSOMT' if economics_target['profitable'] else '❌ ULØNNSOMT'}")

    # ========================================
    # 4. FINN BREAK-EVEN
    # ========================================
    print("\n4️⃣ BREAK-EVEN ANALYSE...")
    print("-" * 40)

    break_even = find_break_even_cost(
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        annual_value=value_drivers['total_annual_value_nok']
    )

    print(f"🎯 Break-even batterikostnad: {break_even:,.0f} NOK/kWh")
    print(f"   (Ved denne kostnaden er NPV = 0)")

    # ========================================
    # 5. SENSITIVITETSANALYSE
    # ========================================
    print("\n5️⃣ SENSITIVITETSANALYSE...")
    print("-" * 40)

    sensitivity_results = sensitivity_analysis(
        base_capacity_kwh=BATTERY_CAPACITY_KWH,
        base_annual_value=value_drivers['total_annual_value_nok'],
        cost_range=(2000, 5000),
        cost_steps=7
    )

    print("\nKostnad | NPV        | IRR   | Status")
    print("-" * 40)
    for result in sensitivity_results:
        status = "✅" if result['profitable'] else "❌"
        irr_str = f"{result['irr']:.1%}" if result['irr'] else "  N/A"
        print(f"{result['cost_per_kwh']:,} kr | {result['npv']:10,.0f} | {irr_str} | {status}")

    # ========================================
    # 6. OPPSUMMERING
    # ========================================
    print("\n" + "="*60)
    print("OPPSUMMERING")
    print("="*60)

    print(f"""
ANLEGGSDATA:
• Solceller: {PV_CAPACITY_KWP} kWp
• Årsproduksjon: {data['production_kw'].sum()/1000:.1f} MWh
• Årsforbruk: {data['consumption_kw'].sum()/1000:.1f} MWh

BATTERISPESIFIKASJONER:
• Størrelse: {BATTERY_CAPACITY_KWH} kWh
• Effekt: {BATTERY_POWER_KW} kW

VERDIDRIVERE:
• Total årlig verdi: {value_drivers['total_annual_value_nok']:,.0f} NOK
• Viktigste driver: {max(value_drivers['demand_charge']['percentage_of_total'],
                         value_drivers['arbitrage']['percentage_of_total']):.0f}% ({"effekttariff" if value_drivers['demand_charge']['percentage_of_total'] > value_drivers['arbitrage']['percentage_of_total'] else "arbitrasje"})

AVKORTNING:
• Total: {value_drivers['curtailment']['total_kwh']:,.0f} kWh/år
• Verdi: {value_drivers['curtailment']['annual_value_nok']:,.0f} NOK/år
• Andel av total verdi: {value_drivers['curtailment']['percentage_of_total']:.0f}%

ØKONOMI:
• Break-even kostnad: {break_even:,.0f} NOK/kWh
• Status ved {BATTERY_COST_CURRENT:,} NOK/kWh: {"✅ LØNNSOMT" if economics_current['profitable'] else "❌ ULØNNSOMT"}
• Status ved {BATTERY_COST_TARGET:,} NOK/kWh: {"✅ LØNNSOMT" if economics_target['profitable'] else "❌ ULØNNSOMT"}

ANBEFALING:
{"✅ Batteriet er lønnsomt med dagens priser!" if economics_current['profitable'] else
f"⏳ Vent til batterikostnaden faller under {break_even:,.0f} NOK/kWh" if break_even < BATTERY_COST_CURRENT else
"❌ Batteriet er ikke lønnsomt med dagens teknologi"}
""")


if __name__ == "__main__":
    main()