"""
Base class for report generation with shared utilities.

This module provides an abstract base class that all report generators
inherit from, ensuring consistent structure and reusable utilities.

Note: Matplotlib dependencies have been moved to MatplotlibReportGenerator.
      For new reports, use PlotlyReportGenerator instead.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from .result_models import SimulationResult


class ReportGenerator(ABC):
    """
    Abstract base class for battery optimization report generators.

    All concrete report classes should inherit from this base and implement
    the `generate()` method to produce their specific analysis outputs.

    Attributes:
        results: List of SimulationResult instances for analysis
        output_dir: Root directory for all generated outputs
        figures: List of paths to generated figure files
        report_timestamp: Timestamp when report generation started
    """

    def __init__(
        self,
        results: List[SimulationResult],
        output_dir: Path,
        theme: str = 'light'
    ):
        """
        Initialize report generator.

        Args:
            results: One or more SimulationResult instances to analyze
            output_dir: Base directory for outputs (e.g., Path('results'))
            theme: Visual theme for reports ('light' or 'dark')
        """
        if not isinstance(results, list):
            results = [results]

        self.results = results
        self.output_dir = Path(output_dir)
        self.theme = theme
        self.figures: List[Path] = []
        self.report_timestamp = datetime.now()

        # Ensure output directories exist
        self._create_output_structure()

    def _create_output_structure(self):
        """Create standard output directory structure."""
        (self.output_dir / 'simulations').mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'figures').mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'reports').mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def generate(self) -> Path:
        """
        Generate the report.

        Must be implemented by subclasses to produce their specific analysis.

        Returns:
            Path to the main report file (e.g., markdown report)
        """
        pass


    def create_index(
        self,
        title: str = "Battery Optimization Report",
        additional_sections: Optional[Dict[str, str]] = None
    ) -> Path:
        """
        Generate markdown index file linking all report outputs.

        Args:
            title: Report title for index page
            additional_sections: Optional dict of {section_name: markdown_content}

        Returns:
            Path to generated index.md file
        """
        timestamp_str = self.report_timestamp.strftime('%Y-%m-%d_%H%M%S')
        index_path = self.output_dir / 'reports' / f"{timestamp_str}_index.md"

        with open(index_path, 'w') as f:
            # Header
            f.write(f"# {title}\n\n")
            f.write(f"**Generated:** {self.report_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Scenarios
            f.write("## Analyzed Scenarios\n\n")
            for result in self.results:
                f.write(f"- **{result.scenario_name}**\n")
                f.write(f"  - Battery: {result.battery_config.get('capacity_kwh', 'N/A')} kWh, "
                       f"{result.battery_config.get('power_kw', 'N/A')} kW\n")
                f.write(f"  - Strategy: {result.strategy_config.get('type', 'N/A')}\n")
                f.write(f"  - Total Cost: {result.cost_summary.get('total_cost_nok', 'N/A'):.0f} NOK/year\n")

            # Additional sections
            if additional_sections:
                for section_name, content in additional_sections.items():
                    f.write(f"\n## {section_name}\n\n")
                    f.write(content)
                    f.write("\n")

            # Figures
            if self.figures:
                f.write("\n## Generated Visualizations\n\n")
                for fig_path in self.figures:
                    rel_path = fig_path.relative_to(self.output_dir)
                    fig_name = fig_path.stem.replace('_', ' ').title()
                    f.write(f"### {fig_name}\n\n")
                    f.write(f"![{fig_name}](../{rel_path})\n\n")

        return index_path

    def get_timestamped_filename(self, base_name: str, extension: str = 'md') -> str:
        """
        Generate timestamped filename for reports.

        Args:
            base_name: Base filename without extension (e.g., 'breakeven_analysis')
            extension: File extension without dot (default: 'md')

        Returns:
            Filename string like '2024-10-30_120530_breakeven_analysis.md'
        """
        timestamp_str = self.report_timestamp.strftime('%Y-%m-%d_%H%M%S')
        return f"{timestamp_str}_{base_name}.{extension}"

    def write_markdown_header(
        self,
        filepath: Path,
        title: str,
        summary_points: Optional[List[str]] = None
    ):
        """
        Write standard markdown header for reports.

        Args:
            filepath: Path to markdown file
            title: Report title
            summary_points: Optional list of bullet points for executive summary
        """
        with open(filepath, 'w') as f:
            f.write(f"# {title}\n\n")
            f.write(f"**Generated:** {self.report_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            if summary_points:
                f.write("## Executive Summary\n\n")
                for point in summary_points:
                    f.write(f"- {point}\n")
                f.write("\n")


    def format_currency(self, value: float, currency: str = 'NOK') -> str:
        """Format currency values consistently."""
        return f"{value:,.0f} {currency}"

    def format_percentage(self, value: float, decimals: int = 1) -> str:
        """Format percentage values consistently."""
        return f"{value:.{decimals}f}%"

    def format_energy(self, value: float, unit: str = 'kWh') -> str:
        """Format energy values consistently."""
        if value >= 1000:
            return f"{value/1000:.1f} MWh"
        return f"{value:.1f} {unit}"

    def create_summary_table(
        self,
        data: Dict[str, Any],
        filepath: Path,
        title: str = "Summary Statistics"
    ):
        """
        Create and save a summary table as both CSV and markdown.

        Args:
            data: Dictionary with summary data
            filepath: Path for output files (without extension)
            title: Table title for markdown
        """
        import pandas as pd

        df = pd.DataFrame([data]).T
        df.columns = ['Value']

        # Save as CSV
        csv_path = filepath.with_suffix('.csv')
        df.to_csv(csv_path)

        # Save as markdown
        md_path = filepath.with_suffix('.md')
        with open(md_path, 'w') as f:
            f.write(f"# {title}\n\n")
            f.write(df.to_markdown())
            f.write("\n")

        return csv_path, md_path


class SingleScenarioReport(ReportGenerator):
    """
    Base class for reports analyzing a single scenario.

    Convenience class for reports that focus on one SimulationResult.
    """

    def __init__(
        self,
        result: SimulationResult,
        output_dir: Path,
        theme: str = 'light'
    ):
        """
        Initialize single-scenario report.

        Args:
            result: Single SimulationResult to analyze
            output_dir: Base directory for outputs
            theme: Visual theme for reports ('light' or 'dark')
        """
        super().__init__([result], output_dir, theme=theme)
        self.result = result


class ComparisonReport(ReportGenerator):
    """
    Base class for reports comparing multiple scenarios.

    Convenience class for reports that compare SimulationResults,
    typically requiring a reference scenario for baseline comparison.
    """

    def __init__(
        self,
        results: List[SimulationResult],
        reference_scenario: str,
        output_dir: Path,
        theme: str = 'light'
    ):
        """
        Initialize comparison report.

        Args:
            results: List of SimulationResults to compare
            reference_scenario: Name of baseline scenario
            output_dir: Base directory for outputs
            theme: Visual theme for reports ('light' or 'dark')
        """
        super().__init__(results, output_dir, theme=theme)
        self.reference_scenario = reference_scenario

        # Validate reference exists
        scenario_names = [r.scenario_name for r in results]
        if reference_scenario not in scenario_names:
            raise ValueError(
                f"Reference scenario '{reference_scenario}' not found. "
                f"Available: {scenario_names}"
            )

        # Store reference for easy access
        self.reference = next(r for r in results if r.scenario_name == reference_scenario)
