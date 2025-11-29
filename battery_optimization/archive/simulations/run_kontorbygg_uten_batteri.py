"""
Simulering av kontorbygg UTEN batteri for sammenligning.
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
        # NO BATTERY - set to 0
        self.battery = BatteryConfig(
            capacity_kwh=0.0,  # NO BATTERY
            power_kw=0.0,      # NO BATTERY
            efficiency_roundtrip=0.90,
            min_soc=0.10,
            max_soc=0.90,
            degradation=DegradationConfig(enabled=False)
        )
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
        self.battery_capacity_kwh = 0.0  # NO BATTERY
        self.battery_power_kw = 0.0       # NO BATTERY

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

print("="*80)
print("KONTORBYGG SIMULERING - UTEN BATTERI")
print("="*80)
print("System:")
print("  • Solkraft: 100 kWp (PVGIS Stavanger)")
print("  • Nettkapasitet: 100 kW (import og eksport)")
print("  • Forbruk: 114,000 kWh/år (kontorbygg)")
print("  • Batteri: INGEN (0 kWh)")
print("  • Nettariff: Lnett commercial")
print("="*80)

print("\n📡 Laster data...")
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
optimizer = MonthlyLPOptimizer(config=config, resolution='PT60M', battery_kwh=0.0, battery_kw=0.0)

results = []
E_initial = 0.0  # No battery

for month in range(1, 13):
    month_data = year_data[year_data['timestamp'].dt.month == month].copy()
    if len(month_data) == 0:
        continue

    timestamps = pd.DatetimeIndex(month_data['timestamp'])
    pv_production = month_data['pv_kw'].values
    load_consumption = month_data['load_kw'].values
    spot_prices = month_data['spot_price_nok'].values

    result = optimizer.optimize_month(
        month_idx=month,
        pv_production=pv_production,
        load_consumption=load_consumption,
        spot_prices=spot_prices,
        timestamps=timestamps,
        E_initial=E_initial
    )

    results.append({
        'month': month,
        'pv_total_kwh': pv_production.sum(),
        'load_total_kwh': load_consumption.sum(),
        'grid_import_kwh': result.P_grid_import.sum(),
        'grid_export_kwh': result.P_grid_export.sum(),
        'curtailment_kwh': result.P_curtail.sum(),
        'energy_cost_nok': result.energy_cost,
        'power_cost_nok': result.power_cost,
        'total_cost_nok': result.objective_value,
        'peak_kw': result.P_peak,
    })

df_results = pd.DataFrame(results)

# Calculate annual totals
annual_pv = df_results['pv_total_kwh'].sum()
annual_load = df_results['load_total_kwh'].sum()
annual_import = df_results['grid_import_kwh'].sum()
annual_export = df_results['grid_export_kwh'].sum()
annual_curtail = df_results['curtailment_kwh'].sum()
annual_energy_cost = df_results['energy_cost_nok'].sum()
annual_power_cost = df_results['power_cost_nok'].sum()
annual_total_cost = df_results['total_cost_nok'].sum()

export_ratio = (annual_export / annual_pv) * 100 if annual_pv > 0 else 0
curtail_ratio = (annual_curtail / annual_pv) * 100 if annual_pv > 0 else 0
self_consumption = annual_pv - annual_export - annual_curtail
self_consumption_ratio = (self_consumption / annual_pv) * 100 if annual_pv > 0 else 0

print("\n" + "="*80)
print("ÅRLIG RESULTAT - UTEN BATTERI")
print("="*80)

print("\n📊 Energibalanser:")
print(f"   Solproduksjon: {annual_pv:,.0f} kWh")
print(f"   Forbruk: {annual_load:,.0f} kWh")
print(f"   Import fra nett: {annual_import:,.0f} kWh")
print(f"   Eksport til nett: {annual_export:,.0f} kWh")
print(f"   Avklippet solkraft: {annual_curtail:,.0f} kWh")

print(f"\n💰 Kostnader:")
print(f"   Energikostnad: {annual_energy_cost:,.0f} NOK")
print(f"   Effekttariff: {annual_power_cost:,.0f} NOK")
print(f"   Total kostnad: {annual_total_cost:,.0f} NOK")

print(f"\n🎯 Nøkkeltall:")
print(f"   Egenforbruk av solkraft: {self_consumption:,.0f} kWh ({self_consumption_ratio:.1f}%)")
print(f"   Eksport til nett: {annual_export:,.0f} kWh ({export_ratio:.1f}%)")
print(f"   Avklippet solkraft: {annual_curtail:,.0f} kWh ({curtail_ratio:.1f}%)")
print(f"   Egenforsyningsgrad: {(self_consumption/annual_load)*100:.1f}%")

print("\n" + "="*80)
print(f"🔴 SVAR: {export_ratio:.1f}% av solkraften må eksporteres til nett (UTEN BATTERI)")
print("="*80)

# Save results
output_file = project_root / 'results' / 'kontorbygg_uten_batteri_results.csv'
df_results.to_csv(output_file, index=False)
print(f"\n✓ Resultater lagret til: {output_file}")
