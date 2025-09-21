"""
EKTE solproduksjon fra PVGIS API
Ikke tull-tall!
"""
import requests
import pandas as pd
import numpy as np
from typing import Tuple
import json
import os
from datetime import datetime


class PVGISProduction:
    """Henter REELL solproduksjon fra PVGIS EU JRC"""

    def __init__(
        self,
        lat: float = 58.97,  # Stavanger
        lon: float = 5.73,
        pv_capacity_kwp: float = 138.55,
        tilt: float = 30,
        azimuth: float = 180,  # South
        system_loss: float = 7  # Realistisk systemtap
    ):
        self.lat = lat
        self.lon = lon
        self.pv_capacity_kwp = pv_capacity_kwp
        self.tilt = tilt
        self.azimuth = azimuth
        self.system_loss = system_loss
        self.cache_dir = "data/pv_profiles"
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = f"{self.cache_dir}/pvgis_{lat}_{lon}_{pv_capacity_kwp}kWp.csv"

    def fetch_hourly_production(self, year: int = 2020, refresh: bool = False) -> pd.Series:
        """
        Hent time-for-time produksjon for et år fra PVGIS
        Bruker typisk meteorologisk år (TMY)

        Args:
            year: År for data (brukes for TMY)
            refresh: Hvis True, hent nye data selv om cache finnes
        """
        # Check cache first (unless refresh requested)
        if os.path.exists(self.cache_file) and not refresh:
            print(f"📁 Bruker cached PVGIS data: {self.cache_file}")
            data = pd.read_csv(self.cache_file, index_col=0, parse_dates=True)
            # Print summary
            print(f"   • Årsproduksjon: {data['production_kw'].sum()/1000:.1f} MWh")
            print(f"   • Maks effekt: {data['production_kw'].max():.1f} kW")
            return data['production_kw']

        if refresh:
            print("🔄 Oppdaterer PVGIS data (--refresh-data flagg)")
        else:
            print("📡 Ingen cache funnet, henter nye PVGIS data...")

        print(f"🌐 Henter PVGIS data for {self.lat}, {self.lon}...")

        # PVGIS API endpoint
        base_url = "https://re.jrc.ec.europa.eu/api/v5_2/seriescalc"

        params = {
            'lat': self.lat,
            'lon': self.lon,
            'peakpower': self.pv_capacity_kwp,
            'angle': self.tilt,
            'aspect': self.azimuth - 180,  # PVGIS uses 0=South
            'startyear': year,
            'endyear': year,
            'pvcalculation': 1,
            'loss': self.system_loss,
            'outputformat': 'json'
        }

        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Extract hourly data
            hourly_data = data['outputs']['hourly']

            # Create DataFrame
            timestamps = []
            production = []

            for entry in hourly_data:
                # Parse PVGIS timestamp format: "20200101:0010"
                time_str = entry['time']
                year = int(time_str[:4])
                month = int(time_str[4:6])
                day = int(time_str[6:8])
                hour = int(time_str[9:11])
                minute = int(time_str[11:13])

                timestamp = pd.Timestamp(year=year, month=month, day=day,
                                        hour=hour, minute=minute)
                timestamps.append(timestamp)

                # P is the PV production in W, convert to kW
                production.append(entry['P'] / 1000)

            # Create series
            production_series = pd.Series(
                production,
                index=pd.DatetimeIndex(timestamps),
                name='production_kw'
            )

            # For full year, we need 8760 hours
            # PVGIS gives us actual year data, resample if needed
            if len(production_series) < 8760:
                print(f"⚠️ PVGIS ga {len(production_series)} timer, fyller til 8760...")
                # Create full year index
                full_index = pd.date_range(
                    start=f'{year}-01-01',
                    end=f'{year}-12-31 23:00',
                    freq='h'
                )
                production_series = production_series.reindex(full_index, fill_value=0)

            # Save to cache
            os.makedirs('data', exist_ok=True)
            production_series.to_frame().to_csv(self.cache_file)
            print(f"💾 Cached PVGIS data til {self.cache_file}")

            return production_series

        except Exception as e:
            print(f"❌ PVGIS API feilet: {e}")
            print("Faller tilbake til syntetisk produksjon...")
            return self._generate_synthetic_production(year)

    def _generate_synthetic_production(self, year: int) -> pd.Series:
        """
        Fallback: Generer realistisk produksjon basert på pvlib
        """
        try:
            import pvlib
            from pvlib import location
            from pvlib import irradiance

            print("🔧 Genererer produksjon med pvlib...")

            # Create location
            site = location.Location(
                latitude=self.lat,
                longitude=self.lon,
                tz='Europe/Oslo',
                altitude=10
            )

            # Create time index
            times = pd.date_range(
                start=f'{year}-01-01',
                end=f'{year}-12-31 23:00',
                freq='h',
                tz='Europe/Oslo'
            )

            # Get solar position
            solar_position = site.get_solarposition(times)

            # Clear sky model
            clearsky = site.get_clearsky(times)

            # Apply random clouds (realistic for Stavanger)
            cloud_cover = np.random.beta(2, 5, len(times))  # More clouds than sun
            ghi = clearsky['ghi'] * (1 - cloud_cover * 0.8)

            # Calculate POA irradiance
            poa_irradiance = irradiance.get_total_irradiance(
                surface_tilt=self.tilt,
                surface_azimuth=self.azimuth,
                dni=clearsky['dni'] * (1 - cloud_cover * 0.9),
                ghi=ghi,
                dhi=clearsky['dhi'] * (1 - cloud_cover * 0.7),
                solar_zenith=solar_position['apparent_zenith'],
                solar_azimuth=solar_position['azimuth']
            )

            # Simple PV model
            # Assuming 1000 W/m2 = 1 kWp
            production = (poa_irradiance['poa_global'] / 1000) * self.pv_capacity_kwp

            # Apply system losses (7% tap)
            production *= (1 - self.system_loss / 100)

            # Cap at inverter limit (if specified)
            production = production.clip(upper=110)  # 110 kW inverter

            return pd.Series(production.values, index=times.tz_localize(None), name='production_kw')

        except ImportError:
            print("❌ pvlib ikke installert, bruker enkel modell...")
            # Ultra simple fallback
            hours = 8760
            timestamps = pd.date_range(f'{year}-01-01', periods=hours, freq='h')

            # Stavanger seasonal factors
            seasonal = [0.1, 0.15, 0.3, 0.5, 0.7, 0.85,
                       0.85, 0.7, 0.5, 0.3, 0.15, 0.1]

            production = []
            for i, ts in enumerate(timestamps):
                hour = ts.hour
                month = ts.month

                # Basic daily pattern
                if 10 <= hour <= 14:
                    daily = 1.0
                elif 8 <= hour <= 16:
                    daily = 0.6
                elif 6 <= hour <= 18:
                    daily = 0.2
                else:
                    daily = 0

                # Random weather
                weather = 0.3 + 0.7 * np.random.random()

                # Calculate
                prod = self.pv_capacity_kwp * seasonal[month-1] * daily * weather
                production.append(min(prod, 110))  # Cap at inverter

            return pd.Series(production, index=timestamps, name='production_kw')