#!/usr/bin/env python3
"""
Fikser varighetskurve-grafen:
- DC-produksjon som area graph
- Beholder AC-produksjon som linje
- Legger til makseffekt 138.55 kWp linje
- Beholder inverter og nettgrense
"""

import pickle
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Last inn resultater
print("Laster simuleringsresultater...")
with open('results/realistic_simulation_results.pkl', 'rb') as f:
    results = pickle.load(f)

# Hent systemkonfigurasjon
system_config = results.get('system_config', {})
pv_capacity = system_config.get('pv_capacity_kwp', 138.55)
inverter_capacity = system_config.get('inverter_capacity_kw', 100)
grid_limit = system_config.get('grid_limit_kw', 77)

# Lag dataframe
production_dc = np.array(results.get('production_dc', []))
production_ac = np.array(results.get('production_ac', []))

df = pd.DataFrame({
    'DC_production': production_dc,
    'AC_production': production_ac
})
df.index = pd.date_range(start='2024-01-01', periods=len(df), freq='h')

# Sorter for varighetskurve
print("Lager varighetskurve...")
dc_sorted = np.sort(df['DC_production'].values)[::-1]
ac_sorted = np.sort(df['AC_production'].values)[::-1]
hours = np.arange(len(dc_sorted))

# Lag figur
fig = go.Figure()

# DC-produksjon som area graph (filled)
fig.add_trace(go.Scatter(
    x=hours,
    y=dc_sorted,
    name='DC-produksjon',
    mode='lines',
    line=dict(color='orange', width=2),
    fill='tozeroy',
    fillcolor='rgba(255, 165, 0, 0.3)'
))

# AC-produksjon som vanlig linje
fig.add_trace(go.Scatter(
    x=hours,
    y=ac_sorted,
    name='AC-produksjon',
    mode='lines',
    line=dict(color='blue', width=2)
))

# Legg til grenselinjer
fig.add_hline(y=pv_capacity, line_dash="dash", line_color="darkorange",
               annotation_text=f"Maks DC ({pv_capacity:.1f} kWp)")

fig.add_hline(y=inverter_capacity, line_dash="dash", line_color="purple",
               annotation_text=f"Inverter ({inverter_capacity} kW)")

fig.add_hline(y=grid_limit, line_dash="dash", line_color="red",
               annotation_text=f"Nettgrense ({grid_limit} kW)")

# Oppdater layout
fig.update_layout(
    title='Varighetskurve - DC vs AC solproduksjon',
    xaxis_title='Timer i året',
    yaxis_title='Effekt (kW)',
    hovermode='x unified',
    height=500,
    template='plotly_white'
)

# Lagre
output_file = 'results/fig3_duration_curve.html'
fig.write_html(output_file)
print(f"✅ Oppdatert varighetskurve lagret: {output_file}")
print(f"   - DC-produksjon som area graph (filled)")
print(f"   - AC-produksjon som linje")
print(f"   - Maks DC effekt: {pv_capacity:.1f} kWp")
print(f"   - Inverter grense: {inverter_capacity} kW")
print(f"   - Nettgrense: {grid_limit} kW")