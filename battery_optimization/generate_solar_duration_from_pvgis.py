#!/usr/bin/env python3
"""
Generate solar duration curve report using REAL PVGIS data.

Uses actual PVGIS hourly production data instead of synthetic test data.
"""

from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

from core.reporting.result_models import SimulationResult
from reports import SolarDurationCurveReport


def load_pvgis_data() -> pd.DataFrame:
    """Load real PVGIS production data."""
    pvgis_file = Path("data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv")

    if not pvgis_file.exists():
        raise FileNotFoundError(f"PVGIS data not found: {pvgis_file}")

    df = pd.read_csv(pvgis_file)
    df['timestamp'] = pd.to_datetime(df['Unnamed: 0'])
    df = df.set_index('timestamp')

    return df


def create_simulation_result_from_pvgis() -> SimulationResult:
    """
    Create a SimulationResult from real PVGIS data.

    This is production-only (no battery, no consumption modeling).
    Focus is on solar production varighetskurve.
    """
    print("\n📊 Loading REAL PVGIS data...")
    df = load_pvgis_data()

    # Production data (AC from PVGIS)
    production_ac_kw = df['production_kw'].values

    # Estimate DC production (assuming 95% inverter efficiency)
    production_dc_kw = production_ac_kw / 0.95

    # Simple consumption model (commercial profile)
    hours = len(production_ac_kw)
    consumption_kw = 50 + 30 * np.abs(np.sin((np.arange(hours) + 6) * 2 * np.pi / 24))

    # Grid power (no battery)
    grid_power_kw = consumption_kw - production_ac_kw

    # Curtailment at 77 kW grid limit
    curtailment_kw = np.maximum(0, production_ac_kw - 77)

    # Spot prices (simplified)
    spot_price = 0.3 + 0.5 * np.abs(np.sin((np.arange(hours) + 6) * 2 * np.pi / 24))

    # Create timestamps (PVGIS is 2020 data with 8784 hours - leap year)
    start_date = datetime(2020, 1, 1)
    timestamps = pd.date_range(start_date, periods=hours, freq='h')

    print(f"  ✅ Loaded {hours} hours of data")
    print(f"  Max AC: {production_ac_kw.max():.2f} kW")
    print(f"  Annual: {production_ac_kw.sum():.1f} kWh = {production_ac_kw.sum()/1000:.1f} MWh")
    print(f"  Specific: {production_ac_kw.sum()/138.55:.0f} kWh/kWp")

    # Create SimulationResult
    result = SimulationResult(
        scenario_name='pvgis_real',
        timestamp=timestamps,
        production_dc_kw=production_dc_kw,
        production_ac_kw=production_ac_kw,
        consumption_kw=consumption_kw,
        grid_power_kw=grid_power_kw,
        battery_power_ac_kw=np.zeros(hours),
        battery_soc_kwh=np.zeros(hours),
        curtailment_kw=curtailment_kw,
        spot_price=spot_price,
        cost_summary={'total_cost_nok': 0},  # Not relevant for duration curve
        battery_config={},
        strategy_config={'type': 'NoControl'},
        simulation_metadata={
            'data_source': 'PVGIS',
            'location': 'Stavanger (58.97°N, 5.73°E)',
            'pv_capacity_kwp': 138.55,
            'year': 2020
        }
    )

    return result


def main():
    print("\n" + "="*70)
    print("📊 SOLAR DURATION CURVE - EKTE PVGIS DATA")
    print("="*70)

    # Load real PVGIS data
    result = create_simulation_result_from_pvgis()

    # Save result for future use
    print("\n💾 Saving simulation result...")
    output_dir = Path("results")
    result_dir = result.save(output_dir)
    print(f"  ✅ Saved: {result_dir}")

    # Generate solar duration curve report
    print("\n📈 Generating Solar Duration Curve Report...")
    report = SolarDurationCurveReport(
        results=result,
        output_dir=output_dir,
        pv_capacity_kwp=138.55,
        inverter_limit_kw=110,
        grid_limit_kw=77
    )

    report_path = report.generate()

    print("\n✅ REPORT COMPLETE")
    print("="*70)
    print(f"\n📄 Report: {report_path}")
    print(f"📊 Figures:")
    for fig in report.figures:
        print(f"   {fig.relative_to(output_dir)}")

    print("\n🎯 KEY FINDINGS (Real PVGIS data):")
    print(f"   Annual production: {result.production_ac_kw.sum()/1000:.1f} MWh")
    print(f"   Max AC power: {result.production_ac_kw.max():.1f} kW")
    print(f"   Hours > 77 kW: {(result.production_ac_kw > 77).sum()}")
    print(f"   Potential curtailment: {result.curtailment_kw.sum():.1f} kWh")

    print("\n" + "="*70)


if __name__ == "__main__":
    main()
