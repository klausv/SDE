#!/usr/bin/env python3
"""
Sammenligning med RIKTIG LP-optimering: Times- vs 15-minutters oppløsning
Bruker MonthlyLPOptimizer for korrekt optimalisering!

Periode: 30. september - 31. oktober 2025
Batteri: 30 kWh / 15 kW
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path

from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.price_fetcher import fetch_prices
from core.time_aggregation import upsample_hourly_to_15min
from config import config


def prepare_month_data(month_start, month_end, resolution='PT60M'):
    """
    Forbered data for én måned med spesifisert oppløsning.
    """
    print(f"\n📅 Forbereder data: {month_start} til {month_end}")
    print(f"   Oppløsning: {resolution}")

    # Opprett timestamps
    if resolution == 'PT60M':
        timestamps = pd.date_range(
            start=month_start,
            end=month_end,
            freq='h',
            tz='Europe/Oslo'
        )
    else:  # PT15M
        timestamps = pd.date_range(
            start=month_start,
            end=month_end,
            freq='15min',
            tz='Europe/Oslo'
        )

    print(f"   Antall intervaller: {len(timestamps)}")

    # Hent spotpriser for hele 2025
    year = timestamps[0].year
    print(f"📊 Henter spotpriser for {year} med {resolution}...")
    full_prices = fetch_prices(year, 'NO2', resolution=resolution)

    # Filtrer til ønsket periode
    mask = (full_prices.index >= pd.Timestamp(month_start, tz='Europe/Oslo')) & \
           (full_prices.index <= pd.Timestamp(month_end, tz='Europe/Oslo'))
    spot_prices = full_prices[mask].copy()

    # Juster til nøyaktig lengde
    if len(spot_prices) > len(timestamps):
        spot_prices = spot_prices[:len(timestamps)]
    spot_prices.index = timestamps[:len(spot_prices)]

    print(f"   ✅ {len(spot_prices)} spotpriser")
    print(f"   Gjennomsnitt: {spot_prices.mean():.3f} kr/kWh")
    print(f"   Min-Maks: {spot_prices.min():.3f} - {spot_prices.max():.3f} kr/kWh")

    # Generer PV-produksjon (forenklet modell)
    print(f"☀️ Genererer PV-produksjon...")
    pv_production = []
    for ts in timestamps:
        hour = ts.hour
        day_of_year = ts.dayofyear

        # Sesongfaktor (lavere i oktober enn september)
        season_factor = 0.8 + 0.2 * np.cos((day_of_year - 172) * 2 * np.pi / 365)

        # Daglig solkurve (maks kl 13)
        if 7 <= hour <= 19:
            hour_angle = (hour - 13) / 6
            solar_elevation = max(0, np.cos(hour_angle))
            pv_kw = 110 * solar_elevation * season_factor  # 110 kW maks (inverter)
        else:
            pv_kw = 0

        pv_production.append(pv_kw)

    pv_production = pd.Series(pv_production, index=timestamps)
    timestep_hours = 0.25 if resolution == 'PT15M' else 1.0
    total_pv_kwh = pv_production.sum() * timestep_hours
    print(f"   ✅ Total PV: {total_pv_kwh:.0f} kWh")

    # Generer forbruk (kommersiell profil)
    print(f"🏢 Genererer forbruksprofil...")
    consumption = []
    for ts in timestamps:
        hour = ts.hour
        is_weekday = ts.weekday() < 5
        month = ts.month

        # Sesongfaktor (mer forbruk i oktober - oppvarming)
        season_factor = 1.1 if month == 10 else 1.0

        if is_weekday:
            if 8 <= hour < 17:
                base_load = 35 * season_factor
            elif 6 <= hour < 8 or 17 <= hour < 20:
                base_load = 25 * season_factor
            else:
                base_load = 15 * season_factor
        else:
            base_load = 12 * season_factor

        # Legg til variasjon
        consumption.append(base_load * (0.95 + 0.1 * np.random.random()))

    consumption = pd.Series(consumption, index=timestamps)
    total_cons_kwh = consumption.sum() * timestep_hours
    print(f"   ✅ Total forbruk: {total_cons_kwh:.0f} kWh")

    return timestamps, spot_prices, pv_production, consumption


def run_lp_optimization(timestamps, spot_prices, pv_production, consumption,
                       battery_kwh, battery_kw, resolution, month_idx):
    """
    Kjør LP-basert optimering med MonthlyLPOptimizer.
    """
    print(f"\n🔋 LP-Optimering: {battery_kwh} kWh / {battery_kw} kW")
    print(f"   Oppløsning: {resolution}")

    # Konfigurer batteri
    config.battery_capacity_kwh = battery_kwh
    config.battery_power_kw = battery_kw

    # Initialiser LP-optimerer med korrekt oppløsning
    optimizer = MonthlyLPOptimizer(config, resolution=resolution,
                                   battery_kwh=battery_kwh, battery_kw=battery_kw)

    # Kjør optimering
    result = optimizer.optimize_month(
        month_idx=month_idx,
        pv_production=pv_production.values,
        load_consumption=consumption.values,
        spot_prices=spot_prices.values,
        timestamps=timestamps,
        E_initial=battery_kwh * 0.5  # Start ved 50% SOC
    )

    if not result.success:
        print(f"   ❌ Optimering feilet: {result.message}")
        return None

    print(f"   ✅ Optimering fullført!")
    print(f"   Objektiv verdi: {result.objective_value:,.2f} kr")
    print(f"   Energikostnad: {result.energy_cost:,.2f} kr")
    print(f"   Effektkostnad: {result.power_cost:,.2f} kr")

    return result


def analyze_results(result_hourly, result_15min, timestamps_h, timestamps_15):
    """
    Analyser og sammenlign resultater fra begge oppløsningene.
    """
    print("\n" + "="*80)
    print("DETALJERT SAMMENLIGNING")
    print("="*80)

    # Datagrunnlag
    print(f"\n📊 Datagrunnlag:")
    print(f"  Times (PT60M):     {len(timestamps_h):>6} intervaller")
    print(f"  15-minutt (PT15M): {len(timestamps_15):>6} intervaller")
    print(f"  Forhold:           {len(timestamps_15) / len(timestamps_h):>6.1f}x")

    # Kostnadskomponenter
    print(f"\n💰 Kostnadskomponenter:")
    print(f"  Energikostnad (times):     {result_hourly.energy_cost:>10,.2f} kr")
    print(f"  Energikostnad (15-minutt): {result_15min.energy_cost:>10,.2f} kr")
    energy_diff = result_15min.energy_cost - result_hourly.energy_cost
    energy_pct = (energy_diff / result_hourly.energy_cost * 100) if result_hourly.energy_cost != 0 else 0
    print(f"  Forskjell:                 {energy_diff:>+10,.2f} kr ({energy_pct:+.1f}%)")

    print(f"\n⚡ Effektkostnader:")
    print(f"  Times:     {result_hourly.power_cost:>10,.2f} kr")
    print(f"  15-minutt: {result_15min.power_cost:>10,.2f} kr")
    power_diff = result_15min.power_cost - result_hourly.power_cost
    power_pct = (power_diff / result_hourly.power_cost * 100) if result_hourly.power_cost != 0 else 0
    print(f"  Forskjell: {power_diff:>+10,.2f} kr ({power_pct:+.1f}%)")

    print(f"\n📈 Total kostnadsreduksjon (objektiv verdi):")
    print(f"  Times:     {result_hourly.objective_value:>10,.2f} kr")
    print(f"  15-minutt: {result_15min.objective_value:>10,.2f} kr")
    total_diff = result_15min.objective_value - result_hourly.objective_value

    # VIKTIG: Objektiv verdi er kostnad som skal minimeres
    # Lavere verdi = bedre resultat
    # Men vi vil vise besparelsen, så vi inverterer forskjellen
    savings_diff = result_hourly.objective_value - result_15min.objective_value
    savings_pct = (savings_diff / result_hourly.objective_value * 100) if result_hourly.objective_value != 0 else 0

    print(f"  Forbedring:  {savings_diff:>+10,.2f} kr ({savings_pct:+.1f}%)")

    # Batteridrift
    timestep_h = 1.0
    timestep_15 = 0.25

    charge_kwh_h = result_hourly.P_charge.sum() * timestep_h
    charge_kwh_15 = result_15min.P_charge.sum() * timestep_15

    discharge_kwh_h = result_hourly.P_discharge.sum() * timestep_h
    discharge_kwh_15 = result_15min.P_discharge.sum() * timestep_15

    battery_kwh = config.battery_capacity_kwh
    cycles_h = charge_kwh_h / battery_kwh
    cycles_15 = charge_kwh_15 / battery_kwh

    print(f"\n🔋 Batteridrift:")
    print(f"  Lading (times):     {charge_kwh_h:>8,.1f} kWh ({cycles_h:.2f} sykluser)")
    print(f"  Lading (15-minutt): {charge_kwh_15:>8,.1f} kWh ({cycles_15:.2f} sykluser)")
    print(f"  Utlading (times):     {discharge_kwh_h:>8,.1f} kWh")
    print(f"  Utlading (15-minutt): {discharge_kwh_15:>8,.1f} kWh")
    print(f"  Peak topp (times):     {result_hourly.P_peak:.2f} kW")
    print(f"  Peak topp (15-minutt): {result_15min.P_peak:.2f} kW")

    # Returner sammenligning
    return {
        'energy_cost': {
            'hourly': float(result_hourly.energy_cost),
            '15min': float(result_15min.energy_cost),
            'diff_kr': float(energy_diff),
            'diff_pct': float(energy_pct)
        },
        'power_cost': {
            'hourly': float(result_hourly.power_cost),
            '15min': float(result_15min.power_cost),
            'diff_kr': float(power_diff),
            'diff_pct': float(power_pct)
        },
        'total_objective': {
            'hourly': float(result_hourly.objective_value),
            '15min': float(result_15min.objective_value),
            'savings_kr': float(savings_diff),
            'savings_pct': float(savings_pct)
        },
        'battery_operation': {
            'hourly': {
                'charge_kwh': float(charge_kwh_h),
                'discharge_kwh': float(discharge_kwh_h),
                'cycles': float(cycles_h),
                'peak_kw': float(result_hourly.P_peak)
            },
            '15min': {
                'charge_kwh': float(charge_kwh_15),
                'discharge_kwh': float(discharge_kwh_15),
                'cycles': float(cycles_15),
                'peak_kw': float(result_15min.P_peak)
            }
        }
    }


def main():
    """Kjør LP-basert sammenligning."""
    print("\n" + "="*80)
    print("LP-OPTIMERING: TIMES- VS 15-MINUTTERS OPPLØSNING")
    print("="*80)
    print("\nBruker MonthlyLPOptimizer - RIKTIG optimeringsalgoritme!")
    print("\nBatteri: 30 kWh / 15 kW")
    print("Periode: 30. september - 31. oktober 2025")
    print("\nOptimering:")
    print("  - Spothandel: LP-basert optimering med spesifisert oppløsning")
    print("  - Effekttariffer: Beregnes på timesbasis (aggregeres fra 15-min)")
    print("  - Forbruksavregning: Timesbasis")
    print("="*80)

    battery_kwh = 30
    battery_kw = 15  # Original konfigurasjon

    # September (siste dag)
    print("\n" + "="*80)
    print("SEPTEMBER 2025 (siste dag)")
    print("="*80)

    timestamps_sept_h, prices_sept_h, pv_sept_h, cons_sept_h = prepare_month_data(
        '2025-09-30', '2025-09-30 23:59', 'PT60M'
    )
    result_sept_h = run_lp_optimization(
        timestamps_sept_h, prices_sept_h, pv_sept_h, cons_sept_h,
        battery_kwh, battery_kw, 'PT60M', month_idx=9
    )

    timestamps_sept_15, prices_sept_15, pv_sept_15, cons_sept_15 = prepare_month_data(
        '2025-09-30', '2025-09-30 23:59', 'PT15M'
    )
    result_sept_15 = run_lp_optimization(
        timestamps_sept_15, prices_sept_15, pv_sept_15, cons_sept_15,
        battery_kwh, battery_kw, 'PT15M', month_idx=9
    )

    comparison_sept = analyze_results(result_sept_h, result_sept_15, timestamps_sept_h, timestamps_sept_15)

    # Oktober (full måned)
    print("\n" + "="*80)
    print("OKTOBER 2025 (full måned)")
    print("="*80)

    timestamps_oct_h, prices_oct_h, pv_oct_h, cons_oct_h = prepare_month_data(
        '2025-10-01', '2025-10-31 23:59', 'PT60M'
    )
    result_oct_h = run_lp_optimization(
        timestamps_oct_h, prices_oct_h, pv_oct_h, cons_oct_h,
        battery_kwh, battery_kw, 'PT60M', month_idx=10
    )

    timestamps_oct_15, prices_oct_15, pv_oct_15, cons_oct_15 = prepare_month_data(
        '2025-10-01', '2025-10-31 23:59', 'PT15M'
    )
    result_oct_15 = run_lp_optimization(
        timestamps_oct_15, prices_oct_15, pv_oct_15, cons_oct_15,
        battery_kwh, battery_kw, 'PT15M', month_idx=10
    )

    comparison_oct = analyze_results(result_oct_h, result_oct_15, timestamps_oct_h, timestamps_oct_15)

    # Total for periode
    print("\n" + "="*80)
    print("TOTAL PERIODE (30. sept - 31. okt 2025)")
    print("="*80)

    total_hourly = result_sept_h.objective_value + result_oct_h.objective_value
    total_15min = result_sept_15.objective_value + result_oct_15.objective_value
    total_savings = total_hourly - total_15min
    total_savings_pct = (total_savings / total_hourly * 100) if total_hourly != 0 else 0

    print(f"\n💰 Total kostnadsreduksjon:")
    print(f"  Times (PT60M):     {total_hourly:>10,.2f} kr")
    print(f"  15-minutt (PT15M): {total_15min:>10,.2f} kr")
    print(f"  Forbedring:        {total_savings:>+10,.2f} kr ({total_savings_pct:+.1f}%)")

    # Årsestimat
    days_in_period = 32  # 30 sept + 31 dager i okt
    annual_factor = 365 / days_in_period

    annual_hourly = total_hourly * annual_factor
    annual_15min = total_15min * annual_factor
    annual_savings = total_savings * annual_factor
    annual_savings_pct = total_savings_pct

    print(f"\n📅 Årsestimat (ekstrapolert fra {days_in_period} dager):")
    print(f"  Kostnad times:     {annual_hourly:>10,.2f} kr/år")
    print(f"  Kostnad 15-minutt: {annual_15min:>10,.2f} kr/år")
    print(f"  Besparelse:        {annual_savings:>+10,.2f} kr/år ({annual_savings_pct:+.1f}%)")

    print("\n" + "="*80)
    print("KONKLUSJON")
    print("="*80)

    if total_savings_pct > 5:
        print("\n✅ 15-minutters oppløsning gir betydelig besparelse (>5%)")
        print("    Anbefales sterkt for operasjonell planlegging og maksimering av inntekt")
    elif total_savings_pct > 2:
        print("\n✓  15-minutters oppløsning gir moderat besparelse (2-5%)")
        print("    Verdt å vurdere avhengig av implementeringskostnader")
    elif total_savings_pct > 0:
        print("\n⚠️  Liten besparelse (<2%) med 15-minutters oppløsning")
        print("    Timesoppløsning kan være tilstrekkelig for denne konfigurasjonen")
    else:
        print("\n❌ 15-minutters oppløsning viser ingen fordel")
        print("    Dette kan skyldes prisstrukturen i denne perioden")

    # Lagre resultater
    output_dir = Path('results')
    output_dir.mkdir(exist_ok=True)

    results = {
        'battery': {'kwh': battery_kwh, 'kw': battery_kw},
        'period': {
            'start': '2025-09-30',
            'end': '2025-10-31',
            'days': days_in_period
        },
        'september': comparison_sept,
        'october': comparison_oct,
        'total': {
            'hourly_kr': float(total_hourly),
            '15min_kr': float(total_15min),
            'savings_kr': float(total_savings),
            'savings_pct': float(total_savings_pct)
        },
        'annual_estimate': {
            'hourly_kr': float(annual_hourly),
            '15min_kr': float(annual_15min),
            'savings_kr': float(annual_savings),
            'savings_pct': float(annual_savings_pct)
        },
        'method': 'LP optimization (MonthlyLPOptimizer)',
        'timestamp': datetime.now().isoformat()
    }

    output_file = output_dir / 'lp_comparison_sept_oct_2025.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resultater lagret: {output_file}")
    print("="*80)


if __name__ == "__main__":
    main()
