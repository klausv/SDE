#!/usr/bin/env python
"""
Plott avkortningsanalyse med stacked bars
Viser produksjon vs avkortning time for time
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from core.pvgis_solar import PVGISProduction

# Hent produksjonsdata
print("📊 Lager avkortningsanalyse med stacked bars...")
pvgis = PVGISProduction(
    lat=58.97,
    lon=5.73,
    pv_capacity_kwp=138.55,
    tilt=30,
    azimuth=180
)
production = pvgis.fetch_hourly_production(year=2020)

# System grenser
GRID_LIMIT_KW = 77  # Netteksport grense

# Beregn avkortning
utilized_production = np.minimum(production, GRID_LIMIT_KW)
curtailment = np.maximum(0, production - GRID_LIMIT_KW)

# Convert to DataFrame for easier handling
df = pd.DataFrame({
    'timestamp': production.index,
    'utilized': utilized_production.values,
    'curtailed': curtailment.values,
    'total': production.values
})
df.set_index('timestamp', inplace=True)

# Lag flere visualiseringer
fig = plt.figure(figsize=(20, 14))

# --- PLOT 1: Årsoversikt med månedlig aggregering ---
ax1 = plt.subplot(3, 1, 1)

# Aggreger til månedlig
monthly = df.resample('M').sum() / 1000  # Convert to MWh

# Stacked bar chart
width = 20  # days
x = range(len(monthly))
p1 = ax1.bar(x, monthly['utilized'], width=0.8, label='Levert til nett',
             color='green', alpha=0.7)
p2 = ax1.bar(x, monthly['curtailed'], width=0.8, bottom=monthly['utilized'],
             label='Avkortet', color='red', alpha=0.7)

# Formatting
ax1.set_xlabel('Måned', fontsize=12)
ax1.set_ylabel('Energi (MWh)', fontsize=12)
ax1.set_title('Månedlig produksjon og avkortning - Stacked', fontsize=14, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des'])
ax1.legend()
ax1.grid(True, alpha=0.3)

# Legg til verdier på søylene
for i, (idx, row) in enumerate(monthly.iterrows()):
    if row['curtailed'] > 0.1:  # Only show if significant
        ax1.text(i, row['utilized'] + row['curtailed']/2,
                f'{row["curtailed"]:.1f}',
                ha='center', va='center', color='white', fontweight='bold')

# --- PLOT 2: Time-for-time for verste uke (høy avkortning) ---
ax2 = plt.subplot(3, 1, 2)

# Finn uken med mest avkortning
weekly_curtailment = df['curtailed'].resample('W').sum()
worst_week = weekly_curtailment.idxmax()
week_start = worst_week - pd.Timedelta(days=3)
week_end = worst_week + pd.Timedelta(days=4)

week_data = df[(df.index >= week_start) & (df.index < week_end)]

# Plot hourly stacked bars
hours = range(len(week_data))
ax2.bar(hours, week_data['utilized'], width=1.0,
        label='Levert til nett', color='green', alpha=0.7)
ax2.bar(hours, week_data['curtailed'], width=1.0,
        bottom=week_data['utilized'], label='Avkortet', color='red', alpha=0.7)

# Add grid line
ax2.axhline(y=GRID_LIMIT_KW, color='black', linestyle='--',
           linewidth=1, label=f'Nettgrense {GRID_LIMIT_KW} kW')

ax2.set_xlabel('Timer i uken', fontsize=12)
ax2.set_ylabel('Effekt (kW)', fontsize=12)
ax2.set_title(f'Uke med høyest avkortning ({week_start.strftime("%d.%m")} - {week_end.strftime("%d.%m.%Y")})',
             fontsize=14, fontweight='bold')
ax2.legend()
ax2.grid(True, alpha=0.3, axis='y')
ax2.set_xlim([0, len(week_data)])

# --- PLOT 3: Døgnprofil - gjennomsnitt per time ---
ax3 = plt.subplot(3, 1, 3)

# Calculate average hourly profile
hourly_avg = df.groupby(df.index.hour).mean()

# Stacked bar chart for average day
hours = range(24)
ax3.bar(hours, hourly_avg['utilized'], width=0.8,
        label='Gjennomsnittlig levert', color='green', alpha=0.7)
ax3.bar(hours, hourly_avg['curtailed'], width=0.8,
        bottom=hourly_avg['utilized'], label='Gjennomsnittlig avkortet',
        color='red', alpha=0.7)

# Add grid line
ax3.axhline(y=GRID_LIMIT_KW, color='black', linestyle='--',
           linewidth=1, label=f'Nettgrense {GRID_LIMIT_KW} kW')

ax3.set_xlabel('Time på døgnet', fontsize=12)
ax3.set_ylabel('Effekt (kW)', fontsize=12)
ax3.set_title('Gjennomsnittlig døgnprofil - Produksjon vs Avkortning',
             fontsize=14, fontweight='bold')
ax3.set_xticks(hours)
ax3.set_xticklabels([f'{h:02d}' for h in hours])
ax3.legend()
ax3.grid(True, alpha=0.3, axis='y')

# Legg til prosent avkortet per time
for hour in range(24):
    total = hourly_avg.loc[hour, 'utilized'] + hourly_avg.loc[hour, 'curtailed']
    if total > 0 and hourly_avg.loc[hour, 'curtailed'] > 0.5:
        pct = hourly_avg.loc[hour, 'curtailed'] / total * 100
        ax3.text(hour, total + 2, f'{pct:.0f}%',
                ha='center', va='bottom', fontsize=8)

plt.tight_layout()

# Lagre
output_file = 'results/curtailment_stacked_analysis.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"💾 Lagret stacked curtailment plot: {output_file}")

# Print statistikk
print("\n📊 AVKORTNINGSSTATISTIKK:")
print("="*50)
print(f"Total produksjon:        {df['total'].sum()/1000:.1f} MWh")
print(f"Levert til nett:        {df['utilized'].sum()/1000:.1f} MWh")
print(f"Avkortet:               {df['curtailed'].sum()/1000:.1f} MWh")
print(f"Avkortningsprosent:     {df['curtailed'].sum()/df['total'].sum()*100:.1f}%")
print()
print(f"Timer med avkortning:   {(df['curtailed'] > 0).sum()} av {len(df)} timer")
print(f"Maks avkortning/time:   {df['curtailed'].max():.1f} kW")
print(f"Gjennomsnittlig avkortning når det skjer: {df[df['curtailed']>0]['curtailed'].mean():.1f} kW")
print()

# Månedlig oversikt
print("MÅNEDLIG AVKORTNING:")
monthly_stats = df.groupby(df.index.month).agg({
    'total': 'sum',
    'curtailed': 'sum'
})
monthly_stats['pct'] = monthly_stats['curtailed'] / monthly_stats['total'] * 100

months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
         'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']

for month_num, month_name in enumerate(months, 1):
    if month_num in monthly_stats.index:
        total = monthly_stats.loc[month_num, 'total'] / 1000
        curtailed = monthly_stats.loc[month_num, 'curtailed'] / 1000
        pct = monthly_stats.loc[month_num, 'pct']
        print(f"  {month_name}: {curtailed:5.1f} MWh av {total:5.1f} MWh ({pct:4.1f}%)")

print("="*50)