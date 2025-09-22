#!/usr/bin/env python
"""
Plott varighetskurve for solproduksjon
Viser installert effekt og faktisk produksjon
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from core.pvgis_solar import PVGISProduction

# Hent produksjonsdata
print("📊 Lager varighetskurve for solproduksjon...")
pvgis = PVGISProduction(
    lat=58.97,
    lon=5.73,
    pv_capacity_kwp=138.55,
    tilt=30,
    azimuth=180
)
production = pvgis.fetch_hourly_production(year=2020)

# System spesifikasjoner
PV_CAPACITY_KWP = 138.55  # Installert solkraft
INVERTER_LIMIT_KW = 110   # Inverter begrensning
GRID_LIMIT_KW = 77        # Netteksport grense

# Sorter produksjon fra høyest til lavest
sorted_production = production.sort_values(ascending=False).reset_index(drop=True)

# Beregn timer
hours = np.arange(len(sorted_production))

# Lag plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# --- PLOT 1: Full varighetskurve ---
ax1.fill_between(hours, 0, sorted_production, alpha=0.3, color='orange', label='Produksjon')
ax1.axhline(y=PV_CAPACITY_KWP, color='red', linestyle='--', linewidth=2, label=f'Installert effekt: {PV_CAPACITY_KWP:.1f} kWp')
ax1.axhline(y=INVERTER_LIMIT_KW, color='blue', linestyle='--', linewidth=1.5, label=f'Inverter grense: {INVERTER_LIMIT_KW} kW')
ax1.axhline(y=GRID_LIMIT_KW, color='green', linestyle='--', linewidth=1.5, label=f'Nett grense: {GRID_LIMIT_KW} kW')

ax1.set_xlabel('Timer i året', fontsize=12)
ax1.set_ylabel('Effekt (kW)', fontsize=12)
ax1.set_title('Varighetskurve for solproduksjon - Stavanger 2020', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper right')
ax1.set_xlim([0, 8784])
ax1.set_ylim([0, PV_CAPACITY_KWP * 1.05])

# Legg til statistikk
textstr = f'Årsproduksjon: {production.sum()/1000:.1f} MWh\n'
textstr += f'Maks produksjon: {production.max():.1f} kW\n'
textstr += f'Kapasitetsfaktor: {production.sum()/(PV_CAPACITY_KWP*len(production))*100:.1f}%\n'
textstr += f'Timer > {GRID_LIMIT_KW} kW: {(production > GRID_LIMIT_KW).sum()}'

props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
ax1.text(0.02, 0.95, textstr, transform=ax1.transAxes, fontsize=10,
         verticalalignment='top', bbox=props)

# --- PLOT 2: Zoom på topp 2000 timer ---
zoom_hours = 2000
ax2.fill_between(hours[:zoom_hours], 0, sorted_production[:zoom_hours],
                 alpha=0.3, color='orange', label='Produksjon')
ax2.axhline(y=PV_CAPACITY_KWP, color='red', linestyle='--', linewidth=2, label=f'Installert: {PV_CAPACITY_KWP:.1f} kWp')
ax2.axhline(y=INVERTER_LIMIT_KW, color='blue', linestyle='--', linewidth=1.5, label=f'Inverter: {INVERTER_LIMIT_KW} kW')
ax2.axhline(y=GRID_LIMIT_KW, color='green', linestyle='--', linewidth=1.5, label=f'Nett: {GRID_LIMIT_KW} kW')

ax2.set_xlabel('Timer i året', fontsize=12)
ax2.set_ylabel('Effekt (kW)', fontsize=12)
ax2.set_title(f'Varighetskurve - Zoom på topp {zoom_hours} timer', fontsize=14, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.legend(loc='upper right')
ax2.set_xlim([0, zoom_hours])
ax2.set_ylim([0, PV_CAPACITY_KWP * 1.05])

# Beregn avkortning
curtailment = (production - GRID_LIMIT_KW).clip(lower=0)
total_curtailment = curtailment.sum()
curtailment_hours = (curtailment > 0).sum()

# Legg til avkortningsinfo
curtailment_text = f'Avkortning (>{GRID_LIMIT_KW} kW):\n'
curtailment_text += f'  Timer: {curtailment_hours}\n'
curtailment_text += f'  Energi: {total_curtailment:.0f} kWh\n'
curtailment_text += f'  Andel: {total_curtailment/production.sum()*100:.1f}%'

props2 = dict(boxstyle='round', facecolor='lightcoral', alpha=0.5)
ax2.text(0.7, 0.95, curtailment_text, transform=ax2.transAxes, fontsize=10,
         verticalalignment='top', bbox=props2)

plt.tight_layout()

# Lagre
output_file = 'results/duration_curve_with_capacity.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"💾 Lagret varighetskurve: {output_file}")

# Lag også en enkel tabell med nøkkeltall
print("\n📊 NØKKELTALL FRA VARIGHETSKURVE:")
print("="*50)
print(f"Installert effekt:      {PV_CAPACITY_KWP:.1f} kWp")
print(f"Inverter grense:        {INVERTER_LIMIT_KW:.0f} kW")
print(f"Nett eksportgrense:     {GRID_LIMIT_KW:.0f} kW")
print()
print(f"Årsproduksjon:          {production.sum()/1000:.1f} MWh")
print(f"Maks produksjon:        {production.max():.1f} kW")
print(f"Kapasitetsfaktor:       {production.sum()/(PV_CAPACITY_KWP*len(production))*100:.1f}%")
print(f"Fullasttimer:           {production.sum()/PV_CAPACITY_KWP:.0f} timer")
print()
print(f"Timer over nettgrense:  {(production > GRID_LIMIT_KW).sum()} timer")
print(f"Avkortning:             {total_curtailment/1000:.1f} MWh ({total_curtailment/production.sum()*100:.1f}%)")
print()

# Beregn produksjon i ulike intervaller
intervals = [
    (0, 10, "0-10 kW"),
    (10, 30, "10-30 kW"),
    (30, 50, "30-50 kW"),
    (50, 77, "50-77 kW"),
    (77, 110, "77-110 kW"),
    (110, 140, "110-140 kW")
]

print("PRODUKSJONSFORDELING:")
for low, high, label in intervals:
    hours_in_range = ((production >= low) & (production < high)).sum()
    energy_in_range = production[(production >= low) & (production < high)].sum()
    print(f"  {label:12s}: {hours_in_range:5d} timer, {energy_in_range/1000:7.1f} MWh ({energy_in_range/production.sum()*100:5.1f}%)")

print("="*50)