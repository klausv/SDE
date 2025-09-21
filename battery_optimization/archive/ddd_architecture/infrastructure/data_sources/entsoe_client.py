"""
ENTSO-E API client for fetching electricity spot prices
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd
import requests
from pathlib import Path
import pickle

from domain.value_objects.energy import EnergyPrice


logger = logging.getLogger(__name__)


class ENTSOEClient:
    """Client for ENTSO-E Transparency Platform API"""

    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[Path] = None):
        """
        Initialize ENTSO-E client

        Args:
            api_key: ENTSO-E API key (or from environment)
            cache_dir: Directory for caching data
        """
        self.api_key = api_key or os.getenv('ENTSOE_API_KEY')
        if not self.api_key:
            logger.warning("No ENTSO-E API key provided. Will use cached/simulated data.")

        self.base_url = "https://web-api.tp.entsoe.eu/api"
        self.cache_dir = cache_dir or Path('data/cache/entsoe')
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Area codes for Nordic countries
        self.area_codes = {
            'NO1': '10YNO-1--------2',  # Oslo
            'NO2': '10YNO-2--------T',  # Kristiansand
            'NO3': '10YNO-3--------J',  # Trondheim
            'NO4': '10YNO-4--------9',  # Tromsø
            'NO5': '10Y1001A1001A48H',  # Bergen
            'SE1': '10Y1001A1001A44P',  # Luleå
            'SE2': '10Y1001A1001A45N',  # Sundsvall
            'SE3': '10Y1001A1001A46L',  # Stockholm
            'SE4': '10Y1001A1001A47J',  # Malmö
            'DK1': '10YDK-1--------W',  # Jutland
            'DK2': '10YDK-2--------M',  # Zealand
        }

    def fetch_day_ahead_prices(
        self,
        start_date: datetime,
        end_date: datetime,
        bidding_zone: str = 'NO2',
        use_cache: bool = True
    ) -> pd.Series:
        """
        Fetch day-ahead electricity prices

        Args:
            start_date: Start of period
            end_date: End of period
            bidding_zone: Price area (e.g., 'NO2' for Stavanger)
            use_cache: Use cached data if available

        Returns:
            Series with hourly prices (EUR/MWh)
        """
        # Check cache first
        cache_key = f"prices_{bidding_zone}_{start_date.date()}_{end_date.date()}"
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        if use_cache and cache_file.exists():
            logger.info(f"Loading cached prices from {cache_file}")
            with open(cache_file, 'rb') as f:
                return pickle.load(f)

        if not self.api_key:
            logger.info("No API key - generating simulated prices")
            return self._generate_simulated_prices(start_date, end_date)

        # Fetch from API
        try:
            prices = self._fetch_from_api(start_date, end_date, bidding_zone)

            # Cache the results
            with open(cache_file, 'wb') as f:
                pickle.dump(prices, f)

            return prices

        except Exception as e:
            logger.error(f"Failed to fetch prices from ENTSO-E: {e}")
            logger.info("Falling back to simulated prices")
            return self._generate_simulated_prices(start_date, end_date)

    def _fetch_from_api(
        self,
        start_date: datetime,
        end_date: datetime,
        bidding_zone: str
    ) -> pd.Series:
        """Fetch prices from ENTSO-E API"""
        # Format dates for API
        start_str = start_date.strftime('%Y%m%d%H%M')
        end_str = end_date.strftime('%Y%m%d%H%M')

        params = {
            'securityToken': self.api_key,
            'documentType': 'A44',  # Day-ahead prices
            'in_Domain': self.area_codes[bidding_zone],
            'out_Domain': self.area_codes[bidding_zone],
            'periodStart': start_str,
            'periodEnd': end_str
        }

        response = requests.get(self.base_url, params=params)
        response.raise_for_status()

        # Parse XML response (simplified - real implementation would use xml parser)
        prices_data = self._parse_entsoe_xml(response.text)

        # Create time series
        date_range = pd.date_range(start=start_date, end=end_date, freq='h')
        prices = pd.Series(prices_data, index=date_range)

        return prices

    def _parse_entsoe_xml(self, xml_content: str) -> list:
        """Parse ENTSO-E XML response"""
        # Simplified parsing - real implementation would use proper XML parser
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_content)
        prices = []

        # Find all price points
        for timeseries in root.findall('.//{*}TimeSeries'):
            for period in timeseries.findall('.//{*}Period'):
                for point in period.findall('.//{*}Point'):
                    position = point.find('.//{*}position').text
                    price = float(point.find('.//{*}price.amount').text)
                    prices.append(price)

        return prices

    def _generate_simulated_prices(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.Series:
        """Generate realistic simulated electricity prices"""
        import numpy as np

        # Create hourly timestamps
        date_range = pd.date_range(start=start_date, end=end_date, freq='h')
        n_hours = len(date_range)

        # Base price pattern (EUR/MWh)
        base_price = 50  # Average price

        # Daily pattern (higher during day)
        daily_pattern = np.array([
            35, 35, 35, 35, 35, 40,  # 00-06: Night
            55, 65, 70, 65, 60, 55,  # 06-12: Morning peak
            50, 50, 55, 60, 65, 70,  # 12-18: Afternoon peak
            65, 55, 45, 40, 35, 35   # 18-24: Evening
        ])

        # Weekly pattern (lower on weekends)
        weekly_factors = np.array([
            1.1,   # Monday
            1.1,   # Tuesday
            1.1,   # Wednesday
            1.1,   # Thursday
            1.0,   # Friday
            0.8,   # Saturday
            0.7    # Sunday
        ])

        # Seasonal pattern (higher in winter)
        seasonal_factors = np.array([
            1.3,   # Jan
            1.25,  # Feb
            1.15,  # Mar
            1.0,   # Apr
            0.85,  # May
            0.8,   # Jun
            0.8,   # Jul
            0.85,  # Aug
            0.95,  # Sep
            1.05,  # Oct
            1.2,   # Nov
            1.3    # Dec
        ])

        prices = []
        for timestamp in date_range:
            hour_price = daily_pattern[timestamp.hour]
            week_factor = weekly_factors[timestamp.dayofweek]
            season_factor = seasonal_factors[timestamp.month - 1]

            # Add some randomness
            random_factor = 1 + np.random.normal(0, 0.15)

            price = hour_price * week_factor * season_factor * random_factor
            prices.append(max(0, price))  # Ensure non-negative

        return pd.Series(prices, index=date_range)

    def convert_to_nok(
        self,
        prices_eur: pd.Series,
        exchange_rate: float = 11.5
    ) -> pd.Series:
        """
        Convert prices from EUR/MWh to NOK/kWh

        Args:
            prices_eur: Prices in EUR/MWh
            exchange_rate: EUR to NOK exchange rate

        Returns:
            Prices in NOK/kWh
        """
        # Convert EUR/MWh to NOK/kWh
        prices_nok_per_kwh = (prices_eur * exchange_rate) / 1000
        return prices_nok_per_kwh

    def get_price_statistics(self, prices: pd.Series) -> Dict[str, float]:
        """Calculate price statistics"""
        return {
            'mean': prices.mean(),
            'median': prices.median(),
            'std': prices.std(),
            'min': prices.min(),
            'max': prices.max(),
            'p10': prices.quantile(0.1),
            'p90': prices.quantile(0.9)
        }

    def get_peak_hours_prices(
        self,
        prices: pd.Series,
        peak_hours: tuple = (6, 22),
        peak_days: list = [0, 1, 2, 3, 4]  # Monday-Friday
    ) -> pd.Series:
        """Extract prices during peak hours"""
        mask = (
            (prices.index.hour >= peak_hours[0]) &
            (prices.index.hour < peak_hours[1]) &
            (prices.index.dayofweek.isin(peak_days))
        )
        return prices[mask]

    def get_off_peak_prices(
        self,
        prices: pd.Series,
        peak_hours: tuple = (6, 22),
        peak_days: list = [0, 1, 2, 3, 4]
    ) -> pd.Series:
        """Extract prices during off-peak hours"""
        mask = (
            (prices.index.hour >= peak_hours[0]) &
            (prices.index.hour < peak_hours[1]) &
            (prices.index.dayofweek.isin(peak_days))
        )
        return prices[~mask]


class PriceForecaster:
    """Forecast future electricity prices"""

    def __init__(self, historical_prices: pd.Series):
        self.historical = historical_prices

    def forecast_next_year(
        self,
        inflation_rate: float = 0.02,
        volatility_increase: float = 1.1
    ) -> pd.Series:
        """
        Forecast prices for next year based on historical patterns

        Args:
            inflation_rate: Annual price increase
            volatility_increase: Factor for increased volatility

        Returns:
            Forecasted prices
        """
        # Use historical patterns with adjustments
        base_pattern = self.historical.groupby([
            self.historical.index.month,
            self.historical.index.dayofweek,
            self.historical.index.hour
        ]).mean()

        # Generate next year's timestamps
        start_date = self.historical.index[-1] + timedelta(hours=1)
        end_date = start_date + timedelta(days=365)
        future_index = pd.date_range(start=start_date, end=end_date, freq='h')

        forecasted = []
        for timestamp in future_index:
            # Get base price from pattern
            key = (timestamp.month, timestamp.dayofweek, timestamp.hour)
            if key in base_pattern.index:
                base_price = base_pattern[key]
            else:
                base_price = self.historical.mean()

            # Apply inflation
            inflated_price = base_price * (1 + inflation_rate)

            # Add volatility
            volatility = self.historical.std() * volatility_increase
            random_shock = np.random.normal(0, volatility)
            final_price = inflated_price + random_shock

            forecasted.append(max(0, final_price))

        return pd.Series(forecasted, index=future_index)