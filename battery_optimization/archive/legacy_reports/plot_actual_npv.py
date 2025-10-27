#!/usr/bin/env python3
"""
Plotter NPV med FAKTISKE verdier fra optimeringsresultatene
Ikke oppfunnede tall!
"""

import pickle
import plotly.graph_objects as go

# Last inn FAKTISKE resultater
print("Laster faktiske optimeringsresultater...")
with open('results/realistic_simulation_results.pkl', 'rb') as f:
    results = pickle.load(f)

opt_results = results.get('optimization_results')

# Hent data for 5000 kr/kWh (market)
market = opt_results[opt_results['cost_scenario'] == 'market'].sort_values('battery_kwh')
battery_sizes_market = market['battery_kwh'].values
npv_5000 = market['npv'].values / 1000  # Konverter til 1000 NOK

# Hent data for 2500 kr/kWh (target)
target = opt_results[opt_results['cost_scenario'] == 'target'].sort_values('battery_kwh')
battery_sizes_target = target['battery_kwh'].values
npv_2500 = target['npv'].values / 1000  # Konverter til 1000 NOK

# Lag figur
fig = go.Figure()

# Plott faktiske verdier for 5000 kr/kWh
fig.add_trace(go.Scatter(
    x=battery_sizes_market,
    y=npv_5000,
    name='5000 kr/kWh (marked)',
    mode='lines+markers',
    line=dict(color='#DC143C', width=3),
    marker=dict(size=6)
))

# Plott faktiske verdier for 2500 kr/kWh
fig.add_trace(go.Scatter(
    x=battery_sizes_target,
    y=npv_2500,
    name='2500 kr/kWh (target)',
    mode='lines+markers',
    line=dict(color='#32CD32', width=3),
    marker=dict(size=6)
))

# Legg til break-even linje
fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=2,
               annotation_text="Break-even (NPV = 0)")

# Marker viktige punkter
# 10 kWh ved 5000
fig.add_annotation(
    x=10,
    y=npv_5000[0],
    text=f"10 kWh @ 5000:<br><b>{npv_5000[0]:.1f} kNOK</b><br>(Dette ser feil ut!)",
    showarrow=True,
    arrowhead=2,
    ax=50,
    ay=-30,
    bgcolor="yellow",
    bordercolor="red",
    borderwidth=2
)

# 50 kWh ved 2500 (break-even punkt)
idx_50_target = list(battery_sizes_target).index(50)
fig.add_annotation(
    x=50,
    y=npv_2500[idx_50_target],
    text=f"50 kWh @ 2500:<br><b>{npv_2500[idx_50_target]:.1f} kNOK</b>",
    showarrow=True,
    arrowhead=2,
    ax=-60,
    ay=30,
    bgcolor="white",
    bordercolor="green"
)

# Oppdater layout
fig.update_layout(
    title='NPV vs Batteristørrelse - FAKTISKE VERDIER FRA OPTIMERING',
    xaxis_title='Batteristørrelse (kWh)',
    yaxis_title='NPV (1000 NOK)',
    hovermode='x unified',
    height=600,
    template='plotly_white',
    xaxis=dict(
        range=[0, 200],
        tickmode='linear',
        dtick=20
    ),
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01
    )
)

# Advarselsboks
fig.add_annotation(
    x=150,
    y=-200,
    text="<b>⚠️ ADVARSEL:</b><br>" +
         "Disse verdiene kommer direkte<br>" +
         "fra optimization_results.pkl<br>" +
         "MEN de ser feil ut!<br><br>" +
         "Ved 5000 kr/kWh skal NPV<br>" +
         "være NEGATIV for alle størrelser!",
    showarrow=False,
    bgcolor="rgba(255, 255, 0, 0.3)",
    bordercolor="red",
    borderwidth=2,
    font=dict(size=11, color="red")
)

# Lagre
output_file = 'results/fig7_npv.html'
fig.write_html(output_file)

print(f"✅ NPV-graf med FAKTISKE verdier lagret: {output_file}")
print(f"\n⚠️  MEN VERDIENE SER FEIL UT:")
print(f"   - 10 kWh @ 5000 kr/kWh: {npv_5000[0]:.1f} kNOK (SKULLE VÆRT NEGATIV!)")
print(f"   - 10 kWh @ 2500 kr/kWh: {npv_2500[0]:.1f} kNOK")
print(f"\nDet ser ut som optimeringsresultatene har feil verdier lagret!")