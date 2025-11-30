"""
Script to load and pivot consumption data from Måleverdier_COMBINED_ALL.csv
Separates consumption and production into separate columns.
"""

import pandas as pd
from pathlib import Path


def load_consumption_data(file_path: str = None) -> pd.DataFrame:
    """
    Load consumption data from CSV and pivot to separate consumption/production columns.

    Args:
        file_path: Path to CSV file. If None, uses default location.

    Returns:
        DataFrame with columns:
        - timestamp: Start time of measurement period
        - forbruk_kwh: Consumption in kWh
        - produksjon_kwh: Production in kWh
    """
    if file_path is None:
        file_path = Path(__file__).parent.parent / "data" / "consumption" / "Måleverdier_COMBINED_ALL.csv"

    # Read CSV with semicolon separator
    df = pd.read_csv(file_path, sep=";", encoding="utf-8")

    # Parse datetime columns (convert to UTC to handle mixed timezones)
    df['Fra'] = pd.to_datetime(df['Fra'], utc=True)
    df['Til'] = pd.to_datetime(df['Til'], utc=True)

    # Extract measurement type from Målenavn (Forbruk or Produksjon)
    df['type'] = df['Målenavn'].str.extract(r'(Forbruk|Produksjon)')[0]

    # Pivot: rows become timestamps, columns become forbruk/produksjon
    pivot_df = df.pivot_table(
        index='Fra',
        columns='type',
        values='Volum',
        aggfunc='first'  # Take first value if duplicates exist
    ).reset_index()

    # Rename columns for clarity
    pivot_df.columns.name = None  # Remove multi-index name

    # Handle cases where only one type exists
    column_mapping = {'Fra': 'timestamp'}
    if 'Forbruk' in pivot_df.columns:
        column_mapping['Forbruk'] = 'forbruk_kwh'
    if 'Produksjon' in pivot_df.columns:
        column_mapping['Produksjon'] = 'produksjon_kwh'

    pivot_df = pivot_df.rename(columns=column_mapping)

    # Ensure both columns exist, fill with 0 if missing
    if 'forbruk_kwh' not in pivot_df.columns:
        pivot_df['forbruk_kwh'] = 0.0
    if 'produksjon_kwh' not in pivot_df.columns:
        pivot_df['produksjon_kwh'] = 0.0

    # Fill NaN values with 0 (missing data points in time series)
    pivot_df['forbruk_kwh'] = pivot_df['forbruk_kwh'].fillna(0)
    pivot_df['produksjon_kwh'] = pivot_df['produksjon_kwh'].fillna(0)

    # Sort by timestamp
    pivot_df = pivot_df.sort_values('timestamp').reset_index(drop=True)

    return pivot_df


def print_data_summary(df: pd.DataFrame):
    """Print summary statistics of the loaded data."""
    print("\n" + "="*60)
    print("DATA SUMMARY")
    print("="*60)
    print(f"\nTotal records: {len(df):,}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

    print("\nForbruk (Consumption):")
    print(f"  Total: {df['forbruk_kwh'].sum():,.1f} kWh")
    print(f"  Mean: {df['forbruk_kwh'].mean():.2f} kWh/hour")
    print(f"  Max: {df['forbruk_kwh'].max():.2f} kWh")
    print(f"  Min: {df['forbruk_kwh'].min():.2f} kWh")

    print("\nProduksjon (Production):")
    print(f"  Total: {df['produksjon_kwh'].sum():,.1f} kWh")
    print(f"  Mean: {df['produksjon_kwh'].mean():.2f} kWh/hour")
    print(f"  Max: {df['produksjon_kwh'].max():.2f} kWh")
    print(f"  Min: {df['produksjon_kwh'].min():.2f} kWh")

    print("\nNett Export (Production - Consumption):")
    nett_export = df['produksjon_kwh'] - df['forbruk_kwh']
    print(f"  Total: {nett_export.sum():,.1f} kWh")
    print(f"  Mean: {nett_export.mean():.2f} kWh/hour")

    print("\nFirst 5 rows:")
    print(df.head())

    print("\nLast 5 rows:")
    print(df.tail())
    print("="*60 + "\n")


if __name__ == "__main__":
    # Load data
    df = load_consumption_data()

    # Print summary
    print_data_summary(df)

    # Save to processed file for easy reuse
    output_path = Path(__file__).parent.parent / "data" / "consumption" / "processed_consumption_data.csv"
    df.to_csv(output_path, index=False)
    print(f"Processed data saved to: {output_path}")
