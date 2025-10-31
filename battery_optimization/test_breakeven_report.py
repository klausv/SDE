"""
Test script for the new BreakevenReport system.

This creates sample SimulationResult instances and generates a break-even analysis
report to validate the reporting framework works correctly.
"""

from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from core.reporting import SimulationResult
from reports import BreakevenReport


def create_sample_simulation_results():
    """
    Create sample SimulationResult instances for testing.

    Returns:
        Tuple of (reference_result, battery_result)
    """
    # Create sample timestamps (1 year, hourly)
    start_date = datetime(2024, 1, 1)
    timestamps = pd.date_range(start_date, periods=8760, freq='h')

    # Sample data arrays (simplified for testing)
    hours = np.arange(8760)

    # Solar production (sinusoidal pattern with daily/yearly variation)
    production_dc = 150 * np.abs(np.sin(hours * 2 * np.pi / 24)) * (1 + 0.3 * np.sin(hours * 2 * np.pi / 8760))
    production_ac = production_dc * 0.95  # Inverter efficiency

    # Consumption (base load + daily variation)
    consumption = 50 + 30 * np.abs(np.sin((hours + 6) * 2 * np.pi / 24))

    # Reference scenario (no battery)
    grid_power_ref = consumption - production_ac
    curtailment_ref = np.maximum(0, production_ac - consumption - 77)  # 77 kW grid limit

    # Battery scenario
    battery_power = np.zeros(8760)
    battery_soc = np.full(8760, 10.0)  # Start at 10 kWh (50% SOC for 20 kWh battery)

    # Simple battery operation simulation
    for i in range(1, 8760):
        excess = production_ac[i] - consumption[i]

        if excess > 0:  # Charge battery
            charge_power = min(excess, 10.0, (18 - battery_soc[i-1]) * 0.9)  # 10 kW limit, max SOC 18 kWh
            battery_power[i] = charge_power
            battery_soc[i] = battery_soc[i-1] + charge_power * 0.9  # 90% efficiency
        else:  # Discharge battery
            discharge_power = min(abs(excess), 10.0, (battery_soc[i-1] - 2) * 0.9)  # 10 kW limit, min SOC 2 kWh
            battery_power[i] = -discharge_power
            battery_soc[i] = battery_soc[i-1] - discharge_power / 0.9

        battery_soc[i] = np.clip(battery_soc[i], 2, 18)

    grid_power_battery = consumption - production_ac - battery_power
    curtailment_battery = np.maximum(0, production_ac - consumption - battery_power - 77)

    # Spot prices (simplified: low at night, high during day)
    spot_price = 0.3 + 0.5 * np.abs(np.sin((hours + 6) * 2 * np.pi / 24))

    # Reference result
    reference = SimulationResult(
        scenario_name='reference',
        timestamp=timestamps,
        production_dc_kw=production_dc,
        production_ac_kw=production_ac,
        consumption_kw=consumption,
        grid_power_kw=grid_power_ref,
        battery_power_ac_kw=np.zeros(8760),
        battery_soc_kwh=np.zeros(8760),
        curtailment_kw=curtailment_ref,
        spot_price=spot_price,
        cost_summary={
            'total_cost_nok': 425000.0,
            'energy_cost_nok': 350000.0,
            'power_cost_nok': 75000.0
        },
        battery_config={},
        strategy_config={'type': 'NoControl'}
    )

    # Battery result
    battery = SimulationResult(
        scenario_name='simplerule_20kwh',
        timestamp=timestamps,
        production_dc_kw=production_dc,
        production_ac_kw=production_ac,
        consumption_kw=consumption,
        grid_power_kw=grid_power_battery,
        battery_power_ac_kw=battery_power,
        battery_soc_kwh=battery_soc,
        curtailment_kw=curtailment_battery,
        spot_price=spot_price,
        cost_summary={
            'total_cost_nok': 385000.0,  # 40,000 NOK savings
            'energy_cost_nok': 320000.0,
            'power_cost_nok': 65000.0
        },
        battery_config={
            'capacity_kwh': 20.0,
            'power_kw': 10.0,
            'efficiency': 0.90,
            'min_soc': 0.1,
            'max_soc': 0.9
        },
        strategy_config={
            'type': 'SimpleRule',
            'cheap_price_threshold': 0.3,
            'expensive_price_threshold': 0.8
        }
    )

    return reference, battery


def main():
    print("\n" + "="*80)
    print(" TESTING BREAKEVEN REPORT SYSTEM")
    print("="*80)

    # Create sample results
    print("\n1. Creating sample simulation results...")
    reference, battery = create_sample_simulation_results()
    print(f"   ✓ Reference scenario: {reference.scenario_name}")
    print(f"   ✓ Battery scenario: {battery.scenario_name}")
    print(f"   ✓ Annual savings: {reference.cost_summary['total_cost_nok'] - battery.cost_summary['total_cost_nok']:,.0f} NOK")

    # Save sample results
    print("\n2. Saving sample results...")
    output_dir = Path(__file__).parent / 'results'
    ref_dir = reference.save(output_dir)
    battery_dir = battery.save(output_dir)
    print(f"   ✓ Reference saved: {ref_dir}")
    print(f"   ✓ Battery saved: {battery_dir}")

    # Test loading
    print("\n3. Testing result loading...")
    loaded_ref = SimulationResult.load(ref_dir)
    loaded_battery = SimulationResult.load(battery_dir)
    print(f"   ✓ Reference loaded: {loaded_ref.scenario_name}")
    print(f"   ✓ Battery loaded: {loaded_battery.scenario_name}")

    # Generate break-even report
    print("\n4. Generating break-even analysis report...")
    report = BreakevenReport(
        reference=loaded_ref,
        battery_scenario=loaded_battery,
        output_dir=output_dir,
        battery_lifetime_years=10,
        discount_rate=0.05,
        market_cost_per_kwh=5000.0
    )

    report_path = report.generate()

    print("\n" + "="*80)
    print(" TEST COMPLETE")
    print("="*80)
    print(f"\nGenerated files:")
    print(f"  - Main report: {report_path}")
    print(f"  - Figures: {output_dir / 'figures' / 'breakeven'}")
    print(f"  - Simulations: {output_dir / 'simulations'}")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
