"""
Interactive Plotly Visualizations for Battery Sizing Optimization
=================================================================

Provides interactive heatmaps and 3D surfaces for NPV and break-even cost
analysis with Norsk Solkraft theme integration.

Author: Claude Code
Date: 2025-01-10
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

from src.visualization.norsk_solkraft_theme import (
    apply_light_theme,
    get_brand_colors,
    COLORS,
    GRAYS
)


def plot_npv_heatmap_plotly(E_grid, P_grid, npv_grid, grid_best_E, grid_best_P,
                             powell_optimal_E, powell_optimal_P):
    """
    Interactive NPV heatmap with hover tooltips and optimal point markers.

    Args:
        E_grid: 1D array of battery capacity values [kWh]
        P_grid: 1D array of battery power values [kW]
        npv_grid: 2D array of NPV values [NOK] with shape (len(E_grid), len(P_grid))
        grid_best_E: Best E_nom from grid search [kWh]
        grid_best_P: Best P_max from grid search [kW]
        powell_optimal_E: Optimal E_nom from Powell refinement [kWh]
        powell_optimal_P: Optimal P_max from Powell refinement [kW]

    Returns:
        plotly.graph_objects.Figure
    """
    # Convert NPV to millions NOK for readability
    npv_millions = npv_grid / 1e6

    fig = go.Figure(data=go.Heatmap(
        x=P_grid,  # P_max values (columns)
        y=E_grid,  # E_nom values (rows)
        z=npv_millions,
        colorscale='RdYlGn',  # Red (negative) to Green (positive)
        hovertemplate='<b>Battery Configuration</b><br>' +
                      'Capacity: %{y:.0f} kWh<br>' +
                      'Power: %{x:.0f} kW<br>' +
                      'NPV: %{z:.2f} M NOK<br>' +
                      '<extra></extra>',
        colorbar=dict(
            title="NPV (M NOK)",
            tickformat=".2f",
            len=0.7,
            y=0.5
        ),
        zmid=0  # Center colorscale at zero (green = positive, red = negative)
    ))

    # Add contour lines at NPV intervals
    fig.add_trace(go.Contour(
        x=P_grid,
        y=E_grid,
        z=npv_millions,
        showscale=False,
        contours=dict(
            start=-1,
            end=1,
            size=0.2,  # Every 200k NOK
            showlabels=True,
            labelfont=dict(size=10, color='black')
        ),
        line=dict(color='black', width=1),
        opacity=0.4,
        hoverinfo='skip',
        name='Contour lines'
    ))

    # Highlight break-even contour (NPV = 0)
    fig.add_trace(go.Contour(
        x=P_grid,
        y=E_grid,
        z=npv_millions,
        showscale=False,
        contours=dict(
            start=0,
            end=0,
            size=1,
            showlabels=False
        ),
        line=dict(color='black', width=3),
        opacity=0.8,
        hoverinfo='skip',
        name='Break-even (NPV=0)'
    ))

    # Mark grid best point
    fig.add_trace(go.Scatter(
        x=[grid_best_P],
        y=[grid_best_E],
        mode='markers+text',
        marker=dict(
            size=18,
            color=COLORS['blå'],
            symbol='star',
            line=dict(width=2, color='white')
        ),
        text=f'Grid Best<br>{grid_best_E:.0f} kWh<br>{grid_best_P:.0f} kW',
        textposition='top center',
        textfont=dict(size=11, color=GRAYS['karbonsvart'], family='Arial'),
        name='Grid Best',
        hovertemplate='<b>Grid Search Best</b><br>' +
                      f'Capacity: {grid_best_E:.1f} kWh<br>' +
                      f'Power: {grid_best_P:.1f} kW<br>' +
                      '<extra></extra>'
    ))

    # Mark Powell optimal point
    fig.add_trace(go.Scatter(
        x=[powell_optimal_P],
        y=[powell_optimal_E],
        mode='markers+text',
        marker=dict(
            size=22,
            color=COLORS['oransje'],
            symbol='star',
            line=dict(width=2, color='white')
        ),
        text=f'Optimal<br>{powell_optimal_E:.0f} kWh<br>{powell_optimal_P:.0f} kW',
        textposition='bottom center',
        textfont=dict(size=12, color=GRAYS['karbonsvart'], family='Arial Black'),
        name='Powell Optimal',
        hovertemplate='<b>Powell Optimal</b><br>' +
                      f'Capacity: {powell_optimal_E:.1f} kWh<br>' +
                      f'Power: {powell_optimal_P:.1f} kW<br>' +
                      '<extra></extra>'
    ))

    # Apply theme and layout
    apply_light_theme(fig)

    fig.update_layout(
        title=dict(
            text="Battery Sizing Optimization - NPV Heatmap",
            font=dict(size=20)
        ),
        xaxis_title="Battery Power Rating (kW)",
        yaxis_title="Battery Capacity (kWh)",
        height=700,
        hovermode='closest'
    )

    return fig


def plot_npv_surface_plotly(E_grid, P_grid, npv_grid, powell_optimal_E, powell_optimal_P, powell_optimal_npv):
    """
    Interactive 3D NPV surface with rotation capability.

    Args:
        E_grid: 1D array of battery capacity values [kWh]
        P_grid: 1D array of battery power values [kW]
        npv_grid: 2D array of NPV values [NOK] with shape (len(E_grid), len(P_grid))
        powell_optimal_E: Optimal E_nom from Powell refinement [kWh]
        powell_optimal_P: Optimal P_max from Powell refinement [kW]
        powell_optimal_npv: Optimal NPV [NOK]

    Returns:
        plotly.graph_objects.Figure
    """
    # Convert NPV to millions NOK for readability
    npv_millions = npv_grid / 1e6

    # Create meshgrid for surface plot
    P_mesh, E_mesh = np.meshgrid(P_grid, E_grid)

    fig = go.Figure(data=go.Surface(
        x=P_mesh,
        y=E_mesh,
        z=npv_millions,
        colorscale='RdYlGn',
        hovertemplate='<b>Battery Configuration</b><br>' +
                      'Capacity: %{y:.0f} kWh<br>' +
                      'Power: %{x:.0f} kW<br>' +
                      'NPV: %{z:.2f} M NOK<br>' +
                      '<extra></extra>',
        colorbar=dict(
            title="NPV (M NOK)",
            tickformat=".2f",
            len=0.7,
            y=0.5
        ),
        opacity=0.9,
        name='NPV Surface'
    ))

    # Mark optimal point
    fig.add_trace(go.Scatter3d(
        x=[powell_optimal_P],
        y=[powell_optimal_E],
        z=[powell_optimal_npv / 1e6],
        mode='markers+text',
        marker=dict(
            size=12,
            color=COLORS['oransje'],
            symbol='diamond',
            line=dict(width=3, color='white')
        ),
        text=f'Optimal<br>{powell_optimal_E:.0f} kWh<br>{powell_optimal_P:.0f} kW<br>{powell_optimal_npv/1e6:.2f} M NOK',
        textposition='top center',
        textfont=dict(size=11, color=GRAYS['karbonsvart']),
        name='Optimal Point',
        hovertemplate='<b>Optimal Point</b><br>' +
                      f'Capacity: {powell_optimal_E:.1f} kWh<br>' +
                      f'Power: {powell_optimal_P:.1f} kW<br>' +
                      f'NPV: {powell_optimal_npv/1e6:.2f} M NOK<br>' +
                      '<extra></extra>'
    ))

    # Apply theme
    apply_light_theme(fig)

    fig.update_layout(
        title=dict(
            text="Battery Sizing Optimization - 3D NPV Surface",
            font=dict(size=20)
        ),
        scene=dict(
            xaxis_title="Power Rating (kW)",
            yaxis_title="Capacity (kWh)",
            zaxis_title="NPV (M NOK)",
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.3)
            ),
            xaxis=dict(backgroundcolor=GRAYS['lys'], gridcolor=GRAYS['silver']),
            yaxis=dict(backgroundcolor=GRAYS['lys'], gridcolor=GRAYS['silver']),
            zaxis=dict(backgroundcolor=GRAYS['lys'], gridcolor=GRAYS['silver'])
        ),
        height=800
    )

    return fig


def plot_breakeven_heatmap_plotly(E_grid, P_grid, breakeven_grid, grid_best_E, grid_best_P,
                                   powell_optimal_E, powell_optimal_P, market_cost=5000, target_cost=2500):
    """
    Interactive break-even cost heatmap with market reference lines.

    Args:
        E_grid: 1D array of battery capacity values [kWh]
        P_grid: 1D array of battery power values [kW]
        breakeven_grid: 2D array of break-even costs [NOK/kWh] with shape (len(E_grid), len(P_grid))
        grid_best_E: Best E_nom from grid search [kWh]
        grid_best_P: Best P_max from grid search [kW]
        powell_optimal_E: Optimal E_nom from Powell refinement [kWh]
        powell_optimal_P: Optimal P_max from Powell refinement [kW]
        market_cost: Current market battery cost [NOK/kWh] (default: 5000)
        target_cost: Target battery cost for viability [NOK/kWh] (default: 2500)

    Returns:
        plotly.graph_objects.Figure
    """
    fig = go.Figure(data=go.Heatmap(
        x=P_grid,
        y=E_grid,
        z=breakeven_grid,
        colorscale='Blues',  # Higher is better for break-even cost
        hovertemplate='<b>Battery Configuration</b><br>' +
                      'Capacity: %{y:.0f} kWh<br>' +
                      'Power: %{x:.0f} kW<br>' +
                      'Max viable cost: %{z:,.0f} NOK/kWh<br>' +
                      '<extra></extra>',
        colorbar=dict(
            title="Break-even Cost<br>(NOK/kWh)",
            tickformat=",.0f",
            len=0.7,
            y=0.5
        )
    ))

    # Add contour lines
    fig.add_trace(go.Contour(
        x=P_grid,
        y=E_grid,
        z=breakeven_grid,
        showscale=False,
        contours=dict(
            start=1000,
            end=6000,
            size=500,  # Every 500 NOK/kWh
            showlabels=True,
            labelfont=dict(size=10, color='black')
        ),
        line=dict(color='darkblue', width=1),
        opacity=0.3,
        hoverinfo='skip',
        name='Contour lines'
    ))

    # Highlight market cost contour
    if market_cost < breakeven_grid.max():
        fig.add_trace(go.Contour(
            x=P_grid,
            y=E_grid,
            z=breakeven_grid,
            showscale=False,
            contours=dict(
                start=market_cost,
                end=market_cost,
                size=1,
                showlabels=False
            ),
            line=dict(color=COLORS['mørk_rød'], width=3),
            opacity=0.8,
            hoverinfo='skip',
            name=f'Market Cost ({market_cost} NOK/kWh)'
        ))

    # Highlight target cost contour
    if target_cost < breakeven_grid.max():
        fig.add_trace(go.Contour(
            x=P_grid,
            y=E_grid,
            z=breakeven_grid,
            showscale=False,
            contours=dict(
                start=target_cost,
                end=target_cost,
                size=1,
                showlabels=False
            ),
            line=dict(color=COLORS['mose_grønn'], width=3),
            opacity=0.8,
            hoverinfo='skip',
            name=f'Target Cost ({target_cost} NOK/kWh)'
        ))

    # Mark grid best point
    fig.add_trace(go.Scatter(
        x=[grid_best_P],
        y=[grid_best_E],
        mode='markers',
        marker=dict(
            size=18,
            color=COLORS['blå'],
            symbol='star',
            line=dict(width=2, color='white')
        ),
        name='Grid Best',
        hovertemplate='<b>Grid Search Best</b><br>' +
                      f'Capacity: {grid_best_E:.1f} kWh<br>' +
                      f'Power: {grid_best_P:.1f} kW<br>' +
                      '<extra></extra>'
    ))

    # Mark Powell optimal point
    fig.add_trace(go.Scatter(
        x=[powell_optimal_P],
        y=[powell_optimal_E],
        mode='markers+text',
        marker=dict(
            size=22,
            color=COLORS['oransje'],
            symbol='star',
            line=dict(width=2, color='white')
        ),
        text=f'Optimal',
        textposition='bottom center',
        textfont=dict(size=12, color=GRAYS['karbonsvart'], family='Arial Black'),
        name='Powell Optimal',
        hovertemplate='<b>Powell Optimal</b><br>' +
                      f'Capacity: {powell_optimal_E:.1f} kWh<br>' +
                      f'Power: {powell_optimal_P:.1f} kW<br>' +
                      '<extra></extra>'
    ))

    # Apply theme
    apply_light_theme(fig)

    fig.update_layout(
        title=dict(
            text="Battery Sizing Optimization - Break-even Cost Heatmap",
            font=dict(size=20)
        ),
        xaxis_title="Battery Power Rating (kW)",
        yaxis_title="Battery Capacity (kWh)",
        height=700,
        hovermode='closest'
    )

    return fig


def plot_breakeven_surface_plotly(E_grid, P_grid, breakeven_grid, powell_optimal_E,
                                   powell_optimal_P, optimal_breakeven):
    """
    Interactive 3D break-even cost surface.

    Args:
        E_grid: 1D array of battery capacity values [kWh]
        P_grid: 1D array of battery power values [kW]
        breakeven_grid: 2D array of break-even costs [NOK/kWh] with shape (len(E_grid), len(P_grid))
        powell_optimal_E: Optimal E_nom from Powell refinement [kWh]
        powell_optimal_P: Optimal P_max from Powell refinement [kW]
        optimal_breakeven: Break-even cost at optimal point [NOK/kWh]

    Returns:
        plotly.graph_objects.Figure
    """
    # Create meshgrid for surface plot
    P_mesh, E_mesh = np.meshgrid(P_grid, E_grid)

    fig = go.Figure(data=go.Surface(
        x=P_mesh,
        y=E_mesh,
        z=breakeven_grid,
        colorscale='Blues',
        hovertemplate='<b>Battery Configuration</b><br>' +
                      'Capacity: %{y:.0f} kWh<br>' +
                      'Power: %{x:.0f} kW<br>' +
                      'Max viable cost: %{z:,.0f} NOK/kWh<br>' +
                      '<extra></extra>',
        colorbar=dict(
            title="Break-even Cost<br>(NOK/kWh)",
            tickformat=",.0f",
            len=0.7,
            y=0.5
        ),
        opacity=0.9,
        name='Break-even Surface'
    ))

    # Mark optimal point
    fig.add_trace(go.Scatter3d(
        x=[powell_optimal_P],
        y=[powell_optimal_E],
        z=[optimal_breakeven],
        mode='markers+text',
        marker=dict(
            size=12,
            color=COLORS['oransje'],
            symbol='diamond',
            line=dict(width=3, color='white')
        ),
        text=f'Optimal<br>{powell_optimal_E:.0f} kWh<br>{powell_optimal_P:.0f} kW<br>{optimal_breakeven:,.0f} NOK/kWh',
        textposition='top center',
        textfont=dict(size=11, color=GRAYS['karbonsvart']),
        name='Optimal Point',
        hovertemplate='<b>Optimal Point</b><br>' +
                      f'Capacity: {powell_optimal_E:.1f} kWh<br>' +
                      f'Power: {powell_optimal_P:.1f} kW<br>' +
                      f'Break-even: {optimal_breakeven:,.0f} NOK/kWh<br>' +
                      '<extra></extra>'
    ))

    # Apply theme
    apply_light_theme(fig)

    fig.update_layout(
        title=dict(
            text="Battery Sizing Optimization - 3D Break-even Cost Surface",
            font=dict(size=20)
        ),
        scene=dict(
            xaxis_title="Power Rating (kW)",
            yaxis_title="Capacity (kWh)",
            zaxis_title="Break-even Cost (NOK/kWh)",
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.3)
            ),
            xaxis=dict(backgroundcolor=GRAYS['lys'], gridcolor=GRAYS['silver']),
            yaxis=dict(backgroundcolor=GRAYS['lys'], gridcolor=GRAYS['silver']),
            zaxis=dict(backgroundcolor=GRAYS['lys'], gridcolor=GRAYS['silver'])
        ),
        height=800
    )

    return fig


def export_plotly_figures(fig, output_path, filename_base, export_png=True):
    """
    Export Plotly figure to HTML (interactive) and optionally PNG (static).

    Args:
        fig: Plotly figure object
        output_path: Path object for output directory
        filename_base: Base filename without extension (e.g., 'battery_sizing_optimization')
        export_png: If True, also export static PNG via kaleido (requires kaleido package)

    Returns:
        tuple: (html_path, png_path or None)
    """
    output_path.mkdir(exist_ok=True, parents=True)

    # Export interactive HTML
    html_path = output_path / f'{filename_base}.html'
    fig.write_html(html_path)
    print(f"✓ Saved interactive HTML: {html_path}")

    png_path = None
    if export_png:
        try:
            png_path = output_path / f'{filename_base}.png'
            fig.write_image(png_path, width=1200, height=800, scale=2)
            print(f"✓ Saved static PNG: {png_path}")
        except Exception as e:
            print(f"⚠ PNG export failed (kaleido not installed?): {e}")
            print("  Tip: Install with: pip install kaleido")

    return html_path, png_path
