"""
Clean battery analysis V2 - Med ResultPresenter og sensitivitetsanalyse
"""
import pandas as pd
from analysis.data_generators import generate_complete_dataset
from analysis.value_drivers import calculate_all_value_drivers
from analysis.economic_analysis import (
    analyze_battery_economics,
    sensitivity_analysis,
    find_break_even_cost
)
from analysis.result_presenter import BatteryAnalysisResults, ResultPresenter


def main():
    """Kjør komplett batterianalyse med ren kode"""

    # ========================================
    # KONFIGURASJON
    # ========================================
    # Anleggsparametere
    PV_CAPACITY_KWP = 138.55
    INVERTER_LIMIT_KW = 110
    ANNUAL_CONSUMPTION_KWH = 90000
    GRID_LIMIT_KW = 77
    BATTERY_CAPACITY_KWH = 100
    BATTERY_POWER_KW = 50

    # Økonomiske parametere
    BATTERY_COST_CURRENT = 5000  # NOK/kWh dagens pris
    BATTERY_COST_TARGET = 3000   # NOK/kWh målpris

    # ========================================
    # DATAGENERING
    # ========================================
    print("\n⏳ Genererer tidsseriedata...")
    data = generate_complete_dataset(
        year=2024,
        pv_capacity_kwp=PV_CAPACITY_KWP,
        inverter_limit_kw=INVERTER_LIMIT_KW,
        annual_consumption_kwh=ANNUAL_CONSUMPTION_KWH,
        profile_type='commercial'
    )

    # ========================================
    # VERDIDRIVERE
    # ========================================
    print("⏳ Beregner verdidrivere...")
    value_drivers = calculate_all_value_drivers(
        data=data,
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        battery_power_kw=BATTERY_POWER_KW,
        grid_limit_kw=GRID_LIMIT_KW
    )

    # ========================================
    # ØKONOMISK ANALYSE
    # ========================================
    print("⏳ Kjører økonomisk analyse...")

    # Analyse med dagens kostnad
    economics_current = analyze_battery_economics(
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        battery_cost_per_kwh=BATTERY_COST_CURRENT,
        annual_value=value_drivers['total_annual_value_nok']
    )

    # Break-even analyse
    break_even = find_break_even_cost(
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        annual_value=value_drivers['total_annual_value_nok']
    )

    # Sensitivitetsanalyse
    sensitivity_results = sensitivity_analysis(
        base_capacity_kwh=BATTERY_CAPACITY_KWH,
        base_annual_value=value_drivers['total_annual_value_nok'],
        cost_range=(2000, 6000),
        cost_steps=9
    )

    # ========================================
    # OPPRETT RESULTAT-OBJEKT
    # ========================================
    results = BatteryAnalysisResults(
        # System parameters
        pv_capacity_kwp=PV_CAPACITY_KWP,
        inverter_limit_kw=INVERTER_LIMIT_KW,
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        battery_power_kw=BATTERY_POWER_KW,
        grid_limit_kw=GRID_LIMIT_KW,
        annual_consumption_kwh=ANNUAL_CONSUMPTION_KWH,

        # Data summary
        annual_production_mwh=data['production_kw'].sum() / 1000,
        annual_consumption_mwh=data['consumption_kw'].sum() / 1000,
        avg_spot_price=data['spot_price_nok'].mean(),

        # Value drivers
        curtailment_kwh=value_drivers['curtailment']['total_kwh'],
        curtailment_value_nok=value_drivers['curtailment']['annual_value_nok'],
        arbitrage_value_nok=value_drivers['arbitrage']['annual_value_nok'],
        demand_charge_value_nok=value_drivers['demand_charge']['annual_value_nok'],
        self_consumption_value_nok=value_drivers['self_consumption']['annual_value_nok'],
        total_annual_value_nok=value_drivers['total_annual_value_nok'],

        # Economics
        battery_cost_per_kwh=BATTERY_COST_CURRENT,
        initial_investment=economics_current['initial_investment'],
        npv=economics_current['npv'],
        irr=economics_current['irr'],
        payback_years=economics_current['payback_years'],
        break_even_cost=break_even,

        # Sensitivity analysis
        sensitivity_results=sensitivity_results
    )

    # ========================================
    # VIS RESULTATER
    # ========================================
    presenter = ResultPresenter(results)
    presenter.print_full_report("KOMPLETT BATTERIANALYSE")

    # ========================================
    # SAMMENLIGN MED MÅLPRIS
    # ========================================
    print(f"\n📊 SAMMENLIGNING MED MÅLPRIS ({BATTERY_COST_TARGET:,} NOK/kWh):")
    print("-" * 40)

    economics_target = analyze_battery_economics(
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        battery_cost_per_kwh=BATTERY_COST_TARGET,
        annual_value=value_drivers['total_annual_value_nok']
    )

    print(f"Ved {BATTERY_COST_TARGET:,} NOK/kWh:")
    print(f"   • NPV: {economics_target['npv']:,.0f} NOK")
    print(f"   • IRR: {economics_target['irr']:.1%}" if economics_target['irr'] else "   • IRR: N/A")
    print(f"   • Tilbakebetalingstid: {economics_target['payback_years']:.1f} år")
    print(f"   • Status: {'✅ LØNNSOMT' if economics_target['profitable'] else '❌ ULØNNSOMT'}")

    improvement = economics_target['npv'] - economics_current['npv']
    print(f"\n   → NPV forbedring: {improvement:,.0f} NOK")
    print(f"   → {improvement/economics_current['initial_investment']*100:.0f}% bedre avkastning")


if __name__ == "__main__":
    main()