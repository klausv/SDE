#!/usr/bin/env python3
"""
Battery Optimization System - Unified Entry Point
==================================================

Unified simulation system supporting three modes:
1. Rolling Horizon: Real-time operation with persistent state
2. Monthly: Single or multi-month analysis
3. Yearly: Annual investment analysis with weekly optimizations

Usage:
    python main.py run --config configs/rolling_horizon_realtime.yaml
    python main.py rolling --battery-kwh 80 --battery-kw 60
    python main.py monthly --months 1,2,3
    python main.py yearly --resolution PT60M
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.config.simulation_config import SimulationConfig
from src.simulation import (
    RollingHorizonOrchestrator,
    MonthlyOrchestrator,
    YearlyOrchestrator,
)


def run_from_config(config_path: Path) -> None:
    """
    Run simulation from YAML configuration file.

    Args:
        config_path: Path to YAML configuration file
    """
    print(f"Loading configuration from: {config_path}")

    try:
        config = SimulationConfig.from_yaml(config_path)
        config.validate()
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # Select orchestrator based on mode
    if config.mode == "rolling_horizon":
        orchestrator = RollingHorizonOrchestrator(config)
    elif config.mode == "monthly":
        orchestrator = MonthlyOrchestrator(config)
    elif config.mode == "yearly":
        orchestrator = YearlyOrchestrator(config)
    else:
        print(f"Error: Unknown mode '{config.mode}'")
        sys.exit(1)

    # Run simulation
    try:
        results = orchestrator.run()
    except Exception as e:
        print(f"\nSimulation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Save results
    output_dir = Path(config.output_dir)
    print(f"\nSaving results to: {output_dir}")
    results.save_all(output_dir, save_plots=config.save_plots)

    print("\n" + "="*70)
    print("Simulation Complete!")
    print("="*70)


def run_rolling_horizon(args) -> None:
    """Quick rolling horizon simulation with command-line parameters."""
    # Create config programmatically
    from battery_optimization.src.config.simulation_config import (
        SimulationConfig,
        BatteryConfigSim,
        DataSourceConfig,
        RollingHorizonModeConfig,
        SimulationPeriodConfig,
    )

    config = SimulationConfig(
        mode="rolling_horizon",
        time_resolution=args.resolution,
        simulation_period=SimulationPeriodConfig(
            start_date=args.start_date,
            end_date=args.end_date,
        ),
        battery=BatteryConfigSim(
            capacity_kwh=args.battery_kwh,
            power_kw=args.battery_kw,
        ),
        data_sources=DataSourceConfig(
            prices_file=args.prices_file,
            production_file=args.production_file,
            consumption_file=args.consumption_file,
        ),
        rolling_horizon=RollingHorizonModeConfig(
            horizon_hours=args.horizon_hours,
            update_frequency_minutes=args.update_freq,
        ),
        output_dir=args.output_dir,
    )

    orchestrator = RollingHorizonOrchestrator(config)
    results = orchestrator.run()

    output_dir = Path(args.output_dir)
    results.save_all(output_dir, save_plots=True)


def run_monthly(args) -> None:
    """Quick monthly simulation with command-line parameters."""
    from battery_optimization.src.config.simulation_config import (
        SimulationConfig,
        BatteryConfigSim,
        DataSourceConfig,
        MonthlyModeConfig,
        SimulationPeriodConfig,
    )

    # Parse months
    if args.months == "all":
        months = "all"
    else:
        months = [int(m) for m in args.months.split(',')]

    config = SimulationConfig(
        mode="monthly",
        time_resolution=args.resolution,
        simulation_period=SimulationPeriodConfig(
            start_date=args.start_date,
            end_date=args.end_date,
        ),
        battery=BatteryConfigSim(
            capacity_kwh=args.battery_kwh,
            power_kw=args.battery_kw,
        ),
        data_sources=DataSourceConfig(
            prices_file=args.prices_file,
            production_file=args.production_file,
            consumption_file=args.consumption_file,
        ),
        monthly=MonthlyModeConfig(months=months),
        output_dir=args.output_dir,
    )

    orchestrator = MonthlyOrchestrator(config)
    results = orchestrator.run()

    output_dir = Path(args.output_dir)
    results.save_all(output_dir, save_plots=True)


def run_yearly(args) -> None:
    """Quick yearly simulation with command-line parameters."""
    from battery_optimization.src.config.simulation_config import (
        SimulationConfig,
        BatteryConfigSim,
        DataSourceConfig,
        YearlyModeConfig,
        SimulationPeriodConfig,
    )

    config = SimulationConfig(
        mode="yearly",
        time_resolution=args.resolution,
        simulation_period=SimulationPeriodConfig(
            start_date=args.start_date,
            end_date=args.end_date,
        ),
        battery=BatteryConfigSim(
            capacity_kwh=args.battery_kwh,
            power_kw=args.battery_kw,
        ),
        data_sources=DataSourceConfig(
            prices_file=args.prices_file,
            production_file=args.production_file,
            consumption_file=args.consumption_file,
        ),
        yearly=YearlyModeConfig(
            horizon_hours=args.horizon_hours,
            weeks=args.weeks,
        ),
        output_dir=args.output_dir,
    )

    orchestrator = YearlyOrchestrator(config)
    results = orchestrator.run()

    output_dir = Path(args.output_dir)
    results.save_all(output_dir, save_plots=True)


def main():
    parser = argparse.ArgumentParser(
        description="Battery Optimization System - Unified Entry Point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run from YAML configuration
  python main.py run --config configs/rolling_horizon_realtime.yaml
  python main.py run --config configs/monthly_analysis.yaml

  # Quick modes with CLI parameters
  python main.py rolling --battery-kwh 80 --battery-kw 60
  python main.py monthly --months 1,2,3 --resolution PT60M
  python main.py yearly --weeks 52
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # RUN command (from YAML config)
    run_parser = subparsers.add_parser("run", help="Run simulation from YAML config")
    run_parser.add_argument("--config", type=str, required=True,
                           help="Path to YAML configuration file")

    # Default data paths
    default_prices = "data/spot_prices/2024_NO2_hourly.csv"
    default_production = "data/pv_profiles/pvgis_stavanger_2024.csv"
    default_consumption = "data/consumption/commercial_2024.csv"

    # ROLLING command (quick rolling horizon mode)
    rolling_parser = subparsers.add_parser("rolling", help="Quick rolling horizon mode")
    rolling_parser.add_argument("--battery-kwh", type=float, default=80,
                               help="Battery capacity (kWh)")
    rolling_parser.add_argument("--battery-kw", type=float, default=60,
                               help="Battery power (kW)")
    rolling_parser.add_argument("--horizon-hours", type=int, default=24,
                               help="Optimization horizon (hours)")
    rolling_parser.add_argument("--update-freq", type=int, default=60,
                               help="Update frequency (minutes)")
    rolling_parser.add_argument("--resolution", type=str, default="PT60M",
                               choices=["PT60M", "PT15M"],
                               help="Time resolution")
    rolling_parser.add_argument("--start-date", type=str, default="2024-01-01",
                               help="Start date (YYYY-MM-DD)")
    rolling_parser.add_argument("--end-date", type=str, default="2024-12-31",
                               help="End date (YYYY-MM-DD)")
    rolling_parser.add_argument("--prices-file", type=str, default=default_prices,
                               help="Prices CSV file")
    rolling_parser.add_argument("--production-file", type=str, default=default_production,
                               help="Production CSV file")
    rolling_parser.add_argument("--consumption-file", type=str, default=default_consumption,
                               help="Consumption CSV file")
    rolling_parser.add_argument("--output-dir", type=str, default="results/rolling_horizon",
                               help="Output directory")

    # MONTHLY command (quick monthly mode)
    monthly_parser = subparsers.add_parser("monthly", help="Quick monthly mode")
    monthly_parser.add_argument("--battery-kwh", type=float, default=100,
                               help="Battery capacity (kWh)")
    monthly_parser.add_argument("--battery-kw", type=float, default=75,
                               help="Battery power (kW)")
    monthly_parser.add_argument("--months", type=str, default="all",
                               help="Months to analyze (comma-separated or 'all')")
    monthly_parser.add_argument("--resolution", type=str, default="PT60M",
                               choices=["PT60M", "PT15M"],
                               help="Time resolution")
    monthly_parser.add_argument("--start-date", type=str, default="2024-01-01",
                               help="Start date (YYYY-MM-DD)")
    monthly_parser.add_argument("--end-date", type=str, default="2024-12-31",
                               help="End date (YYYY-MM-DD)")
    monthly_parser.add_argument("--prices-file", type=str, default=default_prices,
                               help="Prices CSV file")
    monthly_parser.add_argument("--production-file", type=str, default=default_production,
                               help="Production CSV file")
    monthly_parser.add_argument("--consumption-file", type=str, default=default_consumption,
                               help="Consumption CSV file")
    monthly_parser.add_argument("--output-dir", type=str, default="results/monthly",
                               help="Output directory")

    # YEARLY command (quick yearly mode)
    yearly_parser = subparsers.add_parser("yearly", help="Quick yearly mode")
    yearly_parser.add_argument("--battery-kwh", type=float, default=80,
                               help="Battery capacity (kWh)")
    yearly_parser.add_argument("--battery-kw", type=float, default=60,
                               help="Battery power (kW)")
    yearly_parser.add_argument("--horizon-hours", type=int, default=168,
                               help="Weekly optimization horizon (hours)")
    yearly_parser.add_argument("--weeks", type=int, default=52,
                               help="Number of weeks to simulate")
    yearly_parser.add_argument("--resolution", type=str, default="PT60M",
                               choices=["PT60M", "PT15M"],
                               help="Time resolution")
    yearly_parser.add_argument("--start-date", type=str, default="2024-01-01",
                               help="Start date (YYYY-MM-DD)")
    yearly_parser.add_argument("--end-date", type=str, default="2024-12-31",
                               help="End date (YYYY-MM-DD)")
    yearly_parser.add_argument("--prices-file", type=str, default=default_prices,
                               help="Prices CSV file")
    yearly_parser.add_argument("--production-file", type=str, default=default_production,
                               help="Production CSV file")
    yearly_parser.add_argument("--consumption-file", type=str, default=default_consumption,
                               help="Consumption CSV file")
    yearly_parser.add_argument("--output-dir", type=str, default="results/yearly",
                               help="Output directory")

    args = parser.parse_args()

    if not args.command:
        print("Battery Optimization System v2.0")
        print("=================================")
        print("\nUnified simulation system with three modes:")
        print("  1. Rolling Horizon - Real-time operation")
        print("  2. Monthly - Single/multi-month analysis")
        print("  3. Yearly - Annual investment analysis")
        print("\nUse -h for help on available commands")
        parser.print_help()
        sys.exit(1)

    # Route to appropriate function
    if args.command == "run":
        run_from_config(Path(args.config))
    elif args.command == "rolling":
        run_rolling_horizon(args)
    elif args.command == "monthly":
        run_monthly(args)
    elif args.command == "yearly":
        run_yearly(args)


if __name__ == "__main__":
    main()
