"""
Test script for Rolling Horizon Optimizer.

Validates that the 24-hour LP formulation works correctly before
integrating into battery sizing workflow.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from config import BatteryOptimizationConfig
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from operational.state_manager import BatterySystemState, calculate_average_power_tariff_rate


def test_rolling_horizon_optimizer():
    """Test rolling horizon optimizer with synthetic 24h data."""

    print("\n" + "="*70)
    print("ROLLING HORIZON OPTIMIZER TEST")
    print("="*70)

    # Load configuration
    config = BatteryOptimizationConfig()

    # Initialize state manager
    state = BatterySystemState(
        current_soc_kwh=6.6,  # 50% of 13.2 kWh
        battery_capacity_kwh=13.2,
        current_monthly_peak_kw=45.0,  # Some existing peak
        power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(config.tariff)
    )

    print(f"\nInitial State: {state}")
    print(f"  Power tariff rate: {state.power_tariff_rate_nok_per_kw:.2f} NOK/kW/month")

    # Create 24-hour synthetic data (96 timesteps @ 15min)
    T = 96
    timestamps = pd.date_range(start='2024-06-15 00:00', periods=T, freq='15min')

    # PV production: ramp up from 6am, peak at noon, down by 8pm
    hours = np.array([ts.hour + ts.minute/60 for ts in timestamps])
    pv_production = np.maximum(0, 40 * np.sin(np.pi * (hours - 6) / 14))  # 0 to 40 kW
    pv_production[hours < 6] = 0
    pv_production[hours > 20] = 0

    # Load consumption: baseline 30 kW with peaks at morning (8am) and evening (7pm)
    load_consumption = 30 + 10 * np.sin(2 * np.pi * hours / 24)  # 20-40 kW variation

    # Spot prices: low at night (0.30), high during day (0.80)
    spot_prices = 0.30 + 0.50 * (hours > 6) * (hours < 22)  # Step function

    print(f"\n24-Hour Forecast Summary:")
    print(f"  PV production: {pv_production.min():.1f} - {pv_production.max():.1f} kW")
    print(f"  Load consumption: {load_consumption.min():.1f} - {load_consumption.max():.1f} kW")
    print(f"  Spot prices: {spot_prices.min():.2f} - {spot_prices.max():.2f} NOK/kWh")

    # Initialize optimizer with 13.2 kWh, 10 kW battery (from our optimal sizing)
    optimizer = RollingHorizonOptimizer(
        config=config,
        battery_kwh=13.2,
        battery_kw=10.0
    )

    # Optimize 24 hours
    print(f"\n{'='*70}")
    print(f"Running 24-hour optimization...")
    print(f"{'='*70}")

    result = optimizer.optimize_24h(
        current_state=state,
        pv_production=pv_production,
        load_consumption=load_consumption,
        spot_prices=spot_prices,
        timestamps=timestamps,
        verbose=True
    )

    # Display results
    print(f"\n{'='*70}")
    print(f"OPTIMIZATION RESULTS")
    print(f"{'='*70}")

    if result.success:
        print(f"✓ Optimization successful")
        print(f"\nCost Breakdown:")
        print(f"  Total cost: {result.objective_value:,.2f} NOK")
        print(f"  Energy cost: {result.energy_cost:,.2f} NOK")
        print(f"  Peak penalty: {result.peak_penalty_cost:,.2f} NOK")

        print(f"\nBattery Operation:")
        print(f"  Initial SOC: {result.E_battery[0]:.2f} kWh ({result.E_battery[0]/13.2*100:.1f}%)")
        print(f"  Final SOC: {result.E_battery_final:.2f} kWh ({result.E_battery_final/13.2*100:.1f}%)")
        print(f"  Max charge power: {result.P_charge.max():.2f} kW")
        print(f"  Max discharge power: {result.P_discharge.max():.2f} kW")
        print(f"  Total energy throughput: {np.sum(result.P_charge) * 0.25:.2f} kWh")

        print(f"\nGrid Interaction:")
        print(f"  Max grid import: {result.P_grid_import.max():.2f} kW")
        print(f"  Max grid export: {result.P_grid_export.max():.2f} kW")
        print(f"  Total curtailment: {np.sum(result.P_curtail) * 0.25:.2f} kWh")

        print(f"\nNext Control Action:")
        print(f"  Battery setpoint: {result.next_battery_setpoint_kw:.2f} kW")
        print(f"    (Charge={result.P_charge[0]:.2f} kW, Discharge={result.P_discharge[0]:.2f} kW)")

        print(f"\nPerformance:")
        print(f"  Solve time: {result.solve_time_seconds:.3f} seconds")

        # Check if solve time is acceptable for real-time use
        if result.solve_time_seconds < 1.0:
            print(f"  ✓ Fast enough for 15-min updates")
        else:
            print(f"  ⚠ May be too slow for real-time (target <1 sec)")

        print(f"\n{'='*70}")
        print(f"TEST PASSED ✓")
        print(f"{'='*70}\n")

        return True

    else:
        print(f"❌ Optimization failed: {result.message}")
        print(f"\n{'='*70}")
        print(f"TEST FAILED ✗")
        print(f"{'='*70}\n")
        return False


if __name__ == "__main__":
    success = test_rolling_horizon_optimizer()
    exit(0 if success else 1)
