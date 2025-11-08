"""
Test script: Compare 1h vs 2h aggregation for break-even battery cost.

Tests same battery configuration with:
1. Full 1h resolution (baseline)
2. 2h temporal aggregation (fast)

Compares:
- Annual costs
- Break-even battery costs
- Computation time
- Error introduced by aggregation
"""

import time
from pathlib import Path

from optimize_battery_sizing_fast import FastBatterySizingOptimizer
from config import config


def test_single_battery_1h_vs_2h():
    """
    Test single battery configuration with both 1h and 2h resolution.

    Battery: 80 kWh / 50 kW (known good configuration)
    """
    print("\n" + "="*80)
    print("TEST: 1H VS 2H RESOLUTION - BREAK-EVEN COST COMPARISON")
    print("="*80)
    print()

    battery_kwh = 80
    battery_kw = 50

    print(f"Test battery: {battery_kwh} kWh / {battery_kw} kW")
    print()

    # Initialize optimizer
    optimizer = FastBatterySizingOptimizer(year=2025, aggregation_hours=2)

    # =========================================================================
    # Test 1: Full 1h resolution (BASELINE)
    # =========================================================================
    print("="*80)
    print("TEST 1: FULL 1H RESOLUTION (BASELINE)")
    print("="*80)
    print()

    start_1h = time.time()

    # Reference (no battery) with 1h
    print("Calculating reference (no battery) with 1h resolution...")
    ref_1h = optimizer.calculate_reference(use_aggregation=False)

    # Battery with 1h
    print(f"Optimizing {battery_kwh} kWh / {battery_kw} kW with 1h resolution...")
    result_1h = optimizer.optimize_battery_config(
        battery_kwh, battery_kw, ref_1h, use_aggregation=False
    )

    elapsed_1h = time.time() - start_1h

    print()
    print(f"✓ 1H Resolution Results:")
    print(f"  Reference cost: {ref_1h['annual_total_cost']:,.0f} kr/år")
    print(f"  Battery cost: {result_1h['annual_total_cost']:,.0f} kr/år")
    print(f"  Annual savings: {result_1h['annual_savings']:,.0f} kr")
    print(f"  NPV savings: {result_1h['npv_savings']:,.0f} kr")
    print(f"  BREAK-EVEN: {result_1h['breakeven_cost_per_kwh']:,.0f} kr/kWh")
    print(f"  Time: {elapsed_1h:.1f} seconds")
    print()

    # =========================================================================
    # Test 2: 2h aggregation (FAST)
    # =========================================================================
    print("="*80)
    print("TEST 2: 2H AGGREGATION (FAST)")
    print("="*80)
    print()

    start_2h = time.time()

    # Reference (no battery) with 2h
    print("Calculating reference (no battery) with 2h aggregation...")
    ref_2h = optimizer.calculate_reference(use_aggregation=True)

    # Battery with 2h
    print(f"Optimizing {battery_kwh} kWh / {battery_kw} kW with 2h aggregation...")
    result_2h = optimizer.optimize_battery_config(
        battery_kwh, battery_kw, ref_2h, use_aggregation=True
    )

    elapsed_2h = time.time() - start_2h

    print()
    print(f"✓ 2H Aggregation Results:")
    print(f"  Reference cost: {ref_2h['annual_total_cost']:,.0f} kr/år")
    print(f"  Battery cost: {result_2h['annual_total_cost']:,.0f} kr/år")
    print(f"  Annual savings: {result_2h['annual_savings']:,.0f} kr")
    print(f"  NPV savings: {result_2h['npv_savings']:,.0f} kr")
    print(f"  BREAK-EVEN: {result_2h['breakeven_cost_per_kwh']:,.0f} kr/kWh")
    print(f"  Time: {elapsed_2h:.1f} seconds")
    print()

    # =========================================================================
    # Comparison
    # =========================================================================
    print("="*80)
    print("COMPARISON: 1H VS 2H")
    print("="*80)
    print()

    # Errors
    ref_error = abs(ref_2h['annual_total_cost'] - ref_1h['annual_total_cost']) / ref_1h['annual_total_cost'] * 100
    battery_error = abs(result_2h['annual_total_cost'] - result_1h['annual_total_cost']) / result_1h['annual_total_cost'] * 100
    savings_error = abs(result_2h['annual_savings'] - result_1h['annual_savings']) / result_1h['annual_savings'] * 100
    breakeven_error = abs(result_2h['breakeven_cost_per_kwh'] - result_1h['breakeven_cost_per_kwh']) / result_1h['breakeven_cost_per_kwh'] * 100

    speedup = elapsed_1h / elapsed_2h

    print(f"{'Metric':<30} {'1h Resolution':<20} {'2h Aggregation':<20} {'Error %':<10}")
    print("-" * 80)
    print(f"{'Reference cost (kr/år)':<30} {ref_1h['annual_total_cost']:>19,.0f} {ref_2h['annual_total_cost']:>19,.0f} {ref_error:>9.2f}%")
    print(f"{'Battery cost (kr/år)':<30} {result_1h['annual_total_cost']:>19,.0f} {result_2h['annual_total_cost']:>19,.0f} {battery_error:>9.2f}%")
    print(f"{'Annual savings (kr)':<30} {result_1h['annual_savings']:>19,.0f} {result_2h['annual_savings']:>19,.0f} {savings_error:>9.2f}%")
    print(f"{'NPV savings (kr)':<30} {result_1h['npv_savings']:>19,.0f} {result_2h['npv_savings']:>19,.0f} {'-':>10}")
    print(f"{'Break-even (kr/kWh)':<30} {result_1h['breakeven_cost_per_kwh']:>19,.0f} {result_2h['breakeven_cost_per_kwh']:>19,.0f} {breakeven_error:>9.2f}%")
    print()
    print(f"{'Computation time (sec)':<30} {elapsed_1h:>19.1f} {elapsed_2h:>19.1f} {'-':>10}")
    print(f"{'Speedup':<30} {'1.0x':>19} {speedup:>18.1f}x {'-':>10}")
    print()

    # Assessment
    print("ASSESSMENT:")
    print("-" * 80)
    print()

    if breakeven_error < 2.0:
        print(f"✅ EXCELLENT: Break-even error {breakeven_error:.2f}% < 2%")
        print(f"   2h aggregation is suitable for battery sizing")
    elif breakeven_error < 5.0:
        print(f"✅ GOOD: Break-even error {breakeven_error:.2f}% < 5%")
        print(f"   2h aggregation acceptable for most use cases")
    elif breakeven_error < 10.0:
        print(f"⚠️  ACCEPTABLE: Break-even error {breakeven_error:.2f}% < 10%")
        print(f"   2h aggregation usable but verify critical decisions")
    else:
        print(f"❌ HIGH ERROR: Break-even error {breakeven_error:.2f}% > 10%")
        print(f"   2h aggregation not recommended")

    print()
    print(f"Performance gain: {speedup:.1f}x faster ({elapsed_1h:.1f}s → {elapsed_2h:.1f}s)")
    print()

    # Market comparison
    print("MARKET COMPARISON:")
    print("-" * 80)
    print()

    market_cost = config.battery.market_cost_nok_per_kwh
    target_cost = config.battery.target_cost_nok_per_kwh

    print(f"Market cost: {market_cost:,.0f} kr/kWh")
    print(f"Target cost: {target_cost:,.0f} kr/kWh")
    print()

    print(f"1h Break-even: {result_1h['breakeven_cost_per_kwh']:,.0f} kr/kWh")
    if result_1h['breakeven_cost_per_kwh'] >= market_cost:
        print(f"  ✅ PROFITABLE at market prices")
    elif result_1h['breakeven_cost_per_kwh'] >= target_cost:
        print(f"  ⚠️  POTENTIALLY VIABLE if costs reach {result_1h['breakeven_cost_per_kwh']:,.0f} kr/kWh")
    else:
        print(f"  ❌ NOT VIABLE at current market prices")

    print()
    print(f"2h Break-even: {result_2h['breakeven_cost_per_kwh']:,.0f} kr/kWh")
    if result_2h['breakeven_cost_per_kwh'] >= market_cost:
        print(f"  ✅ PROFITABLE at market prices")
    elif result_2h['breakeven_cost_per_kwh'] >= target_cost:
        print(f"  ⚠️  POTENTIALLY VIABLE if costs reach {result_2h['breakeven_cost_per_kwh']:,.0f} kr/kWh")
    else:
        print(f"  ❌ NOT VIABLE at current market prices")

    print()
    print("="*80)

    # Save results
    output_dir = Path(__file__).parent / 'results'
    output_dir.mkdir(exist_ok=True)

    import json
    results_file = output_dir / 'test_1h_vs_2h_comparison.json'
    with open(results_file, 'w') as f:
        json.dump({
            'battery_kwh': battery_kwh,
            'battery_kw': battery_kw,
            '1h_resolution': {
                'reference_cost': ref_1h['annual_total_cost'],
                'battery_cost': result_1h['annual_total_cost'],
                'annual_savings': result_1h['annual_savings'],
                'npv_savings': result_1h['npv_savings'],
                'breakeven_cost_per_kwh': result_1h['breakeven_cost_per_kwh'],
                'elapsed_time': elapsed_1h
            },
            '2h_aggregation': {
                'reference_cost': ref_2h['annual_total_cost'],
                'battery_cost': result_2h['annual_total_cost'],
                'annual_savings': result_2h['annual_savings'],
                'npv_savings': result_2h['npv_savings'],
                'breakeven_cost_per_kwh': result_2h['breakeven_cost_per_kwh'],
                'elapsed_time': elapsed_2h
            },
            'comparison': {
                'breakeven_error_pct': breakeven_error,
                'savings_error_pct': savings_error,
                'speedup': speedup
            }
        }, f, indent=2)

    print(f"\n✓ Results saved to {results_file}")
    print()

    return {
        '1h': result_1h,
        '2h': result_2h,
        'breakeven_error_pct': breakeven_error,
        'speedup': speedup
    }


if __name__ == "__main__":
    result = test_single_battery_1h_vs_2h()
