"""
Enhanced visualization of historical electricity prices with insights and annotations
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import seaborn as sns
from pathlib import Path
import numpy as np

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (20, 14)
plt.rcParams['font.size'] = 10

# Load data
data_file = Path('results/historical_analysis/NO1_annual_prices_2003_2024.csv')
df = pd.read_csv(data_file)

# Create figure with subplots
fig = plt.figure(figsize=(20, 16))
gs = fig.add_gridspec(3, 2, hspace=0.35, wspace=0.25)

# Define color scheme
color_normal = '#2E86AB'
color_transition = '#F18F01'
color_new_normal = '#C73E1D'
color_volatility = '#A23B72'

# ============================================================================
# PLOT 1: Annual Average Prices with Timeline Annotations
# ============================================================================
ax1 = fig.add_subplot(gs[0, :])

# Plot price line
ax1.plot(df['year'], df['mean_eur_mwh'],
         marker='o', linewidth=3, markersize=8,
         color=color_normal, label='Gjennomsnittspris', zorder=3)

# Add shaded uncertainty band
ax1.fill_between(df['year'],
                 df['mean_eur_mwh'] - df['std_eur_mwh'],
                 df['mean_eur_mwh'] + df['std_eur_mwh'],
                 alpha=0.2, color=color_normal, zorder=2)

# Add background shading for different periods
ax1.axvspan(2014, 2019.5, alpha=0.1, color='green', zorder=1)
ax1.axvspan(2019.5, 2021.5, alpha=0.15, color='orange', zorder=1)
ax1.axvspan(2021.5, 2024.5, alpha=0.1, color='red', zorder=1)

# Key event annotations - adjusted positions to prevent overlap
events = [
    (2020, 110, 'COVID-19\nEtterspørsel-\nsjokk\nVol: 89%', 'top'),
    (2021, 170, 'NordLink\n(Mai 2021)\n1400 MW\ntil DE', 'top'),
    (2021.6, 230, 'North Sea\nLink (Okt)\n1400 MW\ntil UK', 'top'),
    (2021.9, 25, 'Single Price-\nSingle Position\n(Nov 2021)', 'bottom'),
    (2022.3, 270, 'Energi-\nkrise\n193 EUR/\nMWh', 'top'),
]

for year, y_pos, text, position in events:
    if position == 'top':
        ax1.annotate(text, xy=(year, df[df['year']==int(year)]['mean_eur_mwh'].values[0] if int(year) in df['year'].values else y_pos),
                    xytext=(year, y_pos),
                    fontsize=8, ha='center',
                    bbox=dict(boxstyle='round,pad=0.4', facecolor='yellow', alpha=0.75, linewidth=1.2),
                    arrowprops=dict(arrowstyle='->', lw=1.2, color='black'))
    else:
        ax1.annotate(text, xy=(year, df[df['year']==int(year)]['mean_eur_mwh'].values[0] if int(year) in df['year'].values else 60),
                    xytext=(year, y_pos),
                    fontsize=8, ha='center',
                    bbox=dict(boxstyle='round,pad=0.4', facecolor='lightblue', alpha=0.75, linewidth=1.2),
                    arrowprops=dict(arrowstyle='->', lw=1.2, color='black'))

# Period labels - positioned at different heights to avoid overlap
ax1.text(2016.5, 285, 'STABIL PERIODE\nVolatilitet 16-39%',
         fontsize=10, ha='center', weight='bold',
         bbox=dict(boxstyle='round,pad=0.6', facecolor='lightgreen', alpha=0.7, linewidth=1.5))

ax1.text(2020.5, 270, 'OVERGANG\nReformer',
         fontsize=10, ha='center', weight='bold',
         bbox=dict(boxstyle='round,pad=0.6', facecolor='lightyellow', alpha=0.7, linewidth=1.5))

ax1.text(2023, 285, 'NYTT NORMALT\nVolatilitet 57-79%',
         fontsize=10, ha='center', weight='bold',
         bbox=dict(boxstyle='round,pad=0.6', facecolor='lightcoral', alpha=0.7, linewidth=1.5))

ax1.set_xlabel('År', fontsize=14, fontweight='bold')
ax1.set_ylabel('Pris (EUR/MWh)', fontsize=14, fontweight='bold')
ax1.set_title('Historisk Prisutvikling NO1 med Nøkkelhendelser',
              fontsize=16, fontweight='bold', pad=20)
ax1.grid(True, alpha=0.3, zorder=1)
ax1.set_xlim(2013.5, 2024.5)
ax1.set_ylim(-10, 300)

# ============================================================================
# PLOT 2: Volatility Over Time with Structural Break Annotations
# ============================================================================
ax2 = fig.add_subplot(gs[1, 0])

# Bar chart with color coding
colors = []
for idx, row in df.iterrows():
    if row['year'] < 2020:
        colors.append('green')
    elif row['year'] == 2020:
        colors.append('red')
    else:
        colors.append('orange')

bars = ax2.bar(df['year'], df['volatility'] * 100,
               color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)

# Add horizontal reference lines
ax2.axhline(y=21.2, color='green', linestyle='--', linewidth=2,
            label='2019 nivå (21%)', alpha=0.7)
ax2.axhline(y=89.1, color='red', linestyle='--', linewidth=2,
            label='2020 topp (89%)', alpha=0.7)

# Annotations for structural breaks
ax2.annotate('STRUKTURELT SKIFTE\nVolatilitet 4x høyere!',
            xy=(2020, 89), xytext=(2017.5, 75),
            fontsize=10, weight='bold',
            bbox=dict(boxstyle='round,pad=0.6', facecolor='red', alpha=0.4, linewidth=2),
            arrowprops=dict(arrowstyle='->', lw=2, color='red'))

ax2.annotate('Nordic Balancing Model\nSingle Price (Nov 2021)\n15-min settlement prep',
            xy=(2021, 64), xytext=(2019, 45),
            fontsize=8.5,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.7, linewidth=1.5),
            arrowprops=dict(arrowstyle='->', lw=1.5, color='blue'))

ax2.annotate('Permanent høyt nivå\n(importert volatilitet\nvia kabler)',
            xy=(2024, 79), xytext=(2022, 92),
            fontsize=8.5,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7, linewidth=1.5),
            arrowprops=dict(arrowstyle='->', lw=1.5, color='orange'))

ax2.set_xlabel('År', fontsize=12, fontweight='bold')
ax2.set_ylabel('Volatilitet (Standardavvik/Gjennomsnitt) %', fontsize=12, fontweight='bold')
ax2.set_title('Volatilitetsutvikling: Fra Stabilt til Høy-Volatilt Regime',
              fontsize=14, fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')
ax2.legend(loc='upper left', fontsize=10)
ax2.set_ylim(0, 100)

# ============================================================================
# PLOT 3: Negative Prices Emergence
# ============================================================================
ax3 = fig.add_subplot(gs[1, 1])

# Filter to show only years with data
negative_data = df[['year', 'num_negative', 'pct_negative']].copy()

# Bar chart
bars = ax3.bar(negative_data['year'], negative_data['num_negative'],
               color=color_volatility, alpha=0.7, edgecolor='black', linewidth=1.5)

# Highlight 2023 spike
max_idx = negative_data['num_negative'].idxmax()
bars[max_idx - df.index[0]].set_color('red')
bars[max_idx - df.index[0]].set_alpha(0.9)

# Annotations
ax3.annotate('Første negative\npriser noensinne\ni NO1',
            xy=(2020, 5), xytext=(2017, 100),
            fontsize=10, weight='bold',
            bbox=dict(boxstyle='round,pad=0.6', facecolor='yellow', alpha=0.7),
            arrowprops=dict(arrowstyle='->', lw=2, color='red'))

ax3.annotate('381 timer (4.3%)\nImportert volatilitet fra\ntysk/britisk vind+sol',
            xy=(2023, 381), xytext=(2021, 320),
            fontsize=10, weight='bold',
            bbox=dict(boxstyle='round,pad=0.6', facecolor='red', alpha=0.3),
            arrowprops=dict(arrowstyle='->', lw=2, color='red'))

ax3.axvline(x=2021, color='blue', linestyle='--', linewidth=2, alpha=0.5,
           label='Kabler åpnet (2021)')

ax3.set_xlabel('År', fontsize=12, fontweight='bold')
ax3.set_ylabel('Antall timer med negativ pris', fontsize=12, fontweight='bold')
ax3.set_title('Negative Priser: Indikator på Importert Uregulerbar Kraft',
              fontsize=14, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')
ax3.legend(loc='upper left', fontsize=10)

# ============================================================================
# PLOT 4: Price Range Expansion
# ============================================================================
ax4 = fig.add_subplot(gs[2, 0])

# Price range visualization
ax4.fill_between(df['year'],
                 df['min_eur_mwh'],
                 df['max_eur_mwh'],
                 alpha=0.3, color=color_new_normal, label='Min-Max Spenn')

ax4.plot(df['year'], df['mean_eur_mwh'],
        marker='o', linewidth=2, markersize=7,
        color=color_normal, label='Gjennomsnitt', zorder=3)

ax4.plot(df['year'], df['p10_eur_mwh'],
        linestyle='--', linewidth=1.5, color='gray', label='P10 (10% laveste)', zorder=2)

ax4.plot(df['year'], df['p90_eur_mwh'],
        linestyle='--', linewidth=1.5, color='darkgray', label='P90 (10% høyeste)', zorder=2)

# Annotations
ax4.annotate('Max pris: 800 EUR/MWh\n(2022 energikrise)',
            xy=(2022, 800), xytext=(2020, 700),
            fontsize=10, weight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='red', alpha=0.3),
            arrowprops=dict(arrowstyle='->', lw=2, color='red'))

ax4.annotate('Min pris: -62 EUR/MWh\n(2023 - overproduksjon)',
            xy=(2023, -61.84), xytext=(2021, -150),
            fontsize=10, weight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='blue', alpha=0.3),
            arrowprops=dict(arrowstyle='->', lw=2, color='blue'))

ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)

ax4.set_xlabel('År', fontsize=12, fontweight='bold')
ax4.set_ylabel('Pris (EUR/MWh)', fontsize=12, fontweight='bold')
ax4.set_title('Prisutvikling med Ekstremverdier: Økende Spredning',
              fontsize=14, fontweight='bold')
ax4.legend(loc='upper left', fontsize=10)
ax4.grid(True, alpha=0.3)

# ============================================================================
# PLOT 5: Three Main Factors - THREE COLUMN LAYOUT
# ============================================================================
ax5 = fig.add_subplot(gs[2, 1])
ax5.axis('off')

# Title
ax5.text(0.5, 0.98, 'TRE HOVEDÅRSAKER TIL VOLATILITETSØKNING',
        ha='center', va='top', fontsize=13, weight='bold',
        transform=ax5.transAxes,
        bbox=dict(boxstyle='round,pad=0.7', facecolor='lightgray', alpha=0.8))

# Factor 1: Market Reforms (LEFT column)
factor1_text = """1: MARKEDSREFORMER
(2020-2021)

• Single Price-Single
  Position (Nov 2021)
  Slår sammen prod/
  forbruk ubalanser

• 15-minutters oppgjør
  (fra 2023)
  4x flere handels-
  punkter per time

• mFRR erstatter RKOM
  Kapasitet flyttes til
  spotmarkedet

EFFEKT:
Volatilitet øker fra
21% til 89% i 2020!"""

ax5.text(0.02, 0.85, factor1_text,
        ha='left', va='top', fontsize=7.5, family='monospace',
        transform=ax5.transAxes,
        bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.75, linewidth=2))

# Factor 2: Interconnectors (MIDDLE column)
factor2_text = """2: UTENLANDSKABLER
(2021)

• NordLink -> Tyskland
  Kapasitet: 1400 MW
  Tysk vind+sol:
  117 -> 157 GW
  (2020-2024)

• North Sea Link -> UK
  Kapasitet: 1400 MW
  Britisk offshore
  vind: Massiv vekst
  (2018-2024)

EFFEKT:
Norge importerer
volatilitet fra
tyske/britiske
uregulerbare
kraftmarkeder"""

ax5.text(0.35, 0.85, factor2_text,
        ha='left', va='top', fontsize=7.5, family='monospace',
        transform=ax5.transAxes,
        bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.75, linewidth=2))

# Factor 3: Imported Volatility (RIGHT column)
factor3_text = """3: IMPORTERT
VOLATILITET

NØKKELINNSIKT:
Norge har IKKE
installert mye
uregulerbar prod.,
men IMPORTERER
volatiliteten!

• Norsk vannkraft:
  Stabil/regulerbar
• Tysk vind/sol:
  Uregulerbar/volatil
• Britisk offshore:
  Høy vekst/volatil
• Kabler (2800 MW):
  Overfører vol.

BEVIS:
• Negative priser:
  0 -> 381t (2023)
• Volatilitet:
  21% -> 79%
  (permanent)"""

ax5.text(0.68, 0.85, factor3_text,
        ha='left', va='top', fontsize=7.5, family='monospace',
        transform=ax5.transAxes,
        bbox=dict(boxstyle='round,pad=0.5', facecolor='lightcoral', alpha=0.75, linewidth=2))

# Overall title
fig.suptitle('NO1 (Oslo) Historisk Prisanalyse 2014-2024: Strukturell Endring i Kraftmarkedet',
            fontsize=18, fontweight='bold', y=0.995)

# Add footer with key insight
footer_text = (
    "KONKLUSJON: Volatilitetsøkningen fra 2020 skyldes kombinasjonen av markedsreformer (Nordic Balancing Model), "
    "nye utenlandskabler (2800 MW til DE/UK), og import av volatilitet fra uregulerbar tysk/britisk produksjon. "
    "Dette representerer et PERMANENT skifte i markedsdynamikken.\n\n"
    "IMPLIKASJON FOR BATTERIER: Høy volatilitet = bedre business case for energilagring (større arbitrasjemuligheter)"
)

fig.text(0.5, 0.01, footer_text,
        ha='center', va='bottom', fontsize=10,
        bbox=dict(boxstyle='round,pad=1', facecolor='wheat', alpha=0.8),
        wrap=True)

plt.tight_layout(rect=[0, 0.04, 1, 0.99])

# Save
output_file = Path('results/historical_analysis/NO1_enhanced_analysis_with_insights.png')
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"✓ Saved enhanced visualization to: {output_file}")

# Close figure to free memory
plt.close(fig)
