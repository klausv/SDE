#!/usr/bin/env python3
"""
Fikser døgnprofil-grafen:
- Fjerner inverter og nettgrense linjer
- DC og AC produksjon som area graph
- Forbruk som line graph
"""

import pickle
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Last inn resultater
print("Laster simuleringsresultater...")
with open('results/realistic_simulation_results.pkl', 'rb') as f:
    results = pickle.load(f)

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

# Beregn gjennomsnittlig døgnprofil
print("Beregner døgnprofil...")
hourly_avg = df.groupby(df.index.hour).mean()

# Lag figur
fig = go.Figure()

# DC-produksjon som area (filled)
fig.add_trace(go.Scatter(
    x=hourly_avg.index,
    y=hourly_avg['DC_production'],
    name='DC-produksjon',
    mode='lines',
    line=dict(color='#FFA500', width=2),
    fill='tozeroy',
    fillcolor='rgba(255, 165, 0, 0.3)'
))

# AC-produksjon som area (filled)
fig.add_trace(go.Scatter(
    x=hourly_avg.index,
    y=hourly_avg['AC_production'],
    name='AC-produksjon',
    mode='lines',
    line=dict(color='#4169E1', width=2),
    fill='tozeroy',
    fillcolor='rgba(65, 105, 225, 0.3)'
))

# Forbruk som vanlig linje (IKKE filled)
fig.add_trace(go.Scatter(
    x=hourly_avg.index,
    y=hourly_avg['consumption'],
    name='Forbruk',
    mode='lines+markers',
    line=dict(color='#32CD32', width=3),
    marker=dict(size=6)
))

# Oppdater layout - INGEN grenselinjer
fig.update_layout(
    title='Gjennomsnittlig døgnprofil - DC vs AC',
    xaxis_title='Time på døgnet',
    yaxis_title='Effekt (kW)',
    hovermode='x unified',
    height=500,
    template='plotly_white',
    xaxis=dict(
        tickmode='array',
        tickvals=list(range(0, 24, 2)),
        ticktext=[f'{h:02d}:00' for h in range(0, 24, 2)]
    )
)

# Lagre
output_file = 'results/fig2_daily_profile.html'
fig.write_html(output_file)
print(f"✅ Oppdatert døgnprofil lagret: {output_file}")
print("   - DC og AC som area graphs (filled)")
print("   - Forbruk som line graph")
print("   - Fjernet inverter og nettgrense linjer")