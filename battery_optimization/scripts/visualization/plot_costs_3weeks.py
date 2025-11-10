"""
Cost Analysis and Visualization for Reference Case (No Battery)

Simulates and plots:
1. Energy flows (solar, load, grid import/export)
2. Hourly costs breakdown
3. Spot prices and tariffs
4. Annual cost summary

Period: 3 weeks from June 1st, 2020
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from core.battery import Battery
from core.strategies import NoControlStrategy
from core.simulator import BatterySimulator
from core.economic_cost import calculate_total_cost
from core.pvgis_solar import PVGISProduction
from core.price_fetcher import ENTSOEPriceFetcher
from core.consumption_profiles import ConsumptionProfile


def plot_3week_costs(results_df, costs_hourly, spot_prices, timestamps, start_date='2020-06-01'):
    """
    Create comprehensive 3-week visualization of costs and energy flows
    """
    # Add timestamp index to results
    results_df = results_df.copy()
    results_df.index = timestamps

    # Filter to 3 weeks starting from June 1st
    start = pd.Timestamp(start_date)
    end = start + pd.Timedelta(days=21)
    mask = (results_df.index >= start) & (results_df.index < end)

    df_period = results_df[mask].copy()
    costs_period = costs_hourly[mask].copy()
    prices_period = spot_prices[mask].copy()

    # Create figure with subplots
    fig, axes = plt.subplots(4, 1, figsize=(16, 14))
    fig.suptitle('Economic Cost Analysis - Reference Case (No Battery)\n3 Weeks from June 1, 2020',
                 fontsize=16, fontweight='bold')

    # -------------------------------------------------------------------------
    # Plot 1: Energy Flows
    # -------------------------------------------------------------------------
    ax1 = axes[0]

    ax1.fill_between(df_period.index, 0, df_period['production_ac_kw'],
                     alpha=0.3, color='orange', label='Solar Production')
    ax1.plot(df_period.index, df_period['consumption_kw'],
            color='red', linewidth=1.5, label='Load Consumption')
    ax1.plot(df_period.index, df_period['grid_power_kw'],
            color='blue', linewidth=1.5, label='Grid Power (+ import, - export)')

    ax1.axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
    ax1.set_ylabel('Power (kW)', fontsize=12, fontweight='bold')
    ax1.set_title('Energy Flows', fontsize=13, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(df_period.index[0], df_period.index[-1])

    # -------------------------------------------------------------------------
    # Plot 2: Grid Import/Export Split
    # -------------------------------------------------------------------------
    ax2 = axes[1]

    grid_import = df_period['grid_power_kw'].clip(lower=0)
    grid_export = (-df_period['grid_power_kw']).clip(lower=0)

    ax2.fill_between(df_period.index, 0, grid_import,
                     alpha=0.6, color='red', label='Grid Import')
    ax2.fill_between(df_period.index, 0, -grid_export,
                     alpha=0.6, color='green', label='Grid Export')

    ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax2.set_ylabel('Grid Power (kW)', fontsize=12, fontweight='bold')
    ax2.set_title('Grid Import/Export', fontsize=13, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(df_period.index[0], df_period.index[-1])

    # -------------------------------------------------------------------------
    # Plot 3: Spot Prices and Tariffs
    # -------------------------------------------------------------------------
    ax3 = axes[2]

    ax3.plot(prices_period.index, prices_period.values,
            color='purple', linewidth=1.5, label='Spot Price', alpha=0.8)
    ax3.plot(costs_period.index, costs_period['energy_tariff_nok_kwh'],
            color='orange', linewidth=1.2, label='Energy Tariff', linestyle='--')
    ax3.plot(costs_period.index, costs_period['consumption_tax_nok_kwh'],
            color='brown', linewidth=1.2, label='Consumption Tax', linestyle=':')

    # Total price (spot + tariff + tax)
    total_price = (costs_period['spot_price_nok_kwh'] +
                   costs_period['energy_tariff_nok_kwh'] +
                   costs_period['consumption_tax_nok_kwh'])
    ax3.plot(costs_period.index, total_price,
            color='black', linewidth=2, label='Total Price', alpha=0.7)

    ax3.set_ylabel('Price (NOK/kWh)', fontsize=12, fontweight='bold')
    ax3.set_title('Electricity Prices and Tariffs', fontsize=13, fontweight='bold')
    ax3.legend(loc='upper right', fontsize=10)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(costs_period.index[0], costs_period.index[-1])

    # -------------------------------------------------------------------------
    # Plot 4: Hourly Costs
    # -------------------------------------------------------------------------
    ax4 = axes[3]

    # Separate positive costs (import) and negative costs (export revenue)
    cost_import = costs_period['import_cost_nok'].clip(lower=0)
    revenue_export = costs_period['export_revenue_nok'].clip(lower=0)

    ax4.fill_between(costs_period.index, 0, cost_import,
                     alpha=0.6, color='red', label='Import Cost')
    ax4.fill_between(costs_period.index, 0, -revenue_export,
                     alpha=0.6, color='green', label='Export Revenue')

    ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax4.set_ylabel('Cost (NOK/hour)', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax4.set_title('Hourly Energy Costs', fontsize=13, fontweight='bold')
    ax4.legend(loc='upper right', fontsize=10)
    ax4.grid(True, alpha=0.3)
    ax4.set_xlim(costs_period.index[0], costs_period.index[-1])

    # Format x-axis for all subplots
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()

    # Save figure
    output_file = 'results/costs_3weeks_june.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✓ Plot saved: {output_file}")

    return fig


def print_annual_summary(costs_results, results_df):
    """
    Print comprehensive annual cost summary
    """
    print("\n" + "="*80)
    print(" ANNUAL COST SUMMARY - Reference Case (No Battery)")
    print("="*80)

    # Total costs
    print("\n1. TOTAL COSTS")
    print("-" * 80)
    print(f"   Total Annual Cost:        {costs_results['total_cost_nok']:>12,.0f} NOK")
    print(f"   - Energy charges:         {costs_results['energy_cost_nok']:>12,.0f} NOK ({costs_results['energy_cost_nok']/costs_results['total_cost_nok']*100:>5.1f}%)")
    print(f"   - Peak power charges:     {costs_results['peak_cost_nok']:>12,.0f} NOK ({costs_results['peak_cost_nok']/costs_results['total_cost_nok']*100:>5.1f}%)")

    # Energy flows
    print("\n2. ANNUAL ENERGY FLOWS")
    print("-" * 80)

    solar_prod = results_df['production_ac_kw'].sum()
    load_cons = results_df['consumption_kw'].sum()
    grid_import = results_df['grid_power_kw'].clip(lower=0).sum()
    grid_export = (-results_df['grid_power_kw'].clip(upper=0)).sum()
    curtailment = results_df['curtailment_kw'].sum()
    inverter_clip = results_df['inverter_clipping_kw'].sum()

    print(f"   Solar Production:         {solar_prod:>12,.0f} kWh")
    print(f"   Load Consumption:         {load_cons:>12,.0f} kWh")
    print(f"   Grid Import:              {grid_import:>12,.0f} kWh")
    print(f"   Grid Export:              {grid_export:>12,.0f} kWh")
    print(f"   Curtailment:              {curtailment:>12,.0f} kWh ({curtailment/solar_prod*100:>5.2f}%)")
    print(f"   Inverter Clipping:        {inverter_clip:>12,.0f} kWh ({inverter_clip/results_df['production_dc_kw'].sum()*100:>5.2f}%)")

    # Monthly breakdown
    print("\n3. MONTHLY BREAKDOWN")
    print("-" * 80)
    print(f"{'Month':<10} {'Peak (kW)':>12} {'Peak Cost':>14} {'Energy Cost':>15} {'Total Cost':>15}")
    print("-" * 80)

    for _, row in costs_results['monthly_breakdown'].iterrows():
        month_name = pd.Timestamp(2020, int(row['month']), 1).strftime('%B')
        print(f"{month_name:<10} {row['peak_power_kw']:>12.1f} "
              f"{row['peak_cost_nok']:>14,.0f} "
              f"{row['energy_cost_nok']:>15,.0f} "
              f"{row['total_cost_nok']:>15,.0f}")

    # Cost metrics
    print("\n4. COST METRICS")
    print("-" * 80)

    # Per kWh costs
    cost_per_kwh_consumption = costs_results['total_cost_nok'] / load_cons
    cost_per_kwh_import = costs_results['energy_cost_nok'] / grid_import

    print(f"   Average cost per kWh consumed:     {cost_per_kwh_consumption:>8.3f} NOK/kWh")
    print(f"   Average cost per kWh imported:     {cost_per_kwh_import:>8.3f} NOK/kWh")

    # Monthly average costs
    avg_monthly_energy = costs_results['energy_cost_nok'] / 12
    avg_monthly_peak = costs_results['peak_cost_nok'] / 12
    avg_monthly_total = costs_results['total_cost_nok'] / 12

    print(f"\n   Average monthly energy cost:       {avg_monthly_energy:>12,.0f} NOK/month")
    print(f"   Average monthly peak cost:         {avg_monthly_peak:>12,.0f} NOK/month")
    print(f"   Average monthly total cost:        {avg_monthly_total:>12,.0f} NOK/month")

    # Peak power statistics
    peaks = costs_results['monthly_breakdown']['peak_power_kw']
    print(f"\n   Peak demand (annual max):          {peaks.max():>12.1f} kW")
    print(f"   Peak demand (annual min):          {peaks.min():>12.1f} kW")
    print(f"   Peak demand (annual avg):          {peaks.mean():>12.1f} kW")

    print("\n" + "="*80)


def main():
    print("\n" + "="*80)
    print(" COST ANALYSIS - Reference Case (No Battery)")
    print(" 3-Week Visualization + Annual Summary")
    print("="*80)

    # Load data
    print("\nLoading data...")

    # Solar production (PVGIS typical year)
    pvgis = PVGISProduction(
        lat=58.97, lon=5.73, pv_capacity_kwp=138.55,
        tilt=30, azimuth=173, system_loss=14
    )
    production = pvgis.fetch_hourly_production(2024, refresh=False)
    year = production.index[0].year

    # Consumption profile
    consumption = ConsumptionProfile.generate_annual_profile(
        profile_type='commercial_office',
        annual_kwh=300000,
        year=year
    )

    # Spot prices
    price_fetcher = ENTSOEPriceFetcher()
    spot_prices = price_fetcher.fetch_prices(2024, 'NO2', refresh=False)
    spot_prices.index = spot_prices.index.map(lambda x: x.replace(year=year))

    # Handle NaN values
    if spot_prices.isna().any():
        spot_prices = spot_prices.ffill().bfill()

    # Align data
    min_len = min(len(production), len(consumption), len(spot_prices))
    production = production[:min_len]
    consumption = consumption[:min_len]
    spot_prices = spot_prices[:min_len]
    timestamps = production.index

    print(f"  Data loaded: {min_len} hours (year {year})")

    # Run simulation
    print("\nRunning simulation (reference case - no battery)...")
    strategy = NoControlStrategy()
    simulator = BatterySimulator(strategy=strategy, battery=None)

    results = simulator.simulate_year(
        production, consumption, spot_prices,
        solar_inverter_capacity_kw=110,
        grid_export_limit_kw=77,
        battery_inverter_efficiency=0.98
    )

    print("  ✓ Simulation complete")

    # Calculate costs
    print("\nCalculating economic costs...")
    costs = calculate_total_cost(
        grid_import_power=results['grid_power_kw'].clip(lower=0).values,
        grid_export_power=(-results['grid_power_kw'].clip(upper=0)).values,
        timestamps=timestamps,
        spot_prices=spot_prices.values,
        timestep_hours=1.0
    )

    print("  ✓ Cost calculation complete")

    # Plot 3-week period
    print("\nGenerating 3-week visualization (June 1-21)...")
    fig = plot_3week_costs(results, costs['hourly_details'], spot_prices, timestamps, start_date='2020-06-01')
    plt.show()

    # Print annual summary
    print_annual_summary(costs, results)

    print("\n" + "="*80)
    print(" Analysis Complete")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
