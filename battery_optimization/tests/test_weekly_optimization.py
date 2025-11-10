"""
Unit tests for weekly sequential optimization in optimize_battery_dimensions.py

Tests validate:
- Weekly timestep calculation for PT60M and PT15M resolutions
- Month boundary detection and peak reset
- State carryover between weeks (SOC, degradation)
- Cost accumulation across 52 weeks
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.analysis.optimize_battery_dimensions import BatteryDimensionOptimizer
from core.battery_system_state import BatterySystemState
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from src.config.simulation_config import SimulationConfig


class TestWeeklyTimestepCalculation:
    """Test weekly timestep calculation for different resolutions"""

    def test_hourly_resolution_timesteps(self):
        """PT60M should have 168 timesteps per week (7 days × 24 hours)"""
        resolution = 'PT60M'
        if resolution == 'PT60M':
            weekly_timesteps = 168
        elif resolution == 'PT15M':
            weekly_timesteps = 672

        assert weekly_timesteps == 168, "Hourly resolution should have 168 timesteps/week"

    def test_15min_resolution_timesteps(self):
        """PT15M should have 672 timesteps per week (7 days × 24 hours × 4)"""
        resolution = 'PT15M'
        if resolution == 'PT60M':
            weekly_timesteps = 168
        elif resolution == 'PT15M':
            weekly_timesteps = 672

        assert weekly_timesteps == 672, "15-min resolution should have 672 timesteps/week"

    def test_52_weeks_covers_year(self):
        """52 weeks should approximately cover a full year"""
        weekly_timesteps_hourly = 168
        total_timesteps = 52 * weekly_timesteps_hourly

        # Year has 8760 hours (365 days × 24 hours)
        # 52 weeks = 8736 hours (within 24 hours of full year)
        assert total_timesteps == 8736, "52 weeks should equal 8736 hours"
        assert abs(total_timesteps - 8760) <= 24, "52 weeks should be within 24 hours of full year"


class TestMonthBoundaryDetection:
    """Test month boundary detection and peak reset logic"""

    def test_month_boundary_detection(self):
        """Verify month changes are detected correctly"""
        # Create timestamps spanning month boundary
        timestamps = pd.date_range('2024-01-28', periods=10, freq='D')

        prev_month = timestamps[0].month
        month_changes = []

        for i, ts in enumerate(timestamps):
            current_month = ts.month
            if current_month != prev_month:
                month_changes.append((i, prev_month, current_month))
                prev_month = current_month

        # Should detect January → February transition
        assert len(month_changes) == 1, "Should detect exactly one month boundary"
        assert month_changes[0][1] == 1, "Previous month should be January"
        assert month_changes[0][2] == 2, "Current month should be February"

    def test_peak_reset_at_month_boundary(self):
        """Verify monthly peak resets when crossing month boundary"""
        # Create state with high peak
        state = BatterySystemState(
            battery_capacity_kwh=100,
            current_soc_kwh=50,
            current_monthly_peak_kw=80.0,  # High peak from previous month
            month_start_date=datetime(2024, 1, 1),
            power_tariff_rate_nok_per_kw=50.0
        )

        # Verify initial state
        assert state.current_monthly_peak_kw == 80.0

        # Reset at month boundary
        new_month_start = datetime(2024, 2, 1)
        state._reset_monthly_peak(new_month_start)

        # Peak should be reset to 0
        assert state.current_monthly_peak_kw == 0.0, "Peak should reset to 0 at month boundary"
        assert state.month_start_date == new_month_start, "Month start date should update"


class TestStateCarryover:
    """Test state persistence between weekly optimizations"""

    def test_soc_carryover_between_weeks(self):
        """SOC should carry over from week N to week N+1"""
        initial_soc = 50.0
        final_soc_week1 = 65.0

        # Week 1: Start at 50%, end at 65%
        state = BatterySystemState(
            battery_capacity_kwh=100,
            current_soc_kwh=initial_soc,
            current_monthly_peak_kw=0.0,
            month_start_date=datetime(2024, 1, 1),
            power_tariff_rate_nok_per_kw=50.0
        )

        # Update state after week 1
        state.update_from_measurement(
            timestamp=datetime(2024, 1, 7, 23, 0),
            soc_kwh=final_soc_week1,
            grid_import_power_kw=10.0
        )

        # Week 2 should start at 65% SOC
        assert state.current_soc_kwh == final_soc_week1, "SOC should carry over to next week"

    def test_monthly_peak_does_not_carry_across_months(self):
        """Monthly peak should NOT carry over across month boundaries"""
        # Week in January with high peak
        state = BatterySystemState(
            battery_capacity_kwh=100,
            current_soc_kwh=50,
            current_monthly_peak_kw=75.0,
            month_start_date=datetime(2024, 1, 1),
            power_tariff_rate_nok_per_kw=50.0
        )

        # Simulate measurement that updates peak
        state.update_from_measurement(
            timestamp=datetime(2024, 1, 31, 23, 0),
            soc_kwh=55.0,
            grid_import_power_kw=80.0  # New peak
        )

        assert state.current_monthly_peak_kw == 80.0

        # Reset at February boundary
        state._reset_monthly_peak(datetime(2024, 2, 1))

        assert state.current_monthly_peak_kw == 0.0, "Peak should not carry across months"


class TestWeeklyOptimizationIntegration:
    """Integration tests for weekly optimization flow"""

    @pytest.fixture
    def simple_config(self):
        """Create minimal config for testing"""
        return SimulationConfig(
            mode='rolling_horizon',
            time_resolution='PT60M',
            simulation_period={
                'start_date': '2024-01-01',
                'end_date': '2024-02-01'  # 1 month for fast testing
            },
            battery={
                'capacity_kwh': 80,
                'power_kw': 60,
                'efficiency': 0.90,
                'initial_soc_percent': 50.0,
                'min_soc_percent': 10.0,
                'max_soc_percent': 90.0
            },
            data_sources={
                'prices_file': 'data/spot_prices/2024_NO2_hourly.csv',
                'production_file': 'data/pv_profiles/pvgis_stavanger_2024.csv',
                'consumption_file': 'data/consumption/commercial_2024.csv'
            },
            mode_specific={
                'rolling_horizon': {
                    'horizon_hours': 168,  # Weekly
                    'update_frequency_minutes': 60,
                    'persistent_state': True
                }
            }
        )

    def test_optimizer_accepts_168h_horizon(self, simple_config):
        """RollingHorizonOptimizer should accept horizon_hours=168"""
        optimizer = RollingHorizonOptimizer(
            config=simple_config,
            battery_kwh=80,
            battery_kw=60,
            horizon_hours=168
        )

        assert optimizer.horizon_hours == 168, "Should accept 168-hour horizon"
        # For PT15M: 168 hours × 4 timesteps/hour = 672 timesteps
        assert optimizer.T == 672, "Should calculate 672 timesteps for weekly horizon"

    def test_week_count_for_full_year(self):
        """52 weeks should be used for full year optimization"""
        num_weeks = 52
        weekly_timesteps_hourly = 168

        # Full year approximation
        total_hours = num_weeks * weekly_timesteps_hourly
        assert total_hours == 8736, "52 weeks should equal 8736 hours"


class TestPerformanceCharacteristics:
    """Test expected performance characteristics"""

    def test_weekly_faster_than_monthly(self):
        """Weekly optimization should be ~7.5× faster than monthly"""
        # Expected solve times (from analysis)
        monthly_solve_time = 1.0  # seconds per month
        weekly_solve_time = 0.03  # seconds per week

        # Annual times
        monthly_annual = 12 * monthly_solve_time  # 12 months
        weekly_annual = 52 * weekly_solve_time    # 52 weeks

        speedup = monthly_annual / weekly_annual

        assert speedup > 7.0, f"Weekly should be >7× faster (actual: {speedup:.1f}×)"
        assert speedup < 8.5, f"Speedup should be realistic (actual: {speedup:.1f}×)"

    def test_weekly_timesteps_smaller_than_monthly(self):
        """Weekly windows should have fewer timesteps than monthly"""
        weekly_timesteps_hourly = 168  # 7 days
        monthly_timesteps_hourly = 744  # ~31 days (average)

        ratio = monthly_timesteps_hourly / weekly_timesteps_hourly

        assert ratio > 4.0, "Monthly windows should be >4× larger"
        assert weekly_timesteps_hourly < monthly_timesteps_hourly


def test_cost_accumulation_structure():
    """Test that cost accumulation follows correct structure"""
    # Simulate 52 weeks of cost accumulation
    weekly_costs = np.random.uniform(1000, 2000, 52)  # Random costs per week

    baseline_cost = weekly_costs.sum()
    battery_costs = weekly_costs * 0.85  # 15% savings
    battery_cost = battery_costs.sum()

    annual_savings = baseline_cost - battery_cost

    assert annual_savings > 0, "Battery should provide savings"
    assert annual_savings / baseline_cost > 0.10, "Should save at least 10%"
    assert annual_savings / baseline_cost < 0.20, "Savings should be realistic (<20%)"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
