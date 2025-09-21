"""
Tests for ENTSO-E client
"""
import pytest
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import tempfile

from infrastructure.data_sources.entsoe_client import ENTSOEClient, PriceForecaster


class TestENTSOEClient:
    """Test ENTSO-E API client"""

    @pytest.fixture
    def client(self):
        """Create client with temp cache dir"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield ENTSOEClient(cache_dir=Path(tmpdir))

    def test_client_initialization(self, client):
        """Test client initialization"""
        assert client.base_url == "https://web-api.tp.entsoe.eu/api"
        assert 'NO2' in client.area_codes
        assert client.cache_dir.exists()

    def test_simulated_prices_generation(self, client):
        """Test generating simulated prices when no API key"""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 7, 23)

        prices = client.fetch_day_ahead_prices(
            start_date=start,
            end_date=end,
            bidding_zone='NO2',
            use_cache=False
        )

        # Should return hourly prices for 7 days
        assert len(prices) == 7 * 24
        assert isinstance(prices, pd.Series)
        assert prices.index[0] == start
        assert prices.min() >= 0  # No negative prices

    def test_price_conversion_to_nok(self, client):
        """Test EUR to NOK conversion"""
        # Create sample EUR prices
        prices_eur = pd.Series([50, 60, 70])  # EUR/MWh

        prices_nok = client.convert_to_nok(prices_eur, exchange_rate=11.5)

        # Should convert to NOK/kWh
        assert prices_nok[0] == pytest.approx(50 * 11.5 / 1000, rel=0.001)
        assert prices_nok[1] == pytest.approx(60 * 11.5 / 1000, rel=0.001)

    def test_price_statistics(self, client):
        """Test calculating price statistics"""
        prices = pd.Series([10, 20, 30, 40, 50])

        stats = client.get_price_statistics(prices)

        assert stats['mean'] == 30
        assert stats['median'] == 30
        assert stats['min'] == 10
        assert stats['max'] == 50
        assert 'std' in stats
        assert 'p10' in stats
        assert 'p90' in stats

    def test_peak_hours_extraction(self, client):
        """Test extracting peak hours prices"""
        # Create hourly prices for 2 days
        index = pd.date_range(start='2024-01-01', periods=48, freq='h')
        prices = pd.Series(range(48), index=index)

        peak_prices = client.get_peak_hours_prices(prices)

        # Should only include Mon-Fri 06:00-22:00
        # Jan 1, 2024 is Monday
        assert len(peak_prices) == 32  # 16 hours * 2 days
        assert peak_prices.index[0].hour == 6
        assert peak_prices.index[15].hour == 21

    def test_off_peak_prices(self, client):
        """Test extracting off-peak prices"""
        # Create hourly prices for 2 days
        index = pd.date_range(start='2024-01-01', periods=48, freq='h')
        prices = pd.Series(range(48), index=index)

        off_peak_prices = client.get_off_peak_prices(prices)

        # Should include nights and early mornings
        assert len(off_peak_prices) == 16  # 48 total - 32 peak

    def test_cache_functionality(self, client):
        """Test that caching works"""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1, 23)

        # First call - generates data
        prices1 = client.fetch_day_ahead_prices(
            start_date=start,
            end_date=end,
            bidding_zone='NO2',
            use_cache=True
        )

        # Second call - should use cache
        prices2 = client.fetch_day_ahead_prices(
            start_date=start,
            end_date=end,
            bidding_zone='NO2',
            use_cache=True
        )

        # Should return identical data
        assert prices1.equals(prices2)


class TestPriceForecaster:
    """Test price forecasting functionality"""

    def test_forecaster_initialization(self):
        """Test forecaster initialization"""
        historical = pd.Series(
            [50, 60, 70],
            index=pd.date_range('2024-01-01', periods=3, freq='h')
        )
        forecaster = PriceForecaster(historical)

        assert len(forecaster.historical) == 3

    def test_forecast_generation(self):
        """Test generating price forecast"""
        # Create historical data for one week
        historical = pd.Series(
            range(168),  # 7 days * 24 hours
            index=pd.date_range('2024-01-01', periods=168, freq='h')
        )
        forecaster = PriceForecaster(historical)

        forecast = forecaster.forecast_next_year(
            inflation_rate=0.02,
            volatility_increase=1.0
        )

        # Should generate full year forecast
        assert len(forecast) >= 365 * 24
        assert forecast.min() >= 0  # No negative prices

    def test_forecast_with_inflation(self):
        """Test that inflation is applied in forecast"""
        # Create constant historical prices
        historical = pd.Series(
            [100] * 168,
            index=pd.date_range('2024-01-01', periods=168, freq='h')
        )
        forecaster = PriceForecaster(historical)

        forecast = forecaster.forecast_next_year(
            inflation_rate=0.10,  # 10% inflation
            volatility_increase=0  # No volatility for testing
        )

        # Average should be higher due to inflation
        # (not exact due to random component)
        assert forecast.mean() > 100