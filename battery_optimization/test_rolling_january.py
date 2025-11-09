"""
Test rolling horizon optimizer for January 2024 with 15-min resolution.
Winter conditions: low solar, higher heating load.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from config import BatteryOptimizationConfig
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from operational.state_manager import BatterySystemState, calculate_average_power_tariff_rate

def test_rolling_january():
    """Simulate January 2024 with rolling horizon optimization (15-min resolution)."""

    print("\n" + "="*80)
    print("ROLLING HORIZON SIMULATION - JANUARY 2024 (WINTER CONDITIONS)")
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
    # Peak only 30 kW at noon, zero before 8am and after 4pm
    solar_elevation = np.maximum(0, np.sin(np.pi * (hours_of_day - 8) / 8))
    pv_production = 30.0 * solar_elevation  # 0-30 kW
    pv_production[hours_of_day < 8] = 0   # Night: before 8am
    pv_production[hours_of_day > 16] = 0  # Night: after 4pm

    # Load consumption: Higher in winter due to heating
    # Base: 35 kW, Business hours boost: +20 kW, Evening peak: +10 kW
    load_base = 35.0  # 35 kW baseline (winter heating)
    load_daytime = load_base + 20.0 * ((hours_of_day >= 8) & (hours_of_day <= 17))
    load_evening_peak = 10.0 * ((hours_of_day >= 17) & (hours_of_day <= 20))
    load_consumption = load_base + (load_daytime - load_base) + load_evening_peak

    # Spot prices: Winter pattern (higher overall, peaks during cold days)
    # Base: 0.60 NOK/kWh
    # Morning peak (06-09): 0.90 NOK/kWh
    # Evening peak (17-21): 1.00 NOK/kWh
    # Night (22-06): 0.40 NOK/kWh
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
    print(f"  Grid import needed: Always (solar < load)")

    # Initialize rolling horizon optimizer
    optimizer = RollingHorizonOptimizer(
        config=config,
        battery_kwh=30.0,  # 30 kWh battery
        battery_kw=30.0    # 30 kW power rating (increased for peak shaving capability)
    )

    # Initialize state with simulation start time
    state = BatterySystemState(
        current_soc_kwh=15.0,  # 50% SOC
        battery_capacity_kwh=30.0,
        current_monthly_peak_kw=50.0,  # Start with 50 kW peak (typical winter)
        power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(config.tariff),
        last_update=start_date,  # Set to simulation start to avoid month boundary bug
        month_start_date=start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    )

    print(f"\nInitial state:")
    print(f"  Battery: 30.0 kWh, 30.0 kW")
    print(f"  SOC: {state.current_soc_kwh:.2f} kWh ({state.current_soc_kwh/30.0*100:.1f}%)")
    print(f"  Monthly peak: {state.current_monthly_peak_kw:.2f} kW")

    # Run rolling horizon simulation
    # 24-hour windows (96 timesteps @ 15min), step forward 24 hours each time
    window_timesteps = 96  # 24 hours × 4 quarters/hour
    step_timesteps = 96  # Non-overlapping windows for speed

    results = []
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
            verbose=(w % 5 == 0)  # Verbose output every 5 windows
        )

        if not result.success:
            print(f"\nWindow {w}: FAILED - {result.message}")
            break

        # Store results
        results.append({
            'window': w,
            'date': window_timestamps[0].date(),
            'energy_cost': result.energy_cost,
            'peak_penalty_progressive': result.peak_penalty_cost,
            'peak_penalty_actual': result.peak_penalty_actual,
            'objective_progressive': result.objective_value,
            'objective_actual': result.objective_value_actual,
            'final_soc': result.E_battery[-1],
            'max_grid_import': result.P_grid_import.max(),
        })

        # Update state for next window (use last timestep of current window)
        state.update_from_measurement(
            timestamp=window_timestamps[-1],
            soc_kwh=result.E_battery[-1],
            grid_import_power_kw=result.P_grid_import[-1]
        )

        # Brief progress update
        if (w + 1) % 5 == 0:
            print(f"  Progress: {w+1}/{total_windows} windows completed")

    print(f"\n" + "="*80)
    print("JANUARY 2024 SIMULATION RESULTS")
    print("="*80)

    if results:
        df = pd.DataFrame(results)

        # Calculate MONTHLY power tariff based on maximum peak across all windows
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
        print(f"  Min grid import: {df['max_grid_import'].min():.2f} kW")
        print(f"  Avg daily energy cost: {df['energy_cost'].mean():.2f} NOK/day")

        # Battery usage analysis
        print(f"\nBattery Performance:")
        soc_range = df['final_soc'].max() - df['final_soc'].min()
        print(f"  SOC range: {df['final_soc'].min():.2f} - {df['final_soc'].max():.2f} kWh")
        print(f"  Average final SOC: {df['final_soc'].mean():.2f} kWh ({df['final_soc'].mean()/30.0*100:.1f}%)")

        print(f"\n" + "="*80)
        return True
    else:
        print("\n❌ No results generated")
        return False


if __name__ == "__main__":
    import sys
    success = test_rolling_january()
    sys.exit(0 if success else 1)
