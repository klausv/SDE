#!/usr/bin/env python3
"""
3D Break-Even Battery Cost Visualization with Powell Optimization Result

Plots break-even battery costs across battery size (E_nom) and power (P_max),
with the Powell-optimized point highlighted.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import json
from pathlib import Path

# Paths
results_dir = Path(__file__).parent / 'results' / 'battery_dimensioning_PT60M'
grid_results_file = results_dir / 'grid_search_results.csv'
powell_results_file = results_dir / 'powell_refinement_results.json'
output_file = results_dir / 'plots' / 'breakeven_3d_with_powell.png'

# Create output directory
output_file.parent.mkdir(parents=True, exist_ok=True)

print("="*70)
print("3D BREAK-EVEN BATTERY COST VISUALIZATION")
print("="*70)

# Load grid search results
print(f"\nLoading grid search results from: {grid_results_file}")
df = pd.read_csv(grid_results_file)
print(f"  Loaded {len(df)} grid search points")

# Load Powell results
print(f"\nLoading Powell refinement results from: {powell_results_file}")
with open(powell_results_file, 'r') as f:
    powell = json.load(f)

print(f"\n  Powell Optimal Point:")
print(f"    E_nom: {powell['optimal_E_nom_kwh']:.2f} kWh")
print(f"    P_max: {powell['optimal_P_max_kw']:.2f} kW")
print(f"    NPV: {powell['optimal_npv_nok']:,.0f} NOK")
print(f"    Break-even cost: {powell['breakeven_cost_per_kwh']:,.0f} NOK/kWh")
print(f"    Annual savings: {powell['annual_savings_nok']:,.0f} NOK/year")

# Calculate break-even cost for grid points
# Break-even: NPV = 0
# NPV = -CAPEX + PV(annual_savings)
# At break-even: CAPEX = PV(annual_savings)
# CAPEX = E_nom * cost_per_kwh
# So: cost_per_kwh = PV(annual_savings) / E_nom

# Assuming same discount rate and lifetime as Powell
discount_rate = 0.05  # 5%
lifetime_years = 15

# Calculate present value factor
pv_factor = sum(1 / (1 + discount_rate)**year for year in range(1, lifetime_years + 1))

# Calculate break-even cost per kWh for each grid point
df['pv_savings'] = df['annual_savings_nok'] * pv_factor
df['breakeven_cost_per_kwh'] = df['pv_savings'] / df['E_nom_kwh']

print(f"\nGrid Search Break-even Cost Range:")
print(f"  Min: {df['breakeven_cost_per_kwh'].min():,.0f} NOK/kWh")
print(f"  Max: {df['breakeven_cost_per_kwh'].max():,.0f} NOK/kWh")
print(f"  Mean: {df['breakeven_cost_per_kwh'].mean():,.0f} NOK/kWh")

# Get unique E and P values for grid
E_unique = sorted(df['E_nom_kwh'].unique())
P_unique = sorted(df['P_max_kw'].unique())

print(f"\nGrid dimensions:")
print(f"  E_nom range: {E_unique[0]:.0f} - {E_unique[-1]:.0f} kWh ({len(E_unique)} points)")
print(f"  P_max range: {P_unique[0]:.0f} - {P_unique[-1]:.0f} kW ({len(P_unique)} points)")

# Create meshgrid
E_grid = np.array(E_unique)
P_grid = np.array(P_unique)
E_mesh, P_mesh = np.meshgrid(E_grid, P_grid)

# Reshape break-even costs to match meshgrid
breakeven_grid = df.pivot_table(
    values='breakeven_cost_per_kwh',
    index='P_max_kw',
    columns='E_nom_kwh'
).values

# Create 3D plot
print("\nCreating 3D visualization...")
fig = plt.figure(figsize=(16, 12))
ax = fig.add_subplot(111, projection='3d')

# Plot surface
surf = ax.plot_surface(
    E_mesh, P_mesh, breakeven_grid,
    cmap='viridis',
    alpha=0.7,
    edgecolor='none',
    linewidth=0,
    antialiased=True
)

# Add wireframe for better depth perception
ax.plot_wireframe(
    E_mesh, P_mesh, breakeven_grid,
    color='gray',
    alpha=0.2,
    linewidth=0.5
)

# Plot Powell optimal point
ax.scatter(
    [powell['optimal_E_nom_kwh']],
    [powell['optimal_P_max_kw']],
    [powell['breakeven_cost_per_kwh']],
    color='red',
    s=300,
    marker='*',
    edgecolors='darkred',
    linewidths=2,
    label=f"Powell Optimal\n({powell['optimal_E_nom_kwh']:.1f} kWh, {powell['optimal_P_max_kw']:.1f} kW)\n{powell['breakeven_cost_per_kwh']:.0f} NOK/kWh",
    zorder=100
)

# Add vertical line from Powell point to surface
ax.plot(
    [powell['optimal_E_nom_kwh'], powell['optimal_E_nom_kwh']],
    [powell['optimal_P_max_kw'], powell['optimal_P_max_kw']],
    [0, powell['breakeven_cost_per_kwh']],
    'r--',
    linewidth=2,
    alpha=0.6
)

# Find grid search best point
best_grid_idx = df['npv_nok'].idxmax()
best_grid = df.loc[best_grid_idx]

ax.scatter(
    [best_grid['E_nom_kwh']],
    [best_grid['P_max_kw']],
    [best_grid['breakeven_cost_per_kwh']],
    color='orange',
    s=200,
    marker='o',
    edgecolors='darkorange',
    linewidths=2,
    label=f"Grid Search Best\n({best_grid['E_nom_kwh']:.0f} kWh, {best_grid['P_max_kw']:.0f} kW)\n{best_grid['breakeven_cost_per_kwh']:.0f} NOK/kWh",
    zorder=99
)

# Labels and title
ax.set_xlabel('Battery Capacity (kWh)', fontsize=12, fontweight='bold', labelpad=10)
ax.set_ylabel('Battery Power (kW)', fontsize=12, fontweight='bold', labelpad=10)
ax.set_zlabel('Break-Even Cost (NOK/kWh)', fontsize=12, fontweight='bold', labelpad=10)

ax.set_title(
    'Battery Break-Even Cost: 3D Landscape with Powell Optimization\n'
    f'Discount Rate: {discount_rate*100:.0f}%, Lifetime: {lifetime_years} years',
    fontsize=14,
    fontweight='bold',
    pad=20
)

# Colorbar
cbar = fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, pad=0.1)
cbar.set_label('Break-Even Cost (NOK/kWh)', fontsize=11, fontweight='bold')

# Legend
ax.legend(loc='upper left', fontsize=10, framealpha=0.9)

# View angle for better visualization
ax.view_init(elev=20, azim=45)

# Grid
ax.grid(True, alpha=0.3)

# Add text box with key metrics
textstr = (
    f'Powell Improvement:\n'
    f'  NPV: {powell["npv_improvement_nok"]:,.0f} NOK\n'
    f'  vs Grid Best: {powell["npv_improvement_percent"]:.1f}%\n'
    f'\n'
    f'Market Cost: 5,000 NOK/kWh\n'
    f'Powell Break-even: {powell["breakeven_cost_per_kwh"]:,.0f} NOK/kWh\n'
    f'Gap: {5000 - powell["breakeven_cost_per_kwh"]:,.0f} NOK/kWh'
)

props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
ax.text2D(
    0.02, 0.98,
    textstr,
    transform=ax.transAxes,
    fontsize=9,
    verticalalignment='top',
    bbox=props,
    family='monospace'
)

plt.tight_layout()

# Save figure
print(f"\nSaving figure to: {output_file}")
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"✓ Saved: {output_file}")

# Also create a contour plot view
print("\nCreating contour plot...")
fig2, ax2 = plt.subplots(figsize=(12, 9))

# Contour plot
contour = ax2.contourf(E_mesh, P_mesh, breakeven_grid, levels=20, cmap='viridis', alpha=0.8)
contour_lines = ax2.contour(E_mesh, P_mesh, breakeven_grid, levels=10, colors='black', alpha=0.3, linewidths=0.5)
ax2.clabel(contour_lines, inline=True, fontsize=8, fmt='%0.0f')

# Plot points
ax2.scatter(
    df['E_nom_kwh'], df['P_max_kw'],
    c=df['breakeven_cost_per_kwh'],
    cmap='viridis',
    s=100,
    edgecolors='black',
    linewidths=0.5,
    alpha=0.6
)

# Powell optimal
ax2.scatter(
    powell['optimal_E_nom_kwh'],
    powell['optimal_P_max_kw'],
    color='red',
    s=500,
    marker='*',
    edgecolors='darkred',
    linewidths=2,
    label=f"Powell Optimal: {powell['breakeven_cost_per_kwh']:.0f} NOK/kWh",
    zorder=100
)

# Grid search best
ax2.scatter(
    best_grid['E_nom_kwh'],
    best_grid['P_max_kw'],
    color='orange',
    s=300,
    marker='o',
    edgecolors='darkorange',
    linewidths=2,
    label=f"Grid Best: {best_grid['breakeven_cost_per_kwh']:.0f} NOK/kWh",
    zorder=99
)

# Labels
ax2.set_xlabel('Battery Capacity (kWh)', fontsize=12, fontweight='bold')
ax2.set_ylabel('Battery Power (kW)', fontsize=12, fontweight='bold')
ax2.set_title(
    'Battery Break-Even Cost: Contour Map\n'
    f'Discount Rate: {discount_rate*100:.0f}%, Lifetime: {lifetime_years} years',
    fontsize=14,
    fontweight='bold',
    pad=15
)

# Colorbar
cbar2 = plt.colorbar(contour, ax=ax2)
cbar2.set_label('Break-Even Cost (NOK/kWh)', fontsize=11, fontweight='bold')

# Legend
ax2.legend(loc='upper right', fontsize=10, framealpha=0.9)

# Grid
ax2.grid(True, alpha=0.3, linestyle='--')

plt.tight_layout()

# Save contour plot
output_file2 = results_dir / 'plots' / 'breakeven_contour_with_powell.png'
print(f"Saving contour plot to: {output_file2}")
plt.savefig(output_file2, dpi=300, bbox_inches='tight')
print(f"✓ Saved: {output_file2}")

print("\n" + "="*70)
print("VISUALIZATION COMPLETE")
print("="*70)
print(f"\nGenerated files:")
print(f"  1. {output_file}")
print(f"  2. {output_file2}")
print("\nKey Finding:")
print(f"  Powell optimal break-even: {powell['breakeven_cost_per_kwh']:,.0f} NOK/kWh")
print(f"  Current market price: 5,000 NOK/kWh")
print(f"  Required cost reduction: {((5000 - powell['breakeven_cost_per_kwh'])/5000)*100:.1f}%")
print("="*70)

plt.show()
