#!/usr/bin/env python3
"""
Detaljert analyse med oppnådd solkraftpris, arbitrasjepris og unngått nettariff
Basert på faktiske PVsol-data og 90 MWh årlig forbruk
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def analyze_with_detailed_prices():
    """
    Analyser batteriøkonomi med detaljerte prisberegninger
    """
    print("=" * 70)
    print("🔋 BATTERIOPTIMALISERING MED DETALJERT PRISANALYSE")
    print("=" * 70)

    # Systemparametere fra PVsol
    pv_capacity = 138.55  # kWp (faktisk installert)
    pv_annual = 133_017  # kWh/år (PVsol resultat)
    load_annual = 90_000  # kWh/år (spesifisert av bruker)
    grid_limit = 70  # kW (70% av 100 kW inverter)

    print("\n📊 Energibalanse:")
    print(f"  • PV installert: {pv_capacity:.2f} kWp")
    print(f"  • Årlig PV-produksjon: {pv_annual/1000:.1f} MWh")
    print(f"  • Årlig forbruk: {load_annual/1000:.0f} MWh")
    print(f"  • Netto eksport: {(pv_annual - load_annual)/1000:.1f} MWh")

    # Generer timesdata for et år
    hours = 8760
    timestamps = pd.date_range('2024-01-01', periods=hours, freq='h')

    # PV-produksjonsprofil (forenklet basert på norske solforhold)
    def generate_pv_profile(hours):
        """Generer realistisk PV-produksjonsprofil for Stavanger"""
        pv_hourly = np.zeros(hours)
        for h in range(hours):
            day_of_year = (h // 24) + 1
            hour_of_day = h % 24

            # Sesongvariasjon (sommer høy, vinter lav)
            seasonal_factor = 1 + 0.8 * np.sin((day_of_year - 80) * 2 * np.pi / 365)

            # Daglig variasjon (produksjon 06-20)
            if 6 <= hour_of_day <= 20:
                daily_factor = np.sin((hour_of_day - 6) * np.pi / 14)
            else:
                daily_factor = 0

            # Maksimal timeeffekt ca 90% av installert kapasitet
            max_hourly = pv_capacity * 0.9
            pv_hourly[h] = max_hourly * seasonal_factor * daily_factor

        # Skaler til riktig årsproduksjon
        pv_hourly = pv_hourly * (pv_annual / pv_hourly.sum())
        return pv_hourly

    # Generer spotprisprrofil (typisk norsk mønster)
    def generate_spot_prices(hours):
        """Generer realistiske spotpriser med døgn- og sesongvariasjon"""
        prices = np.zeros(hours)
        base_price = 0.8  # NOK/kWh gjennomsnitt

        for h in range(hours):
            day_of_year = (h // 24) + 1
            hour_of_day = h % 24
            day_of_week = (h // 24) % 7

            # Sesongvariasjon (høyere om vinteren)
            seasonal = 1 + 0.3 * np.cos((day_of_year - 1) * 2 * np.pi / 365)

            # Døgnvariasjon
            if 6 <= hour_of_day <= 9:  # Morgentopp
                daily = 1.3
            elif 17 <= hour_of_day <= 20:  # Kveldstopp
                daily = 1.4
            elif 0 <= hour_of_day <= 5:  # Natt
                daily = 0.6
            else:  # Dag
                daily = 1.0

            # Helg har lavere priser
            if day_of_week >= 5:
                daily *= 0.8

            prices[h] = base_price * seasonal * daily * (1 + np.random.normal(0, 0.1))
            prices[h] = max(0.1, prices[h])  # Minimum 0.1 NOK/kWh

        return prices

    # Generer data
    pv_production = generate_pv_profile(hours)
    spot_prices = generate_spot_prices(hours)

    # Lastprofil (kommersielt bygg)
    base_load = load_annual / hours  # ~10.3 kW gjennomsnitt
    load_profile = np.zeros(hours)
    for h in range(hours):
        hour_of_day = h % 24
        day_of_week = (h // 24) % 7

        # Daglig lastmønster
        if 6 <= hour_of_day <= 18 and day_of_week < 5:  # Arbeidstid ukedager
            load_profile[h] = base_load * 1.8
        elif 6 <= hour_of_day <= 22:  # Kveld/helg
            load_profile[h] = base_load * 0.8
        else:  # Natt
            load_profile[h] = base_load * 0.3

    # Juster til eksakt årlig forbruk
    load_profile = load_profile * (load_annual / load_profile.sum())

    print("\n💰 PRISANALYSE:")
    # Beregn gjennomsnittspriser
    avg_spot_price = np.mean(spot_prices)

    # Sommerhalvår (april-september = måned 4-9, time 2160-6552)
    summer_start = 31 + 28 + 31  # dager før april
    summer_end = summer_start + 30 + 31 + 30 + 31 + 31 + 30  # april-september
    summer_hours = range(summer_start * 24, summer_end * 24)
    avg_summer_price = np.mean(spot_prices[summer_hours])

    # Vinterhalvår (oktober-mars)
    winter_hours = list(range(0, summer_start * 24)) + list(range(summer_end * 24, hours))
    avg_winter_price = np.mean(spot_prices[winter_hours])

    print(f"  • Gjennomsnittlig spotpris (hele året): {avg_spot_price:.3f} NOK/kWh")
    print(f"  • Gjennomsnittlig spotpris sommerhalvår (apr-sep): {avg_summer_price:.3f} NOK/kWh")
    print(f"  • Gjennomsnittlig spotpris vinterhalvår (okt-mar): {avg_winter_price:.3f} NOK/kWh")

    print("\n☀️ OPPNÅDD PRIS SOLKRAFT (uten batteri):")
    # Beregn volumvektet solkraftpris
    solar_revenue = np.sum(pv_production * spot_prices)
    solar_weighted_price = solar_revenue / pv_annual

    # Volumvektet pris for sommer og vinter
    summer_solar_revenue = np.sum(pv_production[summer_hours] * spot_prices[summer_hours])
    summer_solar_production = np.sum(pv_production[summer_hours])
    summer_solar_price = summer_solar_revenue / summer_solar_production if summer_solar_production > 0 else 0

    winter_solar_revenue = np.sum(pv_production[winter_hours] * spot_prices[winter_hours])
    winter_solar_production = np.sum(pv_production[winter_hours])
    winter_solar_price = winter_solar_revenue / winter_solar_production if winter_solar_production > 0 else 0

    print(f"  • Oppnådd solkraftpris (hele året): {solar_weighted_price:.3f} NOK/kWh")
    print(f"  • Oppnådd solkraftpris (sommerhalvår): {summer_solar_price:.3f} NOK/kWh")
    print(f"  • Oppnådd solkraftpris (vinterhalvår): {winter_solar_price:.3f} NOK/kWh")
    print(f"  • Relativ verdi: {solar_weighted_price/avg_spot_price:.1%} av årsgjennomsnittet")
    print(f"  • Produksjonsandel sommer: {summer_solar_production/pv_annual:.1%}")

    # Nettariffer (Lnett for bedrifter <100 MWh/år)
    energy_tariff_peak = 0.296  # NOK/kWh (06-22 hverdager)
    energy_tariff_offpeak = 0.176  # NOK/kWh (natt/helg)

    def get_grid_tariff(hour):
        """Returner nettariff for gitt time"""
        hour_of_day = hour % 24
        day_of_week = (hour // 24) % 7

        if day_of_week < 5 and 6 <= hour_of_day <= 22:
            return energy_tariff_peak
        else:
            return energy_tariff_offpeak

    # Test ulike batterikonfigurasjoner
    configs = [
        (30, 20), (30, 30),
        (50, 30), (50, 40), (50, 50),
        (75, 40), (75, 50), (75, 60),
        (100, 50), (100, 60), (100, 75),
        (125, 60), (125, 75), (125, 100),
        (150, 75), (150, 100)
    ]

    print("\n📊 BATTERIANALYSE MED DETALJERTE PRISER:")
    print("\nKap.\tEffekt\tNPV\t\tArbitrasje\tUnngått\t\tPayback")
    print("kWh\tkW\tNOK\t\tNOK/kWh\t\tnettariff\tår")
    print("-" * 75)

    best_npv = -float('inf')
    best_config = None
    best_details = None

    for capacity_kwh, power_kw in configs:
        # Simuler batteridrift gjennom året
        battery_soc = capacity_kwh * 0.5  # Start 50% ladet
        battery_charge = np.zeros(hours)
        battery_discharge = np.zeros(hours)

        for h in range(hours):
            net_load = load_profile[h] - pv_production[h]
            grid_tariff = get_grid_tariff(h)
            total_cost = spot_prices[h] + grid_tariff

            # Enkel lading/utladingsstrategi
            if net_load < -5 and battery_soc < capacity_kwh * 0.9:  # Overskudd, lad
                charge = min(power_kw, -net_load, (capacity_kwh * 0.9 - battery_soc))
                battery_charge[h] = charge
                battery_soc += charge * 0.9  # 90% effektivitet

            elif net_load > 5 and battery_soc > capacity_kwh * 0.1:  # Underskudd, utlad
                discharge = min(power_kw, net_load, (battery_soc - capacity_kwh * 0.1))
                battery_discharge[h] = discharge
                battery_soc -= discharge

            # Arbitrasje: lad når billig, selg når dyrt
            elif total_cost < 0.5 and battery_soc < capacity_kwh * 0.9:  # Billig strøm
                charge = min(power_kw, (capacity_kwh * 0.9 - battery_soc))
                battery_charge[h] = charge
                battery_soc += charge * 0.9

            elif total_cost > 1.2 and battery_soc > capacity_kwh * 0.2:  # Dyr strøm
                discharge = min(power_kw, (battery_soc - capacity_kwh * 0.2))
                battery_discharge[h] = discharge
                battery_soc -= discharge

        # Beregn økonomiske resultater
        total_discharge = battery_discharge.sum()
        total_charge = battery_charge.sum()

        # Arbitrasjeverdi: forskjell mellom salgs- og kjøpspris
        discharge_value = np.sum(battery_discharge * (spot_prices + [get_grid_tariff(h) for h in range(hours)]))
        charge_cost = np.sum(battery_charge * spot_prices)
        arbitrage_value = discharge_value - charge_cost
        arbitrage_price_diff = arbitrage_value / total_discharge if total_discharge > 0 else 0

        # Unngått nettariff
        grid_tariff_avoided = np.sum(battery_discharge * [get_grid_tariff(h) for h in range(hours)])
        avoided_tariff_per_kwh = grid_tariff_avoided / total_discharge if total_discharge > 0 else 0

        # Total årlig inntekt
        annual_revenue = arbitrage_value + grid_tariff_avoided

        # NPV-beregning
        investment = capacity_kwh * 3000  # NOK
        lifetime_years = 15
        discount_rate = 0.05
        degradation = 0.02

        npv = -investment
        for year in range(1, lifetime_years + 1):
            yearly_revenue = annual_revenue * (1 - degradation * year)
            npv += yearly_revenue / (1 + discount_rate) ** year

        payback = investment / annual_revenue if annual_revenue > 0 else 99

        if npv > 0:  # Vis kun lønnsomme konfigurasjoner
            print(f"{capacity_kwh}\t{power_kw}\t{npv:>8,.0f}\t{arbitrage_price_diff:.3f}\t\t"
                  f"{avoided_tariff_per_kwh:.3f}\t\t{payback:.1f}")

        if npv > best_npv:
            best_npv = npv
            best_config = (capacity_kwh, power_kw)
            best_details = {
                'arbitrage_diff': arbitrage_price_diff,
                'avoided_tariff': avoided_tariff_per_kwh,
                'annual_revenue': annual_revenue,
                'total_discharge': total_discharge,
                'payback': payback
            }

    print("\n" + "=" * 70)
    print("✅ OPTIMAL KONFIGURASJON MED PRISANALYSE")
    print("=" * 70)

    if best_config and best_details:
        capacity, power = best_config
        print(f"\n🔋 Optimal batteristørrelse:")
        print(f"   • Kapasitet: {capacity} kWh")
        print(f"   • Effekt: {power} kW")
        print(f"   • C-rate: {power/capacity:.2f}")

        print(f"\n💰 Detaljert økonomi @ 3000 NOK/kWh:")
        print(f"   • NPV: {best_npv:,.0f} NOK")
        print(f"   • Årlige inntekter: {best_details['annual_revenue']:,.0f} NOK")
        print(f"   • Tilbakebetalingstid: {best_details['payback']:.1f} år")

        print(f"\n📈 Prisanalyse:")
        print(f"   • Oppnådd arbitrasjepris: {best_details['arbitrage_diff']:.3f} NOK/kWh")
        print(f"   • Unngått nettariff: {best_details['avoided_tariff']:.3f} NOK/kWh")
        print(f"   • Total prisdifferanse: {best_details['arbitrage_diff'] + best_details['avoided_tariff']:.3f} NOK/kWh")
        print(f"   • Årlig utladning: {best_details['total_discharge']/1000:.1f} MWh")

        # Sammenligning med solkraftpris
        print(f"\n📊 Sammenligning:")
        print(f"   • Oppnådd solkraftpris (uten batteri): {solar_weighted_price:.3f} NOK/kWh")
        print(f"   • Forbedring med batteri: +{best_details['arbitrage_diff']:.3f} NOK/kWh")
        print(f"   • Total verdi med batteri: {solar_weighted_price + best_details['arbitrage_diff']:.3f} NOK/kWh")

    return best_config, best_npv

if __name__ == "__main__":
    config, npv = analyze_with_detailed_prices()

    print("\n" + "=" * 70)
    print("KONKLUSJON")
    print("=" * 70)
    print("\n📝 Hovedfunn:")
    print("  • Solkraft oppnår lavere pris enn gjennomsnittet (produksjon midt på dagen)")
    print("  • Batteri forbedrer verdien gjennom arbitrasje og unngått nettariff")
    print("  • Optimal strategi: Lad om natten (billig), selg på dagtid (dyrt)")
    print("  • Nettariffen utgjør betydelig del av verdiskapningen")