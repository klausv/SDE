#!/usr/bin/env python3
"""
Lager ALLE plott fra figurlista som SEPARATE HTML-filer
Bruker samme tilnærming som plot_monthly_production.py som FUNGERER
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
consumption = np.array(results.get('consumption', []))
prices = np.array(results.get('prices', []))

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

# ========== PLOTT 1: MÅNEDLIG (ENKEL) ==========
print("Lager månedlig plott...")
monthly = df.resample('ME').agg({
    'DC_production': 'sum',
    'AC_production': 'sum',
    'delivered_to_grid': 'sum',
    'consumption': 'sum',
    'inverter_clipping': 'sum',
    'grid_curtailment': 'sum'
})
monthly = monthly / 1000

months_no = ['Januar', 'Februar', 'Mars', 'April', 'Mai', 'Juni',
             'Juli', 'August', 'September', 'Oktober', 'November', 'Desember']

fig1 = go.Figure()

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

fig1.write_html('results/fig1_monthly.html')
print("✅ Lagret: results/fig1_monthly.html")

# ========== PLOTT 2: DØGNPROFIL ==========
print("Lager døgnprofil...")
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
    height=500,
    template='plotly_white'
)

fig2.write_html('results/fig2_daily_profile.html')
print("✅ Lagret: results/fig2_daily_profile.html")

# ========== PLOTT 3: VARIGHETSKURVE ==========
print("Lager varighetskurve...")
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
    height=500,
    template='plotly_white'
)

fig3.write_html('results/fig3_duration_curve.html')
print("✅ Lagret: results/fig3_duration_curve.html")

# ========== PLOTT 4: EFFEKTTARIFF ==========
print("Lager effekttariff plott...")
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
               annotation_text="Typisk peak uten batteri")
fig4.add_vline(x=72, line_dash="dash", line_color="blue",
               annotation_text="Med 10 kWh batteri")

fig4.update_layout(
    title='Effekttariff struktur (Lnett) - Intervallbasert',
    xaxis_title='Effekt (kW)',
    yaxis_title='NOK/måned',
    hovermode='x unified',
    height=500,
    template='plotly_white'
)

fig4.write_html('results/fig4_power_tariff.html')
print("✅ Lagret: results/fig4_power_tariff.html")

# ========== PLOTT 5: MAI ANALYSE ==========
print("Lager mai analyse...")
may_data = df['2024-05-01':'2024-05-31']

fig5 = go.Figure()

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

fig5.update_layout(
    title='Systemanalyse Mai 2024',
    xaxis_title='Dato',
    yaxis_title='Effekt (kW)',
    hovermode='x unified',
    height=500,
    template='plotly_white'
)

fig5.write_html('results/fig5_may_analysis.html')
print("✅ Lagret: results/fig5_may_analysis.html")

# ========== PLOTT 6: 15. JUNI ==========
print("Lager 15. juni plott...")
june15 = df.loc['2024-06-15']

fig6 = go.Figure()

fig6.add_trace(go.Bar(
    x=june15.index.hour,
    y=june15['delivered_to_grid'],
    name='Levert til nett',
    marker_color='#2E8B57'
))

fig6.add_trace(go.Bar(
    x=june15.index.hour,
    y=june15['grid_curtailment'],
    name='Curtailment',
    marker_color='#DC143C'
))

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

fig6.update_layout(
    title='Representativ dag - 15. juni 2024',
    xaxis_title='Time',
    yaxis_title='kW',
    barmode='stack',
    hovermode='x unified',
    height=500,
    template='plotly_white'
)

fig6.write_html('results/fig6_june15.html')
print("✅ Lagret: results/fig6_june15.html")

# ========== PLOTT 7: NPV VS BATTERISTØRRELSE ==========
print("Lager NPV plott...")
battery_sizes = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
npv_5000 = [0, -11, -31, -52, -73, -93, -114, -134, -155, -175, -196]
npv_2500 = [0, 15, 22, 30, 37, 45, 52, 60, 67, 75, 82]

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
    height=500,
    template='plotly_white'
)

fig7.write_html('results/fig7_npv.html')
print("✅ Lagret: results/fig7_npv.html")

# ========== PLOTT 8: KONTANTSTRØM ==========
print("Lager kontantstrøm plott...")
years = list(range(2025, 2040))
cashflow = [-50, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3]

fig8 = go.Figure()

fig8.add_trace(go.Bar(
    x=years,
    y=cashflow,
    name='Årlig kontantstrøm',
    marker_color=['red'] + ['green']*14
))

fig8.update_layout(
    title='Kontantstrøm over batteriets levetid (10 kWh)',
    xaxis_title='År',
    yaxis_title='Årlig kontantstrøm (1000 NOK)',
    hovermode='x unified',
    height=500,
    template='plotly_white'
)

fig8.write_html('results/fig8_cashflow.html')
print("✅ Lagret: results/fig8_cashflow.html")

# ========== PLOTT 9: VERDIDRIVERE PIE ==========
print("Lager verdidrivere plott...")

fig9 = go.Figure()

fig9.add_trace(go.Pie(
    labels=['Effekttariff', 'Arbitrasje', 'Curtailment'],
    values=[45, 35, 20],
    hole=0.3,
    marker=dict(colors=['#FF6B6B', '#4ECDC4', '#95E1D3'])
))

fig9.update_layout(
    title='Fordeling av verdidrivere',
    height=500,
    template='plotly_white'
)

fig9.write_html('results/fig9_value_drivers.html')
print("✅ Lagret: results/fig9_value_drivers.html")

print("\n" + "="*60)
print("ALLE PLOTT LAGRET SOM SEPARATE FILER:")
print("="*60)
print("1. fig1_monthly.html - Månedlig produksjon")
print("2. fig2_daily_profile.html - Døgnprofil")
print("3. fig3_duration_curve.html - Varighetskurve")
print("4. fig4_power_tariff.html - Effekttariff")
print("5. fig5_may_analysis.html - Mai analyse")
print("6. fig6_june15.html - 15. juni")
print("7. fig7_npv.html - NPV analyse")
print("8. fig8_cashflow.html - Kontantstrøm")
print("9. fig9_value_drivers.html - Verdidrivere")
print("\nÅpne hver fil separat i nettleseren for å se plottene.")