#!/usr/bin/env python
"""
Bedre analyse som fokuserer på RELEVANTE metrikker
Ikke misvisende gjennomsnitt over 24 timer!
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from core.pvgis_solar import PVGISProduction

print("📊 Lager forbedret analyse (uten misvisende 24t-gjennomsnitt)...")

# Hent data
pvgis = PVGISProduction(lat=58.97, lon=5.73, pv_capacity_kwp=138.55)
production = pvgis.fetch_hourly_production(year=2020)

# System params
PV_CAPACITY = 138.55
INVERTER_LIMIT = 110
GRID_LIMIT = 77

# Create figure
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# --- PLOT 1: Månedlig ENERGI (ikke effekt!) ---
ax1 = axes[0, 0]
monthly_energy = production.resample('ME').sum() / 1000  # MWh

months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
          'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']
colors = ['#1f77b4' if i < 3 or i > 8 else '#ff7f0e' if i < 6 else '#2ca02c'
          for i in range(12)]

bars = ax1.bar(months, monthly_energy, color=colors, alpha=0.7)
ax1.set_ylabel('Energi (MWh)', fontsize=12)
ax1.set_title('Månedlig solenergiproduksjon', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3, axis='y')

# Add values on bars
for bar, val in zip(bars, monthly_energy):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
            f'{val:.1f}', ha='center', va='bottom', fontsize=9)

# --- PLOT 2: Produksjonstimer per måned ---
ax2 = axes[0, 1]
production_hours = production.groupby(production.index.month).apply(
    lambda x: (x > 0.1).sum()  # Timer med produksjon > 0.1 kW
)

bars2 = ax2.bar(months, production_hours, color='green', alpha=0.7)
ax2.set_ylabel('Timer med produksjon', fontsize=12)
ax2.set_title('Produksjonstimer per måned', fontsize=14, fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')

# Add sunrise/sunset info
for i, (bar, hours) in enumerate(zip(bars2, production_hours)):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
            f'{hours:.0f}h', ha='center', va='bottom', fontsize=9)

# --- PLOT 3: Maksimal effekt per måned ---
ax3 = axes[1, 0]
monthly_max = production.groupby(production.index.month).max()
monthly_95_percentile = production.groupby(production.index.month).quantile(0.95)

# Bar chart with two series
x = np.arange(len(months))
width = 0.35

bars3_max = ax3.bar(x - width/2, monthly_max, width,
                    label='Maks effekt', color='red', alpha=0.7)
bars3_95 = ax3.bar(x + width/2, monthly_95_percentile, width,
                   label='95% percentil', color='orange', alpha=0.7)

# Add limit lines
ax3.axhline(y=GRID_LIMIT, color='green', linestyle='--',
           linewidth=1, label=f'Nettgrense {GRID_LIMIT} kW')
ax3.axhline(y=INVERTER_LIMIT, color='blue', linestyle='--',
           linewidth=1, label=f'Inverter {INVERTER_LIMIT} kW')

ax3.set_ylabel('Effekt (kW)', fontsize=12)
ax3.set_title('Maksimal effekt per måned', fontsize=14, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels(months)
ax3.legend(loc='upper right')
ax3.grid(True, alpha=0.3, axis='y')

# --- PLOT 4: Timer over nettgrense ---
ax4 = axes[1, 1]
hours_above_limit = production.groupby(production.index.month).apply(
    lambda x: (x > GRID_LIMIT).sum()
)

bars4 = ax4.bar(months, hours_above_limit, color='red', alpha=0.7)
ax4.set_ylabel('Timer over 77 kW', fontsize=12)
ax4.set_title('Timer med avkortningsrisiko', fontsize=14, fontweight='bold')
ax4.grid(True, alpha=0.3, axis='y')

# Add values
for bar, val in zip(bars4, hours_above_limit):
    if val > 0:
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                f'{val:.0f}h', ha='center', va='bottom', fontsize=9)

# Add percentage of month
total_hours = [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744]
for i, (bar, hours) in enumerate(zip(bars4, hours_above_limit)):
    if hours > 0:
        pct = hours / total_hours[i] * 100
        ax4.text(bar.get_x() + bar.get_width()/2, hours/2,
                f'{pct:.1f}%', ha='center', va='center',
                fontsize=8, color='white', fontweight='bold')

plt.suptitle('Solkraftanalyse - Relevante metrikker (ikke 24t-gjennomsnitt!)',
            fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()

# Save
output_file = 'results/better_solar_analysis.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"💾 Lagret forbedret analyse: {output_file}")

# Print key stats
print("\n📊 NØKKELSTATISTIKK (relevante tall):")
print("="*50)
print("\nÅRSBASIS:")
print(f"  Total energi:           {production.sum()/1000:.1f} MWh")
print(f"  Kapasitetsfaktor:       {production.sum()/(PV_CAPACITY*8760)*100:.1f}%")
print(f"  Timer med produksjon:   {(production > 0.1).sum()} ({(production > 0.1).sum()/8760*100:.1f}%)")
print(f"  Timer over nettgrense:  {(production > GRID_LIMIT).sum()} ({(production > GRID_LIMIT).sum()/8760*100:.1f}%)")

print("\nPRODUKSJONSTIMER (når sola skinner):")
daylight_hours = production[production > 0.1]
print(f"  Gjennomsnitt når sol:   {daylight_hours.mean():.1f} kW")
print(f"  Median når sol:         {daylight_hours.median():.1f} kW")
print(f"  Maks effekt:            {daylight_hours.max():.1f} kW")

print("\nSESONGVARIASJON:")
summer_months = [5, 6, 7, 8]  # Mai-Aug
winter_months = [11, 12, 1, 2]  # Nov-Feb

summer_prod = production[production.index.month.isin(summer_months)]
winter_prod = production[production.index.month.isin(winter_months)]

print(f"  Sommer (mai-aug):")
print(f"    - Energi:             {summer_prod.sum()/1000:.1f} MWh ({summer_prod.sum()/production.sum()*100:.0f}% av året)")
print(f"    - Timer > 77 kW:      {(summer_prod > GRID_LIMIT).sum()}")
print(f"  Vinter (nov-feb):")
print(f"    - Energi:             {winter_prod.sum()/1000:.1f} MWh ({winter_prod.sum()/production.sum()*100:.0f}% av året)")
print(f"    - Timer > 77 kW:      {(winter_prod > GRID_LIMIT).sum()}")

print("="*50)
print("\n✅ Dette er RELEVANTE tall - ikke misvisende 24t-gjennomsnitt!")