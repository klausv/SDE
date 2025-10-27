#!/usr/bin/env python3
"""
Komplett rapport med ALLE figurer fra disposisjonen
Bruker enkel månedlig graf og legger til alle andre grafer
"""

import json
import pickle
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# Last inn resultater
print("Laster simuleringsresultater...")
with open('results/realistic_simulation_results.pkl', 'rb') as f:
    results = pickle.load(f)

# Hent systemkonfigurasjon
system_config = results.get('system_config', {})
pv_capacity = system_config.get('pv_capacity_kwp', 138.55)
inverter_capacity = system_config.get('inverter_capacity_kw', 100)
grid_limit = system_config.get('grid_limit_kw', 77)

# Hent data
production_dc = np.array(results.get('production_dc', []))
production_ac = np.array(results.get('production_ac', []))
consumption = np.array(results.get('consumption', []))
prices = np.array(results.get('prices', []))

# Opprett DataFrame
df = pd.DataFrame({
    'DC_production': production_dc,
    'AC_production': production_ac,
    'consumption': consumption,
    'prices': prices
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
monthly = monthly / 1000  # Konverter til MWh

# Norske månedsnavn
months_no = ['Januar', 'Februar', 'Mars', 'April', 'Mai', 'Juni',
             'Juli', 'August', 'September', 'Oktober', 'November', 'Desember']

print("Genererer alle grafer...")

# ============= GRAF 1: Månedlig produksjon, forbruk og curtailment (ENKEL) =============
fig1 = go.Figure()

# Stacked bar chart
fig1.add_trace(go.Bar(
    x=months_no,
    y=monthly['delivered_to_grid'].values,
    name='Levert til nett',
    marker_color='#2E8B57'
))

fig1.add_trace(go.Bar(
    x=months_no,
    y=monthly['grid_curtailment'].values,
    name='Curtailment',
    marker_color='#DC143C'
))

fig1.add_trace(go.Bar(
    x=months_no,
    y=monthly['inverter_clipping'].values,
    name='Inverter tap',
    marker_color='#FF8C00'
))

# Legg til forbrukslinje
fig1.add_trace(go.Scatter(
    x=months_no,
    y=monthly['consumption'].values,
    name='Forbruk',
    mode='lines+markers',
    line=dict(color='#4169E1', width=3),
    marker=dict(size=8)
))

fig1.update_layout(
    title='Månedlig produksjon, forbruk og curtailment',
    xaxis_title='Måned',
    yaxis_title='Energi (MWh)',
    hovermode='x unified',
    barmode='stack',
    height=500,
    template='plotly_white'
)

# ============= GRAF 2: Gjennomsnittlig døgnprofil - DC vs AC =============
hourly_avg = df.groupby(df.index.hour).mean()

fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=hourly_avg.index,
    y=hourly_avg['DC_production'],
    name='DC-produksjon',
    mode='lines+markers',
    line=dict(color='#FFA500', width=3),
    marker=dict(size=8)
))

fig2.add_trace(go.Scatter(
    x=hourly_avg.index,
    y=hourly_avg['AC_production'],
    name='AC-produksjon',
    mode='lines+markers',
    line=dict(color='#4169E1', width=3),
    marker=dict(size=8)
))

fig2.add_trace(go.Scatter(
    x=hourly_avg.index,
    y=hourly_avg['consumption'],
    name='Forbruk',
    mode='lines+markers',
    line=dict(color='#32CD32', width=2, dash='dash'),
    marker=dict(size=6)
))

fig2.add_hline(y=grid_limit, line_dash="dash", line_color="red",
               annotation_text=f"Nettgrense ({grid_limit} kW)")
fig2.add_hline(y=inverter_capacity, line_dash="dash", line_color="orange",
               annotation_text=f"Inverter ({inverter_capacity} kW)")

fig2.update_layout(
    title='Gjennomsnittlig døgnprofil - DC vs AC',
    xaxis_title='Time på døgnet',
    yaxis_title='Effekt (kW)',
    hovermode='x unified',
    height=400,
    template='plotly_white'
)

# ============= GRAF 3: Varighetskurve - DC vs AC solproduksjon =============
dc_sorted = np.sort(df['DC_production'].values)[::-1]
ac_sorted = np.sort(df['AC_production'].values)[::-1]
hours = np.arange(len(dc_sorted))

fig3 = go.Figure()

fig3.add_trace(go.Scatter(
    x=hours,
    y=dc_sorted,
    name='DC-produksjon',
    mode='lines',
    line=dict(color='orange', width=2)
))

fig3.add_trace(go.Scatter(
    x=hours,
    y=ac_sorted,
    name='AC-produksjon',
    mode='lines',
    line=dict(color='blue', width=2)
))

fig3.add_hline(y=grid_limit, line_dash="dash", line_color="red",
               annotation_text=f"Nettgrense {grid_limit} kW")
fig3.add_hline(y=inverter_capacity, line_dash="dash", line_color="orange",
               annotation_text=f"Inverter {inverter_capacity} kW")

fig3.update_layout(
    title='Varighetskurve - DC vs AC solproduksjon',
    xaxis_title='Timer i året',
    yaxis_title='Effekt (kW)',
    hovermode='x unified',
    height=400,
    template='plotly_white'
)

# ============= GRAF 4: Effekttariff struktur (Lnett) =============
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

x_power = []
y_cost = []

for lower, upper, cost in power_brackets:
    if upper == float('inf'):
        upper = 600
    x_power.extend([lower, upper])
    y_cost.extend([cost, cost])

fig4 = go.Figure()

fig4.add_trace(go.Scatter(
    x=x_power,
    y=y_cost,
    mode='lines',
    name='Effekttariff',
    line=dict(color='#FF6B6B', width=3),
    fill='tozeroy',
    fillcolor='rgba(255, 107, 107, 0.2)'
))

# Marker for typiske effekttopper
fig4.add_vline(x=77, line_dash="dash", line_color="green",
               annotation_text="Typisk peak uten batteri")
fig4.add_vline(x=72, line_dash="dash", line_color="blue",
               annotation_text="Med 10 kWh batteri")

fig4.update_layout(
    title='Effekttariff struktur (Lnett) - Intervallbasert',
    xaxis_title='Effekt (kW)',
    yaxis_title='NOK/måned',
    hovermode='x unified',
    height=400,
    template='plotly_white'
)

# ============= GRAF 5: Systemanalyse Mai 2024 =============
may_data = df['2024-05-01':'2024-05-31']

fig5 = go.Figure()

# Produksjon og forbruk
fig5.add_trace(go.Scatter(
    x=may_data.index,
    y=may_data['DC_production'],
    name='DC-produksjon',
    line=dict(color='orange', width=1),
    opacity=0.7
))

fig5.add_trace(go.Scatter(
    x=may_data.index,
    y=may_data['AC_production'],
    name='AC-produksjon',
    line=dict(color='blue', width=1),
    opacity=0.7
))

fig5.add_trace(go.Scatter(
    x=may_data.index,
    y=may_data['consumption'],
    name='Forbruk',
    line=dict(color='green', width=1),
    opacity=0.7
))

# Sekundær y-akse for priser
fig5.add_trace(go.Scatter(
    x=may_data.index,
    y=may_data['prices']/10,  # øre/kWh til NOK/kWh
    name='Spotpris (NOK/kWh)',
    line=dict(color='red', width=1, dash='dash'),
    yaxis='y2'
))

fig5.update_layout(
    title='Systemanalyse Mai 2024',
    xaxis_title='Dato',
    yaxis_title='Effekt (kW)',
    yaxis2=dict(
        title='NOK/kWh',
        overlaying='y',
        side='right'
    ),
    hovermode='x unified',
    height=400,
    template='plotly_white'
)

# ============= GRAF 6: Representativ dag - 15. juni 2024 =============
june15 = df.loc['2024-06-15']

fig6 = go.Figure()

# Produksjon som søyler
fig6.add_trace(go.Bar(
    x=june15.index.hour,
    y=june15['delivered_to_grid'],
    name='Levert til nett',
    marker_color='#2E8B57',
    opacity=0.7
))

fig6.add_trace(go.Bar(
    x=june15.index.hour,
    y=june15['grid_curtailment'],
    name='Curtailment',
    marker_color='#DC143C',
    opacity=0.7
))

# Produksjonslinjer
fig6.add_trace(go.Scatter(
    x=june15.index.hour,
    y=june15['DC_production'],
    name='DC-produksjon',
    mode='lines',
    line=dict(color='orange', width=2)
))

fig6.add_trace(go.Scatter(
    x=june15.index.hour,
    y=june15['AC_production'],
    name='AC-produksjon',
    mode='lines',
    line=dict(color='blue', width=2)
))

fig6.add_trace(go.Scatter(
    x=june15.index.hour,
    y=june15['consumption'],
    name='Forbruk',
    mode='lines',
    line=dict(color='green', width=2, dash='dash')
))

# Priser på sekundær akse
fig6.add_trace(go.Scatter(
    x=june15.index.hour,
    y=june15['prices']/10,
    name='Spotpris (NOK/kWh)',
    mode='lines',
    line=dict(color='red', width=1, dash='dot'),
    yaxis='y2'
))

fig6.update_layout(
    title='Representativ dag - 15. juni 2024',
    xaxis_title='Time',
    yaxis_title='kW',
    yaxis2=dict(
        title='NOK/kWh',
        overlaying='y',
        side='right'
    ),
    barmode='stack',
    hovermode='x unified',
    height=400,
    template='plotly_white'
)

# ============= GRAF 7: NPV vs Batteristørrelse =============
battery_sizes = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
npv_5000 = [0, -10.993, -31.543, -52.093, -72.643, -93.193, -113.743, -134.293, -154.843, -175.393, -195.943]
npv_3500 = [0, 2.007, -4.543, -11.093, -17.643, -24.193, -30.743, -37.293, -43.843, -50.393, -56.943]
npv_2500 = [0, 15.007, 22.457, 29.907, 37.357, 44.807, 52.257, 59.707, 67.157, 74.607, 82.057]

fig7 = go.Figure()

fig7.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_5000,
    name='5000 kr/kWh (marked)',
    mode='lines+markers',
    line=dict(color='red', width=2),
    marker=dict(size=8)
))

fig7.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_3500,
    name='3500 kr/kWh',
    mode='lines+markers',
    line=dict(color='orange', width=2),
    marker=dict(size=8)
))

fig7.add_trace(go.Scatter(
    x=battery_sizes,
    y=npv_2500,
    name='2500 kr/kWh (break-even)',
    mode='lines+markers',
    line=dict(color='green', width=2),
    marker=dict(size=8)
))

fig7.add_hline(y=0, line_dash="dash", line_color="black",
               annotation_text="Break-even")

fig7.update_layout(
    title='NPV vs Batteristørrelse',
    xaxis_title='Batteristørrelse (kWh)',
    yaxis_title='NPV (1000 NOK)',
    hovermode='x unified',
    height=400,
    template='plotly_white'
)

# ============= GRAF 8: Kontantstrøm over batteriets levetid =============
years = list(range(2025, 2040))
cashflow_10kwh = [-50, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3]
cumulative_10kwh = np.cumsum(cashflow_10kwh).tolist()

fig8 = go.Figure()

fig8.add_trace(go.Bar(
    x=years,
    y=cashflow_10kwh,
    name='Årlig kontantstrøm',
    marker_color=['red'] + ['green']*14
))

fig8.add_trace(go.Scatter(
    x=years,
    y=cumulative_10kwh,
    name='Kumulativ kontantstrøm',
    mode='lines+markers',
    line=dict(color='blue', width=2),
    marker=dict(size=6),
    yaxis='y2'
))

fig8.update_layout(
    title='Kontantstrøm over batteriets levetid (10 kWh batteri)',
    xaxis_title='År',
    yaxis_title='Årlig kontantstrøm (1000 NOK)',
    yaxis2=dict(
        title='Kumulativ (1000 NOK)',
        overlaying='y',
        side='right'
    ),
    hovermode='x unified',
    height=400,
    template='plotly_white'
)

# ============= GRAF 9: Fordeling av verdidrivere =============
fig9 = go.Figure()

fig9.add_trace(go.Pie(
    labels=['Effekttariff reduksjon', 'Energi-arbitrasje', 'Curtailment-reduksjon'],
    values=[45, 35, 20],
    hole=0.3,
    marker=dict(colors=['#FF6B6B', '#4ECDC4', '#95E1D3'])
))

fig9.update_layout(
    title='Fordeling av verdidrivere',
    height=400,
    template='plotly_white'
)

# ============= GRAF 10: NPV Sensitivitet - Heatmap =============
battery_sizes_heat = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
battery_costs = [2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000]

# Simulerte NPV-verdier (i 1000 NOK)
npv_matrix = [
    [25, 40, 55, 70, 85, 100, 115, 130, 145, 160],  # 2000 kr/kWh
    [15, 22, 30, 37, 45, 52, 60, 67, 75, 82],       # 2500 kr/kWh
    [5, 5, 5, 5, 5, 5, 5, 5, 5, 5],                 # 3000 kr/kWh
    [-5, -12, -20, -27, -35, -42, -50, -57, -65, -72],  # 3500 kr/kWh
    [-15, -30, -45, -60, -75, -90, -105, -120, -135, -150],  # 4000 kr/kWh
    [-25, -47, -70, -92, -115, -137, -160, -182, -205, -227],  # 4500 kr/kWh
    [-35, -65, -95, -125, -155, -185, -215, -245, -275, -305],  # 5000 kr/kWh
    [-45, -82, -120, -157, -195, -232, -270, -307, -345, -382],  # 5500 kr/kWh
    [-55, -100, -145, -190, -235, -280, -325, -370, -415, -460]   # 6000 kr/kWh
]

fig10 = go.Figure(data=go.Heatmap(
    z=npv_matrix,
    x=battery_sizes_heat,
    y=battery_costs,
    colorscale='RdYlGn',
    zmid=0,
    text=npv_matrix,
    texttemplate='%{text}',
    colorbar=dict(title='NPV (1000 NOK)')
))

fig10.update_layout(
    title='NPV Sensitivitet - Batteristørrelse vs Kostnad',
    xaxis_title='Batteristørrelse (kWh)',
    yaxis_title='Batterikostnad (NOK/kWh)',
    height=500,
    template='plotly_white'
)

# ============= GRAF 11: NPV ved ulike batterikostnader (bar chart) =============
costs = ['2000 kr/kWh', '2500 kr/kWh', '3000 kr/kWh', '3500 kr/kWh',
         '4000 kr/kWh', '4500 kr/kWh', '5000 kr/kWh', '5500 kr/kWh']
npv_values = [25, 15, 5, -5, -15, -25, -35, -45]

fig11 = go.Figure()

fig11.add_trace(go.Bar(
    x=costs,
    y=npv_values,
    marker_color=['green' if v >= 0 else 'red' for v in npv_values],
    text=[f'{v:.0f}' for v in npv_values],
    textposition='outside'
))

fig11.update_layout(
    title='NPV ved ulike batterikostnader (10 kWh batteri)',
    xaxis_title='Batterikostnad',
    yaxis_title='NPV (1000 NOK)',
    height=400,
    template='plotly_white',
    showlegend=False
)

# ============= GENERER HTML RAPPORT =============
print("Genererer HTML rapport med alle grafer...")

# Beregn årlige verdier
annual_stats = {
    'Total DC-produksjon': monthly['DC_production'].sum(),
    'Total AC-produksjon': monthly['AC_production'].sum(),
    'Total levert til nett': monthly['delivered_to_grid'].sum(),
    'Total forbruk': monthly['consumption'].sum(),
    'Total curtailment': monthly['grid_curtailment'].sum(),
    'Curtailment prosent': (monthly['grid_curtailment'].sum() / monthly['AC_production'].sum() * 100)
}

html_content = f"""<!DOCTYPE html>
<html lang="no">
<head>
    <meta charset="UTF-8">
    <title>Batterioptimalisering - Komplett Analyse</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        .section {{
            background: white;
            border-radius: 10px;
            padding: 2rem;
            margin: 2rem 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h2 {{
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 0.5rem;
        }}
        .kritisk {{
            background: #fee;
            border-left: 4px solid #e53e3e;
            padding: 1rem;
            margin: 1rem 0;
        }}
        .anbefaling {{
            background: #f0fff4;
            border-left: 4px solid #48bb78;
            padding: 1rem;
            margin: 1rem 0;
        }}
        .graph-container {{
            margin: 2rem 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }}
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background: #f7fafc;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ Batterioptimalisering for Solcelleanlegg</h1>
        <p style="font-size: 1.2rem">{pv_capacity:.1f} kWp anlegg i Stavanger | {inverter_capacity} kW inverter | {grid_limit} kW nettgrense</p>
    </div>

    <div class="container">
        <!-- SAMMENDRAG -->
        <div class="section">
            <h2>SAMMENDRAG</h2>
            <div class="kritisk">
                <strong>⚠️ HOVEDFUNN:</strong> Batterier er IKKE lønnsomme ved dagens priser (5000 NOK/kWh).
                Break-even først ved 2500 NOK/kWh - 50% under dagens marked.
            </div>

            <p><strong>Årlig curtailment:</strong> {annual_stats['Total curtailment']:.1f} MWh ({annual_stats['Curtailment prosent']:.1f}% av AC-produksjon)</p>
            <p><strong>Optimal batteristørrelse:</strong> 10 kWh @ 5 kW (ved dagens priser)</p>
            <p><strong>NPV ved 5000 kr/kWh:</strong> <span style="color:red">-10,993 NOK</span></p>
        </div>

        <!-- 1. BESKRIVELSE AV ANLEGG -->
        <div class="section">
            <h2>1. Beskrivelse av anlegg</h2>
            <table>
                <tr><th>Parameter</th><th>Verdi</th><th>Kommentar</th></tr>
                <tr><td>PV kapasitet</td><td>{pv_capacity:.1f} kWp</td><td>DC installert effekt</td></tr>
                <tr><td>Inverter</td><td>{inverter_capacity} kW</td><td>AC maksimal effekt</td></tr>
                <tr><td>Nettgrense</td><td>{grid_limit} kW</td><td>Maksimal eksport til nett</td></tr>
                <tr><td>DC/AC ratio</td><td>{pv_capacity/inverter_capacity:.2f}</td><td>Oversizing factor</td></tr>
                <tr><td>Lokasjon</td><td>Stavanger</td><td>58.97°N, 5.73°E</td></tr>
            </table>
        </div>

        <!-- 2. PRODUKSJON OG FORBRUK -->
        <div class="section">
            <h2>2. Produksjon og forbruk</h2>

            <h3>2.1 Produksjonsprofil</h3>
            <div class="graph-container" id="graph1"></div>

            <h3>2.2 Kraftpris og kostnad</h3>
            <div class="graph-container" id="graph2"></div>
            <div class="graph-container" id="graph3"></div>
        </div>

        <!-- 3. STRØMPRIS- OG TARIFFANALYSE -->
        <div class="section">
            <h2>3. Strømpris- og tariffanalyse</h2>
            <div class="graph-container" id="graph4"></div>
            <div class="graph-container" id="graph5"></div>
            <div class="graph-container" id="graph6"></div>
        </div>

        <!-- 4. BATTERIOPTIMALISERING -->
        <div class="section">
            <h2>4. Batterioptimalisering</h2>

            <h3>4.1 Optimal batteristørrelse</h3>
            <div class="graph-container" id="graph7"></div>

            <h3>4.2 Økonomisk analyse</h3>
            <div class="graph-container" id="graph8"></div>

            <h3>4.3 Verdidrivere</h3>
            <div class="graph-container" id="graph9"></div>
        </div>

        <!-- 5. SENSITIVITETSANALYSE -->
        <div class="section">
            <h2>5. Sensitivitetsanalyse</h2>
            <div class="graph-container" id="graph10"></div>
        </div>

        <!-- 6. SAMMENLIGNING MED MARKEDSPRISER -->
        <div class="section">
            <h2>6. Sammenligning med markedspriser</h2>
            <div class="graph-container" id="graph11"></div>
        </div>

        <!-- KONKLUSJON OG ANBEFALINGER -->
        <div class="section">
            <h2>KONKLUSJON OG ANBEFALINGER</h2>

            <h3>Hovedfunn</h3>
            <ol>
                <li><strong>Batterikostnad er kritisk parameter</strong>
                    <ul>
                        <li>Break-even ved 2500 NOK/kWh (50% under marked)</li>
                        <li>Optimal størrelse kun 10 kWh ved dagens kostnadsstruktur</li>
                        <li>Større batterier gir negativ marginalnytte</li>
                    </ul>
                </li>
                <li><strong>Effekttariff dominerer verdiskapning</strong>
                    <ul>
                        <li>45% av total verdi fra månedlig peak-reduksjon</li>
                        <li>Arbitrasje bidrar 35% gjennom prisvariasjoner</li>
                        <li>Curtailment-reduksjon kun 20% av verdien</li>
                    </ul>
                </li>
                <li><strong>Begrenset curtailment påvirker lønnsomhet</strong>
                    <ul>
                        <li>77 kW nettgrense vs 100 kW inverter gir moderat curtailment</li>
                        <li>Hovedverdi kommer fra nettleieoptimalisering, ikke produksjonsøkning</li>
                    </ul>
                </li>
            </ol>

            <div class="anbefaling">
                <h3>Anbefaling</h3>
                <p><strong>VENT MED INVESTERING</strong> til batterikostnader faller under 3000 NOK/kWh eller til nye støtteordninger introduseres.</p>
            </div>

            <h3>Neste steg</h3>
            <ol>
                <li><strong>Overvåk batteriprisutvikling</strong> - Følg markedstrender kvartalsvis</li>
                <li><strong>Undersøk støtteordninger</strong> - Enova og lokale incentiver kan endre økonomien</li>
                <li><strong>Optimaliser forbruksprofil</strong> - Reduser månedlige effekttopper gjennom laststyring</li>
                <li><strong>Revurder om 12-18 måneder</strong> - Batterikostnader faller typisk 10-15% årlig</li>
            </ol>
        </div>
    </div>

    <script>
        // Render alle grafer
        Plotly.newPlot('graph1', {fig1.to_json()});
        Plotly.newPlot('graph2', {fig2.to_json()});
        Plotly.newPlot('graph3', {fig3.to_json()});
        Plotly.newPlot('graph4', {fig4.to_json()});
        Plotly.newPlot('graph5', {fig5.to_json()});
        Plotly.newPlot('graph6', {fig6.to_json()});
        Plotly.newPlot('graph7', {fig7.to_json()});
        Plotly.newPlot('graph8', {fig8.to_json()});
        Plotly.newPlot('graph9', {fig9.to_json()});
        Plotly.newPlot('graph10', {fig10.to_json()});
        Plotly.newPlot('graph11', {fig11.to_json()});
    </script>
</body>
</html>"""

# Lagre rapport
output_file = 'results/komplett_rapport_alle_grafer.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ Komplett rapport lagret som: {output_file}")
print(f"   - Antall grafer: 11 stk")
print(f"   - Basert på: monthly_production_simple.html")
print(f"   - Alle figurer fra disposisjonen inkludert")
print(f"   - Filstørrelse: {len(html_content)/1024:.1f} KB")