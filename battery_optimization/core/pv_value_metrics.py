"""
PV Value Metrics Calculator

Calculates the economic value of solar PV generation, including:
- Average obtained price of PV (weighted by consumption vs export)
- Self-consumption rate
- Export rate
- Value comparison with/without battery
"""

import numpy as np
import pandas as pd
from typing import Dict


def calculate_pv_value_metrics(
    pv_production_kw: np.ndarray,
    load_consumption_kw: np.ndarray,
    grid_import_kw: np.ndarray,
    grid_export_kw: np.ndarray,
    timestamps: pd.DatetimeIndex,
    spot_prices: np.ndarray,
    energy_tariff_nok_kwh: np.ndarray,
    consumption_tax_nok_kwh: np.ndarray,
    feed_in_tariff: float = 0.04,
    timestep_hours: float = 1.0
) -> Dict:
    """
    Calculate the average obtained price of PV generation.

    The PV value is calculated as a weighted average of:
    1. Self-consumed PV: valued at avoided import cost (spot + tariff + tax)
    2. Exported PV: valued at export compensation (typically spot price only or feed-in tariff)

    Args:
        pv_production_kw: Solar PV production (kW), shape (T,)
        load_consumption_kw: Load consumption (kW), shape (T,)
        grid_import_kw: Grid import power (kW), shape (T,)
        grid_export_kw: Grid export power (kW), shape (T,)
        timestamps: Time index for each timestep
        spot_prices: Hourly spot prices (NOK/kWh), shape (T,)
        energy_tariff_nok_kwh: Energy tariff for each hour (NOK/kWh), shape (T,)
        consumption_tax_nok_kwh: Consumption tax for each hour (NOK/kWh), shape (T,)
        feed_in_tariff: Export compensation (NOK/kWh), default 0.04
        timestep_hours: Duration of each timestep (hours), default 1.0

    Returns:
        dict: Dictionary containing:
            - pv_total_energy_kwh: Total PV production energy (kWh)
            - pv_self_consumed_kwh: PV energy self-consumed (kWh)
            - pv_exported_kwh: PV energy exported to grid (kWh)
            - self_consumption_rate: Fraction of PV self-consumed (0-1)
            - export_rate: Fraction of PV exported (0-1)
            - pv_self_consumed_value_nok: Value of self-consumed PV (NOK)
            - pv_exported_value_nok: Value of exported PV (NOK)
            - pv_total_value_nok: Total value of PV generation (NOK)
            - pv_average_price_nok_kwh: Average obtained price (NOK/kWh)
            - avoided_import_avg_price: Average avoided import price (NOK/kWh)
            - export_avg_price: Average export price (NOK/kWh)
    """
    T = len(pv_production_kw)

    # Calculate self-consumed vs exported PV energy
    # Self-consumed PV = PV production that doesn't go to grid
    # For each hour: PV goes to (1) load, (2) battery charging, (3) grid export

    # Simple approach: PV self-consumed = PV production - Grid export
    pv_self_consumed_kw = np.maximum(0, pv_production_kw - grid_export_kw)
    pv_exported_kw = grid_export_kw  # All grid export comes from PV (assuming no battery discharge to grid)

    # Energy (kWh)
    pv_total_energy = np.sum(pv_production_kw) * timestep_hours
    pv_self_consumed_energy = np.sum(pv_self_consumed_kw) * timestep_hours
    pv_exported_energy = np.sum(pv_exported_kw) * timestep_hours

    # Rates
    self_consumption_rate = pv_self_consumed_energy / pv_total_energy if pv_total_energy > 0 else 0
    export_rate = pv_exported_energy / pv_total_energy if pv_total_energy > 0 else 0

    # Calculate value of self-consumed PV
    # Self-consumed PV avoids import at full retail price (spot + tariff + tax)
    avoided_import_price = spot_prices + energy_tariff_nok_kwh + consumption_tax_nok_kwh
    pv_self_consumed_value = np.sum(pv_self_consumed_kw * avoided_import_price * timestep_hours)

    # Calculate value of exported PV
    # Exported PV receives feed-in tariff (or spot price minus fees)
    # For "plusskunde" (net metering customer), typically no export compensation, just spot price
    # Using feed_in_tariff parameter (default 0.04 NOK/kWh)
    export_price = np.full(T, feed_in_tariff)  # Could also use spot_prices if different
    pv_exported_value = np.sum(pv_exported_kw * export_price * timestep_hours)

    # Total PV value
    pv_total_value = pv_self_consumed_value + pv_exported_value

    # Average obtained price of PV (weighted average)
    pv_average_price = pv_total_value / pv_total_energy if pv_total_energy > 0 else 0

    # Average prices by component
    avoided_import_avg = (pv_self_consumed_value / pv_self_consumed_energy
                         if pv_self_consumed_energy > 0 else 0)
    export_avg = (pv_exported_value / pv_exported_energy
                 if pv_exported_energy > 0 else 0)

    return {
        'pv_total_energy_kwh': pv_total_energy,
        'pv_self_consumed_kwh': pv_self_consumed_energy,
        'pv_exported_kwh': pv_exported_energy,
        'self_consumption_rate': self_consumption_rate,
        'export_rate': export_rate,
        'pv_self_consumed_value_nok': pv_self_consumed_value,
        'pv_exported_value_nok': pv_exported_value,
        'pv_total_value_nok': pv_total_value,
        'pv_average_price_nok_kwh': pv_average_price,
        'avoided_import_avg_price_nok_kwh': avoided_import_avg,
        'export_avg_price_nok_kwh': export_avg
    }


def print_pv_value_summary(metrics: Dict, scenario_name: str = ""):
    """
    Print formatted PV value metrics summary
    """
    if scenario_name:
        print(f"\n{'='*80}")
        print(f" PV VALUE METRICS - {scenario_name}")
        print(f"{'='*80}")
    else:
        print(f"\n{'='*80}")
        print(" PV VALUE METRICS")
        print(f"{'='*80}")

    print("\n1. PV ENERGY DISTRIBUTION")
    print("-" * 80)
    print(f"   Total PV production:           {metrics['pv_total_energy_kwh']:>12,.0f} kWh")
    print(f"   Self-consumed:                 {metrics['pv_self_consumed_kwh']:>12,.0f} kWh "
          f"({metrics['self_consumption_rate']*100:>5.1f}%)")
    print(f"   Exported to grid:              {metrics['pv_exported_kwh']:>12,.0f} kWh "
          f"({metrics['export_rate']*100:>5.1f}%)")

    print("\n2. PV ECONOMIC VALUE")
    print("-" * 80)
    print(f"   Value of self-consumed PV:     {metrics['pv_self_consumed_value_nok']:>12,.0f} NOK")
    print(f"   Value of exported PV:          {metrics['pv_exported_value_nok']:>12,.0f} NOK")
    print(f"   Total PV value:                {metrics['pv_total_value_nok']:>12,.0f} NOK")

    print("\n3. AVERAGE OBTAINED PV PRICE")
    print("-" * 80)
    print(f"   Average PV price (weighted):   {metrics['pv_average_price_nok_kwh']:>12.3f} NOK/kWh")
    print(f"   - Self-consumed avg price:     {metrics['avoided_import_avg_price_nok_kwh']:>12.3f} NOK/kWh")
    print(f"   - Exported avg price:          {metrics['export_avg_price_nok_kwh']:>12.3f} NOK/kWh")

    print("\n" + "="*80)


def compare_pv_value(metrics_ref: Dict, metrics_battery: Dict):
    """
    Compare PV value metrics between reference and battery scenarios
    """
    print("\n" + "="*80)
    print(" PV VALUE COMPARISON: Reference vs Battery")
    print("="*80)

    # Self-consumption improvement
    sc_improvement = (metrics_battery['self_consumption_rate'] -
                     metrics_ref['self_consumption_rate']) * 100

    # Value improvement
    value_improvement = (metrics_battery['pv_total_value_nok'] -
                        metrics_ref['pv_total_value_nok'])
    value_improvement_pct = (value_improvement /
                            metrics_ref['pv_total_value_nok'] * 100)

    # Average price improvement
    price_improvement = (metrics_battery['pv_average_price_nok_kwh'] -
                        metrics_ref['pv_average_price_nok_kwh'])

    print("\n1. SELF-CONSUMPTION IMPROVEMENT")
    print("-" * 80)
    print(f"   Reference self-consumption:    {metrics_ref['self_consumption_rate']*100:>12.1f} %")
    print(f"   Battery self-consumption:      {metrics_battery['self_consumption_rate']*100:>12.1f} %")
    print(f"   Improvement:                   {sc_improvement:>12.1f} percentage points")

    print("\n2. PV VALUE IMPROVEMENT")
    print("-" * 80)
    print(f"   Reference PV value:            {metrics_ref['pv_total_value_nok']:>12,.0f} NOK")
    print(f"   Battery PV value:              {metrics_battery['pv_total_value_nok']:>12,.0f} NOK")
    print(f"   Improvement:                   {value_improvement:>12,.0f} NOK "
          f"({value_improvement_pct:>5.2f}%)")

    print("\n3. AVERAGE PV PRICE IMPROVEMENT")
    print("-" * 80)
    print(f"   Reference avg price:           {metrics_ref['pv_average_price_nok_kwh']:>12.3f} NOK/kWh")
    print(f"   Battery avg price:             {metrics_battery['pv_average_price_nok_kwh']:>12.3f} NOK/kWh")
    print(f"   Improvement:                   {price_improvement:>12.3f} NOK/kWh")

    print("\n" + "="*80)

    return {
        'self_consumption_improvement_pct': sc_improvement,
        'pv_value_improvement_nok': value_improvement,
        'pv_value_improvement_pct': value_improvement_pct,
        'avg_price_improvement_nok_kwh': price_improvement
    }
