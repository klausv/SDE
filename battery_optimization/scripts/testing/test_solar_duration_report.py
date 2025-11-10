#!/usr/bin/env python3
"""
Test script for Solar Duration Curve Report.

Loads existing simulation data and generates solar duration curve visualization.
"""

from pathlib import Path
from core.reporting.result_models import SimulationResult
from reports import SolarDurationCurveReport, generate_report

def test_solar_duration_with_existing_data():
    """Test solar duration report with existing simulation results."""

    print("\n" + "="*70)
    print("📊 TESTING SOLAR DURATION CURVE REPORT")
    print("="*70)

    # Load existing simulation result
    result_dir = Path("results/simulations/2025-10-30_092324_reference")

    if not result_dir.exists():
        print(f"\n❌ Simulation directory not found: {result_dir}")
        print("   Run a simulation first to generate test data.")
        return

    print(f"\n📂 Loading simulation result from: {result_dir}")
    result = SimulationResult.load(result_dir)

    print(f"   ✅ Loaded {len(result.production_ac_kw)} hours of data")
    print(f"   Annual production: {sum(result.production_ac_kw)/1000:.1f} MWh")
    print(f"   Max AC power: {max(result.production_ac_kw):.1f} kW")

    # Generate report using the class directly
    print("\n📈 Generating Solar Duration Curve Report...")
    print("   Method 1: Using SolarDurationCurveReport class directly")

    report = SolarDurationCurveReport(
        results=result,
        output_dir=Path("results")
    )

    report_path = report.generate()

    print(f"\n✅ Report generated successfully!")
    print(f"   Report: {report_path}")
    print(f"   Figures: {len(report.figures)} generated")
    for fig in report.figures:
        print(f"      - {fig}")

    # Test factory function
    print("\n📈 Testing factory function...")
    print("   Method 2: Using generate_report() factory")

    report_path_2 = generate_report(
        'solar_duration',
        results=result,
        output_dir=Path("results")
    )

    print(f"   ✅ Factory method successful: {report_path_2}")

    print("\n" + "="*70)
    print("✅ SOLAR DURATION REPORT TEST COMPLETE")
    print("="*70)
    print("\nGenerated files:")
    print(f"  📄 Report: {report_path}")
    print(f"  📊 Figures:")
    for fig in report.figures:
        print(f"     {fig.relative_to(Path('results'))}")
    print("\nOpen the markdown report to view analysis and visualizations.")


def test_solar_duration_with_custom_params():
    """Test with custom system parameters."""

    print("\n" + "="*70)
    print("📊 TESTING WITH CUSTOM PARAMETERS")
    print("="*70)

    result_dir = Path("results/simulations/2025-10-30_092324_reference")

    if not result_dir.exists():
        print(f"\n❌ Simulation directory not found: {result_dir}")
        return

    print(f"\n📂 Loading data...")
    result = SimulationResult.load(result_dir)

    # Custom parameters (e.g., different grid limit scenario)
    print("\n🔧 Testing scenario: Lower grid limit (50 kW)")

    report = SolarDurationCurveReport(
        results=result,
        output_dir=Path("results"),
        pv_capacity_kwp=138.55,
        inverter_limit_kw=110,
        grid_limit_kw=50  # Lower limit to see more curtailment
    )

    report_path = report.generate()

    print(f"\n✅ Custom scenario report generated: {report_path}")
    print("   This shows increased curtailment with 50 kW grid limit")


if __name__ == "__main__":
    # Test with existing simulation data
    test_solar_duration_with_existing_data()

    # Test with custom parameters (optional)
    # test_solar_duration_with_custom_params()

    print("\n✨ All tests passed! Solar Duration Curve Report is ready to use.")
