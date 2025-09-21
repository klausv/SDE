#!/usr/bin/env python3
"""
Test script for battery optimization with 2023-2025 data focus
Uses differential evolution for optimization
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import pytz
import warnings
warnings.filterwarnings('ignore')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import SystemConfig, LnettTariff, BatteryConfig, EconomicConfig
from src.optimization.optimizer import BatteryOptimizer
from src.analysis.visualization import ResultVisualizer
from src.data_fetchers.solar_production import SolarProductionModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_realistic_2024_prices(n_hours: int = 8760) -> pd.Series:
    """
    Generate realistic NO2 prices based on 2023-2024 patterns
    Post energy-crisis "new normal" prices
    """
    # Base price levels (NOK/kWh) - higher than pre-2022 but lower than crisis peak
    summer_base = 0.50  # Apr-Sep
    winter_base = 0.85  # Oct-Mar

    # Create hourly timestamps for full year
    timestamps = pd.date_range(
        start='2024-01-01',
        periods=n_hours,
        freq='H',
        tz='Europe/Oslo'
    )

    prices = []
    for ts in timestamps:
        month = ts.month
        hour = ts.hour
        weekday = ts.weekday()

        # Seasonal base
        if 4 <= month <= 9:
            base_price = summer_base
        else:
            base_price = winter_base

        # Hourly pattern (typical for NO2)
        hourly_factors = {
            0: 0.85, 1: 0.82, 2: 0.80, 3: 0.78, 4: 0.77, 5: 0.80,  # Night
            6: 0.90, 7: 1.05, 8: 1.15, 9: 1.10, 10: 1.05, 11: 1.00,  # Morning
            12: 0.95, 13: 0.93, 14: 0.95, 15: 1.00, 16: 1.08, 17: 1.20,  # Afternoon/evening peak
            18: 1.25, 19: 1.22, 20: 1.15, 21: 1.05, 22: 0.95, 23: 0.88  # Evening
        }
        hour_factor = hourly_factors[hour]

        # Weekend reduction
        weekend_factor = 0.85 if weekday >= 5 else 1.0

        # Random volatility (±30% reflecting post-crisis volatility)
        daily_volatility = np.random.normal(0, 0.15)

        # Calculate final price
        price = base_price * hour_factor * weekend_factor * (1 + daily_volatility)

        # Occasional price spikes (5% chance, reflecting tight supply situations)
        if np.random.random() < 0.05:
            price *= np.random.uniform(1.5, 2.5)

        # Ensure non-negative
        price = max(0.10, price)

        prices.append(price)

    return pd.Series(prices, index=timestamps)

def generate_commercial_load_profile(n_hours: int = 8760) -> pd.Series:
    """
    Generate realistic commercial load profile for Stavanger
    Typical office/commercial building pattern
    """
    timestamps = pd.date_range(
        start='2024-01-01',
        periods=n_hours,
        freq='H',
        tz='Europe/Oslo'
    )

    loads = []
    base_load = 25  # kW base load (ventilation, servers, etc)

    for ts in timestamps:
        hour = ts.hour
        weekday = ts.weekday()
        month = ts.month

        # Working hours pattern (Mon-Fri)
        if weekday < 5:  # Weekday
            if 7 <= hour <= 18:
                # Business hours
                if 8 <= hour <= 17:
                    load_factor = 2.0  # Full operation
                else:
                    load_factor = 1.5  # Ramp up/down
            else:
                load_factor = 0.4  # Night/standby
        else:  # Weekend
            load_factor = 0.3  # Minimal weekend load

        # Seasonal variation (heating/cooling)
        if month in [12, 1, 2]:  # Winter - heating
            seasonal_factor = 1.2
        elif month in [6, 7, 8]:  # Summer - some cooling
            seasonal_factor = 1.1
        else:
            seasonal_factor = 1.0

        # Random variation
        random_factor = np.random.normal(1.0, 0.05)

        load = base_load * load_factor * seasonal_factor * random_factor
        loads.append(max(5, load))  # Minimum 5 kW

    return pd.Series(loads, index=timestamps)

def main():
    """Run battery optimization with realistic 2023-2025 era prices"""

    print("\n" + "="*70)
    print("🔋 BATTERY OPTIMIZATION - POST ENERGY-CRISIS ANALYSIS (2023-2025)")
    print("="*70)

    print("\n📊 System Specifications:")
    print(f"  • PV: 150 kWp, 25° south-facing, Stavanger")
    print(f"  • Inverter: 110 kW (oversizing 1.36)")
    print(f"  • Grid limit: 77 kW")
    print(f"  • Analysis period: 2024 (representative post-crisis year)")

    # Initialize configurations
    system_config = SystemConfig()
    lnett_tariff = LnettTariff()
    battery_config = BatteryConfig()
    economic_config = EconomicConfig()

    # Initialize models
    print("\n🔄 Initializing models...")

    pv_model = SolarProductionModel(
        pv_capacity_kwp=system_config.pv_capacity_kwp,
        inverter_capacity_kw=system_config.inverter_capacity_kw,
        latitude=system_config.location_lat,
        longitude=system_config.location_lon,
        tilt=system_config.tilt,
        azimuth=system_config.azimuth
    )

    optimizer = BatteryOptimizer(
        system_config,
        lnett_tariff,
        battery_config,
        economic_config
    )

    visualizer = ResultVisualizer()

    # Generate data
    print("\n📈 Generating 2024 data profiles...")
    print("  • Creating post-crisis price patterns (0.50-0.85 NOK/kWh base)")

    # Full year data
    n_hours = 8760

    # Generate PV production
    print("  • Calculating PV production for Stavanger...")
    start_date = datetime(2024, 1, 1, 0, 0, tzinfo=pytz.timezone('Europe/Oslo'))
    end_date = datetime(2024, 12, 31, 23, 0, tzinfo=pytz.timezone('Europe/Oslo'))
    pv_production = pv_model.calculate_hourly_production(start_date, end_date, use_cache=True)

    # Generate spot prices (2023-2025 "new normal")
    print("  • Generating NO2 spot prices (post-crisis levels)...")
    spot_prices = generate_realistic_2024_prices(n_hours)

    # Generate load profile
    print("  • Creating commercial load profile...")
    load_profile = generate_commercial_load_profile(n_hours)

    # Show data statistics
    print("\n📊 Data Statistics:")
    print(f"  • PV total: {pv_production.sum()/1000:.1f} MWh/year")
    print(f"  • PV capacity factor: {pv_production.mean()/150:.1%}")
    print(f"  • Spot price mean: {spot_prices.mean():.3f} NOK/kWh")
    print(f"  • Spot price range: {spot_prices.min():.3f} - {spot_prices.max():.3f} NOK/kWh")
    print(f"  • Price volatility (std): {spot_prices.std():.3f} NOK/kWh")
    print(f"  • Load total: {load_profile.sum()/1000:.1f} MWh/year")
    print(f"  • Peak demand: {load_profile.max():.1f} kW")

    # Run optimization
    print("\n🎯 Running differential evolution optimization...")
    print("  • Search space: 10-200 kWh, 10-100 kW")
    print("  • Target battery cost: 3000 NOK/kWh")
    print("  • Strategy: Combined (peak shaving + arbitrage)")

    try:
        result = optimizer.optimize_battery_size(
            pv_production,
            spot_prices,
            load_profile,
            target_battery_cost=3000,
            capacity_range=(10, 200),
            power_range=(10, 100),
            strategy='combined'
        )

        print("\n" + "="*70)
        print("✅ OPTIMIZATION RESULTS")
        print("="*70)

        print(f"\n🔋 Optimal Battery Configuration:")
        print(f"  • Capacity: {result.optimal_capacity_kwh:.1f} kWh")
        print(f"  • Power: {result.optimal_power_kw:.1f} kW")
        print(f"  • C-rate: {result.optimal_c_rate:.2f}")

        print(f"\n💰 Economic Analysis (at 3000 NOK/kWh):")
        print(f"  • NPV: {result.npv_at_target_cost:,.0f} NOK")
        if result.economic_results.irr:
            print(f"  • IRR: {result.economic_results.irr:.1%}")
        else:
            print(f"  • IRR: N/A (negative NPV)")

        if result.economic_results.payback_years:
            print(f"  • Payback: {result.economic_results.payback_years:.1f} years")
        else:
            print(f"  • Payback: >15 years")

        print(f"  • Annual savings: {result.economic_results.annual_savings:,.0f} NOK/year")

        print(f"\n🎯 Break-even Analysis:")
        print(f"  • Max battery cost for profitability: {result.max_battery_cost_per_kwh:.0f} NOK/kWh")

        if result.max_battery_cost_per_kwh > 3000:
            margin = (result.max_battery_cost_per_kwh - 3000) / 3000 * 100
            print(f"  ✅ Current prices (3000 NOK/kWh) leave {margin:.0f}% margin")
            print(f"  → Investment is PROFITABLE")
        else:
            gap = (3000 - result.max_battery_cost_per_kwh) / 3000 * 100
            print(f"  ⚠️ Battery prices need to drop {gap:.0f}% for profitability")
            print(f"  → Wait for better prices")

        print(f"\n📈 Revenue Streams (15-year total):")
        for source, value in result.economic_results.revenue_breakdown.items():
            pct = value / result.economic_results.total_revenue * 100
            source_name = source.replace('_', ' ').title()
            print(f"  • {source_name}: {value:,.0f} NOK ({pct:.0f}%)")

        print(f"\n⚡ Operation Metrics:")
        print(f"  • Annual cycles: {result.operation_metrics.get('cycles', 0):.0f}")
        print(f"  • Self-consumption: {result.operation_metrics.get('self_consumption_rate', 0):.1%}")
        print(f"  • Curtailment avoided: {result.operation_metrics.get('curtailment_avoided_kwh', 0):,.0f} kWh/year")

        # Generate visualizations
        print("\n📊 Generating visualizations...")

        # NPV sensitivity to battery cost
        if result.sensitivity_data is not None and not result.sensitivity_data.empty:
            fig = visualizer.plot_npv_heatmap(
                result.sensitivity_data,
                battery_cost=3000,
                save_name='npv_heatmap_2024'
            )
            print("  ✓ NPV heatmap saved")

        # Generate report
        visualizer.generate_summary_report(result, 'optimization_report_2024')
        print("  ✓ Summary report saved")

        print("\n" + "="*70)
        print("🎯 KEY INSIGHTS FOR 2023-2025 MARKET CONDITIONS")
        print("="*70)

        print(f"\n1. With post-crisis 'new normal' prices (0.5-0.85 NOK/kWh):")
        print(f"   • Battery storage {'IS' if result.max_battery_cost_per_kwh > 3000 else 'IS NOT'} profitable")
        print(f"   • Main value: {max(result.economic_results.revenue_breakdown.items(), key=lambda x: x[1])[0].replace('_', ' ').title()}")

        print(f"\n2. Critical factors:")
        print(f"   • Price volatility is key for arbitrage value")
        print(f"   • Peak shaving provides stable base revenue")
        print(f"   • Grid constraint (77 kW) creates curtailment value")

        print(f"\n3. Investment recommendation:")
        if result.max_battery_cost_per_kwh > 3500:
            print(f"   ✅ STRONG BUY - Good margins even with price uncertainty")
        elif result.max_battery_cost_per_kwh > 3000:
            print(f"   ✅ BUY - Positive NPV with current battery prices")
        elif result.max_battery_cost_per_kwh > 2500:
            print(f"   ⚠️ WAIT - Monitor battery price trends")
        else:
            print(f"   ❌ NOT VIABLE - Need significant cost reductions")

        print("\n✅ Analysis complete! Check 'results/reports/' for detailed results.")

    except Exception as e:
        logger.error(f"Error during optimization: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()