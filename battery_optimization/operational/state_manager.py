"""
Battery System State Manager for Rolling Horizon Optimization.

Tracks system state variables required for adaptive peak penalty calculation
and operational decision-making. Implements the methodology from
PEAK_PENALTY_METHODOLOGY.md.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class BatterySystemState:
    """
    Tracks real-time state of battery system for rolling horizon optimization.

    State variables:
        - Battery SOC (State of Charge)
        - Monthly peak demand tracking
        - Time within month for penalty calculation
    """

    # Battery state
    current_soc_kwh: float = 0.0           # Current battery energy [kWh]
    battery_capacity_kwh: float = 0.0      # Nominal capacity [kWh]

    # Monthly peak tracking
    current_monthly_peak_kw: float = 0.0   # Peak grid import this month [kW]
    month_start_date: Optional[datetime] = None
    last_update: Optional[datetime] = None

    # Tariff parameters (for penalty calculation)
    power_tariff_rate_nok_per_kw: float = 0.0  # Average tariff rate [NOK/kW/month]

    def __post_init__(self):
        """Initialize with current time if not provided."""
        if self.last_update is None:
            self.last_update = datetime.now()
        if self.month_start_date is None:
            self.month_start_date = self.last_update.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @property
    def current_soc_percent(self) -> float:
        """Current SOC as percentage [0-100]."""
        if self.battery_capacity_kwh == 0:
            return 0.0
        return 100.0 * self.current_soc_kwh / self.battery_capacity_kwh

    @property
    def days_remaining_in_month(self) -> int:
        """Days remaining until end of current month."""
        if self.last_update is None:
            return 15  # Default mid-month

        # Get last day of current month
        if self.last_update.month == 12:
            next_month = self.last_update.replace(year=self.last_update.year + 1, month=1, day=1)
        else:
            next_month = self.last_update.replace(month=self.last_update.month + 1, day=1)

        month_end = next_month - pd.Timedelta(days=1)
        days_left = (month_end.date() - self.last_update.date()).days

        return max(0, days_left)

    @property
    def days_elapsed_in_month(self) -> int:
        """Days elapsed since start of current month."""
        if self.last_update is None or self.month_start_date is None:
            return 15  # Default mid-month

        return (self.last_update.date() - self.month_start_date.date()).days

    def update_from_measurement(self,
                                timestamp: datetime,
                                soc_kwh: float,
                                grid_import_power_kw: float):
        """
        Update state from real-time measurements.

        Args:
            timestamp: Measurement timestamp
            soc_kwh: Battery state of charge [kWh]
            grid_import_power_kw: Current grid import power [kW] (positive = import)
        """
        # Check for month boundary crossing
        if self.last_update is not None and timestamp.month != self.last_update.month:
            self._reset_monthly_peak(timestamp)

        # Update battery SOC
        self.current_soc_kwh = soc_kwh

        # Update monthly peak if exceeded
        if grid_import_power_kw > self.current_monthly_peak_kw:
            self.current_monthly_peak_kw = grid_import_power_kw

        self.last_update = timestamp

    def _reset_monthly_peak(self, new_month_timestamp: datetime):
        """Reset peak tracking at month boundary."""
        self.current_monthly_peak_kw = 0.0
        self.month_start_date = new_month_timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def calculate_adaptive_peak_penalty(self,
                                       current_grid_import_kw: float,
                                       forecast_grid_import_24h: np.ndarray) -> float:
        """
        Calculate adaptive peak penalty coefficient for LP objective function.

        Implements the state-based penalty methodology from PEAK_PENALTY_METHODOLOGY.md:

        penalty = base × proximity_factor × forecast_risk × time_factor

        Args:
            current_grid_import_kw: Current grid import power [kW]
            forecast_grid_import_24h: 24-hour forecast of grid import [kW]

        Returns:
            Penalty coefficient [NOK/kW] for peak violation in LP objective
        """
        if self.power_tariff_rate_nok_per_kw == 0:
            return 0.0  # No power tariff configured

        # Base penalty: proportional to remaining month cost impact
        # If we create a new peak now, we pay for it for rest of month
        # BUT: for a 24h rolling horizon, we only charge this window's share (1/days_left)
        # This gives the marginal cost of a peak increase for THIS 24h period
        days_left = max(1, self.days_remaining_in_month)
        monthly_penalty = self.power_tariff_rate_nok_per_kw * (days_left / 30.0)
        base_penalty = monthly_penalty / days_left  # Prorate to 1-day share

        # Proximity factor: amplify if current demand is close to peak
        # (Higher risk of accidentally exceeding)
        proximity_threshold = 0.9 * self.current_monthly_peak_kw
        if current_grid_import_kw > proximity_threshold and self.current_monthly_peak_kw > 0:
            proximity_factor = 2.0  # Double penalty when near peak
        else:
            proximity_factor = 1.0

        # Forecast risk factor: amplify if forecast predicts peak exceedance
        # Check if any forecasted value exceeds current peak
        max_forecast = np.max(forecast_grid_import_24h) if len(forecast_grid_import_24h) > 0 else 0.0
        if max_forecast > self.current_monthly_peak_kw and self.current_monthly_peak_kw > 0:
            forecast_risk_factor = 1.5  # Increase penalty if peak violation likely
        else:
            forecast_risk_factor = 1.0

        # Time factor: increase penalty as month progresses
        # (Later in month = peak harder to reduce, more time to pay for it)
        days_elapsed = self.days_elapsed_in_month
        time_factor = 1.0 + 0.5 * (days_elapsed / 30.0)  # 1.0 to 1.5

        # Combined adaptive penalty
        penalty = base_penalty * proximity_factor * forecast_risk_factor * time_factor

        return penalty

    def get_state_summary(self) -> dict:
        """Get summary of current state for logging/debugging."""
        return {
            'timestamp': self.last_update.isoformat() if self.last_update else None,
            'soc_kwh': self.current_soc_kwh,
            'soc_percent': self.current_soc_percent,
            'monthly_peak_kw': self.current_monthly_peak_kw,
            'days_remaining': self.days_remaining_in_month,
            'days_elapsed': self.days_elapsed_in_month,
            'power_tariff_rate': self.power_tariff_rate_nok_per_kw
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"BatterySystemState("
            f"SOC={self.current_soc_percent:.1f}%, "
            f"Peak={self.current_monthly_peak_kw:.1f}kW, "
            f"Days_left={self.days_remaining_in_month})"
        )


def calculate_average_power_tariff_rate(tariff_config) -> float:
    """
    Calculate average power tariff rate from bracketed structure.

    Used to estimate penalty coefficient for state manager.

    Args:
        tariff_config: Tariff configuration with power_brackets

    Returns:
        Average rate [NOK/kW/month] across typical demand range
    """
    if not hasattr(tariff_config, 'power_brackets'):
        return 50.0  # Default fallback

    brackets = tariff_config.power_brackets

    # Estimate average rate for typical commercial demand (20-80 kW range)
    # Take weighted average across middle brackets
    total_cost = 0
    total_power = 0

    for (from_kw, to_kw, cost) in brackets:
        if from_kw >= 80:  # Beyond typical range
            break

        if to_kw == float('inf'):
            to_kw = 100  # Cap for calculation

        # Weight by bracket width
        width = min(to_kw, 80) - max(from_kw, 20)
        if width > 0:
            total_cost += cost * width
            total_power += width

    if total_power == 0:
        return 50.0  # Fallback

    avg_rate = total_cost / total_power
    return avg_rate
