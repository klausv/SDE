#!/usr/bin/env python3
"""
Komplett batterianalyse med KORREKTE parametere:
- 138.55 kWp PV (faktisk installert)
- 133 MWh/år produksjon (PVsol resultat)
- 90 MWh/år forbruk (spesifisert av bruker)
- 30° takvinkel (korrekt)
- Full time-for-time simulering
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Legg til src i path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import SystemConfig, LnettTariff, BatteryConfig, EconomicConfig
from src.optimization.battery_model import BatteryModel, BatterySpec
from src.optimization.economic_model import EconomicModel

def generate_load_profile_90mwh(n_hours=8760):
    """Generer lastprofil som summerer til NØYAKTIG 90 MWh/år"""
    # Kommersielt lastmønster
    hourly_pattern = np.array([
        0.3, 0.3, 0.3, 0.3, 0.3, 0.4,  # 00-06: Natt
        0.6, 0.8, 1.0, 1.0, 1.0, 0.9,  # 06-12: Morgen
        0.7, 0.8, 0.9, 1.0, 0.9, 0.7,  # 12-18: Ettermiddag
        0.5, 0.4, 0.3, 0.3, 0.3, 0.3   # 18-24: Kveld
    ])

    # Beregn base_load for å oppnå 90 MWh/år
    avg_pattern_factor = hourly_pattern.mean()
    target_annual_kwh = 90_000
    base_load = target_annual_kwh / (n_hours * avg_pattern_factor)

    loads = []
    for i in range(n_hours):
        hour = i % 24
        day = i // 24

        # Legg til sesongvariasjon (høyere forbruk om vinteren)
        seasonal_factor = 1.0 + 0.2 * np.cos((day - 15) * 2 * np.pi / 365)

        # Daglig variasjon
        daily_var = np.random.normal(0, 0.05)

        load = base_load * hourly_pattern[hour] * seasonal_factor * (1 + daily_var)
        loads.append(max(1, load))

    loads = np.array(loads)

    # Juster til NØYAKTIG 90 MWh
    actual_sum = loads.sum()
    adjustment_factor = target_annual_kwh / actual_sum
    loads = loads * adjustment_factor

    return pd.Series(loads)

def generate_pv_production_133mwh(n_hours=8760):
    """Generer PV-produksjon som summerer til NØYAKTIG 133 MWh/år"""
    pv_capacity = 138.55  # kWp
    target_annual_kwh = 133_017

    pv_hourly = []
    for h in range(n_hours):
        day_of_year = (h // 24) + 1
        hour_of_day = h % 24

        # Sesongvariasjon (sommer høy, vinter lav)
        seasonal_factor = 1 + 0.8 * np.sin((day_of_year - 80) * 2 * np.pi / 365)

        # Daglig produksjonsmønster
        if 5 <= hour_of_day <= 21:
            # Sola oppe (utvidet for sommer i Norge)
            sun_angle = np.sin((hour_of_day - 5) * np.pi / 16)
            if sun_angle > 0:
                production = pv_capacity * 0.85 * seasonal_factor * sun_angle
            else:
                production = 0
        else:
            production = 0

        # Legg til litt variasjon (skyer etc)
        if production > 0:
            production *= (1 + np.random.normal(0, 0.15))
            production = max(0, min(production, 100))  # Maks 100 kW (invertergrense)

        pv_hourly.append(production)

    pv_hourly = np.array(pv_hourly)

    # Juster til NØYAKTIG 133 MWh
    actual_sum = pv_hourly.sum()
    if actual_sum > 0:
        adjustment_factor = target_annual_kwh / actual_sum
        pv_hourly = pv_hourly * adjustment_factor

    return pd.Series(pv_hourly)

def generate_spot_prices(n_hours=8760):
    """Generer realistiske spotpriser for Norge"""
    prices = []
    base_price = 0.8  # NOK/kWh gjennomsnitt

    for h in range(n_hours):
        day_of_year = (h // 24) + 1
        hour_of_day = h % 24
        weekday = ((h // 24) % 7) < 5

        # Sesongvariasjon
        seasonal = 1 + 0.4 * np.cos((day_of_year - 1) * 2 * np.pi / 365)

        # Døgnvariasjon
        if weekday:
            if 6 <= hour_of_day <= 9:  # Morgentopp
                daily = 1.3
            elif 16 <= hour_of_day <= 20:  # Kveldstopp
                daily = 1.4
            elif 0 <= hour_of_day <= 5:  # Natt
                daily = 0.6
            else:  # Dag
                daily = 1.0
        else:  # Helg
            daily = 0.8

        price = base_price * seasonal * daily * (1 + np.random.normal(0, 0.1))
        prices.append(max(0.1, price))

    return pd.Series(prices)

def simulate_battery_operation(battery_kwh, battery_kw, pv_production, load_profile, spot_prices):
    """Simuler batteridrift gjennom året"""
    n_hours = len(pv_production)
    battery_soc = battery_kwh * 0.5  # Start 50% ladet
    efficiency = 0.9

    charge = np.zeros(n_hours)
    discharge = np.zeros(n_hours)
    soc_array = np.zeros(n_hours)

    # Nettariffer
    energy_tariff_peak = 0.296  # NOK/kWh (06-22 hverdager)
    energy_tariff_offpeak = 0.176  # NOK/kWh

    for h in range(n_hours):
        net_load = load_profile[h] - pv_production[h]
        hour_of_day = h % 24
        weekday = ((h // 24) % 7) < 5

        # Beregn nettariff
        if weekday and 6 <= hour_of_day <= 22:
            grid_tariff = energy_tariff_peak
        else:
            grid_tariff = energy_tariff_offpeak

        total_price = spot_prices[h] + grid_tariff

        # Batteristrategi
        if net_load < -5 and battery_soc < battery_kwh * 0.95:
            # Overskudd PV - lad batteri
            charge_power = min(battery_kw, -net_load, (battery_kwh * 0.95 - battery_soc))
            charge[h] = charge_power
            battery_soc += charge_power * efficiency

        elif net_load > 5 and battery_soc > battery_kwh * 0.1:
            # Underskudd - bruk batteri
            discharge_power = min(battery_kw, net_load, battery_soc - battery_kwh * 0.1)
            discharge[h] = discharge_power
            battery_soc -= discharge_power

        # Arbitrasje
        elif total_price < 0.5 and battery_soc < battery_kwh * 0.95:
            # Billig strøm - lad
            charge_power = min(battery_kw, battery_kwh * 0.95 - battery_soc)
            charge[h] = charge_power
            battery_soc += charge_power * efficiency

        elif total_price > 1.2 and battery_soc > battery_kwh * 0.2:
            # Dyr strøm - selg
            discharge_power = min(battery_kw, battery_soc - battery_kwh * 0.2)
            discharge[h] = discharge_power
            battery_soc -= discharge_power

        soc_array[h] = battery_soc

    return charge, discharge, soc_array

def run_analysis():
    """Kjør komplett analyse med 90 MWh forbruk"""
    print("=" * 70)
    print("🔋 KOMPLETT BATTERIANALYSE MED KORREKTE PARAMETERE")
    print("=" * 70)

    # Systemparametere
    print("\n📊 Systemkonfigurasjon:")
    print(f"  • PV-kapasitet: 138.55 kWp")
    print(f"  • Årlig PV-produksjon: 133 MWh (mål)")
    print(f"  • Årlig forbruk: 90 MWh (mål)")
    print(f"  • Takvinkel: 30°")
    print(f"  • Invertergrense: 100 kW")
    print(f"  • Nettgrense: 70 kW")

    # Generer tidsserier
    print("\n⏰ Genererer tidsserier (8760 timer)...")
    timestamps = pd.date_range('2024-01-01', periods=8760, freq='h')

    load_profile = generate_load_profile_90mwh()
    load_profile.index = timestamps

    pv_production = generate_pv_production_133mwh()
    pv_production.index = timestamps

    spot_prices = generate_spot_prices()
    spot_prices.index = timestamps

    # Verifiser summer
    print(f"\n✅ Verifisering:")
    print(f"  • Faktisk årlig forbruk: {load_profile.sum()/1000:.1f} MWh")
    print(f"  • Faktisk PV-produksjon: {pv_production.sum()/1000:.1f} MWh")
    print(f"  • Gjennomsnittlig spotpris: {spot_prices.mean():.3f} NOK/kWh")

    # Beregn sesongvariasjoner
    summer_months = [4, 5, 6, 7, 8, 9]
    summer_mask = timestamps.month.isin(summer_months)

    summer_spot = spot_prices[summer_mask].mean()
    winter_spot = spot_prices[~summer_mask].mean()

    print(f"\n💰 Prisanalyse:")
    print(f"  • Gjennomsnittspris hele året: {spot_prices.mean():.3f} NOK/kWh")
    print(f"  • Gjennomsnittspris sommerhalvår: {summer_spot:.3f} NOK/kWh")
    print(f"  • Gjennomsnittspris vinterhalvår: {winter_spot:.3f} NOK/kWh")

    # Beregn oppnådd solkraftpris
    solar_revenue = (pv_production * spot_prices).sum()
    solar_weighted_price = solar_revenue / pv_production.sum()

    summer_solar_revenue = (pv_production[summer_mask] * spot_prices[summer_mask]).sum()
    summer_solar_prod = pv_production[summer_mask].sum()
    summer_solar_price = summer_solar_revenue / summer_solar_prod if summer_solar_prod > 0 else 0

    winter_solar_revenue = (pv_production[~summer_mask] * spot_prices[~summer_mask]).sum()
    winter_solar_prod = pv_production[~summer_mask].sum()
    winter_solar_price = winter_solar_revenue / winter_solar_prod if winter_solar_prod > 0 else 0

    print(f"\n☀️ Oppnådd solkraftpris (uten batteri):")
    print(f"  • Hele året: {solar_weighted_price:.3f} NOK/kWh")
    print(f"  • Sommerhalvår: {summer_solar_price:.3f} NOK/kWh")
    print(f"  • Vinterhalvår: {winter_solar_price:.3f} NOK/kWh")
    print(f"  • Relativ verdi: {solar_weighted_price/spot_prices.mean():.1%} av gjennomsnitt")
    print(f"  • Produksjonsandel sommer: {summer_solar_prod/pv_production.sum():.1%}")

    # Test batterikonfigurasjoner
    configs = [
        (30, 20), (30, 30),
        (50, 30), (50, 40), (50, 50),
        (75, 40), (75, 50), (75, 60),
        (100, 50), (100, 60), (100, 75),
        (125, 60), (125, 75), (125, 100),
        (150, 75), (150, 100)
    ]

    print("\n📊 Batterianalyse:")
    print("\nKap.\tEffekt\tNPV\t\tArbitrasje\tUnngått\t\tPayback")
    print("kWh\tkW\tNOK\t\tNOK/kWh\t\tnettariff\tår")
    print("-" * 75)

    best_npv = -float('inf')
    best_config = None
    best_details = None

    tariff = LnettTariff()
    economic_config = EconomicConfig()

    for battery_kwh, battery_kw in configs:
        # Simuler batteridrift
        charge, discharge, soc = simulate_battery_operation(
            battery_kwh, battery_kw, pv_production, load_profile, spot_prices
        )

        total_discharge = discharge.sum()
        total_charge = charge.sum()

        # Beregn økonomi
        # Arbitrasjeverdi
        discharge_revenues = []
        charge_costs = []

        for h in range(8760):
            if discharge[h] > 0:
                hour_of_day = h % 24
                weekday = ((h // 24) % 7) < 5
                if weekday and 6 <= hour_of_day <= 22:
                    grid_tariff = 0.296
                else:
                    grid_tariff = 0.176

                discharge_revenues.append(discharge[h] * (spot_prices.iloc[h] + grid_tariff))

            if charge[h] > 0:
                charge_costs.append(charge[h] * spot_prices.iloc[h])

        total_discharge_revenue = sum(discharge_revenues)
        total_charge_cost = sum(charge_costs)
        arbitrage_value = total_discharge_revenue - total_charge_cost

        if total_discharge > 0:
            arbitrage_per_kwh = arbitrage_value / total_discharge
            avoided_tariff = sum(discharge_revenues) / total_discharge - sum(charge_costs) / total_charge
        else:
            arbitrage_per_kwh = 0
            avoided_tariff = 0

        # NPV-beregning
        annual_revenue = arbitrage_value
        investment = battery_kwh * 3000
        lifetime = 15
        discount_rate = 0.05
        degradation = 0.02

        npv = -investment
        for year in range(1, lifetime + 1):
            yearly_revenue = annual_revenue * (1 - degradation * year)
            npv += yearly_revenue / (1 + discount_rate) ** year

        payback = investment / annual_revenue if annual_revenue > 0 else 99

        if npv > 0:  # Vis kun lønnsomme
            print(f"{battery_kwh}\t{battery_kw}\t{npv:>8,.0f}\t"
                  f"{arbitrage_per_kwh:.3f}\t\t{avoided_tariff:.3f}\t\t{payback:.1f}")

        if npv > best_npv:
            best_npv = npv
            best_config = (battery_kwh, battery_kw)
            best_details = {
                'arbitrage_per_kwh': arbitrage_per_kwh,
                'avoided_tariff': avoided_tariff,
                'annual_revenue': annual_revenue,
                'total_discharge': total_discharge,
                'payback': payback
            }

    print("\n" + "=" * 70)
    print("✅ OPTIMAL KONFIGURASJON")
    print("=" * 70)

    if best_config and best_details:
        capacity, power = best_config
        print(f"\n🔋 Optimal batteri:")
        print(f"  • Kapasitet: {capacity} kWh")
        print(f"  • Effekt: {power} kW")
        print(f"  • C-rate: {power/capacity:.2f}")

        print(f"\n💰 Økonomi @ 3000 NOK/kWh:")
        print(f"  • NPV: {best_npv:,.0f} NOK")
        print(f"  • Årlige inntekter: {best_details['annual_revenue']:,.0f} NOK")
        print(f"  • Tilbakebetalingstid: {best_details['payback']:.1f} år")

        print(f"\n📈 Detaljert prisanalyse:")
        print(f"  • Oppnådd arbitrasjepris: {best_details['arbitrage_per_kwh']:.3f} NOK/kWh")
        print(f"  • Unngått nettariff komponent: {best_details['avoided_tariff']:.3f} NOK/kWh")
        print(f"  • Årlig utladning: {best_details['total_discharge']/1000:.1f} MWh")

        # Break-even analyse
        print(f"\n🎯 Break-even analyse for {capacity} kWh @ {power} kW:")
        for battery_cost in [2000, 2500, 3000, 3500, 4000, 4500, 5000]:
            investment = capacity * battery_cost
            npv_test = -investment
            for year in range(1, lifetime + 1):
                yearly_revenue = best_details['annual_revenue'] * (1 - degradation * year)
                npv_test += yearly_revenue / (1 + discount_rate) ** year

            status = "✅" if npv_test > 0 else "❌"
            print(f"  {battery_cost} NOK/kWh: NPV = {npv_test:>10,.0f} {status}")

    return best_config, best_npv

if __name__ == "__main__":
    config, npv = run_analysis()

    print("\n" + "=" * 70)
    print("KONKLUSJON")
    print("=" * 70)
    print("\n📝 Hovedfunn:")
    print("  • Med 90 MWh forbruk og 133 MWh produksjon")
    print("  • 43 MWh overskudd gir begrenset arbitrasjemulighet")
    print("  • Batteriet må primært tjene på tidsforskyvning")
    print("  • Nettariffen utgjør viktig del av inntekten")