"""
Battery Operation Report Generator - Unified Interactive Plotly Visualization

This module consolidates three existing matplotlib visualization scripts into a
comprehensive, theme-native Plotly report with configurable time periods.

Consolidates:
- plot_battery_simulation.py (3 weeks, June focus, 2-row layout)
- visualize_results.py (3 weeks, configurable start, 4×2 layout)
- visualize_battery_management.py (monthly detail, comprehensive metrics)

Author: Klaus + Claude
Date: November 2025
"""

from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .plotly_report_generator import PlotlyReportGenerator
from .result_models import SimulationResult
from .factory import ReportFactory
from src.visualization.norsk_solkraft_theme import get_brand_colors, get_semantic_colors


@ReportFactory.register('battery_operation')
class BatteryOperationReport(PlotlyReportGenerator):
    """
    Unified battery operation visualization with configurable time periods.

    Creates comprehensive interactive Plotly dashboard showing:
    - Battery state of charge and curtailment
    - Battery power flow (charge/discharge)
    - Grid power flow (import/export)
    - Spot prices and solar production
    - Cost components breakdown
    - Operational metrics summary

    Features:
    - Configurable period (3weeks, 1month, 3months, custom range)
    - Automatic battery dimension detection from metadata
    - Norsk Solkraft themed visualizations
    - Interactive zoom, pan, hover tooltips
    - Multiple export formats (HTML, PNG via kaleido)

    Layout: 2 columns × 6 rows (12 subplots total)

    Attributes:
        period: Time period selection ('3weeks', '1month', '3months', 'custom')
        start_date: Optional custom start date (YYYY-MM-DD format)
        end_date: Optional custom end date (YYYY-MM-DD format)
        export_png: Whether to export static PNG in addition to HTML
        battery_kwh: Battery capacity (auto-detected from metadata if not specified)
        battery_kw: Battery power rating (auto-detected from metadata if not specified)
    """

    PERIOD_CONFIGS = {
        '3weeks': {'days': 21, 'default_start': '2024-06-01'},
        '1month': {'days': 30, 'default_start': '2024-06-01'},
        '3months': {'days': 90, 'default_start': '2024-01-01'},
        'custom': {'days': None, 'default_start': None}
    }

    def __init__(
        self,
        result: SimulationResult,
        output_dir: Path,
        period: str = '3weeks',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        export_png: bool = False,
        battery_kwh: Optional[float] = None,
        battery_kw: Optional[float] = None
    ):
        """
        Initialize battery operation report generator.

        Args:
            result: SimulationResult containing trajectory data
            output_dir: Base directory for outputs (e.g., Path('results'))
            period: Time period selection ('3weeks', '1month', '3months', 'custom')
            start_date: Optional start date override (YYYY-MM-DD format)
            end_date: Optional end date override (YYYY-MM-DD format)
            export_png: Whether to export static PNG (requires kaleido)
            battery_kwh: Battery capacity override (auto-detected if None)
            battery_kw: Battery power rating override (auto-detected if None)

        Raises:
            ValueError: If period is invalid or custom period missing dates
        """
        super().__init__([result], output_dir, theme='light')

        # Maintain backward compatibility: self.result (singular) for this class
        self.result = result

        # Validate period
        if period not in self.PERIOD_CONFIGS:
            raise ValueError(
                f"Invalid period '{period}'. "
                f"Must be one of: {list(self.PERIOD_CONFIGS.keys())}"
            )

        if period == 'custom' and (start_date is None or end_date is None):
            raise ValueError("Custom period requires both start_date and end_date")

        self.period = period
        self.start_date = start_date
        self.end_date = end_date
        self.export_png = export_png

        # Battery dimensions (auto-detect or override)
        self.battery_kwh = battery_kwh or result.battery_config.get('capacity_kwh', 100)
        self.battery_kw = battery_kw or result.battery_config.get('power_kw', 50)

        # Load brand colors for consistent styling
        self.colors = get_brand_colors()
        self.semantic = get_semantic_colors()

        # Prepare trajectory data
        self.df = self._prepare_data()

    def _prepare_data(self) -> pd.DataFrame:
        """
        Prepare trajectory data for visualization.

        Filters to selected time period and adds calculated columns.

        Returns:
            Filtered and enriched DataFrame with trajectory data
        """
        # Convert result to DataFrame
        df = self.result.to_dataframe()

        # Determine time range
        start, end = self._get_time_range(df.index)

        # Filter to period
        df_filtered = df[(df.index >= start) & (df.index < end)].copy()

        if len(df_filtered) == 0:
            raise ValueError(
                f"No data found in period {start.date()} to {end.date()}. "
                f"Available range: {df.index[0].date()} to {df.index[-1].date()}"
            )

        # Add calculated columns
        df_filtered['soc_pct'] = (df_filtered['battery_soc_kwh'] / self.battery_kwh) * 100
        df_filtered['hour'] = df_filtered.index.hour
        df_filtered['weekday'] = df_filtered.index.weekday
        df_filtered['is_peak'] = (
            (df_filtered['weekday'] < 5) &
            (df_filtered['hour'] >= 6) &
            (df_filtered['hour'] < 22)
        )

        return df_filtered

    def _get_time_range(self, full_index: pd.DatetimeIndex) -> Tuple[pd.Timestamp, pd.Timestamp]:
        """
        Determine start and end timestamps for visualization period.

        Args:
            full_index: Complete DatetimeIndex from trajectory data

        Returns:
            Tuple of (start_timestamp, end_timestamp)
        """
        config = self.PERIOD_CONFIGS[self.period]

        if self.period == 'custom':
            start = pd.Timestamp(self.start_date)
            end = pd.Timestamp(self.end_date)
        else:
            # Use provided start_date or default
            if self.start_date:
                start = pd.Timestamp(self.start_date)
            else:
                start = pd.Timestamp(config['default_start'])

            end = start + timedelta(days=config['days'])

        # Validate against available data
        if start < full_index[0]:
            print(f"Warning: Requested start {start.date()} before data start {full_index[0].date()}")
            start = full_index[0]

        if end > full_index[-1]:
            print(f"Warning: Requested end {end.date()} after data end {full_index[-1].date()}")
            end = full_index[-1]

        return start, end

    def _create_figure(self) -> go.Figure:
        """
        Create comprehensive Plotly figure with 6 rows × 2 columns layout.

        Returns:
            Configured Plotly figure with all subplots
        """
        # Define subplot titles
        row_titles = [
            'Battery State of Charge',
            'Curtailed Power',
            'Battery Power Flow',
            'C-Rate Indicator',
            'Grid Power Flow',
            'Tariff Zones',
            'Spot Price',
            'Solar Production',
            'Cost Components',
            'Cumulative Cost',
            'Daily Metrics',
            'Weekly Aggregates'
        ]

        # Create subplots with secondary y-axes where needed
        fig = make_subplots(
            rows=6, cols=2,
            subplot_titles=row_titles,
            specs=[
                [{'secondary_y': False}, {'secondary_y': False}],  # Row 1: SOC + Curtailment
                [{'secondary_y': False}, {'secondary_y': False}],  # Row 2: Battery Power + C-Rate
                [{'secondary_y': False}, {'secondary_y': False}],  # Row 3: Grid + Tariff
                [{'secondary_y': True}, {'secondary_y': False}],   # Row 4: Spot/Solar + Production
                [{'secondary_y': False}, {'secondary_y': False}],  # Row 5: Cost components + Cumulative
                [{'type': 'table'}, {'type': 'table'}]             # Row 6: Tables
            ],
            vertical_spacing=0.05,
            horizontal_spacing=0.08,
            row_heights=[0.16, 0.16, 0.16, 0.16, 0.16, 0.20]
        )

        # Apply Norsk Solkraft light theme (inherited from PlotlyReportGenerator)
        self.apply_theme(fig, height=2400, hovermode='x unified')

        # Populate all subplots
        self._add_soc_subplot(fig, row=1, col=1)
        self._add_curtailment_subplot(fig, row=1, col=2)
        self._add_battery_power_subplot(fig, row=2, col=1)
        self._add_crate_subplot(fig, row=2, col=2)
        self._add_grid_power_subplot(fig, row=3, col=1)
        self._add_tariff_zones_subplot(fig, row=3, col=2)
        self._add_spot_price_subplot(fig, row=4, col=1)
        self._add_solar_production_subplot(fig, row=4, col=2)
        self._add_cost_components_subplot(fig, row=5, col=1)
        self._add_cumulative_cost_subplot(fig, row=5, col=2)
        self._add_daily_metrics_table(fig, row=6, col=1)
        self._add_weekly_aggregates_table(fig, row=6, col=2)

        # Add custom title with battery/period info
        fig.update_layout(
            title={
                'text': (
                    f'Battery Operation Report - {self.battery_kwh} kWh / {self.battery_kw} kW<br>'
                    f'<sub>Period: {self.df.index[0].date()} to {self.df.index[-1].date()} '
                    f'({len(self.df)} timesteps)</sub>'
                ),
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18}
            }
        )

        return fig

    def _add_soc_subplot(self, fig: go.Figure, row: int, col: int):
        """Add Battery State of Charge subplot (Row 1, Col 1)"""
        # SOC area fill
        fig.add_trace(
            go.Scatter(
                x=self.df.index,
                y=self.df['soc_pct'],
                fill='tozeroy',
                fillcolor='rgba(76, 175, 80, 0.3)',  # Green with transparency
                line=dict(color='#4CAF50', width=2),
                name='SOC',
                hovertemplate='%{y:.1f}%<extra></extra>'
            ),
            row=row, col=col
        )

        # Min/Max SOC limits
        soc_min = self.result.battery_config.get('min_soc_pct', 20)
        soc_max = self.result.battery_config.get('max_soc_pct', 80)

        fig.add_hline(
            y=soc_min, line_dash='dash', line_color='#C62828',
            annotation_text=f'Min SOC ({soc_min}%)',
            row=row, col=col
        )
        fig.add_hline(
            y=soc_max, line_dash='dash', line_color='#00897B',
            annotation_text=f'Max SOC ({soc_max}%)',
            row=row, col=col
        )

        # Update axes
        fig.update_yaxes(title_text='SOC (%)', range=[0, 100], row=row, col=col)

    def _add_curtailment_subplot(self, fig: go.Figure, row: int, col: int):
        """Add Curtailed Power subplot (Row 1, Col 2)"""
        fig.add_trace(
            go.Scatter(
                x=self.df.index,
                y=self.df['curtailment_kw'],
                fill='tozeroy',
                fillcolor='rgba(198, 40, 40, 0.3)',  # Red with transparency
                line=dict(color='#C62828', width=1.5),
                name='Curtailment',
                hovertemplate='%{y:.1f} kW<extra></extra>'
            ),
            row=row, col=col
        )

        fig.update_yaxes(title_text='Curtailed Power (kW)', row=row, col=col)

    def _add_battery_power_subplot(self, fig: go.Figure, row: int, col: int):
        """Add Battery Power Flow subplot (Row 2, Col 1)"""
        # Separate charge and discharge
        charge_power = np.where(self.df['battery_power_ac_kw'] > 0, self.df['battery_power_ac_kw'], 0)
        discharge_power = np.where(self.df['battery_power_ac_kw'] < 0, self.df['battery_power_ac_kw'], 0)

        # Charge (positive, green)
        fig.add_trace(
            go.Bar(
                x=self.df.index,
                y=charge_power,
                marker_color='#00897B',
                name='Charge',
                hovertemplate='Charge: %{y:.1f} kW<extra></extra>'
            ),
            row=row, col=col
        )

        # Discharge (negative, red)
        fig.add_trace(
            go.Bar(
                x=self.df.index,
                y=discharge_power,
                marker_color='#C62828',
                name='Discharge',
                hovertemplate='Discharge: %{y:.1f} kW<extra></extra>'
            ),
            row=row, col=col
        )

        # Power limits
        fig.add_hline(y=self.battery_kw, line_dash='dot', line_color='gray', row=row, col=col)
        fig.add_hline(y=-self.battery_kw, line_dash='dot', line_color='gray', row=row, col=col)

        fig.update_yaxes(
            title_text='Battery Power (kW)',
            range=[-self.battery_kw * 1.1, self.battery_kw * 1.1],
            row=row, col=col
        )

    def _add_crate_subplot(self, fig: go.Figure, row: int, col: int):
        """Add C-Rate Indicator subplot (Row 2, Col 2)"""
        # Calculate C-rate: power / capacity
        c_rate = np.abs(self.df['battery_power_ac_kw']) / self.battery_kwh

        fig.add_trace(
            go.Scatter(
                x=self.df.index,
                y=c_rate,
                line=dict(color='#1B263B', width=1.5),
                name='C-Rate',
                hovertemplate='C-Rate: %{y:.2f}<extra></extra>'
            ),
            row=row, col=col
        )

        # Reference line at 1C
        fig.add_hline(
            y=1.0, line_dash='dash', line_color='#FCC808',
            annotation_text='1C',
            row=row, col=col
        )

        fig.update_yaxes(title_text='C-Rate (P/E)', row=row, col=col)

    def _add_grid_power_subplot(self, fig: go.Figure, row: int, col: int):
        """Add Grid Power Flow subplot (Row 3, Col 1)"""
        # Consolidated net grid flow (positive=import, negative=export)
        grid_import = np.where(self.df['grid_power_kw'] > 0, self.df['grid_power_kw'], 0)
        grid_export = np.where(self.df['grid_power_kw'] < 0, self.df['grid_power_kw'], 0)

        # Import (positive, red)
        fig.add_trace(
            go.Scatter(
                x=self.df.index,
                y=grid_import,
                fill='tozeroy',
                fillcolor='rgba(255, 143, 0, 0.3)',  # Amber
                line=dict(color='#FF8F00', width=1.5),
                name='Grid Import',
                hovertemplate='Import: %{y:.1f} kW<extra></extra>'
            ),
            row=row, col=col
        )

        # Export (negative, green)
        fig.add_trace(
            go.Scatter(
                x=self.df.index,
                y=grid_export,
                fill='tozeroy',
                fillcolor='rgba(0, 137, 123, 0.3)',  # Teal
                line=dict(color='#00897B', width=1.5),
                name='Grid Export',
                hovertemplate='Export: %{y:.1f} kW<extra></extra>'
            ),
            row=row, col=col
        )

        # Grid limit reference
        grid_limit = self.result.simulation_metadata.get('grid_limit_kw', 70)
        fig.add_hline(
            y=grid_limit, line_dash='dash', line_color='gray',
            annotation_text=f'Grid Limit ({grid_limit} kW)',
            row=row, col=col
        )

        fig.update_yaxes(title_text='Grid Power (kW)', row=row, col=col)

    def _add_tariff_zones_subplot(self, fig: go.Figure, row: int, col: int):
        """Add Tariff Zones visualization (Row 3, Col 2)"""
        # Create stacked bar showing peak/off-peak hours
        peak_mask = self.df['is_peak']

        # Peak hours (red)
        fig.add_trace(
            go.Bar(
                x=self.df.index,
                y=peak_mask.astype(int),
                marker_color='#C62828',
                name='Peak Hours',
                hovertemplate='Peak Tariff<extra></extra>'
            ),
            row=row, col=col
        )

        # Off-peak hours (green)
        fig.add_trace(
            go.Bar(
                x=self.df.index,
                y=(~peak_mask).astype(int),
                marker_color='#00897B',
                name='Off-Peak Hours',
                hovertemplate='Off-Peak Tariff<extra></extra>'
            ),
            row=row, col=col
        )

        fig.update_yaxes(title_text='Tariff Zone', showticklabels=False, row=row, col=col)

    def _add_spot_price_subplot(self, fig: go.Figure, row: int, col: int):
        """Add Spot Price subplot (Row 4, Col 1) with dual y-axis"""
        # Spot price (primary y-axis)
        fig.add_trace(
            go.Scatter(
                x=self.df.index,
                y=self.df['spot_price'],
                line=dict(color='#4CAF50', width=2.5),  # Thick green line
                name='Spot Price',
                hovertemplate='Price: %{y:.3f} NOK/kWh<extra></extra>'
            ),
            row=row, col=col, secondary_y=False
        )

        fig.update_yaxes(title_text='Spot Price (NOK/kWh)', row=row, col=col, secondary_y=False)

    def _add_solar_production_subplot(self, fig: go.Figure, row: int, col: int):
        """Add Solar Production subplot (Row 4, Col 2)"""
        fig.add_trace(
            go.Scatter(
                x=self.df.index,
                y=self.df['production_ac_kw'],
                fill='tozeroy',
                fillcolor='rgba(252, 200, 8, 0.3)',  # Yellow
                line=dict(color='#FCC808', width=1.5),
                name='Solar Production',
                hovertemplate='Production: %{y:.1f} kW<extra></extra>'
            ),
            row=row, col=col
        )

        fig.update_yaxes(title_text='Solar Production (kW)', row=row, col=col)

    def _add_cost_components_subplot(self, fig: go.Figure, row: int, col: int):
        """Add Cost Components Breakdown subplot (Row 5, Col 1)"""
        # Calculate cost components per timestep
        timestep_hours = (self.df.index[1] - self.df.index[0]).total_seconds() / 3600

        # Energy cost (import - export)
        grid_import_cost = np.where(
            self.df['grid_power_kw'] > 0,
            self.df['grid_power_kw'] * self.df['spot_price'] * timestep_hours,
            0
        )
        grid_export_revenue = np.where(
            self.df['grid_power_kw'] < 0,
            -self.df['grid_power_kw'] * self.df['spot_price'] * timestep_hours,
            0
        )
        energy_cost = grid_import_cost - grid_export_revenue

        # Stacked area for cost components
        fig.add_trace(
            go.Scatter(
                x=self.df.index,
                y=energy_cost,
                fill='tozeroy',
                fillcolor='rgba(255, 143, 0, 0.5)',
                line=dict(width=0),
                name='Energy Cost',
                stackgroup='costs',
                hovertemplate='Energy: %{y:.2f} NOK<extra></extra>'
            ),
            row=row, col=col
        )

        fig.update_yaxes(title_text='Cost Components (NOK)', row=row, col=col)

    def _add_cumulative_cost_subplot(self, fig: go.Figure, row: int, col: int):
        """Add Cumulative Cost subplot (Row 5, Col 2)"""
        # Calculate cumulative cost
        timestep_hours = (self.df.index[1] - self.df.index[0]).total_seconds() / 3600

        cost_per_step = (
            np.where(self.df['grid_power_kw'] > 0,
                    self.df['grid_power_kw'] * self.df['spot_price'], 0) -
            np.where(self.df['grid_power_kw'] < 0,
                    -self.df['grid_power_kw'] * self.df['spot_price'], 0)
        ) * timestep_hours

        cumulative_cost = np.cumsum(cost_per_step)

        fig.add_trace(
            go.Scatter(
                x=self.df.index,
                y=cumulative_cost,
                line=dict(color='#1B263B', width=2.5),
                name='Cumulative Cost',
                hovertemplate='Total: %{y:.0f} NOK<extra></extra>'
            ),
            row=row, col=col
        )

        fig.update_yaxes(title_text='Cumulative Cost (NOK)', row=row, col=col)

    def _add_daily_metrics_table(self, fig: go.Figure, row: int, col: int):
        """Add Daily Metrics table (Row 6, Col 1)"""
        # Calculate daily aggregates
        daily = self.df.resample('D').agg({
            'production_ac_kw': 'sum',
            'consumption_kw': 'sum',
            'grid_power_kw': lambda x: x[x > 0].sum(),  # Import only
            'battery_power_ac_kw': lambda x: (x[x > 0].sum(), x[x < 0].abs().sum()),
            'curtailment_kw': 'sum'
        })

        # Format for table
        dates = [d.strftime('%Y-%m-%d') for d in daily.index]
        production = [f'{v:.0f}' for v in daily['production_ac_kw']]
        consumption = [f'{v:.0f}' for v in daily['consumption_kw']]
        grid_import = [f'{v:.0f}' for v in daily['grid_power_kw']]

        fig.add_trace(
            go.Table(
                header=dict(
                    values=['<b>Date</b>', '<b>Production</b>', '<b>Consumption</b>', '<b>Grid Import</b>'],
                    fill_color='#44546A',
                    align='left',
                    font=dict(color='white', size=11)
                ),
                cells=dict(
                    values=[dates[:10], production[:10], consumption[:10], grid_import[:10]],  # Limit to 10 rows
                    fill_color='#E0E0E0',
                    align=['left', 'right', 'right', 'right'],
                    font=dict(size=10)
                )
            ),
            row=row, col=col
        )

    def _add_weekly_aggregates_table(self, fig: go.Figure, row: int, col: int):
        """Add Weekly Aggregates table (Row 6, Col 2)"""
        # Calculate weekly metrics
        weekly = self.df.resample('W').agg({
            'production_ac_kw': 'sum',
            'battery_power_ac_kw': lambda x: x[x > 0].sum(),  # Total charging
            'curtailment_kw': 'sum',
            'battery_soc_kwh': 'mean'
        })

        # Calculate equivalent cycles
        weekly['cycles'] = weekly['battery_power_ac_kw'] / (2 * self.battery_kwh)

        # Format for table
        weeks = [f'Week {i+1}' for i in range(len(weekly))]
        production = [f'{v:.0f} kWh' for v in weekly['production_ac_kw']]
        cycles = [f'{v:.2f}' for v in weekly['cycles']]
        curtail = [f'{v:.0f} kWh' for v in weekly['curtailment_kw']]

        fig.add_trace(
            go.Table(
                header=dict(
                    values=['<b>Week</b>', '<b>Production</b>', '<b>Cycles</b>', '<b>Curtailment</b>'],
                    fill_color='#44546A',
                    align='left',
                    font=dict(color='white', size=11)
                ),
                cells=dict(
                    values=[weeks, production, cycles, curtail],
                    fill_color='#E0E0E0',
                    align=['left', 'right', 'right', 'right'],
                    font=dict(size=10)
                )
            ),
            row=row, col=col
        )

    def generate(self) -> Path:
        """
        Generate battery operation report and export to HTML/PNG.

        Returns:
            Path to main HTML report file
        """
        print(f"\nGenerating Battery Operation Report...")
        print(f"  Period: {self.period}")
        print(f"  Battery: {self.battery_kwh} kWh / {self.battery_kw} kW")
        print(f"  Time range: {self.df.index[0].date()} to {self.df.index[-1].date()}")
        print(f"  Timesteps: {len(self.df)}")

        # Create figure
        fig = self._create_figure()

        # Save using inherited PlotlyReportGenerator method
        html_path = self.save_plotly_figure(
            fig,
            filename=f'battery_operation_{self.period}',
            subdir='reports',
            title=f'Battery Operation Report ({self.period})',
            export_png=self.export_png
        )

        return html_path

    def get_summary_metrics(self) -> Dict[str, Any]:
        """
        Calculate summary metrics for the reporting period.

        Returns:
            Dictionary with operational and economic metrics
        """
        timestep_hours = (self.df.index[1] - self.df.index[0]).total_seconds() / 3600

        # Energy flows
        total_production = self.df['production_ac_kw'].sum() * timestep_hours
        total_consumption = self.df['consumption_kw'].sum() * timestep_hours
        total_grid_import = self.df['grid_power_kw'][self.df['grid_power_kw'] > 0].sum() * timestep_hours
        total_grid_export = -self.df['grid_power_kw'][self.df['grid_power_kw'] < 0].sum() * timestep_hours
        total_curtailment = self.df['curtailment_kw'].sum() * timestep_hours

        # Battery utilization
        total_charge = self.df['battery_power_ac_kw'][self.df['battery_power_ac_kw'] > 0].sum() * timestep_hours
        total_discharge = self.df['battery_power_ac_kw'][self.df['battery_power_ac_kw'] < 0].abs().sum() * timestep_hours
        equivalent_cycles = (total_charge + total_discharge) / (2 * self.battery_kwh)

        charge_hours = (self.df['battery_power_ac_kw'] > 0).sum()
        discharge_hours = (self.df['battery_power_ac_kw'] < 0).sum()
        idle_hours = len(self.df) - charge_hours - discharge_hours

        # Efficiency
        roundtrip_efficiency = (total_discharge / total_charge * 100) if total_charge > 0 else 0

        return {
            'period': f"{self.df.index[0].date()} to {self.df.index[-1].date()}",
            'timesteps': len(self.df),
            'duration_hours': len(self.df) * timestep_hours,

            # Energy flows (kWh)
            'production_kwh': float(total_production),
            'consumption_kwh': float(total_consumption),
            'grid_import_kwh': float(total_grid_import),
            'grid_export_kwh': float(total_grid_export),
            'curtailment_kwh': float(total_curtailment),

            # Battery operations
            'battery_charge_kwh': float(total_charge),
            'battery_discharge_kwh': float(total_discharge),
            'equivalent_cycles': float(equivalent_cycles),
            'roundtrip_efficiency_pct': float(roundtrip_efficiency),

            # Utilization
            'charge_hours': int(charge_hours),
            'discharge_hours': int(discharge_hours),
            'idle_hours': int(idle_hours),
            'utilization_pct': float((charge_hours + discharge_hours) / len(self.df) * 100),

            # SOC statistics
            'soc_min_pct': float(self.df['soc_pct'].min()),
            'soc_max_pct': float(self.df['soc_pct'].max()),
            'soc_mean_pct': float(self.df['soc_pct'].mean()),
            'soc_start_pct': float(self.df['soc_pct'].iloc[0]),
            'soc_end_pct': float(self.df['soc_pct'].iloc[-1]),

            # Peak power
            'peak_grid_import_kw': float(self.df['grid_power_kw'].max()),
            'peak_grid_export_kw': float(self.df['grid_power_kw'].min()),
            'peak_production_kw': float(self.df['production_ac_kw'].max()),
        }
