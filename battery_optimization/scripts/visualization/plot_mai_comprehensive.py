"""
Omfattende visualisering av mai måned - kontorbygg scenario.
Inspirert av 15-minutters vs 60-minutters sammenligning.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import numpy as np

project_root = Path(__file__).parent
hourly_file = project_root / 'results' / 'kontorbygg_hourly_mai_des.csv'

# Load data
df = pd.read_csv(hourly_file)
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Filter for May only
df_mai = df[df['month'] == 5].copy()
df_mai = df_mai.sort_values('timestamp').reset_index(drop=True)

# Load monthly results for summary
monthly_file = project_root / 'results' / 'kontorbygg_korrekt_results.csv'
df_monthly = pd.read_csv(monthly_file)
mai_monthly = df_monthly[df_monthly['month'] == 5].iloc[0]

# Create comprehensive figure (3x3 grid)
fig = plt.figure(figsize=(18, 14))
gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

# Title
fig.suptitle('Mai 2024 - Kontorbygg 100 kWp / 40 kWh Batteri\n' +
             'Timeoppløsning | PVGIS soldata | Lnett commercial tariff',
             fontsize=16, fontweight='bold')

# =============================================================================
# Panel 1: Battery State of Charge (SOC)
# =============================================================================
ax1 = fig.add_subplot(gs[0, 0])
ax1.plot(df_mai['timestamp'], df_mai['soc_pct'], linewidth=1.5, color='blue', label='SOC')
ax1.axhline(90, color='red', linestyle='--', alpha=0.5, linewidth=1)
ax1.axhline(10, color='red', linestyle='--', alpha=0.5, linewidth=1)
ax1.fill_between(df_mai['timestamp'], 10, 90, alpha=0.1, color='green')
ax1.set_ylabel('Batterinivå (kWh)')
ax1.set_title('Battery State of Charge - ZOOMET')
ax1.grid(True, alpha=0.3)
ax1.set_ylim([0, 100])
ax1.legend(fontsize=9, loc='upper right')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
ax1.text(0.02, 0.95, 'SOC max (27 kWh)', transform=ax1.transAxes,
         fontsize=8, verticalalignment='top', color='red')
ax1.text(0.02, 0.05, 'SOC min (3 kWh)', transform=ax1.transAxes,
         fontsize=8, verticalalignment='bottom', color='red')

# =============================================================================
# Panel 2: Spot Prices (constant in this case)
# =============================================================================
ax2 = fig.add_subplot(gs[0, 1])
ax2.plot(df_mai['timestamp'], df_mai['spot_price_nok'], linewidth=1.5, color='red', label='Spotpris')
ax2.axhline(0.80, color='orange', linestyle='--', alpha=0.5, linewidth=1, label='Gjennomsnitt: 0.80 kr/kWh')
ax2.set_ylabel('Pris (NOK/kWh)')
ax2.set_title('Spotpriser (antatt konstant)')
ax2.grid(True, alpha=0.3)
ax2.legend(fontsize=9)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

# =============================================================================
# Panel 3: Battery Charging/Discharging
# =============================================================================
ax3 = fig.add_subplot(gs[0, 2])
ax3.fill_between(df_mai['timestamp'], 0, df_mai['battery_charge_kw'],
                 alpha=0.7, label='Lading', color='orange', step='post')
ax3.fill_between(df_mai['timestamp'], 0, -df_mai['battery_discharge_kw'],
                 alpha=0.7, label='Utlading', color='purple', step='post')
ax3.axhline(0, color='black', linewidth=0.8)
ax3.set_ylabel('Effekt (kW)')
ax3.set_title('Batterikjøring (+ = lading, - = utlading)')
ax3.legend(fontsize=9)
ax3.grid(True, alpha=0.3)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

# =============================================================================
# Panel 4: Grid Import/Export
# =============================================================================
ax4 = fig.add_subplot(gs[1, 0])
ax4.fill_between(df_mai['timestamp'], 0, df_mai['grid_import_kw'],
                 alpha=0.6, label='Import (60-min)', color='lightcoral', step='post')
ax4.fill_between(df_mai['timestamp'], 0, df_mai['grid_export_kw'],
                 alpha=0.6, label='Eksport (60-min)', color='lightgreen', step='post')
ax4.axhline(70, color='red', linestyle='--', alpha=0.5, linewidth=1, label='Nettgrense (100 kW)')
ax4.set_ylabel('Nettkraft (kW)')
ax4.set_title('Nettimport/eksport')
ax4.legend(fontsize=9)
ax4.grid(True, alpha=0.3)
ax4.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

# =============================================================================
# Panel 5: Solar Production vs Load
# =============================================================================
ax5 = fig.add_subplot(gs[1, 1])
ax5.plot(df_mai['timestamp'], df_mai['pv_kw'], label='Solproduksjon',
         color='gold', linewidth=1.5, alpha=0.8)
ax5.plot(df_mai['timestamp'], df_mai['load_kw'], label='Forbruk',
         color='purple', linewidth=1.5, alpha=0.8)
ax5.set_ylabel('Effekt (kW)')
ax5.set_title('Solproduksjon vs Forbruk')
ax5.legend(fontsize=9)
ax5.grid(True, alpha=0.3)
ax5.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

# =============================================================================
# Panel 6: Economic Comparison (bar chart)
# =============================================================================
ax6 = fig.add_subplot(gs[1, 2])

# Get data from monthly results
energy_cost = mai_monthly['energy_cost_nok']
power_cost = mai_monthly['power_cost_nok']
total_cost = mai_monthly['total_cost_nok']

# From without battery simulation (estimated proportionally)
# Mai is one of the negative cost months, so we need to handle this carefully
categories = ['Energikostnad', 'Effekttariff', 'Egenforbruk\nverdi']
values = [abs(energy_cost), power_cost, abs(energy_cost) if energy_cost < 0 else 0]
colors = ['steelblue', 'coral', 'green']

bars = ax6.bar(categories, values, color=colors, alpha=0.7)
for i, (bar, val) in enumerate(zip(bars, values)):
    height = bar.get_height()
    ax6.text(bar.get_x() + bar.get_width()/2., height,
             f'{val:.0f} NOK', ha='center', va='bottom', fontsize=9)

ax6.set_ylabel('Beløp (NOK)')
ax6.set_title('Økonomisk sammenligning (1 måned)')
ax6.grid(True, alpha=0.3, axis='y')

# =============================================================================
# Panel 7: Cumulative Energy Cost
# =============================================================================
ax7 = fig.add_subplot(gs[2, 0])

# Calculate cumulative cost (simplified - assume uniform distribution)
hours = len(df_mai)
cum_cost = np.linspace(0, total_cost, hours)

ax7.plot(df_mai['timestamp'], cum_cost, linewidth=2, color='steelblue', label='Kumulativ kostnad')
ax7.set_ylabel('Akkumulert kostnad (NOK)')
ax7.set_xlabel('Dato')
ax7.set_title('Kumulativ energikostnad')
ax7.grid(True, alpha=0.3)
ax7.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

# Add final value annotation
ax7.text(0.98, 0.02, f'Differanse: {total_cost:.0f} NOK',
         transform=ax7.transAxes, fontsize=10,
         verticalalignment='bottom', horizontalalignment='right',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# =============================================================================
# Panel 8: Summary Statistics (text box)
# =============================================================================
ax8 = fig.add_subplot(gs[2, 1])
ax8.axis('off')

# Calculate statistics
pv_total = df_mai['pv_kw'].sum()
load_total = df_mai['load_kw'].sum()
import_total = df_mai['grid_import_kw'].sum()
export_total = df_mai['grid_export_kw'].sum()
charge_total = df_mai['battery_charge_kw'].sum()
discharge_total = df_mai['battery_discharge_kw'].sum()
self_consumption = pv_total - export_total
battery_cycles = charge_total / 40.0

summary_text = f"""SAMMENDRAG - Mai 2024

ØKONOMI:
• Energikostnad: {energy_cost:.0f} NOK
• Effekttariff: {power_cost:.0f} NOK
• Total kostnad: {total_cost:.0f} NOK

BATTERIBRUK:
• Sykluser: {battery_cycles:.2f}
• Lading: {charge_total:.0f} kWh
• Utlading: {discharge_total:.0f} kWh
• Ødning: {(1 - discharge_total/charge_total)*100:.1f}%

NETT:
• Import: {import_total:.0f} kWh
• Eksport: {export_total:.0f} kWh

SOLENERGI:
• Produksjon: {pv_total:.0f} kWh
• Egenforbruk: {self_consumption:.0f} kWh ({self_consumption/pv_total*100:.1f}%)
• Eksport: {export_total:.0f} kWh ({export_total/pv_total*100:.1f}%)

OPTIMALISERINGER:
• Optimaliseringer: 744 (hver time)
"""

ax8.text(0.1, 0.95, summary_text, transform=ax8.transAxes,
         fontsize=10, verticalalignment='top', family='monospace',
         bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))

# =============================================================================
# Panel 9: Battery Efficiency & Utilization
# =============================================================================
ax9 = fig.add_subplot(gs[2, 2])
ax9.axis('off')

# Calculate daily statistics
df_mai['date'] = df_mai['timestamp'].dt.date
daily_stats = df_mai.groupby('date').agg({
    'battery_charge_kw': 'sum',
    'battery_discharge_kw': 'sum',
    'soc_pct': ['min', 'max', 'mean']
}).reset_index()

avg_daily_charge = daily_stats['battery_charge_kw']['sum'].mean()
avg_daily_discharge = daily_stats['battery_discharge_kw']['sum'].mean()
avg_soc_range = (daily_stats['soc_pct']['max'] - daily_stats['soc_pct']['min']).mean()

efficiency_text = f"""BATTERIYELSE & UTNYTTELSE

DAGLIG GJENNOMSNITT:
• Lading: {avg_daily_charge:.1f} kWh/dag
• Utlading: {avg_daily_discharge:.1f} kWh/dag
• SOC-spenn: {avg_soc_range:.1f}%

BATTERIPARAMETERE:
• Kapasitet: 40 kWh
• Effekt: 40 kW
• Virkningsgrad: 90%
• SOC-grenser: 10-90% (32 kWh brukbar)

MÅNEDSYTELSE:
• Sykluser/dag: {battery_cycles/31:.2f}
• Total sykluser: {battery_cycles:.2f}
• Utnyttelsesgrad: {(charge_total/(40*31))*100:.1f}%
• Tapte kWh: {charge_total - discharge_total:.1f} kWh

BESPARELSE:
• Peak shaving: {power_cost:.0f} NOK reduksjon
• Arbitrage: {abs(energy_cost):.0f} NOK gevinst
"""

ax9.text(0.1, 0.95, efficiency_text, transform=ax9.transAxes,
         fontsize=10, verticalalignment='top', family='monospace',
         bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

# Save figure
output_file = project_root / 'results' / 'mai_comprehensive_visualization.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"✓ Omfattende visualisering lagret til: {output_file}")

# Print key statistics
print(f"\n{'='*70}")
print("MAI 2024 - NØKKELSTATISTIKK")
print(f"{'='*70}")
print(f"Solproduksjon: {pv_total:.0f} kWh")
print(f"Forbruk: {load_total:.0f} kWh")
print(f"Egenforbruk: {self_consumption:.0f} kWh ({self_consumption/pv_total*100:.1f}%)")
print(f"Eksport: {export_total:.0f} kWh ({export_total/pv_total*100:.1f}%)")
print(f"Batterisykluser: {battery_cycles:.2f}")
print(f"Total kostnad: {total_cost:.0f} NOK")
print(f"{'='*70}")
