"""
Backward compatibility wrapper for operational module.

This module provides imports from src.operational for scripts
that use the direct 'operational' import path.
"""

from src.operational.state_manager import (
    BatterySystemState,
    calculate_average_power_tariff_rate,
)

__all__ = [
    'BatterySystemState',
    'calculate_average_power_tariff_rate',
]
