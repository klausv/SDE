"""
Economic Cost Function Module

Implements total electricity cost calculation following Korpås et al. methodology:
- Energy costs: spot prices + time-of-use tariffs + consumption tax
- Peak power costs: monthly capacity charges with progressive brackets

Based on Norwegian Lnett commercial tariff structure.
No VAT included (company assumption).
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple


# =============================================================================
# TARIFF CONFIGURATION (Lnett Commercial < 100 MWh/year)
# =============================================================================

# Energy tariffs (NOK/kWh excluding VAT)
ENERGY_TARIFF_DAY = 0.296  # Mon-Fri 06:00-22:00
ENERGY_TARIFF_NIGHT = 0.176  # Mon-Fri 22:00-06:00 + weekends

# Consumption tax by month (NOK/kWh)
CONSUMPTION_TAX = {
    1: 0.0979,
    2: 0.0979,
    3: 0.0979,  # Jan-Mar (winter)
    4: 0.1693,
    5: 0.1693,
    6: 0.1693,
    7: 0.1693,
    8: 0.1693,
    9: 0.1693,  # Apr-Sep (summer)
    10: 0.1253,
    11: 0.1253,
    12: 0.1253,  # Oct-Dec (fall)
}

# Power tariff progressive brackets (NOK/month per bracket)
# Each bracket specifies: (min_kW, max_kW): cost_NOK_per_month
POWER_TARIFF_BRACKETS = [
    (0, 2, 136),
    (2, 5, 232),
    (5, 10, 372),
    (10, 15, 572),
    (15, 20, 772),
    (20, 25, 972),
    (25, 50, 1772),
    (50, 75, 2572),
    (75, 100, 3372),
    (100, float("inf"), 5600),
]

# Feed-in tariff (export compensation, NOK/kWh)
FEED_IN_TARIFF = 0.04


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_energy_tariff(timestamp: pd.Timestamp) -> float:
    """
    Get time-of-use energy tariff for given timestamp.

    Args:
        timestamp: pandas Timestamp

    Returns:
        energy_tariff: NOK/kWh (excluding VAT)
    """
    # Check if weekday (0=Monday, 6=Sunday)
    is_weekday = timestamp.weekday() < 5

    # Check if peak hours (06:00-22:00)
    is_peak_hours = 6 <= timestamp.hour < 22

    if is_weekday and is_peak_hours:
        return ENERGY_TARIFF_DAY
    else:
        return ENERGY_TARIFF_NIGHT


def get_consumption_tax(month: int) -> float:
    """
    Get seasonal consumption tax for given month.

    Args:
        month: Month number (1-12)

    Returns:
        consumption_tax: NOK/kWh
    """
    return CONSUMPTION_TAX[month]


def get_power_tariff(peak_kw: float) -> float:
    """
    Get monthly power tariff for given peak demand using progressive brackets.

    Args:
        peak_kw: Monthly peak power in kW

    Returns:
        power_tariff: NOK/month
    """
    for min_kw, max_kw, cost in POWER_TARIFF_BRACKETS:
        if min_kw <= peak_kw < max_kw:
            return cost

    # Should never reach here if brackets are properly defined
    return POWER_TARIFF_BRACKETS[-1][2]


# =============================================================================
# MAIN COST CALCULATION FUNCTIONS
# =============================================================================


def calculate_energy_cost(
    grid_import_power: np.ndarray,
    grid_export_power: np.ndarray,
    timestamps: pd.DatetimeIndex,
    spot_prices: np.ndarray,
    timestep_hours: float = 1.0,
) -> Tuple[float, pd.DataFrame]:
    """
    Calculate total energy cost (hourly spot + tariff + tax).

    Based on Korpås Equation 5 (energy term):
    C_energy = Σ [(spot + tariff + tax) × import - feed_in × export] × Δt

    Args:
        grid_import_power: Power bought from grid (kW), shape (T,)
        grid_export_power: Power sold to grid (kW), shape (T,)
        timestamps: Time index for each timestep
        spot_prices: Hourly spot prices (NOK/kWh), shape (T,)
        timestep_hours: Duration of each timestep in hours (default 1.0)

    Returns:
        total_energy_cost: Total annual energy cost in NOK
        hourly_details: DataFrame with hourly cost breakdown
    """
    T = len(grid_import_power)

    # Initialize arrays for breakdown
    energy_tariffs = np.zeros(T)
    consumption_taxes = np.zeros(T)
    import_costs = np.zeros(T)
    export_revenues = np.zeros(T)

    # Calculate hourly costs
    for t in range(T):
        timestamp = timestamps[t]

        # Get tariffs for this hour
        energy_tariff = get_energy_tariff(timestamp)
        consumption_tax = get_consumption_tax(timestamp.month)

        # Store for breakdown
        energy_tariffs[t] = energy_tariff
        consumption_taxes[t] = consumption_tax

        # Calculate import cost
        total_price_import = spot_prices[t] + energy_tariff + consumption_tax
        import_costs[t] = grid_import_power[t] * total_price_import * timestep_hours

        # Calculate export revenue (only feed-in tariff, no spot price compensation)
        export_revenues[t] = grid_export_power[t] * FEED_IN_TARIFF * timestep_hours

    # Total energy cost
    total_energy_cost = np.sum(import_costs) - np.sum(export_revenues)

    # Create detailed DataFrame
    hourly_details = pd.DataFrame(
        {
            "timestamp": timestamps,
            "grid_import_kw": grid_import_power,
            "grid_export_kw": grid_export_power,
            "spot_price_nok_kwh": spot_prices,
            "energy_tariff_nok_kwh": energy_tariffs,
            "consumption_tax_nok_kwh": consumption_taxes,
            "import_cost_nok": import_costs,
            "export_revenue_nok": export_revenues,
            "net_cost_nok": import_costs - export_revenues,
        }
    )

    return total_energy_cost, hourly_details


def calculate_peak_cost(
    grid_import_power: np.ndarray, timestamps: pd.DatetimeIndex
) -> Tuple[float, pd.DataFrame]:
    """
    Calculate total peak power cost (monthly capacity charges).

    Based on Korpås Equation 5 (peak term):
    C_peak = Σ_months get_power_tariff(monthly_peak)

    Uses Norwegian standard: average of top 3 daily peaks per month.

    Args:
        grid_import_power: Power bought from grid (kW), shape (T,)
        timestamps: Time index for each timestep

    Returns:
        total_peak_cost: Total annual peak cost in NOK
        monthly_details: DataFrame with monthly peak breakdown
    """
    # Create DataFrame for easier grouping
    df = pd.DataFrame(
        {"timestamp": timestamps, "grid_import_kw": grid_import_power}
    )

    df["date"] = df["timestamp"].dt.date
    df["month"] = df["timestamp"].dt.month
    df["year"] = df["timestamp"].dt.year

    monthly_peaks = []
    monthly_costs = []
    months = []

    # Calculate for each month
    for (year, month), month_data in df.groupby(["year", "month"]):
        # Get daily peaks for this month
        daily_peaks = month_data.groupby("date")["grid_import_kw"].max()

        # Norwegian standard: average of top 3 daily peaks
        if len(daily_peaks) >= 3:
            monthly_peak = daily_peaks.nlargest(3).mean()
        else:
            monthly_peak = daily_peaks.max()

        # Get tariff for this peak
        monthly_cost = get_power_tariff(monthly_peak)

        months.append(month)
        monthly_peaks.append(monthly_peak)
        monthly_costs.append(monthly_cost)

    # Total peak cost
    total_peak_cost = sum(monthly_costs)

    # Create detailed DataFrame
    monthly_details = pd.DataFrame(
        {
            "month": months,
            "peak_power_kw": monthly_peaks,
            "peak_cost_nok": monthly_costs,
        }
    )

    return total_peak_cost, monthly_details


def calculate_total_cost(
    grid_import_power: np.ndarray,
    grid_export_power: np.ndarray,
    timestamps: pd.DatetimeIndex,
    spot_prices: np.ndarray,
    timestep_hours: float = 1.0,
) -> Dict:
    """
    Calculate total electricity cost (energy + peak).

    Main API function implementing Korpås Equation 5:
    C_total = C_energy + C_peak

    No VAT included (company assumption).
    No battery degradation cost (simplified model).

    Args:
        grid_import_power: Power bought from grid (kW), shape (T,)
        grid_export_power: Power sold to grid (kW), shape (T,)
        timestamps: Time index for each timestep
        spot_prices: Hourly spot prices (NOK/kWh), shape (T,)
        timestep_hours: Duration of each timestep in hours (default 1.0)

    Returns:
        results: Dictionary containing:
            - total_cost_nok: Total annual cost
            - energy_cost_nok: Energy component
            - peak_cost_nok: Peak component
            - monthly_breakdown: DataFrame with monthly details
            - hourly_details: DataFrame with hourly details
    """
    # Calculate energy cost
    energy_cost, hourly_details = calculate_energy_cost(
        grid_import_power, grid_export_power, timestamps, spot_prices, timestep_hours
    )

    # Calculate peak cost
    peak_cost, monthly_details = calculate_peak_cost(grid_import_power, timestamps)

    # Add energy cost breakdown to monthly details
    monthly_energy_costs = []
    for month in monthly_details["month"]:
        month_mask = timestamps.month == month
        month_energy_cost = hourly_details.loc[month_mask, "net_cost_nok"].sum()
        monthly_energy_costs.append(month_energy_cost)

    monthly_details["energy_cost_nok"] = monthly_energy_costs
    monthly_details["total_cost_nok"] = (
        monthly_details["energy_cost_nok"] + monthly_details["peak_cost_nok"]
    )

    # Total cost
    total_cost = energy_cost + peak_cost

    return {
        "total_cost_nok": total_cost,
        "energy_cost_nok": energy_cost,
        "peak_cost_nok": peak_cost,
        "monthly_breakdown": monthly_details,
        "hourly_details": hourly_details,
    }
