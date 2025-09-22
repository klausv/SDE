"""
Centralized configuration for battery optimization project.
All system parameters, tariffs, and economic assumptions in one place.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, List
from datetime import datetime
import yaml
from pathlib import Path


@dataclass
class LocationConfig:
    """Geographic and site configuration"""
    name: str = "Stavanger"
    latitude: float = 58.97
    longitude: float = 5.73
    timezone: str = "Europe/Oslo"


@dataclass
class SolarSystemConfig:
    """Solar PV system configuration"""
    # Standardized values based on PVGIS and actual system
    pv_capacity_kwp: float = 138.55  # DC capacity from PVGIS
    inverter_capacity_kw: float = 100  # AC capacity (GROWATT MAX 100KTL3)
    grid_export_limit_kw: float = 77  # 70% of inverter (safety margin)
    tilt_degrees: float = 30.0  # Faktisk takhelning Snødevegen
    azimuth_degrees: float = 180.0  # Due south
    inverter_efficiency: float = 0.98
    dc_to_ac_loss: float = 0.02  # 2% conversion loss


@dataclass
class ConsumptionConfig:
    """Load profile configuration"""
    annual_kwh: float = 300000  # Commercial scale consumption
    profile_type: str = "commercial"
    base_load_kw: float = 20.0
    peak_load_kw: float = 50.0


@dataclass
class BatteryConfig:
    """Battery system parameters"""
    efficiency_roundtrip: float = 0.90
    min_soc: float = 0.10
    max_soc: float = 0.90
    max_c_rate_charge: float = 1.0
    max_c_rate_discharge: float = 1.0
    degradation_rate_yearly: float = 0.02
    lifetime_years: int = 15
    # Cost scenarios
    market_cost_nok_per_kwh: float = 5000
    target_cost_nok_per_kwh: float = 2500


@dataclass
class TariffConfig:
    """Lnett grid tariff structure"""

    # Energy charges (NOK/kWh) - Lnett commercial tariff
    energy_peak: float = 0.296  # Mon-Fri 06:00-22:00
    energy_offpeak: float = 0.176  # Nights/weekends
    energy_tariff: float = 0.054  # Grid energy component

    # NON-PROGRESSIVE Power tariff brackets: (lower_kw, upper_kw, cost_nok_month)
    # IMPORTANT: This is a bracket tariff - you ONLY pay for the bracket your peak falls in!
    power_brackets: List[Tuple[float, float, float]] = field(default_factory=lambda: [
        (0, 2, 136),           # 136 kr/måned for 0-2 kW
        (2, 5, 232),           # 232 kr/måned for 2-5 kW
        (5, 10, 372),          # 372 kr/måned for 5-10 kW
        (10, 15, 572),         # 572 kr/måned for 10-15 kW
        (15, 20, 772),         # 772 kr/måned for 15-20 kW
        (20, 25, 972),         # 972 kr/måned for 20-25 kW
        (25, 50, 1772),        # 1772 kr/måned for 25-50 kW
        (50, 75, 2572),        # 2572 kr/måned for 50-75 kW
        (75, 100, 3372),       # 3372 kr/måned for 75-100 kW
        (100, float('inf'), 5600)  # 5600 kr/måned for >100 kW
    ])

    # Consumption tax by month (NOK/kWh) - 2024 rates
    consumption_tax_monthly: Dict[int, float] = field(default_factory=lambda: {
        1: 0.0979, 2: 0.0979, 3: 0.0979,    # Jan-Mar (winter low)
        4: 0.1693, 5: 0.1693, 6: 0.1693,    # Apr-Jun (spring high)
        7: 0.1693, 8: 0.1693, 9: 0.1693,    # Jul-Sep (summer high)
        10: 0.1253, 11: 0.1253, 12: 0.1253  # Oct-Dec (autumn medium)
    })

    enova_fee_yearly: float = 800.0  # Annual Enova fee

    def get_power_cost(self, peak_kw: float) -> float:
        """
        Calculate monthly power tariff for given peak demand.
        This is the CORRECT Lnett calculation - you ONLY pay for the bracket your peak falls in.

        Example: 30 kW peak costs:
        - Falls in 25-50 kW bracket → 1772 NOK/month

        NOT progressive - you don't pay for all lower brackets!
        """
        for from_kw, to_kw, cost_per_month in self.power_brackets:
            if from_kw <= peak_kw < to_kw:
                return cost_per_month

        # If above 100 kW, return the flat fee
        return self.power_brackets[-1][2]

    # Alias for backward compatibility
    def get_progressive_power_cost(self, peak_kw: float) -> float:
        """Deprecated - use get_power_cost instead"""
        return self.get_power_cost(peak_kw)

    def get_simple_power_cost(self, peak_kw: float) -> float:
        """Deprecated - use get_power_cost instead"""
        return self.get_power_cost(peak_kw)

    def is_peak_hours(self, timestamp: datetime) -> bool:
        """Check if timestamp is during peak tariff hours"""
        if timestamp.weekday() >= 5:  # Weekend (Saturday=5, Sunday=6)
            return False
        return 6 <= timestamp.hour < 22  # Peak hours 06:00-22:00


@dataclass
class EconomicConfig:
    """Economic analysis parameters"""
    discount_rate: float = 0.05
    eur_to_nok: float = 11.5
    vat_rate: float = 0.25
    installation_markup: float = 0.25

    # Spot price assumptions
    spot_price_avg_2024: float = 0.85  # NOK/kWh average for NO2

    # Analysis parameters
    project_lifetime_years: int = 15
    include_degradation: bool = True


@dataclass
class AnalysisConfig:
    """Analysis and simulation settings"""
    include_sensitivity: bool = False
    sensitivity_range: Tuple[float, float] = (2000, 6000)  # Battery cost range
    output_format: str = "full"
    cache_data: bool = True
    use_cached_prices: bool = True
    use_cached_pvgis: bool = True


@dataclass
class BatteryOptimizationConfig:
    """Complete system configuration"""
    location: LocationConfig = field(default_factory=LocationConfig)
    solar: SolarSystemConfig = field(default_factory=SolarSystemConfig)
    consumption: ConsumptionConfig = field(default_factory=ConsumptionConfig)
    battery: BatteryConfig = field(default_factory=BatteryConfig)
    tariff: TariffConfig = field(default_factory=TariffConfig)
    economics: EconomicConfig = field(default_factory=EconomicConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)

    @classmethod
    def from_yaml(cls, yaml_path: str = "config.yaml"):
        """Load configuration from YAML file"""
        config_file = Path(__file__).parent / yaml_path
        if config_file.exists():
            with open(config_file, 'r') as f:
                data = yaml.safe_load(f)
            # TODO: Implement proper YAML to dataclass conversion
            # For now, just return default config
            return cls()
        return cls()

    def to_dict(self) -> dict:
        """Convert configuration to dictionary"""
        # Simple conversion for now
        return {
            'location': self.location.__dict__,
            'solar': self.solar.__dict__,
            'consumption': self.consumption.__dict__,
            'battery': self.battery.__dict__,
            'tariff': {k: v for k, v in self.tariff.__dict__.items()
                      if not k.startswith('_')},
            'economics': self.economics.__dict__,
            'analysis': self.analysis.__dict__
        }


# Global configuration instance
config = BatteryOptimizationConfig()

# Backward compatibility aliases (for gradual migration)
system_config = config.solar
lnett_tariff = config.tariff
battery_config = config.battery
economic_config = config.economics

# Export commonly used values directly for easier access
POWER_TARIFF = config.tariff.power_brackets
CONSUMPTION_TAX = config.tariff.consumption_tax_monthly


def get_power_tariff(peak_kw: float) -> float:
    """
    Progressive power tariff calculation.
    Backward compatibility function using the centralized config.
    """
    return config.tariff.get_progressive_power_cost(peak_kw)


if __name__ == "__main__":
    # Test configuration
    print("Battery Optimization Configuration")
    print("=" * 50)
    print(f"PV Capacity: {config.solar.pv_capacity_kwp} kWp")
    print(f"Inverter: {config.solar.inverter_capacity_kw} kW")
    print(f"Grid Limit: {config.solar.grid_export_limit_kw} kW")
    print(f"Battery Cost (market): {config.battery.market_cost_nok_per_kwh} NOK/kWh")
    print(f"Battery Cost (target): {config.battery.target_cost_nok_per_kwh} NOK/kWh")

    # Test progressive tariff calculation
    print("\nProgressive Power Tariff Examples:")
    for peak in [10, 30, 50, 100, 150]:
        cost = config.tariff.get_progressive_power_cost(peak)
        print(f"  {peak:3d} kW: {cost:8,.0f} NOK/month")