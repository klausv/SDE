#!/usr/bin/env python3
"""
Get PVGIS data for EXACT location and system specifications
Location: 58.92964446749999, 5.6230515864177155 (2 moh)
System: 138.5 kWp, 100 kW inverter, 70 kW grid limit
"""
import requests
import numpy as np
import pandas as pd
import pickle
from datetime import datetime

# EXACT system specifications
LAT = 58.92964446749999
LON = 5.6230515864177155
ELEVATION = 2  # meters above sea level
PV_CAPACITY = 138.55  # kWp (exact from PVSol)
INVERTER_LIMIT = 100  # kW
GRID_LIMIT = 70  # kW
TILT = 15  # degrees (from PVSol document)
AZIMUTH = 171  # south facing (from PVSol document)

def get_pvgis_hourly_production():
    """Get hourly PV production from PVGIS for exact location"""

    url = "https://re.jrc.ec.europa.eu/api/seriescalc"

    params = {
        'lat': LAT,
        'lon': LON,
        'peakpower': PV_CAPACITY,
        'loss': 14,  # System losses (matching PVSol)
        'angle': TILT,
        'aspect': AZIMUTH - 180,  # PVGIS uses 0=South, PVSol uses 180=South
        'outputformat': 'json',
        'browser': 0
    }

    print(f"🌍 Fetching PVGIS data for exact location:")
    print(f"   Coordinates: {LAT:.6f}, {LON:.6f}")
    print(f"   Elevation: {ELEVATION} m")
    print(f"   System: {PV_CAPACITY} kWp")
    print(f"   Inverter: {INVERTER_LIMIT} kW")
    print(f"   Grid limit: {GRID_LIMIT} kW")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Extract hourly data
        hourly_data = data.get('outputs', {}).get('hourly', [])

        if not hourly_data:
            raise ValueError("No hourly data in PVGIS response")

        print(f"✅ Got {len(hourly_data)} hours of data")

        # Convert to DataFrame
        df = pd.DataFrame(hourly_data)

        # Parse timestamp
        df['time'] = pd.to_datetime(df['time'], format='%Y%m%d:%H%M')
        df.set_index('time', inplace=True)

        # P is PV power in W, convert to kW
        df['pv_dc_kw'] = df['P'] / 1000.0

        # Apply inverter clipping
        df['pv_ac_kw'] = np.minimum(df['pv_dc_kw'], INVERTER_LIMIT)

        # Track clipping losses
        df['inverter_clipping'] = df['pv_dc_kw'] - df['pv_ac_kw']

        # Check grid constraint
        df['grid_constraint'] = np.maximum(0, df['pv_ac_kw'] - GRID_LIMIT)

        return df

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def get_pvgis_tmy_data():
    """Get TMY solar radiation data"""

    url = "https://re.jrc.ec.europa.eu/api/tmy"

    params = {
        'lat': LAT,
        'lon': LON,
        'outputformat': 'json'
    }

    print(f"\n📊 Fetching TMY data...")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        hourly_data = data.get('outputs', {}).get('tmy_hourly', [])

        if not hourly_data:
            raise ValueError("No TMY data")

        df = pd.DataFrame(hourly_data)

        # Parse time
        df['time'] = pd.to_datetime(df['time(UTC)'], format='%Y%m%d:%H%M', errors='coerce')
        df.set_index('time', inplace=True)

        # Calculate PV from radiation
        # Global horizontal irradiance
        ghi = df['G(h)'].fillna(0)

        # Simple PV model
        pv_dc = (ghi / 1000) * PV_CAPACITY * 0.85  # 85% system efficiency

        # Apply inverter limit
        pv_ac = np.minimum(pv_dc, INVERTER_LIMIT)

        df['pv_dc_kw'] = pv_dc
        df['pv_ac_kw'] = pv_ac
        df['inverter_clipping'] = pv_dc - pv_ac

        print(f"✅ Got TMY data with {len(df)} hours")

        return df

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def analyze_production(df):
    """Analyze PV production statistics"""

    if df is None or df.empty:
        return

    # Take one year (8760 hours)
    if len(df) > 8760:
        df_year = df.iloc[:8760]
    else:
        df_year = df

    total_dc = df_year['pv_dc_kw'].sum()
    total_ac = df_year['pv_ac_kw'].sum()
    clipping_loss = df_year['inverter_clipping'].sum()

    hours_at_inverter_limit = (df_year['pv_ac_kw'] >= INVERTER_LIMIT * 0.99).sum()
    hours_above_grid_limit = (df_year['pv_ac_kw'] > GRID_LIMIT).sum()
    potential_curtailment = df_year['grid_constraint'].sum() if 'grid_constraint' in df_year.columns else 0

    capacity_factor = df_year['pv_ac_kw'].mean() / PV_CAPACITY

    print("\n📈 Annual Production Analysis:")
    print(f"   • Total DC production: {total_dc/1000:.1f} MWh")
    print(f"   • Total AC production: {total_ac/1000:.1f} MWh")
    print(f"   • Inverter clipping loss: {clipping_loss/1000:.1f} MWh ({clipping_loss/total_dc*100:.1f}%)")
    print(f"   • Hours at inverter limit: {hours_at_inverter_limit}")
    print(f"   • Hours above grid limit: {hours_above_grid_limit}")
    print(f"   • Potential curtailment: {potential_curtailment/1000:.1f} MWh")
    print(f"   • Capacity factor: {capacity_factor:.1%}")
    print(f"   • Peak AC output: {df_year['pv_ac_kw'].max():.1f} kW")

    # Monthly breakdown
    print("\n📅 Monthly Production (MWh):")
    monthly = df_year['pv_ac_kw'].resample('ME').sum() / 1000
    for month, prod in monthly.items():
        if 'grid_constraint' in df_year.columns:
            curtailed = df_year.loc[df_year.index.month == month.month, 'grid_constraint'].sum() / 1000
            print(f"   {month.strftime('%B'):10s}: {prod:5.1f} MWh  (curtailment: {curtailed:.1f} MWh)")
        else:
            print(f"   {month.strftime('%B'):10s}: {prod:5.1f} MWh")

    return df_year

def main():
    print("\n" + "="*70)
    print("🔋 PVGIS DATA FOR EXACT SYSTEM LOCATION")
    print("="*70)

    # Method 1: Direct PV calculation
    print("\n📊 Method 1: PVGIS PV Production Model")
    df_pv = get_pvgis_hourly_production()

    if df_pv is not None:
        df_analyzed = analyze_production(df_pv)

        # Save data
        df_analyzed.to_pickle('data/pvgis_exact_production.pkl')
        print("\n✅ Saved to data/pvgis_exact_production.pkl")

    # Method 2: TMY radiation data
    print("\n" + "="*50)
    print("📊 Method 2: TMY Radiation Model")
    df_tmy = get_pvgis_tmy_data()

    if df_tmy is not None:
        analyze_production(df_tmy)
        df_tmy.to_pickle('data/pvgis_exact_tmy.pkl')
        print("\n✅ Saved to data/pvgis_exact_tmy.pkl")

    print("\n" + "="*70)
    print("✅ Ready for battery optimization with exact data!")
    print("="*70)

if __name__ == "__main__":
    main()