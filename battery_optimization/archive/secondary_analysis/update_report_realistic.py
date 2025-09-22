#!/usr/bin/env python3
"""
Oppdater Jupyter-rapporten med realistiske data
"""

import pickle
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Last realistisk simuleringsdata
with open('results/realistic_simulation_results.pkl', 'rb') as f:
    results = pickle.load(f)

production_dc = results['production_dc']
production_ac = results['production_ac']
consumption = results['consumption']
base_results = results['base_results']
optimization_results = results['optimization_results']

print("=== OPPDATERER RAPPORT MED REALISTISKE DATA ===")
print(f"Datakilde: PVGIS timesverdier for Stavanger")
print(f"DC produksjon: {production_dc.sum()/1000:.1f} MWh/år")
print(f"AC produksjon: {production_ac.sum()/1000:.1f} MWh/år")
print(f"Forbruk: {consumption.sum()/1000:.1f} MWh/år")

# 1. VARIGHETSKURVE - DC vs AC
print("\n1. Lager varighetskurve DC vs AC...")
prod_dc_sorted = np.sort(production_dc.values)[::-1]
prod_ac_sorted = np.sort(production_ac.values)[::-1]
hours = np.arange(len(prod_dc_sorted))

fig_duration = go.Figure()

# DC produksjon (oransje)
fig_duration.add_trace(go.Scatter(
    x=hours,
    y=prod_dc_sorted,
    fill='tozeroy',
    name='DC produksjon (solceller)',
    line=dict(color='orange', width=2),
    fillcolor='rgba(255, 165, 0, 0.3)'
))

# AC produksjon (gul)
fig_duration.add_trace(go.Scatter(
    x=hours,
    y=prod_ac_sorted,
    fill='tozeroy',
    name='AC produksjon (etter inverter)',
    line=dict(color='gold', width=2),
    fillcolor='rgba(255, 215, 0, 0.5)'
))

# Kapasitetsgrenser
fig_duration.add_hline(y=138.55, line_dash="dash", line_color="darkgreen",
                       annotation_text="PV DC kapasitet (138.55 kWp)")
fig_duration.add_hline(y=100, line_dash="dash", line_color="blue",
                       annotation_text="Inverter AC (100 kW)")
fig_duration.add_hline(y=77, line_dash="dash", line_color="red",
                       annotation_text="Nettkapasitet (77 kW)")

fig_duration.update_layout(
    title='Varighetskurve - DC vs AC solproduksjon (PVGIS data)',
    xaxis_title='Timer i året',
    yaxis_title='Effekt (kW)',
    height=500
)

# 2. DØGNPROFILER - Realistiske
print("2. Lager realistiske døgnprofiler...")

# Gjennomsnittlig døgnprofil for sommer og vinter
summer_mask = production_dc.index.month.isin([6, 7, 8])
winter_mask = production_dc.index.month.isin([12, 1, 2])

summer_prod_hourly = production_dc[summer_mask].groupby(production_dc.index[summer_mask].hour).mean()
winter_prod_hourly = production_dc[winter_mask].groupby(production_dc.index[winter_mask].hour).mean()

# Forbruksprofil ukedag vs helg
weekday_mask = consumption.index.weekday < 5
weekend_mask = consumption.index.weekday >= 5

weekday_cons_hourly = consumption[weekday_mask].groupby(consumption.index[weekday_mask].hour).mean()
weekend_cons_hourly = consumption[weekend_mask].groupby(consumption.index[weekend_mask].hour).mean()

fig_daily = make_subplots(
    rows=1, cols=2,
    subplot_titles=['Solproduksjon - Døgnprofil', 'Forbruk - Døgnprofil']
)

# Produksjon
fig_daily.add_trace(
    go.Scatter(x=list(range(24)), y=summer_prod_hourly.values,
               name='Sommer DC', line=dict(color='orange', width=2)),
    row=1, col=1
)
fig_daily.add_trace(
    go.Scatter(x=list(range(24)), y=winter_prod_hourly.values,
               name='Vinter DC', line=dict(color='blue', width=2)),
    row=1, col=1
)

# Forbruk
fig_daily.add_trace(
    go.Scatter(x=list(range(24)), y=weekday_cons_hourly.values,
               name='Ukedager', line=dict(color='red', width=2)),
    row=1, col=2
)
fig_daily.add_trace(
    go.Scatter(x=list(range(24)), y=weekend_cons_hourly.values,
               name='Helg', line=dict(color='green', width=2)),
    row=1, col=2
)

fig_daily.update_xaxes(title_text="Time på døgnet", row=1, col=1)
fig_daily.update_xaxes(title_text="Time på døgnet", row=1, col=2)
fig_daily.update_yaxes(title_text="Effekt (kW)", row=1, col=1)
fig_daily.update_yaxes(title_text="Forbruk (kW)", row=1, col=2)

fig_daily.update_layout(height=400, title_text="Realistiske døgnprofiler (PVGIS + kommersielt forbruk)")

# 3. MÅNEDLIG FORDELING
print("3. Lager månedlig fordeling...")
monthly_dc = production_dc.resample('ME').sum() / 1000
monthly_ac = production_ac.resample('ME').sum() / 1000
monthly_consumption = consumption.resample('ME').sum() / 1000
monthly_curtailment = base_results['grid_curtailment'].resample('ME').sum() / 1000

months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']

fig_monthly = go.Figure()

fig_monthly.add_trace(go.Bar(
    x=months, y=monthly_dc.values[:12],
    name='DC produksjon',
    marker_color='orange',
    opacity=0.8
))

fig_monthly.add_trace(go.Bar(
    x=months, y=monthly_ac.values[:12],
    name='AC produksjon',
    marker_color='gold'
))

fig_monthly.add_trace(go.Bar(
    x=months, y=monthly_consumption.values[:12],
    name='Forbruk',
    marker_color='lightblue'
))

fig_monthly.add_trace(go.Bar(
    x=months, y=monthly_curtailment.values[:12],
    name='Curtailment',
    marker_color='red'
))

fig_monthly.update_layout(
    title='Månedlig energibalanse (PVGIS data)',
    xaxis_title='Måned',
    yaxis_title='Energi (MWh)',
    barmode='group',
    height=500
)

# Lagre alle figurer
print("\n4. Lagrer figurer...")
fig_duration.write_html('results/duration_curve_realistic.html')
fig_daily.write_html('results/daily_profiles_realistic.html')
fig_monthly.write_html('results/monthly_balance_realistic.html')

# Oppsummering
print("\n=== VIKTIGE FORSKJELLER MED REALISTISKE DATA ===")
print(f"Optimal batteristørrelse: 10 kWh (vs 80-100 kWh med syntetiske data)")
print(f"DC produksjon: {production_dc.sum()/1000:.1f} MWh (PVGIS)")
print(f"Invertertap: {(production_dc.sum() - production_ac.sum())/1000:.1f} MWh")
print(f"Curtailment: {base_results['grid_curtailment'].sum()/1000:.1f} MWh")
print(f"Forbruk variasjon: {consumption.min():.1f} - {consumption.max():.1f} kW")
print(f"Produksjon variasjon: 0 - {production_dc.max():.1f} kW")

print("\n✅ Rapporten kan nå oppdateres med realistiske grafer!")