#!/usr/bin/env python3
"""
Battery optimization analysis with 90 MWh annual load
Maintains the commercial load profile shape but scales to 90 MWh/year
"""
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import SystemConfig, LnettTariff, BatteryConfig, EconomicConfig
from src.optimization.optimizer import BatteryOptimizer
from src.data_fetchers.solar_production import SolarProductionModel

def generate_90mwh_load_profile(n_hours: int = 8760) -> pd.Series:
    """
    Generate load profile with 90 MWh annual consumption
    Maintains commercial building profile shape
    """
    # Commercial load pattern (same shape as original)
    hourly_pattern = np.array([
        0.3, 0.3, 0.3, 0.3, 0.3, 0.4,  # 00-06: Night (low)
        0.6, 0.8, 1.0, 1.0, 1.0, 0.9,  # 06-12: Morning peak
        0.7, 0.8, 0.9, 1.0, 0.9, 0.7,  # 12-18: Afternoon
        0.5, 0.4, 0.3, 0.3, 0.3, 0.3   # 18-24: Evening
    ])

    # Calculate base load to achieve 90 MWh/year
    # Average pattern factor
    avg_pattern = hourly_pattern.mean()  # ~0.58

    # Target: 90,000 kWh / 8760 hours = 10.27 kWh average
    # base_load * avg_pattern = 10.27
    base_load = 90_000 / (8760 * avg_pattern)  # ~17.7 kW

    # Generate hourly loads
    loads = []
    for i in range(n_hours):
        hour = i % 24
        day = i // 24

        # Add some daily and seasonal variation
        seasonal_factor = 1.0 + 0.1 * np.sin((day - 80) * 2 * np.pi / 365)  # Winter peak
        daily_var = np.random.normal(0, 0.05)

        load = base_load * hourly_pattern[hour] * seasonal_factor * (1 + daily_var)
        loads.append(max(3, load))  # Minimum 3 kW

    loads = pd.Series(loads)

    # Verify and adjust to exactly 90 MWh
    actual_annual = loads.sum()
    adjustment_factor = 90_000 / actual_annual
    loads = loads * adjustment_factor

    print(f"Load profile created:")
    print(f"  • Annual consumption: {loads.sum()/1000:.1f} MWh")
    print(f"  • Peak demand: {loads.max():.1f} kW")
    print(f"  • Average demand: {loads.mean():.1f} kW")
    print(f"  • Min demand: {loads.min():.1f} kW")
    print(f"  • Load factor: {loads.mean()/loads.max():.2%}")

    return loads

def run_analysis_with_90mwh():
    """Run battery optimization with 90 MWh annual load"""

    print("=" * 70)
    print("BATTERY OPTIMIZATION WITH 90 MWH ANNUAL LOAD")
    print("=" * 70)

    # Create configurations
    system_config = SystemConfig()
    tariff = LnettTariff()
    battery_config = BatteryConfig()
    economic_config = EconomicConfig()

    # Initialize optimizer
    optimizer = BatteryOptimizer(
        system_config=system_config,
        tariff=tariff,
        battery_config=battery_config,
        economic_config=economic_config
    )

    print("\n📊 System Configuration:")
    print(f"  • PV capacity: {system_config.pv_capacity_kwp} kWp")
    print(f"  • Grid limit: {system_config.grid_capacity_kw} kW")
    print(f"  • Location: Stavanger ({system_config.location_lat}°N)")

    # Generate PV production (use existing model)
    print("\n☀️ Generating PV production profile...")
    solar_model = SolarProductionModel(
        pv_capacity_kwp=system_config.pv_capacity_kwp,
        inverter_capacity_kw=system_config.inverter_capacity_kw,
        latitude=system_config.location_lat,
        longitude=system_config.location_lon,
        tilt=system_config.tilt,
        azimuth=system_config.azimuth
    )
    pv_production_array, timestamps = solar_model.generate_production(days=365, use_cache=True)
    pv_production = pd.Series(pv_production_array, index=timestamps)

    pv_annual = pv_production.sum() / 1000
    print(f"  • Annual PV production: {pv_annual:.1f} MWh")
    print(f"  • Peak production: {pv_production.max():.1f} kW")

    # Generate load profile (90 MWh/year)
    print("\n🏢 Generating load profile...")
    load_profile = generate_90mwh_load_profile(len(pv_production))
    load_profile.index = timestamps

    # Generate spot prices
    print("\n💰 Generating spot prices...")
    spot_prices = optimizer._generate_sample_spot_prices(len(pv_production))
    spot_prices.index = timestamps
    print(f"  • Average price: {spot_prices.mean():.3f} NOK/kWh")
    print(f"  • Price range: {spot_prices.min():.3f} - {spot_prices.max():.3f} NOK/kWh")

    # Calculate self-consumption potential
    print("\n⚡ Energy balance:")
    net_load = load_profile - pv_production
    print(f"  • Total consumption: {load_profile.sum()/1000:.1f} MWh/year")
    print(f"  • Total PV production: {pv_annual:.1f} MWh/year")
    print(f"  • Direct self-consumption: {min(load_profile.sum(), pv_production.sum())/1000:.1f} MWh")
    print(f"  • Net import need: {max(0, net_load.sum())/1000:.1f} MWh/year")
    print(f"  • Excess PV (curtailable): {max(0, -net_load.sum())/1000:.1f} MWh/year")

    # Run optimization
    print("\n🔄 Running optimization...")
    optimization_result = optimizer.optimize_battery_size(
        pv_production=pv_production,
        spot_prices=spot_prices,
        load_profile=load_profile,
        target_battery_cost=3000,
        strategy='combined'
    )

    # Display results
    print("\n" + "=" * 70)
    print("✅ OPTIMIZATION RESULTS WITH 90 MWH LOAD")
    print("=" * 70)

    print(f"\n🔋 Optimal Battery Configuration:")
    print(f"  • Capacity: {optimization_result.optimal_capacity_kwh:.1f} kWh")
    print(f"  • Power: {optimization_result.optimal_power_kw:.1f} kW")
    print(f"  • C-rate: {optimization_result.optimal_c_rate:.2f}C")

    print(f"\n💰 Economics @ 3000 NOK/kWh:")
    print(f"  • NPV: {optimization_result.npv_at_target_cost:,.0f} NOK")
    print(f"  • Annual revenue: {optimization_result.economic_results.annual_revenue:,.0f} NOK")
    print(f"  • Payback period: {optimization_result.economic_results.payback_period:.1f} years")
    print(f"  • IRR: {optimization_result.economic_results.irr:.1%}")

    print(f"\n🎯 Break-even Analysis:")
    print(f"  • Max battery cost for positive NPV: {optimization_result.max_battery_cost_per_kwh:,.0f} NOK/kWh")

    print(f"\n📊 Operation Metrics:")
    for key, value in optimization_result.operation_metrics.items():
        if 'rate' in key or 'factor' in key:
            print(f"  • {key.replace('_', ' ').title()}: {value:.1%}")
        else:
            print(f"  • {key.replace('_', ' ').title()}: {value:,.0f}")

    # Test different battery costs
    print(f"\n💵 NPV at Different Battery Costs:")
    for cost in [2000, 2500, 3000, 3500, 4000, 4500, 5000]:
        # Create battery for this cost
        from src.optimization.battery_model import BatteryModel, BatterySpec

        spec = BatterySpec(
            capacity_kwh=optimization_result.optimal_capacity_kwh,
            power_kw=optimization_result.optimal_power_kw,
            efficiency=battery_config.round_trip_efficiency,
            degradation_rate=battery_config.annual_degradation,
            min_soc=battery_config.min_soc,
            max_soc=battery_config.max_soc
        )

        battery = BatteryModel(spec)
        operation_results = battery.simulate_operation(
            pv_production,
            spot_prices,
            load_profile,
            system_config.grid_capacity_kw,
            'combined'
        )

        from src.optimization.economic_model import EconomicModel
        economic_model = EconomicModel(tariff, economic_config)

        economic_results = economic_model.calculate_npv(
            operation_results,
            spot_prices,
            load_profile,
            cost,
            optimization_result.optimal_capacity_kwh,
            optimization_result.optimal_power_kw
        )

        status = "✅" if economic_results.npv > 0 else "❌"
        print(f"  {cost} NOK/kWh: NPV = {economic_results.npv:>10,.0f} NOK {status}")

    return optimization_result

if __name__ == "__main__":
    result = run_analysis_with_90mwh()

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("Key finding: With 90 MWh annual load (vs ~160 MWh before),")
    print("the battery economics change significantly due to:")
    print("  1. Less self-consumption opportunity")
    print("  2. More curtailment needed")
    print("  3. Different arbitrage patterns")
    print("=" * 70)