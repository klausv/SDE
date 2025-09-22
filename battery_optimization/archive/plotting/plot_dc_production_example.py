#!/usr/bin/env python3
"""
Example of plotting DC production vs AC production with curtailment
"""

import pickle
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Load the new simulation results with DC tracking
with open('results/simulation_results_dc.pkl', 'rb') as f:
    results = pickle.load(f)

production_dc = results['production_dc']
production_ac = results['production_ac']
inverter_clipping = results['inverter_clipping']
base_results = results['base_results']

# Create duration curves showing all components
prod_dc_sorted = np.sort(production_dc.values)[::-1]
prod_ac_sorted = np.sort(production_ac.values)[::-1]
hours = np.arange(len(prod_dc_sorted))

# Create figure with subplots
fig = make_subplots(
    rows=2, cols=1,
    subplot_titles=['Varighetskurve - Full DC produksjon vs AC etter inverter',
                    'Månedlig produksjon og tap'],
    vertical_spacing=0.15,
    row_heights=[0.6, 0.4]
)

# Duration curve
fig.add_trace(
    go.Scatter(x=hours, y=prod_dc_sorted, fill='tozeroy',
               name='DC produksjon (før inverter)',
               line=dict(color='orange', width=2)),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(x=hours, y=prod_ac_sorted, fill='tozeroy',
               name='AC produksjon (etter inverter)',
               line=dict(color='gold', width=2)),
    row=1, col=1
)

# Add capacity lines
fig.add_hline(y=138.55, line_dash="dash", line_color="red",
              annotation_text="PV DC kapasitet (138.55 kWp)",
              row=1, col=1)
fig.add_hline(y=100, line_dash="dash", line_color="blue",
              annotation_text="Inverter AC (100 kW)",
              row=1, col=1)
fig.add_hline(y=77, line_dash="dash", line_color="green",
              annotation_text="Nettkapasitet (77 kW)",
              row=1, col=1)

# Monthly analysis
monthly_dc = production_dc.resample('ME').sum() / 1000  # MWh
monthly_ac = production_ac.resample('ME').sum() / 1000  # MWh
monthly_inverter_clip = inverter_clipping.resample('ME').sum() / 1000  # MWh
monthly_grid_curt = base_results['grid_curtailment'].resample('ME').sum() / 1000  # MWh

months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']

fig.add_trace(
    go.Bar(x=months, y=monthly_dc.values, name='DC produksjon',
           marker_color='orange', opacity=0.7),
    row=2, col=1
)

fig.add_trace(
    go.Bar(x=months, y=monthly_ac.values, name='AC produksjon',
           marker_color='gold'),
    row=2, col=1
)

fig.add_trace(
    go.Bar(x=months, y=-monthly_inverter_clip.values, name='Inverter clipping',
           marker_color='red'),
    row=2, col=1
)

fig.add_trace(
    go.Bar(x=months, y=-monthly_grid_curt.values, name='Grid curtailment',
           marker_color='darkred'),
    row=2, col=1
)

# Update layout
fig.update_xaxes(title_text="Timer i året", row=1, col=1)
fig.update_xaxes(title_text="Måned", row=2, col=1)
fig.update_yaxes(title_text="Effekt (kW)", row=1, col=1)
fig.update_yaxes(title_text="Energi (MWh)", row=2, col=1)

fig.update_layout(
    height=800,
    title_text="DC vs AC Produksjonsanalyse - Snødevegen 122",
    showlegend=True,
    hovermode='x unified'
)

# Show the plot
fig.show()

# Print summary statistics
print("\n=== Produksjonsanalyse ===")
print(f"Maksimal DC produksjon: {production_dc.max():.1f} kW")
print(f"Maksimal AC produksjon: {production_ac.max():.1f} kW")
print(f"Total årlig DC produksjon: {production_dc.sum()/1000:.1f} MWh")
print(f"Total årlig AC produksjon: {production_ac.sum()/1000:.1f} MWh")
print(f"Tap i inverter (clipping): {inverter_clipping.sum()/1000:.1f} MWh ({inverter_clipping.sum()/production_dc.sum()*100:.1f}%)")
print(f"Tap i nett (curtailment): {base_results['grid_curtailment'].sum()/1000:.1f} MWh")
print(f"Totale tap: {(inverter_clipping.sum() + base_results['grid_curtailment'].sum())/1000:.1f} MWh")