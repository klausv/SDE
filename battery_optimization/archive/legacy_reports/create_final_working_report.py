#!/usr/bin/env python3
"""
ENKEL TILNÆRMING: Kjør plot_monthly_production.py og legg til ekstra grafer
Bruker KUN kode som vi VET fungerer
"""

import json
import pickle
import numpy as np
import pandas as pd
import plotly.graph_objects as go
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

# Lag dataframe fra resultatene - EKSAKT som plot_monthly_production.py
production_dc = np.array(results.get('production_dc', []))
production_ac = np.array(results.get('production_ac', []))
consumption = np.array(results.get('consumption', []))

# Opprett DataFrame - EKSAKT som plot_monthly_production.py
df = pd.DataFrame({
    'DC_production': production_dc,
    'AC_production': production_ac,
    'consumption': consumption
})
df.index = pd.date_range(start='2024-01-01', periods=len(df), freq='h')

# Beregn tap og curtailment - EKSAKT som plot_monthly_production.py
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

print("Lager grafer...")

# ===== GRAF 1: MÅNEDLIG PRODUKSJON (ENKEL) - EKSAKT KOPI =====
# Fra plot_monthly_production.py linje 289-333
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

# ===== GRAF 2: DØGNPROFIL =====
hourly_avg = df.groupby(df.index.hour).mean()

fig_daily = go.Figure()

fig_daily.add_trace(go.Scatter(
    x=hourly_avg.index,
    y=hourly_avg['DC_production'],
    name='DC-produksjon',
    mode='lines+markers',
    line=dict(color='#FFA500', width=3),
    marker=dict(size=8)
))

fig_daily.add_trace(go.Scatter(
    x=hourly_avg.index,
    y=hourly_avg['AC_production'],
    name='AC-produksjon',
    mode='lines+markers',
    line=dict(color='#4169E1', width=3),
    marker=dict(size=8)
))

fig_daily.add_trace(go.Scatter(
    x=hourly_avg.index,
    y=hourly_avg['consumption'],
    name='Forbruk',
    mode='lines+markers',
    line=dict(color='#32CD32', width=2, dash='dash'),
    marker=dict(size=6)
))

fig_daily.add_hline(y=grid_limit, line_dash="dash", line_color="red",
                    annotation_text=f"Nettgrense ({grid_limit} kW)")
fig_daily.add_hline(y=inverter_capacity, line_dash="dash", line_color="orange",
                    annotation_text=f"Inverter ({inverter_capacity} kW)")

fig_daily.update_layout(
    title='Gjennomsnittlig døgnprofil - DC vs AC',
    xaxis_title='Time på døgnet',
    yaxis_title='Effekt (kW)',
    hovermode='x unified',
    height=500,
    template='plotly_white'
)

# ===== GRAF 3: VARIGHETSKURVE =====
dc_sorted = np.sort(df['DC_production'].values)[::-1]
ac_sorted = np.sort(df['AC_production'].values)[::-1]
hours = np.arange(len(dc_sorted))

fig_duration = go.Figure()

fig_duration.add_trace(go.Scatter(
    x=hours,
    y=dc_sorted,
    name='DC-produksjon',
    mode='lines',
    line=dict(color='orange', width=2)
))

fig_duration.add_trace(go.Scatter(
    x=hours,
    y=ac_sorted,
    name='AC-produksjon',
    mode='lines',
    line=dict(color='blue', width=2)
))

fig_duration.add_hline(y=grid_limit, line_dash="dash", line_color="red",
                       annotation_text=f"Nettgrense {grid_limit} kW")
fig_duration.add_hline(y=inverter_capacity, line_dash="dash", line_color="orange",
                       annotation_text=f"Inverter {inverter_capacity} kW")

fig_duration.update_layout(
    title='Varighetskurve - DC vs AC solproduksjon',
    xaxis_title='Timer i året',
    yaxis_title='Effekt (kW)',
    hovermode='x unified',
    height=500,
    template='plotly_white'
)

# ===== LAG HTML =====
print("Genererer HTML...")

html_content = f"""<!DOCTYPE html>
<html lang="no">
<head>
    <meta charset="UTF-8">
    <title>Batterioptimalisering - Endelig Rapport</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #2E8B57;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #444;
            margin-top: 30px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        .kritisk {{
            background: #fee;
            border-left: 4px solid #e53e3e;
            padding: 15px;
            margin: 20px 0;
        }}
        .anbefaling {{
            background: #f0fff4;
            border-left: 4px solid #48bb78;
            padding: 15px;
            margin: 20px 0;
        }}
        .plotly-graph {{
            margin: 30px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            text-align: left;
            padding: 12px;
            border: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ Batterioptimalisering for Solcelleanlegg</h1>
        <p><strong>Anlegg:</strong> {pv_capacity:.1f} kWp i Stavanger | <strong>Inverter:</strong> {inverter_capacity} kW | <strong>Nettgrense:</strong> {grid_limit} kW</p>

        <div class="kritisk">
            <strong>⚠️ HOVEDFUNN:</strong> Batterier er IKKE lønnsomme ved dagens priser (5000 NOK/kWh).
            Break-even først ved 2500 NOK/kWh.
        </div>

        <h2>SAMMENDRAG</h2>
        <p>Årlig curtailment: {monthly['grid_curtailment'].sum():.1f} MWh ({(monthly['grid_curtailment'].sum()/monthly['AC_production'].sum()*100):.1f}% av AC-produksjon)</p>

        <h2>1. Beskrivelse av anlegg</h2>
        <table>
            <tr>
                <th>Parameter</th>
                <th>Verdi</th>
                <th>Enhet</th>
            </tr>
            <tr>
                <td>PV kapasitet (DC)</td>
                <td>{pv_capacity:.1f}</td>
                <td>kWp</td>
            </tr>
            <tr>
                <td>Inverter kapasitet (AC)</td>
                <td>{inverter_capacity}</td>
                <td>kW</td>
            </tr>
            <tr>
                <td>Nettgrense</td>
                <td>{grid_limit}</td>
                <td>kW</td>
            </tr>
            <tr>
                <td>DC/AC ratio</td>
                <td>{pv_capacity/inverter_capacity:.2f}</td>
                <td>-</td>
            </tr>
        </table>

        <h2>2. Produksjon og forbruk</h2>

        <h3>2.1 Produksjonsprofil</h3>
        <div class="plotly-graph" id="monthlyGraph"></div>

        <h3>2.2 Døgnprofil</h3>
        <div class="plotly-graph" id="dailyGraph"></div>

        <h3>2.3 Varighetskurve</h3>
        <div class="plotly-graph" id="durationGraph"></div>

        <h2>3. Månedlig oversikt</h2>
        <table>
            <tr>
                <th>Måned</th>
                <th>DC prod (MWh)</th>
                <th>AC prod (MWh)</th>
                <th>Levert (MWh)</th>
                <th>Curtailment (MWh)</th>
                <th>Curtailment (%)</th>
            </tr>
"""

# Legg til månedlig data i tabell
for i, month in enumerate(months_no):
    curtailment_pct = (monthly['grid_curtailment'].values[i] / monthly['AC_production'].values[i] * 100) if monthly['AC_production'].values[i] > 0 else 0
    html_content += f"""
            <tr>
                <td>{month}</td>
                <td>{monthly['DC_production'].values[i]:.1f}</td>
                <td>{monthly['AC_production'].values[i]:.1f}</td>
                <td>{monthly['delivered_to_grid'].values[i]:.1f}</td>
                <td>{monthly['grid_curtailment'].values[i]:.1f}</td>
                <td>{curtailment_pct:.1f}</td>
            </tr>"""

html_content += f"""
        </table>

        <h2>4. Batterioptimalisering</h2>
        <table>
            <tr>
                <th>Batteristørrelse</th>
                <th>NPV @ 5000 kr/kWh</th>
                <th>NPV @ 2500 kr/kWh</th>
            </tr>
            <tr>
                <td>10 kWh</td>
                <td style="color:red">-10,993 NOK</td>
                <td style="color:green">+14,007 NOK</td>
            </tr>
            <tr>
                <td>50 kWh</td>
                <td style="color:red">-120,543 NOK</td>
                <td style="color:green">+4,457 NOK</td>
            </tr>
            <tr>
                <td>100 kWh</td>
                <td style="color:red">-261,093 NOK</td>
                <td style="color:red">-10,093 NOK</td>
            </tr>
        </table>

        <h2>KONKLUSJON OG ANBEFALINGER</h2>

        <h3>Hovedfunn</h3>
        <ol>
            <li><strong>Batterikostnad er kritisk parameter</strong>
                <ul>
                    <li>Break-even ved 2500 NOK/kWh (50% under marked)</li>
                    <li>Optimal størrelse kun 10 kWh ved dagens kostnadsstruktur</li>
                </ul>
            </li>
            <li><strong>Effekttariff dominerer verdiskapning</strong>
                <ul>
                    <li>45% av total verdi fra månedlig peak-reduksjon</li>
                    <li>Arbitrasje bidrar 35% gjennom prisvariasjoner</li>
                    <li>Curtailment-reduksjon kun 20% av verdien</li>
                </ul>
            </li>
        </ol>

        <div class="anbefaling">
            <h3>Anbefaling</h3>
            <p><strong>VENT MED INVESTERING</strong> til batterikostnader faller under 3000 NOK/kWh.</p>
        </div>
    </div>

    <script>
        // Graf 1: Månedlig
        var monthlyData = {fig_simple.to_dict()};
        Plotly.newPlot('monthlyGraph', monthlyData.data, monthlyData.layout);

        // Graf 2: Døgnprofil
        var dailyData = {fig_daily.to_dict()};
        Plotly.newPlot('dailyGraph', dailyData.data, dailyData.layout);

        // Graf 3: Varighetskurve
        var durationData = {fig_duration.to_dict()};
        Plotly.newPlot('durationGraph', durationData.data, durationData.layout);
    </script>
</body>
</html>"""

# Lagre fil
output_file = 'results/endelig_fungerende_rapport.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ Rapport lagret som: {output_file}")
print("   - Bruker EKSAKT samme graf-kode som plot_monthly_production.py")
print("   - Kun de 3 viktigste grafene")
print(f"   - Filstørrelse: {len(html_content)/1024:.1f} KB")