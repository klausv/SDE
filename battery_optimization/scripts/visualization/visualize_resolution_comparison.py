#!/usr/bin/env python3
"""
Visualize time resolution comparison: PT60M (hourly) vs PT15M (15-minute).

Migrated to RollingHorizonOptimizer with weekly sequential optimization (52 weeks).

Shows:
1. Annual cost comparison (PT60M vs PT15M)
2. SOC pattern differences (hourly may miss intra-hour fluctuations)
3. Solve time comparison (PT15M should be ~3-4× slower due to 4× timesteps)
4. Peak demand tracking differences
5. Curtailment differences (higher resolution may capture more curtailment)

Key Metrics:
- Number of optimization windows (both should be 52 weeks)
- Average solve time per week
- Annual cost breakdown (energy, power tariff, degradation)
- Battery utilization patterns
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for WSL
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys
from pathlib import Path
from datetime import datetime
import time

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config import BatteryOptimizationConfig, DegradationConfig
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from core.price_fetcher import ENTSOEPriceFetcher
from core.pvgis_solar import PVGISProduction
from operational import BatterySystemState, calculate_average_power_tariff_rate


def load_data_at_resolution(year=2024, resolution='PT60M'):
    """Load spot prices and solar production at specified resolution"""
    print(f"\n{'='*70}")
    print(f"Loading data for resolution: {resolution}")
    print(f"{'='*70}")

    # Load spot prices
    fetcher = ENTSOEPriceFetcher(resolution=resolution)
    prices_series = fetcher.fetch_prices(year=year, area='NO2', resolution=resolution)
    prices_df = prices_series.to_frame('price_nok_per_kwh')

    timestamps = prices_df.index
    spot_prices = prices_df['price_nok_per_kwh'].values

    # Load solar production (hourly from PVGIS)
    pvgis = PVGISProduction(
        lat=58.97,
        lon=5.73,
        pv_capacity_kwp=138.55,
        tilt=30.0,
        azimuth=173.0
    )

    pvgis_series = pvgis.fetch_hourly_production(year=year)
    pvgis_data = pvgis_series.to_frame('production_kw')
    pvgis_data.rename(columns={'production_kw': 'pv_power_kw'}, inplace=True)

    # Match timestamps to resolution
    pv_production = np.zeros(len(timestamps))
    for i, ts in enumerate(timestamps):
        matching = pvgis_data[
            (pvgis_data.index.month == ts.month) &
            (pvgis_data.index.day == ts.day) &
            (pvgis_data.index.hour == ts.hour)
        ]
        if len(matching) > 0:
            pv_production[i] = matching['pv_power_kw'].values[0]

    # Create synthetic load (simple pattern)
    annual_kwh = 300000
    hours_per_year = 8760
    avg_load = annual_kwh / hours_per_year

    load = np.zeros(len(timestamps))
    for i, ts in enumerate(timestamps):
        base = avg_load * 0.6
        if ts.weekday() < 5 and 6 <= ts.hour < 18:
            load[i] = base * 1.8
        elif 18 <= ts.hour < 22:
            load[i] = base * 1.3
        else:
            load[i] = base

    print(f"  Loaded {len(timestamps)} timesteps")
    print(f"  Price range: {spot_prices.min():.3f} - {spot_prices.max():.3f} NOK/kWh")
    print(f"  PV production: {pv_production.sum():.0f} kW·timesteps")
    print(f"  Load consumption: {load.sum():.0f} kW·timesteps")

    return timestamps, spot_prices, pv_production, load


def run_weekly_sequential_optimization(
    timestamps,
    spot_prices,
    pv_production,
    load,
    battery_kwh,
    battery_kw,
    resolution,
    config
):
    """
    Run weekly sequential optimization for full year.

    Args:
        timestamps: Full year timestamps
        spot_prices: Full year spot prices [NOK/kWh]
        pv_production: Full year PV production [kW]
        load: Full year load consumption [kW]
        battery_kwh: Battery capacity [kWh]
        battery_kw: Battery power rating [kW]
        resolution: Time resolution ('PT60M' or 'PT15M')
        config: BatteryOptimizationConfig object

    Returns:
        Dictionary with full year results and weekly metrics
    """
    print(f"\n{'='*70}")
    print(f"Running weekly sequential optimization - {resolution}")
    print(f"{'='*70}")
    print(f"Battery: {battery_kwh} kWh, {battery_kw} kW")
    print(f"Horizon: 168 hours (7 days)")
    print()

    # Calculate weekly timesteps
    if resolution == 'PT60M':
        weekly_timesteps = 168  # 7 days @ hourly
    elif resolution == 'PT15M':
        weekly_timesteps = 672  # 7 days @ 15-min
    else:
        raise ValueError(f"Unsupported resolution: {resolution}")

    n_timesteps = len(timestamps)
    print(f"Total timesteps: {n_timesteps}")
    print(f"Weekly timesteps: {weekly_timesteps}")
    print(f"Expected weeks: {n_timesteps // weekly_timesteps}")

    # Initialize optimizer
    optimizer = RollingHorizonOptimizer(
        config=config,
        battery_kwh=battery_kwh,
        battery_kw=battery_kw,
        horizon_hours=168  # Weekly optimization
    )

    # Initialize battery system state
    state = BatterySystemState(
        battery_capacity_kwh=battery_kwh,
        current_soc_kwh=0.5 * battery_kwh,  # Start at 50% SOC
        current_monthly_peak_kw=0.0,
        month_start_date=timestamps[0].replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(config.tariff)
    )

    # Storage for full year results
    full_results = {
        'P_charge': [],
        'P_discharge': [],
        'P_grid_import': [],
        'P_grid_export': [],
        'E_battery': [],
        'P_curtail': [],
        'DP_cyc': [],
        'DP_total': [],
        'weekly_costs': [],
        'weekly_energy_costs': [],
        'weekly_power_costs': [],
        'weekly_degradation_costs': [],
        'weekly_solve_times': []
    }

    # Run weekly sequential optimization
    print("\nOptimizing weekly windows...")
    prev_month = timestamps[0].month if n_timesteps > 0 else 1

    week = 0
    while True:
        t_start = week * weekly_timesteps
        t_end = min(t_start + weekly_timesteps, n_timesteps)

        if t_start >= n_timesteps:
            break  # Reached end of data

        # Check for month boundary and reset peak
        current_month = timestamps[t_start].month
        if current_month != prev_month:
            state._reset_monthly_peak(timestamps[t_start])
            print(f"  Week {week}: Month boundary {prev_month} → {current_month}, peak reset")
            prev_month = current_month

        # Optimize week
        start_time = time.time()
        result = optimizer.optimize_window(
            current_state=state,
            pv_production=pv_production[t_start:t_end],
            load_consumption=load[t_start:t_end],
            spot_prices=spot_prices[t_start:t_end],
            timestamps=timestamps[t_start:t_end],
            verbose=False
        )
        solve_time = time.time() - start_time

        if not result.success:
            print(f"  ❌ Week {week} optimization failed: {result.message}")
            return None

        # Store results
        full_results['P_charge'].extend(result.P_charge)
        full_results['P_discharge'].extend(result.P_discharge)
        full_results['P_grid_import'].extend(result.P_grid_import)
        full_results['P_grid_export'].extend(result.P_grid_export)
        full_results['E_battery'].extend(result.E_battery)
        full_results['P_curtail'].extend(result.P_curtail)
        full_results['DP_cyc'].extend(result.DP_cyc)
        full_results['DP_total'].extend(result.DP_total)

        full_results['weekly_costs'].append(result.objective_value)
        full_results['weekly_energy_costs'].append(result.energy_cost)
        full_results['weekly_power_costs'].append(result.peak_penalty_actual)
        full_results['weekly_degradation_costs'].append(result.degradation_cost)
        full_results['weekly_solve_times'].append(solve_time)

        # Update state for next week
        state.update_from_measurement(
            timestamp=timestamps[t_end - 1],
            soc_kwh=result.E_battery_final,
            grid_import_power_kw=result.P_grid_import[-1] if len(result.P_grid_import) > 0 else 0.0
        )

        if week % 10 == 0:
            print(f"  Week {week}: Cost={result.objective_value:.2f} NOK, Solve={solve_time:.3f}s")

        week += 1

    # Convert to numpy arrays
    for key in ['P_charge', 'P_discharge', 'P_grid_import', 'P_grid_export',
                'E_battery', 'P_curtail', 'DP_cyc', 'DP_total']:
        full_results[key] = np.array(full_results[key])

    # Calculate annual totals
    annual_cost = sum(full_results['weekly_costs'])
    annual_energy_cost = sum(full_results['weekly_energy_costs'])
    annual_power_cost = sum(full_results['weekly_power_costs'])
    annual_degradation_cost = sum(full_results['weekly_degradation_costs'])
    avg_solve_time = np.mean(full_results['weekly_solve_times'])

    print(f"\n✓ Optimization complete - {week} weeks")
    print(f"  Annual cost: {annual_cost:,.0f} NOK")
    print(f"  Energy cost: {annual_energy_cost:,.0f} NOK")
    print(f"  Power cost: {annual_power_cost:,.0f} NOK")
    print(f"  Degradation cost: {annual_degradation_cost:,.0f} NOK")
    print(f"  Avg solve time: {avg_solve_time:.3f}s/week")

    return {
        'results': full_results,
        'annual_cost': annual_cost,
        'annual_energy_cost': annual_energy_cost,
        'annual_power_cost': annual_power_cost,
        'annual_degradation_cost': annual_degradation_cost,
        'avg_solve_time': avg_solve_time,
        'num_weeks': week
    }


def create_comparison_visualizations(
    data_hourly,
    data_15min,
    timestamps_hourly,
    timestamps_15min,
    battery_kwh,
    battery_kw,
    year
):
    """Create comprehensive comparison visualizations"""

    output_dir = Path(__file__).parent / 'results' / 'figures'
    output_dir.mkdir(parents=True, exist_ok=True)

    # ========================================================================
    # Figure 1: Full Year Overview - SOC and Solve Times
    # ========================================================================
    fig1 = plt.figure(figsize=(18, 10))

    # 1.1: SOC comparison (full year)
    ax1 = plt.subplot(3, 1, 1)

    # Trim to matching lengths
    len_h = len(data_hourly['results']['E_battery'])
    len_15 = len(data_15min['results']['E_battery'])
    ts_h = timestamps_hourly[:len_h]
    ts_15 = timestamps_15min[:len_15]

    soc_h = (data_hourly['results']['E_battery'] / battery_kwh) * 100
    soc_15 = (data_15min['results']['E_battery'] / battery_kwh) * 100

    ax1.plot(ts_h, soc_h, 'b-', linewidth=1.2, label='Hourly (PT60M)', alpha=0.7)
    ax1.plot(ts_15, soc_15, 'r-', linewidth=0.8, label='15-Minute (PT15M)', alpha=0.6)
    ax1.axhline(y=20, color='gray', linestyle='--', alpha=0.4, label='SOC Limits')
    ax1.axhline(y=80, color='gray', linestyle='--', alpha=0.4)
    ax1.set_ylabel('State of Charge (%)', fontsize=12, fontweight='bold')
    ax1.set_ylim([0, 100])
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.set_title(f'Resolution Comparison: PT60M vs PT15M | Battery: {battery_kwh} kWh / {battery_kw} kW | Year: {year}',
                  fontsize=14, fontweight='bold')

    # 1.2: Weekly solve times
    ax2 = plt.subplot(3, 1, 2)

    weeks_h = np.arange(len(data_hourly['results']['weekly_solve_times']))
    weeks_15 = np.arange(len(data_15min['results']['weekly_solve_times']))

    ax2.bar(weeks_h - 0.2, data_hourly['results']['weekly_solve_times'],
            width=0.4, color='blue', alpha=0.7, label='Hourly (PT60M)')
    ax2.bar(weeks_15 + 0.2, data_15min['results']['weekly_solve_times'],
            width=0.4, color='red', alpha=0.7, label='15-Minute (PT15M)')

    ax2.axhline(y=data_hourly['avg_solve_time'], color='blue',
                linestyle='--', linewidth=2, label=f'Avg (PT60M): {data_hourly["avg_solve_time"]:.3f}s')
    ax2.axhline(y=data_15min['avg_solve_time'], color='red',
                linestyle='--', linewidth=2, label=f'Avg (PT15M): {data_15min["avg_solve_time"]:.3f}s')

    ax2.set_ylabel('Solve Time (seconds)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Week Number', fontsize=12)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.legend(loc='upper right', fontsize=9)
    ax2.set_title('Weekly Optimization Solve Times', fontsize=12, fontweight='bold')

    # 1.3: Weekly cost comparison
    ax3 = plt.subplot(3, 1, 3)

    ax3.plot(weeks_h, data_hourly['results']['weekly_costs'], 'b-o',
             linewidth=1.5, markersize=3, label='Hourly (PT60M)', alpha=0.7)
    ax3.plot(weeks_15, data_15min['results']['weekly_costs'], 'r-s',
             linewidth=1.2, markersize=2, label='15-Minute (PT15M)', alpha=0.6)

    ax3.set_ylabel('Weekly Cost (NOK)', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Week Number', fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc='upper right', fontsize=10)
    ax3.set_title('Weekly Optimization Costs', fontsize=12, fontweight='bold')

    plt.tight_layout()
    output_file1 = output_dir / f'resolution_comparison_overview_year{year}.png'
    plt.savefig(output_file1, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved: {output_file1}")
    plt.close()

    # ========================================================================
    # Figure 2: Detailed 3-Day View (Oct 10-12 for visibility)
    # ========================================================================
    fig2, axes = plt.subplots(4, 2, figsize=(16, 14))
    fig2.suptitle(f'Detailed Comparison: 3-Day Sample (Oct 10-12, {year})\n'
                  f'Battery: {battery_kwh} kWh / {battery_kw} kW',
                  fontsize=14, fontweight='bold')

    # Select 3-day window
    start_plot = pd.Timestamp(f'{year}-10-10', tz='Europe/Oslo')
    end_plot = pd.Timestamp(f'{year}-10-12 23:59', tz='Europe/Oslo')

    mask_h = (ts_h >= start_plot) & (ts_h <= end_plot)
    mask_15 = (ts_15 >= start_plot) & (ts_15 <= end_plot)

    # Row 1: SOC
    axes[0, 0].plot(ts_h[mask_h], soc_h[mask_h], 'b-', linewidth=2)
    axes[0, 0].axhline(y=20, color='r', linestyle='--', alpha=0.5)
    axes[0, 0].axhline(y=80, color='r', linestyle='--', alpha=0.5)
    axes[0, 0].set_ylabel('SOC (%)', fontsize=11, fontweight='bold')
    axes[0, 0].set_title('Hourly (PT60M)', fontsize=12, fontweight='bold')
    axes[0, 0].set_ylim([0, 100])
    axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].plot(ts_15[mask_15], soc_15[mask_15], 'r-', linewidth=1.5)
    axes[0, 1].axhline(y=20, color='r', linestyle='--', alpha=0.5)
    axes[0, 1].axhline(y=80, color='r', linestyle='--', alpha=0.5)
    axes[0, 1].set_ylabel('SOC (%)', fontsize=11, fontweight='bold')
    axes[0, 1].set_title('15-Minute (PT15M)', fontsize=12, fontweight='bold')
    axes[0, 1].set_ylim([0, 100])
    axes[0, 1].grid(True, alpha=0.3)

    # Row 2: Battery charge/discharge
    P_charge_h = data_hourly['results']['P_charge'][:len_h]
    P_discharge_h = data_hourly['results']['P_discharge'][:len_h]
    P_charge_15 = data_15min['results']['P_charge'][:len_15]
    P_discharge_15 = data_15min['results']['P_discharge'][:len_15]

    axes[1, 0].fill_between(ts_h[mask_h], 0, P_charge_h[mask_h],
                             color='green', alpha=0.5, label='Charge')
    axes[1, 0].fill_between(ts_h[mask_h], 0, -P_discharge_h[mask_h],
                             color='red', alpha=0.5, label='Discharge')
    axes[1, 0].set_ylabel('Battery Power (kW)', fontsize=11, fontweight='bold')
    axes[1, 0].set_ylim([-battery_kw * 1.1, battery_kw * 1.1])
    axes[1, 0].axhline(y=0, color='black', linewidth=0.5)
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].legend(loc='upper right', fontsize=9)

    axes[1, 1].fill_between(ts_15[mask_15], 0, P_charge_15[mask_15],
                             color='green', alpha=0.5, label='Charge')
    axes[1, 1].fill_between(ts_15[mask_15], 0, -P_discharge_15[mask_15],
                             color='red', alpha=0.5, label='Discharge')
    axes[1, 1].set_ylabel('Battery Power (kW)', fontsize=11, fontweight='bold')
    axes[1, 1].set_ylim([-battery_kw * 1.1, battery_kw * 1.1])
    axes[1, 1].axhline(y=0, color='black', linewidth=0.5)
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].legend(loc='upper right', fontsize=9)

    # Row 3: Grid import/export
    P_import_h = data_hourly['results']['P_grid_import'][:len_h]
    P_export_h = data_hourly['results']['P_grid_export'][:len_h]
    P_import_15 = data_15min['results']['P_grid_import'][:len_15]
    P_export_15 = data_15min['results']['P_grid_export'][:len_15]

    axes[2, 0].fill_between(ts_h[mask_h], 0, P_import_h[mask_h],
                             color='orange', alpha=0.5, label='Import')
    axes[2, 0].fill_between(ts_h[mask_h], 0, -P_export_h[mask_h],
                             color='blue', alpha=0.5, label='Export')
    axes[2, 0].set_ylabel('Grid Power (kW)', fontsize=11, fontweight='bold')
    axes[2, 0].axhline(y=0, color='black', linewidth=0.5)
    axes[2, 0].grid(True, alpha=0.3)
    axes[2, 0].legend(loc='upper right', fontsize=9)

    axes[2, 1].fill_between(ts_15[mask_15], 0, P_import_15[mask_15],
                             color='orange', alpha=0.5, label='Import')
    axes[2, 1].fill_between(ts_15[mask_15], 0, -P_export_15[mask_15],
                             color='blue', alpha=0.5, label='Export')
    axes[2, 1].set_ylabel('Grid Power (kW)', fontsize=11, fontweight='bold')
    axes[2, 1].axhline(y=0, color='black', linewidth=0.5)
    axes[2, 1].grid(True, alpha=0.3)
    axes[2, 1].legend(loc='upper right', fontsize=9)

    # Row 4: Curtailment
    P_curtail_h = data_hourly['results']['P_curtail'][:len_h]
    P_curtail_15 = data_15min['results']['P_curtail'][:len_15]

    axes[3, 0].fill_between(ts_h[mask_h], 0, P_curtail_h[mask_h],
                             color='purple', alpha=0.4, label='Curtailment')
    axes[3, 0].set_ylabel('Curtailment (kW)', fontsize=11, fontweight='bold')
    axes[3, 0].set_xlabel('Time', fontsize=11)
    axes[3, 0].grid(True, alpha=0.3)
    axes[3, 0].legend(loc='upper right', fontsize=9)

    axes[3, 1].fill_between(ts_15[mask_15], 0, P_curtail_15[mask_15],
                             color='purple', alpha=0.4, label='Curtailment')
    axes[3, 1].set_ylabel('Curtailment (kW)', fontsize=11, fontweight='bold')
    axes[3, 1].set_xlabel('Time', fontsize=11)
    axes[3, 1].grid(True, alpha=0.3)
    axes[3, 1].legend(loc='upper right', fontsize=9)

    # Format x-axis for all subplots
    for ax in axes.flatten():
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d\n%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center', fontsize=9)
        ax.set_xlim(start_plot, end_plot)

    plt.tight_layout(rect=[0, 0.02, 1, 0.98])
    output_file2 = output_dir / f'resolution_comparison_detail_year{year}.png'
    plt.savefig(output_file2, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file2}")
    plt.close()

    # ========================================================================
    # Figure 3: Comparison Summary Metrics
    # ========================================================================
    fig3, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig3.suptitle(f'Resolution Comparison Summary - Year {year}', fontsize=14, fontweight='bold')

    # 3.1: Annual cost breakdown
    ax_cost = axes[0, 0]
    categories = ['Energy', 'Power Tariff', 'Degradation']
    costs_h = [
        data_hourly['annual_energy_cost'],
        data_hourly['annual_power_cost'],
        data_hourly['annual_degradation_cost']
    ]
    costs_15 = [
        data_15min['annual_energy_cost'],
        data_15min['annual_power_cost'],
        data_15min['annual_degradation_cost']
    ]

    x_pos = np.arange(len(categories))
    width = 0.35

    ax_cost.bar(x_pos - width/2, costs_h, width, label='Hourly (PT60M)', color='blue', alpha=0.7)
    ax_cost.bar(x_pos + width/2, costs_15, width, label='15-Min (PT15M)', color='red', alpha=0.7)
    ax_cost.set_ylabel('Annual Cost (NOK)', fontsize=11, fontweight='bold')
    ax_cost.set_xticks(x_pos)
    ax_cost.set_xticklabels(categories, fontsize=10)
    ax_cost.legend(loc='upper right', fontsize=9)
    ax_cost.grid(True, alpha=0.3, axis='y')
    ax_cost.set_title('Annual Cost Breakdown', fontsize=12, fontweight='bold')

    # 3.2: Total annual cost comparison
    ax_total = axes[0, 1]
    total_costs = [data_hourly['annual_cost'], data_15min['annual_cost']]
    colors_total = ['blue', 'red']
    ax_total.bar(['Hourly\n(PT60M)', '15-Min\n(PT15M)'], total_costs,
                 color=colors_total, alpha=0.7, width=0.5)
    ax_total.set_ylabel('Total Annual Cost (NOK)', fontsize=11, fontweight='bold')
    ax_total.grid(True, alpha=0.3, axis='y')
    ax_total.set_title('Total Annual Cost Comparison', fontsize=12, fontweight='bold')

    # Add cost difference annotation
    cost_diff = data_15min['annual_cost'] - data_hourly['annual_cost']
    cost_diff_pct = (cost_diff / data_hourly['annual_cost']) * 100
    ax_total.text(0.5, 0.95, f'Difference: {cost_diff:+,.0f} NOK ({cost_diff_pct:+.2f}%)',
                  transform=ax_total.transAxes, fontsize=10, fontweight='bold',
                  verticalalignment='top', horizontalalignment='center',
                  bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.6))

    # 3.3: Solve time comparison
    ax_time = axes[1, 0]
    solve_times = [data_hourly['avg_solve_time'], data_15min['avg_solve_time']]
    ax_time.bar(['Hourly\n(PT60M)', '15-Min\n(PT15M)'], solve_times,
                color=colors_total, alpha=0.7, width=0.5)
    ax_time.set_ylabel('Average Solve Time (seconds)', fontsize=11, fontweight='bold')
    ax_time.grid(True, alpha=0.3, axis='y')
    ax_time.set_title('Weekly Optimization Solve Time', fontsize=12, fontweight='bold')

    # Add speedup annotation
    speedup_ratio = data_15min['avg_solve_time'] / data_hourly['avg_solve_time']
    ax_time.text(0.5, 0.95, f'PT15M is {speedup_ratio:.2f}× slower\n(due to 4× timesteps)',
                 transform=ax_time.transAxes, fontsize=10, fontweight='bold',
                 verticalalignment='top', horizontalalignment='center',
                 bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.6))

    # 3.4: Metrics table
    ax_metrics = axes[1, 1]
    ax_metrics.axis('off')

    # Calculate additional metrics
    total_charge_h = data_hourly['results']['P_charge'].sum() * 1.0  # kWh (hourly)
    total_charge_15 = data_15min['results']['P_charge'].sum() * 0.25  # kWh (15-min)
    cycles_h = total_charge_h / battery_kwh
    cycles_15 = total_charge_15 / battery_kwh

    total_curtail_h = data_hourly['results']['P_curtail'].sum() * 1.0  # kWh
    total_curtail_15 = data_15min['results']['P_curtail'].sum() * 0.25  # kWh

    metrics_text = f"""
    COMPARISON METRICS SUMMARY
    {'─'*45}

    Resolution:
      Hourly:         {data_hourly['num_weeks']} weeks optimized
      15-Minute:      {data_15min['num_weeks']} weeks optimized

    Annual Costs:
      Hourly:         {data_hourly['annual_cost']:>12,.0f} NOK
      15-Minute:      {data_15min['annual_cost']:>12,.0f} NOK
      Difference:     {cost_diff:>12,.0f} NOK ({cost_diff_pct:+.2f}%)

    Battery Utilization:
      Charged (PT60M):  {total_charge_h:>10,.0f} kWh ({cycles_h:.1f} cycles)
      Charged (PT15M):  {total_charge_15:>10,.0f} kWh ({cycles_15:.1f} cycles)

    Solar Curtailment:
      PT60M:          {total_curtail_h:>12,.0f} kWh
      PT15M:          {total_curtail_15:>12,.0f} kWh

    Computational Performance:
      Avg solve (PT60M): {data_hourly['avg_solve_time']:>8.3f} s/week
      Avg solve (PT15M): {data_15min['avg_solve_time']:>8.3f} s/week
      Speedup ratio:     {speedup_ratio:>8.2f}×
    """

    ax_metrics.text(0.05, 0.5, metrics_text, fontsize=9, family='monospace',
                    verticalalignment='center', transform=ax_metrics.transAxes)

    plt.tight_layout(rect=[0, 0.02, 1, 0.98])
    output_file3 = output_dir / f'resolution_comparison_metrics_year{year}.png'
    plt.savefig(output_file3, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file3}")
    plt.close()


def main():
    """Main execution for resolution comparison"""

    print("\n" + "="*70)
    print("RESOLUTION COMPARISON: PT60M vs PT15M")
    print("Weekly Sequential Optimization (52 weeks each)")
    print("="*70)
    print()

    # Configuration
    year = 2024
    battery_kwh = 100  # Configurable battery size
    battery_kw = 50    # Configurable power rating

    # Create config with degradation
    config = BatteryOptimizationConfig()
    config.battery.degradation = DegradationConfig(
        enabled=True,
        cycle_life_full_dod=5000,
        calendar_life_years=28.0
    )

    # ========================================================================
    # HOURLY RESOLUTION (PT60M)
    # ========================================================================
    timestamps_h, spot_prices_h, pv_production_h, load_h = load_data_at_resolution(
        year=year,
        resolution='PT60M'
    )

    data_hourly = run_weekly_sequential_optimization(
        timestamps=timestamps_h,
        spot_prices=spot_prices_h,
        pv_production=pv_production_h,
        load=load_h,
        battery_kwh=battery_kwh,
        battery_kw=battery_kw,
        resolution='PT60M',
        config=config
    )

    if data_hourly is None:
        print("\n❌ Hourly optimization failed")
        return 1

    # ========================================================================
    # 15-MINUTE RESOLUTION (PT15M)
    # ========================================================================
    timestamps_15, spot_prices_15, pv_production_15, load_15 = load_data_at_resolution(
        year=year,
        resolution='PT15M'
    )

    data_15min = run_weekly_sequential_optimization(
        timestamps=timestamps_15,
        spot_prices=spot_prices_15,
        pv_production=pv_production_15,
        load=load_15,
        battery_kwh=battery_kwh,
        battery_kw=battery_kw,
        resolution='PT15M',
        config=config
    )

    if data_15min is None:
        print("\n❌ 15-minute optimization failed")
        return 1

    # ========================================================================
    # CREATE VISUALIZATIONS
    # ========================================================================
    print("\n" + "="*70)
    print("CREATING COMPARISON VISUALIZATIONS")
    print("="*70)

    create_comparison_visualizations(
        data_hourly=data_hourly,
        data_15min=data_15min,
        timestamps_hourly=timestamps_h,
        timestamps_15min=timestamps_15,
        battery_kwh=battery_kwh,
        battery_kw=battery_kw,
        year=year
    )

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "="*70)
    print("RESOLUTION COMPARISON SUMMARY")
    print("="*70)

    print(f"\nConfiguration:")
    print(f"  Battery: {battery_kwh} kWh / {battery_kw} kW")
    print(f"  Year: {year}")
    print(f"  Optimization: Weekly sequential (168-hour horizon)")

    print(f"\nHourly (PT60M):")
    print(f"  Weeks optimized: {data_hourly['num_weeks']}")
    print(f"  Annual cost: {data_hourly['annual_cost']:,.0f} NOK")
    print(f"  Avg solve time: {data_hourly['avg_solve_time']:.3f} s/week")

    print(f"\n15-Minute (PT15M):")
    print(f"  Weeks optimized: {data_15min['num_weeks']}")
    print(f"  Annual cost: {data_15min['annual_cost']:,.0f} NOK")
    print(f"  Avg solve time: {data_15min['avg_solve_time']:.3f} s/week")

    cost_diff = data_15min['annual_cost'] - data_hourly['annual_cost']
    cost_diff_pct = (cost_diff / data_hourly['annual_cost']) * 100
    speedup_ratio = data_15min['avg_solve_time'] / data_hourly['avg_solve_time']

    print(f"\nDifferences:")
    print(f"  Cost difference: {cost_diff:+,.0f} NOK ({cost_diff_pct:+.2f}%)")
    print(f"  Solve time ratio: {speedup_ratio:.2f}× (PT15M / PT60M)")

    print("\n" + "="*70)
    print("✓ RESOLUTION COMPARISON COMPLETED")
    print("="*70)
    print("\nOutput files in 'results/figures/':")
    print(f"  - resolution_comparison_overview_year{year}.png")
    print(f"  - resolution_comparison_detail_year{year}.png")
    print(f"  - resolution_comparison_metrics_year{year}.png")

    return 0


if __name__ == "__main__":
    sys.exit(main())
