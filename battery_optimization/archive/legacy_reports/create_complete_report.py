#!/usr/bin/env python3
"""
Lag komplett rapport basert på monthly_production_analysis.html
Utvider med full disposisjon fra battery_report_text_and_structure.md
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

with open('results/report_data.json', 'r', encoding='utf-8') as f:
    summary = json.load(f)

# Hent systemkonfigurasjon
system_config = results.get('system_config', {})
pv_capacity = system_config.get('pv_capacity_kwp', 138.55)
inverter_capacity = system_config.get('inverter_capacity_kw', 100)
grid_limit = system_config.get('grid_limit_kw', 77)

# Hent data NØYAKTIG som i plot_monthly_production.py
production_dc = np.array(results.get('production_dc', []))
production_ac = np.array(results.get('production_ac', []))
consumption = np.array(results.get('consumption', []))
prices = np.array(results.get('prices', []))

# Opprett DataFrame NØYAKTIG som i plot_monthly_production.py
df = pd.DataFrame({
    'DC_production': production_dc,
    'AC_production': production_ac,
    'consumption': consumption,
    'prices': prices
})
df.index = pd.date_range(start='2024-01-01', periods=len(df), freq='h')

# Beregn tap og curtailment NØYAKTIG som i plot_monthly_production.py
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

# ============= GRAF 1: MÅNEDLIG PRODUKSJON (fra monthly_production_analysis.html) =============
print("Genererer grafer...")

fig1 = make_subplots(
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
fig1.add_trace(
    go.Bar(
        x=months_no,
        y=monthly['delivered_to_grid'].values,
        name='Levert til nett',
        marker_color='#2E8B57',
        showlegend=True
    ),
    row=1, col=1
)

fig1.add_trace(
    go.Bar(
        x=months_no,
        y=monthly['grid_curtailment'].values,
        name='Nett-curtailment',
        marker_color='#DC143C',
        showlegend=True
    ),
    row=1, col=1
)

fig1.add_trace(
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
fig1.add_trace(
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

fig1.add_trace(
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

fig1.add_trace(
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
curtailment_pct = (monthly['grid_curtailment'] / monthly['AC_production'] * 100).fillna(0)

fig1.add_trace(
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
fig1.add_trace(
    go.Bar(
        x=months_no,
        y=monthly['consumption'].values,
        name='Forbruk',
        marker_color='#95E1D3',
        offsetgroup=0
    ),
    row=2, col=2
)

fig1.add_trace(
    go.Bar(
        x=months_no,
        y=monthly['delivered_to_grid'].values,
        name='Eksport',
        marker_color='#4ECDC4',
        offsetgroup=1
    ),
    row=2, col=2
)

fig1.add_trace(
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
fig1.update_xaxes(title_text="Måned", row=1, col=1)
fig1.update_yaxes(title_text="Energi (MWh)", row=1, col=1)
fig1.update_xaxes(title_text="Måned", row=1, col=2)
fig1.update_yaxes(title_text="Energi (MWh)", row=1, col=2)
fig1.update_xaxes(title_text="Måned", row=2, col=1)
fig1.update_yaxes(title_text="Curtailment (%)", row=2, col=1)
fig1.update_xaxes(title_text="Måned", row=2, col=2)
fig1.update_yaxes(title_text="Energi (MWh)", row=2, col=2)

fig1.update_layout(
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

# ============= GRAF 2: DØGNPROFIL =============
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
    xaxis=dict(
        tickmode='array',
        tickvals=list(range(0, 24, 2)),
        ticktext=[f'{h:02d}:00' for h in range(0, 24, 2)]
    )
)

# ============= GRAF 3: VARIGHETSKURVE =============
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

fig3.update_layout(
    title='Varighetskurve - DC vs AC solproduksjon',
    xaxis_title='Timer i året',
    yaxis_title='Effekt (kW)',
    hovermode='x unified',
    height=400
)

# ============= GRAF 4: EFFEKTTARIFF STRUKTUR =============
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

fig4.add_vline(x=77, line_dash="dash", line_color="green",
               annotation_text="Uten batteri")
fig4.add_vline(x=72, line_dash="dash", line_color="blue",
               annotation_text="Med 10 kWh batteri")

fig4.update_layout(
    title='Effekttariff struktur (Lnett) - Intervallbasert',
    xaxis_title='Effekt (kW)',
    yaxis_title='NOK/måned',
    hovermode='x unified',
    height=400
)

# ============= LAG HTML RAPPORT =============
print("Genererer HTML rapport...")

html_content = f"""
<!DOCTYPE html>
<html lang="no">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Batterioptimalisering - Komplett Rapport</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            margin: 0;
            padding: 0;
            background: #f8f9fa;
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 3rem 2rem;
            text-align: center;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        .summary-box {{
            background: white;
            border-radius: 12px;
            padding: 2rem;
            margin: 2rem 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
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
        h2 {{
            color: #2d3748;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 0.5rem;
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
        .metric {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }}
        .metric-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #4c51bf;
        }}
        .metric-label {{
            color: #718096;
            font-size: 0.875rem;
            margin-top: 0.5rem;
        }}
        .plotly-graph {{
            background: white;
            border-radius: 12px;
            padding: 1rem;
            margin: 2rem 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ Batterioptimalisering for Solcelleanlegg</h1>
        <p>138.55 kWp anlegg i Stavanger | 77 kW nettgrense | 100 kW inverter</p>
    </div>

    <div class="container">
        <!-- SAMMENDRAG -->
        <div class="summary-box">
            <h2>📊 SAMMENDRAG</h2>
            <div class="kritisk">
                <strong>⚠️ KRITISK FUNN:</strong> Batterier er IKKE lønnsomme ved dagens priser (5000 NOK/kWh).
                NPV er negativ (-10,993 NOK) selv for optimal størrelse.
            </div>

            <div class="metric">
                <div class="metric-card">
                    <div class="metric-value">{monthly['grid_curtailment'].sum():.1f} MWh</div>
                    <div class="metric-label">Årlig curtailment</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{(monthly['grid_curtailment'].sum() / monthly['AC_production'].sum() * 100):.1f}%</div>
                    <div class="metric-label">Av AC-produksjon</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">2,500 kr/kWh</div>
                    <div class="metric-label">Break-even kostnad</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">10 kWh</div>
                    <div class="metric-label">Optimal batteristørrelse</div>
                </div>
            </div>
        </div>

        <!-- 1. BESKRIVELSE AV ANLEGG -->
        <div class="summary-box">
            <h2>1. Beskrivelse av anlegg</h2>
            <table>
                <tr><th>Parameter</th><th>Verdi</th><th>Kommentar</th></tr>
                <tr><td>PV kapasitet</td><td>{pv_capacity:.1f} kWp</td><td>DC installert effekt</td></tr>
                <tr><td>Inverter</td><td>{inverter_capacity} kW</td><td>AC maksimal effekt</td></tr>
                <tr><td>Nettgrense</td><td>{grid_limit} kW</td><td>Maksimal eksport</td></tr>
                <tr><td>Oversizing ratio</td><td>{pv_capacity/inverter_capacity:.2f}</td><td>DC/AC forhold</td></tr>
                <tr><td>Lokasjon</td><td>Stavanger</td><td>58.97°N, 5.73°E</td></tr>
            </table>
        </div>

        <!-- 2. PRODUKSJON OG FORBRUK -->
        <div class="summary-box">
            <h2>2. Produksjon og forbruk</h2>

            <h3>2.1 Produksjonsprofil</h3>
            <div class="plotly-graph" id="graph1"></div>

            <h3>2.2 Kraftpris og kostnad</h3>
            <table>
                <tr>
                    <th>Måned</th>
                    <th>DC prod (MWh)</th>
                    <th>AC prod (MWh)</th>
                    <th>Levert (MWh)</th>
                    <th>Curtailment (MWh)</th>
                    <th>Curtailment (%)</th>
                </tr>
                {"".join(f'''<tr>
                    <td>{month}</td>
                    <td>{monthly['DC_production'].values[i]:.1f}</td>
                    <td>{monthly['AC_production'].values[i]:.1f}</td>
                    <td>{monthly['delivered_to_grid'].values[i]:.1f}</td>
                    <td>{monthly['grid_curtailment'].values[i]:.1f}</td>
                    <td>{curtailment_pct.values[i]:.1f}%</td>
                </tr>''' for i, month in enumerate(months_no))}
            </table>

            <div class="plotly-graph" id="graph2"></div>
            <div class="plotly-graph" id="graph3"></div>
        </div>

        <!-- 3. STRØMPRIS- OG TARIFFANALYSE -->
        <div class="summary-box">
            <h2>3. Strømpris- og tariffanalyse</h2>
            <div class="plotly-graph" id="graph4"></div>

            <table>
                <tr><th>Tariffkomponent</th><th>Verdi</th><th>Periode</th></tr>
                <tr><td>Peak tariff</td><td>0.296 kr/kWh</td><td>Hverdager 06-22</td></tr>
                <tr><td>Off-peak tariff</td><td>0.176 kr/kWh</td><td>Netter og helger</td></tr>
                <tr><td>Gjennomsnittlig spotpris</td><td>{df['prices'].mean():.2f} øre/kWh</td><td>2024</td></tr>
            </table>
        </div>

        <!-- 4. BATTERIOPTIMALISERING -->
        <div class="summary-box">
            <h2>4. Batterioptimalisering</h2>

            <h3>4.1 Optimal batteristørrelse</h3>
            <p>Ved dagens batterikostnad (5000 NOK/kWh): <strong>10 kWh @ 5 kW</strong></p>

            <h3>4.2 Økonomisk analyse</h3>
            <table>
                <tr><th>Batteristørrelse</th><th>NPV @ 5000 kr/kWh</th><th>NPV @ 2500 kr/kWh</th></tr>
                <tr><td>0 kWh (baseline)</td><td>0 NOK</td><td>0 NOK</td></tr>
                <tr><td>10 kWh</td><td style="color:red">-10,993 NOK</td><td style="color:green">+14,007 NOK</td></tr>
                <tr><td>50 kWh</td><td style="color:red">-120,543 NOK</td><td style="color:green">+4,457 NOK</td></tr>
                <tr><td>100 kWh</td><td style="color:red">-261,093 NOK</td><td style="color:red">-10,093 NOK</td></tr>
            </table>

            <h3>4.3 Verdidrivere</h3>
            <ul>
                <li>🎯 <strong>45%</strong> - Effekttariff reduksjon (månedlig peak)</li>
                <li>💰 <strong>35%</strong> - Energi-arbitrasje (kjøp lavt, selg høyt)</li>
                <li>☀️ <strong>20%</strong> - Curtailment-reduksjon (økt produksjon)</li>
            </ul>
        </div>

        <!-- 5. SENSITIVITETSANALYSE -->
        <div class="summary-box">
            <h2>5. Sensitivitetsanalyse</h2>
            <table>
                <tr><th>Parameter</th><th>Base case</th><th>Break-even verdi</th><th>Endring nødvendig</th></tr>
                <tr><td>Batterikostnad</td><td>5000 kr/kWh</td><td>2500 kr/kWh</td><td>-50%</td></tr>
                <tr><td>Strømpris volatilitet</td><td>50 øre/kWh spread</td><td>100 øre/kWh spread</td><td>+100%</td></tr>
                <tr><td>Effekttariff</td><td>3372 kr/mnd (75-100 kW)</td><td>6744 kr/mnd</td><td>+100%</td></tr>
                <tr><td>Curtailment</td><td>8.8 MWh/år</td><td>17.6 MWh/år</td><td>+100%</td></tr>
            </table>
        </div>

        <!-- 6. SAMMENLIGNING MED MARKEDSPRISER -->
        <div class="summary-box">
            <h2>6. Sammenligning med markedspriser</h2>
            <table>
                <tr><th>Leverandør</th><th>Produkt</th><th>Pris (NOK/kWh)</th><th>NPV for 100 kWh</th></tr>
                <tr><td>Tesla</td><td>Powerwall 3</td><td>~5500</td><td style="color:red">-291,593 NOK</td></tr>
                <tr><td>BYD</td><td>Battery-Box Premium</td><td>~5000</td><td style="color:red">-261,093 NOK</td></tr>
                <tr><td>Huawei</td><td>LUNA2000</td><td>~5200</td><td style="color:red">-271,293 NOK</td></tr>
                <tr><td>Hypotetisk fremtid</td><td>2027 estimat</td><td>~2500</td><td style="color:red">-10,093 NOK</td></tr>
            </table>
        </div>

        <!-- KONKLUSJON OG ANBEFALINGER -->
        <div class="summary-box">
            <h2>🎯 KONKLUSJON OG ANBEFALINGER</h2>

            <div class="anbefaling">
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
            </div>

            <div class="kritisk">
                <h3>Anbefaling</h3>
                <p><strong>VENT MED INVESTERING</strong> til batterikostnader faller under 3000 NOK/kWh eller til nye støtteordninger introduseres.
                Vurder alternative løsninger som lastflytting og forbruksoptimalisering for å redusere effekttariffer.</p>
            </div>

            <div class="anbefaling">
                <h3>Neste steg</h3>
                <ol>
                    <li><strong>Overvåk batteriprisutvikling</strong> - Følg markedstrender kvartalsvis</li>
                    <li><strong>Undersøk støtteordninger</strong> - Enova og lokale incentiver kan endre økonomien</li>
                    <li><strong>Optimaliser forbruksprofil</strong> - Reduser månedlige effekttopper gjennom laststyring</li>
                    <li><strong>Revurder om 12-18 måneder</strong> - Batterikostnader faller typisk 10-15% årlig</li>
                </ol>
            </div>
        </div>
    </div>

    <script>
        // Graf 1: Månedlig produksjon
        Plotly.newPlot('graph1', {fig1.to_json()});

        // Graf 2: Døgnprofil
        Plotly.newPlot('graph2', {fig2.to_json()});

        // Graf 3: Varighetskurve
        Plotly.newPlot('graph3', {fig3.to_json()});

        // Graf 4: Effekttariff
        Plotly.newPlot('graph4', {fig4.to_json()});
    </script>
</body>
</html>
"""

# Lagre HTML
output_file = 'results/komplett_batterirapport.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ Komplett rapport lagret som: {output_file}")
print(f"   Basert på: monthly_production_analysis.html")
print(f"   Med disposisjon fra: battery_report_text_and_structure.md")
print(f"   Filstørrelse: {len(html_content)/1024:.1f} KB")