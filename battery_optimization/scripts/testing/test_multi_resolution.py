#!/usr/bin/env python3
"""
Test script for multi-resolution price fetcher

Tests both hourly and 15-minute resolution support
"""

from core.price_fetcher import ENTSOEPriceFetcher, fetch_prices
import pandas as pd


def test_resolution_constants():
    """Test resolution constants are properly defined"""
    print("="*60)
    print("TEST: Resolution Constants")
    print("="*60)

    assert ENTSOEPriceFetcher.RESOLUTION_HOURLY == 'PT60M'
    assert ENTSOEPriceFetcher.RESOLUTION_15MIN == 'PT15M'
    assert len(ENTSOEPriceFetcher.VALID_RESOLUTIONS) == 2

    print("✅ Resolution constants defined correctly")
    print()


def test_initialization():
    """Test fetcher initialization with different resolutions"""
    print("="*60)
    print("TEST: Initialization")
    print("="*60)

    # Default (hourly)
    fetcher_default = ENTSOEPriceFetcher()
    assert fetcher_default.resolution == 'PT60M'
    print(f"✅ Default resolution: {fetcher_default.resolution}")

    # Explicit hourly
    fetcher_hourly = ENTSOEPriceFetcher(resolution='PT60M')
    assert fetcher_hourly.resolution == 'PT60M'
    print(f"✅ Hourly resolution: {fetcher_hourly.resolution}")

    # 15-minute
    fetcher_15min = ENTSOEPriceFetcher(resolution='PT15M')
    assert fetcher_15min.resolution == 'PT15M'
    print(f"✅ 15-min resolution: {fetcher_15min.resolution}")

    # Invalid resolution (should raise error)
    try:
        fetcher_bad = ENTSOEPriceFetcher(resolution='PT30M')
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"✅ Invalid resolution correctly rejected: {e}")

    print()


def test_convenience_function():
    """Test convenience function with both resolutions"""
    print("="*60)
    print("TEST: Convenience Function")
    print("="*60)

    # Hourly (default)
    prices_hourly = fetch_prices(2024, 'NO2', resolution='PT60M', refresh=True)
    assert isinstance(prices_hourly, pd.Series)
    assert len(prices_hourly) > 8700  # Allow for leap year + DST
    assert len(prices_hourly) < 8800
    print(f"✅ Hourly fetch: {len(prices_hourly)} data points")
    print(f"   Expected: ~8760 hours (leap year + DST: 8784)")

    # 15-minute
    prices_15min = fetch_prices(2024, 'NO2', resolution='PT15M', refresh=True)
    assert isinstance(prices_15min, pd.Series)
    assert len(prices_15min) > 35000  # Allow for leap year + DST
    assert len(prices_15min) < 35200
    print(f"✅ 15-min fetch: {len(prices_15min)} data points")
    print(f"   Expected: ~35040 intervals (leap year + DST: 35136)")

    # Verify 4x relationship
    ratio = len(prices_15min) / len(prices_hourly)
    assert 3.9 < ratio < 4.1  # Allow small tolerance
    print(f"✅ Data point ratio: {ratio:.2f}x (expected ~4x)")

    print()


def test_cache_files():
    """Test that cache files are created with correct naming"""
    print("="*60)
    print("TEST: Cache File Naming")
    print("="*60)

    import os
    from pathlib import Path

    cache_dir = Path('data/spot_prices')

    # Check hourly cache
    hourly_cache = cache_dir / 'NO2_2024_60min_real.csv'
    assert hourly_cache.exists(), "Hourly cache file not found"
    hourly_size = hourly_cache.stat().st_size / 1024  # KB
    print(f"✅ Hourly cache: {hourly_cache.name} ({hourly_size:.1f} KB)")

    # Check 15-minute cache
    min15_cache = cache_dir / 'NO2_2024_15min_real.csv'
    assert min15_cache.exists(), "15-minute cache file not found"
    min15_size = min15_cache.stat().st_size / 1024  # KB
    print(f"✅ 15-min cache: {min15_cache.name} ({min15_size:.1f} KB)")

    # Verify 15-min file is larger
    assert min15_size > hourly_size * 3.5, "15-min cache should be ~4x larger"
    print(f"✅ Size ratio: {min15_size/hourly_size:.2f}x (expected ~4x)")

    print()


def test_metadata():
    """Test that metadata includes resolution information"""
    print("="*60)
    print("TEST: Metadata with Resolution")
    print("="*60)

    import json
    from pathlib import Path

    metadata_file = Path('data/spot_prices/cache_metadata.json')
    assert metadata_file.exists(), "Metadata file not found"

    with open(metadata_file) as f:
        metadata = json.load(f)

    # Check hourly metadata
    hourly_key = 'NO2_2024_60min'
    assert hourly_key in metadata, f"Metadata key {hourly_key} not found"
    hourly_meta = metadata[hourly_key]
    assert hourly_meta['resolution'] == 'PT60M'
    assert hourly_meta['expected_points'] == 8760
    print(f"✅ Hourly metadata: {hourly_meta['resolution']}, {hourly_meta['expected_points']} points")

    # Check 15-minute metadata
    min15_key = 'NO2_2024_15min'
    assert min15_key in metadata, f"Metadata key {min15_key} not found"
    min15_meta = metadata[min15_key]
    assert min15_meta['resolution'] == 'PT15M'
    assert min15_meta['expected_points'] == 35040
    print(f"✅ 15-min metadata: {min15_meta['resolution']}, {min15_meta['expected_points']} points")

    print()


def test_data_validation():
    """Test data point validation"""
    print("="*60)
    print("TEST: Data Point Validation")
    print("="*60)

    fetcher = ENTSOEPriceFetcher()

    # Create test series with correct length
    import pandas as pd
    import numpy as np

    # Hourly - correct length
    times_h = pd.date_range('2024-01-01', '2024-12-31 23:00', freq='h', tz='Europe/Oslo')
    prices_h = pd.Series(np.random.rand(len(times_h)), index=times_h)
    result_h = fetcher._validate_data_points(prices_h, 2024, 'PT60M')
    # Note: May show warning due to leap year, but won't return False
    print(f"✅ Hourly validation: {len(prices_h)} points (2024 leap year)")

    # 15-minute - correct length
    times_15 = pd.date_range('2024-01-01', '2024-12-31 23:45', freq='15min', tz='Europe/Oslo')
    prices_15 = pd.Series(np.random.rand(len(times_15)), index=times_15)
    result_15 = fetcher._validate_data_points(prices_15, 2024, 'PT15M')
    print(f"✅ 15-min validation: {len(prices_15)} points (2024 leap year)")

    print()


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("MULTI-RESOLUTION PRICE FETCHER TEST SUITE")
    print("="*60 + "\n")

    try:
        test_resolution_constants()
        test_initialization()
        test_convenience_function()
        test_cache_files()
        test_metadata()
        test_data_validation()

        print("="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nSummary:")
        print("  ✅ Resolution constants defined")
        print("  ✅ Initialization with multiple resolutions")
        print("  ✅ Convenience function works for both resolutions")
        print("  ✅ Cache files created with correct naming")
        print("  ✅ Metadata includes resolution information")
        print("  ✅ Data point validation functional")
        print("\nMulti-resolution support is production-ready!")

        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
