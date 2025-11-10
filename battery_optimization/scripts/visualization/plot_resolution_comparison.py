#!/usr/bin/env python3
"""
Plot NO2 electricity prices comparing hourly and 15-minute resolution
From September 30, 2025 (transition date) until now
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from core.price_fetcher import fetch_prices
import numpy as np


def fetch_price_range(start_date, end_date, area='NO2', resolution='PT60M'):
    """
    Fetch prices for a date range

    Args:
        start_date: Start date string 'YYYY-MM-DD'
        end_date: End date string 'YYYY-MM-DD'
        area: Bidding zone
        resolution: Time resolution

    Returns:
        Series with prices in date range
    """
    start = pd.Timestamp(start_date, tz='Europe/Oslo')
    end = pd.Timestamp(end_date, tz='Europe/Oslo')

    # Fetch full year data (will be cached)
    year = start.year
    prices = fetch_prices(year, area, resolution=resolution)

    # Filter to date range
    mask = (prices.index >= start) & (prices.index <= end)
    return prices[mask]


def plot_resolution_comparison():
    """Plot hourly vs 15-minute resolution comparison"""

    print("="*60)
    print("ELECTRICITY PRICE RESOLUTION COMPARISON")
    print("="*60)
    print("\nFetching price data...")
    print("Period: September 30, 2025 - October 31, 2025")
    print("Area: NO2 (Stavanger)")
    print()

    # Define date range
    start_date = '2025-09-30'
    end_date = '2025-10-31'

    # Fetch both resolutions
    print("📡 Fetching hourly prices (PT60M)...")
    prices_hourly = fetch_price_range(start_date, end_date, resolution='PT60M')
    print(f"   Retrieved {len(prices_hourly)} hourly data points")

    print("\n📡 Fetching 15-minute prices (PT15M)...")
    prices_15min = fetch_price_range(start_date, end_date, resolution='PT15M')
    print(f"   Retrieved {len(prices_15min)} 15-minute data points")

    print(f"\n📊 Data point ratio: {len(prices_15min) / len(prices_hourly):.2f}x")

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))
    fig.suptitle('NO2 Electricity Spot Prices: Hourly vs 15-Minute Resolution\n'
                 'September 30 - October 31, 2025',
                 fontsize=16, fontweight='bold')

    # Subplot 1: Full period comparison
    ax1.plot(prices_hourly.index, prices_hourly.values,
             label='Hourly (PT60M)', linewidth=2, alpha=0.7, color='#2E86AB')
    ax1.plot(prices_15min.index, prices_15min.values,
             label='15-minute (PT15M)', linewidth=1, alpha=0.6, color='#A23B72')

    ax1.set_ylabel('Price (NOK/kWh)', fontsize=12)
    ax1.set_title('Full Period Overview (1 month)', fontsize=13, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='red', linestyle='--', linewidth=0.5, alpha=0.5)

    # Format x-axis
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Subplot 2: Zoomed in to 3 days to show resolution difference
    zoom_start = pd.Timestamp('2025-10-15', tz='Europe/Oslo')
    zoom_end = pd.Timestamp('2025-10-18', tz='Europe/Oslo')

    mask_h = (prices_hourly.index >= zoom_start) & (prices_hourly.index <= zoom_end)
    mask_15 = (prices_15min.index >= zoom_start) & (prices_15min.index <= zoom_end)

    zoom_hourly = prices_hourly[mask_h]
    zoom_15min = prices_15min[mask_15]

    ax2.plot(zoom_hourly.index, zoom_hourly.values,
             label='Hourly (PT60M)', linewidth=2.5, alpha=0.8,
             color='#2E86AB', marker='o', markersize=5)
    ax2.plot(zoom_15min.index, zoom_15min.values,
             label='15-minute (PT15M)', linewidth=1.5, alpha=0.7,
             color='#A23B72', marker='.', markersize=3)

    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Price (NOK/kWh)', fontsize=12)
    ax2.set_title('Detail View: 3-Day Period (15-18 Oct) - Resolution Comparison',
                  fontsize=13, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='red', linestyle='--', linewidth=0.5, alpha=0.5)

    # Format x-axis for zoomed view
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d %b %H:%M'))
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()

    # Save figure
    output_file = 'results/resolution_comparison_sept_oct_2025.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n💾 Plot saved: {output_file}")

    # Display statistics
    print("\n" + "="*60)
    print("STATISTICS")
    print("="*60)

    print("\nHourly Resolution (PT60M):")
    print(f"  Data points: {len(prices_hourly)}")
    print(f"  Mean price:  {prices_hourly.mean():.3f} NOK/kWh")
    print(f"  Min price:   {prices_hourly.min():.3f} NOK/kWh")
    print(f"  Max price:   {prices_hourly.max():.3f} NOK/kWh")
    print(f"  Std dev:     {prices_hourly.std():.3f} NOK/kWh")

    print("\n15-Minute Resolution (PT15M):")
    print(f"  Data points: {len(prices_15min)}")
    print(f"  Mean price:  {prices_15min.mean():.3f} NOK/kWh")
    print(f"  Min price:   {prices_15min.min():.3f} NOK/kWh")
    print(f"  Max price:   {prices_15min.max():.3f} NOK/kWh")
    print(f"  Std dev:     {prices_15min.std():.3f} NOK/kWh")

    # Price volatility comparison
    hourly_changes = prices_hourly.diff().abs().mean()
    min15_changes = prices_15min.diff().abs().mean()

    print("\nPrice Volatility (Mean Absolute Change):")
    print(f"  Hourly:    {hourly_changes:.4f} NOK/kWh per interval")
    print(f"  15-minute: {min15_changes:.4f} NOK/kWh per interval")

    # Peak detection
    hourly_peaks = (prices_hourly > prices_hourly.quantile(0.9)).sum()
    min15_peaks = (prices_15min > prices_15min.quantile(0.9)).sum()

    print("\nPrice Spikes (>90th percentile):")
    print(f"  Hourly:    {hourly_peaks} occurrences")
    print(f"  15-minute: {min15_peaks} occurrences")

    print("\n" + "="*60)
    print("KEY INSIGHTS")
    print("="*60)
    print("\n✅ 15-minute resolution provides:")
    print(f"   • {len(prices_15min) / len(prices_hourly):.1f}x more data points")
    print(f"   • Better capture of price spikes: {min15_peaks} vs {hourly_peaks}")
    print(f"   • More precise arbitrage opportunities")
    print(f"   • Improved battery control granularity")

    print("\n📈 Battery Optimization Impact:")
    print("   • Hourly: Good for strategic planning")
    print("   • 15-min: Better for real-time operations and intraday trading")

    print("\n" + "="*60)

    plt.show()


if __name__ == "__main__":
    plot_resolution_comparison()
