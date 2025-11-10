"""
BatterySimulation Facade for IPython/Interactive Usage.

Provides a simple, Pythonic API for running battery optimization simulations
with direct data passing (DataFrames, arrays) instead of file-based configuration.
"""

from typing import Optional, Union
from datetime import datetime
import pandas as pd
import numpy as np

from src.config.simulation_config import SimulationConfig, BatteryConfigSim
from src.data.data_manager import TimeSeriesData, DataManager
from src.simulation.rolling_horizon_orchestrator import RollingHorizonOrchestrator
from src.simulation.simulation_results import SimulationResults


class BatterySimulation:
    """
    Facade class for easy battery optimization simulations in IPython.

    Supports three usage patterns:
    1. File-based: Load from YAML config + CSV files
    2. DataFrame-based: Pass pandas DataFrames directly
    3. Array-based: Pass numpy arrays directly

    Examples:
        # Pattern 1: File-based (existing workflow)
        >>> sim = BatterySimulation.from_config('configs/working_config.yaml')
        >>> results = sim.run()

        # Pattern 2: DataFrame-based
        >>> df = pd.read_csv('data.csv', index_col=0, parse_dates=True)
        >>> sim = BatterySimulation.from_dataframe(df, battery_kwh=80, battery_kw=60)
        >>> results = sim.run()

        # Pattern 3: Array-based
        >>> timestamps = pd.date_range('2024-06-01', periods=720, freq='h')
        >>> prices = np.random.uniform(0.5, 1.5, 720)
        >>> sim = BatterySimulation.from_arrays(
        ...     timestamps=timestamps,
        ...     prices=prices,
        ...     production=pv_data,
        ...     consumption=load_data,
        ...     battery_kwh=80,
        ...     battery_kw=60
        ... )
        >>> results = sim.run()
    """

    def __init__(
        self,
        config: SimulationConfig,
        data: Optional[TimeSeriesData] = None
    ):
        """
        Initialize battery simulation.

        Args:
            config: Simulation configuration
            data: Optional pre-loaded TimeSeriesData
        """
        self.config = config
        self.data = data
        self._results: Optional[SimulationResults] = None

    @classmethod
    def from_config(cls, config_path: str) -> "BatterySimulation":
        """
        Create simulation from YAML config file (file-based pattern).

        Args:
            config_path: Path to YAML configuration file

        Returns:
            BatterySimulation instance

        Example:
            >>> sim = BatterySimulation.from_config('configs/working_config.yaml')
            >>> results = sim.run()
        """
        config = SimulationConfig.from_yaml(config_path)
        return cls(config=config, data=None)

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        battery_kwh: float,
        battery_kw: float,
        price_col: str = 'price_nok_per_kwh',
        production_col: str = 'pv_production_kw',
        consumption_col: str = 'consumption_kw',
        initial_soc_percent: float = 50.0,
        min_soc_percent: float = 10.0,
        max_soc_percent: float = 90.0,
        efficiency: float = 0.90,
        horizon_hours: int = 24,
        update_frequency_minutes: int = 60,
        resolution: Optional[str] = None
    ) -> "BatterySimulation":
        """
        Create simulation from pandas DataFrame (DataFrame-based pattern).

        Args:
            df: DataFrame with DatetimeIndex and columns for prices, production, consumption
            battery_kwh: Battery energy capacity [kWh]
            battery_kw: Battery power capacity [kW]
            price_col: Column name for prices (default: 'price_nok_per_kwh')
            production_col: Column name for PV production (default: 'pv_production_kw')
            consumption_col: Column name for consumption (default: 'consumption_kw')
            initial_soc_percent: Initial SOC (default: 50%)
            min_soc_percent: Minimum SOC (default: 10%)
            max_soc_percent: Maximum SOC (default: 90%)
            efficiency: Round-trip efficiency (default: 0.90)
            horizon_hours: Optimization horizon (default: 24h)
            update_frequency_minutes: Rolling horizon update frequency (default: 60 min)
            resolution: Time resolution ('PT60M' or 'PT15M'). Auto-detected if None.

        Returns:
            BatterySimulation instance

        Example:
            >>> df = pd.read_csv('data.csv', index_col=0, parse_dates=True)
            >>> sim = BatterySimulation.from_dataframe(df, battery_kwh=80, battery_kw=60)
            >>> results = sim.run()
        """
        # Create TimeSeriesData from DataFrame
        data = TimeSeriesData.from_dataframe(
            df=df,
            price_col=price_col,
            production_col=production_col,
            consumption_col=consumption_col,
            resolution=resolution
        )

        # Create minimal config
        config = cls._create_minimal_config(
            battery_kwh=battery_kwh,
            battery_kw=battery_kw,
            initial_soc_percent=initial_soc_percent,
            min_soc_percent=min_soc_percent,
            max_soc_percent=max_soc_percent,
            efficiency=efficiency,
            horizon_hours=horizon_hours,
            update_frequency_minutes=update_frequency_minutes,
            time_resolution=data.resolution,
            start_date=data.timestamps[0].strftime('%Y-%m-%d'),
            end_date=data.timestamps[-1].strftime('%Y-%m-%d')
        )

        return cls(config=config, data=data)

    @classmethod
    def from_arrays(
        cls,
        timestamps: pd.DatetimeIndex,
        prices: np.ndarray,
        production: np.ndarray,
        consumption: np.ndarray,
        battery_kwh: float,
        battery_kw: float,
        initial_soc_percent: float = 50.0,
        min_soc_percent: float = 10.0,
        max_soc_percent: float = 90.0,
        efficiency: float = 0.90,
        horizon_hours: int = 24,
        update_frequency_minutes: int = 60,
        resolution: Optional[str] = None
    ) -> "BatterySimulation":
        """
        Create simulation from numpy arrays (array-based pattern).

        Args:
            timestamps: DatetimeIndex with timestamps
            prices: Array of electricity prices [NOK/kWh]
            production: Array of PV production [kW]
            consumption: Array of consumption [kW]
            battery_kwh: Battery energy capacity [kWh]
            battery_kw: Battery power capacity [kW]
            initial_soc_percent: Initial SOC (default: 50%)
            min_soc_percent: Minimum SOC (default: 10%)
            max_soc_percent: Maximum SOC (default: 90%)
            efficiency: Round-trip efficiency (default: 0.90)
            horizon_hours: Optimization horizon (default: 24h)
            update_frequency_minutes: Rolling horizon update frequency (default: 60 min)
            resolution: Time resolution ('PT60M' or 'PT15M'). Auto-detected if None.

        Returns:
            BatterySimulation instance

        Example:
            >>> timestamps = pd.date_range('2024-06-01', periods=720, freq='h')
            >>> prices = np.random.uniform(0.5, 1.5, 720)
            >>> production = np.random.uniform(0, 100, 720)
            >>> consumption = np.random.uniform(20, 50, 720)
            >>> sim = BatterySimulation.from_arrays(
            ...     timestamps, prices, production, consumption,
            ...     battery_kwh=80, battery_kw=60
            ... )
            >>> results = sim.run()
        """
        # Create TimeSeriesData from arrays
        data = TimeSeriesData.from_arrays(
            timestamps=timestamps,
            prices=prices,
            production=production,
            consumption=consumption,
            resolution=resolution
        )

        # Create minimal config
        config = cls._create_minimal_config(
            battery_kwh=battery_kwh,
            battery_kw=battery_kw,
            initial_soc_percent=initial_soc_percent,
            min_soc_percent=min_soc_percent,
            max_soc_percent=max_soc_percent,
            efficiency=efficiency,
            horizon_hours=horizon_hours,
            update_frequency_minutes=update_frequency_minutes,
            time_resolution=data.resolution,
            start_date=data.timestamps[0].strftime('%Y-%m-%d'),
            end_date=data.timestamps[-1].strftime('%Y-%m-%d')
        )

        return cls(config=config, data=data)

    @staticmethod
    def _create_minimal_config(
        battery_kwh: float,
        battery_kw: float,
        initial_soc_percent: float,
        min_soc_percent: float,
        max_soc_percent: float,
        efficiency: float,
        horizon_hours: int,
        update_frequency_minutes: int,
        time_resolution: str,
        start_date: str,
        end_date: str
    ) -> SimulationConfig:
        """Create minimal simulation config for programmatic usage."""
        from src.config.simulation_config import (
            SimulationPeriodConfig,
            DataSourceConfig,
            RollingHorizonModeConfig
        )

        return SimulationConfig(
            mode='rolling_horizon',
            time_resolution=time_resolution,
            simulation_period=SimulationPeriodConfig(
                start_date=start_date,
                end_date=end_date
            ),
            battery=BatteryConfigSim(
                capacity_kwh=battery_kwh,
                power_kw=battery_kw,
                initial_soc_percent=initial_soc_percent,
                min_soc_percent=min_soc_percent,
                max_soc_percent=max_soc_percent,
                efficiency=efficiency
            ),
            data_sources=DataSourceConfig(
                prices_file='',  # Not used when data provided directly
                production_file='',
                consumption_file=''
            ),
            rolling_horizon=RollingHorizonModeConfig(
                horizon_hours=horizon_hours,
                update_frequency_minutes=update_frequency_minutes
            )
        )

    def run(self) -> SimulationResults:
        """
        Run the battery optimization simulation.

        Returns:
            SimulationResults with full trajectory and metrics

        Raises:
            RuntimeError: If simulation fails
        """
        # Create orchestrator with optional pre-loaded data
        if self.data is not None:
            # Use custom data manager with pre-loaded data
            orchestrator = RollingHorizonOrchestrator(self.config)
            orchestrator.data_manager = DataManager(self.config, data=self.data)
        else:
            # Standard file-based workflow
            orchestrator = RollingHorizonOrchestrator(self.config)

        # Run simulation
        self._results = orchestrator.run()
        return self._results

    @property
    def results(self) -> Optional[SimulationResults]:
        """Get simulation results (None if not yet run)."""
        return self._results

    def summary(self) -> dict:
        """
        Get summary of simulation results.

        Returns:
            Dictionary with key metrics

        Raises:
            RuntimeError: If simulation has not been run yet
        """
        if self._results is None:
            raise RuntimeError("Simulation not run yet. Call run() first.")

        return {
            'timesteps': len(self._results.trajectory),
            'final_soc_percent': self._results.final_soc_percent,
            'total_energy_cost': self._results.trajectory['P_grid_import_kw'].sum() * 1.0,  # Simplified
            'output_path': str(self._results.output_path) if self._results.output_path else None
        }
