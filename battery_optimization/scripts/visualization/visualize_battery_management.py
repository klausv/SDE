"""
Visualize battery management with realistic LFP degradation model.

Creates comprehensive plots showing:
- Battery SOC and charge/discharge behavior
- Spot prices and solar production
- Degradation accumulation over time
- Economic performance metrics

Uses RollingHorizonOptimizer with weekly sequential optimization (52 weeks).
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for WSL
import matplotlib.pyplot as plt
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path (2 levels up from this script)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config import BatteryOptimizationConfig, DegradationConfig
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from core.price_fetcher import ENTSOEPriceFetcher
from core.pvgis_solar import PVGISProduction
from operational import BatterySystemState, calculate_average_power_tariff_rate


def load_real_data(year=2024, resolution='PT60M'):
    """Load real spot prices and solar production data for full year"""

    # Load spot prices
    fetcher = ENTSOEPriceFetcher(resolution=resolution)
    prices_series = fetcher.fetch_prices(year=year, area='NO2', resolution=resolution)
    prices_df = prices_series.to_frame('price_nok_per_kwh')

    timestamps = prices_df.index
    spot_prices = prices_df['price_nok_per_kwh'].values

    # Load solar production
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

    # Match timestamps (handle different resolutions)
    pv_production = np.zeros(len(timestamps))
    for i, ts in enumerate(timestamps):
        matching = pvgis_data[
            (pvgis_data.index.month == ts.month) &
            (pvgis_data.index.day == ts.day) &
            (pvgis_data.index.hour == ts.hour)
        ]
        if len(matching) > 0:
            pv_production[i] = matching['pv_power_kw'].values[0]

    return timestamps, spot_prices, pv_production


def create_synthetic_load(timestamps, annual_kwh=300000):
    """Create realistic commercial load profile"""
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

    return load


def run_and_visualize(battery_kwh=100, battery_kw=50, year=2024, resolution='PT60M',
                      visualize_weeks=[0, 1, 2]):
    """
    Run weekly sequential optimization and create comprehensive visualizations.

    Args:
        battery_kwh: Battery capacity [kWh]
        battery_kw: Battery power rating [kW]
        year: Year for analysis
        resolution: Time resolution ('PT60M' or 'PT15M')
        visualize_weeks: List of week indices to visualize in detail (0-51)
    """

    print(f"\n{'='*70}")
    print(f"BATTERY MANAGEMENT VISUALIZATION - Full Year {year}")
    print(f"{'='*70}")
    print(f"Battery: {battery_kwh} kWh, {battery_kw} kW")
    print(f"Resolution: {resolution}")
    print(f"Strategy: Weekly Sequential Optimization (52 weeks)")
    print()

    # Create config with degradation
    config = BatteryOptimizationConfig()
    config.battery.degradation = DegradationConfig(
        enabled=True,
        cycle_life_full_dod=5000,
        calendar_life_years=28.0
    )

    # Load full year data
    print("Loading data...")
    timestamps, spot_prices, pv_production = load_real_data(year=year, resolution=resolution)
    load = create_synthetic_load(timestamps, annual_kwh=300000)

    n_timesteps = len(timestamps)
    print(f"  Loaded {n_timesteps} timesteps")

    # Calculate weekly timesteps based on resolution
    if resolution == 'PT60M':
        weekly_timesteps = 168  # 7 days @ hourly
    elif resolution == 'PT15M':
        weekly_timesteps = 672  # 7 days @ 15-min
    else:
        raise ValueError(f"Unsupported resolution: {resolution}")

    print(f"  Weekly timesteps: {weekly_timesteps}")

    # Initialize optimizer
    optimizer = RollingHorizonOptimizer(
        config=config,
        battery_kwh=battery_kwh,
        battery_kw=battery_kw,
        horizon_hours=168  # Weekly optimization (7 days)
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
        'weekly_degradation_costs': []
    }

    # Run weekly sequential optimization
    print("\nRunning weekly sequential optimization...")
    prev_month = timestamps[0].month if n_timesteps > 0 else 1

    for week in range(52):
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
        result = optimizer.optimize_window(
            current_state=state,
            pv_production=pv_production[t_start:t_end],
            load_consumption=load[t_start:t_end],
            spot_prices=spot_prices[t_start:t_end],
            timestamps=timestamps[t_start:t_end],
            verbose=False
        )

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

        # Update state for next week
        state.update_from_measurement(
            timestamp=timestamps[t_end - 1],
            soc_kwh=result.E_battery_final,
            grid_import_power_kw=result.P_grid_import[-1] if len(result.P_grid_import) > 0 else 0.0
        )

        if week % 10 == 0:
            print(f"  Week {week}/52 complete - Cost: {result.objective_value:.2f} NOK")

    # Convert to numpy arrays
    for key in ['P_charge', 'P_discharge', 'P_grid_import', 'P_grid_export',
                'E_battery', 'P_curtail', 'DP_cyc', 'DP_total']:
        full_results[key] = np.array(full_results[key])

    # Create aggregate result object (for compatibility with old visualization code)
    class AggregateResult:
        def __init__(self, results_dict, battery_kwh):
            self.P_charge = results_dict['P_charge']
            self.P_discharge = results_dict['P_discharge']
            self.P_grid_import = results_dict['P_grid_import']
            self.P_grid_export = results_dict['P_grid_export']
            self.E_battery = results_dict['E_battery']
            self.P_curtail = results_dict['P_curtail']
            self.DP_cyc = results_dict['DP_cyc']
            self.DP_total = results_dict['DP_total']
            self.DP_cal = results_dict['DP_total'][0] - results_dict['DP_cyc'][0]  # Approximate
            self.E_battery_final = results_dict['E_battery'][-1]
            self.P_peak = np.max(results_dict['P_grid_import'])

            # Annual aggregates
            self.objective_value = sum(results_dict['weekly_costs'])
            self.energy_cost = sum(results_dict['weekly_energy_costs'])
            self.power_cost = sum(results_dict['weekly_power_costs'])
            self.degradation_cost = sum(results_dict['weekly_degradation_costs'])

            self.success = True
            self.message = "Weekly sequential optimization completed"

    result = AggregateResult(full_results, battery_kwh)

    print(f"\n✓ Annual optimization complete")
    print(f"  Total cost: {result.objective_value:,.0f} NOK")
    print(f"  Energy cost: {result.energy_cost:,.0f} NOK")
    print(f"  Power cost: {result.power_cost:,.0f} NOK")
    print(f"  Degradation cost: {result.degradation_cost:,.0f} NOK")

    # Trim timestamps and data to match length (handle incomplete final week)
    actual_length = len(result.E_battery)
    timestamps_plot = timestamps[:actual_length]
    spot_prices_plot = spot_prices[:actual_length]
    pv_production_plot = pv_production[:actual_length]
    load_plot = load[:actual_length]

    # Create visualizations
    fig = plt.figure(figsize=(20, 12))

    # 1. Battery SOC and charge/discharge power
    ax1 = plt.subplot(4, 1, 1)
    ax1_twin = ax1.twinx()

    # SOC
    soc_pct = (result.E_battery / battery_kwh) * 100
    ax1.plot(timestamps_plot, soc_pct, 'b-', linewidth=1.5, label='Battery SOC', alpha=0.8)
    ax1.axhline(y=20, color='r', linestyle='--', alpha=0.5, label='Min SOC (20%)')
    ax1.axhline(y=80, color='g', linestyle='--', alpha=0.5, label='Max SOC (80%)')
    ax1.set_ylabel('State of Charge (%)', fontsize=12, color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.set_ylim([0, 100])
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')

    # Charge/discharge power (use simplified visualization for full year)
    net_power = result.P_charge - result.P_discharge
    # For full year, use line plot instead of bars
    ax1_twin.fill_between(timestamps_plot, 0, net_power, where=(net_power>0),
                           color='green', alpha=0.3, label='Charge')
    ax1_twin.fill_between(timestamps_plot, 0, net_power, where=(net_power<0),
                           color='red', alpha=0.3, label='Discharge')
    ax1_twin.set_ylabel('Battery Power (kW)\nGreen=Charge, Red=Discharge', fontsize=12)
    ax1_twin.set_ylim([-battery_kw*1.1, battery_kw*1.1])
    ax1_twin.legend(loc='upper right')

    ax1.set_title(f'Battery Management - {battery_kwh} kWh / {battery_kw} kW (Full Year {year})',
                  fontsize=14, fontweight='bold')

    # 2. Spot prices
    ax2 = plt.subplot(4, 1, 2, sharex=ax1)
    ax2.fill_between(timestamps_plot, spot_prices_plot, alpha=0.4, color='orange', label='Spot Price')
    ax2.plot(timestamps_plot, spot_prices_plot, 'orange', linewidth=0.8, alpha=0.7)
    ax2.set_ylabel('Spot Price (NOK/kWh)', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right')
    ax2.set_title('Electricity Spot Prices (NO2)', fontsize=12, fontweight='bold')

    # 3. Solar production and load
    ax3 = plt.subplot(4, 1, 3, sharex=ax1)
    ax3.fill_between(timestamps_plot, pv_production_plot, alpha=0.3, color='gold', label='PV Production')
    ax3.plot(timestamps_plot, pv_production_plot, 'gold', linewidth=0.8, alpha=0.7)
    ax3.plot(timestamps_plot, load_plot, 'navy', linewidth=0.8, alpha=0.7, label='Load Consumption')
    ax3.set_ylabel('Power (kW)', fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc='upper right')
    ax3.set_title('Solar Production and Load Profile', fontsize=12, fontweight='bold')

    # 4. Degradation accumulation
    ax4 = plt.subplot(4, 1, 4, sharex=ax1)

    if result.DP_total is not None and len(result.DP_total) > 0:
        cumulative_deg = np.cumsum(result.DP_total)
        cyclic_cum = np.cumsum(result.DP_cyc)
        # Estimate calendar degradation (approximate from first timestep)
        calendar_rate = result.DP_cal if hasattr(result, 'DP_cal') else 0.0
        calendar_cum = calendar_rate * np.arange(1, len(timestamps_plot) + 1)

        ax4.plot(timestamps_plot, cumulative_deg, 'r-', linewidth=2, label='Total Degradation')
        ax4.plot(timestamps_plot, cyclic_cum, 'orange', linewidth=1.5, linestyle='--',
                label='Cyclic Degradation')
        ax4.plot(timestamps_plot, calendar_cum, 'gray', linewidth=1.5, linestyle=':',
                label='Calendar Degradation (est.)')

        ax4.set_ylabel('Cumulative Degradation (%)', fontsize=12)
        ax4.grid(True, alpha=0.3)
        ax4.legend(loc='upper left')
        ax4.set_title('Battery Degradation Accumulation (LFP Model)', fontsize=12, fontweight='bold')

    ax4.set_xlabel('Date', fontsize=12)

    plt.tight_layout()

    # Save figure
    output_file = Path(__file__).parent / 'results' / 'figures' / f'battery_management_year{year}.png'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved visualization: {output_file}")

    # Create summary metrics figure
    fig2, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Cost breakdown - handle negative energy cost (from exports)
    ax_cost = axes[0, 0]

    if result.energy_cost < 0:
        # Revenue from exports - show as separate bar chart
        ax_cost.axis('off')
        costs_text = f"""
        COST/REVENUE BREAKDOWN
        {'─'*30}

        Energy Revenue:  {-result.energy_cost:>8,.0f} NOK
        Power Tariff:    {result.power_cost:>8,.0f} NOK
        Degradation:     {result.degradation_cost:>8,.0f} NOK
        {'─'*30}
        Net Cost:        {result.objective_value:>8,.0f} NOK

        (Positive solar exports
         exceed grid imports)
        """
        ax_cost.text(0.5, 0.5, costs_text, fontsize=10, family='monospace',
                    verticalalignment='center', horizontalalignment='center',
                    transform=ax_cost.transAxes)
    else:
        # Normal positive costs - show pie chart
        costs = [result.energy_cost, result.power_cost, result.degradation_cost]
        labels = ['Energy Cost', 'Power Tariff', 'Degradation Cost']
        colors_pie = ['#ff9999', '#66b3ff', '#99ff99']
        ax_cost.pie(costs, labels=labels, autopct='%1.1f%%', colors=colors_pie, startangle=90)
        ax_cost.set_title('Cost Breakdown', fontsize=12, fontweight='bold')

    # Battery utilization
    ax_util = axes[0, 1]
    charge_hours = np.sum(result.P_charge > 0)
    discharge_hours = np.sum(result.P_discharge > 0)
    idle_hours = len(result.E_battery) - charge_hours - discharge_hours

    utilization = [charge_hours, discharge_hours, idle_hours]
    labels_util = ['Charging', 'Discharging', 'Idle']
    colors_util = ['green', 'red', 'gray']
    ax_util.pie(utilization, labels=labels_util, autopct='%1.1f%%', colors=colors_util, startangle=90)
    ax_util.set_title('Battery Operational Time (Full Year)', fontsize=12, fontweight='bold')

    # Degradation breakdown
    ax_deg = axes[1, 0]
    total_deg = np.sum(result.DP_total) if result.DP_total is not None and len(result.DP_total) > 0 else 0
    cyclic_deg = np.sum(result.DP_cyc) if result.DP_cyc is not None and len(result.DP_cyc) > 0 else 0
    calendar_rate = result.DP_cal if hasattr(result, 'DP_cal') else 0.0
    calendar_deg = calendar_rate * len(result.E_battery)

    deg_data = [cyclic_deg, calendar_deg]
    labels_deg = ['Cyclic', 'Calendar (est.)']
    colors_deg = ['orange', 'gray']
    ax_deg.bar(labels_deg, deg_data, color=colors_deg, alpha=0.7)
    ax_deg.set_ylabel('Degradation (%)', fontsize=12)
    ax_deg.set_title('Degradation Sources (Full Year)', fontsize=12, fontweight='bold')
    ax_deg.grid(True, alpha=0.3, axis='y')

    # Key metrics table
    ax_metrics = axes[1, 1]
    ax_metrics.axis('off')

    equiv_cycles = cyclic_deg / (20.0 / 5000) if cyclic_deg > 0 else 0
    # Already annual since we ran full year
    actual_hours = len(result.E_battery)
    timestep_hours = 1.0 if resolution == 'PT60M' else 0.25

    avg_charge_power = np.mean(result.P_charge[result.P_charge > 0]) if np.any(result.P_charge > 0) else 0
    avg_discharge_power = np.mean(result.P_discharge[result.P_discharge > 0]) if np.any(result.P_discharge > 0) else 0

    metrics_text = f"""
    ANNUAL PERFORMANCE METRICS
    {'─'*40}

    Energy Economics (Annual):
      Energy Cost:        {result.energy_cost:>10,.0f} NOK
      Power Tariff:       {result.power_cost:>10,.0f} NOK
      Degradation Cost:   {result.degradation_cost:>10,.0f} NOK
      Total Annual Cost:  {result.objective_value:>10,.0f} NOK

    Battery Performance (Full Year):
      Total Degradation:  {total_deg:>10.3f} %
      Equiv. Cycles:      {equiv_cycles:>10.1f} cycles
      Cycles per Year:    {equiv_cycles:>10.0f} cycles/yr
      Avg Charge Power:   {avg_charge_power:>10.1f} kW
      Avg Discharge Pwr:  {avg_discharge_power:>10.1f} kW

    System Operations:
      Annual Peak Power:  {result.P_peak:>10.1f} kW
      Final SOC:          {result.E_battery_final/battery_kwh*100:>10.1f} %
      Hours Charging:     {charge_hours:>10.0f} hrs
      Hours Discharging:  {discharge_hours:>10.0f} hrs
      Total Timesteps:    {actual_hours:>10,.0f}
    """

    ax_metrics.text(0.05, 0.5, metrics_text, fontsize=9, family='monospace',
                   verticalalignment='center', transform=ax_metrics.transAxes)

    plt.tight_layout()

    # Save metrics figure
    output_file2 = Path(__file__).parent / 'results' / 'figures' / f'battery_metrics_year{year}.png'
    plt.savefig(output_file2, dpi=300, bbox_inches='tight')
    print(f"✓ Saved metrics: {output_file2}")
    plt.close('all')

    return result


def main():
    """Generate battery management visualizations with weekly sequential optimization"""

    print("\n" + "="*70)
    print("BATTERY MANAGEMENT VISUALIZATION WITH LFP DEGRADATION")
    print("Weekly Sequential Optimization (52 weeks)")
    print("="*70)
    print()

    # Run for full year 2024
    result = run_and_visualize(
        battery_kwh=100,
        battery_kw=50,
        year=2024,
        resolution='PT60M',
        visualize_weeks=[0, 1, 2]  # Not used yet, reserved for future detailed week plots
    )

    if result is None:
        print("\n❌ Visualization failed")
        return 1

    print("\n" + "="*70)
    print("✓ VISUALIZATION COMPLETED")
    print("="*70)
    print("\nCheck 'results/figures/' directory for output files:")
    print("  - battery_management_year2024.png")
    print("  - battery_metrics_year2024.png")

    return 0


if __name__ == "__main__":
    sys.exit(main())
