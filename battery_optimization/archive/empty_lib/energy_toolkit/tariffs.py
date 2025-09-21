"""
Grid tariff structures for Norway and general use
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np

from domain.value_objects.energy import Energy, Power
from domain.value_objects.money import Money, CostPerUnit


class TariffStructure(ABC):
    """Abstract base class for tariff structures"""

    @abstractmethod
    def calculate_energy_charge(self, consumption: pd.Series) -> Money:
        """Calculate energy charges for consumption series"""
        pass

    @abstractmethod
    def calculate_demand_charge(self, peak_demand: Power, month: int) -> Money:
        """Calculate monthly demand charge based on peak"""
        pass

    @abstractmethod
    def calculate_total_cost(self, consumption: pd.Series, peaks: pd.Series) -> Money:
        """Calculate total cost including all components"""
        pass


@dataclass
class TimeOfUseTariff(TariffStructure):
    """Time-of-use tariff with peak/off-peak rates"""

    peak_rate: CostPerUnit  # NOK/kWh during peak
    off_peak_rate: CostPerUnit  # NOK/kWh during off-peak
    peak_hours: Tuple[int, int] = (6, 22)  # Start and end hour
    peak_days: List[int] = None  # Days of week (0=Monday)

    def __post_init__(self):
        if self.peak_days is None:
            self.peak_days = [0, 1, 2, 3, 4]  # Monday-Friday

    def calculate_energy_charge(self, consumption: pd.Series) -> Money:
        """Calculate energy charges based on time-of-use"""
        peak_mask = self._get_peak_mask(consumption.index)

        peak_consumption = consumption[peak_mask].sum()
        off_peak_consumption = consumption[~peak_mask].sum()

        peak_cost = self.peak_rate.calculate_total(peak_consumption)
        off_peak_cost = self.off_peak_rate.calculate_total(off_peak_consumption)

        return peak_cost + off_peak_cost

    def calculate_demand_charge(self, peak_demand: Power, month: int) -> Money:
        """No demand charge in simple TOU tariff"""
        return Money.nok(0)

    def calculate_total_cost(self, consumption: pd.Series, peaks: pd.Series = None) -> Money:
        """Calculate total cost"""
        return self.calculate_energy_charge(consumption)

    def _get_peak_mask(self, index: pd.DatetimeIndex) -> pd.Series:
        """Get boolean mask for peak hours"""
        return (
            (index.hour >= self.peak_hours[0]) &
            (index.hour < self.peak_hours[1]) &
            (index.dayofweek.isin(self.peak_days))
        )


@dataclass
class DemandChargeTariff(TariffStructure):
    """Tariff with demand charges based on peak power"""

    energy_rate: CostPerUnit  # NOK/kWh
    demand_rate: CostPerUnit  # NOK/kW/month
    measurement_method: str = "highest_hour"  # or "average_three_highest"

    def calculate_energy_charge(self, consumption: pd.Series) -> Money:
        """Calculate flat energy charge"""
        total_consumption = consumption.sum()
        return self.energy_rate.calculate_total(total_consumption)

    def calculate_demand_charge(self, peak_demand: Power, month: int) -> Money:
        """Calculate monthly demand charge"""
        return self.demand_rate.calculate_total(peak_demand.kw)

    def calculate_total_cost(self, consumption: pd.Series, peaks: pd.Series) -> Money:
        """Calculate total cost with demand charges"""
        energy_cost = self.calculate_energy_charge(consumption)

        # Calculate monthly demand charges
        demand_cost = Money.nok(0)
        for month, peak in peaks.items():
            demand_cost += self.calculate_demand_charge(Power.from_kw(peak), month)

        return energy_cost + demand_cost


@dataclass
class TieredTariff(TariffStructure):
    """Progressive tiered tariff structure"""

    tiers: List[Dict[str, float]]  # List of {from_kwh, to_kwh, rate}

    def calculate_energy_charge(self, consumption: pd.Series) -> Money:
        """Calculate tiered energy charges"""
        total_consumption = consumption.sum()
        cost = 0.0

        for tier in self.tiers:
            from_kwh = tier['from_kwh']
            to_kwh = tier['to_kwh']
            rate = tier['rate']

            if total_consumption > from_kwh:
                tier_consumption = min(total_consumption - from_kwh, to_kwh - from_kwh)
                cost += tier_consumption * rate

                if total_consumption <= to_kwh:
                    break

        return Money.nok(cost)

    def calculate_demand_charge(self, peak_demand: Power, month: int) -> Money:
        """No demand charge in tiered tariff"""
        return Money.nok(0)

    def calculate_total_cost(self, consumption: pd.Series, peaks: pd.Series = None) -> Money:
        """Calculate total cost"""
        return self.calculate_energy_charge(consumption)


class LnettCommercialTariff(TariffStructure):
    """Lnett commercial tariff structure for Norway"""

    def __init__(self):
        # Energy rates (NOK/kWh)
        self.peak_energy_rate = 0.296  # Mon-Fri 06:00-22:00
        self.off_peak_energy_rate = 0.176  # Nights and weekends

        # Power charge brackets (NOK per kW per month)
        self.power_brackets = [
            {'from_kw': 0, 'to_kw': 2, 'rate': 136},
            {'from_kw': 2, 'to_kw': 5, 'rate': 232},
            {'from_kw': 5, 'to_kw': 10, 'rate': 372},
            {'from_kw': 10, 'to_kw': 15, 'rate': 572},
            {'from_kw': 15, 'to_kw': 20, 'rate': 772},
            {'from_kw': 20, 'to_kw': 25, 'rate': 972},
            {'from_kw': 25, 'to_kw': 50, 'rate': 1772},
            {'from_kw': 50, 'to_kw': 75, 'rate': 2572},
            {'from_kw': 75, 'to_kw': 100, 'rate': 3372},
            {'from_kw': 100, 'to_kw': 999999, 'rate': 5600}
        ]

        # Consumption tax by month (NOK/kWh)
        self.consumption_tax = {
            1: 0.1541, 2: 0.1541, 3: 0.1541,  # Jan-Mar (winter)
            4: 0.0891, 5: 0.0891, 6: 0.0891,  # Apr-Jun
            7: 0.0891, 8: 0.0891, 9: 0.0891,  # Jul-Sep
            10: 0.0891, 11: 0.0891, 12: 0.1541  # Oct-Dec
        }

        # Fixed charges
        self.enova_fee_annual = 800  # NOK/year

    def calculate_energy_charge(self, consumption: pd.Series) -> Money:
        """Calculate energy charges including consumption tax"""
        # Peak hours mask (Mon-Fri 06:00-22:00)
        peak_mask = (
            (consumption.index.hour >= 6) &
            (consumption.index.hour < 22) &
            (consumption.index.dayofweek < 5)
        )

        peak_consumption = consumption[peak_mask].sum()
        off_peak_consumption = consumption[~peak_mask].sum()

        # Base energy charges
        energy_cost = (
            peak_consumption * self.peak_energy_rate +
            off_peak_consumption * self.off_peak_energy_rate
        )

        # Add consumption tax
        for month in range(1, 13):
            month_mask = consumption.index.month == month
            month_consumption = consumption[month_mask].sum()
            energy_cost += month_consumption * self.consumption_tax[month]

        return Money.nok(energy_cost)

    def calculate_demand_charge(self, peak_demand: Power, month: int) -> Money:
        """Calculate progressive bracket-based demand charge"""
        monthly_cost = 0.0
        remaining_demand = peak_demand.kw

        for bracket in self.power_brackets:
            if remaining_demand <= 0:
                break

            bracket_size = bracket['to_kw'] - bracket['from_kw']
            bracket_demand = min(remaining_demand, bracket_size)

            if bracket_demand > 0:
                monthly_cost += bracket_demand * bracket['rate']
                remaining_demand -= bracket_demand

        return Money.nok(monthly_cost)

    def calculate_total_cost(self, consumption: pd.Series, peaks: pd.Series) -> Money:
        """Calculate total annual cost"""
        # Energy charges
        energy_cost = self.calculate_energy_charge(consumption)

        # Demand charges (monthly)
        demand_cost = Money.nok(0)
        for month, peak_kw in peaks.items():
            monthly_demand = self.calculate_demand_charge(Power.from_kw(peak_kw), month)
            demand_cost += monthly_demand

        # Fixed charges
        fixed_cost = Money.nok(self.enova_fee_annual)

        return energy_cost + demand_cost + fixed_cost

    def get_marginal_demand_cost(self, current_peak: Power) -> float:
        """Get marginal cost of increasing peak by 1 kW"""
        # Find which bracket we're in
        for bracket in self.power_brackets:
            if bracket['from_kw'] <= current_peak.kw < bracket['to_kw']:
                return bracket['rate']

        return self.power_brackets[-1]['rate']  # Highest bracket


class TensioCommercialTariff(TariffStructure):
    """Tensio commercial tariff structure for Norway"""

    def __init__(self):
        # Seasonal time-of-use rates
        self.winter_peak_rate = 0.32  # Nov-Mar, Mon-Fri 06:00-21:00
        self.summer_peak_rate = 0.24  # Apr-Oct, Mon-Fri 06:00-21:00
        self.off_peak_rate = 0.18

        # Flat demand charge
        self.demand_rate_per_kw = 45  # NOK/kW/month

        # Winter months
        self.winter_months = [11, 12, 1, 2, 3]

    def calculate_energy_charge(self, consumption: pd.Series) -> Money:
        """Calculate seasonal time-of-use energy charges"""
        cost = 0.0

        for timestamp, kwh in consumption.items():
            hour = timestamp.hour
            month = timestamp.month
            weekday = timestamp.dayofweek

            # Check if peak hours (Mon-Fri 06:00-21:00)
            is_peak_hour = (6 <= hour < 21) and (weekday < 5)

            if is_peak_hour:
                if month in self.winter_months:
                    cost += kwh * self.winter_peak_rate
                else:
                    cost += kwh * self.summer_peak_rate
            else:
                cost += kwh * self.off_peak_rate

        return Money.nok(cost)

    def calculate_demand_charge(self, peak_demand: Power, month: int) -> Money:
        """Calculate flat rate demand charge"""
        return Money.nok(peak_demand.kw * self.demand_rate_per_kw)

    def calculate_total_cost(self, consumption: pd.Series, peaks: pd.Series) -> Money:
        """Calculate total cost"""
        energy_cost = self.calculate_energy_charge(consumption)

        # Average of three highest hours method
        demand_cost = Money.nok(0)
        for month, peak_values in peaks.groupby(peaks.index.month):
            # Get three highest hours
            top_three = peak_values.nlargest(3)
            average_peak = top_three.mean()
            demand_cost += self.calculate_demand_charge(Power.from_kw(average_peak), month)

        return energy_cost + demand_cost


class TariffComparator:
    """Compare different tariff structures"""

    def __init__(self, tariffs: Dict[str, TariffStructure]):
        self.tariffs = tariffs

    def compare(
        self,
        consumption: pd.Series,
        peaks: pd.Series
    ) -> pd.DataFrame:
        """Compare costs across all tariffs"""
        results = []

        for name, tariff in self.tariffs.items():
            total_cost = tariff.calculate_total_cost(consumption, peaks)
            energy_cost = tariff.calculate_energy_charge(consumption)

            # Calculate demand cost as difference
            demand_cost = total_cost.amount - energy_cost.amount

            results.append({
                'tariff': name,
                'total_cost_nok': total_cost.amount,
                'energy_cost_nok': energy_cost.amount,
                'demand_cost_nok': demand_cost,
                'avg_cost_per_kwh': total_cost.amount / consumption.sum()
            })

        return pd.DataFrame(results).sort_values('total_cost_nok')