"""
Test script for interactive Plotly battery sizing visualizations.

This script generates sample data to test the new Plotly visualization functions
without running the full optimization (which takes ~15 minutes).

Author: Claude Code
Date: 2025-01-10
"""

import numpy as np
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.visualization.battery_sizing_plotly import (
    plot_npv_heatmap_plotly,
    plot_npv_surface_plotly,
    plot_breakeven_heatmap_plotly,
    plot_breakeven_surface_plotly,
    export_plotly_figures
)


def generate_sample_data():
    """
    Generate realistic sample data for testing visualizations.

    Returns NPV and break-even cost grids similar to actual optimization results.
    """
    print("Generating sample data...")

    # Battery dimension ranges (similar to actual optimization)
    E_grid = np.linspace(10, 200, 10)  # 10-200 kWh
    P_grid = np.linspace(10, 100, 10)  # 10-100 kW

    # Create meshgrid
    E_mesh, P_mesh = np.meshgrid(E_grid, P_grid, indexing='ij')

    # Simulate NPV surface (realistic shape with optimal around 80-100 kWh, 40-60 kW)
    # NPV formula: Peaks around E=90 kWh, P=50 kW with negative values at extremes
    E_optimal = 90
    P_optimal = 50

    # Gaussian-like peak with asymmetry
    npv_grid = np.zeros_like(E_mesh)
    for i in range(len(E_grid)):
        for j in range(len(P_grid)):
            E = E_grid[i]
            P = P_grid[j]

            # Distance from optimal point (weighted)
            E_dist = ((E - E_optimal) / 50) ** 2
            P_dist = ((P - P_optimal) / 30) ** 2

            # Base NPV with realistic magnitude
            base_npv = 500000 * np.exp(-(E_dist + P_dist))

            # Subtract investment cost (increases with E and P)
            investment_cost = 3000 * E + 1500 * P + 50000

            # Annual savings (increases with E and P, but with diminishing returns)
            annual_savings = 50000 * (1 - np.exp(-E / 100)) * (1 - np.exp(-P / 50))

            # NPV over 15 years (5% discount)
            pv_factor = 10.38  # Sum of discount factors for 15 years @ 5%
            npv = -investment_cost + annual_savings * pv_factor

            npv_grid[i, j] = npv

    # Simulate break-even cost grid (inversely related to NPV)
    # Break-even cost = (annual_savings * pv_factor) / E_nom
    breakeven_grid = np.zeros_like(E_mesh)
    for i in range(len(E_grid)):
        for j in range(len(P_grid)):
            E = E_grid[i]
            P = P_grid[j]

            # Annual savings (same formula as above)
            annual_savings = 50000 * (1 - np.exp(-E / 100)) * (1 - np.exp(-P / 50))

            # Break-even cost per kWh
            pv_factor = 10.38
            breakeven_cost = (annual_savings * pv_factor) / E if E > 0 else 0

            breakeven_grid[i, j] = breakeven_cost

    # Find optimal points
    optimal_idx = np.unravel_index(np.argmax(npv_grid), npv_grid.shape)
    grid_best_E = E_grid[optimal_idx[0]]
    grid_best_P = P_grid[optimal_idx[1]]
    grid_best_npv = npv_grid[optimal_idx]

    # Simulate Powell refinement (slightly different from grid best)
    powell_optimal_E = grid_best_E + 5
    powell_optimal_P = grid_best_P + 3
    powell_optimal_npv = grid_best_npv + 10000  # Slightly better

    print(f"✓ Sample data generated:")
    print(f"  E_grid: {E_grid.min():.0f} - {E_grid.max():.0f} kWh ({len(E_grid)} points)")
    print(f"  P_grid: {P_grid.min():.0f} - {P_grid.max():.0f} kW ({len(P_grid)} points)")
    print(f"  Grid best: E={grid_best_E:.1f} kWh, P={grid_best_P:.1f} kW, NPV={grid_best_npv:,.0f} NOK")
    print(f"  Powell optimal: E={powell_optimal_E:.1f} kWh, P={powell_optimal_P:.1f} kW, NPV={powell_optimal_npv:,.0f} NOK")

    return {
        'E_grid': E_grid,
        'P_grid': P_grid,
        'npv_grid': npv_grid,
        'breakeven_grid': breakeven_grid,
        'grid_best_E': grid_best_E,
        'grid_best_P': grid_best_P,
        'grid_best_npv': grid_best_npv,
        'powell_optimal_E': powell_optimal_E,
        'powell_optimal_P': powell_optimal_P,
        'powell_optimal_npv': powell_optimal_npv
    }


def main():
    """Test all Plotly visualization functions"""

    print("="*70)
    print("Testing Interactive Plotly Battery Sizing Visualizations")
    print("="*70)

    # Generate sample data
    data = generate_sample_data()

    # Output directory
    output_dir = Path(__file__).parent / 'test_results'
    output_dir.mkdir(exist_ok=True)

    print("\n" + "="*70)
    print("Generating Visualizations")
    print("="*70)

    # 1. NPV Heatmap (2D)
    print("\n1. NPV Heatmap (2D interactive)...")
    fig_npv_2d = plot_npv_heatmap_plotly(
        E_grid=data['E_grid'],
        P_grid=data['P_grid'],
        npv_grid=data['npv_grid'],
        grid_best_E=data['grid_best_E'],
        grid_best_P=data['grid_best_P'],
        powell_optimal_E=data['powell_optimal_E'],
        powell_optimal_P=data['powell_optimal_P']
    )

    html_path, png_path = export_plotly_figures(
        fig=fig_npv_2d,
        output_path=output_dir,
        filename_base='test_battery_sizing_npv_heatmap',
        export_png=False  # Set to True if kaleido is installed
    )

    # 2. NPV 3D Surface
    print("\n2. NPV 3D Surface...")
    fig_npv_3d = plot_npv_surface_plotly(
        E_grid=data['E_grid'],
        P_grid=data['P_grid'],
        npv_grid=data['npv_grid'],
        powell_optimal_E=data['powell_optimal_E'],
        powell_optimal_P=data['powell_optimal_P'],
        powell_optimal_npv=data['powell_optimal_npv']
    )

    html_path, png_path = export_plotly_figures(
        fig=fig_npv_3d,
        output_path=output_dir,
        filename_base='test_battery_sizing_npv_3d',
        export_png=False
    )

    # 3. Break-even Cost Heatmap (2D)
    print("\n3. Break-even Cost Heatmap (2D interactive)...")
    fig_breakeven_2d = plot_breakeven_heatmap_plotly(
        E_grid=data['E_grid'],
        P_grid=data['P_grid'],
        breakeven_grid=data['breakeven_grid'],
        grid_best_E=data['grid_best_E'],
        grid_best_P=data['grid_best_P'],
        powell_optimal_E=data['powell_optimal_E'],
        powell_optimal_P=data['powell_optimal_P'],
        market_cost=5000,
        target_cost=2500
    )

    html_path, png_path = export_plotly_figures(
        fig=fig_breakeven_2d,
        output_path=output_dir,
        filename_base='test_battery_sizing_breakeven_heatmap',
        export_png=False
    )

    # 4. Break-even Cost 3D Surface
    print("\n4. Break-even Cost 3D Surface...")

    # Find break-even at optimal point
    P_idx = np.argmin(np.abs(data['P_grid'] - data['powell_optimal_P']))
    E_idx = np.argmin(np.abs(data['E_grid'] - data['powell_optimal_E']))
    optimal_breakeven = data['breakeven_grid'][E_idx, P_idx]

    fig_breakeven_3d = plot_breakeven_surface_plotly(
        E_grid=data['E_grid'],
        P_grid=data['P_grid'],
        breakeven_grid=data['breakeven_grid'],
        powell_optimal_E=data['powell_optimal_E'],
        powell_optimal_P=data['powell_optimal_P'],
        optimal_breakeven=optimal_breakeven
    )

    html_path, png_path = export_plotly_figures(
        fig=fig_breakeven_3d,
        output_path=output_dir,
        filename_base='test_battery_sizing_breakeven_3d',
        export_png=False
    )

    print("\n" + "="*70)
    print("Test Complete!")
    print("="*70)
    print(f"\nInteractive HTML files saved to: {output_dir}")
    print("\nOpen the HTML files in a web browser to explore:")
    print(f"  - test_battery_sizing_npv_heatmap.html")
    print(f"  - test_battery_sizing_npv_3d.html")
    print(f"  - test_battery_sizing_breakeven_heatmap.html")
    print(f"  - test_battery_sizing_breakeven_3d.html")
    print("\nInteractive features:")
    print("  - Hover over heatmap/surface to see detailed values")
    print("  - Rotate 3D surfaces by clicking and dragging")
    print("  - Zoom in/out with scroll wheel")
    print("  - Click legend items to show/hide traces")
    print("  - Use toolbar buttons (top-right) to save, zoom, pan, etc.")


if __name__ == '__main__':
    main()
