"""
Kjør simulering bare for mai og desember for å få timedata.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.lp_monthly_optimizer import MonthlyLPOptimizer
from src.config.legacy_config_adapter import (
    SolarSystemConfig, BatteryConfig, GridTariffConfig,
    LocationConfig, ConsumptionConfig, DegradationConfig
)

class KontorbyggConfigLnett:
    def __init__(self):
        self.location = LocationConfig()
        self.solar = SolarSystemConfig(
            pv_capacity_kwp=100.0,
            grid_import_limit_kw=100.0,
            grid_export_limit_kw=100.0,
            grid_connection_limit_kw=100.0
        )
        self.battery = BatteryConfig(
            capacity_kwh=40.0,
            power_kw=40.0,
            efficiency_roundtrip=0.90,
            min_soc=0.10,
            max_soc=0.90,
            degradation=DegradationConfig(enabled=False)
        )
        # Lnett commercial tariff
        self.tariff = GridTariffConfig(
            energy_peak=0.296,
            energy_offpeak=0.176,
            power_brackets=[
                (0, 2, 136), (2, 5, 232), (5, 10, 372), (10, 15, 572),
                (15, 20, 772), (20, 25, 972), (25, 50, 1772),
                (50, 75, 2572), (75, 100, 3372), (100, 200, 5600)
            ]
        )
        self.consumption = ConsumptionConfig(annual_kwh=114000)
        self.battery_capacity_kwh = 40.0
        self.battery_power_kw = 40.0

def load_pvgis_data_stavanger(target_capacity_kwp: float = 100.0, year: int = 2024) -> pd.DataFrame:
    pvgis_file = project_root / 'data' / 'pv_profiles' / 'pvgis_58.97_5.73_150kWp.csv'
    df = pd.read_csv(pvgis_file)
    df.rename(columns={'Unnamed: 0': 'timestamp', 'production_kw': 'pv_kw'}, inplace=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['timestamp'] = df['timestamp'].apply(
        lambda x: x.replace(year=2024) if x.month != 2 or x.day != 29
        else pd.Timestamp('2024-02-28') + pd.Timedelta(hours=x.hour)
    )
    df['timestamp'] = df['timestamp'].dt.floor('h')
    original_capacity = 150.0
    scaling_factor = target_capacity_kwp / original_capacity
    df['pv_kw'] = df['pv_kw'] * scaling_factor
    return df

def create_commercial_load_profile(year: int = 2024, annual_kwh: float = 114000) -> pd.DataFrame:
    start = pd.Timestamp(f'{year}-01-01 00:00:00')
    end = pd.Timestamp(f'{year}-12-31 23:00:00')
    timestamps = pd.date_range(start, end, freq='h')
    load = np.zeros(len(timestamps))

    for i, ts in enumerate(timestamps):
        hour = ts.hour
        is_weekday = ts.weekday() < 5
        month = ts.month

        if month == 6 or month == 7:
            season_factor = 0.5
        elif month == 8:
            season_factor = 0.7
        else:
            season_factor = 1.0

        if is_weekday:
            if 7 <= hour < 9:
                load[i] = 25.0 * season_factor
            elif 9 <= hour < 12:
                load[i] = 35.0 * season_factor
            elif 12 <= hour < 13:
                load[i] = 28.0 * season_factor
            elif 13 <= hour < 16:
                load[i] = 33.0 * season_factor
            elif 16 <= hour < 18:
                load[i] = 22.0 * season_factor
            else:
                load[i] = 6.0 * season_factor
        else:
            load[i] = 5.0 * season_factor

    current_annual = load.sum()
    scaling_factor = annual_kwh / current_annual
    load = load * scaling_factor

    return pd.DataFrame({'timestamp': timestamps, 'load_kw': load})

def load_spot_prices(year: int = 2024) -> pd.DataFrame:
    """Load spot price data for NO2 (Stavanger area)."""
    price_file = project_root / 'data' / 'spot_prices' / f'NO2_{year}_60min_real.csv'

    if price_file.exists():
        print(f"✓ Laster spotpriser fra: {price_file}")
        df = pd.read_csv(price_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_localize(None)
        df['spot_price_nok'] = df['price_nok']
        print(f"   Gjennomsnitt: {df['spot_price_nok'].mean():.3f} NOK/kWh")
        return df[['timestamp', 'spot_price_nok']]
    else:
        print(f"⚠ Spotpris fil ikke funnet ({price_file}), bruker default 0.50 NOK/kWh")
        start = pd.Timestamp(f'{year}-01-01 00:00:00')
        end = pd.Timestamp(f'{year}-12-31 23:00:00')
        timestamps = pd.date_range(start, end, freq='h')
        return pd.DataFrame({
            'timestamp': timestamps,
            'spot_price_nok': np.full(len(timestamps), 0.50)
        })

print("Laster data...")
pv_df = load_pvgis_data_stavanger(target_capacity_kwp=100.0)
load_df = create_commercial_load_profile(year=2024, annual_kwh=114000)
price_df = load_spot_prices(year=2024)

year_data = pv_df.merge(load_df, on='timestamp', how='outer')
year_data = year_data.merge(price_df, on='timestamp', how='outer')
year_data = year_data.sort_values('timestamp').reset_index(drop=True)
year_data['pv_kw'] = year_data['pv_kw'].fillna(0)
year_data['load_kw'] = year_data['load_kw'].fillna(load_df['load_kw'].mean())
year_data['spot_price_nok'] = year_data['spot_price_nok'].fillna(0.50)

config = KontorbyggConfigLnett()
optimizer = MonthlyLPOptimizer(config=config, resolution='PT60M', battery_kwh=40.0, battery_kw=40.0)

hourly_results = []

for month in [5, 12]:  # Mai og Desember
    print(f"\n{'='*70}")
    print(f"Simulerer måned {month} ({'Mai' if month == 5 else 'Desember'})")
    print(f"{'='*70}")

    month_data = year_data[year_data['timestamp'].dt.month == month].copy()
    timestamps = pd.DatetimeIndex(month_data['timestamp'])
    pv_production = month_data['pv_kw'].values
    load_consumption = month_data['load_kw'].values
    spot_prices = month_data['spot_price_nok'].values

    # Estimate initial SOC based on month
    E_initial = 20.0 if month == 5 else 4.0  # Mai: 50%, Des: 10%

    result = optimizer.optimize_month(
        month_idx=month,
        pv_production=pv_production,
        load_consumption=load_consumption,
        spot_prices=spot_prices,
        timestamps=timestamps,
        E_initial=E_initial
    )

    for i, ts in enumerate(timestamps):
        hourly_results.append({
            'timestamp': ts,
            'month': month,
            'pv_kw': pv_production[i],
            'load_kw': load_consumption[i],
            'grid_import_kw': result.P_grid_import[i],
            'grid_export_kw': result.P_grid_export[i],
            'battery_charge_kw': result.P_charge[i],
            'battery_discharge_kw': result.P_discharge[i],
            'battery_energy_kwh': result.E_battery[i],
            'soc_pct': (result.E_battery[i] / 40.0) * 100,
            'spot_price_nok': spot_prices[i],
        })

df_hourly = pd.DataFrame(hourly_results)
output_file = project_root / 'results' / 'kontorbygg_hourly_mai_des.csv'
df_hourly.to_csv(output_file, index=False)
print(f"\n✓ Timedata lagret til: {output_file}")
print(f"  Mai: {len(df_hourly[df_hourly.month==5])} timer")
print(f"  Desember: {len(df_hourly[df_hourly.month==12])} timer")
