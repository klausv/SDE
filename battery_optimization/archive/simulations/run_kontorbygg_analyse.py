"""
Simulering av kontorbygg med solkraft og batteri.

System:
- Solkraft: 100 kWp
- Nettkapasitet: 100 kW
- Forbruk: 114,000 kWh/år (kontorbygg)
- Batteri: 40 kWh, 40 kW
- Simulering: Monthly LP, timeoppløsning (PT60M)
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

class KontorbyggConfig:
    """Simple config object for office building scenario."""
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
        self.tariff = GridTariffConfig()
        self.consumption = ConsumptionConfig(annual_kwh=114000)

        # Add direct attributes for optimizer compatibility
        self.battery_capacity_kwh = 40.0
        self.battery_power_kw = 40.0

def create_office_load_profile(year: int = 2024) -> pd.DataFrame:
    """
    Create realistic office building load profile: 114,000 kWh/year.

    Office characteristics:
    - Mon-Fri: 06:00-18:00 high load
    - Weekends: Low base load
    - Summer reduction (vacation)
    """
    # Create hourly timestamps for full year
    start = pd.Timestamp(f'{year}-01-01 00:00:00')
    end = pd.Timestamp(f'{year}-12-31 23:00:00')
    timestamps = pd.date_range(start, end, freq='h')

    # Target annual consumption
    annual_kwh = 114_000

    # Base load pattern (kW)
    load = np.zeros(len(timestamps))

    for i, ts in enumerate(timestamps):
        hour = ts.hour
        is_weekday = ts.weekday() < 5  # Mon-Fri
        month = ts.month

        # Summer reduction factor (June-August)
        summer_factor = 0.6 if month in [6, 7, 8] else 1.0

        if is_weekday:
            # Weekday office hours (06:00-18:00)
            if 6 <= hour < 9:
                load[i] = 20.0 * summer_factor  # Morning ramp-up
            elif 9 <= hour < 17:
                load[i] = 25.0 * summer_factor  # Peak office hours
            elif 17 <= hour < 19:
                load[i] = 18.0 * summer_factor  # Evening ramp-down
            else:
                load[i] = 5.0 * summer_factor   # Night base load
        else:
            # Weekend - low base load
            load[i] = 3.0 * summer_factor

    # Scale to match annual target
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

    return df

def load_pvgis_data(year: int = 2024, pv_capacity_kwp: float = 100.0) -> pd.DataFrame:
    """Load PVGIS solar production data and scale to capacity."""

    # Try to load existing PVGIS data
    pvgis_file = project_root / 'data' / 'pv_profiles' / 'pvgis_stavanger_2024_hourly.csv'

    if pvgis_file.exists():
        print(f"✓ Laster PVGIS data fra: {pvgis_file}")
        df = pd.read_csv(pvgis_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Scale to desired capacity (PVGIS data is typically for 1 kWp)
        if 'pv_kw' in df.columns:
            # Already scaled, rescale to target
            current_capacity = df['pv_kw'].max() / 0.8  # Assume max is 80% of capacity
            scale_factor = pv_capacity_kwp / current_capacity
            df['pv_kw'] = df['pv_kw'] * scale_factor
        elif 'P' in df.columns:
            # PVGIS raw data (W per kWp installed)
            df['pv_kw'] = (df['P'] / 1000.0) * pv_capacity_kwp

        return df
    else:
        print("⚠ PVGIS fil ikke funnet, genererer syntetisk solprofil")
        return create_synthetic_solar_profile(year, pv_capacity_kwp)

def create_synthetic_solar_profile(year: int, pv_capacity_kwp: float) -> pd.DataFrame:
    """Create simple synthetic solar production profile."""
    start = pd.Timestamp(f'{year}-01-01 00:00:00')
    end = pd.Timestamp(f'{year}-12-31 23:00:00')
    timestamps = pd.date_range(start, end, freq='h')

    pv = np.zeros(len(timestamps))

    for i, ts in enumerate(timestamps):
        hour = ts.hour
        month = ts.month
        day_of_year = ts.dayofyear

        # Seasonal factor (more sun in summer)
        season_factor = 0.3 + 0.7 * (1 - abs(day_of_year - 182) / 182)

        # Daily pattern (bell curve)
        if 6 <= hour <= 20:
            hour_angle = (hour - 13) / 7.0  # Peak at 13:00
            daily_factor = np.exp(-2 * hour_angle**2)
            pv[i] = pv_capacity_kwp * daily_factor * season_factor

    return pd.DataFrame({'timestamp': timestamps, 'pv_kw': pv})

def load_spot_prices(year: int = 2024) -> pd.DataFrame:
    """Load spot price data."""
    price_file = project_root / 'data' / 'spot_prices' / f'{year}_NO2_hourly.csv'

    if price_file.exists():
        print(f"✓ Laster spotpriser fra: {price_file}")
        df = pd.read_csv(price_file)
        df['timestamp'] = pd.to_datetime(df['HourUTC'])
        df['spot_price_nok'] = df['SpotPriceNOK'] / 1000.0  # Øre to NOK
        return df[['timestamp', 'spot_price_nok']]
    else:
        print("⚠ Spotpris fil ikke funnet, bruker default 0.50 NOK/kWh")
        start = pd.Timestamp(f'{year}-01-01 00:00:00')
        end = pd.Timestamp(f'{year}-12-31 23:00:00')
        timestamps = pd.date_range(start, end, freq='h')
        return pd.DataFrame({
            'timestamp': timestamps,
            'spot_price_nok': np.full(len(timestamps), 0.50)
        })

def run_kontorbygg_simulation():
    """Run full year simulation for office building."""

    print("="*80)
    print("KONTORBYGG SIMULERING - Monthly LP")
    print("="*80)
    print("System:")
    print("  • Solkraft: 100 kWp")
    print("  • Nettkapasitet: 100 kW (import og eksport)")
    print("  • Forbruk: 114,000 kWh/år")
    print("  • Batteri: 40 kWh / 40 kW")
    print("  • Oppløsning: PT60M (timebasert)")
    print("="*80)

    # Create configuration
    config = KontorbyggConfig()

    # Load data
    print("\n📡 Laster data...")

    # Load solar production
    pv_df = load_pvgis_data(year=2024, pv_capacity_kwp=100.0)

    # Create office load profile
    load_df = create_office_load_profile(year=2024)

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

    # Initialize optimizer
    optimizer = MonthlyLPOptimizer(
        config=config,
        resolution='PT60M',
        battery_kwh=40.0,
        battery_kw=40.0
    )

    # Run monthly optimization
    results = []
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

        # Store results
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

    # Print results
    print("\n" + "="*80)
    print("ÅRLIG RESULTAT")
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
    print(f"🔴 SVAR: {export_ratio:.1f}% av solkraften må eksporteres til nett")
    print("="*80)

    # Save detailed results
    output_file = project_root / 'results' / 'kontorbygg_monthly_results.csv'
    output_file.parent.mkdir(exist_ok=True)
    df_results.to_csv(output_file, index=False)
    print(f"\n✓ Detaljerte resultater lagret til: {output_file}")

    return df_results, {
        'annual_pv_kwh': annual_pv,
        'annual_export_kwh': annual_export,
        'export_ratio_pct': export_ratio,
        'curtail_ratio_pct': curtail_ratio,
        'self_consumption_ratio_pct': self_consumption_ratio,
    }

if __name__ == '__main__':
    results_df, summary = run_kontorbygg_simulation()
