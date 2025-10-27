#!/usr/bin/env python3
"""
Plott månedlig produksjon, forbruk og curtailment
"""

import json
import pickle
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Last inn resultater
print("Laster simuleringsresultater...")
with open('results/realistic_simulation_results.pkl', 'rb') as f:
    results = pickle.load(f)

# Hent systemkonfigurasjon
system_config = results.get('system_config', {})
pv_capacity = system_config.get('pv_capacity_kwp', 138.55)
inverter_capacity = system_config.get('inverter_capacity_kw', 100)
grid_limit = system_config.get('grid_limit_kw', 77)

# Lag dataframe fra resultatene
production_dc = np.array(results.get('production_dc', []))
production_ac = np.array(results.get('production_ac', []))
consumption = np.array(results.get('consumption', []))

# Opprett DataFrame
df = pd.DataFrame({
    'DC_production': production_dc,
    'AC_production': production_ac,
    'consumption': consumption
})
df.index = pd.date_range(start='2024-01-01', periods=len(df), freq='h')

# Beregn tap og curtailment
df['inverter_clipping'] = np.maximum(0, df['DC_production'] - inverter_capacity)
df['grid_curtailment'] = np.maximum(0, df['AC_production'] - grid_limit)
df['delivered_to_grid'] = df['AC_production'] - df['grid_curtailment']

# Aggreger månedlig
monthly = df.resample('ME').agg({
    'DC_production': 'sum',
    'AC_production': 'sum',
    'delivered_to_grid': 'sum',
    'consumption': 'sum',
    'inverter_clipping': 'sum',
    'grid_curtailment': 'sum'
})

# Konverter til MWh for bedre lesbarhet
monthly = monthly / 1000

# Norske månedsnavn
months_no = ['Januar', 'Februar', 'Mars', 'April', 'Mai', 'Juni',
             'Juli', 'August', 'September', 'Oktober', 'November', 'Desember']

# Lag figur med flere visualiseringer
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=(
        'Produksjon og tap',
        'Forbruk vs produksjon',
        'Curtailment detaljer',
        'Månedlig energibalanse'
    ),
    specs=[[{'type': 'bar'}, {'type': 'scatter'}],
           [{'type': 'bar'}, {'type': 'bar'}]],
    vertical_spacing=0.12,
    horizontal_spacing=0.1
)

# ========= SUBPLOT 1: Produksjon og tap =========
fig.add_trace(
    go.Bar(
        x=months_no,
        y=monthly['delivered_to_grid'].values,
        name='Levert til nett',
        marker_color='#2E8B57',
        showlegend=True
    ),
    row=1, col=1
)

fig.add_trace(
    go.Bar(
        x=months_no,
        y=monthly['grid_curtailment'].values,
        name='Nett-curtailment',
        marker_color='#DC143C',
        showlegend=True
    ),
    row=1, col=1
)

fig.add_trace(
    go.Bar(
        x=months_no,
        y=monthly['inverter_clipping'].values,
        name='Inverter-clipping',
        marker_color='#FF8C00',
        showlegend=True
    ),
    row=1, col=1
)

# ========= SUBPLOT 2: Forbruk vs produksjon =========
fig.add_trace(
    go.Scatter(
        x=months_no,
        y=monthly['AC_production'].values,
        name='AC-produksjon',
        mode='lines+markers',
        line=dict(color='#4169E1', width=3),
        marker=dict(size=10)
    ),
    row=1, col=2
)

fig.add_trace(
    go.Scatter(
        x=months_no,
        y=monthly['consumption'].values,
        name='Forbruk',
        mode='lines+markers',
        line=dict(color='#32CD32', width=3),
        marker=dict(size=10)
    ),
    row=1, col=2
)

fig.add_trace(
    go.Scatter(
        x=months_no,
        y=monthly['DC_production'].values,
        name='DC-produksjon',
        mode='lines+markers',
        line=dict(color='#FFA500', width=2, dash='dash'),
        marker=dict(size=8)
    ),
    row=1, col=2
)

# ========= SUBPLOT 3: Curtailment detaljer =========
# Beregn curtailment som prosent av produksjon
curtailment_pct = (monthly['grid_curtailment'] / monthly['AC_production'] * 100).fillna(0)

fig.add_trace(
    go.Bar(
        x=months_no,
        y=curtailment_pct.values,
        name='Curtailment %',
        marker_color='#FF6B6B',
        text=[f'{x:.1f}%' for x in curtailment_pct.values],
        textposition='outside'
    ),
    row=2, col=1
)

# ========= SUBPLOT 4: Månedlig energibalanse =========
# Stablede søyler for energibalanse
fig.add_trace(
    go.Bar(
        x=months_no,
        y=monthly['consumption'].values,
        name='Forbruk',
        marker_color='#95E1D3',
        offsetgroup=0
    ),
    row=2, col=2
)

fig.add_trace(
    go.Bar(
        x=months_no,
        y=monthly['delivered_to_grid'].values,
        name='Eksport',
        marker_color='#4ECDC4',
        offsetgroup=1
    ),
    row=2, col=2
)

fig.add_trace(
    go.Bar(
        x=months_no,
        y=monthly['grid_curtailment'].values,
        name='Tapt (curtailment)',
        marker_color='#F38181',
        offsetgroup=1
    ),
    row=2, col=2
)

# ========= OPPDATER LAYOUT =========
fig.update_xaxes(title_text="Måned", row=1, col=1)
fig.update_yaxes(title_text="Energi (MWh)", row=1, col=1)

fig.update_xaxes(title_text="Måned", row=1, col=2)
fig.update_yaxes(title_text="Energi (MWh)", row=1, col=2)

fig.update_xaxes(title_text="Måned", row=2, col=1)
fig.update_yaxes(title_text="Curtailment (%)", row=2, col=1)

fig.update_xaxes(title_text="Måned", row=2, col=2)
fig.update_yaxes(title_text="Energi (MWh)", row=2, col=2)

# Barmode for subplot 1 og 4
fig.update_layout(
    title={
        'text': f'Månedlig produksjon, forbruk og curtailment<br><sub>{pv_capacity:.1f} kWp anlegg i Stavanger</sub>',
        'x': 0.5,
        'xanchor': 'center'
    },
    height=800,
    showlegend=True,
    hovermode='x unified',
    barmode='stack'
)

# Vis figuren
fig.show()

# Skriv ut statistikk
print("\n" + "="*60)
print("MÅNEDLIG STATISTIKK")
print("="*60)

# Lag oppsummeringstabell
summary_df = pd.DataFrame({
    'Måned': months_no,
    'DC prod (MWh)': monthly['DC_production'].values.round(1),
    'AC prod (MWh)': monthly['AC_production'].values.round(1),
    'Levert (MWh)': monthly['delivered_to_grid'].values.round(1),
    'Forbruk (MWh)': monthly['consumption'].values.round(1),
    'Curtailment (MWh)': monthly['grid_curtailment'].values.round(1),
    'Curtailment (%)': curtailment_pct.values.round(1)
})

print(summary_df.to_string(index=False))

print("\n" + "="*60)
print("ÅRLIG OPPSUMMERING")
print("="*60)

annual_stats = {
    'Total DC-produksjon': monthly['DC_production'].sum(),
    'Total AC-produksjon': monthly['AC_production'].sum(),
    'Total levert til nett': monthly['delivered_to_grid'].sum(),
    'Total forbruk': monthly['consumption'].sum(),
    'Total inverter-clipping': monthly['inverter_clipping'].sum(),
    'Total nett-curtailment': monthly['grid_curtailment'].sum(),
    'Systemvirkningsgrad': (monthly['delivered_to_grid'].sum() / monthly['DC_production'].sum() * 100)
}

for key, value in annual_stats.items():
    if 'virkningsgrad' in key.lower():
        print(f"{key:.<35} {value:.1f} %")
    else:
        print(f"{key:.<35} {value:.1f} MWh")

# Identifiser kritiske måneder
print("\n" + "="*60)
print("KRITISKE PERIODER")
print("="*60)

# Måneder med mest curtailment
worst_curtailment = summary_df.nlargest(3, 'Curtailment (MWh)')
print("\nMåneder med mest curtailment:")
for _, row in worst_curtailment.iterrows():
    print(f"  {row['Måned']:.<15} {row['Curtailment (MWh)']} MWh ({row['Curtailment (%)']}%)")

# Måneder med høyest forbruk vs produksjon ratio
summary_df['Dekningsgrad'] = (summary_df['AC prod (MWh)'] / summary_df['Forbruk (MWh)'] * 100).round(1)
lowest_coverage = summary_df.nsmallest(3, 'Dekningsgrad')
print("\nMåneder med lavest soldekning:")
for _, row in lowest_coverage.iterrows():
    print(f"  {row['Måned']:.<15} {row['Dekningsgrad']}% dekning")

# Lagre figuren
print("\n" + "="*60)
print("Lagrer figur...")
fig.write_html('results/monthly_production_analysis.html')
print("✅ Figur lagret som: results/monthly_production_analysis.html")

# Lag også en forenklet versjon
fig_simple = go.Figure()

# Stacked bar chart
fig_simple.add_trace(go.Bar(
    x=months_no,
    y=monthly['delivered_to_grid'].values,
    name='Levert til nett',
    marker_color='#2E8B57'
))

fig_simple.add_trace(go.Bar(
    x=months_no,
    y=monthly['grid_curtailment'].values,
    name='Curtailment',
    marker_color='#DC143C'
))

fig_simple.add_trace(go.Bar(
    x=months_no,
    y=monthly['inverter_clipping'].values,
    name='Inverter tap',
    marker_color='#FF8C00'
))

# Legg til forbrukslinje
fig_simple.add_trace(go.Scatter(
    x=months_no,
    y=monthly['consumption'].values,
    name='Forbruk',
    mode='lines+markers',
    line=dict(color='#4169E1', width=3),
    marker=dict(size=8)
))

fig_simple.update_layout(
    title='Månedlig produksjon, forbruk og curtailment',
    xaxis_title='Måned',
    yaxis_title='Energi (MWh)',
    hovermode='x unified',
    barmode='stack',
    height=500,
    template='plotly_white'
)

fig_simple.show()
fig_simple.write_html('results/monthly_production_simple.html')
print("✅ Forenklet figur lagret som: results/monthly_production_simple.html")