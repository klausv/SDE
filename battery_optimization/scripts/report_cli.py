#!/usr/bin/env python
"""
Battery Optimization Reporting CLI

Command-line interface for generating reports and visualizations from
stored simulation results without re-running expensive simulations.

Usage:
    python scripts/report_cli.py list                    # List all results
    python scripts/report_cli.py show <result_id>        # Show result details
    python scripts/report_cli.py report <result_id>      # Generate markdown report
    python scripts/report_cli.py plots <result_id>       # Generate plots
    python scripts/report_cli.py export <result_id>      # Export CSV files
    python scripts/report_cli.py compare <id1> <id2>     # Compare two results
    python scripts/report_cli.py stats                   # Show storage statistics
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add parent directory to path
parent_path = Path(__file__).parent.parent
sys.path.insert(0, str(parent_path))

from src.persistence import ResultStorage, StorageFormat
from src.simulation.simulation_results import SimulationResults
from src.persistence.result_storage import ResultMetadata


def cmd_list(storage: ResultStorage, mode: Optional[str] = None) -> None:
    """List all stored simulation results."""
    results = storage.list_results(mode=mode)

    if not results:
        print("No stored results found.")
        return

    print(f"\nFound {len(results)} stored result(s):\n")
    print("=" * 100)

    for meta in results:
        print(f"ID: {meta.result_id}")
        print(f"  Created:  {meta.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Mode:     {meta.mode}")
        print(f"  Period:   {meta.start_date.date()} to {meta.end_date.date()}")
        print(f"  Battery:  {meta.battery_kwh} kWh @ {meta.battery_kw} kW")
        print(f"  Format:   {meta.storage_format}")
        print(f"  Size:     {meta.file_size_mb:.2f} MB")

        if meta.optimizer_method:
            print(f"  Optimizer: {meta.optimizer_method}")
        if meta.execution_time_s:
            print(f"  Runtime:  {meta.execution_time_s:.1f} seconds")
        if meta.total_cost_nok:
            print(f"  Total Cost: {meta.total_cost_nok:,.0f} NOK")
        if meta.notes:
            print(f"  Notes:    {meta.notes}")
        print("-" * 100)


def cmd_show(storage: ResultStorage, result_id: str) -> None:
    """Show detailed information about a specific result."""
    meta = storage.get_metadata(result_id)

    print(f"\nResult Details: {result_id}")
    print("=" * 100)
    print(f"Created:         {meta.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode:            {meta.mode}")
    print(f"Period:          {meta.start_date.date()} to {meta.end_date.date()}")
    print(f"Battery Config:  {meta.battery_kwh} kWh @ {meta.battery_kw} kW")
    print(f"Storage Format:  {meta.storage_format}")
    print(f"File Size:       {meta.file_size_mb:.2f} MB")
    print(f"File Path:       {meta.file_path}")

    if meta.optimizer_method:
        print(f"Optimizer:       {meta.optimizer_method}")
    if meta.execution_time_s:
        print(f"Execution Time:  {meta.execution_time_s:.1f} seconds")
    if meta.total_cost_nok:
        print(f"Total Cost:      {meta.total_cost_nok:,.0f} NOK")
    if meta.notes:
        print(f"Notes:           {meta.notes}")

    # Load full result for additional details
    print("\nLoading full result data...")
    results = storage.load(result_id)

    print(f"Trajectory Points:  {len(results.trajectory)}")
    print(f"Monthly Summaries:  {len(results.monthly_summary)}")
    print(f"Economic Metrics:   {len(results.economic_metrics)}")

    if results.economic_metrics:
        print("\nEconomic Metrics:")
        for key, value in results.economic_metrics.items():
            if isinstance(value, (int, float)):
                print(f"  {key:20s} = {value:,.2f}")
            else:
                print(f"  {key:20s} = {value}")

    print("=" * 100)


def cmd_report(storage: ResultStorage, result_id: str, output_file: Optional[str] = None) -> None:
    """Generate markdown report from stored results."""
    print(f"Loading result: {result_id}")
    results = storage.load(result_id)

    print("Generating markdown report...")
    report = results.to_report()

    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report)
        print(f"✓ Report saved to: {output_path.absolute()}")
    else:
        print("\n" + "=" * 100)
        print(report)
        print("=" * 100)


def cmd_plots(storage: ResultStorage, result_id: str, output_dir: Optional[str] = None) -> None:
    """Generate visualization plots from stored results."""
    print(f"Loading result: {result_id}")
    results = storage.load(result_id)

    if output_dir is None:
        output_dir = f"results/reports/{result_id}_plots"

    output_path = Path(output_dir)
    print(f"Generating plots to: {output_path.absolute()}")

    results.to_plots(output_path)
    print("✓ Plots generated successfully")


def cmd_export(storage: ResultStorage, result_id: str, output_dir: Optional[str] = None) -> None:
    """Export results to CSV files."""
    print(f"Loading result: {result_id}")
    results = storage.load(result_id)

    if output_dir is None:
        output_dir = f"results/reports/{result_id}_csv"

    output_path = Path(output_dir)
    print(f"Exporting CSV files to: {output_path.absolute()}")

    results.to_csv(output_path)
    print("✓ CSV files exported successfully")


def cmd_compare(storage: ResultStorage, result_id1: str, result_id2: str) -> None:
    """Compare two stored results."""
    print(f"Loading results...")
    results1 = storage.load(result_id1)
    results2 = storage.load(result_id2)

    meta1 = storage.get_metadata(result_id1)
    meta2 = storage.get_metadata(result_id2)

    print(f"\nComparing Results:")
    print("=" * 100)

    # Metadata comparison
    print(f"\n{'Metric':<30s} {'Result 1':>20s} {'Result 2':>20s} {'Difference':>20s}")
    print("-" * 100)

    # Battery configuration
    print(f"{'Battery Capacity (kWh)':<30s} {meta1.battery_kwh:>20.1f} {meta2.battery_kwh:>20.1f} {meta2.battery_kwh - meta1.battery_kwh:>20.1f}")
    print(f"{'Battery Power (kW)':<30s} {meta1.battery_kw:>20.1f} {meta2.battery_kw:>20.1f} {meta2.battery_kw - meta1.battery_kw:>20.1f}")

    # Execution
    if meta1.execution_time_s and meta2.execution_time_s:
        print(f"{'Execution Time (s)':<30s} {meta1.execution_time_s:>20.1f} {meta2.execution_time_s:>20.1f} {meta2.execution_time_s - meta1.execution_time_s:>20.1f}")

    # Economic metrics
    if meta1.total_cost_nok and meta2.total_cost_nok:
        diff_cost = meta2.total_cost_nok - meta1.total_cost_nok
        print(f"{'Total Cost (NOK)':<30s} {meta1.total_cost_nok:>20,.0f} {meta2.total_cost_nok:>20,.0f} {diff_cost:>20,.0f}")

    # Compare all economic metrics
    print("\nDetailed Economic Comparison:")
    print("-" * 100)

    all_keys = set(results1.economic_metrics.keys()) | set(results2.economic_metrics.keys())

    for key in sorted(all_keys):
        val1 = results1.economic_metrics.get(key)
        val2 = results2.economic_metrics.get(key)

        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            diff = val2 - val1
            pct_change = (diff / val1 * 100) if val1 != 0 else 0
            print(f"{key:<30s} {val1:>20,.2f} {val2:>20,.2f} {diff:>15,.2f} ({pct_change:>6.1f}%)")
        else:
            print(f"{key:<30s} {str(val1):>20s} {str(val2):>20s}")

    print("=" * 100)


def cmd_stats(storage: ResultStorage) -> None:
    """Show storage statistics."""
    stats = storage.get_storage_stats()

    print("\nStorage Statistics:")
    print("=" * 100)
    print(f"Total Results:    {stats['total_results']}")
    print(f"Total Size:       {stats['total_size_mb']:.2f} MB")
    print(f"Storage Directory: {stats['storage_dir']}")

    print("\nResults by Mode:")
    for mode, count in stats['results_by_mode'].items():
        print(f"  {mode:20s} {count:>5d} result(s)")

    # Format breakdown
    all_results = storage.list_results()
    formats = {}
    for meta in all_results:
        formats[meta.storage_format] = formats.get(meta.storage_format, 0) + 1

    print("\nResults by Format:")
    for format_name, count in formats.items():
        print(f"  {format_name:20s} {count:>5d} result(s)")

    print("=" * 100)


def cmd_delete(storage: ResultStorage, result_id: str, confirm: bool = False) -> None:
    """Delete a stored result."""
    if not confirm:
        print(f"Warning: This will permanently delete result '{result_id}'")
        response = input("Type 'yes' to confirm: ")
        if response.lower() != 'yes':
            print("Deletion cancelled.")
            return

    print(f"Deleting result: {result_id}")
    storage.delete(result_id)
    print("✓ Result deleted successfully")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Battery Optimization Reporting CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all stored results
  python scripts/report_cli.py list

  # Show details of specific result
  python scripts/report_cli.py show rolling_horizon_20241001_120000

  # Generate markdown report
  python scripts/report_cli.py report rolling_horizon_20241001_120000

  # Generate plots
  python scripts/report_cli.py plots rolling_horizon_20241001_120000

  # Export to CSV
  python scripts/report_cli.py export rolling_horizon_20241001_120000

  # Compare two results
  python scripts/report_cli.py compare result1_id result2_id

  # Show storage statistics
  python scripts/report_cli.py stats
        """
    )

    parser.add_argument(
        '--storage-dir',
        default='results',
        help='Results storage directory (default: results/)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # List command
    parser_list = subparsers.add_parser('list', help='List all stored results')
    parser_list.add_argument('--mode', help='Filter by simulation mode')

    # Show command
    parser_show = subparsers.add_parser('show', help='Show result details')
    parser_show.add_argument('result_id', help='Result ID to show')

    # Report command
    parser_report = subparsers.add_parser('report', help='Generate markdown report')
    parser_report.add_argument('result_id', help='Result ID to report')
    parser_report.add_argument('-o', '--output', help='Output file path (default: print to console)')

    # Plots command
    parser_plots = subparsers.add_parser('plots', help='Generate visualization plots')
    parser_plots.add_argument('result_id', help='Result ID to visualize')
    parser_plots.add_argument('-o', '--output-dir', help='Output directory (default: results/reports/{id}_plots/)')

    # Export command
    parser_export = subparsers.add_parser('export', help='Export to CSV files')
    parser_export.add_argument('result_id', help='Result ID to export')
    parser_export.add_argument('-o', '--output-dir', help='Output directory (default: results/reports/{id}_csv/)')

    # Compare command
    parser_compare = subparsers.add_parser('compare', help='Compare two results')
    parser_compare.add_argument('result_id1', help='First result ID')
    parser_compare.add_argument('result_id2', help='Second result ID')

    # Stats command
    parser_stats = subparsers.add_parser('stats', help='Show storage statistics')

    # Delete command
    parser_delete = subparsers.add_parser('delete', help='Delete a stored result')
    parser_delete.add_argument('result_id', help='Result ID to delete')
    parser_delete.add_argument('-y', '--yes', action='store_true', help='Skip confirmation prompt')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize storage
    storage = ResultStorage(results_dir=args.storage_dir)

    # Execute command
    try:
        if args.command == 'list':
            cmd_list(storage, mode=args.mode)
        elif args.command == 'show':
            cmd_show(storage, args.result_id)
        elif args.command == 'report':
            cmd_report(storage, args.result_id, output_file=args.output)
        elif args.command == 'plots':
            cmd_plots(storage, args.result_id, output_dir=args.output_dir)
        elif args.command == 'export':
            cmd_export(storage, args.result_id, output_dir=args.output_dir)
        elif args.command == 'compare':
            cmd_compare(storage, args.result_id1, args.result_id2)
        elif args.command == 'stats':
            cmd_stats(storage)
        elif args.command == 'delete':
            cmd_delete(storage, args.result_id, confirm=args.yes)
        else:
            parser.print_help()

    except KeyError as e:
        print(f"Error: Result not found - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
