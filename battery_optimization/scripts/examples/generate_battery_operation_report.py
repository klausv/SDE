"""
Example script: Generate Battery Operation Report

This script demonstrates how to use the BatteryOperationReport class
to create comprehensive interactive visualizations of battery operation data.

Usage:
    python scripts/examples/generate_battery_operation_report.py

Examples:
    # Generate 3-week report (default)
    python generate_battery_operation_report.py

    # Generate 1-month report
    python generate_battery_operation_report.py --period 1month

    # Generate custom period report
    python generate_battery_operation_report.py --period custom --start 2024-06-01 --end 2024-08-31

    # Export PNG in addition to HTML
    python generate_battery_operation_report.py --export-png
"""

import sys
from pathlib import Path
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.reporting import SimulationResult, BatteryOperationReport


def generate_report(
    results_dir: str = 'results/yearly_2024',
    period: str = '3weeks',
    start_date: str = None,
    end_date: str = None,
    export_png: bool = False
):
    """
    Generate battery operation report from saved simulation results.

    Args:
        results_dir: Path to directory containing trajectory.csv and metadata.csv
        period: Time period ('3weeks', '1month', '3months', 'custom')
        start_date: Optional start date for custom period (YYYY-MM-DD)
        end_date: Optional end date for custom period (YYYY-MM-DD)
        export_png: Whether to export static PNG (requires kaleido)

    Returns:
        Path to generated HTML report
    """
    print("="*70)
    print("BATTERY OPERATION REPORT GENERATOR")
    print("="*70)

    # Step 1: Load simulation results
    print(f"\n1. Loading simulation results from: {results_dir}")
    results_path = Path(results_dir)

    if not results_path.exists():
        raise FileNotFoundError(f"Results directory not found: {results_dir}")

    # Check for trajectory.csv
    trajectory_path = results_path / "trajectory.csv"
    if not trajectory_path.exists():
        raise FileNotFoundError(
            f"trajectory.csv not found in {results_dir}\n"
            f"Expected format: {trajectory_path}"
        )

    # Load using SimulationResult (assumes saved format)
    # For now, we'll create a minimal result from trajectory data
    # In production, use SimulationResult.load(results_path) if full result is saved
    import pandas as pd
    import numpy as np

    # Load trajectory
    df = pd.read_csv(trajectory_path, parse_dates=['timestamp'])
    df.set_index('timestamp', inplace=True)

    # Load metadata for battery config
    metadata_path = results_path / "metadata.csv"
    if metadata_path.exists():
        metadata = pd.read_csv(metadata_path)
        battery_kwh = float(metadata['battery_capacity_kwh'].iloc[0])
        battery_kw = float(metadata['battery_power_kw'].iloc[0])
        print(f"   ✓ Battery config: {battery_kwh} kWh / {battery_kw} kW")
    else:
        battery_kwh = 100  # Default fallback
        battery_kw = 50
        print(f"   ⚠ No metadata.csv found, using defaults: {battery_kwh} kWh / {battery_kw} kW")

    # Create SimulationResult from trajectory
    # Map column names from trajectory to SimulationResult format
    result = SimulationResult(
        scenario_name=f"battery_operation_{period}",
        timestamp=df.index,
        production_dc_kw=df.get('production_dc_kw', df.get('P_pv_kw', np.zeros(len(df)))).values,
        production_ac_kw=df.get('production_ac_kw', df.get('P_pv_kw', np.zeros(len(df)))).values,
        consumption_kw=df.get('consumption_kw', df.get('P_load_kw', np.zeros(len(df)))).values,
        grid_power_kw=df['P_grid_import_kw'].values - df.get('P_grid_export_kw', np.zeros(len(df))).values,
        battery_power_ac_kw=df['P_charge_kw'].values - df['P_discharge_kw'].values,
        battery_soc_kwh=df['E_battery_kwh'].values,
        curtailment_kw=df.get('P_curtail_kw', np.zeros(len(df))).values,
        spot_price=df.get('spot_price_nok', np.zeros(len(df))).values,
        cost_summary={
            'total_cost_nok': 0,  # Not needed for visualization
            'energy_cost_nok': 0,
            'power_cost_nok': 0,
            'degradation_cost_nok': 0
        },
        battery_config={
            'capacity_kwh': battery_kwh,
            'power_kw': battery_kw,
            'min_soc_pct': 20,
            'max_soc_pct': 80
        },
        strategy_config={
            'type': 'RollingHorizon',
            'horizon_hours': 168
        },
        simulation_metadata={
            'grid_limit_kw': 77,
            'source': 'trajectory.csv'
        }
    )

    print(f"   ✓ Loaded {len(df)} timesteps")
    print(f"   ✓ Time range: {df.index[0].date()} to {df.index[-1].date()}")

    # Step 2: Create report generator
    print(f"\n2. Creating report generator")
    print(f"   Period: {period}")
    if period == 'custom':
        print(f"   Start: {start_date}")
        print(f"   End: {end_date}")

    report = BatteryOperationReport(
        result=result,
        output_dir=results_path.parent,  # Use parent of results dir
        period=period,
        start_date=start_date,
        end_date=end_date,
        export_png=export_png,
        battery_kwh=battery_kwh,
        battery_kw=battery_kw
    )

    # Step 3: Generate report
    print(f"\n3. Generating interactive visualization...")
    html_path = report.generate()

    # Step 4: Display summary metrics
    print(f"\n4. Summary Metrics")
    print("="*70)
    metrics = report.get_summary_metrics()

    print(f"\n   Period: {metrics['period']}")
    print(f"   Duration: {metrics['duration_hours']:.0f} hours ({metrics['timesteps']} timesteps)")

    print(f"\n   Energy Flows:")
    print(f"      Production:    {metrics['production_kwh']:>10,.0f} kWh")
    print(f"      Consumption:   {metrics['consumption_kwh']:>10,.0f} kWh")
    print(f"      Grid Import:   {metrics['grid_import_kwh']:>10,.0f} kWh")
    print(f"      Grid Export:   {metrics['grid_export_kwh']:>10,.0f} kWh")
    print(f"      Curtailment:   {metrics['curtailment_kwh']:>10,.0f} kWh")

    print(f"\n   Battery Operations:")
    print(f"      Charged:       {metrics['battery_charge_kwh']:>10,.0f} kWh")
    print(f"      Discharged:    {metrics['battery_discharge_kwh']:>10,.0f} kWh")
    print(f"      Cycles:        {metrics['equivalent_cycles']:>10,.1f}")
    print(f"      Efficiency:    {metrics['roundtrip_efficiency_pct']:>10,.1f} %")

    print(f"\n   Utilization:")
    print(f"      Charging:      {metrics['charge_hours']:>10,} hours ({metrics['charge_hours']/metrics['duration_hours']*100:.1f}%)")
    print(f"      Discharging:   {metrics['discharge_hours']:>10,} hours ({metrics['discharge_hours']/metrics['duration_hours']*100:.1f}%)")
    print(f"      Idle:          {metrics['idle_hours']:>10,} hours ({metrics['idle_hours']/metrics['duration_hours']*100:.1f}%)")

    print(f"\n   SOC Statistics:")
    print(f"      Min:           {metrics['soc_min_pct']:>10,.1f} %")
    print(f"      Max:           {metrics['soc_max_pct']:>10,.1f} %")
    print(f"      Mean:          {metrics['soc_mean_pct']:>10,.1f} %")
    print(f"      Start:         {metrics['soc_start_pct']:>10,.1f} %")
    print(f"      End:           {metrics['soc_end_pct']:>10,.1f} %")

    # Step 5: Success message
    print("\n" + "="*70)
    print("✓ REPORT GENERATED SUCCESSFULLY")
    print("="*70)
    print(f"\nInteractive report: {html_path}")
    print("\nOpen in browser to explore:")
    print(f"  - Zoom, pan, and hover for details")
    print(f"  - Click legend items to toggle visibility")
    print(f"  - Use range slider for time navigation")

    return html_path


def main():
    """Command-line interface for report generation."""
    parser = argparse.ArgumentParser(
        description='Generate Battery Operation Report from simulation results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 3-week report (default)
  python generate_battery_operation_report.py

  # Generate 1-month report
  python generate_battery_operation_report.py --period 1month

  # Generate 3-month report starting January 1
  python generate_battery_operation_report.py --period 3months --start 2024-01-01

  # Generate custom period with PNG export
  python generate_battery_operation_report.py --period custom --start 2024-06-01 --end 2024-08-31 --export-png
        """
    )

    parser.add_argument(
        '--results-dir',
        type=str,
        default='results/yearly_2024',
        help='Path to results directory (default: results/yearly_2024)'
    )

    parser.add_argument(
        '--period',
        type=str,
        choices=['3weeks', '1month', '3months', 'custom'],
        default='3weeks',
        help='Time period for visualization (default: 3weeks)'
    )

    parser.add_argument(
        '--start',
        type=str,
        default=None,
        help='Start date for custom period (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end',
        type=str,
        default=None,
        help='End date for custom period (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--export-png',
        action='store_true',
        help='Export static PNG in addition to HTML (requires kaleido)'
    )

    args = parser.parse_args()

    # Validate custom period
    if args.period == 'custom' and (args.start is None or args.end is None):
        parser.error("Custom period requires both --start and --end")

    try:
        html_path = generate_report(
            results_dir=args.results_dir,
            period=args.period,
            start_date=args.start,
            end_date=args.end,
            export_png=args.export_png
        )
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
