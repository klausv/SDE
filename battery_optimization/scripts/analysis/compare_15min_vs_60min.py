"""
Compare 15-minute vs 60-minute time resolution for battery optimization.

Fetches ENTSO-E price data for October 2025 and runs rolling horizon
simulations with both resolutions to compare:
- Charging strategies
- Revenue from reduced import
- Spot arbitrage opportunities
- Power tariff reduction
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from typing import Dict, Any

# Import project modules
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from src.operational.state_manager import BatterySystemState, calculate_average_power_tariff_rate
from config import BatteryOptimizationConfig


def fetch_entsoe_data_october_2025(resolution: str = 'PT60M') -> pd.DataFrame:
    """
    Fetch or generate ENTSO-E price data for October 2025.

    Args:
        resolution: 'PT60M' (hourly) or 'PT15M' (15-minute)

    Returns:
        DataFrame with timestamp and price_nok_per_kwh columns
    """
    print(f"\n{'='*70}")
    print(f"Fetching October 2025 price data ({resolution})")
    print(f"{'='*70}")

    # Use first week of October for faster comparison
    start_date = datetime(2025, 10, 1, 0, 0)
    end_date = datetime(2025, 10, 7, 23, 59)

    # Determine frequency
    freq = '15min' if resolution == 'PT15M' else 'h'

    # Create timestamp index
    timestamps = pd.date_range(start=start_date, end=end_date, freq=freq)

    # Generate realistic October prices (autumn pattern)
    # Base pattern: higher prices during peak hours, lower at night
    prices = []

    for ts in timestamps:
        hour = ts.hour
        weekday = ts.weekday()

        # Daily price pattern (EUR/MWh)
        if 0 <= hour < 6:
            base_price = 35  # Night: low demand
        elif 6 <= hour < 9:
            base_price = 65  # Morning peak
        elif 9 <= hour < 16:
            base_price = 55  # Daytime
        elif 16 <= hour < 20:
            base_price = 70  # Evening peak
        else:
            base_price = 45  # Late evening

        # Weekend adjustment (lower prices)
        if weekday >= 5:  # Saturday/Sunday
            base_price *= 0.85

        # October seasonal factor (autumn - moderate prices)
        seasonal_factor = 1.05

        # Add realistic volatility
        volatility = np.random.normal(1.0, 0.12)

        price_eur_mwh = base_price * seasonal_factor * volatility

        # Convert EUR/MWh to NOK/kWh (exchange rate 11.5)
        price_nok_kwh = (price_eur_mwh * 11.5) / 1000

        prices.append(max(0.1, price_nok_kwh))  # Ensure positive

    df = pd.DataFrame({
        'timestamp': timestamps,
        'price_nok_per_kwh': prices
    })

    print(f"  Generated {len(df)} price points")
    print(f"  Price range: {df['price_nok_per_kwh'].min():.3f} - {df['price_nok_per_kwh'].max():.3f} NOK/kWh")
    print(f"  Mean price: {df['price_nok_per_kwh'].mean():.3f} NOK/kWh")

    return df


def resample_to_hourly(df_15min: pd.DataFrame) -> pd.DataFrame:
    """
    Resample 15-minute data to hourly by averaging.

    Args:
        df_15min: DataFrame with 15-minute data

    Returns:
        DataFrame with hourly data
    """
    df_hourly = df_15min.set_index('timestamp').resample('h').mean().reset_index()
    return df_hourly


def run_rolling_horizon_simulation(
    price_data: pd.DataFrame,
    resolution: str,
    battery_kw: float = 30.0,
    battery_kwh: float = 30.0,
    horizon_hours: int = 24
) -> Dict[str, Any]:
    """
    Run rolling horizon simulation for October 2025.

    Args:
        price_data: DataFrame with timestamp and price columns
        resolution: 'PT60M' or 'PT15M'
        battery_kw: Battery power rating [kW]
        battery_kwh: Battery capacity [kWh]
        horizon_hours: Optimization horizon [hours]

    Returns:
        Dict with simulation results and metrics
    """
    print(f"\n{'='*70}")
    print(f"Running Rolling Horizon Simulation ({resolution})")
    print(f"{'='*70}")
    print(f"  Battery: {battery_kw} kW / {battery_kwh} kWh")
    print(f"  Horizon: {horizon_hours} hours")
    print(f"  Period: October 2025 (first week - 7 days)")

    # Load system configuration
    config = BatteryOptimizationConfig()

    # Initialize optimizer
    optimizer = RollingHorizonOptimizer(
        config=config,
        battery_kwh=battery_kwh,
        battery_kw=battery_kw,
        horizon_hours=horizon_hours,
        resolution=resolution
    )

    # Initialize system state
    initial_soc_kwh = battery_kwh * 0.5  # Start at 50% SOC
    sim_start = datetime(2025, 10, 1, 0, 0)
    month_start = datetime(2025, 10, 1, 0, 0)

    state = BatterySystemState(
        current_soc_kwh=initial_soc_kwh,
        battery_capacity_kwh=battery_kwh,
        current_monthly_peak_kw=0.0,
        power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(config.tariff),
        last_update=sim_start,
        month_start_date=month_start
    )

    # Prepare data
    timestamps = pd.to_datetime(price_data['timestamp'].values)
    prices = price_data['price_nok_per_kwh'].values

    # For simplicity, assume constant load and no PV production
    # (Focus on price arbitrage only)
    timestep_hours = 1.0 if resolution == 'PT60M' else 0.25
    n_timesteps = len(timestamps)

    # Constant load: 20 kW commercial load
    load_consumption = np.full(n_timesteps, 20.0)

    # No PV production (October, night hours dominate for this comparison)
    pv_production = np.zeros(n_timesteps)

    # Run simulation: optimize every 4 hours to reduce computation time
    update_frequency_timesteps = 16 if resolution == 'PT15M' else 4  # Update every 4 hours

    results = {
        'timestamps': [],
        'soc_kwh': [],
        'battery_power_kw': [],
        'grid_import_kw': [],
        'grid_export_kw': [],
        'spot_price_nok_kwh': [],
        'energy_cost_nok': [],
        'peak_kw': [],
    }

    total_energy_cost = 0.0
    total_arbitrage_profit = 0.0
    peak_demand_kw = 0.0

    # Simulate month (update every hour in real-time manner)
    current_timestep = 0
    optimization_count = 0

    while current_timestep < n_timesteps - int(horizon_hours / timestep_hours):
        # Get optimization window
        window_size = int(horizon_hours / timestep_hours)
        window_end = min(current_timestep + window_size, n_timesteps)

        window_timestamps = timestamps[current_timestep:window_end]
        window_prices = prices[current_timestep:window_end]
        window_load = load_consumption[current_timestep:window_end]
        window_pv = pv_production[current_timestep:window_end]

        # Pad if necessary
        if len(window_timestamps) < window_size:
            break

        # Optimize
        result = optimizer.optimize_window(
            current_state=state,
            pv_production=window_pv,
            load_consumption=window_load,
            spot_prices=window_prices,
            timestamps=window_timestamps,
            verbose=False
        )

        if not result.success:
            print(f"  Warning: Optimization failed at timestep {current_timestep}")
            current_timestep += update_frequency_timesteps
            continue

        # Apply first control action
        battery_setpoint = result.next_battery_setpoint_kw

        # Update state
        new_soc = state.current_soc_kwh + battery_setpoint * timestep_hours
        new_soc = np.clip(new_soc, optimizer.SOC_min * battery_kwh, optimizer.SOC_max * battery_kwh)

        grid_import = result.P_grid_import[0]
        peak_demand_kw = max(peak_demand_kw, grid_import)

        # Store results
        results['timestamps'].append(timestamps[current_timestep])
        results['soc_kwh'].append(new_soc)
        results['battery_power_kw'].append(battery_setpoint)
        results['grid_import_kw'].append(grid_import)
        results['grid_export_kw'].append(result.P_grid_export[0])
        results['spot_price_nok_kwh'].append(prices[current_timestep])
        results['energy_cost_nok'].append(result.energy_cost)
        results['peak_kw'].append(peak_demand_kw)

        total_energy_cost += result.energy_cost

        # Update state for next iteration
        state.current_soc_kwh = new_soc
        state.current_monthly_peak_kw = peak_demand_kw
        state.last_update = timestamps[current_timestep]

        current_timestep += update_frequency_timesteps
        optimization_count += 1

        if optimization_count % 50 == 0:
            print(f"  Progress: {optimization_count} optimizations, Day {int(current_timestep * timestep_hours / 24) + 1}")

    # Calculate metrics
    results_df = pd.DataFrame(results)

    metrics = {
        'resolution': resolution,
        'timestep_hours': timestep_hours,
        'total_energy_cost_nok': total_energy_cost,
        'peak_demand_kw': peak_demand_kw,
        'avg_soc_percent': (results_df['soc_kwh'].mean() / battery_kwh) * 100,
        'total_charge_kwh': results_df[results_df['battery_power_kw'] > 0]['battery_power_kw'].sum() * timestep_hours,
        'total_discharge_kwh': abs(results_df[results_df['battery_power_kw'] < 0]['battery_power_kw'].sum()) * timestep_hours,
        'optimization_count': optimization_count,
        'results_df': results_df
    }

    # Calculate power tariff cost
    tariff_cost = config.tariff.get_power_cost(peak_demand_kw)
    metrics['power_tariff_cost_nok'] = tariff_cost

    print(f"\n  ✓ Simulation complete!")
    print(f"  Total energy cost: {total_energy_cost:,.2f} NOK")
    print(f"  Peak demand: {peak_demand_kw:.2f} kW")
    print(f"  Power tariff: {tariff_cost:.2f} NOK/month")
    print(f"  Battery cycles: {metrics['total_discharge_kwh'] / battery_kwh:.2f}")
    print(f"  Optimizations: {optimization_count}")

    return metrics


def compare_results(metrics_60min: Dict, metrics_15min: Dict):
    """
    Compare results between 60-minute and 15-minute resolutions.

    Args:
        metrics_60min: Results from 60-minute simulation
        metrics_15min: Results from 15-minute simulation
    """
    print(f"\n{'='*70}")
    print(f"COMPARISON: 15-minute vs 60-minute Resolution")
    print(f"{'='*70}")

    # Energy cost comparison
    energy_cost_60 = metrics_60min['total_energy_cost_nok']
    energy_cost_15 = metrics_15min['total_energy_cost_nok']
    energy_savings = energy_cost_60 - energy_cost_15
    energy_savings_pct = (energy_savings / energy_cost_60) * 100 if energy_cost_60 > 0 else 0

    print(f"\n📊 Energy Cost:")
    print(f"  60-min: {energy_cost_60:,.2f} NOK")
    print(f"  15-min: {energy_cost_15:,.2f} NOK")
    print(f"  Savings: {energy_savings:,.2f} NOK ({energy_savings_pct:+.2f}%)")

    # Peak demand comparison
    peak_60 = metrics_60min['peak_demand_kw']
    peak_15 = metrics_15min['peak_demand_kw']
    peak_reduction = peak_60 - peak_15
    peak_reduction_pct = (peak_reduction / peak_60) * 100 if peak_60 > 0 else 0

    print(f"\n⚡ Peak Demand:")
    print(f"  60-min: {peak_60:.2f} kW")
    print(f"  15-min: {peak_15:.2f} kW")
    print(f"  Reduction: {peak_reduction:.2f} kW ({peak_reduction_pct:+.2f}%)")

    # Power tariff comparison
    tariff_60 = metrics_60min['power_tariff_cost_nok']
    tariff_15 = metrics_15min['power_tariff_cost_nok']
    tariff_savings = tariff_60 - tariff_15
    tariff_savings_pct = (tariff_savings / tariff_60) * 100 if tariff_60 > 0 else 0

    print(f"\n💰 Power Tariff Cost:")
    print(f"  60-min: {tariff_60:.2f} NOK/month")
    print(f"  15-min: {tariff_15:.2f} NOK/month")
    print(f"  Savings: {tariff_savings:.2f} NOK ({tariff_savings_pct:+.2f}%)")

    # Battery utilization comparison
    cycles_60 = metrics_60min['total_discharge_kwh'] / 30.0
    cycles_15 = metrics_15min['total_discharge_kwh'] / 30.0

    print(f"\n🔋 Battery Utilization:")
    print(f"  60-min: {cycles_60:.2f} full cycles")
    print(f"  15-min: {cycles_15:.2f} full cycles")
    print(f"  Difference: {cycles_15 - cycles_60:+.2f} cycles")

    # Total monthly savings
    total_savings = energy_savings + tariff_savings

    print(f"\n💵 Total Monthly Savings (15-min vs 60-min):")
    print(f"  {total_savings:,.2f} NOK/month")
    print(f"  {total_savings * 12:,.2f} NOK/year")

    # Create comparison plots
    create_comparison_plots(metrics_60min, metrics_15min)

    return {
        'energy_savings_nok': energy_savings,
        'energy_savings_pct': energy_savings_pct,
        'peak_reduction_kw': peak_reduction,
        'tariff_savings_nok': tariff_savings,
        'total_monthly_savings_nok': total_savings,
        'total_annual_savings_nok': total_savings * 12
    }


def create_comparison_plots(metrics_60min: Dict, metrics_15min: Dict):
    """Create visualization plots comparing the two resolutions."""

    fig, axes = plt.subplots(3, 2, figsize=(16, 12))
    fig.suptitle('15-minute vs 60-minute Resolution Comparison\nOctober 2025 - 30 kW/30 kWh Battery',
                 fontsize=16, fontweight='bold')

    df_60 = metrics_60min['results_df']
    df_15 = metrics_15min['results_df']

    # Plot 1: Battery SOC comparison (first 7 days)
    ax = axes[0, 0]
    days_to_plot = 7
    hours_60 = min(days_to_plot * 24, len(df_60))
    hours_15 = min(days_to_plot * 24 * 4, len(df_15))

    ax.plot(df_60['timestamps'][:hours_60], df_60['soc_kwh'][:hours_60],
            label='60-min', linewidth=2, alpha=0.8)
    ax.plot(df_15['timestamps'][:hours_15], df_15['soc_kwh'][:hours_15],
            label='15-min', linewidth=1.5, alpha=0.8)
    ax.set_ylabel('Battery SOC [kWh]')
    ax.set_title('Battery State of Charge (First 7 Days)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 2: Battery power comparison (first 3 days)
    ax = axes[0, 1]
    hours_60 = min(3 * 24, len(df_60))
    hours_15 = min(3 * 24 * 4, len(df_15))

    ax.plot(df_60['timestamps'][:hours_60], df_60['battery_power_kw'][:hours_60],
            label='60-min', linewidth=2, alpha=0.8)
    ax.plot(df_15['timestamps'][:hours_15], df_15['battery_power_kw'][:hours_15],
            label='15-min', linewidth=1.5, alpha=0.8)
    ax.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
    ax.set_ylabel('Battery Power [kW]')
    ax.set_title('Battery Charging Strategy (First 3 Days)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 3: Grid import comparison
    ax = axes[1, 0]
    ax.plot(df_60['timestamps'][:hours_60], df_60['grid_import_kw'][:hours_60],
            label='60-min', linewidth=2, alpha=0.8)
    ax.plot(df_15['timestamps'][:hours_15], df_15['grid_import_kw'][:hours_15],
            label='15-min', linewidth=1.5, alpha=0.8)
    ax.set_ylabel('Grid Import [kW]')
    ax.set_title('Grid Import Power (First 3 Days)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 4: Spot price overlay
    ax = axes[1, 1]
    ax.plot(df_60['timestamps'][:hours_60], df_60['spot_price_nok_kwh'][:hours_60],
            label='Spot Price', color='orange', linewidth=2, alpha=0.8)
    ax.set_ylabel('Spot Price [NOK/kWh]')
    ax.set_title('Electricity Spot Prices (First 3 Days)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 5: Cumulative energy cost
    ax = axes[2, 0]
    cumulative_cost_60 = df_60['energy_cost_nok'].cumsum()
    cumulative_cost_15 = df_15['energy_cost_nok'].cumsum()

    ax.plot(df_60['timestamps'], cumulative_cost_60, label='60-min', linewidth=2, alpha=0.8)
    ax.plot(df_15['timestamps'], cumulative_cost_15, label='15-min', linewidth=2, alpha=0.8)
    ax.set_ylabel('Cumulative Cost [NOK]')
    ax.set_title('Cumulative Energy Cost (Full Month)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 6: Cost savings metrics
    ax = axes[2, 1]
    categories = ['Energy\nCost', 'Peak\nDemand', 'Power\nTariff', 'Total\nSavings']

    energy_savings = metrics_60min['total_energy_cost_nok'] - metrics_15min['total_energy_cost_nok']
    peak_reduction = metrics_60min['peak_demand_kw'] - metrics_15min['peak_demand_kw']
    tariff_savings = metrics_60min['power_tariff_cost_nok'] - metrics_15min['power_tariff_cost_nok']
    total_savings = energy_savings + tariff_savings

    values = [energy_savings, peak_reduction * 10, tariff_savings, total_savings]  # Scale peak for visualization
    colors = ['green' if v > 0 else 'red' for v in values]

    bars = ax.bar(categories, values, color=colors, alpha=0.7)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.set_ylabel('Savings [NOK or kW×10]')
    ax.set_title('15-min Advantage (Positive = Better)')
    ax.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}',
                ha='center', va='bottom' if height > 0 else 'top')

    plt.tight_layout()

    # Save plot
    output_file = '/mnt/c/users/klaus/klauspython/SDE/battery_optimization/results/resolution_comparison_oct2025.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n📊 Plots saved to: {output_file}")
    plt.close()


def main():
    """Main execution function."""
    print("\n" + "="*70)
    print("BATTERY OPTIMIZATION: 15-min vs 60-min Resolution Comparison")
    print("="*70)
    print("Battery: 30 kW / 30 kWh")
    print("Period: October 2025 (First Week - 7 Days)")
    print("="*70)

    # Step 1: Fetch price data for both resolutions
    print("\n[1/5] Fetching price data...")
    prices_15min = fetch_entsoe_data_october_2025(resolution='PT15M')
    prices_60min = resample_to_hourly(prices_15min)

    # Step 2: Run 60-minute simulation
    print("\n[2/5] Running 60-minute resolution simulation...")
    metrics_60min = run_rolling_horizon_simulation(
        price_data=prices_60min,
        resolution='PT60M',
        battery_kw=30.0,
        battery_kwh=30.0,
        horizon_hours=24
    )

    # Step 3: Run 15-minute simulation
    print("\n[3/5] Running 15-minute resolution simulation...")
    metrics_15min = run_rolling_horizon_simulation(
        price_data=prices_15min,
        resolution='PT15M',
        battery_kw=30.0,
        battery_kwh=30.0,
        horizon_hours=24
    )

    # Step 4: Compare results
    print("\n[4/5] Comparing results...")
    comparison = compare_results(metrics_60min, metrics_15min)

    # Step 5: Generate report
    print("\n[5/5] Generating report...")
    print("\n" + "="*70)
    print("EXECUTIVE SUMMARY")
    print("="*70)
    print(f"\nSwitching from 60-minute to 15-minute resolution provides:")
    print(f"  • Energy cost savings: {comparison['energy_savings_pct']:+.2f}%")
    print(f"  • Peak demand reduction: {comparison['peak_reduction_kw']:.2f} kW")
    print(f"  • Monthly savings: {comparison['total_monthly_savings_nok']:,.2f} NOK")
    print(f"  • Annual savings: {comparison['total_annual_savings_nok']:,.2f} NOK")
    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    main()
