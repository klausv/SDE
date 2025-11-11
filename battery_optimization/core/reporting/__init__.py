"""
Reporting subsystem for battery optimization analysis.

This module provides structured result handling, report generation,
and visualization capabilities for battery optimization scenarios.
"""

from .result_models import SimulationResult, ComparisonResult
from .report_generator import ReportGenerator
from .plotly_report_generator import PlotlyReportGenerator
from .matplotlib_report_generator import MatplotlibReportGenerator
from .factory import ReportFactory
from .battery_operation_report import BatteryOperationReport

__all__ = [
    'SimulationResult',
    'ComparisonResult',
    'ReportGenerator',
    'PlotlyReportGenerator',
    'MatplotlibReportGenerator',
    'ReportFactory',
    'BatteryOperationReport',
]
