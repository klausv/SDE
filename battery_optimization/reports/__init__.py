"""
Battery optimization report implementations.

This module contains concrete report generators for various analyses:
- Break-even cost analysis
- Solar duration curve analysis
- Strategy diagnostics
- Scenario comparisons
- Executive summaries
"""

from .breakeven_analysis import BreakevenReport
from .solar_duration import SolarDurationCurveReport

# Report registry for factory pattern
AVAILABLE_REPORTS = {
    'breakeven': BreakevenReport,
    'solar_duration': SolarDurationCurveReport,
    # Future additions:
    # 'diagnostics': StrategyDiagnosticReport,
    # 'comparison': ScenarioComparisonReport,
    # 'executive': ExecutiveSummaryReport,
}


def generate_report(report_type: str, **kwargs):
    """
    Factory function for report generation.

    Args:
        report_type: Type of report to generate ('breakeven', 'diagnostics', etc.)
        **kwargs: Arguments to pass to the specific report class

    Returns:
        Path to generated main report file

    Raises:
        ValueError: If report_type is not recognized

    Example:
        >>> from pathlib import Path
        >>> from core.reporting import SimulationResult
        >>> ref = SimulationResult.load(Path('results/simulations/2024-10-30_reference'))
        >>> battery = SimulationResult.load(Path('results/simulations/2024-10-30_battery'))
        >>> report_path = generate_report(
        ...     'breakeven',
        ...     reference=ref,
        ...     battery_scenario=battery,
        ...     output_dir=Path('results')
        ... )
    """
    if report_type not in AVAILABLE_REPORTS:
        raise ValueError(
            f"Unknown report type: '{report_type}'. "
            f"Available: {list(AVAILABLE_REPORTS.keys())}"
        )

    report_class = AVAILABLE_REPORTS[report_type]
    report_instance = report_class(**kwargs)
    return report_instance.generate()


def list_available_reports():
    """
    List all available report types with descriptions.

    Returns:
        Dict mapping report type to its class and docstring
    """
    return {
        name: {
            'class': cls.__name__,
            'description': cls.__doc__.strip().split('\n')[0] if cls.__doc__ else 'No description'
        }
        for name, cls in AVAILABLE_REPORTS.items()
    }


__all__ = [
    'BreakevenReport',
    'SolarDurationCurveReport',
    'generate_report',
    'list_available_reports',
    'AVAILABLE_REPORTS',
]
