"""
Simplest possible rolling horizon test - just run the optimizer on January data.
No NPV calculation, just check window costs.
"""

import numpy as np
import pandas as pd
from config import BatteryOptimizationConfig
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from operational.state_manager import BatterySystemState, calculate_average_power_tariff_rate
from core.price_fetcher import fetch_and_process_prices

def test_rolling_simple():
    """Test rolling horizon with January 2024 data, 1-hour resolution."""

    print("\n" + "="*70)
    print("SIMPLE ROLLING HORIZON TEST - JANUARY 2024, 1-HOUR RESOLUTION")
    print("="*70)

    # Load configuration
    config = BatteryOptimizationConfig()

    # Fetch price data for 2024
    print("\nFetching price data...")
    price_data = fetch_and_process_prices(
        year=2024,
        bidding_zone='NO2',
        config=config,
        resolution='PT60M',
        use_cache=True
    )

    # Filter to January only
    timestamps = pd.to_datetime(price_data['timestamp'])
    jan_mask = (timestamps.dt.month == 1)

    print(f"Total timesteps: {len(timestamps)}")
    print(f"January timesteps: {jan_mask.sum()}")

    # Create January data
    jan_timestamps = timestamps[jan_mask].reset_index(drop=True)
    jan_prices = price_data['price_nok_per_kwh'].values[jan_mask]

    # For testing: use simple synthetic PV and load
    # PV: 0 at night (0-6am, 8pm-midnight), peak 40 kW at noon
    # Load: constant 30 kW
    hours = np.array([ts.hour for ts in jan_timestamps])
    pv_production = np.maximum(0, 40 * np.sin(np.pi * (hours - 6) / 14))
    pv_production[hours < 6] = 0
    pv_production[hours > 20] = 0
    load_consumption = np.full(len(jan_timestamps), 30.0)

    print(f"\nData summary:")
    print(f"  Timestamps: {len(jan_timestamps)}")
    print(f"  Date range: {jan_timestamps.iloc[0]} to {jan_timestamps.iloc[-1]}")
    print(f"  Spot prices: {jan_prices.min():.2f} - {jan_prices.max():.2f} NOK/kWh")
    print(f"  PV production: {pv_production.min():.1f} - {pv_production.max():.1f} kW")
    print(f"  Load: {load_consumption.min():.1f} - {load_consumption.max():.1f} kW")

    # Initialize rolling horizon optimizer
    optimizer = RollingHorizonOptimizer(
        config=config,
        battery_kwh=13.2,
        battery_kw=10.0
    )

    # Initialize state
    state = BatterySystemState(
        current_soc_kwh=6.6,  # 50% SOC
        battery_capacity_kwh=13.2,
        current_monthly_peak_kw=45.0,
        power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(config.tariff)
    )

    print(f"\nInitial state: {state}")
    print(f"  Power tariff rate: {state.power_tariff_rate_nok_per_kw:.2f} NOK/kW/month")

    # Run first 3 windows to check costs
    print(f"\n{'='*70}")
    print("Running first 3 windows (24h each)")
    print(f"{'='*70}")

    horizon_hours = 24
    total_windows = len(jan_timestamps) // horizon_hours

    for w in range(min(3, total_windows)):
        t_start = w * horizon_hours
        t_end = min(t_start + horizon_hours, len(jan_timestamps))

        # Get window data
        window_pv = pv_production[t_start:t_end]
        window_load = load_consumption[t_start:t_end]
        window_prices = jan_prices[t_start:t_end]
        window_timestamps = jan_timestamps[t_start:t_end]

        # Optimize
        result = optimizer.optimize_24h(
            current_state=state,
            pv_production=window_pv,
            load_consumption=window_load,
            spot_prices=window_prices,
            timestamps=window_timestamps,
            verbose=False
        )

        if result.success:
            print(f"\nWindow {w}:")
            print(f"  Objective: {result.objective_value:,.2f} NOK")
            print(f"  Energy cost: {result.energy_cost:,.2f} NOK")
            print(f"  Peak penalty: {result.peak_penalty_cost:,.2f} NOK")
            print(f"  Final SOC: {result.E_battery_final:.2f} kWh")

            # Update state for next window
            state.update_from_measurement(
                timestamp=window_timestamps.iloc[-1],
                soc_kwh=result.E_battery_final,
                grid_import_power_kw=result.P_grid_import[-1] if len(result.P_grid_import) > 0 else 0.0
            )
        else:
            print(f"\nWindow {w}: FAILED - {result.message}")
            return False

    print(f"\n{'='*70}")
    print("TEST COMPLETE ✓")
    print(f"{'='*70}\n")
    return True


if __name__ == "__main__":
    import sys
    success = test_rolling_simple()
    sys.exit(0 if success else 1)
