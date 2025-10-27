#!/usr/bin/env python3
"""
Fikser effekttariff-grafen:
- Bruker piler (annotations) som peker på kurven
- Fjerner vertikale linjer
"""

import plotly.graph_objects as go

print("Lager effekttariff-graf med piler...")

# Effekttariff struktur (Lnett C13)
power_brackets = [
    (0, 5, 189),
    (5, 10, 321),
    (10, 20, 643),
    (20, 50, 1607),
    (50, 75, 2572),
    (75, 100, 3372),
    (100, 200, 4300),
    (200, 300, 8600),
    (300, 500, 12900),
    (500, float('inf'), 21500)
]

# Lag x og y verdier for trappekurven
x_power = []
y_cost = []

for lower, upper, cost in power_brackets:
    if upper == float('inf'):
        upper = 600
    x_power.extend([lower, upper])
    y_cost.extend([cost, cost])

# Lag figur
fig = go.Figure()

# Legg til hovedkurven
fig.add_trace(go.Scatter(
    x=x_power,
    y=y_cost,
    mode='lines',
    name='Effekttariff',
    line=dict(color='#FF6B6B', width=4),
    fill='tozeroy',
    fillcolor='rgba(255, 107, 107, 0.2)'
))

# Marker punkter for typiske effekttopper
# Punkt for 77 kW (uten batteri)
fig.add_trace(go.Scatter(
    x=[77],
    y=[3372],
    mode='markers',
    name='Uten batteri (77 kW)',
    marker=dict(color='red', size=12, symbol='circle')
))

# Punkt for 72 kW (med batteri)
fig.add_trace(go.Scatter(
    x=[72],
    y=[2572],
    mode='markers',
    name='Med 10 kWh batteri (72 kW)',
    marker=dict(color='green', size=12, symbol='circle')
))

# Legg til piler som annotasjoner
fig.add_annotation(
    x=77,
    y=3372,
    text="Typisk peak<br>uten batteri<br>77 kW → 3372 kr/mnd",
    showarrow=True,
    arrowhead=2,
    arrowsize=1.5,
    arrowwidth=3,
    arrowcolor="red",
    ax=-80,
    ay=-60,
    bgcolor="white",
    bordercolor="red",
    borderwidth=2
)

fig.add_annotation(
    x=72,
    y=2572,
    text="Med batteri<br>72 kW → 2572 kr/mnd<br>Spart: 800 kr/mnd",
    showarrow=True,
    arrowhead=2,
    arrowsize=1.5,
    arrowwidth=3,
    arrowcolor="green",
    ax=80,
    ay=-80,
    bgcolor="white",
    bordercolor="green",
    borderwidth=2
)

# Legg til informasjonsboks
fig.add_annotation(
    x=350,
    y=15000,
    text="<b>Effekttariff Lnett C13</b><br>" +
         "Betales basert på høyeste<br>" +
         "time i måneden<br><br>" +
         "Årlig besparelse ved<br>" +
         "5 kW reduksjon:<br>" +
         "<b>9,600 NOK</b>",
    showarrow=False,
    bgcolor="rgba(255, 255, 255, 0.9)",
    bordercolor="#FF6B6B",
    borderwidth=2,
    font=dict(size=11)
)

# Oppdater layout
fig.update_layout(
    title='Effekttariff struktur (Lnett) - Intervallbasert',
    xaxis_title='Effekt (kW)',
    yaxis_title='NOK/måned',
    hovermode='x unified',
    height=500,
    template='plotly_white',
    xaxis=dict(range=[0, 150]),  # Fokuser på relevant område
    yaxis=dict(range=[0, 5000])
)

# Lagre
output_file = 'results/fig4_power_tariff.html'
fig.write_html(output_file)
print(f"✅ Oppdatert effekttariff lagret: {output_file}")
print("   - Bruker piler som peker på kurven")
print("   - Markerer punkter for 72 kW (med batteri) og 77 kW (uten)")
print("   - Fjernet vertikale linjer")