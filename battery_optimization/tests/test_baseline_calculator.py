"""
Tests for BaselineCalculator - No Battery Mode

Tests baseline calculation functionality for economic comparison.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from src.optimization.baseline_calculator import BaselineCalculator
from src.optimization.base_optimizer import OptimizationResult


class TestBaselineCalculator:
    """Test suite for BaselineCalculator."""

    def test_initialization(self):
        """Test baseline calculator initialization."""
        calc = BaselineCalculator(grid_limit_kw=77)

        assert calc.battery_kwh == 0.0
        assert calc.battery_kw == 0.0
        assert calc.grid_limit_import_kw == 77
        assert calc.grid_limit_export_kw == 77

    def test_initialization_separate_limits(self):
        """Test initialization with separate import/export limits."""
        calc = BaselineCalculator(
            grid_limit_import_kw=100,
            grid_limit_export_kw=77
        )

        assert calc.grid_limit_import_kw == 100
        assert calc.grid_limit_export_kw == 77

    def test_simple_deficit(self):
        """Test calculation with consumption > production (grid import)."""
        calc = BaselineCalculator(grid_limit_kw=100)

        timestamps = pd.date_range("2024-01-01", periods=4, freq="h")
        pv_production = np.array([0, 10, 20, 10])  # Low production
        consumption = np.array([50, 50, 50, 50])    # Constant consumption
        spot_prices = np.array([0.5, 0.5, 0.5, 0.5])

        result = calc.optimize(
            timestamps=timestamps,
            pv_production=pv_production,
            consumption=consumption,
            spot_prices=spot_prices,
        )

        # Should import from grid
        expected_import = consumption - pv_production
        np.testing.assert_array_almost_equal(result.P_grid_import, expected_import)

        # No export
        np.testing.assert_array_almost_equal(result.P_grid_export, np.zeros(4))

        # No curtailment
        np.testing.assert_array_almost_equal(result.P_curtail, np.zeros(4))

        # Battery arrays should be zero
        np.testing.assert_array_almost_equal(result.P_charge, np.zeros(4))
        np.testing.assert_array_almost_equal(result.P_discharge, np.zeros(4))
        np.testing.assert_array_almost_equal(result.E_battery, np.zeros(4))

        assert result.success
        assert "baseline" in result.message.lower()

    def test_simple_surplus(self):
        """Test calculation with production > consumption (grid export)."""
        calc = BaselineCalculator(grid_limit_kw=100)

        timestamps = pd.date_range("2024-06-15", periods=4, freq="h")
        pv_production = np.array([80, 90, 100, 80])  # High production
        consumption = np.array([30, 30, 30, 30])     # Low consumption
        spot_prices = np.array([0.5, 0.5, 0.5, 0.5])

        result = calc.optimize(
            timestamps=timestamps,
            pv_production=pv_production,
            consumption=consumption,
            spot_prices=spot_prices,
        )

        # Should export to grid
        expected_export = pv_production - consumption
        np.testing.assert_array_almost_equal(result.P_grid_export, expected_export)

        # No import
        np.testing.assert_array_almost_equal(result.P_grid_import, np.zeros(4))

        # No curtailment (under grid limit)
        np.testing.assert_array_almost_equal(result.P_curtail, np.zeros(4))

        assert result.success

    def test_curtailment(self):
        """Test curtailment when export exceeds grid limit."""
        calc = BaselineCalculator(grid_limit_kw=50)  # Low grid limit

        timestamps = pd.date_range("2024-06-15", periods=4, freq="h")
        pv_production = np.array([100, 120, 110, 100])  # High production
        consumption = np.array([30, 30, 30, 30])        # Low consumption
        spot_prices = np.array([0.5, 0.5, 0.5, 0.5])

        result = calc.optimize(
            timestamps=timestamps,
            pv_production=pv_production,
            consumption=consumption,
            spot_prices=spot_prices,
        )

        # Export limited to grid_limit_kw
        np.testing.assert_array_almost_equal(result.P_grid_export, np.array([50, 50, 50, 50]))

        # Curtailment = surplus - grid_limit
        net_production = pv_production - consumption
        expected_curtail = np.maximum(0, net_production - 50)
        np.testing.assert_array_almost_equal(result.P_curtail, expected_curtail)

        assert result.success

    def test_energy_cost_calculation(self):
        """Test that energy costs are calculated correctly."""
        calc = BaselineCalculator(grid_limit_kw=100)

        timestamps = pd.date_range("2024-01-01", periods=2, freq="h")
        pv_production = np.array([10, 60])
        consumption = np.array([50, 30])
        spot_prices = np.array([1.0, 2.0])  # Different prices

        result = calc.optimize(
            timestamps=timestamps,
            pv_production=pv_production,
            consumption=consumption,
            spot_prices=spot_prices,
        )

        # Hour 0: import 40 kWh @ 1.0 = 40 NOK
        # Hour 1: export 30 kWh @ 2.0 = 60 NOK revenue
        # Net cost = 40 - 60 = -20 NOK (profit)
        expected_import_cost = 40 * 1.0  # 40 NOK
        expected_export_revenue = 30 * 2.0  # 60 NOK
        expected_energy_cost = expected_import_cost - expected_export_revenue  # -20 NOK

        assert result.energy_cost == pytest.approx(expected_energy_cost)
        assert result.objective_value == pytest.approx(expected_energy_cost)

    def test_fast_calculation(self):
        """Test that baseline calculation is very fast."""
        import time

        calc = BaselineCalculator(grid_limit_kw=77)

        # Large dataset (1 year, hourly)
        timestamps = pd.date_range("2024-01-01", periods=8760, freq="h")
        pv_production = np.random.rand(8760) * 100
        consumption = np.random.rand(8760) * 50 + 30
        spot_prices = np.random.rand(8760) * 0.5 + 0.3

        start = time.time()
        result = calc.optimize(
            timestamps=timestamps,
            pv_production=pv_production,
            consumption=consumption,
            spot_prices=spot_prices,
        )
        calc_time = time.time() - start

        # Should be very fast (< 100ms for 8760 timesteps)
        assert calc_time < 0.1
        assert result.success
        assert result.solve_time_seconds < 0.1

    def test_result_structure_compatibility(self):
        """Test that result structure matches OptimizationResult interface."""
        calc = BaselineCalculator(grid_limit_kw=77)

        timestamps = pd.date_range("2024-01-01", periods=24, freq="h")
        pv_production = np.random.rand(24) * 80
        consumption = np.random.rand(24) * 40 + 20
        spot_prices = np.random.rand(24) * 0.5 + 0.3

        result = calc.optimize(
            timestamps=timestamps,
            pv_production=pv_production,
            consumption=consumption,
            spot_prices=spot_prices,
        )

        # Check type
        assert isinstance(result, OptimizationResult)

        # Check all required arrays exist and have correct length
        assert len(result.P_charge) == 24
        assert len(result.P_discharge) == 24
        assert len(result.P_grid_import) == 24
        assert len(result.P_grid_export) == 24
        assert len(result.E_battery) == 24
        assert len(result.P_curtail) == 24

        # Check costs exist
        assert result.objective_value is not None
        assert result.energy_cost is not None

        # Check to_dataframe works
        df = result.to_dataframe(timestamps)
        assert len(df) == 24
        assert 'P_grid_import_kw' in df.columns
        assert 'P_grid_export_kw' in df.columns

    def test_repr(self):
        """Test string representation."""
        calc = BaselineCalculator(grid_limit_import_kw=77, grid_limit_export_kw=50)
        repr_str = repr(calc)

        assert "BaselineCalculator" in repr_str
        assert "77" in repr_str  # Import limit
        assert "50" in repr_str  # Export limit


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
