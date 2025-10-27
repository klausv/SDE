"""
PV production model for solar installation in Stavanger
Uses pvlib for detailed solar modeling
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple
try:
    from pvlib import location
    from pvlib.temperature import sapm_cell
    from pvlib.irradiance import get_total_irradiance
    PVLIB_AVAILABLE = True
except ImportError:
    PVLIB_AVAILABLE = False
import pytz
import logging
from pathlib import Path
import pickle

logger = logging.getLogger(__name__)

class SolarProductionModel:
    """Model for simulating PV production with oversizing and inverter clipping"""

    def __init__(
        self,
        pv_capacity_kwp: float = 150.0,
        inverter_capacity_kw: float = 110.0,
        latitude: float = 58.97,
        longitude: float = 5.73,
        tilt: float = 25.0,
        azimuth: float = 180.0,
        altitude: float = 10.0
    ):
        """
        Initialize solar production model

        Args:
            pv_capacity_kwp: PV array capacity in kWp
            inverter_capacity_kw: Inverter AC capacity in kW
            latitude: Site latitude
            longitude: Site longitude
            tilt: Panel tilt angle (degrees from horizontal)
            azimuth: Panel azimuth (degrees, 180 = south)
            altitude: Site altitude above sea level (m)
        """
        self.pv_capacity_kwp = pv_capacity_kwp
        self.inverter_capacity_kw = inverter_capacity_kw
        self.oversizing_ratio = pv_capacity_kwp / inverter_capacity_kw

        # Location setup
        self.location = location.Location(
            latitude=latitude,
            longitude=longitude,
            tz='Europe/Oslo',
            altitude=altitude,
            name='Stavanger'
        )

        # Panel configuration (using typical commercial panels)
        self.panels_per_string = 25  # Example configuration
        self.strings_per_inverter = 24  # To reach 150 kWp
        self.panel_capacity = 250  # Wp per panel (example)

        # Temperature model parameters (SAPM open rack glass polymer)
        self.temperature_model_parameters = {'a': -3.47, 'b': -0.0594, 'deltaT': 3}

        # System losses
        self.system_losses = {
            'soiling': 0.02,  # 2% soiling losses
            'shading': 0.03,  # 3% shading losses
            'snow': 0.02,  # 2% snow losses (annual average)
            'mismatch': 0.02,  # 2% mismatch losses
            'wiring': 0.02,  # 2% DC wiring losses
            'connections': 0.005,  # 0.5% connection losses
            'availability': 0.03,  # 3% availability losses
        }
        self.total_loss_factor = 1 - sum(self.system_losses.values())

        # Cache directory
        self.cache_dir = Path('data/pv_profiles')
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def calculate_hourly_production(
        self,
        start_date: datetime,
        end_date: datetime,
        use_cache: bool = True
    ) -> pd.Series:
        """
        Calculate hourly PV production for given period

        Args:
            start_date: Start date
            end_date: End date
            use_cache: Whether to use cached data if available

        Returns:
            pd.Series with hourly production in kW
        """
        # Check cache
        cache_file = self._get_cache_filename(start_date, end_date)
        if use_cache and cache_file.exists():
            logger.info(f"Loading cached PV production from {cache_file}")
            with open(cache_file, 'rb') as f:
                return pickle.load(f)

        # Generate hourly timestamps
        times = pd.date_range(
            start=start_date,
            end=end_date,
            freq='H',
            tz=self.location.tz
        )

        # Get solar position
        solar_position = self.location.get_solarposition(times)

        # Get clear-sky irradiance
        clearsky = self.location.get_clearsky(times)

        # Calculate POA (Plane of Array) irradiance
        poa_irradiance = get_total_irradiance(
            surface_tilt=self.tilt,
            surface_azimuth=self.azimuth,
            dni=clearsky['dni'],
            ghi=clearsky['ghi'],
            dhi=clearsky['dhi'],
            solar_zenith=solar_position['apparent_zenith'],
            solar_azimuth=solar_position['azimuth']
        )

        # Apply typical weather variability (simplified model)
        # In production, this should use actual weather data
        weather_factor = self._apply_weather_variability(times)

        # Calculate DC power output
        dc_power = self._calculate_dc_power(
            poa_irradiance['poa_global'] * weather_factor,
            cell_temperature=self._estimate_cell_temperature(
                poa_irradiance['poa_global'],
                times
            )
        )

        # Apply system losses
        dc_power_after_losses = dc_power * self.total_loss_factor

        # Apply inverter clipping
        ac_power = np.minimum(dc_power_after_losses, self.inverter_capacity_kw)

        # Create series
        production = pd.Series(ac_power, index=times)

        # Save to cache
        with open(cache_file, 'wb') as f:
            pickle.dump(production, f)

        return production

    def _calculate_dc_power(
        self,
        poa_irradiance: pd.Series,
        cell_temperature: pd.Series
    ) -> np.ndarray:
        """
        Calculate DC power output from irradiance

        Args:
            poa_irradiance: Plane of array irradiance (W/m²)
            cell_temperature: Cell temperature (°C)

        Returns:
            DC power in kW
        """
        # Simple model: linear with irradiance, adjusted for temperature
        # Temperature coefficient: -0.4%/°C (typical for silicon)
        temp_coefficient = -0.004
        reference_temp = 25  # °C

        # Temperature derating
        temp_factor = 1 + temp_coefficient * (cell_temperature - reference_temp)

        # Power calculation (simplified)
        # Assuming 1000 W/m² = rated power at STC
        dc_power = (poa_irradiance / 1000) * self.pv_capacity_kwp * temp_factor

        # Ensure non-negative
        dc_power = np.maximum(dc_power, 0)

        return dc_power

    def _estimate_cell_temperature(
        self,
        poa_irradiance: pd.Series,
        times: pd.DatetimeIndex
    ) -> pd.Series:
        """
        Estimate cell temperature based on ambient and irradiance

        Args:
            poa_irradiance: Plane of array irradiance (W/m²)
            times: Timestamps

        Returns:
            Cell temperature in °C
        """
        # Simplified ambient temperature model for Stavanger
        # Monthly average temperatures (°C)
        monthly_temps = {
            1: 2, 2: 2, 3: 4, 4: 7, 5: 11, 6: 14,
            7: 16, 8: 16, 9: 13, 10: 9, 11: 5, 12: 3
        }

        # Get ambient temperature based on month
        ambient_temp = pd.Series(
            [monthly_temps[t.month] + 5 * np.sin((t.hour - 6) * np.pi / 12)
             for t in times],
            index=times
        )

        # NOCT model for cell temperature
        # NOCT = 45°C (typical), irradiance at NOCT = 800 W/m²
        noct = 45
        irradiance_noct = 800
        ambient_noct = 20

        cell_temp = ambient_temp + (noct - ambient_noct) * (poa_irradiance / irradiance_noct)

        return cell_temp

    def _apply_weather_variability(
        self,
        times: pd.DatetimeIndex
    ) -> pd.Series:
        """
        Apply realistic weather variability to clear-sky model

        Args:
            times: Timestamps

        Returns:
            Weather factor (0-1)
        """
        # Simplified weather model for Stavanger
        # Monthly cloud cover factors (rough approximation)
        monthly_factors = {
            1: 0.3, 2: 0.35, 3: 0.45, 4: 0.55, 5: 0.6, 6: 0.65,
            7: 0.65, 8: 0.6, 9: 0.5, 10: 0.4, 11: 0.3, 12: 0.25
        }

        # Base weather factor
        weather_factor = pd.Series(
            [monthly_factors[t.month] for t in times],
            index=times
        )

        # Add daily variability
        np.random.seed(42)  # For reproducibility
        daily_variation = np.random.normal(0, 0.15, len(times))
        weather_factor = weather_factor * (1 + daily_variation)

        # Clip to realistic range
        weather_factor = weather_factor.clip(0.0, 1.0)

        return weather_factor

    def calculate_annual_production(
        self,
        year: int,
        use_cache: bool = True
    ) -> Tuple[pd.Series, dict]:
        """
        Calculate annual PV production with statistics

        Args:
            year: Year to calculate
            use_cache: Whether to use cached data

        Returns:
            Tuple of (hourly production series, statistics dict)
        """
        start_date = datetime(year, 1, 1, 0, 0, tzinfo=pytz.timezone('Europe/Oslo'))
        end_date = datetime(year, 12, 31, 23, 0, tzinfo=pytz.timezone('Europe/Oslo'))

        production = self.calculate_hourly_production(start_date, end_date, use_cache)

        # Calculate statistics
        stats = {
            'total_production_mwh': production.sum() / 1000,
            'capacity_factor': production.mean() / self.pv_capacity_kwp,
            'max_output_kw': production.max(),
            'hours_at_inverter_limit': (production >= self.inverter_capacity_kw * 0.99).sum(),
            'clipping_loss_mwh': self._estimate_clipping_loss(production) / 1000,
            'monthly_production_mwh': production.resample('M').sum() / 1000,
        }

        return production, stats

    def _estimate_clipping_loss(
        self,
        production: pd.Series
    ) -> float:
        """
        Estimate energy lost due to inverter clipping

        Args:
            production: AC production series

        Returns:
            Estimated clipping loss in kWh
        """
        # Simplified estimation: when at inverter limit, assume 10% additional potential
        hours_clipped = production >= self.inverter_capacity_kw * 0.99
        estimated_loss = hours_clipped.sum() * self.inverter_capacity_kw * 0.1

        return estimated_loss

    def _get_cache_filename(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Path:
        """Generate cache filename based on date range and system config"""
        config_hash = f"{self.pv_capacity_kwp}_{self.inverter_capacity_kw}_{self.tilt}_{self.azimuth}"
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        return self.cache_dir / f"pv_production_{config_hash}_{start_str}_{end_str}.pkl"


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Initialize model with Stavanger system specs
    model = SolarProductionModel(
        pv_capacity_kwp=150,
        inverter_capacity_kw=110,
        latitude=58.97,
        longitude=5.73,
        tilt=15,
        azimuth=180
    )

    # Calculate production for a sample period
    start = datetime(2024, 6, 1, tzinfo=pytz.timezone('Europe/Oslo'))
    end = datetime(2024, 6, 7, tzinfo=pytz.timezone('Europe/Oslo'))

    production = model.calculate_hourly_production(start, end)

    print(f"Total production (kWh): {production.sum():.1f}")
    print(f"Average production (kW): {production.mean():.1f}")
    print(f"Max production (kW): {production.max():.1f}")
    print(f"Capacity factor: {production.mean() / 150:.2%}")