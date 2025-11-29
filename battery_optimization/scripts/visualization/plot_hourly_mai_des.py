"""
Visualisering av timedata for mai og desember.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

project_root = Path(__file__).parent
hourly_file = project_root / 'results' / 'kontorbygg_hourly_mai_des.csv'

df = pd.read_csv(hourly_file)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['day'] = df['timestamp'].dt.day
df['hour'] = df['timestamp'].dt.hour

# Split into mai and desember
df_mai = df[df['month'] == 5].copy()
df_des = df[df['month'] == 12].copy()

# Create figure with 2 columns (mai, desember) and 3 rows
fig, axes = plt.subplots(3, 2, figsize=(18, 12))
fig.suptitle('Timeoppløsning: Mai vs Desember', fontsize=16, fontweight='bold')

# ============================================================================
# ROW 1: SOC (State of Charge)
# ============================================================================
ax_mai_soc = axes[0, 0]
ax_des_soc = axes[0, 1]

x_mai = range(len(df_mai))
x_des = range(len(df_des))

ax_mai_soc.plot(x_mai, df_mai['soc_pct'], linewidth=1.5, color='blue')
ax_mai_soc.axhline(90, color='red', linestyle='--', alpha=0.5, label='Max SOC (90%)')
ax_mai_soc.axhline(10, color='red', linestyle='--', alpha=0.5, label='Min SOC (10%)')
ax_mai_soc.fill_between(x_mai, 10, 90, alpha=0.1, color='green')
ax_mai_soc.set_ylabel('SOC (%)')
ax_mai_soc.set_xlabel('Timer i mai')
ax_mai_soc.set_title('MAI: Batteri State of Charge (SOC)')
ax_mai_soc.grid(True, alpha=0.3)
ax_mai_soc.set_ylim([0, 100])
ax_mai_soc.legend(fontsize=9)

ax_des_soc.plot(x_des, df_des['soc_pct'], linewidth=1.5, color='blue')
ax_des_soc.axhline(90, color='red', linestyle='--', alpha=0.5, label='Max SOC (90%)')
ax_des_soc.axhline(10, color='red', linestyle='--', alpha=0.5, label='Min SOC (10%)')
ax_des_soc.fill_between(x_des, 10, 90, alpha=0.1, color='green')
ax_des_soc.set_ylabel('SOC (%)')
ax_des_soc.set_xlabel('Timer i desember')
ax_des_soc.set_title('DESEMBER: Batteri State of Charge (SOC)')
ax_des_soc.grid(True, alpha=0.3)
ax_des_soc.set_ylim([0, 100])
ax_des_soc.legend(fontsize=9)

# ============================================================================
# ROW 2: Lading/Utlading
# ============================================================================
ax_mai_bat = axes[1, 0]
ax_des_bat = axes[1, 1]

ax_mai_bat.fill_between(x_mai, 0, df_mai['battery_charge_kw'],
                         alpha=0.7, label='Lading', color='orange')
ax_mai_bat.fill_between(x_mai, 0, -df_mai['battery_discharge_kw'],
                         alpha=0.7, label='Utlading', color='purple')
ax_mai_bat.axhline(0, color='black', linewidth=0.8)
ax_mai_bat.set_ylabel('Effekt (kW)')
ax_mai_bat.set_xlabel('Timer i mai')
ax_mai_bat.set_title('MAI: Batterilading og Utlading')
ax_mai_bat.legend()
ax_mai_bat.grid(True, alpha=0.3)

ax_des_bat.fill_between(x_des, 0, df_des['battery_charge_kw'],
                         alpha=0.7, label='Lading', color='orange')
ax_des_bat.fill_between(x_des, 0, -df_des['battery_discharge_kw'],
                         alpha=0.7, label='Utlading', color='purple')
ax_des_bat.axhline(0, color='black', linewidth=0.8)
ax_des_bat.set_ylabel('Effekt (kW)')
ax_des_bat.set_xlabel('Timer i desember')
ax_des_bat.set_title('DESEMBER: Batterilading og Utlading')
ax_des_bat.legend()
ax_des_bat.grid(True, alpha=0.3)

# ============================================================================
# ROW 3: Energiflyt (Sol, Forbruk, Import, Eksport)
# ============================================================================
ax_mai_flow = axes[2, 0]
ax_des_flow = axes[2, 1]

ax_mai_flow.plot(x_mai, df_mai['pv_kw'], label='Sol', color='gold', linewidth=1.5, alpha=0.8)
ax_mai_flow.plot(x_mai, df_mai['load_kw'], label='Forbruk', color='blue', linewidth=1.5, alpha=0.8)
ax_mai_flow.plot(x_mai, df_mai['grid_import_kw'], label='Import', color='red', linewidth=1, alpha=0.6)
ax_mai_flow.plot(x_mai, df_mai['grid_export_kw'], label='Eksport', color='green', linewidth=1, alpha=0.6)
ax_mai_flow.set_ylabel('Effekt (kW)')
ax_mai_flow.set_xlabel('Timer i mai')
ax_mai_flow.set_title('MAI: Energiflyt')
ax_mai_flow.legend(fontsize=9)
ax_mai_flow.grid(True, alpha=0.3)

ax_des_flow.plot(x_des, df_des['pv_kw'], label='Sol', color='gold', linewidth=1.5, alpha=0.8)
ax_des_flow.plot(x_des, df_des['load_kw'], label='Forbruk', color='blue', linewidth=1.5, alpha=0.8)
ax_des_flow.plot(x_des, df_des['grid_import_kw'], label='Import', color='red', linewidth=1, alpha=0.6)
ax_des_flow.plot(x_des, df_des['grid_export_kw'], label='Eksport', color='green', linewidth=1, alpha=0.6)
ax_des_flow.set_ylabel('Effekt (kW)')
ax_des_flow.set_xlabel('Timer i desember')
ax_des_flow.set_title('DESEMBER: Energiflyt')
ax_des_flow.legend(fontsize=9)
ax_des_flow.grid(True, alpha=0.3)

plt.tight_layout()

output_file = project_root / 'results' / 'kontorbygg_hourly_mai_des.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"✓ Timeplot lagret til: {output_file}")

# Print some statistics
print(f"\n{'='*70}")
print("MAI STATISTIKK")
print(f"{'='*70}")
print(f"SOC gjennomsnitt: {df_mai['soc_pct'].mean():.1f}%")
print(f"SOC min: {df_mai['soc_pct'].min():.1f}%")
print(f"SOC maks: {df_mai['soc_pct'].max():.1f}%")
print(f"Total lading: {df_mai['battery_charge_kw'].sum():.0f} kWh")
print(f"Total utlading: {df_mai['battery_discharge_kw'].sum():.0f} kWh")
print(f"Maks ladeffekt: {df_mai['battery_charge_kw'].max():.1f} kW")
print(f"Maks utladingseffekt: {df_mai['battery_discharge_kw'].max():.1f} kW")

print(f"\n{'='*70}")
print("DESEMBER STATISTIKK")
print(f"{'='*70}")
print(f"SOC gjennomsnitt: {df_des['soc_pct'].mean():.1f}%")
print(f"SOC min: {df_des['soc_pct'].min():.1f}%")
print(f"SOC maks: {df_des['soc_pct'].max():.1f}%")
print(f"Total lading: {df_des['battery_charge_kw'].sum():.0f} kWh")
print(f"Total utlading: {df_des['battery_discharge_kw'].sum():.0f} kWh")
print(f"Maks ladeffekt: {df_des['battery_charge_kw'].max():.1f} kW")
print(f"Maks utladingseffekt: {df_des['battery_discharge_kw'].max():.1f} kW")
