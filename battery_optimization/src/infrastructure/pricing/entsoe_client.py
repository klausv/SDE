"""
ENTSO-E API client for fetching electricity price data.

Modernized client with caching, error handling, and clean interface.
"""

import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional
import pytz
import logging
import pickle

logger = logging.getLogger(__name__)


class ENTSOEClient:
    """
    Client for fetching electricity prices from ENTSO-E Transparency Platform.

    Provides cached access to day-ahead market prices for Norwegian price areas.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        area_code: str = "NO_2",
        cache_dir: Optional[str | Path] = None
    ):
        """
        Initialize ENTSO-E client.

        Args:
            api_key: ENTSO-E API key. If None, reads from ENTSOE_API_KEY environment variable.
            area_code: Price area code (default: "NO_2" for Southern Norway)
            cache_dir: Directory for caching API responses (default: data/spot_prices)

        Raises:
            ValueError: If API key not provided and not in environment
            ImportError: If entsoe-py package not installed
        """
        # Get API key
        self.api_key = api_key or os.getenv('ENTSOE_API_KEY')
        if not self.api_key:
            raise ValueError(
                "ENTSO-E API key not provided. "
                "Set ENTSOE_API_KEY environment variable or pass api_key parameter."
            )

        # Initialize client
        try:
            from entsoe import EntsoePandasClient
            self.client = EntsoePandasClient(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "entsoe-py package required for ENTSO-E API access. "
                "Install with: pip install entsoe-py"
            )

        self.area_code = area_code
        self.tz = pytz.timezone('Europe/Oslo')

        # Setup cache
        if cache_dir is None:
            cache_dir = Path('data/spot_prices')
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_filename(self, start_date: datetime, end_date: datetime) -> Path:
        """
        Generate cache filename for given date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Path to cache file
        """
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        filename = f"{self.area_code}_{start_str}_{end_str}_prices.pkl"
        return self.cache_dir / filename

    def fetch_day_ahead_prices(
        self,
        start_date: datetime,
        end_date: datetime,
        use_cache: bool = True
    ) -> pd.Series:
        """
        Fetch day-ahead prices for configured area.

        Args:
            start_date: Start datetime (timezone-aware or naive, converted to Oslo time)
            end_date: End datetime (timezone-aware or naive, converted to Oslo time)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            pd.Series with hourly prices in EUR/MWh, indexed by timestamp (timezone-aware)

        Raises:
            Exception: If API request fails
        """
        # Convert to Oslo timezone if needed
        if start_date.tzinfo is None:
            start_date = self.tz.localize(start_date)
        else:
            start_date = start_date.astimezone(self.tz)

        if end_date.tzinfo is None:
            end_date = self.tz.localize(end_date)
        else:
            end_date = end_date.astimezone(self.tz)

        # Check cache first
        cache_file = self._get_cache_filename(start_date, end_date)
        if use_cache and cache_file.exists():
            logger.info(f"Loading cached prices from {cache_file}")
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache file {cache_file}: {e}")
                # Continue to API fetch

        # Fetch from API
        try:
            logger.info(f"Fetching prices from ENTSO-E for {self.area_code}: {start_date} to {end_date}")
            prices = self.client.query_day_ahead_prices(
                self.area_code,
                start=start_date,
                end=end_date
            )

            # Save to cache
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(prices, f)
                logger.debug(f"Saved prices to cache: {cache_file}")
            except Exception as e:
                logger.warning(f"Failed to save cache file {cache_file}: {e}")

            return prices

        except Exception as e:
            logger.error(f"Error fetching prices from ENTSO-E: {e}")
            raise

    def fetch_year_prices(
        self,
        year: int,
        use_cache: bool = True
    ) -> pd.Series:
        """
        Fetch day-ahead prices for an entire year.

        Args:
            year: Year to fetch (e.g., 2024)
            use_cache: Whether to use cached data

        Returns:
            pd.Series with hourly prices for the year

        Example:
            >>> client = ENTSOEClient()
            >>> prices_2024 = client.fetch_year_prices(2024)
        """
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31, 23, 59, 59)

        return self.fetch_day_ahead_prices(
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache
        )

    def fetch_month_prices(
        self,
        year: int,
        month: int,
        use_cache: bool = True
    ) -> pd.Series:
        """
        Fetch day-ahead prices for a specific month.

        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)
            use_cache: Whether to use cached data

        Returns:
            pd.Series with hourly prices for the month

        Example:
            >>> client = ENTSOEClient()
            >>> prices_jan = client.fetch_month_prices(2024, 1)
        """
        from calendar import monthrange

        start_date = datetime(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = datetime(year, month, last_day, 23, 59, 59)

        return self.fetch_day_ahead_prices(
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache
        )

    def clear_cache(self):
        """
        Clear all cached price data.

        Removes all .pkl files from the cache directory.
        """
        if not self.cache_dir.exists():
            return

        cache_files = list(self.cache_dir.glob('*.pkl'))
        for cache_file in cache_files:
            try:
                cache_file.unlink()
                logger.debug(f"Deleted cache file: {cache_file}")
            except Exception as e:
                logger.warning(f"Failed to delete cache file {cache_file}: {e}")

        logger.info(f"Cleared {len(cache_files)} cache files")

    def get_cache_info(self) -> dict:
        """
        Get information about cached data.

        Returns:
            Dictionary with cache statistics
        """
        if not self.cache_dir.exists():
            return {
                'cache_dir': str(self.cache_dir),
                'exists': False,
                'num_files': 0,
                'total_size_mb': 0.0
            }

        cache_files = list(self.cache_dir.glob('*.pkl'))
        total_size = sum(f.stat().st_size for f in cache_files)

        return {
            'cache_dir': str(self.cache_dir),
            'exists': True,
            'num_files': len(cache_files),
            'total_size_mb': total_size / (1024 * 1024),
            'files': [f.name for f in cache_files]
        }
