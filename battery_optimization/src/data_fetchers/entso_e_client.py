"""
ENTSO-E API client for fetching day-ahead electricity prices for NO2 (Southern Norway)
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple
import pytz
from entsoe import EntsoePandasClient
import logging
from pathlib import Path
import pickle

logger = logging.getLogger(__name__)

class ENTSOEClient:
    """Client for fetching electricity prices from ENTSO-E Transparency Platform"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ENTSO-E client

        Args:
            api_key: ENTSO-E API key. If not provided, looks for ENTSOE_API_KEY in environment
        """
        self.api_key = api_key or os.getenv('ENTSOE_API_KEY')
        if not self.api_key:
            raise ValueError(
                "ENTSO-E API key not provided. "
                "Please set ENTSOE_API_KEY environment variable or pass api_key parameter"
            )

        self.client = EntsoePandasClient(api_key=self.api_key)
        self.area_code = 'NO_2'  # Southern Norway
        self.tz = pytz.timezone('Europe/Oslo')
        self.cache_dir = Path('data/spot_prices')
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_day_ahead_prices(
        self,
        start_date: datetime,
        end_date: datetime,
        use_cache: bool = True
    ) -> pd.Series:
        """
        Fetch day-ahead prices for NO2 area

        Args:
            start_date: Start date (timezone-aware or naive, will be converted to Oslo time)
            end_date: End date (timezone-aware or naive, will be converted to Oslo time)
            use_cache: Whether to use cached data if available

        Returns:
            pd.Series with hourly prices in EUR/MWh, indexed by timestamp
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
            with open(cache_file, 'rb') as f:
                return pickle.load(f)

        try:
            logger.info(f"Fetching prices from ENTSO-E for {start_date} to {end_date}")
            prices = self.client.query_day_ahead_prices(
                self.area_code,
                start=start_date,
                end=end_date
            )

            # Save to cache
            with open(cache_file, 'wb') as f:
                pickle.dump(prices, f)

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
        Fetch day-ahead prices for an entire year

        Args:
            year: Year to fetch prices for
            use_cache: Whether to use cached data if available

        Returns:
            pd.Series with hourly prices in EUR/MWh
        """
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31, 23, 59, 59)

        return self.fetch_day_ahead_prices(start_date, end_date, use_cache)

    def convert_to_nok_per_kwh(
        self,
        prices_eur_mwh: pd.Series,
        eur_to_nok: float = 11.5
    ) -> pd.Series:
        """
        Convert prices from EUR/MWh to NOK/kWh

        Args:
            prices_eur_mwh: Prices in EUR/MWh
            eur_to_nok: EUR to NOK exchange rate

        Returns:
            pd.Series with prices in NOK/kWh
        """
        return prices_eur_mwh * eur_to_nok / 1000

    def get_price_statistics(
        self,
        prices: pd.Series,
        period: str = 'monthly'
    ) -> pd.DataFrame:
        """
        Calculate price statistics for given period

        Args:
            prices: Price series
            period: 'monthly', 'quarterly', or 'yearly'

        Returns:
            DataFrame with statistics (mean, std, min, max, percentiles)
        """
        if period == 'monthly':
            grouper = pd.Grouper(freq='M')
        elif period == 'quarterly':
            grouper = pd.Grouper(freq='Q')
        elif period == 'yearly':
            grouper = pd.Grouper(freq='Y')
        else:
            raise ValueError(f"Invalid period: {period}")

        grouped = prices.groupby(grouper)

        stats = pd.DataFrame({
            'mean': grouped.mean(),
            'std': grouped.std(),
            'min': grouped.min(),
            'max': grouped.max(),
            'p25': grouped.quantile(0.25),
            'p50': grouped.quantile(0.50),
            'p75': grouped.quantile(0.75),
            'p90': grouped.quantile(0.90),
            'volatility': grouped.std() / grouped.mean()  # Coefficient of variation
        })

        return stats

    def identify_price_patterns(
        self,
        prices: pd.Series
    ) -> pd.DataFrame:
        """
        Identify typical price patterns (hourly, daily, seasonal)

        Args:
            prices: Price series

        Returns:
            DataFrame with pattern analysis
        """
        df = pd.DataFrame({'price': prices})
        df['hour'] = df.index.hour
        df['day_of_week'] = df.index.dayofweek
        df['month'] = df.index.month
        df['is_weekend'] = df['day_of_week'] >= 5

        # Hourly pattern
        hourly_pattern = df.groupby('hour')['price'].agg(['mean', 'std'])

        # Weekday vs weekend
        weekend_pattern = df.groupby('is_weekend')['price'].agg(['mean', 'std'])

        # Monthly pattern
        monthly_pattern = df.groupby('month')['price'].agg(['mean', 'std'])

        return {
            'hourly': hourly_pattern,
            'weekend': weekend_pattern,
            'monthly': monthly_pattern
        }

    def _get_cache_filename(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Path:
        """Generate cache filename based on date range"""
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        return self.cache_dir / f"NO2_prices_{start_str}_{end_str}.pkl"


def create_sample_env_file():
    """Create a sample .env file for ENTSO-E API configuration"""
    env_content = """# ENTSO-E Transparency Platform API Configuration
# Get your API key from: https://transparency.entsoe.eu/
# 1. Register for free account
# 2. Login and go to "My Account Settings"
# 3. Generate security token
# 4. Copy token here:

ENTSOE_API_KEY=your_api_key_here
"""

    env_file = Path('.env')
    if not env_file.exists():
        with open(env_file, 'w') as f:
            f.write(env_content)
        print(f"Created sample .env file. Please add your ENTSO-E API key.")
    else:
        print(".env file already exists")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Create sample .env if needed
    create_sample_env_file()

    # Example of how to use the client (requires valid API key)
    try:
        client = ENTSOEClient()

        # Fetch prices for a specific date range
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 7)

        prices_eur = client.fetch_day_ahead_prices(start, end)
        prices_nok = client.convert_to_nok_per_kwh(prices_eur)

        print(f"Average price (NOK/kWh): {prices_nok.mean():.3f}")
        print(f"Max price (NOK/kWh): {prices_nok.max():.3f}")
        print(f"Min price (NOK/kWh): {prices_nok.min():.3f}")

    except ValueError as e:
        print(f"Please configure your ENTSO-E API key: {e}")