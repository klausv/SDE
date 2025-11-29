"""
Simulering av kontorbygg med solkraft og batteri - KORREKTE DATA.

System:
- Solkraft: 100 kWp (PVGIS Stavanger, ~87,200 kWh/år)
- Nettkapasitet: 100 kW
- Forbruk: 114,000 kWh/år (kontorbygg standard profil)
- Batteri: 40 kWh, 40 kW
- Simulering: Monthly LP, timeoppløsning (PT60M)
- Nettariff: Lnett commercial
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.lp_monthly_optimizer import MonthlyLPOptimizer
from src.config.legacy_config_adapter import (
    SolarSystemConfig,
    BatteryConfig,
    GridTariffConfig,
    LocationConfig,
    ConsumptionConfig,
    DegradationConfig
)

class KontorbyggConfigLnett:
    """Config object for office building with Lnett tariff."""
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

        # Lnett commercial tariff (correct brackets)
        # Source: Lnett nettleie for næring
        self.tariff = GridTariffConfig(
            energy_peak=0.296,      # Mon-Fri 06:00-22:00
            energy_offpeak=0.176,   # Nights/weekends
            power_brackets=[
                (0, 2, 136),        # 0-2 kW: 136 NOK/mnd
                (2, 5, 232),        # 2-5 kW: 232 NOK/mnd (totalt)
                (5, 10, 372),       # 5-10 kW: 372 NOK/mnd
                (10, 15, 572),      # 10-15 kW: 572 NOK/mnd
                (15, 20, 772),      # 15-20 kW: 772 NOK/mnd
                (20, 25, 972),      # 20-25 kW: 972 NOK/mnd
                (25, 50, 1772),     # 25-50 kW: 1772 NOK/mnd
                (50, 75, 2572),     # 50-75 kW: 2572 NOK/mnd
                (75, 100, 3372),    # 75-100 kW: 3372 NOK/mnd
                (100, 200, 5600)    # 100-200 kW: 5600 NOK/mnd
            ]
        )

        self.consumption = ConsumptionConfig(annual_kwh=114000)

        # Add direct attributes for optimizer compatibility
        self.battery_capacity_kwh = 40.0
        self.battery_power_kw = 40.0

def load_pvgis_data_stavanger(target_capacity_kwp: float = 100.0) -> pd.DataFrame:
    """
    Load PVGIS data for Stavanger and scale to target capacity.

    PVGIS data is from 2020 but represents typical meteorological year (TMY).
    """
    pvgis_file = project_root / 'data' / 'pv_profiles' / 'pvgis_58.97_5.73_150kWp.csv'

    if not pvgis_file.exists():
        raise FileNotFoundError(f"PVGIS data not found: {pvgis_file}")

    print(f"✓ Laster PVGIS data fra: {pvgis_file}")
    df = pd.read_csv(pvgis_file)

    # Rename columns
    df.rename(columns={'Unnamed: 0': 'timestamp', 'production_kw': 'pv_kw'}, inplace=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Original is 150 kWp, scale to target
    original_capacity = 150.0
    scaling_factor = target_capacity_kwp / original_capacity
    df['pv_kw'] = df['pv_kw'] * scaling_factor

    # Convert 2020 timestamps to 2024 (keeping day-of-year pattern)
    # This preserves the seasonal pattern while using 2024 calendar
    df['timestamp'] = df['timestamp'].apply(
        lambda x: x.replace(year=2024) if x.month != 2 or x.day != 29
        else pd.Timestamp('2024-02-28') + pd.Timedelta(hours=x.hour)
    )

    # Round timestamps to hour (PVGIS has :11 minutes, we need :00)
    df['timestamp'] = df['timestamp'].dt.floor('h')

    annual_production = df['pv_kw'].sum()
    fulllast_hours = annual_production / target_capacity_kwp

    print(f"\n📊 PVGIS Solproduksjon (Stavanger):")
    print(f"   Kapasitet: {target_capacity_kwp:.1f} kWp")
    print(f"   Årlig produksjon: {annual_production:,.0f} kWh")
    print(f"   Fulllasttimer: {fulllast_hours:.0f} timer/år")
    print(f"   Maks effekt: {df['pv_kw'].max():.1f} kW")
    print(f"   Gjennomsnitt: {df['pv_kw'].mean():.1f} kW")

    return df

def create_commercial_load_profile(year: int = 2024, annual_kwh: float = 114000) -> pd.DataFrame:
    """
    Create realistic commercial/office building load profile.

    Based on typical Norwegian office building consumption patterns:
    - Business hours (Mon-Fri 07:00-17:00): High load
    - Extended hours (06:00-07:00, 17:00-19:00): Medium load
    - Night/weekend: Base load (HVAC, security, servers)
    - Summer reduction (vacation periods)
    """
    # Create hourly timestamps for full year
    start = pd.Timestamp(f'{year}-01-01 00:00:00')
    end = pd.Timestamp(f'{year}-12-31 23:00:00')
    timestamps = pd.date_range(start, end, freq='h')

    # Base load pattern (kW) - normalized, will scale later
    load = np.zeros(len(timestamps))

    for i, ts in enumerate(timestamps):
        hour = ts.hour
        is_weekday = ts.weekday() < 5  # Mon-Fri
        month = ts.month

        # Seasonal factors
        if month in [6, 7]:
            # June-July: Summer vacation (50% reduction)
            season_factor = 0.5
        elif month == 8:
            # August: Partial vacation (70% activity)
            season_factor = 0.7
        elif month == 12:
            # December: Christmas reduced activity
            season_factor = 0.8
        else:
            season_factor = 1.0

        if is_weekday:
            # Weekday pattern
            if hour < 6:
                # Night: Base load (HVAC, security, servers)
                load[i] = 8.0
            elif 6 <= hour < 7:
                # Morning startup
                load[i] = 15.0 * season_factor
            elif 7 <= hour < 9:
                # Morning ramp-up
                load[i] = 25.0 * season_factor
            elif 9 <= hour < 12:
                # Morning peak (lights, PCs, coffee, heating/cooling)
                load[i] = 35.0 * season_factor
            elif 12 <= hour < 13:
                # Lunch (slight reduction)
                load[i] = 30.0 * season_factor
            elif 13 <= hour < 16:
                # Afternoon peak
                load[i] = 33.0 * season_factor
            elif 16 <= hour < 17:
                # Afternoon decline
                load[i] = 28.0 * season_factor
            elif 17 <= hour < 19:
                # Evening ramp-down
                load[i] = 18.0 * season_factor
            elif 19 <= hour < 22:
                # Evening cleaning/late workers
                load[i] = 12.0 * season_factor
            else:
                # Late night base load
                load[i] = 8.0
        else:
            # Weekend/holiday pattern
            if 8 <= hour < 18:
                # Some weekend activity (cleaning, maintenance)
                load[i] = 6.0
            else:
                # Weekend base load
                load[i] = 5.0

    # Scale to match target annual consumption
    current_annual = load.sum()
    scaling_factor = annual_kwh / current_annual
    load = load * scaling_factor

    df = pd.DataFrame({
        'timestamp': timestamps,
        'load_kw': load
    })

    print(f"\n📊 Lastprofil kontorbygg:")
    print(f"   Årlig forbruk: {load.sum():,.0f} kWh")
    print(f"   Gjennomsnitt: {load.mean():.1f} kW")
    print(f"   Maks: {load.max():.1f} kW")
    print(f"   Min: {load.min():.1f} kW")

    # Show monthly pattern
    df_temp = df.copy()
    df_temp['month'] = df_temp['timestamp'].dt.month
    monthly = df_temp.groupby('month')['load_kw'].sum()
    print(f"\n   Månedlig fordeling:")
    for m, val in monthly.items():
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']
        print(f"   {month_names[m-1]}: {val:7,.0f} kWh")

    return df

def load_spot_prices(year: int = 2024) -> pd.DataFrame:
    """Load spot price data for NO2 (Stavanger area)."""
    price_file = project_root / 'data' / 'spot_prices' / f'NO2_{year}_60min_real.csv'

    if price_file.exists():
        print(f"✓ Laster spotpriser fra: {price_file}")
        df = pd.read_csv(price_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_localize(None)
        df['spot_price_nok'] = df['price_nok']

        print(f"\n📊 Spotpriser NO2 (Stavanger):")
        print(f"   Gjennomsnitt: {df['spot_price_nok'].mean():.3f} NOK/kWh")
        print(f"   Min: {df['spot_price_nok'].min():.3f} NOK/kWh")
        print(f"   Maks: {df['spot_price_nok'].max():.3f} NOK/kWh")

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

def run_simulation():
    """Run full year simulation with correct data."""

    print("="*80)
    print("KONTORBYGG SIMULERING - KORREKTE DATA")
    print("="*80)
    print("System:")
    print("  • Solkraft: 100 kWp (PVGIS Stavanger)")
    print("  • Nettkapasitet: 100 kW (import og eksport)")
    print("  • Forbruk: 114,000 kWh/år (kontorbygg standard)")
    print("  • Batteri: 40 kWh / 40 kW")
    print("  • Nettariff: Lnett commercial")
    print("  • Oppløsning: PT60M (timebasert)")
    print("="*80)

    # Create configuration with Lnett tariff
    config = KontorbyggConfigLnett()

    # Load data
    print("\n📡 Laster data...")

    # Load PVGIS solar production (scaled to 100 kWp)
    pv_df = load_pvgis_data_stavanger(target_capacity_kwp=100.0)

    # Create commercial/office load profile
    load_df = create_commercial_load_profile(year=2024, annual_kwh=114000)

    # Load spot prices
    price_df = load_spot_prices(year=2024)

    # Merge all data
    year_data = pv_df.merge(load_df, on='timestamp', how='outer')
    year_data = year_data.merge(price_df, on='timestamp', how='outer')
    year_data = year_data.sort_values('timestamp').reset_index(drop=True)

    # Fill any missing values
    year_data['pv_kw'] = year_data['pv_kw'].fillna(0)
    year_data['load_kw'] = year_data['load_kw'].fillna(load_df['load_kw'].mean())
    year_data['spot_price_nok'] = year_data['spot_price_nok'].fillna(0.50)

    print(f"\n✓ Data lastet: {len(year_data)} timer")
    print(f"  Solproduksjon: {year_data['pv_kw'].sum():,.0f} kWh/år")
    print(f"  Forbruk: {year_data['load_kw'].sum():,.0f} kWh/år")
    print(f"  Gj.snitt spotpris: {year_data['spot_price_nok'].mean():.3f} NOK/kWh")

    # Initialize optimizer with Lnett tariff
    optimizer = MonthlyLPOptimizer(
        config=config,
        resolution='PT60M',
        battery_kwh=40.0,
        battery_kw=40.0
    )

    # Run monthly optimization
    results = []
    hourly_results = []  # Store hourly data
    E_initial = 20.0  # Start at 50% SOC

    for month in range(1, 13):
        # Get month data
        month_data = year_data[year_data['timestamp'].dt.month == month].copy()

        if len(month_data) == 0:
            continue

        timestamps = pd.DatetimeIndex(month_data['timestamp'])
        pv_production = month_data['pv_kw'].values
        load_consumption = month_data['load_kw'].values
        spot_prices = month_data['spot_price_nok'].values

        # Optimize month
        result = optimizer.optimize_month(
            month_idx=month,
            pv_production=pv_production,
            load_consumption=load_consumption,
            spot_prices=spot_prices,
            timestamps=timestamps,
            E_initial=E_initial
        )

        # Store monthly aggregates
        results.append({
            'month': month,
            'pv_total_kwh': pv_production.sum(),
            'load_total_kwh': load_consumption.sum(),
            'grid_import_kwh': result.P_grid_import.sum(),
            'grid_export_kwh': result.P_grid_export.sum(),
            'battery_charge_kwh': result.P_charge.sum(),
            'battery_discharge_kwh': result.P_discharge.sum(),
            'curtailment_kwh': result.P_curtail.sum(),
            'energy_cost_nok': result.energy_cost,
            'power_cost_nok': result.power_cost,
            'total_cost_nok': result.objective_value,
            'peak_kw': result.P_peak,
        })

        # Store hourly data for mai (5) and desember (12)
        if month in [5, 12]:
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
                    'soc_pct': (result.E_battery[i] / 40.0) * 100,  # SOC in %
                    'spot_price_nok': spot_prices[i],
                })

        # Update initial SOC for next month
        E_initial = result.E_battery_final

    # Create summary DataFrame
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

    # Calculate key metrics
    export_ratio = (annual_export / annual_pv) * 100 if annual_pv > 0 else 0
    curtail_ratio = (annual_curtail / annual_pv) * 100 if annual_pv > 0 else 0
    self_consumption = annual_pv - annual_export - annual_curtail
    self_consumption_ratio = (self_consumption / annual_pv) * 100 if annual_pv > 0 else 0
    self_sufficiency = (self_consumption / annual_load) * 100 if annual_load > 0 else 0

    # Print results
    print("\n" + "="*80)
    print("ÅRLIG RESULTAT - KORREKTE DATA")
    print("="*80)

    print("\n📊 Energibalanser:")
    print(f"   Solproduksjon: {annual_pv:,.0f} kWh")
    print(f"   Forbruk: {annual_load:,.0f} kWh")
    print(f"   Import fra nett: {annual_import:,.0f} kWh")
    print(f"   Eksport til nett: {annual_export:,.0f} kWh")
    print(f"   Avklippet solkraft: {annual_curtail:,.0f} kWh")

    print(f"\n🔋 Batteri:")
    print(f"   Total lading: {df_results['battery_charge_kwh'].sum():,.0f} kWh")
    print(f"   Total utlading: {df_results['battery_discharge_kwh'].sum():,.0f} kWh")
    battery_cycles = df_results['battery_charge_kwh'].sum() / 40.0  # 40 kWh battery
    print(f"   Ekvivalente sykluser: {battery_cycles:.0f} sykluser/år")

    print(f"\n💰 Kostnader:")
    print(f"   Energikostnad: {annual_energy_cost:,.0f} NOK")
    print(f"   Effekttariff: {annual_power_cost:,.0f} NOK")
    print(f"   Total kostnad: {annual_total_cost:,.0f} NOK")

    print(f"\n🎯 Nøkkeltall:")
    print(f"   Egenforbruk av solkraft: {self_consumption:,.0f} kWh ({self_consumption_ratio:.1f}%)")
    print(f"   Eksport til nett: {annual_export:,.0f} kWh ({export_ratio:.1f}%)")
    print(f"   Avklippet solkraft: {annual_curtail:,.0f} kWh ({curtail_ratio:.1f}%)")
    print(f"   Egenforsyningsgrad: {self_sufficiency:.1f}%")

    print("\n" + "="*80)
    print(f"🔴 SVAR: {export_ratio:.1f}% av solkraften må eksporteres til nett")
    print("="*80)

    # Save detailed results
    output_file = project_root / 'results' / 'kontorbygg_korrekt_results.csv'
    output_file.parent.mkdir(exist_ok=True)
    df_results.to_csv(output_file, index=False)
    print(f"\n✓ Detaljerte månedlige resultater lagret til: {output_file}")

    # Save hourly results for mai and desember
    if hourly_results:
        df_hourly = pd.DataFrame(hourly_results)
        hourly_file = project_root / 'results' / 'kontorbygg_hourly_mai_des.csv'
        df_hourly.to_csv(hourly_file, index=False)
        print(f"✓ Timedata for mai og desember lagret til: {hourly_file}")

    return df_results, {
        'annual_pv_kwh': annual_pv,
        'annual_load_kwh': annual_load,
        'annual_export_kwh': annual_export,
        'export_ratio_pct': export_ratio,
        'curtail_ratio_pct': curtail_ratio,
        'self_consumption_ratio_pct': self_consumption_ratio,
        'self_sufficiency_pct': self_sufficiency,
    }

if __name__ == '__main__':
    results_df, summary = run_simulation()
