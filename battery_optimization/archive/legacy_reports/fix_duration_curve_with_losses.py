#!/usr/bin/env python3
"""
Fikser varighetskurve med prosent-tap annotasjoner
- Viser % tap fra DC til AC (inverter curtailment)
- Viser % tap fra AC til nett (grid curtailment)
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

# Beregn tap
df['inverter_clipping'] = np.maximum(0, df['DC_production'] - inverter_capacity)
df['grid_curtailment'] = np.maximum(0, df['AC_production'] - grid_limit)
df['delivered_to_grid'] = df['AC_production'] - df['grid_curtailment']

# Beregn totale tap
total_dc = df['DC_production'].sum()
total_ac = df['AC_production'].sum()
total_delivered = df['delivered_to_grid'].sum()
total_inverter_loss = df['inverter_clipping'].sum()
total_grid_curtailment = df['grid_curtailment'].sum()

# Beregn prosenter
dc_to_ac_loss_pct = ((total_dc - total_ac) / total_dc * 100) if total_dc > 0 else 0
ac_to_grid_loss_pct = (total_grid_curtailment / total_ac * 100) if total_ac > 0 else 0
total_efficiency = (total_delivered / total_dc * 100) if total_dc > 0 else 0

print(f"Tap-analyse:")
print(f"  DC produksjon: {total_dc/1000:.1f} MWh")
print(f"  AC produksjon: {total_ac/1000:.1f} MWh")
print(f"  Levert til nett: {total_delivered/1000:.1f} MWh")
print(f"  DC→AC tap: {dc_to_ac_loss_pct:.1f}%")
print(f"  AC→Nett tap: {ac_to_grid_loss_pct:.1f}%")
print(f"  Total virkningsgrad: {total_efficiency:.1f}%")

# Sorter for varighetskurve
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
    fillcolor='rgba(255, 165, 0, 0.3)',
    hovertemplate='%{y:.1f} kW<br>%{x} timer<extra></extra>'
))

# AC-produksjon som vanlig linje
fig.add_trace(go.Scatter(
    x=hours,
    y=ac_sorted,
    name='AC-produksjon',
    mode='lines',
    line=dict(color='blue', width=2),
    hovertemplate='%{y:.1f} kW<br>%{x} timer<extra></extra>'
))

# Legg til grenselinjer
fig.add_hline(y=pv_capacity, line_dash="dash", line_color="darkorange",
               annotation_text=f"Maks DC ({pv_capacity:.1f} kWp)")

fig.add_hline(y=inverter_capacity, line_dash="dash", line_color="purple",
               annotation_text=f"Inverter ({inverter_capacity} kW)")

fig.add_hline(y=grid_limit, line_dash="dash", line_color="red",
               annotation_text=f"Nettgrense ({grid_limit} kW)")

# Legg til tap-annotasjoner med piler
# DC til AC tap
fig.add_annotation(
    x=1000,
    y=(pv_capacity + inverter_capacity) / 2,
    text=f"<b>DC→AC tap</b><br>{total_inverter_loss/1000:.1f} MWh/år<br>({dc_to_ac_loss_pct:.1f}% av DC)",
    showarrow=True,
    arrowhead=2,
    arrowsize=1,
    arrowwidth=2,
    arrowcolor="purple",
    ax=100,
    ay=0,
    bgcolor="rgba(255, 255, 255, 0.9)",
    bordercolor="purple",
    borderwidth=2,
    font=dict(size=11)
)

# AC til nett tap (grid curtailment)
fig.add_annotation(
    x=500,
    y=(inverter_capacity + grid_limit) / 2,
    text=f"<b>AC→Nett tap</b><br>{total_grid_curtailment/1000:.1f} MWh/år<br>({ac_to_grid_loss_pct:.1f}% av AC)",
    showarrow=True,
    arrowhead=2,
    arrowsize=1,
    arrowwidth=2,
    arrowcolor="red",
    ax=-100,
    ay=0,
    bgcolor="rgba(255, 255, 255, 0.9)",
    bordercolor="red",
    borderwidth=2,
    font=dict(size=11)
)

# Total virkningsgrad boks
fig.add_annotation(
    x=6000,
    y=120,
    text=f"<b>Energiflyt årlig:</b><br>" +
         f"DC prod: {total_dc/1000:.1f} MWh<br>" +
         f"↓ <i>inverter tap {(total_dc-total_ac)/1000:.1f} MWh</i><br>" +
         f"AC prod: {total_ac/1000:.1f} MWh<br>" +
         f"↓ <i>nett curtail {total_grid_curtailment/1000:.1f} MWh</i><br>" +
         f"Levert: {total_delivered/1000:.1f} MWh<br><br>" +
         f"<b>Total virkningsgrad:<br>{total_efficiency:.1f}%</b>",
    showarrow=False,
    bgcolor="rgba(255, 255, 255, 0.95)",
    bordercolor="green",
    borderwidth=2,
    font=dict(size=10),
    align='left'
)

# Oppdater layout
fig.update_layout(
    title={
        'text': f'Varighetskurve - DC vs AC solproduksjon<br><sub>Virkningsgrad: {total_efficiency:.1f}% | DC→AC tap: {dc_to_ac_loss_pct:.1f}% | AC→Nett tap: {ac_to_grid_loss_pct:.1f}%</sub>',
        'x': 0.5,
        'xanchor': 'center'
    },
    xaxis_title='Timer i året',
    yaxis_title='Effekt (kW)',
    hovermode='x unified',
    height=550,
    template='plotly_white',
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01
    )
)

# Lagre
output_file = 'results/fig3_duration_curve.html'
fig.write_html(output_file)

print(f"\n✅ Oppdatert varighetskurve lagret: {output_file}")
print(f"   - DC→AC tap: {dc_to_ac_loss_pct:.1f}% ({total_inverter_loss/1000:.1f} MWh)")
print(f"   - AC→Nett tap: {ac_to_grid_loss_pct:.1f}% ({total_grid_curtailment/1000:.1f} MWh)")
print(f"   - Total virkningsgrad: {total_efficiency:.1f}%")