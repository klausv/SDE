"""
Compare 15-minute vs 60-minute resolution for October 2025.
Sequential daily optimization with 24-hour horizon.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from src.operational.state_manager import BatterySystemState, calculate_average_power_tariff_rate
from config import BatteryOptimizationConfig


def generate_october_prices(resolution: str = 'PT60M') -> pd.DataFrame:
    """Generate realistic October 2025 price data."""

    start_date = datetime(2025, 10, 1, 0, 0)
    end_date = datetime(2025, 10, 31, 23, 59)

    freq = '15min' if resolution == 'PT15M' else 'h'
    timestamps = pd.date_range(start=start_date, end=end_date, freq=freq)

    prices = []
    for ts in timestamps:
        hour = ts.hour
        weekday = ts.weekday()

        # Daily pattern (EUR/MWh)
        if 0 <= hour < 6:
            base_price = 35
        elif 6 <= hour < 9:
            base_price = 65
        elif 9 <= hour < 16:
            base_price = 55
        elif 16 <= hour < 20:
            base_price = 70
        else:
            base_price = 45

        # Weekend discount
        if weekday >= 5:
            base_price *= 0.85

        # October factor
        seasonal_factor = 1.05

        # Volatility
        volatility = np.random.normal(1.0, 0.12)

        price_eur_mwh = base_price * seasonal_factor * volatility
        price_nok_kwh = (price_eur_mwh * 11.5) / 1000

        prices.append(max(0.1, price_nok_kwh))

    return pd.DataFrame({
        'timestamp': timestamps,
        'price_nok_per_kwh': prices
    })


def run_monthly_simulation(resolution: str, battery_kw: float = 30.0, battery_kwh: float = 30.0):
    """
    Run full October month with sequential daily optimizations.

    Args:
        resolution: 'PT60M' or 'PT15M'
        battery_kw: Battery power [kW]
        battery_kwh: Battery capacity [kWh]
    """

    print(f"\n{'='*70}")
    print(f"October 2025 Simulation - {resolution}")
    print(f"{'='*70}")

    # Generate price data
    print(f"Generating price data ({resolution})...")
    price_data = generate_october_prices(resolution)
    print(f"  {len(price_data)} timesteps")

    # Configuration
    config = BatteryOptimizationConfig()

    # Optimizer with 24-hour horizon
    optimizer = RollingHorizonOptimizer(
        config=config,
        battery_kwh=battery_kwh,
        battery_kw=battery_kw,
        horizon_hours=24,
        resolution=resolution
    )

    # Initialize state
    sim_start = datetime(2025, 10, 1, 0, 0)
    month_start = datetime(2025, 10, 1, 0, 0)

    state = BatterySystemState(
        current_soc_kwh=battery_kwh * 0.5,
        battery_capacity_kwh=battery_kwh,
        current_monthly_peak_kw=0.0,
        power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(config.tariff),
        last_update=sim_start,
        month_start_date=month_start
    )

    # Data arrays
    timestamps = pd.to_datetime(price_data['timestamp'].values)
    prices = price_data['price_nok_per_kwh'].values

    # Constant load: 20 kW
    load = np.full(len(timestamps), 20.0)

    # No PV for simplicity
    pv = np.zeros(len(timestamps))

    # Timestep info
    timestep_hours = 1.0 if resolution == 'PT60M' else 0.25
    timesteps_per_day = int(24 / timestep_hours)

    # Results storage
    results = {
        'timestamp': [],
        'soc_kwh': [],
        'battery_power_kw': [],
        'grid_import_kw': [],
        'spot_price': []
    }

    total_energy_cost = 0.0
    peak_demand = 0.0

    # Run optimization every 24 hours
    current_idx = 0
    day = 1

    print(f"\nRunning sequential optimizations (update every 24h)...")

    while current_idx < len(timestamps) - timesteps_per_day:
        # Get 24-hour window
        end_idx = current_idx + timesteps_per_day

        window_ts = timestamps[current_idx:end_idx]
        window_prices = prices[current_idx:end_idx]
        window_load = load[current_idx:end_idx]
        window_pv = pv[current_idx:end_idx]

        # Optimize
        result = optimizer.optimize_window(
            current_state=state,
            pv_production=window_pv,
            load_consumption=window_load,
            spot_prices=window_prices,
            timestamps=window_ts,
            verbose=False
        )

        if not result.success:
            print(f"  Day {day}: Optimization failed!")
            current_idx += timesteps_per_day
            day += 1
            continue

        # Store results for this 24h window
        for i in range(len(result.P_charge)):
            results['timestamp'].append(window_ts[i])
            results['soc_kwh'].append(result.E_battery[i])
            battery_power = result.P_charge[i] - result.P_discharge[i]
            results['battery_power_kw'].append(battery_power)
            results['grid_import_kw'].append(result.P_grid_import[i])
            results['spot_price'].append(window_prices[i])

        # Update metrics
        total_energy_cost += result.energy_cost
        peak_demand = max(peak_demand, result.P_grid_import.max())

        # Update state for next day
        state.current_soc_kwh = result.E_battery[-1]
        state.current_monthly_peak_kw = peak_demand
        state.last_update = window_ts[-1]

        if day % 5 == 0:
            print(f"  Day {day}/31 complete")

        current_idx += timesteps_per_day
        day += 1

    # Calculate final metrics
    results_df = pd.DataFrame(results)

    tariff_cost = config.tariff.get_power_cost(peak_demand)

    total_charge = results_df[results_df['battery_power_kw'] > 0]['battery_power_kw'].sum() * timestep_hours
    total_discharge = abs(results_df[results_df['battery_power_kw'] < 0]['battery_power_kw'].sum()) * timestep_hours
    cycles = total_discharge / battery_kwh

    print(f"\n  ✓ Month complete!")
    print(f"  Energy cost: {total_energy_cost:,.2f} NOK")
    print(f"  Peak demand: {peak_demand:.2f} kW")
    print(f"  Power tariff: {tariff_cost:.2f} NOK/month")
    print(f"  Battery cycles: {cycles:.2f}")
    print(f"  Optimizations: {day-1}")

    return {
        'resolution': resolution,
        'results_df': results_df,
        'energy_cost': total_energy_cost,
        'peak_demand': peak_demand,
        'tariff_cost': tariff_cost,
        'cycles': cycles,
        'optimizations': day-1
    }


def compare_and_plot(metrics_60, metrics_15):
    """Compare results and create plots."""

    print(f"\n{'='*70}")
    print(f"COMPARISON RESULTS")
    print(f"{'='*70}")

    # Energy cost comparison
    energy_diff = metrics_15['energy_cost'] - metrics_60['energy_cost']
    energy_pct = (energy_diff / metrics_60['energy_cost']) * 100

    print(f"\n💰 Energy Cost:")
    print(f"  60-min: {metrics_60['energy_cost']:,.2f} NOK")
    print(f"  15-min: {metrics_15['energy_cost']:,.2f} NOK")
    print(f"  Difference: {energy_diff:+,.2f} NOK ({energy_pct:+.2f}%)")

    # Peak demand
    peak_diff = metrics_15['peak_demand'] - metrics_60['peak_demand']
    peak_pct = (peak_diff / metrics_60['peak_demand']) * 100

    print(f"\n⚡ Peak Demand:")
    print(f"  60-min: {metrics_60['peak_demand']:.2f} kW")
    print(f"  15-min: {metrics_15['peak_demand']:.2f} kW")
    print(f"  Difference: {peak_diff:+.2f} kW ({peak_pct:+.2f}%)")

    # Power tariff
    tariff_diff = metrics_15['tariff_cost'] - metrics_60['tariff_cost']

    print(f"\n🔌 Power Tariff:")
    print(f"  60-min: {metrics_60['tariff_cost']:.2f} NOK/month")
    print(f"  15-min: {metrics_15['tariff_cost']:.2f} NOK/month")
    print(f"  Difference: {tariff_diff:+.2f} NOK")

    # Battery utilization
    cycles_diff = metrics_15['cycles'] - metrics_60['cycles']

    print(f"\n🔋 Battery Cycles:")
    print(f"  60-min: {metrics_60['cycles']:.2f} full cycles")
    print(f"  15-min: {metrics_15['cycles']:.2f} full cycles")
    print(f"  Difference: {cycles_diff:+.2f}")

    # Total savings
    total_diff = energy_diff + tariff_diff

    print(f"\n💵 Total Monthly Impact (15-min vs 60-min):")
    print(f"  {total_diff:+,.2f} NOK/month")
    print(f"  {total_diff * 12:+,.2f} NOK/year")

    # Create plots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('15-min vs 60-min Resolution - October 2025 (30 kW/30 kWh)',
                 fontsize=14, fontweight='bold')

    df_60 = metrics_60['results_df']
    df_15 = metrics_15['results_df']

    # Plot 1: SOC comparison (first week)
    ax = axes[0, 0]
    days = 7
    hours_60 = days * 24
    hours_15 = days * 24 * 4

    ax.plot(df_60['timestamp'][:hours_60], df_60['soc_kwh'][:hours_60],
            label='60-min', linewidth=2)
    ax.plot(df_15['timestamp'][:hours_15], df_15['soc_kwh'][:hours_15],
            label='15-min', linewidth=1.5, alpha=0.8)
    ax.set_ylabel('SOC [kWh]')
    ax.set_title('Battery State of Charge (First Week)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 2: Battery power (first 3 days)
    ax = axes[0, 1]
    hours_60 = 3 * 24
    hours_15 = 3 * 24 * 4

    ax.plot(df_60['timestamp'][:hours_60], df_60['battery_power_kw'][:hours_60],
            label='60-min', linewidth=2)
    ax.plot(df_15['timestamp'][:hours_15], df_15['battery_power_kw'][:hours_15],
            label='15-min', linewidth=1.5, alpha=0.8)
    ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5)
    ax.set_ylabel('Battery Power [kW]')
    ax.set_title('Charging Strategy (First 3 Days)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 3: Grid import (first 3 days)
    ax = axes[1, 0]
    ax.plot(df_60['timestamp'][:hours_60], df_60['grid_import_kw'][:hours_60],
            label='60-min', linewidth=2)
    ax.plot(df_15['timestamp'][:hours_15], df_15['grid_import_kw'][:hours_15],
            label='15-min', linewidth=1.5, alpha=0.8)
    ax.set_ylabel('Grid Import [kW]')
    ax.set_title('Grid Import Power (First 3 Days)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 4: Summary metrics
    ax = axes[1, 1]
    categories = ['Energy\nCost', 'Peak\nDemand\n(kW)', 'Tariff\nCost', 'Battery\nCycles']
    values_60 = [metrics_60['energy_cost']/100, metrics_60['peak_demand'],
                 metrics_60['tariff_cost']/10, metrics_60['cycles']*100]
    values_15 = [metrics_15['energy_cost']/100, metrics_15['peak_demand'],
                 metrics_15['tariff_cost']/10, metrics_15['cycles']*100]

    x = np.arange(len(categories))
    width = 0.35

    ax.bar(x - width/2, values_60, width, label='60-min', alpha=0.8)
    ax.bar(x + width/2, values_15, width, label='15-min', alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.set_title('Metrics Comparison (scaled for visibility)')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    output_file = '/mnt/c/users/klaus/klauspython/SDE/battery_optimization/results/resolution_comparison_oct2025.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n📊 Plot saved: {output_file}")
    plt.close()


def main():
    print("\n" + "="*70)
    print("RESOLUTION COMPARISON: 15-min vs 60-min")
    print("="*70)
    print("Period: October 2025 (full month)")
    print("Battery: 30 kW / 30 kWh")
    print("Horizon: 24 hours (sequential daily updates)")
    print("="*70)

    # Run 60-minute simulation
    print("\n[1/3] Running 60-minute resolution...")
    metrics_60 = run_monthly_simulation(resolution='PT60M', battery_kw=30.0, battery_kwh=30.0)

    # Run 15-minute simulation
    print("\n[2/3] Running 15-minute resolution...")
    metrics_15 = run_monthly_simulation(resolution='PT15M', battery_kw=30.0, battery_kwh=30.0)

    # Compare and plot
    print("\n[3/3] Comparing results...")
    compare_and_plot(metrics_60, metrics_15)

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)


if __name__ == '__main__':
    main()
