#!/usr/bin/env python3
"""
Run Full Year 2024 Battery Optimization Simulation
Generates comprehensive annual report with monthly breakdown
"""

import sys
import time
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

from src.simulation.battery_simulation import BatterySimulation

def generate_annual_report(results, config_path):
    """Generate comprehensive annual report from simulation results."""

    traj = results.trajectory

    print("\n" + "="*80)
    print("BATTERY OPTIMIZATION - ANNUAL REPORT 2024")
    print("="*80)

    # =========================================================================
    # 1. SIMULATION OVERVIEW
    # =========================================================================
    print("\n" + "─"*80)
    print("1. SIMULATION OVERVIEW")
    print("─"*80)

    start_date = traj.index[0]
    end_date = traj.index[-1]
    duration_days = (end_date - start_date).days + 1

    print(f"Period:           {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Duration:         {duration_days} days ({len(traj)} hours)")
    print(f"Resolution:       Hourly (PT60M)")
    print(f"Configuration:    {config_path}")

    # Battery configuration
    battery_capacity = traj['E_battery_kwh'].max() / 0.9  # Approximate from max SOC
    print(f"\nBattery System:")
    print(f"  Capacity:       {battery_capacity:.1f} kWh")
    print(f"  Usable range:   10% - 90% SOC")
    print(f"  Efficiency:     90% round-trip")

    # =========================================================================
    # 2. ANNUAL ENERGY FLOWS
    # =========================================================================
    print("\n" + "─"*80)
    print("2. ANNUAL ENERGY FLOWS")
    print("─"*80)

    # Calculate totals
    total_production = traj['pv_production_kw'].sum() if 'pv_production_kw' in traj else 0
    total_consumption = traj['consumption_kw'].sum() if 'consumption_kw' in traj else 0
    total_grid_import = traj['P_grid_import_kw'].sum()
    total_grid_export = traj['P_grid_export_kw'].sum()
    total_curtailment = traj['P_curtail_kw'].sum() if 'P_curtail_kw' in traj else 0
    total_charge = traj['P_charge_kw'].sum()
    total_discharge = traj['P_discharge_kw'].sum()

    print(f"PV Production:      {total_production:>10,.0f} kWh")
    print(f"Consumption:        {total_consumption:>10,.0f} kWh")
    print(f"Grid Import:        {total_grid_import:>10,.0f} kWh")
    print(f"Grid Export:        {total_grid_export:>10,.0f} kWh")
    print(f"Curtailment:        {total_curtailment:>10,.0f} kWh")

    print(f"\nBattery Operations:")
    print(f"  Total Charge:     {total_charge:>10,.0f} kWh")
    print(f"  Total Discharge:  {total_discharge:>10,.0f} kWh")
    print(f"  Cycles:           {total_discharge / battery_capacity:>10,.1f} full cycles")
    print(f"  Efficiency:       {(total_discharge / total_charge * 100) if total_charge > 0 else 0:>10,.1f}%")

    # Energy balance
    net_grid = total_grid_import - total_grid_export
    print(f"\nNet Grid:           {net_grid:>10,.0f} kWh {'(import)' if net_grid > 0 else '(export)'}")

    # =========================================================================
    # 3. SELF-CONSUMPTION & SELF-SUFFICIENCY
    # =========================================================================
    print("\n" + "─"*80)
    print("3. SELF-CONSUMPTION & SELF-SUFFICIENCY")
    print("─"*80)

    # Self-consumption: How much of PV production is used locally (not exported)
    pv_self_consumed = total_production - total_grid_export if total_production > 0 else 0
    self_consumption_rate = (pv_self_consumed / total_production * 100) if total_production > 0 else 0

    # Self-sufficiency: How much of consumption is covered by PV (not imported)
    self_supplied = total_consumption - total_grid_import if total_consumption > 0 else 0
    self_sufficiency_rate = (self_supplied / total_consumption * 100) if total_consumption > 0 else 0

    print(f"Self-Consumption:")
    print(f"  PV used locally:  {pv_self_consumed:>10,.0f} kWh")
    print(f"  Rate:             {self_consumption_rate:>10,.1f}%")

    print(f"\nSelf-Sufficiency:")
    print(f"  Consumption from PV: {self_supplied:>10,.0f} kWh")
    print(f"  Rate:             {self_sufficiency_rate:>10,.1f}%")

    # =========================================================================
    # 4. BATTERY PERFORMANCE
    # =========================================================================
    print("\n" + "─"*80)
    print("4. BATTERY PERFORMANCE")
    print("─"*80)

    soc_percent = traj['soc_percent']

    print(f"State of Charge (SOC):")
    print(f"  Average:          {soc_percent.mean():>10,.1f}%")
    print(f"  Minimum:          {soc_percent.min():>10,.1f}%")
    print(f"  Maximum:          {soc_percent.max():>10,.1f}%")
    print(f"  Std Dev:          {soc_percent.std():>10,.1f}%")

    # Count charge/discharge cycles
    charging_hours = (traj['P_charge_kw'] > 0.1).sum()
    discharging_hours = (traj['P_discharge_kw'] > 0.1).sum()
    idle_hours = len(traj) - charging_hours - discharging_hours

    print(f"\nOperating Hours:")
    print(f"  Charging:         {charging_hours:>10,} hours ({charging_hours/len(traj)*100:.1f}%)")
    print(f"  Discharging:      {discharging_hours:>10,} hours ({discharging_hours/len(traj)*100:.1f}%)")
    print(f"  Idle:             {idle_hours:>10,} hours ({idle_hours/len(traj)*100:.1f}%)")

    # Peak power
    max_charge_power = traj['P_charge_kw'].max()
    max_discharge_power = traj['P_discharge_kw'].max()

    print(f"\nPeak Power:")
    print(f"  Max Charge:       {max_charge_power:>10,.1f} kW")
    print(f"  Max Discharge:    {max_discharge_power:>10,.1f} kW")

    # =========================================================================
    # 5. GRID INTERACTION
    # =========================================================================
    print("\n" + "─"*80)
    print("5. GRID INTERACTION")
    print("─"*80)

    peak_import = traj['P_grid_import_kw'].max()
    peak_export = traj['P_grid_export_kw'].max()
    avg_import = traj[traj['P_grid_import_kw'] > 0]['P_grid_import_kw'].mean()
    avg_export = traj[traj['P_grid_export_kw'] > 0]['P_grid_export_kw'].mean()

    print(f"Import:")
    print(f"  Peak:             {peak_import:>10,.1f} kW")
    print(f"  Average:          {avg_import:>10,.1f} kW (when importing)")
    print(f"  Total:            {total_grid_import:>10,.0f} kWh")

    print(f"\nExport:")
    print(f"  Peak:             {peak_export:>10,.1f} kW")
    print(f"  Average:          {avg_export:>10,.1f} kW (when exporting)")
    print(f"  Total:            {total_grid_export:>10,.0f} kWh")

    # Count hours with import/export
    import_hours = (traj['P_grid_import_kw'] > 0).sum()
    export_hours = (traj['P_grid_export_kw'] > 0).sum()

    print(f"\nGrid Activity:")
    print(f"  Import hours:     {import_hours:>10,} ({import_hours/len(traj)*100:.1f}%)")
    print(f"  Export hours:     {export_hours:>10,} ({export_hours/len(traj)*100:.1f}%)")

    # =========================================================================
    # 6. MONTHLY BREAKDOWN
    # =========================================================================
    print("\n" + "─"*80)
    print("6. MONTHLY BREAKDOWN")
    print("─"*80)

    # Create monthly dataframe
    monthly = pd.DataFrame({
        'production': traj['pv_production_kw'] if 'pv_production_kw' in traj else 0,
        'consumption': traj['consumption_kw'] if 'consumption_kw' in traj else 0,
        'grid_import': traj['P_grid_import_kw'],
        'grid_export': traj['P_grid_export_kw'],
        'battery_charge': traj['P_charge_kw'],
        'battery_discharge': traj['P_discharge_kw'],
    }, index=traj.index).resample('ME').sum()

    print(f"\n{'Month':<10} {'Production':<12} {'Consumption':<13} {'Import':<10} {'Export':<10} {'Cycles':<8}")
    print("─" * 80)

    for month, row in monthly.iterrows():
        cycles = row['battery_discharge'] / battery_capacity
        print(f"{month.strftime('%Y-%m'):<10} "
              f"{row['production']:>10,.0f} kWh  "
              f"{row['consumption']:>10,.0f} kWh  "
              f"{row['grid_import']:>8,.0f} kWh  "
              f"{row['grid_export']:>8,.0f} kWh  "
              f"{cycles:>6.1f}")

    # =========================================================================
    # 7. SEASONAL ANALYSIS
    # =========================================================================
    print("\n" + "─"*80)
    print("7. SEASONAL ANALYSIS")
    print("─"*80)

    # Define seasons (Northern Hemisphere)
    def get_season(month):
        if month in [12, 1, 2]:
            return 'Winter'
        elif month in [3, 4, 5]:
            return 'Spring'
        elif month in [6, 7, 8]:
            return 'Summer'
        else:
            return 'Fall'

    traj['season'] = traj.index.month.map(get_season)
    seasonal = traj.groupby('season')[['pv_production_kw', 'consumption_kw',
                                        'P_grid_import_kw', 'P_grid_export_kw',
                                        'P_charge_kw', 'P_discharge_kw']].sum()

    for season in ['Winter', 'Spring', 'Summer', 'Fall']:
        if season in seasonal.index:
            row = seasonal.loc[season]
            cycles = row['P_discharge_kw'] / battery_capacity
            print(f"\n{season}:")
            print(f"  Production:       {row['pv_production_kw']:>10,.0f} kWh")
            print(f"  Consumption:      {row['consumption_kw']:>10,.0f} kWh")
            print(f"  Grid Import:      {row['P_grid_import_kw']:>10,.0f} kWh")
            print(f"  Grid Export:      {row['P_grid_export_kw']:>10,.0f} kWh")
            print(f"  Battery Cycles:   {cycles:>10,.1f}")

    # =========================================================================
    # 8. KEY PERFORMANCE INDICATORS
    # =========================================================================
    print("\n" + "─"*80)
    print("8. KEY PERFORMANCE INDICATORS (KPIs)")
    print("─"*80)

    # Calculate various KPIs
    capacity_factor = (total_production / (138.55 * 8760 if total_production > 0 else 1)) * 100  # 138.55 kWp system

    print(f"\nSystem Performance:")
    print(f"  PV Capacity Factor:     {capacity_factor:>8.1f}%")
    print(f"  Self-Consumption Rate:  {self_consumption_rate:>8.1f}%")
    print(f"  Self-Sufficiency Rate:  {self_sufficiency_rate:>8.1f}%")
    print(f"  Battery Utilization:    {(charging_hours + discharging_hours) / len(traj) * 100:>8.1f}%")

    print(f"\nEnergy Efficiency:")
    print(f"  Battery Round-Trip:     {(total_discharge / total_charge * 100) if total_charge > 0 else 0:>8.1f}%")
    print(f"  Grid Import/Export:     {total_grid_export / total_grid_import if total_grid_import > 0 else 0:>8.2f}")

    print(f"\nOperational Metrics:")
    print(f"  Annual Cycles:          {total_discharge / battery_capacity:>8.1f} cycles")
    print(f"  Avg Daily Throughput:   {(total_charge + total_discharge) / duration_days:>8.1f} kWh/day")
    print(f"  Battery DoD:            {(soc_percent.max() - soc_percent.min()):>8.1f}%")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    print(f"\n✅ Simulation completed successfully for full year 2024")
    print(f"   • {len(traj):,} timesteps processed")
    print(f"   • {total_discharge / battery_capacity:.1f} battery cycles")
    print(f"   • {self_consumption_rate:.1f}% self-consumption rate")
    print(f"   • {self_sufficiency_rate:.1f}% self-sufficiency rate")
    print(f"   • {net_grid:,.0f} kWh net grid {'import' if net_grid > 0 else 'export'}")

    print("\n" + "="*80)

    return {
        'total_production': total_production,
        'total_consumption': total_consumption,
        'total_grid_import': total_grid_import,
        'total_grid_export': total_grid_export,
        'battery_cycles': total_discharge / battery_capacity,
        'self_consumption_rate': self_consumption_rate,
        'self_sufficiency_rate': self_sufficiency_rate,
        'monthly': monthly,
        'seasonal': seasonal,
    }


def main():
    """Run yearly simulation and generate report."""

    config_path = 'configs/yearly_2024.yaml'

    print("="*80)
    print("BATTERY OPTIMIZATION - YEARLY SIMULATION 2024")
    print("="*80)
    print(f"\nConfiguration: {config_path}")
    print("Data sources:  Real CSV files (prices, PV, consumption)")
    print("Period:        January 1 - December 31, 2024 (full year)")
    print("Battery:       80 kWh / 60 kW")

    print("\n" + "─"*80)
    print("Starting simulation...")
    print("─"*80)
    print("\nThis may take 2-5 minutes for full year optimization...\n")

    # Run simulation with timing
    start_time = time.time()

    try:
        sim = BatterySimulation.from_config(config_path)
        results = sim.run()

        elapsed = time.time() - start_time

        print(f"\n✅ Simulation completed in {elapsed:.1f} seconds")
        print(f"   ({len(results.trajectory)} timesteps, {elapsed/len(results.trajectory)*1000:.1f} ms/timestep)")

        # Generate comprehensive report
        report_data = generate_annual_report(results, config_path)

        # Save trajectory to CSV
        output_file = 'results/yearly_2024_trajectory.csv'
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        results.trajectory.to_csv(output_file)
        print(f"\n💾 Full trajectory saved to: {output_file}")

        # Save monthly summary
        monthly_file = 'results/yearly_2024_monthly.csv'
        report_data['monthly'].to_csv(monthly_file)
        print(f"💾 Monthly summary saved to: {monthly_file}")

        return 0

    except Exception as e:
        print(f"\n❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
