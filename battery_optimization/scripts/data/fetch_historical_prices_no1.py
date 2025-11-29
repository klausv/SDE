"""
Fetch historical annual average electricity prices for NO1 (Oslo, Norway) from 2003-2024
Uses ENTSO-E Transparency Platform API
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
from entsoe import EntsoePandasClient
import pytz

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class HistoricalPricesFetcher:
    """Fetch and analyze historical electricity prices for NO1"""

    def __init__(self, api_key: str = None):
        """
        Initialize the fetcher

        Args:
            api_key: ENTSO-E API key (if not provided, loads from .env)
        """
        self.api_key = api_key or os.getenv('ENTSOE_API_KEY')
        if not self.api_key:
            raise ValueError(
                "ENTSO-E API key not found. "
                "Please set ENTSOE_API_KEY in .env file"
            )

        self.client = EntsoePandasClient(api_key=self.api_key)
        self.area_code = 'NO_1'  # Oslo, Norway
        self.tz = pytz.timezone('Europe/Oslo')

        # Create output directories
        self.data_dir = Path('data/historical_prices')
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.results_dir = Path('results/historical_analysis')
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def fetch_year_prices(self, year: int, use_cache: bool = True) -> pd.Series:
        """
        Fetch day-ahead prices for entire year

        Args:
            year: Year to fetch (e.g., 2024)
            use_cache: Whether to use cached data if available

        Returns:
            pd.Series with hourly prices in EUR/MWh
        """
        cache_file = self.data_dir / f"NO1_prices_{year}.pkl"

        # Check cache
        if use_cache and cache_file.exists():
            logger.info(f"Loading cached data for {year}")
            return pd.read_pickle(cache_file)

        try:
            # Create timezone-aware pandas Timestamp objects
            start = pd.Timestamp(year=year, month=1, day=1, hour=0, tz=self.tz)
            end = pd.Timestamp(year=year, month=12, day=31, hour=23, tz=self.tz)

            logger.info(f"Fetching prices for {year} from ENTSO-E API...")
            prices = self.client.query_day_ahead_prices(
                self.area_code,
                start=start,
                end=end
            )

            # Save to cache
            prices.to_pickle(cache_file)
            logger.info(f"Saved {year} data to cache")

            return prices

        except Exception as e:
            logger.error(f"Error fetching {year}: {e}")
            return None

    def fetch_all_years(
        self,
        start_year: int = 2003,
        end_year: int = 2024,
        use_cache: bool = True
    ) -> dict:
        """
        Fetch prices for multiple years

        Args:
            start_year: First year to fetch
            end_year: Last year to fetch
            use_cache: Whether to use cached data

        Returns:
            dict mapping year -> price series
        """
        all_prices = {}

        for year in range(start_year, end_year + 1):
            logger.info(f"Processing year {year}...")
            prices = self.fetch_year_prices(year, use_cache=use_cache)

            if prices is not None:
                all_prices[year] = prices
                logger.info(f"✓ {year}: {len(prices)} hours, avg {prices.mean():.2f} EUR/MWh")
            else:
                logger.warning(f"✗ {year}: Failed to fetch data")

        return all_prices

    def calculate_annual_statistics(self, all_prices: dict) -> pd.DataFrame:
        """
        Calculate annual statistics from price data

        Args:
            all_prices: dict mapping year -> price series

        Returns:
            DataFrame with annual statistics
        """
        stats = []

        for year, prices in sorted(all_prices.items()):
            # Convert to NOK/kWh for Norwegian context
            eur_to_nok = 11.5  # Approximate average rate
            prices_nok_kwh = prices * eur_to_nok / 1000

            stats.append({
                'year': year,
                'mean_eur_mwh': prices.mean(),
                'median_eur_mwh': prices.median(),
                'std_eur_mwh': prices.std(),
                'min_eur_mwh': prices.min(),
                'max_eur_mwh': prices.max(),
                'mean_nok_kwh': prices_nok_kwh.mean(),
                'median_nok_kwh': prices_nok_kwh.median(),
                'std_nok_kwh': prices_nok_kwh.std(),
                'min_nok_kwh': prices_nok_kwh.min(),
                'max_nok_kwh': prices_nok_kwh.max(),
                'p10_eur_mwh': prices.quantile(0.10),
                'p90_eur_mwh': prices.quantile(0.90),
                'p10_nok_kwh': prices_nok_kwh.quantile(0.10),
                'p90_nok_kwh': prices_nok_kwh.quantile(0.90),
                'volatility': prices.std() / prices.mean(),  # Coefficient of variation
                'num_hours': len(prices),
                'num_negative': (prices < 0).sum(),
                'pct_negative': (prices < 0).sum() / len(prices) * 100
            })

        return pd.DataFrame(stats)

    def save_results(self, stats_df: pd.DataFrame):
        """
        Save statistics to CSV

        Args:
            stats_df: DataFrame with annual statistics
        """
        output_file = self.results_dir / 'NO1_annual_prices_2003_2024.csv'
        stats_df.to_csv(output_file, index=False, float_format='%.4f')
        logger.info(f"Saved results to {output_file}")

        # Also create a summary file
        summary_file = self.results_dir / 'NO1_price_summary.txt'
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("ENTSO-E Electricity Price Analysis for NO1 (Oslo, Norway)\n")
            f.write("=" * 70 + "\n")
            f.write(f"Period: 2003-2024\n")
            f.write(f"Total years analyzed: {len(stats_df)}\n\n")

            f.write("ANNUAL AVERAGE PRICES (EUR/MWh)\n")
            f.write("-" * 70 + "\n")
            for _, row in stats_df.iterrows():
                f.write(f"{int(row['year'])}: {row['mean_eur_mwh']:7.2f} EUR/MWh "
                       f"({row['mean_nok_kwh']:5.3f} NOK/kWh)\n")

            f.write("\n" + "=" * 70 + "\n")
            f.write("OVERALL STATISTICS (2003-2024)\n")
            f.write("-" * 70 + "\n")
            f.write(f"Average annual mean: {stats_df['mean_eur_mwh'].mean():.2f} EUR/MWh\n")
            f.write(f"Minimum annual mean: {stats_df['mean_eur_mwh'].min():.2f} EUR/MWh ({stats_df[stats_df['mean_eur_mwh'] == stats_df['mean_eur_mwh'].min()]['year'].values[0]:.0f})\n")
            f.write(f"Maximum annual mean: {stats_df['mean_eur_mwh'].max():.2f} EUR/MWh ({stats_df[stats_df['mean_eur_mwh'] == stats_df['mean_eur_mwh'].max()]['year'].values[0]:.0f})\n")
            f.write(f"Standard deviation: {stats_df['mean_eur_mwh'].std():.2f} EUR/MWh\n")
            f.write(f"Average volatility: {stats_df['volatility'].mean():.2%}\n")

        logger.info(f"Saved summary to {summary_file}")

    def create_visualizations(self, stats_df: pd.DataFrame):
        """
        Create visualizations of historical prices

        Args:
            stats_df: DataFrame with annual statistics
        """
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (14, 10)

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Annual average prices over time (EUR/MWh)
        ax1 = axes[0, 0]
        ax1.plot(stats_df['year'], stats_df['mean_eur_mwh'],
                marker='o', linewidth=2, markersize=6, color='#2E86AB')
        ax1.fill_between(stats_df['year'],
                         stats_df['mean_eur_mwh'] - stats_df['std_eur_mwh'],
                         stats_df['mean_eur_mwh'] + stats_df['std_eur_mwh'],
                         alpha=0.3, color='#2E86AB')
        ax1.set_xlabel('År', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Pris (EUR/MWh)', fontsize=12, fontweight='bold')
        ax1.set_title('Gjennomsnittlig Strømpris NO1 (Oslo)', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)

        # 2. Annual average prices in NOK/kWh
        ax2 = axes[0, 1]
        ax2.plot(stats_df['year'], stats_df['mean_nok_kwh'],
                marker='s', linewidth=2, markersize=6, color='#A23B72')
        ax2.fill_between(stats_df['year'],
                         stats_df['mean_nok_kwh'] - stats_df['std_nok_kwh'],
                         stats_df['mean_nok_kwh'] + stats_df['std_nok_kwh'],
                         alpha=0.3, color='#A23B72')
        ax2.set_xlabel('År', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Pris (NOK/kWh)', fontsize=12, fontweight='bold')
        ax2.set_title('Gjennomsnittlig Strømpris NO1 (NOK/kWh)', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        # 3. Volatility over time
        ax3 = axes[1, 0]
        ax3.bar(stats_df['year'], stats_df['volatility'] * 100,
               color='#F18F01', alpha=0.7, edgecolor='black')
        ax3.set_xlabel('År', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Volatilitet (%)', fontsize=12, fontweight='bold')
        ax3.set_title('Prisvolatilitet over Tid (Standardavvik/Gjennomsnitt)',
                     fontsize=14, fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')

        # 4. Price range (min/max) over time
        ax4 = axes[1, 1]
        ax4.fill_between(stats_df['year'],
                         stats_df['min_eur_mwh'],
                         stats_df['max_eur_mwh'],
                         alpha=0.4, color='#C73E1D', label='Min-Max Range')
        ax4.plot(stats_df['year'], stats_df['mean_eur_mwh'],
                marker='o', linewidth=2, markersize=6,
                color='#2E86AB', label='Gjennomsnitt')
        ax4.plot(stats_df['year'], stats_df['p10_eur_mwh'],
                linestyle='--', linewidth=1, color='gray', label='P10')
        ax4.plot(stats_df['year'], stats_df['p90_eur_mwh'],
                linestyle='--', linewidth=1, color='gray', label='P90')
        ax4.set_xlabel('År', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Pris (EUR/MWh)', fontsize=12, fontweight='bold')
        ax4.set_title('Prisutvikling med Spredning', fontsize=14, fontweight='bold')
        ax4.legend(loc='upper left', fontsize=10)
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save figure
        output_file = self.results_dir / 'NO1_historical_prices_analysis.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Saved visualization to {output_file}")

        plt.show()


def main():
    """Main execution function"""

    logger.info("Starting historical price analysis for NO1 (Oslo)")
    logger.info("=" * 70)

    try:
        # Initialize fetcher
        fetcher = HistoricalPricesFetcher()

        # Fetch all years (2003-2024)
        logger.info("Fetching data from ENTSO-E (this may take several minutes)...")
        all_prices = fetcher.fetch_all_years(
            start_year=2003,
            end_year=2024,
            use_cache=True  # Set to False to force re-fetch
        )

        if not all_prices:
            logger.error("No data fetched. Exiting.")
            return

        logger.info(f"\nSuccessfully fetched data for {len(all_prices)} years")

        # Calculate statistics
        logger.info("\nCalculating annual statistics...")
        stats_df = fetcher.calculate_annual_statistics(all_prices)

        # Display results
        logger.info("\n" + "=" * 70)
        logger.info("ANNUAL AVERAGE PRICES (EUR/MWh)")
        logger.info("-" * 70)
        for _, row in stats_df.iterrows():
            logger.info(f"{int(row['year'])}: {row['mean_eur_mwh']:7.2f} EUR/MWh "
                       f"(σ={row['std_eur_mwh']:.2f}, "
                       f"min={row['min_eur_mwh']:.2f}, "
                       f"max={row['max_eur_mwh']:.2f})")

        # Save results
        logger.info("\nSaving results...")
        fetcher.save_results(stats_df)

        # Create visualizations
        logger.info("\nCreating visualizations...")
        fetcher.create_visualizations(stats_df)

        logger.info("\n" + "=" * 70)
        logger.info("Analysis complete!")
        logger.info(f"Results saved to: {fetcher.results_dir}")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
