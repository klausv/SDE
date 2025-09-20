"""
Configuration for battery optimization analysis
All prices in NOK, power in kW, energy in kWh
"""
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime

@dataclass
class SystemConfig:
    """PV system configuration"""
    pv_capacity_kwp: float = 150.0
    inverter_capacity_kw: float = 110.0
    grid_capacity_kw: float = 77.0  # 70% of inverter
    location_lat: float = 58.97
    location_lon: float = 5.73
    tilt: float = 25.0  # degrees
    azimuth: float = 180.0  # South facing

@dataclass
class LnettTariff:
    """Lnett tariff structure for commercial customers < 100 MWh/year"""

    # Energy charges (øre/kWh -> kr/kWh)
    energy_day: float = 0.296  # Mon-Fri 06:00-22:00
    energy_night_weekend: float = 0.176  # Mon-Fri 22:00-06:00 + weekends

    # Power tariff brackets (kr/month per bracket)
    power_tariff_brackets: Dict[tuple, float] = None

    # Consumption tax by month (øre/kWh -> kr/kWh)
    consumption_tax: Dict[int, float] = None

    # Enova fee (kr/year)
    enova_fee: float = 800.0

    def __post_init__(self):
        if self.power_tariff_brackets is None:
            self.power_tariff_brackets = {
                (0, 2): 136,
                (2, 5): 232,
                (5, 10): 372,
                (10, 15): 572,
                (15, 20): 772,
                (20, 25): 972,
                (25, 50): 1772,
                (50, 75): 2572,
                (75, 100): 3372,
                (100, float('inf')): 5600
            }

        if self.consumption_tax is None:
            # Month -> tax in kr/kWh
            self.consumption_tax = {
                1: 0.0979, 2: 0.0979, 3: 0.0979,  # Jan-Mar
                4: 0.1693, 5: 0.1693, 6: 0.1693,  # Apr-Jun
                7: 0.1693, 8: 0.1693, 9: 0.1693,  # Jul-Sep
                10: 0.1253, 11: 0.1253, 12: 0.1253  # Oct-Dec
            }

    def get_power_tariff(self, peak_kw: float) -> float:
        """Get monthly power tariff based on peak demand"""
        for (lower, upper), cost in self.power_tariff_brackets.items():
            if lower <= peak_kw < upper:
                return cost
        return 5600  # Max bracket

    def is_peak_hours(self, timestamp: datetime) -> bool:
        """Check if timestamp is during peak hours"""
        if timestamp.weekday() >= 5:  # Weekend
            return False
        hour = timestamp.hour
        return 6 <= hour < 22

@dataclass
class BatteryConfig:
    """Battery system configuration"""
    min_soc: float = 0.1  # Minimum state of charge (10%)
    max_soc: float = 0.9  # Maximum state of charge (90%)
    round_trip_efficiency: float = 0.90  # 90% round-trip efficiency
    max_c_rate_charge: float = 1.0  # Maximum charge rate (1C)
    max_c_rate_discharge: float = 1.0  # Maximum discharge rate (1C)
    degradation_rate_yearly: float = 0.02  # 2% capacity loss per year

@dataclass
class EconomicConfig:
    """Economic parameters"""
    discount_rate: float = 0.05  # 5% annual discount rate
    battery_lifetime_years: int = 15
    eur_to_nok: float = 11.5  # EUR to NOK exchange rate

    # VAT
    vat_rate: float = 0.25  # 25% MVA

# Create default configurations
system_config = SystemConfig()
lnett_tariff = LnettTariff()
battery_config = BatteryConfig()
economic_config = EconomicConfig()