"""
Simple test script for LFP battery degradation modeling in LP optimizer.

Tests:
1. Basic degradation constraint functionality
2. Cost separation (battery vs system)
3. Degradation enabled vs disabled comparison
"""

import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import BatteryOptimizationConfig, DegradationConfig
from core.lp_monthly_optimizer import MonthlyLPOptimizer

def create_test_config(degradation_enabled=False):
    """Create test configuration with degradation option"""
    config = BatteryOptimizationConfig()

    # Enable/disable degradation
    config.battery.degradation = DegradationConfig(
        enabled=degradation_enabled,
        cycle_life_full_dod=5000,
        calendar_life_years=28.0
    )

    return config

def create_simple_test_data(T=168):  # 1 week hourly
    """
    Create simple test data for one week.

    Scenario:
    - Constant load: 30 kW
    - Simple solar pattern: 0 at night, 50 kW during day (12 hours)
    - Constant spot price: 0.50 NOK/kWh
    """
    # Timestamps for one week
    timestamps = pd.date_range('2024-01-01', periods=T, freq='H')

    # Load: constant 30 kW
    load = np.full(T, 30.0)

    # Solar: simple pattern (50 kW during 8am-8pm, 0 otherwise)
    pv = np.array([50.0 if 8 <= ts.hour < 20 else 0.0 for ts in timestamps])

    # Spot prices: constant 0.50 NOK/kWh
    spot_prices = np.full(T, 0.50)

    return timestamps, load, pv, spot_prices

def test_degradation_basics():
    """Test 1: Basic degradation functionality"""
    print("=" * 80)
    print("TEST 1: Basic Degradation Functionality")
    print("=" * 80)

    # Create config with degradation enabled
    config = create_test_config(degradation_enabled=True)

    # Create optimizer (100 kWh, 50 kW battery)
    optimizer = MonthlyLPOptimizer(config, resolution='PT60M', battery_kwh=100, battery_kw=50)

    # Generate test data
    timestamps, load, pv, spot_prices = create_simple_test_data(T=168)

    # Run optimization
    result = optimizer.optimize_month(
        month_idx=1,
        pv_production=pv,
        load_consumption=load,
        spot_prices=spot_prices,
        timestamps=timestamps,
        E_initial=50.0  # 50% SOC
    )

    # Validate results
    print("\n" + "=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)

    assert result.success, "Optimization should succeed"
    print("✓ Optimization succeeded")

    assert result.degradation_cost > 0, "Degradation cost should be positive"
    print(f"✓ Degradation cost: {result.degradation_cost:,.2f} NOK")

    assert result.DP_total is not None, "DP_total should be populated"
    print(f"✓ Total degradation: {np.sum(result.DP_total):.4f}%")

    assert result.DP_cyc is not None, "DP_cyc should be populated"
    print(f"✓ Cyclic degradation: {np.sum(result.DP_cyc):.4f}%")

    assert result.DP_cal is not None, "DP_cal should be populated"
    print(f"✓ Calendar degradation per timestep: {result.DP_cal:.6f}%")

    # Check max{} operator: DP_total[t] >= max(DP_cyc[t], DP_cal)
    for t in range(len(result.DP_total)):
        expected_min = max(result.DP_cyc[t], result.DP_cal)
        assert result.DP_total[t] >= expected_min - 1e-6, f"DP_total[{t}] should be >= max(DP_cyc, DP_cal)"
    print("✓ Max operator constraint satisfied: DP[t] >= max(DP_cyc[t], DP_cal)")

    print("\nTest 1: PASSED ✓")
    return result

def test_cost_separation():
    """Test 2: Cost separation (battery vs system)"""
    print("\n" + "=" * 80)
    print("TEST 2: Cost Separation (Battery vs System)")
    print("=" * 80)

    config = create_test_config(degradation_enabled=True)

    # Battery costs
    battery_cost = config.battery.get_battery_cost()
    print(f"Battery cell cost: {battery_cost:,.0f} NOK/kWh")

    # System costs (100 kWh battery)
    system_cost_100kwh = config.battery.get_system_cost_per_kwh(100)
    print(f"System cost (100 kWh): {system_cost_100kwh:,.0f} NOK/kWh")

    # Validate separation
    assert battery_cost == 3054, f"Battery cost should be 3054 NOK/kWh, got {battery_cost}"
    print("✓ Battery cost correct: 3,054 NOK/kWh")

    # System cost = (3054 × 100 + 39726 + 1680) / 100 = 3,460 NOK/kWh
    expected_system_cost = (3054 * 100 + 39726 + 1680) / 100
    assert abs(system_cost_100kwh - expected_system_cost) < 1, \
        f"System cost should be ~{expected_system_cost:.0f}, got {system_cost_100kwh:.0f}"
    print(f"✓ System cost correct: {system_cost_100kwh:,.0f} NOK/kWh")

    print("\nTest 2: PASSED ✓")

def test_with_vs_without_degradation():
    """Test 3: Compare WITH vs WITHOUT degradation"""
    print("\n" + "=" * 80)
    print("TEST 3: WITH vs WITHOUT Degradation Comparison")
    print("=" * 80)

    # Test data
    timestamps, load, pv, spot_prices = create_simple_test_data(T=168)

    # Run WITHOUT degradation
    print("\n--- WITHOUT Degradation ---")
    config_no_deg = create_test_config(degradation_enabled=False)
    optimizer_no_deg = MonthlyLPOptimizer(config_no_deg, resolution='PT60M', battery_kwh=100, battery_kw=50)
    result_no_deg = optimizer_no_deg.optimize_month(
        month_idx=1,
        pv_production=pv,
        load_consumption=load,
        spot_prices=spot_prices,
        timestamps=timestamps,
        E_initial=50.0
    )

    # Run WITH degradation
    print("\n--- WITH Degradation ---")
    config_deg = create_test_config(degradation_enabled=True)
    optimizer_deg = MonthlyLPOptimizer(config_deg, resolution='PT60M', battery_kwh=100, battery_kw=50)
    result_deg = optimizer_deg.optimize_month(
        month_idx=1,
        pv_production=pv,
        load_consumption=load,
        spot_prices=spot_prices,
        timestamps=timestamps,
        E_initial=50.0
    )

    # Compare results
    print("\n" + "=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)

    print(f"\nCosts (WITHOUT degradation):")
    print(f"  Energy cost: {result_no_deg.energy_cost:,.2f} NOK")
    print(f"  Power cost: {result_no_deg.power_cost:,.2f} NOK")
    print(f"  Degradation cost: {result_no_deg.degradation_cost:,.2f} NOK")
    print(f"  Total: {result_no_deg.objective_value:,.2f} NOK")

    print(f"\nCosts (WITH degradation):")
    print(f"  Energy cost: {result_deg.energy_cost:,.2f} NOK")
    print(f"  Power cost: {result_deg.power_cost:,.2f} NOK")
    print(f"  Degradation cost: {result_deg.degradation_cost:,.2f} NOK")
    print(f"  Total: {result_deg.objective_value:,.2f} NOK")

    # Calculate differences
    cost_increase = result_deg.objective_value - result_no_deg.objective_value
    pct_increase = (cost_increase / result_no_deg.objective_value) * 100

    print(f"\nDegradation Impact:")
    print(f"  Cost increase: {cost_increase:,.2f} NOK")
    print(f"  Percentage increase: {pct_increase:.2f}%")

    # Validate
    assert result_deg.objective_value > result_no_deg.objective_value, \
        "WITH degradation should have higher cost than WITHOUT"
    print("✓ Cost with degradation > cost without degradation")

    assert result_deg.degradation_cost > 0, "Degradation cost should be positive"
    print(f"✓ Degradation cost: {result_deg.degradation_cost:,.2f} NOK")

    # Expected degradation cost should be reasonable relative to total costs
    # For LFP with 0.02%/cycle degradation, it's reasonable to be 5-20% of energy cost
    assert result_deg.degradation_cost < result_deg.energy_cost * 0.25, \
        "Degradation cost should be <25% of energy cost for one week"
    print(f"✓ Degradation cost is reasonable: {result_deg.degradation_cost/result_deg.energy_cost*100:.1f}% of energy cost")

    print("\nTest 3: PASSED ✓")

    return result_no_deg, result_deg

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("LFP BATTERY DEGRADATION MODEL - SIMPLE VALIDATION TESTS")
    print("="*80)

    try:
        # Test 1: Basic functionality
        result_with_deg = test_degradation_basics()

        # Test 2: Cost separation
        test_cost_separation()

        # Test 3: Comparison
        result_no_deg, result_deg = test_with_vs_without_degradation()

        # Summary
        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80)
        print("\nLFP degradation model implementation validated successfully!")
        print(f"\nKey Results:")
        print(f"  - Degradation modeling: WORKING")
        print(f"  - Cost separation: CORRECT")
        print(f"  - LP formulation: STABLE")
        print(f"  - Degradation cost (1 week, 100kWh): ~{result_deg.degradation_cost:.2f} NOK")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
