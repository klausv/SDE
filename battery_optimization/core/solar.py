"""
Solar system calculations - simplified
"""
import numpy as np
import pandas as pd
from typing import Optional


class SolarSystem:
    """Simple solar PV system model"""

    def __init__(
        self,
        pv_capacity_kwp: float = 138.55,
        inverter_limit_kw: float = 110,
        location: str = 'stavanger',
        tilt: float = 15,
        azimuth: float = 173
    ):
        self.pv_capacity_kwp = pv_capacity_kwp
        self.inverter_limit_kw = inverter_limit_kw
        self.location = location
        self.tilt = tilt
        self.azimuth = azimuth

    def generate_production(self, year: int = 2024) -> pd.Series:
        """
        Generate hourly solar production for a year
        Simplified model for Stavanger
        """
        hours = 8760
        timestamps = pd.date_range(f'{year}-01-01', periods=hours, freq='h')

        # Stavanger seasonal factors (59°N)
        seasonal_factors = [0.1, 0.2, 0.4, 0.7, 0.9, 1.0,
                           1.0, 0.9, 0.7, 0.4, 0.2, 0.1]  # Jan-Dec

        production = []
        for hour, timestamp in enumerate(timestamps):
            month = timestamp.month
            hour_of_day = timestamp.hour

            # Seasonal variation
            season_factor = seasonal_factors[month - 1]

            # Daily solar pattern
            if 10 <= hour_of_day <= 14:  # Peak hours
                daily_factor = 1.0
            elif 8 <= hour_of_day <= 16:  # Daylight
                daily_factor = 0.7
            elif 6 <= hour_of_day <= 18:  # Dawn/dusk
                daily_factor = 0.3
            else:  # Night
                daily_factor = 0

            # Weather variation
            weather_factor = 0.5 + 0.5 * np.random.random()

            # Calculate production
            production_kw = self.pv_capacity_kwp * season_factor * daily_factor * weather_factor
            production_kw = min(production_kw, self.inverter_limit_kw)

            production.append(production_kw)

        return pd.Series(production, index=timestamps, name='production_kw')

    def calculate_curtailment(
        self,
        production: pd.Series,
        grid_limit_kw: float = 70
    ) -> dict:
        """Calculate curtailed energy"""
        curtailment = (production - grid_limit_kw).clip(lower=0)

        return {
            'total_kwh': curtailment.sum(),
            'hours': (curtailment > 0).sum(),
            'percentage': (curtailment.sum() / production.sum()) * 100,
            'series': curtailment
        }