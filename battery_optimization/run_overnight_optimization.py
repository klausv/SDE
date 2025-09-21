#!/usr/bin/env python
"""
OVERNIGHT OPTIMIZATION RUN - Bruk den eksisterende optimizer med høyere presisjon
Kjører differential evolution med mange iterasjoner for å finne optimal løsning
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

from core.optimizer import BatteryOptimizer
from core.pvgis_solar import PVGISProduction
from core.entso_e_prices import ENTSOEPrices
# from core.consumption_profiles import create_consumption_profile  # Not needed

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('optimization_overnight.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

print("="*80)
print("🌙 NATTOPTIMERING - HØYPRESISJON BATTERIDIMENSJONERING")
print("="*80)
print(f"Start tid: {datetime.now()}")
print("Kjører differential evolution med høy presisjon")
print("Estimert kjøretid: 2-8 timer")
print("-"*80)

# System configuration
SYSTEM_CONFIG = {
    'pv_capacity_kwp': 150,
    'inverter_capacity_kw': 110,
    'grid_limit_kw': 77,
    'location': {'lat': 58.97, 'lon': 5.73},  # Stavanger
    'annual_consumption_kwh': 90000,
    'battery_efficiency': 0.90,
    'min_soc': 0.10,
    'max_soc': 0.90
}

# Different battery cost scenarios to test
BATTERY_COSTS = [3000, 3500, 4000, 4500, 5000, 5500, 6000]

def run_high_precision_optimization():
    """
    Run optimization with high precision settings
    """
    start_time = time.time()

    # 1. FETCH DATA
    logger.info("Henter data...")

    # Get solar production
    pvgis = PVGISProduction(
        lat=SYSTEM_CONFIG['location']['lat'],
        lon=SYSTEM_CONFIG['location']['lon'],
        pv_capacity_kwp=SYSTEM_CONFIG['pv_capacity_kwp'],
        system_loss=7
    )
    production = pvgis.get_hourly_production()
    logger.info(f"Solproduksjon: {production.sum()/1000:.1f} MWh/år")

    # Get spot prices
    price_fetcher = ENTSOEPrices(cache_dir="data/spot_prices")
    spot_prices = price_fetcher.get_cached_or_fetch(
        start_date="2024-01-01",
        end_date="2024-12-31",
        area="NO2"
    )

    if spot_prices is None or len(spot_prices) == 0:
        logger.warning("Bruker simulerte priser")
        # Create realistic price pattern
        hours = pd.date_range('2024-01-01', periods=8760, freq='h')
        np.random.seed(42)

        # Base price with variations
        base = 0.80
        hourly = np.array([1.3 if 6 <= h.hour < 22 else 0.8 for h in hours])
        weekly = np.array([1.0 if h.dayofweek < 5 else 0.9 for h in hours])
        seasonal = np.array([1.2 if h.month <= 3 or h.month >= 10 else 0.9 for h in hours])
        noise = np.random.normal(1.0, 0.15, len(hours))

        spot_prices = pd.Series(
            base * hourly * weekly * seasonal * np.clip(noise, 0.7, 1.5),
            index=hours
        )

    logger.info(f"Spotpriser: gjennomsnitt {spot_prices.mean():.3f} NOK/kWh")

    # Create consumption profile (office pattern)
    annual_consumption = SYSTEM_CONFIG['annual_consumption_kwh']
    base_load = annual_consumption / 8760
    consumption_list = []

    for hour in production.index:
        if isinstance(hour, pd.Timestamp):
            h = hour.hour
            dow = hour.dayofweek
        else:
            h = 12  # Default
            dow = 1

        # Office pattern: higher during work hours
        if 7 <= h < 17 and dow < 5:  # Weekdays 07-17
            consumption_list.append(base_load * 1.5)
        else:
            consumption_list.append(base_load * 0.7)

    consumption = pd.Series(consumption_list, index=production.index)
    # Scale to match annual consumption
    consumption = consumption * (annual_consumption / consumption.sum())
    logger.info(f"Forbruk: {consumption.sum()/1000:.1f} MWh/år")

    # 2. RUN OPTIMIZATIONS FOR DIFFERENT COSTS
    results = []

    for battery_cost in BATTERY_COSTS:
        logger.info(f"\n{'='*60}")
        logger.info(f"Optimerer for batterikostnad: {battery_cost} NOK/kWh")
        logger.info(f"{'='*60}")

        # Create optimizer with HIGH PRECISION settings
        optimizer = BatteryOptimizer(
            grid_limit_kw=SYSTEM_CONFIG['grid_limit_kw'],
            efficiency=SYSTEM_CONFIG['battery_efficiency'],
            min_soc=SYSTEM_CONFIG['min_soc'],
            max_soc=SYSTEM_CONFIG['max_soc']
        )

        # Monkey-patch the optimize method to use higher precision
        original_optimize = optimizer.optimize

        def high_precision_optimize(production, consumption, spot_prices,
                                   target_battery_cost, capacity_range, power_range,
                                   min_hours_capacity):
            """Override with high precision settings"""
            from scipy.optimize import differential_evolution, NonlinearConstraint

            def objective(x):
                capacity_kwh, power_kw = x
                if capacity_kwh < min_hours_capacity * power_kw:
                    return 1e10

                operation = optimizer._simulate_battery_operation(
                    production=production,
                    consumption=consumption,
                    spot_prices=spot_prices,
                    capacity_kwh=capacity_kwh,
                    power_kw=power_kw
                )

                economics = optimizer._calculate_economics(
                    operation=operation,
                    capacity_kwh=capacity_kwh,
                    battery_cost_per_kwh=target_battery_cost
                )

                return -economics['npv']

            def constraint_func(x):
                capacity_kwh, power_kw = x
                return capacity_kwh - min_hours_capacity * power_kw

            constraint = NonlinearConstraint(constraint_func, 0, np.inf)

            # HIGH PRECISION SETTINGS
            result = differential_evolution(
                objective,
                bounds=[capacity_range, power_range],
                constraints=constraint,
                maxiter=100,  # Much higher than default 10
                popsize=15,   # Larger population
                tol=0.001,    # Tighter tolerance
                atol=0.001,   # Absolute tolerance
                workers=4,    # Use multiple cores
                updating='deferred',  # Better for parallel
                polish=True,  # Polish with L-BFGS-B at end
                seed=42,
                disp=True  # Show progress
            )

            # Build result using original method structure
            optimal_capacity, optimal_power = result.x

            # Run final simulation
            final_operation = optimizer._simulate_battery_operation(
                production=production,
                consumption=consumption,
                spot_prices=spot_prices,
                capacity_kwh=optimal_capacity,
                power_kw=optimal_power
            )

            final_economics = optimizer._calculate_economics(
                operation=final_operation,
                capacity_kwh=optimal_capacity,
                battery_cost_per_kwh=target_battery_cost
            )

            metrics = optimizer._calculate_metrics(final_operation)

            break_even_cost = optimizer._find_break_even_cost(
                production=production,
                consumption=consumption,
                spot_prices=spot_prices,
                capacity_kwh=optimal_capacity,
                power_kw=optimal_power
            )

            from core.optimizer import OptimizationResult
            return OptimizationResult(
                optimal_capacity_kwh=optimal_capacity,
                optimal_power_kw=optimal_power,
                optimal_c_rate=optimal_power / optimal_capacity,
                max_battery_cost_per_kwh=break_even_cost,
                npv_at_target_cost=final_economics['npv'],
                economic_results=final_economics,
                operation_metrics=metrics,
                hourly_operation=final_operation
            )

        # Replace with high precision version
        optimizer.optimize = high_precision_optimize

        try:
            # Run optimization
            opt_result = optimizer.optimize(
                production=production,
                consumption=consumption,
                spot_prices=spot_prices,
                target_battery_cost=battery_cost,
                capacity_range=(10, 200),
                power_range=(5, 100),
                min_hours_capacity=2.0
            )

            result = {
                'battery_cost': battery_cost,
                'optimal_kwh': opt_result.optimal_capacity_kwh,
                'optimal_kw': opt_result.optimal_power_kw,
                'c_rate': opt_result.optimal_c_rate,
                'hours': opt_result.optimal_capacity_kwh / opt_result.optimal_power_kw,
                'npv': opt_result.npv_at_target_cost,
                'annual_savings': opt_result.economic_results['annual_benefit'],
                'irr': opt_result.economic_results.get('irr', 0),
                'payback': opt_result.economic_results.get('payback_years', 999),
                'break_even_cost': opt_result.max_battery_cost_per_kwh,
                'curtailment_avoided': opt_result.operation_metrics['total_curtailment_avoided'],
                'cycles_per_year': opt_result.operation_metrics['cycles_per_year']
            }

            logger.info(f"✅ Optimal: {result['optimal_kwh']:.0f} kWh / {result['optimal_kw']:.0f} kW")
            logger.info(f"   NPV: {result['npv']:+,.0f} NOK")
            logger.info(f"   Break-even: {result['break_even_cost']:,.0f} NOK/kWh")

            results.append(result)

            # Save intermediate results
            pd.DataFrame(results).to_csv('results/overnight_optimization_results.csv', index=False)

        except Exception as e:
            logger.error(f"❌ Feilet for {battery_cost} NOK/kWh: {str(e)}")
            continue

    # 3. ANALYZE AND REPORT
    elapsed = time.time() - start_time
    logger.info(f"\n{'='*80}")
    logger.info(f"FERDIG! Kjøretid: {elapsed/3600:.1f} timer")
    logger.info(f"{'='*80}")

    if results:
        df = pd.DataFrame(results)

        # Find best for 5000 NOK/kWh (market price)
        market_result = df[df['battery_cost'] == 5000].iloc[0] if 5000 in df['battery_cost'].values else df.iloc[len(df)//2]

        print("\n📊 RESULTATER FOR ULIKE BATTERIKOSTNADER:")
        print("-"*80)
        print(f"{'Kr/kWh':>8} {'Optimal':>14} {'NPV':>12} {'IRR':>8} {'Payback':>8} {'Break-even':>12}")
        print(f"{'':>8} {'kWh / kW':>14} {'(NOK)':>12} {'(%)':>8} {'(år)':>8} {'(kr/kWh)':>12}")
        print("-"*80)

        for _, row in df.iterrows():
            print(f"{row['battery_cost']:8.0f} {row['optimal_kwh']:6.0f} / {row['optimal_kw']:5.0f} "
                  f"{row['npv']:12,.0f} {row['irr']:8.1f} {row['payback']:8.1f} "
                  f"{row['break_even_cost']:12,.0f}")

        # Save detailed Excel report
        with pd.ExcelWriter('results/overnight_optimization_report.xlsx') as writer:
            df.to_excel(writer, sheet_name='Summary', index=False)

            # Add detailed metrics sheet
            detailed_metrics = pd.DataFrame({
                'Metric': ['Optimal kapasitet (kWh)', 'Optimal effekt (kW)', 'C-rate',
                          'Timer batteri', 'NPV ved 5000 kr/kWh', 'Break-even kostnad',
                          'Årlige sykler', 'Avkortning unngått (MWh/år)'],
                'Verdi': [f"{market_result['optimal_kwh']:.0f}",
                         f"{market_result['optimal_kw']:.0f}",
                         f"{market_result['c_rate']:.2f}",
                         f"{market_result['hours']:.1f}",
                         f"{market_result['npv']:,.0f} NOK",
                         f"{market_result['break_even_cost']:,.0f} NOK/kWh",
                         f"{market_result['cycles_per_year']:.0f}",
                         f"{market_result['curtailment_avoided']/1000:.1f}"]
            })
            detailed_metrics.to_excel(writer, sheet_name='Detailed', index=False)

        logger.info(f"\n💾 Resultater lagret til Excel")

        # Create visualization
        import matplotlib.pyplot as plt
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        # NPV vs battery cost
        ax1.plot(df['battery_cost'], df['npv']/1000, 'o-', linewidth=2, markersize=8)
        ax1.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        ax1.set_xlabel('Batterikostnad (NOK/kWh)')
        ax1.set_ylabel('NPV (1000 NOK)')
        ax1.set_title('NPV vs Batterikostnad')
        ax1.grid(True, alpha=0.3)

        # Optimal size vs battery cost
        ax2.plot(df['battery_cost'], df['optimal_kwh'], 'o-', label='Kapasitet (kWh)', linewidth=2, markersize=8)
        ax2.plot(df['battery_cost'], df['optimal_kw'], 's-', label='Effekt (kW)', linewidth=2, markersize=8)
        ax2.set_xlabel('Batterikostnad (NOK/kWh)')
        ax2.set_ylabel('Optimal størrelse')
        ax2.set_title('Optimal Batteristørrelse')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # IRR vs battery cost
        ax3.plot(df['battery_cost'], df['irr'], 'o-', linewidth=2, markersize=8, color='green')
        ax3.axhline(y=10, color='orange', linestyle='--', alpha=0.5, label='10% hurdle')
        ax3.set_xlabel('Batterikostnad (NOK/kWh)')
        ax3.set_ylabel('IRR (%)')
        ax3.set_title('Internrente')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Payback vs battery cost
        ax4.plot(df['battery_cost'], df['payback'], 'o-', linewidth=2, markersize=8, color='red')
        ax4.axhline(y=10, color='orange', linestyle='--', alpha=0.5, label='10 år')
        ax4.axhline(y=15, color='red', linestyle='--', alpha=0.5, label='15 år levetid')
        ax4.set_xlabel('Batterikostnad (NOK/kWh)')
        ax4.set_ylabel('Tilbakebetalingstid (år)')
        ax4.set_title('Payback Period')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        ax4.set_ylim([0, 20])

        plt.suptitle('Høypresisjons Batteroptimering - Nattekjøring', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig('results/overnight_optimization_charts.png', dpi=150, bbox_inches='tight')
        logger.info("📊 Grafer lagret")

    logger.info(f"\n✅ Optimering fullført: {datetime.now()}")

if __name__ == "__main__":
    run_high_precision_optimization()