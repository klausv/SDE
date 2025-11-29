"""
Economic Cost Function Module

Implements total electricity cost calculation following Korpås et al. methodology:
- Energy costs: spot prices + time-of-use tariffs + consumption tax
- Peak power costs: monthly capacity charges with progressive brackets

Based on Norwegian Lnett commercial tariff structure.
No VAT included (company assumption).

REFACTORED: Now uses unified tariff configuration from infrastructure module.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional

# Import tariff infrastructure
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from infrastructure.tariffs import TariffLoader, TariffProfile


# =============================================================================
# TARIFF CONFIGURATION (Unified from YAML)
# =============================================================================

# Load default Lnett 2024 tariff configuration
# This provides backward compatibility for existing code
_DEFAULT_TARIFF = TariffLoader.get_default_tariff()

# Deprecated constants (kept for backward compatibility, will be removed in future)
# Use _DEFAULT_TARIFF methods instead
ENERGY_TARIFF_DAY = _DEFAULT_TARIFF.energy.peak_rate
ENERGY_TARIFF_NIGHT = _DEFAULT_TARIFF.energy.offpeak_rate
FEED_IN_TARIFF = _DEFAULT_TARIFF.feed_in.rate

# Deprecated: Use _DEFAULT_TARIFF.get_consumption_tax(month) instead
CONSUMPTION_TAX = {month: _DEFAULT_TARIFF.get_consumption_tax(month) for month in range(1, 13)}

# Deprecated: Use _DEFAULT_TARIFF.get_power_tariff(peak_kw) instead
POWER_TARIFF_BRACKETS = [
    (bracket.min_kw, bracket.max_kw, bracket.cost_nok_month)
    for bracket in _DEFAULT_TARIFF.power.brackets
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_energy_tariff(timestamp: pd.Timestamp, tariff: Optional[TariffProfile] = None) -> float:
    """
    Get time-of-use energy tariff for given timestamp.

    Args:
        timestamp: pandas Timestamp
        tariff: Optional TariffProfile (uses default if None)

    Returns:
        energy_tariff: NOK/kWh (excluding VAT)
    """
    if tariff is None:
        tariff = _DEFAULT_TARIFF

    return tariff.get_energy_tariff(timestamp)


def get_consumption_tax(month: int, tariff: Optional[TariffProfile] = None) -> float:
    """
    Get seasonal consumption tax for given month.

    Args:
        month: Month number (1-12)
        tariff: Optional TariffProfile (uses default if None)

    Returns:
        consumption_tax: NOK/kWh
    """
    if tariff is None:
        tariff = _DEFAULT_TARIFF

    return tariff.get_consumption_tax(month)


def get_power_tariff(peak_kw: float, tariff: Optional[TariffProfile] = None) -> float:
    """
    Get monthly power tariff for given peak demand.

    Args:
        peak_kw: Monthly peak power in kW
        tariff: Optional TariffProfile (uses default if None)

    Returns:
        power_tariff: NOK/month
    """
    if tariff is None:
        tariff = _DEFAULT_TARIFF

    return tariff.get_power_tariff(peak_kw)


# =============================================================================
# MAIN COST CALCULATION FUNCTIONS
# =============================================================================


def calculate_energy_cost(
    grid_import_power: np.ndarray,
    grid_export_power: np.ndarray,
    timestamps: pd.DatetimeIndex,
    spot_prices: np.ndarray,
    timestep_hours: float = 1.0,
    tariff: Optional[TariffProfile] = None,
) -> Tuple[float, pd.DataFrame]:
    """
    Calculate total energy cost (hourly spot + tariff + tax).

    Based on Korpås Equation 5 (energy term):
    C_energy = Σ [(spot + tariff + tax) × import - (spot + feed_in) × export] × Δt

    Args:
        grid_import_power: Power bought from grid (kW), shape (T,)
        grid_export_power: Power sold to grid (kW), shape (T,)
        timestamps: Time index for each timestep
        spot_prices: Hourly spot prices (NOK/kWh), shape (T,)
        timestep_hours: Duration of each timestep in hours (default 1.0)
        tariff: Optional TariffProfile (uses default if None)

    Returns:
        total_energy_cost: Total annual energy cost in NOK
        hourly_details: DataFrame with hourly cost breakdown
    """
    if tariff is None:
        tariff = _DEFAULT_TARIFF

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
        energy_tariff = get_energy_tariff(timestamp, tariff)
        consumption_tax = get_consumption_tax(timestamp.month, tariff)

        # Store for breakdown
        energy_tariffs[t] = energy_tariff
        consumption_taxes[t] = consumption_tax

        # Calculate import cost
        total_price_import = spot_prices[t] + energy_tariff + consumption_tax
        import_costs[t] = grid_import_power[t] * total_price_import * timestep_hours

        # Calculate export revenue (spot price + feed-in tariff/plusskunde-støtte)
        # Norwegian "plusskunde" gets: spot price + grid tariff reduction (~0.04 NOK/kWh)
        total_price_export = spot_prices[t] + tariff.get_feed_in_tariff()
        export_revenues[t] = grid_export_power[t] * total_price_export * timestep_hours

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
    grid_import_power: np.ndarray,
    timestamps: pd.DatetimeIndex,
    tariff: Optional[TariffProfile] = None,
) -> Tuple[float, pd.DataFrame]:
    """
    Calculate total peak power cost (monthly capacity charges).

    Based on Korpås Equation 5 (peak term):
    C_peak = Σ_months get_power_tariff(monthly_peak)

    Uses Norwegian standard: average of top 3 daily peaks per month.

    Args:
        grid_import_power: Power bought from grid (kW), shape (T,)
        timestamps: Time index for each timestep
        tariff: Optional TariffProfile (uses default if None)

    Returns:
        total_peak_cost: Total annual peak cost in NOK
        monthly_details: DataFrame with monthly peak breakdown
    """
    if tariff is None:
        tariff = _DEFAULT_TARIFF
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
        monthly_cost = get_power_tariff(monthly_peak, tariff)

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
    tariff: Optional[TariffProfile] = None,
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
        tariff: Optional TariffProfile (uses default if None)

    Returns:
        results: Dictionary containing:
            - total_cost_nok: Total annual cost
            - energy_cost_nok: Energy component
            - peak_cost_nok: Peak component
            - monthly_breakdown: DataFrame with monthly details
            - hourly_details: DataFrame with hourly details
    """
    if tariff is None:
        tariff = _DEFAULT_TARIFF

    # Calculate energy cost
    energy_cost, hourly_details = calculate_energy_cost(
        grid_import_power, grid_export_power, timestamps, spot_prices, timestep_hours, tariff
    )

    # Calculate peak cost
    peak_cost, monthly_details = calculate_peak_cost(grid_import_power, timestamps, tariff)

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
