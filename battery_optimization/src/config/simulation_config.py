"""
Unified simulation configuration system for battery optimization.

Supports three simulation modes:
1. Rolling Horizon: Real-time operation with 24h lookah

ead
2. Monthly: Single or multi-month optimization analysis
3. Yearly: Annual investment analysis with weekly optimizations
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Union, Literal
import yaml


@dataclass
class BatteryConfigSim:
    """Battery system parameters for simulation."""
    capacity_kwh: float = 80.0
    power_kw: float = 60.0
    efficiency: float = 0.90
    initial_soc_percent: float = 50.0
    min_soc_percent: float = 10.0
    max_soc_percent: float = 90.0


@dataclass
class DataSourceConfig:
    """Configuration for input data files."""
    prices_file: str = "data/spot_prices/2024_NO2_hourly.csv"
    production_file: str = "data/pv_profiles/pvgis_stavanger_2024.csv"
    consumption_file: str = "data/consumption/commercial_2024.csv"

    def resolve_paths(self, base_dir: Path) -> None:
        """
        Convert relative paths to absolute paths with security validation.

        Args:
            base_dir: Base directory for resolving relative paths

        Raises:
            ValueError: If resolved path is outside base directory (path traversal attack)
        """
        # C3 Fix: Canonicalize base directory to prevent path traversal
        base_dir = Path(base_dir).resolve()

        # Resolve and validate each file path
        for attr in ['prices_file', 'production_file', 'consumption_file']:
            rel_path = getattr(self, attr)

            # Skip if already absolute
            if Path(rel_path).is_absolute():
                # Still validate it's within a safe location
                abs_path = Path(rel_path).resolve()
            else:
                # Resolve relative to base_dir
                abs_path = (base_dir / rel_path).resolve()

            # Security: Ensure resolved path is within base_dir or its subdirectories
            try:
                abs_path.relative_to(base_dir)
            except ValueError:
                raise ValueError(
                    f"Security violation: {attr} path '{rel_path}' resolves to "
                    f"'{abs_path}' which is outside base directory '{base_dir}'. "
                    f"This may be a path traversal attack."
                )

            setattr(self, attr, str(abs_path))


@dataclass
class RollingHorizonModeConfig:
    """Configuration specific to rolling horizon simulation."""
    horizon_hours: int = 24
    update_frequency_minutes: int = 60
    persistent_state: bool = True


@dataclass
class MonthlyModeConfig:
    """Configuration specific to monthly optimization."""
    months: Union[List[int], Literal["all"]] = "all"

    def get_month_list(self) -> List[int]:
        """Get list of months to simulate."""
        if self.months == "all":
            return list(range(1, 13))
        return self.months


@dataclass
class YearlyModeConfig:
    """Configuration specific to yearly simulation."""
    horizon_hours: int = 168  # Full week
    weeks: int = 52


@dataclass
class SimulationPeriodConfig:
    """Time period for simulation."""
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"

    def get_start_datetime(self) -> datetime:
        """Parse start date to datetime."""
        return datetime.fromisoformat(self.start_date)

    def get_end_datetime(self) -> datetime:
        """Parse end date to datetime."""
        return datetime.fromisoformat(self.end_date)


@dataclass
class SimulationConfig:
    """
    Master configuration for battery optimization simulations.

    Supports three simulation modes:
    - rolling_horizon: Real-time operation with persistent state
    - monthly: Single or multi-month analysis
    - yearly: Annual investment analysis with weekly optimization
    """

    # Core settings
    mode: Literal["rolling_horizon", "monthly", "yearly"] = "rolling_horizon"
    time_resolution: str = "PT60M"  # ISO 8601 duration: PT60M (hourly) or PT15M (15-min)

    # Simulation period
    simulation_period: SimulationPeriodConfig = field(default_factory=SimulationPeriodConfig)

    # Battery configuration
    battery: BatteryConfigSim = field(default_factory=BatteryConfigSim)

    # Data sources
    data_sources: DataSourceConfig = field(default_factory=DataSourceConfig)

    # Mode-specific configurations
    rolling_horizon: RollingHorizonModeConfig = field(default_factory=RollingHorizonModeConfig)
    monthly: MonthlyModeConfig = field(default_factory=MonthlyModeConfig)
    yearly: YearlyModeConfig = field(default_factory=YearlyModeConfig)

    # Output settings
    output_dir: str = "results"
    save_trajectory: bool = True
    save_plots: bool = True

    @classmethod
    def from_yaml(cls, yaml_path: Union[str, Path]) -> "SimulationConfig":
        """
        Load simulation configuration from YAML file.

        Args:
            yaml_path: Path to YAML configuration file

        Returns:
            SimulationConfig instance

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            ValueError: If YAML is invalid or missing required fields
        """
        yaml_path = Path(yaml_path)

        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

        with open(yaml_path, 'r') as f:
            config_dict = yaml.safe_load(f)

        if config_dict is None:
            raise ValueError(f"Empty or invalid YAML file: {yaml_path}")

        # Parse nested configurations
        config = cls(
            mode=config_dict.get('mode', 'rolling_horizon'),
            time_resolution=config_dict.get('time_resolution', 'PT60M'),
            output_dir=config_dict.get('output_dir', 'results'),
            save_trajectory=config_dict.get('save_trajectory', True),
            save_plots=config_dict.get('save_plots', True),
        )

        # Parse simulation period
        if 'simulation_period' in config_dict:
            period_dict = config_dict['simulation_period']
            config.simulation_period = SimulationPeriodConfig(
                start_date=period_dict.get('start_date', '2024-01-01'),
                end_date=period_dict.get('end_date', '2024-12-31'),
            )

        # Parse battery configuration
        if 'battery' in config_dict:
            battery_dict = config_dict['battery']
            config.battery = BatteryConfigSim(
                capacity_kwh=battery_dict.get('capacity_kwh', 80.0),
                power_kw=battery_dict.get('power_kw', 60.0),
                efficiency=battery_dict.get('efficiency', 0.90),
                initial_soc_percent=battery_dict.get('initial_soc_percent', 50.0),
                min_soc_percent=battery_dict.get('min_soc_percent', 10.0),
                max_soc_percent=battery_dict.get('max_soc_percent', 90.0),
            )

        # Parse data sources
        if 'data_sources' in config_dict:
            data_dict = config_dict['data_sources']
            config.data_sources = DataSourceConfig(
                prices_file=data_dict.get('prices_file', 'data/spot_prices/2024_NO2_hourly.csv'),
                production_file=data_dict.get('production_file', 'data/pv_profiles/pvgis_stavanger_2024.csv'),
                consumption_file=data_dict.get('consumption_file', 'data/consumption/commercial_2024.csv'),
            )
            # Resolve relative paths
            config.data_sources.resolve_paths(yaml_path.parent.parent)

        # Parse mode-specific configurations
        if 'mode_specific' in config_dict:
            mode_specific = config_dict['mode_specific']

            if 'rolling_horizon' in mode_specific:
                rh_dict = mode_specific['rolling_horizon']
                config.rolling_horizon = RollingHorizonModeConfig(
                    horizon_hours=rh_dict.get('horizon_hours', 24),
                    update_frequency_minutes=rh_dict.get('update_frequency_minutes', 60),
                    persistent_state=rh_dict.get('persistent_state', True),
                )

            if 'monthly' in mode_specific:
                monthly_dict = mode_specific['monthly']
                months_value = monthly_dict.get('months', 'all')
                config.monthly = MonthlyModeConfig(months=months_value)

            if 'yearly' in mode_specific:
                yearly_dict = mode_specific['yearly']
                config.yearly = YearlyModeConfig(
                    horizon_hours=yearly_dict.get('horizon_hours', 168),
                    weeks=yearly_dict.get('weeks', 52),
                )

        return config

    def to_yaml(self, yaml_path: Union[str, Path]) -> None:
        """
        Save configuration to YAML file.

        Args:
            yaml_path: Path to save YAML file
        """
        yaml_path = Path(yaml_path)
        yaml_path.parent.mkdir(parents=True, exist_ok=True)

        config_dict = {
            'mode': self.mode,
            'time_resolution': self.time_resolution,
            'simulation_period': {
                'start_date': self.simulation_period.start_date,
                'end_date': self.simulation_period.end_date,
            },
            'battery': {
                'capacity_kwh': self.battery.capacity_kwh,
                'power_kw': self.battery.power_kw,
                'efficiency': self.battery.efficiency,
                'initial_soc_percent': self.battery.initial_soc_percent,
                'min_soc_percent': self.battery.min_soc_percent,
                'max_soc_percent': self.battery.max_soc_percent,
            },
            'data_sources': {
                'prices_file': self.data_sources.prices_file,
                'production_file': self.data_sources.production_file,
                'consumption_file': self.data_sources.consumption_file,
            },
            'mode_specific': {
                'rolling_horizon': {
                    'horizon_hours': self.rolling_horizon.horizon_hours,
                    'update_frequency_minutes': self.rolling_horizon.update_frequency_minutes,
                    'persistent_state': self.rolling_horizon.persistent_state,
                },
                'monthly': {
                    'months': self.monthly.months,
                },
                'yearly': {
                    'horizon_hours': self.yearly.horizon_hours,
                    'weeks': self.yearly.weeks,
                },
            },
            'output_dir': self.output_dir,
            'save_trajectory': self.save_trajectory,
            'save_plots': self.save_plots,
        }

        with open(yaml_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

    def validate(self) -> None:
        """
        Validate configuration parameters.

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate mode
        valid_modes = ["rolling_horizon", "monthly", "yearly"]
        if self.mode not in valid_modes:
            raise ValueError(f"Invalid mode '{self.mode}'. Must be one of: {valid_modes}")

        # Validate time resolution
        valid_resolutions = ["PT60M", "PT15M"]
        if self.time_resolution not in valid_resolutions:
            raise ValueError(f"Invalid time_resolution '{self.time_resolution}'. Must be one of: {valid_resolutions}")

        # Validate battery parameters
        if self.battery.capacity_kwh <= 0:
            raise ValueError("Battery capacity_kwh must be positive")
        if self.battery.power_kw <= 0:
            raise ValueError("Battery power_kw must be positive")
        if not (0 < self.battery.efficiency <= 1):
            raise ValueError("Battery efficiency must be between 0 and 1")
        if not (0 <= self.battery.initial_soc_percent <= 100):
            raise ValueError("Battery initial_soc_percent must be between 0 and 100")
        if not (0 <= self.battery.min_soc_percent < self.battery.max_soc_percent <= 100):
            raise ValueError("Battery SOC limits invalid: 0 <= min < max <= 100")

        # Validate dates
        try:
            start = self.simulation_period.get_start_datetime()
            end = self.simulation_period.get_end_datetime()
            if start >= end:
                raise ValueError("Start date must be before end date")
        except Exception as e:
            raise ValueError(f"Invalid date format: {e}")

        # Validate data source files exist
        for file_attr in ['prices_file', 'production_file', 'consumption_file']:
            file_path = Path(getattr(self.data_sources, file_attr))
            if not file_path.exists():
                raise FileNotFoundError(f"Data file not found: {file_path}")

        # Mode-specific validations
        if self.mode == "rolling_horizon":
            if self.rolling_horizon.horizon_hours <= 0:
                raise ValueError("Rolling horizon horizon_hours must be positive")
            if self.rolling_horizon.update_frequency_minutes <= 0:
                raise ValueError("Rolling horizon update_frequency_minutes must be positive")

        elif self.mode == "monthly":
            if isinstance(self.monthly.months, list):
                for month in self.monthly.months:
                    if not (1 <= month <= 12):
                        raise ValueError(f"Invalid month: {month}. Must be 1-12")

        elif self.mode == "yearly":
            if self.yearly.horizon_hours <= 0:
                raise ValueError("Yearly horizon_hours must be positive")
            if not (1 <= self.yearly.weeks <= 53):
                raise ValueError("Yearly weeks must be between 1 and 53")

    def get_mode_config(self) -> Union[RollingHorizonModeConfig, MonthlyModeConfig, YearlyModeConfig]:
        """Get the mode-specific configuration object."""
        if self.mode == "rolling_horizon":
            return self.rolling_horizon
        elif self.mode == "monthly":
            return self.monthly
        elif self.mode == "yearly":
            return self.yearly
        else:
            raise ValueError(f"Unknown mode: {self.mode}")
