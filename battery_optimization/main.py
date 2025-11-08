#!/usr/bin/env python3
"""
Battery Optimization System for 150kWp Solar Installation
==========================================================

Main entry point for battery optimization analysis in Stavanger, Norway.
Analyzes economic viability through peak shaving, energy arbitrage, and power tariff reduction.

Usage:
    python main.py simulate    # Run simulation with real PVGIS data
    python main.py analyze     # Run sensitivity analysis
    python main.py report      # Generate comprehensive report

DC Production Tracking:
    All simulations include DC tracking by default to accurately measure:
    - Inverter clipping losses (DC > inverter capacity)
    - Grid curtailment losses (AC > grid limit)
    - Overall system efficiency

Author: Battery Optimization Team
Date: 2024-2025
"""

import sys
import argparse
import subprocess
from pathlib import Path

def run_simulation(args):
    """Run battery simulation with real PVGIS data and DC tracking."""
    cmd = ["python", "run_simulation.py"]

    if args.battery_range:
        cmd.extend(["--battery-range"] + args.battery_range)
    if args.output_prefix:
        cmd.extend(["--output-prefix", args.output_prefix])
    if args.base_battery:
        cmd.extend(["--base-battery"] + args.base_battery)

    print(f"Running simulation with real PVGIS data...")
    print(f"DC tracking enabled for inverter curtailment analysis")
    print(f"Command: {' '.join(cmd)}")
    subprocess.run(cmd)

def run_optimization(args):
    """Alias for simulation - both use real data now."""
    print("Note: 'optimize' now runs the same real-data simulation")
    
    # Add default attributes for simulation if not present
    if not hasattr(args, 'battery_range'):
        args.battery_range = None
    if not hasattr(args, 'output_prefix'):
        args.output_prefix = None
    if not hasattr(args, 'base_battery'):
        args.base_battery = None
    
    run_simulation(args)

def run_analysis(args):
    """Run sensitivity analysis across parameter variations."""
    scripts = [
        "sensitivity_analysis.py",
        "analyze_value_drivers.py",
    ]

    for script in scripts:
        script_path = Path("scripts") / script
        if not script_path.exists():
            script_path = Path(script)

        if script_path.exists():
            print(f"\nRunning {script}...")
            subprocess.run(["python", str(script_path)])
        else:
            print(f"Warning: {script} not found")

def generate_report(args):
    """Generate comprehensive battery optimization report"""
    print("Generating comprehensive report...")
    
    # Add default attributes for simulation if not present
    if not hasattr(args, 'battery_range'):
        args.battery_range = None
    if not hasattr(args, 'output_prefix'):
        args.output_prefix = None
    if not hasattr(args, 'base_battery'):
        args.base_battery = None
    
    # Run simulation first to get fresh data
    run_simulation(args)

    # Then generate visualizations
    viz_scripts = [
        "create_visualizations.py",
        "plot_optimization_results.py"
    ]

    for script in viz_scripts:
        if Path(script).exists():
            print(f"Generating visualizations with {script}...")
            subprocess.run(["python", script])

    print("\nReport generation complete!")
    print("Check results/ directory for output files")

def main():
    parser = argparse.ArgumentParser(
        description="Battery Optimization System - Main Entry Point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py simulate                    # Run standard simulation
  python main.py simulate --battery-range 50 200  # Custom battery range
  python main.py optimize                    # Find optimal configuration
  python main.py analyze                     # Run sensitivity analysis
  python main.py report                      # Generate full report

Key Features:
  - DC production tracking (always enabled for accurate loss calculation)
  - Inverter clipping analysis (150kWp DC -> 110kW AC)
  - Grid curtailment analysis (110kW AC -> 77kW grid limit)
  - Norwegian tariff structure (Lnett commercial)
  - Real PVGIS solar data for Stavanger location
        """
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Simulate command
    sim_parser = subparsers.add_parser("simulate", help="Run battery simulation")
    sim_parser.add_argument("--battery-range", nargs=2, type=int, metavar=("MIN", "MAX"),
                           help="Battery size range to test (kWh)")
    sim_parser.add_argument("--output-prefix", type=str,
                           help="Prefix for output files")
    sim_parser.add_argument("--base-battery", nargs=2, type=int, metavar=("KWH", "KW"),
                           help="Base case battery configuration")
    sim_parser.add_argument("--resolution", type=str, default='PT60M',
                           choices=['PT60M', 'PT15M'],
                           help="Time resolution: PT60M (hourly, default) or PT15M (15-minute)")

    # Optimize command
    opt_parser = subparsers.add_parser("optimize", help="Find optimal battery configuration")
    opt_parser.add_argument("--use-cache", action="store_true",
                           help="Use cached PVGIS and price data")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Run sensitivity analysis")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate comprehensive report")
    report_parser.add_argument("--output-prefix", type=str, default="report",
                              help="Prefix for report files")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        print("Battery Optimization System v1.0")
        print("================================")
        print("\nSystem Configuration:")
        print("  - PV System: 150 kWp DC (138.55 kWp rated)")
        print("  - Inverter: 110 kW AC (oversizing 1.36)")
        print("  - Grid Limit: 77 kW (curtailment above this)")
        print("  - Location: Stavanger, Norway (58.97°N, 5.73°E)")
        print("\nUse -h for help on available commands")
        parser.print_help()
        sys.exit(1)

    # Route to appropriate function
    if args.command == "simulate":
        run_simulation(args)
    elif args.command == "optimize":
        run_optimization(args)
    elif args.command == "analyze":
        run_analysis(args)
    elif args.command == "report":
        generate_report(args)

if __name__ == "__main__":
    main()