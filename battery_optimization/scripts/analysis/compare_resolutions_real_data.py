"""
Compare 15-minute vs 60-minute resolution with REAL DATA.

Uses:
- Real ENTSO-E NO2 spot prices for October 2025
- Real PVGIS solar production data
- Full system configuration (138.55 kWp PV, 70 kW grid limit, commercial load)
- Lnett tariff structure
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from src.operational.state_manager import BatterySystemState, calculate_average_power_tariff_rate
from config import BatteryOptimizationConfig
from create_detailed_plots import create_comprehensive_plots


def load_real_spot_prices(resolution: str, start_date: str = '2025-10-20', end_date: str = '2025-10-26') -> pd.DataFrame:
    """
    Load real ENTSO-E NO2 spot prices.

    Args:
        resolution: 'PT60M' or 'PT15M'
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        DataFrame with timestamp and price_nok columns
    """
    print(f"\n📊 Loading REAL ENTSO-E NO2 spot prices ({resolution})...")

    # Select file based on resolution
    if resolution == 'PT15M':
        file_path = 'data/spot_prices/NO2_2025_15min_real.csv'
    else:
        file_path = 'data/spot_prices/NO2_2025_60min_real.csv'

    # Load data
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.rename(columns={'price_nok': 'price_nok_per_kwh'})

    # Convert to Oslo time
    df['timestamp'] = df['timestamp'].dt.tz_convert('Europe/Oslo')

    # Filter to specified date range
    start = pd.Timestamp(start_date, tz='Europe/Oslo')
    end = pd.Timestamp(end_date, tz='Europe/Oslo') + pd.Timedelta(hours=23, minutes=59)
    df = df[(df['timestamp'] >= start) & (df['timestamp'] <= end)].copy()

    print(f"  ✓ Loaded {len(df)} real price points for {start_date} to {end_date}")
    print(f"  Price range: {df['price_nok_per_kwh'].min():.3f} - {df['price_nok_per_kwh'].max():.3f} NOK/kWh")
    print(f"  Mean price: {df['price_nok_per_kwh'].mean():.3f} NOK/kWh")

    return df


def load_pvgis_production(timestamps: pd.DatetimeIndex, pv_capacity_kwp: float = 138.55) -> np.ndarray:
    """
    Load and interpolate PVGIS solar production data.

    Args:
        timestamps: Target timestamps for production values
        pv_capacity_kwp: PV system capacity [kWp]

    Returns:
        Array of PV production values [kW]
    """
    print(f"\n☀️ Loading PVGIS solar production data...")

    # Load PVGIS data
    pv_file = f'data/pv_profiles/pvgis_58.97_5.73_{pv_capacity_kwp}kWp.csv'
    pv_df = pd.read_csv(pv_file, index_col=0, parse_dates=True)

    print(f"  File: {pv_file}")
    print(f"  PVGIS data points: {len(pv_df)}")

    # Match by day-of-year and hour
    pv_production = np.zeros(len(timestamps))

    for i, ts in enumerate(timestamps):
        doy = ts.dayofyear
        hour = ts.hour
        minute = ts.minute

        # Find matching pattern in PVGIS data
        # PVGIS has hourly data, interpolate for 15-min if needed
        pvgis_match = pv_df[(pv_df.index.dayofyear == doy) & (pv_df.index.hour == hour)]

        if len(pvgis_match) > 0:
            hourly_value = pvgis_match['production_kw'].values[0]

            # For 15-min data, use same hourly value (PVGIS is hourly average)
            pv_production[i] = hourly_value
        else:
            pv_production[i] = 0.0

    print(f"  ✓ Mapped {len(pv_production)} production points")
    print(f"  Production range: {pv_production.min():.1f} - {pv_production.max():.1f} kW")
    print(f"  Mean production: {pv_production.mean():.1f} kW (October = autumn)")

    return pv_production


def load_consumption_profile(timestamps: pd.DatetimeIndex, annual_kwh: float = 300000) -> np.ndarray:
    """
    Generate commercial consumption profile.

    Args:
        timestamps: Timestamps for consumption values
        annual_kwh: Annual consumption [kWh]

    Returns:
        Array of consumption values [kW]
    """
    print(f"\n🏭 Generating commercial consumption profile...")

    n_hours_year = 8760
    avg_power_kw = annual_kwh / n_hours_year

    consumption = np.zeros(len(timestamps))

    for i, ts in enumerate(timestamps):
        hour = ts.hour
        weekday = ts.weekday()

        # Commercial pattern: higher during business hours
        if weekday < 5:  # Monday-Friday
            if 6 <= hour < 18:
                load_factor = 1.3  # Daytime business hours
            elif 18 <= hour < 22:
                load_factor = 0.9  # Evening
            else:
                load_factor = 0.5  # Night
        else:  # Weekend
            if 8 <= hour < 16:
                load_factor = 0.7  # Reduced weekend operation
            else:
                load_factor = 0.4  # Low weekend/night

        consumption[i] = avg_power_kw * load_factor

    print(f"  ✓ Generated {len(consumption)} consumption points")
    print(f"  Consumption range: {consumption.min():.1f} - {consumption.max():.1f} kW")
    print(f"  Mean consumption: {consumption.mean():.1f} kW")

    return consumption


def run_simulation_with_real_data(resolution: str, battery_kw: float = 30.0, battery_kwh: float = 30.0):
    """
    Run October 2025 simulation with real data.

    Args:
        resolution: 'PT60M' or 'PT15M'
        battery_kw: Battery power [kW]
        battery_kwh: Battery capacity [kWh]

    Returns:
        Dictionary with simulation metrics
    """
    print(f"\n{'='*70}")
    print(f"SIMULATION: {resolution} - October 2025 (REAL DATA)")
    print(f"{'='*70}")

    # Load real price data (week of Oct 20-26, 2025)
    price_data = load_real_spot_prices(resolution, start_date='2025-10-20', end_date='2025-10-26')

    # Configuration
    config = BatteryOptimizationConfig()

    # Load PV production
    timestamps = pd.to_datetime(price_data['timestamp'].values)
    pv_production = load_pvgis_production(timestamps, config.solar.pv_capacity_kwp)

    # Load consumption
    consumption = load_consumption_profile(timestamps, config.consumption.annual_kwh)

    # Optimizer
    optimizer = RollingHorizonOptimizer(
        config=config,
        battery_kwh=battery_kwh,
        battery_kw=battery_kw,
        horizon_hours=24,
        resolution=resolution
    )

    # Initialize state
    sim_start = datetime(2025, 10, 20, 0, 0)
    month_start = datetime(2025, 10, 1, 0, 0)  # Keep month start for tariff calculations

    state = BatterySystemState(
        current_soc_kwh=battery_kwh * 0.5,
        battery_capacity_kwh=battery_kwh,
        current_monthly_peak_kw=0.0,
        power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(config.tariff),
        last_update=sim_start,
        month_start_date=month_start
    )

    # Extract data arrays
    prices = price_data['price_nok_per_kwh'].values

    # Timestep info
    timestep_hours = 1.0 if resolution == 'PT60M' else 0.25
    timesteps_per_day = int(24 / timestep_hours)

    # Results storage
    results = {
        'timestamp': [],
        'soc_kwh': [],
        'battery_power_kw': [],
        'grid_import_kw': [],
        'grid_export_kw': [],
        'pv_production_kw': [],
        'consumption_kw': [],
        'spot_price': [],
        'curtailment_kw': []
    }

    total_energy_cost = 0.0
    peak_demand = 0.0
    total_curtailment = 0.0

    # Run rolling horizon optimizations (update every timestep)
    current_idx = 0
    optimization_count = 0

    print(f"\nRunning rolling horizon optimizations (update every {timestep_hours:.2f} hours)...")
    print(f"  Total timesteps: {len(timestamps)}")
    print(f"  Expected optimizations: ~{len(timestamps) - timesteps_per_day}")

    while current_idx < len(timestamps) - timesteps_per_day:
        end_idx = current_idx + timesteps_per_day

        window_ts = timestamps[current_idx:end_idx]
        window_prices = prices[current_idx:end_idx]
        window_pv = pv_production[current_idx:end_idx]
        window_load = consumption[current_idx:end_idx]

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
            print(f"  Optimization {optimization_count}: Failed!")
            current_idx += 1
            optimization_count += 1
            continue

        # Apply ONLY the first timestep action (rolling horizon)
        # Store the action and resulting SOC after applying it
        battery_power = result.P_charge[0] - result.P_discharge[0]

        # SOC AFTER first timestep action (result.E_battery[1] if available, else compute)
        if len(result.E_battery) > 1:
            soc_after = result.E_battery[1]
        else:
            # Fallback computation
            charge_energy = result.P_charge[0] * timestep_hours * 0.9  # efficiency
            discharge_energy = result.P_discharge[0] * timestep_hours / 0.9
            soc_after = state.current_soc_kwh + charge_energy - discharge_energy

        results['timestamp'].append(window_ts[0])
        results['soc_kwh'].append(soc_after)
        results['battery_power_kw'].append(battery_power)
        results['grid_import_kw'].append(result.P_grid_import[0])
        results['grid_export_kw'].append(result.P_grid_export[0])
        results['pv_production_kw'].append(window_pv[0])
        results['consumption_kw'].append(window_load[0])
        results['spot_price'].append(window_prices[0])
        results['curtailment_kw'].append(result.P_curtail[0])

        # Update metrics (only for first timestep)
        energy_cost_timestep = (
            result.P_grid_import[0] * window_prices[0] * timestep_hours -
            result.P_grid_export[0] * window_prices[0] * timestep_hours
        )
        total_energy_cost += energy_cost_timestep
        peak_demand = max(peak_demand, result.P_grid_import[0])
        total_curtailment += result.P_curtail[0] * timestep_hours

        # Update state with SOC AFTER first timestep action
        state.current_soc_kwh = soc_after
        state.current_monthly_peak_kw = peak_demand
        state.last_update = window_ts[0]

        # Progress reporting
        if optimization_count % 100 == 0:
            day = int(current_idx * timestep_hours / 24) + 1
            print(f"  Progress: {optimization_count} optimizations, Day {day}/7")

        # Move to next timestep (rolling horizon)
        current_idx += 1
        optimization_count += 1

    # Calculate metrics
    results_df = pd.DataFrame(results)

    tariff_cost = config.tariff.get_power_cost(peak_demand)

    total_charge = results_df[results_df['battery_power_kw'] > 0]['battery_power_kw'].sum() * timestep_hours
    total_discharge = abs(results_df[results_df['battery_power_kw'] < 0]['battery_power_kw'].sum()) * timestep_hours
    cycles = total_discharge / battery_kwh

    total_pv_production = results_df['pv_production_kw'].sum() * timestep_hours
    total_consumption = results_df['consumption_kw'].sum() * timestep_hours
    total_grid_import = results_df['grid_import_kw'].sum() * timestep_hours
    total_grid_export = results_df['grid_export_kw'].sum() * timestep_hours

    print(f"\n{'='*70}")
    print(f"RESULTS: {resolution}")
    print(f"{'='*70}")
    print(f"  Optimizations: {optimization_count}")
    print(f"  Energy cost: {total_energy_cost:,.2f} NOK")
    print(f"  Peak demand: {peak_demand:.2f} kW")
    print(f"  Power tariff: {tariff_cost:.2f} NOK/month")
    print(f"  Battery cycles: {cycles:.2f}")
    print(f"  PV production: {total_pv_production:,.0f} kWh")
    print(f"  Consumption: {total_consumption:,.0f} kWh")
    print(f"  Grid import: {total_grid_import:,.0f} kWh")
    print(f"  Grid export: {total_grid_export:,.0f} kWh")
    print(f"  Curtailment: {total_curtailment:,.0f} kWh")
    print(f"  Self-consumption: {((total_pv_production - total_grid_export - total_curtailment) / total_pv_production * 100):.1f}%")

    return {
        'resolution': resolution,
        'results_df': results_df,
        'energy_cost': total_energy_cost,
        'peak_demand': peak_demand,
        'tariff_cost': tariff_cost,
        'cycles': cycles,
        'pv_production_kwh': total_pv_production,
        'consumption_kwh': total_consumption,
        'grid_import_kwh': total_grid_import,
        'grid_export_kwh': total_grid_export,
        'curtailment_kwh': total_curtailment,
        'optimizations': optimization_count
    }


def compare_and_visualize(metrics_60, metrics_15):
    """Compare results and create detailed visualization."""

    print(f"\n{'='*70}")
    print(f"FINAL COMPARISON: 15-min vs 60-min Resolution")
    print(f"{'='*70}")

    # Cost comparison
    energy_diff = metrics_15['energy_cost'] - metrics_60['energy_cost']
    energy_pct = (energy_diff / metrics_60['energy_cost']) * 100

    tariff_diff = metrics_15['tariff_cost'] - metrics_60['tariff_cost']
    total_diff = energy_diff + tariff_diff

    print(f"\n💰 ECONOMIC IMPACT:")
    print(f"  Energy cost (60-min): {metrics_60['energy_cost']:,.2f} NOK")
    print(f"  Energy cost (15-min): {metrics_15['energy_cost']:,.2f} NOK")
    print(f"  Difference: {energy_diff:+,.2f} NOK ({energy_pct:+.2f}%)")
    print(f"")
    print(f"  Power tariff (60-min): {metrics_60['tariff_cost']:.2f} NOK")
    print(f"  Power tariff (15-min): {metrics_15['tariff_cost']:.2f} NOK")
    print(f"  Difference: {tariff_diff:+.2f} NOK")
    print(f"")
    print(f"  TOTAL MONTHLY: {total_diff:+,.2f} NOK")
    print(f"  TOTAL ANNUAL: {total_diff * 12:+,.2f} NOK")

    # Peak demand
    peak_diff = metrics_15['peak_demand'] - metrics_60['peak_demand']
    peak_pct = (peak_diff / metrics_60['peak_demand']) * 100

    print(f"\n⚡ PEAK DEMAND:")
    print(f"  60-min: {metrics_60['peak_demand']:.2f} kW")
    print(f"  15-min: {metrics_15['peak_demand']:.2f} kW")
    print(f"  Difference: {peak_diff:+.2f} kW ({peak_pct:+.2f}%)")

    # Battery utilization
    cycles_diff = metrics_15['cycles'] - metrics_60['cycles']

    print(f"\n🔋 BATTERY UTILIZATION:")
    print(f"  60-min: {metrics_60['cycles']:.2f} full cycles")
    print(f"  15-min: {metrics_15['cycles']:.2f} full cycles")
    print(f"  Difference: {cycles_diff:+.2f} cycles")

    # Energy flows
    print(f"\n🔌 ENERGY FLOWS (October 2025):")
    print(f"  PV production: {metrics_60['pv_production_kwh']:,.0f} kWh")
    print(f"  Consumption: {metrics_60['consumption_kwh']:,.0f} kWh")
    print(f"  Grid import (60-min): {metrics_60['grid_import_kwh']:,.0f} kWh")
    print(f"  Grid import (15-min): {metrics_15['grid_import_kwh']:,.0f} kWh")
    print(f"  Grid export (60-min): {metrics_60['grid_export_kwh']:,.0f} kWh")
    print(f"  Grid export (15-min): {metrics_15['grid_export_kwh']:,.0f} kWh")
    print(f"  Curtailment (60-min): {metrics_60['curtailment_kwh']:,.0f} kWh")
    print(f"  Curtailment (15-min): {metrics_15['curtailment_kwh']:,.0f} kWh")

    # Create comprehensive plots
    fig, axes = plt.subplots(3, 2, figsize=(16, 14))
    fig.suptitle('15-min vs 60-min Resolution Comparison - October 2025\n'
                 '30 kW/30 kWh Battery | Real ENTSO-E NO2 Prices | PVGIS Solar Data',
                 fontsize=14, fontweight='bold')

    df_60 = metrics_60['results_df']
    df_15 = metrics_15['results_df']

    # Plot 1: SOC comparison (first week)
    ax = axes[0, 0]
    days = 7
    hours_60 = days * 24
    hours_15 = days * 24 * 4

    ax.plot(df_60['timestamp'][:hours_60], df_60['soc_kwh'][:hours_60],
            label='60-min', linewidth=2, color='blue')
    ax.plot(df_15['timestamp'][:hours_15], df_15['soc_kwh'][:hours_15],
            label='15-min', linewidth=1.5, alpha=0.8, color='orange')
    ax.set_ylabel('SOC [kWh]', fontsize=10)
    ax.set_title('Battery State of Charge (First Week)', fontsize=11)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 2: Battery power (first 3 days)
    ax = axes[0, 1]
    hours_60 = 3 * 24
    hours_15 = 3 * 24 * 4

    ax.plot(df_60['timestamp'][:hours_60], df_60['battery_power_kw'][:hours_60],
            label='60-min', linewidth=2, color='blue')
    ax.plot(df_15['timestamp'][:hours_15], df_15['battery_power_kw'][:hours_15],
            label='15-min', linewidth=1.5, alpha=0.8, color='orange')
    ax.axhline(y=0, color='k', linestyle='--', linewidth=0.5)
    ax.set_ylabel('Battery Power [kW]', fontsize=10)
    ax.set_title('Charging Strategy (First 3 Days)', fontsize=11)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 3: Grid import/export
    ax = axes[1, 0]
    ax.plot(df_60['timestamp'][:hours_60], df_60['grid_import_kw'][:hours_60],
            label='Import (60-min)', linewidth=2, color='blue')
    ax.plot(df_60['timestamp'][:hours_60], -df_60['grid_export_kw'][:hours_60],
            label='Export (60-min)', linewidth=2, color='green', alpha=0.6)
    ax.plot(df_15['timestamp'][:hours_15], df_15['grid_import_kw'][:hours_15],
            label='Import (15-min)', linewidth=1.5, alpha=0.8, color='orange')
    ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
    ax.axhline(y=70, color='r', linestyle='--', linewidth=1, label='Grid limit (70 kW)')
    ax.set_ylabel('Grid Power [kW]', fontsize=10)
    ax.set_title('Grid Import/Export (First 3 Days)', fontsize=11)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Plot 4: PV + Consumption overlay
    ax = axes[1, 1]
    ax.plot(df_60['timestamp'][:hours_60], df_60['pv_production_kw'][:hours_60],
            label='PV Production', linewidth=2, color='gold')
    ax.plot(df_60['timestamp'][:hours_60], df_60['consumption_kw'][:hours_60],
            label='Consumption', linewidth=2, color='purple', alpha=0.7)
    ax.set_ylabel('Power [kW]', fontsize=10)
    ax.set_title('PV Production vs Consumption (First 3 Days)', fontsize=11)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 5: Spot prices
    ax = axes[2, 0]
    ax.plot(df_60['timestamp'], df_60['spot_price'], label='Spot Price', color='red', linewidth=1.5)
    ax.set_ylabel('Price [NOK/kWh]', fontsize=10)
    ax.set_title('ENTSO-E NO2 Spot Prices (October 2025)', fontsize=11)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 6: Cost comparison bars
    ax = axes[2, 1]
    categories = ['Energy\nCost', 'Power\nTariff', 'Total\nCost', 'Battery\nCycles']
    values_60 = [metrics_60['energy_cost']/1000, metrics_60['tariff_cost']/100,
                 (metrics_60['energy_cost'] + metrics_60['tariff_cost'])/1000,
                 metrics_60['cycles']]
    values_15 = [metrics_15['energy_cost']/1000, metrics_15['tariff_cost']/100,
                 (metrics_15['energy_cost'] + metrics_15['tariff_cost'])/1000,
                 metrics_15['cycles']]

    x = np.arange(len(categories))
    width = 0.35

    bars1 = ax.bar(x - width/2, values_60, width, label='60-min', alpha=0.8, color='blue')
    bars2 = ax.bar(x + width/2, values_15, width, label='15-min', alpha=0.8, color='orange')

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_ylabel('Value (scaled)', fontsize=10)
    ax.set_title('Metrics Comparison\n(Energy/Total in 1000 NOK, Tariff in 100 NOK)', fontsize=11)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()

    output_file = '/mnt/c/users/klaus/klauspython/SDE/battery_optimization/results/resolution_comparison_oct2025_real.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n📊 Visualization saved: {output_file}")
    plt.close()


def main():
    import pickle
    from pathlib import Path

    print("\n" + "="*70)
    print("RESOLUTION COMPARISON - REAL DATA")
    print("="*70)
    print("Period: October 20-26, 2025 (1 week)")
    print("Battery: 30 kW / 30 kWh")
    print("PV: 138.55 kWp (Stavanger, NO2)")
    print("Data: Real ENTSO-E prices + PVGIS production")
    print("Update frequency: Every timestep (rolling horizon)")
    print("="*70)

    # Check for saved results
    results_dir = Path('/mnt/c/users/klaus/klauspython/SDE/battery_optimization/results/mai_rolling_horizon')
    results_dir.mkdir(parents=True, exist_ok=True)
    results_file = results_dir / 'resolution_comparison_results.pkl'

    if results_file.exists():
        print("\n🔍 Found saved results, loading...")
        with open(results_file, 'rb') as f:
            saved_data = pickle.load(f)
            metrics_60 = saved_data['metrics_60']
            metrics_15 = saved_data['metrics_15']
        print("  ✓ Results loaded successfully")
    else:
        # Run simulations
        print("\n[1/3] Running 60-minute simulation...")
        metrics_60 = run_simulation_with_real_data('PT60M', battery_kw=30.0, battery_kwh=30.0)

        print("\n[2/3] Running 15-minute simulation...")
        metrics_15 = run_simulation_with_real_data('PT15M', battery_kw=30.0, battery_kwh=30.0)

        # Save results
        print("\n💾 Saving results for future use...")
        with open(results_file, 'wb') as f:
            pickle.dump({
                'metrics_60': metrics_60,
                'metrics_15': metrics_15
            }, f)
        print(f"  ✓ Results saved to: {results_file}")

    print("\n[3/4] Comparing results...")
    compare_and_visualize(metrics_60, metrics_15)

    print("\n[4/4] Creating detailed plots...")
    plot_file = create_comprehensive_plots(metrics_60, metrics_15)

    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE WITH REAL DATA")
    print("="*70)
    print(f"\n📊 Plots generated:")
    print(f"  • Summary: results/resolution_comparison_oct2025_real.png")
    print(f"  • Detailed: {plot_file}")
    print(f"\n💾 Results cached: {results_file}")
    print(f"  To re-run simulations, delete this file")


if __name__ == '__main__':
    main()
