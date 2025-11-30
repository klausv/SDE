"""
Baseline Calculator - No Battery Mode

Calculates system performance without battery storage, reusing infrastructure
for pricing, weather, tariffs, and result persistence. Provides critical
economic baseline for comparing battery investment ROI.

This calculator bypasses optimization solvers entirely, providing instant
calculation instead of 30-60s solver overhead.
"""

from typing import Optional
import pandas as pd
import numpy as np
import time

from src.optimization.base_optimizer import BaseOptimizer, OptimizationResult
from src.operational.state_manager import BatterySystemState


class BaselineCalculator(BaseOptimizer):
    """
    Baseline calculator for no-battery scenario.

    Calculates grid flows and costs without battery storage, respecting
    grid limits and applying curtailment when necessary. Reuses the same
    tariff and pricing infrastructure as battery optimizers.

    Design Decision:
        - Uses BaseOptimizer interface for compatibility
        - Returns OptimizationResult with zero battery arrays
        - Instant calculation (no solver overhead)
        - Respects grid_limit_kw for curtailment

    Performance:
        - ~0.001s calculation time vs 30-60s for LP/MPC solvers
        - 99%+ time savings for baseline scenarios

    Usage:
        >>> baseline = BaselineCalculator(grid_limit_kw=77)
        >>> result = baseline.optimize(timestamps, pv, consumption, prices)
        >>> print(f"Baseline cost: {result.objective_value:.0f} NOK")
    """

    def __init__(
        self,
        grid_limit_kw: Optional[float] = None,
        grid_limit_import_kw: Optional[float] = None,
        grid_limit_export_kw: Optional[float] = None,
        battery_kwh: float = 0.0,  # Always 0 for baseline
        battery_kw: float = 0.0,   # Always 0 for baseline
        battery_efficiency: float = 0.90,  # Not used but kept for interface
        min_soc_percent: float = 10.0,     # Not used
        max_soc_percent: float = 90.0,     # Not used
    ):
        """
        Initialize baseline calculator.

        Args:
            grid_limit_kw: Overall grid limit (applied to both import/export)
            grid_limit_import_kw: Grid import limit (if different from export)
            grid_limit_export_kw: Grid export limit (if different from import)
            battery_kwh: Always 0 for baseline (interface compatibility)
            battery_kw: Always 0 for baseline (interface compatibility)
            battery_efficiency: Not used (interface compatibility)
            min_soc_percent: Not used (interface compatibility)
            max_soc_percent: Not used (interface compatibility)

        Note:
            Battery parameters are kept for BaseOptimizer interface compatibility
            but are always zero for baseline calculations.
        """
        # Override battery params to 0 for baseline
        # Use 0.01 instead of 0 to avoid validation errors in BaseOptimizer
        super().__init__(
            battery_kwh=0.01,  # Small value to pass validation
            battery_kw=0.01,   # Small value to pass validation
            battery_efficiency=battery_efficiency,
            min_soc_percent=min_soc_percent,
            max_soc_percent=max_soc_percent,
        )

        # Override to actual zero for calculations
        self.battery_kwh = 0.0
        self.battery_kw = 0.0

        # Grid limits for curtailment
        if grid_limit_kw is not None:
            self.grid_limit_import_kw = grid_limit_kw
            self.grid_limit_export_kw = grid_limit_kw
        else:
            self.grid_limit_import_kw = grid_limit_import_kw if grid_limit_import_kw is not None else float('inf')
            self.grid_limit_export_kw = grid_limit_export_kw if grid_limit_export_kw is not None else float('inf')

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
        Calculate baseline scenario without battery.

        Power balance without battery:
            P_net = P_pv - P_consumption

            If P_net > 0 (surplus):
                P_grid_export = min(P_net, grid_limit_export)
                P_curtail = max(0, P_net - grid_limit_export)
                P_grid_import = 0

            If P_net <= 0 (deficit):
                P_grid_import = min(abs(P_net), grid_limit_import)
                P_grid_export = 0
                P_curtail = 0

        Args:
            timestamps: Time index for data
            pv_production: PV production in kW
            consumption: Consumption in kW
            spot_prices: Electricity prices in NOK/kWh
            initial_soc_kwh: Ignored (no battery)
            battery_state: Ignored (no battery)

        Returns:
            OptimizationResult with zero battery arrays and calculated costs
        """
        start_time = time.time()

        # Validate inputs
        self._validate_inputs(timestamps, pv_production, consumption, spot_prices)

        n = len(timestamps)
        dt_hours = self._calculate_timestep_hours(timestamps)

        # Calculate net power (positive = surplus, negative = deficit)
        P_net = pv_production - consumption

        # Initialize arrays
        P_grid_import = np.zeros(n)
        P_grid_export = np.zeros(n)
        P_curtail = np.zeros(n)

        # Calculate grid flows and curtailment
        for i in range(n):
            if P_net[i] > 0:
                # Surplus - export to grid (up to limit)
                P_grid_export[i] = min(P_net[i], self.grid_limit_export_kw)
                P_curtail[i] = max(0, P_net[i] - self.grid_limit_export_kw)
                P_grid_import[i] = 0
            else:
                # Deficit - import from grid (up to limit)
                P_grid_import[i] = min(abs(P_net[i]), self.grid_limit_import_kw)
                P_grid_export[i] = 0
                P_curtail[i] = 0

        # Battery arrays are all zeros (no battery)
        P_charge = np.zeros(n)
        P_discharge = np.zeros(n)
        E_battery = np.zeros(n)

        # Calculate energy costs
        # Import cost (positive) - Export revenue (negative)
        energy_import_cost = np.sum(P_grid_import * dt_hours * spot_prices)
        energy_export_revenue = np.sum(P_grid_export * dt_hours * spot_prices)
        energy_cost = energy_import_cost - energy_export_revenue

        # Total cost (only energy for baseline, power tariff handled by orchestrator)
        objective_value = energy_cost

        solve_time = time.time() - start_time

        return OptimizationResult(
            P_charge=P_charge,
            P_discharge=P_discharge,
            P_grid_import=P_grid_import,
            P_grid_export=P_grid_export,
            E_battery=E_battery,
            P_curtail=P_curtail,
            objective_value=objective_value,
            energy_cost=energy_cost,
            power_cost=None,  # Calculated by orchestrator
            degradation_cost=None,  # No battery
            peak_penalty_cost=None,
            DOD_abs=None,
            DP_cyc=None,
            DP_cal=None,
            DP_total=None,
            success=True,
            message="Baseline calculation (no battery)",
            solve_time_seconds=solve_time,
            E_battery_final=0.0,
        )

    def _calculate_timestep_hours(self, timestamps: pd.DatetimeIndex) -> np.ndarray:
        """
        Calculate timestep duration in hours.

        Args:
            timestamps: Time index

        Returns:
            Array of timestep durations in hours
        """
        if len(timestamps) < 2:
            # Default to 1 hour for single timestep
            return np.array([1.0])

        # Calculate differences
        dt = np.diff(timestamps).astype('timedelta64[s]').astype(float) / 3600.0

        # Extend to match length (repeat last interval)
        dt_hours = np.append(dt, dt[-1])

        return dt_hours

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"BaselineCalculator("
            f"grid_import={self.grid_limit_import_kw:.0f} kW, "
            f"grid_export={self.grid_limit_export_kw:.0f} kW)"
        )
