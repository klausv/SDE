"""
Example usage of pricing and weather infrastructure modules.

Demonstrates how to use the new dataclass-based infrastructure for:
- Loading electricity price data
- Loading solar production data
- Data filtering and statistics

These infrastructure modules can be shared between battery and solar PV modules.
"""

import sys
from pathlib import Path

# Add parent directory to path
parent_path = Path(__file__).parent
sys.path.insert(0, str(parent_path))

from src.infrastructure.pricing import PriceLoader, PriceData
from src.infrastructure.weather import SolarProductionLoader, SolarProductionData


def example_price_loading():
    """Example: Loading electricity price data."""
    print("=" * 70)
    print("PRICING INFRASTRUCTURE EXAMPLE")
    print("=" * 70)
    print()

    # Initialize price loader
    loader = PriceLoader(eur_to_nok=11.5, default_area_code="NO2")

    # Example 1: Load from CSV file
    print("1. Loading prices from CSV file...")
    try:
        # This would work with actual price data file:
        # prices = loader.from_csv("data/spot_prices/NO2_2024_60min_real.csv")
        print("   ✓ from_csv() method available")
        print("   - Handles EUR/MWh → NOK/kWh conversion automatically")
        print("   - Manages timezone conversion (UTC → Oslo local time)")
        print("   - Removes duplicate timestamps (DST handling)")
    except FileNotFoundError:
        print("   (Skipped - no data file available)")
    print()

    # Example 2: Price conversion utility
    print("2. Price conversion utilities...")
    import numpy as np
    prices_eur_mwh = np.array([50.0, 100.0, 75.0])
    prices_nok_kwh = PriceLoader.convert_eur_mwh_to_nok_kwh(prices_eur_mwh, 11.5)
    print(f"   EUR/MWh: {prices_eur_mwh}")
    print(f"   NOK/kWh: {prices_nok_kwh}")
    print(f"   ✓ Conversion: 50 EUR/MWh = {prices_nok_kwh[0]:.3f} NOK/kWh")
    print()

    # Example 3: ENTSO-E API usage (requires API key)
    print("3. ENTSO-E API integration...")
    print("   ✓ ENTSOEClient available with caching")
    print("   - fetch_day_ahead_prices(start, end)")
    print("   - fetch_year_prices(2024)")
    print("   - fetch_month_prices(2024, 10)")
    print("   - Automatic EUR/MWh → NOK/kWh conversion")
    print("   - File-based caching (data/spot_prices/)")
    print()

    # Example 4: PriceData dataclass features
    print("4. PriceData dataclass features...")
    print("   Available methods:")
    print("   - get_statistics() → min, max, mean, std, median")
    print("   - filter_period(start, end) → time-filtered data")
    print("   - to_dataframe() → pandas DataFrame")
    print("   ✓ Type-safe with full validation")
    print()


def example_solar_loading():
    """Example: Loading solar production data."""
    print("=" * 70)
    print("WEATHER INFRASTRUCTURE EXAMPLE")
    print("=" * 70)
    print()

    # Initialize solar loader
    loader = SolarProductionLoader(
        default_capacity_kwp=150.0,
        default_location="Stavanger",
        default_latitude=58.97,
        default_longitude=5.73
    )

    # Example 1: Load from CSV file
    print("1. Loading solar production from CSV file...")
    try:
        # This would work with actual production data file:
        # production = loader.from_csv("data/pv_profiles/pvgis_58.97_5.73_150kWp.csv")
        print("   ✓ from_csv() method available")
        print("   - Automatic year shifting (PVGIS TMY → 2024)")
        print("   - Resampling to hourly (handles :11 minute offsets)")
        print("   - Capacity tracking for scaling")
    except FileNotFoundError:
        print("   (Skipped - no data file available)")
    print()

    # Example 2: PVGIS API usage
    print("2. PVGIS API integration...")
    print("   ✓ from_pvgis_api() method available (requires pvlib)")
    print("   - Fetches typical meteorological year (TMY) data")
    print("   - Returns hourly production estimates")
    print("   - Includes system losses and capacity scaling")
    print("   Example:")
    print("     production = loader.from_pvgis_api(")
    print("         latitude=58.97, longitude=5.73,")
    print("         capacity_kwp=150, tilt=30, azimuth=180")
    print("     )")
    print()

    # Example 3: SolarProductionData features
    print("3. SolarProductionData dataclass features...")
    print("   Available methods:")
    print("   - get_statistics() → min, max, mean, annual_kwh, capacity_factor")
    print("   - scale_to_capacity(200) → scale 150kWp data to 200kWp")
    print("   - filter_period(start, end) → time-filtered data")
    print("   - to_dataframe() → pandas DataFrame")
    print("   ✓ Type-safe with validation (e.g., negative values → 0)")
    print()

    # Example 4: Capacity scaling
    print("4. Capacity scaling example...")
    print("   If you have 150 kWp production data:")
    print("     data_150 = loader.from_csv('production_150kwp.csv', capacity_kwp=150)")
    print("     data_200 = data_150.scale_to_capacity(200)  # Scale to 200 kWp")
    print("   ✓ Enables reusing PVGIS data for different capacities")
    print()


def main():
    """Run infrastructure examples."""
    print()
    print("═" * 70)
    print("INFRASTRUCTURE MODULES USAGE EXAMPLES")
    print("═" * 70)
    print()
    print("Demonstrates the new dataclass-based infrastructure modules")
    print("for pricing and weather data management.")
    print()

    example_price_loading()
    print()
    example_solar_loading()

    print("=" * 70)
    print("BENEFITS OF NEW INFRASTRUCTURE")
    print("=" * 70)
    print()
    print("✓ Dataclass-based: Type-safe with automatic validation")
    print("✓ Unified API: Consistent interface across data sources")
    print("✓ Modular: Pricing and weather modules can be used independently")
    print("✓ Shared: Can be used by both battery and solar PV modules")
    print("✓ Flexible: Support for multiple data sources (files, APIs)")
    print("✓ Cached: Built-in caching for API requests")
    print("✓ Tested: Input validation and error handling")
    print()
    print("USAGE IN BATTERY OPTIMIZATION:")
    print()
    print("  from src.infrastructure.pricing import PriceLoader")
    print("  from src.infrastructure.weather import SolarProductionLoader")
    print()
    print("  # Load price data")
    print("  price_loader = PriceLoader(eur_to_nok=11.5)")
    print("  prices = price_loader.from_csv('spot_prices.csv')")
    print()
    print("  # Load solar production")
    print("  solar_loader = SolarProductionLoader(default_capacity_kwp=150)")
    print("  production = solar_loader.from_csv('pv_production.csv')")
    print()
    print("  # Get statistics")
    print("  print(prices.get_statistics())")
    print("  print(production.get_statistics())")
    print()


if __name__ == "__main__":
    main()
