"""
Create detailed comparison plots for 15-min vs 60-min resolution.
Shows SOC, prices, import/export, and revenue breakdown.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# Load results from the comparison run
# We'll need to save the results first, so let's modify the script


def create_comprehensive_plots(metrics_60, metrics_15):
    """
    Create detailed comparison plots.

    Args:
        metrics_60: Results dictionary from 60-min simulation
        metrics_15: Results dictionary from 15-min simulation
    """

    df_60 = metrics_60['results_df']
    df_15 = metrics_15['results_df']

    # Debug: Print SOC statistics
    print("\n🔍 SOC Debug Information:")
    print(f"  60-min SOC range: {df_60['soc_kwh'].min():.2f} - {df_60['soc_kwh'].max():.2f} kWh")
    print(f"  60-min SOC mean: {df_60['soc_kwh'].mean():.2f} kWh")
    print(f"  60-min SOC std: {df_60['soc_kwh'].std():.2f} kWh")
    print(f"  15-min SOC range: {df_15['soc_kwh'].min():.2f} - {df_15['soc_kwh'].max():.2f} kWh")
    print(f"  15-min SOC mean: {df_15['soc_kwh'].mean():.2f} kWh")
    print(f"  15-min SOC std: {df_15['soc_kwh'].std():.2f} kWh")

    # Create figure with subplots
    fig = plt.figure(figsize=(18, 14))
    gs = fig.add_gridspec(4, 2, hspace=0.3, wspace=0.25)

    # Main title
    fig.suptitle('15-minutters vs 60-minutters oppløsning - Oktober 20-26, 2025\n'
                 '30 kW/30 kWh Batteri | Reelle ENTSO-E NO2 priser | PVGIS soldata',
                 fontsize=16, fontweight='bold')

    # ============================================================================
    # PLOT 1: Battery SOC comparison (ZOOMED to show variation)
    # ============================================================================
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(df_60['timestamp'], df_60['soc_kwh'],
             label='60-min', linewidth=2.5, color='#2E86AB', alpha=0.9)
    ax1.plot(df_15['timestamp'], df_15['soc_kwh'],
             label='15-min', linewidth=1.8, color='#F24236', alpha=0.8)

    # Zoom to actual SOC range used (with some margin)
    soc_min = min(df_60['soc_kwh'].min(), df_15['soc_kwh'].min())
    soc_max = max(df_60['soc_kwh'].max(), df_15['soc_kwh'].max())
    margin = (soc_max - soc_min) * 0.1  # 10% margin
    ax1.set_ylim([max(0, soc_min - margin), min(30, soc_max + margin)])

    # Add reference lines for limits
    ax1.axhline(y=30*0.9, color='red', linestyle='--', linewidth=1, alpha=0.5, label='SOC max (27 kWh)')
    ax1.axhline(y=30*0.1, color='red', linestyle='--', linewidth=1, alpha=0.5, label='SOC min (3 kWh)')

    ax1.set_ylabel('Batterinivå [kWh]', fontsize=11, fontweight='bold')
    ax1.set_title('Battery State of Charge - ZOOMET (viser reell variasjon)', fontsize=12, fontweight='bold')
    ax1.legend(loc='best', fontsize=8)
    ax1.grid(True, alpha=0.3, linestyle=':')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

    # ============================================================================
    # PLOT 2: Spot prices with volatility
    # ============================================================================
    ax2 = fig.add_subplot(gs[0, 1])

    # Plot 60-min prices
    ax2.plot(df_60['timestamp'], df_60['spot_price'],
             label='Spotpris (60-min)', linewidth=2, color='#E63946', alpha=0.8)

    # Add 15-min prices with transparency to show granularity
    ax2.plot(df_15['timestamp'], df_15['spot_price'],
             label='Spotpris (15-min)', linewidth=1, color='#E63946', alpha=0.3)

    # Price statistics
    mean_price = df_60['spot_price'].mean()
    ax2.axhline(y=mean_price, color='orange', linestyle='--', linewidth=1.5,
                label=f'Gjennomsnitt: {mean_price:.2f} kr/kWh')

    ax2.set_ylabel('Pris [NOK/kWh]', fontsize=11, fontweight='bold')
    ax2.set_title('ENTSO-E NO2 Spotpriser', fontsize=12, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3, linestyle=':')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

    # ============================================================================
    # PLOT 3: Battery power (charging/discharging)
    # ============================================================================
    ax3 = fig.add_subplot(gs[1, 0])

    ax3.fill_between(df_60['timestamp'], 0, df_60['battery_power_kw'],
                     where=(df_60['battery_power_kw'] >= 0),
                     color='green', alpha=0.4, label='Lading (60-min)')
    ax3.fill_between(df_60['timestamp'], 0, df_60['battery_power_kw'],
                     where=(df_60['battery_power_kw'] < 0),
                     color='red', alpha=0.4, label='Utlading (60-min)')

    ax3.plot(df_15['timestamp'], df_15['battery_power_kw'],
             linewidth=1, color='blue', alpha=0.5, label='15-min')

    ax3.axhline(y=0, color='black', linewidth=0.8)
    ax3.axhline(y=30, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax3.axhline(y=-30, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    ax3.set_ylabel('Batterieffekt [kW]', fontsize=11, fontweight='bold')
    ax3.set_title('Batterikjøring (+ = lading, - = utlading)', fontsize=12, fontweight='bold')
    ax3.legend(loc='upper right', fontsize=9)
    ax3.grid(True, alpha=0.3, linestyle=':')
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

    # ============================================================================
    # PLOT 4: Grid import/export comparison
    # ============================================================================
    ax4 = fig.add_subplot(gs[1, 1])

    # 60-min import/export
    ax4.fill_between(df_60['timestamp'], 0, df_60['grid_import_kw'],
                     color='#FF6B6B', alpha=0.5, label='Import (60-min)')
    ax4.fill_between(df_60['timestamp'], 0, -df_60['grid_export_kw'],
                     color='#4ECDC4', alpha=0.5, label='Eksport (60-min)')

    # Add 15-min as lines for comparison
    ax4.plot(df_15['timestamp'], df_15['grid_import_kw'],
             linewidth=1, color='red', alpha=0.4, label='Import (15-min)')
    ax4.plot(df_15['timestamp'], -df_15['grid_export_kw'],
             linewidth=1, color='teal', alpha=0.4, label='Eksport (15-min)')

    ax4.axhline(y=70, color='red', linestyle='--', linewidth=1.5,
                label='Nettgrense (70 kW)')
    ax4.axhline(y=0, color='black', linewidth=0.8)

    ax4.set_ylabel('Netteffekt [kW]', fontsize=11, fontweight='bold')
    ax4.set_title('Nettimport/-eksport', fontsize=12, fontweight='bold')
    ax4.legend(loc='upper right', fontsize=8, ncol=2)
    ax4.grid(True, alpha=0.3, linestyle=':')
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

    # ============================================================================
    # PLOT 5: PV production vs consumption
    # ============================================================================
    ax5 = fig.add_subplot(gs[2, 0])

    ax5.fill_between(df_60['timestamp'], 0, df_60['pv_production_kw'],
                     color='gold', alpha=0.6, label='Solproduksjon')
    ax5.plot(df_60['timestamp'], df_60['consumption_kw'],
             linewidth=2, color='purple', alpha=0.7, label='Forbruk')

    ax5.set_ylabel('Effekt [kW]', fontsize=11, fontweight='bold')
    ax5.set_title('Solproduksjon vs Forbruk', fontsize=12, fontweight='bold')
    ax5.legend(loc='upper right', fontsize=9)
    ax5.grid(True, alpha=0.3, linestyle=':')
    ax5.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

    # ============================================================================
    # PLOT 6: Revenue breakdown comparison
    # ============================================================================
    ax6 = fig.add_subplot(gs[2, 1])

    # Calculate revenue components
    timestep_60 = 1.0
    timestep_15 = 0.25

    # For 60-min
    grid_cost_60 = (df_60['grid_import_kw'] * df_60['spot_price'] * timestep_60).sum()
    grid_revenue_60 = (df_60['grid_export_kw'] * df_60['spot_price'] * timestep_60).sum()
    pv_self_consumption_60 = (df_60['pv_production_kw'] - df_60['grid_export_kw']).sum() * timestep_60
    pv_value_60 = pv_self_consumption_60 * df_60['spot_price'].mean()

    # For 15-min
    grid_cost_15 = (df_15['grid_import_kw'] * df_15['spot_price'] * timestep_15).sum()
    grid_revenue_15 = (df_15['grid_export_kw'] * df_15['spot_price'] * timestep_15).sum()
    pv_self_consumption_15 = (df_15['pv_production_kw'] - df_15['grid_export_kw']).sum() * timestep_15
    pv_value_15 = pv_self_consumption_15 * df_15['spot_price'].mean()

    categories = ['Nettimport\nkostnad', 'Netteksport\ninntekt', 'Egenforbruk\nverdi']

    values_60 = [grid_cost_60, grid_revenue_60, pv_value_60]
    values_15 = [grid_cost_15, grid_revenue_15, pv_value_15]

    x = np.arange(len(categories))
    width = 0.35

    bars1 = ax6.bar(x - width/2, values_60, width, label='60-min',
                    alpha=0.8, color='#2E86AB')
    bars2 = ax6.bar(x + width/2, values_15, width, label='15-min',
                    alpha=0.8, color='#F24236')

    ax6.set_ylabel('Beløp [NOK]', fontsize=11, fontweight='bold')
    ax6.set_title('Økonomisk sammenligning (1 uke)', fontsize=12, fontweight='bold')
    ax6.set_xticks(x)
    ax6.set_xticklabels(categories, fontsize=9)
    ax6.legend(fontsize=9)
    ax6.grid(True, alpha=0.3, linestyle=':', axis='y')

    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax6.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.0f}',
                    ha='center', va='bottom', fontsize=8)

    # ============================================================================
    # PLOT 7: Cumulative cost comparison
    # ============================================================================
    ax7 = fig.add_subplot(gs[3, 0])

    # Calculate cumulative costs
    cumulative_cost_60 = []
    cumulative_cost_15 = []

    running_cost_60 = 0
    running_cost_15 = 0

    for i, row in df_60.iterrows():
        cost = row['grid_import_kw'] * row['spot_price'] * timestep_60
        revenue = row['grid_export_kw'] * row['spot_price'] * timestep_60
        running_cost_60 += (cost - revenue)
        cumulative_cost_60.append(running_cost_60)

    for i, row in df_15.iterrows():
        cost = row['grid_import_kw'] * row['spot_price'] * timestep_15
        revenue = row['grid_export_kw'] * row['spot_price'] * timestep_15
        running_cost_15 += (cost - revenue)
        cumulative_cost_15.append(running_cost_15)

    ax7.plot(df_60['timestamp'], cumulative_cost_60,
             linewidth=2.5, color='#2E86AB', label='60-min', alpha=0.9)
    ax7.plot(df_15['timestamp'], cumulative_cost_15,
             linewidth=2, color='#F24236', label='15-min', alpha=0.8)

    # Show the difference at the end
    diff = cumulative_cost_15[-1] - cumulative_cost_60[-1]
    ax7.text(df_60['timestamp'].iloc[-1], cumulative_cost_60[-1],
             f'  Differanse: {diff:+.2f} NOK',
             fontsize=9, ha='left', va='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    ax7.set_ylabel('Akkumulert kostnad [NOK]', fontsize=11, fontweight='bold')
    ax7.set_title('Kumulativ energikostnad', fontsize=12, fontweight='bold')
    ax7.legend(loc='upper left', fontsize=9)
    ax7.grid(True, alpha=0.3, linestyle=':')
    ax7.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

    # ============================================================================
    # PLOT 8: Key metrics summary
    # ============================================================================
    ax8 = fig.add_subplot(gs[3, 1])
    ax8.axis('off')

    # Create summary text
    summary_text = f"""
    SAMMENDRAG - Uke 20-26 oktober 2025

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ØKONOMI:
    • Energikostnad (60-min): {metrics_60['energy_cost']:.2f} NOK
    • Energikostnad (15-min): {metrics_15['energy_cost']:.2f} NOK
    • Differanse: {metrics_15['energy_cost'] - metrics_60['energy_cost']:+.2f} NOK

    BATTERIBRUK:
    • Sykluser (60-min): {metrics_60['cycles']:.2f}
    • Sykluser (15-min): {metrics_15['cycles']:.2f}
    • Økning: {((metrics_15['cycles']/metrics_60['cycles']-1)*100):+.1f}%

    NETT:
    • Import (60-min): {metrics_60['grid_import_kwh']:.0f} kWh
    • Import (15-min): {metrics_15['grid_import_kwh']:.0f} kWh
    • Eksport (60-min): {metrics_60['grid_export_kwh']:.0f} kWh
    • Eksport (15-min): {metrics_15['grid_export_kwh']:.0f} kWh

    SOLENERGI:
    • Produksjon: {metrics_60['pv_production_kwh']:.0f} kWh
    • Egenforbruk (60-min): {((metrics_60['pv_production_kwh'] - metrics_60['grid_export_kwh'])/metrics_60['pv_production_kwh']*100):.1f}%
    • Egenforbruk (15-min): {((metrics_15['pv_production_kwh'] - metrics_15['grid_export_kwh'])/metrics_15['pv_production_kwh']*100):.1f}%

    OPTIMALISERINGER:
    • 60-min: {metrics_60['optimizations']} (hver time)
    • 15-min: {metrics_15['optimizations']} (hver 15. min)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """

    ax8.text(0.1, 0.9, summary_text,
             transform=ax8.transAxes,
             fontsize=10,
             verticalalignment='top',
             fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

    # Save figure
    plt.tight_layout()
    output_file = '/mnt/c/users/klaus/klauspython/SDE/battery_optimization/results/detailed_comparison_plots.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n📊 Detaljerte plots lagret: {output_file}")
    plt.close()

    return output_file


if __name__ == '__main__':
    # This will be called from the main comparison script
    print("This module should be imported and called with metrics data")
