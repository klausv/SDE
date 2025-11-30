"""
Baseline Calculator Example - No Battery Mode

Demonstrates baseline calculation for economic comparison.
Shows how to calculate system performance without battery storage
to establish ROI baseline for battery investment analysis.
"""

from datetime import datetime
from src import (
    SimulationConfig,
    PriceLoader,
    SolarProductionLoader,
    OptimizerFactory,
    ResultStorage,
)
from src.simulation import MonthlyOrchestrator


def example_baseline_from_yaml():
    """Load baseline config from YAML and run simulation."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Baseline from YAML Configuration")
    print("=" * 80)

    # Load baseline configuration
    config = SimulationConfig.from_yaml("configs/baseline_monthly.yaml")

    print(f"\nConfiguration loaded:")
    print(f"  Mode: {config.mode}")
    print(f"  Battery capacity: {config.battery.capacity_kwh} kWh (baseline mode)")
    print(f"  Time resolution: {config.time_resolution}")

    # Create orchestrator and run
    orchestrator = MonthlyOrchestrator(config)
    results = orchestrator.run()

    print(f"\nBaseline Results:")
    print(f"  Total cost: {results.economic_metrics['total_cost_nok']:,.0f} NOK")
    print(f"  Energy cost: {results.economic_metrics.get('energy_cost_nok', 0):,.0f} NOK")
    print(f"  Power tariff: {results.economic_metrics.get('power_tariff_nok', 0):,.0f} NOK")

    # Save baseline results for later comparison
    storage = ResultStorage("results/")
    baseline_id = results.save_to_storage(storage, notes="Baseline - no battery")
    print(f"\nBaseline saved as: {baseline_id}")

    return results, baseline_id


def example_baseline_programmatic():
    """Create baseline calculator programmatically."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Programmatic Baseline Creation")
    print("=" * 80)

    # Create configuration with zero battery
    from src.config.simulation_config import (
        BatteryConfigSim,
        SimulationPeriodConfig,
        MonthlyModeConfig,
        EconomicConfig,
    )

    config = SimulationConfig(
        mode="baseline",  # Explicit baseline mode
        time_resolution="PT60M",
        simulation_period=SimulationPeriodConfig(
            start_date="2024-01-01",
            end_date="2024-03-31"  # Q1 only
        ),
        battery=BatteryConfigSim(
            capacity_kwh=0.0,  # Zero battery
            power_kw=0.0,
        ),
        monthly=MonthlyModeConfig(months=[1, 2, 3]),  # Q1
        economic=EconomicConfig(
            discount_rate=0.05,
            project_years=15
        ),
    )

    # Create baseline calculator via factory
    baseline_calc = OptimizerFactory.create_from_config(config)

    print(f"\nBaseline calculator created:")
    print(f"  Type: {type(baseline_calc).__name__}")
    print(f"  {baseline_calc}")

    return baseline_calc


def example_direct_calculation():
    """Use BaselineCalculator directly for quick analysis."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Direct Baseline Calculation (No Orchestrator)")
    print("=" * 80)

    from src.optimization.baseline_calculator import BaselineCalculator
    import pandas as pd
    import numpy as np

    # Create baseline calculator with grid limits
    calculator = BaselineCalculator(
        grid_limit_kw=77,  # 77 kW grid limit
    )

    print(f"Baseline calculator: {calculator}")

    # Generate simple test data (1 day, hourly)
    timestamps = pd.date_range("2024-06-15", periods=24, freq="h")

    # Summer day pattern
    hour = np.arange(24)
    pv_production = np.maximum(0, 50 * np.sin((hour - 6) * np.pi / 12))  # Peak at noon
    consumption = 40 + 10 * np.sin(hour * np.pi / 12)  # Peak afternoon
    spot_prices = 0.50 + 0.30 * np.sin((hour - 12) * np.pi / 12)  # Peak evening

    print(f"\nTest data (24 hours):")
    print(f"  PV production: {pv_production.min():.1f} - {pv_production.max():.1f} kW")
    print(f"  Consumption: {consumption.min():.1f} - {consumption.max():.1f} kW")
    print(f"  Spot prices: {spot_prices.min():.2f} - {spot_prices.max():.2f} NOK/kWh")

    # Calculate baseline (INSTANT - no solver)
    import time
    start = time.time()
    result = calculator.optimize(
        timestamps=timestamps,
        pv_production=pv_production,
        consumption=consumption,
        spot_prices=spot_prices,
    )
    calc_time = time.time() - start

    print(f"\nBaseline calculation:")
    print(f"  Calculation time: {calc_time*1000:.3f} ms (instant!)")
    print(f"  Success: {result.success}")
    print(f"  Message: {result.message}")

    print(f"\nGrid flows:")
    print(f"  Total import: {result.P_grid_import.sum():.1f} kWh")
    print(f"  Total export: {result.P_grid_export.sum():.1f} kWh")
    print(f"  Total curtailment: {result.P_curtail.sum():.1f} kWh")

    print(f"\nCosts:")
    print(f"  Energy cost: {result.energy_cost:.2f} NOK")
    print(f"  Objective value: {result.objective_value:.2f} NOK")

    # Show when curtailment occurs
    curtailment_hours = np.where(result.P_curtail > 0)[0]
    if len(curtailment_hours) > 0:
        print(f"\nCurtailment detected at hours: {curtailment_hours.tolist()}")
        for h in curtailment_hours:
            print(f"  Hour {h}: PV={pv_production[h]:.1f} kW, "
                  f"Consumption={consumption[h]:.1f} kW, "
                  f"Curtailed={result.P_curtail[h]:.1f} kW")


def example_baseline_vs_battery_comparison():
    """Compare baseline (no battery) vs battery optimization."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Baseline vs Battery Comparison")
    print("=" * 80)

    from src.config.simulation_config import BatteryConfigSim

    storage = ResultStorage("results/")

    # 1. Run baseline
    print("\n1. Running baseline (no battery)...")
    baseline_config = SimulationConfig.from_yaml("configs/baseline_monthly.yaml")
    baseline_orch = MonthlyOrchestrator(baseline_config)
    baseline_results = baseline_orch.run()
    baseline_id = baseline_results.save_to_storage(storage, notes="Baseline for comparison")

    # 2. Run with battery
    print("\n2. Running with battery (80 kWh, 60 kW)...")
    battery_config = SimulationConfig.from_yaml("configs/baseline_monthly.yaml")
    battery_config.mode = "monthly"
    battery_config.battery = BatteryConfigSim(
        capacity_kwh=80.0,
        power_kw=60.0,
        efficiency=0.90
    )
    battery_orch = MonthlyOrchestrator(battery_config)
    battery_results = battery_orch.run()
    battery_id = battery_results.save_to_storage(storage, notes="80kWh/60kW battery")

    # 3. Calculate savings
    baseline_cost = baseline_results.economic_metrics['total_cost_nok']
    battery_cost = battery_results.economic_metrics['total_cost_nok']
    annual_savings = baseline_cost - battery_cost

    print(f"\n" + "=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)
    print(f"\nBaseline (no battery):")
    print(f"  Total cost: {baseline_cost:,.0f} NOK")
    print(f"\nWith battery (80 kWh / 60 kW):")
    print(f"  Total cost: {battery_cost:,.0f} NOK")
    print(f"\nAnnual savings: {annual_savings:,.0f} NOK ({annual_savings/baseline_cost*100:.1f}%)")

    # 4. Calculate ROI metrics
    battery_investment = 80 * 5000  # 5000 NOK/kWh assumption
    payback_years = battery_investment / annual_savings if annual_savings > 0 else float('inf')

    print(f"\nROI Analysis:")
    print(f"  Battery investment: {battery_investment:,.0f} NOK")
    print(f"  Annual savings: {annual_savings:,.0f} NOK")
    print(f"  Simple payback: {payback_years:.1f} years")

    if payback_years <= 15:
        print(f"  ✓ Payback within project lifetime (15 years)")
    else:
        print(f"  ✗ Payback exceeds project lifetime")

    print(f"\nUse CLI for detailed comparison:")
    print(f"  python scripts/report_cli.py compare {baseline_id} {battery_id}")


def main():
    """Run all baseline examples."""
    print("\n" + "=" * 80)
    print("BASELINE CALCULATOR EXAMPLES")
    print("=" * 80)
    print("\nDemonstrates:")
    print("  1. Baseline from YAML config")
    print("  2. Programmatic baseline creation")
    print("  3. Direct calculation (no orchestrator)")
    print("  4. Baseline vs battery comparison")
    print("\nPerformance: Instant calculation (~1ms) vs 30-60s LP solver")

    try:
        # Example 1: YAML config
        example_baseline_from_yaml()

        # Example 2: Programmatic
        example_baseline_programmatic()

        # Example 3: Direct calculation
        example_direct_calculation()

        # Example 4: Comparison (commented out - requires full data)
        # example_baseline_vs_battery_comparison()

        print("\n" + "=" * 80)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
