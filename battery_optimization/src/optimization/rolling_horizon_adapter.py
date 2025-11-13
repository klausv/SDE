"""
Adapter to make existing RollingHorizonOptimizer conform to BaseOptimizer interface.

This adapter wraps the existing core/rolling_horizon_optimizer.py implementation
without modifying it, allowing it to work with the new unified orchestration system.
"""

from typing import Optional
import pandas as pd
import numpy as np

from core.rolling_horizon_optimizer import (
    RollingHorizonOptimizer as CoreRollingHorizonOptimizer,
    RollingHorizonResult,
)
from src.operational.state_manager import BatterySystemState
from src.optimization.base_optimizer import (
    BaseOptimizer,
    OptimizationResult,
)
from src.config.legacy_config_adapter import get_global_legacy_config


class RollingHorizonAdapter(BaseOptimizer):
    """
    Adapter for existing RollingHorizonOptimizer to work with new BaseOptimizer interface.

    This allows the proven rolling horizon implementation to be used in the new
    orchestration system without modifications to the core logic.
    """

    def __init__(
        self,
        battery_kwh: float,
        battery_kw: float,
        battery_efficiency: float = 0.90,
        min_soc_percent: float = 10.0,
        max_soc_percent: float = 90.0,
        horizon_hours: int = 24,
        resolution: str = 'PT15M',
        use_global_config: bool = True,
    ):
        """
        Initialize rolling horizon adapter.

        Args:
            battery_kwh: Battery energy capacity
            battery_kw: Battery power capacity
            battery_efficiency: Round-trip efficiency (0-1)
            min_soc_percent: Minimum SOC (0-100)
            max_soc_percent: Maximum SOC (0-100)
            horizon_hours: Optimization horizon in hours (default: 24)
            resolution: Time resolution - 'PT60M' (hourly) or 'PT15M' (15-minute, default)
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

        # Initialize core optimizer with global config and configurable resolution
        if use_global_config:
            self._core_optimizer = CoreRollingHorizonOptimizer(
                config=get_global_legacy_config(),
                battery_kwh=battery_kwh,
                battery_kw=battery_kw,
                horizon_hours=horizon_hours,
                resolution=resolution,
            )
        else:
            raise ValueError("Non-global config mode not yet supported")

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
        Run rolling horizon optimization.

        Args:
            timestamps: Time index for optimization window
            pv_production: PV production in kW
            consumption: Consumption in kW
            spot_prices: Electricity prices in NOK/kWh
            initial_soc_kwh: Initial battery SOC (optional)
            battery_state: Complete battery system state (optional)

        Returns:
            OptimizationResult with trajectories and costs

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If optimization fails
        """
        # Validate inputs
        self._validate_inputs(timestamps, pv_production, consumption, spot_prices)

        # Create/update battery state
        if battery_state is None:
            E_initial = self._get_initial_soc(initial_soc_kwh, battery_state)
            battery_state = BatterySystemState(
                current_soc_kwh=E_initial,
                battery_capacity_kwh=self.battery_kwh,
            )

        # Call core optimizer (method is optimize_24h in legacy code)
        try:
            core_result: RollingHorizonResult = self._core_optimizer.optimize_24h(
                current_state=battery_state,  # Legacy uses BatterySystemState
                pv_production=pv_production,
                load_consumption=consumption,
                spot_prices=spot_prices,
                timestamps=timestamps,
            )
        except Exception as e:
            raise RuntimeError(f"Rolling horizon optimization failed: {e}")

        # Convert core result to unified OptimizationResult
        unified_result = OptimizationResult(
            P_charge=core_result.P_charge,
            P_discharge=core_result.P_discharge,
            P_grid_import=core_result.P_grid_import,
            P_grid_export=core_result.P_grid_export,
            E_battery=core_result.E_battery,
            P_curtail=core_result.P_curtail,
            objective_value=core_result.objective_value_actual,  # Use actual (not LP approximation)
            energy_cost=core_result.energy_cost,
            power_cost=None,  # Rolling horizon doesn't have separate power cost
            degradation_cost=core_result.degradation_cost,
            peak_penalty_cost=core_result.peak_penalty_actual,  # Use actual step function
            DOD_abs=core_result.DOD_abs,
            DP_cyc=core_result.DP_cyc,
            DP_cal=None,  # Not stored separately in core result
            DP_total=core_result.DP_total,
            success=core_result.success,
            message=core_result.message,
            solve_time_seconds=core_result.solve_time_seconds,
            E_battery_final=core_result.E_battery_final,
        )

        return unified_result

    def get_horizon_hours(self) -> int:
        """Get optimization horizon in hours."""
        return self.horizon_hours

    def get_timesteps_per_hour(self) -> int:
        """Get number of timesteps per hour (4 for 15-min resolution)."""
        return 4  # Fixed 15-min resolution in core optimizer

    def get_total_timesteps(self) -> int:
        """Get total number of timesteps in horizon."""
        return self.horizon_hours * self.get_timesteps_per_hour()
