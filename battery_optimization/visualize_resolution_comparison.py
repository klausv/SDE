#!/usr/bin/env python3
"""
Visualize the LP optimization results for hourly vs 15-minute resolution.

Shows:
1. Spot prices at both resolutions
2. Battery SOC (State of Charge)
3. Charge/discharge power
4. Grid import/export
5. How the battery responds to intra-hour price variations
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from core.price_fetcher import fetch_prices
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.time_aggregation import upsample_hourly_to_15min
from config import config

def prepare_data(start_date, end_date, resolution='PT60M'):
    """Prepare data for optimization."""
    print(f"\n📅 Preparing data: {start_date} to {end_date}")
    print(f"   Resolution: {resolution}")

    # Fetch spot prices
    year = start_date.year
    prices = fetch_prices(year, 'NO2', resolution=resolution)
    prices = prices.loc[start_date:end_date]
    timestamps = prices.index

    print(f"   ✅ {len(prices)} price points")

    # Generate PV production (simplified)
    hours = pd.date_range(start_date, end_date, freq='h', tz='Europe/Oslo')
    pv_hourly = []
    for ts in hours:
        hour = ts.hour
        if 6 <= hour <= 20:
            # Parabolic profile peaking at noon
            pv = 150 * (1 - ((hour - 13) / 7) ** 2) * 0.7  # kW
        else:
            pv = 0
        pv_hourly.append(pv)

    pv_hourly = pd.Series(pv_hourly, index=hours)

    if resolution == 'PT15M':
        pv_production = upsample_hourly_to_15min(pv_hourly.values, pv_hourly.index)
    else:
        pv_production = pv_hourly

    # Generate consumption (simplified)
    consumption = []
    for ts in timestamps:
        hour = ts.hour
        # Higher during day, lower at night
        if 6 <= hour <= 22:
            load = 25 + np.random.uniform(-5, 5)  # kW
        else:
            load = 15 + np.random.uniform(-3, 3)  # kW
        consumption.append(load)

    consumption = pd.Series(consumption, index=timestamps)

    print(f"   ✅ Total PV: {pv_production.sum() * (1.0 if resolution == 'PT60M' else 0.25):.0f} kWh")
    print(f"   ✅ Total consumption: {consumption.sum() * (1.0 if resolution == 'PT60M' else 0.25):.0f} kWh")

    return timestamps, prices, pv_production, consumption


def run_optimization(timestamps, prices, pv_production, consumption,
                     battery_kwh, battery_kw, resolution):
    """Run LP optimization and return full results."""
    print(f"\n🔋 Running LP optimization: {battery_kwh} kWh / {battery_kw} kW")
    print(f"   Resolution: {resolution}")

    optimizer = MonthlyLPOptimizer(config, resolution=resolution,
                                   battery_kwh=battery_kwh, battery_kw=battery_kw)

    # Handle both pandas Series and numpy arrays
    pv_vals = pv_production.values if hasattr(pv_production, 'values') else pv_production
    consumption_vals = consumption.values if hasattr(consumption, 'values') else consumption
    price_vals = prices.values if hasattr(prices, 'values') else prices

    result = optimizer.optimize_month(
        month_idx=10,
        pv_production=pv_vals,
        load_consumption=consumption_vals,
        spot_prices=price_vals,
        timestamps=timestamps,
        E_initial=battery_kwh * 0.5
    )

    if result.success:
        print(f"   ✅ Objective: {result.objective_value:,.2f} kr")
        print(f"   Energy cost: {result.energy_cost:,.2f} kr")
        print(f"   Power cost: {result.power_cost:,.2f} kr")
    else:
        print(f"   ❌ Optimization failed!")

    return result


def plot_comparison(data_hourly, data_15min, battery_kwh, battery_kw, save_path=None):
    """
    Create comprehensive visualization comparing hourly and 15-minute optimization.

    Shows 3 days to make patterns clear.
    """
    # Extract data
    timestamps_h = data_hourly['timestamps']
    timestamps_15 = data_15min['timestamps']

    # Select 3 representative days (Oct 10-12)
    start_plot = pd.Timestamp('2025-10-10', tz='Europe/Oslo')
    end_plot = pd.Timestamp('2025-10-12 23:59', tz='Europe/Oslo')

    mask_h = (timestamps_h >= start_plot) & (timestamps_h <= end_plot)
    mask_15 = (timestamps_15 >= start_plot) & (timestamps_15 <= end_plot)

    # Create figure
    fig, axes = plt.subplots(4, 2, figsize=(16, 14))
    fig.suptitle(f'LP Optimization: Hourly vs 15-Minute Resolution\n'
                 f'Battery: {battery_kwh} kWh / {battery_kw} kW | Period: Oct 10-12, 2025',
                 fontsize=16, fontweight='bold')

    # Left column: Hourly (PT60M)
    # Right column: 15-minute (PT15M)

    # --- Row 1: Spot Prices ---
    ax_price_h = axes[0, 0]
    ax_price_15 = axes[0, 1]

    ax_price_h.plot(timestamps_h[mask_h], data_hourly['prices'][mask_h],
                    'o-', color='steelblue', linewidth=2, markersize=4)
    ax_price_h.set_ylabel('Spot Price [kr/kWh]', fontsize=11, fontweight='bold')
    ax_price_h.set_title('Hourly Resolution (PT60M)', fontsize=12, fontweight='bold')
    ax_price_h.grid(True, alpha=0.3)
    ax_price_h.set_xlim(start_plot, end_plot)

    ax_price_15.plot(timestamps_15[mask_15], data_15min['prices'][mask_15],
                     '-', color='darkgreen', linewidth=1, alpha=0.7)
    ax_price_15.set_ylabel('Spot Price [kr/kWh]', fontsize=11, fontweight='bold')
    ax_price_15.set_title('15-Minute Resolution (PT15M)', fontsize=12, fontweight='bold')
    ax_price_15.grid(True, alpha=0.3)
    ax_price_15.set_xlim(start_plot, end_plot)

    # Add intra-hour variation annotation
    ax_price_15.text(0.02, 0.98, 'Captures intra-hour\nprice variation',
                     transform=ax_price_15.transAxes, fontsize=9,
                     verticalalignment='top', bbox=dict(boxstyle='round',
                     facecolor='wheat', alpha=0.5))

    # --- Row 2: Battery State of Charge (SOC) ---
    ax_soc_h = axes[1, 0]
    ax_soc_15 = axes[1, 1]

    soc_h = data_hourly['result'].E_battery / battery_kwh * 100
    soc_15 = data_15min['result'].E_battery / battery_kwh * 100

    ax_soc_h.plot(timestamps_h[mask_h], soc_h[mask_h],
                  '-', color='purple', linewidth=2)
    ax_soc_h.axhline(y=10, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Min SOC')
    ax_soc_h.axhline(y=90, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Max SOC')
    ax_soc_h.set_ylabel('SOC [%]', fontsize=11, fontweight='bold')
    ax_soc_h.set_ylim(0, 100)
    ax_soc_h.grid(True, alpha=0.3)
    ax_soc_h.legend(loc='upper right', fontsize=8)
    ax_soc_h.set_xlim(start_plot, end_plot)

    ax_soc_15.plot(timestamps_15[mask_15], soc_15[mask_15],
                   '-', color='purple', linewidth=1.5)
    ax_soc_15.axhline(y=10, color='red', linestyle='--', linewidth=1, alpha=0.5)
    ax_soc_15.axhline(y=90, color='red', linestyle='--', linewidth=1, alpha=0.5)
    ax_soc_15.set_ylabel('SOC [%]', fontsize=11, fontweight='bold')
    ax_soc_15.set_ylim(0, 100)
    ax_soc_15.grid(True, alpha=0.3)
    ax_soc_15.set_xlim(start_plot, end_plot)

    # --- Row 3: Battery Charge/Discharge Power ---
    ax_bat_h = axes[2, 0]
    ax_bat_15 = axes[2, 1]

    P_charge_h = data_hourly['result'].P_charge
    P_discharge_h = data_hourly['result'].P_discharge
    P_charge_15 = data_15min['result'].P_charge
    P_discharge_15 = data_15min['result'].P_discharge

    ax_bat_h.fill_between(timestamps_h[mask_h], 0, P_charge_h[mask_h],
                           color='green', alpha=0.5, label='Charge')
    ax_bat_h.fill_between(timestamps_h[mask_h], 0, -P_discharge_h[mask_h],
                           color='red', alpha=0.5, label='Discharge')
    ax_bat_h.set_ylabel('Battery Power [kW]', fontsize=11, fontweight='bold')
    ax_bat_h.set_ylim(-battery_kw * 1.1, battery_kw * 1.1)
    ax_bat_h.axhline(y=0, color='black', linewidth=0.5)
    ax_bat_h.grid(True, alpha=0.3)
    ax_bat_h.legend(loc='upper right', fontsize=8)
    ax_bat_h.set_xlim(start_plot, end_plot)

    ax_bat_15.fill_between(timestamps_15[mask_15], 0, P_charge_15[mask_15],
                            color='green', alpha=0.5, label='Charge')
    ax_bat_15.fill_between(timestamps_15[mask_15], 0, -P_discharge_15[mask_15],
                            color='red', alpha=0.5, label='Discharge')
    ax_bat_15.set_ylabel('Battery Power [kW]', fontsize=11, fontweight='bold')
    ax_bat_15.set_ylim(-battery_kw * 1.1, battery_kw * 1.1)
    ax_bat_15.axhline(y=0, color='black', linewidth=0.5)
    ax_bat_15.grid(True, alpha=0.3)
    ax_bat_15.legend(loc='upper right', fontsize=8)
    ax_bat_15.set_xlim(start_plot, end_plot)

    # --- Row 4: Grid Import/Export ---
    ax_grid_h = axes[3, 0]
    ax_grid_15 = axes[3, 1]

    P_import_h = data_hourly['result'].P_grid_import
    P_export_h = data_hourly['result'].P_grid_export
    P_import_15 = data_15min['result'].P_grid_import
    P_export_15 = data_15min['result'].P_grid_export

    ax_grid_h.fill_between(timestamps_h[mask_h], 0, P_import_h[mask_h],
                            color='orange', alpha=0.5, label='Import')
    ax_grid_h.fill_between(timestamps_h[mask_h], 0, -P_export_h[mask_h],
                            color='blue', alpha=0.5, label='Export')
    ax_grid_h.set_ylabel('Grid Power [kW]', fontsize=11, fontweight='bold')
    ax_grid_h.set_xlabel('Time', fontsize=11, fontweight='bold')
    ax_grid_h.axhline(y=0, color='black', linewidth=0.5)
    ax_grid_h.grid(True, alpha=0.3)
    ax_grid_h.legend(loc='upper right', fontsize=8)
    ax_grid_h.set_xlim(start_plot, end_plot)

    ax_grid_15.fill_between(timestamps_15[mask_15], 0, P_import_15[mask_15],
                             color='orange', alpha=0.5, label='Import')
    ax_grid_15.fill_between(timestamps_15[mask_15], 0, -P_export_15[mask_15],
                             color='blue', alpha=0.5, label='Export')
    ax_grid_15.set_ylabel('Grid Power [kW]', fontsize=11, fontweight='bold')
    ax_grid_15.set_xlabel('Time', fontsize=11, fontweight='bold')
    ax_grid_15.axhline(y=0, color='black', linewidth=0.5)
    ax_grid_15.grid(True, alpha=0.3)
    ax_grid_15.legend(loc='upper right', fontsize=8)
    ax_grid_15.set_xlim(start_plot, end_plot)

    # Format x-axis
    for ax in axes.flatten():
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d\n%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center', fontsize=9)

    plt.tight_layout(rect=[0, 0.03, 1, 0.97])

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\n💾 Plot saved: {save_path}")

    plt.show()


def main():
    """Main execution."""
    print("\n" + "="*80)
    print("VISUALIZATION: LP OPTIMIZATION COMPARISON")
    print("="*80)

    battery_kwh = 30
    battery_kw = 30

    # Prepare data for October 10-12 (3 days for fast optimization and clear plots)
    start_date = pd.Timestamp('2025-10-10', tz='Europe/Oslo')
    end_date = pd.Timestamp('2025-10-12 23:59', tz='Europe/Oslo')

    print("\n" + "="*80)
    print("HOURLY RESOLUTION (PT60M)")
    print("="*80)
    timestamps_h, prices_h, pv_h, consumption_h = prepare_data(
        start_date, end_date, resolution='PT60M'
    )
    result_h = run_optimization(
        timestamps_h, prices_h, pv_h, consumption_h,
        battery_kwh, battery_kw, resolution='PT60M'
    )

    print("\n" + "="*80)
    print("15-MINUTE RESOLUTION (PT15M)")
    print("="*80)
    timestamps_15, prices_15, pv_15, consumption_15 = prepare_data(
        start_date, end_date, resolution='PT15M'
    )
    result_15 = run_optimization(
        timestamps_15, prices_15, pv_15, consumption_15,
        battery_kwh, battery_kw, resolution='PT15M'
    )

    # Package data for plotting
    data_hourly = {
        'timestamps': timestamps_h,
        'prices': prices_h,
        'pv': pv_h,
        'consumption': consumption_h,
        'result': result_h
    }

    data_15min = {
        'timestamps': timestamps_15,
        'prices': prices_15,
        'pv': pv_15,
        'consumption': consumption_15,
        'result': result_15
    }

    # Create visualization
    print("\n" + "="*80)
    print("CREATING VISUALIZATION")
    print("="*80)
    plot_comparison(
        data_hourly, data_15min,
        battery_kwh, battery_kw,
        save_path='results/resolution_comparison_plot.png'
    )

    # Summary statistics
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)

    print(f"\n💰 Economic Results:")
    print(f"  Hourly:    {result_h.objective_value:,.2f} kr")
    print(f"  15-minute: {result_15.objective_value:,.2f} kr")
    print(f"  Difference: {result_h.objective_value - result_15.objective_value:+,.2f} kr")
    print(f"  Improvement: {(result_h.objective_value - result_15.objective_value) / result_h.objective_value * 100:+.2f}%")

    charge_h = result_h.P_charge.sum() * 1.0  # kWh
    charge_15 = result_15.P_charge.sum() * 0.25  # kWh

    print(f"\n🔋 Battery Utilization:")
    print(f"  Charged (hourly):    {charge_h:.1f} kWh ({charge_h / battery_kwh:.2f} cycles)")
    print(f"  Charged (15-minute): {charge_15:.1f} kWh ({charge_15 / battery_kwh:.2f} cycles)")
    print(f"  Difference: {charge_15 - charge_h:+.1f} kWh ({(charge_15 - charge_h) / charge_h * 100:+.1f}%)")


if __name__ == "__main__":
    main()
