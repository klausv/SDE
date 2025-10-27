#!/usr/bin/env python3
"""
Plotter NPV med de NYE korrekte verdiene fra optimeringen
Utvider til 200 kWh
"""

import pickle
import numpy as np
import plotly.graph_objects as go

# Last inn resultater
print("Laster optimeringsresultater...")
with open('results/realistic_simulation_results.pkl', 'rb') as f:
    results = pickle.load(f)

opt_results = results.get('optimization_results')

# Hent data for 5000 kr/kWh (market)
market = opt_results[opt_results['cost_scenario'] == 'market'].sort_values('battery_kwh')
battery_sizes_5000 = market['battery_kwh'].values
npv_5000 = market['npv'].values / 1000  # Konverter til 1000 NOK

# Hent data for 2500 kr/kWh (target)
target = opt_results[opt_results['cost_scenario'] == 'target'].sort_values('battery_kwh')
battery_sizes_2500 = target['battery_kwh'].values
npv_2500 = target['npv'].values / 1000  # Konverter til 1000 NOK

# Lag figur
fig = go.Figure()

# 5000 kr/kWh - Dagens marked
fig.add_trace(go.Scatter(
    x=battery_sizes_5000,
    y=npv_5000,
    name='5000 kr/kWh (dagens marked)',
    mode='lines+markers',
    line=dict(color='#DC143C', width=3),
    marker=dict(size=6),
    hovertemplate='%{x} kWh: %{y:.0f} kNOK<extra></extra>'
))

# 2500 kr/kWh - Target/fremtidig
fig.add_trace(go.Scatter(
    x=battery_sizes_2500,
    y=npv_2500,
    name='2500 kr/kWh (50% reduksjon)',
    mode='lines+markers',
    line=dict(color='#32CD32', width=3),
    marker=dict(size=6),
    hovertemplate='%{x} kWh: %{y:.0f} kNOK<extra></extra>'
))

# Interpoler for mellomverdier (3500 og 4000 kr/kWh)
# Antar lineær sammenheng mellom kostnad og NPV
npv_4000 = []
npv_3500 = []
npv_3000 = []

for i, size in enumerate(battery_sizes_5000):
    if i < len(npv_2500):
        # Lineær interpolasjon
        npv_at_5000 = npv_5000[i]
        npv_at_2500 = npv_2500[i]

        # NPV = a * cost + b
        # Finn a og b
        a = (npv_at_5000 - npv_at_2500) / (5000 - 2500)
        b = npv_at_2500 - a * 2500

        npv_4000.append(a * 4000 + b)
        npv_3500.append(a * 3500 + b)
        npv_3000.append(a * 3000 + b)

# 4000 kr/kWh
fig.add_trace(go.Scatter(
    x=battery_sizes_5000[:len(npv_4000)],
    y=npv_4000,
    name='4000 kr/kWh',
    mode='lines',
    line=dict(color='#FF8C00', width=2, dash='dot'),
    hovertemplate='%{x} kWh: %{y:.0f} kNOK<extra></extra>'
))

# 3500 kr/kWh
fig.add_trace(go.Scatter(
    x=battery_sizes_5000[:len(npv_3500)],
    y=npv_3500,
    name='3500 kr/kWh',
    mode='lines',
    line=dict(color='#FFA500', width=2, dash='dot'),
    hovertemplate='%{x} kWh: %{y:.0f} kNOK<extra></extra>'
))

# 3000 kr/kWh
fig.add_trace(go.Scatter(
    x=battery_sizes_5000[:len(npv_3000)],
    y=npv_3000,
    name='3000 kr/kWh',
    mode='lines',
    line=dict(color='#FFD700', width=2, dash='dot'),
    hovertemplate='%{x} kWh: %{y:.0f} kNOK<extra></extra>'
))

# Break-even linje
fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=2,
               annotation_text="Break-even (NPV = 0)")

# Marker viktige punkter
# Optimal ved 5000 kr/kWh
if npv_5000[0] > 0:
    fig.add_annotation(
        x=10,
        y=npv_5000[0],
        text=f"<b>10 kWh @ 5000:</b><br>{npv_5000[0]:.0f} kNOK<br>Lønnsomt pga effekttariff!",
        showarrow=True,
        arrowhead=2,
        ax=60,
        ay=-40,
        bgcolor="lightgreen",
        bordercolor="darkgreen",
        borderwidth=2
    )

# Punkt hvor 5000 kr/kWh blir ulønnsomt
for i, npv in enumerate(npv_5000):
    if npv < 0:
        fig.add_annotation(
            x=battery_sizes_5000[i],
            y=npv,
            text=f"Ved {battery_sizes_5000[i]:.0f} kWh<br>blir 5000 kr/kWh<br>ulønnsomt",
            showarrow=True,
            arrowhead=2,
            ax=-60,
            ay=-30,
            bgcolor="lightyellow",
            bordercolor="red"
        )
        break

# Oppdater layout
fig.update_layout(
    title='NPV vs Batteristørrelse - Oppdaterte verdier fra optimering',
    xaxis_title='Batteristørrelse (kWh)',
    yaxis_title='NPV (1000 NOK)',
    hovermode='x unified',
    height=600,
    template='plotly_white',
    xaxis=dict(
        range=[0, 210],
        tickmode='linear',
        dtick=20
    ),
    yaxis=dict(
        range=[-400, 100],
        tickmode='linear',
        dtick=50
    ),
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01,
        bgcolor='rgba(255,255,255,0.9)',
        bordercolor='gray',
        borderwidth=1
    )
)

# Informasjonsboks
fig.add_annotation(
    x=150,
    y=-250,
    text="<b>Viktige funn:</b><br>" +
         "• 10 kWh kan være lønnsomt<br>" +
         "  selv ved 5000 kr/kWh!<br>" +
         "• Effekttariff-besparelser<br>" +
         "  dominerer for små batterier<br>" +
         "• Større batterier (>20 kWh)<br>" +
         "  er ulønnsomme ved dagens priser<br>" +
         "• Avtagende marginalnytte",
    showarrow=False,
    bgcolor="rgba(255, 255, 255, 0.95)",
    bordercolor="gray",
    borderwidth=2,
    font=dict(size=11),
    align='left'
)

# Lagre
output_file = 'results/fig7_npv.html'
fig.write_html(output_file)

print(f"✅ NPV-graf med korrekte verdier lagret: {output_file}")
print(f"\nViktige verdier:")
print(f"  10 kWh @ 5000 kr/kWh: {npv_5000[0]:.0f} kNOK")
print(f"  20 kWh @ 5000 kr/kWh: {npv_5000[1]:.0f} kNOK")
print(f"  50 kWh @ 5000 kr/kWh: {npv_5000[4]:.0f} kNOK")
print(f"  10 kWh @ 2500 kr/kWh: {npv_2500[0]:.0f} kNOK")
print(f"  50 kWh @ 2500 kr/kWh: {npv_2500[4]:.0f} kNOK")