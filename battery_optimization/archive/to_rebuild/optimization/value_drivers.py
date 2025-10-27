"""
Calculate value drivers for battery storage
"""
import numpy as np
import pandas as pd
from typing import Dict, Any


def calculate_curtailment_value(
    production: pd.Series,
    grid_limit_kw: float = 77,
    feed_in_price: float = 0.45
) -> Dict[str, float]:
    """
    Calculate value from avoided curtailment

    Args:
        production: Hourly production series
        grid_limit_kw: Grid export limit
        feed_in_price: Net price for grid feed-in (NOK/kWh)

    Returns:
        Dictionary with curtailment metrics
    """
    curtailment = (production - grid_limit_kw).clip(lower=0)
    total_curtailment_kwh = curtailment.sum()
    hours_with_curtailment = (curtailment > 0).sum()
    curtailment_value = total_curtailment_kwh * feed_in_price

    return {
        'total_kwh': total_curtailment_kwh,
        'hours': hours_with_curtailment,
        'annual_value_nok': curtailment_value,
        'percentage_of_production': (total_curtailment_kwh / production.sum()) * 100
    }


def calculate_arbitrage_value(
    prices: pd.Series,
    battery_capacity_kwh: float = 50,
    battery_efficiency: float = 0.95,  # Moderne LFP batterier
    depth_of_discharge: float = 0.90  # Moderne batterier tillater høyere DoD
) -> Dict[str, float]:
    """
    Calculate value from energy arbitrage (buy low, sell high)

    Args:
        prices: Hourly electricity prices
        battery_capacity_kwh: Battery capacity
        battery_efficiency: Round-trip efficiency
        depth_of_discharge: Usable capacity fraction

    Returns:
        Dictionary with arbitrage metrics
    """
    # Find price thresholds
    low_price_threshold = prices.quantile(0.25)
    high_price_threshold = prices.quantile(0.75)

    # Calculate average prices in each period
    low_price_avg = prices[prices < low_price_threshold].mean()
    high_price_avg = prices[prices > high_price_threshold].mean()
    price_spread = high_price_avg - low_price_avg

    # Assume daily cycling
    daily_energy = battery_capacity_kwh * depth_of_discharge
    annual_energy = daily_energy * 365

    # Account for efficiency losses
    arbitrage_value = annual_energy * price_spread * battery_efficiency

    return {
        'low_price_avg': low_price_avg,
        'high_price_avg': high_price_avg,
        'price_spread': price_spread,
        'annual_cycles': 365,
        'annual_value_nok': arbitrage_value
    }


def calculate_demand_charge_savings(
    consumption: pd.Series,
    peak_reduction_kw: float = None,
    battery_power_kw: float = 20
) -> Dict[str, float]:
    """
    Calculate savings from reduced demand charges

    Args:
        consumption: Hourly consumption series
        peak_reduction_kw: Peak reduction capability (if None, calculated from battery)
        battery_power_kw: Battery power rating

    Returns:
        Dictionary with demand charge savings
    """
    # Calculate monthly peaks
    monthly_peaks = consumption.resample('ME').max()

    if peak_reduction_kw is None:
        # Estimate peak reduction capability
        peak_reduction_kw = min(battery_power_kw, monthly_peaks.mean() * 0.3)

    # Lnett tariff structure (simplified)
    def calculate_tariff(peak_kw):
        brackets = [
            (0, 2, 136),
            (2, 5, 232),
            (5, 10, 372),
            (10, 15, 572),
            (15, 20, 772),
            (20, 25, 972),
            (25, 50, 1772),
            (50, 75, 2572),
            (75, 100, 3372),
            (100, 9999, 5600)
        ]

        monthly_charge = 0
        for from_kw, to_kw, rate in brackets:
            if peak_kw > from_kw:
                bracket_kw = min(peak_kw - from_kw, to_kw - from_kw)
                monthly_charge += bracket_kw * rate
            if peak_kw <= to_kw:
                break

        return monthly_charge

    # Calculate with and without battery
    original_charges = sum(calculate_tariff(peak) for peak in monthly_peaks)
    reduced_peaks = monthly_peaks - peak_reduction_kw
    reduced_charges = sum(calculate_tariff(max(0, peak)) for peak in reduced_peaks)

    savings = original_charges - reduced_charges

    return {
        'avg_monthly_peak_kw': monthly_peaks.mean(),
        'peak_reduction_kw': peak_reduction_kw,
        'original_annual_charge': original_charges,
        'reduced_annual_charge': reduced_charges,
        'annual_value_nok': savings
    }


def calculate_self_consumption_value(
    production: pd.Series,
    consumption: pd.Series,
    prices: pd.Series,
    battery_capacity_kwh: float = 50,
    battery_efficiency: float = 0.95  # Moderne LFP batterier
) -> Dict[str, float]:
    """
    Calculate value from increased self-consumption

    Args:
        production: Hourly production series
        consumption: Hourly consumption series
        prices: Hourly electricity prices
        battery_capacity_kwh: Battery capacity
        battery_efficiency: Battery efficiency

    Returns:
        Dictionary with self-consumption metrics
    """
    # Calculate net import (when consumption > production)
    net_import = (consumption - production).clip(lower=0)

    # Estimate battery contribution (simplified)
    # Assume battery can store excess and discharge when needed
    daily_cycling_potential = battery_capacity_kwh * 0.8 * 365  # Annual kWh

    # Limit to actual import needs
    battery_contribution = min(net_import.sum(), daily_cycling_potential)

    # Value at average import price
    avg_import_price = prices[net_import > 0].mean() if (net_import > 0).any() else prices.mean()
    self_consumption_value = battery_contribution * avg_import_price * battery_efficiency

    return {
        'total_import_kwh': net_import.sum(),
        'battery_contribution_kwh': battery_contribution,
        'avg_import_price': avg_import_price,
        'annual_value_nok': self_consumption_value,
        'self_sufficiency_increase': (battery_contribution / consumption.sum()) * 100
    }


def calculate_all_value_drivers(
    data: pd.DataFrame,
    battery_capacity_kwh: float = 50,
    battery_power_kw: float = 20,
    grid_limit_kw: float = 77
) -> Dict[str, Any]:
    """
    Calculate all value drivers for battery storage

    Args:
        data: DataFrame with production_kw, consumption_kw, spot_price_nok columns
        battery_capacity_kwh: Battery capacity
        battery_power_kw: Battery power rating
        grid_limit_kw: Grid export limit

    Returns:
        Dictionary with all value drivers and total
    """
    results = {}

    # 1. Curtailment value
    results['curtailment'] = calculate_curtailment_value(
        data['production_kw'],
        grid_limit_kw
    )

    # 2. Arbitrage value
    results['arbitrage'] = calculate_arbitrage_value(
        data['spot_price_nok'],
        battery_capacity_kwh
    )

    # 3. Demand charge savings
    results['demand_charge'] = calculate_demand_charge_savings(
        data['consumption_kw'],
        battery_power_kw=battery_power_kw
    )

    # 4. Self-consumption value
    results['self_consumption'] = calculate_self_consumption_value(
        data['production_kw'],
        data['consumption_kw'],
        data['spot_price_nok'],
        battery_capacity_kwh
    )

    # Calculate total
    total_value = sum(
        driver['annual_value_nok']
        for driver in results.values()
    )

    results['total_annual_value_nok'] = total_value

    # Add percentages
    for key in ['curtailment', 'arbitrage', 'demand_charge', 'self_consumption']:
        results[key]['percentage_of_total'] = (
            results[key]['annual_value_nok'] / total_value * 100
        )

    return results