"""
Plotly-specific report generator base class.

Extends ReportGenerator with Plotly utilities for creating interactive HTML
reports following Norsk Solkraft theme standards and accessibility guidelines.

**Usage:**
    from core.reporting import PlotlyReportGenerator
    from plotly.subplots import make_subplots
    import plotly.graph_objects as go

    class MyPlotlyReport(PlotlyReportGenerator):
        def generate(self) -> Path:
            fig = make_subplots(rows=2, cols=1)
            # ... add traces ...

            # Apply theme (automatic)
            self.apply_theme(fig)

            # Save with standard config
            return self.save_plotly_figure(
                fig,
                filename='my_report.html',
                title='My Report'
            )

**Author**: Battery Optimization Team
**Created**: 2025-01-11
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import logging

from .report_generator import ReportGenerator
from .result_models import SimulationResult
from src.visualization.norsk_solkraft_theme import apply_light_theme

logger = logging.getLogger(__name__)


class PlotlyReportGenerator(ReportGenerator):
    """
    Base class for Plotly-based interactive HTML reports.

    Provides utilities for:
    - Consistent Norsk Solkraft theme application
    - Standard hover tooltip formatting
    - HTML and PNG export with optimal settings
    - Accessibility compliance validation
    - Panel numbering and layout helpers

    Attributes:
        results: List of SimulationResult instances
        output_dir: Root directory for outputs
        plotly_config: Standard Plotly export configuration
        color_palette: Norsk Solkraft brand colors
    """

    # Norsk Solkraft Color Palette
    COLORS = {
        'blå': '#00609F',         # Primary - brand, comparison baseline
        'oransje': '#F5A621',     # Accent - energy costs, key metrics
        'grønn': '#4CAF50',       # Success - savings, positive results
        'rød': '#E53935',         # Warning - high costs, risks
        'grå': '#757575',         # Neutral - reference scenarios
        'lys_grå': '#F5F5F5',     # Backgrounds
        'mørk_grå': '#424242',    # Secondary text
        'karbonsvart': '#212121'  # Primary text
    }

    # Standard Plotly configuration for exports
    PLOTLY_CONFIG = {
        'displayModeBar': True,
        'displaylogo': False,
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'battery_report',
            'height': 1080,
            'width': 1920,
            'scale': 2
        },
        'modeBarButtonsToRemove': [
            'lasso2d',
            'select2d'
        ]
    }

    def __init__(
        self,
        results: List[SimulationResult],
        output_dir: Path,
        theme: str = 'light'
    ):
        """
        Initialize Plotly report generator.

        Args:
            results: One or more SimulationResult instances to analyze
            output_dir: Base directory for outputs (e.g., Path('results'))
            theme: Theme variant ('light' or 'dark', default: 'light')
        """
        super().__init__(results, output_dir)
        self.theme = theme
        self.plotly_figures: List[Path] = []  # Track generated HTML files

    def apply_theme(
        self,
        fig: go.Figure,
        title: Optional[str] = None,
        height: Optional[int] = None,
        hovermode: str = 'x unified'
    ) -> go.Figure:
        """
        Apply Norsk Solkraft theme to Plotly figure.

        Args:
            fig: Plotly figure to style
            title: Optional report title
            height: Optional figure height in pixels
            hovermode: Hover behavior ('x unified', 'closest', etc.)

        Returns:
            Styled figure (modified in-place)

        Example:
            >>> fig = go.Figure()
            >>> fig.add_scatter(x=[1,2,3], y=[4,5,6])
            >>> self.apply_theme(fig, title='Battery SOC', height=600)
        """
        # Apply Norsk Solkraft light theme
        apply_light_theme(fig)

        # Update layout with additional settings
        layout_updates = {
            'hovermode': hovermode,
            'hoverlabel': dict(
                bgcolor='white',
                font_size=12,
                font_family='Arial, sans-serif'
            )
        }

        if title:
            layout_updates['title'] = title

        if height:
            layout_updates['height'] = height

        fig.update_layout(**layout_updates)

        return fig

    def save_plotly_figure(
        self,
        fig: go.Figure,
        filename: str,
        subdir: str = '',
        title: Optional[str] = None,
        export_png: bool = False
    ) -> Path:
        """
        Save Plotly figure as HTML (and optionally PNG).

        Automatically applies theme if not already applied.

        Args:
            fig: Plotly figure to save
            filename: Output filename (should end in .html)
            subdir: Optional subdirectory within reports/ (e.g., 'battery_operation')
            title: Optional figure title (applied if not set)
            export_png: If True, also export PNG via kaleido (requires kaleido package)

        Returns:
            Path to saved HTML file

        Example:
            >>> fig = make_subplots(rows=2, cols=1)
            >>> # ... add traces ...
            >>> path = self.save_plotly_figure(
            ...     fig,
            ...     filename='battery_report.html',
            ...     title='Battery Operation Analysis',
            ...     export_png=True
            ... )
        """
        # Ensure filename ends with .html
        if not filename.endswith('.html'):
            filename = filename.replace('.png', '.html').replace('.pdf', '.html')
            if not filename.endswith('.html'):
                filename += '.html'

        # Create subdirectory if specified
        if subdir:
            report_dir = self.output_dir / 'reports' / subdir
        else:
            report_dir = self.output_dir / 'reports'

        report_dir.mkdir(parents=True, exist_ok=True)

        # Apply theme if title provided (assumes theme not yet applied)
        if title:
            self.apply_theme(fig, title=title)

        # Save HTML
        html_path = report_dir / filename
        fig.write_html(
            html_path,
            include_plotlyjs='cdn',  # Lightweight, browser-cached
            config=self.PLOTLY_CONFIG
        )

        # Track for index generation
        self.plotly_figures.append(html_path)

        logger.info(f"Saved Plotly HTML: {html_path}")

        # Optional PNG export
        if export_png:
            png_path = html_path.with_suffix('.png')
            try:
                fig.write_image(
                    png_path,
                    width=1920,
                    height=1080,
                    scale=2
                )
                logger.info(f"Saved PNG: {png_path}")
            except Exception as e:
                logger.warning(
                    f"PNG export failed: {e}. "
                    "Install kaleido for PNG support: pip install kaleido"
                )

        return html_path

    def create_hover_template(
        self,
        variable_name: str,
        value_format: str = '.1f',
        unit: str = '',
        include_timestamp: bool = True,
        extra_fields: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create standardized hover tooltip template.

        Args:
            variable_name: Name of variable (e.g., 'Battery SOC')
            value_format: Python format string for value (default: '.1f' for 1 decimal)
            unit: Unit suffix (e.g., 'kWh', 'kW', 'kr', '%')
            include_timestamp: If True, add 'Time: %{x}' line
            extra_fields: Optional dict of {label: format_string} for additional fields

        Returns:
            Formatted hovertemplate string

        Example:
            >>> template = self.create_hover_template(
            ...     'Battery SOC',
            ...     value_format='.1f',
            ...     unit='kWh',
            ...     include_timestamp=True,
            ...     extra_fields={'C-Rate': '.2f'}
            ... )
            >>> # Returns: '<b>Battery SOC</b>: %{y:.1f} kWh<br>Time: %{x}<br>C-Rate: %{customdata:.2f}<extra></extra>'
        """
        template_parts = [f"<b>{variable_name}</b>: %{{y:{value_format}}}"]

        if unit:
            template_parts[0] += f" {unit}"

        if include_timestamp:
            template_parts.append("Time: %{x}")

        if extra_fields:
            for label, fmt in extra_fields.items():
                template_parts.append(f"{label}: %{{customdata:{fmt}}}")

        template = "<br>".join(template_parts)
        template += "<extra></extra>"  # Remove trace name redundancy

        return template

    def create_panel_grid(
        self,
        rows: int,
        cols: int = 2,
        subplot_titles: Optional[List[str]] = None,
        vertical_spacing: float = 0.08,
        horizontal_spacing: float = 0.12,
        row_heights: Optional[List[float]] = None,
        specs: Optional[List[List[Dict]]] = None
    ) -> go.Figure:
        """
        Create standard panel grid layout.

        Args:
            rows: Number of rows
            cols: Number of columns (default: 2 for 6×2 grid)
            subplot_titles: List of panel titles (length = rows × cols)
            vertical_spacing: Vertical gap between panels (0-1 scale)
            horizontal_spacing: Horizontal gap between panels (0-1 scale)
            row_heights: Optional list of relative row heights
            specs: Optional subplot specifications (for merged cells, etc.)

        Returns:
            Figure with subplot grid

        Example:
            >>> fig = self.create_panel_grid(
            ...     rows=6,
            ...     cols=2,
            ...     subplot_titles=[
            ...         'SOC', 'Curtailment',
            ...         'Battery Power', 'Grid Power',
            ...         # ... 8 more titles
            ...     ]
            ... )
        """
        fig = make_subplots(
            rows=rows,
            cols=cols,
            subplot_titles=subplot_titles,
            vertical_spacing=vertical_spacing,
            horizontal_spacing=horizontal_spacing,
            row_heights=row_heights,
            specs=specs
        )

        return fig

    def add_range_selector(
        self,
        fig: go.Figure,
        buttons: Optional[List[Dict]] = None
    ):
        """
        Add time range selector to figure.

        Args:
            fig: Plotly figure to modify
            buttons: Optional custom button configurations

        Example:
            >>> self.add_range_selector(fig)
            >>> # Adds buttons: 1w, 2w, all
        """
        if buttons is None:
            buttons = [
                dict(count=7, label="1w", step="day", stepmode="backward"),
                dict(count=14, label="2w", step="day", stepmode="backward"),
                dict(step="all", label="All")
            ]

        fig.update_xaxes(
            rangeselector=dict(
                buttons=buttons,
                bgcolor=self.COLORS['lys_grå'],
                activecolor=self.COLORS['oransje'],
                font=dict(color=self.COLORS['karbonsvart'])
            )
        )

    def add_annotations(
        self,
        fig: go.Figure,
        annotations: List[Dict[str, Any]],
        font_size: int = 10,
        font_color: str = '#212121'
    ):
        """
        Add text annotations to figure.

        Args:
            fig: Plotly figure to annotate
            annotations: List of annotation dicts with keys: x, y, text, (optional) xref, yref
            font_size: Annotation font size
            font_color: Annotation font color

        Example:
            >>> self.add_annotations(
            ...     fig,
            ...     annotations=[
            ...         {'x': 50, 'y': 80, 'text': 'Optimal Point'},
            ...         {'x': 30, 'y': 60, 'text': 'Grid Best'}
            ...     ]
            ... )
        """
        for annot in annotations:
            fig.add_annotation(
                x=annot['x'],
                y=annot['y'],
                text=annot['text'],
                xref=annot.get('xref', 'x'),
                yref=annot.get('yref', 'y'),
                showarrow=annot.get('showarrow', True),
                arrowhead=annot.get('arrowhead', 2),
                arrowsize=annot.get('arrowsize', 1),
                arrowwidth=annot.get('arrowwidth', 2),
                arrowcolor=annot.get('arrowcolor', self.COLORS['karbonsvart']),
                font=dict(
                    size=font_size,
                    color=font_color
                ),
                bgcolor=annot.get('bgcolor', 'white'),
                bordercolor=annot.get('bordercolor', self.COLORS['grå']),
                borderwidth=annot.get('borderwidth', 1)
            )

    def validate_accessibility(
        self,
        fig: go.Figure,
        check_contrast: bool = True,
        check_colorblind: bool = True
    ) -> Dict[str, Any]:
        """
        Validate figure accessibility compliance.

        Args:
            fig: Plotly figure to validate
            check_contrast: Validate WCAG contrast ratios
            check_colorblind: Check for colorblind-safe palettes

        Returns:
            Dict with validation results and warnings

        Example:
            >>> validation = self.validate_accessibility(fig)
            >>> if validation['warnings']:
            ...     logger.warning(f"Accessibility issues: {validation['warnings']}")
        """
        validation = {
            'wcag_aa_compliant': True,
            'wcag_aaa_compliant': True,
            'colorblind_safe': True,
            'warnings': [],
            'recommendations': []
        }

        # Check for red-green colorscales (problematic for deuteranopia)
        if check_colorblind:
            for trace in fig.data:
                if hasattr(trace, 'colorscale'):
                    colorscale_name = str(trace.colorscale)
                    if 'RdYlGn' in colorscale_name:
                        validation['colorblind_safe'] = False
                        validation['warnings'].append(
                            f"Trace uses RdYlGn colorscale (not colorblind-safe)"
                        )
                        validation['recommendations'].append(
                            "Replace RdYlGn with RdYlBu or PuOr for deuteranopia compatibility"
                        )

        # Check text contrast (simplified check - assumes light background)
        if check_contrast:
            layout = fig.layout
            bg_color = getattr(layout, 'paper_bgcolor', '#F5F5F5')

            # Simplified contrast check (full check requires color luminance calculation)
            if bg_color in ['#FFFFFF', '#F5F5F5']:  # Light backgrounds
                font_color = getattr(layout.font, 'color', '#212121')
                if font_color not in ['#000000', '#212121', '#424242']:
                    validation['warnings'].append(
                        f"Font color {font_color} may not meet WCAG AA contrast on light background"
                    )
                    validation['recommendations'].append(
                        "Use #212121 (karbonsvart) for optimal contrast"
                    )

        return validation

    def create_plotly_index(
        self,
        title: str = "Battery Optimization Interactive Reports",
        include_thumbnails: bool = False
    ) -> Path:
        """
        Generate HTML index file linking all Plotly reports.

        Args:
            title: Index page title
            include_thumbnails: If True, embed report thumbnails (requires screenshots)

        Returns:
            Path to generated index.html file

        Example:
            >>> index_path = self.create_plotly_index(
            ...     title='Battery Analysis Dashboard',
            ...     include_thumbnails=False
            ... )
        """
        timestamp_str = self.report_timestamp.strftime('%Y-%m-%d_%H%M%S')
        index_path = self.output_dir / 'reports' / f"{timestamp_str}_index.html"

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: {self.COLORS['lys_grå']};
            color: {self.COLORS['karbonsvart']};
            margin: 0;
            padding: 20px;
        }}
        .header {{
            background-color: {self.COLORS['blå']};
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .report-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        .report-card {{
            background-color: white;
            border: 1px solid {self.COLORS['grå']};
            border-radius: 8px;
            padding: 20px;
            transition: box-shadow 0.3s;
        }}
        .report-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .report-link {{
            color: {self.COLORS['blå']};
            text-decoration: none;
            font-weight: bold;
            font-size: 18px;
        }}
        .report-link:hover {{
            color: {self.COLORS['oransje']};
        }}
        .report-meta {{
            color: {self.COLORS['grå']};
            font-size: 14px;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p><strong>Generated:</strong> {self.report_timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Total Reports:</strong> {len(self.plotly_figures)}</p>
    </div>

    <div class="report-grid">
"""

        # Add report cards
        for fig_path in self.plotly_figures:
            rel_path = fig_path.relative_to(self.output_dir / 'reports')
            report_name = fig_path.stem.replace('_', ' ').title()
            file_size_mb = fig_path.stat().st_size / (1024 * 1024)

            html_content += f"""
        <div class="report-card">
            <a href="{rel_path}" class="report-link">{report_name}</a>
            <div class="report-meta">
                <p>File: {rel_path}</p>
                <p>Size: {file_size_mb:.1f} MB</p>
            </div>
        </div>
"""

        html_content += """
    </div>
</body>
</html>
"""

        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"Created Plotly index: {index_path}")
        return index_path

    def get_color_palette(self, n_colors: int = 4, palette_type: str = 'standard') -> List[str]:
        """
        Get color palette for visualizations.

        Args:
            n_colors: Number of colors needed (max 8)
            palette_type: 'standard', 'diverging', 'sequential'

        Returns:
            List of hex color codes

        Example:
            >>> colors = self.get_color_palette(4, palette_type='standard')
            >>> # Returns: ['#00609F', '#F5A621', '#4CAF50', '#E53935']
        """
        if palette_type == 'standard':
            palette = [
                self.COLORS['blå'],
                self.COLORS['oransje'],
                self.COLORS['grønn'],
                self.COLORS['rød'],
                self.COLORS['grå'],
                self.COLORS['mørk_grå'],
                '#9C27B0',  # Purple
                '#FF9800'   # Deep Orange
            ]
        elif palette_type == 'diverging':
            palette = [
                '#E53935',  # Red
                '#FF9800',  # Orange
                '#FFEB3B',  # Yellow
                '#4CAF50',  # Green
                '#00609F'   # Blue
            ]
        elif palette_type == 'sequential':
            palette = [
                '#F5F5F5',  # Very light
                '#B0BEC5',  # Light
                '#78909C',  # Medium
                '#546E7A',  # Medium-dark
                '#37474F',  # Dark
                '#212121'   # Very dark
            ]
        else:
            raise ValueError(f"Unknown palette_type: {palette_type}")

        return palette[:min(n_colors, len(palette))]
