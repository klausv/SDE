"""
Data manager for battery optimization simulations.

Provides high-level interface for loading, windowing, and managing time-series data.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple
import pandas as pd
import numpy as np

from src.config.simulation_config import SimulationConfig
from .file_loaders import (
    load_price_data,
    load_production_data,
    load_consumption_data,
    resample_timeseries,
    align_timeseries,
    detect_resolution,
)


@dataclass
class TimeSeriesData:
    """
    Container for aligned time-series data.

    All arrays have the same length and correspond to timestamps.
    """
    timestamps: pd.DatetimeIndex
    prices_nok_per_kwh: np.ndarray
    pv_production_kw: np.ndarray
    consumption_kw: np.ndarray
    resolution: str  # 'PT60M' or 'PT15M'

    def __post_init__(self):
        """Validate data consistency."""
        n = len(self.timestamps)
        if len(self.prices_nok_per_kwh) != n:
            raise ValueError("prices_nok_per_kwh length doesn't match timestamps")
        if len(self.pv_production_kw) != n:
            raise ValueError("pv_production_kw length doesn't match timestamps")
        if len(self.consumption_kw) != n:
            raise ValueError("consumption_kw length doesn't match timestamps")

    def __len__(self) -> int:
        """Return number of time steps."""
        return len(self.timestamps)

    def get_window(
        self,
        start: datetime,
        hours: int,
        allow_partial: bool = False
    ) -> "TimeSeriesData":
        """
        Extract time window from data.

        Args:
            start: Start datetime
            hours: Number of hours to include
            allow_partial: If False, raise error for incomplete windows (default: False)

        Returns:
            New TimeSeriesData with windowed data

        Raises:
            ValueError: If window is outside data range or incomplete (when allow_partial=False)
        """
        end = start + timedelta(hours=hours)

        # Find indices within window
        mask = (self.timestamps >= start) & (self.timestamps < end)

        if not mask.any():
            raise ValueError(
                f"No data in window [{start}, {end}). "
                f"Data range: [{self.timestamps[0]}, {self.timestamps[-1]}]"
            )

        # C2 Fix: Validate window completeness
        actual_timesteps = mask.sum()

        # Calculate expected timesteps based on resolution
        if self.resolution == 'PT60M':
            expected_timesteps = hours
        elif self.resolution == 'PT15M':
            expected_timesteps = hours * 4
        else:
            # For other resolutions, parse the ISO 8601 duration
            if self.resolution.startswith('PT') and self.resolution.endswith('M'):
                minutes = int(self.resolution[2:-1])
                expected_timesteps = int(hours * 60 / minutes)
            else:
                # Unknown resolution - skip validation
                expected_timesteps = actual_timesteps

        # Check if window is complete
        if actual_timesteps < expected_timesteps and not allow_partial:
            raise ValueError(
                f"Incomplete window: expected {expected_timesteps} timesteps "
                f"for {hours}h at {self.resolution} resolution, but got {actual_timesteps}. "
                f"Window [{start}, {end}) extends beyond available data "
                f"[{self.timestamps[0]}, {self.timestamps[-1]}]. "
                f"Set allow_partial=True to allow incomplete windows."
            )

        return TimeSeriesData(
            timestamps=self.timestamps[mask],
            prices_nok_per_kwh=self.prices_nok_per_kwh[mask],
            pv_production_kw=self.pv_production_kw[mask],
            consumption_kw=self.consumption_kw[mask],
            resolution=self.resolution,
        )

    def get_month(self, year: int, month: int) -> "TimeSeriesData":
        """
        Extract data for specific month.

        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)

        Returns:
            New TimeSeriesData with month's data

        Raises:
            ValueError: If no data for specified month
        """
        mask = (self.timestamps.year == year) & (self.timestamps.month == month)

        if not mask.any():
            raise ValueError(f"No data for {year}-{month:02d}")

        return TimeSeriesData(
            timestamps=self.timestamps[mask],
            prices_nok_per_kwh=self.prices_nok_per_kwh[mask],
            pv_production_kw=self.pv_production_kw[mask],
            consumption_kw=self.consumption_kw[mask],
            resolution=self.resolution,
        )

    def get_week(self, year: int, week: int) -> "TimeSeriesData":
        """
        Extract data for specific ISO week.

        Args:
            year: Year (e.g., 2024)
            week: ISO week number (1-53)

        Returns:
            New TimeSeriesData with week's data

        Raises:
            ValueError: If no data for specified week
        """
        mask = (self.timestamps.isocalendar().year == year) & \
               (self.timestamps.isocalendar().week == week)

        if not mask.any():
            raise ValueError(f"No data for {year}-W{week:02d}")

        return TimeSeriesData(
            timestamps=self.timestamps[mask],
            prices_nok_per_kwh=self.prices_nok_per_kwh[mask],
            pv_production_kw=self.pv_production_kw[mask],
            consumption_kw=self.consumption_kw[mask],
            resolution=self.resolution,
        )

    def resample_to(
        self,
        target_resolution: str,
        price_method: str = "mean",
        production_method: str = "mean",
        consumption_method: str = "mean"
    ) -> "TimeSeriesData":
        """
        Resample data to different time resolution.

        Args:
            target_resolution: Target resolution ('PT60M', 'PT15M', etc.)
            price_method: Resampling method for prices (default: 'mean')
            production_method: Resampling method for production (default: 'mean')
            consumption_method: Resampling method for consumption (default: 'mean')

        Returns:
            New TimeSeriesData with resampled data
        """
        if target_resolution == self.resolution:
            return self  # No resampling needed

        timestamps_price, prices = resample_timeseries(
            self.timestamps, self.prices_nok_per_kwh, target_resolution, price_method
        )
        timestamps_prod, production = resample_timeseries(
            self.timestamps, self.pv_production_kw, target_resolution, production_method
        )
        timestamps_cons, consumption = resample_timeseries(
            self.timestamps, self.consumption_kw, target_resolution, consumption_method
        )

        # Align to common timestamps (should be same, but safeguard)
        common_timestamps, aligned_values = align_timeseries(
            [timestamps_price, timestamps_prod, timestamps_cons],
            [prices, production, consumption]
        )

        return TimeSeriesData(
            timestamps=common_timestamps,
            prices_nok_per_kwh=aligned_values[0],
            pv_production_kw=aligned_values[1],
            consumption_kw=aligned_values[2],
            resolution=target_resolution,
        )

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert to pandas DataFrame.

        Returns:
            DataFrame with all time series data
        """
        return pd.DataFrame({
            'timestamp': self.timestamps,
            'price_nok_per_kwh': self.prices_nok_per_kwh,
            'pv_production_kw': self.pv_production_kw,
            'consumption_kw': self.consumption_kw,
        }).set_index('timestamp')

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        price_col: str = 'price_nok_per_kwh',
        production_col: str = 'pv_production_kw',
        consumption_col: str = 'consumption_kw',
        resolution: Optional[str] = None
    ) -> "TimeSeriesData":
        """
        Create TimeSeriesData from pandas DataFrame.

        Args:
            df: DataFrame with DatetimeIndex and data columns
            price_col: Column name for prices (default: 'price_nok_per_kwh')
            production_col: Column name for PV production (default: 'pv_production_kw')
            consumption_col: Column name for consumption (default: 'consumption_kw')
            resolution: Time resolution ('PT60M', 'PT15M', etc.). Auto-detected if None.

        Returns:
            TimeSeriesData instance

        Raises:
            ValueError: If DataFrame doesn't have DatetimeIndex or required columns

        Example:
            >>> df = pd.read_csv('data.csv', index_col=0, parse_dates=True)
            >>> data = TimeSeriesData.from_dataframe(df)
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame must have DatetimeIndex")

        if price_col not in df.columns:
            raise ValueError(f"Price column '{price_col}' not found in DataFrame")
        if production_col not in df.columns:
            raise ValueError(f"Production column '{production_col}' not found in DataFrame")
        if consumption_col not in df.columns:
            raise ValueError(f"Consumption column '{consumption_col}' not found in DataFrame")

        timestamps = df.index

        # Auto-detect resolution if not provided
        if resolution is None:
            resolution = detect_resolution(timestamps)

        return cls(
            timestamps=timestamps,
            prices_nok_per_kwh=df[price_col].values,
            pv_production_kw=df[production_col].values,
            consumption_kw=df[consumption_col].values,
            resolution=resolution,
        )

    @classmethod
    def from_arrays(
        cls,
        timestamps: pd.DatetimeIndex,
        prices: np.ndarray,
        production: np.ndarray,
        consumption: np.ndarray,
        resolution: Optional[str] = None
    ) -> "TimeSeriesData":
        """
        Create TimeSeriesData from numpy arrays.

        Args:
            timestamps: DatetimeIndex with timestamps
            prices: Array of electricity prices [NOK/kWh]
            production: Array of PV production [kW]
            consumption: Array of consumption [kW]
            resolution: Time resolution ('PT60M', 'PT15M', etc.). Auto-detected if None.

        Returns:
            TimeSeriesData instance

        Raises:
            ValueError: If arrays have different lengths

        Example:
            >>> timestamps = pd.date_range('2024-01-01', periods=24, freq='h')
            >>> prices = np.random.uniform(0.5, 1.5, 24)
            >>> production = np.random.uniform(0, 100, 24)
            >>> consumption = np.random.uniform(20, 50, 24)
            >>> data = TimeSeriesData.from_arrays(timestamps, prices, production, consumption)
        """
        if not isinstance(timestamps, pd.DatetimeIndex):
            timestamps = pd.DatetimeIndex(timestamps)

        # Auto-detect resolution if not provided
        if resolution is None:
            resolution = detect_resolution(timestamps)

        return cls(
            timestamps=timestamps,
            prices_nok_per_kwh=prices,
            pv_production_kw=production,
            consumption_kw=consumption,
            resolution=resolution,
        )


class DataManager:
    """
    High-level data management for battery optimization.

    Handles loading, validation, resampling, and windowing of input data.
    """

    def __init__(
        self,
        config: SimulationConfig,
        data: Optional[TimeSeriesData] = None
    ):
        """
        Initialize DataManager with configuration.

        Args:
            config: Simulation configuration
            data: Optional pre-loaded TimeSeriesData (for programmatic usage)
        """
        self.config = config
        self._data: Optional[TimeSeriesData] = data

    def load_data(self) -> TimeSeriesData:
        """
        Load all input data from files specified in configuration.

        If data was provided directly in __init__, returns that data
        (after filtering/resampling if needed).

        Returns:
            TimeSeriesData with all loaded and aligned data

        Raises:
            FileNotFoundError: If any data file is missing
            ValueError: If data cannot be loaded or aligned
        """
        # If data already provided, use it
        if self._data is not None:
            data = self._data
        else:
            # Load individual data series from files
            timestamps_price, prices = load_price_data(
                self.config.data_sources.prices_file
            )
            timestamps_prod, production = load_production_data(
                self.config.data_sources.production_file
            )
            timestamps_cons, consumption = load_consumption_data(
                self.config.data_sources.consumption_file
            )

            # Detect resolution from timestamps
            detected_resolution = detect_resolution(timestamps_price)

            # Align all time series to common timestamps
            common_timestamps, aligned_values = align_timeseries(
                [timestamps_price, timestamps_prod, timestamps_cons],
                [prices, production, consumption]
            )

            # Create TimeSeriesData
            data = TimeSeriesData(
                timestamps=common_timestamps,
                prices_nok_per_kwh=aligned_values[0],
                pv_production_kw=aligned_values[1],
                consumption_kw=aligned_values[2],
                resolution=detected_resolution,
            )

        # Resample if needed
        if data.resolution != self.config.time_resolution:
            data = data.resample_to(self.config.time_resolution)

        # Filter to simulation period if specified
        start = self.config.simulation_period.get_start_datetime()
        end = self.config.simulation_period.get_end_datetime()
        mask = (data.timestamps >= start) & (data.timestamps <= end)
        data = TimeSeriesData(
            timestamps=data.timestamps[mask],
            prices_nok_per_kwh=data.prices_nok_per_kwh[mask],
            pv_production_kw=data.pv_production_kw[mask],
            consumption_kw=data.consumption_kw[mask],
            resolution=data.resolution,
        )

        self._data = data
        return data

    def get_data(self) -> TimeSeriesData:
        """
        Get loaded data (loads if not already loaded).

        Returns:
            TimeSeriesData with all data

        Raises:
            RuntimeError: If data has not been loaded
        """
        if self._data is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")
        return self._data

    def get_window(self, start: datetime, hours: int) -> TimeSeriesData:
        """
        Get time window from loaded data.

        Args:
            start: Start datetime
            hours: Number of hours to include

        Returns:
            TimeSeriesData with windowed data

        Raises:
            RuntimeError: If data has not been loaded
            ValueError: If window is outside data range
        """
        data = self.get_data()
        return data.get_window(start, hours)

    def get_month(self, year: int, month: int) -> TimeSeriesData:
        """
        Get data for specific month.

        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)

        Returns:
            TimeSeriesData with month's data

        Raises:
            RuntimeError: If data has not been loaded
            ValueError: If no data for specified month
        """
        data = self.get_data()
        return data.get_month(year, month)

    def get_week(self, year: int, week: int) -> TimeSeriesData:
        """
        Get data for specific ISO week.

        Args:
            year: Year (e.g., 2024)
            week: ISO week number (1-53)

        Returns:
            TimeSeriesData with week's data

        Raises:
            RuntimeError: If data has not been loaded
            ValueError: If no data for specified week
        """
        data = self.get_data()
        return data.get_week(year, week)

    def get_date_range(self) -> Tuple[datetime, datetime]:
        """
        Get date range of loaded data.

        Returns:
            Tuple of (start_datetime, end_datetime)

        Raises:
            RuntimeError: If data has not been loaded
        """
        data = self.get_data()
        return data.timestamps[0].to_pydatetime(), data.timestamps[-1].to_pydatetime()

    def summary(self) -> dict:
        """
        Get summary statistics of loaded data.

        Returns:
            Dictionary with summary statistics

        Raises:
            RuntimeError: If data has not been loaded
        """
        data = self.get_data()

        return {
            'start_date': data.timestamps[0].isoformat(),
            'end_date': data.timestamps[-1].isoformat(),
            'num_timesteps': len(data),
            'resolution': data.resolution,
            'price_stats': {
                'min': float(np.min(data.prices_nok_per_kwh)),
                'max': float(np.max(data.prices_nok_per_kwh)),
                'mean': float(np.mean(data.prices_nok_per_kwh)),
                'std': float(np.std(data.prices_nok_per_kwh)),
            },
            'production_stats': {
                'min': float(np.min(data.pv_production_kw)),
                'max': float(np.max(data.pv_production_kw)),
                'mean': float(np.mean(data.pv_production_kw)),
                'total_kwh': float(np.sum(data.pv_production_kw) *
                                   (1.0 if data.resolution == 'PT60M' else 0.25)),
            },
            'consumption_stats': {
                'min': float(np.min(data.consumption_kw)),
                'max': float(np.max(data.consumption_kw)),
                'mean': float(np.mean(data.consumption_kw)),
                'total_kwh': float(np.sum(data.consumption_kw) *
                                   (1.0 if data.resolution == 'PT60M' else 0.25)),
            },
        }
