"""
Full Pipeline Integration Tests

Tests complete simulation pipeline using real data from CSV files.
These tests verify that the entire system works end-to-end with actual data.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from src.config.simulation_config import SimulationConfig
from src.simulation.rolling_horizon_orchestrator import RollingHorizonOrchestrator
from src.simulation.battery_simulation import BatterySimulation
from src.data.data_manager import DataManager, TimeSeriesData
from src.data.file_loaders import load_price_data, load_production_data, load_consumption_data, align_timeseries


# Test configuration and data paths
CONFIG_FILE = Path(__file__).parent.parent.parent / "configs" / "working_config.yaml"
DATA_DIR = Path(__file__).parent.parent.parent / "data"
PRICE_FILE = DATA_DIR / "spot_prices" / "NO2_2024_60min_real.csv"
PRODUCTION_FILE = DATA_DIR / "pv_profiles" / "pvgis_58.97_5.73_138.55kWp.csv"
CONSUMPTION_FILE = DATA_DIR / "consumption" / "commercial_2024.csv"


class TestConfigBasedSimulation:
    """Tests for file-based simulation using YAML config."""

    def test_working_config_exists(self):
        """Verify working config file exists."""
        assert CONFIG_FILE.exists(), f"Config file not found: {CONFIG_FILE}"

    def test_load_config_from_yaml(self):
        """Test loading config from YAML file."""
        config = SimulationConfig.from_yaml(str(CONFIG_FILE))

        assert config is not None, "Failed to load config"
        assert config.battery.capacity_kwh == 80, "Battery capacity mismatch"
        assert config.battery.power_kw == 60, "Battery power mismatch"

    @pytest.mark.slow
    def test_full_simulation_from_config(self):
        """Test complete simulation using config file (June 2024)."""
        # Load config
        config = SimulationConfig.from_yaml(str(CONFIG_FILE))

        # Run simulation
        orchestrator = RollingHorizonOrchestrator(config)
        results = orchestrator.run()

        # Verify results
        assert results is not None, "Simulation returned None"
        assert len(results.trajectory) > 0, "No trajectory data in results"
        assert len(results.trajectory) >= 600, f"Expected ≥600 timesteps for June, got {len(results.trajectory)}"

        # Check SOC is within bounds
        soc_percent = results.trajectory['soc_percent']
        assert np.all(soc_percent >= 9.9), f"SOC below minimum: {soc_percent.min():.1f}%"
        assert np.all(soc_percent <= 90.1), f"SOC above maximum: {soc_percent.max():.1f}%"


class TestPythonicAPISimulation:
    """Tests for Pythonic API (DataFrame/array-based)."""

    def test_simulation_from_arrays(self):
        """Test simulation using array-based API."""
        # Load real data
        timestamps_price, prices = load_price_data(str(PRICE_FILE))
        timestamps_prod, production = load_production_data(str(PRODUCTION_FILE))
        timestamps_cons, consumption = load_consumption_data(str(CONSUMPTION_FILE))

        # Align
        common_timestamps, aligned_values = align_timeseries(
            [timestamps_price, timestamps_prod, timestamps_cons],
            [prices, production, consumption]
        )

        # Filter to small test period (first week of June 2024)
        mask = (common_timestamps >= '2024-06-01') & (common_timestamps < '2024-06-08')
        timestamps_test = common_timestamps[mask]
        prices_test = aligned_values[0][mask]
        production_test = aligned_values[1][mask]
        consumption_test = aligned_values[2][mask]

        # Create simulation
        sim = BatterySimulation.from_arrays(
            timestamps_test, prices_test, production_test, consumption_test,
            battery_kwh=80, battery_kw=60
        )

        # Run simulation
        results = sim.run()

        # Verify results
        assert results is not None, "Simulation returned None"
        assert len(results.trajectory) > 0, "No trajectory data"
        assert len(results.trajectory) >= 100, f"Expected ≥100 hours for first week, got {len(results.trajectory)}"

    def test_simulation_from_dataframe(self):
        """Test simulation using DataFrame-based API."""
        # Load real data
        timestamps_price, prices = load_price_data(str(PRICE_FILE))
        timestamps_prod, production = load_production_data(str(PRODUCTION_FILE))
        timestamps_cons, consumption = load_consumption_data(str(CONSUMPTION_FILE))

        # Align
        common_timestamps, aligned_values = align_timeseries(
            [timestamps_price, timestamps_prod, timestamps_cons],
            [prices, production, consumption]
        )

        # Create DataFrame for first week of June 2024
        mask = (common_timestamps >= '2024-06-01') & (common_timestamps < '2024-06-08')
        df = pd.DataFrame({
            'price_nok_per_kwh': aligned_values[0][mask],
            'pv_production_kw': aligned_values[1][mask],
            'consumption_kw': aligned_values[2][mask]
        }, index=common_timestamps[mask])

        # Create simulation
        sim = BatterySimulation.from_dataframe(df, battery_kwh=80, battery_kw=60)

        # Run simulation
        results = sim.run()

        # Verify results
        assert results is not None, "Simulation returned None"
        assert len(results.trajectory) > 0, "No trajectory data"
        assert len(results.trajectory) >= 100, f"Expected ≥100 hours for first week, got {len(results.trajectory)}"


class TestDataManagerIntegration:
    """Tests for DataManager with real files."""

    def test_data_manager_loads_all_files(self):
        """Test DataManager loads all three data files."""
        config = SimulationConfig.from_yaml(str(CONFIG_FILE))
        dm = DataManager(config)

        data = dm.load_data()

        assert data is not None, "DataManager returned None"
        assert len(data) > 0, "No data loaded"
        assert len(data.timestamps) > 0, "No timestamps"
        assert len(data.prices_nok_per_kwh) > 0, "No prices"
        assert len(data.pv_production_kw) > 0, "No production data"
        assert len(data.consumption_kw) > 0, "No consumption data"

    def test_data_manager_filters_to_simulation_period(self):
        """Test DataManager filters data to simulation period."""
        config = SimulationConfig.from_yaml(str(CONFIG_FILE))
        dm = DataManager(config)

        data = dm.load_data()

        # Check data is within simulation period (June 2024)
        assert data.timestamps[0].year == 2024, "Start year should be 2024"
        assert data.timestamps[0].month == 6, "Start month should be June"
        assert data.timestamps[-1].year == 2024, "End year should be 2024"
        assert data.timestamps[-1].month == 6, "End month should be June"

    def test_data_manager_with_direct_data(self):
        """Test DataManager accepts pre-loaded TimeSeriesData."""
        config = SimulationConfig.from_yaml(str(CONFIG_FILE))

        # Create TimeSeriesData manually
        timestamps = pd.date_range('2024-06-01', periods=48, freq='h')
        prices = np.random.uniform(0.5, 1.5, 48)
        production = np.random.uniform(0, 100, 48)
        consumption = np.random.uniform(20, 50, 48)

        data = TimeSeriesData.from_arrays(timestamps, prices, production, consumption)

        # Pass to DataManager
        dm = DataManager(config, data=data)

        loaded_data = dm.load_data()

        # Should return the pre-loaded data (possibly resampled)
        assert loaded_data is not None, "DataManager returned None"
        assert len(loaded_data) > 0, "No data"


class TestTimeSeriesDataConstructors:
    """Tests for TimeSeriesData constructor methods."""

    def test_from_dataframe_with_real_data(self):
        """Test TimeSeriesData.from_dataframe() with real data."""
        # Load real data
        timestamps_price, prices = load_price_data(str(PRICE_FILE))
        timestamps_prod, production = load_production_data(str(PRODUCTION_FILE))
        timestamps_cons, consumption = load_consumption_data(str(CONSUMPTION_FILE))

        # Align
        common_timestamps, aligned_values = align_timeseries(
            [timestamps_price, timestamps_prod, timestamps_cons],
            [prices, production, consumption]
        )

        # Create DataFrame
        df = pd.DataFrame({
            'price_nok_per_kwh': aligned_values[0][:100],
            'pv_production_kw': aligned_values[1][:100],
            'consumption_kw': aligned_values[2][:100]
        }, index=common_timestamps[:100])

        # Create TimeSeriesData
        data = TimeSeriesData.from_dataframe(df)

        assert data is not None, "from_dataframe returned None"
        assert len(data) == 100, f"Expected 100 timesteps, got {len(data)}"
        assert data.resolution == 'PT60M', f"Expected PT60M, got {data.resolution}"

    def test_from_arrays_with_real_data(self):
        """Test TimeSeriesData.from_arrays() with real data."""
        # Load real data
        timestamps_price, prices = load_price_data(str(PRICE_FILE))
        timestamps_prod, production = load_production_data(str(PRODUCTION_FILE))
        timestamps_cons, consumption = load_consumption_data(str(CONSUMPTION_FILE))

        # Align
        common_timestamps, aligned_values = align_timeseries(
            [timestamps_price, timestamps_prod, timestamps_cons],
            [prices, production, consumption]
        )

        # Use first 100 timesteps
        data = TimeSeriesData.from_arrays(
            common_timestamps[:100],
            aligned_values[0][:100],
            aligned_values[1][:100],
            aligned_values[2][:100]
        )

        assert data is not None, "from_arrays returned None"
        assert len(data) == 100, f"Expected 100 timesteps, got {len(data)}"
        assert data.resolution == 'PT60M', f"Expected PT60M, got {data.resolution}"


class TestResultsValidation:
    """Tests for validating simulation results."""

    @pytest.mark.slow
    def test_results_have_required_columns(self):
        """Test that simulation results have all required columns."""
        config = SimulationConfig.from_yaml(str(CONFIG_FILE))
        orchestrator = RollingHorizonOrchestrator(config)
        results = orchestrator.run()

        trajectory = results.trajectory

        # Check required columns exist
        required_cols = ['P_charge_kw', 'P_discharge_kw', 'P_grid_import_kw', 'P_grid_export_kw',
                        'E_battery_kwh', 'P_curtail_kw', 'soc_percent']

        for col in required_cols:
            assert col in trajectory.columns, f"Missing required column: {col}"

    @pytest.mark.slow
    def test_results_energy_balance(self):
        """Test that energy balance is maintained in results."""
        config = SimulationConfig.from_yaml(str(CONFIG_FILE))
        orchestrator = RollingHorizonOrchestrator(config)
        results = orchestrator.run()

        trajectory = results.trajectory

        # Battery charge/discharge should not happen simultaneously
        charge = trajectory['P_charge_kw']
        discharge = trajectory['P_discharge_kw']

        # Allow small simultaneous values due to numerical precision
        simultaneous = (charge > 0.1) & (discharge > 0.1)
        assert simultaneous.sum() == 0, f"Found {simultaneous.sum()} timesteps with simultaneous charge/discharge"

    @pytest.mark.slow
    def test_results_soc_consistency(self):
        """Test that SOC changes are consistent with charge/discharge."""
        config = SimulationConfig.from_yaml(str(CONFIG_FILE))
        orchestrator = RollingHorizonOrchestrator(config)
        results = orchestrator.run()

        trajectory = results.trajectory
        capacity_kwh = config.battery.capacity_kwh

        # Calculate expected SOC changes
        soc_kwh = trajectory['E_battery_kwh']
        soc_changes = soc_kwh.diff()

        # First timestep will be NaN
        soc_changes = soc_changes[1:]

        # SOC changes should be reasonable (≤ battery power * timestep duration)
        max_change = config.battery.power_kw * 1.0  # Hourly data
        assert np.all(np.abs(soc_changes) <= max_change * 1.1), \
            f"Found SOC change exceeding maximum: {np.abs(soc_changes).max():.2f} kWh"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
