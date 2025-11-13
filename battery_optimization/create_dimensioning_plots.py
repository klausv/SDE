#!/usr/bin/env python3
"""
Create visualization plots for battery dimensioning results.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Load data
results_dir = Path('results/battery_dimensioning_PT60M')
df = pd.read_csv(results_dir / 'grid_search_results.csv')

# Create output directory for plots
plots_dir = results_dir / 'plots'
plots_dir.mkdir(exist_ok=True)

print('Creating dimensioning visualization plots...')
print(f'Data shape: {df.shape}')
print(f'E_nom range: {df.E_nom_kwh.min():.0f} - {df.E_nom_kwh.max():.0f} kWh')
print(f'P_max range: {df.P_max_kw.min():.0f} - {df.P_max_kw.max():.0f} kW')
print()

# ============================================================================
# Plot 1: NPV Heatmap
# ============================================================================
print('Creating NPV heatmap...')
fig, ax = plt.subplots(figsize=(12, 8))

pivot_npv = df.pivot(index='P_max_kw', columns='E_nom_kwh', values='npv_nok')
sns.heatmap(pivot_npv / 1000, annot=True, fmt='.0f', cmap='RdYlGn', 
            center=-200, ax=ax, cbar_kws={'label': 'NPV (1000 NOK)'})

ax.set_title('NPV for forskjellige batterikonfigurasjoner\n(Negativt = tap)', 
             fontsize=14, fontweight='bold')
ax.set_xlabel('Batterikapasitet (kWh)', fontsize=12)
ax.set_ylabel('Batterieffekt (kW)', fontsize=12)

plt.tight_layout()
plt.savefig(plots_dir / '1_npv_heatmap.png', dpi=300, bbox_inches='tight')
print(f'✓ Saved: {plots_dir / "1_npv_heatmap.png"}')
plt.close()

# ============================================================================
# Plot 2: Annual Savings vs CAPEX
# ============================================================================
print('Creating annual savings vs CAPEX scatter...')
fig, ax = plt.subplots(figsize=(12, 8))

# Color by E_nom
scatter = ax.scatter(df['capex_nok'] / 1000, df['annual_savings_nok'], 
                     c=df['E_nom_kwh'], s=100, alpha=0.7, cmap='viridis',
                     edgecolors='black', linewidth=0.5)

# Add break-even line (where NPV = 0)
# NPV = 0 when PV(savings) = CAPEX
# For 5% discount rate and 15 years: annuity factor ≈ 10.38
annuity_factor = sum(1 / (1.05**year) for year in range(1, 16))
capex_range = np.linspace(0, df['capex_nok'].max(), 100)
breakeven_savings = capex_range / annuity_factor

ax.plot(capex_range / 1000, breakeven_savings, 'r--', linewidth=2, 
        label='Break-even linje (NPV=0)')

# Annotate best point
best_idx = df['npv_nok'].idxmax()
best = df.iloc[best_idx]
ax.annotate(f'Beste: {best.E_nom_kwh:.0f}kWh/{best.P_max_kw:.0f}kW\nNPV: {best.npv_nok/1000:.0f}k NOK',
            xy=(best.capex_nok/1000, best.annual_savings_nok),
            xytext=(best.capex_nok/1000 + 50, best.annual_savings_nok + 2000),
            arrowprops=dict(arrowstyle='->', color='red', lw=2),
            fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))

cbar = plt.colorbar(scatter, ax=ax, label='Batterikapasitet (kWh)')
ax.set_xlabel('CAPEX (1000 NOK)', fontsize=12)
ax.set_ylabel('Årlige besparelser (NOK)', fontsize=12)
ax.set_title('Årlige besparelser vs Investeringskostnad\n(Punkter over rød linje gir positiv NPV)', 
             fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=11)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(plots_dir / '2_savings_vs_capex.png', dpi=300, bbox_inches='tight')
print(f'✓ Saved: {plots_dir / "2_savings_vs_capex.png"}')
plt.close()

# ============================================================================
# Plot 3: NPV by Battery Size (grouped by power)
# ============================================================================
print('Creating NPV by battery size...')
fig, ax = plt.subplots(figsize=(14, 8))

for p_max in sorted(df['P_max_kw'].unique()):
    subset = df[df['P_max_kw'] == p_max].sort_values('E_nom_kwh')
    ax.plot(subset['E_nom_kwh'], subset['npv_nok'] / 1000, 
            marker='o', linewidth=2, markersize=8, 
            label=f'{p_max:.0f} kW', alpha=0.8)

ax.axhline(y=0, color='red', linestyle='--', linewidth=2, label='Break-even (NPV=0)')
ax.set_xlabel('Batterikapasitet (kWh)', fontsize=12)
ax.set_ylabel('NPV (1000 NOK)', fontsize=12)
ax.set_title('NPV som funksjon av batteristørrelse\n(Negative verdier = ulønnsomt)', 
             fontsize=14, fontweight='bold')
ax.legend(title='Batterieffekt', fontsize=9, ncol=2, loc='lower left')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(plots_dir / '3_npv_by_size.png', dpi=300, bbox_inches='tight')
print(f'✓ Saved: {plots_dir / "3_npv_by_size.png"}')
plt.close()

# ============================================================================
# Plot 4: Payback Period Heatmap
# ============================================================================
print('Creating payback period heatmap...')
fig, ax = plt.subplots(figsize=(12, 8))

# Calculate payback period (simple)
df['payback_years'] = df['capex_nok'] / df['annual_savings_nok']
df.loc[df['annual_savings_nok'] <= 0, 'payback_years'] = np.inf

pivot_payback = df.pivot(index='P_max_kw', columns='E_nom_kwh', values='payback_years')
# Cap at 30 years for visualization
pivot_payback_capped = pivot_payback.clip(upper=30)

sns.heatmap(pivot_payback_capped, annot=True, fmt='.1f', cmap='RdYlGn_r', 
            center=15, ax=ax, cbar_kws={'label': 'Tilbakebetalingstid (år)'})

ax.set_title('Tilbakebetalingstid for forskjellige batterikonfigurasjoner\n(Prosjektlevetid: 15 år)', 
             fontsize=14, fontweight='bold')
ax.set_xlabel('Batterikapasitet (kWh)', fontsize=12)
ax.set_ylabel('Batterieffekt (kW)', fontsize=12)

plt.tight_layout()
plt.savefig(plots_dir / '4_payback_period_heatmap.png', dpi=300, bbox_inches='tight')
print(f'✓ Saved: {plots_dir / "4_payback_period_heatmap.png"}')
plt.close()

# ============================================================================
# Plot 5: Break-even Battery Cost
# ============================================================================
print('Creating break-even cost analysis...')
fig, ax = plt.subplots(figsize=(12, 8))

# Calculate break-even cost per kWh for each configuration
annuity_factor = sum(1 / (1.05**year) for year in range(1, 16))
df['breakeven_cost_per_kwh'] = (df['annual_savings_nok'] * annuity_factor) / df['E_nom_kwh']

# Filter to show only reasonable ranges
df_filtered = df[df['breakeven_cost_per_kwh'] < 10000]

for p_max in sorted(df_filtered['P_max_kw'].unique()):
    subset = df_filtered[df_filtered['P_max_kw'] == p_max].sort_values('E_nom_kwh')
    ax.plot(subset['E_nom_kwh'], subset['breakeven_cost_per_kwh'], 
            marker='o', linewidth=2, markersize=8, 
            label=f'{p_max:.0f} kW', alpha=0.8)

ax.axhline(y=5000, color='red', linestyle='--', linewidth=2, 
           label='Dagens markedspris (5000 NOK/kWh)')
ax.axhline(y=2500, color='green', linestyle='--', linewidth=2, 
           label='Målpris (2500 NOK/kWh)')

ax.set_xlabel('Batterikapasitet (kWh)', fontsize=12)
ax.set_ylabel('Break-even batterikostnad (NOK/kWh)', fontsize=12)
ax.set_title('Break-even batterikostnad for lønnsomhet\n(Konfigurasjon lønnsom hvis break-even > markedspris)', 
             fontsize=14, fontweight='bold')
ax.legend(title='Batterieffekt', fontsize=9, ncol=2, loc='upper right')
ax.grid(True, alpha=0.3)
ax.set_ylim(0, 8000)

plt.tight_layout()
plt.savefig(plots_dir / '5_breakeven_cost.png', dpi=300, bbox_inches='tight')
print(f'✓ Saved: {plots_dir / "5_breakeven_cost.png"}')
plt.close()

# ============================================================================
# Plot 6: Top 10 Configurations Comparison
# ============================================================================
print('Creating top 10 configurations comparison...')
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

# Get top 10 by NPV
top10 = df.nlargest(10, 'npv_nok').copy()
top10['config'] = top10['E_nom_kwh'].astype(int).astype(str) + 'kWh/' + top10['P_max_kw'].astype(int).astype(str) + 'kW'

# 1. NPV comparison
ax1.barh(range(len(top10)), top10['npv_nok']/1000, color='steelblue', edgecolor='black')
ax1.set_yticks(range(len(top10)))
ax1.set_yticklabels(top10['config'])
ax1.set_xlabel('NPV (1000 NOK)', fontsize=11)
ax1.set_title('NPV for top 10 konfigurasjoner', fontsize=12, fontweight='bold')
ax1.axvline(x=0, color='red', linestyle='--', linewidth=1)
ax1.grid(axis='x', alpha=0.3)

# 2. Annual savings comparison
ax2.barh(range(len(top10)), top10['annual_savings_nok'], color='green', alpha=0.7, edgecolor='black')
ax2.set_yticks(range(len(top10)))
ax2.set_yticklabels(top10['config'])
ax2.set_xlabel('Årlige besparelser (NOK)', fontsize=11)
ax2.set_title('Årlige besparelser for top 10', fontsize=12, fontweight='bold')
ax2.grid(axis='x', alpha=0.3)

# 3. CAPEX comparison
ax3.barh(range(len(top10)), top10['capex_nok']/1000, color='coral', edgecolor='black')
ax3.set_yticks(range(len(top10)))
ax3.set_yticklabels(top10['config'])
ax3.set_xlabel('CAPEX (1000 NOK)', fontsize=11)
ax3.set_title('Investeringskostnad for top 10', fontsize=12, fontweight='bold')
ax3.grid(axis='x', alpha=0.3)

# 4. Payback period comparison
ax4.barh(range(len(top10)), top10['payback_years'], color='purple', alpha=0.7, edgecolor='black')
ax4.set_yticks(range(len(top10)))
ax4.set_yticklabels(top10['config'])
ax4.set_xlabel('Tilbakebetalingstid (år)', fontsize=11)
ax4.set_title('Tilbakebetalingstid for top 10', fontsize=12, fontweight='bold')
ax4.axvline(x=15, color='red', linestyle='--', linewidth=2, label='Prosjektlevetid (15 år)')
ax4.legend(fontsize=9)
ax4.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig(plots_dir / '6_top10_comparison.png', dpi=300, bbox_inches='tight')
print(f'✓ Saved: {plots_dir / "6_top10_comparison.png"}')
plt.close()

print()
print('='*80)
print('All plots created successfully!')
print(f'Location: {plots_dir.absolute()}')
print('='*80)

# Create index file
with open(plots_dir / 'README.txt', 'w') as f:
    f.write("""BATTERIDIMENSJONERING - VISUALISERINGSPLOTT

Plottoversikt:
=============

1. npv_heatmap.png
   - Varmekart som viser NPV for alle batterikonfigurasjoner
   - Akser: Batterikapasitet (kWh) vs Batterieffekt (kW)
   - Fargekode: Grønn = bedre, rød = verre

2. savings_vs_capex.png
   - Årlige besparelser vs investeringskostnad
   - Rød linje viser break-even punkt (NPV=0)
   - Punkter over linjen ville vært lønnsomme

3. npv_by_size.png
   - NPV som funksjon av batteristørrelse
   - Separate linjer for hver batterieffekt
   - Viser hvordan NPV avtar med økende størrelse

4. payback_period_heatmap.png
   - Tilbakebetalingstid for alle konfigurasjoner
   - Referanse: Prosjektlevetid er 15 år
   - Grønn = rask tilbakebetaling, rød = lang

5. breakeven_cost.png
   - Break-even batterikostnad for å oppnå lønnsomhet
   - Sammenligning med dagens markedspris (5000 NOK/kWh)
   - Viser hvor mye prisen må falle for lønnsomhet

6. top10_comparison.png
   - Detaljert sammenligning av de 10 beste konfigurasjonene
   - Fire subplot: NPV, besparelser, CAPEX, tilbakebetalingstid

Alle plott er generert med høy oppløsning (300 DPI) for rapportbruk.
""")

