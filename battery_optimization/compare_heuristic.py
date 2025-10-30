"""
Compare Reference Case vs Heuristic Battery Strategy

Runs simulations for:
1. Reference case (no battery)
2. SimpleRule heuristic strategy (20 kWh / 10 kW battery)

Outputs:
- 3-week comparison plots (June 1-21)
- Annual cost comparison
- Savings analysis
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from core.battery import Battery
from core.strategies import NoControlStrategy, SimpleRuleStrategy
from core.simulator import BatterySimulator
from core.economic_cost import calculate_total_cost
from core.pvgis_solar import PVGISProduction
from core.price_fetcher import ENTSOEPriceFetcher
from core.consumption_profiles import ConsumptionProfile


def plot_comparison_3weeks(results_ref, results_heur, costs_ref, costs_heur,
                           timestamps, battery_size_kwh=20.0, start_date='2020-06-01'):
    """
    Create comparison visualization for 3 weeks
    """
    # Filter to 3-week period
    start = pd.Timestamp(start_date)
    end = start + pd.Timedelta(days=21)
    mask = (timestamps >= start) & (timestamps < end)

    # Add timestamps to results
    results_ref = results_ref.copy()
    results_ref.index = timestamps
    results_heur = results_heur.copy()
    results_heur.index = timestamps

    # Filter data
    ref_period = results_ref[mask]
    heur_period = results_heur[mask]
    costs_ref_period = costs_ref['hourly_details'][mask]
    costs_heur_period = costs_heur['hourly_details'][mask]

    # Create figure
    fig, axes = plt.subplots(5, 1, figsize=(16, 16))
    fig.suptitle('Heuristic Battery Strategy vs Reference Case\n3 Weeks from June 1, 2020',
                 fontsize=16, fontweight='bold')

    # -------------------------------------------------------------------------
    # Plot 1: Battery SOC and Power
    # -------------------------------------------------------------------------
    ax1 = axes[0]

    # SOC (left axis)
    color_soc = 'tab:blue'
    ax1.plot(heur_period.index, heur_period['battery_soc_kwh'],
            color=color_soc, linewidth=2, label='Battery SOC')
    ax1.axhline(y=battery_size_kwh * 0.9, color=color_soc, linestyle='--',
               linewidth=0.8, alpha=0.5, label='Max SOC (90%)')
    ax1.axhline(y=battery_size_kwh * 0.1, color=color_soc, linestyle='--',
               linewidth=0.8, alpha=0.5, label='Min SOC (10%)')
    ax1.set_ylabel('Battery SOC (kWh)', fontsize=12, fontweight='bold', color=color_soc)
    ax1.tick_params(axis='y', labelcolor=color_soc)
    ax1.set_ylim(0, battery_size_kwh)

    # Battery power (right axis)
    ax1_twin = ax1.twinx()
    color_power = 'tab:red'
    battery_power_ac = heur_period['battery_power_ac_kw']
    ax1_twin.fill_between(heur_period.index,
                          0, battery_power_ac.clip(lower=0),
                          alpha=0.4, color='green', label='Charging')
    ax1_twin.fill_between(heur_period.index,
                          0, battery_power_ac.clip(upper=0),
                          alpha=0.4, color='red', label='Discharging')
    ax1_twin.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax1_twin.set_ylabel('Battery Power (kW)', fontsize=12, fontweight='bold', color=color_power)
    ax1_twin.tick_params(axis='y', labelcolor=color_power)

    ax1.set_title('Battery State of Charge and Power', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(heur_period.index[0], heur_period.index[-1])

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_twin.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)

    # -------------------------------------------------------------------------
    # Plot 2: Grid Power Comparison
    # -------------------------------------------------------------------------
    ax2 = axes[1]

    ax2.plot(ref_period.index, ref_period['grid_power_kw'],
            color='gray', linewidth=1.5, alpha=0.7, label='Reference (no battery)')
    ax2.plot(heur_period.index, heur_period['grid_power_kw'],
            color='blue', linewidth=1.5, label='Heuristic strategy')
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)

    ax2.set_ylabel('Grid Power (kW)', fontsize=12, fontweight='bold')
    ax2.set_title('Grid Import/Export Comparison', fontsize=13, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(ref_period.index[0], ref_period.index[-1])

    # -------------------------------------------------------------------------
    # Plot 3: Grid Import Reduction
    # -------------------------------------------------------------------------
    ax3 = axes[2]

    grid_import_ref = ref_period['grid_power_kw'].clip(lower=0)
    grid_import_heur = heur_period['grid_power_kw'].clip(lower=0)
    import_reduction = grid_import_ref - grid_import_heur

    ax3.fill_between(ref_period.index, 0, grid_import_ref,
                     alpha=0.3, color='red', label='Reference import')
    ax3.fill_between(heur_period.index, 0, grid_import_heur,
                     alpha=0.5, color='orange', label='Heuristic import')
    ax3.fill_between(heur_period.index, 0, import_reduction,
                     alpha=0.6, color='green', label='Import reduction')

    ax3.set_ylabel('Grid Import (kW)', fontsize=12, fontweight='bold')
    ax3.set_title('Grid Import Reduction from Battery', fontsize=13, fontweight='bold')
    ax3.legend(loc='upper right', fontsize=10)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(ref_period.index[0], ref_period.index[-1])

    # -------------------------------------------------------------------------
    # Plot 4: Hourly Cost Comparison
    # -------------------------------------------------------------------------
    ax4 = axes[3]

    cost_ref = costs_ref_period['net_cost_nok']
    cost_heur = costs_heur_period['net_cost_nok']
    cost_savings = cost_ref - cost_heur

    ax4.plot(costs_ref_period.index, cost_ref,
            color='red', linewidth=1.5, alpha=0.7, label='Reference cost')
    ax4.plot(costs_heur_period.index, cost_heur,
            color='blue', linewidth=1.5, label='Heuristic cost')
    ax4.fill_between(costs_heur_period.index, cost_heur, cost_ref,
                     where=(cost_savings > 0),
                     alpha=0.4, color='green', label='Cost savings')
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.8)

    ax4.set_ylabel('Hourly Cost (NOK)', fontsize=12, fontweight='bold')
    ax4.set_title('Hourly Energy Cost Comparison', fontsize=13, fontweight='bold')
    ax4.legend(loc='upper right', fontsize=10)
    ax4.grid(True, alpha=0.3)
    ax4.set_xlim(costs_ref_period.index[0], costs_ref_period.index[-1])

    # -------------------------------------------------------------------------
    # Plot 5: Cumulative Savings
    # -------------------------------------------------------------------------
    ax5 = axes[4]

    cumulative_savings = cost_savings.cumsum()

    ax5.fill_between(costs_heur_period.index, 0, cumulative_savings,
                     alpha=0.5, color='green')
    ax5.plot(costs_heur_period.index, cumulative_savings,
            color='darkgreen', linewidth=2, label='Cumulative savings')
    ax5.axhline(y=0, color='black', linestyle='-', linewidth=0.8)

    ax5.set_ylabel('Cumulative Savings (NOK)', fontsize=12, fontweight='bold')
    ax5.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax5.set_title('Cumulative Cost Savings (3 weeks)', fontsize=13, fontweight='bold')
    ax5.legend(loc='upper left', fontsize=10)
    ax5.grid(True, alpha=0.3)
    ax5.set_xlim(costs_heur_period.index[0], costs_heur_period.index[-1])

    # Format x-axis
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()

    # Save
    output_file = 'results/comparison_heuristic_3weeks.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✓ Comparison plot saved: {output_file}")

    return fig


def print_comparison_summary(costs_ref, costs_heur, results_ref, results_heur):
    """
    Print detailed comparison summary
    """
    print("\n" + "="*80)
    print(" ANNUAL COMPARISON: Reference vs Heuristic Battery Strategy")
    print("="*80)

    # Cost comparison
    savings_total = costs_ref['total_cost_nok'] - costs_heur['total_cost_nok']
    savings_energy = costs_ref['energy_cost_nok'] - costs_heur['energy_cost_nok']
    savings_peak = costs_ref['peak_cost_nok'] - costs_heur['peak_cost_nok']
    savings_pct = (savings_total / costs_ref['total_cost_nok']) * 100

    print("\n1. COST COMPARISON")
    print("-" * 80)
    print(f"{'Metric':<30} {'Reference':<18} {'Heuristic':<18} {'Savings':<18}")
    print("-" * 80)
    print(f"{'Total Annual Cost':<30} {costs_ref['total_cost_nok']:>15,.0f} NOK "
          f"{costs_heur['total_cost_nok']:>15,.0f} NOK "
          f"{savings_total:>15,.0f} NOK ({savings_pct:>5.2f}%)")
    print(f"{'  - Energy charges':<30} {costs_ref['energy_cost_nok']:>15,.0f} NOK "
          f"{costs_heur['energy_cost_nok']:>15,.0f} NOK "
          f"{savings_energy:>15,.0f} NOK")
    print(f"{'  - Peak power charges':<30} {costs_ref['peak_cost_nok']:>15,.0f} NOK "
          f"{costs_heur['peak_cost_nok']:>15,.0f} NOK "
          f"{savings_peak:>15,.0f} NOK")

    # Energy flow comparison
    print("\n2. ENERGY FLOW COMPARISON")
    print("-" * 80)

    grid_import_ref = results_ref['grid_power_kw'].clip(lower=0).sum()
    grid_import_heur = results_heur['grid_power_kw'].clip(lower=0).sum()
    grid_export_ref = (-results_ref['grid_power_kw'].clip(upper=0)).sum()
    grid_export_heur = (-results_heur['grid_power_kw'].clip(upper=0)).sum()

    import_reduction = grid_import_ref - grid_import_heur
    export_reduction = grid_export_ref - grid_export_heur

    print(f"{'Metric':<30} {'Reference':<18} {'Heuristic':<18} {'Change':<18}")
    print("-" * 80)
    print(f"{'Grid Import':<30} {grid_import_ref:>15,.0f} kWh "
          f"{grid_import_heur:>15,.0f} kWh "
          f"{-import_reduction:>15,.0f} kWh ({-import_reduction/grid_import_ref*100:>5.2f}%)")
    print(f"{'Grid Export':<30} {grid_export_ref:>15,.0f} kWh "
          f"{grid_export_heur:>15,.0f} kWh "
          f"{-export_reduction:>15,.0f} kWh ({-export_reduction/grid_export_ref*100:>5.2f}%)")

    # Battery statistics
    print("\n3. BATTERY PERFORMANCE")
    print("-" * 80)

    battery_energy_charged = results_heur['battery_power_ac_kw'].clip(lower=0).sum()
    battery_energy_discharged = (-results_heur['battery_power_ac_kw'].clip(upper=0)).sum()
    roundtrip_energy = min(battery_energy_charged, battery_energy_discharged)
    efficiency_apparent = (battery_energy_discharged / battery_energy_charged * 100) if battery_energy_charged > 0 else 0

    # Count cycles (approximate: total energy / capacity)
    battery_capacity = 20.0  # kWh
    cycles = battery_energy_discharged / battery_capacity

    print(f"   Energy charged (AC):           {battery_energy_charged:>12,.0f} kWh")
    print(f"   Energy discharged (AC):        {battery_energy_discharged:>12,.0f} kWh")
    print(f"   Roundtrip efficiency:          {efficiency_apparent:>12.1f} %")
    print(f"   Equivalent full cycles:        {cycles:>12.1f} cycles/year")
    print(f"   Import reduction:              {import_reduction:>12,.0f} kWh")
    print(f"   Export reduction:              {export_reduction:>12,.0f} kWh (stored in battery)")

    # Monthly savings
    print("\n4. MONTHLY SAVINGS BREAKDOWN")
    print("-" * 80)
    print(f"{'Month':<10} {'Ref Cost':>14} {'Heur Cost':>14} {'Savings':>14} {'Peak Δ':>12}")
    print("-" * 80)

    for idx, row_ref in costs_ref['monthly_breakdown'].iterrows():
        row_heur = costs_heur['monthly_breakdown'].iloc[idx]
        month_name = pd.Timestamp(2020, int(row_ref['month']), 1).strftime('%B')
        month_savings = row_ref['total_cost_nok'] - row_heur['total_cost_nok']
        peak_reduction = row_ref['peak_power_kw'] - row_heur['peak_power_kw']

        print(f"{month_name:<10} {row_ref['total_cost_nok']:>14,.0f} "
              f"{row_heur['total_cost_nok']:>14,.0f} "
              f"{month_savings:>14,.0f} "
              f"{peak_reduction:>12.1f} kW")

    # Economic metrics
    print("\n5. ECONOMIC METRICS")
    print("-" * 80)

    monthly_savings = savings_total / 12
    battery_cost_estimate = 20 * 5000  # 20 kWh @ 5000 NOK/kWh (current market)
    payback_years = battery_cost_estimate / savings_total if savings_total > 0 else float('inf')

    print(f"   Annual savings:                {savings_total:>12,.0f} NOK/year")
    print(f"   Monthly savings:               {monthly_savings:>12,.0f} NOK/month")
    print(f"   Savings per cycle:             {savings_total/cycles:>12,.0f} NOK/cycle")
    print(f"\n   Battery cost (market):         {battery_cost_estimate:>12,.0f} NOK (5000 NOK/kWh)")
    print(f"   Simple payback period:         {payback_years:>12.1f} years")
    print(f"   Required battery cost:         {savings_total*15/battery_capacity:>12,.0f} NOK/kWh (15-year payback)")

    print("\n" + "="*80)


def main():
    print("\n" + "="*80)
    print(" HEURISTIC BATTERY STRATEGY COMPARISON")
    print(" Reference Case vs SimpleRule Strategy (20 kWh / 10 kW)")
    print("="*80)

    # Load data
    print("\nLoading data...")

    pvgis = PVGISProduction(
        lat=58.97, lon=5.73, pv_capacity_kwp=138.55,
        tilt=30, azimuth=173, system_loss=14
    )
    production = pvgis.fetch_hourly_production(2024, refresh=False)
    year = production.index[0].year

    consumption = ConsumptionProfile.generate_annual_profile(
        profile_type='commercial_office',
        annual_kwh=300000,
        year=year
    )

    price_fetcher = ENTSOEPriceFetcher()
    spot_prices = price_fetcher.fetch_prices(2024, 'NO2', refresh=False)
    spot_prices.index = spot_prices.index.map(lambda x: x.replace(year=year))

    if spot_prices.isna().any():
        spot_prices = spot_prices.ffill().bfill()

    min_len = min(len(production), len(consumption), len(spot_prices))
    production = production[:min_len]
    consumption = consumption[:min_len]
    spot_prices = spot_prices[:min_len]
    timestamps = production.index

    print(f"  Data loaded: {min_len} hours (year {year})")

    # Run simulations
    print("\nRunning simulations...")

    # Reference case
    print("  - Reference case (no battery)...")
    strategy_ref = NoControlStrategy()
    sim_ref = BatterySimulator(strategy=strategy_ref, battery=None)
    results_ref = sim_ref.simulate_year(
        production, consumption, spot_prices,
        solar_inverter_capacity_kw=110,
        grid_export_limit_kw=77,
        battery_inverter_efficiency=0.98
    )

    # Heuristic strategy
    print("  - Heuristic strategy (SimpleRule)...")
    battery = Battery(
        capacity_kwh=20.0,
        power_kw=10.0,
        efficiency=0.90,
        min_soc=0.1,
        max_soc=0.9,
        max_c_rate_charge=1.0,
        max_c_rate_discharge=1.0
    )

    strategy_heur = SimpleRuleStrategy(
        cheap_price_threshold=0.3,
        expensive_price_threshold=0.8,
        night_hours=(0, 6)
    )

    sim_heur = BatterySimulator(strategy=strategy_heur, battery=battery)
    results_heur = sim_heur.simulate_year(
        production, consumption, spot_prices,
        solar_inverter_capacity_kw=110,
        grid_export_limit_kw=77,
        battery_inverter_efficiency=0.98
    )

    print("  ✓ Simulations complete")

    # Calculate costs
    print("\nCalculating economic costs...")

    costs_ref = calculate_total_cost(
        grid_import_power=results_ref['grid_power_kw'].clip(lower=0).values,
        grid_export_power=(-results_ref['grid_power_kw'].clip(upper=0)).values,
        timestamps=timestamps,
        spot_prices=spot_prices.values,
        timestep_hours=1.0
    )

    costs_heur = calculate_total_cost(
        grid_import_power=results_heur['grid_power_kw'].clip(lower=0).values,
        grid_export_power=(-results_heur['grid_power_kw'].clip(upper=0)).values,
        timestamps=timestamps,
        spot_prices=spot_prices.values,
        timestep_hours=1.0
    )

    print("  ✓ Cost calculations complete")

    # Generate plots
    print("\nGenerating comparison visualization (June 1-21)...")
    fig = plot_comparison_3weeks(results_ref, results_heur, costs_ref, costs_heur,
                                 timestamps, battery_size_kwh=20.0, start_date='2020-06-01')
    plt.close(fig)  # Close instead of show to avoid hanging

    # Print summary
    print_comparison_summary(costs_ref, costs_heur, results_ref, results_heur)

    print("\n" + "="*80)
    print(" Analysis Complete")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
