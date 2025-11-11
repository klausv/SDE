"""
Backward compatibility wrapper for legacy config classes.

This module provides imports from the archived legacy config for scripts
that haven't been migrated to the new src.config.simulation_config structure.
"""

from archive.legacy_entry_points.config_legacy import (
    BatteryOptimizationConfig,
    DegradationConfig,
)

__all__ = [
    'BatteryOptimizationConfig',
    'DegradationConfig',
]
