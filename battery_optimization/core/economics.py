"""
Economic calculations - NPV, IRR, payback
"""
import numpy as np
from typing import List, Optional


class EconomicAnalyzer:
    """Simple economic analysis for battery investment"""

    def __init__(
        self,
        discount_rate: float = 0.05,
        project_years: int = 15,
        degradation_rate: float = 0.02
    ):
        self.discount_rate = discount_rate
        self.project_years = project_years
        self.degradation_rate = degradation_rate

    def calculate_npv(self, cash_flows: List[float]) -> float:
        """
        Calculate Net Present Value
        First element should be negative (investment)
        """
        npv = 0
        for year, cash_flow in enumerate(cash_flows):
            npv += cash_flow / ((1 + self.discount_rate) ** year)
        return npv

    def calculate_irr(self, cash_flows: List[float]) -> Optional[float]:
        """Calculate Internal Rate of Return"""
        # Use numpy's IRR function
        try:
            # Newton's method
            rate = 0.1
            tolerance = 1e-6
            max_iterations = 100

            for _ in range(max_iterations):
                npv = 0
                npv_derivative = 0

                for year, cash_flow in enumerate(cash_flows):
                    discount_factor = (1 + rate) ** year
                    npv += cash_flow / discount_factor
                    if year > 0:
                        npv_derivative -= year * cash_flow / ((1 + rate) ** (year + 1))

                if abs(npv) < tolerance:
                    return rate

                if npv_derivative != 0:
                    rate = rate - npv / npv_derivative
                    rate = max(-0.99, min(rate, 10))

            return None
        except:
            return None

    def calculate_payback(
        self,
        initial_investment: float,
        annual_savings: float
    ) -> float:
        """Simple payback period calculation"""
        if annual_savings <= 0:
            return float('inf')

        cumulative = 0
        for year in range(1, 51):  # Max 50 years
            yearly_savings = annual_savings * ((1 - self.degradation_rate) ** year)
            cumulative += yearly_savings
            if cumulative >= initial_investment:
                return year

        return float('inf')

    def analyze_battery(
        self,
        battery_capacity_kwh: float,
        battery_cost_per_kwh: float,
        annual_value: float
    ) -> dict:
        """Complete economic analysis for battery"""
        initial_investment = battery_capacity_kwh * battery_cost_per_kwh

        # Generate cash flows
        cash_flows = [-initial_investment]
        for year in range(1, self.project_years + 1):
            yearly_value = annual_value * ((1 - self.degradation_rate) ** year)
            cash_flows.append(yearly_value)

        # Calculate metrics
        npv = self.calculate_npv(cash_flows)
        irr = self.calculate_irr(cash_flows)
        payback = self.calculate_payback(initial_investment, annual_value)

        return {
            'initial_investment': initial_investment,
            'npv': npv,
            'irr': irr,
            'payback_years': payback,
            'profitable': npv > 0
        }

    def find_break_even_cost(
        self,
        battery_capacity_kwh: float,
        annual_value: float,
        tolerance: float = 10
    ) -> float:
        """Find break-even battery cost where NPV = 0"""
        low, high = 1000, 10000

        while high - low > tolerance:
            mid = (low + high) / 2
            result = self.analyze_battery(battery_capacity_kwh, mid, annual_value)

            if result['npv'] > 0:
                low = mid
            else:
                high = mid

        return (low + high) / 2