"""
Comprehensive test suite for Solar Production modules
Tests both PVGIS API integration and simple solar model

Test Categories:
- AC1: PVGIS API Integration and Caching
- AC2: Production Data Quality and Validation
- AC3: Inverter Limits and Clipping
- AC4: Curtailment Calculations
- AC5: Fallback and Error Handling
"""

import pytest
import pandas as pd
import numpy as np
import os
from pathlib import Path
from datetime import datetime

from core.pvgis_solar import PVGISProduction
from core.solar import SolarSystem
from config import SolarSystemConfig, LocationConfig


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def config():
    """Solar system configuration from project config"""
    return SolarSystemConfig()


@pytest.fixture
def location():
    """Location configuration"""
    return LocationConfig()


@pytest.fixture
def pvgis_fetcher(location, config):
    """PVGIS production fetcher with project configuration"""
    return PVGISProduction(
        lat=location.latitude,
        lon=location.longitude,
        pv_capacity_kwp=config.pv_capacity_kwp,
        tilt=config.tilt_degrees,
        azimuth=config.azimuth_degrees,
        system_loss=2  # 2% system loss (DC-to-AC loss from config)
    )


@pytest.fixture
def simple_solar(config):
    """Simple solar system model"""
    return SolarSystem(
        pv_capacity_kwp=config.pv_capacity_kwp,
        inverter_limit_kw=config.inverter_capacity_kw,
        location='stavanger',
        tilt=config.tilt_degrees,
        azimuth=config.azimuth_degrees
    )


# ============================================================================
# AC1: PVGIS API Integration and Caching
# ============================================================================

class TestAC1_PVGIS_Integration:
    """Test PVGIS API integration, caching, and data fetching"""

    def test_pvgis_cache_exists(self, pvgis_fetcher):
        """Check if PVGIS cache directory and file exist"""
        assert os.path.exists(pvgis_fetcher.cache_dir), "Cache directory should exist"

        # Cache file should exist after first fetch
        cache_file = Path(pvgis_fetcher.cache_file)
        print(f"\n📁 Cache file: {cache_file}")
        print(f"   Exists: {cache_file.exists()}")
        if cache_file.exists():
            size_kb = cache_file.stat().st_size / 1024
            print(f"   Size: {size_kb:.1f} KB")

    def test_fetch_production_data(self, pvgis_fetcher):
        """Fetch production data (uses cache if available)"""
        print("\n🌐 Fetching PVGIS production data...")

        production = pvgis_fetcher.fetch_hourly_production(year=2020, refresh=False)

        assert production is not None, "Production data should not be None"
        assert isinstance(production, pd.Series), "Production should be pandas Series"
        assert len(production) > 0, "Production should have data"

        print(f"\n✅ Fetched {len(production)} hours of data")
        print(f"   Annual production: {production.sum()/1000:.1f} MWh")
        print(f"   Peak production: {production.max():.1f} kW")

    def test_cached_data_loads_properly(self, pvgis_fetcher):
        """Verify cached data can be loaded correctly"""
        cache_file = Path(pvgis_fetcher.cache_file)

        if cache_file.exists():
            # Load from cache
            production = pvgis_fetcher.fetch_hourly_production(year=2020, refresh=False)

            assert isinstance(production.index, pd.DatetimeIndex), "Index should be DatetimeIndex"
            assert production.name == 'production_kw', "Series should be named 'production_kw'"
            print(f"\n✅ Cache loaded successfully")
        else:
            pytest.skip("No cache file exists yet - run test_fetch_production_data first")

    def test_pvgis_api_parameters(self, pvgis_fetcher, config, location):
        """Verify PVGIS fetcher has correct parameters"""
        print("\n🔧 PVGIS Configuration:")
        print(f"   Latitude: {pvgis_fetcher.lat} (expected: {location.latitude})")
        print(f"   Longitude: {pvgis_fetcher.lon} (expected: {location.longitude})")
        print(f"   PV Capacity: {pvgis_fetcher.pv_capacity_kwp} kWp (expected: {config.pv_capacity_kwp})")
        print(f"   Tilt: {pvgis_fetcher.tilt}° (expected: {config.tilt_degrees})")
        print(f"   Azimuth: {pvgis_fetcher.azimuth}° (expected: {config.azimuth_degrees})")

        assert pvgis_fetcher.lat == location.latitude
        assert pvgis_fetcher.lon == location.longitude
        assert pvgis_fetcher.pv_capacity_kwp == config.pv_capacity_kwp
        assert pvgis_fetcher.tilt == config.tilt_degrees
        assert pvgis_fetcher.azimuth == config.azimuth_degrees


# ============================================================================
# AC2: Production Data Quality and Validation
# ============================================================================

class TestAC2_ProductionDataQuality:
    """Test production data quality, ranges, and annual totals"""

    def test_production_full_year_hours(self, pvgis_fetcher):
        """Verify production data has correct hours for full year"""
        production = pvgis_fetcher.fetch_hourly_production(year=2020)

        # 2020 is a leap year (366 days = 8784 hours)
        # Normal year would be 8760 hours
        expected_hours = 8784  # Leap year
        assert len(production) == expected_hours, f"Expected {expected_hours} hours for 2020, got {len(production)}"
        print(f"\n✅ Full leap year 2020: {len(production)} hours")

    def test_production_values_realistic(self, pvgis_fetcher, config):
        """Check production values are within realistic ranges"""
        production = pvgis_fetcher.fetch_hourly_production(year=2020)

        # Basic statistics
        mean_kw = production.mean()
        max_kw = production.max()
        min_kw = production.min()
        annual_mwh = production.sum() / 1000

        print(f"\n📊 Production Statistics:")
        print(f"   Annual: {annual_mwh:.1f} MWh")
        print(f"   Mean: {mean_kw:.2f} kW")
        print(f"   Max: {max_kw:.1f} kW")
        print(f"   Min: {min_kw:.1f} kW")

        # Validation ranges for 138.55 kWp in Stavanger (in MWh, not kWh!)
        assert 80 <= annual_mwh <= 150, f"Annual production {annual_mwh:.1f} MWh seems unrealistic"
        assert min_kw >= 0, "Production should not be negative"
        # Note: PVGIS returns DC production before inverter clipping, so max may exceed inverter
        assert max_kw <= config.pv_capacity_kwp * 1.1, f"Max {max_kw:.1f} kW exceeds PV capacity {config.pv_capacity_kwp}"

    def test_production_no_missing_hours(self, pvgis_fetcher):
        """Verify no gaps in hourly sequence"""
        production = pvgis_fetcher.fetch_hourly_production(year=2020)

        # Check for NaN values
        nan_count = production.isna().sum()
        assert nan_count == 0, f"Found {nan_count} NaN values in production data"

        # Check time differences
        time_diffs = production.index.to_series().diff().dropna()
        expected_diff = pd.Timedelta(hours=1)

        irregular = time_diffs[time_diffs != expected_diff]
        assert len(irregular) == 0, f"Found {len(irregular)} irregular time intervals"

        print(f"\n✅ No missing hours, all values present")

    def test_production_seasonal_variation(self, pvgis_fetcher):
        """Verify production shows expected seasonal patterns"""
        production = pvgis_fetcher.fetch_hourly_production(year=2020)

        # Calculate monthly averages
        monthly_avg = production.groupby(production.index.month).mean()

        print(f"\n📅 Monthly Average Production (kW):")
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        for month_num, month_name in enumerate(months, 1):
            print(f"   {month_name}: {monthly_avg[month_num]:.2f} kW")

        # Summer (Jun-Jul) should be higher than winter (Dec-Jan)
        summer_avg = monthly_avg[[6, 7]].mean()
        winter_avg = monthly_avg[[12, 1]].mean()

        assert summer_avg > winter_avg, "Summer production should exceed winter production"
        print(f"\n✅ Seasonal variation confirmed: Summer {summer_avg:.2f} kW > Winter {winter_avg:.2f} kW")

    def test_production_daily_pattern(self, pvgis_fetcher):
        """Verify production shows expected daily patterns"""
        production = pvgis_fetcher.fetch_hourly_production(year=2020)

        # Get average production by hour of day
        hourly_avg = production.groupby(production.index.hour).mean()

        print(f"\n🕐 Average Production by Hour (kW):")
        for hour in range(24):
            print(f"   {hour:02d}:00 - {hourly_avg[hour]:.2f} kW")

        # Night hours (00-05, 20-23) should have very low production
        night_production = hourly_avg[[0, 1, 2, 3, 4, 5, 20, 21, 22, 23]].mean()
        # Midday hours (10-14) should have highest production
        midday_production = hourly_avg[[10, 11, 12, 13, 14]].mean()

        assert midday_production > night_production * 10, "Midday should have much higher production than night"
        print(f"\n✅ Daily pattern confirmed: Midday {midday_production:.2f} kW >> Night {night_production:.2f} kW")


# ============================================================================
# AC3: Inverter Limits and Clipping
# ============================================================================

class TestAC3_InverterLimits:
    """Test inverter capacity limits and production clipping"""

    def test_production_vs_inverter_capacity(self, pvgis_fetcher, config):
        """Analyze production vs inverter capacity (PVGIS gives DC, not AC)"""
        production = pvgis_fetcher.fetch_hourly_production(year=2020)

        max_production = production.max()
        inverter_limit = config.inverter_capacity_kw
        pv_capacity = config.pv_capacity_kwp

        print(f"\n⚡ Production vs Inverter Analysis:")
        print(f"   PV capacity (DC): {pv_capacity} kWp")
        print(f"   Inverter capacity (AC): {inverter_limit} kW")
        print(f"   Max production: {max_production:.1f} kW")

        # PVGIS returns DC power, which can exceed inverter AC capacity
        # This is expected and shows oversizing ratio
        if max_production > inverter_limit:
            print(f"   ⚠️ DC production exceeds AC inverter ({max_production:.1f} > {inverter_limit})")
            print(f"   This indicates inverter clipping will occur")

        # Max should not exceed DC capacity
        assert max_production <= pv_capacity * 1.1, \
            f"Production {max_production:.1f} kW exceeds PV DC capacity {pv_capacity} kW"

    def test_clipping_events_detection(self, pvgis_fetcher, config):
        """Detect when production is clipped by inverter"""
        production = pvgis_fetcher.fetch_hourly_production(year=2020)

        # Define clipping threshold (99% of inverter capacity)
        clip_threshold = config.inverter_capacity_kw * 0.99
        clipping_events = production >= clip_threshold

        clipped_hours = clipping_events.sum()
        clipped_energy = production[clipping_events].sum()

        print(f"\n✂️ Clipping Analysis:")
        print(f"   Clipped hours: {clipped_hours} ({clipped_hours/8760*100:.2f}%)")
        print(f"   Clipped energy: {clipped_energy/1000:.1f} MWh")

        if clipped_hours > 0:
            print(f"   ⚠️ Production is being limited by inverter capacity")
        else:
            print(f"   ✅ No significant clipping detected")

    def test_oversizing_ratio(self, config):
        """Verify PV-to-inverter oversizing ratio"""
        oversizing = config.pv_capacity_kwp / config.inverter_capacity_kw

        print(f"\n📏 System Sizing:")
        print(f"   PV capacity: {config.pv_capacity_kwp} kWp")
        print(f"   Inverter capacity: {config.inverter_capacity_kw} kW")
        print(f"   Oversizing ratio: {oversizing:.2f}")

        # Typical oversizing is 1.0-1.4 for Stavanger
        assert 1.0 <= oversizing <= 1.5, f"Oversizing ratio {oversizing:.2f} outside typical range"
        print(f"   ✅ Oversizing ratio within acceptable range")


# ============================================================================
# AC4: Curtailment Calculations
# ============================================================================

class TestAC4_CurtailmentCalculations:
    """Test curtailment calculations for grid export limits"""

    def test_curtailment_calculation(self, simple_solar, config):
        """Calculate curtailment with grid export limit"""
        production = simple_solar.generate_production(year=2024)

        curtailment = simple_solar.calculate_curtailment(
            production=production,
            grid_limit_kw=config.grid_export_limit_kw
        )

        print(f"\n✂️ Curtailment Analysis (Grid limit: {config.grid_export_limit_kw} kW):")
        print(f"   Total curtailed: {curtailment['total_kwh']/1000:.1f} MWh")
        print(f"   Curtailment hours: {curtailment['hours']}")
        print(f"   Percentage: {curtailment['percentage']:.2f}%")

        assert 'total_kwh' in curtailment
        assert 'hours' in curtailment
        assert 'percentage' in curtailment
        assert 'series' in curtailment

        # Curtailment should be non-negative
        assert curtailment['total_kwh'] >= 0
        assert curtailment['hours'] >= 0
        assert 0 <= curtailment['percentage'] <= 100

    def test_no_curtailment_high_limit(self, simple_solar):
        """No curtailment when grid limit exceeds production"""
        production = simple_solar.generate_production(year=2024)

        # Set very high grid limit
        curtailment = simple_solar.calculate_curtailment(
            production=production,
            grid_limit_kw=200  # Higher than any production
        )

        print(f"\n✅ High Grid Limit Test (200 kW):")
        print(f"   Curtailment: {curtailment['total_kwh']:.2f} kWh")
        print(f"   Hours: {curtailment['hours']}")

        assert curtailment['total_kwh'] == 0, "Should have zero curtailment with high limit"
        assert curtailment['hours'] == 0

    def test_maximum_curtailment_low_limit(self, simple_solar):
        """High curtailment when grid limit is very low"""
        production = simple_solar.generate_production(year=2024)

        # Set very low grid limit
        curtailment = simple_solar.calculate_curtailment(
            production=production,
            grid_limit_kw=10  # Much lower than typical production
        )

        print(f"\n✂️ Low Grid Limit Test (10 kW):")
        print(f"   Curtailment: {curtailment['total_kwh']/1000:.1f} MWh")
        print(f"   Percentage: {curtailment['percentage']:.2f}%")

        # Should have significant curtailment
        assert curtailment['percentage'] > 10, "Should have >10% curtailment with 10 kW limit"


# ============================================================================
# AC5: Fallback and Error Handling
# ============================================================================

class TestAC5_FallbackHandling:
    """Test fallback mechanisms when PVGIS API unavailable"""

    def test_simple_solar_generates_data(self, simple_solar):
        """Simple solar model generates valid production data"""
        production = simple_solar.generate_production(year=2024)

        assert isinstance(production, pd.Series)
        assert len(production) == 8760
        assert production.name == 'production_kw'

        print(f"\n✅ Simple solar model:")
        print(f"   Hours: {len(production)}")
        print(f"   Annual: {production.sum()/1000:.1f} MWh")
        print(f"   Max: {production.max():.1f} kW")

    def test_simple_solar_respects_inverter_limit(self, simple_solar, config):
        """Simple model respects inverter capacity"""
        production = simple_solar.generate_production(year=2024)

        max_production = production.max()
        assert max_production <= config.inverter_capacity_kw, \
            f"Simple model exceeded inverter limit: {max_production:.1f} kW"

        print(f"\n✅ Simple model respects {config.inverter_capacity_kw} kW limit")

    def test_simple_solar_has_seasonal_variation(self, simple_solar):
        """Simple model shows seasonal variation"""
        production = simple_solar.generate_production(year=2024)

        monthly_avg = production.groupby(production.index.month).mean()
        summer_avg = monthly_avg[[6, 7]].mean()
        winter_avg = monthly_avg[[12, 1]].mean()

        assert summer_avg > winter_avg, "Summer should exceed winter in simple model"
        print(f"\n✅ Simple model seasonal variation: Summer {summer_avg:.2f} kW > Winter {winter_avg:.2f} kW")


# ============================================================================
# Summary Test
# ============================================================================

def test_solar_module_summary(pvgis_fetcher, simple_solar, config):
    """
    Generate comprehensive summary of solar production capabilities
    """
    print("\n" + "="*70)
    print("SOLAR PRODUCTION MODULE - TEST SUMMARY")
    print("="*70)

    # PVGIS data
    pvgis_prod = pvgis_fetcher.fetch_hourly_production(year=2020)
    print(f"\n📊 PVGIS Production (2020):")
    print(f"   Annual: {pvgis_prod.sum()/1000:.1f} MWh")
    print(f"   Peak: {pvgis_prod.max():.1f} kW")
    print(f"   Capacity factor: {pvgis_prod.mean()/config.pv_capacity_kwp*100:.1f}%")

    # Simple model
    simple_prod = simple_solar.generate_production(year=2024)
    print(f"\n📊 Simple Model Production (2024):")
    print(f"   Annual: {simple_prod.sum()/1000:.1f} MWh")
    print(f"   Peak: {simple_prod.max():.1f} kW")

    # Curtailment
    curtailment = simple_solar.calculate_curtailment(
        production=pvgis_prod,
        grid_limit_kw=config.grid_export_limit_kw
    )
    print(f"\n✂️ Curtailment (Grid limit: {config.grid_export_limit_kw} kW):")
    print(f"   Curtailed: {curtailment['total_kwh']/1000:.1f} MWh ({curtailment['percentage']:.2f}%)")
    print(f"   Hours: {curtailment['hours']} ({curtailment['hours']/8760*100:.2f}%)")

    print("\n" + "="*70)
    print("✅ ALL SOLAR PRODUCTION TESTS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    # Run with: pytest tests/test_solar_production.py -v
    pytest.main([__file__, '-v', '-s'])
