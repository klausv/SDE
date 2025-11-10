"""
Weekly optimizer for yearly simulation mode.

Uses MonthlyLPAdapter with 168-hour (1 week) horizon for annual investment analysis.
"""

from typing import Optional
import pandas as pd
import numpy as np

from src.operational.state_manager import BatterySystemState
from src.optimization.base_optimizer import (
    BaseOptimizer,
    OptimizationResult,
)
from src.optimization.monthly_lp_adapter import MonthlyLPAdapter


class WeeklyOptimizer(BaseOptimizer):
    """
    Weekly optimizer using 168-hour horizon.

    This is a wrapper around MonthlyLPAdapter configured for weekly optimization.
    Used in yearly mode for profitability analysis with 52 weekly solves.
    """

    def __init__(
        self,
        battery_kwh: float,
        battery_kw: float,
        battery_efficiency: float = 0.90,
        min_soc_percent: float = 10.0,
        max_soc_percent: float = 90.0,
        resolution: str = 'PT60M',
        horizon_hours: int = 168,
        use_global_config: bool = True,
    ):
        """
        Initialize weekly optimizer.

        Args:
            battery_kwh: Battery energy capacity
            battery_kw: Battery power capacity
            battery_efficiency: Round-trip efficiency (0-1)
            min_soc_percent: Minimum SOC (0-100)
            max_soc_percent: Maximum SOC (0-100)
            resolution: Time resolution ('PT60M' or 'PT15M')
            horizon_hours: Optimization horizon in hours (default: 168 = 1 week)
            use_global_config: Use global config object for tariffs/system params
        """
        super().__init__(
            battery_kwh=battery_kwh,
            battery_kw=battery_kw,
            battery_efficiency=battery_efficiency,
            min_soc_percent=min_soc_percent,
            max_soc_percent=max_soc_percent,
        )

        self.horizon_hours = horizon_hours
        self.resolution = resolution
        self.use_global_config = use_global_config

        # Use MonthlyLPAdapter as the underlying optimizer
        # (it works for any time period, not just months)
        self._optimizer = MonthlyLPAdapter(
            battery_kwh=battery_kwh,
            battery_kw=battery_kw,
            battery_efficiency=battery_efficiency,
            min_soc_percent=min_soc_percent,
            max_soc_percent=max_soc_percent,
            resolution=resolution,
            use_global_config=use_global_config,
        )

        # Calculate expected timesteps
        timesteps_per_hour = 1 if resolution == 'PT60M' else 4
        self.expected_timesteps = horizon_hours * timesteps_per_hour

    def optimize(
        self,
        timestamps: pd.DatetimeIndex,
        pv_production: np.ndarray,
        consumption: np.ndarray,
        spot_prices: np.ndarray,
        initial_soc_kwh: Optional[float] = None,
        battery_state: Optional[BatterySystemState] = None,
    ) -> OptimizationResult:
        """
        Run weekly optimization.

        Args:
            timestamps: Time index for one week (168 hours)
            pv_production: PV production in kW
            consumption: Consumption in kW
            spot_prices: Electricity prices in NOK/kWh
            initial_soc_kwh: Initial battery SOC (optional)
            battery_state: Complete battery system state (optional)

        Returns:
            OptimizationResult with trajectories and costs

        Raises:
            ValueError: If inputs are invalid or not weekly period
            RuntimeError: If optimization fails
        """
        # Validate inputs
        self._validate_inputs(timestamps, pv_production, consumption, spot_prices)

        # Validate time period is approximately one week
        actual_hours = len(timestamps) * (1.0 if self.resolution == 'PT60M' else 0.25)
        if abs(actual_hours - self.horizon_hours) > 1:  # Allow 1h tolerance
            raise ValueError(
                f"Expected {self.horizon_hours} hours of data, "
                f"got {actual_hours} hours ({len(timestamps)} timesteps)"
            )

        # Delegate to monthly LP adapter (works for any period)
        try:
            result = self._optimizer.optimize(
                timestamps=timestamps,
                pv_production=pv_production,
                consumption=consumption,
                spot_prices=spot_prices,
                initial_soc_kwh=initial_soc_kwh,
                battery_state=battery_state,
            )
        except Exception as e:
            raise RuntimeError(f"Weekly optimization failed: {e}")

        return result

    def get_horizon_hours(self) -> int:
        """Get optimization horizon in hours."""
        return self.horizon_hours

    def get_resolution(self) -> str:
        """Get time resolution ('PT60M' or 'PT15M')."""
        return self.resolution

    def get_expected_timesteps(self) -> int:
        """Get expected number of timesteps for weekly optimization."""
        return self.expected_timesteps
