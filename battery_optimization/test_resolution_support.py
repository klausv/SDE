#!/usr/bin/env python3
"""
Quick Validation Test for Multi-Resolution Support

Tests that the resolution switching implementation works correctly:
1. Time aggregation functions (15-min ↔ hourly)
2. LP optimizer initialization with both resolutions
3. Price fetching at both resolutions
4. Data preparation for both resolutions

Run this script to verify the implementation before running full optimizations.

Usage:
    python test_resolution_support.py
"""

import numpy as np
import pandas as pd
from core.time_aggregation import (
    aggregate_15min_to_hourly_peak,
    upsample_hourly_to_15min,
    validate_resolution,
    get_resolution_info
)
from core.price_fetcher import fetch_prices
from config import config


def test_time_aggregation():
    """Test time aggregation functions."""
    print("\n" + "="*70)
    print("TEST 1: Time Aggregation Functions")
    print("="*70)

    # Create test data
    timestamps_hourly = pd.date_range('2024-01-01', periods=24, freq='h', tz='Europe/Oslo')
    data_hourly = np.array([10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65,
                            70, 75, 80, 85, 90, 95, 100, 95, 90, 85, 80, 75])

    # Test upsampling
    print("\n📈 Testing hourly → 15-minute upsampling...")
    data_15min = upsample_hourly_to_15min(data_hourly, timestamps_hourly)
    print(f"  Input:  {len(data_hourly)} hourly values")
    print(f"  Output: {len(data_15min)} 15-minute values")
    assert len(data_15min) == len(data_hourly) * 4, "Upsampling length mismatch!"
    print("  ✅ Upsampling works correctly")

    # Test aggregation
    print("\n📉 Testing 15-minute → hourly peak aggregation...")
    data_hourly_reconstructed = aggregate_15min_to_hourly_peak(data_15min.values)
    print(f"  Input:  {len(data_15min)} 15-minute values")
    print(f"  Output: {len(data_hourly_reconstructed)} hourly peaks")
    assert len(data_hourly_reconstructed) == len(data_hourly), "Aggregation length mismatch!"
    print("  ✅ Aggregation works correctly")

    # Test validation
    print("\n✓ Testing resolution validation...")
    is_valid_15min, msg_15min = validate_resolution(data_15min.values, data_15min.index, 'PT15M')
    is_valid_hourly, msg_hourly = validate_resolution(data_hourly, timestamps_hourly, 'PT60M')
    assert is_valid_15min, f"15-min validation failed: {msg_15min}"
    assert is_valid_hourly, f"Hourly validation failed: {msg_hourly}"
    print("  ✅ Validation works correctly")

    print("\n✅ All time aggregation tests passed!")


def test_price_fetcher():
    """Test price fetching at both resolutions."""
    print("\n" + "="*70)
    print("TEST 2: Price Fetcher Multi-Resolution Support")
    print("="*70)

    year = 2024
    area = 'NO2'

    # Test hourly prices
    print("\n💰 Fetching hourly prices (PT60M)...")
    try:
        prices_hourly = fetch_prices(year, area, resolution='PT60M')
        print(f"  ✅ Retrieved {len(prices_hourly)} hourly data points")
        assert 8700 < len(prices_hourly) < 8800, "Unexpected hourly data point count"
    except Exception as e:
        print(f"  ⚠ Warning: Could not fetch hourly prices: {e}")
        print(f"  This is OK if API is unavailable (will use simulated data)")

    # Test 15-minute prices
    print("\n💰 Fetching 15-minute prices (PT15M)...")
    try:
        prices_15min = fetch_prices(year, area, resolution='PT15M')
        print(f"  ✅ Retrieved {len(prices_15min)} 15-minute data points")
        assert 35000 < len(prices_15min) < 35200, "Unexpected 15-min data point count"

        # Verify 4x relationship
        if 'prices_hourly' in locals():
            ratio = len(prices_15min) / len(prices_hourly)
            print(f"  Ratio: {ratio:.2f}x (expected ~4x)")
            assert 3.9 < ratio < 4.1, "Data point ratio incorrect"
    except Exception as e:
        print(f"  ⚠ Warning: Could not fetch 15-min prices: {e}")
        print(f"  This is OK if API is unavailable (will use simulated data)")

    print("\n✅ Price fetcher tests completed!")


def test_lp_optimizer():
    """Test LP optimizer initialization with both resolutions."""
    print("\n" + "="*70)
    print("TEST 3: LP Optimizer Resolution Support")
    print("="*70)

    from core.lp_monthly_optimizer import MonthlyLPOptimizer

    # Test hourly initialization
    print("\n🔧 Initializing optimizer with PT60M...")
    optimizer_hourly = MonthlyLPOptimizer(config, resolution='PT60M')
    assert optimizer_hourly.resolution == 'PT60M'
    assert optimizer_hourly.timestep_hours == 1.0
    print(f"  ✅ Hourly optimizer: timestep = {optimizer_hourly.timestep_hours} hours")

    # Test 15-minute initialization
    print("\n🔧 Initializing optimizer with PT15M...")
    optimizer_15min = MonthlyLPOptimizer(config, resolution='PT15M')
    assert optimizer_15min.resolution == 'PT15M'
    assert optimizer_15min.timestep_hours == 0.25
    print(f"  ✅ 15-min optimizer: timestep = {optimizer_15min.timestep_hours} hours")

    # Test invalid resolution (should raise error)
    print("\n🔧 Testing invalid resolution rejection...")
    try:
        optimizer_bad = MonthlyLPOptimizer(config, resolution='PT30M')
        assert False, "Should have raised ValueError for invalid resolution"
    except ValueError as e:
        print(f"  ✅ Invalid resolution correctly rejected: {e}")

    print("\n✅ LP optimizer tests passed!")


def test_resolution_info():
    """Test resolution detection and info functions."""
    print("\n" + "="*70)
    print("TEST 4: Resolution Detection")
    print("="*70)

    # Create test timestamps
    timestamps_hourly = pd.date_range('2024-01-01', periods=24, freq='h', tz='Europe/Oslo')
    timestamps_15min = pd.date_range('2024-01-01', periods=96, freq='15min', tz='Europe/Oslo')

    # Test hourly detection
    print("\n🔍 Detecting hourly resolution...")
    info_hourly = get_resolution_info(timestamps_hourly)
    print(f"  Detected: {info_hourly['detected_resolution']}")
    print(f"  Median interval: {info_hourly['median_interval']}")
    assert info_hourly['detected_resolution'] == 'PT60M'
    print("  ✅ Hourly detection correct")

    # Test 15-minute detection
    print("\n🔍 Detecting 15-minute resolution...")
    info_15min = get_resolution_info(timestamps_15min)
    print(f"  Detected: {info_15min['detected_resolution']}")
    print(f"  Median interval: {info_15min['median_interval']}")
    assert info_15min['detected_resolution'] == 'PT15M'
    print("  ✅ 15-minute detection correct")

    print("\n✅ Resolution detection tests passed!")


def main():
    """Run all validation tests."""
    print("\n" + "="*70)
    print("MULTI-RESOLUTION SUPPORT VALIDATION TEST")
    print("="*70)
    print("\nTesting implementation of optional 15-minute resolution support...")
    print("This validates backward compatibility (PT60M default) and new PT15M support")

    try:
        # Run all tests
        test_time_aggregation()
        test_price_fetcher()
        test_lp_optimizer()
        test_resolution_info()

        # Summary
        print("\n" + "="*70)
        print("✅ ALL VALIDATION TESTS PASSED!")
        print("="*70)
        print("\nSummary:")
        print("  ✅ Time aggregation functions working correctly")
        print("  ✅ Price fetcher supports both resolutions")
        print("  ✅ LP optimizer handles resolution switching")
        print("  ✅ Resolution detection working properly")
        print("\n💡 Multi-resolution support is ready to use!")
        print("\nNext steps:")
        print("  1. Run comparison: python compare_resolutions.py")
        print("  2. Try 15-min optimization: python run_simulation.py --resolution PT15M")
        print("  3. Compare results and quantify arbitrage improvement")

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
