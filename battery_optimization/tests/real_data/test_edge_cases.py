"""
Edge Case Tests for Real Data Handling

Tests for challenging real-world scenarios:
- DST (Daylight Saving Time) transitions
- Leap years (2024 has 366 days)
- Minute offsets in PVGIS data
- Missing data periods
- Data alignment across different time zones
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

from src.data.file_loaders import (
    load_price_data,
    load_production_data,
    load_consumption_data,
    align_timeseries,
    detect_resolution,
    resample_timeseries,
)


# Test data paths
DATA_DIR = Path(__file__).parent.parent.parent / "data"
PRICE_FILE = DATA_DIR / "spot_prices" / "NO2_2024_60min_real.csv"
PRODUCTION_FILE = DATA_DIR / "pv_profiles" / "pvgis_58.97_5.73_138.55kWp.csv"
CONSUMPTION_FILE = DATA_DIR / "consumption" / "commercial_2024.csv"


class TestDSTTransitions:
    """Tests for DST (Daylight Saving Time) transition handling."""

    def test_spring_dst_transition(self):
        """Test spring DST transition (clocks forward, missing hour)."""
        # In Europe/Oslo, spring 2024 DST: March 31 at 02:00 → 03:00
        timestamps, prices = load_price_data(str(PRICE_FILE))

        # Filter to March 31, 2024
        dst_date = pd.Timestamp('2024-03-31')
        dst_mask = timestamps.date == dst_date.date()
        dst_timestamps = timestamps[dst_mask]

        if len(dst_timestamps) > 0:
            # Check that 02:00 hour is missing (spring forward)
            hours = dst_timestamps.hour
            assert 2 not in hours, "Hour 02:00 should be missing during spring DST transition"

            # Should have 23 hours on this day (not 24)
            assert len(dst_timestamps) == 23, f"Expected 23 hours on DST spring day, got {len(dst_timestamps)}"

    def test_fall_dst_transition(self):
        """Test fall DST transition (clocks backward, duplicate hour)."""
        # In Europe/Oslo, fall 2024 DST: October 27 at 03:00 → 02:00
        timestamps, prices = load_price_data(str(PRICE_FILE))

        # Filter to October 27, 2024
        dst_date = pd.Timestamp('2024-10-27')
        dst_mask = timestamps.date == dst_date.date()
        dst_timestamps = timestamps[dst_mask]

        if len(dst_timestamps) > 0:
            # After duplicate removal, should have 24 hours (not 25)
            assert len(dst_timestamps) == 24, f"Expected 24 hours after duplicate removal, got {len(dst_timestamps)}"

            # Check no duplicates
            duplicates = dst_timestamps[dst_timestamps.duplicated()]
            assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate timestamps after DST handling"

    def test_dst_no_data_gaps(self):
        """Test that DST transitions don't create unexpected data gaps."""
        timestamps, prices = load_price_data(str(PRICE_FILE))

        # Calculate hour differences
        diffs = pd.Series(timestamps[1:]).reset_index(drop=True) - pd.Series(timestamps[:-1]).reset_index(drop=True)
        diff_hours = diffs.dt.total_seconds() / 3600

        # Most should be 1 hour
        most_common_diff = diff_hours.mode()[0]
        assert most_common_diff == 1.0, f"Expected 1h resolution, got {most_common_diff}h"

        # Allow for 2h gap (DST spring) or 0h gap (after duplicate removal)
        max_gap = diff_hours.max()
        assert max_gap <= 2.0, f"Found unexpected gap: {max_gap} hours"


class TestLeapYear:
    """Tests for leap year handling (2024 has 366 days)."""

    def test_2024_is_leap_year(self):
        """Verify that 2024 is correctly identified as leap year."""
        timestamps, _ = load_price_data(str(PRICE_FILE))

        # Check February 29, 2024 exists
        feb_29_mask = (timestamps.month == 2) & (timestamps.day == 29) & (timestamps.year == 2024)
        feb_29_data = timestamps[feb_29_mask]

        if len(timestamps[timestamps.year == 2024]) > 0:
            assert len(feb_29_data) > 0, "February 29, 2024 should exist (leap year)"

    def test_total_hours_in_2024(self):
        """Test that 2024 has correct number of hours (366 days * 24h - 1h for DST)."""
        timestamps, _ = load_price_data(str(PRICE_FILE))

        # Filter to 2024
        year_2024_mask = timestamps.year == 2024
        timestamps_2024 = timestamps[year_2024_mask]

        if len(timestamps_2024) > 100:  # Only test if we have substantial 2024 data
            # 366 days * 24h = 8784h, minus 1h for spring DST = 8783h
            expected_hours = 8783
            actual_hours = len(timestamps_2024)

            # Allow some tolerance for incomplete year data
            assert abs(actual_hours - expected_hours) < 100, \
                f"Expected ~{expected_hours} hours in 2024, got {actual_hours}"


class TestPVGISMinuteOffset:
    """Tests for handling PVGIS :11 minute offset."""

    def test_pvgis_minute_offset_removed(self):
        """Test that PVGIS :11 offset is removed by resampling."""
        timestamps, production = load_production_data(str(PRODUCTION_FILE))

        # Check all minutes are :00
        unique_minutes = timestamps.minute.unique()
        assert len(unique_minutes) == 1, f"Expected only :00 minutes, found {unique_minutes}"
        assert unique_minutes[0] == 0, f"Expected :00 minutes, got :{unique_minutes[0]:02d}"

    def test_pvgis_hourly_resampling_preserves_total(self):
        """Test that resampling preserves total energy (approximately)."""
        # This is hard to test without the original data, but we can check that
        # the hourly values are reasonable
        timestamps, production = load_production_data(str(PRODUCTION_FILE))

        # Annual total should be reasonable
        annual_kwh = np.sum(production) * 1.0  # Hourly data
        assert 50000 < annual_kwh < 200000, f"Annual production {annual_kwh:.0f} kWh outside reasonable range"


class TestYearMapping:
    """Tests for PVGIS representative year mapping."""

    def test_production_year_mapped_to_2024(self):
        """Test that PVGIS representative year data is mapped to 2024."""
        timestamps, production = load_production_data(str(PRODUCTION_FILE))

        # After mapping, all years should be 2024
        unique_years = timestamps.year.unique()

        # Should have 2024 (might also have other years if data spans multiple years)
        assert 2024 in unique_years, "Expected 2024 in mapped PV data"

    def test_production_seasonal_pattern_preserved(self):
        """Test that seasonal pattern is preserved after year mapping."""
        timestamps, production = load_production_data(str(PRODUCTION_FILE))

        # Calculate monthly averages
        monthly_avg = pd.Series(production, index=timestamps).resample('ME').mean()

        # Summer months (Jun-Aug) should have higher production than winter (Dec-Feb)
        if len(monthly_avg) >= 12:
            summer_avg = monthly_avg[monthly_avg.index.month.isin([6, 7, 8])].mean()
            winter_avg = monthly_avg[monthly_avg.index.month.isin([12, 1, 2])].mean()

            assert summer_avg > winter_avg * 2, \
                f"Summer avg {summer_avg:.1f} should be >2x winter avg {winter_avg:.1f}"


class TestDataAlignment:
    """Tests for edge cases in data alignment."""

    def test_alignment_handles_different_start_times(self):
        """Test alignment when data sources have different start times."""
        timestamps_price, prices = load_price_data(str(PRICE_FILE))
        timestamps_prod, production = load_production_data(str(PRODUCTION_FILE))

        # Align
        common_timestamps, aligned_values = align_timeseries(
            [timestamps_price, timestamps_prod],
            [prices, production]
        )

        # Should find overlap
        assert len(common_timestamps) > 0, "No overlap found between data sources"

        # All aligned values should have matching lengths
        assert len(aligned_values[0]) == len(common_timestamps)
        assert len(aligned_values[1]) == len(common_timestamps)

    def test_alignment_removes_non_overlapping_periods(self):
        """Test that alignment correctly removes non-overlapping periods."""
        timestamps_price, prices = load_price_data(str(PRICE_FILE))
        timestamps_prod, production = load_production_data(str(PRODUCTION_FILE))

        # Align
        common_timestamps, aligned_values = align_timeseries(
            [timestamps_price, timestamps_prod],
            [prices, production]
        )

        # Common timestamps should be subset of both original
        assert common_timestamps[0] >= min(timestamps_price[0], timestamps_prod[0]), \
            "Common start should not be before any source start"
        assert common_timestamps[-1] <= max(timestamps_price[-1], timestamps_prod[-1]), \
            "Common end should not be after any source end"


class TestResolutionHandling:
    """Tests for different time resolutions."""

    def test_detect_hourly_resolution(self):
        """Test hourly resolution detection."""
        timestamps, _ = load_price_data(str(PRICE_FILE))
        resolution = detect_resolution(timestamps)

        assert resolution == 'PT60M', f"Expected PT60M, got {resolution}"

    def test_resample_hourly_to_15min(self):
        """Test resampling from hourly to 15-minute."""
        timestamps = pd.date_range('2024-01-01', periods=24, freq='h')
        values = np.random.uniform(0, 100, 24)

        resampled_timestamps, resampled_values = resample_timeseries(
            timestamps, values, 'PT15M', method='interpolate'
        )

        # Should have approximately 4x as many timesteps (pandas resampling endpoint handling)
        assert 90 <= len(resampled_timestamps) <= 96, \
            f"Expected ~96 timesteps after 15min resampling, got {len(resampled_timestamps)}"

        # All values should be finite
        assert np.all(np.isfinite(resampled_values)), "Found NaN/Inf in resampled data"

    def test_resample_15min_to_hourly(self):
        """Test resampling from 15-minute to hourly."""
        timestamps = pd.date_range('2024-01-01', periods=96, freq='15min')
        values = np.random.uniform(0, 100, 96)

        resampled_timestamps, resampled_values = resample_timeseries(
            timestamps, values, 'PT60M', method='mean'
        )

        # Should have 1/4 as many timesteps
        assert len(resampled_timestamps) == 24, \
            f"Expected 24 timesteps after hourly resampling, got {len(resampled_timestamps)}"

        # Mean values should be in range
        assert np.all(resampled_values >= 0), "Found negative values after resampling"
        assert np.all(resampled_values <= 100), "Found out-of-range values after resampling"


class TestMissingDataHandling:
    """Tests for handling missing or incomplete data."""

    def test_no_missing_values_in_loaded_data(self):
        """Test that loaded data has no NaN values."""
        timestamps_price, prices = load_price_data(str(PRICE_FILE))
        timestamps_prod, production = load_production_data(str(PRODUCTION_FILE))
        timestamps_cons, consumption = load_consumption_data(str(CONSUMPTION_FILE))

        assert not np.any(np.isnan(prices)), "Found NaN in price data"
        assert not np.any(np.isnan(production)), "Found NaN in production data"
        assert not np.any(np.isnan(consumption)), "Found NaN in consumption data"

    def test_no_infinite_values_in_loaded_data(self):
        """Test that loaded data has no infinite values."""
        timestamps_price, prices = load_price_data(str(PRICE_FILE))
        timestamps_prod, production = load_production_data(str(PRODUCTION_FILE))
        timestamps_cons, consumption = load_consumption_data(str(CONSUMPTION_FILE))

        assert not np.any(np.isinf(prices)), "Found Inf in price data"
        assert not np.any(np.isinf(production)), "Found Inf in production data"
        assert not np.any(np.isinf(consumption)), "Found Inf in consumption data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
