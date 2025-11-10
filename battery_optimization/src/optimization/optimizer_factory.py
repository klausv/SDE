"""
Factory for creating optimizer instances based on simulation configuration.

Provides unified interface for creating different optimizer types.
"""

from typing import Literal
from src.config.simulation_config import SimulationConfig
from src.optimization.base_optimizer import BaseOptimizer
from src.optimization.rolling_horizon_adapter import RollingHorizonAdapter
from src.optimization.monthly_lp_adapter import MonthlyLPAdapter
from src.optimization.weekly_optimizer import WeeklyOptimizer


class OptimizerFactory:
    """
    Factory for creating battery optimizers.

    Creates appropriate optimizer instance based on simulation mode and configuration.
    """

    @staticmethod
    def create(
        mode: Literal["rolling_horizon", "monthly", "yearly"],
        config: SimulationConfig
    ) -> BaseOptimizer:
        """
        Create optimizer for specified simulation mode.

        Args:
            mode: Simulation mode ('rolling_horizon', 'monthly', or 'yearly')
            config: Simulation configuration

        Returns:
            BaseOptimizer instance configured for specified mode

        Raises:
            ValueError: If mode is invalid or configuration is incompatible
        """
        battery_config = config.battery

        if mode == "rolling_horizon":
            return OptimizerFactory._create_rolling_horizon(config)

        elif mode == "monthly":
            return OptimizerFactory._create_monthly(config)

        elif mode == "yearly":
            return OptimizerFactory._create_yearly(config)

        else:
            raise ValueError(
                f"Invalid mode '{mode}'. "
                f"Must be 'rolling_horizon', 'monthly', or 'yearly'"
            )

    @staticmethod
    def _create_rolling_horizon(config: SimulationConfig) -> RollingHorizonAdapter:
        """
        Create rolling horizon optimizer.

        Args:
            config: Simulation configuration

        Returns:
            RollingHorizonAdapter configured from config
        """
        battery_config = config.battery
        rolling_config = config.rolling_horizon

        # Note: Current implementation uses 15-min resolution internally
        # regardless of config.time_resolution
        optimizer = RollingHorizonAdapter(
            battery_kwh=battery_config.capacity_kwh,
            battery_kw=battery_config.power_kw,
            battery_efficiency=battery_config.efficiency,
            min_soc_percent=battery_config.min_soc_percent,
            max_soc_percent=battery_config.max_soc_percent,
            horizon_hours=rolling_config.horizon_hours,
            use_global_config=True,
        )

        return optimizer

    @staticmethod
    def _create_monthly(config: SimulationConfig) -> MonthlyLPAdapter:
        """
        Create monthly optimizer.

        Args:
            config: Simulation configuration

        Returns:
            MonthlyLPAdapter configured from config
        """
        battery_config = config.battery

        optimizer = MonthlyLPAdapter(
            battery_kwh=battery_config.capacity_kwh,
            battery_kw=battery_config.power_kw,
            battery_efficiency=battery_config.efficiency,
            min_soc_percent=battery_config.min_soc_percent,
            max_soc_percent=battery_config.max_soc_percent,
            resolution=config.time_resolution,
            use_global_config=True,
        )

        return optimizer

    @staticmethod
    def _create_yearly(config: SimulationConfig) -> WeeklyOptimizer:
        """
        Create yearly optimizer (weekly horizon).

        Args:
            config: Simulation configuration

        Returns:
            WeeklyOptimizer configured from config
        """
        battery_config = config.battery
        yearly_config = config.yearly

        optimizer = WeeklyOptimizer(
            battery_kwh=battery_config.capacity_kwh,
            battery_kw=battery_config.power_kw,
            battery_efficiency=battery_config.efficiency,
            min_soc_percent=battery_config.min_soc_percent,
            max_soc_percent=battery_config.max_soc_percent,
            resolution=config.time_resolution,
            horizon_hours=yearly_config.horizon_hours,
            use_global_config=True,
        )

        return optimizer

    @staticmethod
    def create_from_config(config: SimulationConfig) -> BaseOptimizer:
        """
        Create optimizer from configuration (convenience method).

        Uses config.mode to determine optimizer type.

        Args:
            config: Simulation configuration

        Returns:
            BaseOptimizer instance

        Raises:
            ValueError: If configuration is invalid
        """
        return OptimizerFactory.create(mode=config.mode, config=config)
