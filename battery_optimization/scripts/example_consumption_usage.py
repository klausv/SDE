"""
Example usage of the consumption data loading function.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from load_consumption_data import load_consumption_data
import pandas as pd


def main():
    # Load the data
    df = load_consumption_data()

    print("="*60)
    print("EXAMPLE USAGE OF CONSUMPTION DATA")
    print("="*60)

    # Example 1: Filter by date range
    print("\n1. Filter for June 2024:")
    june_2024 = df[
        (df['timestamp'] >= pd.Timestamp('2024-06-01', tz='UTC')) &
        (df['timestamp'] < pd.Timestamp('2024-07-01', tz='UTC'))
    ]
    print(f"   Records: {len(june_2024)}")
    print(f"   Consumption: {june_2024['forbruk_kwh'].sum():.1f} kWh")
    print(f"   Production: {june_2024['produksjon_kwh'].sum():.1f} kWh")

    # Example 2: Calculate net consumption by month
    print("\n2. Monthly net consumption (Production - Consumption):")
    df['month'] = df['timestamp'].dt.to_period('M')
    monthly = df.groupby('month').agg({
        'forbruk_kwh': 'sum',
        'produksjon_kwh': 'sum'
    })
    monthly['nett_kwh'] = monthly['produksjon_kwh'] - monthly['forbruk_kwh']
    print(monthly.tail(12))  # Last 12 months

    # Example 3: Find peak consumption hours
    print("\n3. Top 10 peak consumption hours:")
    top_consumption = df.nlargest(10, 'forbruk_kwh')[['timestamp', 'forbruk_kwh', 'produksjon_kwh']]
    print(top_consumption)

    # Example 4: Find peak production hours
    print("\n4. Top 10 peak production hours:")
    top_production = df.nlargest(10, 'produksjon_kwh')[['timestamp', 'forbruk_kwh', 'produksjon_kwh']]
    print(top_production)

    # Example 5: Calculate self-consumption ratio
    print("\n5. Self-consumption analysis:")
    total_production = df['produksjon_kwh'].sum()
    total_consumption = df['forbruk_kwh'].sum()

    # Self-consumed = min(production, consumption) per hour
    df['self_consumed'] = df[['forbruk_kwh', 'produksjon_kwh']].min(axis=1)
    total_self_consumed = df['self_consumed'].sum()

    self_consumption_rate = (total_self_consumed / total_production * 100) if total_production > 0 else 0
    self_sufficiency_rate = (total_self_consumed / total_consumption * 100) if total_consumption > 0 else 0

    print(f"   Total production: {total_production:,.1f} kWh")
    print(f"   Total consumption: {total_consumption:,.1f} kWh")
    print(f"   Self-consumed: {total_self_consumed:,.1f} kWh")
    print(f"   Self-consumption rate: {self_consumption_rate:.1f}% (of production used locally)")
    print(f"   Self-sufficiency rate: {self_sufficiency_rate:.1f}% (of consumption from solar)")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
