"""
Unified ENTSO-E Price Fetching Module

Consolidates functionality from:
- entso_e_prices.py (cache management, metadata, user-friendly output)
- fetch_real_prices.py (working XML parsing, month-by-month fetching)

This module fetches real day-ahead electricity prices from ENTSO-E Transparency Platform
for Norwegian bidding zones (NO1-NO5).
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import xml.etree.ElementTree as ET
import json
from pathlib import Path
from typing import Optional, Dict, Tuple


class ENTSOEPriceFetcher:
    """
    Unified price fetcher for ENTSO-E Transparency Platform

    Features:
    - Real XML parsing from ENTSO-E API
    - Month-by-month fetching to avoid API limits
    - Intelligent caching with metadata
    - EUR/MWh → NOK/kWh conversion
    - UTC → Europe/Oslo timezone conversion
    - Fallback to simulated data if API fails
    """

    # ENTSO-E domain codes for Norwegian bidding zones
    DOMAIN_CODES = {
        'NO1': '10YNO-1--------2',  # Oslo
        'NO2': '10YNO-2--------T',  # Kristiansand (incl. Stavanger)
        'NO3': '10YNO-3--------J',  # Trondheim
        'NO4': '10YNO-4--------9',  # Tromsø
        'NO5': '10Y1001A1001A48H',  # Bergen
    }

    # XML namespace for ENTSO-E responses
    XML_NAMESPACE = {'ns': 'urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3'}

    # Default EUR/NOK exchange rate (TODO: make configurable or fetch dynamically)
    DEFAULT_EUR_NOK_RATE = 11.5

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        eur_nok_rate: float = DEFAULT_EUR_NOK_RATE
    ):
        """
        Initialize price fetcher

        Args:
            api_key: ENTSO-E API key (if None, reads from ENTSOE_API_KEY env var)
            cache_dir: Directory for caching data (default: data/spot_prices)
            eur_nok_rate: EUR/NOK exchange rate for conversion
        """
        self.api_key = api_key or os.getenv('ENTSOE_API_KEY')
        self.cache_dir = cache_dir or Path('data/spot_prices')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / 'cache_metadata.json'
        self.eur_nok_rate = eur_nok_rate
        self.api_url = "https://web-api.tp.entsoe.eu/api"

    def fetch_prices(
        self,
        year: int,
        area: str = 'NO2',
        refresh: bool = False,
        use_fallback: bool = True
    ) -> pd.Series:
        """
        Fetch day-ahead electricity prices for a specific year and area

        Args:
            year: Year to fetch prices for (e.g., 2023)
            area: Bidding zone code (NO1-NO5)
            refresh: If True, fetch fresh data even if cache exists
            use_fallback: If True, generate simulated data if API fails

        Returns:
            pandas Series with hourly prices (NOK/kWh) indexed by timestamp (Europe/Oslo)

        Raises:
            ValueError: If API key missing and fallback disabled
            RuntimeError: If API fails and fallback disabled
        """
        cache_file = self.cache_dir / f"{area}_{year}_real.csv"

        # Show cached data info
        self._show_cached_data_info()

        # Check cache (unless refresh requested)
        if cache_file.exists() and not refresh:
            return self._load_from_cache(cache_file, area, year)

        # Fetch fresh data
        if refresh:
            print(f"🔄 Refreshing prices for {area} {year}...")
        else:
            print(f"📡 No cache found for {area} {year}, fetching from API...")

        # Validate API key
        if not self.api_key:
            if use_fallback:
                print("⚠️ ENTSOE_API_KEY not set - using simulated data")
                return self._generate_fallback_prices(year, area)
            else:
                raise ValueError(
                    "ENTSOE_API_KEY required for real data fetching. "
                    "Set environment variable or disable fallback."
                )

        # Fetch from API
        try:
            prices = self._fetch_from_api(year, area)
            self._save_to_cache(prices, cache_file, area, year, source='ENTSO-E API')
            self._print_statistics(prices, year)
            return prices

        except Exception as e:
            print(f"⚠️ API fetch failed: {e}")

            if use_fallback:
                print("📊 Falling back to simulated data...")
                return self._generate_fallback_prices(year, area)
            else:
                raise RuntimeError(f"API fetch failed and fallback disabled: {e}")

    def _fetch_from_api(self, year: int, area: str) -> pd.Series:
        """Fetch prices from ENTSO-E API with month-by-month requests"""

        domain = self.DOMAIN_CODES.get(area)
        if not domain:
            raise ValueError(f"Unknown area code: {area}. Valid: {list(self.DOMAIN_CODES.keys())}")

        print(f"🌐 Fetching {area} prices for {year} from ENTSO-E API...")

        all_prices = []

        # Fetch month by month to avoid API limits
        for month in range(1, 13):
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)

            params = {
                'securityToken': self.api_key,
                'documentType': 'A44',  # Day-ahead prices
                'in_Domain': domain,
                'out_Domain': domain,
                'periodStart': start_date.strftime('%Y%m%d%H%M'),
                'periodEnd': (end_date - timedelta(hours=1)).strftime('%Y%m%d%H%M')
            }

            print(f"  Fetching {start_date.strftime('%B %Y')}...")

            response = requests.get(self.api_url, params=params, timeout=30)

            if response.status_code != 200:
                print(f"  ⚠️ Error {response.status_code}: {response.text[:200]}")
                continue

            # Parse XML response
            month_prices = self._parse_xml_response(response.content)
            all_prices.extend(month_prices)

        if not all_prices:
            raise RuntimeError("No data received from API for any month")

        # Create DataFrame
        df = pd.DataFrame(all_prices)
        df.set_index('timestamp', inplace=True)
        df = df.sort_index()

        # Remove duplicates (keep first occurrence)
        df = df[~df.index.duplicated(keep='first')]

        # Resample to ensure hourly data and interpolate small gaps
        df = df.resample('h').mean().interpolate(limit=3)

        print(f"✅ Fetched {len(df)} hours of data")

        return df['price_nok']

    def _parse_xml_response(self, xml_content: bytes) -> list:
        """Parse ENTSO-E XML response and extract prices"""

        root = ET.fromstring(xml_content)
        prices = []

        for timeseries in root.findall('.//ns:TimeSeries', self.XML_NAMESPACE):
            period = timeseries.find('.//ns:Period', self.XML_NAMESPACE)
            if period is None:
                continue

            # Get start time and resolution
            start_elem = period.find('ns:timeInterval/ns:start', self.XML_NAMESPACE)
            if start_elem is None:
                continue

            start_text = start_elem.text
            start_time = pd.Timestamp(start_text[:-1], tz='UTC')  # Remove 'Z'

            # Extract price points
            points = period.findall('ns:Point', self.XML_NAMESPACE)

            for point in points:
                position_elem = point.find('ns:position', self.XML_NAMESPACE)
                price_elem = point.find('ns:price.amount', self.XML_NAMESPACE)

                if position_elem is None or price_elem is None:
                    continue

                position = int(position_elem.text)
                price_eur_mwh = float(price_elem.text)

                # Calculate timestamp (position is 1-indexed)
                timestamp = start_time + pd.Timedelta(hours=position - 1)

                # Convert EUR/MWh to NOK/kWh
                price_nok_kwh = price_eur_mwh * self.eur_nok_rate / 1000

                prices.append({
                    'timestamp': timestamp.tz_convert('Europe/Oslo'),
                    'price_nok': price_nok_kwh
                })

        return prices

    def _generate_fallback_prices(self, year: int, area: str) -> pd.Series:
        """
        Generate realistic simulated prices based on NO2 patterns

        Only used when API is unavailable or API key not set.
        For production use, always use real ENTSO-E data.
        """
        print(f"📊 Generating simulated prices for {area} {year}...")
        print("⚠️ WARNING: Using simulated data - not real market prices!")

        # Create hourly timestamp index with correct timezone
        times = pd.date_range(
            f'{year}-01-01',
            f'{year}-12-31 23:00',
            freq='h',
            tz='Europe/Oslo'
        )

        prices = []
        for ts in times:
            month = ts.month
            hour = ts.hour
            weekday = ts.weekday()

            # Seasonal base price (based on typical NO2 patterns)
            if month in [12, 1, 2]:  # Winter - higher demand
                base = 0.90
            elif month in [6, 7, 8]:  # Summer - lower demand
                base = 0.40
            elif month in [3, 4, 5]:  # Spring - moderate with renewables
                base = 0.60
            else:  # Autumn
                base = 0.70

            # Hourly pattern
            if 7 <= hour <= 9 or 17 <= hour <= 20:  # Peak hours
                hour_factor = 1.4
            elif 10 <= hour <= 16:  # Day
                hour_factor = 1.1
            elif 23 <= hour or hour <= 5:  # Night
                hour_factor = 0.7
            else:
                hour_factor = 1.0

            # Weekday effect
            day_factor = 1.1 if weekday < 5 else 0.9

            # Random market variation
            random_factor = np.random.normal(1.0, 0.15)
            random_factor = np.clip(random_factor, 0.6, 1.4)

            # Calculate price
            price = base * hour_factor * day_factor * random_factor

            # Occasional spikes (1% chance)
            if np.random.random() < 0.01:
                price *= np.random.uniform(2.0, 2.5)

            # Occasional negative prices in spring/summer (simulate renewable oversupply)
            if month in [5, 6] and 11 <= hour <= 14 and np.random.random() < 0.02:
                price = -np.random.uniform(0.001, 0.05)

            # Realistic bounds
            price = np.clip(price, -0.1, 3.0)

            prices.append(price)

        series = pd.Series(prices, index=times, name='price_nok')

        # Save to cache
        cache_file = self.cache_dir / f"{area}_{year}_real.csv"
        self._save_to_cache(series, cache_file, area, year, source='Simulated')

        self._print_statistics(series, year)

        return series

    def _load_from_cache(self, cache_file: Path, area: str, year: int) -> pd.Series:
        """Load prices from cache file"""

        metadata = self._get_cache_metadata(area, year)

        print(f"📁 Loading cached prices: {cache_file.name}")
        if metadata:
            print(f"   • Source: {metadata.get('source', 'Unknown')}")
            print(f"   • Fetched: {metadata.get('fetched_date', 'Unknown')}")

        data = pd.read_csv(cache_file, index_col=0, parse_dates=True)

        # Ensure index is DatetimeIndex (pd.read_csv may return generic Index)
        if not isinstance(data.index, pd.DatetimeIndex):
            # Use utc=True to handle timezone-aware strings properly
            data.index = pd.to_datetime(data.index, utc=True).tz_convert('Europe/Oslo')

        # Ensure timezone aware - handle ambiguous times during DST transitions
        elif data.index.tz is None:
            # Use 'NaT' for ambiguous/nonexistent times (DST transitions)
            # This handles both spring forward (nonexistent hour) and fall back (ambiguous hour)
            try:
                data.index = data.index.tz_localize('Europe/Oslo', ambiguous='NaT', nonexistent='NaT')
                # Drop any NaT values created by DST issues
                data = data[data.index.notna()]
            except Exception:
                # If all else fails, just mark as UTC and convert
                data.index = data.index.tz_localize('UTC').tz_convert('Europe/Oslo')

        series = data['price_nok']

        # Print summary
        print(f"   • Mean: {series.mean():.3f} NOK/kWh")
        print(f"   • Range: {series.min():.3f} to {series.max():.3f} NOK/kWh")

        return series

    def _save_to_cache(
        self,
        prices: pd.Series,
        cache_file: Path,
        area: str,
        year: int,
        source: str
    ):
        """Save prices to cache with metadata"""

        # Convert to DataFrame and save with index name for proper loading
        df = prices.to_frame()
        df.index.name = 'timestamp'  # Ensure index has name
        df.to_csv(cache_file)

        # Update metadata
        self._update_cache_metadata(
            area,
            year,
            source,
            note=f"Fetched via unified price fetcher"
        )

        print(f"💾 Saved to cache: {cache_file.name}")

    def _print_statistics(self, prices: pd.Series, year: int):
        """Print price statistics"""

        print(f"\n📊 Price Statistics {year}:")
        print(f"   • Mean:   {prices.mean():.3f} NOK/kWh")
        print(f"   • Median: {prices.median():.3f} NOK/kWh")
        print(f"   • Min:    {prices.min():.3f} NOK/kWh")
        print(f"   • Max:    {prices.max():.3f} NOK/kWh")
        print(f"   • Std:    {prices.std():.3f} NOK/kWh")

        # Check for negative prices
        negative = prices[prices < 0]
        if len(negative) > 0:
            print(f"   • Negative prices: {len(negative)} hours ({len(negative)/len(prices)*100:.1f}%)")

    def _show_cached_data_info(self):
        """Display information about cached data files"""

        cached_files = sorted(self.cache_dir.glob("NO*_*.csv"))

        if not cached_files:
            return  # Silent if no cache

        print("\n📦 Cached Price Data:")
        print("=" * 60)

        metadata = self._load_metadata()

        for file in cached_files:
            # Extract area and year from filename
            parts = file.stem.split('_')
            if len(parts) >= 2:
                area = parts[0]
                year = parts[1]

                key = f"{area}_{year}"
                file_metadata = metadata.get(key, {})

                size_kb = file.stat().st_size / 1024

                print(f"   {area} {year}: {size_kb:.1f} KB")
                if file_metadata:
                    print(f"      Source: {file_metadata.get('source', 'Unknown')}")
                    print(f"      Date: {file_metadata.get('fetched_date', 'Unknown')}")

        print("=" * 60 + "\n")

    def _load_metadata(self) -> dict:
        """Load metadata from JSON file"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_metadata(self, metadata: dict):
        """Save metadata to JSON file"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

    def _get_cache_metadata(self, area: str, year: int) -> dict:
        """Get metadata for specific cache file"""
        metadata = self._load_metadata()
        key = f"{area}_{year}"
        return metadata.get(key, {})

    def _update_cache_metadata(self, area: str, year: int, source: str, note: str = None):
        """Update metadata for cache file"""
        metadata = self._load_metadata()
        key = f"{area}_{year}"

        metadata[key] = {
            'area': area,
            'year': year,
            'source': source,
            'fetched_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'note': note,
            'eur_nok_rate': self.eur_nok_rate
        }

        self._save_metadata(metadata)


# Convenience function for backward compatibility
def fetch_prices(
    year: int,
    area: str = 'NO2',
    api_key: Optional[str] = None,
    refresh: bool = False
) -> pd.Series:
    """
    Fetch electricity prices (convenience function)

    Args:
        year: Year to fetch (e.g., 2023)
        area: Bidding zone (NO1-NO5)
        api_key: ENTSO-E API key (optional, reads from env)
        refresh: Force fresh fetch even if cached

    Returns:
        Series with hourly prices in NOK/kWh
    """
    fetcher = ENTSOEPriceFetcher(api_key=api_key)
    return fetcher.fetch_prices(year, area, refresh=refresh)


if __name__ == "__main__":
    # Quick test
    import sys

    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2023
    area = sys.argv[2] if len(sys.argv) > 2 else 'NO2'

    print(f"Testing price fetcher for {area} {year}...")

    fetcher = ENTSOEPriceFetcher()
    prices = fetcher.fetch_prices(year, area)

    print(f"\n✅ Successfully fetched {len(prices)} hourly prices")
