"""
Create minimal test data files for integration tests.

This script creates small sample data files for fast integration testing.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta


def create_test_data(output_dir: Path, days: int = 7):
    """
    Create test data files for integration tests.

    Args:
        output_dir: Directory to save test data
        days: Number of days of data to create
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create hourly timestamps for specified days
    start_date = datetime(2024, 1, 1)
    timestamps_hourly = pd.date_range(start_date, periods=days*24, freq='H')

    # Create 15-minute timestamps
    timestamps_15min = pd.date_range(start_date, periods=days*24*4, freq='15T')

    # 1. Prices (hourly)
    # Simple pattern: higher during day, lower at night
    prices_hourly = []
    for ts in timestamps_hourly:
        if 6 <= ts.hour < 22 and ts.weekday() < 5:
            base_price = 0.8  # Peak hours weekday
        else:
            base_price = 0.4  # Off-peak
        noise = np.random.normal(0, 0.1)
        prices_hourly.append(max(0.1, base_price + noise))

    prices_df = pd.DataFrame({
        'timestamp': timestamps_hourly,
        'price_nok_per_kwh': prices_hourly
    })
    prices_df.to_csv(output_dir / 'test_prices_hourly.csv', index=False)

    # 2. Production (hourly)
    # Simple solar pattern: zero at night, peak at noon
    production_hourly = []
    for ts in timestamps_hourly:
        if 6 <= ts.hour < 20:
            # Sine curve for solar production
            hour_angle = (ts.hour - 13) / 7 * np.pi
            production = max(0, 50 * np.cos(hour_angle) + np.random.normal(0, 5))
        else:
            production = 0
        production_hourly.append(production)

    production_df = pd.DataFrame({
        'timestamp': timestamps_hourly,
        'production_kw': production_hourly
    })
    production_df.to_csv(output_dir / 'test_production_hourly.csv', index=False)

    # 3. Consumption (hourly)
    # Simple commercial pattern: high during business hours
    consumption_hourly = []
    for ts in timestamps_hourly:
        if 8 <= ts.hour < 18 and ts.weekday() < 5:
            base_load = 30 + np.random.normal(0, 3)  # Business hours
        elif 6 <= ts.hour < 22:
            base_load = 15 + np.random.normal(0, 2)  # Extended hours
        else:
            base_load = 5 + np.random.normal(0, 1)   # Night
        consumption_hourly.append(max(0, base_load))

    consumption_df = pd.DataFrame({
        'timestamp': timestamps_hourly,
        'consumption_kw': consumption_hourly
    })
    consumption_df.to_csv(output_dir / 'test_consumption_hourly.csv', index=False)

    # 4. Create 15-minute versions by interpolation
    prices_15min = np.repeat(prices_hourly, 4)
    production_15min = np.repeat(production_hourly, 4)
    consumption_15min = np.repeat(consumption_hourly, 4)

    prices_15min_df = pd.DataFrame({
        'timestamp': timestamps_15min,
        'price_nok_per_kwh': prices_15min
    })
    prices_15min_df.to_csv(output_dir / 'test_prices_15min.csv', index=False)

    production_15min_df = pd.DataFrame({
        'timestamp': timestamps_15min,
        'production_kw': production_15min
    })
    production_15min_df.to_csv(output_dir / 'test_production_15min.csv', index=False)

    consumption_15min_df = pd.DataFrame({
        'timestamp': timestamps_15min,
        'consumption_kw': consumption_15min
    })
    consumption_15min_df.to_csv(output_dir / 'test_consumption_15min.csv', index=False)

    print(f"Created test data in {output_dir}:")
    print(f"  - Hourly data: {days} days ({len(timestamps_hourly)} timesteps)")
    print(f"  - 15-min data: {days} days ({len(timestamps_15min)} timesteps)")


if __name__ == "__main__":
    fixtures_dir = Path(__file__).parent
    create_test_data(fixtures_dir, days=7)
