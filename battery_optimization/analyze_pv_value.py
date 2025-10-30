"""
Analyze PV Value Metrics

Calculates the average obtained price of PV generation for:
1. Reference case (no battery)
2. Heuristic battery strategy

Shows how battery storage improves PV economics by increasing self-consumption.
"""

import numpy as np
import pandas as pd

from core.battery import Battery
from core.strategies import NoControlStrategy, SimpleRuleStrategy
from core.simulator import BatterySimulator
from core.economic_cost import (calculate_total_cost, get_energy_tariff,
                                get_consumption_tax)
from core.pv_value_metrics import (calculate_pv_value_metrics,
                                   print_pv_value_summary,
                                   compare_pv_value)
from core.pvgis_solar import PVGISProduction
from core.price_fetcher import ENTSOEPriceFetcher
from core.consumption_profiles import ConsumptionProfile


def main():
    print("\n" + "="*80)
    print(" PV VALUE ANALYSIS")
    print(" Average Obtained Price of PV Generation")
    print("="*80)

    # Load data
    print("\nLoading data...")

    pvgis = PVGISProduction(
        lat=58.97, lon=5.73, pv_capacity_kwp=138.55,
        tilt=30, azimuth=173, system_loss=14
    )
    production = pvgis.fetch_hourly_production(2024, refresh=False)
    year = production.index[0].year

    consumption = ConsumptionProfile.generate_annual_profile(
        profile_type='commercial_office',
        annual_kwh=300000,
        year=year
    )

    price_fetcher = ENTSOEPriceFetcher()
    spot_prices = price_fetcher.fetch_prices(2024, 'NO2', refresh=False)
    spot_prices.index = spot_prices.index.map(lambda x: x.replace(year=year))

    if spot_prices.isna().any():
        spot_prices = spot_prices.ffill().bfill()

    min_len = min(len(production), len(consumption), len(spot_prices))
    production = production[:min_len]
    consumption = consumption[:min_len]
    spot_prices = spot_prices[:min_len]
    timestamps = production.index

    print(f"  Data loaded: {min_len} hours (year {year})")

    # Prepare tariff arrays
    energy_tariff = np.array([get_energy_tariff(ts) for ts in timestamps])
    consumption_tax = np.array([get_consumption_tax(ts.month) for ts in timestamps])

    # Run simulations
    print("\nRunning simulations...")

    # Reference case
    print("  - Reference case (no battery)...")
    strategy_ref = NoControlStrategy()
    sim_ref = BatterySimulator(strategy=strategy_ref, battery=None)
    results_ref = sim_ref.simulate_year(
        production, consumption, spot_prices,
        solar_inverter_capacity_kw=110,
        grid_export_limit_kw=77,
        battery_inverter_efficiency=0.98
    )

    # Heuristic strategy
    print("  - Heuristic strategy (SimpleRule)...")
    battery = Battery(
        capacity_kwh=20.0,
        power_kw=10.0,
        efficiency=0.90,
        min_soc=0.1,
        max_soc=0.9,
        max_c_rate_charge=1.0,
        max_c_rate_discharge=1.0
    )

    strategy_heur = SimpleRuleStrategy(
        cheap_price_threshold=0.3,
        expensive_price_threshold=0.8,
        night_hours=(0, 6)
    )

    sim_heur = BatterySimulator(strategy=strategy_heur, battery=battery)
    results_heur = sim_heur.simulate_year(
        production, consumption, spot_prices,
        solar_inverter_capacity_kw=110,
        grid_export_limit_kw=77,
        battery_inverter_efficiency=0.98
    )

    print("  ✓ Simulations complete")

    # Calculate PV value metrics
    print("\nCalculating PV value metrics...")

    # Reference case
    pv_metrics_ref = calculate_pv_value_metrics(
        pv_production_kw=results_ref['production_ac_kw'].values,
        load_consumption_kw=results_ref['consumption_kw'].values,
        grid_import_kw=results_ref['grid_power_kw'].clip(lower=0).values,
        grid_export_kw=(-results_ref['grid_power_kw'].clip(upper=0)).values,
        timestamps=timestamps,
        spot_prices=spot_prices.values,
        energy_tariff_nok_kwh=energy_tariff,
        consumption_tax_nok_kwh=consumption_tax,
        feed_in_tariff=0.04,
        timestep_hours=1.0
    )

    # Heuristic case
    pv_metrics_heur = calculate_pv_value_metrics(
        pv_production_kw=results_heur['production_ac_kw'].values,
        load_consumption_kw=results_heur['consumption_kw'].values,
        grid_import_kw=results_heur['grid_power_kw'].clip(lower=0).values,
        grid_export_kw=(-results_heur['grid_power_kw'].clip(upper=0)).values,
        timestamps=timestamps,
        spot_prices=spot_prices.values,
        energy_tariff_nok_kwh=energy_tariff,
        consumption_tax_nok_kwh=consumption_tax,
        feed_in_tariff=0.04,
        timestep_hours=1.0
    )

    print("  ✓ Metrics calculated")

    # Print results
    print_pv_value_summary(pv_metrics_ref, scenario_name="Reference Case (No Battery)")
    print_pv_value_summary(pv_metrics_heur, scenario_name="Heuristic Strategy (20 kWh Battery)")

    # Compare
    comparison = compare_pv_value(pv_metrics_ref, pv_metrics_heur)

    # Additional insights
    print("\n" + "="*80)
    print(" KEY INSIGHTS")
    print("="*80)

    print("\n1. SELF-CONSUMPTION")
    print("-" * 80)
    print(f"   Without battery: {pv_metrics_ref['self_consumption_rate']*100:.1f}% "
          f"of PV is self-consumed")
    print(f"   With battery:    {pv_metrics_heur['self_consumption_rate']*100:.1f}% "
          f"of PV is self-consumed")
    print(f"   → Battery increases self-consumption by "
          f"{comparison['self_consumption_improvement_pct']:.1f} percentage points")

    print("\n2. PV ECONOMIC VALUE")
    print("-" * 80)
    print(f"   Without battery: PV generates {pv_metrics_ref['pv_total_value_nok']:,.0f} NOK/year")
    print(f"   With battery:    PV generates {pv_metrics_heur['pv_total_value_nok']:,.0f} NOK/year")
    print(f"   → Battery increases PV value by {comparison['pv_value_improvement_nok']:,.0f} NOK/year "
          f"({comparison['pv_value_improvement_pct']:.2f}%)")

    print("\n3. AVERAGE OBTAINED PV PRICE")
    print("-" * 80)
    print(f"   Without battery: {pv_metrics_ref['pv_average_price_nok_kwh']:.3f} NOK/kWh")
    print(f"   With battery:    {pv_metrics_heur['pv_average_price_nok_kwh']:.3f} NOK/kWh")
    print(f"   → Battery increases average PV price by "
          f"{comparison['avg_price_improvement_nok_kwh']:.3f} NOK/kWh")

    print("\n4. INTERPRETATION")
    print("-" * 80)
    print("   The 'average obtained price of PV' represents the weighted economic value")
    print("   of solar generation:")
    print()
    print(f"   • Self-consumed PV ({pv_metrics_ref['self_consumption_rate']*100:.1f}% of total) is valued at")
    print(f"     {pv_metrics_ref['avoided_import_avg_price_nok_kwh']:.3f} NOK/kWh (avoided import cost)")
    print(f"   • Exported PV ({pv_metrics_ref['export_rate']*100:.1f}% of total) is valued at")
    print(f"     {pv_metrics_ref['export_avg_price_nok_kwh']:.3f} NOK/kWh (export compensation)")
    print()
    print("   Battery storage increases self-consumption, shifting more PV energy from")
    print("   low-value export (0.04 NOK/kWh) to high-value self-consumption")
    print(f"   ({pv_metrics_ref['avoided_import_avg_price_nok_kwh']:.3f} NOK/kWh).")

    print("\n5. COMPARISON WITH SPOT PRICE")
    print("-" * 80)
    avg_spot = spot_prices.mean()
    print(f"   Average spot price:            {avg_spot:.3f} NOK/kWh")
    print(f"   Average PV price (no battery): {pv_metrics_ref['pv_average_price_nok_kwh']:.3f} NOK/kWh")
    print(f"   → PV value is {pv_metrics_ref['pv_average_price_nok_kwh']/avg_spot:.2f}x spot price")
    print()
    print("   This shows that self-consumed solar is much more valuable than spot price")
    print("   due to avoided grid tariffs and taxes.")

    print("\n" + "="*80)
    print(" Analysis Complete")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
