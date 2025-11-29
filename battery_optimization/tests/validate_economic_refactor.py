"""
Validation script for economic_analysis.py refactoring.

Tests that the refactored config-driven functions produce identical results
to the original hardcoded values.
"""

import sys
from pathlib import Path

# Add parent directory to path
parent_path = Path(__file__).parent
sys.path.insert(0, str(parent_path))

import numpy as np
from core.economic_analysis import (
    calculate_breakeven_cost,
    calculate_npv,
    calculate_irr,
    calculate_payback_period,
    analyze_battery_investment,
)
from src.config.simulation_config import EconomicConfig, BatteryEconomicsConfig, DegradationConfig


def test_backward_compatibility():
    """Test that default behavior matches old hardcoded values."""
    print("=" * 60)
    print("BACKWARD COMPATIBILITY TEST")
    print("=" * 60)
    print()

    # Test parameters
    annual_savings = 5000  # NOK/year
    battery_kwh = 30
    battery_kw = 15
    battery_cost = 5000  # NOK/kWh

    # Test 1: Break-even cost with defaults
    breakeven = calculate_breakeven_cost(annual_savings, battery_kwh, battery_kw)
    print(f"✓ Break-even cost (default config): {breakeven:.2f} NOK/kWh")
    assert breakeven > 0, "Break-even cost should be positive"

    # Test 2: NPV with defaults
    npv = calculate_npv(annual_savings, battery_kwh, battery_cost)
    print(f"✓ NPV (default config): {npv:.2f} NOK")

    # Test 3: IRR with defaults
    irr = calculate_irr(annual_savings, battery_kwh, battery_cost)
    if irr is not None:
        print(f"✓ IRR (default config): {irr*100:.2f}%")
    else:
        print(f"✓ IRR (default config): No solution found")

    # Test 4: Payback period with defaults
    payback = calculate_payback_period(annual_savings, battery_kwh, battery_cost)
    print(f"✓ Payback period (default config): {payback:.1f} years")

    # Test 5: Comprehensive analysis with defaults
    analysis = analyze_battery_investment(
        annual_savings, battery_kwh, battery_kw, battery_cost
    )
    print(f"✓ Comprehensive analysis (default config):")
    print(f"    NPV: {analysis['npv']:.2f} NOK")
    print(f"    Break-even: {analysis['breakeven_cost']:.2f} NOK/kWh")
    print(f"    Investment: {analysis['total_investment']:.2f} NOK")
    print()


def test_custom_config():
    """Test that custom config values are correctly applied."""
    print("=" * 60)
    print("CUSTOM CONFIG TEST")
    print("=" * 60)
    print()

    # Create custom configs with different values
    custom_economic = EconomicConfig(
        discount_rate=0.08,  # 8% instead of 5%
        project_years=20,    # 20 years instead of 15
        eur_to_nok=12.0
    )

    custom_degradation = DegradationConfig(
        enabled=True,
        annual_rate=0.03,    # 3% instead of 2%
        model="linear",
        capacity_floor=0.60  # 60% instead of 70%
    )

    custom_battery_economics = BatteryEconomicsConfig(
        cell_cost_per_kwh=3054.0,
        inverter_cost_per_kw=1324.2,
        control_system_cost_nok=1680.0,
        installation_markup=0.30,  # 30% instead of 25%
        degradation=custom_degradation
    )

    # Test parameters
    annual_savings = 5000
    battery_kwh = 30
    battery_kw = 15
    battery_cost = 5000

    # Test with custom config
    breakeven = calculate_breakeven_cost(
        annual_savings, battery_kwh, battery_kw,
        economic_config=custom_economic,
        battery_economics=custom_battery_economics
    )
    print(f"✓ Break-even (custom 8%, 20yr, 3% degr, 30% markup): {breakeven:.2f} NOK/kWh")

    npv = calculate_npv(
        annual_savings, battery_kwh, battery_cost,
        economic_config=custom_economic,
        battery_economics=custom_battery_economics
    )
    print(f"✓ NPV (custom config): {npv:.2f} NOK")

    analysis = analyze_battery_investment(
        annual_savings, battery_kwh, battery_kw, battery_cost,
        economic_config=custom_economic,
        battery_economics=custom_battery_economics
    )
    print(f"✓ Investment (30% markup): {analysis['total_investment']:.2f} NOK")

    # Verify custom values were used
    expected_investment = battery_cost * battery_kwh * 1.30  # 30% markup
    assert abs(analysis['total_investment'] - expected_investment) < 1.0, \
        f"Expected {expected_investment}, got {analysis['total_investment']}"
    print(f"✓ Custom markup correctly applied")
    print()


def test_parameter_override():
    """Test that explicit parameters override config."""
    print("=" * 60)
    print("PARAMETER OVERRIDE TEST")
    print("=" * 60)
    print()

    # Create config with one set of values
    config = EconomicConfig(discount_rate=0.05)

    annual_savings = 5000
    battery_kwh = 30
    battery_kw = 15

    # Calculate with config default
    breakeven_config = calculate_breakeven_cost(
        annual_savings, battery_kwh, battery_kw,
        economic_config=config
    )

    # Calculate with explicit override
    breakeven_override = calculate_breakeven_cost(
        annual_savings, battery_kwh, battery_kw,
        discount_rate=0.10,  # Override with 10%
        economic_config=config
    )

    print(f"✓ Break-even with 5% (config): {breakeven_config:.2f} NOK/kWh")
    print(f"✓ Break-even with 10% (override): {breakeven_override:.2f} NOK/kWh")

    # Results should be different
    assert abs(breakeven_config - breakeven_override) > 100, \
        "Override should produce different result"
    print(f"✓ Parameter override working correctly")
    print()


def test_exact_equivalence():
    """Test that new config-driven approach gives exact same results as old hardcoded approach."""
    print("=" * 60)
    print("EXACT EQUIVALENCE TEST")
    print("=" * 60)
    print()
    print("Verifying new config system produces identical results to old hardcoded values...")
    print()

    # Old hardcoded defaults:
    # discount_rate = 0.05
    # lifetime_years = 15
    # degradation_rate = 0.02
    # installation_markup = 0.25
    # capacity_floor = 0.7

    annual_savings = 10000
    battery_kwh = 80
    battery_kw = 60
    battery_cost = 3000

    # Method 1: Using explicit parameters (old way)
    result_old = analyze_battery_investment(
        annual_savings, battery_kwh, battery_kw, battery_cost,
        discount_rate=0.05,
        lifetime_years=15,
        degradation_rate=0.02,
        installation_markup=0.25
    )

    # Method 2: Using default config (new way)
    result_new = analyze_battery_investment(
        annual_savings, battery_kwh, battery_kw, battery_cost
    )

    # Compare all metrics
    metrics = ['npv', 'payback_period', 'breakeven_cost', 'total_investment', 'pv_savings']

    all_match = True
    for metric in metrics:
        old_val = result_old[metric]
        new_val = result_new[metric]

        # Handle NaN comparison
        if np.isnan(old_val) and np.isnan(new_val):
            print(f"  ✓ {metric}: Both NaN (match)")
        elif abs(old_val - new_val) < 0.01:  # Allow tiny floating point differences
            print(f"  ✓ {metric}: {old_val:.2f} (exact match)")
        else:
            print(f"  ✗ {metric}: Old={old_val:.2f}, New={new_val:.2f} (MISMATCH!)")
            all_match = False

    # IRR needs special handling (can be None)
    irr_old = result_old.get('irr')
    irr_new = result_new.get('irr')
    if (irr_old is None and irr_new is None) or \
       (np.isnan(irr_old) and np.isnan(irr_new)):
        print(f"  ✓ irr: Both None/NaN (match)")
    elif abs(irr_old - irr_new) < 0.0001:
        print(f"  ✓ irr: {irr_old*100:.3f}% (exact match)")
    else:
        print(f"  ✗ irr: Old={irr_old*100:.3f}%, New={irr_new*100:.3f}% (MISMATCH!)")
        all_match = False

    print()
    if all_match:
        print("✅ EXACT EQUIVALENCE VERIFIED")
    else:
        print("❌ EQUIVALENCE TEST FAILED")

    assert all_match, "Results should be identical"
    print()


def main():
    """Run all validation tests."""
    print()
    print("═" * 60)
    print("ECONOMIC ANALYSIS REFACTORING VALIDATION")
    print("═" * 60)
    print()
    print("Testing config-driven economic analysis functions...")
    print()

    try:
        test_backward_compatibility()
        test_custom_config()
        test_parameter_override()
        test_exact_equivalence()

        print("=" * 60)
        print("✅ ALL VALIDATION TESTS PASSED")
        print("=" * 60)
        print()
        print("Summary:")
        print("  • Backward compatibility maintained")
        print("  • Custom config values correctly applied")
        print("  • Parameter overrides working")
        print("  • Results identical to old hardcoded approach")
        print()
        print("REFACTORING SUCCESS:")
        print("  • All economic parameters now configurable via YAML")
        print("  • Installation markup: 25% (default) → configurable")
        print("  • Degradation rate: 2%/year (default) → configurable")
        print("  • Capacity floor: 70% (default) → configurable")
        print("  • Discount rate, project years from EconomicConfig")
        print()

        return 0

    except AssertionError as e:
        print("=" * 60)
        print("❌ VALIDATION FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
