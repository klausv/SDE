"""
Abstract base class for battery optimization algorithms.

Defines common interface for all optimizer implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import pandas as pd
import numpy as np

from src.operational.state_manager import BatterySystemState


@dataclass
class OptimizationResult:
    """
    Common result structure for all optimizers.

    Contains optimization trajectories, costs, and metadata.
    """
    # Optimization trajectories (all same length)
    P_charge: np.ndarray  # Battery charging power (kW)
    P_discharge: np.ndarray  # Battery discharging power (kW)
    P_grid_import: np.ndarray  # Grid import power (kW)
    P_grid_export: np.ndarray  # Grid export power (kW)
    E_battery: np.ndarray  # Battery state of charge (kWh)
    P_curtail: np.ndarray  # PV curtailment (kW)

    # Cost breakdown
    objective_value: float  # Total cost (NOK)
    energy_cost: float  # Spot energy cost (NOK)
    power_cost: Optional[float] = None  # Power tariff cost (NOK)
    degradation_cost: Optional[float] = None  # Battery degradation cost (NOK)
    peak_penalty_cost: Optional[float] = None  # Peak penalty (rolling horizon)

    # Degradation tracking (optional)
    DOD_abs: Optional[np.ndarray] = None  # Absolute depth of discharge
    DP_cyc: Optional[np.ndarray] = None  # Cycle degradation per timestep
    DP_cal: Optional[np.ndarray] = None  # Calendar degradation per timestep
    DP_total: Optional[np.ndarray] = None  # Total degradation per timestep

    # Metadata
    success: bool = True
    message: str = ""
    solve_time_seconds: float = 0.0

    # Final battery state
    E_battery_final: Optional[float] = None

    @property
    def next_battery_setpoint_kw(self) -> float:
        """Get next control action (for rolling horizon)."""
        if len(self.P_charge) > 0:
            return self.P_charge[0] - self.P_discharge[0]
        return 0.0

    def to_dataframe(self, timestamps: pd.DatetimeIndex) -> pd.DataFrame:
        """
        Convert optimization result to DataFrame.

        Args:
            timestamps: Timestamps corresponding to result arrays

        Returns:
            DataFrame with all trajectories
        """
        data = {
            'timestamp': timestamps,
            'P_charge_kw': self.P_charge,
            'P_discharge_kw': self.P_discharge,
            'P_grid_import_kw': self.P_grid_import,
            'P_grid_export_kw': self.P_grid_export,
            'E_battery_kwh': self.E_battery,
            'P_curtail_kw': self.P_curtail,
        }

        # Add optional degradation columns
        if self.DOD_abs is not None:
            data['DOD_abs'] = self.DOD_abs
        if self.DP_cyc is not None:
            data['DP_cyc'] = self.DP_cyc
        if self.DP_cal is not None:
            data['DP_cal'] = self.DP_cal
        if self.DP_total is not None:
            data['DP_total'] = self.DP_total

        return pd.DataFrame(data).set_index('timestamp')


class BaseOptimizer(ABC):
    """
    Abstract base class for battery optimization algorithms.

    All optimizer implementations must inherit from this class and implement
    the optimize() method.
    """

    def __init__(
        self,
        battery_kwh: float,
        battery_kw: float,
        battery_efficiency: float = 0.90,
        min_soc_percent: float = 10.0,
        max_soc_percent: float = 90.0,
    ):
        """
        Initialize base optimizer.

        Args:
            battery_kwh: Battery energy capacity
            battery_kw: Battery power capacity
            battery_efficiency: Round-trip efficiency (0-1)
            min_soc_percent: Minimum SOC (0-100)
            max_soc_percent: Maximum SOC (0-100)
        """
        self.battery_kwh = battery_kwh
        self.battery_kw = battery_kw
        self.battery_efficiency = battery_efficiency
        self.min_soc_percent = min_soc_percent
        self.max_soc_percent = max_soc_percent

        # Validate parameters
        if battery_kwh <= 0:
            raise ValueError("battery_kwh must be positive")
        if battery_kw <= 0:
            raise ValueError("battery_kw must be positive")
        if not (0 < battery_efficiency <= 1):
            raise ValueError("battery_efficiency must be between 0 and 1")
        if not (0 <= min_soc_percent < max_soc_percent <= 100):
            raise ValueError("Invalid SOC limits: 0 <= min < max <= 100")

    @abstractmethod
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
        Run optimization for given inputs.

        Args:
            timestamps: Time index for data
            pv_production: PV production in kW
            consumption: Consumption in kW
            spot_prices: Electricity prices in NOK/kWh
            initial_soc_kwh: Initial battery state of charge (optional)
            battery_state: Complete battery system state (optional, for rolling horizon)

        Returns:
            OptimizationResult with trajectories and costs

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If optimization fails
        """
        pass

    def _validate_inputs(
        self,
        timestamps: pd.DatetimeIndex,
        pv_production: np.ndarray,
        consumption: np.ndarray,
        spot_prices: np.ndarray,
    ) -> None:
        """
        Validate optimization inputs.

        Args:
            timestamps: Time index
            pv_production: PV production array
            consumption: Consumption array
            spot_prices: Price array

        Raises:
            ValueError: If inputs are invalid
        """
        n = len(timestamps)

        if len(pv_production) != n:
            raise ValueError(f"pv_production length {len(pv_production)} != timestamps length {n}")
        if len(consumption) != n:
            raise ValueError(f"consumption length {len(consumption)} != timestamps length {n}")
        if len(spot_prices) != n:
            raise ValueError(f"spot_prices length {len(spot_prices)} != timestamps length {n}")

        if n == 0:
            raise ValueError("Empty input arrays")

        if np.any(pv_production < 0):
            raise ValueError("pv_production contains negative values")
        if np.any(consumption < 0):
            raise ValueError("consumption contains negative values")

    def _get_initial_soc(
        self,
        initial_soc_kwh: Optional[float],
        battery_state: Optional[BatterySystemState],
    ) -> float:
        """
        Determine initial SOC from various sources.

        Priority: initial_soc_kwh > battery_state.current_soc_kwh > 50% SOC

        Args:
            initial_soc_kwh: Explicit initial SOC
            battery_state: Battery system state

        Returns:
            Initial SOC in kWh
        """
        if initial_soc_kwh is not None:
            return initial_soc_kwh

        if battery_state is not None:
            return battery_state.current_soc_kwh

        # Default to 50% SOC
        return self.battery_kwh * 0.5
