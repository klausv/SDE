#!/usr/bin/env python3
"""
Generer rapport med EKSAKT samme kode som plot_monthly_production.py
Legger til disposisjonstekst etterpå
"""

import json
import pickle
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Last inn resultater - EKSAKT som plot_monthly_production.py
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

# Aggreger månedlig - EKSAKT som plot_monthly_production.py
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

# Norske månedsnavn - EKSAKT som plot_monthly_production.py
months_no = ['Januar', 'Februar', 'Mars', 'April', 'Mai', 'Juni',
             'Juli', 'August', 'September', 'Oktober', 'November', 'Desember']

# Lag figur med flere visualiseringer - EKSAKT KOPI fra plot_monthly_production.py
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

# ========= OPPDATER LAYOUT - EKSAKT fra plot_monthly_production.py =========
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

# Konverter til HTML
graph_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

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

# Beregn årlige verdier
annual_stats = {
    'Total DC-produksjon': monthly['DC_production'].sum(),
    'Total AC-produksjon': monthly['AC_production'].sum(),
    'Total levert til nett': monthly['delivered_to_grid'].sum(),
    'Total forbruk': monthly['consumption'].sum(),
    'Total inverter-clipping': monthly['inverter_clipping'].sum(),
    'Total nett-curtailment': monthly['grid_curtailment'].sum(),
    'Systemvirkningsgrad': (monthly['delivered_to_grid'].sum() / monthly['DC_production'].sum() * 100)
}

# Generer HTML-rapport
html_content = f"""<!DOCTYPE html>
<html lang="no">
<head>
    <meta charset="UTF-8">
    <title>Batterioptimalisering - Fullstendig Rapport</title>
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
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            text-align: left;
            padding: 12px;
            border: 1px solid #ddd;
        }}
        th {{
            background-color: #2E8B57;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
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
        .summary-box {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ Batterioptimalisering for Solcelleanlegg</h1>
        <p><strong>Anlegg:</strong> {pv_capacity:.1f} kWp i Stavanger | <strong>Inverter:</strong> {inverter_capacity} kW | <strong>Nettgrense:</strong> {grid_limit} kW</p>

        <!-- SAMMENDRAG -->
        <div class="summary-box">
            <h2>SAMMENDRAG</h2>
            <div class="kritisk">
                <strong>⚠️ KRITISK:</strong> Batterier er IKKE lønnsomme ved dagens priser (5000 NOK/kWh).
                Break-even krever 50% prisreduksjon til 2500 NOK/kWh.
            </div>

            <p><strong>Nøkkeltall:</strong></p>
            <ul>
                <li>Årlig curtailment: {annual_stats['Total nett-curtailment']:.1f} MWh ({(annual_stats['Total nett-curtailment']/annual_stats['Total AC-produksjon']*100):.1f}%)</li>
                <li>Systemvirkningsgrad: {annual_stats['Systemvirkningsgrad']:.1f}%</li>
                <li>Optimal batteristørrelse ved dagens priser: 10 kWh</li>
                <li>NPV ved 5000 kr/kWh: -10,993 NOK</li>
            </ul>
        </div>

        <!-- 1. BESKRIVELSE AV ANLEGG -->
        <h2>1. Beskrivelse av anlegg</h2>
        <table>
            <tr><th>Parameter</th><th>Verdi</th><th>Enhet</th></tr>
            <tr><td>PV kapasitet (DC)</td><td>{pv_capacity:.1f}</td><td>kWp</td></tr>
            <tr><td>Inverter kapasitet (AC)</td><td>{inverter_capacity}</td><td>kW</td></tr>
            <tr><td>Nettgrense</td><td>{grid_limit}</td><td>kW</td></tr>
            <tr><td>DC/AC ratio</td><td>{pv_capacity/inverter_capacity:.2f}</td><td>-</td></tr>
            <tr><td>Lokasjon</td><td>Stavanger</td><td>58.97°N, 5.73°E</td></tr>
        </table>

        <!-- 2. PRODUKSJON OG FORBRUK -->
        <h2>2. Produksjon og forbruk</h2>

        <h3>2.1 Produksjonsprofil</h3>
        {graph_html}

        <h3>2.2 Månedlig oversikt</h3>
        <table>
            <tr>
                <th>Måned</th>
                <th>DC prod (MWh)</th>
                <th>AC prod (MWh)</th>
                <th>Levert (MWh)</th>
                <th>Forbruk (MWh)</th>
                <th>Curtailment (MWh)</th>
                <th>Curtailment (%)</th>
            </tr>
            {''.join(f"<tr><td>{row['Måned']}</td><td>{row['DC prod (MWh)']}</td><td>{row['AC prod (MWh)']}</td><td>{row['Levert (MWh)']}</td><td>{row['Forbruk (MWh)']}</td><td>{row['Curtailment (MWh)']}</td><td>{row['Curtailment (%)']}</td></tr>" for _, row in summary_df.iterrows())}
        </table>

        <!-- 3. STRØMPRIS- OG TARIFFANALYSE -->
        <h2>3. Strømpris- og tariffanalyse</h2>
        <table>
            <tr><th>Tariffkomponent</th><th>Verdi</th><th>Periode</th></tr>
            <tr><td>Peak tariff</td><td>0.296 kr/kWh</td><td>Hverdager 06-22</td></tr>
            <tr><td>Off-peak tariff</td><td>0.176 kr/kWh</td><td>Netter og helger</td></tr>
            <tr><td>Effekttariff 75-100 kW</td><td>3372 kr/mnd</td><td>Månedlig peak</td></tr>
        </table>

        <!-- 4. BATTERIOPTIMALISERING -->
        <h2>4. Batterioptimalisering</h2>

        <h3>4.1 Optimal batteristørrelse</h3>
        <p>Ved dagens batterikostnad (5000 NOK/kWh): <strong>10 kWh @ 5 kW</strong></p>

        <h3>4.2 Økonomisk analyse</h3>
        <table>
            <tr><th>Batteristørrelse</th><th>NPV @ 5000 kr/kWh</th><th>NPV @ 2500 kr/kWh</th></tr>
            <tr><td>10 kWh</td><td style="color:red">-10,993 NOK</td><td style="color:green">+14,007 NOK</td></tr>
            <tr><td>50 kWh</td><td style="color:red">-120,543 NOK</td><td style="color:green">+4,457 NOK</td></tr>
            <tr><td>100 kWh</td><td style="color:red">-261,093 NOK</td><td style="color:red">-10,093 NOK</td></tr>
        </table>

        <h3>4.3 Verdidrivere</h3>
        <ul>
            <li>45% - Effekttariff reduksjon</li>
            <li>35% - Energi-arbitrasje</li>
            <li>20% - Curtailment-reduksjon</li>
        </ul>

        <!-- 5. SENSITIVITETSANALYSE -->
        <h2>5. Sensitivitetsanalyse</h2>
        <table>
            <tr><th>Parameter</th><th>Base case</th><th>Break-even</th><th>Endring nødvendig</th></tr>
            <tr><td>Batterikostnad</td><td>5000 kr/kWh</td><td>2500 kr/kWh</td><td>-50%</td></tr>
            <tr><td>Strømprisvolatilitet</td><td>50 øre/kWh</td><td>100 øre/kWh</td><td>+100%</td></tr>
            <tr><td>Effekttariff</td><td>3372 kr/mnd</td><td>6744 kr/mnd</td><td>+100%</td></tr>
        </table>

        <!-- 6. SAMMENLIGNING MED MARKEDSPRISER -->
        <h2>6. Sammenligning med markedspriser</h2>
        <p>Markedspriser ligger typisk på 5000-5500 NOK/kWh, som gir negativ NPV for alle batteristørrelser.</p>

        <!-- KONKLUSJON OG ANBEFALINGER -->
        <h2>KONKLUSJON OG ANBEFALINGER</h2>

        <div class="summary-box">
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

        <div class="anbefaling">
            <h3>Anbefaling</h3>
            <p><strong>VENT MED INVESTERING</strong> til batterikostnader faller under 3000 NOK/kWh eller til nye støtteordninger introduseres.
            Vurder alternative løsninger som lastflytting og forbruksoptimalisering for å redusere effekttariffer.</p>
        </div>

        <div class="summary-box">
            <h3>Neste steg</h3>
            <ol>
                <li><strong>Overvåk batteriprisutvikling</strong> - Følg markedstrender kvartalsvis</li>
                <li><strong>Undersøk støtteordninger</strong> - Enova og lokale incentiver kan endre økonomien</li>
                <li><strong>Optimaliser forbruksprofil</strong> - Reduser månedlige effekttopper gjennom laststyring</li>
                <li><strong>Revurder om 12-18 måneder</strong> - Batterikostnader faller typisk 10-15% årlig</li>
            </ol>
        </div>

        <!-- ÅRLIG OPPSUMMERING -->
        <h2>Årlig oppsummering</h2>
        <table>
            <tr><th>Parameter</th><th>Verdi</th></tr>
            <tr><td>Total DC-produksjon</td><td>{annual_stats['Total DC-produksjon']:.1f} MWh</td></tr>
            <tr><td>Total AC-produksjon</td><td>{annual_stats['Total AC-produksjon']:.1f} MWh</td></tr>
            <tr><td>Total levert til nett</td><td>{annual_stats['Total levert til nett']:.1f} MWh</td></tr>
            <tr><td>Total forbruk</td><td>{annual_stats['Total forbruk']:.1f} MWh</td></tr>
            <tr><td>Total inverter-clipping</td><td>{annual_stats['Total inverter-clipping']:.1f} MWh</td></tr>
            <tr><td>Total nett-curtailment</td><td>{annual_stats['Total nett-curtailment']:.1f} MWh</td></tr>
            <tr><td>Systemvirkningsgrad</td><td>{annual_stats['Systemvirkningsgrad']:.1f}%</td></tr>
        </table>
    </div>
</body>
</html>"""

# Lagre fil
output_file = 'results/fungerende_fullstendig_rapport.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ Rapport lagret som: {output_file}")
print("   - Grafer: EKSAKT kopi fra plot_monthly_production.py")
print("   - Disposisjon: Fra battery_report_text_and_structure.md")
print(f"   - Filstørrelse: {len(html_content)/1024:.1f} KB")