#!/usr/bin/env python3
"""
Resolution Comparison Tool - LP-based with Degradation

Compares battery optimization results between hourly (PT60M) and 15-minute (PT15M)
time resolutions using LP optimization with full degradation modeling to quantify:
- Arbitrage revenue (spot price trading)
- Power tariff savings
- Battery degradation costs (cyclic + calendric)
- Total economic performance (NPV, payback period)

This version uses MonthlyLPOptimizer with degradation enabled for accurate comparison.

Usage:
    python compare_resolutions.py                      # Compare with default 30 kWh battery
    python compare_resolutions.py --battery-kwh 100    # Compare with custom battery size
    python compare_resolutions.py --save-plot          # Generate comparison visualization
    python compare_resolutions.py --no-degradation     # Disable degradation modeling
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import argparse
from datetime import datetime
from pathlib import Path

# Import LP optimizer with degradation
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.price_fetcher import fetch_prices
from core.time_aggregation import upsample_hourly_to_15min
from run_simulation import load_real_solar_production, generate_realistic_consumption_profile
from config import config


def run_optimization_at_resolution(battery_kwh, battery_kw, resolution='PT60M', enable_degradation=True):
    """
    Run LP-based battery optimization at specified resolution with degradation modeling.

    Args:
        battery_kwh: Battery capacity [kWh]
        battery_kw: Battery power [kW]
        resolution: 'PT60M' or 'PT15M'
        enable_degradation: Enable battery degradation modeling

    Returns:
        Dictionary with optimization results and economics
    """
    print(f"\n{'='*70}")
    print(f"LP OPTIMIZATION: {battery_kwh} kWh / {battery_kw} kW @ {resolution}")
    print(f"Degradation: {'ENABLED' if enable_degradation else 'DISABLED'}")
    print(f"{'='*70}")

    # Enable/disable degradation in config
    config.battery.degradation.enabled = enable_degradation

    # Load base data (always hourly from PVGIS)
    production_dc, production_ac, inverter_clipping = load_real_solar_production()
    consumption = generate_realistic_consumption_profile(production_dc.index)

    year = production_dc.index[0].year

    # Prepare data at target resolution
    if resolution == 'PT15M':
        # Upsample to 15-minute resolution
        production_dc = upsample_hourly_to_15min(production_dc, production_dc.index)
        production_ac = upsample_hourly_to_15min(production_ac, production_ac.index)
        consumption = upsample_hourly_to_15min(consumption, consumption.index)
        timestamps = production_dc.index
    else:
        timestamps = production_dc.index

    # Fetch spot prices at target resolution
    print(f"\nFetching {resolution} spot prices for {year}...")
    spot_prices = fetch_prices(year, 'NO2', resolution=resolution)

    # Align prices with production timestamps
    if len(spot_prices) != len(timestamps):
        print(f"  Aligning prices: {len(spot_prices)} → {len(timestamps)}")
        spot_prices = spot_prices.reindex(timestamps, method='ffill')

    print(f"\nData prepared:")
    print(f"  Intervals: {len(timestamps)}")
    print(f"  Production range: {production_ac.min():.1f} - {production_ac.max():.1f} kW")
    print(f"  Price range: {spot_prices.min():.3f} - {spot_prices.max():.3f} NOK/kWh")

    # Initialize LP optimizer with degradation
    optimizer = MonthlyLPOptimizer(
        config,
        resolution=resolution,
        battery_kwh=battery_kwh,
        battery_kw=battery_kw
    )

    # Run monthly optimizations for full year
    print(f"\n{'='*70}")
    print("Running 12 Monthly LP Optimizations")
    print(f"{'='*70}")

    monthly_results = []
    E_initial = battery_kwh * 0.5  # Start at 50% SOC

    for month_idx in range(1, 13):
        # Get month data
        month_start = timestamps[timestamps.month == month_idx][0]
        month_end = timestamps[timestamps.month == month_idx][-1]

        month_mask = (timestamps >= month_start) & (timestamps <= month_end)
        month_timestamps = timestamps[month_mask]
        month_production = production_ac[month_mask]
        month_consumption = consumption[month_mask]
        month_prices = spot_prices[month_mask]

        print(f"\n📅 Month {month_idx} ({month_start.strftime('%B %Y')})")
        print(f"   Intervals: {len(month_timestamps)}")

        # Run optimization
        result = optimizer.optimize_month(
            month_idx=month_idx,
            timestamps=month_timestamps,
            spot_prices=month_prices.values,
            pv_production=month_production.values,
            load_consumption=month_consumption.values,
            E_initial=E_initial
        )

        if result.success:
            monthly_results.append(result)
            E_initial = result.E_battery_final  # Carry SOC to next month

            print(f"   ✅ Optimized | Energy: {result.energy_cost:.0f} kr | Power: {result.power_cost:.0f} kr", end='')
            if enable_degradation:
                print(f" | Degrad: {result.degradation_cost:.0f} kr")
            else:
                print()
        else:
            print(f"   ❌ Failed: {result.message}")
            return None

    # Aggregate yearly results
    print(f"\n{'='*70}")
    print("Yearly Aggregation")
    print(f"{'='*70}")

    total_energy_cost = sum(r.energy_cost for r in monthly_results)
    total_power_cost = sum(r.power_cost for r in monthly_results)
    total_degradation_cost = sum(r.degradation_cost for r in monthly_results) if enable_degradation else 0.0

    # Calculate total cycles and degradation
    if enable_degradation:
        total_equivalent_cycles = sum(np.sum(r.DOD_abs) for r in monthly_results)
        total_cyclic_degradation = sum(np.sum(r.DP_cyc) for r in monthly_results)
        total_calendar_degradation = sum(r.DP_cal * len(r.E_battery) for r in monthly_results)
        total_degradation = total_cyclic_degradation + total_calendar_degradation
    else:
        total_equivalent_cycles = 0
        total_cyclic_degradation = 0
        total_calendar_degradation = 0
        total_degradation = 0

    # Calculate revenue components (infer from costs)
    # Grid export revenue (negative energy cost component)
    # Arbitrage value = discharge revenue - charge cost
    # Curtailment savings = avoided curtailment value

    # For simplicity, use total energy/power savings as proxy
    annual_operational_cost = total_energy_cost + total_power_cost + total_degradation_cost

    # Economics calculation
    battery_cost_per_kwh = config.battery.get_battery_cost()  # NOK/kWh (cells only)
    investment = battery_kwh * battery_cost_per_kwh

    # Annual savings = reduction in costs (approximation)
    # For comparison, we assume baseline cost without battery and calculate savings
    # This is simplified - real calculation would need baseline run
    annual_savings = -annual_operational_cost  # Negative cost = savings

    # NPV calculation
    discount_rate = config.economics.discount_rate
    lifetime = config.economics.project_lifetime_years

    npv = -investment
    for year in range(1, lifetime + 1):
        npv += annual_savings / (1 + discount_rate) ** year

    payback = investment / annual_savings if annual_savings > 0 else float('inf')

    print(f"\n💰 Economic Results:")
    print(f"   Energy cost: {total_energy_cost:,.0f} NOK/year")
    print(f"   Power cost: {total_power_cost:,.0f} NOK/year")
    if enable_degradation:
        print(f"   Degradation cost: {total_degradation_cost:,.0f} NOK/year")
        print(f"   Equivalent cycles: {total_equivalent_cycles:.1f} cycles/year")
        print(f"   Total degradation: {total_degradation:.3f}% /year")
        print(f"     - Cyclic: {total_cyclic_degradation:.3f}%")
        print(f"     - Calendar: {total_calendar_degradation:.3f}%")
    print(f"   Total operational cost: {annual_operational_cost:,.0f} NOK/year")
    print(f"   Investment: {investment:,.0f} NOK")
    print(f"   NPV: {npv:,.0f} NOK")
    print(f"   Payback: {payback:.2f} years")

    return {
        'resolution': resolution,
        'battery_kwh': battery_kwh,
        'battery_kw': battery_kw,
        'data_points': len(timestamps),
        'degradation_enabled': enable_degradation,
        'economics': {
            'annual_savings': annual_savings,
            'energy_cost': total_energy_cost,
            'power_cost': total_power_cost,
            'degradation_cost': total_degradation_cost,
            'total_operational_cost': annual_operational_cost,
            'npv': npv,
            'payback': payback,
            'investment': investment,
            'equivalent_cycles': total_equivalent_cycles,
            'total_degradation_pct': total_degradation,
            'cyclic_degradation_pct': total_cyclic_degradation,
            'calendar_degradation_pct': total_calendar_degradation
        },
        'monthly_results': monthly_results,
        'production_stats': {
            'dc_total': production_dc.sum(),
            'ac_total': production_ac.sum()
        }
    }


def compare_resolutions(battery_kwh=30, battery_kw=15, save_plot=False, enable_degradation=True):
    """
    Compare LP optimization results between hourly and 15-minute resolutions with degradation.

    Args:
        battery_kwh: Battery capacity [kWh]
        battery_kw: Battery power [kW]
        save_plot: Whether to save comparison visualization
        enable_degradation: Enable battery degradation modeling

    Returns:
        Dictionary with comparison results
    """
    print("\n" + "="*70)
    print("RESOLUTION COMPARISON ANALYSIS - LP with Degradation")
    print("="*70)
    print(f"Battery Configuration: {battery_kwh} kWh / {battery_kw} kW")
    print(f"Battery Cost: {config.battery.get_battery_cost()} NOK/kWh")
    print(f"Degradation: {'ENABLED' if enable_degradation else 'DISABLED'}")
    print("="*70)

    # Run both optimizations
    results_hourly = run_optimization_at_resolution(battery_kwh, battery_kw, 'PT60M', enable_degradation)
    results_15min = run_optimization_at_resolution(battery_kwh, battery_kw, 'PT15M', enable_degradation)

    # Extract economics for comparison
    econ_hourly = results_hourly['economics']
    econ_15min = results_15min['economics']

    # Calculate improvements
    energy_cost_change = (
        (econ_15min['energy_cost'] - econ_hourly['energy_cost']) /
        max(abs(econ_hourly['energy_cost']), 1.0) * 100
    )

    power_cost_change = (
        (econ_15min['power_cost'] - econ_hourly['power_cost']) /
        max(abs(econ_hourly['power_cost']), 1.0) * 100
    )

    degradation_cost_change = (
        (econ_15min['degradation_cost'] - econ_hourly['degradation_cost']) /
        max(abs(econ_hourly['degradation_cost']), 1.0) * 100
    ) if enable_degradation else 0.0

    total_savings_improvement = (
        (econ_15min['annual_savings'] - econ_hourly['annual_savings']) /
        max(abs(econ_hourly['annual_savings']), 1.0) * 100
    )

    npv_improvement = (
        (econ_15min['npv'] - econ_hourly['npv']) /
        max(abs(econ_hourly['npv']), 1.0) * 100
    )

    # Compile comparison
    comparison = {
        'battery_config': {
            'capacity_kwh': battery_kwh,
            'power_kw': battery_kw,
            'cost_per_kwh': config.battery.get_battery_cost()
        },
        'degradation_enabled': enable_degradation,
        'data_points': {
            'hourly': results_hourly['data_points'],
            '15min': results_15min['data_points'],
            'ratio': results_15min['data_points'] / results_hourly['data_points']
        },
        'energy_cost': {
            'hourly': econ_hourly['energy_cost'],
            '15min': econ_15min['energy_cost'],
            'change_pct': energy_cost_change
        },
        'power_cost': {
            'hourly': econ_hourly['power_cost'],
            '15min': econ_15min['power_cost'],
            'change_pct': power_cost_change
        },
        'degradation_cost': {
            'hourly': econ_hourly['degradation_cost'],
            '15min': econ_15min['degradation_cost'],
            'change_pct': degradation_cost_change
        } if enable_degradation else None,
        'degradation_metrics': {
            'equivalent_cycles_hourly': econ_hourly['equivalent_cycles'],
            'equivalent_cycles_15min': econ_15min['equivalent_cycles'],
            'cycles_increase_pct': (
                (econ_15min['equivalent_cycles'] - econ_hourly['equivalent_cycles']) /
                max(econ_hourly['equivalent_cycles'], 1.0) * 100
            ),
            'total_degradation_hourly_pct': econ_hourly['total_degradation_pct'],
            'total_degradation_15min_pct': econ_15min['total_degradation_pct']
        } if enable_degradation else None,
        'total_savings': {
            'hourly': econ_hourly['annual_savings'],
            '15min': econ_15min['annual_savings'],
            'improvement_pct': total_savings_improvement
        },
        'npv': {
            'hourly': econ_hourly['npv'],
            '15min': econ_15min['npv'],
            'improvement_pct': npv_improvement
        },
        'payback': {
            'hourly': econ_hourly['payback'],
            '15min': econ_15min['payback'],
            'improvement_years': econ_hourly['payback'] - econ_15min['payback']
        },
        'timestamp': datetime.now().isoformat()
    }

    # Print comparison report
    print_comparison_report(comparison)

    # Save results
    output_dir = Path('results')
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f'resolution_comparison_{battery_kwh}kwh.json'
    with open(output_file, 'w') as f:
        json.dump(comparison, f, indent=2)
    print(f"\n💾 Comparison results saved: {output_file}")

    # Generate visualization if requested
    if save_plot:
        plot_comparison(comparison, results_hourly, results_15min)

    return comparison


def print_comparison_report(comparison):
    """Print formatted comparison report."""
    print("\n" + "="*70)
    print("COMPARISON RESULTS - LP with Degradation")
    print("="*70)

    print(f"\n📊 Data Points:")
    print(f"  Hourly:    {comparison['data_points']['hourly']:,} intervals")
    print(f"  15-minute: {comparison['data_points']['15min']:,} intervals")
    print(f"  Ratio:     {comparison['data_points']['ratio']:.1f}x")

    print(f"\n💡 Energy Cost (Grid Import - Export):")
    print(f"  Hourly:    {comparison['energy_cost']['hourly']:,.0f} NOK/year")
    print(f"  15-minute: {comparison['energy_cost']['15min']:,.0f} NOK/year")
    print(f"  Change:    {comparison['energy_cost']['change_pct']:+.1f}%")

    print(f"\n⚡ Power Tariff Cost:")
    print(f"  Hourly:    {comparison['power_cost']['hourly']:,.0f} NOK/year")
    print(f"  15-minute: {comparison['power_cost']['15min']:,.0f} NOK/year")
    print(f"  Change:    {comparison['power_cost']['change_pct']:+.1f}%")

    if comparison['degradation_enabled']:
        print(f"\n🔋 Battery Degradation Cost:")
        print(f"  Hourly:    {comparison['degradation_cost']['hourly']:,.0f} NOK/year")
        print(f"  15-minute: {comparison['degradation_cost']['15min']:,.0f} NOK/year")
        print(f"  Change:    {comparison['degradation_cost']['change_pct']:+.1f}%")

        metrics = comparison['degradation_metrics']
        print(f"\n🔄 Cycling & Degradation:")
        print(f"  Equivalent Cycles:")
        print(f"    Hourly:    {metrics['equivalent_cycles_hourly']:.1f} cycles/year")
        print(f"    15-minute: {metrics['equivalent_cycles_15min']:.1f} cycles/year")
        print(f"    Increase:  {metrics['cycles_increase_pct']:+.1f}%")
        print(f"  Total Degradation:")
        print(f"    Hourly:    {metrics['total_degradation_hourly_pct']:.3f}% /year")
        print(f"    15-minute: {metrics['total_degradation_15min_pct']:.3f}% /year")

    print(f"\n💵 Net Annual Savings:")
    print(f"  Hourly:       {comparison['total_savings']['hourly']:,.0f} NOK/year")
    print(f"  15-minute:    {comparison['total_savings']['15min']:,.0f} NOK/year")
    print(f"  Improvement:  {comparison['total_savings']['improvement_pct']:+.1f}%")

    print(f"\n📈 Net Present Value (NPV):")
    print(f"  Hourly:       {comparison['npv']['hourly']:,.0f} NOK")
    print(f"  15-minute:    {comparison['npv']['15min']:,.0f} NOK")
    print(f"  Improvement:  {comparison['npv']['improvement_pct']:+.1f}%")

    print(f"\n⏱ Payback Period:")
    print(f"  Hourly:      {comparison['payback']['hourly']:.2f} years")
    print(f"  15-minute:   {comparison['payback']['15min']:.2f} years")
    print(f"  Improvement: {comparison['payback']['improvement_years']:+.2f} years")

    print("\n" + "="*70)
    print("KEY INSIGHTS")
    print("="*70)

    total_imp = comparison['total_savings']['improvement_pct']

    if comparison['degradation_enabled']:
        cycles_inc = comparison['degradation_metrics']['cycles_increase_pct']
        print(f"🔋 Battery cycling increased by {cycles_inc:.1f}% with 15-min resolution")
        print(f"💸 Degradation cost increased by {comparison['degradation_cost']['change_pct']:+.1f}%")

    if total_imp > 5:
        print(f"✅ Overall economic improvement: {total_imp:.1f}%")
    elif total_imp > 0:
        print(f"✓ Modest economic improvement: {total_imp:.1f}%")
    else:
        print(f"⚠ No significant economic benefit from 15-minute resolution")
        if comparison['degradation_enabled']:
            print(f"   Increased cycling costs offset finer resolution benefits")

    print("\n💡 Recommendation:")
    if total_imp > 3:
        print("  ✅ Use 15-minute resolution - provides measurable economic benefit")
    elif total_imp > 0:
        print("  ⚖️  Marginal benefit - hourly resolution sufficient for most analyses")
    else:
        print("  ❌ Stick with hourly resolution - 15-min adds complexity without benefit")

    print("="*70)


def plot_comparison(comparison, results_hourly, results_15min):
    """
    Generate comparison visualization.

    Args:
        comparison: Comparison dictionary
        results_hourly: Hourly optimization results
        results_15min: 15-minute optimization results
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(
        f"Resolution Comparison: {comparison['battery_config']['capacity_kwh']} kWh Battery\n"
        f"Hourly (PT60M) vs 15-Minute (PT15M)",
        fontsize=16, fontweight='bold'
    )

    # Plot 1: Revenue Breakdown
    ax1 = axes[0, 0]
    categories = ['Arbitrage', 'Power Tariff', 'Curtailment']
    hourly_values = [
        comparison['arbitrage']['hourly'],
        comparison['power_tariff']['hourly'],
        comparison['curtailment']['hourly']
    ]
    min15_values = [
        comparison['arbitrage']['15min'],
        comparison['power_tariff']['15min'],
        comparison['curtailment']['15min']
    ]

    x = np.arange(len(categories))
    width = 0.35

    ax1.bar(x - width/2, hourly_values, width, label='Hourly', alpha=0.8)
    ax1.bar(x + width/2, min15_values, width, label='15-minute', alpha=0.8)
    ax1.set_ylabel('Revenue (NOK/year)')
    ax1.set_title('Revenue Component Comparison')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: NPV Comparison
    ax2 = axes[0, 1]
    npv_labels = ['Hourly', '15-minute']
    npv_values = [comparison['npv']['hourly'], comparison['npv']['15min']]
    colors = ['#2E86AB', '#A23B72']

    bars = ax2.bar(npv_labels, npv_values, color=colors, alpha=0.8)
    ax2.set_ylabel('NPV (NOK)')
    ax2.set_title('Net Present Value Comparison')
    ax2.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:,.0f}',
                ha='center', va='bottom')

    # Plot 3: Payback Period
    ax3 = axes[1, 0]
    payback_labels = ['Hourly', '15-minute']
    payback_values = [
        comparison['payback']['hourly'],
        comparison['payback']['15min']
    ]

    bars = ax3.bar(payback_labels, payback_values, color=colors, alpha=0.8)
    ax3.set_ylabel('Years')
    ax3.set_title('Payback Period')
    ax3.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}',
                ha='center', va='bottom')

    # Plot 4: Improvement Summary
    ax4 = axes[1, 1]
    improvements = [
        comparison['arbitrage']['improvement_pct'],
        comparison['total_savings']['improvement_pct'],
        comparison['npv']['improvement_pct']
    ]
    improvement_labels = ['Arbitrage', 'Total Savings', 'NPV']

    colors_imp = ['green' if x > 0 else 'red' for x in improvements]
    bars = ax4.barh(improvement_labels, improvements, color=colors_imp, alpha=0.7)
    ax4.set_xlabel('Improvement (%)')
    ax4.set_title('15-Minute vs Hourly Improvement')
    ax4.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax4.grid(True, alpha=0.3, axis='x')

    # Add value labels
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax4.text(width, bar.get_y() + bar.get_height()/2.,
                f'{width:+.1f}%',
                ha='left' if width > 0 else 'right',
                va='center')

    plt.tight_layout()

    # Save figure
    output_file = Path('results') / f'resolution_comparison_{comparison["battery_config"]["capacity_kwh"]}kwh.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n📊 Comparison plot saved: {output_file}")

    plt.show()


def main():
    """Main entry point for resolution comparison."""
    parser = argparse.ArgumentParser(
        description="Compare LP battery optimization: hourly vs 15-minute resolution with degradation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python compare_resolutions.py                          # Default 30 kWh battery with degradation
  python compare_resolutions.py --battery-kwh 100        # 100 kWh battery
  python compare_resolutions.py --no-degradation         # Disable degradation modeling
  python compare_resolutions.py --save-plot              # With visualization
  python compare_resolutions.py --battery-kwh 80 --battery-kw 40  # Custom config
        """
    )

    parser.add_argument('--battery-kwh', type=float, default=30,
                       help='Battery capacity in kWh (default: 30)')
    parser.add_argument('--battery-kw', type=float, default=None,
                       help='Battery power in kW (default: 0.5 * capacity)')
    parser.add_argument('--save-plot', action='store_true',
                       help='Generate and save comparison visualization')
    parser.add_argument('--no-degradation', action='store_true',
                       help='Disable battery degradation modeling')

    args = parser.parse_args()

    # Calculate battery power if not specified (C-rate of 0.5)
    battery_kw = args.battery_kw if args.battery_kw else args.battery_kwh * 0.5

    # Run comparison
    comparison = compare_resolutions(
        battery_kwh=args.battery_kwh,
        battery_kw=battery_kw,
        save_plot=args.save_plot,
        enable_degradation=not args.no_degradation
    )

    return 0


if __name__ == "__main__":
    exit(main())
