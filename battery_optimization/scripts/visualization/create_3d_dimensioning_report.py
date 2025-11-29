#!/usr/bin/env python3
"""
Generer fullstendig batteridimensjoneringsrapport med 3D-visualiseringer
Samme stil som tidligere rapporter
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns
import json
from pathlib import Path

# Konfigurasjon
results_dir = Path('results/battery_dimensioning_PT60M')
plots_dir = results_dir / 'plots'
plots_dir.mkdir(exist_ok=True)

# Les data
df = pd.read_csv(results_dir / 'grid_search_results.csv')
with open(results_dir / 'dimensioning_summary.json') as f:
    summary = json.load(f)

# Konstantanter
ANNUITY_FACTOR = sum(1 / (1.05**year) for year in range(1, 16))

print("Genererer 3D batteridimensjoneringsrapport...")
print(f"Data: {len(df)} konfigurasjoner")

# ============================================================================
# PLOT 1: 3D SURFACE - NPV som funksjon av kapasitet og effekt
# ============================================================================
print("  [1/8] 3D NPV-overflate...")

fig = plt.figure(figsize=(14, 10))
ax = fig.add_subplot(111, projection='3d')

# Pivot data for 3D surface
pivot_npv = df.pivot(index='P_max_kw', columns='E_nom_kwh', values='npv_nok')
X = pivot_npv.columns.values
Y = pivot_npv.index.values
X, Y = np.meshgrid(X, Y)
Z = pivot_npv.values / 1000  # Convert to 1000 NOK

# Plot surface
surf = ax.plot_surface(X, Y, Z, cmap='RdYlGn', alpha=0.8,
                       vmin=-1000, vmax=0, edgecolor='none')

# Best point
best = df.loc[df['npv_nok'].idxmax()]
ax.scatter([best['E_nom_kwh']], [best['P_max_kw']], [best['npv_nok']/1000],
          color='red', s=200, marker='*', edgecolors='black', linewidths=2,
          label=f'Best: {best["E_nom_kwh"]:.0f} kWh / {best["P_max_kw"]:.0f} kW')

# Labels
ax.set_xlabel('Batterikapasitet (kWh)', fontsize=12, labelpad=10)
ax.set_ylabel('Batterieffekt (kW)', fontsize=12, labelpad=10)
ax.set_zlabel('NPV (1000 NOK)', fontsize=12, labelpad=10)
ax.set_title('Netto nåverdi som funksjon av batteristørrelse\n(3D overflate)',
            fontsize=14, fontweight='bold', pad=20)

# Colorbar
fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5, label='NPV (1000 NOK)')

# Legend
ax.legend(loc='upper left', fontsize=10)

# View angle
ax.view_init(elev=20, azim=135)

plt.tight_layout()
plt.savefig(plots_dir / '1_npv_3d_surface.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# PLOT 2: 3D SCATTER - NPV med fargekoding etter besparelser
# ============================================================================
print("  [2/8] 3D scatter med besparelser...")

fig = plt.figure(figsize=(14, 10))
ax = fig.add_subplot(111, projection='3d')

# Color by annual savings
scatter = ax.scatter(df['E_nom_kwh'], df['P_max_kw'], df['npv_nok']/1000,
                    c=df['annual_savings_nok'], cmap='viridis', s=100, alpha=0.7,
                    edgecolors='black', linewidths=0.5)

# Best point
ax.scatter([best['E_nom_kwh']], [best['P_max_kw']], [best['npv_nok']/1000],
          color='red', s=300, marker='*', edgecolors='black', linewidths=2,
          label=f'Best: {best["E_nom_kwh"]:.0f} kWh / {best["P_max_kw"]:.0f} kW')

# Zero NPV plane
xx, yy = np.meshgrid(np.linspace(df['E_nom_kwh'].min(), df['E_nom_kwh'].max(), 10),
                     np.linspace(df['P_max_kw'].min(), df['P_max_kw'].max(), 10))
zz = np.zeros_like(xx)
ax.plot_surface(xx, yy, zz, alpha=0.2, color='gray')

# Labels
ax.set_xlabel('Batterikapasitet (kWh)', fontsize=12, labelpad=10)
ax.set_ylabel('Batterieffekt (kW)', fontsize=12, labelpad=10)
ax.set_zlabel('NPV (1000 NOK)', fontsize=12, labelpad=10)
ax.set_title('NPV fargekodlet etter årlige besparelser\n(Varmere farge = høyere besparelse)',
            fontsize=14, fontweight='bold', pad=20)

# Colorbar
cbar = fig.colorbar(scatter, ax=ax, shrink=0.5, aspect=5)
cbar.set_label('Årlige besparelser (NOK)', fontsize=10)

ax.legend(loc='upper left', fontsize=10)
ax.view_init(elev=20, azim=135)

plt.tight_layout()
plt.savefig(plots_dir / '2_npv_3d_scatter.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# PLOT 3: 2D HEATMAP - NPV
# ============================================================================
print("  [3/8] NPV heatmap...")

fig, ax = plt.subplots(figsize=(12, 8))

pivot_npv = df.pivot(index='P_max_kw', columns='E_nom_kwh', values='npv_nok')
sns.heatmap(pivot_npv / 1000, annot=True, fmt='.0f', cmap='RdYlGn',
           center=-200, ax=ax, cbar_kws={'label': 'NPV (1000 NOK)'})

ax.set_xlabel('Batterikapasitet (kWh)', fontsize=12)
ax.set_ylabel('Batterieffekt (kW)', fontsize=12)
ax.set_title('Netto nåverdi (NPV) for alle batterikonfigurasjoner\n(Negativ = tap over 15 år)',
            fontsize=14, fontweight='bold')

# Mark best
best_idx = df['npv_nok'].idxmax()
best_row = df.loc[best_idx]
x_idx = list(pivot_npv.columns).index(best_row['E_nom_kwh'])
y_idx = list(pivot_npv.index).index(best_row['P_max_kw'])
ax.add_patch(plt.Rectangle((x_idx, y_idx), 1, 1, fill=False,
                           edgecolor='red', linewidth=3))

plt.tight_layout()
plt.savefig(plots_dir / '3_npv_heatmap.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# PLOT 4: SAVINGS VS CAPEX med break-even linje
# ============================================================================
print("  [4/8] Besparelser vs investeringskostnad...")

fig, ax = plt.subplots(figsize=(12, 8))

# Scatter plot
scatter = ax.scatter(df['capex_nok'] / 1000, df['annual_savings_nok'],
                    c=df['E_nom_kwh'], cmap='plasma', s=100,
                    alpha=0.7, edgecolors='black', linewidths=0.5)

# Break-even line
capex_range = np.linspace(0, df['capex_nok'].max(), 100)
breakeven_savings = capex_range / ANNUITY_FACTOR
ax.plot(capex_range / 1000, breakeven_savings, 'r--', linewidth=2,
       label='Break-even linje (NPV=0)', zorder=5)

# Best point
ax.scatter([best['capex_nok']/1000], [best['annual_savings_nok']],
          color='red', s=300, marker='*', edgecolors='black', linewidths=2,
          label=f'Best: {best["E_nom_kwh"]:.0f} kWh / {best["P_max_kw"]:.0f} kW',
          zorder=10)

# Colorbar
cbar = plt.colorbar(scatter, ax=ax)
cbar.set_label('Batterikapasitet (kWh)', fontsize=10)

ax.set_xlabel('Investeringskostnad (1000 NOK)', fontsize=12)
ax.set_ylabel('Årlige besparelser (NOK)', fontsize=12)
ax.set_title('Årlige besparelser vs investeringskostnad\n(Punkter over rød linje gir positiv NPV)',
            fontsize=14, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(plots_dir / '4_savings_vs_capex.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# PLOT 5: NPV BY SIZE - linjeplot for hver effekt
# ============================================================================
print("  [5/8] NPV etter størrelse...")

fig, ax = plt.subplots(figsize=(12, 8))

# Plot lines for each power level
for P_max in df['P_max_kw'].unique():
    data = df[df['P_max_kw'] == P_max].sort_values('E_nom_kwh')
    ax.plot(data['E_nom_kwh'], data['npv_nok']/1000,
           marker='o', linewidth=2, markersize=6,
           label=f'{P_max:.0f} kW')

# Zero line
ax.axhline(0, color='red', linestyle='--', linewidth=2, label='Break-even (NPV=0)')

ax.set_xlabel('Batterikapasitet (kWh)', fontsize=12)
ax.set_ylabel('NPV (1000 NOK)', fontsize=12)
ax.set_title('Netto nåverdi som funksjon av batteristørrelse\n(Negativ verdi = ulønnsomt)',
            fontsize=14, fontweight='bold')
ax.legend(title='Batterieffekt', fontsize=9, ncol=2)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(plots_dir / '5_npv_by_size.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# PLOT 6: BREAK-EVEN COST - hva må batteripris være?
# ============================================================================
print("  [6/8] Break-even batterikostnad...")

# Calculate break-even cost for each config
df['breakeven_cost_nok_per_kwh'] = (df['annual_savings_nok'] * ANNUITY_FACTOR) / df['E_nom_kwh']

# Market reference lines
TODAY_MARKET = 5000  # NOK/kWh
TARGET = 2500  # NOK/kWh

fig, ax = plt.subplots(figsize=(12, 8))

# Plot lines for each capacity
for E_nom in sorted(df['E_nom_kwh'].unique()):
    data = df[df['E_nom_kwh'] == E_nom].sort_values('P_max_kw')
    ax.plot(data['P_max_kw'], data['breakeven_cost_nok_per_kwh'],
           marker='o', linewidth=2, markersize=6,
           label=f'{E_nom:.0f} kWh')

# Reference lines
ax.axhline(TODAY_MARKET, color='red', linestyle='--', linewidth=2,
          label=f'Dagens markedspris ({TODAY_MARKET} NOK/kWh)')
ax.axhline(TARGET, color='green', linestyle='--', linewidth=2,
          label=f'Målpris ({TARGET} NOK/kWh)')

ax.set_xlabel('Batterieffekt (kW)', fontsize=12)
ax.set_ylabel('Break-even batterikostnad (NOK/kWh)', fontsize=12)
ax.set_title('Nødvendig batteripris for lønnsomhet (NPV=0)\n(Lavere kurve = lavere krav)',
            fontsize=14, fontweight='bold')
ax.legend(title='Batterikapasitet', fontsize=9, ncol=2)
ax.grid(True, alpha=0.3)
ax.set_ylim(0, 6000)

plt.tight_layout()
plt.savefig(plots_dir / '6_breakeven_cost.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# PLOT 7: TOP 10 COMPARISON
# ============================================================================
print("  [7/8] Top 10 sammenligning...")

top10 = df.nlargest(10, 'npv_nok')

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# NPV
ax = axes[0, 0]
configs = [f'{row["E_nom_kwh"]:.0f}kWh/{row["P_max_kw"]:.0f}kW'
          for _, row in top10.iterrows()]
ax.barh(configs, top10['npv_nok']/1000, color='steelblue', edgecolor='black')
ax.axvline(0, color='red', linestyle='--', linewidth=2)
ax.set_xlabel('NPV (1000 NOK)', fontsize=11)
ax.set_title('NPV for top 10 konfigurasjoner', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3, axis='x')

# Savings
ax = axes[0, 1]
ax.barh(configs, top10['annual_savings_nok'], color='green', edgecolor='black')
ax.set_xlabel('Årlige besparelser (NOK)', fontsize=11)
ax.set_title('Årlige besparelser for top 10', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3, axis='x')

# CAPEX
ax = axes[1, 0]
ax.barh(configs, top10['capex_nok']/1000, color='orange', edgecolor='black')
ax.set_xlabel('CAPEX (1000 NOK)', fontsize=11)
ax.set_title('Investeringskostnad for top 10', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3, axis='x')

# Payback
ax = axes[1, 1]
payback_years = top10['capex_nok'] / top10['annual_savings_nok']
colors = ['green' if pb <= 15 else 'red' for pb in payback_years]
ax.barh(configs, payback_years, color=colors, edgecolor='black')
ax.axvline(15, color='red', linestyle='--', linewidth=2, label='Prosjektlevetid (15 år)')
ax.set_xlabel('Tilbakebetalingstid (år)', fontsize=11)
ax.set_title('Tilbakebetalingstid for top 10', fontsize=12, fontweight='bold')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3, axis='x')

plt.tight_layout()
plt.savefig(plots_dir / '7_top10_comparison.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# PLOT 8: 3D CONTOUR - NPV konturlinjer
# ============================================================================
print("  [8/8] 3D konturplot...")

fig = plt.figure(figsize=(14, 10))
ax = fig.add_subplot(111, projection='3d')

# Prepare data
pivot_npv = df.pivot(index='P_max_kw', columns='E_nom_kwh', values='npv_nok')
X = pivot_npv.columns.values
Y = pivot_npv.index.values
X, Y = np.meshgrid(X, Y)
Z = pivot_npv.values / 1000

# Contour plot
contours = ax.contour3D(X, Y, Z, levels=20, cmap='RdYlGn', alpha=0.7)

# Best point
ax.scatter([best['E_nom_kwh']], [best['P_max_kw']], [best['npv_nok']/1000],
          color='red', s=300, marker='*', edgecolors='black', linewidths=2,
          label=f'Best: {best["E_nom_kwh"]:.0f} kWh / {best["P_max_kw"]:.0f} kW')

# Labels
ax.set_xlabel('Batterikapasitet (kWh)', fontsize=12, labelpad=10)
ax.set_ylabel('Batterieffekt (kW)', fontsize=12, labelpad=10)
ax.set_zlabel('NPV (1000 NOK)', fontsize=12, labelpad=10)
ax.set_title('NPV konturlinjer i 3D\n(Høyere linjer = bedre økonomi)',
            fontsize=14, fontweight='bold', pad=20)

# Colorbar
fig.colorbar(contours, ax=ax, shrink=0.5, aspect=5, label='NPV (1000 NOK)')

ax.legend(loc='upper left', fontsize=10)
ax.view_init(elev=25, azim=135)

plt.tight_layout()
plt.savefig(plots_dir / '8_npv_3d_contour.png', dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# GENERATE TEXT REPORT
# ============================================================================
print("\nGenererer tekstrapport...")

report_path = results_dir / 'FULLSTENDIG_RAPPORT.md'

# Calculate additional metrics
baseline_cost = summary['baseline']['annual_cost_nok']
baseline_consumption = summary['baseline']['annual_consumption_kwh']
baseline_production = summary['baseline']['annual_pv_production_kwh']

best_config = df.loc[df['npv_nok'].idxmax()]
worst_config = df.loc[df['npv_nok'].idxmin()]

report = f"""# BATTERIDIMENSJONERING - FULLSTENDIG ANALYSE MED 3D-VISUALISERINGER

**Analysedato**: {summary['analysis_metadata']['timestamp'][:10]}
**Simuleringsperiode**: {summary['analysis_metadata']['year']} (365 dager)
**Optimeringsmodus**: Daglig rullerende horisont (24 timer)
**Tidsoppløsning**: {summary['analysis_metadata']['resolution']}
**Diskonteringsrente**: {summary['analysis_metadata']['discount_rate']*100:.1f}%
**Prosjektlevetid**: {summary['analysis_metadata']['project_years']} år

---

## 📋 EXECUTIVE SUMMARY

### 🎯 Hovedkonklusjon
Med **{baseline_consumption:.0f} kWh årlig forbruk** og **{baseline_production:.0f} kWh PV-produksjon** er batterilager
**IKKE økonomisk lønnsomt** ved dagens markedspriser ({summary['analysis_metadata']['battery_cost_per_kwh']:.0f} NOK/kWh).

### 💡 Beste konfigurasjon (Grid Search)
- **Batteri**: {best_config['E_nom_kwh']:.0f} kWh / {best_config['P_max_kw']:.0f} kW
- **C-rate**: {best_config['P_max_kw']/best_config['E_nom_kwh']:.2f}
- **NPV**: {best_config['npv_nok']:,.0f} NOK (tap over 15 år)
- **Årlige besparelser**: {best_config['annual_savings_nok']:,.0f} NOK
- **Investeringskostnad**: {best_config['capex_nok']:,.0f} NOK
- **Tilbakebetalingstid**: {best_config['capex_nok']/best_config['annual_savings_nok']:.1f} år

### ⚠️ Break-even analyse
| Batterikapasitet | Break-even pris (NOK/kWh) | Prisreduksjon nødvendig |
|------------------|---------------------------|------------------------|
| {top10.iloc[0]['E_nom_kwh']:.0f} kWh | {top10.iloc[0]['breakeven_cost_nok_per_kwh']:.0f} | {(1 - top10.iloc[0]['breakeven_cost_nok_per_kwh']/5000)*100:.0f}% |
| {top10.iloc[4]['E_nom_kwh']:.0f} kWh | {top10.iloc[4]['breakeven_cost_nok_per_kwh']:.0f} | {(1 - top10.iloc[4]['breakeven_cost_nok_per_kwh']/5000)*100:.0f}% |
| {top10.iloc[9]['E_nom_kwh']:.0f} kWh | {top10.iloc[9]['breakeven_cost_nok_per_kwh']:.0f} | {(1 - top10.iloc[9]['breakeven_cost_nok_per_kwh']/5000)*100:.0f}% |

---

## 🏗️ SYSTEMOPPSETT

### Anlegg
- **PV-kapasitet**: 150 kWp (sør, 25° helning)
- **Inverter**: 110 kW
- **Nettgrense**: 70 kW
- **Lokasjon**: Stavanger (58.97°N, 5.73°E)

### Årlige energimengder ({summary['analysis_metadata']['year']})
| Type | Verdi | Merknad |
|------|-------|---------|
| PV-produksjon | {baseline_production:,.0f} kWh | Faktisk produksjon |
| Forbruk | {baseline_consumption:,.0f} kWh | Generert forbruksprofil |
| Selvforbruksandel (uten batteri) | ~{(baseline_consumption/baseline_production)*100:.0f}% | Direkteforbruk |
| Eksport til nett | ~{(baseline_production - baseline_consumption):,.0f} kWh | ~{((baseline_production - baseline_consumption)/baseline_production)*100:.0f}% av produksjon |

### Økonomiske forutsetninger
- **Batteripris**: {summary['analysis_metadata']['battery_cost_per_kwh']:,.0f} NOK/kWh (CAPEX)
- **Diskonteringsrente**: {summary['analysis_metadata']['discount_rate']*100:.1f}% per år
- **Prosjektlevetid**: {summary['analysis_metadata']['project_years']} år
- **Annuitetsfaktor**: {ANNUITY_FACTOR:.2f}

### Tariffstruktur (Lnett)
- **Nettsalg**: ~0.10 NOK/kWh (gjennomsnitt)
- **Spotpris**: Variabel, gjennomsnitt ~0.72 NOK/kWh
- **Effekttariff**: Progressiv, 5 trinn fra 48-213 NOK/kW/mnd

---

## 📊 GRID SEARCH RESULTATER

### Søkeområde
- **Kapasitet**: {summary['grid_search']['E_nom_range_kwh'][0]:.0f} - {summary['grid_search']['E_nom_range_kwh'][1]:.0f} kWh ({len(df['E_nom_kwh'].unique())} nivåer)
- **Effekt**: {summary['grid_search']['P_max_range_kw'][0]:.0f} - {summary['grid_search']['P_max_range_kw'][1]:.0f} kW ({len(df['P_max_kw'].unique())} nivåer)
- **Totalt**: {summary['grid_search']['total_combinations']} konfigurasjoner testet

### Beste konfigurasjon
```
Kapasitet:       {best_config['E_nom_kwh']:.0f} kWh
Effekt:          {best_config['P_max_kw']:.0f} kW
C-rate:          {best_config['P_max_kw']/best_config['E_nom_kwh']:.2f}

NPV (15 år):     {best_config['npv_nok']:,.0f} NOK
Årlige besparelser: {best_config['annual_savings_nok']:,.0f} NOK
CAPEX:           {best_config['capex_nok']:,.0f} NOK
Tilbakebetalingstid: {best_config['capex_nok']/best_config['annual_savings_nok']:.1f} år

Break-even pris: {best_config['breakeven_cost_nok_per_kwh']:,.0f} NOK/kWh
Prisreduksjon:   {(1 - best_config['breakeven_cost_nok_per_kwh']/5000)*100:.0f}% fra dagens nivå
```

### Verste konfigurasjon
```
Kapasitet:       {worst_config['E_nom_kwh']:.0f} kWh
Effekt:          {worst_config['P_max_kw']:.0f} kW
NPV (15 år):     {worst_config['npv_nok']:,.0f} NOK
Tap vs beste:    {(best_config['npv_nok'] - worst_config['npv_nok']):,.0f} NOK
```

---

## 🔬 POWELL'S METHOD REFINEMENT

Powell's metode er en gradientfri optimaliseringsalgoritme som raffinerer grid search-resultatet.

### Optimalt resultat
```
Kapasitet:       {summary['powell_refinement']['optimal_E_nom_kwh']:.2f} kWh
Effekt:          {summary['powell_refinement']['optimal_P_max_kw']:.2f} kW
C-rate:          {summary['economic_metrics']['c_rate']:.2f}

NPV (15 år):     {summary['powell_refinement']['optimal_npv_nok']:,.0f} NOK
Forbedring:      {summary['powell_refinement']['improvement_over_grid_nok']:,.0f} NOK
Forbedring:      {summary['powell_refinement']['improvement_percent']:.1f}%

Årlige besparelser: {summary['economic_metrics']['annual_savings_nok']:,.0f} NOK
CAPEX:           {summary['economic_metrics']['capex_nok']:,.0f} NOK
Tilbakebetalingstid: {summary['economic_metrics']['payback_years']:.1f} år

Break-even pris: {summary['economic_metrics']['breakeven_cost_per_kwh']:,.0f} NOK/kWh
```

### Tolkning
Powell-refinementet finner et **mikrobatteri** ({summary['powell_refinement']['optimal_E_nom_kwh']:.1f} kWh) med høy effekt
({summary['powell_refinement']['optimal_P_max_kw']:.0f} kW) som gir bedre NPV enn grid search. Dette indikerer at:

1. **Små batterier** reduserer CAPEX mer enn de reduserer inntekter
2. **Høy C-rate** (effekt/kapasitet) gir bedre fleksibilitet
3. Grid search-beste ({best_config['E_nom_kwh']:.0f} kWh) er fortsatt **praktisk bedre**

**Anbefaling**: Bruk grid search-beste for realistisk dimensjonering.

---

## 📈 TRENDER OG MØNSTRE

### Kapasitetseffekter
"""

# Add capacity analysis
capacity_groups = df.groupby('E_nom_kwh').agg({
    'npv_nok': 'mean',
    'annual_savings_nok': 'mean',
    'capex_nok': 'first'
}).reset_index()

report += "\n| Kapasitet | Gj.snitt NPV | Gj.snitt besparelser | CAPEX |\n"
report += "|-----------|--------------|----------------------|-------|\n"
for _, row in capacity_groups.iterrows():
    report += f"| {row['E_nom_kwh']:.0f} kWh | {row['npv_nok']:,.0f} NOK | {row['annual_savings_nok']:,.0f} NOK | {row['capex_nok']:,.0f} NOK |\n"

report += f"""

**Observasjon**: NPV forverres med økende kapasitet fordi:
- CAPEX vokser lineært med størrelse
- Besparelser øker saktere (avtagende marginalnytte)
- Større batterier gir mer tap (virkningsgrad)

### Effekteffekter
"""

power_groups = df.groupby('P_max_kw').agg({
    'npv_nok': 'mean',
    'annual_savings_nok': 'mean'
}).reset_index()

report += "\n| Effekt | Gj.snitt NPV | Gj.snitt besparelser |\n"
report += "|--------|--------------|----------------------|\n"
for _, row in power_groups.iterrows():
    report += f"| {row['P_max_kw']:.0f} kW | {row['npv_nok']:,.0f} NOK | {row['annual_savings_nok']:,.0f} NOK |\n"

report += f"""

**Observasjon**: Effekt har **mindre betydning** enn kapasitet fordi:
- Kostnaden er lav sammenlignet med energilagring
- Nettgrensen (70 kW) begrenser effektbehov
- Høy effekt gir mer fleksibilitet i optimaliseringen

---

## 🎨 VISUALISERINGER

Alle figurer er lagret i `plots/` mappen:

### 3D-overflater og scatter
1. **1_npv_3d_surface.png**: NPV som 3D-overflate av kapasitet og effekt
2. **2_npv_3d_scatter.png**: NPV som 3D-scatter fargekodlet etter besparelser
3. **8_npv_3d_contour.png**: NPV konturlinjer i 3D

### 2D-analyser
4. **3_npv_heatmap.png**: NPV heatmap for alle konfigurasjoner
5. **4_savings_vs_capex.png**: Besparelser vs investeringskostnad med break-even linje
6. **5_npv_by_size.png**: NPV som funksjon av batteristørrelse (linjeplot per effekt)
7. **6_breakeven_cost.png**: Nødvendig batteripris for lønnsomhet
8. **7_top10_comparison.png**: Sammenligning av top 10 konfigurasjoner

---

## 🎯 ANBEFALINGER

### Kortsiktige (0-2 år)
1. **IKKE invester** i batterilager ved dagens priser (5 000 NOK/kWh)
2. **Overvåk** markedet for prisutvikling på LFP-batterier
3. **Optimaliser** forbruksprofil for økt direkteforbruk (gratis selvforbruk)
4. **Vurder** andre investeringer med bedre NPV

### Mellomlange (2-5 år)
1. **Revurder** ved batteripris < {best_config['breakeven_cost_nok_per_kwh']:.0f} NOK/kWh (break-even)
2. **Installer** hvis prisreduksjon på {(1 - best_config['breakeven_cost_nok_per_kwh']/5000)*100:.0f}% oppnås
3. **Optimaliser størrelse** med oppdatert grid search når priser faller
4. **Vurder** alternative batteriteknologier (nye kjemier)

### Langsiktige (5+ år)
1. **Forventer** at batterier blir lønnsomme når priser når 2 500-3 000 NOK/kWh
2. **Kombiner** med oppgradering av PV-system hvis ekspansjon planlegges
3. **Utforsk** Vehicle-to-Grid (V2G) hvis bilpark elektrisfiseres
4. **Vurder** deltakelse i frekvensreguleringsmarkeder (mFRR, aFRR)

---

## ⚠️ RISIKOANALYSE

### Økonomiske risikoer
| Risiko | Sannsynlighet | Påvirkning | Tiltak |
|--------|---------------|------------|--------|
| Batteripriser faller ikke | Middels | Høy | Vent med investering |
| Spotpriser synker | Middels | Middels | Reduserer arbitrasjeverdi |
| Effekttariffer øker | Lav | Positiv | Øker lønnsomhet |
| Teknologi foreldes | Middels | Middels | Leasing i stedet for kjøp |

### Tekniske risikoer
| Risiko | Sannsynlighet | Påvirkning | Tiltak |
|--------|---------------|------------|--------|
| Degradering raskere enn forventet | Lav | Middels | Garanti på kapasitet |
| Inverter-kompatibilitet | Lav | Lav | Spesifiser krav tidlig |
| Nettgrense endres | Lav | Middels | Følg nettselskapets planer |

---

## 📚 REFERANSER

### Datakilder
- **PV-produksjon**: PVGIS (Photovoltaic Geographical Information System)
- **Spotpriser**: ENTSO-E Transparency Platform (NO2 prisområde)
- **Forbruksprofil**: Generert kommersiell profil med {baseline_consumption:.0f} kWh årlig
- **Tariffstruktur**: Lnett AS (progressiv effekttariff)

### Metode
- **Optimalisering**: Lineær programmering (HiGHS solver)
- **Horisont**: 24 timer rullerende (365 daglige optimaliseringer)
- **Grid search**: {summary['grid_search']['total_combinations']} konfigurasjoner
- **Refinement**: Powell's method (gradientfri optimalisering)

### Verktøy
- **Python**: 3.11+
- **Optimalisering**: scipy.optimize, HiGHS LP-solver
- **Visualisering**: matplotlib, seaborn
- **Analyse**: pandas, numpy

---

## 📞 KONTAKT

For spørsmål om denne analysen, kontakt:
- **Prosjekt**: Battery Optimization System (BOS)
- **Dato**: {summary['analysis_metadata']['timestamp'][:10]}
- **Konfigurasjon**: `configs/dimensioning_2024.yaml`

---

**💡 Merk**: Denne analysen er basert på simulerte data for 2024 med generert forbruksprofil.
For en endelig investeringsbeslutning bør analysen kjøres med faktisk historisk forbruksdata.

**🔄 Oppdatering**: Kjør `python run_battery_dimensioning_PT60M.py` for å oppdatere analysen med nye data.
"""

# Write report
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report)

print(f"\n✅ Rapport generert: {report_path}")
print(f"✅ 8 plott lagret i: {plots_dir}")
print("\nFiler:")
print("  - FULLSTENDIG_RAPPORT.md")
print("  - plots/1_npv_3d_surface.png")
print("  - plots/2_npv_3d_scatter.png")
print("  - plots/3_npv_heatmap.png")
print("  - plots/4_savings_vs_capex.png")
print("  - plots/5_npv_by_size.png")
print("  - plots/6_breakeven_cost.png")
print("  - plots/7_top10_comparison.png")
print("  - plots/8_npv_3d_contour.png")
