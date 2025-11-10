"""
Practical Example: Integrating Dual Variable Attribution with WeeklyOptimizer

This example shows how to:
1. Extract dual variables from PuLP LP solution
2. Attribute battery value to specific functions using duals
3. Aggregate weekly results to annual breakdown
4. Generate stakeholder-friendly reports

Run this example after having WeeklyOptimizer results.
"""

import sys
sys.path.append('/mnt/c/Users/klaus/klauspython/SDE/battery_optimization')

import numpy as np
from src.optimization.dual_value_attribution import DualValueAttributor, DualVariables
from src.optimization.weekly_optimizer import WeeklyOptimizer
from src.config import Config


def extract_duals_from_weekly_optimizer(optimizer: WeeklyOptimizer) -> DualVariables:
    """
    Extract dual variables from WeeklyOptimizer's solved LP problem.

    Parameters:
    -----------
    optimizer : WeeklyOptimizer
        Solved weekly optimization problem

    Returns:
    --------
    DualVariables
        Organized dual variables by constraint type
    """
    prob = optimizer.prob  # Access LP problem

    # Check that problem was solved successfully
    if prob.status != 1:  # 1 = Optimal
        raise ValueError(f"LP not solved to optimality. Status: {prob.status}")

    # Initialize lists for each constraint type
    duals_dict = {
        'peak': [],
        'soc_dynamics': [],
        'soc_upper': [],
        'soc_lower': [],
        'export_limit': [],
        'energy_balance': [],
        'charge_limit': [],
        'discharge_limit': []
    }

    # Extract duals from all constraints
    for name, constraint in prob.constraints.items():
        dual_value = constraint.pi if constraint.pi is not None else 0.0

        # Categorize by constraint name pattern
        name_lower = name.lower()

        if 'peak' in name_lower:
            duals_dict['peak'].append(dual_value)
        elif 'soc_dynamics' in name_lower or 'battery_balance' in name_lower:
            duals_dict['soc_dynamics'].append(dual_value)
        elif 'soc_max' in name_lower or 'capacity_upper' in name_lower:
            duals_dict['soc_upper'].append(dual_value)
        elif 'soc_min' in name_lower or 'capacity_lower' in name_lower:
            duals_dict['soc_lower'].append(dual_value)
        elif 'export_limit' in name_lower or 'grid_limit' in name_lower:
            duals_dict['export_limit'].append(dual_value)
        elif 'energy_balance' in name_lower or 'power_balance' in name_lower:
            duals_dict['energy_balance'].append(dual_value)
        elif 'charge_limit' in name_lower or 'max_charge' in name_lower:
            duals_dict['charge_limit'].append(dual_value)
        elif 'discharge_limit' in name_lower or 'max_discharge' in name_lower:
            duals_dict['discharge_limit'].append(dual_value)

    # Convert to numpy arrays
    return DualVariables(
        peak_constraints=np.array(duals_dict['peak']),
        soc_dynamics=np.array(duals_dict['soc_dynamics']),
        soc_upper_bounds=np.array(duals_dict['soc_upper']),
        soc_lower_bounds=np.array(duals_dict['soc_lower']),
        export_limits=np.array(duals_dict['export_limit']),
        energy_balance=np.array(duals_dict['energy_balance']),
        charge_limits=np.array(duals_dict['charge_limit']),
        discharge_limits=np.array(duals_dict['discharge_limit'])
    )


def demonstrate_weekly_attribution():
    """
    Example: Attribute value for a single week using dual variables.
    """
    print("="*60)
    print("Dual Variable Attribution - Weekly Example")
    print("="*60)

    # Initialize configuration
    config = Config()

    # Example: Create WeeklyOptimizer for week 1 (winter)
    # In practice, you'd loop through all 52 weeks
    week_num = 1

    # You need to have:
    # - spot_prices: hourly electricity prices [NOK/kWh] for 168 hours
    # - pv_production: hourly PV output [kW] for 168 hours
    # - consumption: hourly consumption [kW] for 168 hours (if applicable)

    # Placeholder data (replace with real data from your data fetchers)
    hours_per_week = 168
    spot_prices = np.random.uniform(0.3, 1.2, hours_per_week)  # NOK/kWh
    pv_production = np.random.uniform(0, 100, hours_per_week)  # kW (replace with real PVGIS)
    energy_tariff = np.full(hours_per_week, 0.15)  # NOK/kWh (constant tariff)

    # Create and solve optimizer (replace with your actual optimizer instantiation)
    # optimizer = WeeklyOptimizer(
    #     week_num=week_num,
    #     spot_prices=spot_prices,
    #     pv_production=pv_production,
    #     config=config
    # )
    # optimizer.solve()

    # For demonstration, assume optimizer is solved
    print(f"\nWeek {week_num} Optimization Complete")
    print("-" * 60)

    # Extract dual variables
    # duals = extract_duals_from_weekly_optimizer(optimizer)
    # print(f"Extracted {len(duals.peak_constraints)} peak constraint duals")
    # print(f"Extracted {len(duals.soc_dynamics)} SOC dynamics duals")
    # print(f"Extracted {len(duals.export_limits)} export limit duals")

    # Initialize value attributor
    attributor = DualValueAttributor(
        power_tariff_rate=config.POWER_TARIFF_HIGH,  # NOK/kW/month
        efficiency=config.BATTERY_EFFICIENCY,
        eur_to_nok=config.EUR_TO_NOK
    )

    # Get solution data from optimizer
    # solution_data = {
    #     'P_charge': optimizer.P_charge_values,      # [kW]
    #     'P_discharge': optimizer.P_discharge_values, # [kW]
    #     'SOC': optimizer.SOC_values                  # [kWh]
    # }

    # Attribute value using dual variables
    # week_values = attributor.attribute_weekly_value(
    #     duals=duals,
    #     solution_data=solution_data,
    #     spot_prices=spot_prices,
    #     energy_tariff=energy_tariff,
    #     pv_production=pv_production,
    #     battery_capacity_kwh=config.BATTERY_CAPACITY_KWH
    # )

    # Print results
    # print("\nValue Attribution for Week", week_num)
    # print("-" * 60)
    # for category, value in week_values.to_dict().items():
    #     print(f"{category:30s}: {value:10.2f} kr")

    print("\n[This is a template - replace placeholder data with real optimizer]")


def demonstrate_annual_attribution():
    """
    Example: Aggregate 52 weekly attributions to annual totals.
    """
    print("\n" + "="*60)
    print("Annual Value Attribution - 52 Weeks")
    print("="*60)

    # Initialize attributor
    config = Config()
    attributor = DualValueAttributor(
        power_tariff_rate=config.POWER_TARIFF_HIGH,
        efficiency=config.BATTERY_EFFICIENCY
    )

    # Loop through all 52 weeks
    weekly_attributions = []

    # for week_num in range(1, 53):
    #     # 1. Get data for this week
    #     spot_prices = get_spot_prices_for_week(week_num)
    #     pv_production = get_pv_for_week(week_num)
    #     energy_tariff = get_tariff_for_week(week_num)
    #
    #     # 2. Solve optimization
    #     optimizer = WeeklyOptimizer(week_num, spot_prices, pv_production, config)
    #     optimizer.solve()
    #
    #     # 3. Extract duals
    #     duals = extract_duals_from_weekly_optimizer(optimizer)
    #
    #     # 4. Get solution
    #     solution = optimizer.get_solution_dict()
    #
    #     # 5. Attribute value
    #     week_values = attributor.attribute_weekly_value(
    #         duals=duals,
    #         solution_data=solution,
    #         spot_prices=spot_prices,
    #         energy_tariff=energy_tariff,
    #         pv_production=pv_production,
    #         battery_capacity_kwh=config.BATTERY_CAPACITY_KWH
    #     )
    #
    #     weekly_attributions.append(week_values)
    #
    #     if week_num % 13 == 0:
    #         print(f"Processed {week_num}/52 weeks...")

    # Aggregate to annual totals
    # annual_values = attributor.aggregate_annual_attribution(weekly_attributions)

    # Print annual report
    # print("\n" + "="*60)
    # print("ANNUAL VALUE ATTRIBUTION REPORT")
    # print("="*60)
    # print(f"\nBattery: {config.BATTERY_CAPACITY_KWH} kWh @ {config.BATTERY_POWER_KW} kW")
    # print(f"Location: Stavanger ({config.LATITUDE}°N, {config.LONGITUDE}°E)")
    # print(f"PV System: {config.PV_CAPACITY_KW} kWp")
    # print("\n" + "-"*60)
    # print("Value Breakdown:")
    # print("-"*60)

    # total_gross = (annual_values.peak_shaving +
    #                annual_values.curtailment_avoidance +
    #                annual_values.arbitrage +
    #                annual_values.self_consumption)

    # for category, value in annual_values.to_dict().items():
    #     if category == 'Total Net Value':
    #         print("-"*60)
    #     if 'Degradation' not in category and 'Total' not in category:
    #         percentage = (value / total_gross * 100) if total_gross > 0 else 0
    #         print(f"{category:30s}: {value:10,.0f} kr  ({percentage:5.1f}%)")
    #     else:
    #         print(f"{category:30s}: {value:10,.0f} kr")

    # print("="*60)

    print("\n[Template - integrate with your 52-week loop]")


def demonstrate_validation():
    """
    Example: Validate dual-based attribution against manual method.
    """
    print("\n" + "="*60)
    print("Validation: Dual Attribution vs Manual Method")
    print("="*60)

    # After running both methods:
    # dual_based = {...}  # From DualValueAttributor
    # manual = {...}      # From your existing manual allocation

    # Compare totals
    # print("\nComparison:")
    # print("-"*60)
    # print(f"{'Category':<30s} {'Dual':<12s} {'Manual':<12s} {'Diff %':<10s}")
    # print("-"*60)

    # for category in ['peak_shaving', 'arbitrage', 'curtailment', 'self_consumption']:
    #     dual_val = dual_based[category]
    #     manual_val = manual[category]
    #     diff_pct = ((dual_val - manual_val) / manual_val * 100) if manual_val != 0 else 0
    #
    #     print(f"{category:<30s} {dual_val:>10,.0f} kr {manual_val:>10,.0f} kr {diff_pct:>8.1f}%")

    # Total check
    # dual_total = sum(dual_based.values())
    # manual_total = sum(manual.values())
    # print("-"*60)
    # print(f"{'Total':<30s} {dual_total:>10,.0f} kr {manual_total:>10,.0f} kr")

    # Sanity checks
    # print("\n" + "="*60)
    # print("Sanity Checks:")
    # print("="*60)

    # 1. Value conservation
    # total_savings = baseline_cost - optimized_cost
    # assert abs(dual_total - total_savings) < total_savings * 0.01, "Value not conserved!"
    # print("✓ Value conservation: PASS")

    # 2. No negative values (except degradation)
    # assert dual_based['peak_shaving'] >= 0, "Negative peak shaving!"
    # assert dual_based['curtailment'] >= 0, "Negative curtailment!"
    # assert dual_based['arbitrage'] >= 0, "Negative arbitrage!"
    # print("✓ Non-negative values: PASS")

    # 3. Physical bounds
    # max_curtailment = estimate_max_curtailment(pv_production, grid_limit)
    # assert dual_based['curtailment'] <= max_curtailment, "Curtailment value too high!"
    # print("✓ Physical bounds: PASS")

    print("\n[Validation template - compare your results]")


def generate_stakeholder_report(annual_values_dict):
    """
    Generate executive-friendly report from dual-based attribution.

    Parameters:
    -----------
    annual_values_dict : dict
        Output from DualValueAttributor.aggregate_annual_attribution()
    """
    print("\n" + "="*80)
    print("BATTERY ECONOMIC VALUE ATTRIBUTION REPORT")
    print("="*80)

    print("\nEXECUTIVE SUMMARY")
    print("-"*80)

    total_gross = sum(v for k, v in annual_values_dict.items()
                      if k not in ['Degradation Cost', 'Total Net Value'])
    total_net = annual_values_dict.get('Total Net Value', 0)

    print(f"\nGross Annual Value:     {total_gross:>12,.0f} kr")
    print(f"Battery Degradation:    {annual_values_dict.get('Degradation Cost', 0):>12,.0f} kr")
    print(f"Net Annual Value:       {total_net:>12,.0f} kr")

    print("\n\nVALUE BREAKDOWN BY FUNCTION")
    print("-"*80)
    print(f"{'Category':<40s} {'Value (kr)':<15s} {'% of Total':<12s}")
    print("-"*80)

    categories = [
        ('Peak Shaving', 'Reducing monthly peak demand charges'),
        ('Curtailment Avoidance', 'Storing PV that would exceed grid limit'),
        ('Energy Arbitrage', 'Buying low / selling high on spot market'),
        ('Self-Consumption', 'Using stored PV instead of grid import')
    ]

    for category, description in categories:
        value = annual_values_dict.get(category, 0)
        percentage = (value / total_gross * 100) if total_gross > 0 else 0

        print(f"{category:<40s} {value:>12,.0f}   {percentage:>8.1f}%")
        print(f"  → {description}")
        print()

    print("="*80)

    # Insights
    print("\nKEY INSIGHTS")
    print("-"*80)

    # Find dominant value source
    values_only = {k: v for k, v in annual_values_dict.items()
                   if k not in ['Degradation Cost', 'Total Net Value']}
    dominant = max(values_only, key=values_only.get)
    dominant_pct = (values_only[dominant] / total_gross * 100)

    print(f"• Primary value driver: {dominant} ({dominant_pct:.0f}% of total)")

    # Check if battery is economic
    if total_net > 0:
        print(f"• Battery generates positive net value: {total_net:,.0f} kr/year")
    else:
        print(f"• Battery is not economic at current costs (net: {total_net:,.0f} kr/year)")

    # Improvement suggestions
    print("\nOPTIMIZATION OPPORTUNITIES")
    print("-"*80)

    if annual_values_dict.get('Curtailment Avoidance', 0) > 5000:
        print("• High curtailment value → Consider increasing battery power rating")

    if annual_values_dict.get('Energy Arbitrage', 0) < 5000:
        print("• Low arbitrage value → Check if spot price volatility justifies larger capacity")

    if annual_values_dict.get('Peak Shaving', 0) > 15000:
        print("• Significant peak shaving → Battery well-suited for power tariff reduction")

    print("\n" + "="*80)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("DUAL VARIABLE ATTRIBUTION - INTEGRATION EXAMPLES")
    print("="*80)
    print("\nThis script demonstrates how to integrate dual variable attribution")
    print("with your existing WeeklyOptimizer and economic analysis.")
    print("\nUncomment and modify code sections to use with real data.")
    print("="*80)

    # Run examples
    demonstrate_weekly_attribution()
    demonstrate_annual_attribution()
    demonstrate_validation()

    # Example stakeholder report (with dummy data)
    example_annual_values = {
        'Peak Shaving': 18500,
        'Curtailment Avoidance': 6200,
        'Energy Arbitrage': 4800,
        'Self-Consumption': 11500,
        'Degradation Cost': -3100,
        'Total Net Value': 37900
    }

    generate_stakeholder_report(example_annual_values)

    print("\n" + "="*80)
    print("Next Steps:")
    print("="*80)
    print("1. Modify WeeklyOptimizer to save 'prob' object after solving")
    print("2. Extract duals using extract_duals_from_weekly_optimizer()")
    print("3. Attribute value for each week using DualValueAttributor")
    print("4. Aggregate 52 weeks to annual totals")
    print("5. Compare with manual allocation method for validation")
    print("6. Generate stakeholder report with insights")
    print("="*80 + "\n")
