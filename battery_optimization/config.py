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
    inverter_capacity_kw: float = 110  # AC capacity (GROWATT MAX 110KTL3)
    grid_connection_limit_kw: float = 70  # Nettilkobling - symmetrisk grense
    grid_import_limit_kw: float = 70  # Import begrenset av nettilkobling
    grid_export_limit_kw: float = 70  # Export begrenset av nettilkobling
    tilt_degrees: float = 30.0  # Faktisk takhelning Snødevegen
    azimuth_degrees: float = 173.0  # South
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
class DegradationConfig:
    """LFP battery degradation modeling parameters (Korpås model)"""

    # Enable/disable degradation modeling in LP optimization
    enabled: bool = False

    # LFP-specific parameters (based on Skanbatt ESS specifications)
    # NOTE: These are TECHNICAL lifetimes (to 80% SOH), not economic lifetimes
    cycle_life_full_dod: int = 5000          # Cycles at 100% DOD until 80% SOH (technical)
    calendar_life_years: float = 28.0        # Years until 80% SOH from calendar aging only (technical)

    # End-of-life degradation threshold (80% SOH = 20% capacity loss)
    eol_degradation_percent: float = 20.0    # Battery unusable after 20% degradation

    # Derived parameters (computed in __post_init__)
    rho_constant: float = field(init=False)         # %/cycle constant (cyclic degradation rate)
    dp_cal_per_hour: float = field(init=False)      # %/hour (calendric degradation rate)

    def __post_init__(self):
        """Calculate derived degradation parameters for LP formulation

        IMPORTANT: Degradation is measured as percentage loss of capacity.
        At 20% degradation, the battery has 80% SOH (State of Health).

        Technical lifetime definitions:
        - cycle_life_full_dod: Number of 100% DOD cycles to reach 20% degradation
        - calendar_life_years: Years to reach 20% degradation from calendar aging alone
        """
        # Cyclic degradation rate: constant for LFP (simpler than NMC piecewise)
        # 5000 cycles causes 20% degradation → 0.004% per full cycle
        self.rho_constant = self.eol_degradation_percent / self.cycle_life_full_dod

        # Calendric degradation per hour
        # 28 years causes 20% degradation → 0.000081% per hour
        hours_per_lifetime = self.calendar_life_years * 365 * 24
        self.dp_cal_per_hour = self.eol_degradation_percent / hours_per_lifetime


@dataclass
class BatteryConfig:
    """Battery system parameters"""
    efficiency_roundtrip: float = 0.90
    min_soc: float = 0.10
    max_soc: float = 0.90
    max_c_rate_charge: float = 1.0
    max_c_rate_discharge: float = 1.0
    degradation_rate_yearly: float = 0.02  # Simple annual degradation (for backward compatibility)
    lifetime_years: int = 15  # ECONOMIC lifetime for NPV analysis (not technical lifetime!)

    # COST SEPARATION (critical for proper degradation modeling)
    # Battery cell cost ONLY (used for degradation calculation in LP)
    # Based on Skanbatt ESS Rack 48V 30.72kWh: 93,800 NOK / 30.72 kWh = 3,054 NOK/kWh
    battery_cell_cost_nok_per_kwh: float = 3054

    # Fixed system component costs (independent of battery size)
    inverter_cost_nok: float = 39726  # Victron Multiplus-II 5kVA × 6 units
    control_system_cost_nok: float = 1680  # Cerbo GX control system

    # Legacy cost scenarios (for comparison/backward compatibility)
    market_cost_nok_per_kwh: float = 5000
    target_cost_nok_per_kwh: float = 2500

    # Degradation modeling configuration
    degradation: DegradationConfig = field(default_factory=DegradationConfig)

    def get_system_cost_per_kwh(self, battery_kwh: float) -> float:
        """
        Calculate total system cost per kWh (for break-even analysis).

        System cost = Battery cells + Inverter + Control system

        This is the cost used for economic analysis and break-even calculations,
        as it represents the total investment required per kWh of storage.

        Args:
            battery_kwh: Battery capacity [kWh]

        Returns:
            System cost [NOK/kWh] including all components

        Examples:
            30.72 kWh battery (Skanbatt reference):
            (3054 × 30.72 + 39726 + 1680) / 30.72 = 4,404 NOK/kWh

            100 kWh battery:
            (3054 × 100 + 39726 + 1680) / 100 = 3,468 NOK/kWh

            Note: Larger batteries have lower cost/kWh because fixed costs
                  (inverter + control) are amortized over more capacity.
        """
        battery_cell_cost_total = self.battery_cell_cost_nok_per_kwh * battery_kwh
        total_system_cost = battery_cell_cost_total + self.inverter_cost_nok + self.control_system_cost_nok
        return total_system_cost / battery_kwh

    def get_battery_cost(self) -> float:
        """
        Get battery cell cost for degradation modeling [NOK/kWh].

        This cost excludes inverter and control systems, as degradation
        only affects the battery cells themselves.

        Returns:
            Battery cell cost [NOK/kWh]
        """
        return self.battery_cell_cost_nok_per_kwh


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
    # Time resolution for optimization
    resolution: str = 'PT60M'  # 'PT60M' (hourly) or 'PT15M' (15-minute)

    # Analysis options
    include_sensitivity: bool = False
    sensitivity_range: Tuple[float, float] = (2000, 6000)  # Battery cost range
    output_format: str = "full"

    # Caching
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

            # Map YAML keys to dataclass fields (handle naming differences)
            site_data = data.get('site', {})
            solar_data = data.get('solar', {})
            consumption_data = data.get('consumption', {})
            battery_data = data.get('battery', {})
            economics_data = data.get('economics', {})
            analysis_data = data.get('analysis', {})

            # Handle solar config naming differences
            if 'inverter_limit_kw' in solar_data:
                solar_data['inverter_capacity_kw'] = solar_data.pop('inverter_limit_kw')

            # Handle battery naming differences (degradation_rate in YAML, degradation_rate_yearly in code)
            if 'degradation_rate' in economics_data:
                battery_data['degradation_rate_yearly'] = economics_data['degradation_rate']
            if 'project_years' in economics_data:
                battery_data['lifetime_years'] = economics_data['project_years']

            # Create config objects from YAML data
            return cls(
                location=LocationConfig(
                    name=site_data.get('location', LocationConfig.name),
                    latitude=site_data.get('latitude', LocationConfig.latitude),
                    longitude=site_data.get('longitude', LocationConfig.longitude),
                ),
                solar=SolarSystemConfig(**{k: v for k, v in solar_data.items()
                                           if k in SolarSystemConfig.__dataclass_fields__}),
                consumption=ConsumptionConfig(
                    annual_kwh=consumption_data.get('annual_kwh', ConsumptionConfig.annual_kwh),
                    profile_type=consumption_data.get('profile_type', ConsumptionConfig.profile_type),
                ),
                battery=BatteryConfig(**{k: v for k, v in battery_data.items()
                                        if k in BatteryConfig.__dataclass_fields__}),
                economics=EconomicConfig(
                    discount_rate=economics_data.get('discount_rate', EconomicConfig.discount_rate),
                    project_lifetime_years=economics_data.get('project_years', EconomicConfig.project_lifetime_years),
                ),
                analysis=AnalysisConfig(**{k: v for k, v in analysis_data.items()
                                          if k in AnalysisConfig.__dataclass_fields__}),
            )
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


# Global configuration instance - loads from config.yaml
config = BatteryOptimizationConfig.from_yaml()

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