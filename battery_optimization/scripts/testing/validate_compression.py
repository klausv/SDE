"""
Validate representative dataset compression against full-year data.

Compares LP optimization results between:
- Full month dataset (745 hours for October)
- Representative dataset (384 hours for full year)

Target: <2% error in key metrics
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys

from config import config
from core.price_fetcher import fetch_prices
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.representative_dataset import RepresentativeDatasetGenerator


def test_october_compression():
    """
    Test compression on October 2025 data.

    Steps:
    1. Load full October data (745 hours)
    2. Create representative dataset (select 16 days from October)
    3. Run LP optimization on both
    4. Compare results
    """

    print("=" * 80)
    print("COMPRESSION VALIDATION: Oktober 2025")
    print("=" * 80)
    print()

    # Battery configuration
    battery_kwh = 30
    battery_kw = 15

    print(f"Batteri: {battery_kwh} kWh / {battery_kw} kW")
    print()

    # =========================================================================
    # STEP 1: Load full Oktober data
    # =========================================================================
    print("=" * 80)
    print("FULL MONTH DATA (Oktober 2025)")
    print("=" * 80)

    start_date = datetime(2025, 10, 1)
    end_date = datetime(2025, 10, 31, 23, 59)

    # Fetch spot prices for full year, then filter to October
    full_prices = fetch_prices(2025, 'NO2', resolution='PT60M')

    # Filter to October
    mask = (full_prices.index >= pd.Timestamp(start_date, tz='Europe/Oslo')) & \
           (full_prices.index <= pd.Timestamp(end_date, tz='Europe/Oslo'))
    spot_prices_oct = full_prices[mask]
    timestamps_full = spot_prices_oct.index

    # Generate PV production (simplified model from compare_sept_oct_lp.py)
    pv_full = []
    for ts in timestamps_full:
        hour = ts.hour
        day_of_year = ts.dayofyear

        # Summer: higher production, Winter: lower production
        season_factor = 0.3 + 0.7 * np.sin((day_of_year - 80) * 2 * np.pi / 365)

        # Daily curve (6am-8pm solar window)
        if 6 <= hour <= 20:
            hour_factor = np.sin((hour - 6) * np.pi / 14)
            pv_kw = config.solar.pv_capacity_kwp * season_factor * hour_factor * 0.8
        else:
            pv_kw = 0

        pv_full.append(pv_kw)

    pv_full = pd.Series(pv_full, index=timestamps_full)

    # Generate consumption (commercial profile)
    load_full = []
    for ts in timestamps_full:
        hour = ts.hour
        is_weekday = ts.weekday() < 5
        day_of_year = ts.dayofyear

        # Seasonal factor (higher in winter)
        season_factor = 1.2 - 0.4 * np.sin((day_of_year - 80) * 2 * np.pi / 365)

        # Weekday vs weekend
        if is_weekday:
            if 7 <= hour <= 16:
                base_load = 25 * season_factor
            elif 17 <= hour <= 22:
                base_load = 18 * season_factor
            else:
                base_load = 12 * season_factor
        else:
            base_load = 12 * season_factor

        load_full.append(base_load * (0.95 + 0.1 * np.random.random()))

    load_full = pd.Series(load_full, index=timestamps_full)

    print(f"Timestamps: {len(timestamps_full)}")
    print(f"PV total: {pv_full.sum():.1f} kWh")
    print(f"Load total: {load_full.sum():.1f} kWh")

    # Calculate mean for spot prices (handle both Series and ndarray)
    if hasattr(spot_prices_oct, 'mean'):
        spot_mean = spot_prices_oct.mean()
    else:
        spot_mean = np.mean(spot_prices_oct)
    print(f"Spot avg: {spot_mean:.3f} kr/kWh")
    print()

    # Run LP optimization on full month
    print("Running LP optimization on full month...")
    optimizer_full = MonthlyLPOptimizer(
        config,
        resolution='PT60M',
        battery_kwh=battery_kwh,
        battery_kw=battery_kw
    )

    # Convert to values if needed
    spot_vals = spot_prices_oct.values if hasattr(spot_prices_oct, 'values') else spot_prices_oct
    pv_vals = pv_full.values if hasattr(pv_full, 'values') else pv_full
    load_vals = load_full.values if hasattr(load_full, 'values') else load_full

    result_full = optimizer_full.optimize_month(
        month_idx=10,
        pv_production=pv_vals,
        load_consumption=load_vals,
        spot_prices=spot_vals,
        timestamps=timestamps_full,
        E_initial=battery_kwh * 0.5
    )

    print(f"✓ Full month optimization complete")
    print(f"  Total cost: {result_full.objective_value:.2f} kr")
    print(f"  Energy cost: {result_full.energy_cost:.2f} kr")
    print(f"  Power cost: {result_full.power_cost:.2f} kr")
    print(f"  Peak power: {result_full.P_peak:.2f} kW")
    print()

    # =========================================================================
    # STEP 2: Create representative dataset from October
    # =========================================================================
    print("=" * 80)
    print("REPRESENTATIVE DATASET (16 days from Oktober)")
    print("=" * 80)

    generator = RepresentativeDatasetGenerator(n_typical_days=12, n_extreme_days=4)

    repr_timestamps, repr_pv, repr_load, repr_spot, metadata = generator.select_representative_days(
        timestamps_full,
        pv_full,
        load_full,
        spot_prices_oct.values
    )

    print(f"Selected {metadata['representative_hours']} hours from {len(metadata['typical_days'])} typical + {len(metadata['extreme_days'])} extreme days")
    print(f"Compression ratio: {metadata['compression_ratio']:.1f}x")
    print()

    print("Typical days:")
    for day in metadata['typical_days']:
        print(f"  - {day}")
    print()

    print("Extreme days:")
    for day in metadata['extreme_days']:
        print(f"  - {day}")
    print()

    # Run LP optimization on representative dataset
    print("Running LP optimization on representative dataset...")
    optimizer_repr = MonthlyLPOptimizer(
        config,
        resolution='PT60M',
        battery_kwh=battery_kwh,
        battery_kw=battery_kw
    )

    result_repr = optimizer_repr.optimize_month(
        month_idx=10,
        pv_production=repr_pv,
        load_consumption=repr_load,
        spot_prices=repr_spot,
        timestamps=repr_timestamps,
        E_initial=battery_kwh * 0.5
    )

    print(f"✓ Representative dataset optimization complete")
    print(f"  Total cost: {result_repr.objective_value:.2f} kr")
    print(f"  Energy cost: {result_repr.energy_cost:.2f} kr")
    print(f"  Power cost: {result_repr.power_cost:.2f} kr")
    print(f"  Peak power: {result_repr.P_peak:.2f} kW")
    print()

    # =========================================================================
    # STEP 3: Scale representative results to monthly basis
    # =========================================================================
    print("=" * 80)
    print("SCALING TO MONTHLY BASIS")
    print("=" * 80)

    # Calculate scaling factor for energy costs
    # Energy scales linearly with hours
    scale_factor = len(timestamps_full) / len(repr_timestamps)

    # Power cost doesn't scale - it's based on monthly peak which we already captured
    # Total cost = scaled energy cost + power cost (not scaled)

    scaled_energy_cost = result_repr.energy_cost * scale_factor
    scaled_power_cost = result_repr.power_cost  # Keep as-is
    scaled_total_cost = scaled_energy_cost + scaled_power_cost

    result_repr_scaled = {
        'total_cost': scaled_total_cost,
        'energy_cost': scaled_energy_cost,
        'power_cost': scaled_power_cost,
        'peak_import_kw': result_repr.P_peak,  # Max value doesn't scale
    }

    print(f"Scale factor: {scale_factor:.2f}x")
    print(f"Scaled results:")
    print(f"  Total cost: {result_repr_scaled['total_cost']:.2f} kr")
    print(f"  Energy cost: {result_repr_scaled['energy_cost']:.2f} kr")
    print(f"  Power cost: {result_repr_scaled['power_cost']:.2f} kr")
    print(f"  Peak power: {result_repr_scaled['peak_import_kw']:.2f} kW")
    print()

    # =========================================================================
    # STEP 4: Compare and validate
    # =========================================================================
    print("=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)
    print()

    metrics = [
        ('Total cost', 'total_cost', result_full.objective_value, result_repr_scaled['total_cost']),
        ('Energy cost', 'energy_cost', result_full.energy_cost, result_repr_scaled['energy_cost']),
        ('Power cost', 'power_cost', result_full.power_cost, result_repr_scaled['power_cost']),
        ('Peak power', 'peak_import_kw', result_full.P_peak, result_repr_scaled['peak_import_kw'])
    ]

    errors = []

    print(f"{'Metric':<20} {'Full':<15} {'Compressed':<15} {'Error':<10}")
    print("-" * 60)

    for name, key, full_val, compressed_val in metrics:
        if full_val != 0:
            error_pct = abs((compressed_val - full_val) / full_val) * 100
        else:
            error_pct = 0.0

        errors.append(error_pct)

        error_str = f"{error_pct:.2f}%"
        print(f"{name:<20} {full_val:<15.2f} {compressed_val:<15.2f} {error_str:<10}")

    print()
    avg_error = np.mean(errors)
    max_error = np.max(errors)

    print(f"Average error: {avg_error:.2f}%")
    print(f"Maximum error: {max_error:.2f}%")
    print()

    # Validation assessment
    if avg_error < 2.0:
        print("✓ VALIDATION PASSED: Average error <2%")
        validation_passed = True
    else:
        print("✗ VALIDATION FAILED: Average error ≥2%")
        validation_passed = False

    if max_error < 5.0:
        print("✓ Maximum error acceptable (<5%)")
    else:
        print("⚠ Maximum error high (≥5%)")

    print()
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)

    if validation_passed:
        print("Representative dataset compression is SUITABLE for optimization.")
        print(f"Can reduce computational time by {metadata['compression_ratio']:.0f}x with <2% error.")
    else:
        print("Representative dataset needs refinement.")
        print("Consider: More typical days, better extreme scenario selection, or different weighting.")

    return {
        'validation_passed': validation_passed,
        'avg_error': avg_error,
        'max_error': max_error,
        'compression_ratio': metadata['compression_ratio'],
        'full_result': result_full,
        'repr_result_scaled': result_repr_scaled
    }


if __name__ == "__main__":
    result = test_october_compression()

    if result['validation_passed']:
        sys.exit(0)
    else:
        sys.exit(1)
