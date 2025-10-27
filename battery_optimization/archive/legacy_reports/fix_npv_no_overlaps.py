#!/usr/bin/env python3
"""
Fikser NPV-grafen - fjerner overlapp og rammer på tekstbokser
"""

import numpy as np
import plotly.graph_objects as go

print("Lager NPV-graf med forbedret layout...")

# Batteristørrelser opp til 100 kWh
battery_sizes = np.arange(0, 110, 10)

def calculate_npv_realistic(size_kwh, cost_per_kwh):
    """
    Realistisk NPV-beregning basert på analysen
    """
    if size_kwh == 0:
        return 0

    # Årlige besparelser (avtagende med størrelse)
    annual_savings = 0

    if size_kwh <= 10:
        annual_savings = size_kwh * 350  # 3500 for 10 kWh
    elif size_kwh <= 50:
        annual_savings = 3500 + (size_kwh - 10) * 200  # 2000 per 10 kWh
    elif size_kwh <= 100:
        annual_savings = 3500 + 40 * 200 + (size_kwh - 50) * 100  # 1000 per 10 kWh
    else:
        annual_savings = 3500 + 40 * 200 + 50 * 100 + (size_kwh - 100) * 50  # 500 per 10 kWh

    # NPV beregning (15 år, 5% diskontering)
    discount_rate = 0.05
    years = 15
    npv_factor = (1 - (1 + discount_rate)**(-years)) / discount_rate  # ~10.38

    total_savings = annual_savings * npv_factor
    investment = size_kwh * cost_per_kwh

    # Returner i 1000 NOK
    return (total_savings - investment) / 1000

# Beregn NPV for ulike kostnadsnivåer
npv_5000 = [calculate_npv_realistic(size, 5000) for size in battery_sizes]
npv_4500 = [calculate_npv_realistic(size, 4500) for size in battery_sizes]
npv_4000 = [calculate_npv_realistic(size, 4000) for size in battery_sizes]
npv_3500 = [calculate_npv_realistic(size, 3500) for size in battery_sizes]
npv_3000 = [calculate_npv_realistic(size, 3000) for size in battery_sizes]
npv_2500 = [calculate_npv_realistic(size, 2500) for size in battery_sizes]
npv_2000 = [calculate_npv_realistic(size, 2000) for size in battery_sizes]

# Lag figur
fig = go.Figure()

# Legg til linjer for ulike kostnadsscenarier
fig.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_5000,
    name='5000 kr/kWh (dagens marked)',
    mode='lines+markers',
    line=dict(color='#DC143C', width=3),
    marker=dict(size=4)
))

fig.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_4500,
    name='4500 kr/kWh',
    mode='lines',
    line=dict(color='#FF6347', width=2),
))

fig.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_4000,
    name='4000 kr/kWh',
    mode='lines',
    line=dict(color='#FF8C00', width=2),
))

fig.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_3500,
    name='3500 kr/kWh',
    mode='lines',
    line=dict(color='#FFA500', width=2),
))

fig.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_3000,
    name='3000 kr/kWh',
    mode='lines',
    line=dict(color='#FFD700', width=2),
))

fig.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_2500,
    name='2500 kr/kWh (break-even)',
    mode='lines+markers',
    line=dict(color='#32CD32', width=3),
    marker=dict(size=4)
))

fig.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_2000,
    name='2000 kr/kWh',
    mode='lines',
    line=dict(color='#228B22', width=2, dash='dash'),
))

# Legg til break-even linje
fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=2,
               annotation_text="Break-even (NPV = 0)")

# Marker noen viktige punkter med bedre plassering
# Ved 5000 kr/kWh og 10 kWh - flytt lengre til høyre
fig.add_annotation(
    x=10,
    y=npv_5000[1],
    text=f"10 kWh @ 5000:<br>{npv_5000[1]:.0f} kNOK",
    showarrow=True,
    arrowhead=2,
    ax=80,  # Økt avstand
    ay=-60,  # Flyttet lengre ned
    bgcolor="rgba(0, 0, 0, 0)",  # Helt transparent
    bordercolor="rgba(0, 0, 0, 0)",  # Ingen ramme
    font=dict(size=10, color="black")
)

# Optimal ved 2500 kr/kWh - flytt lengre opp og til venstre
optimal_2500_idx = np.argmax(npv_2500)
fig.add_annotation(
    x=battery_sizes[optimal_2500_idx],
    y=npv_2500[optimal_2500_idx],
    text=f"Optimal @ 2500:<br>{battery_sizes[optimal_2500_idx]} kWh<br>{npv_2500[optimal_2500_idx]:.0f} kNOK",
    showarrow=True,
    arrowhead=2,
    ax=-80,  # Økt avstand til venstre
    ay=-80,  # Flyttet lengre ned
    bgcolor="rgba(0, 0, 0, 0)",  # Helt transparent
    bordercolor="rgba(0, 0, 0, 0)",  # Ingen ramme
    font=dict(size=10, color="black")
)

# Oppdater layout
fig.update_layout(
    title='NPV vs Batteristørrelse - Realistiske verdier',
    xaxis_title='Batteristørrelse (kWh)',
    yaxis_title='NPV (1000 NOK)',
    hovermode='x unified',
    height=600,
    template='plotly_white',
    xaxis=dict(
        range=[0, 100],
        tickmode='linear',
        dtick=10
    ),
    yaxis=dict(
        range=[-1000, 200],
        tickmode='linear',
        dtick=100
    ),
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01
    )
)

# Legg til forklaringsboks - justert for 100 kWh skala
fig.add_annotation(
    x=80,  # Justert for 100 kWh skala
    y=-800,  # Flyttet lengre ned
    text="<b>Viktige punkter:</b><br>" +
         "• Ved 5000 kr/kWh: ALLTID negativ NPV<br>" +
         "• Break-even ved ~2500 kr/kWh<br>" +
         "• Avtagende marginalnytte<br>" +
         "• Optimal størrelse: 10-50 kWh<br>" +
         "• Større batterier = dårligere økonomi",
    showarrow=False,
    bgcolor="rgba(0, 0, 0, 0)",  # Helt transparent
    bordercolor="rgba(0, 0, 0, 0)",  # Ingen ramme
    font=dict(size=11, color="black"),
    align='left'
)

# Lagre
output_file = 'results/fig7_npv.html'
fig.write_html(output_file)

print(f"✅ Forbedret NPV-graf lagret: {output_file}")
print(f"   - Fjernet rammer og bakgrunn på tekstbokser")
print(f"   - Økt avstand mellom tekst og linjer")
print(f"   - Bedre plassering av annotasjoner")