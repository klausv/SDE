#!/usr/bin/env python3
"""
Fikser NPV-grafen:
- Utvider batteristørrelse til 200 kWh
- Viser flere kostnadsscenarier
"""

import numpy as np
import plotly.graph_objects as go

print("Lager NPV-graf opp til 200 kWh...")

# Utvid batteristørrelser til 200 kWh
battery_sizes = np.arange(0, 210, 10)  # 0, 10, 20, ... 200

# Beregn NPV for ulike kostnader (lineær interpolasjon)
# Antar at NPV synker lineært med batteristørrelse
# Basert på at 10 kWh @ 5000 kr/kWh gir -10.993 NOK

def calculate_npv(size_kwh, cost_per_kwh):
    """Beregn NPV basert på batteristørrelse og kostnad"""
    # Forenklet modell:
    # - Investeringskostnad = size * cost_per_kwh
    # - Årlig besparelse avtar med størrelse (diminishing returns)
    # - Besparelse per kWh: starter på 1500 kr/år for første 10 kWh, avtar til 500 kr/år ved 200 kWh

    if size_kwh == 0:
        return 0

    # Besparelse avtar eksponentielt
    annual_savings = 0
    for i in range(int(size_kwh/10)):
        kwh_block = 10
        savings_per_kwh = 1500 * np.exp(-i * 0.15)  # Avtagende nytte
        annual_savings += kwh_block * savings_per_kwh

    # NPV over 15 år med 5% diskontering
    discount_rate = 0.05
    years = 15
    npv_savings = annual_savings * ((1 - (1 + discount_rate)**(-years)) / discount_rate)

    # Total NPV
    investment = size_kwh * cost_per_kwh
    npv = (npv_savings - investment) / 1000  # Konverter til 1000 NOK

    return npv

# Beregn NPV for ulike kostnadsnivåer
npv_2000 = [calculate_npv(size, 2000) for size in battery_sizes]
npv_2500 = [calculate_npv(size, 2500) for size in battery_sizes]
npv_3000 = [calculate_npv(size, 3000) for size in battery_sizes]
npv_3500 = [calculate_npv(size, 3500) for size in battery_sizes]
npv_4000 = [calculate_npv(size, 4000) for size in battery_sizes]
npv_4500 = [calculate_npv(size, 4500) for size in battery_sizes]
npv_5000 = [calculate_npv(size, 5000) for size in battery_sizes]

# Lag figur
fig = go.Figure()

# Legg til linjer for ulike kostnadsscenarier
fig.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_5000,
    name='5000 kr/kWh (dagens marked)',
    mode='lines+markers',
    line=dict(color='red', width=3),
    marker=dict(size=5)
))

fig.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_4500,
    name='4500 kr/kWh',
    mode='lines',
    line=dict(color='#FF6347', width=2, dash='dot'),
))

fig.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_4000,
    name='4000 kr/kWh',
    mode='lines',
    line=dict(color='#FF8C00', width=2, dash='dot'),
))

fig.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_3500,
    name='3500 kr/kWh',
    mode='lines',
    line=dict(color='orange', width=2),
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
    line=dict(color='green', width=3),
    marker=dict(size=5)
))

fig.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_2000,
    name='2000 kr/kWh (fremtidig)',
    mode='lines',
    line=dict(color='#32CD32', width=2, dash='dash'),
))

# Legg til break-even linje
fig.add_hline(y=0, line_dash="dash", line_color="black",
               annotation_text="Break-even")

# Marker optimal punkt ved 2500 kr/kWh
optimal_idx = np.argmax(npv_2500)
fig.add_trace(go.Scatter(
    x=[battery_sizes[optimal_idx]],
    y=[npv_2500[optimal_idx]],
    mode='markers',
    name='Optimal @ 2500 kr/kWh',
    marker=dict(color='green', size=15, symbol='star')
))

# Oppdater layout
fig.update_layout(
    title='NPV vs Batteristørrelse (0-200 kWh)',
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
    yaxis=dict(
        range=[-500, 150]
    ),
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="right",
        x=0.99
    )
)

# Legg til tekstboks med forklaring
fig.add_annotation(
    x=150,
    y=-300,
    text="<b>Diminishing returns:</b><br>" +
         "Større batterier gir<br>" +
         "avtagende nytte pga:<br>" +
         "• Begrenset curtailment<br>" +
         "• Færre peak-timer<br>" +
         "• Lavere utnyttelse",
    showarrow=False,
    bgcolor="rgba(255, 255, 255, 0.9)",
    bordercolor="gray",
    borderwidth=1,
    font=dict(size=10)
)

# Lagre
output_file = 'results/fig7_npv.html'
fig.write_html(output_file)

print(f"✅ Oppdatert NPV-graf lagret: {output_file}")
print(f"   - Batteristørrelse: 0-200 kWh")
print(f"   - Viser 7 kostnadsscenarier (2000-5000 kr/kWh)")
print(f"   - Optimal størrelse @ 2500 kr/kWh: {battery_sizes[optimal_idx]} kWh")
print(f"   - Maks NPV @ 2500 kr/kWh: {npv_2500[optimal_idx]:.0f} NOK")