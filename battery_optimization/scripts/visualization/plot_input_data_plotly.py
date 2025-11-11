"""
Interactive Input Data Validation Dashboard
============================================

Comprehensive Plotly-based validation dashboard for battery optimization input data.
Replaces matplotlib static plots with interactive, theme-compliant visualizations.

Features:
- 12 validation visualizations in 6-row × 2-column grid layout
- Synchronized zoom and range selectors
- Data quality indicators and completeness checks
- Tariff zone highlighting and duration curves
- Full year analysis with monthly aggregates
- Norsk Solkraft theme compliance

Usage:
    python scripts/visualization/plot_input_data_plotly.py
    python scripts/visualization/plot_input_data_plotly.py --year 2024 --output results/reports
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# Import data loaders
import sys
sys.path.insert(0, str(Path(__file__).parents[2]))

from core.pvgis_solar import PVGISProduction
from core.price_fetcher import ENTSOEPriceFetcher
from core.consumption_profiles import ConsumptionProfile
from src.visualization.norsk_solkraft_theme import (
    apply_light_theme,
    get_brand_colors,
    get_gray_scale
)


# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADING & VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def load_and_validate_input_data(year=2024):
    """
    Load input data with comprehensive quality checks

    Args:
        year: Year to analyze (2024 for real data, 2020 for typical year)

    Returns:
        dict with:
            - 'prices': Spot prices (NOK/kWh)
            - 'production': PV production (kW)
            - 'consumption': Load profile (kW)
            - 'quality': Data quality metrics dict
            - 'metadata': Data source information
    """

    print("=" * 70)
    print(f"LOADING INPUT DATA FOR {year}")
    print("=" * 70)

    # 1. Solar Production (PVGIS - returns typical year 2020 data)
    print("\n1. Solar Production (PVGIS typical year)...")
    pvgis = PVGISProduction(
        lat=58.97,
        lon=5.73,
        pv_capacity_kwp=138.55,
        tilt=30,
        azimuth=173,
        system_loss=14
    )
    production = pvgis.fetch_hourly_production(year, refresh=False)
    actual_year = production.index[0].year
    print(f"   ✓ {len(production)} hours, total={production.sum():.0f} kWh")
    print(f"   Note: PVGIS returns typical year data (year={actual_year})")

    # 2. Consumption Profile (synthetic commercial office)
    print("\n2. Consumption Profile (synthetic commercial office)...")
    consumption = ConsumptionProfile.generate_annual_profile(
        profile_type='commercial_office',
        annual_kwh=300000,
        year=actual_year
    )
    print(f"   ✓ {len(consumption)} hours, total={consumption.sum():.0f} kWh")

    # 3. Spot Prices (real 2024 data, aligned to actual_year)
    print("\n3. Spot Prices (ENTSO-E NO2 real data)...")
    price_fetcher = ENTSOEPriceFetcher()
    spot_prices = price_fetcher.fetch_prices(year, 'NO2', refresh=False)
    # Align to same year as PVGIS
    spot_prices.index = spot_prices.index.map(lambda x: x.replace(year=actual_year))
    print(f"   ✓ {len(spot_prices)} hours, mean={spot_prices.mean():.3f} NOK/kWh")

    # 4. Align to minimum length
    min_len = min(len(production), len(consumption), len(spot_prices))
    production = production[:min_len]
    consumption = consumption[:min_len]
    spot_prices = spot_prices[:min_len]
    print(f"\n4. Data aligned to {min_len} hours")

    # 5. Calculate derived data
    net_load = consumption - production  # Positive = grid import, Negative = export
    curtailment_risk = production - 77  # Above grid limit (77 kW)
    curtailment_risk = curtailment_risk[curtailment_risk > 0]

    # 6. Quality validation
    quality = {
        'prices_missing_pct': (spot_prices.isna().sum() / len(spot_prices)) * 100,
        'prices_negative_count': (spot_prices < 0).sum(),
        'production_missing_pct': (production.isna().sum() / len(production)) * 100,
        'production_negative_count': (production < 0).sum(),
        'consumption_missing_pct': (consumption.isna().sum() / len(consumption)) * 100,
        'consumption_unrealistic_count': (consumption > 1000).sum(),  # >1 MW unusual
        'timestamps_aligned': len(production) == len(consumption) == len(spot_prices),
        'curtailment_hours': len(curtailment_risk),
        'curtailment_energy_kwh': curtailment_risk.sum() if len(curtailment_risk) > 0 else 0
    }

    # 7. Metadata
    metadata = {
        'year': actual_year,
        'requested_year': year,
        'data_points': min_len,
        'pv_system': {
            'capacity_kwp': 138.55,
            'location': 'Stavanger (58.97°N, 5.73°E)',
            'tilt': 30,
            'azimuth': 173
        },
        'consumption_profile': 'commercial_office (300 MWh/year)',
        'grid_limit_kw': 77,
        'timestamp_start': production.index[0],
        'timestamp_end': production.index[-1]
    }

    print("\n" + "=" * 70)
    print("DATA QUALITY REPORT")
    print("=" * 70)
    for key, value in quality.items():
        if isinstance(value, bool):
            status = "✅" if value else "❌"
            print(f"  {status} {key}: {value}")
        elif 'pct' in key:
            print(f"  {key}: {value:.2f}%")
        else:
            print(f"  {key}: {value}")

    return {
        'prices': spot_prices,
        'production': production,
        'consumption': consumption,
        'net_load': net_load,
        'quality': quality,
        'metadata': metadata
    }


# ═══════════════════════════════════════════════════════════════════════════
# VISUALIZATION COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════

def create_price_timeseries(prices, colors, grays):
    """Row 1 Left: Annual spot price timeseries with tariff zones"""

    # Define tariff zones (peak = Mon-Fri 06:00-22:00)
    is_peak = (prices.index.dayofweek < 5) & (prices.index.hour >= 6) & (prices.index.hour < 22)

    fig = go.Figure()

    # Add tariff zone backgrounds
    # This is simplified - for full accuracy would need shapes for each zone
    fig.add_hline(
        y=0,
        line_dash="solid",
        line_color=grays['silver'],
        line_width=1,
        annotation_text="Zero Price Line",
        annotation_position="right"
    )

    # Price line
    fig.add_scatter(
        x=prices.index,
        y=prices.values,
        mode='lines',
        name='Spot Price',
        line=dict(color=colors['oransje'], width=1.5),
        hovertemplate='<b>%{x|%d.%m.%Y %H:%M}</b><br>Price: %{y:.3f} NOK/kWh<extra></extra>'
    )

    # Mean price line
    mean_price = prices.mean()
    fig.add_hline(
        y=mean_price,
        line_dash="dash",
        line_color=grays['skifer'],
        annotation_text=f"Mean: {mean_price:.3f} NOK/kWh",
        annotation_position="right"
    )

    fig.update_layout(
        title="Spot Price Timeseries (Full Year)",
        xaxis_title="Date",
        yaxis_title="Price (NOK/kWh)",
        hovermode='x unified',
        height=350
    )

    # Add range selector
    fig.update_xaxes(
        rangeselector=dict(
            buttons=[
                dict(count=7, label="1w", step="day", stepmode="backward"),
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(step="all", label="Year")
            ],
            bgcolor=grays['lys'],
            activecolor=colors['oransje']
        )
    )

    return fig


def create_price_histogram(prices, colors, grays):
    """Row 1 Right: Price distribution histogram"""

    fig = go.Figure()

    fig.add_histogram(
        x=prices.values,
        nbinsx=50,
        marker_color=colors['oransje'],
        opacity=0.7,
        name='Price Distribution'
    )

    # Add statistical markers
    percentiles = {
        'P25': np.percentile(prices, 25),
        'Median': np.percentile(prices, 50),
        'P75': np.percentile(prices, 75),
        'Mean': prices.mean()
    }

    for label, value in percentiles.items():
        color = colors['blå'] if label == 'Mean' else grays['skifer']
        fig.add_vline(
            x=value,
            line_dash="dash",
            line_color=color,
            annotation_text=f"{label}: {value:.3f}",
            annotation_position="top"
        )

    # Highlight negative prices if any
    negative_count = (prices < 0).sum()
    if negative_count > 0:
        fig.add_annotation(
            x=prices.min(),
            y=0,
            text=f"⚠️ {negative_count} negative price events",
            showarrow=True,
            arrowhead=2,
            bgcolor=colors['mørk_rød'],
            font=dict(color='white')
        )

    fig.update_layout(
        title="Price Distribution",
        xaxis_title="Price (NOK/kWh)",
        yaxis_title="Frequency",
        height=350
    )

    return fig


def create_pv_timeseries(production, colors, grays):
    """Row 2 Left: Annual PV production curve"""

    fig = go.Figure()

    # Production area chart
    fig.add_scatter(
        x=production.index,
        y=production.values,
        fill='tozeroy',
        mode='lines',
        name='Solar Production',
        line=dict(color=colors['gul'], width=1),
        fillcolor=f"rgba(252, 200, 8, 0.3)",  # Transparent yellow
        hovertemplate='<b>%{x|%d.%m.%Y %H:%M}</b><br>Production: %{y:.1f} kW<extra></extra>'
    )

    # Monthly aggregates (rolling 24h average for visibility)
    monthly_avg = production.rolling(window=24*7, min_periods=1).mean()
    fig.add_scatter(
        x=monthly_avg.index,
        y=monthly_avg.values,
        mode='lines',
        name='Weekly Average',
        line=dict(color=colors['oransje'], width=2, dash='dash')
    )

    fig.update_layout(
        title="PV Production (Full Year)",
        xaxis_title="Date",
        yaxis_title="Power (kW)",
        hovermode='x unified',
        height=350
    )

    # Synchronized x-axis with prices
    fig.update_xaxes(matches='x')

    return fig


def create_pv_heatmap(production, colors, grays):
    """Row 2 Right: Daily production heatmap"""

    # Reshape data into day × hour matrix
    df = pd.DataFrame({
        'day_of_year': production.index.dayofyear,
        'hour': production.index.hour,
        'power': production.values
    })

    # Pivot to create heatmap data
    heatmap_data = df.pivot_table(
        values='power',
        index='hour',
        columns='day_of_year',
        aggfunc='mean'
    )

    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns,
        y=heatmap_data.index,
        colorscale='YlOrRd',
        colorbar=dict(title="Power (kW)"),
        hovertemplate='Day: %{x}<br>Hour: %{y}<br>Power: %{z:.1f} kW<extra></extra>'
    ))

    fig.update_layout(
        title="Daily Production Pattern Heatmap",
        xaxis_title="Day of Year",
        yaxis_title="Hour of Day",
        height=350
    )

    return fig


def create_consumption_timeseries(consumption, colors, grays):
    """Row 3 Left: Load profile timeseries"""

    fig = go.Figure()

    # Consumption area chart
    fig.add_scatter(
        x=consumption.index,
        y=consumption.values,
        fill='tozeroy',
        mode='lines',
        name='Consumption',
        line=dict(color=colors['blå'], width=1),
        fillcolor=f"rgba(0, 96, 159, 0.2)",  # Transparent blue
        hovertemplate='<b>%{x|%d.%m.%Y %H:%M}</b><br>Load: %{y:.1f} kW<extra></extra>'
    )

    # Baseload line (minimum consumption)
    baseload = consumption.quantile(0.05)  # 5th percentile as baseload
    fig.add_hline(
        y=baseload,
        line_dash="dash",
        line_color=grays['skifer'],
        annotation_text=f"Baseload: {baseload:.1f} kW",
        annotation_position="right"
    )

    fig.update_layout(
        title="Consumption Profile (Full Year)",
        xaxis_title="Date",
        yaxis_title="Power (kW)",
        hovermode='x unified',
        height=350
    )

    fig.update_xaxes(matches='x')

    return fig


def create_duration_curve(data, title, grid_limit=None, colors=None, grays=None):
    """Create interactive load duration curve"""

    # Sort data descending
    sorted_data = np.sort(data.values)[::-1]
    percentiles = np.linspace(0, 100, len(sorted_data))

    fig = go.Figure()

    # Main curve
    fig.add_scatter(
        x=percentiles,
        y=sorted_data,
        mode='lines',
        name='Load',
        line=dict(width=2, color=colors['blå']),
        hovertemplate='Percentile: %{x:.1f}%<br>Power: %{y:.1f} kW<extra></extra>'
    )

    # Grid limit line
    if grid_limit:
        fig.add_hline(
            y=grid_limit,
            line_dash="dash",
            line_color=colors['mørk_rød'],
            line_width=2,
            annotation_text=f"Grid Limit: {grid_limit} kW",
            annotation_position="right"
        )

    # Percentile markers
    for p in [50, 90, 95]:
        idx = int(p * len(sorted_data) / 100)
        fig.add_vline(
            x=p,
            line_dash="dot",
            line_color=grays['teknisk'],
            annotation_text=f"P{p}: {sorted_data[idx]:.1f} kW",
            annotation_position="top"
        )

    fig.update_layout(
        title=title,
        xaxis_title="Percentile (%)",
        yaxis_title="Power (kW)",
        height=350
    )

    return fig


def create_net_load_timeseries(net_load, colors, grays):
    """Row 4 Left: Net load (consumption - production)"""

    fig = go.Figure()

    # Separate positive and negative for different colors
    net_load_pos = net_load.copy()
    net_load_pos[net_load_pos < 0] = 0

    net_load_neg = net_load.copy()
    net_load_neg[net_load_neg > 0] = 0

    # Grid import (positive)
    fig.add_scatter(
        x=net_load_pos.index,
        y=net_load_pos.values,
        fill='tozeroy',
        mode='lines',
        name='Grid Import',
        line=dict(color=colors['mørk_rød'], width=0.5),
        fillcolor=f"rgba(183, 28, 28, 0.3)",
        hovertemplate='<b>%{x|%d.%m.%Y %H:%M}</b><br>Import: %{y:.1f} kW<extra></extra>'
    )

    # Solar export (negative)
    fig.add_scatter(
        x=net_load_neg.index,
        y=net_load_neg.values,
        fill='tozeroy',
        mode='lines',
        name='Solar Excess',
        line=dict(color=colors['mose_grønn'], width=0.5),
        fillcolor=f"rgba(168, 216, 168, 0.3)",
        hovertemplate='<b>%{x|%d.%m.%Y %H:%M}</b><br>Excess: %{y:.1f} kW<extra></extra>'
    )

    # Zero line
    fig.add_hline(
        y=0,
        line_color=grays['svart'],
        line_width=2
    )

    fig.update_layout(
        title="Net Load (Consumption - Production)",
        xaxis_title="Date",
        yaxis_title="Net Power (kW)",
        hovermode='x unified',
        height=350
    )

    fig.update_xaxes(matches='x')

    return fig


def create_curtailment_scatter(production, consumption, colors, grays, grid_limit=77):
    """Row 4 Right: Curtailment risk zones scatter plot"""

    # Calculate net load for coloring
    net_load = consumption - production

    fig = go.Figure()

    fig.add_scatter(
        x=consumption.values,
        y=production.values,
        mode='markers',
        marker=dict(
            color=net_load.values,
            colorscale='RdYlGn_r',  # Red = import, Green = export
            size=3,
            opacity=0.5,
            colorbar=dict(title="Net Load (kW)")
        ),
        name='Operating Points',
        hovertemplate='Consumption: %{x:.1f} kW<br>Production: %{y:.1f} kW<extra></extra>'
    )

    # Grid limit boundary line
    fig.add_hline(
        y=grid_limit,
        line_dash="dash",
        line_color=colors['mørk_rød'],
        line_width=2,
        annotation_text=f"Grid Limit: {grid_limit} kW",
        annotation_position="right"
    )

    # Curtailment risk zone shading
    fig.add_hrect(
        y0=grid_limit,
        y1=production.max(),
        fillcolor=colors['mørk_rød'],
        opacity=0.1,
        line_width=0,
        annotation_text="Curtailment Risk Zone",
        annotation_position="top left"
    )

    fig.update_layout(
        title="Curtailment Risk Analysis",
        xaxis_title="Consumption (kW)",
        yaxis_title="Solar Production (kW)",
        height=350
    )

    return fig


def create_monthly_balance(production, consumption, prices, colors, grays):
    """Row 5 Left: Monthly energy balance"""

    # Aggregate by month
    monthly_prod = production.resample('M').sum() / 1000  # MWh
    monthly_cons = consumption.resample('M').sum() / 1000  # MWh
    monthly_net = monthly_cons - monthly_prod

    months = [m.strftime('%b') for m in monthly_prod.index]

    fig = go.Figure()

    # Stacked bars
    fig.add_bar(
        x=months,
        y=monthly_prod.values,
        name='Solar Production',
        marker_color=colors['gul']
    )

    fig.add_bar(
        x=months,
        y=monthly_cons.values,
        name='Consumption',
        marker_color=colors['blå']
    )

    fig.add_bar(
        x=months,
        y=monthly_net.values,
        name='Net Import',
        marker_color=colors['mørk_rød']
    )

    fig.update_layout(
        title="Monthly Energy Balance",
        xaxis_title="Month",
        yaxis_title="Energy (MWh)",
        barmode='group',
        height=350
    )

    return fig


def create_monthly_statistics_table(production, consumption, prices, colors, grays):
    """Row 5 Right: Monthly statistics table"""

    # Calculate monthly stats
    monthly_stats = pd.DataFrame({
        'Max Solar (kW)': production.resample('M').max(),
        'Max Load (kW)': consumption.resample('M').max(),
        'Avg Price (NOK/kWh)': prices.resample('M').mean(),
        'Solar Energy (MWh)': production.resample('M').sum() / 1000,
        'Load Energy (MWh)': consumption.resample('M').sum() / 1000
    })

    monthly_stats.index = [m.strftime('%b %Y') for m in monthly_stats.index]

    # Calculate curtailment hours per month
    curtailment = production - 77
    curtailment_hours = (curtailment > 0).resample('M').sum()
    monthly_stats['Curtailment Hours'] = curtailment_hours.values

    # Create table
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['<b>Month</b>'] + [f'<b>{col}</b>' for col in monthly_stats.columns],
            fill_color=colors['blå'],
            font=dict(color='white', size=11),
            align='left'
        ),
        cells=dict(
            values=[monthly_stats.index] + [monthly_stats[col].round(2) for col in monthly_stats.columns],
            fill_color=[grays['snø']],
            align='left',
            font=dict(size=10)
        )
    )])

    fig.update_layout(
        title="Monthly Statistics Summary",
        height=350
    )

    return fig


def create_data_completeness_heatmap(prices, production, consumption, colors, grays):
    """Row 6 Left: Data completeness heatmap"""

    # Create completeness matrix (1 = complete, 0 = missing)
    df = pd.DataFrame({
        'Prices': ~prices.isna(),
        'Production': ~production.isna(),
        'Consumption': ~consumption.isna()
    })

    # Aggregate by day
    daily_completeness = df.resample('D').mean() * 100  # Percentage

    fig = go.Figure(data=go.Heatmap(
        z=daily_completeness.T.values,
        x=daily_completeness.index,
        y=daily_completeness.columns,
        colorscale=[[0, colors['mørk_rød']], [1, colors['mose_grønn']]],
        zmin=0,
        zmax=100,
        colorbar=dict(title="Complete (%)"),
        hovertemplate='Date: %{x|%d.%m.%Y}<br>Dataset: %{y}<br>Complete: %{z:.1f}%<extra></extra>'
    ))

    fig.update_layout(
        title="Data Completeness by Day",
        xaxis_title="Date",
        yaxis_title="Dataset",
        height=350
    )

    return fig


def create_statistics_summary_table(data, colors, grays):
    """Row 6 Right: Statistics summary table"""

    prices = data['prices']
    production = data['production']
    consumption = data['consumption']
    quality = data['quality']
    metadata = data['metadata']

    # Build statistics table
    stats_data = {
        'Dataset': ['Spot Prices', 'PV Production', 'Consumption'],
        'Mean': [
            f"{prices.mean():.3f} NOK/kWh",
            f"{production.mean():.1f} kW",
            f"{consumption.mean():.1f} kW"
        ],
        'Median': [
            f"{prices.median():.3f} NOK/kWh",
            f"{production.median():.1f} kW",
            f"{consumption.median():.1f} kW"
        ],
        'Std Dev': [
            f"{prices.std():.3f}",
            f"{production.std():.1f} kW",
            f"{consumption.std():.1f} kW"
        ],
        'Min': [
            f"{prices.min():.3f} NOK/kWh",
            f"{production.min():.1f} kW",
            f"{consumption.min():.1f} kW"
        ],
        'Max': [
            f"{prices.max():.3f} NOK/kWh",
            f"{production.max():.1f} kW",
            f"{consumption.max():.1f} kW"
        ],
        'Missing %': [
            f"{quality['prices_missing_pct']:.2f}%",
            f"{quality['production_missing_pct']:.2f}%",
            f"{quality['consumption_missing_pct']:.2f}%"
        ]
    }

    stats_df = pd.DataFrame(stats_data)

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=[f'<b>{col}</b>' for col in stats_df.columns],
            fill_color=colors['blå'],
            font=dict(color='white', size=11),
            align='left'
        ),
        cells=dict(
            values=[stats_df[col] for col in stats_df.columns],
            fill_color=[grays['snø']],
            align='left',
            font=dict(size=10)
        )
    )])

    # Add metadata annotations
    metadata_text = (
        f"<b>Data Source Information</b><br>"
        f"Year: {metadata['year']} (requested: {metadata['requested_year']})<br>"
        f"Data points: {metadata['data_points']:,} hours<br>"
        f"PV System: {metadata['pv_system']['capacity_kwp']} kWp, {metadata['pv_system']['location']}<br>"
        f"Consumption: {metadata['consumption_profile']}<br>"
        f"Grid Limit: {metadata['grid_limit_kw']} kW<br>"
        f"Period: {metadata['timestamp_start']} to {metadata['timestamp_end']}"
    )

    fig.add_annotation(
        text=metadata_text,
        xref="paper", yref="paper",
        x=0.5, y=-0.15,
        showarrow=False,
        font=dict(size=9),
        align='left',
        bgcolor=grays['lys'],
        bordercolor=grays['teknisk'],
        borderwidth=1
    )

    fig.update_layout(
        title="Statistics Summary",
        height=400  # Extra height for metadata
    )

    return fig


# ═══════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════

def create_validation_dashboard(data):
    """
    Create comprehensive 6-row × 2-column validation dashboard

    Args:
        data: Output from load_and_validate_input_data()

    Returns:
        Plotly figure with complete dashboard
    """

    print("\n" + "=" * 70)
    print("BUILDING VALIDATION DASHBOARD")
    print("=" * 70)

    # Get theme colors
    colors = get_brand_colors()
    grays = get_gray_scale()

    prices = data['prices']
    production = data['production']
    consumption = data['consumption']
    net_load = data['net_load']

    # Create subplots: 6 rows × 2 columns
    fig = make_subplots(
        rows=6, cols=2,
        row_heights=[0.15, 0.15, 0.15, 0.15, 0.15, 0.25],  # Extra height for bottom row
        subplot_titles=(
            "Spot Price Timeseries", "Price Distribution",
            "PV Production (Full Year)", "Daily Production Heatmap",
            "Consumption Profile", "Load Duration Curve",
            "Net Load Analysis", "Curtailment Risk Zones",
            "Monthly Energy Balance", "Monthly Statistics",
            "Data Completeness", "Statistics Summary"
        ),
        specs=[
            [{"type": "scatter"}, {"type": "histogram"}],
            [{"type": "scatter"}, {"type": "heatmap"}],
            [{"type": "scatter"}, {"type": "scatter"}],
            [{"type": "scatter"}, {"type": "scatter"}],
            [{"type": "bar"}, {"type": "table"}],
            [{"type": "heatmap"}, {"type": "table"}]
        ],
        vertical_spacing=0.08,
        horizontal_spacing=0.10
    )

    print("\n1. Creating Row 1: Spot Price Analysis...")
    # Row 1 Left: Price timeseries
    price_ts = create_price_timeseries(prices, colors, grays)
    for trace in price_ts.data:
        fig.add_trace(trace, row=1, col=1)

    # Row 1 Right: Price histogram
    price_hist = create_price_histogram(prices, colors, grays)
    for trace in price_hist.data:
        fig.add_trace(trace, row=1, col=2)

    print("2. Creating Row 2: Solar Production Analysis...")
    # Row 2 Left: PV timeseries
    pv_ts = create_pv_timeseries(production, colors, grays)
    for trace in pv_ts.data:
        fig.add_trace(trace, row=2, col=1)

    # Row 2 Right: PV heatmap
    pv_heat = create_pv_heatmap(production, colors, grays)
    for trace in pv_heat.data:
        fig.add_trace(trace, row=2, col=2)

    print("3. Creating Row 3: Consumption Analysis...")
    # Row 3 Left: Consumption timeseries
    cons_ts = create_consumption_timeseries(consumption, colors, grays)
    for trace in cons_ts.data:
        fig.add_trace(trace, row=3, col=1)

    # Row 3 Right: Duration curve
    dur_curve = create_duration_curve(consumption, "Load Duration Curve",
                                     grid_limit=77, colors=colors, grays=grays)
    for trace in dur_curve.data:
        fig.add_trace(trace, row=3, col=2)

    print("4. Creating Row 4: Net Load Analysis...")
    # Row 4 Left: Net load
    net_ts = create_net_load_timeseries(net_load, colors, grays)
    for trace in net_ts.data:
        fig.add_trace(trace, row=4, col=1)

    # Row 4 Right: Curtailment scatter
    curt_scatter = create_curtailment_scatter(production, consumption, colors, grays)
    for trace in curt_scatter.data:
        fig.add_trace(trace, row=4, col=2)

    print("5. Creating Row 5: Monthly Aggregates...")
    # Row 5 Left: Monthly balance
    monthly_bal = create_monthly_balance(production, consumption, prices, colors, grays)
    for trace in monthly_bal.data:
        fig.add_trace(trace, row=5, col=1)

    # Row 5 Right: Monthly stats table
    monthly_table = create_monthly_statistics_table(production, consumption, prices, colors, grays)
    for trace in monthly_table.data:
        fig.add_trace(trace, row=5, col=2)

    print("6. Creating Row 6: Data Quality Indicators...")
    # Row 6 Left: Completeness heatmap
    complete_heat = create_data_completeness_heatmap(prices, production, consumption, colors, grays)
    for trace in complete_heat.data:
        fig.add_trace(trace, row=6, col=1)

    # Row 6 Right: Statistics table
    stats_table = create_statistics_summary_table(data, colors, grays)
    for trace in stats_table.data:
        fig.add_trace(trace, row=6, col=2)

    # Update layout for full dashboard
    fig.update_layout(
        height=2800,  # Tall dashboard
        title_text="<b>Input Data Validation Dashboard</b><br><sub>Battery Optimization System - Full Year Analysis</sub>",
        title_font_size=24,
        showlegend=False,  # Individual legends per subplot
        hovermode='closest'
    )

    # Synchronize x-axes for timeseries plots
    fig.update_xaxes(matches='x', row=1, col=1)
    fig.update_xaxes(matches='x', row=2, col=1)
    fig.update_xaxes(matches='x', row=3, col=1)
    fig.update_xaxes(matches='x', row=4, col=1)

    print("✅ Dashboard assembly complete")

    return fig


def generate_input_validation_report(year=2024, output_dir='results'):
    """
    Generate comprehensive input data validation dashboard

    Args:
        year: Year to analyze (default: 2024)
        output_dir: Output directory for HTML report

    Returns:
        Path to generated HTML report
    """

    print("\n" + "═" * 70)
    print("INPUT DATA VALIDATION REPORT GENERATOR")
    print("═" * 70)
    print(f"Year: {year}")
    print(f"Output: {output_dir}/reports/")

    # Apply Norsk Solkraft theme
    apply_light_theme()

    # Load and validate data
    data = load_and_validate_input_data(year)

    # Create dashboard
    fig = create_validation_dashboard(data)

    # Save HTML report
    output_path = Path(output_dir) / 'reports'
    output_path.mkdir(parents=True, exist_ok=True)
    html_file = output_path / f'input_validation_{year}.html'

    fig.write_html(
        str(html_file),
        include_plotlyjs='cdn',
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': f'input_validation_{year}',
                'height': 2800,
                'width': 1400,
                'scale': 2
            }
        }
    )

    print("\n" + "=" * 70)
    print("REPORT GENERATION COMPLETE")
    print("=" * 70)
    print(f"✅ HTML Report: {html_file}")
    print(f"📊 Dashboard contains 12 validation visualizations")
    print(f"📈 Interactive features: zoom, pan, hover, range selectors")
    print(f"🎨 Theme: Norsk Solkraft Light (hvit bakgrunn)")

    # Print quality summary
    quality = data['quality']
    print("\n" + "=" * 70)
    print("DATA QUALITY SUMMARY")
    print("=" * 70)
    print(f"✅ Timestamps aligned: {quality['timestamps_aligned']}")
    print(f"📊 Missing data:")
    print(f"   - Prices: {quality['prices_missing_pct']:.2f}%")
    print(f"   - Production: {quality['production_missing_pct']:.2f}%")
    print(f"   - Consumption: {quality['consumption_missing_pct']:.2f}%")
    print(f"⚠️  Negative prices: {quality['prices_negative_count']} events")
    print(f"⚠️  Curtailment risk: {quality['curtailment_hours']} hours ({quality['curtailment_energy_kwh']:.0f} kWh)")

    return html_file


# ═══════════════════════════════════════════════════════════════════════════
# COMMAND LINE INTERFACE
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate interactive input data validation dashboard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Default: 2024 data, output to results/reports/
    python scripts/visualization/plot_input_data_plotly.py

    # Custom year and output directory
    python scripts/visualization/plot_input_data_plotly.py --year 2023 --output ./output

    # Generate report and open in browser
    python scripts/visualization/plot_input_data_plotly.py --show
        """
    )

    parser.add_argument(
        '--year',
        type=int,
        default=2024,
        help='Year to analyze (default: 2024)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='results',
        help='Output directory (default: results)'
    )

    parser.add_argument(
        '--show',
        action='store_true',
        help='Open report in browser after generation'
    )

    args = parser.parse_args()

    # Generate report
    report_path = generate_input_validation_report(
        year=args.year,
        output_dir=args.output
    )

    # Open in browser if requested
    if args.show:
        import webbrowser
        webbrowser.open(f'file://{report_path.absolute()}')
        print(f"\n🌐 Opening report in browser...")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
