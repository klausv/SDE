"""
Price data loader with dataclass-based interface.

Provides unified API for loading electricity price data from multiple sources:
- CSV files (historical data)
- ENTSO-E API (live/recent data)
- Cached data

Handles price conversion (EUR/MWh → NOK/kWh) and timezone management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    """
    Container for electricity price time series data.

    Attributes:
        timestamps: DatetimeIndex with timestamps (timezone-naive, local time)
        prices_nok_per_kwh: Array of electricity prices in NOK/kWh
        source: Data source identifier ("file", "entsoe_api", "cache")
        currency: Original currency ("NOK" or "EUR")
        unit: Original unit ("kWh" or "MWh")
        area_code: Price area code (e.g., "NO2" for Southern Norway)
    """
    timestamps: pd.DatetimeIndex
    prices_nok_per_kwh: np.ndarray
    source: Literal["file", "entsoe_api", "cache"] = "file"
    currency: str = "NOK"
    unit: str = "kWh"
    area_code: str = "NO2"

    def __post_init__(self):
        """Validate data consistency."""
        if len(self.timestamps) != len(self.prices_nok_per_kwh):
            raise ValueError(
                f"Length mismatch: {len(self.timestamps)} timestamps vs "
                f"{len(self.prices_nok_per_kwh)} prices"
            )

        if len(self.timestamps) == 0:
            raise ValueError("Price data cannot be empty")

        # Ensure timezone-naive timestamps
        if self.timestamps.tz is not None:
            logger.warning("Converting timezone-aware timestamps to timezone-naive (local time)")
            self.timestamps = self.timestamps.tz_localize(None)

    def __len__(self) -> int:
        """Return number of price points."""
        return len(self.timestamps)

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert to pandas DataFrame.

        Returns:
            DataFrame with timestamp index and price column
        """
        return pd.DataFrame({
            'price_nok_kwh': self.prices_nok_per_kwh
        }, index=self.timestamps)

    def get_statistics(self) -> dict:
        """
        Get price statistics.

        Returns:
            Dictionary with min, max, mean, std, median prices
        """
        return {
            'min': float(np.min(self.prices_nok_per_kwh)),
            'max': float(np.max(self.prices_nok_per_kwh)),
            'mean': float(np.mean(self.prices_nok_per_kwh)),
            'std': float(np.std(self.prices_nok_per_kwh)),
            'median': float(np.median(self.prices_nok_per_kwh)),
            'count': len(self.prices_nok_per_kwh)
        }

    def filter_period(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> "PriceData":
        """
        Filter price data to specific time period.

        Args:
            start: Start datetime (inclusive). None means from beginning.
            end: End datetime (inclusive). None means to end.

        Returns:
            New PriceData with filtered data
        """
        mask = np.ones(len(self.timestamps), dtype=bool)

        if start is not None:
            mask &= self.timestamps >= start

        if end is not None:
            mask &= self.timestamps <= end

        if not mask.any():
            raise ValueError(f"No data in period [{start}, {end}]")

        return PriceData(
            timestamps=self.timestamps[mask],
            prices_nok_per_kwh=self.prices_nok_per_kwh[mask],
            source=self.source,
            currency=self.currency,
            unit=self.unit,
            area_code=self.area_code
        )


class PriceLoader:
    """
    Unified interface for loading electricity price data.

    Handles multiple data sources and price conversions.
    """

    def __init__(
        self,
        eur_to_nok: float = 11.5,
        default_area_code: str = "NO2"
    ):
        """
        Initialize price loader.

        Args:
            eur_to_nok: EUR to NOK exchange rate for conversions
            default_area_code: Default price area code
        """
        self.eur_to_nok = eur_to_nok
        self.default_area_code = default_area_code

    @staticmethod
    def convert_eur_mwh_to_nok_kwh(
        prices_eur_mwh: np.ndarray,
        eur_to_nok: float
    ) -> np.ndarray:
        """
        Convert prices from EUR/MWh to NOK/kWh.

        Args:
            prices_eur_mwh: Prices in EUR/MWh
            eur_to_nok: EUR to NOK exchange rate

        Returns:
            Prices in NOK/kWh

        Example:
            >>> prices_eur = np.array([50.0, 100.0])  # EUR/MWh
            >>> converted = PriceLoader.convert_eur_mwh_to_nok_kwh(prices_eur, 11.5)
            >>> converted
            array([0.575, 1.15])  # NOK/kWh
        """
        # EUR/MWh → NOK/MWh → NOK/kWh
        # 1 MWh = 1000 kWh
        prices_nok_mwh = prices_eur_mwh * eur_to_nok
        prices_nok_kwh = prices_nok_mwh / 1000.0
        return prices_nok_kwh

    def from_csv(
        self,
        file_path: str | Path,
        timestamp_col: str = "timestamp",
        price_col: str = "price",
        currency: str = "NOK",
        unit: str = "kWh"
    ) -> PriceData:
        """
        Load price data from CSV file.

        Expected CSV format:
        - timestamp column: datetime
        - price column: numeric (in specified currency/unit)

        Args:
            file_path: Path to CSV file
            timestamp_col: Name of timestamp column (default: "timestamp")
            price_col: Name of price column (default: "price")
            currency: Price currency ("NOK" or "EUR")
            unit: Price unit ("kWh" or "MWh")

        Returns:
            PriceData with loaded prices

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Price data file not found: {file_path}")

        logger.info(f"Loading price data from {file_path}")

        # Read CSV
        df = pd.read_csv(file_path)

        # Parse timestamp column
        if timestamp_col in df.columns:
            df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)
            df.set_index(timestamp_col, inplace=True)
        elif df.index.name == timestamp_col or isinstance(df.index, pd.DatetimeIndex):
            # Already has datetime index
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index, utc=True)
        else:
            # Try first column
            df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0], utc=True)
            df.set_index(df.columns[0], inplace=True)

        # Convert to Oslo time then remove timezone (timezone-naive local time)
        df.index = df.index.tz_convert('Europe/Oslo').tz_localize(None)

        # Remove duplicate timestamps (DST transitions)
        df = df[~df.index.duplicated(keep='first')]

        if df.empty:
            raise ValueError(f"Price data file is empty: {file_path}")

        # Get price column
        if price_col in df.columns:
            prices = df[price_col].values
        else:
            # Use first data column
            prices = df.iloc[:, 0].values

        # Convert if necessary
        if currency == "EUR" and unit == "MWh":
            prices = self.convert_eur_mwh_to_nok_kwh(prices, self.eur_to_nok)
            final_currency = "NOK"
            final_unit = "kWh"
        elif currency == "NOK" and unit == "MWh":
            prices = prices / 1000.0  # MWh → kWh
            final_currency = "NOK"
            final_unit = "kWh"
        else:
            final_currency = currency
            final_unit = unit

        timestamps = pd.DatetimeIndex(df.index)

        logger.info(f"Loaded {len(timestamps)} price points from {file_path}")

        return PriceData(
            timestamps=timestamps,
            prices_nok_per_kwh=prices,
            source="file",
            currency=final_currency,
            unit=final_unit,
            area_code=self.default_area_code
        )

    def from_entsoe_api(
        self,
        start_date: datetime,
        end_date: datetime,
        area_code: Optional[str] = None,
        api_key: Optional[str] = None,
        use_cache: bool = True
    ) -> PriceData:
        """
        Fetch price data from ENTSO-E API.

        Args:
            start_date: Start datetime
            end_date: End datetime
            area_code: Price area code (e.g., "NO2"). Uses default if None.
            api_key: ENTSO-E API key. Uses environment variable if None.
            use_cache: Whether to use cached data if available

        Returns:
            PriceData with fetched prices

        Raises:
            ImportError: If entsoe package not installed
            ValueError: If API key not provided
        """
        try:
            from .entsoe_client import ENTSOEClient
        except ImportError:
            raise ImportError(
                "entsoe package required for API access. "
                "Install with: pip install entsoe-py"
            )

        area = area_code or self.default_area_code

        logger.info(f"Fetching prices from ENTSO-E API for {area}: {start_date} to {end_date}")

        client = ENTSOEClient(api_key=api_key, area_code=area)
        prices_series = client.fetch_day_ahead_prices(
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache
        )

        # ENTSO-E returns EUR/MWh
        prices_nok_kwh = self.convert_eur_mwh_to_nok_kwh(
            prices_series.values,
            self.eur_to_nok
        )

        # Convert to timezone-naive local time
        timestamps = prices_series.index.tz_convert('Europe/Oslo').tz_localize(None)

        logger.info(f"Fetched {len(timestamps)} price points from ENTSO-E API")

        return PriceData(
            timestamps=pd.DatetimeIndex(timestamps),
            prices_nok_per_kwh=prices_nok_kwh,
            source="entsoe_api",
            currency="NOK",  # Converted
            unit="kWh",      # Converted
            area_code=area
        )
