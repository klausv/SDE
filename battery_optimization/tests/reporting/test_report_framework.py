"""
Comprehensive tests for refactored reporting framework.

Tests core functionality of the report generation framework:
- ReportFactory registration and instantiation
- PlotlyReportGenerator inheritance and theme application
- MatplotlibReportGenerator deprecation
- BatteryOperationReport functionality
- Report generator base class utilities
"""

import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.reporting import (
    ReportFactory,
    ReportGenerator,
    PlotlyReportGenerator,
    MatplotlibReportGenerator,
    BatteryOperationReport,
    SimulationResult
)


class TestReportFactory:
    """Test ReportFactory pattern implementation."""

    def test_battery_operation_registered(self):
        """Verify BatteryOperationReport is registered."""
        reports = ReportFactory.list_reports()
        assert 'battery_operation' in reports

    def test_get_report_class(self):
        """Verify factory can retrieve report class."""
        ReportClass = ReportFactory.get_report_class('battery_operation')
        assert ReportClass == BatteryOperationReport

    def test_get_report_info(self):
        """Verify factory provides report metadata."""
        info = ReportFactory.get_report_info('battery_operation')
        assert info['name'] == 'battery_operation'
        assert info['class'] == 'BatteryOperationReport'
        assert 'PlotlyReportGenerator' in info['base_classes']

    def test_invalid_report_name(self):
        """Verify factory raises error for unknown report."""
        with pytest.raises(ValueError, match="Unknown report type"):
            ReportFactory.get_report_class('nonexistent_report')


class TestPlotlyReportGenerator:
    """Test PlotlyReportGenerator base class."""

    def test_inheritance_chain(self):
        """Verify BatteryOperationReport inherits from PlotlyReportGenerator."""
        assert issubclass(BatteryOperationReport, PlotlyReportGenerator)

    def test_colors_defined(self):
        """Verify Norsk Solkraft color palette is defined."""
        assert hasattr(PlotlyReportGenerator, 'COLORS')
        colors = PlotlyReportGenerator.COLORS
        assert 'blå' in colors
        assert 'oransje' in colors
        assert colors['blå'] == '#00609F'

    def test_plotly_config_defined(self):
        """Verify Plotly configuration is defined."""
        assert hasattr(PlotlyReportGenerator, 'PLOTLY_CONFIG')
        config = PlotlyReportGenerator.PLOTLY_CONFIG
        assert 'displayModeBar' in config
        assert 'toImageButtonOptions' in config


class TestBatteryOperationReport:
    """Test BatteryOperationReport refactored functionality."""

    def test_factory_registration(self):
        """Verify report can be instantiated via factory."""
        reports = ReportFactory.list_reports()
        assert 'battery_operation' in reports

    def test_period_configs(self):
        """Verify period configurations are defined."""
        assert hasattr(BatteryOperationReport, 'PERIOD_CONFIGS')
        configs = BatteryOperationReport.PERIOD_CONFIGS
        # Check actual period names from implementation
        assert '3weeks' in configs
        assert '1month' in configs
        assert '3months' in configs
        assert 'custom' in configs

    def test_period_config_structure(self):
        """Verify period configurations have required fields."""
        configs = BatteryOperationReport.PERIOD_CONFIGS
        for period_name, config in configs.items():
            assert 'days' in config or period_name == 'custom'
            assert 'default_start' in config


class TestMatplotlibReportGenerator:
    """Test MatplotlibReportGenerator deprecation."""

    def test_deprecation_warning(self, capsys):
        """Verify deprecation warning is shown on instantiation."""
        # Create a concrete test class since MatplotlibReportGenerator is abstract
        from unittest.mock import Mock

        class TestMatplotlibReport(MatplotlibReportGenerator):
            def generate(self):
                return Path('/tmp/test.png')

        mock_result = Mock()
        report = TestMatplotlibReport(
            results=[mock_result],
            output_dir=Path('/tmp/test')
        )

        # Check for deprecation warning in output
        captured = capsys.readouterr()
        assert 'deprecated' in captured.out.lower()

    def test_has_matplotlib_methods(self):
        """Verify matplotlib-specific methods are present."""
        assert hasattr(MatplotlibReportGenerator, 'save_figure')
        assert hasattr(MatplotlibReportGenerator, '_apply_plot_style')


class TestReportGeneratorBase:
    """Test base ReportGenerator class utilities."""

    def test_theme_parameter(self):
        """Verify theme parameter is accepted."""
        from unittest.mock import Mock

        # Create concrete test class
        class TestReport(ReportGenerator):
            def generate(self):
                return Path('/tmp/test.html')

        mock_result = Mock()

        # Test with different themes
        report_light = TestReport([mock_result], Path('/tmp'), theme='light')
        assert report_light.theme == 'light'

        report_dark = TestReport([mock_result], Path('/tmp'), theme='dark')
        assert report_dark.theme == 'dark'

    def test_output_structure_creation(self):
        """Verify output directories are created."""
        from unittest.mock import Mock
        import tempfile

        class TestReport(ReportGenerator):
            def generate(self):
                return Path('/tmp/test.html')

        mock_result = Mock()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            report = TestReport([mock_result], output_dir)

            assert (output_dir / 'simulations').exists()
            assert (output_dir / 'figures').exists()
            assert (output_dir / 'reports').exists()

    def test_format_utilities(self):
        """Test formatting utility methods."""
        from unittest.mock import Mock

        class TestReport(ReportGenerator):
            def generate(self):
                return Path('/tmp/test.html')

        mock_result = Mock()
        report = TestReport([mock_result], Path('/tmp'))

        # Test currency formatting
        assert report.format_currency(1234.56) == "1,235 NOK"
        assert report.format_currency(1234.56, 'EUR') == "1,235 EUR"

        # Test percentage formatting
        assert report.format_percentage(12.345) == "12.3%"
        assert report.format_percentage(12.345, decimals=2) == "12.35%"

        # Test energy formatting
        assert report.format_energy(500) == "500.0 kWh"
        assert report.format_energy(1500) == "1.5 MWh"


class TestFactoryAdvanced:
    """Advanced factory pattern tests."""

    def test_registration_prevents_duplicates(self):
        """Verify factory prevents duplicate registration."""
        from core.reporting.factory import ReportFactory as Factory

        # Attempt to register duplicate should raise error
        with pytest.raises(ValueError, match="already registered"):
            @Factory.register('battery_operation')
            class DuplicateReport(PlotlyReportGenerator):
                pass

    def test_get_report_info_completeness(self):
        """Verify report info contains all expected fields."""
        info = ReportFactory.get_report_info('battery_operation')

        required_fields = ['name', 'class', 'module', 'docstring', 'base_classes']
        for field in required_fields:
            assert field in info
            assert info[field] is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
