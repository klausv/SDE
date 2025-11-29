#!/usr/bin/env python3
"""
Run Full Year 2024 Battery Optimization - Simplified Report
"""

import sys
import time
import numpy as np
import pandas as pd
from pathlib import Path

from src.simulation.battery_simulation import BatterySimulation
from src.data.file_loaders import load_price_data, load_production_data, load_consumption_data


def main():
    """Run yearly simulation with simplified report."""

    config_path = 'configs/yearly_2024.yaml'

    print("="*80)
    print("BATTERY OPTIMIZATION - YEARLY SIMULATION 2024")
    print("="*80)
    print(f"\nConfiguration: {config_path}")
    print("Period:        January 1 - December 31, 2024 (full year)")
    print("Battery:       80 kWh / 60 kW")

    print("\n" + "─"*80)
    print("Loading input data...")
    print("─"*80)

    # Load input data separately for reporting
    try:
        timestamps_price, prices = load_price_data('data/spot_prices/NO2_2024_60min_real.csv')
        timestamps_prod, production = load_production_data('data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv')
        timestamps_cons, consumption = load_consumption_data('data/consumption/commercial_2024.csv')

        print(f"✅ Price data:       {len(timestamps_price)} hours")
        print(f"✅ Production data:  {len(timestamps_prod)} hours")
        print(f"✅ Consumption data: {len(timestamps_cons)} hours")
    except Exception as e:
        print(f"❌ Failed to load input data: {e}")
        return 1

    print("\n" + "─"*80)
    print("Running simulation...")
    print("─"*80)
    print("\nThis may take 5-10 minutes for full year optimization...\n")

    start_time = time.time()

    try:
        sim = BatterySimulation.from_config(config_path)
        results = sim.run()

        elapsed = time.time() - start_time
        traj = results.trajectory

        print(f"\n✅ Simulation completed in {elapsed:.1f} seconds")
        print(f"   Processed: {len(traj)} timesteps")
        print(f"   Speed: {elapsed/len(traj)*1000:.1f} ms/timestep")

        # =====================================================================
        # GENERATE REPORT
        # =====================================================================

        print("\n" + "="*80)
        print("BATTERY OPTIMIZATION - ANNUAL REPORT 2024")
        print("="*80)

        # Basic info
        start_date = traj.index[0]
        end_date = traj.index[-1]
        duration_days = (end_date - start_date).days + 1

        print(f"\nPeriod:           {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Duration:         {duration_days} days ({len(traj)} hours)")

        # Battery capacity (approximate from SOC)
        battery_capacity = 80.0  # From config

        # Calculate totals from trajectory
        total_grid_import = traj['P_grid_import_kw'].sum()
        total_grid_export = traj['P_grid_export_kw'].sum()
        total_charge = traj['P_charge_kw'].sum()
        total_discharge = traj['P_discharge_kw'].sum()
        total_curtail = traj['P_curtail_kw'].sum() if 'P_curtail_kw' in traj else 0

        # Calculate totals from input data (for the same period)
        mask = (timestamps_prod >= start_date) & (timestamps_prod <= end_date)
        total_production = production[mask].sum()
        total_consumption = consumption[mask].sum()

        print("\n" + "─"*80)
        print("ENERGY FLOWS")
        print("─"*80)
        print(f"\nInput Data (from CSV files):")
        print(f"  PV Production:      {total_production:>12,.0f} kWh")
        print(f"  Consumption:        {total_consumption:>12,.0f} kWh")

        print(f"\nGrid Interaction (optimized):")
        print(f"  Grid Import:        {total_grid_import:>12,.0f} kWh")
        print(f"  Grid Export:        {total_grid_export:>12,.0f} kWh")
        print(f"  Net Grid:           {total_grid_import - total_grid_export:>12,.0f} kWh")
        if total_curtail > 0:
            print(f"  Curtailment:        {total_curtail:>12,.0f} kWh")

        print(f"\nBattery Operations:")
        print(f"  Total Charge:       {total_charge:>12,.0f} kWh")
        print(f"  Total Discharge:    {total_discharge:>12,.0f} kWh")
        print(f"  Full Cycles:        {total_discharge / battery_capacity:>12.1f} cycles")
        print(f"  Round-trip Eff:     {(total_discharge / total_charge * 100) if total_charge > 0 else 0:>12.1f}%")

        # Self-consumption metrics
        pv_self_consumed = total_production - total_grid_export
        self_consumption_rate = (pv_self_consumed / total_production * 100) if total_production > 0 else 0
        self_supplied = total_consumption - total_grid_import
        self_sufficiency_rate = (self_supplied / total_consumption * 100) if total_consumption > 0 else 0

        print("\n" + "─"*80)
        print("SELF-CONSUMPTION METRICS")
        print("─"*80)
        print(f"\nSelf-Consumption:")
        print(f"  PV used locally:    {pv_self_consumed:>12,.0f} kWh")
        print(f"  Rate:               {self_consumption_rate:>12.1f}%")

        print(f"\nSelf-Sufficiency:")
        print(f"  From PV:            {self_supplied:>12,.0f} kWh")
        print(f"  Rate:               {self_sufficiency_rate:>12.1f}%")

        # SOC statistics
        soc_percent = traj['soc_percent']

        print("\n" + "─"*80)
        print("BATTERY PERFORMANCE")
        print("─"*80)
        print(f"\nState of Charge (SOC):")
        print(f"  Average:            {soc_percent.mean():>12.1f}%")
        print(f"  Minimum:            {soc_percent.min():>12.1f}%")
        print(f"  Maximum:            {soc_percent.max():>12.1f}%")
        print(f"  Std Dev:            {soc_percent.std():>12.1f}%")

        # Operating hours
        charging_hours = (traj['P_charge_kw'] > 0.1).sum()
        discharging_hours = (traj['P_discharge_kw'] > 0.1).sum()
        idle_hours = len(traj) - charging_hours - discharging_hours

        print(f"\nOperating Time:")
        print(f"  Charging:           {charging_hours:>12,} hours ({charging_hours/len(traj)*100:.1f}%)")
        print(f"  Discharging:        {discharging_hours:>12,} hours ({discharging_hours/len(traj)*100:.1f}%)")
        print(f"  Idle:               {idle_hours:>12,} hours ({idle_hours/len(traj)*100:.1f}%)")

        # Grid statistics
        peak_import = traj['P_grid_import_kw'].max()
        peak_export = traj['P_grid_export_kw'].max()

        print("\n" + "─"*80)
        print("GRID INTERACTION")
        print("─"*80)
        print(f"\nPeak Power:")
        print(f"  Import:             {peak_import:>12.1f} kW")
        print(f"  Export:             {peak_export:>12.1f} kW")

        import_hours = (traj['P_grid_import_kw'] > 0).sum()
        export_hours = (traj['P_grid_export_kw'] > 0).sum()

        print(f"\nGrid Activity:")
        print(f"  Import hours:       {import_hours:>12,} ({import_hours/len(traj)*100:.1f}%)")
        print(f"  Export hours:       {export_hours:>12,} ({export_hours/len(traj)*100:.1f}%)")

        # Monthly breakdown
        print("\n" + "─"*80)
        print("MONTHLY BREAKDOWN")
        print("─"*80)

        monthly = pd.DataFrame({
            'grid_import': traj['P_grid_import_kw'],
            'grid_export': traj['P_grid_export_kw'],
            'battery_charge': traj['P_charge_kw'],
            'battery_discharge': traj['P_discharge_kw'],
        }, index=traj.index).resample('ME').sum()

        print(f"\n{'Month':<10} {'Import':<12} {'Export':<12} {'Charge':<12} {'Discharge':<12} {'Cycles':<8}")
        print("─" * 80)

        for month, row in monthly.iterrows():
            cycles = row['battery_discharge'] / battery_capacity
            print(f"{month.strftime('%Y-%m'):<10} "
                  f"{row['grid_import']:>10,.0f} kWh "
                  f"{row['grid_export']:>10,.0f} kWh "
                  f"{row['battery_charge']:>10,.0f} kWh "
                  f"{row['battery_discharge']:>10,.0f} kWh "
                  f"{cycles:>6.1f}")

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)

        print(f"\n✅ Full year simulation completed")
        print(f"   • {len(traj):,} timesteps optimized")
        print(f"   • {total_discharge / battery_capacity:.1f} battery cycles")
        print(f"   • {self_consumption_rate:.1f}% self-consumption rate")
        print(f"   • {self_sufficiency_rate:.1f}% self-sufficiency rate")
        print(f"   • {(total_grid_import - total_grid_export):,.0f} kWh net grid import")

        # Save results
        output_dir = Path('results')
        output_dir.mkdir(exist_ok=True)

        trajectory_file = output_dir / 'yearly_2024_trajectory.csv'
        traj.to_csv(trajectory_file)
        print(f"\n💾 Trajectory saved: {trajectory_file}")

        monthly_file = output_dir / 'yearly_2024_monthly.csv'
        monthly.to_csv(monthly_file)
        print(f"💾 Monthly summary saved: {monthly_file}")

        print("\n" + "="*80)

        return 0

    except Exception as e:
        print(f"\n❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
