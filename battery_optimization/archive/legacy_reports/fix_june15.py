#!/usr/bin/env python3
"""
Fikser 15. juni grafen:
- Alle produksjonsverdier som area graphs
- DC-produksjon, AC-produksjon, curtailment og levert til nett
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
grid_limit = system_config.get('grid_limit_kw', 77)
inverter_capacity = system_config.get('inverter_capacity_kw', 100)

# Lag dataframe
production_dc = np.array(results.get('production_dc', []))
production_ac = np.array(results.get('production_ac', []))
consumption = np.array(results.get('consumption', []))

df = pd.DataFrame({
    'DC_production': production_dc,
    'AC_production': production_ac,
    'consumption': consumption
})
df.index = pd.date_range(start='2024-01-01', periods=len(df), freq='h')

# Beregn curtailment og leveranse
df['grid_curtailment'] = np.maximum(0, df['AC_production'] - grid_limit)
df['delivered_to_grid'] = df['AC_production'] - df['grid_curtailment']

# Hent data for 15. juni
print("Henter data for 15. juni 2024...")
june15 = df.loc['2024-06-15']

# Lag figur
fig = go.Figure()

# DC-produksjon som area (bakgrunn)
fig.add_trace(go.Scatter(
    x=june15.index.hour,
    y=june15['DC_production'],
    name='DC-produksjon',
    mode='lines',
    line=dict(color='#FFA500', width=2),
    fill='tozeroy',
    fillcolor='rgba(255, 165, 0, 0.3)'
))

# AC-produksjon som area
fig.add_trace(go.Scatter(
    x=june15.index.hour,
    y=june15['AC_production'],
    name='AC-produksjon (total)',
    mode='lines',
    line=dict(color='#4169E1', width=2),
    fill='tozeroy',
    fillcolor='rgba(65, 105, 225, 0.3)'
))

# Levert til nett som area (grønn)
fig.add_trace(go.Scatter(
    x=june15.index.hour,
    y=june15['delivered_to_grid'],
    name='Levert til nett',
    mode='lines',
    line=dict(color='#2E8B57', width=2),
    fill='tozeroy',
    fillcolor='rgba(46, 139, 87, 0.4)'
))

# Curtailment som area (rød) - mellom delivered og AC production
fig.add_trace(go.Scatter(
    x=june15.index.hour,
    y=june15['AC_production'],
    name='Curtailment',
    mode='lines',
    line=dict(color='#DC143C', width=2),
    fill='tonexty',
    fillcolor='rgba(220, 20, 60, 0.4)',
    showlegend=True
))

# Legg til forbrukslinje for referanse
fig.add_trace(go.Scatter(
    x=june15.index.hour,
    y=june15['consumption'],
    name='Forbruk',
    mode='lines+markers',
    line=dict(color='#32CD32', width=3, dash='dash'),
    marker=dict(size=6)
))

# Legg til grenselinjer
fig.add_hline(y=grid_limit, line_dash="dash", line_color="red",
               annotation_text=f"Nettgrense ({grid_limit} kW)")

# Oppdater layout
fig.update_layout(
    title='Representativ dag - 15. juni 2024',
    xaxis_title='Time',
    yaxis_title='Effekt (kW)',
    hovermode='x unified',
    height=500,
    template='plotly_white',
    xaxis=dict(
        tickmode='array',
        tickvals=list(range(0, 24, 2)),
        ticktext=[f'{h:02d}:00' for h in range(0, 24, 2)]
    ),
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01
    )
)

# Lagre
output_file = 'results/fig6_june15.html'
fig.write_html(output_file)
print(f"✅ Oppdatert 15. juni graf lagret: {output_file}")
print("   - DC-produksjon: Area graph (oransje)")
print("   - AC-produksjon: Area graph (blå)")
print("   - Levert til nett: Area graph (grønn)")
print("   - Curtailment: Area graph (rød)")
print("   - Forbruk: Linje (grønn stiplet)")
print(f"   - Maks curtailment: {june15['grid_curtailment'].max():.1f} kW")