#!/usr/bin/env python3
"""
Sammenligning av batterilønnsomhet: Times- vs 15-minutters oppløsning
Periode: 30. september - 31. oktober 2025
Batteri: 30 kWh / 15 kW

Spothandel:
- Referanse: Timesoppløsning (PT60M)
- Test: 15-minutters oppløsning (PT15M)

Avregning (begge simuleringer):
- Forbruk: Timesbasis
- Effekttariffer: Timesbasis (aggregert fra 15-min hvis relevant)
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path

from core.price_fetcher import fetch_prices
from config import config, get_power_tariff


def load_september_october_data(resolution='PT60M'):
    """
    Last data for perioden 30. september - 31. oktober 2025.

    Args:
        resolution: 'PT60M' (times) eller 'PT15M' (15-minutt)

    Returns:
        Tuple av (timestamps, spot_prices, pv_production, consumption)
    """
    # Definer periode
    start_date = '2025-09-30'
    end_date = '2025-10-31 23:59'

    # Opprett timestamps basert på oppløsning
    if resolution == 'PT60M':
        timestamps = pd.date_range(
            start=start_date,
            end=end_date,
            freq='h',
            tz='Europe/Oslo'
        )
    else:  # PT15M
        timestamps = pd.date_range(
            start=start_date,
            end=end_date,
            freq='15min',
            tz='Europe/Oslo'
        )

    print(f"\n📅 Periode: {start_date} til {end_date}")
    print(f"   Oppløsning: {resolution}")
    print(f"   Antall intervaller: {len(timestamps)}")

    # Hent spotpriser
    print(f"📊 Henter spotpriser ({resolution})...")
    try:
        # Hent full år og filtrer til periode
        full_prices = fetch_prices(2025, 'NO2', resolution=resolution)
        mask = (full_prices.index >= pd.Timestamp(start_date, tz='Europe/Oslo')) & \
               (full_prices.index <= pd.Timestamp(end_date, tz='Europe/Oslo'))
        spot_prices = full_prices[mask]

        # Tilpass til timestamps
        if len(spot_prices) != len(timestamps):
            print(f"   Justerer prisdata fra {len(spot_prices)} til {len(timestamps)} punkter")
            spot_prices = spot_prices[:len(timestamps)]
        spot_prices.index = timestamps[:len(spot_prices)]

        print(f"   ✅ Lastet {len(spot_prices)} spotpriser")
        print(f"   Gjennomsnitt: {spot_prices.mean():.3f} kr/kWh")
        print(f"   Min: {spot_prices.min():.3f} kr/kWh")
        print(f"   Max: {spot_prices.max():.3f} kr/kWh")
    except Exception as e:
        print(f"   ⚠️ Feil ved henting av priser: {e}")
        print(f"   Bruker simulerte priser...")
        # Generer enkle simulerte priser
        base = 0.85
        spot_prices = pd.Series(
            [base * (1 + 0.3 * np.sin(2 * np.pi * i / (len(timestamps)/7)))
             for i in range(len(timestamps))],
            index=timestamps
        )

    # Generer forenklet PV-produksjon (sol mellom 08:00-18:00)
    print(f"☀️ Genererer PV-produksjon...")
    pv_production = []
    for ts in timestamps:
        hour = ts.hour
        if 8 <= hour <= 18:
            # Enkel sinuskurve for solproduksjon
            hour_angle = (hour - 13) / 5  # Maks kl 13
            pv_kw = 100 * max(0, np.cos(hour_angle))
        else:
            pv_kw = 0
        pv_production.append(pv_kw)

    pv_production = pd.Series(pv_production, index=timestamps)
    print(f"   ✅ PV maks: {pv_production.max():.1f} kW")
    print(f"   Total produksjon: {pv_production.sum() * (1 if resolution == 'PT60M' else 0.25):.0f} kWh")

    # Generer forbruk (kommersiell profil)
    print(f"🏢 Genererer forbruksprofil...")
    consumption = []
    for ts in timestamps:
        hour = ts.hour
        is_weekday = ts.weekday() < 5

        if is_weekday:
            if 8 <= hour < 17:
                base_load = 40
            elif 6 <= hour < 8 or 17 <= hour < 20:
                base_load = 25
            else:
                base_load = 15
        else:
            base_load = 12

        # Legg til litt variasjon
        consumption.append(base_load * (0.9 + 0.2 * np.random.random()))

    consumption = pd.Series(consumption, index=timestamps)
    print(f"   ✅ Forbruk gjennomsnitt: {consumption.mean():.1f} kW")
    print(f"   Total forbruk: {consumption.sum() * (1 if resolution == 'PT60M' else 0.25):.0f} kWh")

    return timestamps, spot_prices, pv_production, consumption


def simulate_battery_with_resolution(
    timestamps, spot_prices, pv_production, consumption,
    battery_kwh, battery_kw, resolution
):
    """
    Simuler batteridrift med spesifisert oppløsning for spothandel.

    Effekttariffer beregnes alltid på timesbasis (aggregeres hvis nødvendig).
    """
    print(f"\n🔋 Simulerer batteri: {battery_kwh} kWh / {battery_kw} kW")
    print(f"   Spothandel oppløsning: {resolution}")
    print(f"   Effekttariff oppløsning: Timesbasis (alltid)")

    T = len(timestamps)
    timestep_hours = 0.25 if resolution == 'PT15M' else 1.0

    # Initialiser arrays
    soc = np.zeros(T)
    charge = np.zeros(T)
    discharge = np.zeros(T)
    grid_import = np.zeros(T)
    grid_export = np.zeros(T)

    soc[0] = battery_kwh * 0.5  # Start ved 50% SOC
    efficiency = 0.90
    eta = np.sqrt(efficiency)

    # Enkel grådighetsalgoritme basert på spotpriser
    for t in range(1, T):
        net_power = pv_production.iloc[t] - consumption.iloc[t]

        # Sjekk om pris er lav (tid for lading) eller høy (tid for utlading)
        window = min(12, T - t)  # Se 3 timer frem (12 intervaller @ 15-min)
        avg_price_ahead = spot_prices.iloc[t:t+window].mean()
        current_price = spot_prices.iloc[t]

        if net_power > 0:
            # Overskuddsproduksjon
            if current_price < avg_price_ahead * 0.95:  # Pris er lav, lad batteri
                charge_power = min(net_power, battery_kw,
                                 (battery_kwh - soc[t-1]) / (eta * timestep_hours))
                charge[t] = charge_power
                soc[t] = soc[t-1] + charge_power * eta * timestep_hours
                grid_export[t] = net_power - charge_power
            else:
                # Eksporter direkte
                soc[t] = soc[t-1]
                grid_export[t] = net_power
        else:
            # Nettoimport nødvendig
            deficit = -net_power

            if current_price > avg_price_ahead * 1.05 and soc[t-1] > 0:  # Høy pris, bruk batteri
                discharge_power = min(deficit, battery_kw, soc[t-1] / timestep_hours * eta)
                discharge[t] = discharge_power
                soc[t] = soc[t-1] - discharge_power / eta * timestep_hours
                grid_import[t] = max(0, deficit - discharge_power)
            else:
                # Importer fra nett
                soc[t] = soc[t-1]
                grid_import[t] = deficit

    # Beregn økonomi
    print(f"\n💰 Beregner økonomi...")

    # Spothandelsinntekter (på aktuell oppløsning)
    spot_revenue = (grid_export * spot_prices).sum() * timestep_hours
    spot_cost = (grid_import * spot_prices).sum() * timestep_hours
    net_spot = spot_revenue - spot_cost

    print(f"   Spotinntekt: {spot_revenue:,.2f} kr")
    print(f"   Spotkostnad: {spot_cost:,.2f} kr")
    print(f"   Netto spot: {net_spot:,.2f} kr")

    # Effekttariff (alltid på timesbasis)
    if resolution == 'PT15M':
        # Aggreger grid_import til timestopper
        from core.time_aggregation import aggregate_15min_to_hourly_peak
        grid_import_hourly = aggregate_15min_to_hourly_peak(grid_import, timestamps)
    else:
        grid_import_hourly = grid_import

    # Beregn månedlige toppbelastninger
    if resolution == 'PT15M':
        # Lag timesindeks for aggregering
        hourly_timestamps = timestamps[::4]
        df_hourly = pd.DataFrame({
            'grid_import': grid_import_hourly,
            'month': [ts.month for ts in hourly_timestamps]
        })
    else:
        df_hourly = pd.DataFrame({
            'grid_import': grid_import,
            'month': [ts.month for ts in timestamps]
        })

    monthly_peaks = df_hourly.groupby('month')['grid_import'].max()

    # Beregn effektkostnader
    power_cost_total = 0
    for month, peak in monthly_peaks.items():
        monthly_cost = get_power_tariff(peak)
        power_cost_total += monthly_cost
        print(f"   Måned {month}: topp {peak:.1f} kW → {monthly_cost:.2f} kr")

    print(f"   Total effektkostnad: {power_cost_total:,.2f} kr (2 måneder)")

    # Total nettoinntekt for perioden
    total_net = net_spot - power_cost_total

    results = {
        'resolution': resolution,
        'period_days': (timestamps[-1] - timestamps[0]).days + 1,
        'data_points': T,
        'timestep_hours': timestep_hours,
        'spot_revenue': float(spot_revenue),
        'spot_cost': float(spot_cost),
        'net_spot': float(net_spot),
        'power_cost': float(power_cost_total),
        'total_net_income': float(total_net),
        'battery_cycles': float((charge.sum() * timestep_hours) / battery_kwh),
        'avg_soc': float(soc.mean() / battery_kwh * 100),
        'monthly_peaks': {int(k): float(v) for k, v in monthly_peaks.items()}
    }

    return results


def main():
    """Kjør sammenligning for spesifisert batteri og periode."""
    print("\n" + "="*80)
    print("SAMMENLIGNING: TIMES- VS 15-MINUTTERS OPPLØSNING FOR SPOTHANDEL")
    print("="*80)
    print("\nBatteri: 30 kWh / 15 kW")
    print("Periode: 30. september - 31. oktober 2025")
    print("\nSimulering:")
    print("  - Spothandel: Times (PT60M) vs 15-minutt (PT15M)")
    print("  - Effekttariffer: Timesbasis (begge)")
    print("  - Forbruksavregning: Timesbasis (begge)")
    print("="*80)

    battery_kwh = 30
    battery_kw = 15

    # Kjør simulering med timesoppløsning (referanse)
    print("\n" + "="*80)
    print("REFERANSE: Timesoppløsning (PT60M)")
    print("="*80)
    timestamps_h, prices_h, pv_h, cons_h = load_september_october_data('PT60M')
    results_hourly = simulate_battery_with_resolution(
        timestamps_h, prices_h, pv_h, cons_h,
        battery_kwh, battery_kw, 'PT60M'
    )

    # Kjør simulering med 15-minutters oppløsning
    print("\n" + "="*80)
    print("TEST: 15-minutters oppløsning (PT15M)")
    print("="*80)
    timestamps_15, prices_15, pv_15, cons_15 = load_september_october_data('PT15M')
    results_15min = simulate_battery_with_resolution(
        timestamps_15, prices_15, pv_15, cons_15,
        battery_kwh, battery_kw, 'PT15M'
    )

    # Sammenlign resultater
    print("\n" + "="*80)
    print("SAMMENLIGNING AV RESULTATER")
    print("="*80)

    print(f"\n📊 Datagrunnlag:")
    print(f"  Times (PT60M):    {results_hourly['data_points']:>6} intervaller")
    print(f"  15-minutt (PT15M): {results_15min['data_points']:>6} intervaller")
    print(f"  Forhold:          {results_15min['data_points'] / results_hourly['data_points']:>6.1f}x")

    print(f"\n💰 Spothandel (nettoinntekt):")
    print(f"  Times:     {results_hourly['net_spot']:>10,.2f} kr")
    print(f"  15-minutt: {results_15min['net_spot']:>10,.2f} kr")
    diff_spot = results_15min['net_spot'] - results_hourly['net_spot']
    pct_spot = (diff_spot / abs(results_hourly['net_spot']) * 100) if results_hourly['net_spot'] != 0 else 0
    print(f"  Forskjell: {diff_spot:>+10,.2f} kr ({pct_spot:+.1f}%)")

    print(f"\n⚡ Effektkostnader:")
    print(f"  Times:     {results_hourly['power_cost']:>10,.2f} kr")
    print(f"  15-minutt: {results_15min['power_cost']:>10,.2f} kr")
    diff_power = results_15min['power_cost'] - results_hourly['power_cost']
    pct_power = (diff_power / results_hourly['power_cost'] * 100) if results_hourly['power_cost'] != 0 else 0
    print(f"  Forskjell: {diff_power:>+10,.2f} kr ({pct_power:+.1f}%)")

    print(f"\n📈 Total nettoinntekt (spot - effekt):")
    print(f"  Times:     {results_hourly['total_net_income']:>10,.2f} kr")
    print(f"  15-minutt: {results_15min['total_net_income']:>10,.2f} kr")
    diff_total = results_15min['total_net_income'] - results_hourly['total_net_income']
    pct_total = (diff_total / abs(results_hourly['total_net_income']) * 100) if results_hourly['total_net_income'] != 0 else 0
    print(f"  Forskjell: {diff_total:>+10,.2f} kr ({pct_total:+.1f}%)")

    print(f"\n🔋 Batteridrift:")
    print(f"  Sykluser (times):     {results_hourly['battery_cycles']:.2f}")
    print(f"  Sykluser (15-minutt): {results_15min['battery_cycles']:.2f}")
    print(f"  Gj.snitt SOC (times):     {results_hourly['avg_soc']:.1f}%")
    print(f"  Gj.snitt SOC (15-minutt): {results_15min['avg_soc']:.1f}%")

    # Årsestimat
    days_in_period = results_hourly['period_days']
    annual_factor = 365 / days_in_period

    print(f"\n📅 Årsestimat (ekstrapolert fra {days_in_period} dager):")
    annual_hourly = results_hourly['total_net_income'] * annual_factor
    annual_15min = results_15min['total_net_income'] * annual_factor
    annual_diff = annual_15min - annual_hourly
    annual_pct = (annual_diff / abs(annual_hourly) * 100) if annual_hourly != 0 else 0

    print(f"  Times:     {annual_hourly:>10,.2f} kr/år")
    print(f"  15-minutt: {annual_15min:>10,.2f} kr/år")
    print(f"  Forskjell: {annual_diff:>+10,.2f} kr/år ({annual_pct:+.1f}%)")

    print("\n" + "="*80)
    print("KONKLUSJON")
    print("="*80)

    if abs(pct_total) < 2:
        print("\n⚠️  Liten forskjell (<2%) mellom oppløsningene for denne perioden")
        print("    Timesoppløsning er tilstrekkelig for strategisk planlegging")
    elif pct_total > 5:
        print("\n✅ 15-minutters oppløsning gir betydelig fordel (>5%)")
        print("    Anbefales for operasjonell planlegging og maksimering av inntekt")
    elif pct_total > 0:
        print("\n✓  15-minutters oppløsning gir moderat fordel (2-5%)")
        print("    Kan være verdt det avhengig av driftskostnader")
    else:
        print("\n⚠️  15-minutters oppløsning viser ingen fordel for denne perioden")
        print("    Dette kan skyldes lave prisvariasjoner eller begrenset handel")

    # Lagre resultater
    output_dir = Path('results')
    output_dir.mkdir(exist_ok=True)

    comparison = {
        'battery': {'kwh': battery_kwh, 'kw': battery_kw},
        'period': {
            'start': '2025-09-30',
            'end': '2025-10-31',
            'days': days_in_period
        },
        'hourly': results_hourly,
        '15min': results_15min,
        'comparison': {
            'spot_diff_kr': float(diff_spot),
            'spot_diff_pct': float(pct_spot),
            'power_diff_kr': float(diff_power),
            'power_diff_pct': float(pct_power),
            'total_diff_kr': float(diff_total),
            'total_diff_pct': float(pct_total),
            'annual_estimate': {
                'hourly_kr': float(annual_hourly),
                '15min_kr': float(annual_15min),
                'diff_kr': float(annual_diff),
                'diff_pct': float(annual_pct)
            }
        },
        'timestamp': datetime.now().isoformat()
    }

    output_file = output_dir / 'comparison_sept_oct_2025.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resultater lagret: {output_file}")
    print("="*80)


if __name__ == "__main__":
    main()
