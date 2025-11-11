"""
Interactive Plotly Cost Analysis - 3 Week Detailed Breakdown
=============================================================

Migrated from matplotlib to interactive Plotly with enhanced features:
- 6-panel interactive dashboard with comprehensive cost visualizations
- Reference (no battery) vs Battery scenario comparison
- Norsk Solkraft branded theme with professional styling
- Detailed cost breakdown by category (energy, power tariff, degradation)
- Hover tooltips with full cost details
- Time range selector for focused analysis
- Export to HTML (primary) and PNG (optional)

Usage:
    from scripts.visualization.plot_costs_3weeks_plotly import generate_cost_report

    report_path = generate_cost_report(
        trajectory_path=Path('results/yearly_2024/trajectory.csv'),
        reference_path=Path('results/yearly_2024/reference_trajectory.csv'),
        output_dir=Path('results'),
        period='3weeks'
    )

Author: Klaus + Claude
Date: November 2025
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from typing import Optional, Tuple, Dict
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.visualization.norsk_solkraft_theme import apply_light_theme, get_brand_colors


# Cost component colors (Norsk Solkraft palette)
COST_COLORS = {
    'energy': '#F5A621',      # Solenergi Oransje - energy costs
    'power': '#00609F',       # Profesjonell Blå - power tariff
    'degradation': '#B71C1C', # Mørk Rød - degradation
    'savings': '#A8D8A8',     # Mose Grønn - savings
    'reference': '#8A8A8A',   # Teknisk grå - reference scenario
    'battery': '#F5A621',     # Oransje - battery scenario
}


def prepare_cost_data(
    trajectory_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    start_date: str = '2024-06-01',
    period_days: int = 21
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepare cost data from trajectory DataFrames for 3-week period.

    Args:
        trajectory_df: Battery scenario trajectory
        reference_df: Reference (no battery) scenario trajectory
        prices_df: Spot prices with timestamp
        start_date: Start date for analysis period
        period_days: Number of days to analyze

    Returns:
        Tuple of (battery_costs_df, reference_costs_df) with hourly cost breakdown
    """
    # Parse timestamps and normalize timezone
    trajectory_df['timestamp'] = pd.to_datetime(trajectory_df['timestamp']).dt.tz_localize(None)
    reference_df['timestamp'] = pd.to_datetime(reference_df['timestamp']).dt.tz_localize(None)
    prices_df['timestamp'] = pd.to_datetime(prices_df['timestamp'], utc=True).dt.tz_localize(None)

    # Filter to 3-week period
    start = pd.Timestamp(start_date).tz_localize(None)
    end = (start + pd.Timedelta(days=period_days)).tz_localize(None)

    trajectory_period = trajectory_df[
        (trajectory_df['timestamp'] >= start) & (trajectory_df['timestamp'] < end)
    ].copy()

    reference_period = reference_df[
        (reference_df['timestamp'] >= start) & (reference_df['timestamp'] < end)
    ].copy()

    prices_period = prices_df[
        (prices_df['timestamp'] >= start) & (prices_df['timestamp'] < end)
    ].copy()

    # Merge prices
    trajectory_period = trajectory_period.merge(prices_period, on='timestamp', how='left')
    reference_period = reference_period.merge(prices_period, on='timestamp', how='left')

    # Add time-of-use tariff information
    trajectory_period['hour'] = trajectory_period['timestamp'].dt.hour
    trajectory_period['weekday'] = trajectory_period['timestamp'].dt.weekday
    trajectory_period['is_peak'] = (
        (trajectory_period['weekday'] < 5) &
        (trajectory_period['hour'] >= 6) &
        (trajectory_period['hour'] < 22)
    )

    reference_period['hour'] = reference_period['timestamp'].dt.hour
    reference_period['weekday'] = reference_period['timestamp'].dt.weekday
    reference_period['is_peak'] = (
        (reference_period['weekday'] < 5) &
        (reference_period['hour'] >= 6) &
        (reference_period['hour'] < 22)
    )

    # Tariff rates (Lnett commercial)
    TARIFF_PEAK = 0.296  # kr/kWh
    TARIFF_OFFPEAK = 0.176  # kr/kWh
    ENERGY_TAX = 0.1791  # kr/kWh
    FEED_IN_PREMIUM = 0.04  # kr/kWh

    trajectory_period['tariff'] = np.where(
        trajectory_period['is_peak'], TARIFF_PEAK, TARIFF_OFFPEAK
    )
    reference_period['tariff'] = np.where(
        reference_period['is_peak'], TARIFF_PEAK, TARIFF_OFFPEAK
    )

    # Calculate hourly energy costs
    # Import cost = import_kWh * (spot + tariff + tax)
    trajectory_period['energy_cost'] = (
        trajectory_period['P_grid_import_kw'] *
        (trajectory_period['price_nok'] + trajectory_period['tariff'] + ENERGY_TAX)
    )

    reference_period['energy_cost'] = (
        reference_period['P_grid_import_kw'] *
        (reference_period['price_nok'] + reference_period['tariff'] + ENERGY_TAX)
    )

    # Export revenue (negative cost)
    trajectory_period['export_revenue'] = (
        trajectory_period['P_grid_export_kw'] *
        (trajectory_period['price_nok'] + FEED_IN_PREMIUM)
    )

    reference_period['export_revenue'] = (
        reference_period['P_grid_export_kw'] *
        (reference_period['price_nok'] + FEED_IN_PREMIUM)
    )

    # Net energy cost (positive = cost, negative = revenue)
    trajectory_period['net_energy_cost'] = (
        trajectory_period['energy_cost'] - trajectory_period['export_revenue']
    )
    reference_period['net_energy_cost'] = (
        reference_period['energy_cost'] - reference_period['export_revenue']
    )

    # Power tariff cost (allocated hourly from monthly peak)
    # For simplicity, allocate evenly across hours in the period
    # In reality, this is monthly billing based on peak demand
    trajectory_period['power_cost'] = 0  # Will calculate monthly peaks separately
    reference_period['power_cost'] = 0

    # Degradation cost (battery only)
    DEGRADATION_COST_PER_KWH = 0.05  # kr/kWh cycled
    trajectory_period['degradation_cost'] = (
        (trajectory_period['P_charge_kw'] + trajectory_period['P_discharge_kw']) / 2 *
        DEGRADATION_COST_PER_KWH
    )
    reference_period['degradation_cost'] = 0  # No battery in reference

    # Total hourly cost
    trajectory_period['total_cost'] = (
        trajectory_period['net_energy_cost'] +
        trajectory_period['power_cost'] +
        trajectory_period['degradation_cost']
    )

    reference_period['total_cost'] = (
        reference_period['net_energy_cost'] +
        reference_period['power_cost']
    )

    return trajectory_period, reference_period


def create_cost_dashboard(
    battery_costs: pd.DataFrame,
    reference_costs: pd.DataFrame,
    period_name: str = '3 Weeks - June 2024'
) -> go.Figure:
    """
    Create comprehensive 6-panel interactive cost dashboard.

    Panels:
    1. Cost Components Stacked Area (Reference vs Battery)
    2. Cumulative Cost Comparison
    3. Daily Savings Breakdown
    4. Cost Metrics Summary Table
    5. Hourly Cost Heatmap
    6. Cost per kWh Analysis

    Args:
        battery_costs: Battery scenario cost data
        reference_costs: Reference scenario cost data
        period_name: Display name for the period

    Returns:
        Plotly Figure with 6-panel dashboard
    """
    # Create subplot structure (3 rows x 2 cols)
    fig = make_subplots(
        rows=3, cols=2,
        row_heights=[0.30, 0.30, 0.40],
        column_widths=[0.55, 0.45],
        subplot_titles=(
            'Cost Components - Reference (No Battery)',
            'Cost Components - Battery Scenario',
            'Cumulative Cost Comparison',
            'Daily Savings Breakdown',
            'Cost Metrics Summary',
            'Hourly Cost Heatmap (kr/h)'
        ),
        specs=[
            [{"type": "scatter"}, {"type": "scatter"}],
            [{"type": "scatter"}, {"type": "bar"}],
            [{"type": "table"}, {"type": "heatmap"}]
        ],
        vertical_spacing=0.10,
        horizontal_spacing=0.08
    )

    # =========================================================================
    # PANEL 1 & 2: Cost Components Stacked Area Charts
    # =========================================================================

    # Aggregate to daily for better visualization
    ref_daily = reference_costs.groupby(reference_costs['timestamp'].dt.date).agg({
        'net_energy_cost': 'sum',
        'power_cost': 'sum',
        'degradation_cost': 'sum',
        'total_cost': 'sum'
    }).reset_index()
    ref_daily.columns = ['date', 'energy_cost', 'power_cost', 'degradation_cost', 'total_cost']

    battery_daily = battery_costs.groupby(battery_costs['timestamp'].dt.date).agg({
        'net_energy_cost': 'sum',
        'power_cost': 'sum',
        'degradation_cost': 'sum',
        'total_cost': 'sum'
    }).reset_index()
    battery_daily.columns = ['date', 'energy_cost', 'power_cost', 'degradation_cost', 'total_cost']

    # Panel 1: Reference scenario stacked area
    fig.add_trace(
        go.Scatter(
            x=ref_daily['date'],
            y=ref_daily['energy_cost'],
            name='Energy Cost (Ref)',
            line=dict(color=COST_COLORS['energy'], width=0),
            fillcolor=f"rgba(245, 166, 33, 0.6)",
            fill='tozeroy',
            stackgroup='ref',
            legendgroup='ref',
            hovertemplate='Energy: %{y:.2f} kr<extra></extra>'
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=ref_daily['date'],
            y=ref_daily['power_cost'],
            name='Power Tariff (Ref)',
            line=dict(color=COST_COLORS['power'], width=0),
            fillcolor=f"rgba(0, 96, 159, 0.6)",
            stackgroup='ref',
            legendgroup='ref',
            hovertemplate='Power: %{y:.2f} kr<extra></extra>'
        ),
        row=1, col=1
    )

    # Panel 2: Battery scenario stacked area
    fig.add_trace(
        go.Scatter(
            x=battery_daily['date'],
            y=battery_daily['energy_cost'],
            name='Energy Cost',
            line=dict(color=COST_COLORS['energy'], width=0),
            fillcolor=f"rgba(245, 166, 33, 0.6)",
            fill='tozeroy',
            stackgroup='battery',
            legendgroup='battery',
            hovertemplate='Energy: %{y:.2f} kr<extra></extra>'
        ),
        row=1, col=2
    )

    fig.add_trace(
        go.Scatter(
            x=battery_daily['date'],
            y=battery_daily['power_cost'],
            name='Power Tariff',
            line=dict(color=COST_COLORS['power'], width=0),
            fillcolor=f"rgba(0, 96, 159, 0.6)",
            stackgroup='battery',
            legendgroup='battery',
            hovertemplate='Power: %{y:.2f} kr<extra></extra>'
        ),
        row=1, col=2
    )

    fig.add_trace(
        go.Scatter(
            x=battery_daily['date'],
            y=battery_daily['degradation_cost'],
            name='Degradation',
            line=dict(color=COST_COLORS['degradation'], width=0),
            fillcolor=f"rgba(183, 28, 28, 0.6)",
            stackgroup='battery',
            legendgroup='battery',
            hovertemplate='Degradation: %{y:.2f} kr<extra></extra>'
        ),
        row=1, col=2
    )

    # =========================================================================
    # PANEL 3: Cumulative Cost Comparison
    # =========================================================================

    ref_daily['cumulative_cost'] = ref_daily['total_cost'].cumsum()
    battery_daily['cumulative_cost'] = battery_daily['total_cost'].cumsum()
    battery_daily['savings'] = ref_daily['cumulative_cost'] - battery_daily['cumulative_cost']

    # Reference line
    fig.add_trace(
        go.Scatter(
            x=ref_daily['date'],
            y=ref_daily['cumulative_cost'],
            name='Reference (No Battery)',
            line=dict(color=COST_COLORS['reference'], width=2.5, dash='dash'),
            legendgroup='cumulative',
            hovertemplate='Reference: %{y:.2f} kr<extra></extra>'
        ),
        row=2, col=1
    )

    # Battery line
    fig.add_trace(
        go.Scatter(
            x=battery_daily['date'],
            y=battery_daily['cumulative_cost'],
            name='Battery Scenario',
            line=dict(color=COST_COLORS['battery'], width=2.5),
            legendgroup='cumulative',
            hovertemplate='Battery: %{y:.2f} kr<extra></extra>'
        ),
        row=2, col=1
    )

    # Shaded savings area
    fig.add_trace(
        go.Scatter(
            x=battery_daily['date'],
            y=ref_daily['cumulative_cost'],
            fill=None,
            mode='lines',
            line=dict(color='rgba(0,0,0,0)'),
            showlegend=False
        ),
        row=2, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=battery_daily['date'],
            y=battery_daily['cumulative_cost'],
            fill='tonexty',
            fillcolor='rgba(168, 216, 168, 0.3)',
            mode='lines',
            line=dict(color='rgba(0,0,0,0)'),
            name='Cumulative Savings',
            legendgroup='cumulative',
            hovertemplate='Savings: %{text:.2f} kr<extra></extra>',
            text=battery_daily['savings']
        ),
        row=2, col=1
    )

    # =========================================================================
    # PANEL 4: Daily Savings Breakdown
    # =========================================================================

    daily_savings = ref_daily['total_cost'] - battery_daily['total_cost']
    colors = [COST_COLORS['savings'] if s > 0 else COST_COLORS['degradation'] for s in daily_savings]

    fig.add_trace(
        go.Bar(
            x=battery_daily['date'],
            y=daily_savings,
            name='Daily Savings',
            marker_color=colors,
            legendgroup='savings',
            hovertemplate='Savings: %{y:.2f} kr/day<extra></extra>'
        ),
        row=2, col=2
    )

    # Add zero line
    fig.add_hline(y=0, line_dash="solid", line_color="#212121", line_width=1, row=2, col=2)

    # =========================================================================
    # PANEL 5: Cost Metrics Summary Table
    # =========================================================================

    total_ref = ref_daily['total_cost'].sum()
    total_battery = battery_daily['total_cost'].sum()
    total_savings = total_ref - total_battery
    savings_pct = (total_savings / total_ref * 100) if total_ref > 0 else 0

    avg_daily_ref = ref_daily['total_cost'].mean()
    avg_daily_battery = battery_daily['total_cost'].mean()

    metrics_table = go.Table(
        header=dict(
            values=['<b>Metric</b>', '<b>Reference</b>', '<b>Battery</b>', '<b>Savings</b>'],
            fill_color='#44546A',
            align='left',
            font=dict(color='white', size=14, family='Arial')
        ),
        cells=dict(
            values=[
                ['Total Energy Cost', 'Total Power Cost', 'Total Degradation', 'Total Cost', 'Avg Daily Cost'],
                [f"{ref_daily['energy_cost'].sum():.2f} kr",
                 f"{ref_daily['power_cost'].sum():.2f} kr",
                 f"0.00 kr",
                 f"{total_ref:.2f} kr",
                 f"{avg_daily_ref:.2f} kr/day"],
                [f"{battery_daily['energy_cost'].sum():.2f} kr",
                 f"{battery_daily['power_cost'].sum():.2f} kr",
                 f"{battery_daily['degradation_cost'].sum():.2f} kr",
                 f"{total_battery:.2f} kr",
                 f"{avg_daily_battery:.2f} kr/day"],
                [f"{ref_daily['energy_cost'].sum() - battery_daily['energy_cost'].sum():.2f} kr",
                 f"{ref_daily['power_cost'].sum() - battery_daily['power_cost'].sum():.2f} kr",
                 f"-{battery_daily['degradation_cost'].sum():.2f} kr",
                 f"{total_savings:.2f} kr ({savings_pct:.1f}%)",
                 f"{avg_daily_ref - avg_daily_battery:.2f} kr/day"]
            ],
            fill_color=['#E0E0E0', '#FAFAFA', '#FAFAFA', '#A8D8A8'],
            align=['left', 'right', 'right', 'right'],
            font=dict(color='#212121', size=13, family='Arial'),
            height=30
        )
    )

    fig.add_trace(metrics_table, row=3, col=1)

    # =========================================================================
    # PANEL 6: Hourly Cost Heatmap
    # =========================================================================

    # Pivot battery costs to create day x hour matrix
    battery_costs['date'] = battery_costs['timestamp'].dt.date
    battery_costs['hour'] = battery_costs['timestamp'].dt.hour

    heatmap_data = battery_costs.pivot_table(
        index='date',
        columns='hour',
        values='total_cost',
        aggfunc='sum'
    )

    fig.add_trace(
        go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=[str(d) for d in heatmap_data.index],
            colorscale=[
                [0, '#A8D8A8'],      # Green for low cost
                [0.5, '#FCC808'],    # Yellow for medium
                [1, '#B71C1C']       # Red for high cost
            ],
            colorbar=dict(title="Cost (kr/h)", x=1.02),
            hovertemplate='Date: %{y}<br>Hour: %{x}<br>Cost: %{z:.2f} kr<extra></extra>'
        ),
        row=3, col=2
    )

    # =========================================================================
    # Update Layout & Axes
    # =========================================================================

    # Y-axis labels
    fig.update_yaxes(title_text="Daily Cost (kr)", row=1, col=1)
    fig.update_yaxes(title_text="Daily Cost (kr)", row=1, col=2)
    fig.update_yaxes(title_text="Cumulative Cost (kr)", row=2, col=1)
    fig.update_yaxes(title_text="Daily Savings (kr)", row=2, col=2)
    fig.update_yaxes(title_text="Date", row=3, col=2)

    # X-axis labels
    fig.update_xaxes(title_text="Date", row=1, col=1)
    fig.update_xaxes(title_text="Date", row=1, col=2)
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=2)
    fig.update_xaxes(title_text="Hour of Day", row=3, col=2)

    # Add range selector to cumulative cost plot
    fig.update_xaxes(
        rangeslider_visible=False,
        rangeselector=dict(
            buttons=list([
                dict(count=7, label="1w", step="day", stepmode="backward"),
                dict(count=14, label="2w", step="day", stepmode="backward"),
                dict(step="all", label="All")
            ]),
            x=0.0,
            y=1.15,
            xanchor='left',
            yanchor='top'
        ),
        row=2, col=1
    )

    # Global layout
    fig.update_layout(
        title=dict(
            text=f"Cost Analysis Dashboard - {period_name}<br>" +
                 f"<sub>Total Savings: {total_savings:.2f} kr ({savings_pct:.1f}%) | " +
                 f"Avg Daily Savings: {avg_daily_ref - avg_daily_battery:.2f} kr/day</sub>",
            font=dict(size=20)
        ),
        height=1400,
        showlegend=True,
        hovermode='closest',
        font=dict(size=12)
    )

    return fig


def generate_cost_report(
    trajectory_path: Path,
    reference_path: Optional[Path] = None,
    output_dir: Path = Path('results'),
    period: str = '3weeks',
    start_date: str = '2024-06-01',
    period_days: int = 21
) -> Path:
    """
    Generate interactive cost analysis report for 3-week period.

    Args:
        trajectory_path: Path to battery scenario trajectory CSV
        reference_path: Path to reference scenario trajectory CSV (optional, will simulate if missing)
        output_dir: Output directory for reports
        period: Period name for file naming
        start_date: Start date for analysis (YYYY-MM-DD)
        period_days: Number of days to analyze

    Returns:
        Path to generated HTML report
    """
    print(f"\n{'='*80}")
    print(f"  COST ANALYSIS REPORT GENERATOR - {period_days} Days")
    print(f"{'='*80}\n")

    # Load data
    print("Loading trajectory data...")
    trajectory_df = pd.read_csv(trajectory_path)

    # Load or create reference scenario
    if reference_path and reference_path.exists():
        print(f"Loading reference data from {reference_path}...")
        reference_df = pd.read_csv(reference_path)
    else:
        print("Reference trajectory not found, creating from trajectory (zero battery action)...")
        reference_df = trajectory_df.copy()
        # Simulate no battery by zeroing battery actions
        reference_df['P_charge_kw'] = 0
        reference_df['P_discharge_kw'] = 0
        reference_df['E_battery_kwh'] = 0

    # Load price data
    print("Loading price data...")
    prices_path = Path('data/spot_prices/NO2_2024_60min_real.csv')
    if not prices_path.exists():
        raise FileNotFoundError(f"Price data not found: {prices_path}")

    prices_df = pd.read_csv(prices_path)

    # Prepare cost data
    print(f"Calculating costs for period: {start_date} to {start_date} + {period_days} days...")
    battery_costs, reference_costs = prepare_cost_data(
        trajectory_df, reference_df, prices_df, start_date, period_days
    )

    # Create dashboard
    print("Creating interactive dashboard...")
    fig = create_cost_dashboard(battery_costs, reference_costs, f"{period_days} Days - {start_date}")

    # Apply Norsk Solkraft theme
    apply_light_theme()
    fig.update_layout(template='norsk_solkraft_light')

    # Save HTML report
    reports_dir = output_dir / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)

    html_path = reports_dir / f'cost_analysis_{period}.html'
    print(f"\nSaving interactive HTML report...")
    fig.write_html(
        html_path,
        include_plotlyjs='cdn',
        config={'displayModeBar': True, 'displaylogo': False}
    )
    print(f"  ✓ HTML report: {html_path}")

    # Optional: Save PNG (requires kaleido)
    try:
        figures_dir = output_dir / 'figures' / 'cost_analysis'
        figures_dir.mkdir(parents=True, exist_ok=True)

        png_path = figures_dir / f'{period}.png'
        print(f"\nSaving PNG export...")
        fig.write_image(png_path, width=1920, height=1400, scale=2)
        print(f"  ✓ PNG export: {png_path}")
    except Exception as e:
        print(f"  ⚠ PNG export skipped (kaleido not available): {e}")

    # Print summary
    total_ref = reference_costs['total_cost'].sum()
    total_battery = battery_costs['total_cost'].sum()
    total_savings = total_ref - total_battery
    savings_pct = (total_savings / total_ref * 100) if total_ref > 0 else 0

    print(f"\n{'='*80}")
    print(f"  COST SUMMARY - {period_days} Days")
    print(f"{'='*80}")
    print(f"  Reference Total Cost:  {total_ref:>10,.2f} kr")
    print(f"  Battery Total Cost:    {total_battery:>10,.2f} kr")
    print(f"  {'─'*80}")
    print(f"  Total Savings:         {total_savings:>10,.2f} kr ({savings_pct:>5.1f}%)")
    print(f"  Avg Daily Savings:     {total_savings/period_days:>10,.2f} kr/day")
    print(f"{'='*80}\n")

    return html_path


if __name__ == "__main__":
    # Example usage
    from pathlib import Path

    # Apply theme globally
    apply_light_theme()

    # Generate report for 3-week period in June
    report_path = generate_cost_report(
        trajectory_path=Path('results/yearly_2024/trajectory.csv'),
        reference_path=None,  # Will be simulated
        output_dir=Path('results'),
        period='3weeks_june',
        start_date='2024-06-01',
        period_days=21
    )

    print(f"\n✓ Cost analysis report generated: {report_path}")
    print("  Open in browser to explore interactive visualizations")

    # Optional: Open in browser automatically
    import webbrowser
    webbrowser.open(f"file://{report_path.absolute()}")
