"""
PVGIS API client for fetching solar production data
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import requests
from pathlib import Path
import json

from domain.value_objects.energy import Energy, Power
from domain.models.solar_system import PVSystemSpecification


logger = logging.getLogger(__name__)


class PVGISClient:
    """Client for PVGIS (Photovoltaic Geographical Information System) API"""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize PVGIS client

        Args:
            cache_dir: Directory for caching data
        """
        self.base_url = "https://re.jrc.ec.europa.eu/api/v5_2"
        self.cache_dir = cache_dir or Path('data/cache/pvgis')
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_hourly_production(
        self,
        latitude: float,
        longitude: float,
        pv_system: PVSystemSpecification,
        year: int = 2019,  # PVGIS typical meteorological year
        use_cache: bool = True
    ) -> pd.Series:
        """
        Fetch hourly PV production data from PVGIS

        Args:
            latitude: Site latitude
            longitude: Site longitude
            pv_system: PV system specifications
            year: Year for data (PVGIS uses typical years)
            use_cache: Use cached data if available

        Returns:
            Series with hourly production (kW)
        """
        # Check cache
        cache_key = f"pvgis_{latitude:.2f}_{longitude:.2f}_{pv_system.installed_capacity.kw:.0f}_{year}"
        cache_file = self.cache_dir / f"{cache_key}.json"

        if use_cache and cache_file.exists():
            logger.info(f"Loading cached PVGIS data from {cache_file}")
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return pd.Series(data['values'], index=pd.to_datetime(data['index']))

        # Fetch from PVGIS
        try:
            production = self._fetch_from_api(latitude, longitude, pv_system, year)

            # Cache the results
            if use_cache:
                cache_data = {
                    'values': production.tolist(),
                    'index': production.index.strftime('%Y-%m-%d %H:%M:%S').tolist()
                }
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f)

            return production

        except Exception as e:
            logger.error(f"Failed to fetch from PVGIS: {e}")
            logger.info("Generating synthetic production data")
            return self._generate_synthetic_production(pv_system, year)

    def _fetch_from_api(
        self,
        latitude: float,
        longitude: float,
        pv_system: PVSystemSpecification,
        year: int
    ) -> pd.Series:
        """Fetch production data from PVGIS API"""
        # PVGIS API parameters
        params = {
            'lat': latitude,
            'lon': longitude,
            'peakpower': pv_system.installed_capacity.kw,
            'pvtechchoice': 'crystSi',  # Crystalline silicon
            'mountingplace': 'building',  # Building integrated
            'loss': int((1 - pv_system.total_system_efficiency) * 100),  # System losses in %
            'fixed': 1,  # Fixed mounting
            'angle': pv_system.tilt,  # Tilt angle
            'aspect': pv_system.azimuth - 180,  # Azimuth (0 = south in PVGIS)
            'startyear': year,
            'endyear': year,
            'outputformat': 'json',
            'browser': 0
        }

        # API endpoint for hourly data
        endpoint = f"{self.base_url}/seriescalc"

        response = requests.get(endpoint, params=params)
        response.raise_for_status()

        data = response.json()

        # Extract hourly data
        hourly_data = data['outputs']['hourly']

        # Create time series
        production = []
        timestamps = []

        for entry in hourly_data:
            # PVGIS provides time in format "YYYYMMDD:HHMM"
            time_str = entry['time']
            year_str = time_str[:4]
            month_str = time_str[4:6]
            day_str = time_str[6:8]
            hour_str = time_str[9:11]
            minute_str = time_str[11:13]

            timestamp = pd.Timestamp(f"{year_str}-{month_str}-{day_str} {hour_str}:{minute_str}")
            timestamps.append(timestamp)

            # P is the PV production in W
            production_w = entry.get('P', 0)
            production.append(production_w / 1000)  # Convert to kW

        return pd.Series(production, index=timestamps)

    def fetch_monthly_averages(
        self,
        latitude: float,
        longitude: float,
        pv_system: PVSystemSpecification,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch monthly average production from PVGIS

        Returns:
            DataFrame with monthly statistics
        """
        cache_key = f"pvgis_monthly_{latitude:.2f}_{longitude:.2f}_{pv_system.installed_capacity.kw:.0f}"
        cache_file = self.cache_dir / f"{cache_key}.json"

        if use_cache and cache_file.exists():
            logger.info(f"Loading cached monthly data from {cache_file}")
            return pd.read_json(cache_file)

        # PVGIS monthly API
        params = {
            'lat': latitude,
            'lon': longitude,
            'peakpower': pv_system.installed_capacity.kw,
            'pvtechchoice': 'crystSi',
            'mountingplace': 'building',
            'loss': int((1 - pv_system.total_system_efficiency) * 100),
            'fixed': 1,
            'angle': pv_system.tilt,
            'aspect': pv_system.azimuth - 180,
            'outputformat': 'json'
        }

        endpoint = f"{self.base_url}/PVcalc"

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()

            data = response.json()
            monthly_data = data['outputs']['monthly']['fixed']

            # Convert to DataFrame
            df = pd.DataFrame(monthly_data)

            if use_cache:
                df.to_json(cache_file)

            return df

        except Exception as e:
            logger.error(f"Failed to fetch monthly data: {e}")
            return self._generate_synthetic_monthly_data(pv_system)

    def get_optimal_angles(
        self,
        latitude: float,
        longitude: float,
        use_cache: bool = True
    ) -> Dict[str, float]:
        """
        Get optimal tilt and azimuth angles for location

        Returns:
            Dictionary with optimal angles
        """
        cache_key = f"optimal_angles_{latitude:.2f}_{longitude:.2f}"
        cache_file = self.cache_dir / f"{cache_key}.json"

        if use_cache and cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)

        # PVGIS optimization API
        params = {
            'lat': latitude,
            'lon': longitude,
            'peakpower': 1,  # 1 kW for normalized results
            'pvtechchoice': 'crystSi',
            'mountingplace': 'free',
            'optimalangles': 1,
            'outputformat': 'json'
        }

        endpoint = f"{self.base_url}/PVcalc"

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()

            data = response.json()
            optimal = {
                'tilt': data['outputs']['optimization']['fixed']['angle'],
                'azimuth': data['outputs']['optimization']['fixed']['azimuth']
            }

            if use_cache:
                with open(cache_file, 'w') as f:
                    json.dump(optimal, f)

            return optimal

        except Exception as e:
            logger.error(f"Failed to get optimal angles: {e}")
            # Return reasonable defaults for Norway
            return {'tilt': 40.0, 'azimuth': 180.0}

    def get_irradiance_data(
        self,
        latitude: float,
        longitude: float,
        year: int = 2019,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Get hourly irradiance data (GHI, DNI, DHI)

        Returns:
            DataFrame with irradiance components
        """
        cache_key = f"irradiance_{latitude:.2f}_{longitude:.2f}_{year}"
        cache_file = self.cache_dir / f"{cache_key}.json"

        if use_cache and cache_file.exists():
            logger.info(f"Loading cached irradiance data from {cache_file}")
            return pd.read_json(cache_file)

        # PVGIS TMY API for irradiance
        params = {
            'lat': latitude,
            'lon': longitude,
            'startyear': 2005,
            'endyear': 2016,
            'outputformat': 'json'
        }

        endpoint = f"{self.base_url}/tmy"

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()

            data = response.json()
            hourly_data = data['outputs']['tmy_hourly']

            # Extract irradiance components
            records = []
            for entry in hourly_data:
                records.append({
                    'time': entry['time(UTC)'],
                    'ghi': entry.get('G(h)', 0),  # Global horizontal
                    'dni': entry.get('Gb(n)', 0),  # Direct normal
                    'dhi': entry.get('Gd(h)', 0),  # Diffuse horizontal
                    'temperature': entry.get('T2m', 15)  # 2m temperature
                })

            df = pd.DataFrame(records)
            df['time'] = pd.to_datetime(df['time'], format='%Y%m%d:%H%M')
            df.set_index('time', inplace=True)

            if use_cache:
                df.to_json(cache_file)

            return df

        except Exception as e:
            logger.error(f"Failed to fetch irradiance data: {e}")
            return self._generate_synthetic_irradiance(year)

    def _generate_synthetic_production(
        self,
        pv_system: PVSystemSpecification,
        year: int
    ) -> pd.Series:
        """Generate synthetic production data"""
        import numpy as np

        # Create hourly timestamps
        start = pd.Timestamp(f'{year}-01-01')
        end = pd.Timestamp(f'{year}-12-31 23:00:00')
        timestamps = pd.date_range(start=start, end=end, freq='h')

        production = []
        for ts in timestamps:
            hour = ts.hour
            month = ts.month

            # Seasonal factor (lower in winter for Norway)
            seasonal_factors = [0.3, 0.4, 0.6, 0.8, 1.0, 1.1,
                                1.1, 1.0, 0.8, 0.6, 0.4, 0.3]
            season_factor = seasonal_factors[month - 1]

            # Daily pattern
            if 6 <= hour <= 18:
                sun_angle = np.sin(np.pi * (hour - 6) / 12)
                daily_factor = sun_angle * season_factor
            else:
                daily_factor = 0

            # Random clouds
            cloud_factor = 0.7 + 0.3 * np.random.random()

            # Calculate production
            hourly_production = (
                pv_system.installed_capacity.kw *
                daily_factor *
                cloud_factor *
                pv_system.total_system_efficiency
            )

            production.append(max(0, hourly_production))

        return pd.Series(production, index=timestamps)

    def _generate_synthetic_monthly_data(
        self,
        pv_system: PVSystemSpecification
    ) -> pd.DataFrame:
        """Generate synthetic monthly production data"""
        months = range(1, 13)
        monthly_yields = [200, 300, 500, 700, 900, 950,
                          950, 850, 650, 450, 250, 150]  # kWh/kWp

        data = []
        for month, yield_per_kwp in zip(months, monthly_yields):
            data.append({
                'month': month,
                'E_m': yield_per_kwp * pv_system.installed_capacity.kw,  # Monthly energy
                'H_sun': yield_per_kwp / 30,  # Daily irradiation
                'SD_m': yield_per_kwp * 0.1  # Standard deviation
            })

        return pd.DataFrame(data)

    def _generate_synthetic_irradiance(self, year: int) -> pd.DataFrame:
        """Generate synthetic irradiance data"""
        import numpy as np

        start = pd.Timestamp(f'{year}-01-01')
        end = pd.Timestamp(f'{year}-12-31 23:00:00')
        timestamps = pd.date_range(start=start, end=end, freq='h')

        data = []
        for ts in timestamps:
            hour = ts.hour
            month = ts.month
            day = ts.dayofyear

            # Solar elevation angle (simplified)
            latitude_rad = np.radians(59)  # Stavanger latitude
            declination = 23.45 * np.sin(np.radians(360 * (284 + day) / 365))
            hour_angle = 15 * (hour - 12)
            elevation = np.arcsin(
                np.sin(np.radians(declination)) * np.sin(latitude_rad) +
                np.cos(np.radians(declination)) * np.cos(latitude_rad) *
                np.cos(np.radians(hour_angle))
            )

            if elevation > 0:
                # Maximum clear-sky irradiance
                ghi_clear = 900 * np.sin(elevation)

                # Cloud factor
                cloud_factor = 0.6 + 0.4 * np.random.random()

                ghi = ghi_clear * cloud_factor
                dni = ghi * 0.7  # Simplified
                dhi = ghi * 0.3

                # Temperature model
                temp_base = 10 + 5 * np.sin(2 * np.pi * day / 365 - np.pi / 2)
                temp = temp_base + 5 * np.sin(np.pi * hour / 12)
            else:
                ghi = dni = dhi = 0
                temp = 5 + 3 * np.sin(2 * np.pi * day / 365 - np.pi / 2)

            data.append({
                'ghi': max(0, ghi),
                'dni': max(0, dni),
                'dhi': max(0, dhi),
                'temperature': temp
            })

        return pd.DataFrame(data, index=timestamps)