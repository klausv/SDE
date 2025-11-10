"""
Real Data Loading Tests

Tests data loading functionality using actual CSV files from the project.
These tests verify that real-world data (with timezone info, year mapping,
minute offsets, etc.) loads correctly.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from src.data.file_loaders import (
    load_price_data,
    load_production_data,
    load_consumption_data,
    align_timeseries,
    detect_resolution,
)


# Test data file paths
DATA_DIR = Path(__file__).parent.parent.parent / "data"
PRICE_FILE = DATA_DIR / "spot_prices" / "NO2_2024_60min_real.csv"
PRODUCTION_FILE = DATA_DIR / "pv_profiles" / "pvgis_58.97_5.73_138.55kWp.csv"
CONSUMPTION_FILE = DATA_DIR / "consumption" / "commercial_2024.csv"


class TestRealPriceDataLoading:
    """Tests for loading real electricity price data."""

    def test_price_file_exists(self):
        """Verify price data file exists."""
        assert PRICE_FILE.exists(), f"Price file not found: {PRICE_FILE}"

    def test_load_price_data_basic(self):
        """Test basic price data loading."""
        timestamps, prices = load_price_data(str(PRICE_FILE))

        assert len(timestamps) > 0, "No price data loaded"
        assert len(prices) > 0, "No price values loaded"
        assert len(timestamps) == len(prices), "Timestamp and price length mismatch"

    def test_price_data_timezone_handling(self):
        """Test that timezone conversion works correctly."""
        timestamps, prices = load_price_data(str(PRICE_FILE))

        # Check timestamps are timezone-naive after processing
        assert timestamps.tz is None, "Timestamps should be timezone-naive after processing"

        # Check timestamps are in expected year
        assert timestamps[0].year == 2024, f"Expected year 2024, got {timestamps[0].year}"

    def test_price_data_no_duplicates(self):
        """Test that DST duplicates have been removed."""
        timestamps, prices = load_price_data(str(PRICE_FILE))

        # Check for duplicate timestamps
        duplicates = timestamps[timestamps.duplicated()]
        assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate timestamps after DST handling"

    def test_price_data_values_reasonable(self):
        """Test that price values are in reasonable range."""
        timestamps, prices = load_price_data(str(PRICE_FILE))

        # Negative prices can occur in spot markets (surplus production)
        assert np.min(prices) > -2.0, f"Found extremely negative prices: min={np.min(prices)}"
        assert np.max(prices) < 10, f"Found suspiciously high prices: max={np.max(prices)}"
        assert np.mean(prices) > 0.1, f"Average price too low: {np.mean(prices)}"

        # Most prices should be positive
        positive_ratio = np.sum(prices > 0) / len(prices)
        assert positive_ratio > 0.90, f"Too many negative prices: only {positive_ratio:.1%} positive"

    def test_price_data_resolution(self):
        """Test that resolution detection works."""
        timestamps, _ = load_price_data(str(PRICE_FILE))

        resolution = detect_resolution(timestamps)
        assert resolution == 'PT60M', f"Expected PT60M, got {resolution}"


class TestRealProductionDataLoading:
    """Tests for loading real PV production data."""

    def test_production_file_exists(self):
        """Verify production data file exists."""
        assert PRODUCTION_FILE.exists(), f"Production file not found: {PRODUCTION_FILE}"

    def test_load_production_data_basic(self):
        """Test basic production data loading."""
        timestamps, production = load_production_data(str(PRODUCTION_FILE))

        assert len(timestamps) > 0, "No production data loaded"
        assert len(production) > 0, "No production values loaded"
        assert len(timestamps) == len(production), "Timestamp and production length mismatch"

    def test_production_year_mapping(self):
        """Test that PVGIS representative year is mapped to 2024."""
        timestamps, production = load_production_data(str(PRODUCTION_FILE))

        # After year mapping, should be 2024
        assert timestamps[0].year == 2024, f"Expected year 2024 after mapping, got {timestamps[0].year}"

    def test_production_minute_offset_removed(self):
        """Test that PVGIS :11 minute offset is removed by resampling."""
        timestamps, production = load_production_data(str(PRODUCTION_FILE))

        # Check all timestamps are at :00 minutes
        minutes = timestamps.minute
        unique_minutes = np.unique(minutes)

        # After hourly resampling, should only have :00 minutes
        assert len(unique_minutes) == 1, f"Expected only :00 minutes, found {unique_minutes}"
        assert unique_minutes[0] == 0, f"Expected :00 minutes, got :{unique_minutes[0]:02d}"

    def test_production_values_reasonable(self):
        """Test that production values are in reasonable range."""
        timestamps, production = load_production_data(str(PRODUCTION_FILE))

        assert np.all(production >= 0), "Found negative production values"
        assert np.max(production) <= 150, f"Max production {np.max(production)} exceeds system capacity"

        # Check annual production is reasonable (should be >0 for Stavanger)
        annual_kwh = np.sum(production) * 1.0  # Hourly data
        assert annual_kwh > 50000, f"Annual production {annual_kwh:.0f} kWh seems too low"
        assert annual_kwh < 200000, f"Annual production {annual_kwh:.0f} kWh seems too high"

    def test_production_has_night_zeros(self):
        """Test that production is zero during night hours."""
        timestamps, production = load_production_data(str(PRODUCTION_FILE))

        # Check winter night hours (e.g., January at 02:00)
        jan_mask = timestamps.month == 1
        hour_mask = timestamps.hour == 2
        night_production = production[jan_mask & hour_mask]

        # Should be mostly zero at 02:00 in January in Stavanger
        assert np.mean(night_production) < 1.0, "Expected ~zero production at night in winter"


class TestRealConsumptionDataLoading:
    """Tests for loading real consumption data."""

    def test_consumption_file_exists(self):
        """Verify consumption data file exists."""
        assert CONSUMPTION_FILE.exists(), f"Consumption file not found: {CONSUMPTION_FILE}"

    def test_load_consumption_data_basic(self):
        """Test basic consumption data loading."""
        timestamps, consumption = load_consumption_data(str(CONSUMPTION_FILE))

        assert len(timestamps) > 0, "No consumption data loaded"
        assert len(consumption) > 0, "No consumption values loaded"
        assert len(timestamps) == len(consumption), "Timestamp and consumption length mismatch"

    def test_consumption_values_reasonable(self):
        """Test that consumption values are in reasonable range."""
        timestamps, consumption = load_consumption_data(str(CONSUMPTION_FILE))

        assert np.all(consumption >= 0), "Found negative consumption values"
        assert np.min(consumption) > 0, "Consumption should always be >0 (base load)"

        # Check mean consumption is reasonable
        mean_consumption = np.mean(consumption)
        assert 20 <= mean_consumption <= 50, f"Mean consumption {mean_consumption:.1f} kW outside expected range"

    def test_consumption_weekday_weekend_pattern(self):
        """Test that consumption has expected weekday/weekend pattern."""
        timestamps, consumption = load_consumption_data(str(CONSUMPTION_FILE))

        # Calculate average for weekdays vs weekends
        weekday_mask = timestamps.weekday < 5
        weekend_mask = timestamps.weekday >= 5

        weekday_avg = np.mean(consumption[weekday_mask])
        weekend_avg = np.mean(consumption[weekend_mask])

        # Commercial profile should have higher weekday consumption
        assert weekday_avg > weekend_avg, "Expected higher consumption on weekdays for commercial profile"


class TestRealDataAlignment:
    """Tests for aligning real data from multiple sources."""

    def test_align_all_three_sources(self):
        """Test aligning price, production, and consumption data."""
        # Load all three
        timestamps_price, prices = load_price_data(str(PRICE_FILE))
        timestamps_prod, production = load_production_data(str(PRODUCTION_FILE))
        timestamps_cons, consumption = load_consumption_data(str(CONSUMPTION_FILE))

        # Align
        common_timestamps, aligned_values = align_timeseries(
            [timestamps_price, timestamps_prod, timestamps_cons],
            [prices, production, consumption]
        )

        # Check alignment
        assert len(common_timestamps) > 0, "No common timestamps after alignment"
        assert len(aligned_values) == 3, "Should have 3 aligned value arrays"

        # Check all aligned arrays have same length
        for i, values in enumerate(aligned_values):
            assert len(values) == len(common_timestamps), \
                f"Aligned array {i} length mismatch: {len(values)} vs {len(common_timestamps)}"

    def test_aligned_data_covers_full_year(self):
        """Test that aligned data covers substantial portion of year."""
        # Load all three
        timestamps_price, prices = load_price_data(str(PRICE_FILE))
        timestamps_prod, production = load_production_data(str(PRODUCTION_FILE))
        timestamps_cons, consumption = load_consumption_data(str(CONSUMPTION_FILE))

        # Align
        common_timestamps, aligned_values = align_timeseries(
            [timestamps_price, timestamps_prod, timestamps_cons],
            [prices, production, consumption]
        )

        # Check coverage
        total_hours = len(common_timestamps)
        assert total_hours >= 8000, f"Expected >8000 hours of aligned data, got {total_hours}"

        # Check year coverage
        unique_months = common_timestamps.month.unique()
        assert len(unique_months) >= 10, f"Expected data for ≥10 months, got {len(unique_months)}"

    def test_aligned_data_no_nans(self):
        """Test that aligned data has no NaN values."""
        # Load all three
        timestamps_price, prices = load_price_data(str(PRICE_FILE))
        timestamps_prod, production = load_production_data(str(PRODUCTION_FILE))
        timestamps_cons, consumption = load_consumption_data(str(CONSUMPTION_FILE))

        # Align
        common_timestamps, aligned_values = align_timeseries(
            [timestamps_price, timestamps_prod, timestamps_cons],
            [prices, production, consumption]
        )

        # Check for NaNs
        for i, values in enumerate(aligned_values):
            nan_count = np.sum(np.isnan(values))
            assert nan_count == 0, f"Found {nan_count} NaN values in aligned array {i}"

    def test_june_2024_data_available(self):
        """Test that June 2024 data is available (used in working_config.yaml)."""
        # Load all three
        timestamps_price, prices = load_price_data(str(PRICE_FILE))
        timestamps_prod, production = load_production_data(str(PRODUCTION_FILE))
        timestamps_cons, consumption = load_consumption_data(str(CONSUMPTION_FILE))

        # Align
        common_timestamps, aligned_values = align_timeseries(
            [timestamps_price, timestamps_prod, timestamps_cons],
            [prices, production, consumption]
        )

        # Filter to June 2024
        june_mask = (common_timestamps.year == 2024) & (common_timestamps.month == 6)
        june_timestamps = common_timestamps[june_mask]

        assert len(june_timestamps) > 0, "No June 2024 data available"
        assert len(june_timestamps) >= 700, f"Expected ~720 hours in June, got {len(june_timestamps)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
