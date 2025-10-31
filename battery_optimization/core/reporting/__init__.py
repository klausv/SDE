"""
Reporting subsystem for battery optimization analysis.

This module provides structured result handling, report generation,
and visualization capabilities for battery optimization scenarios.
"""

from .result_models import SimulationResult, ComparisonResult
from .report_generator import ReportGenerator

__all__ = [
    'SimulationResult',
    'ComparisonResult',
    'ReportGenerator',
]
