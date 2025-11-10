"""
Yearly LP Optimization - 12 Monthly Rolling Optimizations

Runs LP-based battery optimization for the entire year by solving
12 separate monthly problems with rolling SOC (final SOC of month j
becomes initial SOC of month j+1).

Compares with reference case (no battery) to calculate annual savings
and break-even battery cost.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.economic_cost import calculate_total_cost
from config import BatteryOptimizationConfig


def generate_synthetic_yearly_data(config):
    """
    Generate synthetic yearly data for testing.

    In production, this should be replaced with real data from:
    - PVGIS/PVLib for solar production
    - ENTSO-E for spot prices
    - Customer data for load consumption
    """
    print("\n" + "="*70)
    print("Generating Synthetic Yearly Data")
    print("="*70)

    # Date range for 2024
    timestamps = pd.date_range(
        start='2024-01-01',
        end='2024-12-31 23:00:00',
        freq='h',
        tz='Europe/Oslo'
    )

    T = len(timestamps)
    print(f"Time range: {timestamps[0]} to {timestamps[-1]}")
    print(f"Total hours: {T}")

    # 1. PV Production (kW)
    # Simple sinusoidal model with seasonal and daily variations
    day_of_year = timestamps.dayofyear.values
    hour_of_day = timestamps.hour.values

    # Seasonal component (winter low, summer high)
    seasonal_factor = 1 + 0.8 * np.sin(2 * np.pi * (day_of_year - 80) / 365)

    # Daily component (sunrise to sunset)
    daily_factor = np.maximum(0, np.sin(np.pi * (hour_of_day - 6) / 12))

    # Peak capacity varies by season
    pv_production = config.solar.pv_capacity_kwp * seasonal_factor * daily_factor * 0.7

    # Add some noise
    pv_production += np.random.normal(0, 2, T)
    pv_production = np.maximum(0, pv_production)

    print(f"\n1. PV Production:")
    print(f"  Mean: {pv_production.mean():.2f} kW")
    print(f"  Max: {pv_production.max():.2f} kW")
    print(f"  Annual: {pv_production.sum():.0f} kWh")

    # 2. Load Consumption (kW)
    # Commercial load profile: higher during day, lower at night
    is_daytime = (hour_of_day >= 6) & (hour_of_day <= 22)
    is_weekend = timestamps.weekday.values >= 5

    base_load = 25.0  # kW
    daytime_boost = 15.0 * is_daytime
    weekend_reduction = -5.0 * is_weekend

    load_consumption = base_load + daytime_boost + weekend_reduction + np.random.normal(0, 3, T)
    load_consumption = np.maximum(5, load_consumption)

    # Scale to match annual consumption target
    annual_target = config.consumption.annual_kwh
    current_annual = load_consumption.sum()
    load_consumption *= (annual_target / current_annual)

    print(f"\n2. Load Consumption:")
    print(f"  Mean: {load_consumption.mean():.2f} kW")
    print(f"  Max: {load_consumption.max():.2f} kW")
    print(f"  Annual: {load_consumption.sum():.0f} kWh")

    # 3. Spot Prices (NOK/kWh)
    # Realistic Norwegian spot price model
    # Higher during winter, peak hours, and with some randomness

    # Seasonal component (winter expensive, summer cheap)
    month = timestamps.month.values
    seasonal_price = 0.6 + 0.4 * ((month <= 3) | (month >= 11))

    # Daily component (peak hours more expensive)
    daily_price = 1.0 + 0.3 * is_daytime

    # Random component (market volatility)
    random_price = np.random.lognormal(0, 0.3, T)

    spot_prices = 0.5 * seasonal_price * daily_price * random_price

    print(f"\n3. Spot Prices:")
    print(f"  Mean: {spot_prices.mean():.3f} NOK/kWh")
    print(f"  Min: {spot_prices.min():.3f} NOK/kWh")
    print(f"  Max: {spot_prices.max():.3f} NOK/kWh")

    # Create DataFrame
    data = pd.DataFrame({
        'pv_production': pv_production,
        'load': load_consumption,
        'spot_price': spot_prices
    }, index=timestamps)

    print(f"\n✓ Synthetic data generated successfully")

    return data


def run_reference_case(data, config):
    """
    Calculate costs without battery (reference case).

    Grid import = max(0, load - pv)
    Grid export = max(0, pv - load), capped at grid limit
    """
    print("\n" + "="*70)
    print("Running Reference Case (No Battery)")
    print("="*70)

    # Net production (positive = surplus, negative = deficit)
    net = data['pv_production'] - data['load']

    # Grid power (positive = import, negative = export)
    grid_import = np.maximum(0, -net)
    grid_export_uncapped = np.maximum(0, net)

    # Apply grid export limit (77 kW)
    grid_limit = config.solar.grid_export_limit_kw
    grid_export = np.minimum(grid_export_uncapped, grid_limit)

    # Curtailment
    curtailment = grid_export_uncapped - grid_export

    print(f"Total grid import: {grid_import.sum():,.0f} kWh")
    print(f"Total grid export: {grid_export.sum():,.0f} kWh")
    print(f"Total curtailment: {curtailment.sum():,.0f} kWh")
    print(f"Max import: {grid_import.max():.2f} kW")

    # Calculate cost using economic_cost module
    cost_result = calculate_total_cost(
        grid_import_power=grid_import,
        grid_export_power=grid_export,
        timestamps=data.index,
        spot_prices=data['spot_price'].values
    )

    print(f"\nReference Case Costs:")
    print(f"  Total: {cost_result['total_cost_nok']:,.0f} NOK/year")
    print(f"  Energy: {cost_result['energy_cost_nok']:,.0f} NOK/year")
    print(f"  Peak: {cost_result['peak_cost_nok']:,.0f} NOK/year")

    return cost_result, grid_import, grid_export


def run_yearly_lp_optimization(data, config):
    """
    Run LP optimization for 12 months with rolling SOC.

    Returns:
        results_dict: Complete yearly results
    """
    print("\n" + "="*70)
    print("Running Yearly LP Optimization (12 Months)")
    print("="*70)

    optimizer = MonthlyLPOptimizer(config)

    # Initialize
    E_initial = 0.5 * config.battery_capacity_kwh  # Start at 50% SOC

    # Storage for results
    monthly_results = []
    all_P_charge = []
    all_P_discharge = []
    all_P_grid_import = []
    all_P_grid_export = []
    all_E_battery = []

    # Loop over 12 months
    for month in range(1, 13):
        print(f"\n{'='*70}")
        print(f"Month {month}/12")
        print(f"{'='*70}")

        # Extract month data
        month_data = data[data.index.month == month]

        # Run LP optimization
        result = optimizer.optimize_month(
            month_idx=month,
            pv_production=month_data['pv_production'].values,
            load_consumption=month_data['load'].values,
            spot_prices=month_data['spot_price'].values,
            timestamps=month_data.index,
            E_initial=E_initial
        )

        if not result.success:
            print(f"❌ Optimization failed for month {month}: {result.message}")
            return None

        monthly_results.append(result)

        # Store arrays
        all_P_charge.append(result.P_charge)
        all_P_discharge.append(result.P_discharge)
        all_P_grid_import.append(result.P_grid_import)
        all_P_grid_export.append(result.P_grid_export)
        all_E_battery.append(result.E_battery)

        # Update initial SOC for next month
        E_initial = result.E_battery_final

        print(f"✓ Month {month} complete - Objective: {result.objective_value:,.0f} NOK")

    # Concatenate all results
    yearly_P_charge = np.concatenate(all_P_charge)
    yearly_P_discharge = np.concatenate(all_P_discharge)
    yearly_P_grid_import = np.concatenate(all_P_grid_import)
    yearly_P_grid_export = np.concatenate(all_P_grid_export)
    yearly_E_battery = np.concatenate(all_E_battery)

    # Calculate total costs
    print("\n" + "="*70)
    print("Calculating Yearly Costs from LP Results")
    print("="*70)

    cost_result = calculate_total_cost(
        grid_import_power=yearly_P_grid_import,
        grid_export_power=yearly_P_grid_export,
        timestamps=data.index,
        spot_prices=data['spot_price'].values
    )

    print(f"\nLP Optimization Costs:")
    print(f"  Total: {cost_result['total_cost_nok']:,.0f} NOK/year")
    print(f"  Energy: {cost_result['energy_cost_nok']:,.0f} NOK/year")
    print(f"  Peak: {cost_result['peak_cost_nok']:,.0f} NOK/year")

    print(f"\nBattery Operation (Yearly):")
    print(f"  Total charge: {yearly_P_charge.sum():,.0f} kWh")
    print(f"  Total discharge: {yearly_P_discharge.sum():,.0f} kWh")
    print(f"  Cycles: {yearly_P_charge.sum() / config.battery_capacity_kwh:.1f}")
    print(f"  Final SOC: {yearly_E_battery[-1] / config.battery_capacity_kwh * 100:.1f}%")

    return {
        'monthly_results': monthly_results,
        'P_charge': yearly_P_charge,
        'P_discharge': yearly_P_discharge,
        'P_grid_import': yearly_P_grid_import,
        'P_grid_export': yearly_P_grid_export,
        'E_battery': yearly_E_battery,
        'cost_result': cost_result
    }


def calculate_break_even(annual_savings, battery_capacity_kwh, lifetime_years=15, discount_rate=0.05):
    """
    Calculate break-even battery cost where NPV = 0.

    NPV = -Initial_Cost + Σ(t=1..T) [Annual_Savings / (1+r)^t] = 0

    Solving for Initial_Cost:
    Initial_Cost = Annual_Savings * [(1 - (1+r)^-T) / r]
    """
    if annual_savings <= 0:
        return 0

    # Annuity factor
    annuity_factor = (1 - (1 + discount_rate)**(-lifetime_years)) / discount_rate

    # Total NPV of savings
    pv_savings = annual_savings * annuity_factor

    # Break-even cost per kWh
    breakeven_cost_per_kwh = pv_savings / battery_capacity_kwh

    return breakeven_cost_per_kwh


def main():
    """Main execution"""
    print("\n" + "="*70)
    print("YEARLY LP BATTERY OPTIMIZATION")
    print("="*70)

    # Configuration
    config = BatteryOptimizationConfig.from_yaml()

    # Battery sizing for this test
    config.battery_capacity_kwh = 100.0  # 100 kWh
    config.battery_power_kw = 50.0       # 50 kW

    print(f"\nSystem Configuration:")
    print(f"  PV Capacity: {config.solar.pv_capacity_kwp} kWp")
    print(f"  Inverter: {config.solar.inverter_capacity_kw} kW")
    print(f"  Grid Limit: {config.solar.grid_export_limit_kw} kW")
    print(f"  Battery: {config.battery_capacity_kwh} kWh / {config.battery_power_kw} kW")
    print(f"  Annual Load: {config.consumption.annual_kwh:,.0f} kWh")

    # Generate yearly data
    data = generate_synthetic_yearly_data(config)

    # 1. Run reference case (no battery)
    cost_ref, grid_import_ref, grid_export_ref = run_reference_case(data, config)

    # 2. Run LP optimization (with battery)
    lp_results = run_yearly_lp_optimization(data, config)

    if lp_results is None:
        print("\n❌ Yearly optimization failed!")
        return

    cost_lp = lp_results['cost_result']

    # 3. Calculate savings
    annual_savings = cost_ref['total_cost_nok'] - cost_lp['total_cost_nok']

    print("\n" + "="*70)
    print("SAVINGS ANALYSIS")
    print("="*70)

    print(f"\nAnnual Costs:")
    print(f"  Reference (no battery): {cost_ref['total_cost_nok']:,.0f} NOK")
    print(f"  LP with battery: {cost_lp['total_cost_nok']:,.0f} NOK")
    print(f"  Annual savings: {annual_savings:,.0f} NOK")

    # 4. Break-even analysis
    print("\n" + "="*70)
    print("BREAK-EVEN ANALYSIS")
    print("="*70)

    breakeven_cost = calculate_break_even(
        annual_savings=annual_savings,
        battery_capacity_kwh=config.battery_capacity_kwh,
        lifetime_years=15,
        discount_rate=0.05
    )

    print(f"\nEconomic Parameters:")
    print(f"  Battery size: {config.battery_capacity_kwh} kWh")
    print(f"  Lifetime: 15 years")
    print(f"  Discount rate: 5%")
    print(f"  Annual savings: {annual_savings:,.0f} NOK/year")

    print(f"\nBreak-Even Analysis:")
    print(f"  Break-even cost: {breakeven_cost:,.0f} NOK/kWh")
    print(f"  Market cost: 5,000 NOK/kWh")
    print(f"  Cost reduction needed: {5000 - breakeven_cost:,.0f} NOK/kWh ({(1-breakeven_cost/5000)*100:.1f}%)")

    if breakeven_cost >= 5000:
        print(f"\n✅ Battery is economically viable at current market prices!")
    else:
        print(f"\n⚠ Battery requires {5000 - breakeven_cost:,.0f} NOK/kWh cost reduction for viability")

    # 5. Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"\n✓ Yearly LP optimization completed successfully")
    print(f"✓ 12 monthly optimizations solved")
    print(f"✓ Annual savings: {annual_savings:,.0f} NOK")
    print(f"✓ Break-even cost: {breakeven_cost:,.0f} NOK/kWh")

    return {
        'config': config,
        'data': data,
        'cost_ref': cost_ref,
        'cost_lp': cost_lp,
        'lp_results': lp_results,
        'annual_savings': annual_savings,
        'breakeven_cost': breakeven_cost
    }


if __name__ == "__main__":
    results = main()

    if results:
        print("\n" + "="*70)
        print("✅ SUCCESS - Yearly LP Optimization Complete!")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("❌ FAILED")
        print("="*70)
        sys.exit(1)
