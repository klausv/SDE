"""
Analyze solar curtailment across 2024 with 30 kWh battery.

Shows monthly curtailment patterns and total dumped energy.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import BatteryOptimizationConfig, DegradationConfig
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.price_fetcher import ENTSOEPriceFetcher
from core.pvgis_solar import PVGISProduction
import numpy as np
import pandas as pd


def load_real_2024_data():
    """Load real 2024 data"""
    print("Loading 2024 data...")

    # Prices
    fetcher = ENTSOEPriceFetcher(resolution='PT60M')
    prices = fetcher.fetch_prices(year=2024, area='NO2')

    # Solar
    pvgis = PVGISProduction(lat=58.97, lon=5.73, pv_capacity_kwp=138.55, tilt=30.0, azimuth=173.0)
    pv_series = pvgis.fetch_hourly_production(year=2024)

    # Load
    timestamps = prices.index
    load = np.zeros(len(timestamps))
    avg_load = 300000 / 8760
    base = avg_load * 0.6

    for i, ts in enumerate(timestamps):
        ts = pd.Timestamp(ts)
        if ts.weekday() < 5 and 6 <= ts.hour < 18:
            load[i] = base * 1.8
        elif 18 <= ts.hour < 22:
            load[i] = base * 1.3
        else:
            load[i] = base

    # Match PV to price timestamps
    pv = np.zeros(len(timestamps))
    for i, ts in enumerate(timestamps):
        ts = pd.Timestamp(ts)
        matching = pv_series.index[
            (pv_series.index.month == ts.month) &
            (pv_series.index.day == ts.day) &
            (pv_series.index.hour == ts.hour)
        ]
        if len(matching) > 0:
            pv[i] = pv_series.loc[matching[0]]

    # Create DataFrame
    data = pd.DataFrame({
        'spot_price': prices.values,
        'pv_production': pv,
        'load': load
    }, index=timestamps)

    return data


def analyze_curtailment_by_month(battery_kwh=30, battery_kw=15):
    """Run optimization and extract curtailment per month"""

    print("\n" + "="*70)
    print("CURTAILMENT ANALYSIS - 2024")
    print("="*70)
    print(f"Battery: {battery_kwh} kWh, {battery_kw} kW")
    print()

    # Config with degradation
    config = BatteryOptimizationConfig()
    config.battery.degradation = DegradationConfig(
        enabled=True,
        cycle_life_full_dod=5000,
        calendar_life_years=28.0
    )

    optimizer = MonthlyLPOptimizer(config, resolution='PT60M',
                                   battery_kwh=battery_kwh, battery_kw=battery_kw)

    # Load data
    data = load_real_2024_data()
    data['month'] = data.index.month

    E_initial = battery_kwh * 0.5

    curtailment_results = []

    for month in range(1, 13):
        month_data = data[data['month'] == month]

        result = optimizer.optimize_month(
            month_idx=month,
            pv_production=month_data['pv_production'].values,
            load_consumption=month_data['load'].values,
            spot_prices=month_data['spot_price'].values,
            timestamps=month_data.index.values,
            E_initial=E_initial
        )

        if not result.success:
            print(f"Month {month:2d}: ❌ FAILED")
            continue

        # Extract curtailment from optimizer solution
        # P_curtail is now stored directly in MonthlyLPResult
        curtailment = result.P_curtail

        pv = month_data['pv_production'].values
        load = month_data['load'].values

        total_curtail_kwh = np.sum(curtailment)
        total_pv_kwh = np.sum(pv)
        curtail_pct = (total_curtail_kwh / total_pv_kwh * 100) if total_pv_kwh > 0 else 0

        max_curtail_kw = np.max(curtailment)
        hours_curtailing = np.sum(curtailment > 0.1)  # Hours with >0.1 kW curtailment

        curtailment_results.append({
            'month': month,
            'total_pv_kwh': total_pv_kwh,
            'total_curtail_kwh': total_curtail_kwh,
            'curtail_pct': curtail_pct,
            'max_curtail_kw': max_curtail_kw,
            'hours_curtailing': hours_curtailing,
            'avg_price': month_data['spot_price'].mean()
        })

        E_initial = result.E_battery_final

    # Create DataFrame and print results
    df = pd.DataFrame(curtailment_results)

    print("\n" + "="*70)
    print("MONTHLY CURTAILMENT ANALYSIS")
    print("="*70)
    print()

    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    print(f"{'Month':<6} {'Solar':<10} {'Curtail':<10} {'%':<8} {'Peak':<10} {'Hours':<8} {'Avg Price':<10}")
    print(f"{'':6} {'[MWh]':<10} {'[kWh]':<10} {'Lost':<8} {'[kW]':<10} {'>0.1kW':<8} {'[kr/kWh]':<10}")
    print("-"*70)

    for _, row in df.iterrows():
        month_name = month_names[int(row['month'])-1]
        print(f"{month_name:<6} {row['total_pv_kwh']/1000:>8.1f}   "
              f"{row['total_curtail_kwh']:>8.1f}   "
              f"{row['curtail_pct']:>6.2f}%  "
              f"{row['max_curtail_kw']:>8.1f}   "
              f"{int(row['hours_curtailing']):>6d}   "
              f"{row['avg_price']:>8.3f}")

    # Annual totals
    total_pv = df['total_pv_kwh'].sum()
    total_curtail = df['total_curtail_kwh'].sum()
    total_pct = (total_curtail / total_pv * 100) if total_pv > 0 else 0

    print("-"*70)
    print(f"{'TOTAL':<6} {total_pv/1000:>8.1f}   "
          f"{total_curtail:>8.1f}   "
          f"{total_pct:>6.2f}%")

    # Summary statistics
    print("\n" + "="*70)
    print("CURTAILMENT SUMMARY")
    print("="*70)
    print(f"\nAnnual solar production: {total_pv/1000:.1f} MWh")
    print(f"Annual curtailment:      {total_curtail:.1f} kWh ({total_curtail/1000:.2f} MWh)")
    print(f"Curtailment percentage:  {total_pct:.2f}%")
    print(f"\nPeak curtailment: {df['max_curtail_kw'].max():.1f} kW (in {month_names[df['max_curtail_kw'].idxmax()]})")
    print(f"Total hours curtailing: {int(df['hours_curtailing'].sum())} hours")

    # Economic impact (lost revenue if we could have exported)
    avg_export_price = df['avg_price'].mean()
    lost_revenue = total_curtail * avg_export_price
    print(f"\nLost export revenue: {lost_revenue:,.0f} NOK")
    print(f"  (assuming avg export price {avg_export_price:.3f} kr/kWh)")

    # Seasonal pattern
    print("\n" + "="*70)
    print("SEASONAL PATTERN")
    print("="*70)

    seasons = {
        'Winter (Dec-Feb)': [12, 1, 2],
        'Spring (Mar-May)': [3, 4, 5],
        'Summer (Jun-Aug)': [6, 7, 8],
        'Autumn (Sep-Nov)': [9, 10, 11]
    }

    for season_name, months in seasons.items():
        season_df = df[df['month'].isin(months)]
        season_pv = season_df['total_pv_kwh'].sum()
        season_curtail = season_df['total_curtail_kwh'].sum()
        season_pct = (season_curtail / season_pv * 100) if season_pv > 0 else 0
        print(f"{season_name:<20}: {season_curtail:>8.1f} kWh ({season_pct:>5.2f}% of {season_pv/1000:.1f} MWh)")

    return df


def main():
    df = analyze_curtailment_by_month(battery_kwh=30, battery_kw=15)

    print("\n" + "="*70)
    print("✓ CURTAILMENT ANALYSIS COMPLETE")
    print("="*70)

    return df


if __name__ == "__main__":
    main()
