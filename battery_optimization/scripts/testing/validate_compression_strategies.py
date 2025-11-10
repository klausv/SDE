"""
Validate different compression strategies for battery optimization.

Since months are INDEPENDENT (each LP run is separate), we can compress by:
1. Temporal aggregation (1h → 2h, 4h blocks per month)
2. Representative months (12 → 4 representative months, scale results)
3. Combined approach (representative months + temporal aggregation)

Tests accuracy vs speedup trade-offs.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import time
import json
from pathlib import Path

from config import config
from core.price_fetcher import fetch_prices
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.representative_periods import TemporalAggregator


def generate_full_year_data(year: int = 2025):
    """Generate full year of PV, load, and spot price data."""

    print("Generating full year data...")

    # Fetch spot prices
    spot_prices = fetch_prices(year, 'NO2', resolution='PT60M')
    timestamps = spot_prices.index

    # Generate PV production
    pv = []
    for ts in timestamps:
        hour = ts.hour
        day_of_year = ts.dayofyear

        season_factor = 0.3 + 0.7 * np.sin((day_of_year - 80) * 2 * np.pi / 365)

        if 6 <= hour <= 20:
            hour_factor = np.sin((hour - 6) * np.pi / 14)
            pv_kw = config.solar.pv_capacity_kwp * season_factor * hour_factor * 0.8
        else:
            pv_kw = 0

        pv.append(pv_kw)

    pv = np.array(pv)

    # Generate consumption
    load = []
    for ts in timestamps:
        hour = ts.hour
        is_weekday = ts.weekday() < 5
        day_of_year = ts.dayofyear

        season_factor = 1.2 - 0.4 * np.sin((day_of_year - 80) * 2 * np.pi / 365)

        if is_weekday:
            if 7 <= hour <= 16:
                base_load = 25 * season_factor
            elif 17 <= hour <= 22:
                base_load = 18 * season_factor
            else:
                base_load = 12 * season_factor
        else:
            base_load = 12 * season_factor

        load.append(base_load * (0.95 + 0.1 * np.random.random()))

    load = np.array(load)

    print(f"✓ Generated {len(timestamps)} hours of data")
    print(f"  PV total: {pv.sum()/1000:.1f} MWh")
    print(f"  Load total: {load.sum()/1000:.1f} MWh")
    print()

    return timestamps, pv, load, spot_prices.values


def run_baseline_full_year(
    timestamps, pv, load, spot,
    battery_kwh, battery_kw
):
    """
    Baseline: Run LP on all 12 months with hourly resolution.
    """
    print("="*80)
    print("BASELINE: FULL YEAR (12 MONTHS × ~730 HOURS)")
    print("="*80)
    print(f"Battery: {battery_kwh} kWh / {battery_kw} kW")
    print()

    start_time = time.time()

    optimizer = MonthlyLPOptimizer(
        config,
        resolution='PT60M',
        battery_kwh=battery_kwh,
        battery_kw=battery_kw
    )

    monthly_results = []

    for month in range(1, 13):
        # Extract month data
        month_mask = timestamps.month == month
        month_timestamps = timestamps[month_mask]
        month_pv = pv[month_mask]
        month_load = load[month_mask]
        month_spot = spot[month_mask]

        # Run LP
        result = optimizer.optimize_month(
            month_idx=month,
            pv_production=month_pv,
            load_consumption=month_load,
            spot_prices=month_spot,
            timestamps=month_timestamps,
            E_initial=battery_kwh * 0.5
        )

        monthly_results.append(result)

    elapsed = time.time() - start_time

    # Aggregate annual results
    annual_energy_cost = sum([r.energy_cost for r in monthly_results])
    annual_power_cost = sum([r.power_cost for r in monthly_results])
    annual_total = annual_energy_cost + annual_power_cost

    print()
    print(f"✓ Complete in {elapsed:.2f} seconds")
    print(f"  Annual energy cost: {annual_energy_cost:,.0f} kr")
    print(f"  Annual power cost: {annual_power_cost:,.0f} kr")
    print(f"  Annual total: {annual_total:,.0f} kr")
    print()

    return {
        'method': 'baseline_full_year',
        'annual_energy_cost': annual_energy_cost,
        'annual_power_cost': annual_power_cost,
        'annual_total_cost': annual_total,
        'elapsed_time': elapsed,
        'timesteps': len(timestamps),
        'speedup': 1.0
    }


def run_temporal_aggregation(
    timestamps, pv, load, spot,
    battery_kwh, battery_kw,
    agg_hours: int = 2
):
    """
    Temporal aggregation: Run LP on 12 months with aggregated resolution (2h or 4h blocks).
    """
    print("="*80)
    print(f"TEMPORAL AGGREGATION: {agg_hours}H BLOCKS")
    print("="*80)
    print(f"Battery: {battery_kwh} kWh / {battery_kw} kW")
    print()

    start_time = time.time()

    aggregator = TemporalAggregator(agg_hours)
    optimizer = MonthlyLPOptimizer(
        config,
        resolution='PT60M',
        battery_kwh=battery_kwh,
        battery_kw=battery_kw
    )

    # Override timestep
    optimizer.timestep_hours = agg_hours

    monthly_results = []
    total_timesteps = 0

    for month in range(1, 13):
        # Extract month data
        month_mask = timestamps.month == month
        month_timestamps = timestamps[month_mask]
        month_pv = pv[month_mask]
        month_load = load[month_mask]
        month_spot = spot[month_mask]

        # Aggregate
        ts_agg, pv_agg, load_agg, spot_agg = aggregator.aggregate(
            month_timestamps, month_pv, month_load, month_spot
        )

        total_timesteps += len(ts_agg)

        # Run LP
        result = optimizer.optimize_month(
            month_idx=month,
            pv_production=pv_agg,
            load_consumption=load_agg,
            spot_prices=spot_agg,
            timestamps=ts_agg,
            E_initial=battery_kwh * 0.5
        )

        monthly_results.append(result)

    elapsed = time.time() - start_time

    # Aggregate annual
    annual_energy_cost = sum([r.energy_cost for r in monthly_results])
    annual_power_cost = sum([r.power_cost for r in monthly_results])
    annual_total = annual_energy_cost + annual_power_cost

    print()
    print(f"✓ Complete in {elapsed:.2f} seconds")
    print(f"  Total timesteps: {total_timesteps}")
    print(f"  Annual energy cost: {annual_energy_cost:,.0f} kr")
    print(f"  Annual power cost: {annual_power_cost:,.0f} kr")
    print(f"  Annual total: {annual_total:,.0f} kr")
    print()

    return {
        'method': f'temporal_agg_{agg_hours}h',
        'annual_energy_cost': annual_energy_cost,
        'annual_power_cost': annual_power_cost,
        'annual_total_cost': annual_total,
        'elapsed_time': elapsed,
        'timesteps': total_timesteps,
        'speedup': None  # Will be calculated later
    }


def run_representative_months(
    timestamps, pv, load, spot,
    battery_kwh, battery_kw,
    representative_months: list = [1, 4, 7, 10]
):
    """
    Representative months: Run LP on selected months, scale to annual.
    """
    print("="*80)
    print(f"REPRESENTATIVE MONTHS: {representative_months}")
    print("="*80)
    print(f"Battery: {battery_kwh} kWh / {battery_kw} kW")
    print()

    start_time = time.time()

    optimizer = MonthlyLPOptimizer(
        config,
        resolution='PT60M',
        battery_kwh=battery_kwh,
        battery_kw=battery_kw
    )

    monthly_results = {}

    for month in representative_months:
        # Extract month data
        month_mask = timestamps.month == month
        month_timestamps = timestamps[month_mask]
        month_pv = pv[month_mask]
        month_load = load[month_mask]
        month_spot = spot[month_mask]

        # Run LP
        result = optimizer.optimize_month(
            month_idx=month,
            pv_production=month_pv,
            load_consumption=month_load,
            spot_prices=month_spot,
            timestamps=month_timestamps,
            E_initial=battery_kwh * 0.5
        )

        monthly_results[month] = result

    elapsed = time.time() - start_time

    # Scale to annual (each representative month represents 3 months)
    scale_factor = 12 / len(representative_months)

    annual_energy_cost = sum([r.energy_cost for r in monthly_results.values()]) * scale_factor
    annual_power_cost = sum([r.power_cost for r in monthly_results.values()]) * scale_factor
    annual_total = annual_energy_cost + annual_power_cost

    total_timesteps = sum([len(timestamps[timestamps.month == m]) for m in representative_months])

    print()
    print(f"✓ Complete in {elapsed:.2f} seconds")
    print(f"  Representative months: {representative_months}")
    print(f"  Scale factor: {scale_factor}x")
    print(f"  Annual energy cost: {annual_energy_cost:,.0f} kr")
    print(f"  Annual power cost: {annual_power_cost:,.0f} kr")
    print(f"  Annual total: {annual_total:,.0f} kr")
    print()

    return {
        'method': f'representative_months_{len(representative_months)}',
        'annual_energy_cost': annual_energy_cost,
        'annual_power_cost': annual_power_cost,
        'annual_total_cost': annual_total,
        'elapsed_time': elapsed,
        'timesteps': total_timesteps,
        'speedup': None
    }


def run_combined(
    timestamps, pv, load, spot,
    battery_kwh, battery_kw,
    representative_months: list = [1, 4, 7, 10],
    agg_hours: int = 2
):
    """
    Combined: Representative months + temporal aggregation.
    """
    print("="*80)
    print(f"COMBINED: {len(representative_months)} MONTHS × {agg_hours}H BLOCKS")
    print("="*80)
    print(f"Battery: {battery_kwh} kWh / {battery_kw} kW")
    print()

    start_time = time.time()

    aggregator = TemporalAggregator(agg_hours)
    optimizer = MonthlyLPOptimizer(
        config,
        resolution='PT60M',
        battery_kwh=battery_kwh,
        battery_kw=battery_kw
    )

    optimizer.timestep_hours = agg_hours

    monthly_results = {}
    total_timesteps = 0

    for month in representative_months:
        # Extract month data
        month_mask = timestamps.month == month
        month_timestamps = timestamps[month_mask]
        month_pv = pv[month_mask]
        month_load = load[month_mask]
        month_spot = spot[month_mask]

        # Aggregate
        ts_agg, pv_agg, load_agg, spot_agg = aggregator.aggregate(
            month_timestamps, month_pv, month_load, month_spot
        )

        total_timesteps += len(ts_agg)

        # Run LP
        result = optimizer.optimize_month(
            month_idx=month,
            pv_production=pv_agg,
            load_consumption=load_agg,
            spot_prices=spot_agg,
            timestamps=ts_agg,
            E_initial=battery_kwh * 0.5
        )

        monthly_results[month] = result

    elapsed = time.time() - start_time

    # Scale to annual
    scale_factor = 12 / len(representative_months)

    annual_energy_cost = sum([r.energy_cost for r in monthly_results.values()]) * scale_factor
    annual_power_cost = sum([r.power_cost for r in monthly_results.values()]) * scale_factor
    annual_total = annual_energy_cost + annual_power_cost

    print()
    print(f"✓ Complete in {elapsed:.2f} seconds")
    print(f"  Total timesteps: {total_timesteps}")
    print(f"  Annual energy cost: {annual_energy_cost:,.0f} kr")
    print(f"  Annual power cost: {annual_power_cost:,.0f} kr")
    print(f"  Annual total: {annual_total:,.0f} kr")
    print()

    return {
        'method': f'combined_{len(representative_months)}months_{agg_hours}h',
        'annual_energy_cost': annual_energy_cost,
        'annual_power_cost': annual_power_cost,
        'annual_total_cost': annual_total,
        'elapsed_time': elapsed,
        'timesteps': total_timesteps,
        'speedup': None
    }


def calculate_breakeven(result: dict, battery_kwh: float) -> float:
    """Calculate break-even battery cost from annual total cost."""

    # We need reference (no battery) cost to calculate savings
    # For now, return a placeholder - will be calculated in main comparison
    return 0.0


def compare_methods(results: list, baseline_result: dict):
    """
    Compare all methods against baseline.

    Calculate:
    - Error in annual cost
    - Speedup
    - Break-even cost difference
    """
    print("\n" + "="*80)
    print("COMPARISON: ALL METHODS")
    print("="*80)
    print()

    baseline_cost = baseline_result['annual_total_cost']
    baseline_time = baseline_result['elapsed_time']

    comparison = []

    for result in results:
        if result['method'] == 'baseline_full_year':
            continue

        cost = result['annual_total_cost']
        error = abs(cost - baseline_cost) / baseline_cost * 100
        speedup = baseline_time / result['elapsed_time']

        result['error_pct'] = error
        result['speedup'] = speedup

        comparison.append(result)

    # Print table
    print(f"{'Method':<35} {'Timesteps':<12} {'Time (s)':<10} {'Speedup':<10} {'Error %':<10}")
    print("-" * 80)

    print(f"{'Baseline (full year)':<35} {baseline_result['timesteps']:<12} "
          f"{baseline_result['elapsed_time']:<10.2f} {'1.0x':<10} {'0.00%':<10}")

    for res in comparison:
        print(f"{res['method']:<35} {res['timesteps']:<12} "
              f"{res['elapsed_time']:<10.2f} {res['speedup']:<10.1f}x {res['error_pct']:<10.2f}%")

    print()

    # Find best trade-offs
    print("RECOMMENDATIONS:")
    print("-" * 80)

    # Low error (<2%)
    low_error = [r for r in comparison if r['error_pct'] < 2.0]
    if low_error:
        best_low_error = max(low_error, key=lambda x: x['speedup'])
        print(f"✓ Best accuracy (<2% error): {best_low_error['method']}")
        print(f"  Speedup: {best_low_error['speedup']:.1f}x, Error: {best_low_error['error_pct']:.2f}%")
        print()

    # Medium error (<5%)
    medium_error = [r for r in comparison if r['error_pct'] < 5.0]
    if medium_error:
        best_medium_error = max(medium_error, key=lambda x: x['speedup'])
        print(f"✓ Best balance (<5% error): {best_medium_error['method']}")
        print(f"  Speedup: {best_medium_error['speedup']:.1f}x, Error: {best_medium_error['error_pct']:.2f}%")
        print()

    # Maximum speedup
    fastest = max(comparison, key=lambda x: x['speedup'])
    print(f"✓ Fastest: {fastest['method']}")
    print(f"  Speedup: {fastest['speedup']:.1f}x, Error: {fastest['error_pct']:.2f}%")
    print()

    return comparison


def main():
    """Run full validation of compression strategies."""

    print("\n" + "="*80)
    print("COMPRESSION STRATEGY VALIDATION")
    print("="*80)
    print()

    # Test battery configuration
    battery_kwh = 80
    battery_kw = 50

    # Generate full year data
    timestamps, pv, load, spot = generate_full_year_data(2025)

    # Run all methods
    results = []

    # 1. Baseline (full year)
    baseline = run_baseline_full_year(timestamps, pv, load, spot, battery_kwh, battery_kw)
    results.append(baseline)

    # 2. Temporal aggregation (2h)
    temp_2h = run_temporal_aggregation(timestamps, pv, load, spot, battery_kwh, battery_kw, agg_hours=2)
    results.append(temp_2h)

    # 3. Temporal aggregation (4h)
    temp_4h = run_temporal_aggregation(timestamps, pv, load, spot, battery_kwh, battery_kw, agg_hours=4)
    results.append(temp_4h)

    # 4. Representative months (4 months)
    rep_4m = run_representative_months(timestamps, pv, load, spot, battery_kwh, battery_kw,
                                       representative_months=[1, 4, 7, 10])
    results.append(rep_4m)

    # 5. Combined (4 months × 2h)
    combined_4m_2h = run_combined(timestamps, pv, load, spot, battery_kwh, battery_kw,
                                   representative_months=[1, 4, 7, 10], agg_hours=2)
    results.append(combined_4m_2h)

    # 6. Combined (4 months × 4h)
    combined_4m_4h = run_combined(timestamps, pv, load, spot, battery_kwh, battery_kw,
                                   representative_months=[1, 4, 7, 10], agg_hours=4)
    results.append(combined_4m_4h)

    # Compare all methods
    comparison = compare_methods(results, baseline)

    # Save results
    output_dir = Path(__file__).parent / 'results'
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / 'compression_validation.json', 'w') as f:
        json.dump({
            'battery_config': {'kwh': battery_kwh, 'kw': battery_kw},
            'baseline': baseline,
            'methods': comparison
        }, f, indent=2)

    print(f"\n✓ Results saved to {output_dir / 'compression_validation.json'}")
    print()


if __name__ == "__main__":
    main()
