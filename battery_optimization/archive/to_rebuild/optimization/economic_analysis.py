"""
Economic analysis functions for battery investment
"""
import numpy as np
from typing import Dict, List, Tuple


def calculate_npv(
    cash_flows: List[float],
    discount_rate: float = 0.05
) -> float:
    """
    Calculate Net Present Value

    Args:
        cash_flows: List of annual cash flows (year 0 is initial investment)
        discount_rate: Annual discount rate

    Returns:
        NPV value
    """
    npv = 0
    for year, cash_flow in enumerate(cash_flows):
        npv += cash_flow / ((1 + discount_rate) ** year)
    return npv


def calculate_irr(
    cash_flows: List[float],
    max_iterations: int = 100,
    tolerance: float = 1e-6
) -> float:
    """
    Calculate Internal Rate of Return using Newton's method

    Args:
        cash_flows: List of annual cash flows
        max_iterations: Maximum iterations for convergence
        tolerance: Convergence tolerance

    Returns:
        IRR as decimal (0.10 = 10%)
    """
    # Initial guess
    rate = 0.1

    for _ in range(max_iterations):
        # Calculate NPV and its derivative
        npv = 0
        npv_derivative = 0

        for year, cash_flow in enumerate(cash_flows):
            discount_factor = (1 + rate) ** year
            npv += cash_flow / discount_factor
            if year > 0:
                npv_derivative -= year * cash_flow / ((1 + rate) ** (year + 1))

        # Check convergence
        if abs(npv) < tolerance:
            return rate

        # Newton's method update
        if npv_derivative != 0:
            rate = rate - npv / npv_derivative
            # Bound the rate
            rate = max(-0.99, min(rate, 10))

    return None  # Failed to converge


def calculate_payback_period(
    initial_investment: float,
    annual_savings: float,
    degradation_rate: float = 0.02
) -> float:
    """
    Calculate simple payback period considering degradation

    Args:
        initial_investment: Initial battery cost
        annual_savings: First year savings
        degradation_rate: Annual degradation rate

    Returns:
        Payback period in years
    """
    if annual_savings <= 0:
        return float('inf')

    cumulative_savings = 0
    year = 0

    while cumulative_savings < initial_investment and year < 50:
        year += 1
        yearly_savings = annual_savings * ((1 - degradation_rate) ** year)
        cumulative_savings += yearly_savings

    if cumulative_savings >= initial_investment:
        return year
    else:
        return float('inf')


def analyze_battery_economics(
    battery_capacity_kwh: float,
    battery_cost_per_kwh: float,
    annual_value: float,
    project_years: int = 15,
    discount_rate: float = 0.05,
    degradation_rate: float = 0.02
) -> Dict[str, float]:
    """
    Complete economic analysis for battery investment

    Args:
        battery_capacity_kwh: Battery size
        battery_cost_per_kwh: Cost per kWh
        annual_value: Total annual savings/revenue
        project_years: Project lifetime
        discount_rate: Discount rate
        degradation_rate: Annual degradation

    Returns:
        Dictionary with economic metrics
    """
    initial_investment = battery_capacity_kwh * battery_cost_per_kwh

    # Generate cash flows
    cash_flows = [-initial_investment]  # Year 0

    for year in range(1, project_years + 1):
        # Account for degradation
        yearly_value = annual_value * ((1 - degradation_rate) ** year)
        cash_flows.append(yearly_value)

    # Calculate metrics
    npv = calculate_npv(cash_flows, discount_rate)
    irr = calculate_irr(cash_flows)
    payback = calculate_payback_period(initial_investment, annual_value, degradation_rate)

    # Calculate LCOE (Levelized Cost of Energy)
    total_discounted_cost = initial_investment
    total_discounted_energy = 0

    for year in range(1, project_years + 1):
        discount_factor = (1 + discount_rate) ** year
        energy_throughput = battery_capacity_kwh * 365 * 0.8 * ((1 - degradation_rate) ** year)
        total_discounted_energy += energy_throughput / discount_factor

    lcoe = total_discounted_cost / total_discounted_energy if total_discounted_energy > 0 else float('inf')

    return {
        'initial_investment': initial_investment,
        'npv': npv,
        'irr': irr,
        'payback_years': payback,
        'lcoe_nok_per_kwh': lcoe,
        'profitable': npv > 0
    }


def sensitivity_analysis(
    base_capacity_kwh: float,
    base_annual_value: float,
    cost_range: Tuple[float, float] = (2000, 5000),
    cost_steps: int = 10
) -> List[Dict[str, float]]:
    """
    Perform sensitivity analysis on battery cost

    Args:
        base_capacity_kwh: Battery capacity
        base_annual_value: Annual value
        cost_range: Min and max battery cost per kWh
        cost_steps: Number of cost points to analyze

    Returns:
        List of economic results for each cost point
    """
    results = []
    costs = np.linspace(cost_range[0], cost_range[1], cost_steps)

    for cost in costs:
        economics = analyze_battery_economics(
            base_capacity_kwh,
            cost,
            base_annual_value
        )
        economics['cost_per_kwh'] = cost
        results.append(economics)

    return results


def find_break_even_cost(
    battery_capacity_kwh: float,
    annual_value: float,
    search_range: Tuple[float, float] = (1000, 10000),
    tolerance: float = 10
) -> float:
    """
    Find break-even battery cost where NPV = 0

    Args:
        battery_capacity_kwh: Battery capacity
        annual_value: Annual value
        search_range: Search range for cost
        tolerance: Search tolerance in NOK/kWh

    Returns:
        Break-even cost per kWh
    """
    low, high = search_range

    while high - low > tolerance:
        mid = (low + high) / 2
        economics = analyze_battery_economics(
            battery_capacity_kwh,
            mid,
            annual_value
        )

        if economics['npv'] > 0:
            low = mid  # Can afford higher cost
        else:
            high = mid  # Need lower cost

    return (low + high) / 2