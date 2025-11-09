"""
Operational optimization components for real-time battery control.

This package provides the infrastructure for running rolling horizon optimization
in operational mode, including state tracking and control interfaces.
"""

from .state_manager import BatterySystemState

__all__ = ['BatterySystemState']
