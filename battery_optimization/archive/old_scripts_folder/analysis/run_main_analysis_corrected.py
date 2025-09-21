#!/usr/bin/env python3
"""
Kjører hovedanalysen med KORREKTE parametere:
- 138.55 kWp PV (fra PVsol)
- 90 MWh årlig forbruk (spesifisert av bruker)
- Bruker faktiske ENTSO-E spotpriser hvis tilgjengelig
- Full time-for-time optimalisering
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Legg til src i path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import SystemConfig, LnettTariff, BatteryConfig, EconomicConfig
from src.optimization.optimizer import BatteryOptimizer
from src.data_fetchers.solar_production import SolarProductionModel

def run_corrected_analysis():
    """Kjør batterioptimalisering med korrekte parametere"""

    print("=" * 70)
    print("🔋 HOVEDANALYSE MED KORREKTE PARAMETERE")
    print("=" * 70)

    # Opprett konfigurasjon med KORREKTE verdier
    system_config = SystemConfig()

    # OVERSTYR med korrekte verdier
    system_config.pv_capacity_kwp = 138.55  # Fra PVsol
    system_config.inverter_capacity_kw = 100  # Fra PVsol
    system_config.grid_capacity_kw = 70  # 70% av inverter

    print("\n📊 Systemkonfigurasjon (KORRIGERT):")
    print(f"  • PV-kapasitet: {system_config.pv_capacity_kwp} kWp")
    print(f"  • Inverterkapasitet: {system_config.inverter_capacity_kw} kW")
    print(f"  • Nettgrense: {system_config.grid_capacity_kw} kW")
    print(f"  • Lokasjon: Stavanger ({system_config.location_lat}°N)")
    print(f"  • Takvinkel: 30° (korrekt)")
    print(f"  • Orientering: 171° (nesten sør)")

    tariff = LnettTariff()
    battery_config = BatteryConfig()
    economic_config = EconomicConfig()

    # Initialiser optimizer
    optimizer = BatteryOptimizer(
        system_config=system_config,
        tariff=tariff,
        battery_config=battery_config,
        economic_config=economic_config
    )

    # Generer PV-produksjon
    print("\n☀️ Genererer PV-produksjonsprofil...")
    solar_model = SolarProductionModel(
        pv_capacity_kwp=138.55,  # Fra PVsol
        inverter_capacity_kw=100,  # Fra PVsol
        latitude=58.97,
        longitude=5.73,
        tilt=30,  # KORREKT takvinkel (ikke 15 eller 25)
        azimuth=171  # Fra PVsol (nesten sør)
    )

    from datetime import datetime
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31, 23, 59)
    pv_production = solar_model.calculate_hourly_production(start_date, end_date, use_cache=True)
    timestamps = pv_production.index

    # Skaler til faktisk årsproduksjon fra PVsol
    actual_annual = 133_017  # kWh fra PVsol
    current_annual = pv_production.sum()
    scaling_factor = actual_annual / current_annual
    pv_production = pv_production * scaling_factor

    print(f"  • Årlig PV-produksjon (skalert til PVsol): {pv_production.sum()/1000:.1f} MWh")
    print(f"  • Maks produksjon: {pv_production.max():.1f} kW")
    print(f"  • Spesifikk ytelse: {pv_production.sum()/system_config.pv_capacity_kwp:.0f} kWh/kWp")

    # Generer lastprofil - 90 MWh/år
    print("\n🏢 Genererer lastprofil (90 MWh/år)...")
    annual_load = 90_000  # kWh
    base_load = annual_load / 8760

    load_profile = []
    for ts in timestamps:
        hour = ts.hour
        weekday = ts.weekday()

        # Kommersielt lastmønster
        if weekday < 5 and 6 <= hour <= 18:
            load = base_load * 1.8
        elif 6 <= hour <= 22:
            load = base_load * 0.8
        else:
            load = base_load * 0.3

        # Legg til litt variasjon
        load = load * (1 + np.random.normal(0, 0.1))
        load_profile.append(max(1, load))

    load_profile = pd.Series(load_profile, index=timestamps)
    load_profile = load_profile * (annual_load / load_profile.sum())

    print(f"  • Årlig forbruk: {load_profile.sum()/1000:.1f} MWh")
    print(f"  • Maks forbruk: {load_profile.max():.1f} kW")
    print(f"  • Gjennomsnitt: {load_profile.mean():.1f} kW")

    # Hent spotpriser (faktiske eller simulerte)
    print("\n💰 Henter spotpriser...")
    try:
        from src.data_fetchers.price_fetcher import PriceFetcher
        price_fetcher = PriceFetcher()
        spot_prices = price_fetcher.get_prices(timestamps[0], timestamps[-1], price_area='NO2')
        spot_prices = pd.Series(spot_prices, index=timestamps)
        print(f"  • Bruker FAKTISKE spotpriser fra ENTSO-E")
    except:
        print(f"  • Bruker SIMULERTE spotpriser (ENTSO-E ikke tilgjengelig)")
        spot_prices = optimizer._generate_sample_spot_prices(len(pv_production))
        spot_prices.index = timestamps

    avg_price = spot_prices.mean()

    # Beregn sesongpriser
    summer_months = [4, 5, 6, 7, 8, 9]
    summer_mask = spot_prices.index.month.isin(summer_months)
    summer_price = spot_prices[summer_mask].mean()
    winter_price = spot_prices[~summer_mask].mean()

    print(f"  • Gjennomsnittspris (hele året): {avg_price:.3f} NOK/kWh")
    print(f"  • Gjennomsnittspris sommerhalvår: {summer_price:.3f} NOK/kWh")
    print(f"  • Gjennomsnittspris vinterhalvår: {winter_price:.3f} NOK/kWh")

    # Beregn oppnådd solkraftpris
    solar_revenue = (pv_production * spot_prices).sum()
    solar_weighted_price = solar_revenue / pv_production.sum()

    # Sesongvis oppnådd pris
    summer_solar_revenue = (pv_production[summer_mask] * spot_prices[summer_mask]).sum()
    summer_solar_production = pv_production[summer_mask].sum()
    summer_solar_price = summer_solar_revenue / summer_solar_production if summer_solar_production > 0 else 0

    winter_solar_revenue = (pv_production[~summer_mask] * spot_prices[~summer_mask]).sum()
    winter_solar_production = pv_production[~summer_mask].sum()
    winter_solar_price = winter_solar_revenue / winter_solar_production if winter_solar_production > 0 else 0

    print(f"\n☀️ Oppnådd solkraftpris (volumvektet):")
    print(f"  • Hele året: {solar_weighted_price:.3f} NOK/kWh ({solar_weighted_price/avg_price:.1%} av snitt)")
    print(f"  • Sommerhalvår: {summer_solar_price:.3f} NOK/kWh")
    print(f"  • Vinterhalvår: {winter_solar_price:.3f} NOK/kWh")
    print(f"  • Produksjonsandel sommer: {summer_solar_production/pv_production.sum():.1%}")

    # Energibalanse
    print("\n⚡ Energibalanse:")
    net_load = load_profile - pv_production
    print(f"  • Totalt forbruk: {load_profile.sum()/1000:.1f} MWh/år")
    print(f"  • Total PV-produksjon: {pv_production.sum()/1000:.1f} MWh/år")
    print(f"  • Direkte selvforbruk: {min(load_profile.sum(), pv_production.sum())/1000:.1f} MWh")
    print(f"  • Netto importbehov: {max(0, net_load.sum())/1000:.1f} MWh/år")
    print(f"  • Overskudd PV (eksport): {max(0, -net_load.sum())/1000:.1f} MWh/år")

    # Kjør optimalisering
    print("\n🔄 Kjører batterioptimalisering...")
    optimization_result = optimizer.optimize_battery_size(
        pv_production=pv_production,
        spot_prices=spot_prices,
        load_profile=load_profile,
        target_battery_cost=3000,
        strategy='combined'
    )

    # Vis resultater
    print("\n" + "=" * 70)
    print("✅ OPTIMALE RESULTATER MED KORREKTE DATA")
    print("=" * 70)

    print(f"\n🔋 Optimal batterikonfigurasjon:")
    print(f"  • Kapasitet: {optimization_result.optimal_capacity_kwh:.1f} kWh")
    print(f"  • Effekt: {optimization_result.optimal_power_kw:.1f} kW")
    print(f"  • C-rate: {optimization_result.optimal_c_rate:.2f}C")

    print(f"\n💰 Økonomi @ 3000 NOK/kWh:")
    print(f"  • NPV: {optimization_result.npv_at_target_cost:,.0f} NOK")
    print(f"  • Årlige inntekter: {optimization_result.economic_results.annual_revenue:,.0f} NOK")
    print(f"  • Tilbakebetalingstid: {optimization_result.economic_results.payback_period:.1f} år")
    print(f"  • IRR: {optimization_result.economic_results.irr:.1%}")

    print(f"\n🎯 Break-even analyse:")
    print(f"  • Maks batterikost for positiv NPV: {optimization_result.max_battery_cost_per_kwh:,.0f} NOK/kWh")

    # Beregn detaljerte priser fra batteridriften
    if hasattr(optimization_result, 'operation_metrics'):
        metrics = optimization_result.operation_metrics

        # Estimer arbitrasjeverdi
        if 'annual_throughput' in metrics:
            throughput = metrics['annual_throughput']
            # Anta gjennomsnittlig arbitrasjepris basert på throughput og inntekt
            if throughput > 0:
                arbitrage_value = optimization_result.economic_results.annual_revenue / throughput
                print(f"\n📈 Prisanalyse fra batteridrift:")
                print(f"  • Estimert arbitrasjeverdi: {arbitrage_value:.3f} NOK/kWh")
                print(f"  • Årlig gjennomstrømning: {throughput/1000:.1f} MWh")

    print(f"\n📊 Driftsstatistikk:")
    for key, value in optimization_result.operation_metrics.items():
        if 'rate' in key or 'factor' in key:
            print(f"  • {key.replace('_', ' ').title()}: {value:.1%}")
        else:
            print(f"  • {key.replace('_', ' ').title()}: {value:,.0f}")

    # Test forskjellige batterikostnader
    print(f"\n💵 NPV ved ulike batterikostnader:")
    for cost in [2000, 2500, 3000, 3500, 4000, 4500, 5000]:
        from src.optimization.battery_model import BatteryModel, BatterySpec

        spec = BatterySpec(
            capacity_kwh=optimization_result.optimal_capacity_kwh,
            power_kw=optimization_result.optimal_power_kw,
            efficiency=battery_config.round_trip_efficiency,
            degradation_rate=battery_config.annual_degradation,
            min_soc=battery_config.min_soc,
            max_soc=battery_config.max_soc
        )

        battery = BatteryModel(spec)
        operation_results = battery.simulate_operation(
            pv_production,
            spot_prices,
            load_profile,
            system_config.grid_capacity_kw,
            'combined'
        )

        from src.optimization.economic_model import EconomicModel
        economic_model = EconomicModel(tariff, economic_config)

        economic_results = economic_model.calculate_npv(
            operation_results,
            spot_prices,
            load_profile,
            cost,
            optimization_result.optimal_capacity_kwh,
            optimization_result.optimal_power_kw
        )

        status = "✅" if economic_results.npv > 0 else "❌"
        print(f"  {cost} NOK/kWh: NPV = {economic_results.npv:>10,.0f} NOK {status}")

    return optimization_result

if __name__ == "__main__":
    result = run_corrected_analysis()

    print("\n" + "=" * 70)
    print("KONKLUSJON")
    print("=" * 70)
    print("\n📝 Denne analysen bruker:")
    print("  • FULL time-for-time optimalisering (8760 timer)")
    print("  • FAKTISKE spotpriser hvis ENTSO-E er tilgjengelig")
    print("  • KORREKTE systemparametere (138.55 kWp, 90 MWh forbruk)")
    print("  • Avansert batteristrategi (kombinert arbitrasje og selvforbruk)")
    print("\nDette er den mest nøyaktige analysen!")