"""
Test rolling horizon optimizer for January 2024 with 15-min resolution.
Winter conditions: low solar, higher heating load.
Saves detailed results for plotting.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from config import BatteryOptimizationConfig
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from operational.state_manager import BatterySystemState, calculate_average_power_tariff_rate

def test_rolling_january_with_plots():
    """Simulate January 2024 with rolling horizon optimization (15-min resolution)."""

    print("\n" + "="*80)
    print("ROLLING HORIZON SIMULATION - JANUARY 2024 (WITH PLOTS)")
    print("="*80)

    # Load configuration
    config = BatteryOptimizationConfig()

    # Create January 2024 data (31 days × 24 hours × 4 quarters = 2976 timesteps)
    start_date = datetime(2024, 1, 1, 0, 0)
    timestamps = pd.date_range(start_date, periods=31*24*4, freq='15min')

    print(f"\nSimulation period:")
    print(f"  Start: {timestamps[0]}")
    print(f"  End: {timestamps[-1]}")
    print(f"  Total timesteps: {len(timestamps)} (15-min resolution)")

    # Generate synthetic data for January (low solar month)
    hours_of_day = np.array([ts.hour for ts in timestamps])
    days = np.array([ts.day for ts in timestamps])

    # Solar production: Very low in January, short days
    solar_elevation = np.maximum(0, np.sin(np.pi * (hours_of_day - 8) / 8))
    pv_production = 30.0 * solar_elevation  # 0-30 kW
    pv_production[hours_of_day < 8] = 0   # Night: before 8am
    pv_production[hours_of_day > 16] = 0  # Night: after 4pm

    # Load consumption: Higher in winter due to heating
    load_base = 35.0  # 35 kW baseline (winter heating)
    load_daytime = load_base + 20.0 * ((hours_of_day >= 8) & (hours_of_day <= 17))
    load_evening_peak = 10.0 * ((hours_of_day >= 17) & (hours_of_day <= 20))
    load_consumption = load_base + (load_daytime - load_base) + load_evening_peak

    # Spot prices: Winter pattern (higher overall, peaks during cold days)
    spot_prices = np.full(len(timestamps), 0.60)
    spot_prices[hours_of_day < 6] = 0.40  # Cheap night
    spot_prices[(hours_of_day >= 6) & (hours_of_day < 9)] = 0.90  # Morning peak
    spot_prices[(hours_of_day >= 17) & (hours_of_day < 21)] = 1.00  # Evening peak
    spot_prices[hours_of_day >= 22] = 0.40  # Cheap late night

    print(f"\nData summary (January - Winter):")
    print(f"  PV production: {pv_production.min():.1f} - {pv_production.max():.1f} kW (low solar)")
    print(f"  Load consumption: {load_consumption.min():.1f} - {load_consumption.max():.1f} kW (winter heating)")
    print(f"  Spot prices: {spot_prices.min():.2f} - {spot_prices.max():.2f} NOK/kWh")
    print(f"  Net load (load - PV): {(load_consumption - pv_production).min():.1f} - {(load_consumption - pv_production).max():.1f} kW")

    # Initialize rolling horizon optimizer
    optimizer = RollingHorizonOptimizer(
        config=config,
        battery_kwh=30.0,  # 30 kWh battery
        battery_kw=30.0    # 30 kW power rating
    )

    # Initialize state with simulation start time
    state = BatterySystemState(
        current_soc_kwh=15.0,  # 50% SOC
        battery_capacity_kwh=30.0,
        current_monthly_peak_kw=50.0,  # Start with 50 kW peak (typical winter)
        power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(config.tariff),
        last_update=start_date,
        month_start_date=start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    )

    print(f"\nInitial state:")
    print(f"  Battery: 30.0 kWh, 30.0 kW")
    print(f"  SOC: {state.current_soc_kwh:.2f} kWh ({state.current_soc_kwh/30.0*100:.1f}%)")
    print(f"  Monthly peak: {state.current_monthly_peak_kw:.2f} kW")

    # Run rolling horizon simulation
    window_timesteps = 96  # 24 hours × 4 quarters/hour
    step_timesteps = 96  # Non-overlapping windows for speed

    results = []
    detailed_results = {
        'timestamps': [],
        'soc': [],
        'grid_import': [],
        'grid_export': [],
        'battery_charge': [],
        'battery_discharge': [],
        'pv': [],
        'load': [],
        'spot_price': []
    }
    
    total_windows = len(timestamps) // step_timesteps

    print(f"\n" + "="*80)
    print(f"Running {total_windows} optimization windows...")
    print("="*80)

    for w in range(total_windows):
        t_start = w * step_timesteps
        t_end = min(t_start + window_timesteps, len(timestamps))

        if t_end - t_start < window_timesteps:
            print(f"\nWindow {w}: Insufficient data, stopping")
            break

        # Get window data
        window_pv = pv_production[t_start:t_end]
        window_load = load_consumption[t_start:t_end]
        window_prices = spot_prices[t_start:t_end]
        window_timestamps = timestamps[t_start:t_end]

        # Optimize
        result = optimizer.optimize_24h(
            current_state=state,
            pv_production=window_pv,
            load_consumption=window_load,
            spot_prices=window_prices,
            timestamps=window_timestamps,
            verbose=(w % 10 == 0)  # Verbose output every 10 windows
        )

        if not result.success:
            print(f"\nWindow {w}: FAILED - {result.message}")
            break

        # Store aggregated results
        results.append({
            'window': w,
            'date': window_timestamps[0].date(),
            'energy_cost': result.energy_cost,
            'peak_penalty_actual': result.peak_penalty_actual,
            'objective_actual': result.objective_value_actual,
            'final_soc': result.E_battery[-1],
            'max_grid_import': result.P_grid_import.max(),
        })
        
        # Store detailed time series
        detailed_results['timestamps'].extend(window_timestamps)
        detailed_results['soc'].extend(result.E_battery)
        detailed_results['grid_import'].extend(result.P_grid_import)
        detailed_results['grid_export'].extend(result.P_grid_export)
        detailed_results['battery_charge'].extend(result.P_charge)
        detailed_results['battery_discharge'].extend(result.P_discharge)
        detailed_results['pv'].extend(window_pv)
        detailed_results['load'].extend(window_load)
        detailed_results['spot_price'].extend(window_prices)

        # Update state for next window
        state.update_from_measurement(
            timestamp=window_timestamps[-1],
            soc_kwh=result.E_battery[-1],
            grid_import_power_kw=result.P_grid_import[-1]
        )

        if (w + 1) % 5 == 0:
            print(f"  Progress: {w+1}/{total_windows} windows completed")

    print(f"\n" + "="*80)
    print("JANUARY 2024 SIMULATION RESULTS")
    print("="*80)

    if results:
        df = pd.DataFrame(results)
        
        # Calculate MONTHLY power tariff
        max_peak_month = df['max_grid_import'].max()
        monthly_tariff_actual = config.tariff.get_power_cost(max_peak_month)

        print(f"\nMonthly Peak Tracking:")
        print(f"  Maximum peak across month: {max_peak_month:.2f} kW")
        print(f"  Monthly power tariff: {monthly_tariff_actual:,.2f} NOK/month")

        print(f"\nCost Summary for January 2024:")
        print(f"  Energy cost: {df['energy_cost'].sum():,.2f} NOK")
        print(f"  Power tariff (monthly): {monthly_tariff_actual:,.2f} NOK")
        print(f"  **Total cost: {df['energy_cost'].sum() + monthly_tariff_actual:,.2f} NOK**")

        print(f"\nOperational Summary:")
        print(f"  Final SOC: {df['final_soc'].iloc[-1]:.2f} kWh ({df['final_soc'].iloc[-1]/30.0*100:.1f}%)")
        print(f"  Final monthly peak: {state.current_monthly_peak_kw:.2f} kW")
        print(f"  Max grid import: {df['max_grid_import'].max():.2f} kW")
        print(f"  Avg daily energy cost: {df['energy_cost'].mean():.2f} NOK/day")

        # Create detailed DataFrame
        df_detailed = pd.DataFrame(detailed_results)
        df_detailed.set_index('timestamps', inplace=True)
        
        # Generate plots
        print(f"\n" + "="*80)
        print("GENERATING PLOTS")
        print("="*80)
        
        fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
        
        # Plot 1: Power flows
        ax = axes[0]
        ax.plot(df_detailed.index, df_detailed['pv'], label='PV Production', color='orange', alpha=0.7)
        ax.plot(df_detailed.index, df_detailed['load'], label='Load', color='red', alpha=0.7)
        ax.plot(df_detailed.index, df_detailed['grid_import'], label='Grid Import', color='blue', alpha=0.7)
        ax.plot(df_detailed.index, -df_detailed['grid_export'], label='Grid Export', color='green', alpha=0.7)
        ax.axhline(y=max_peak_month, color='red', linestyle='--', label=f'Monthly Peak ({max_peak_month:.1f} kW)')
        ax.set_ylabel('Power [kW]')
        ax.set_title('January 2024: Power Flows')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        # Plot 2: Battery operations
        ax = axes[1]
        ax.plot(df_detailed.index, df_detailed['battery_charge'], label='Charge', color='green', alpha=0.7)
        ax.plot(df_detailed.index, -df_detailed['battery_discharge'], label='Discharge', color='red', alpha=0.7)
        ax.set_ylabel('Battery Power [kW]')
        ax.set_title('Battery Charging/Discharging')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        # Plot 3: Battery SOC
        ax = axes[2]
        ax.plot(df_detailed.index, df_detailed['soc'], label='SOC', color='purple', linewidth=2)
        ax.axhline(y=30*0.9, color='red', linestyle='--', alpha=0.5, label='SOC Max (90%)')
        ax.axhline(y=30*0.1, color='red', linestyle='--', alpha=0.5, label='SOC Min (10%)')
        ax.set_ylabel('SOC [kWh]')
        ax.set_title('Battery State of Charge')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        # Plot 4: Spot prices
        ax = axes[3]
        ax.plot(df_detailed.index, df_detailed['spot_price'], label='Spot Price', color='brown', linewidth=1)
        ax.set_ylabel('Price [NOK/kWh]')
        ax.set_xlabel('Date')
        ax.set_title('Electricity Spot Prices')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = '/mnt/c/Users/klaus/klauspython/SDE/battery_optimization/results/january_2024_rolling_horizon.png'
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        print(f"  ✓ Saved plot: {plot_path}")
        
        # Also create a zoomed view of first 3 days
        fig2, axes2 = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
        
        # First 3 days (3 * 96 = 288 timesteps)
        zoom_end = min(288, len(df_detailed))
        df_zoom = df_detailed.iloc[:zoom_end]
        
        # Plot 1: Power flows (zoomed)
        ax = axes2[0]
        ax.plot(df_zoom.index, df_zoom['pv'], label='PV Production', color='orange', linewidth=2)
        ax.plot(df_zoom.index, df_zoom['load'], label='Load', color='red', linewidth=2)
        ax.plot(df_zoom.index, df_zoom['grid_import'], label='Grid Import', color='blue', linewidth=2)
        ax.plot(df_zoom.index, -df_zoom['grid_export'], label='Grid Export', color='green', linewidth=2)
        ax.axhline(y=max_peak_month, color='red', linestyle='--', label=f'Monthly Peak ({max_peak_month:.1f} kW)')
        ax.set_ylabel('Power [kW]')
        ax.set_title('January 1-3, 2024: Power Flows (Detailed)')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        # Plot 2: Battery operations (zoomed)
        ax = axes2[1]
        ax.plot(df_zoom.index, df_zoom['battery_charge'], label='Charge', color='green', linewidth=2)
        ax.plot(df_zoom.index, -df_zoom['battery_discharge'], label='Discharge', color='red', linewidth=2)
        ax.set_ylabel('Battery Power [kW]')
        ax.set_title('Battery Operations (Detailed)')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        # Plot 3: Battery SOC (zoomed)
        ax = axes2[2]
        ax.plot(df_zoom.index, df_zoom['soc'], label='SOC', color='purple', linewidth=2)
        ax.axhline(y=30*0.9, color='red', linestyle='--', alpha=0.5, label='SOC Max (90%)')
        ax.axhline(y=30*0.1, color='red', linestyle='--', alpha=0.5, label='SOC Min (10%)')
        ax.set_ylabel('SOC [kWh]')
        ax.set_title('Battery State of Charge (Detailed)')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        # Plot 4: Spot prices (zoomed)
        ax = axes2[3]
        ax.plot(df_zoom.index, df_zoom['spot_price'], label='Spot Price', color='brown', linewidth=2)
        ax.set_ylabel('Price [NOK/kWh]')
        ax.set_xlabel('Date')
        ax.set_title('Electricity Spot Prices (Detailed)')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_zoom_path = '/mnt/c/Users/klaus/klauspython/SDE/battery_optimization/results/january_2024_rolling_horizon_zoom.png'
        plt.savefig(plot_zoom_path, dpi=150, bbox_inches='tight')
        print(f"  ✓ Saved zoom plot: {plot_zoom_path}")
        
        print("="*80)
        return True
    else:
        print("\n❌ No results generated")
        return False


if __name__ == "__main__":
    import sys
    success = test_rolling_january_with_plots()
    sys.exit(0 if success else 1)
