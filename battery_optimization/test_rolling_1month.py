"""
Quick test of rolling horizon for ONE MONTH simulation.

Tests with 1-hour resolution for faster iteration on bugs.
"""

import sys
from config import BatteryOptimizationConfig
from optimize_battery_dimensions import BatterySizingOptimizer

def test_rolling_horizon_1month():
    """Test 1-month simulation with rolling horizon for one battery configuration."""

    print("\n" + "="*70)
    print("ROLLING HORIZON 1-MONTH SIMULATION TEST")
    print("="*70)

    # Use optimal battery from previous optimization
    E_nom = 13.2  # kWh
    P_max = 10.0  # kW

    print(f"\nTesting battery: {E_nom} kWh, {P_max} kW")
    print(f"Resolution: 1 hour (PT1H)")
    print(f"Duration: 1 month (January 2024)")

    # Initialize optimizer
    config = BatteryOptimizationConfig()
    optimizer = BatterySizingOptimizer(
        config=config,
        year=2024,
        resolution='PT60M'  # 1-hour resolution for faster testing
    )

    print(f"\nData loaded: {len(optimizer.data['timestamps'])} timesteps")
    print(f"Time span: {optimizer.data['timestamps'][0]} to {optimizer.data['timestamps'][-1]}")

    # Limit to first month (January = ~744 hours)
    # Filter data to January only
    import pandas as pd
    timestamps = pd.Series(optimizer.data['timestamps'])
    jan_mask = (timestamps.dt.month == 1)

    # Create temporary data slice
    original_data = optimizer.data.copy()
    optimizer.data = {
        'timestamps': optimizer.data['timestamps'][jan_mask],
        'pv_production': optimizer.data['pv_production'][jan_mask],
        'load_consumption': optimizer.data['load_consumption'][jan_mask],
        'spot_prices': optimizer.data['spot_prices'][jan_mask]
    }

    print(f"\nFiltered to January: {len(optimizer.data['timestamps'])} timesteps")
    print(f"Time span: {optimizer.data['timestamps'][0]} to {optimizer.data['timestamps'][-1]}")

    # Evaluate this configuration
    print(f"\n{'='*70}")
    print(f"Running 1-month simulation with rolling 24h windows...")
    print(f"{'='*70}")

    result = optimizer.evaluate_npv(
        E_nom=E_nom,
        P_max=P_max,
        verbose=True,
        return_details=True
    )

    # Restore original data
    optimizer.data = original_data

    # Display results
    print(f"\n{'='*70}")
    print(f"RESULTS")
    print(f"{'='*70}")

    if isinstance(result, dict):
        print(f"✓ Simulation successful!")
        print(f"\nEconomic Performance:")
        print(f"  NPV: {result['npv']:,.0f} NOK")
        print(f"  Annual savings: {result['annual_savings']:,.0f} NOK")
        print(f"  Initial cost: {result['initial_cost']:,.0f} NOK")
        print(f"\nCost Analysis:")
        print(f"  Break-even cost: {result['breakeven_cost_per_kwh']:,.0f} NOK/kWh")
        print(f"  Actual cost: {result['actual_cost_per_kwh']:,.0f} NOK/kWh")

        if 'breakeven_cost_per_kwh' in result and result['breakeven_cost_per_kwh'] > 0:
            print(f"  Cost ratio: {result['actual_cost_per_kwh'] / result['breakeven_cost_per_kwh']:.2f}x")

        print(f"\n{'='*70}")
        print(f"TEST PASSED ✓")
        print(f"{'='*70}\n")
        return True
    else:
        print(f"❌ Simulation failed")
        print(f"\n{'='*70}")
        print(f"TEST FAILED ✗")
        print(f"{'='*70}\n")
        return False


if __name__ == "__main__":
    success = test_rolling_horizon_1month()
    sys.exit(0 if success else 1)
