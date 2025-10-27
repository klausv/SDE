"""
Economic model for battery system cost-benefit analysis
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional
from dataclasses import dataclass
import logging
from ..config import LnettTariff, EconomicConfig

logger = logging.getLogger(__name__)

@dataclass
class EconomicResults:
    """Economic analysis results"""
    npv: float
    irr: float
    payback_years: Optional[float]
    annual_savings: float
    total_revenue: float
    total_costs: float
    revenue_breakdown: Dict[str, float]
    yearly_cash_flows: pd.Series

class EconomicModel:
    """Economic model for battery investment analysis"""

    def __init__(
        self,
        tariff: LnettTariff,
        economic_config: EconomicConfig
    ):
        """
        Initialize economic model

        Args:
            tariff: Grid tariff structure
            economic_config: Economic parameters
        """
        self.tariff = tariff
        self.config = economic_config

    def calculate_npv(
        self,
        operation_results: Dict[str, pd.Series],
        spot_prices: pd.Series,
        load_profile: pd.Series,
        battery_cost_per_kwh: float,
        battery_capacity_kwh: float,
        battery_power_kw: float,
        include_vat: bool = True
    ) -> EconomicResults:
        """
        Calculate Net Present Value and economic metrics

        Args:
            operation_results: Battery operation simulation results
            spot_prices: Electricity spot prices (NOK/kWh)
            load_profile: Load consumption profile (kW)
            battery_cost_per_kwh: Battery investment cost (NOK/kWh)
            battery_capacity_kwh: Battery capacity
            battery_power_kw: Battery power rating
            include_vat: Whether to include VAT in calculations

        Returns:
            Economic analysis results
        """
        # Calculate initial investment
        battery_investment = battery_cost_per_kwh * battery_capacity_kwh
        if include_vat:
            battery_investment *= (1 + self.config.vat_rate)

        # Calculate annual revenues
        yearly_revenues = []
        yearly_cash_flows = []

        for year in range(self.config.battery_lifetime_years):
            # Apply degradation factor
            degradation_factor = 1 - (self.config.degradation_rate_yearly * year)

            # Calculate revenues for the year
            revenues = self._calculate_annual_revenues(
                operation_results,
                spot_prices,
                load_profile,
                degradation_factor
            )

            yearly_revenues.append(revenues)

            # Calculate cash flow
            annual_cash_flow = revenues['total']
            yearly_cash_flows.append(annual_cash_flow)

        # Convert to numpy array for NPV calculation
        cash_flows = np.array([-battery_investment] + yearly_cash_flows)
        years = np.arange(len(cash_flows))
        discount_factors = (1 + self.config.discount_rate) ** years

        # Calculate NPV
        npv = np.sum(cash_flows / discount_factors)

        # Calculate IRR
        irr = self._calculate_irr(cash_flows)

        # Calculate payback period
        cumulative_cash = np.cumsum(cash_flows)
        positive_indices = np.where(cumulative_cash > 0)[0]
        if len(positive_indices) > 0:
            payback_years = positive_indices[0]
        else:
            payback_years = None

        # Aggregate results
        total_revenue = sum(r['total'] for r in yearly_revenues)
        revenue_breakdown = {
            'peak_reduction': sum(r['peak_reduction'] for r in yearly_revenues),
            'arbitrage': sum(r['arbitrage'] for r in yearly_revenues),
            'curtailment_avoided': sum(r['curtailment_avoided'] for r in yearly_revenues),
        }

        return EconomicResults(
            npv=npv,
            irr=irr,
            payback_years=payback_years,
            annual_savings=np.mean(yearly_cash_flows),
            total_revenue=total_revenue,
            total_costs=battery_investment,
            revenue_breakdown=revenue_breakdown,
            yearly_cash_flows=pd.Series(yearly_cash_flows)
        )

    def _calculate_annual_revenues(
        self,
        operation_results: Dict[str, pd.Series],
        spot_prices: pd.Series,
        load_profile: pd.Series,
        degradation_factor: float
    ) -> Dict[str, float]:
        """
        Calculate annual revenues from battery operation

        Args:
            operation_results: Battery operation results
            spot_prices: Spot prices (NOK/kWh)
            load_profile: Load profile (kW)
            degradation_factor: Battery degradation factor (0-1)

        Returns:
            Dictionary with revenue components
        """
        # Apply degradation to battery flows
        adjusted_charge = operation_results['battery_charge'] * degradation_factor
        adjusted_discharge = operation_results['battery_discharge'] * degradation_factor

        # 1. Peak reduction savings (effekttariff)
        peak_reduction_savings = self._calculate_peak_reduction_savings(
            load_profile,
            adjusted_discharge,
            operation_results['grid_import']
        )

        # 2. Arbitrage revenue
        arbitrage_revenue = self._calculate_arbitrage_revenue(
            adjusted_charge,
            adjusted_discharge,
            spot_prices
        )

        # 3. Avoided curtailment value
        curtailment_value = self._calculate_curtailment_value(
            operation_results['curtailment'],
            spot_prices
        )

        return {
            'peak_reduction': peak_reduction_savings,
            'arbitrage': arbitrage_revenue,
            'curtailment_avoided': curtailment_value,
            'total': peak_reduction_savings + arbitrage_revenue + curtailment_value
        }

    def _calculate_peak_reduction_savings(
        self,
        load_profile: pd.Series,
        battery_discharge: pd.Series,
        grid_import: pd.Series
    ) -> float:
        """
        Calculate savings from peak power reduction

        Args:
            load_profile: Load consumption (kW)
            battery_discharge: Battery discharge (kW)
            grid_import: Grid import after battery (kW)

        Returns:
            Annual savings from peak reduction (NOK)
        """
        annual_savings = 0

        # Group by month
        monthly_data = pd.DataFrame({
            'load': load_profile,
            'discharge': battery_discharge,
            'grid_import': grid_import,
            'month': load_profile.index.month
        })

        for month in range(1, 13):
            month_data = monthly_data[monthly_data['month'] == month]

            # Calculate peak without battery (based on load)
            # Using daily peaks and averaging top 3 days
            daily_peaks_without = month_data.groupby(month_data.index.date)['load'].max()
            if len(daily_peaks_without) >= 3:
                peak_without = daily_peaks_without.nlargest(3).mean()
            else:
                peak_without = daily_peaks_without.mean()

            # Calculate peak with battery
            daily_peaks_with = month_data.groupby(month_data.index.date)['grid_import'].max()
            if len(daily_peaks_with) >= 3:
                peak_with = daily_peaks_with.nlargest(3).mean()
            else:
                peak_with = daily_peaks_with.mean()

            # Calculate tariff difference
            tariff_without = self.tariff.get_power_tariff(peak_without)
            tariff_with = self.tariff.get_power_tariff(peak_with)

            monthly_savings = tariff_without - tariff_with
            annual_savings += monthly_savings

        return annual_savings

    def _calculate_arbitrage_revenue(
        self,
        battery_charge: pd.Series,
        battery_discharge: pd.Series,
        spot_prices: pd.Series
    ) -> float:
        """
        Calculate revenue from price arbitrage

        Args:
            battery_charge: Battery charging (kW)
            battery_discharge: Battery discharging (kW)
            spot_prices: Spot prices (NOK/kWh)

        Returns:
            Annual arbitrage revenue (NOK)
        """
        # Cost of charging (buying electricity)
        charging_cost = (battery_charge * spot_prices).sum()

        # Revenue from discharging (selling electricity)
        discharging_revenue = (battery_discharge * spot_prices).sum()

        # Net arbitrage revenue
        arbitrage_revenue = discharging_revenue - charging_cost

        # Add grid tariff differential
        # During charging (usually night/low price), we pay night tariff
        # During discharging (usually day/high price), we avoid day tariff
        timestamps = battery_charge.index
        is_peak = pd.Series([self.tariff.is_peak_hours(t) for t in timestamps], index=timestamps)

        charge_tariff_cost = (
            battery_charge[is_peak] * self.tariff.energy_day +
            battery_charge[~is_peak] * self.tariff.energy_night_weekend
        ).sum()

        discharge_tariff_saving = (
            battery_discharge[is_peak] * self.tariff.energy_day +
            battery_discharge[~is_peak] * self.tariff.energy_night_weekend
        ).sum()

        total_arbitrage = arbitrage_revenue + discharge_tariff_saving - charge_tariff_cost

        return total_arbitrage

    def _calculate_curtailment_value(
        self,
        curtailment: pd.Series,
        spot_prices: pd.Series
    ) -> float:
        """
        Calculate value of avoided curtailment

        Args:
            curtailment: Curtailed energy (kWh)
            spot_prices: Spot prices (NOK/kWh)

        Returns:
            Value of avoided curtailment (NOK)
        """
        # Without battery, this energy would be lost
        # With battery, we can store and sell it later
        # Value is based on average spot price
        avoided_curtailment_kwh = curtailment.sum()
        average_price = spot_prices.mean()

        return avoided_curtailment_kwh * average_price * 0.9  # Apply efficiency factor

    def _calculate_irr(
        self,
        cash_flows: np.ndarray,
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ) -> Optional[float]:
        """
        Calculate Internal Rate of Return using Newton's method

        Args:
            cash_flows: Cash flow array (first element is negative investment)
            max_iterations: Maximum iterations for convergence
            tolerance: Convergence tolerance

        Returns:
            IRR as decimal (e.g., 0.15 for 15%) or None if no solution
        """
        # Initial guess
        rate = 0.1

        for _ in range(max_iterations):
            # Calculate NPV and its derivative
            years = np.arange(len(cash_flows))
            factors = (1 + rate) ** years
            npv = np.sum(cash_flows / factors)
            dnpv = -np.sum(years * cash_flows / (factors * (1 + rate)))

            # Newton's method update
            if abs(dnpv) < tolerance:
                return None

            new_rate = rate - npv / dnpv

            # Check convergence
            if abs(new_rate - rate) < tolerance:
                return new_rate

            rate = new_rate

            # Bound check
            if rate < -0.99:
                rate = -0.99
            elif rate > 10:
                rate = 10

        return None

    def calculate_levelized_cost_of_storage(
        self,
        battery_cost_per_kwh: float,
        battery_capacity_kwh: float,
        operation_results: Dict[str, pd.Series],
        include_vat: bool = True
    ) -> float:
        """
        Calculate Levelized Cost of Storage (LCOS)

        Args:
            battery_cost_per_kwh: Battery cost (NOK/kWh)
            battery_capacity_kwh: Battery capacity
            operation_results: Operation results
            include_vat: Whether to include VAT

        Returns:
            LCOS in NOK/kWh
        """
        # Total investment
        total_investment = battery_cost_per_kwh * battery_capacity_kwh
        if include_vat:
            total_investment *= (1 + self.config.vat_rate)

        # Total energy throughput over lifetime
        annual_throughput = operation_results['battery_discharge'].sum()
        total_throughput = 0

        for year in range(self.config.battery_lifetime_years):
            degradation = 1 - (self.config.degradation_rate_yearly * year)
            discounted_throughput = (annual_throughput * degradation) / (
                (1 + self.config.discount_rate) ** year
            )
            total_throughput += discounted_throughput

        # LCOS
        if total_throughput > 0:
            lcos = total_investment / total_throughput
        else:
            lcos = float('inf')

        return lcos