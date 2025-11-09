"""
Test rolling horizon optimizer for June 2024 with REAL DATA (1-hour resolution).
Uses actual ENTSO-E prices, PVGIS solar production, and consumption model.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from config import BatteryOptimizationConfig
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from core.consumption_profiles import ConsumptionProfile
from operational.state_manager import BatterySystemState, calculate_average_power_tariff_rate

def test_rolling_june():
    """Simulate June 2024 with rolling horizon optimization using REAL data (1-hour resolution)."""

    print("\n" + "="*80)
    print("ROLLING HORIZON SIMULATION - JUNE 2024 (REAL DATA, 1-HOUR RESOLUTION)")
    print("="*80)

    # Load configuration
    config = BatteryOptimizationConfig()

    # ========================================================================
    # LOAD REAL ENTSO-E ELECTRICITY PRICES
    # ========================================================================
    print("\n📊 Loading REAL ENTSO-E electricity prices...")
    price_df = pd.read_csv('data/spot_prices/NO2_2024_15min_real.csv')
    price_df['timestamp'] = pd.to_datetime(price_df['timestamp'], utc=True)
    price_df.set_index('timestamp', inplace=True)

    # Convert to local Oslo time (CET/CEST)
    price_df.index = price_df.index.tz_convert('Europe/Oslo')

    # Resample from 15-min to 1-hour resolution (take mean of 4 quarters)
    price_df_hourly = price_df.resample('1h').mean()

    # Extract June 2024 (30 days × 24 hours = 720 timesteps)
    start_date = pd.Timestamp(2024, 6, 1, 0, 0, tz='Europe/Oslo')
    end_date = pd.Timestamp(2024, 6, 30, 23, 0, tz='Europe/Oslo')
    price_june = price_df_hourly.loc[start_date:end_date]

    spot_prices = price_june['price_nok'].values
    timestamps = price_june.index

    print(f"  ✓ Loaded {len(spot_prices)} hourly price points")
    print(f"  Price range: {spot_prices.min():.3f} - {spot_prices.max():.3f} NOK/kWh")
    print(f"  Average price: {spot_prices.mean():.3f} NOK/kWh")

    # ========================================================================
    # LOAD REAL PVGIS SOLAR PRODUCTION
    # ========================================================================
    print("\n☀️ Loading REAL PVGIS solar production data...")
    pv_df = pd.read_csv('data/pv_profiles/pvgis_58.97_5.73_150kWp.csv', index_col=0, parse_dates=True)

    # PVGIS data is from 2020, but we can use it for 2024 (same day-of-year pattern)
    # Create a mapping from day-of-year to production profile
    pv_df.index = pd.to_datetime(pv_df.index)

    # For each hour in June 2024, find corresponding hour in PVGIS data (by day-of-year and hour)
    pv_production = np.zeros(len(timestamps))
    for i, ts in enumerate(timestamps):
        # Find matching day-of-year and hour in PVGIS data
        doy = ts.dayofyear
        hour = ts.hour

        # PVGIS data uses 2020 dates, find matching pattern
        pvgis_match = pv_df[(pv_df.index.dayofyear == doy) & (pv_df.index.hour == hour)]

        if len(pvgis_match) > 0:
            pv_production[i] = pvgis_match['production_kw'].values[0]
        else:
            pv_production[i] = 0.0

    print(f"  ✓ Mapped {len(pv_production)} hourly PV production points")
    print(f"  Production range: {pv_production.min():.1f} - {pv_production.max():.1f} kW")
    print(f"  Average production: {pv_production.mean():.1f} kW (summer = high solar)")

    # ========================================================================
    # GENERATE REAL CONSUMPTION PROFILE
    # ========================================================================
    print("\n🏢 Generating commercial office consumption profile...")
    consumption_profile = ConsumptionProfile.commercial_office(annual_kwh=90000)

    # Generate hourly consumption for June 2024
    load_consumption = np.zeros(len(timestamps))
    for i, ts in enumerate(timestamps):
        hour = ts.hour
        is_weekend = ts.weekday() >= 5  # Saturday=5, Sunday=6

        if is_weekend:
            load_consumption[i] = consumption_profile['weekend'][hour] * consumption_profile['annual_kwh'] / 8760
        else:
            load_consumption[i] = consumption_profile['weekday'][hour] * consumption_profile['annual_kwh'] / 8760

    print(f"  ✓ Generated {len(load_consumption)} hourly consumption points")
    print(f"  Consumption range: {load_consumption.min():.1f} - {load_consumption.max():.1f} kW")
    print(f"  Average consumption: {load_consumption.mean():.1f} kW")
    print(f"  Net load range: {(load_consumption - pv_production).min():.1f} - {(load_consumption - pv_production).max():.1f} kW")

    # ========================================================================
    # INITIALIZE ROLLING HORIZON OPTIMIZER
    # ========================================================================
    print("\n🔋 Initializing rolling horizon optimizer...")
    optimizer = RollingHorizonOptimizer(
        config=config,
        battery_kwh=30.0,  # 30 kWh battery
        battery_kw=30.0    # 30 kW power rating
    )

    # Initialize state with simulation start time (use first timestamp which is timezone-aware)
    sim_start = timestamps[0].to_pydatetime().replace(tzinfo=None)
    month_start = sim_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    state = BatterySystemState(
        current_soc_kwh=15.0,  # 50% SOC
        battery_capacity_kwh=30.0,
        current_monthly_peak_kw=50.0,  # Start with 50 kW peak
        power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(config.tariff),
        last_update=sim_start,
        month_start_date=month_start
    )

    print(f"  Battery: 30.0 kWh, 30.0 kW")
    print(f"  SOC: {state.current_soc_kwh:.2f} kWh ({state.current_soc_kwh/30.0*100:.1f}%)")
    print(f"  Monthly peak: {state.current_monthly_peak_kw:.2f} kW")

    # ========================================================================
    # RESAMPLE TO 15-MINUTE RESOLUTION (required by RollingHorizonOptimizer)
    # ========================================================================
    print(f"\n⏱️  Resampling data to 15-minute resolution (optimizer requirement)...")

    # Create DataFrame for resampling
    df_hourly = pd.DataFrame({
        'pv': pv_production,
        'load': load_consumption,
        'price': spot_prices
    }, index=timestamps)

    # Resample from 1h to 15min (forward fill for constant values over each hour)
    df_15min = df_hourly.resample('15min').ffill()

    # Extract resampled data
    pv_15min = df_15min['pv'].values
    load_15min = df_15min['load'].values
    prices_15min = df_15min['price'].values
    timestamps_15min = df_15min.index

    # Convert to naive datetime (remove timezone)
    timestamps_15min_naive = pd.DatetimeIndex([ts.replace(tzinfo=None) for ts in timestamps_15min])

    print(f"  ✓ Resampled to {len(pv_15min)} timesteps (15-min resolution)")
    print(f"  From: {timestamps_15min_naive[0]}")
    print(f"  To: {timestamps_15min_naive[-1]}")

    # ========================================================================
    # RUN ROLLING HORIZON SIMULATION
    # ========================================================================
    window_timesteps = 96  # 24 hours × 4 quarters = 96 timesteps @ 15-min
    step_timesteps = 96  # Non-overlapping windows

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

    total_windows = len(timestamps_15min_naive) // step_timesteps

    print(f"\n" + "="*80)
    print(f"Running {total_windows} optimization windows (15-min resolution)...")
    print("="*80)

    for w in range(total_windows):
        t_start = w * step_timesteps
        t_end = min(t_start + window_timesteps, len(timestamps_15min_naive))

        if t_end - t_start < window_timesteps:
            print(f"\nWindow {w}: Insufficient data, stopping")
            break

        # Get window data (15-min resolution)
        window_pv = pv_15min[t_start:t_end]
        window_load = load_15min[t_start:t_end]
        window_prices = prices_15min[t_start:t_end]
        window_timestamps = timestamps_15min_naive[t_start:t_end]

        # Optimize
        result = optimizer.optimize_24h(
            current_state=state,
            pv_production=window_pv,
            load_consumption=window_load,
            spot_prices=window_prices,
            timestamps=window_timestamps,
            verbose=(w % 5 == 0)  # Verbose output every 5 windows
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

    # ========================================================================
    # RESULTS ANALYSIS
    # ========================================================================
    print(f"\n" + "="*80)
    print("JUNE 2024 SIMULATION RESULTS (REAL DATA)")
    print("="*80)

    if results:
        df = pd.DataFrame(results)

        # Calculate MONTHLY power tariff
        max_peak_month = df['max_grid_import'].max()
        monthly_tariff_actual = config.tariff.get_power_cost(max_peak_month)

        print(f"\nMonthly Peak Tracking:")
        print(f"  Maximum peak across month: {max_peak_month:.2f} kW")
        print(f"  Monthly power tariff: {monthly_tariff_actual:,.2f} NOK/month")

        print(f"\nCost Summary for June 2024:")
        print(f"  Energy cost: {df['energy_cost'].sum():,.2f} NOK")
        print(f"  Power tariff (monthly): {monthly_tariff_actual:,.2f} NOK")
        print(f"  **Total cost: {df['energy_cost'].sum() + monthly_tariff_actual:,.2f} NOK**")

        print(f"\nOperational Summary:")
        print(f"  Final SOC: {df['final_soc'].iloc[-1]:.2f} kWh ({df['final_soc'].iloc[-1]/30.0*100:.1f}%)")
        print(f"  Final monthly peak: {state.current_monthly_peak_kw:.2f} kW")
        print(f"  Max grid import: {df['max_grid_import'].max():.2f} kW")
        print(f"  Avg daily energy cost: {df['energy_cost'].mean():.2f} NOK/day")

        # ====================================================================
        # GENERATE PLOTS
        # ====================================================================
        df_detailed = pd.DataFrame(detailed_results)
        df_detailed.set_index('timestamps', inplace=True)

        print(f"\n" + "="*80)
        print("GENERATING PLOTS")
        print("="*80)

        fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)

        # Plot 1: Power flows
        ax = axes[0]
        ax.plot(df_detailed.index, df_detailed['pv'], label='PV Production (PVGIS)', color='orange', alpha=0.7)
        ax.plot(df_detailed.index, df_detailed['load'], label='Load (Commercial Office)', color='red', alpha=0.7)
        ax.plot(df_detailed.index, df_detailed['grid_import'], label='Grid Import', color='blue', alpha=0.7)
        ax.plot(df_detailed.index, -df_detailed['grid_export'], label='Grid Export', color='green', alpha=0.7)
        ax.axhline(y=max_peak_month, color='red', linestyle='--', label=f'Monthly Peak ({max_peak_month:.1f} kW)')
        ax.set_ylabel('Power [kW]')
        ax.set_title('June 2024: Power Flows (REAL DATA)')
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

        # Plot 4: Spot prices (REAL ENTSO-E data)
        ax = axes[3]
        ax.plot(df_detailed.index, df_detailed['spot_price'], label='Spot Price (ENTSO-E NO2)', color='brown', linewidth=1)
        ax.set_ylabel('Price [NOK/kWh]')
        ax.set_xlabel('Date')
        ax.set_title('Electricity Spot Prices (REAL DATA)')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = '/mnt/c/Users/klaus/klauspython/SDE/battery_optimization/results/june_2024_real_data.png'
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        print(f"  ✓ Saved plot: {plot_path}")

        # Zoomed view of first 7 days
        fig2, axes2 = plt.subplots(4, 1, figsize=(14, 12), sharex=True)

        zoom_end = min(7*24, len(df_detailed))  # 7 days × 24 hours
        df_zoom = df_detailed.iloc[:zoom_end]

        # Plot 1: Power flows (zoomed)
        ax = axes2[0]
        ax.plot(df_zoom.index, df_zoom['pv'], label='PV Production', color='orange', linewidth=2)
        ax.plot(df_zoom.index, df_zoom['load'], label='Load', color='red', linewidth=2)
        ax.plot(df_zoom.index, df_zoom['grid_import'], label='Grid Import', color='blue', linewidth=2)
        ax.plot(df_zoom.index, -df_zoom['grid_export'], label='Grid Export', color='green', linewidth=2)
        ax.axhline(y=max_peak_month, color='red', linestyle='--', label=f'Monthly Peak ({max_peak_month:.1f} kW)')
        ax.set_ylabel('Power [kW]')
        ax.set_title('June 1-7, 2024: Power Flows (Detailed)')
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
        plot_zoom_path = '/mnt/c/Users/klaus/klauspython/SDE/battery_optimization/results/june_2024_real_data_zoom.png'
        plt.savefig(plot_zoom_path, dpi=150, bbox_inches='tight')
        print(f"  ✓ Saved zoom plot: {plot_zoom_path}")

        print("="*80)
        return True
    else:
        print("\n❌ No results generated")
        return False


if __name__ == "__main__":
    import sys
    success = test_rolling_june()
    sys.exit(0 if success else 1)
