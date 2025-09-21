#!/usr/bin/env python
"""
FULL MILP OPTIMIZATION - Kjør over natten (8 timer tilgjengelig)
Bruker Mixed Integer Linear Programming for eksakt optimal løsning
"""
import time
import numpy as np
import pandas as pd
from datetime import datetime
import logging
import sys
import os

# Add path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.optimization_real.milp_optimizer import MILPBatteryOptimizer
from core.pvgis_solar import PVGISProduction
from core.entso_e_prices import ENTSOEPrices

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("="*80)
print("🚀 FULL MILP OPTIMERING - NATTEKJØRING")
print("="*80)
print(f"Start tid: {datetime.now()}")
print("Estimert kjøretid: 2-8 timer avhengig av problemstørrelse")
print("-"*80)

# System parameters
SYSTEM_CONFIG = {
    'pv_capacity_kwp': 150,  # Full 150 kWp
    'inverter_capacity_kw': 110,
    'grid_limit_kw': 77,
    'location': {'lat': 58.97, 'lon': 5.73},  # Stavanger
    'annual_consumption_kwh': 90000,
    'battery_efficiency': 0.90,  # 90% round-trip
    'min_soc': 0.10,
    'max_soc': 0.90
}

# Economic parameters
ECONOMIC_CONFIG = {
    'discount_rate': 0.05,
    'project_lifetime_years': 15,
    'battery_cost_nok_per_kwh': 5000,  # Inkl. inverter
    'degradation_rate_annual': 0.02
}

# Test different battery configurations
BATTERY_CONFIGS_TO_TEST = [
    # (capacity_kwh, power_kw)
    (20, 10),   # Small, 2-hour
    (40, 20),   # Medium, 2-hour
    (60, 30),   # Medium-large, 2-hour
    (80, 40),   # Large, 2-hour
    (100, 50),  # Very large, 2-hour
    (60, 20),   # 3-hour battery
    (80, 20),   # 4-hour battery
    (100, 25),  # 4-hour battery
]

def run_milp_optimization(battery_kwh, battery_kw, production, consumption, spot_prices, config):
    """
    Run full MILP optimization for one battery configuration
    """
    logger.info(f"Starting MILP for {battery_kwh} kWh / {battery_kw} kW battery...")
    start_time = time.time()

    try:
        # Create optimizer
        # Create config objects for MILPBatteryOptimizer
        system_config = type('obj', (object,), {
            'grid_capacity_kw': config['grid_limit_kw'],
            'battery_efficiency': config['battery_efficiency'],
            'min_soc': config['min_soc'],
            'max_soc': config['max_soc']
        })()

        tariff = type('obj', (object,), {
            'power_tariff_brackets': [(2, 136), (5, 232), (10, 372), (15, 572),
                                     (20, 772), (25, 972), (50, 1772), (75, 2572),
                                     (100, 3372), (200, 5600)]
        })()

        economic_config = type('obj', (object,), {
            'discount_rate': config['discount_rate'],
            'battery_lifetime_years': config['project_lifetime_years']
        })()

        optimizer = MILPBatteryOptimizer(
            system_config=system_config,
            tariff=tariff,
            economic_config=economic_config
        )

        # Set solver parameters for overnight run
        solver_params = {
            'solver': 'CBC',  # Open source, no license needed
            'timeLimit': 7200,  # Max 2 hours per optimization
            'threads': 4,  # Use multiple cores
            'gapRel': 0.01,  # Accept 1% optimality gap
            'msg': 1  # Show solver progress
        }

        # Run optimization
        result = optimizer.optimize(
            production=production,
            consumption=consumption,
            spot_prices=spot_prices,
            solver_params=solver_params
        )

        elapsed_time = time.time() - start_time

        # Calculate economics
        from core.economic_analysis import EconomicAnalyzer
        analyzer = EconomicAnalyzer(
            discount_rate=ECONOMIC_CONFIG['discount_rate'],
            project_years=ECONOMIC_CONFIG['project_lifetime_years']
        )

        economics = analyzer.calculate_npv(
            annual_benefit=result['annual_savings'],
            investment_cost=battery_kwh * ECONOMIC_CONFIG['battery_cost_nok_per_kwh']
        )

        logger.info(f"✅ Completed in {elapsed_time/60:.1f} minutes")
        logger.info(f"   Annual savings: {result['annual_savings']:,.0f} NOK")
        logger.info(f"   NPV: {economics['npv']:+,.0f} NOK")
        logger.info(f"   Solver gap: {result.get('gap', 0)*100:.2f}%")

        return {
            'battery_kwh': battery_kwh,
            'battery_kw': battery_kw,
            'annual_savings': result['annual_savings'],
            'npv': economics['npv'],
            'irr': economics['irr'],
            'payback': economics['payback_years'],
            'computation_time': elapsed_time,
            'solver_gap': result.get('gap', 0),
            'detailed_results': result
        }

    except Exception as e:
        logger.error(f"❌ Failed: {str(e)}")
        return {
            'battery_kwh': battery_kwh,
            'battery_kw': battery_kw,
            'error': str(e),
            'computation_time': time.time() - start_time
        }

def main():
    """
    Main optimization loop - will run for up to 8 hours
    """
    overall_start = time.time()
    max_runtime_hours = 8

    # 1. FETCH DATA
    print("\n📊 HENTER DATA...")
    print("-"*40)

    # Get solar production data
    print("Henter solproduksjon fra PVGIS...")
    pvgis = PVGISProduction(
        lat=SYSTEM_CONFIG['location']['lat'],
        lon=SYSTEM_CONFIG['location']['lon'],
        pv_capacity_kwp=SYSTEM_CONFIG['pv_capacity_kwp'],
        system_loss=7  # 7% loss
    )
    hourly_production = pvgis.fetch_hourly_production()
    print(f"✓ Hentet {len(hourly_production)} timer med produksjonsdata")
    print(f"  Total årsproduksjon: {hourly_production.sum()/1000:.1f} MWh")

    # Get spot prices
    print("\nHenter spotpriser...")
    price_fetcher = ENTSOEPrices()
    spot_prices = price_fetcher.fetch_prices(
        year=2023,
        area="NO2"
    )

    if spot_prices is None or len(spot_prices) == 0:
        print("⚠️ Ingen prisdata - bruker simulerte priser")
        # Create realistic price pattern
        hours = pd.date_range('2024-01-01', periods=8760, freq='h')
        base_price = 0.80  # 80 øre/kWh base

        # Daily pattern: higher during day
        hour_of_day = np.array([h.hour for h in hours])
        daily_pattern = np.where((hour_of_day >= 6) & (hour_of_day < 22), 1.3, 0.8)

        # Weekly pattern: lower in weekends
        day_of_week = np.array([h.dayofweek for h in hours])
        weekly_pattern = np.where(day_of_week < 5, 1.0, 0.9)

        # Seasonal pattern: higher in winter
        month = np.array([h.month for h in hours])
        seasonal_pattern = np.where((month <= 3) | (month >= 10), 1.2, 0.9)

        # Random variation
        np.random.seed(42)
        random_variation = np.random.normal(1.0, 0.2, len(hours))
        random_variation = np.clip(random_variation, 0.5, 2.0)

        spot_prices = pd.Series(
            base_price * daily_pattern * weekly_pattern * seasonal_pattern * random_variation,
            index=hours
        )

    print(f"✓ Spotpriser: {spot_prices.mean():.3f} NOK/kWh gjennomsnitt")
    print(f"  Min: {spot_prices.min():.3f}, Max: {spot_prices.max():.3f}")

    # Create consumption profile (constant for simplicity, could be more complex)
    print("\nGenererer forbruksprofil...")
    annual_consumption = SYSTEM_CONFIG['annual_consumption_kwh']
    base_load = annual_consumption / 8760  # Constant base load

    # Add some daily variation (higher during work hours)
    consumption_profile = pd.Series(index=spot_prices.index, dtype=float)
    for idx in consumption_profile.index:
        hour = idx.hour
        if 7 <= hour < 17 and idx.dayofweek < 5:  # Weekday work hours
            consumption_profile[idx] = base_load * 1.5
        else:
            consumption_profile[idx] = base_load * 0.7

    # Scale to match annual consumption
    consumption_profile *= annual_consumption / consumption_profile.sum()
    print(f"✓ Forbruk: {consumption_profile.sum()/1000:.1f} MWh/år")

    # 2. RUN OPTIMIZATIONS
    print("\n🔧 KJØRER MILP-OPTIMERINGER...")
    print("-"*40)
    print(f"Tester {len(BATTERY_CONFIGS_TO_TEST)} batterikonfigurasjoner")
    print("Dette kan ta flere timer...\n")

    results = []

    for i, (battery_kwh, battery_kw) in enumerate(BATTERY_CONFIGS_TO_TEST):
        # Check if we've exceeded max runtime
        elapsed_hours = (time.time() - overall_start) / 3600
        if elapsed_hours > max_runtime_hours:
            logger.warning(f"⏰ Tidsbegrensning nådd ({max_runtime_hours} timer)")
            break

        print(f"\n[{i+1}/{len(BATTERY_CONFIGS_TO_TEST)}] Testing {battery_kwh} kWh / {battery_kw} kW")
        print(f"  C-rate: {battery_kw/battery_kwh:.2f}, Timer: {battery_kwh/battery_kw:.1f}h")

        result = run_milp_optimization(
            battery_kwh=battery_kwh,
            battery_kw=battery_kw,
            production=hourly_production,
            consumption=consumption_profile,
            spot_prices=spot_prices,
            config=SYSTEM_CONFIG
        )

        results.append(result)

        # Save intermediate results
        df_results = pd.DataFrame(results)
        df_results.to_csv('results/milp_optimization_results.csv', index=False)
        print(f"  Lagret mellomresultater til CSV")

    # 3. ANALYZE RESULTS
    print("\n📊 RESULTATER")
    print("="*80)

    # Convert to DataFrame for analysis
    df_results = pd.DataFrame(results)

    # Filter out errors
    df_success = df_results[~df_results['annual_savings'].isna()].copy()

    if len(df_success) > 0:
        # Find best configuration
        best_idx = df_success['npv'].idxmax()
        best = df_success.loc[best_idx]

        print(f"\n🏆 BESTE KONFIGURASJON:")
        print(f"  Batteri: {best['battery_kwh']:.0f} kWh / {best['battery_kw']:.0f} kW")
        print(f"  NPV: {best['npv']:+,.0f} NOK")
        print(f"  IRR: {best['irr']:.1f}%")
        print(f"  Payback: {best['payback']:.1f} år")
        print(f"  Årlig besparelse: {best['annual_savings']:,.0f} NOK")
        print(f"  Beregningstid: {best['computation_time']/60:.1f} minutter")

        # Show all results sorted by NPV
        print("\n📈 ALLE RESULTATER (sortert etter NPV):")
        print("-"*80)
        print(f"{'kWh':>6} {'kW':>6} {'C-rate':>8} {'Timer':>7} {'NPV (NOK)':>12} {'IRR':>6} {'Payback':>8} {'Tid (min)':>10}")
        print("-"*80)

        for _, row in df_success.sort_values('npv', ascending=False).iterrows():
            c_rate = row['battery_kw'] / row['battery_kwh']
            hours = row['battery_kwh'] / row['battery_kw']
            print(f"{row['battery_kwh']:6.0f} {row['battery_kw']:6.0f} {c_rate:8.2f} {hours:7.1f}h "
                  f"{row['npv']:+12,.0f} {row['irr']:6.1f}% {row['payback']:8.1f} år "
                  f"{row['computation_time']/60:10.1f}")

    else:
        print("❌ Ingen vellykkede optimeringer")

    # Save final results
    df_results.to_excel('results/milp_full_results.xlsx', index=False)
    print(f"\n💾 Lagret komplette resultater til Excel")

    total_time = time.time() - overall_start
    print(f"\n⏱️ Total kjøretid: {total_time/3600:.1f} timer")
    print(f"Ferdig: {datetime.now()}")
    print("="*80)

if __name__ == "__main__":
    main()