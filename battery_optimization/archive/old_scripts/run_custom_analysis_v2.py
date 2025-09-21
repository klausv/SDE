"""
Tilpassbar batterisimulering V2 - Med ren ResultPresenter
"""
import pandas as pd
from analysis.data_generators import generate_complete_dataset
from analysis.value_drivers import calculate_all_value_drivers
from analysis.economic_analysis import (
    analyze_battery_economics,
    find_break_even_cost
)
from analysis.result_presenter import BatteryAnalysisResults, ResultPresenter

# ============================================
# 📝 JUSTERBARE PARAMETERE - ENDRE DISSE!
# ============================================

# Solcelleanlegg
PV_CAPACITY_KWP = 138.55        # Endre meg! (standard: 138.55)
INVERTER_LIMIT_KW = 110          # Endre meg! (standard: 110)

# Forbruk
ANNUAL_CONSUMPTION_KWH = 90000   # Endre meg! (standard: 90000)

# Nettbegrensning
GRID_LIMIT_KW = 77               # Endre meg! (standard: 77)

# BATTERI - HOVEDPARAMETERE
BATTERY_CAPACITY_KWH = 100       # Endre meg! Prøv: 50, 80, 100, 150, 200
BATTERY_POWER_KW = 50            # Endre meg! Prøv: 25, 40, 50, 75, 100

# ØKONOMI
BATTERY_COST_NOK_PER_KWH = 5000  # Endre meg! Prøv: 2000, 3000, 4000, 5000
DISCOUNT_RATE = 0.05             # Endre meg! (5% standard)
PROJECT_YEARS = 15               # Endre meg! (15 år standard)

# ============================================
# KJØR SIMULERING
# ============================================


def run_analysis():
    """Kjør analyse og returner resultater"""

    # 1. Generer data
    print("\n⏳ Genererer data...")
    data = generate_complete_dataset(
        year=2024,
        pv_capacity_kwp=PV_CAPACITY_KWP,
        inverter_limit_kw=INVERTER_LIMIT_KW,
        annual_consumption_kwh=ANNUAL_CONSUMPTION_KWH,
        profile_type='commercial'
    )

    # 2. Beregn verdidrivere
    print("⏳ Beregner verdidrivere...")
    value_drivers = calculate_all_value_drivers(
        data=data,
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        battery_power_kw=BATTERY_POWER_KW,
        grid_limit_kw=GRID_LIMIT_KW
    )

    # 3. Økonomisk analyse
    print("⏳ Kjører økonomisk analyse...")
    economics = analyze_battery_economics(
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        battery_cost_per_kwh=BATTERY_COST_NOK_PER_KWH,
        annual_value=value_drivers['total_annual_value_nok'],
        project_years=PROJECT_YEARS,
        discount_rate=DISCOUNT_RATE
    )

    # 4. Break-even analyse
    break_even = find_break_even_cost(
        battery_capacity_kwh=BATTERY_CAPACITY_KWH,
        annual_value=value_drivers['total_annual_value_nok']
    )

    # 5. Opprett resultat-objekt
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
        battery_cost_per_kwh=BATTERY_COST_NOK_PER_KWH,
        initial_investment=economics['initial_investment'],
        npv=economics['npv'],
        irr=economics['irr'],
        payback_years=economics['payback_years'],
        break_even_cost=break_even
    )

    return results


def main():
    """Hovedprogram"""
    # Kjør analyse
    results = run_analysis()

    # Vis resultater med ResultPresenter
    presenter = ResultPresenter(results)

    # Velg output-format (kan enkelt endres)
    # presenter.print_summary()  # For kort versjon
    presenter.print_full_report("TILPASSET BATTERIANALYSE")  # For full versjon


if __name__ == "__main__":
    main()