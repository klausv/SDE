"""
Run annual battery optimization and save detailed time series results.

Generates:
- Hourly time series for full year (battery SOC, power flows, prices)
- Monthly performance breakdown
- Visualization plots
"""

import sys
import json
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.insert(0, str(Path(__file__).parent))

from config import BatteryOptimizationConfig, DegradationConfig
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.price_fetcher import ENTSOEPriceFetcher
from core.pvgis_solar import PVGISProduction


def load_annual_data():
    """Load full year of real data"""
    print("\nLoading 2024 annual data...")

    # Prices
    fetcher = ENTSOEPriceFetcher(resolution='PT60M')
    prices = fetcher.fetch_prices(year=2024, area='NO2')

    # Solar
    pvgis = PVGISProduction(lat=58.97, lon=5.73, pv_capacity_kwp=138.55, tilt=30.0, azimuth=173.0)
    pv_series = pvgis.fetch_hourly_production(year=2024)

    # Load
    timestamps = prices.index
    load = np.zeros(len(timestamps))
    avg_load = 300000 / 8760
    base = avg_load * 0.6

    for i, ts in enumerate(timestamps):
        ts = pd.Timestamp(ts)
        if ts.weekday() < 5 and 6 <= ts.hour < 18:
            load[i] = base * 1.8
        elif 18 <= ts.hour < 22:
            load[i] = base * 1.3
        else:
            load[i] = base

    # Match PV to price timestamps
    pv = np.zeros(len(timestamps))
    for i, ts in enumerate(timestamps):
        ts = pd.Timestamp(ts)
        matching = pv_series.index[
            (pv_series.index.month == ts.month) &
            (pv_series.index.day == ts.day) &
            (pv_series.index.hour == ts.hour)
        ]
        if len(matching) > 0:
            pv[i] = pv_series.loc[matching[0]]

    # Create DataFrame
    data = pd.DataFrame({
        'spot_price': prices.values,
        'pv_production': pv,
        'load': load
    }, index=timestamps)

    print(f"Loaded {len(data)} hours of data")
    return data


def run_optimization(data, battery_kwh=30, battery_kw=15):
    """Run monthly LP optimization and collect time series"""
    print(f"\nRunning optimization: {battery_kwh} kWh / {battery_kw} kW battery")

    # Config with degradation
    config = BatteryOptimizationConfig()
    config.battery.degradation = DegradationConfig(
        enabled=True,
        cycle_life_full_dod=5000,
        calendar_life_years=28.0
    )

    optimizer = MonthlyLPOptimizer(config, resolution='PT60M',
                                   battery_kwh=battery_kwh, battery_kw=battery_kw)

    # Split by month
    data['month'] = data.index.month

    E_initial = battery_kwh * 0.5

    # Collect time series
    all_timestamps = []
    all_soc = []
    all_charge = []
    all_discharge = []
    all_grid_import = []
    all_grid_export = []
    all_curtail = []
    all_degradation = []

    monthly_results = []

    for month in range(1, 13):
        month_data = data[data['month'] == month]

        result = optimizer.optimize_month(
            month_idx=month,
            pv_production=month_data['pv_production'].values,
            load_consumption=month_data['load'].values,
            spot_prices=month_data['spot_price'].values,
            timestamps=month_data.index.values,
            E_initial=E_initial
        )

        if not result.success:
            print(f"Month {month}: FAILED")
            continue

        print(f"Month {month:2d}: Energy={result.energy_cost:8,.0f} NOK, "
              f"Power={result.power_cost:6,.0f} NOK, "
              f"Degrad={result.degradation_cost:6,.0f} NOK")

        # Collect time series
        all_timestamps.extend(month_data.index)
        all_soc.extend(result.E_battery)
        all_charge.extend(result.P_charge)
        all_discharge.extend(result.P_discharge)
        all_grid_import.extend(result.P_grid_import)
        all_grid_export.extend(result.P_grid_export)
        all_curtail.extend(result.P_curtail)
        all_degradation.extend(result.DP_total if result.DP_total is not None else np.zeros(len(result.E_battery)))

        monthly_results.append({
            'month': month,
            'energy_cost': result.energy_cost,
            'power_cost': result.power_cost,
            'degradation_cost': result.degradation_cost,
            'total_cost': result.energy_cost + result.power_cost + result.degradation_cost,
            'cycles': np.sum(result.DP_cyc) / config.battery.degradation.rho_constant if result.DP_cyc is not None and config.battery.degradation.rho_constant > 0 else 0,
            'curtailment_kwh': np.sum(result.P_curtail)
        })

        E_initial = result.E_battery_final

    # Create time series DataFrame
    ts_df = pd.DataFrame({
        'timestamp': all_timestamps,
        'battery_soc_kwh': all_soc,
        'battery_charge_kw': all_charge,
        'battery_discharge_kw': all_discharge,
        'grid_import_kw': all_grid_import,
        'grid_export_kw': all_grid_export,
        'curtailment_kw': all_curtail,
        'degradation_pct': np.array(all_degradation),  # Already in percentage units from DP_total
    })

    # Add original data
    ts_df = ts_df.merge(data[['spot_price', 'pv_production', 'load']],
                        left_on='timestamp', right_index=True)

    # Calculate net battery power (positive = charging, negative = discharging)
    ts_df['battery_power_kw'] = ts_df['battery_charge_kw'] - ts_df['battery_discharge_kw']

    # Calculate grid net flow (positive = import, negative = export)
    ts_df['grid_net_kw'] = ts_df['grid_import_kw'] - ts_df['grid_export_kw']

    return ts_df, monthly_results


def plot_annual_overview(ts_df, monthly_results, battery_kwh):
    """Create annual overview plots"""
    print("\nGenerating annual overview plots...")

    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(4, 2, hspace=0.3, wspace=0.3)

    # =====================================================================
    # Plot 1: Battery SOC over full year
    # =====================================================================
    ax1 = fig.add_subplot(gs[0, :])

    ax1.plot(ts_df['timestamp'], ts_df['battery_soc_kwh'], linewidth=0.8, color='#9b59b6', alpha=0.8)
    ax1.fill_between(ts_df['timestamp'], 0, ts_df['battery_soc_kwh'], alpha=0.3, color='#9b59b6')

    # Add SOC limits
    soc_min = battery_kwh * 0.1
    soc_max = battery_kwh * 0.9
    ax1.axhline(y=soc_min, color='red', linewidth=1, linestyle='--', alpha=0.5, label=f'Min SOC (10%)')
    ax1.axhline(y=soc_max, color='orange', linewidth=1, linestyle='--', alpha=0.5, label=f'Max SOC (90%)')

    ax1.set_ylabel('SOC (kWh)', fontsize=12)
    ax1.set_title(f'Battery State of Charge - Full Year 2024 ({battery_kwh} kWh battery)',
                  fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(ts_df['timestamp'].min(), ts_df['timestamp'].max())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator())

    # =====================================================================
    # Plot 2: Monthly cost breakdown
    # =====================================================================
    ax2 = fig.add_subplot(gs[1, 0])

    months = [r['month'] for r in monthly_results]
    energy_costs = [r['energy_cost'] for r in monthly_results]
    power_costs = [r['power_cost'] for r in monthly_results]
    degrad_costs = [r['degradation_cost'] for r in monthly_results]

    x = np.arange(len(months))
    width = 0.7

    p1 = ax2.bar(x, energy_costs, width, label='Energy', color='#e74c3c')
    p2 = ax2.bar(x, power_costs, width, bottom=energy_costs, label='Power Tariff', color='#3498db')
    p3 = ax2.bar(x, degrad_costs, width,
                 bottom=[e+p for e,p in zip(energy_costs, power_costs)],
                 label='Degradation', color='#95a5a6')

    ax2.set_ylabel('Cost (NOK)', fontsize=11)
    ax2.set_xlabel('Month', fontsize=11)
    ax2.set_title('Monthly Cost Breakdown', fontsize=13, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(['Jan','Feb','Mar','Apr','May','Jun',
                         'Jul','Aug','Sep','Oct','Nov','Dec'], fontsize=9)
    ax2.legend(loc='upper left', fontsize=9)
    ax2.grid(axis='y', alpha=0.3)

    # =====================================================================
    # Plot 3: Monthly cycles and degradation
    # =====================================================================
    ax3 = fig.add_subplot(gs[1, 1])

    cycles = [r['cycles'] for r in monthly_results]

    ax3.bar(x, cycles, width, color='#f39c12', alpha=0.8, edgecolor='black', linewidth=0.5)

    ax3.set_ylabel('Cycles', fontsize=11)
    ax3.set_xlabel('Month', fontsize=11)
    ax3.set_title('Monthly Battery Cycles', fontsize=13, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(['Jan','Feb','Mar','Apr','May','Jun',
                         'Jul','Aug','Sep','Oct','Nov','Dec'], fontsize=9)
    ax3.grid(axis='y', alpha=0.3)

    # Add total
    total_cycles = sum(cycles)
    ax3.text(0.98, 0.95, f'Total: {total_cycles:.0f} cycles/year',
            transform=ax3.transAxes, ha='right', va='top',
            fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    # =====================================================================
    # Plot 4: Cumulative degradation
    # =====================================================================
    ax4 = fig.add_subplot(gs[2, 0])

    cumulative_deg = np.cumsum(ts_df['degradation_pct'])

    ax4.plot(ts_df['timestamp'], cumulative_deg, linewidth=2, color='#e74c3c')
    ax4.fill_between(ts_df['timestamp'], 0, cumulative_deg, alpha=0.3, color='#e74c3c')

    # Add EOL threshold
    ax4.axhline(y=20, color='red', linewidth=2, linestyle='--', alpha=0.7, label='EOL (20%)')

    ax4.set_ylabel('Cumulative Degradation (%)', fontsize=11)
    ax4.set_title('Battery Degradation Over Year', fontsize=13, fontweight='bold')
    ax4.legend(loc='upper left')
    ax4.grid(True, alpha=0.3)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax4.xaxis.set_major_locator(mdates.MonthLocator())

    # Add final degradation text
    final_deg = cumulative_deg.iloc[-1]
    ax4.text(0.98, 0.05, f'Annual degradation: {final_deg:.2f}%',
            transform=ax4.transAxes, ha='right', va='bottom',
            fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    # =====================================================================
    # Plot 5: Grid flow duration curve
    # =====================================================================
    ax5 = fig.add_subplot(gs[2, 1])

    # Sort grid import/export
    grid_net_sorted = np.sort(ts_df['grid_net_kw'])[::-1]
    hours = np.arange(len(grid_net_sorted))

    # Split into import and export
    import_mask = grid_net_sorted > 0
    export_mask = grid_net_sorted < 0

    ax5.fill_between(hours[import_mask], 0, grid_net_sorted[import_mask],
                     alpha=0.4, color='red', label='Import')
    ax5.fill_between(hours[export_mask], 0, grid_net_sorted[export_mask],
                     alpha=0.4, color='green', label='Export')

    ax5.axhline(y=0, color='black', linewidth=1, linestyle='--', alpha=0.5)
    ax5.set_xlabel('Hours (sorted)', fontsize=11)
    ax5.set_ylabel('Grid Power (kW)', fontsize=11)
    ax5.set_title('Grid Flow Duration Curve', fontsize=13, fontweight='bold')
    ax5.legend(loc='upper right')
    ax5.grid(True, alpha=0.3)

    # =====================================================================
    # Plot 6: Spot price vs battery operation
    # =====================================================================
    ax6 = fig.add_subplot(gs[3, :])

    # Sample every 24 hours for readability
    sample_idx = np.arange(0, len(ts_df), 24)
    ts_sample = ts_df.iloc[sample_idx]

    # Price line
    ax6_price = ax6.twinx()
    ax6_price.plot(ts_sample['timestamp'], ts_sample['spot_price'],
                   color='gray', linewidth=1, alpha=0.5, label='Spot Price')
    ax6_price.set_ylabel('Spot Price (NOK/kWh)', fontsize=11, color='gray')
    ax6_price.tick_params(axis='y', labelcolor='gray')

    # Battery power
    charging = ts_sample['battery_power_kw'].clip(lower=0)
    discharging = -ts_sample['battery_power_kw'].clip(upper=0)

    ax6.fill_between(ts_sample['timestamp'], 0, charging,
                     alpha=0.5, color='green', label='Charging', step='mid')
    ax6.fill_between(ts_sample['timestamp'], 0, -discharging,
                     alpha=0.5, color='red', label='Discharging', step='mid')

    ax6.set_ylabel('Battery Power (kW)', fontsize=11)
    ax6.set_xlabel('Date', fontsize=11)
    ax6.set_title('Battery Operation vs Spot Price (daily aggregation)',
                  fontsize=13, fontweight='bold')
    ax6.legend(loc='upper left')
    ax6.grid(True, alpha=0.3, axis='y')
    ax6.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax6.xaxis.set_major_locator(mdates.MonthLocator())

    fig.suptitle('Battery Optimization - Annual Time Series Analysis 2024',
                 fontsize=16, fontweight='bold', y=0.995)

    # Save
    output_file = Path(__file__).parent / "results" / "figures" / "annual_timeseries_overview.png"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=200, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()

    return output_file


def main():
    """Main execution"""
    print("\n" + "="*70)
    print("ANNUAL TIME SERIES OPTIMIZATION")
    print("="*70)

    # Load data
    data = load_annual_data()

    # Run optimization
    battery_kwh = 30
    battery_kw = 15
    ts_df, monthly_results = run_optimization(data, battery_kwh, battery_kw)

    # Save time series to CSV
    csv_file = Path(__file__).parent / "results" / "annual_timeseries_2024.csv"
    ts_df.to_csv(csv_file, index=False)
    print(f"\n✓ Time series saved: {csv_file} ({len(ts_df)} hours)")

    # Save monthly summary
    summary_file = Path(__file__).parent / "results" / "annual_monthly_summary_2024.json"
    summary_data = {
        'timestamp': datetime.now().isoformat(),
        'battery_kwh': battery_kwh,
        'battery_kw': battery_kw,
        'monthly_results': monthly_results,
        'annual_totals': {
            'energy_cost': sum(r['energy_cost'] for r in monthly_results),
            'power_cost': sum(r['power_cost'] for r in monthly_results),
            'degradation_cost': sum(r['degradation_cost'] for r in monthly_results),
            'total_cost': sum(r['total_cost'] for r in monthly_results),
            'total_cycles': sum(r['cycles'] for r in monthly_results),
            'total_curtailment_kwh': sum(r['curtailment_kwh'] for r in monthly_results),
            'total_degradation_pct': ts_df['degradation_pct'].sum()
        }
    }

    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=2)
    print(f"✓ Monthly summary saved: {summary_file}")

    # Generate plots
    plot_file = plot_annual_overview(ts_df, monthly_results, battery_kwh)

    # Print summary
    print("\n" + "="*70)
    print("ANNUAL SUMMARY")
    print("="*70)
    totals = summary_data['annual_totals']
    print(f"\nTotal costs:")
    print(f"  Energy:       {totals['energy_cost']:>12,.2f} NOK")
    print(f"  Power tariff: {totals['power_cost']:>12,.2f} NOK")
    print(f"  Degradation:  {totals['degradation_cost']:>12,.2f} NOK")
    print(f"  TOTAL:        {totals['total_cost']:>12,.2f} NOK")

    print(f"\nBattery utilization:")
    print(f"  Annual cycles:        {totals['total_cycles']:>8.0f} cycles/year")
    print(f"  Total degradation:    {totals['total_degradation_pct']:>8.2f}%")
    print(f"  Total curtailment:    {totals['total_curtailment_kwh']:>8,.0f} kWh")

    print("\n" + "="*70)
    print("✓ ANNUAL TIME SERIES ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nGenerated files:")
    print(f"  - {csv_file.name}")
    print(f"  - {summary_file.name}")
    print(f"  - {plot_file.name}")

    return ts_df, monthly_results, summary_data


if __name__ == "__main__":
    main()
