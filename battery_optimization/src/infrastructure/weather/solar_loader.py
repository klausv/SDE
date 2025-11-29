"""
Solar production data loader with dataclass-based interface.

Provides unified API for loading solar production data from multiple sources:
- CSV files (historical production data)
- PVGIS API (solar radiation and production estimates)
- PVLib simulations
- Measured production data

Handles data processing, timezone management, and capacity scaling.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class SolarProductionData:
    """
    Container for solar PV production time series data.

    Attributes:
        timestamps: DatetimeIndex with timestamps (timezone-naive, local time)
        production_kw: Array of PV production in kW
        source: Data source identifier ("file", "pvgis_api", "pvlib", "measured")
        capacity_kwp: PV system capacity in kWp
        location: Location identifier (e.g., "Stavanger")
        latitude: Site latitude
        longitude: Site longitude
    """
    timestamps: pd.DatetimeIndex
    production_kw: np.ndarray
    source: Literal["file", "pvgis_api", "pvlib", "measured"] = "file"
    capacity_kwp: float = 150.0
    location: str = "Unknown"
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def __post_init__(self):
        """Validate data consistency."""
        if len(self.timestamps) != len(self.production_kw):
            raise ValueError(
                f"Length mismatch: {len(self.timestamps)} timestamps vs "
                f"{len(self.production_kw)} production values"
            )

        if len(self.timestamps) == 0:
            raise ValueError("Solar production data cannot be empty")

        # Ensure timezone-naive timestamps
        if self.timestamps.tz is not None:
            logger.warning("Converting timezone-aware timestamps to timezone-naive (local time)")
            self.timestamps = self.timestamps.tz_localize(None)

        # Validate production values (should be non-negative)
        if np.any(self.production_kw < 0):
            logger.warning("Found negative production values, clipping to zero")
            self.production_kw = np.maximum(self.production_kw, 0.0)

    def __len__(self) -> int:
        """Return number of production points."""
        return len(self.timestamps)

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert to pandas DataFrame.

        Returns:
            DataFrame with timestamp index and production column
        """
        return pd.DataFrame({
            'production_kw': self.production_kw
        }, index=self.timestamps)

    def get_statistics(self) -> dict:
        """
        Get production statistics.

        Returns:
            Dictionary with min, max, mean, annual production estimates
        """
        # Estimate timestep hours (assume hourly if not clear)
        if len(self.timestamps) > 1:
            timestep_hours = (self.timestamps[1] - self.timestamps[0]).total_seconds() / 3600
        else:
            timestep_hours = 1.0

        # Calculate annual production estimate
        total_kwh = np.sum(self.production_kw) * timestep_hours
        hours_in_data = len(self.production_kw) * timestep_hours
        hours_per_year = 8760
        annual_kwh_estimate = (total_kwh / hours_in_data) * hours_per_year if hours_in_data > 0 else 0

        return {
            'min_kw': float(np.min(self.production_kw)),
            'max_kw': float(np.max(self.production_kw)),
            'mean_kw': float(np.mean(self.production_kw)),
            'total_kwh': float(total_kwh),
            'annual_kwh_estimate': float(annual_kwh_estimate),
            'capacity_factor': float(annual_kwh_estimate / (self.capacity_kwp * hours_per_year)) if self.capacity_kwp > 0 else 0,
            'count': len(self.production_kw)
        }

    def scale_to_capacity(self, target_capacity_kwp: float) -> "SolarProductionData":
        """
        Scale production data to different PV capacity.

        Args:
            target_capacity_kwp: Target capacity in kWp

        Returns:
            New SolarProductionData with scaled production

        Example:
            >>> data_150kwp = loader.from_csv("production_150kwp.csv", capacity_kwp=150)
            >>> data_200kwp = data_150kwp.scale_to_capacity(200)
        """
        if self.capacity_kwp <= 0:
            raise ValueError("Cannot scale: current capacity is zero or negative")

        scaling_factor = target_capacity_kwp / self.capacity_kwp
        scaled_production = self.production_kw * scaling_factor

        logger.info(
            f"Scaling production from {self.capacity_kwp} kWp to {target_capacity_kwp} kWp "
            f"(factor: {scaling_factor:.3f})"
        )

        return SolarProductionData(
            timestamps=self.timestamps.copy(),
            production_kw=scaled_production,
            source=self.source,
            capacity_kwp=target_capacity_kwp,
            location=self.location,
            latitude=self.latitude,
            longitude=self.longitude
        )

    def filter_period(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> "SolarProductionData":
        """
        Filter production data to specific time period.

        Args:
            start: Start datetime (inclusive). None means from beginning.
            end: End datetime (inclusive). None means to end.

        Returns:
            New SolarProductionData with filtered data
        """
        mask = np.ones(len(self.timestamps), dtype=bool)

        if start is not None:
            mask &= self.timestamps >= start

        if end is not None:
            mask &= self.timestamps <= end

        if not mask.any():
            raise ValueError(f"No data in period [{start}, {end}]")

        return SolarProductionData(
            timestamps=self.timestamps[mask],
            production_kw=self.production_kw[mask],
            source=self.source,
            capacity_kwp=self.capacity_kwp,
            location=self.location,
            latitude=self.latitude,
            longitude=self.longitude
        )


class SolarProductionLoader:
    """
    Unified interface for loading solar production data.

    Handles multiple data sources and production scaling.
    """

    def __init__(
        self,
        default_capacity_kwp: float = 150.0,
        default_location: str = "Stavanger",
        default_latitude: float = 58.97,
        default_longitude: float = 5.73
    ):
        """
        Initialize solar production loader.

        Args:
            default_capacity_kwp: Default PV capacity for scaling
            default_location: Default location name
            default_latitude: Default site latitude
            default_longitude: Default site longitude
        """
        self.default_capacity_kwp = default_capacity_kwp
        self.default_location = default_location
        self.default_latitude = default_latitude
        self.default_longitude = default_longitude

    def from_csv(
        self,
        file_path: str | Path,
        timestamp_col: str = "timestamp",
        production_col: str = "production",
        capacity_kwp: Optional[float] = None,
        location: Optional[str] = None,
        year_shift_to: Optional[int] = None
    ) -> SolarProductionData:
        """
        Load solar production data from CSV file.

        Expected CSV format:
        - timestamp column: datetime
        - production column: numeric (kW)

        Args:
            file_path: Path to CSV file
            timestamp_col: Name of timestamp column (default: "timestamp")
            production_col: Name of production column (default: "production")
            capacity_kwp: PV capacity in kWp (uses default if None)
            location: Location name (uses default if None)
            year_shift_to: If specified, shifts all timestamps to this year (useful for PVGIS data)

        Returns:
            SolarProductionData with loaded production

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Production data file not found: {file_path}")

        logger.info(f"Loading solar production from {file_path}")

        # Read CSV
        try:
            df = pd.read_csv(file_path, parse_dates=[0], index_col=0)
        except Exception as e:
            raise ValueError(f"Failed to read production data from {file_path}: {e}")

        if df.empty:
            raise ValueError(f"Production data file is empty: {file_path}")

        # Get production column
        if production_col in df.columns:
            production = df[production_col].values
        else:
            # Use first data column
            production = df.iloc[:, 0].values

        timestamps = pd.DatetimeIndex(df.index)

        # Year shift if requested (common for PVGIS data)
        if year_shift_to is not None and timestamps[0].year != year_shift_to:
            year_diff = year_shift_to - timestamps[0].year
            timestamps = timestamps + pd.DateOffset(years=year_diff)
            logger.info(f"Shifted timestamps from year {timestamps[0].year - year_diff} to {year_shift_to}")

        # Resample to hourly if needed (PVGIS sometimes has :11 minute offset)
        if len(timestamps) > 1:
            time_diff = (timestamps[1] - timestamps[0]).total_seconds() / 60  # minutes
            if time_diff < 58 or time_diff > 62:  # Not hourly
                logger.info("Resampling to hourly resolution")
                df.index = timestamps
                df_hourly = df.resample('h').mean()
                timestamps = pd.DatetimeIndex(df_hourly.index)
                if production_col in df.columns:
                    production = df_hourly[production_col].values
                else:
                    production = df_hourly.iloc[:, 0].values

        capacity = capacity_kwp if capacity_kwp is not None else self.default_capacity_kwp
        loc = location if location is not None else self.default_location

        logger.info(
            f"Loaded {len(timestamps)} production points from {file_path} "
            f"(capacity: {capacity} kWp)"
        )

        return SolarProductionData(
            timestamps=timestamps,
            production_kw=production,
            source="file",
            capacity_kwp=capacity,
            location=loc,
            latitude=self.default_latitude,
            longitude=self.default_longitude
        )

    def from_pvgis_api(
        self,
        latitude: float,
        longitude: float,
        capacity_kwp: float,
        tilt: float = 30.0,
        azimuth: float = 180.0,
        year: int = 2024
    ) -> SolarProductionData:
        """
        Fetch solar production data from PVGIS API.

        Args:
            latitude: Site latitude
            longitude: Site longitude
            capacity_kwp: PV capacity in kWp
            tilt: Panel tilt angle in degrees (default: 30)
            azimuth: Panel azimuth in degrees, 180=south (default: 180)
            year: Year to shift timestamps to (default: 2024)

        Returns:
            SolarProductionData with PVGIS hourly production

        Raises:
            ImportError: If pvlib not installed
            Exception: If API request fails

        Note:
            Requires internet connection and pvlib package
        """
        try:
            from pvlib.iotools import get_pvgis_hourly
        except ImportError:
            raise ImportError(
                "pvlib package required for PVGIS API access. "
                "Install with: pip install pvlib"
            )

        logger.info(
            f"Fetching PVGIS data for lat={latitude}, lon={longitude}, "
            f"capacity={capacity_kwp} kWp"
        )

        try:
            # Fetch typical meteorological year (TMY) data from PVGIS
            data, metadata, inputs = get_pvgis_hourly(
                latitude=latitude,
                longitude=longitude,
                surface_tilt=tilt,
                surface_azimuth=azimuth,
                pvcalculation=True,
                peakpower=capacity_kwp,
                loss=14,  # System losses (%)
                optimalangles=False
            )

            # Extract production (W → kW)
            production_kw = data['P'].values / 1000.0

            # Get timestamps and shift to requested year
            timestamps = data.index
            if timestamps[0].year != year:
                year_diff = year - timestamps[0].year
                timestamps = timestamps + pd.DateOffset(years=year_diff)

            # Convert to timezone-naive
            if timestamps.tz is not None:
                timestamps = timestamps.tz_localize(None)

            logger.info(f"Fetched {len(timestamps)} hourly production values from PVGIS")

            return SolarProductionData(
                timestamps=pd.DatetimeIndex(timestamps),
                production_kw=production_kw,
                source="pvgis_api",
                capacity_kwp=capacity_kwp,
                location=f"Lat{latitude}_Lon{longitude}",
                latitude=latitude,
                longitude=longitude
            )

        except Exception as e:
            logger.error(f"Error fetching PVGIS data: {e}")
            raise
