"""
Test progressive LP formulation with step function post-processing.
"""

import numpy as np
import pandas as pd
from config import BatteryOptimizationConfig
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from operational.state_manager import BatterySystemState, calculate_average_power_tariff_rate

def test_progressive_with_actual():
    """Test that progressive LP + step function post-processing works correctly."""

    print("\n" + "="*70)
    print("PROGRESSIVE LP + STEP FUNCTION POST-PROCESSING TEST")
    print("="*70)

    # Load configuration
    config = BatteryOptimizationConfig()

    # Create simple test data (24 hours, 15-min resolution = 96 timesteps)
    T = 96
    timestamps = pd.date_range('2024-01-01', periods=T, freq='15min')

    # Simple scenario: constant PV, constant load, constant prices
    pv_production = np.full(T, 40.0)  # 40 kW constant
    load_consumption = np.full(T, 30.0)  # 30 kW constant
    spot_prices = np.full(T, 0.50)  # 0.50 NOK/kWh

    # Initialize rolling horizon optimizer
    optimizer = RollingHorizonOptimizer(
        config=config,
        battery_kwh=13.2,
        battery_kw=10.0
    )

    # Initialize state with 45 kW peak
    state = BatterySystemState(
        current_soc_kwh=6.6,  # 50% SOC
        battery_capacity_kwh=13.2,
        current_monthly_peak_kw=45.0,
        power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(config.tariff)
    )

    print(f"\nInitial state:")
    print(f"  Monthly peak: {state.current_monthly_peak_kw:.2f} kW")
    print(f"  SOC: {state.current_soc_kwh:.2f} kWh ({state.current_soc_kwh/13.2*100:.1f}%)")

    # Optimize
    result = optimizer.optimize_24h(
        current_state=state,
        pv_production=pv_production,
        load_consumption=load_consumption,
        spot_prices=spot_prices,
        timestamps=timestamps,
        verbose=True
    )

    if result.success:
        print(f"\n" + "="*70)
        print("COST COMPARISON:")
        print("="*70)
        print(f"Progressive LP costs (used for optimization):")
        print(f"  Energy cost: {result.energy_cost:,.2f} NOK")
        print(f"  Peak penalty: {result.peak_penalty_cost:,.2f} NOK")
        print(f"  Total: {result.objective_value:,.2f} NOK")
        print(f"\nActual step function costs (for reporting):")
        print(f"  Energy cost: {result.energy_cost:,.2f} NOK (same)")
        print(f"  Peak penalty: {result.peak_penalty_actual:,.2f} NOK")
        print(f"  Total: {result.objective_value_actual:,.2f} NOK")
        print(f"\nDifference:")
        print(f"  Peak penalty: {result.peak_penalty_actual - result.peak_penalty_cost:+.2f} NOK")
        print(f"  Total: {result.objective_value_actual - result.objective_value:+.2f} NOK")
        print("="*70)
        return True
    else:
        print(f"\n❌ Optimization failed: {result.message}")
        return False


if __name__ == "__main__":
    import sys
    success = test_progressive_with_actual()
    sys.exit(0 if success else 1)
