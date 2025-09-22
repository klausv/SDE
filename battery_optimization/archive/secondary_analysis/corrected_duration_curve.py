#!/usr/bin/env python3
"""
Corrected duration curve showing both DC and AC production
"""

import numpy as np
import plotly.graph_objects as go
import pickle

# Load the simulation results with DC tracking
with open('results/simulation_results_dc.pkl', 'rb') as f:
    results = pickle.load(f)

production_dc = results['production_dc']
production_ac = results['production_ac']

# Duration curve - sort both DC and AC production
prod_dc_sorted = np.sort(production_dc.values)[::-1]
prod_ac_sorted = np.sort(production_ac.values)[::-1]
hours = np.arange(len(prod_dc_sorted))

fig3 = go.Figure()

# Add DC production (full solar output)
fig3.add_trace(go.Scatter(
    x=hours,
    y=prod_dc_sorted,
    fill='tozeroy',
    name='DC produksjon (solceller)',
    line=dict(color='orange', width=2),
    fillcolor='rgba(255, 165, 0, 0.3)'
))

# Add AC production (after inverter)
fig3.add_trace(go.Scatter(
    x=hours,
    y=prod_ac_sorted,
    fill='tozeroy',
    name='AC produksjon (etter inverter)',
    line=dict(color='gold', width=2),
    fillcolor='rgba(255, 215, 0, 0.5)'
))

# Add capacity lines with correct colors and descriptions
fig3.add_hline(y=138.55, line_dash="dash", line_color="darkgreen",
               annotation_text="PV DC kapasitet (138.55 kWp)",
               annotation_position="right")
fig3.add_hline(y=100, line_dash="dash", line_color="blue",
               annotation_text="Inverter AC grense (100 kW)",
               annotation_position="right")
fig3.add_hline(y=77, line_dash="dash", line_color="red",
               annotation_text="Nettkapasitet (77 kW)",
               annotation_position="right")

fig3.update_layout(
    title='Varighetskurve - DC vs AC solproduksjon',
    xaxis_title='Timer i året',
    yaxis_title='Effekt (kW)',
    height=500,
    hovermode='x unified',
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01
    )
)

# Add annotations for key statistics
fig3.add_annotation(
    x=500, y=120,
    text=f"Maks DC: {production_dc.max():.1f} kW<br>" +
         f"Maks AC: {production_ac.max():.1f} kW<br>" +
         f"Timer DC>100kW: {(production_dc > 100).sum()}<br>" +
         f"Timer AC>77kW: {(production_ac > 77).sum()}",
    showarrow=False,
    bgcolor="white",
    bordercolor="black",
    borderwidth=1
)

fig3.show()

# Print summary
print("\nVARIGHETSKURVE STATISTIKK:")
print(f"Maksimal DC produksjon: {production_dc.max():.1f} kW")
print(f"Maksimal AC produksjon: {production_ac.max():.1f} kW")
print(f"Timer med DC > 100 kW (invertergrense): {(production_dc > 100).sum()} timer")
print(f"Timer med AC > 77 kW (nettgrense): {(production_ac > 77).sum()} timer")
print(f"Total DC produksjon: {production_dc.sum()/1000:.1f} MWh")
print(f"Total AC produksjon: {production_ac.sum()/1000:.1f} MWh")
print(f"Tap i inverter: {(production_dc.sum() - production_ac.sum())/1000:.1f} MWh")