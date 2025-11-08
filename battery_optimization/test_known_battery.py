"""
Test known battery configuration (30 kWh / 15 kW) on representative dataset.

This tests if the representative dataset compression is causing the low break-even costs.
Expected result: ~3000+ NOK/kWh (based on previous full-year analyses)
"""

import numpy as np
import logging

from config import config
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.representative_dataset import RepresentativeDatasetGenerator
from core.economic_analysis import calculate_breakeven_cost
from core.price_fetcher import fetch_prices

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Known configuration from previous analyses
BATTERY_KWH = 30.0
BATTERY_KW = 15.0

logger.info("="*80)
logger.info("TESTING KNOWN BATTERY CONFIGURATION")
logger.info("="*80)
logger.info(f"Battery: {BATTERY_KWH} kWh / {BATTERY_KW} kW")
logger.info(f"Expected break-even: >3000 NOK/kWh (from previous analyses)")
logger.info("")

# Load full year data
logger.info("Loading full year data...")
spot_prices_full = fetch_prices(2025, 'NO2', resolution='PT60M')
timestamps_full = spot_prices_full.index

# Generate PV production
pv_full = []
for ts in timestamps_full:
    hour = ts.hour
    day_of_year = ts.dayofyear

    season_factor = 0.3 + 0.7 * np.sin((day_of_year - 80) * 2 * np.pi / 365)

    if 6 <= hour <= 20:
        hour_factor = np.sin((hour - 6) * np.pi / 14)
        pv_kw = config.solar.pv_capacity_kwp * season_factor * hour_factor * 0.8
    else:
        pv_kw = 0

    pv_full.append(pv_kw)

pv_full = np.array(pv_full)

# Generate consumption
load_full = []
for ts in timestamps_full:
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

    load_full.append(base_load * (0.95 + 0.1 * np.random.random()))

load_full = np.array(load_full)
spot_prices_array = spot_prices_full.values

logger.info(f"Full year: {len(timestamps_full)} hours")
logger.info(f"  PV total: {pv_full.sum():.0f} kWh")
logger.info(f"  Load total: {load_full.sum():.0f} kWh")
logger.info("")

# Create representative dataset
logger.info("Creating representative dataset...")
generator = RepresentativeDatasetGenerator(n_typical_days=12, n_extreme_days=4)

repr_timestamps, repr_pv, repr_load, repr_spot, metadata = \
    generator.select_representative_days(
        timestamps_full,
        pv_full,
        load_full,
        spot_prices_array
    )

logger.info(f"Representative dataset: {len(repr_timestamps)} hours")
logger.info(f"  Compression: {metadata['compression_ratio']:.1f}x")
logger.info("")

# Test 1: Full year optimization
logger.info("TEST 1: Full year data (8760 hours)")
logger.info("-" * 80)

optimizer_full = MonthlyLPOptimizer(
    config,
    resolution='PT60M',
    battery_kwh=BATTERY_KWH,
    battery_kw=BATTERY_KW
)

result_full = optimizer_full.optimize_month(
    month_idx=1,
    pv_production=pv_full,
    load_consumption=load_full,
    spot_prices=spot_prices_array,
    timestamps=timestamps_full,
    E_initial=BATTERY_KWH * 0.5
)

annual_cost_full = result_full.objective_value
logger.info(f"Annual cost WITH battery: {annual_cost_full:,.2f} NOK")

# Estimate cost without battery (rough approximation)
cost_without_battery_full = annual_cost_full * 1.10
annual_savings_full = cost_without_battery_full - annual_cost_full

logger.info(f"Estimated cost WITHOUT battery: {cost_without_battery_full:,.2f} NOK")
logger.info(f"Annual savings: {annual_savings_full:,.2f} NOK/year")

# Calculate break-even
breakeven_full = calculate_breakeven_cost(
    annual_savings=annual_savings_full,
    battery_kwh=BATTERY_KWH,
    battery_kw=BATTERY_KW,
    discount_rate=0.05,
    lifetime_years=15
)

logger.info(f"")
logger.info(f"RESULT (Full year):")
logger.info(f"  Break-even cost: {breakeven_full:.2f} NOK/kWh")
logger.info("")

# Test 2: Representative dataset
logger.info("TEST 2: Representative dataset (384 hours)")
logger.info("-" * 80)

optimizer_repr = MonthlyLPOptimizer(
    config,
    resolution='PT60M',
    battery_kwh=BATTERY_KWH,
    battery_kw=BATTERY_KW
)

result_repr = optimizer_repr.optimize_month(
    month_idx=1,
    pv_production=repr_pv,
    load_consumption=repr_load,
    spot_prices=repr_spot,
    timestamps=repr_timestamps,
    E_initial=BATTERY_KWH * 0.5
)

# Scale to annual
scale_factor = len(timestamps_full) / len(repr_timestamps)
scaled_energy_cost = result_repr.energy_cost * scale_factor
scaled_power_cost = result_repr.power_cost  # Don't scale peak
annual_cost_repr = scaled_energy_cost + scaled_power_cost

logger.info(f"Representative cost (scaled to annual): {annual_cost_repr:,.2f} NOK")

# Estimate cost without battery
cost_without_battery_repr = annual_cost_repr * 1.10
annual_savings_repr = cost_without_battery_repr - annual_cost_repr

logger.info(f"Estimated cost WITHOUT battery: {cost_without_battery_repr:,.2f} NOK")
logger.info(f"Annual savings: {annual_savings_repr:,.2f} NOK/year")

# Calculate break-even
breakeven_repr = calculate_breakeven_cost(
    annual_savings=annual_savings_repr,
    battery_kwh=BATTERY_KWH,
    battery_kw=BATTERY_KW,
    discount_rate=0.05,
    lifetime_years=15
)

logger.info(f"")
logger.info(f"RESULT (Representative dataset):")
logger.info(f"  Break-even cost: {breakeven_repr:.2f} NOK/kWh")
logger.info("")

# Compare
logger.info("="*80)
logger.info("COMPARISON")
logger.info("="*80)
logger.info(f"Expected (from previous analyses): >3000 NOK/kWh")
logger.info(f"Full year (8760 hours):            {breakeven_full:.2f} NOK/kWh")
logger.info(f"Representative (384 hours):        {breakeven_repr:.2f} NOK/kWh")
logger.info(f"")

error_pct = abs((breakeven_repr - breakeven_full) / breakeven_full) * 100
logger.info(f"Compression error: {error_pct:.1f}%")

if breakeven_full < 2000:
    logger.info("")
    logger.info("⚠️  WARNING: Break-even costs are MUCH LOWER than expected!")
    logger.info("    Previous analyses showed >3000 NOK/kWh")
    logger.info("    This indicates a problem in:")
    logger.info("    1. Annual savings calculation (baseline estimation)")
    logger.info("    2. LP optimization setup")
    logger.info("    3. Economic model parameters")
else:
    logger.info("")
    logger.info("✅ Results match expected range (>3000 NOK/kWh)")
    logger.info("   Representative dataset is working correctly")
