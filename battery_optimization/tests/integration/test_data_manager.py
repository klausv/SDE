"""
Integration tests for DataManager.

Tests file loading, windowing, resampling, and error handling with real data files.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

from src.config.simulation_config import (
    SimulationConfig,
    DataSourceConfig,
    SimulationPeriodConfig,
)
from src.data.data_manager import DataManager, TimeSeriesData


# Fixture paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
PRICES_HOURLY = str(FIXTURES_DIR / "test_prices_hourly.csv")
PRODUCTION_HOURLY = str(FIXTURES_DIR / "test_production_hourly.csv")
CONSUMPTION_HOURLY = str(FIXTURES_DIR / "test_consumption_hourly.csv")


@pytest.fixture
def test_config():
    """Create test configuration with fixture data files."""
    config = SimulationConfig(
        mode="rolling_horizon",
        time_resolution="PT60M",
        simulation_period=SimulationPeriodConfig(
            start_date="2024-01-01",
            end_date="2024-01-07",
        ),
        data_sources=DataSourceConfig(
            prices_file=PRICES_HOURLY,
            production_file=PRODUCTION_HOURLY,
            consumption_file=CONSUMPTION_HOURLY,
        ),
    )
    return config


@pytest.fixture
def data_manager(test_config):
    """Create DataManager instance for testing."""
    return DataManager(test_config)


class TestDataManagerLoading:
    """Test data loading functionality."""

    def test_load_data_success(self, data_manager):
        """Test successful data loading."""
        data = data_manager.load_data()

        assert isinstance(data, TimeSeriesData)
        assert len(data) > 0
        assert data.resolution == "PT60M"
        assert len(data.timestamps) == len(data.prices_nok_per_kwh)
        assert len(data.timestamps) == len(data.pv_production_kw)
        assert len(data.timestamps) == len(data.consumption_kw)

    def test_load_data_alignment(self, data_manager):
        """Test that all data series are properly aligned."""
        data = data_manager.load_data()

        # Check no NaN values
        assert not np.any(np.isnan(data.prices_nok_per_kwh))
        assert not np.any(np.isnan(data.pv_production_kw))
        assert not np.any(np.isnan(data.consumption_kw))

        # Check timestamps are monotonic
        assert data.timestamps.is_monotonic_increasing

    def test_get_data_before_load_fails(self, data_manager):
        """Test that get_data() fails before load_data() is called."""
        with pytest.raises(RuntimeError, match="Data not loaded"):
            data_manager.get_data()

    def test_get_data_after_load_succeeds(self, data_manager):
        """Test that get_data() works after load_data()."""
        data_manager.load_data()
        data = data_manager.get_data()
        assert isinstance(data, TimeSeriesData)

    def test_date_range(self, data_manager):
        """Test get_date_range() returns correct period."""
        data_manager.load_data()
        start, end = data_manager.get_date_range()

        assert isinstance(start, datetime)
        assert isinstance(end, datetime)
        assert start < end
        assert start.date() >= datetime(2024, 1, 1).date()
        assert end.date() <= datetime(2024, 1, 8).date()


class TestDataManagerWindowing:
    """Test time windowing functionality."""

    def test_get_window_24h(self, data_manager):
        """Test extracting 24-hour window."""
        data_manager.load_data()
        start = datetime(2024, 1, 2, 0, 0, 0)

        window = data_manager.get_window(start, hours=24)

        assert isinstance(window, TimeSeriesData)
        assert len(window) == 24  # 24 hours @ hourly
        assert window.timestamps[0].to_pydatetime() >= start
        assert window.resolution == "PT60M"

    def test_get_window_partial_day(self, data_manager):
        """Test extracting partial day window."""
        data_manager.load_data()
        start = datetime(2024, 1, 3, 12, 0, 0)

        window = data_manager.get_window(start, hours=6)

        assert isinstance(window, TimeSeriesData)
        assert len(window) == 6  # 6 hours
        assert window.timestamps[0].to_pydatetime() >= start

    def test_get_window_out_of_range(self, data_manager):
        """Test that window extraction fails for out-of-range dates."""
        data_manager.load_data()
        future_start = datetime(2025, 1, 1, 0, 0, 0)

        with pytest.raises(ValueError, match="No data in window"):
            data_manager.get_window(future_start, hours=24)

    def test_get_month(self, data_manager):
        """Test extracting monthly data."""
        data_manager.load_data()

        month_data = data_manager.get_month(year=2024, month=1)

        assert isinstance(month_data, TimeSeriesData)
        assert all(ts.month == 1 for ts in month_data.timestamps)
        assert all(ts.year == 2024 for ts in month_data.timestamps)

    def test_get_month_invalid(self, data_manager):
        """Test that invalid month raises error."""
        data_manager.load_data()

        with pytest.raises(ValueError, match="No data for"):
            data_manager.get_month(year=2024, month=12)

    def test_get_week(self, data_manager):
        """Test extracting weekly data."""
        data_manager.load_data()

        week_data = data_manager.get_week(year=2024, week=1)

        assert isinstance(week_data, TimeSeriesData)
        # Week 1 should have some data (ISO week 1 of 2024 starts Jan 1)
        assert len(week_data) > 0
        assert len(week_data) <= 7 * 24  # At most 7 days of hourly data


class TestDataManagerResampling:
    """Test time resolution resampling."""

    def test_resample_to_same_resolution(self, data_manager):
        """Test that resampling to same resolution returns same data."""
        data = data_manager.load_data()
        resampled = data.resample_to("PT60M")

        assert len(resampled) == len(data)
        assert resampled.resolution == "PT60M"
        np.testing.assert_array_equal(resampled.timestamps, data.timestamps)

    def test_resample_hourly_to_15min(self, data_manager):
        """Test upsampling from hourly to 15-minute."""
        data = data_manager.load_data()
        resampled = data.resample_to("PT15M")

        assert resampled.resolution == "PT15M"
        # Should have more timesteps (approximately 4x, accounting for interpolation)
        assert len(resampled) > len(data)
        # First timestamps should match
        assert resampled.timestamps[0] == data.timestamps[0]


class TestDataManagerSummary:
    """Test summary statistics."""

    def test_summary_structure(self, data_manager):
        """Test that summary returns expected structure."""
        data_manager.load_data()
        summary = data_manager.summary()

        assert isinstance(summary, dict)
        assert 'start_date' in summary
        assert 'end_date' in summary
        assert 'num_timesteps' in summary
        assert 'resolution' in summary
        assert 'price_stats' in summary
        assert 'production_stats' in summary
        assert 'consumption_stats' in summary

    def test_summary_statistics(self, data_manager):
        """Test that summary statistics are reasonable."""
        data_manager.load_data()
        summary = data_manager.summary()

        # Price stats
        price_stats = summary['price_stats']
        assert price_stats['min'] >= 0
        assert price_stats['max'] > price_stats['min']
        assert price_stats['mean'] > 0

        # Production stats
        prod_stats = summary['production_stats']
        assert prod_stats['min'] >= 0
        assert prod_stats['max'] > 0
        assert prod_stats['total_kwh'] > 0

        # Consumption stats
        cons_stats = summary['consumption_stats']
        assert cons_stats['min'] >= 0
        assert cons_stats['max'] > 0
        assert cons_stats['total_kwh'] > 0


class TestTimeSeriesData:
    """Test TimeSeriesData methods."""

    @pytest.fixture
    def sample_data(self, data_manager):
        """Load sample data for testing."""
        return data_manager.load_data()

    def test_to_dataframe(self, sample_data):
        """Test conversion to DataFrame."""
        df = sample_data.to_dataframe()

        assert isinstance(df, pd.DataFrame)
        assert 'price_nok_per_kwh' in df.columns
        assert 'pv_production_kw' in df.columns
        assert 'consumption_kw' in df.columns
        assert len(df) == len(sample_data)

    def test_get_window_method(self, sample_data):
        """Test TimeSeriesData.get_window() method."""
        start = sample_data.timestamps[10].to_pydatetime()
        window = sample_data.get_window(start, hours=12)

        assert len(window) <= 12
        assert window.timestamps[0].to_pydatetime() >= start

    def test_invalid_timeseriesdata_construction(self):
        """Test that mismatched array lengths raise error."""
        timestamps = pd.date_range("2024-01-01", periods=10, freq='h')

        with pytest.raises(ValueError, match="doesn't match timestamps"):
            TimeSeriesData(
                timestamps=timestamps,
                prices_nok_per_kwh=np.zeros(10),
                pv_production_kw=np.zeros(9),  # Wrong length
                consumption_kw=np.zeros(10),
                resolution="PT60M"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
