"""
Visualize break-even analysis results for battery optimization.

Creates summary plots showing:
1. Cost breakdown comparison (reference vs battery)
2. Economic analysis (savings, break-even, NPV)
3. Battery utilization metrics
"""

import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


def load_results():
    """Load break-even analysis results"""
    results_file = Path(__file__).parent / "results" / "breakeven_analysis_2024.json"
    with open(results_file, 'r') as f:
        return json.load(f)


def create_summary_plots(results):
    """Create comprehensive summary visualization"""

    fig = plt.figure(figsize=(16, 10))

    # Create grid layout
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.35)

    # =====================================================================
    # Plot 1: Annual Cost Breakdown (Top Left)
    # =====================================================================
    ax1 = fig.add_subplot(gs[0, 0])

    ref = results['reference_case']
    batt = results['battery_case']

    categories = ['Reference\n(No Battery)', 'Battery\nCase']
    energy_costs = [ref['energy_cost'], batt['energy_cost']]
    power_costs = [ref['power_cost'], batt['power_cost']]
    degradation_costs = [0, batt['degradation_cost']]

    x = np.arange(len(categories))
    width = 0.5

    p1 = ax1.bar(x, energy_costs, width, label='Energy Cost', color='#ff6b6b')
    p2 = ax1.bar(x, power_costs, width, bottom=energy_costs, label='Power Tariff', color='#4ecdc4')
    p3 = ax1.bar(x, degradation_costs, width,
                 bottom=[e+p for e,p in zip(energy_costs, power_costs)],
                 label='Degradation', color='#95a5a6')

    # Add total cost labels
    for i, (e, p, d) in enumerate(zip(energy_costs, power_costs, degradation_costs)):
        total = e + p + d
        ax1.text(i, total + 2000, f'{total:,.0f} NOK', ha='center', fontsize=10, fontweight='bold')

    ax1.set_ylabel('Annual Cost (NOK)', fontsize=11)
    ax1.set_title('Annual Cost Breakdown', fontsize=13, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, fontsize=10)
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(axis='y', alpha=0.3)

    # =====================================================================
    # Plot 2: Savings Breakdown (Top Middle)
    # =====================================================================
    ax2 = fig.add_subplot(gs[0, 1])

    savings = results['savings']
    components = ['Energy\nSavings', 'Power\nSavings', 'Degradation\nCost', 'Net\nSavings']
    values = [
        savings['energy_savings'],
        savings['power_savings'],
        -batt['degradation_cost'],
        savings['annual_savings_nok']
    ]
    colors = ['#2ecc71', '#3498db', '#e74c3c', '#f39c12']

    bars = ax2.bar(components, values, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)

    # Add value labels
    for bar, val in zip(bars, values):
        height = bar.get_height()
        sign = '+' if val >= 0 else ''
        ax2.text(bar.get_x() + bar.get_width()/2, height + (500 if val >= 0 else -500),
                f'{sign}{val:,.0f}', ha='center', va='bottom' if val >= 0 else 'top',
                fontsize=10, fontweight='bold')

    ax2.axhline(y=0, color='black', linewidth=1, linestyle='--', alpha=0.5)
    ax2.set_ylabel('Savings (NOK/year)', fontsize=11)
    ax2.set_title('Annual Savings Breakdown', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)

    # =====================================================================
    # Plot 3: Break-Even Analysis (Top Right)
    # =====================================================================
    ax3 = fig.add_subplot(gs[0, 2])

    be = results['breakeven']
    costs_labels = ['Break-Even\nCost', 'Market\nCost\n(2025)']
    costs_values = [be['breakeven_cost_per_kwh'], be['market_cost_per_kwh']]
    colors_be = ['#2ecc71', '#e74c3c']

    bars = ax3.bar(costs_labels, costs_values, color=colors_be, alpha=0.8, edgecolor='black', linewidth=1.5)

    # Add value labels
    for bar, val in zip(bars, costs_values):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2, height + 100,
                f'{val:,.0f}\nNOK/kWh', ha='center', va='bottom',
                fontsize=10, fontweight='bold')

    # Add gap annotation
    gap = be['market_cost_per_kwh'] - be['breakeven_cost_per_kwh']
    ax3.annotate('', xy=(1, be['breakeven_cost_per_kwh']), xytext=(1, be['market_cost_per_kwh']),
                arrowprops=dict(arrowstyle='<->', color='red', lw=2))
    ax3.text(1.15, (be['breakeven_cost_per_kwh'] + be['market_cost_per_kwh'])/2,
            f'Gap:\n{gap:,.0f}\nNOK/kWh\n({gap/be["market_cost_per_kwh"]*100:.1f}%)',
            va='center', fontsize=9, fontweight='bold', color='red')

    ax3.set_ylabel('Cost (NOK/kWh)', fontsize=11)
    ax3.set_title('Break-Even vs Market Cost', fontsize=13, fontweight='bold')
    ax3.set_ylim(0, be['market_cost_per_kwh'] * 1.15)
    ax3.grid(axis='y', alpha=0.3)

    # =====================================================================
    # Plot 4: NPV Analysis (Middle Left)
    # =====================================================================
    ax4 = fig.add_subplot(gs[1, 0])

    # Calculate NPV over lifetime
    years = np.arange(1, be['lifetime_years'] + 1)
    discount_factor = 1 / (1 + be['discount_rate'])**years
    annual_cash_flow = savings['annual_savings_nok'] * discount_factor
    cumulative_npv = np.cumsum(annual_cash_flow) - be['market_total_cost']

    ax4.plot(years, cumulative_npv, linewidth=2.5, color='#3498db', marker='o', markersize=4)
    ax4.axhline(y=0, color='black', linewidth=1, linestyle='--', alpha=0.5, label='Break-even')
    ax4.fill_between(years, 0, cumulative_npv, where=(cumulative_npv < 0),
                     alpha=0.3, color='red', label='Negative NPV')

    # Annotate final NPV
    final_npv = cumulative_npv[-1]
    ax4.text(be['lifetime_years'], final_npv - 5000,
            f'Final NPV:\n{final_npv:,.0f} NOK',
            ha='right', va='top', fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    ax4.set_xlabel('Year', fontsize=11)
    ax4.set_ylabel('Cumulative NPV (NOK)', fontsize=11)
    ax4.set_title(f'NPV Over {be["lifetime_years"]}-Year Lifetime\n(at {be["market_cost_per_kwh"]:,} NOK/kWh market price)',
                 fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.legend(loc='lower right', fontsize=9)

    # =====================================================================
    # Plot 5: Grid Impact (Middle Center)
    # =====================================================================
    ax5 = fig.add_subplot(gs[1, 1])

    metrics = ['Grid\nImport\n(MWh)', 'Grid\nExport\n(MWh)', 'Curtailment\n(MWh)', 'Peak\nDemand\n(kW)']
    ref_values = [
        ref['grid_import_kwh']/1000,
        ref['grid_export_kwh']/1000,
        ref['curtailment_kwh']/1000,
        ref['peak_kw']
    ]
    batt_values = [
        ref['grid_import_kwh']/1000,  # Not stored separately for battery case
        ref['grid_export_kwh']/1000,   # Not stored separately
        batt['curtailment_kwh']/1000,
        ref['peak_kw']  # Not stored separately
    ]

    x = np.arange(len(metrics))
    width = 0.35

    bars1 = ax5.bar(x - width/2, ref_values, width, label='Reference', color='#95a5a6', alpha=0.8)
    bars2 = ax5.bar(x + width/2, batt_values, width, label='Battery', color='#3498db', alpha=0.8)

    ax5.set_ylabel('Value', fontsize=11)
    ax5.set_title('Grid Impact Comparison', fontsize=13, fontweight='bold')
    ax5.set_xticks(x)
    ax5.set_xticklabels(metrics, fontsize=9)
    ax5.legend(loc='upper right', fontsize=9)
    ax5.grid(axis='y', alpha=0.3)

    # =====================================================================
    # Plot 6: Economic Summary Table (Middle Right)
    # =====================================================================
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis('off')

    battery_info = results['battery']

    summary_text = f"""
    ECONOMIC SUMMARY
    {'='*40}

    Battery Configuration:
    • Capacity: {battery_info['capacity_kwh']} kWh
    • Power Rating: {battery_info['power_kw']} kW

    Annual Performance:
    • Net Savings: {savings['annual_savings_nok']:,.0f} NOK/year
    • Energy Savings: {savings['energy_savings']:,.0f} NOK
    • Power Savings: {savings['power_savings']:,.0f} NOK
    • Degradation Cost: -{batt['degradation_cost']:,.0f} NOK

    Break-Even Analysis:
    • Break-even Cost: {be['breakeven_cost_per_kwh']:,.0f} NOK/kWh
    • Market Cost (2025): {be['market_cost_per_kwh']:,} NOK/kWh
    • Cost Gap: {be['market_cost_per_kwh'] - be['breakeven_cost_per_kwh']:,.0f} NOK/kWh
    • Reduction Needed: {(1 - be['breakeven_cost_per_kwh']/be['market_cost_per_kwh'])*100:.1f}%

    Investment Analysis:
    • Lifetime: {be['lifetime_years']} years
    • Discount Rate: {be['discount_rate']*100:.0f}%
    • PV of Savings: {be['pv_savings_nok']:,.0f} NOK
    • NPV at Market: {be['npv_at_market_price']:,.0f} NOK

    Viability: {'✅ VIABLE' if be['viable'] else '❌ NOT VIABLE'}
    """

    ax6.text(0.05, 0.95, summary_text, transform=ax6.transAxes,
            fontsize=10, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))

    # =====================================================================
    # Plot 7: Cost Comparison Waterfall (Bottom Span)
    # =====================================================================
    ax7 = fig.add_subplot(gs[2, :])

    # Waterfall chart components
    categories = [
        'Reference\nTotal',
        'Energy\nSavings',
        'Power\nSavings',
        'Degradation\nCost',
        'Battery\nTotal'
    ]

    ref_total = ref['total_cost']
    values = [
        ref_total,
        -savings['energy_savings'],
        -savings['power_savings'],
        batt['degradation_cost'],
        batt['total_cost']
    ]

    # Calculate positions for waterfall
    cumulative = [ref_total]
    for i in range(1, len(values)-1):
        cumulative.append(cumulative[-1] + values[i])
    cumulative.append(batt['total_cost'])

    # Plot bars
    colors_waterfall = ['#95a5a6', '#2ecc71', '#3498db', '#e74c3c', '#95a5a6']

    for i, (cat, val, cum) in enumerate(zip(categories, values, cumulative)):
        if i == 0 or i == len(values) - 1:
            # Start and end bars from zero
            ax7.bar(i, val, color=colors_waterfall[i], alpha=0.8, edgecolor='black', linewidth=1.5)
            ax7.text(i, val + 1000, f'{val:,.0f}', ha='center', fontsize=10, fontweight='bold')
        else:
            # Intermediate bars show change
            bottom = cumulative[i-1]
            height = values[i]
            ax7.bar(i, abs(height), bottom=min(bottom, bottom+height),
                   color=colors_waterfall[i], alpha=0.8, edgecolor='black', linewidth=1.5)
            ax7.text(i, bottom + height/2, f'{height:+,.0f}', ha='center',
                    fontsize=9, fontweight='bold', color='white')

            # Connection lines
            if i < len(values) - 2:
                ax7.plot([i, i+1], [cum, cum], 'k--', linewidth=1, alpha=0.5)

    # Highlight net savings
    net_saving = ref_total - batt['total_cost']
    ax7.annotate('', xy=(0, ref_total), xytext=(4, batt['total_cost']),
                arrowprops=dict(arrowstyle='<->', color='green', lw=3, linestyle='--'))
    ax7.text(2, (ref_total + batt['total_cost'])/2 + 5000,
            f'Net Savings:\n{net_saving:,.0f} NOK/year',
            ha='center', fontsize=11, fontweight='bold', color='green',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))

    ax7.set_ylabel('Annual Cost (NOK)', fontsize=12)
    ax7.set_title('Cost Waterfall: Reference → Battery Case', fontsize=14, fontweight='bold')
    ax7.set_xticks(range(len(categories)))
    ax7.set_xticklabels(categories, fontsize=11)
    ax7.grid(axis='y', alpha=0.3)

    # Overall title
    fig.suptitle(f'Battery Optimization Break-Even Analysis - 2024\n' +
                f'Timestamp: {results["timestamp"]}',
                fontsize=16, fontweight='bold', y=0.995)

    # Save figure
    output_file = Path(__file__).parent / "results" / "figures" / "breakeven_analysis_summary.png"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=200, bbox_inches='tight')
    print(f"\n✓ Summary plot saved: {output_file}")
    plt.close()

    return output_file


def main():
    """Main execution"""
    print("\n" + "="*70)
    print("VISUALIZING BREAK-EVEN ANALYSIS RESULTS")
    print("="*70)

    results = load_results()
    output_file = create_summary_plots(results)

    print("\n" + "="*70)
    print("✓ VISUALIZATION COMPLETE")
    print("="*70)
    print(f"\nGenerated plot: {output_file.name}")
    print(f"Full path: {output_file}")

    return output_file


if __name__ == "__main__":
    main()
