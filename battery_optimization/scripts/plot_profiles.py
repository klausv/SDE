"""
Plot consumption and production profiles for the period Dec 2024 - Nov 2025.
Creates three types of plots:
1. Average daily profile (hourly basis) for the year
2. Seasonal profile (monthly aggregation)
3. Monthly daily profiles (hourly basis for each month)
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from load_consumption_data import load_consumption_data


def filter_period(df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    """Filter dataframe for specific period."""
    mask = (df['timestamp'] >= pd.Timestamp(start_date, tz='UTC')) & \
           (df['timestamp'] < pd.Timestamp(end_date, tz='UTC'))
    return df[mask].copy()


def plot_average_daily_profile(df: pd.DataFrame, save_path: Path):
    """
    Plot 1: Average daily profile (hourly basis) for the entire year.
    Shows typical consumption and production pattern over 24 hours.
    """
    # Extract hour from timestamp
    df['hour'] = df['timestamp'].dt.hour

    # Calculate average per hour across all days
    hourly_avg = df.groupby('hour').agg({
        'forbruk_kwh': 'mean',
        'produksjon_kwh': 'mean'
    }).reset_index()

    # Create plot
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(hourly_avg['hour'], hourly_avg['forbruk_kwh'],
            marker='o', linewidth=2, label='Forbruk', color='#d62728')
    ax.plot(hourly_avg['hour'], hourly_avg['produksjon_kwh'],
            marker='s', linewidth=2, label='Produksjon', color='#2ca02c')

    ax.set_xlabel('Time på døgnet', fontsize=12)
    ax.set_ylabel('Gjennomsnittlig effekt (kWh/time)', fontsize=12)
    ax.set_title('Årlig gjennomsnittlig døgnprofil\n(Des 2024 - Nov 2025)',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlim(-0.5, 23.5)

    plt.tight_layout()
    plt.savefig(save_path / 'daily_profile_annual.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {save_path / 'daily_profile_annual.png'}")
    plt.close()


def plot_seasonal_profile(df: pd.DataFrame, save_path: Path):
    """
    Plot 2: Seasonal profile showing monthly totals/averages.
    """
    # Extract month
    df['month'] = df['timestamp'].dt.month

    # Calculate monthly totals
    monthly = df.groupby('month').agg({
        'forbruk_kwh': 'sum',
        'produksjon_kwh': 'sum'
    }).reset_index()

    # Month names in Norwegian
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']

    # Create plot
    fig, ax = plt.subplots(figsize=(14, 6))

    x = np.arange(len(monthly))
    width = 0.35

    bars1 = ax.bar(x - width/2, monthly['forbruk_kwh'], width,
                   label='Forbruk', color='#d62728', alpha=0.8)
    bars2 = ax.bar(x + width/2, monthly['produksjon_kwh'], width,
                   label='Produksjon', color='#2ca02c', alpha=0.8)

    ax.set_xlabel('Måned', fontsize=12)
    ax.set_ylabel('Total energi (kWh)', fontsize=12)
    ax.set_title('Årlig sesongprofil - Månedlige totaler\n(Des 2024 - Nov 2025)',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([month_names[m-1] for m in monthly['month']])
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height):,}',
                   ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    plt.savefig(save_path / 'seasonal_profile_monthly.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {save_path / 'seasonal_profile_monthly.png'}")
    plt.close()


def plot_monthly_daily_profiles(df: pd.DataFrame, save_path: Path):
    """
    Plot 3: Sequential monthly daily profiles (hourly basis).
    X-axis shows continuous time over the year: 12 months × 24 hours = 288 points.
    Each month shows its average daily profile.
    """
    df['month'] = df['timestamp'].dt.month
    df['hour'] = df['timestamp'].dt.hour

    # Month names
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']

    # Calculate average for each month-hour combination
    monthly_hourly = df.groupby(['month', 'hour']).agg({
        'forbruk_kwh': 'mean',
        'produksjon_kwh': 'mean'
    }).reset_index()

    # Create continuous x-axis: month-hour position (0-287)
    # For each month (1-12), hours 0-23
    monthly_hourly['x_position'] = (monthly_hourly['month'] - 1) * 24 + monthly_hourly['hour']

    # Sort by x_position to ensure proper plotting order
    monthly_hourly = monthly_hourly.sort_values('x_position')

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))

    # Plot forbruk (consumption)
    ax1.plot(monthly_hourly['x_position'], monthly_hourly['forbruk_kwh'],
            linewidth=1.5, color='#d62728', label='Forbruk')
    ax1.fill_between(monthly_hourly['x_position'], monthly_hourly['forbruk_kwh'],
                     alpha=0.3, color='#d62728')

    ax1.set_xlabel('Måned og time', fontsize=12)
    ax1.set_ylabel('Gjennomsnittlig forbruk (kWh/time)', fontsize=12)
    ax1.set_title('Månedlige døgnprofiler - Forbruk', fontsize=13, fontweight='bold')

    # Set x-ticks at month boundaries (every 24 hours)
    month_positions = [m * 24 for m in range(12)]
    ax1.set_xticks(month_positions)
    ax1.set_xticklabels(month_names)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(-1, 288)

    # Add vertical lines at month boundaries
    for pos in month_positions:
        ax1.axvline(x=pos, color='gray', linestyle='--', alpha=0.3, linewidth=0.5)

    # Plot produksjon (production)
    ax2.plot(monthly_hourly['x_position'], monthly_hourly['produksjon_kwh'],
            linewidth=1.5, color='#2ca02c', label='Produksjon')
    ax2.fill_between(monthly_hourly['x_position'], monthly_hourly['produksjon_kwh'],
                     alpha=0.3, color='#2ca02c')

    ax2.set_xlabel('Måned og time', fontsize=12)
    ax2.set_ylabel('Gjennomsnittlig produksjon (kWh/time)', fontsize=12)
    ax2.set_title('Månedlige døgnprofiler - Produksjon', fontsize=13, fontweight='bold')

    # Set x-ticks at month boundaries
    ax2.set_xticks(month_positions)
    ax2.set_xticklabels(month_names)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(-1, 288)

    # Add vertical lines at month boundaries
    for pos in month_positions:
        ax2.axvline(x=pos, color='gray', linestyle='--', alpha=0.3, linewidth=0.5)

    plt.suptitle('Månedlige døgnprofiler (timesbasis) - Sekvensielt over året\nDes 2024 - Nov 2025',
                 fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(save_path / 'monthly_daily_profiles.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {save_path / 'monthly_daily_profiles.png'}")
    plt.close()


def print_statistics(df: pd.DataFrame):
    """Print summary statistics for the period."""
    print("\n" + "="*60)
    print("STATISTIKK FOR PERIODEN")
    print("="*60)
    print(f"\nPeriode: {df['timestamp'].min()} til {df['timestamp'].max()}")
    print(f"Antall timer: {len(df):,}")
    print(f"Antall dager: {len(df) / 24:.1f}")

    print(f"\nForbruk:")
    print(f"  Total: {df['forbruk_kwh'].sum():,.1f} kWh")
    print(f"  Gjennomsnitt: {df['forbruk_kwh'].mean():.2f} kWh/time")
    print(f"  Maks: {df['forbruk_kwh'].max():.2f} kWh")
    print(f"  Min: {df['forbruk_kwh'].min():.2f} kWh")

    print(f"\nProduksjon:")
    print(f"  Total: {df['produksjon_kwh'].sum():,.1f} kWh")
    print(f"  Gjennomsnitt: {df['produksjon_kwh'].mean():.2f} kWh/time")
    print(f"  Maks: {df['produksjon_kwh'].max():.2f} kWh")
    print(f"  Min: {df['produksjon_kwh'].min():.2f} kWh")

    nett = df['produksjon_kwh'].sum() - df['forbruk_kwh'].sum()
    print(f"\nNetto (Produksjon - Forbruk):")
    print(f"  Total: {nett:,.1f} kWh")
    print(f"  Gjennomsnitt: {nett / len(df):.2f} kWh/time")

    # Self-consumption
    self_consumed = df[['forbruk_kwh', 'produksjon_kwh']].min(axis=1).sum()
    if df['produksjon_kwh'].sum() > 0:
        self_consumption_rate = self_consumed / df['produksjon_kwh'].sum() * 100
        print(f"\nEgenforbruk:")
        print(f"  Egenforbrukt: {self_consumed:,.1f} kWh")
        print(f"  Egenforbruksgrad: {self_consumption_rate:.1f}%")

    print("="*60 + "\n")


def main():
    print("Loading consumption data...")
    df = load_consumption_data()

    # Filter for period: Dec 1, 2024 - Nov 30, 2025
    print("Filtering for period: Dec 1, 2024 - Nov 30, 2025...")
    df_period = filter_period(df, '2024-12-01', '2025-12-01')

    if len(df_period) == 0:
        print("ERROR: No data found for the specified period!")
        return

    # Print statistics
    print_statistics(df_period)

    # Create output directory
    output_dir = Path(__file__).parent.parent / 'output' / 'profiles'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save filtered dataframe to CSV
    csv_output_path = output_dir / 'period_data_dec2024_nov2025.csv'
    df_period.to_csv(csv_output_path, index=False)
    print(f"\n✓ Saved period data to: {csv_output_path}")

    # Generate plots
    print("Generating plots...")
    plot_average_daily_profile(df_period, output_dir)
    plot_seasonal_profile(df_period, output_dir)
    plot_monthly_daily_profiles(df_period, output_dir)

    print(f"\n✓ All plots saved to: {output_dir}")


if __name__ == "__main__":
    main()
