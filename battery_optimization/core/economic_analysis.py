"""
Economic analysis functions for battery optimization.

Provides break-even cost calculations and NPV analysis for battery investments.

REFACTORED: Now uses configuration dataclasses for economic assumptions.
All parameters can be overridden via function arguments for flexibility.
"""

import numpy as np
from typing import Dict, Optional
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_path = Path(__file__).parent.parent
if str(parent_path) not in sys.path:
    sys.path.insert(0, str(parent_path))

from src.config.simulation_config import EconomicConfig, BatteryEconomicsConfig

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION HELPERS
# =============================================================================

def _get_default_economic_config() -> EconomicConfig:
    """Get default economic configuration."""
    return EconomicConfig()


def _get_default_battery_economics_config() -> BatteryEconomicsConfig:
    """Get default battery economics configuration."""
    return BatteryEconomicsConfig()


# =============================================================================
# ECONOMIC ANALYSIS FUNCTIONS
# =============================================================================

def calculate_breakeven_cost(
    annual_savings: float,
    battery_kwh: float,
    battery_kw: float,
    discount_rate: Optional[float] = None,
    lifetime_years: Optional[int] = None,
    degradation_rate: Optional[float] = None,
    installation_markup: Optional[float] = None,
    economic_config: Optional[EconomicConfig] = None,
    battery_economics: Optional[BatteryEconomicsConfig] = None,
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
        discount_rate: Annual discount rate (overrides config if provided)
        lifetime_years: Battery lifetime (overrides config if provided)
        degradation_rate: Annual capacity degradation (overrides config if provided)
        installation_markup: Installation and BOS costs fraction (overrides config if provided)
        economic_config: Economic configuration (uses defaults if None)
        battery_economics: Battery economics configuration (uses defaults if None)

    Returns:
        Break-even battery cost [NOK/kWh]

    Example:
        >>> calculate_breakeven_cost(
        ...     annual_savings=5000,  # 5000 kr/year savings
        ...     battery_kwh=30,       # 30 kWh battery
        ...     battery_kw=15,        # 15 kW power
        ... )
        4982.5  # Max cost ~5000 NOK/kWh for break-even
    """
    # Get configurations with defaults
    if economic_config is None:
        economic_config = _get_default_economic_config()
    if battery_economics is None:
        battery_economics = _get_default_battery_economics_config()

    # Use provided parameters or fall back to config
    discount_rate = discount_rate if discount_rate is not None else economic_config.discount_rate
    lifetime_years = lifetime_years if lifetime_years is not None else economic_config.project_years
    degradation_rate = degradation_rate if degradation_rate is not None else battery_economics.degradation.annual_rate
    installation_markup = installation_markup if installation_markup is not None else battery_economics.installation_markup
    capacity_floor = battery_economics.degradation.capacity_floor

    # Calculate present value of annual savings over lifetime
    # Account for degradation: savings decrease over time
    pv_savings = 0.0

    for year in range(1, lifetime_years + 1):
        # Degradation factor: battery capacity decreases linearly
        degradation_factor = 1.0 - (degradation_rate * (year - 1))
        degradation_factor = max(capacity_floor, degradation_factor)  # NOW CONFIGURABLE!

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
    discount_rate: Optional[float] = None,
    lifetime_years: Optional[int] = None,
    degradation_rate: Optional[float] = None,
    installation_markup: Optional[float] = None,
    economic_config: Optional[EconomicConfig] = None,
    battery_economics: Optional[BatteryEconomicsConfig] = None,
) -> float:
    """
    Calculate Net Present Value (NPV) of battery investment.

    NPV = PV(savings) - Investment

    Args:
        annual_savings: Annual cost savings [NOK/year]
        battery_kwh: Battery capacity [kWh]
        battery_cost_per_kwh: Battery cost [NOK/kWh]
        discount_rate: Annual discount rate (overrides config if provided)
        lifetime_years: Battery lifetime (overrides config if provided)
        degradation_rate: Annual degradation (overrides config if provided)
        installation_markup: Installation markup (overrides config if provided)
        economic_config: Economic configuration (uses defaults if None)
        battery_economics: Battery economics configuration (uses defaults if None)

    Returns:
        NPV [NOK]
    """
    # Get configurations with defaults
    if economic_config is None:
        economic_config = _get_default_economic_config()
    if battery_economics is None:
        battery_economics = _get_default_battery_economics_config()

    # Use provided parameters or fall back to config
    discount_rate = discount_rate if discount_rate is not None else economic_config.discount_rate
    lifetime_years = lifetime_years if lifetime_years is not None else economic_config.project_years
    degradation_rate = degradation_rate if degradation_rate is not None else battery_economics.degradation.annual_rate
    installation_markup = installation_markup if installation_markup is not None else battery_economics.installation_markup
    capacity_floor = battery_economics.degradation.capacity_floor

    # Calculate PV of savings
    pv_savings = 0.0
    for year in range(1, lifetime_years + 1):
        degradation_factor = 1.0 - (degradation_rate * (year - 1))
        degradation_factor = max(capacity_floor, degradation_factor)

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
    lifetime_years: Optional[int] = None,
    degradation_rate: Optional[float] = None,
    installation_markup: Optional[float] = None,
    economic_config: Optional[EconomicConfig] = None,
    battery_economics: Optional[BatteryEconomicsConfig] = None,
    tolerance: float = 0.0001,
    max_iterations: int = 100,
) -> Optional[float]:
    """
    Calculate Internal Rate of Return (IRR).

    IRR is the discount rate at which NPV = 0.

    Uses Newton-Raphson method to find IRR.

    Args:
        annual_savings: Annual savings [NOK/year]
        battery_kwh: Battery capacity [kWh]
        battery_cost_per_kwh: Battery cost [NOK/kWh]
        lifetime_years: Lifetime (overrides config if provided)
        degradation_rate: Annual degradation (overrides config if provided)
        installation_markup: Installation markup (overrides config if provided)
        economic_config: Economic configuration (uses defaults if None)
        battery_economics: Battery economics configuration (uses defaults if None)
        tolerance: Convergence tolerance (default: 0.01%)
        max_iterations: Max iterations (default: 100)

    Returns:
        IRR as decimal (e.g., 0.15 = 15%), or None if no solution found
    """
    # Get configurations with defaults
    if economic_config is None:
        economic_config = _get_default_economic_config()
    if battery_economics is None:
        battery_economics = _get_default_battery_economics_config()

    # Use provided parameters or fall back to config
    lifetime_years = lifetime_years if lifetime_years is not None else economic_config.project_years
    degradation_rate = degradation_rate if degradation_rate is not None else battery_economics.degradation.annual_rate
    installation_markup = installation_markup if installation_markup is not None else battery_economics.installation_markup
    capacity_floor = battery_economics.degradation.capacity_floor

    investment = battery_cost_per_kwh * battery_kwh * (1 + installation_markup)

    # Initial guess: 10%
    irr = 0.10

    for iteration in range(max_iterations):
        # Calculate NPV at current IRR
        npv = -investment
        for year in range(1, lifetime_years + 1):
            degradation_factor = 1.0 - (degradation_rate * (year - 1))
            degradation_factor = max(capacity_floor, degradation_factor)

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
            degradation_factor = max(capacity_floor, degradation_factor)

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
    degradation_rate: Optional[float] = None,
    installation_markup: Optional[float] = None,
    battery_economics: Optional[BatteryEconomicsConfig] = None,
) -> float:
    """
    Calculate simple payback period (years).

    Payback period is when cumulative savings = investment.
    Does not account for time value of money (discount rate).

    Args:
        annual_savings: Annual savings [NOK/year]
        battery_kwh: Battery capacity [kWh]
        battery_cost_per_kwh: Battery cost [NOK/kWh]
        degradation_rate: Annual degradation (overrides config if provided)
        installation_markup: Installation markup (overrides config if provided)
        battery_economics: Battery economics configuration (uses defaults if None)

    Returns:
        Payback period [years], or np.inf if never pays back
    """
    # Get configuration with defaults
    if battery_economics is None:
        battery_economics = _get_default_battery_economics_config()

    # Use provided parameters or fall back to config
    degradation_rate = degradation_rate if degradation_rate is not None else battery_economics.degradation.annual_rate
    installation_markup = installation_markup if installation_markup is not None else battery_economics.installation_markup
    capacity_floor = battery_economics.degradation.capacity_floor

    investment = battery_cost_per_kwh * battery_kwh * (1 + installation_markup)

    cumulative_savings = 0.0

    for year in range(1, 51):  # Max 50 years
        degradation_factor = 1.0 - (degradation_rate * (year - 1))
        degradation_factor = max(capacity_floor, degradation_factor)

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
    discount_rate: Optional[float] = None,
    lifetime_years: Optional[int] = None,
    degradation_rate: Optional[float] = None,
    installation_markup: Optional[float] = None,
    economic_config: Optional[EconomicConfig] = None,
    battery_economics: Optional[BatteryEconomicsConfig] = None,
) -> Dict[str, float]:
    """
    Comprehensive economic analysis of battery investment.

    Args:
        annual_savings: Annual cost savings [NOK/year]
        battery_kwh: Battery capacity [kWh]
        battery_kw: Battery power [kW]
        battery_cost_per_kwh: Battery cost [NOK/kWh]
        discount_rate: Discount rate (overrides config if provided)
        lifetime_years: Lifetime (overrides config if provided)
        degradation_rate: Degradation (overrides config if provided)
        installation_markup: Installation markup (overrides config if provided)
        economic_config: Economic configuration (uses defaults if None)
        battery_economics: Battery economics configuration (uses defaults if None)

    Returns:
        Dictionary with economic metrics:
        - npv: Net Present Value [NOK]
        - irr: Internal Rate of Return [decimal]
        - payback_period: Simple payback [years]
        - breakeven_cost: Break-even battery cost [NOK/kWh]
        - total_investment: Total upfront investment [NOK]
        - pv_savings: Present value of all savings [NOK]
    """
    # Get configurations with defaults
    if economic_config is None:
        economic_config = _get_default_economic_config()
    if battery_economics is None:
        battery_economics = _get_default_battery_economics_config()

    # Use provided parameters or fall back to config
    discount_rate_val = discount_rate if discount_rate is not None else economic_config.discount_rate
    lifetime_years_val = lifetime_years if lifetime_years is not None else economic_config.project_years
    degradation_rate_val = degradation_rate if degradation_rate is not None else battery_economics.degradation.annual_rate
    installation_markup_val = installation_markup if installation_markup is not None else battery_economics.installation_markup
    capacity_floor = battery_economics.degradation.capacity_floor

    # Pass config objects to all sub-functions for consistency
    npv = calculate_npv(
        annual_savings, battery_kwh, battery_cost_per_kwh,
        discount_rate, lifetime_years, degradation_rate, installation_markup,
        economic_config, battery_economics
    )

    irr = calculate_irr(
        annual_savings, battery_kwh, battery_cost_per_kwh,
        lifetime_years, degradation_rate, installation_markup,
        economic_config, battery_economics
    )

    payback = calculate_payback_period(
        annual_savings, battery_kwh, battery_cost_per_kwh,
        degradation_rate, installation_markup,
        battery_economics
    )

    breakeven = calculate_breakeven_cost(
        annual_savings, battery_kwh, battery_kw,
        discount_rate, lifetime_years, degradation_rate, installation_markup,
        economic_config, battery_economics
    )

    investment = battery_cost_per_kwh * battery_kwh * (1 + installation_markup_val)

    # PV of savings
    pv_savings = 0.0
    for year in range(1, lifetime_years_val + 1):
        degradation_factor = 1.0 - (degradation_rate_val * (year - 1))
        degradation_factor = max(capacity_floor, degradation_factor)
        year_savings = annual_savings * degradation_factor
        discount_factor = 1.0 / ((1.0 + discount_rate_val) ** year)
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
