#!/usr/bin/env python3
"""
Get realistic PV production data for Stavanger using PVGIS API
Uses TMY (Typical Meteorological Year) data which is representative
"""
import requests
import json
import numpy as np
import pandas as pd
from datetime import datetime
import pickle

def get_pvgis_hourly_pv(lat=58.97, lon=5.73, peakpower=150, loss=14, angle=25, aspect=180):
    """
    Get hourly PV production from PVGIS for a typical year

    Args:
        lat: Latitude (Stavanger: 58.97)
        lon: Longitude (Stavanger: 5.73)
        peakpower: Installed capacity in kWp
        loss: System losses in % (cables, inverter, etc)
        angle: Tilt angle in degrees (25° for Stavanger)
        aspect: Azimuth (180 = south)

    Returns:
        DataFrame with hourly PV production
    """

    # PVGIS API endpoint for hourly PV production
    url = "https://re.jrc.ec.europa.eu/api/seriescalc"

    params = {
        'lat': lat,
        'lon': lon,
        'pvcalculation': 1,
        'peakpower': peakpower,
        'loss': loss,
        'angle': angle,
        'aspect': aspect,
        'outputformat': 'json',
        'browser': 0
    }

    print(f"Fetching PVGIS data for Stavanger ({lat}, {lon})...")
    print(f"System: {peakpower} kWp, {angle}° tilt, facing south")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Extract hourly data
        hourly_data = data.get('outputs', {}).get('hourly', [])

        if not hourly_data:
            raise ValueError("No hourly data in PVGIS response")

        print(f"Got {len(hourly_data)} hours of data")

        # Convert to DataFrame
        df = pd.DataFrame(hourly_data)

        # Parse timestamp
        df['time'] = pd.to_datetime(df['time'], format='%Y%m%d:%H%M')
        df.set_index('time', inplace=True)

        # P is the PV power output in W
        df['pv_kw'] = df['P'] / 1000.0  # Convert W to kW

        return df

    except Exception as e:
        print(f"Error fetching PVGIS data: {e}")
        return None

def get_pvgis_tmy_solar(lat=58.97, lon=5.73):
    """
    Get TMY (Typical Meteorological Year) solar radiation data from PVGIS

    Returns:
        DataFrame with hourly solar radiation components
    """

    url = "https://re.jrc.ec.europa.eu/api/tmy"

    params = {
        'lat': lat,
        'lon': lon,
        'outputformat': 'json'
    }

    print(f"Fetching TMY solar data for Stavanger...")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Extract hourly TMY data
        hourly_data = data.get('outputs', {}).get('tmy_hourly', [])

        if not hourly_data:
            raise ValueError("No TMY data in PVGIS response")

        print(f"Got TMY data with {len(hourly_data)} hours")

        # Convert to DataFrame
        df = pd.DataFrame(hourly_data)

        # Parse timestamp
        df['time'] = pd.to_datetime(df['time(UTC)'], format='%Y%m%d:%H%M', errors='coerce')
        df.set_index('time', inplace=True)

        # Key radiation components:
        # G(h): Global horizontal irradiation (W/m²)
        # Gb(n): Direct normal irradiation (W/m²)
        # Gd(h): Diffuse horizontal irradiation (W/m²)

        return df

    except Exception as e:
        print(f"Error fetching TMY data: {e}")
        return None

def calculate_pv_with_inverter_limit(solar_df, pv_capacity_kwp=150, inverter_limit_kw=110):
    """
    Calculate PV production with inverter clipping

    Args:
        solar_df: DataFrame with solar radiation data
        pv_capacity_kwp: PV array capacity
        inverter_limit_kw: Inverter AC limit

    Returns:
        Series with hourly PV production in kW
    """

    # Simplified PV model
    # Using global horizontal irradiance as proxy
    ghi = solar_df['G(h)'].fillna(0)

    # Convert irradiance to PV output
    # Assuming 1000 W/m² = rated capacity at STC
    pv_dc = (ghi / 1000) * pv_capacity_kwp

    # Apply typical system losses (15%)
    pv_ac = pv_dc * 0.85

    # Apply inverter clipping
    pv_clipped = np.minimum(pv_ac, inverter_limit_kw)

    return pv_clipped

def main():
    """Test PVGIS data fetching for Stavanger"""

    print("\n" + "="*60)
    print("🌞 PVGIS DATA FOR STAVANGER SOLAR INSTALLATION")
    print("="*60)

    # Stavanger coordinates
    lat, lon = 58.97, 5.73

    # Method 1: Direct PV calculation from PVGIS
    print("\n📊 Method 1: Direct PV calculation from PVGIS")
    pv_df = get_pvgis_hourly_pv(lat, lon, peakpower=150, angle=25)

    if pv_df is not None:
        # Apply inverter limit
        pv_df['pv_limited'] = np.minimum(pv_df['pv_kw'], 110)

        # Statistics
        total_production = pv_df['pv_limited'].sum()
        capacity_factor = pv_df['pv_limited'].mean() / 150
        hours_at_limit = (pv_df['pv_limited'] >= 109).sum()
        clipping_loss = (pv_df['pv_kw'] - pv_df['pv_limited']).sum()

        print(f"\nResults:")
        print(f"  • Total production: {total_production/1000:.1f} MWh/year")
        print(f"  • Capacity factor: {capacity_factor:.1%}")
        print(f"  • Peak output: {pv_df['pv_limited'].max():.1f} kW")
        print(f"  • Hours at inverter limit: {hours_at_limit}")
        print(f"  • Clipping losses: {clipping_loss/1000:.1f} MWh/year")

        # Save for use in optimization
        pv_df.to_pickle('data/pvgis_stavanger_pv.pkl')
        print(f"\n✅ Saved to data/pvgis_stavanger_pv.pkl")

        # Monthly summary
        print("\n📅 Monthly production (MWh):")
        monthly = pv_df['pv_limited'].resample('M').sum() / 1000
        for month, prod in monthly.items():
            print(f"  {month.strftime('%B')}: {prod:.1f} MWh")

    # Method 2: TMY solar radiation data
    print("\n📊 Method 2: TMY solar radiation data")
    tmy_df = get_pvgis_tmy_solar(lat, lon)

    if tmy_df is not None:
        # Calculate PV from radiation
        pv_production = calculate_pv_with_inverter_limit(tmy_df, 150, 110)

        total_tmy = pv_production.sum()
        print(f"\nTMY-based production: {total_tmy/1000:.1f} MWh/year")

        # Save TMY data
        tmy_df.to_pickle('data/pvgis_stavanger_tmy.pkl')
        pv_production.to_pickle('data/pvgis_stavanger_production.pkl')
        print(f"✅ Saved TMY data")

    print("\n" + "="*60)
    print("✅ PVGIS data ready for battery optimization!")
    print("="*60)

if __name__ == "__main__":
    main()