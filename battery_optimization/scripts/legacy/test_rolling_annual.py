"""
Quick test of rolling horizon annual simulation.

Tests that the modified optimize_battery_dimensions.py works correctly
with rolling 24h optimization windows.
"""

import sys
from config import BatteryOptimizationConfig
from optimize_battery_dimensions import BatterySizingOptimizer

def test_rolling_horizon_annual():
    """Test annual simulation with rolling horizon for one battery configuration."""

    print("\n" + "="*70)
    print("ROLLING HORIZON ANNUAL SIMULATION TEST")
    print("="*70)

    # Use optimal battery from previous optimization
    E_nom = 13.2  # kWh
    P_max = 10.0  # kW

    print(f"\nTesting battery: {E_nom} kWh, {P_max} kW")

    # Initialize optimizer
    config = BatteryOptimizationConfig()
    optimizer = BatterySizingOptimizer(
        config=config,
        year=2024,
        resolution='PT15M'  # 15-minute resolution required for rolling horizon
    )

    print(f"\nData loaded: {len(optimizer.data['timestamps'])} timesteps")
    print(f"Time span: {optimizer.data['timestamps'][0]} to {optimizer.data['timestamps'][-1]}")

    # Evaluate this configuration
    print(f"\n{'='*70}")
    print(f"Running annual simulation with rolling 24h windows...")
    print(f"{'='*70}")

    result = optimizer.evaluate_npv(
        E_nom=E_nom,
        P_max=P_max,
        verbose=True,
        return_details=True
    )

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
        print(f"  Cost ratio: {result['actual_cost_per_kwh'] / result['breakeven_cost_per_kwh']:.2f}x")

        if result['npv'] > 0:
            print(f"\n✓ Positive NPV - Battery economically viable!")
        else:
            print(f"\n⚠ Negative NPV - Battery not viable at current costs")

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
    success = test_rolling_horizon_annual()
    sys.exit(0 if success else 1)
