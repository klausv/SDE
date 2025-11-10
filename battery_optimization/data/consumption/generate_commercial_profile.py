"""
Generate simple commercial consumption profile.

Creates a realistic commercial load profile with:
- Base load: 20 kW
- Peak hours (Mon-Fri 06:00-22:00): 35-50 kW
- Off-peak: 15-25 kW
- Annual total: ~300 MWh
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_commercial_2024_hourly():
    """Generate hourly commercial load profile for 2024."""

    # Create hourly timestamps for 2024
    start = datetime(2024, 1, 1, 0, 0)
    end = datetime(2024, 12, 31, 23, 0)
    timestamps = pd.date_range(start, end, freq='h')

    # Initialize load array
    n = len(timestamps)
    load_kw = np.zeros(n)

    # Base load
    base_load = 20.0

    for i, ts in enumerate(timestamps):
        hour = ts.hour
        weekday = ts.weekday()  # 0=Monday, 6=Sunday

        # Commercial pattern
        if weekday < 5:  # Monday-Friday
            if 6 <= hour < 22:  # Peak hours
                # Peak load with variation
                peak_load = 45.0 + np.random.normal(0, 5)
                load_kw[i] = max(base_load, peak_load)
            else:  # Night
                load_kw[i] = base_load + np.random.normal(0, 3)
        else:  # Weekend
            # Reduced weekend load
            load_kw[i] = base_load * 0.7 + np.random.normal(0, 2)

    # Ensure non-negative
    load_kw = np.maximum(load_kw, 0)

    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': timestamps,
        'consumption_kw': load_kw
    })

    df.set_index('timestamp', inplace=True)

    # Print statistics
    total_kwh = load_kw.sum()
    print(f"Generated commercial load profile:")
    print(f"  Annual consumption: {total_kwh/1000:.1f} MWh")
    print(f"  Mean load: {load_kw.mean():.1f} kW")
    print(f"  Peak load: {load_kw.max():.1f} kW")
    print(f"  Min load: {load_kw.min():.1f} kW")

    return df

if __name__ == "__main__":
    df = generate_commercial_2024_hourly()
    output_file = "data/consumption/commercial_2024.csv"
    df.to_csv(output_file)
    print(f"\n✅ Saved to: {output_file}")
