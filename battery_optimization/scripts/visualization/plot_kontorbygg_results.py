"""
Visualisering av kontorbygg simuleringsresultater.

Viser:
- Månedlig energiflyt (sol, forbruk, import, eksport)
- Batteribruk (lading, utlading)
- Kostnadsfordeling (energi, effekttariff)
- Inntektsstrømmer
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Setup
project_root = Path(__file__).parent
results_file = project_root / 'results' / 'kontorbygg_korrekt_results.csv'

# Load results
df = pd.read_csv(results_file)

# Calculate derived metrics
df['self_consumption_kwh'] = df['pv_total_kwh'] - df['grid_export_kwh'] - df['curtailment_kwh']
df['export_revenue_nok'] = df['grid_export_kwh'] * 0.50  # Assume 0.50 NOK/kWh export price
df['savings_energy_nok'] = df['self_consumption_kwh'] * 0.50  # Value of self-consumed energy
df['savings_power_nok'] = -df['power_cost_nok']  # Negative because it's a cost

# Month names
month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
               'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']
df['month_name'] = df['month'].apply(lambda x: month_names[x-1])

# Create figure with subplots
fig, axes = plt.subplots(3, 2, figsize=(16, 12))
fig.suptitle('Kontorbygg Batteri Analyse - Månedlige Resultater', fontsize=16, fontweight='bold')

# ============================================================================
# Plot 1: Energiflyt (stacket område)
# ============================================================================
ax1 = axes[0, 0]
x = df['month']

# Stack positive flows
ax1.fill_between(x, 0, df['pv_total_kwh'], alpha=0.7, label='Solproduksjon', color='gold')
ax1.fill_between(x, 0, df['grid_import_kwh'], alpha=0.7, label='Import fra nett', color='red')

# Negative flows
ax1.fill_between(x, 0, -df['load_total_kwh'], alpha=0.7, label='Forbruk', color='blue')
ax1.fill_between(x, 0, -df['grid_export_kwh'], alpha=0.7, label='Eksport til nett', color='green')

ax1.axhline(0, color='black', linewidth=0.8, linestyle='--')
ax1.set_xlabel('Måned')
ax1.set_ylabel('Energi (kWh)')
ax1.set_title('Månedlig Energiflyt')
ax1.legend(loc='upper left', fontsize=9)
ax1.set_xticks(x)
ax1.set_xticklabels(df['month_name'], rotation=45)
ax1.grid(True, alpha=0.3)

# ============================================================================
# Plot 2: Batteribruk
# ============================================================================
ax2 = axes[0, 1]
width = 0.35
x_pos = np.arange(len(df))

bars1 = ax2.bar(x_pos - width/2, df['battery_charge_kwh'], width,
                label='Lading', color='orange', alpha=0.8)
bars2 = ax2.bar(x_pos + width/2, df['battery_discharge_kwh'], width,
                label='Utlading', color='purple', alpha=0.8)

ax2.set_xlabel('Måned')
ax2.set_ylabel('Energi (kWh)')
ax2.set_title('Batterilading og Utlading')
ax2.set_xticks(x_pos)
ax2.set_xticklabels(df['month_name'], rotation=45)
ax2.legend()
ax2.grid(True, alpha=0.3, axis='y')

# Add efficiency line
efficiency = df['battery_discharge_kwh'] / df['battery_charge_kwh']
ax2_twin = ax2.twinx()
ax2_twin.plot(x_pos, efficiency * 100, 'g--o', linewidth=2,
              label='Effektivitet', markersize=4)
ax2_twin.set_ylabel('Effektivitet (%)', color='g')
ax2_twin.tick_params(axis='y', labelcolor='g')
ax2_twin.set_ylim([80, 100])
ax2_twin.legend(loc='lower right', fontsize=9)

# ============================================================================
# Plot 3: Import vs Eksport
# ============================================================================
ax3 = axes[1, 0]
width = 0.4
x_pos = np.arange(len(df))

bars1 = ax3.bar(x_pos - width/2, df['grid_import_kwh'], width,
                label='Import', color='red', alpha=0.8)
bars2 = ax3.bar(x_pos + width/2, df['grid_export_kwh'], width,
                label='Eksport', color='green', alpha=0.8)

ax3.set_xlabel('Måned')
ax3.set_ylabel('Energi (kWh)')
ax3.set_title('Nettimport og Netteksport')
ax3.set_xticks(x_pos)
ax3.set_xticklabels(df['month_name'], rotation=45)
ax3.legend()
ax3.grid(True, alpha=0.3, axis='y')

# ============================================================================
# Plot 4: Kostnadsfordeling
# ============================================================================
ax4 = axes[1, 1]
x_pos = np.arange(len(df))

# Stack costs
bottom = np.zeros(len(df))
ax4.bar(x_pos, df['energy_cost_nok'], label='Energikostnad',
        color='steelblue', alpha=0.8)
ax4.bar(x_pos, df['power_cost_nok'], bottom=df['energy_cost_nok'],
        label='Effekttariff', color='darkblue', alpha=0.8)

ax4.set_xlabel('Måned')
ax4.set_ylabel('Kostnad (NOK)')
ax4.set_title('Månedlig Kostnadsfordeling')
ax4.set_xticks(x_pos)
ax4.set_xticklabels(df['month_name'], rotation=45)
ax4.legend()
ax4.grid(True, alpha=0.3, axis='y')

# ============================================================================
# Plot 5: Egenforbruk vs Eksport (prosent av solproduksjon)
# ============================================================================
ax5 = axes[2, 0]
export_pct = (df['grid_export_kwh'] / df['pv_total_kwh']) * 100
selfcons_pct = (df['self_consumption_kwh'] / df['pv_total_kwh']) * 100

x_pos = np.arange(len(df))
ax5.bar(x_pos, selfcons_pct, label='Egenforbruk', color='green', alpha=0.8)
ax5.bar(x_pos, export_pct, bottom=selfcons_pct,
        label='Eksport', color='orange', alpha=0.8)

ax5.set_xlabel('Måned')
ax5.set_ylabel('Andel av solproduksjon (%)')
ax5.set_title('Fordeling av Solkraft: Egenforbruk vs Eksport')
ax5.set_xticks(x_pos)
ax5.set_xticklabels(df['month_name'], rotation=45)
ax5.legend()
ax5.grid(True, alpha=0.3, axis='y')
ax5.set_ylim([0, 100])

# ============================================================================
# Plot 6: Inntektsstrømmer / Besparelser
# ============================================================================
ax6 = axes[2, 1]

# Calculate value streams
export_revenue = df['grid_export_kwh'] * 0.50  # Export revenue
selfcons_value = df['self_consumption_kwh'] * 0.50  # Value of self-consumed solar
total_value = export_revenue + selfcons_value

# Årlig totaler
annual_export_rev = export_revenue.sum()
annual_selfcons_val = selfcons_value.sum()
annual_total = total_value.sum()
annual_costs = df['total_cost_nok'].sum()
annual_net = annual_total - annual_costs

# Pie chart for value distribution
labels = [
    f'Eksportinntekt\n{annual_export_rev:.0f} NOK',
    f'Egenforbruksverdi\n{annual_selfcons_val:.0f} NOK',
]
sizes = [annual_export_rev, annual_selfcons_val]
colors = ['orange', 'green']
explode = (0.05, 0)

ax6.pie(sizes, explode=explode, labels=labels, colors=colors,
        autopct='%1.1f%%', shadow=True, startangle=90)
ax6.set_title(f'Fordeling av Solkraftverdi\n(Total: {annual_total:.0f} NOK/år)')

plt.tight_layout()

# Save figure
output_file = project_root / 'results' / 'kontorbygg_visualisering.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"✓ Visualisering lagret til: {output_file}")

# Print summary statistics
print("\n" + "="*80)
print("ÅRLIG SAMMENDRAG")
print("="*80)
print(f"\n📊 Energi:")
print(f"   Solproduksjon: {df['pv_total_kwh'].sum():,.0f} kWh")
print(f"   Forbruk: {df['load_total_kwh'].sum():,.0f} kWh")
print(f"   Import: {df['grid_import_kwh'].sum():,.0f} kWh")
print(f"   Eksport: {df['grid_export_kwh'].sum():,.0f} kWh ({export_pct.mean():.1f}%)")
print(f"   Egenforbruk: {df['self_consumption_kwh'].sum():,.0f} kWh ({selfcons_pct.mean():.1f}%)")

print(f"\n🔋 Batteri:")
print(f"   Lading: {df['battery_charge_kwh'].sum():,.0f} kWh")
print(f"   Utlading: {df['battery_discharge_kwh'].sum():,.0f} kWh")
avg_eff = (df['battery_discharge_kwh'].sum() / df['battery_charge_kwh'].sum()) * 100
print(f"   Gjennomsnittlig effektivitet: {avg_eff:.1f}%")

print(f"\n💰 Økonomi:")
print(f"   Energikostnad: {df['energy_cost_nok'].sum():,.0f} NOK")
print(f"   Effekttariff: {df['power_cost_nok'].sum():,.0f} NOK")
print(f"   Total kostnad: {df['total_cost_nok'].sum():,.0f} NOK")
print(f"\n   Eksportinntekt: {annual_export_rev:,.0f} NOK")
print(f"   Egenforbruksverdi: {annual_selfcons_val:,.0f} NOK")
print(f"   Total verdi av sol: {annual_total:,.0f} NOK")
print(f"\n   Netto (verdi - kostnad): {annual_net:,.0f} NOK")

print("\n" + "="*80)
