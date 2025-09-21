#!/usr/bin/env python
"""
Plott månedlig energibalanse
Produksjon som area plot, forbruk som line plot
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from core.pvgis_solar import PVGISProduction
from core.consumption_profiles import ConsumptionProfile

print("📊 Lager månedlig energibalanse plot...")

# Hent produksjonsdata
pvgis = PVGISProduction(lat=58.97, lon=5.73, pv_capacity_kwp=138.55)
production = pvgis.fetch_hourly_production(year=2020)

# Generer forbruksprofil (commercial office)
consumption = ConsumptionProfile.generate_annual_profile(
    profile_type='commercial_office',
    annual_kwh=90000,
    year=2020
)

# Align indices
consumption.index = production.index

# Create figure with multiple subplots
fig, axes = plt.subplots(3, 1, figsize=(16, 14))

# --- PLOT 1: Månedlig energibalanse (hovedplot) ---
ax1 = axes[0]

# Aggreger til månedlig
monthly_prod = production.resample('ME').sum() / 1000  # MWh
monthly_cons = consumption.resample('ME').sum() / 1000  # MWh

months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
          'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']
x = np.arange(len(months))

# Area plot for produksjon
ax1.fill_between(x, 0, monthly_prod, alpha=0.4, color='orange', label='Produksjon')

# Line plot for forbruk
ax1.plot(x, monthly_cons, 'b-', linewidth=3, marker='o', markersize=8,
         label='Forbruk', zorder=5)

# Add net export/import bars
net = monthly_prod.values - monthly_cons.values
colors = ['green' if n > 0 else 'red' for n in net]
bars = ax1.bar(x, net, width=0.3, color=colors, alpha=0.3,
               label='Netto (eksport/import)', zorder=3)

# Formatting
ax1.set_xlabel('Måned', fontsize=12)
ax1.set_ylabel('Energi (MWh)', fontsize=12)
ax1.set_title('Månedlig energibalanse - Produksjon vs Forbruk', fontsize=14, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels(months)
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3)
ax1.axhline(y=0, color='black', linewidth=0.5)

# Add values
for i, (prod, cons) in enumerate(zip(monthly_prod, monthly_cons)):
    # Production value
    ax1.text(i, prod + 0.5, f'{prod:.1f}', ha='center', va='bottom',
            fontsize=9, color='darkorange')
    # Consumption value
    ax1.text(i, cons, f'{cons:.1f}', ha='center', va='bottom',
            fontsize=9, color='blue')

# --- PLOT 2: Kumulativ energi gjennom året ---
ax2 = axes[1]

# Calculate cumulative
cumulative_prod = production.cumsum() / 1000  # MWh
cumulative_cons = consumption.cumsum() / 1000  # MWh

# Resample to daily for smoother plot
daily_prod = cumulative_prod.resample('D').last()
daily_cons = cumulative_cons.resample('D').last()

# Area plot for production
ax2.fill_between(daily_prod.index, 0, daily_prod, alpha=0.4,
                 color='orange', label='Kumulativ produksjon')

# Line plot for consumption
ax2.plot(daily_cons.index, daily_cons, 'b-', linewidth=2,
         label='Kumulativt forbruk')

# Add balance line
balance = daily_prod - daily_cons
ax2.plot(daily_prod.index, balance, 'g--', linewidth=1.5,
         label='Netto balanse', alpha=0.7)

ax2.set_xlabel('Dato', fontsize=12)
ax2.set_ylabel('Kumulativ energi (MWh)', fontsize=12)
ax2.set_title('Kumulativ energibalanse gjennom året', fontsize=14, fontweight='bold')
ax2.legend(loc='upper left')
ax2.grid(True, alpha=0.3)

# Format x-axis
import matplotlib.dates as mdates
ax2.xaxis.set_major_locator(mdates.MonthLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b'))

# --- PLOT 3: Selvforsyningsgrad per måned ---
ax3 = axes[2]

# Calculate self-consumption and self-sufficiency
monthly_df = pd.DataFrame({
    'prod': monthly_prod.values,
    'cons': monthly_cons.values
})

# Self-consumption: how much of production is consumed locally
monthly_df['self_consumed'] = monthly_df[['prod', 'cons']].min(axis=1)
monthly_df['exported'] = monthly_df['prod'] - monthly_df['self_consumed']
monthly_df['imported'] = monthly_df['cons'] - monthly_df['self_consumed']

# Self-sufficiency: how much of consumption is covered by production
monthly_df['self_sufficiency'] = (monthly_df['self_consumed'] / monthly_df['cons'] * 100).fillna(0)

# Stacked bar for energy flow
width = 0.35
x1 = x - width/2
x2 = x + width/2

# Production breakdown
p1 = ax3.bar(x1, monthly_df['self_consumed'], width, label='Selvforbruk',
             color='green', alpha=0.7)
p2 = ax3.bar(x1, monthly_df['exported'], width, bottom=monthly_df['self_consumed'],
             label='Eksport', color='lightgreen', alpha=0.5)

# Consumption breakdown
c1 = ax3.bar(x2, monthly_df['self_consumed'], width,
             color='green', alpha=0.7)
c2 = ax3.bar(x2, monthly_df['imported'], width, bottom=monthly_df['self_consumed'],
             label='Import', color='red', alpha=0.5)

# Self-sufficiency line (secondary y-axis)
ax3_2 = ax3.twinx()
ax3_2.plot(x, monthly_df['self_sufficiency'], 'ko-', linewidth=2,
           markersize=6, label='Selvforsyningsgrad (%)')
ax3_2.set_ylabel('Selvforsyningsgrad (%)', fontsize=12)
ax3_2.set_ylim([0, 105])

# Formatting
ax3.set_xlabel('Måned', fontsize=12)
ax3.set_ylabel('Energi (MWh)', fontsize=12)
ax3.set_title('Selvforbruk og selvforsyning per måned', fontsize=14, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels(months)
ax3.legend(loc='upper left')
ax3_2.legend(loc='upper right')
ax3.grid(True, alpha=0.3)

# Add percentage labels
for i, pct in enumerate(monthly_df['self_sufficiency']):
    if pct > 0:
        ax3_2.text(i, pct + 2, f'{pct:.0f}%', ha='center', va='bottom', fontsize=8)

plt.tight_layout()

# Save
output_file = 'results/energy_balance_monthly.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"💾 Lagret energibalanse plot: {output_file}")

# Print statistics
print("\n📊 ENERGIBALANSE STATISTIKK:")
print("="*50)
print(f"ÅRLIG:")
print(f"  Total produksjon:       {monthly_prod.sum():.1f} MWh")
print(f"  Totalt forbruk:         {monthly_cons.sum():.1f} MWh")
print(f"  Netto balanse:          {monthly_prod.sum() - monthly_cons.sum():+.1f} MWh")
print(f"  Selvforbruk:            {monthly_df['self_consumed'].sum():.1f} MWh")
print(f"  Eksport:                {monthly_df['exported'].sum():.1f} MWh")
print(f"  Import:                 {monthly_df['imported'].sum():.1f} MWh")
print(f"  Årlig selvforsyning:    {monthly_df['self_consumed'].sum() / monthly_df['cons'].sum() * 100:.1f}%")

print("\nMÅNEDLIG DETALJER:")
print("Måned | Prod | Forb | Netto | Selvfors.")
print("------|------|------|-------|----------")
for i, month in enumerate(months):
    prod = monthly_prod.iloc[i]
    cons = monthly_cons.iloc[i]
    net = prod - cons
    ss = monthly_df.iloc[i]['self_sufficiency']
    print(f"{month:5s} | {prod:4.1f} | {cons:4.1f} | {net:+5.1f} | {ss:5.1f}%")

print("\nSESSONGER:")
summer = monthly_df.iloc[4:8]  # Mai-Aug
winter = monthly_df.iloc[[11, 0, 1]]  # Des-Jan-Feb
print(f"  Sommer (mai-aug):")
print(f"    Produksjon:           {summer['prod'].sum():.1f} MWh")
print(f"    Forbruk:              {summer['cons'].sum():.1f} MWh")
print(f"    Selvforsyning:        {summer['self_consumed'].sum()/summer['cons'].sum()*100:.1f}%")
print(f"  Vinter (des-feb):")
print(f"    Produksjon:           {winter['prod'].sum():.1f} MWh")
print(f"    Forbruk:              {winter['cons'].sum():.1f} MWh")
print(f"    Selvforsyning:        {winter['self_consumed'].sum()/winter['cons'].sum()*100:.1f}%")

print("="*50)