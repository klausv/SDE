"""
Test batterisimulering med ekte data

Sammenligner 2 strategier:
1. NoControlStrategy (referanse uten batteri)
2. SimpleRuleStrategy (HEMS-lignende)
"""
import pandas as pd
import numpy as np
from core.battery import Battery
from core.strategies import NoControlStrategy, SimpleRuleStrategy
from core.simulator import BatterySimulator
from core.pvgis_solar import PVGISProduction
from core.price_fetcher import ENTSOEPriceFetcher
from core.consumption_profiles import ConsumptionProfile


def main():
    print("="*60)
    print("BATTERISIMULERING MED EKTE DATA")
    print("="*60)

    # Last ekte data
    print("\n1. Laster data...")

    # Solkraftproduksjon (PVGIS - typisk år, returnerer 2020-data)
    print("   - Solkraftproduksjon (PVGIS typisk år)...")
    pvgis = PVGISProduction(
        lat=58.97,
        lon=5.73,
        pv_capacity_kwp=138.55,
        tilt=30,
        azimuth=173,
        system_loss=14
    )
    production = pvgis.fetch_hourly_production(2024, refresh=False)  # Returnerer 2020-data
    year = production.index[0].year  # Hent år fra PVGIS (2020)
    print(f"     Lastet {len(production)} timer (år {year}), sum={production.sum():.0f} kWh")

    # Forbruk (syntetisk, samme år som PVGIS)
    print("   - Forbruk (syntetisk commercial office)...")
    consumption = ConsumptionProfile.generate_annual_profile(
        profile_type='commercial_office',
        annual_kwh=300000,
        year=year
    )
    print(f"     Lastet {len(consumption)} timer, sum={consumption.sum():.0f} kWh")

    # Spotpriser (ENTSO-E 2024, mappet til 2020)
    print("   - Spotpriser (ENTSO-E NO2 2024, mappet til {year})...")
    price_fetcher = ENTSOEPriceFetcher()
    spot_prices = price_fetcher.fetch_prices(2024, 'NO2', refresh=False)
    # Konverter priser til samme år som PVGIS
    spot_prices.index = spot_prices.index.map(lambda x: x.replace(year=year))
    print(f"     Lastet {len(spot_prices)} timer, gjennomsnitt={spot_prices.mean():.2f} NOK/kWh")

    # Sjekk at alle har samme lengde
    min_len = min(len(production), len(consumption), len(spot_prices))
    production = production[:min_len]
    consumption = consumption[:min_len]
    spot_prices = spot_prices[:min_len]
    print(f"\n   Aligned alle til {min_len} timer")

    # Strategi 1: Referanse (uten batteri)
    print("\n2. Simulerer referanse (uten batteri)...")
    strategy_ref = NoControlStrategy()
    sim_ref = BatterySimulator(strategy=strategy_ref, battery=None)
    results_ref = sim_ref.simulate_year(
        production, consumption, spot_prices,
        solar_inverter_capacity_kw=110,
        grid_export_limit_kw=77,
        battery_inverter_efficiency=0.98
    )
    print("   ✓ Ferdig")

    # Strategi 2: SimpleRule
    print("\n3. Simulerer SimpleRuleStrategy...")
    battery_size_kwh = 20
    battery_power_kw = 10
    battery = Battery(
        capacity_kwh=battery_size_kwh,
        power_kw=battery_power_kw,
        max_c_rate_charge=1.0,
        max_c_rate_discharge=1.0
    )
    strategy_simple = SimpleRuleStrategy(
        cheap_price_threshold=0.5,
        expensive_price_threshold=1.0
    )
    sim_simple = BatterySimulator(strategy=strategy_simple, battery=battery)
    results_simple = sim_simple.simulate_year(
        production, consumption, spot_prices,
        solar_inverter_capacity_kw=110,
        grid_export_limit_kw=77,
        battery_inverter_efficiency=0.98
    )
    print("   ✓ Ferdig")

    # Analyser resultater
    print("\n" + "="*60)
    print("RESULTATER")
    print("="*60)

    def analyze_results(df, name):
        print(f"\n{name}:")

        # Nettimport/eksport
        grid_import = df[df['grid_power_kw'] > 0]['grid_power_kw'].sum()
        grid_export = df[df['grid_power_kw'] < 0]['grid_power_kw'].sum()
        peak_import = df['grid_power_kw'].max()

        # Kostnad (forenklet, bare spotpris * nettimport)
        grid_cost = (df['grid_power_kw'] * df['spot_price']).sum()

        # Inverter losses
        if 'inverter_clipping_kw' in df.columns:
            total_clipping = df['inverter_clipping_kw'].sum()
        else:
            total_clipping = 0

        # Curtailment losses
        if 'curtailment_kw' in df.columns:
            total_curtailment = df['curtailment_kw'].sum()
        else:
            total_curtailment = 0

        # Batteri (hvis relevant) - use AC power for consistency
        battery_col = 'battery_power_ac_kw' if 'battery_power_ac_kw' in df.columns else 'battery_power_kw'
        if 'battery_soc_kwh' in df.columns and df['battery_soc_kwh'].max() > 0:
            battery_charge = df[df[battery_col] > 0][battery_col].sum()
            battery_discharge = df[df[battery_col] < 0][battery_col].abs().sum()
            battery_cycles = battery_discharge / battery_size_kwh if battery_size_kwh > 0 else 0
        else:
            battery_charge = 0
            battery_discharge = 0
            battery_cycles = 0

        print(f"  Nettimport:      {grid_import:8.0f} kWh")
        print(f"  Netteksport:     {-grid_export:8.0f} kWh")
        print(f"  Peak import:     {peak_import:8.1f} kW")
        print(f"  Nettkostnad:     {grid_cost:8.0f} NOK")

        if total_clipping > 0:
            print(f"  Inverter clipping: {total_clipping:8.0f} kWh")
        if total_curtailment > 0:
            print(f"  Curtailment:     {total_curtailment:8.0f} kWh")

        if battery_charge > 0:
            print(f"  Batterilading:   {battery_charge:8.0f} kWh")
            print(f"  Batteriutlading: {battery_discharge:8.0f} kWh")
            print(f"  Batterisykluser: {battery_cycles:8.1f}")

        return {
            'grid_import': grid_import,
            'grid_export': -grid_export,
            'peak_import': peak_import,
            'grid_cost': grid_cost,
            'battery_charge': battery_charge,
            'battery_discharge': battery_discharge,
            'battery_cycles': battery_cycles,
            'inverter_clipping': total_clipping,
            'curtailment': total_curtailment
        }

    metrics_ref = analyze_results(results_ref, "REFERANSE (uten batteri)")
    metrics_simple = analyze_results(results_simple, f"SIMPLE RULE (batteri {battery_size_kwh}kWh/{battery_power_kw}kW)")

    # Sammenligning
    print("\n" + "="*60)
    print("SAMMENLIGNING")
    print("="*60)

    cost_saving = metrics_ref['grid_cost'] - metrics_simple['grid_cost']
    cost_saving_pct = (cost_saving / metrics_ref['grid_cost']) * 100

    peak_reduction = metrics_ref['peak_import'] - metrics_simple['peak_import']
    peak_reduction_pct = (peak_reduction / metrics_ref['peak_import']) * 100

    print(f"\nBesparelse nettkostnad: {cost_saving:8.0f} NOK ({cost_saving_pct:+.1f}%)")
    print(f"Reduksjon peak import:  {peak_reduction:8.1f} kW ({peak_reduction_pct:+.1f}%)")
    print(f"Batterisykluser/år:     {metrics_simple['battery_cycles']:8.1f}")

    # Lagre resultater
    print("\n4. Lagrer resultater...")
    results_ref.to_csv('results/test_strategy_reference.csv', index=False)
    results_simple.to_csv('results/test_strategy_simple.csv', index=False)
    print("   ✓ Lagret i results/")

    print("\n" + "="*60)
    print("FERDIG!")
    print("="*60)


if __name__ == "__main__":
    main()
