#!/usr/bin/env python3
"""
Analyze the difference between 15-minute and hourly spot prices.

Compares:
1. Mean absolute difference between 15-min prices and their hourly average
2. Volatility captured by 15-min resolution that hourly misses
"""

import numpy as np
import pandas as pd
from core.price_fetcher import fetch_prices

def analyze_price_resolution_difference():
    """
    Compare 15-minute spot prices with hourly averages.
    """
    print("\n" + "="*80)
    print("PRICE RESOLUTION ANALYSIS: 15-MIN vs HOURLY")
    print("="*80)
    print("\nPeriod: September 30 - October 31, 2025")

    # Fetch prices for both resolutions
    print("\n📊 Fetching spot prices...")
    prices_hourly = fetch_prices(2025, 'NO2', resolution='PT60M')
    prices_15min = fetch_prices(2025, 'NO2', resolution='PT15M')

    # Filter to Sept 30 - Oct 31 period
    start_date = pd.Timestamp('2025-09-30', tz='Europe/Oslo')
    end_date = pd.Timestamp('2025-10-31 23:59', tz='Europe/Oslo')

    prices_hourly = prices_hourly.loc[start_date:end_date]
    prices_15min = prices_15min.loc[start_date:end_date]

    print(f"  Hourly prices: {len(prices_hourly)} data points")
    print(f"  15-min prices: {len(prices_15min)} data points")
    print(f"  Ratio: {len(prices_15min) / len(prices_hourly):.1f}x")

    # Calculate hourly average from 15-min data for comparison
    # Group 15-min data into hourly buckets
    prices_15min_hourly_avg = prices_15min.resample('h').mean()

    # Align timestamps
    common_hours = prices_hourly.index.intersection(prices_15min_hourly_avg.index)
    hourly_aligned = prices_hourly.loc[common_hours]
    hourly_from_15min = prices_15min_hourly_avg.loc[common_hours]

    print(f"\n  Aligned hours for comparison: {len(common_hours)}")

    # Calculate differences between hourly API data and hourly average from 15-min
    print("\n" + "="*80)
    print("COMPARISON 1: Hourly API Prices vs Hourly Average from 15-min Data")
    print("="*80)

    diff_hourly = np.abs(hourly_aligned.values - hourly_from_15min.values)
    print(f"\nMean Absolute Difference: {diff_hourly.mean():.4f} kr/kWh")
    print(f"Max Difference:           {diff_hourly.max():.4f} kr/kWh")
    print(f"Std Deviation:            {diff_hourly.std():.4f} kr/kWh")

    # Calculate intra-hour volatility captured by 15-min resolution
    print("\n" + "="*80)
    print("COMPARISON 2: Intra-Hour Price Volatility (15-min Resolution)")
    print("="*80)

    # For each hour, calculate the standard deviation of 4x 15-min prices
    prices_15min_grouped = prices_15min.groupby(pd.Grouper(freq='h'))

    intra_hour_stds = []
    intra_hour_ranges = []

    for hour, group in prices_15min_grouped:
        if len(group) == 4:  # Full hour with 4x 15-min intervals
            intra_hour_stds.append(group.std())
            intra_hour_ranges.append(group.max() - group.min())

    mean_intra_hour_std = np.mean(intra_hour_stds)
    mean_intra_hour_range = np.mean(intra_hour_ranges)

    print(f"\nMean Intra-Hour Std Dev:  {mean_intra_hour_std:.4f} kr/kWh")
    print(f"Mean Intra-Hour Range:    {mean_intra_hour_range:.4f} kr/kWh")
    print(f"Max Intra-Hour Range:     {np.max(intra_hour_ranges):.4f} kr/kWh")

    # Calculate mean absolute difference between each 15-min price and its hourly average
    print("\n" + "="*80)
    print("COMPARISON 3: 15-Min Price Deviation from Hourly Average")
    print("="*80)

    deviations = []
    for hour, group in prices_15min_grouped:
        if len(group) == 4:
            hour_avg = group.mean()
            deviations.extend(np.abs(group.values - hour_avg))

    mean_abs_deviation = np.mean(deviations)

    print(f"\nMean Absolute Deviation:  {mean_abs_deviation:.4f} kr/kWh")
    print(f"This represents the average price variation within each hour")
    print(f"that is 'smoothed out' when using hourly resolution.")

    # Price statistics
    print("\n" + "="*80)
    print("OVERALL PRICE STATISTICS")
    print("="*80)

    print(f"\nHourly Resolution (PT60M):")
    print(f"  Mean:   {prices_hourly.mean():.3f} kr/kWh")
    print(f"  Std:    {prices_hourly.std():.3f} kr/kWh")
    print(f"  Min:    {prices_hourly.min():.3f} kr/kWh")
    print(f"  Max:    {prices_hourly.max():.3f} kr/kWh")

    print(f"\n15-Minute Resolution (PT15M):")
    print(f"  Mean:   {prices_15min.mean():.3f} kr/kWh")
    print(f"  Std:    {prices_15min.std():.3f} kr/kWh")
    print(f"  Min:    {prices_15min.min():.3f} kr/kWh")
    print(f"  Max:    {prices_15min.max():.3f} kr/kWh")

    # Arbitrage opportunity analysis
    print("\n" + "="*80)
    print("ARBITRAGE OPPORTUNITY ANALYSIS")
    print("="*80)

    # Count significant intra-hour price swings (>10% of hourly average)
    significant_swings = []
    for hour, group in prices_15min_grouped:
        if len(group) == 4:
            hour_avg = group.mean()
            if hour_avg > 0:
                max_swing_pct = (group.max() - group.min()) / hour_avg * 100
                if max_swing_pct > 10:
                    significant_swings.append(max_swing_pct)

    print(f"\nHours with >10% intra-hour price swing: {len(significant_swings)} / {len(common_hours)}")
    print(f"Percentage: {len(significant_swings) / len(common_hours) * 100:.1f}%")

    if significant_swings:
        print(f"\nAmong hours with significant swings:")
        print(f"  Mean swing:  {np.mean(significant_swings):.1f}%")
        print(f"  Max swing:   {np.max(significant_swings):.1f}%")

    print("\n" + "="*80)
    print("INTERPRETATION")
    print("="*80)

    print(f"""
The mean absolute deviation of {mean_abs_deviation:.4f} kr/kWh represents the
average 'price detail' that 15-minute resolution captures within each hour.

This intra-hour price variation creates opportunities for:
1. More precise arbitrage timing (buy at 15-min low, sell at 15-min high)
2. Better alignment with actual battery charging/discharging decisions
3. Capturing short-term price spikes that hourly averaging smooths out

However, the modest savings (1.5%) suggest that for this battery configuration
(30 kWh / 15 kW), the battery's power/energy constraints limit the ability
to fully exploit these intra-hour price variations.
""")

if __name__ == "__main__":
    analyze_price_resolution_difference()
