"""
Adapter to make existing MonthlyLPOptimizer conform to BaseOptimizer interface.

This adapter wraps the existing core/lp_monthly_optimizer.py implementation.
"""

from typing import Optional
import pandas as pd
import numpy as np

from core.lp_monthly_optimizer import (
    MonthlyLPOptimizer as CoreMonthlyLPOptimizer,
    MonthlyLPResult,
)
from src.operational.state_manager import BatterySystemState
from src.optimization.base_optimizer import (
    BaseOptimizer,
    OptimizationResult,
)
from src.config.legacy_config_adapter import get_global_legacy_config


class MonthlyLPAdapter(BaseOptimizer):
    """
    Adapter for existing MonthlyLPOptimizer to work with new BaseOptimizer interface.

    This allows the monthly LP implementation to be used in the new orchestration system.
    """

    def __init__(
        self,
        battery_kwh: float,
        battery_kw: float,
        battery_efficiency: float = 0.90,
        min_soc_percent: float = 10.0,
        max_soc_percent: float = 90.0,
        resolution: str = 'PT60M',
        use_global_config: bool = True,
    ):
        """
        Initialize monthly LP adapter.

        Args:
            battery_kwh: Battery energy capacity
            battery_kw: Battery power capacity
            battery_efficiency: Round-trip efficiency (0-1)
            min_soc_percent: Minimum SOC (0-100)
            max_soc_percent: Maximum SOC (0-100)
            resolution: Time resolution ('PT60M' or 'PT15M')
            use_global_config: Use global config object for tariffs/system params
        """
        super().__init__(
            battery_kwh=battery_kwh,
            battery_kw=battery_kw,
            battery_efficiency=battery_efficiency,
            min_soc_percent=min_soc_percent,
            max_soc_percent=max_soc_percent,
        )

        self.resolution = resolution
        self.use_global_config = use_global_config

        # Initialize core optimizer with global config
        if use_global_config:
            self._core_optimizer = CoreMonthlyLPOptimizer(
                config=get_global_legacy_config(),
                resolution=resolution,
                battery_kwh=battery_kwh,
                battery_kw=battery_kw,
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
        Run monthly LP optimization.

        Args:
            timestamps: Time index for full month
            pv_production: PV production in kW
            consumption: Consumption in kW
            spot_prices: Electricity prices in NOK/kWh
            initial_soc_kwh: Initial battery SOC (optional)
            battery_state: Complete battery system state (optional, not used for monthly)

        Returns:
            OptimizationResult with trajectories and costs

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If optimization fails
        """
        # Validate inputs
        self._validate_inputs(timestamps, pv_production, consumption, spot_prices)

        # Determine initial SOC
        E_initial = self._get_initial_soc(initial_soc_kwh, battery_state)

        # Call core optimizer
        try:
            core_result: MonthlyLPResult = self._core_optimizer.optimize_month(
                month_idx=0,  # Not used in core optimizer logic
                timestamps=timestamps,
                pv_production=pv_production,
                load_consumption=consumption,
                spot_prices=spot_prices,
                E_initial=E_initial,
            )
        except Exception as e:
            raise RuntimeError(f"Monthly LP optimization failed: {e}")

        # Convert core result to unified OptimizationResult
        unified_result = OptimizationResult(
            P_charge=core_result.P_charge,
            P_discharge=core_result.P_discharge,
            P_grid_import=core_result.P_grid_import,
            P_grid_export=core_result.P_grid_export,
            E_battery=core_result.E_battery,
            P_curtail=core_result.P_curtail,
            objective_value=core_result.objective_value,
            energy_cost=core_result.energy_cost,
            power_cost=core_result.power_cost,
            degradation_cost=core_result.degradation_cost if hasattr(core_result, 'degradation_cost') else 0.0,
            peak_penalty_cost=None,  # Monthly LP doesn't have peak penalty
            DOD_abs=core_result.DOD_abs if hasattr(core_result, 'DOD_abs') else None,
            DP_cyc=core_result.DP_cyc if hasattr(core_result, 'DP_cyc') else None,
            DP_cal=core_result.DP_cal if hasattr(core_result, 'DP_cal') else None,
            DP_total=core_result.DP_total if hasattr(core_result, 'DP_total') else None,
            success=core_result.success,
            message=core_result.message,
            solve_time_seconds=0.0,  # Not tracked in core result
            E_battery_final=core_result.E_battery_final,
        )

        return unified_result

    def get_resolution(self) -> str:
        """Get time resolution ('PT60M' or 'PT15M')."""
        return self.resolution
