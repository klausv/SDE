"""
Configuration module for battery optimization simulations.

Provides dataclass-based configuration management with YAML support.

Main Components:
    - SimulationConfig: Primary configuration dataclass

Usage:
    >>> from src.config import SimulationConfig
    >>>
    >>> # Load from YAML
    >>> config = SimulationConfig.from_yaml("configs/rolling_horizon.yaml")
    >>>
    >>> # Access configuration
    >>> print(config.battery.capacity_kwh)
    >>> print(config.economic.discount_rate)
"""

from .simulation_config import SimulationConfig

__all__ = [
    "SimulationConfig",
]
