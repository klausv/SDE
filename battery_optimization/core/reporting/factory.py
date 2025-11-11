"""
Report factory for dynamic report instantiation and discovery.

This module implements the Factory pattern for report generation,
allowing dynamic registration and instantiation of report types.
"""

from pathlib import Path
from typing import Dict, Type, List, Any
from .report_generator import ReportGenerator


class ReportFactory:
    """
    Factory for creating report instances dynamically.

    Reports self-register using the @ReportFactory.register() decorator,
    enabling CLI and programmatic discovery of available report types.

    Usage:
        # Register a report
        @ReportFactory.register('battery_operation')
        class BatteryOperationReport(PlotlyReportGenerator):
            ...

        # Create a report instance
        report = ReportFactory.create(
            'battery_operation',
            result=simulation_result,
            output_dir=Path('results')
        )
    """

    _registry: Dict[str, Type[ReportGenerator]] = {}

    @classmethod
    def register(cls, name: str):
        """
        Decorator for registering report classes.

        Args:
            name: Unique identifier for the report type

        Returns:
            Decorator function

        Example:
            @ReportFactory.register('battery_operation')
            class BatteryOperationReport(PlotlyReportGenerator):
                ...
        """
        def decorator(report_class: Type[ReportGenerator]):
            if name in cls._registry:
                raise ValueError(
                    f"Report '{name}' already registered with "
                    f"{cls._registry[name].__name__}"
                )

            cls._registry[name] = report_class
            return report_class

        return decorator

    @classmethod
    def create(cls, name: str, **kwargs) -> ReportGenerator:
        """
        Create a report instance by name.

        Args:
            name: Registered report type identifier
            **kwargs: Arguments passed to report constructor

        Returns:
            Instantiated report object

        Raises:
            ValueError: If report name is not registered

        Example:
            report = ReportFactory.create(
                'battery_operation',
                result=simulation_result,
                output_dir=Path('results'),
                period='week'
            )
        """
        if name not in cls._registry:
            available = ', '.join(cls._registry.keys())
            raise ValueError(
                f"Unknown report type '{name}'. "
                f"Available: {available}"
            )

        report_class = cls._registry[name]
        return report_class(**kwargs)

    @classmethod
    def list_reports(cls) -> List[str]:
        """
        Get list of all registered report types.

        Returns:
            List of report names

        Example:
            >>> ReportFactory.list_reports()
            ['battery_operation', 'yearly_comprehensive', 'break_even']
        """
        return sorted(cls._registry.keys())

    @classmethod
    def get_report_class(cls, name: str) -> Type[ReportGenerator]:
        """
        Get report class by name without instantiating.

        Args:
            name: Registered report type identifier

        Returns:
            Report class type

        Raises:
            ValueError: If report name is not registered

        Example:
            ReportClass = ReportFactory.get_report_class('battery_operation')
            help(ReportClass)
        """
        if name not in cls._registry:
            available = ', '.join(cls._registry.keys())
            raise ValueError(
                f"Unknown report type '{name}'. "
                f"Available: {available}"
            )

        return cls._registry[name]

    @classmethod
    def get_report_info(cls, name: str) -> Dict[str, Any]:
        """
        Get metadata about a registered report.

        Args:
            name: Registered report type identifier

        Returns:
            Dictionary with report metadata (class, docstring, module)

        Example:
            info = ReportFactory.get_report_info('battery_operation')
            print(info['docstring'])
        """
        report_class = cls.get_report_class(name)

        return {
            'name': name,
            'class': report_class.__name__,
            'module': report_class.__module__,
            'docstring': report_class.__doc__,
            'base_classes': [base.__name__ for base in report_class.__bases__]
        }

    @classmethod
    def clear_registry(cls):
        """
        Clear all registered reports.

        Primarily used for testing purposes.
        """
        cls._registry.clear()
