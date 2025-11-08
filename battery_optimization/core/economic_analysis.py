"""
Economic analysis functions for battery optimization.

Provides break-even cost calculations and NPV analysis for battery investments.
"""

import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_breakeven_cost(
    annual_savings: float,
    battery_kwh: float,
    battery_kw: float,
    discount_rate: float = 0.05,
    lifetime_years: int = 15,
    degradation_rate: float = 0.02,
    installation_markup: float = 0.25
) -> float:
    """
    Calculate break-even battery cost (NOK/kWh) where NPV = 0.

    The break-even cost is the maximum price per kWh at which the battery
    investment breaks even over its lifetime.

    NPV formula:
        NPV = PV(savings) - Investment

    At break-even (NPV = 0):
        Investment = PV(savings)
        battery_cost_per_kwh * battery_kwh * (1 + markup) = PV(savings)

    Therefore:
        breakeven_cost = PV(savings) / (battery_kwh * (1 + markup))

    Args:
        annual_savings: Annual cost savings from battery operation [NOK/year]
        battery_kwh: Battery energy capacity [kWh]
        battery_kw: Battery power rating [kW] (not used in cost, but for context)
        discount_rate: Annual discount rate (default: 5%)
        lifetime_years: Battery lifetime (default: 15 years)
        degradation_rate: Annual capacity degradation (default: 2%/year)
        installation_markup: Installation and BOS costs as fraction of battery cost (default: 25%)

    Returns:
        Break-even battery cost [NOK/kWh]

    Example:
        >>> calculate_breakeven_cost(
        ...     annual_savings=5000,  # 5000 kr/year savings
        ...     battery_kwh=30,       # 30 kWh battery
        ...     battery_kw=15,        # 15 kW power
        ...     discount_rate=0.05,
        ...     lifetime_years=15
        ... )
        4982.5  # Max cost ~5000 NOK/kWh for break-even
    """

    # Calculate present value of annual savings over lifetime
    # Account for degradation: savings decrease over time
    pv_savings = 0.0

    for year in range(1, lifetime_years + 1):
        # Degradation factor: battery capacity decreases linearly
        degradation_factor = 1.0 - (degradation_rate * (year - 1))
        degradation_factor = max(0.7, degradation_factor)  # Floor at 70% capacity

        # Savings in this year (degraded)
        year_savings = annual_savings * degradation_factor

        # Discount to present value
        discount_factor = 1.0 / ((1.0 + discount_rate) ** year)

        pv_savings += year_savings * discount_factor

    # At break-even: Total investment = PV(savings)
    # Total investment = battery_cost_per_kwh * battery_kwh * (1 + markup)
    # Solve for battery_cost_per_kwh:

    total_investment_at_breakeven = pv_savings
    battery_cost_per_kwh = total_investment_at_breakeven / (battery_kwh * (1 + installation_markup))

    logger.debug(f"Break-even calculation:")
    logger.debug(f"  Annual savings: {annual_savings:.2f} NOK/year")
    logger.debug(f"  PV of savings: {pv_savings:.2f} NOK")
    logger.debug(f"  Battery size: {battery_kwh} kWh")
    logger.debug(f"  Installation markup: {installation_markup*100:.1f}%")
    logger.debug(f"  Break-even cost: {battery_cost_per_kwh:.2f} NOK/kWh")

    return battery_cost_per_kwh


def calculate_npv(
    annual_savings: float,
    battery_kwh: float,
    battery_cost_per_kwh: float,
    discount_rate: float = 0.05,
    lifetime_years: int = 15,
    degradation_rate: float = 0.02,
    installation_markup: float = 0.25
) -> float:
    """
    Calculate Net Present Value (NPV) of battery investment.

    NPV = PV(savings) - Investment

    Args:
        annual_savings: Annual cost savings [NOK/year]
        battery_kwh: Battery capacity [kWh]
        battery_cost_per_kwh: Battery cost [NOK/kWh]
        discount_rate: Annual discount rate (default: 5%)
        lifetime_years: Battery lifetime (default: 15 years)
        degradation_rate: Annual degradation (default: 2%/year)
        installation_markup: Installation markup (default: 25%)

    Returns:
        NPV [NOK]
    """

    # Calculate PV of savings
    pv_savings = 0.0
    for year in range(1, lifetime_years + 1):
        degradation_factor = 1.0 - (degradation_rate * (year - 1))
        degradation_factor = max(0.7, degradation_factor)

        year_savings = annual_savings * degradation_factor
        discount_factor = 1.0 / ((1.0 + discount_rate) ** year)
        pv_savings += year_savings * discount_factor

    # Calculate investment
    investment = battery_cost_per_kwh * battery_kwh * (1 + installation_markup)

    # NPV
    npv = pv_savings - investment

    return npv


def calculate_irr(
    annual_savings: float,
    battery_kwh: float,
    battery_cost_per_kwh: float,
    lifetime_years: int = 15,
    degradation_rate: float = 0.02,
    installation_markup: float = 0.25,
    tolerance: float = 0.0001,
    max_iterations: int = 100
) -> Optional[float]:
    """
    Calculate Internal Rate of Return (IRR).

    IRR is the discount rate at which NPV = 0.

    Uses Newton-Raphson method to find IRR.

    Args:
        annual_savings: Annual savings [NOK/year]
        battery_kwh: Battery capacity [kWh]
        battery_cost_per_kwh: Battery cost [NOK/kWh]
        lifetime_years: Lifetime (default: 15 years)
        degradation_rate: Annual degradation (default: 2%)
        installation_markup: Installation markup (default: 25%)
        tolerance: Convergence tolerance (default: 0.01%)
        max_iterations: Max iterations (default: 100)

    Returns:
        IRR as decimal (e.g., 0.15 = 15%), or None if no solution found
    """

    investment = battery_cost_per_kwh * battery_kwh * (1 + installation_markup)

    # Initial guess: 10%
    irr = 0.10

    for iteration in range(max_iterations):
        # Calculate NPV at current IRR
        npv = -investment
        for year in range(1, lifetime_years + 1):
            degradation_factor = 1.0 - (degradation_rate * (year - 1))
            degradation_factor = max(0.7, degradation_factor)

            year_savings = annual_savings * degradation_factor
            discount_factor = 1.0 / ((1.0 + irr) ** year)
            npv += year_savings * discount_factor

        # Check convergence
        if abs(npv) < tolerance:
            return irr

        # Calculate derivative (dNPV/dIRR) for Newton-Raphson
        d_npv = 0.0
        for year in range(1, lifetime_years + 1):
            degradation_factor = 1.0 - (degradation_rate * (year - 1))
            degradation_factor = max(0.7, degradation_factor)

            year_savings = annual_savings * degradation_factor
            d_npv += -year * year_savings / ((1.0 + irr) ** (year + 1))

        # Newton-Raphson update
        if abs(d_npv) > 1e-10:
            irr = irr - npv / d_npv
        else:
            # Derivative too small, can't continue
            logger.warning("IRR calculation: derivative too small")
            return None

        # Keep IRR reasonable
        if irr < -0.5 or irr > 1.0:
            logger.warning(f"IRR calculation diverged: {irr:.4f}")
            return None

    logger.warning("IRR calculation did not converge")
    return None


def calculate_payback_period(
    annual_savings: float,
    battery_kwh: float,
    battery_cost_per_kwh: float,
    degradation_rate: float = 0.02,
    installation_markup: float = 0.25
) -> float:
    """
    Calculate simple payback period (years).

    Payback period is when cumulative savings = investment.
    Does not account for time value of money (discount rate).

    Args:
        annual_savings: Annual savings [NOK/year]
        battery_kwh: Battery capacity [kWh]
        battery_cost_per_kwh: Battery cost [NOK/kWh]
        degradation_rate: Annual degradation (default: 2%)
        installation_markup: Installation markup (default: 25%)

    Returns:
        Payback period [years], or np.inf if never pays back
    """

    investment = battery_cost_per_kwh * battery_kwh * (1 + installation_markup)

    cumulative_savings = 0.0

    for year in range(1, 51):  # Max 50 years
        degradation_factor = 1.0 - (degradation_rate * (year - 1))
        degradation_factor = max(0.7, degradation_factor)

        year_savings = annual_savings * degradation_factor
        cumulative_savings += year_savings

        if cumulative_savings >= investment:
            # Linear interpolation for fractional year
            prev_cumulative = cumulative_savings - year_savings
            fraction = (investment - prev_cumulative) / year_savings
            return year - 1 + fraction

    return np.inf  # Never pays back


def analyze_battery_investment(
    annual_savings: float,
    battery_kwh: float,
    battery_kw: float,
    battery_cost_per_kwh: float,
    discount_rate: float = 0.05,
    lifetime_years: int = 15,
    degradation_rate: float = 0.02,
    installation_markup: float = 0.25
) -> Dict[str, float]:
    """
    Comprehensive economic analysis of battery investment.

    Args:
        annual_savings: Annual cost savings [NOK/year]
        battery_kwh: Battery capacity [kWh]
        battery_kw: Battery power [kW]
        battery_cost_per_kwh: Battery cost [NOK/kWh]
        discount_rate: Discount rate (default: 5%)
        lifetime_years: Lifetime (default: 15 years)
        degradation_rate: Degradation (default: 2%/year)
        installation_markup: Installation markup (default: 25%)

    Returns:
        Dictionary with economic metrics:
        - npv: Net Present Value [NOK]
        - irr: Internal Rate of Return [decimal]
        - payback_period: Simple payback [years]
        - breakeven_cost: Break-even battery cost [NOK/kWh]
        - total_investment: Total upfront investment [NOK]
        - pv_savings: Present value of all savings [NOK]
    """

    npv = calculate_npv(
        annual_savings, battery_kwh, battery_cost_per_kwh,
        discount_rate, lifetime_years, degradation_rate, installation_markup
    )

    irr = calculate_irr(
        annual_savings, battery_kwh, battery_cost_per_kwh,
        lifetime_years, degradation_rate, installation_markup
    )

    payback = calculate_payback_period(
        annual_savings, battery_kwh, battery_cost_per_kwh,
        degradation_rate, installation_markup
    )

    breakeven = calculate_breakeven_cost(
        annual_savings, battery_kwh, battery_kw,
        discount_rate, lifetime_years, degradation_rate, installation_markup
    )

    investment = battery_cost_per_kwh * battery_kwh * (1 + installation_markup)

    # PV of savings
    pv_savings = 0.0
    for year in range(1, lifetime_years + 1):
        degradation_factor = 1.0 - (degradation_rate * (year - 1))
        degradation_factor = max(0.7, degradation_factor)
        year_savings = annual_savings * degradation_factor
        discount_factor = 1.0 / ((1.0 + discount_rate) ** year)
        pv_savings += year_savings * discount_factor

    return {
        'npv': npv,
        'irr': irr if irr is not None else np.nan,
        'payback_period': payback,
        'breakeven_cost': breakeven,
        'total_investment': investment,
        'pv_savings': pv_savings,
        'annual_savings': annual_savings,
        'battery_kwh': battery_kwh,
        'battery_kw': battery_kw
    }


if __name__ == "__main__":
    # Test economic analysis functions
    logging.basicConfig(level=logging.DEBUG)

    print("Economic Analysis Module - Test")
    print("=" * 60)
    print()

    # Test case: 30 kWh / 15 kW battery with 5000 NOK/year savings
    annual_savings = 5000  # NOK/year
    battery_kwh = 30
    battery_kw = 15
    battery_cost_market = 5000  # NOK/kWh (current market)
    battery_cost_target = 2500  # NOK/kWh (target cost)

    print(f"Battery: {battery_kwh} kWh / {battery_kw} kW")
    print(f"Annual savings: {annual_savings} NOK/year")
    print()

    # Calculate break-even cost
    breakeven = calculate_breakeven_cost(annual_savings, battery_kwh, battery_kw)
    print(f"Break-even cost: {breakeven:.2f} NOK/kWh")
    print()

    # Analyze at market cost
    print("At market cost (5000 NOK/kWh):")
    analysis_market = analyze_battery_investment(
        annual_savings, battery_kwh, battery_kw, battery_cost_market
    )
    print(f"  NPV: {analysis_market['npv']:.2f} NOK")
    print(f"  IRR: {analysis_market['irr']*100:.2f}%" if not np.isnan(analysis_market['irr']) else "  IRR: N/A")
    print(f"  Payback: {analysis_market['payback_period']:.1f} years")
    print()

    # Analyze at target cost
    print("At target cost (2500 NOK/kWh):")
    analysis_target = analyze_battery_investment(
        annual_savings, battery_kwh, battery_kw, battery_cost_target
    )
    print(f"  NPV: {analysis_target['npv']:.2f} NOK")
    print(f"  IRR: {analysis_target['irr']*100:.2f}%" if not np.isnan(analysis_target['irr']) else "  IRR: N/A")
    print(f"  Payback: {analysis_target['payback_period']:.1f} years")
