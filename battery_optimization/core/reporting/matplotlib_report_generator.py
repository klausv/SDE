"""
⚠️ DEPRECATED: Matplotlib-based report generation.

This module provides matplotlib-specific report generation utilities.
New reports should use PlotlyReportGenerator instead for interactive HTML output.

Status: Deprecated as of 2025-01-11
Replacement: core/reporting/plotly_report_generator.py
Removal Timeline: To be removed in v2.0
"""

from pathlib import Path
from typing import List
import matplotlib.pyplot as plt
import matplotlib

from .report_generator import ReportGenerator
from .result_models import SimulationResult

# Use non-interactive backend for headless environments
matplotlib.use('Agg')


class MatplotlibReportGenerator(ReportGenerator):
    """
    Base class for matplotlib-based static visualization reports.

    ⚠️ DEPRECATED: Use PlotlyReportGenerator for new reports.

    This class provides utilities for generating static PNG/PDF visualizations
    using matplotlib. For modern interactive HTML reports with better UX,
    use PlotlyReportGenerator instead.

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
        style: str = 'seaborn-v0_8-darkgrid'
    ):
        """
        Initialize matplotlib report generator.

        Args:
            results: One or more SimulationResult instances to analyze
            output_dir: Base directory for outputs (e.g., Path('results'))
            style: Matplotlib style name (default: 'seaborn-v0_8-darkgrid')
        """
        super().__init__(results, output_dir)
        self.style = style
        self._apply_plot_style()

        # Warn about deprecation
        print("⚠️  MatplotlibReportGenerator is deprecated. "
              "Consider using PlotlyReportGenerator for interactive reports.")

    def _apply_plot_style(self):
        """Apply matplotlib style configuration."""
        plt.style.use(self.style)

        # Standard parameters
        plt.rcParams.update({
            'figure.figsize': (10, 6),
            'font.size': 10,
            'axes.titlesize': 12,
            'axes.labelsize': 11,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'legend.fontsize': 9,
            'lines.linewidth': 2,
            'grid.alpha': 0.3
        })

    def save_figure(
        self,
        fig: plt.Figure,
        filename: str,
        subdir: str = '',
        dpi: int = 150,
        bbox_inches: str = 'tight'
    ) -> Path:
        """
        Save matplotlib figure with consistent path structure.

        Args:
            fig: Matplotlib figure to save
            filename: Output filename (with extension, e.g., 'plot.png')
            subdir: Optional subdirectory within figures/ (e.g., 'breakeven')
            dpi: Resolution for raster formats
            bbox_inches: Bounding box adjustment ('tight' removes whitespace)

        Returns:
            Path to saved figure file
        """
        # Create figure subdirectory if specified
        if subdir:
            fig_dir = self.output_dir / 'figures' / subdir
        else:
            fig_dir = self.output_dir / 'figures'

        fig_dir.mkdir(parents=True, exist_ok=True)

        # Save figure
        filepath = fig_dir / filename
        fig.savefig(filepath, dpi=dpi, bbox_inches=bbox_inches)
        plt.close(fig)

        # Track for index generation
        self.figures.append(filepath)

        return filepath

    def create_subplots(
        self,
        nrows: int = 1,
        ncols: int = 1,
        figsize: tuple = None,
        **kwargs
    ) -> tuple:
        """
        Create matplotlib subplots with consistent styling.

        Args:
            nrows: Number of rows
            ncols: Number of columns
            figsize: Figure size (width, height), defaults to rcParams
            **kwargs: Additional arguments passed to plt.subplots()

        Returns:
            Tuple of (figure, axes)
        """
        if figsize is None:
            # Auto-size based on number of subplots
            figsize = (10 * ncols, 6 * nrows)

        return plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize, **kwargs)
