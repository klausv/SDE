"""
Utility functions for energy system calculations
"""
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
import pandas as pd

from domain.value_objects.energy import Energy, Power
from domain.value_objects.money import Money


def calculate_npv(
    cash_flows: List[float],
    discount_rate: float,
    periods: Optional[List[int]] = None
) -> float:
    """
    Calculate Net Present Value

    Args:
        cash_flows: List of cash flows
        discount_rate: Discount rate (e.g., 0.05 for 5%)
        periods: Optional list of period indices (default: 0, 1, 2, ...)

    Returns:
        NPV value
    """
    if periods is None:
        periods = list(range(len(cash_flows)))

    npv = 0.0
    for cash_flow, period in zip(cash_flows, periods):
        discount_factor = (1 + discount_rate) ** period
        npv += cash_flow / discount_factor

    return npv


def calculate_irr(cash_flows: List[float], tolerance: float = 1e-6) -> Optional[float]:
    """
    Calculate Internal Rate of Return

    Args:
        cash_flows: List of cash flows (first should be negative investment)
        tolerance: Convergence tolerance

    Returns:
        IRR as decimal (0.15 = 15%), or None if no solution
    """
    # Newton's method for IRR
    rate = 0.1  # Initial guess
    max_iterations = 100

    for _ in range(max_iterations):
        # Calculate NPV and its derivative
        npv = 0
        dnpv = 0

        for i, cf in enumerate(cash_flows):
            discount_factor = (1 + rate) ** i
            npv += cf / discount_factor

            if i > 0:
                dnpv -= i * cf / ((1 + rate) ** (i + 1))

        # Check convergence
        if abs(npv) < tolerance:
            return rate

        # Newton's method update
        if dnpv != 0:
            rate = rate - npv / dnpv

            # Bound the rate to reasonable values
            rate = max(-0.99, min(rate, 10.0))

    return None  # Failed to converge


def calculate_payback_period(
    cash_flows: List[float],
    interpolate: bool = True
) -> Optional[float]:
    """
    Calculate simple payback period

    Args:
        cash_flows: List of cash flows (first negative, rest positive)
        interpolate: Whether to interpolate for fractional years

    Returns:
        Payback period in years, or None if never pays back
    """
    if not cash_flows or cash_flows[0] >= 0:
        return None

    initial_investment = abs(cash_flows[0])
    cumulative = 0.0

    for i, cf in enumerate(cash_flows[1:], 1):
        cumulative += cf

        if cumulative >= initial_investment:
            if interpolate and i > 1:
                # Linear interpolation for partial year
                previous_cumulative = cumulative - cf
                fraction = (initial_investment - previous_cumulative) / cf
                return i - 1 + fraction
            else:
                return float(i)

    return None  # Never pays back


def calculate_lcoe(
    total_cost: float,
    total_energy_produced: float,
    project_lifetime_years: int,
    discount_rate: float = 0.05,
    annual_costs: Optional[List[float]] = None,
    annual_production: Optional[List[float]] = None
) -> float:
    """
    Calculate Levelized Cost of Energy

    Args:
        total_cost: Total investment cost
        total_energy_produced: Total energy over lifetime (kWh)
        project_lifetime_years: Project lifetime
        discount_rate: Discount rate
        annual_costs: Optional list of annual O&M costs
        annual_production: Optional list of annual production

    Returns:
        LCOE in currency/kWh
    """
    if annual_costs and annual_production:
        # Detailed LCOE calculation
        total_discounted_cost = total_cost  # Initial investment
        total_discounted_energy = 0

        for year in range(1, project_lifetime_years + 1):
            discount_factor = (1 + discount_rate) ** year

            # Annual costs
            if year <= len(annual_costs):
                total_discounted_cost += annual_costs[year - 1] / discount_factor

            # Annual production
            if year <= len(annual_production):
                total_discounted_energy += annual_production[year - 1] / discount_factor

        lcoe = total_discounted_cost / total_discounted_energy if total_discounted_energy > 0 else float('inf')
    else:
        # Simple LCOE
        lcoe = total_cost / total_energy_produced if total_energy_produced > 0 else float('inf')

    return lcoe


def calculate_capacity_factor(
    actual_production: float,
    rated_capacity: float,
    hours: int = 8760
) -> float:
    """
    Calculate capacity factor

    Args:
        actual_production: Actual energy produced (kWh)
        rated_capacity: Rated power capacity (kW)
        hours: Number of hours in period (default: 8760 for year)

    Returns:
        Capacity factor (0-1)
    """
    theoretical_max = rated_capacity * hours
    return actual_production / theoretical_max if theoretical_max > 0 else 0


def calculate_self_consumption_rate(
    pv_production: pd.Series,
    load: pd.Series,
    battery_discharge: Optional[pd.Series] = None
) -> float:
    """
    Calculate self-consumption rate of PV production

    Args:
        pv_production: PV production time series (kW)
        load: Load time series (kW)
        battery_discharge: Optional battery discharge series (kW)

    Returns:
        Self-consumption rate (0-1)
    """
    # Direct self-consumption (PV used directly)
    direct_consumption = pd.DataFrame({
        'pv': pv_production,
        'load': load
    }).min(axis=1).sum()

    # Add battery contribution if available
    if battery_discharge is not None:
        battery_consumption = battery_discharge.sum()
        total_self_consumption = direct_consumption + battery_consumption
    else:
        total_self_consumption = direct_consumption

    total_pv = pv_production.sum()
    return total_self_consumption / total_pv if total_pv > 0 else 0


def calculate_self_sufficiency_rate(
    load: pd.Series,
    pv_production: pd.Series,
    battery_discharge: Optional[pd.Series] = None
) -> float:
    """
    Calculate self-sufficiency rate (autarky)

    Args:
        load: Load time series (kW)
        pv_production: PV production time series (kW)
        battery_discharge: Optional battery discharge series (kW)

    Returns:
        Self-sufficiency rate (0-1)
    """
    # Energy supplied from PV
    pv_to_load = pd.DataFrame({
        'pv': pv_production,
        'load': load
    }).min(axis=1).sum()

    # Add battery contribution
    if battery_discharge is not None:
        total_self_supply = pv_to_load + battery_discharge.sum()
    else:
        total_self_supply = pv_to_load

    total_load = load.sum()
    return total_self_supply / total_load if total_load > 0 else 0


def calculate_peak_shaving_potential(
    load: pd.Series,
    battery_power: float,
    battery_capacity: float,
    strategy: str = 'threshold'
) -> Tuple[float, pd.Series]:
    """
    Calculate peak shaving potential with battery

    Args:
        load: Load time series (kW)
        battery_power: Battery power rating (kW)
        battery_capacity: Battery capacity (kWh)
        strategy: Peak shaving strategy ('threshold' or 'rolling_average')

    Returns:
        Tuple of (peak reduction %, modified load profile)
    """
    original_peak = load.max()
    modified_load = load.copy()

    if strategy == 'threshold':
        # Simple threshold-based peak shaving
        threshold = load.quantile(0.95)  # Shave top 5% of peaks
        battery_soc = battery_capacity * 0.5  # Start at 50% SOC

        for i, (timestamp, demand) in enumerate(load.items()):
            if demand > threshold and battery_soc > 0:
                # Discharge battery
                discharge = min(demand - threshold, battery_power, battery_soc)
                modified_load.iloc[i] = demand - discharge
                battery_soc -= discharge
            elif demand < threshold * 0.8 and battery_soc < battery_capacity:
                # Charge battery during low demand
                charge = min(battery_power, battery_capacity - battery_soc, threshold * 0.8 - demand)
                modified_load.iloc[i] = demand + charge
                battery_soc += charge

    elif strategy == 'rolling_average':
        # Rolling average based strategy
        window = 24  # 24-hour window
        rolling_avg = load.rolling(window=window, center=True).mean()

        battery_soc = battery_capacity * 0.5

        for i, (timestamp, demand) in enumerate(load.items()):
            avg_demand = rolling_avg.iloc[i] if not pd.isna(rolling_avg.iloc[i]) else demand

            if demand > avg_demand * 1.1 and battery_soc > 0:
                # Discharge when above average
                discharge = min(demand - avg_demand, battery_power, battery_soc)
                modified_load.iloc[i] = demand - discharge
                battery_soc -= discharge
            elif demand < avg_demand * 0.9 and battery_soc < battery_capacity:
                # Charge when below average
                charge = min(battery_power, battery_capacity - battery_soc)
                modified_load.iloc[i] = demand + charge
                battery_soc += charge

    new_peak = modified_load.max()
    peak_reduction = (original_peak - new_peak) / original_peak

    return peak_reduction, modified_load


def calculate_grid_independence_hours(
    load: pd.Series,
    pv_production: pd.Series,
    battery_capacity: float = 0
) -> int:
    """
    Calculate number of hours with grid independence

    Args:
        load: Load time series (kW)
        pv_production: PV production time series (kW)
        battery_capacity: Battery capacity (kWh)

    Returns:
        Number of hours without grid import
    """
    net_load = load - pv_production

    if battery_capacity > 0:
        # Simple battery simulation
        battery_soc = battery_capacity * 0.5
        grid_independent_hours = 0

        for net in net_load:
            if net <= 0:
                # Excess PV - charge battery if possible
                excess = -net
                charge = min(excess, battery_capacity - battery_soc)
                battery_soc += charge
                grid_independent_hours += 1
            elif battery_soc >= net:
                # Deficit but battery can supply
                battery_soc -= net
                grid_independent_hours += 1
            # else: Need grid import

        return grid_independent_hours
    else:
        # Without battery
        return (net_load <= 0).sum()


def calculate_emissions_reduction(
    grid_import_baseline: float,
    grid_import_with_system: float,
    grid_emission_factor: float = 0.5  # kg CO2/kWh
) -> Dict[str, float]:
    """
    Calculate CO2 emissions reduction

    Args:
        grid_import_baseline: Baseline grid import (kWh)
        grid_import_with_system: Grid import with PV/battery (kWh)
        grid_emission_factor: Grid emission factor (kg CO2/kWh)

    Returns:
        Dictionary with emissions metrics
    """
    emissions_baseline = grid_import_baseline * grid_emission_factor
    emissions_with_system = grid_import_with_system * grid_emission_factor
    emissions_avoided = emissions_baseline - emissions_with_system

    return {
        'emissions_baseline_kg': emissions_baseline,
        'emissions_with_system_kg': emissions_with_system,
        'emissions_avoided_kg': emissions_avoided,
        'emissions_reduction_percentage': (emissions_avoided / emissions_baseline * 100) if emissions_baseline > 0 else 0
    }