#!/usr/bin/env python3
"""
Test script for updated MILP formulation with all constraints
"""
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.optimization.milp_optimizer import MILPBatteryOptimizer, SOLVER_AVAILABLE, SOLVER_NAME
from src.config import SystemConfig, LnettTariff, BatteryConfig, EconomicConfig

def test_milp_with_constraints():
    """Test MILP optimizer with all new constraints"""

    print("=" * 70)
    print("MILP OPTIMIZER TEST WITH FULL CONSTRAINTS")
    print("=" * 70)
    print(f"Solver: {SOLVER_NAME if SOLVER_AVAILABLE else 'None available'}")

    if not SOLVER_AVAILABLE:
        print("No MILP solver available. Please install OR-Tools, PuLP, or HiGHS")
        return

    # Create configurations
    system_config = SystemConfig()

    tariff = LnettTariff()
    battery_config = BatteryConfig()
    economic_config = EconomicConfig()

    # Initialize optimizer
    optimizer = MILPBatteryOptimizer(
        system_config=system_config,
        tariff=tariff,
        economic_config=economic_config
    )

    # Create simple test profiles (12 typical days, 24 hours each)
    n_days = 12
    hours_per_day = 24
    n_timesteps = n_days * hours_per_day

    # PV production profile (peaks at noon)
    pv_profiles = np.zeros((n_days, hours_per_day))
    for d in range(n_days):
        month = d  # One typical day per month
        seasonal_factor = 0.5 + 0.5 * np.cos((month - 6) * np.pi / 6)  # Peak in summer
        for h in range(hours_per_day):
            if 6 <= h <= 18:
                solar_factor = np.sin((h - 6) * np.pi / 12)
                pv_profiles[d, h] = 150 * solar_factor * seasonal_factor

    # Price profiles (higher during peak hours)
    price_profiles = np.zeros((n_days, hours_per_day))
    for d in range(n_days):
        for h in range(hours_per_day):
            if 6 <= h <= 22:  # Peak hours
                price_profiles[d, h] = 0.8 + 0.2 * np.random.random()
            else:  # Off-peak
                price_profiles[d, h] = 0.3 + 0.1 * np.random.random()

    # Simple load profile (commercial building)
    load_profiles = np.ones((n_days, hours_per_day)) * 20  # Base load 20 kW
    for d in range(n_days):
        for h in range(hours_per_day):
            if 8 <= h <= 17:  # Business hours
                load_profiles[d, h] = 40

    try:
        # Run optimization
        print("\n🔄 Running MILP optimization with full constraints...")
        print("  • C-rate constraints: 0.25C - 1.0C")
        print("  • Mutual exclusion: No simultaneous charge/discharge")
        print("  • Cyclic SOC: Daily energy balance")
        print("  • Min cycles: 0.5 per day (182/year)")
        print("  • Max DOD: 80% per day")

        if SOLVER_AVAILABLE == 'ortools':
            result = optimizer.optimize_with_ortools(
                pv_profiles=pv_profiles,
                price_profiles=price_profiles,
                load_profiles=load_profiles
            )
        elif SOLVER_AVAILABLE == 'pulp':
            result = optimizer.optimize_with_pulp(
                pv_profiles=pv_profiles,
                price_profiles=price_profiles,
                load_profiles=load_profiles
            )
        else:
            result = optimizer.optimize_with_highs(
                pv_profiles=pv_profiles,
                price_profiles=price_profiles,
                load_profiles=load_profiles
            )

        # Display results
        print("\n✅ OPTIMIZATION RESULTS")
        print("-" * 40)
        print(f"Optimal capacity: {result.optimal_capacity_kwh:.1f} kWh")
        print(f"Optimal power: {result.optimal_power_kw:.1f} kW")
        print(f"C-rate: {result.optimal_power_kw/result.optimal_capacity_kwh:.2f}C")
        print(f"Objective value: {result.objective_value:,.0f} NOK")
        print(f"Solver status: {result.solver_status}")
        print(f"Computation time: {result.computation_time:.2f} seconds")
        print(f"Optimality gap: {result.optimality_gap:.2f}")

        # Validate constraints
        c_rate = result.optimal_power_kw / result.optimal_capacity_kwh
        print("\n🔍 CONSTRAINT VALIDATION")
        print("-" * 40)
        print(f"C-rate in range [0.25, 1.0]: {'✅' if 0.25 <= c_rate <= 1.0 else '❌'} ({c_rate:.2f}C)")
        print(f"Capacity in range [10, 200]: {'✅' if 10 <= result.optimal_capacity_kwh <= 200 else '❌'}")
        print(f"Power in range [10, 100]: {'✅' if 10 <= result.optimal_power_kw <= 100 else '❌'}")

        return result

    except Exception as e:
        print(f"\n❌ Error during optimization: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_milp_with_constraints()

    if result:
        print("\n" + "=" * 70)
        print("TEST COMPLETED SUCCESSFULLY")
        print("=" * 70)