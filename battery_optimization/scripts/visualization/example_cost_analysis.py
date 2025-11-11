"""
Example Usage: Interactive Cost Analysis Dashboard
===================================================

Demonstrates various usage patterns for the Plotly cost analysis dashboard.

Usage:
    python scripts/visualization/example_cost_analysis.py

Author: Klaus + Claude
Date: November 2025
"""

from pathlib import Path
from plot_costs_3weeks_plotly import generate_cost_report, apply_light_theme


def example_1_basic_usage():
    """Example 1: Basic usage with default 3-week June period"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Usage - 3 Weeks in June")
    print("="*80)

    report_path = generate_cost_report(
        trajectory_path=Path('results/yearly_2024/trajectory.csv'),
        output_dir=Path('results'),
        period='3weeks_june',
        start_date='2024-06-01',
        period_days=21
    )

    print(f"\n✓ Report generated: {report_path}")
    return report_path


def example_2_winter_period():
    """Example 2: Winter period analysis (high consumption)"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Winter Period - 2 Weeks in February")
    print("="*80)

    report_path = generate_cost_report(
        trajectory_path=Path('results/yearly_2024/trajectory.csv'),
        output_dir=Path('results'),
        period='2weeks_feb',
        start_date='2024-02-01',
        period_days=14
    )

    print(f"\n✓ Report generated: {report_path}")
    return report_path


def example_3_summer_peak():
    """Example 3: Summer peak production period"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Summer Peak - 1 Week in July")
    print("="*80)

    report_path = generate_cost_report(
        trajectory_path=Path('results/yearly_2024/trajectory.csv'),
        output_dir=Path('results'),
        period='1week_july',
        start_date='2024-07-15',
        period_days=7
    )

    print(f"\n✓ Report generated: {report_path}")
    return report_path


def example_4_with_reference():
    """Example 4: Explicit reference scenario comparison"""
    print("\n" + "="*80)
    print("EXAMPLE 4: With Reference Trajectory - 3 Weeks May")
    print("="*80)

    # Note: This assumes you have a reference trajectory CSV
    # If not available, the script will simulate it automatically

    report_path = generate_cost_report(
        trajectory_path=Path('results/yearly_2024/trajectory.csv'),
        reference_path=Path('results/yearly_2024/reference_trajectory.csv'),
        output_dir=Path('results'),
        period='3weeks_may',
        start_date='2024-05-01',
        period_days=21
    )

    print(f"\n✓ Report generated: {report_path}")
    return report_path


def example_5_monthly_analysis():
    """Example 5: Full month analysis"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Full Month Analysis - September")
    print("="*80)

    report_path = generate_cost_report(
        trajectory_path=Path('results/yearly_2024/trajectory.csv'),
        output_dir=Path('results'),
        period='month_september',
        start_date='2024-09-01',
        period_days=30
    )

    print(f"\n✓ Report generated: {report_path}")
    return report_path


def example_6_programmatic_access():
    """Example 6: Programmatic access to cost data"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Programmatic Data Access")
    print("="*80)

    from plot_costs_3weeks_plotly import prepare_cost_data
    import pandas as pd

    # Load data
    trajectory_df = pd.read_csv('results/yearly_2024/trajectory.csv')
    prices_df = pd.read_csv('data/spot_prices/NO2_2024_60min_real.csv')

    # Simulate reference (no battery)
    reference_df = trajectory_df.copy()
    reference_df['P_charge_kw'] = 0
    reference_df['P_discharge_kw'] = 0
    reference_df['E_battery_kwh'] = 0

    # Prepare cost data
    battery_costs, reference_costs = prepare_cost_data(
        trajectory_df, reference_df, prices_df,
        start_date='2024-06-01',
        period_days=21
    )

    # Analyze costs
    total_energy_cost = battery_costs['net_energy_cost'].sum()
    total_degradation = battery_costs['degradation_cost'].sum()
    total_cost = battery_costs['total_cost'].sum()

    ref_total_cost = reference_costs['total_cost'].sum()
    savings = ref_total_cost - total_cost
    savings_pct = (savings / ref_total_cost * 100) if ref_total_cost > 0 else 0

    print(f"\n  Battery Scenario Costs:")
    print(f"    Energy cost:      {total_energy_cost:>10,.2f} kr")
    print(f"    Degradation:      {total_degradation:>10,.2f} kr")
    print(f"    Total cost:       {total_cost:>10,.2f} kr")

    print(f"\n  Reference Scenario:")
    print(f"    Total cost:       {ref_total_cost:>10,.2f} kr")

    print(f"\n  Savings Analysis:")
    print(f"    Total savings:    {savings:>10,.2f} kr ({savings_pct:>5.1f}%)")
    print(f"    Avg daily:        {savings/21:>10,.2f} kr/day")

    # Daily breakdown
    daily_costs = battery_costs.groupby(
        battery_costs['timestamp'].dt.date
    )['total_cost'].sum()

    print(f"\n  Daily Cost Statistics:")
    print(f"    Max daily cost:   {daily_costs.max():>10,.2f} kr")
    print(f"    Min daily cost:   {daily_costs.min():>10,.2f} kr")
    print(f"    Avg daily cost:   {daily_costs.mean():>10,.2f} kr")

    return battery_costs, reference_costs


def run_all_examples():
    """Run all examples sequentially"""
    print("\n" + "#"*80)
    print("# INTERACTIVE COST ANALYSIS DASHBOARD - EXAMPLES")
    print("#"*80)

    # Apply theme globally
    apply_light_theme()

    # Run examples
    reports = []

    try:
        reports.append(example_1_basic_usage())
    except Exception as e:
        print(f"  ⚠ Example 1 failed: {e}")

    try:
        reports.append(example_2_winter_period())
    except Exception as e:
        print(f"  ⚠ Example 2 failed: {e}")

    try:
        reports.append(example_3_summer_peak())
    except Exception as e:
        print(f"  ⚠ Example 3 failed: {e}")

    try:
        reports.append(example_4_with_reference())
    except Exception as e:
        print(f"  ⚠ Example 4 failed: {e}")

    try:
        reports.append(example_5_monthly_analysis())
    except Exception as e:
        print(f"  ⚠ Example 5 failed: {e}")

    try:
        battery_costs, reference_costs = example_6_programmatic_access()
    except Exception as e:
        print(f"  ⚠ Example 6 failed: {e}")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"  Reports generated: {len([r for r in reports if r])}")
    print("\n  Generated files:")
    for report in reports:
        if report:
            print(f"    - {report}")

    print("\n" + "#"*80)
    print("# ALL EXAMPLES COMPLETE")
    print("#"*80 + "\n")


if __name__ == "__main__":
    # Run all examples
    run_all_examples()

    # Or run individual examples:
    # example_1_basic_usage()
    # example_2_winter_period()
    # example_6_programmatic_access()
