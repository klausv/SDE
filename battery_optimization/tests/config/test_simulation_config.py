"""
Unit tests for SimulationConfig and related dataclasses.
"""

import pytest
import yaml
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

from src.config.simulation_config import (
    SimulationConfig,
    BatteryConfigSim,
    DataSourceConfig,
    RollingHorizonModeConfig,
    MonthlyModeConfig,
    YearlyModeConfig,
    SimulationPeriodConfig,
)


class TestBatteryConfigSim:
    """Test battery configuration dataclass."""

    def test_default_values(self):
        """Test default battery configuration values."""
        config = BatteryConfigSim()
        assert config.capacity_kwh == 80.0
        assert config.power_kw == 60.0
        assert config.efficiency == 0.90
        assert config.initial_soc_percent == 50.0
        assert config.min_soc_percent == 10.0
        assert config.max_soc_percent == 90.0

    def test_custom_values(self):
        """Test custom battery configuration values."""
        config = BatteryConfigSim(
            capacity_kwh=100.0,
            power_kw=75.0,
            efficiency=0.95,
        )
        assert config.capacity_kwh == 100.0
        assert config.power_kw == 75.0
        assert config.efficiency == 0.95


class TestDataSourceConfig:
    """Test data source configuration."""

    def test_default_paths(self):
        """Test default data source paths."""
        config = DataSourceConfig()
        assert "spot_prices" in config.prices_file
        assert "pv_profiles" in config.production_file
        assert "consumption" in config.consumption_file

    def test_resolve_paths(self, tmp_path):
        """Test path resolution to absolute paths."""
        config = DataSourceConfig(
            prices_file="data/prices.csv",
            production_file="data/production.csv",
            consumption_file="data/consumption.csv",
        )
        config.resolve_paths(tmp_path)

        assert Path(config.prices_file).is_absolute()
        assert Path(config.production_file).is_absolute()
        assert Path(config.consumption_file).is_absolute()


class TestRollingHorizonModeConfig:
    """Test rolling horizon mode configuration."""

    def test_defaults(self):
        """Test default rolling horizon settings."""
        config = RollingHorizonModeConfig()
        assert config.horizon_hours == 24
        assert config.update_frequency_minutes == 60
        assert config.persistent_state is True

    def test_custom_values(self):
        """Test custom rolling horizon settings."""
        config = RollingHorizonModeConfig(
            horizon_hours=48,
            update_frequency_minutes=15,
            persistent_state=False,
        )
        assert config.horizon_hours == 48
        assert config.update_frequency_minutes == 15
        assert config.persistent_state is False


class TestMonthlyModeConfig:
    """Test monthly mode configuration."""

    def test_all_months(self):
        """Test 'all' months configuration."""
        config = MonthlyModeConfig(months="all")
        assert config.get_month_list() == list(range(1, 13))

    def test_specific_months(self):
        """Test specific months configuration."""
        config = MonthlyModeConfig(months=[1, 2, 3])
        assert config.get_month_list() == [1, 2, 3]

    def test_single_month(self):
        """Test single month configuration."""
        config = MonthlyModeConfig(months=[6])
        assert config.get_month_list() == [6]


class TestYearlyModeConfig:
    """Test yearly mode configuration."""

    def test_defaults(self):
        """Test default yearly mode settings."""
        config = YearlyModeConfig()
        assert config.horizon_hours == 168
        assert config.weeks == 52

    def test_custom_values(self):
        """Test custom yearly mode settings."""
        config = YearlyModeConfig(horizon_hours=24, weeks=53)
        assert config.horizon_hours == 24
        assert config.weeks == 53


class TestSimulationPeriodConfig:
    """Test simulation period configuration."""

    def test_default_period(self):
        """Test default simulation period."""
        config = SimulationPeriodConfig()
        assert config.start_date == "2024-01-01"
        assert config.end_date == "2024-12-31"

    def test_datetime_parsing(self):
        """Test datetime parsing from strings."""
        config = SimulationPeriodConfig(
            start_date="2023-06-15",
            end_date="2023-12-31",
        )
        start = config.get_start_datetime()
        end = config.get_end_datetime()

        assert isinstance(start, datetime)
        assert isinstance(end, datetime)
        assert start.year == 2023
        assert start.month == 6
        assert start.day == 15
        assert end.year == 2023
        assert end.month == 12
        assert end.day == 31


class TestSimulationConfig:
    """Test main simulation configuration."""

    def test_default_config(self):
        """Test default simulation configuration."""
        config = SimulationConfig()
        assert config.mode == "rolling_horizon"
        assert config.time_resolution == "PT60M"
        assert config.save_trajectory is True
        assert config.save_plots is True

    def test_get_mode_config(self):
        """Test getting mode-specific configuration."""
        config = SimulationConfig(mode="rolling_horizon")
        mode_config = config.get_mode_config()
        assert isinstance(mode_config, RollingHorizonModeConfig)

        config = SimulationConfig(mode="monthly")
        mode_config = config.get_mode_config()
        assert isinstance(mode_config, MonthlyModeConfig)

        config = SimulationConfig(mode="yearly")
        mode_config = config.get_mode_config()
        assert isinstance(mode_config, YearlyModeConfig)

    def test_validate_valid_config(self, tmp_path):
        """Test validation of valid configuration."""
        # Create dummy data files
        (tmp_path / "data").mkdir()
        for filename in ["prices.csv", "production.csv", "consumption.csv"]:
            (tmp_path / "data" / filename).touch()

        config = SimulationConfig(
            mode="rolling_horizon",
            time_resolution="PT60M",
            battery=BatteryConfigSim(capacity_kwh=80, power_kw=60),
            data_sources=DataSourceConfig(
                prices_file=str(tmp_path / "data" / "prices.csv"),
                production_file=str(tmp_path / "data" / "production.csv"),
                consumption_file=str(tmp_path / "data" / "consumption.csv"),
            ),
        )

        # Should not raise any exception
        config.validate()

    def test_validate_invalid_mode(self):
        """Test validation fails for invalid mode."""
        config = SimulationConfig(mode="invalid_mode")
        with pytest.raises(ValueError, match="Invalid mode"):
            config.validate()

    def test_validate_invalid_resolution(self):
        """Test validation fails for invalid resolution."""
        config = SimulationConfig(time_resolution="PT30M")
        with pytest.raises(ValueError, match="Invalid time_resolution"):
            config.validate()

    def test_validate_invalid_battery_params(self):
        """Test validation fails for invalid battery parameters."""
        config = SimulationConfig(
            battery=BatteryConfigSim(capacity_kwh=-10)
        )
        with pytest.raises(ValueError, match="capacity_kwh must be positive"):
            config.validate()

        config = SimulationConfig(
            battery=BatteryConfigSim(efficiency=1.5)
        )
        with pytest.raises(ValueError, match="efficiency must be between"):
            config.validate()

    def test_validate_invalid_dates(self):
        """Test validation fails for invalid date range."""
        config = SimulationConfig(
            simulation_period=SimulationPeriodConfig(
                start_date="2024-12-31",
                end_date="2024-01-01",
            )
        )
        with pytest.raises(ValueError, match="Start date must be before end date"):
            config.validate()

    def test_validate_missing_data_files(self):
        """Test validation fails for missing data files."""
        config = SimulationConfig(
            data_sources=DataSourceConfig(
                prices_file="/nonexistent/prices.csv",
                production_file="/nonexistent/production.csv",
                consumption_file="/nonexistent/consumption.csv",
            )
        )
        with pytest.raises(FileNotFoundError, match="Data file not found"):
            config.validate()


class TestYAMLSerialization:
    """Test YAML loading and saving."""

    @pytest.fixture
    def temp_yaml_dir(self):
        """Create temporary directory for YAML files."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_data_files(self, temp_yaml_dir):
        """Create sample data files for testing."""
        data_dir = temp_yaml_dir / "data"
        data_dir.mkdir()

        prices_file = data_dir / "spot_prices" / "2024_NO2_hourly.csv"
        production_file = data_dir / "pv_profiles" / "pvgis_stavanger_2024.csv"
        consumption_file = data_dir / "consumption" / "commercial_2024.csv"

        prices_file.parent.mkdir(parents=True, exist_ok=True)
        production_file.parent.mkdir(parents=True, exist_ok=True)
        consumption_file.parent.mkdir(parents=True, exist_ok=True)

        prices_file.touch()
        production_file.touch()
        consumption_file.touch()

        return {
            "prices": str(prices_file),
            "production": str(production_file),
            "consumption": str(consumption_file),
        }

    def test_to_yaml(self, temp_yaml_dir):
        """Test saving configuration to YAML."""
        config = SimulationConfig(
            mode="monthly",
            time_resolution="PT15M",
            battery=BatteryConfigSim(capacity_kwh=100, power_kw=75),
        )

        yaml_path = temp_yaml_dir / "test_config.yaml"
        config.to_yaml(yaml_path)

        assert yaml_path.exists()

        # Load and verify content
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        assert data['mode'] == "monthly"
        assert data['time_resolution'] == "PT15M"
        assert data['battery']['capacity_kwh'] == 100
        assert data['battery']['power_kw'] == 75

    def test_from_yaml_rolling_horizon(self, temp_yaml_dir, sample_data_files):
        """Test loading rolling horizon configuration from YAML."""
        yaml_content = f"""
mode: rolling_horizon
time_resolution: PT60M

simulation_period:
  start_date: "2024-01-01"
  end_date: "2024-01-31"

battery:
  capacity_kwh: 80
  power_kw: 60
  efficiency: 0.90

data_sources:
  prices_file: "{sample_data_files['prices']}"
  production_file: "{sample_data_files['production']}"
  consumption_file: "{sample_data_files['consumption']}"

mode_specific:
  rolling_horizon:
    horizon_hours: 24
    update_frequency_minutes: 60
    persistent_state: true

output_dir: "results/test"
save_trajectory: true
save_plots: true
"""

        yaml_path = temp_yaml_dir / "rolling_config.yaml"
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        config = SimulationConfig.from_yaml(yaml_path)

        assert config.mode == "rolling_horizon"
        assert config.time_resolution == "PT60M"
        assert config.battery.capacity_kwh == 80
        assert config.battery.power_kw == 60
        assert config.rolling_horizon.horizon_hours == 24
        assert config.rolling_horizon.update_frequency_minutes == 60
        assert config.rolling_horizon.persistent_state is True

    def test_from_yaml_monthly(self, temp_yaml_dir, sample_data_files):
        """Test loading monthly configuration from YAML."""
        yaml_content = f"""
mode: monthly
time_resolution: PT60M

simulation_period:
  start_date: "2024-01-01"
  end_date: "2024-12-31"

battery:
  capacity_kwh: 100
  power_kw: 75

data_sources:
  prices_file: "{sample_data_files['prices']}"
  production_file: "{sample_data_files['production']}"
  consumption_file: "{sample_data_files['consumption']}"

mode_specific:
  monthly:
    months: [1, 2, 3]

output_dir: "results/monthly"
"""

        yaml_path = temp_yaml_dir / "monthly_config.yaml"
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        config = SimulationConfig.from_yaml(yaml_path)

        assert config.mode == "monthly"
        assert config.battery.capacity_kwh == 100
        assert config.monthly.get_month_list() == [1, 2, 3]

    def test_from_yaml_yearly(self, temp_yaml_dir, sample_data_files):
        """Test loading yearly configuration from YAML."""
        yaml_content = f"""
mode: yearly
time_resolution: PT60M

simulation_period:
  start_date: "2024-01-01"
  end_date: "2024-12-31"

battery:
  capacity_kwh: 80
  power_kw: 60

data_sources:
  prices_file: "{sample_data_files['prices']}"
  production_file: "{sample_data_files['production']}"
  consumption_file: "{sample_data_files['consumption']}"

mode_specific:
  yearly:
    horizon_hours: 168
    weeks: 52

output_dir: "results/yearly"
"""

        yaml_path = temp_yaml_dir / "yearly_config.yaml"
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)

        config = SimulationConfig.from_yaml(yaml_path)

        assert config.mode == "yearly"
        assert config.yearly.horizon_hours == 168
        assert config.yearly.weeks == 52

    def test_from_yaml_missing_file(self):
        """Test loading from non-existent YAML file."""
        with pytest.raises(FileNotFoundError):
            SimulationConfig.from_yaml("/nonexistent/config.yaml")

    def test_from_yaml_empty_file(self, temp_yaml_dir):
        """Test loading from empty YAML file."""
        yaml_path = temp_yaml_dir / "empty.yaml"
        yaml_path.touch()

        with pytest.raises(ValueError, match="Empty or invalid YAML"):
            SimulationConfig.from_yaml(yaml_path)

    def test_roundtrip(self, temp_yaml_dir):
        """Test saving and loading configuration maintains data."""
        original = SimulationConfig(
            mode="rolling_horizon",
            time_resolution="PT15M",
            battery=BatteryConfigSim(capacity_kwh=100, power_kw=75, efficiency=0.95),
            rolling_horizon=RollingHorizonModeConfig(
                horizon_hours=48,
                update_frequency_minutes=15,
                persistent_state=False,
            ),
        )

        yaml_path = temp_yaml_dir / "roundtrip.yaml"
        original.to_yaml(yaml_path)

        loaded = SimulationConfig.from_yaml(yaml_path)

        assert loaded.mode == original.mode
        assert loaded.time_resolution == original.time_resolution
        assert loaded.battery.capacity_kwh == original.battery.capacity_kwh
        assert loaded.battery.power_kw == original.battery.power_kw
        assert loaded.battery.efficiency == original.battery.efficiency
        assert loaded.rolling_horizon.horizon_hours == original.rolling_horizon.horizon_hours
        assert loaded.rolling_horizon.update_frequency_minutes == original.rolling_horizon.update_frequency_minutes
        assert loaded.rolling_horizon.persistent_state == original.rolling_horizon.persistent_state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
