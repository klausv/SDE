"""
Legacy config adapter for backward compatibility.

Creates legacy config objects from new SimulationConfig for use with
core/ optimizers that haven't been fully migrated yet.

This adapter provides a complete legacy config structure matching the
original config.py to ensure core/rolling_horizon_optimizer.py works.

REFACTORED: Now uses unified tariff configuration from infrastructure module.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, List
from src.config.simulation_config import SimulationConfig
from src.infrastructure.tariffs import TariffLoader, TariffProfile


@dataclass
class LocationConfig:
    """Geographic and site configuration (legacy)"""
    name: str = "Stavanger"
    latitude: float = 58.97
    longitude: float = 5.73
    timezone: str = "Europe/Oslo"


@dataclass
class SolarSystemConfig:
    """Solar PV system configuration (legacy)"""
    pv_capacity_kwp: float = 138.55
    inverter_capacity_kw: float = 110
    grid_connection_limit_kw: float = 70
    grid_import_limit_kw: float = 70  # Required by core/
    grid_export_limit_kw: float = 70  # Required by core/
    tilt_degrees: float = 30.0
    azimuth_degrees: float = 173.0
    inverter_efficiency: float = 0.98
    dc_to_ac_loss: float = 0.02


@dataclass
class ConsumptionConfig:
    """Load profile configuration (legacy)"""
    annual_kwh: float = 300000
    profile_type: str = "commercial"
    base_load_kw: float = 20.0
    peak_load_kw: float = 50.0

    # Consumption pattern parameters (for generated profiles)
    base_multiplier: float = 0.6
    weekday_business_multiplier: float = 1.8
    evening_multiplier: float = 1.3
    business_hours_start: int = 6
    business_hours_end: int = 18
    evening_hours_start: int = 18
    evening_hours_end: int = 22


@dataclass
class DegradationConfig:
    """LFP battery degradation modeling parameters (legacy)"""
    enabled: bool = False
    cycle_life_full_dod: int = 5000
    calendar_life_years: float = 28.0
    eol_degradation_percent: float = 20.0

    # Derived parameters
    rho_constant: float = field(init=False)
    dp_cal_per_hour: float = field(init=False)

    def __post_init__(self):
        """Calculate derived degradation parameters."""
        self.rho_constant = self.eol_degradation_percent / self.cycle_life_full_dod
        hours_per_lifetime = self.calendar_life_years * 365 * 24
        self.dp_cal_per_hour = self.eol_degradation_percent / hours_per_lifetime


@dataclass
class BatteryConfig:
    """Battery system configuration (legacy)"""
    capacity_kwh: float
    power_kw: float

    # Efficiency parameters
    efficiency: float = 0.90
    efficiency_roundtrip: float = 0.90

    # SOC limits (both percent and fractional for compatibility)
    initial_soc_percent: float = 50.0
    min_soc_percent: float = 10.0
    max_soc_percent: float = 90.0
    min_soc: float = 0.10  # Fractional (0-1)
    max_soc: float = 0.90  # Fractional (0-1)

    # C-rate limits
    max_c_rate_charge: float = 1.0
    max_c_rate_discharge: float = 1.0

    # Cost parameters
    battery_cell_cost_nok_per_kwh: float = 3054
    inverter_cost_nok_per_kw: float = 1324.2
    inverter_reference_power_kw: float = 30.0
    control_system_cost_nok: float = 1680
    market_cost_nok_per_kwh: float = 5000
    target_cost_nok_per_kwh: float = 2500
    cost_per_kwh: float = 5000.0  # Alias for compatibility
    cost_per_kw: float = 1000.0

    # Lifetime
    degradation_rate_yearly: float = 0.02
    lifetime_years: int = 15

    # Nested degradation config
    degradation: DegradationConfig = field(default_factory=DegradationConfig)

    def get_total_battery_system_cost(self, battery_kwh: float, battery_kw: float) -> float:
        """Calculate total battery system cost."""
        cell_cost = battery_kwh * self.battery_cell_cost_nok_per_kwh
        inverter_cost = battery_kw * self.inverter_cost_nok_per_kw
        control_cost = self.control_system_cost_nok
        return cell_cost + inverter_cost + control_cost


@dataclass
class GridTariffConfig:
    """Grid tariff structure (legacy) - REFACTORED to use 2024 tariffs"""
    variable_nok_per_kwh: float = 0.25
    fixed_nok_per_month: float = 500.0

    # Load default 2024 tariff from infrastructure
    _tariff: TariffProfile = field(default_factory=TariffLoader.get_default_tariff, init=False, repr=False)

    # Energy tariffs (required by core/ optimizer) - from YAML config
    @property
    def energy_peak(self) -> float:
        """Mon-Fri 06:00-22:00 (NOK/kWh)"""
        return self._tariff.energy.peak_rate

    @property
    def energy_offpeak(self) -> float:
        """Nights/weekends (NOK/kWh)"""
        return self._tariff.energy.offpeak_rate

    # Power tariff brackets (from, to, cost_per_month) - UPDATED to 2024 tariffs from YAML
    @property
    def power_brackets(self) -> List[Tuple[float, float, float]]:
        """2024 Lnett commercial power tariff brackets"""
        return [
            (bracket.min_kw, bracket.max_kw, bracket.cost_nok_month)
            for bracket in self._tariff.power.brackets
        ]

    # DEPRECATED: Legacy format for backward compatibility (2023 tariffs - DO NOT USE)
    # These are kept only for backward compatibility with old code
    # Use power_brackets property instead (2024 tariffs from YAML)
    power_bracket_widths_kw: Tuple[float, ...] = (50, 50, 50, 100, 100)
    power_bracket_costs_nok: Tuple[float, ...] = (48, 52, 63, 121, 213)

    def is_peak_hours(self, timestamp) -> bool:
        """Check if timestamp is in peak hours (Mon-Fri 06:00-22:00)."""
        return (timestamp.weekday() < 5 and  # Monday-Friday
                6 <= timestamp.hour < 22)  # 06:00-22:00

    def get_power_cost(self, peak_kw: float) -> float:
        """
        Calculate monthly power tariff for given peak demand.
        This is the CORRECT Lnett calculation - you ONLY pay for the bracket your peak falls in.

        Example with 2024 tariffs: 30 kW peak costs:
        - Falls in 25-50 kW bracket → 1772 NOK/month

        NOT progressive - you don't pay for all lower brackets!

        Now uses 2024 tariffs from YAML configuration.
        """
        # Use tariff loader for correct 2024 calculation
        return self._tariff.get_power_tariff(peak_kw)

    # Alias for backward compatibility
    def get_progressive_power_cost(self, peak_kw: float) -> float:
        """Deprecated - use get_power_cost instead"""
        return self.get_power_cost(peak_kw)


@dataclass
class EconomicConfig:
    """Economic analysis parameters (legacy)"""
    project_lifetime_years: int = 15
    discount_rate: float = 0.05
    inflation_rate: float = 0.02
    eur_to_nok: float = 11.5


@dataclass
class LegacySystemConfig:
    """Legacy config object for backward compatibility with core/ optimizers."""

    location: LocationConfig
    solar: SolarSystemConfig
    consumption: ConsumptionConfig
    degradation: DegradationConfig
    battery: BatteryConfig
    tariff: GridTariffConfig
    economic: EconomicConfig

    # Top-level shortcuts for core/ optimizers
    @property
    def battery_capacity_kwh(self) -> float:
        return self.battery.capacity_kwh

    @property
    def battery_power_kw(self) -> float:
        return self.battery.power_kw


def create_legacy_config(sim_config: SimulationConfig) -> LegacySystemConfig:
    """
    Create legacy config object from new SimulationConfig.

    Args:
        sim_config: New simulation configuration

    Returns:
        Legacy config object compatible with core/ optimizers
    """
    # Create battery config with degradation
    battery_config = BatteryConfig(
        capacity_kwh=sim_config.battery.capacity_kwh,
        power_kw=sim_config.battery.power_kw,
        efficiency=sim_config.battery.efficiency,
        efficiency_roundtrip=sim_config.battery.efficiency,
        initial_soc_percent=sim_config.battery.initial_soc_percent,
        min_soc_percent=sim_config.battery.min_soc_percent,
        max_soc_percent=sim_config.battery.max_soc_percent,
        min_soc=sim_config.battery.min_soc_percent / 100.0,
        max_soc=sim_config.battery.max_soc_percent / 100.0,
        degradation=DegradationConfig(),  # Use defaults for now
    )

    # Create legacy config with all nested components
    legacy_config = LegacySystemConfig(
        location=LocationConfig(),
        solar=SolarSystemConfig(),
        consumption=ConsumptionConfig(),
        degradation=DegradationConfig(),
        battery=battery_config,
        tariff=GridTariffConfig(),
        economic=EconomicConfig(),
    )

    return legacy_config


# Global config instance for modules that import "config"
_global_legacy_config: LegacySystemConfig = None


def get_global_legacy_config() -> LegacySystemConfig:
    """
    Get or create global legacy config.

    Returns default legacy config if not explicitly set.
    """
    global _global_legacy_config
    if _global_legacy_config is None:
        # Create default legacy config
        _global_legacy_config = LegacySystemConfig(
            location=LocationConfig(),
            solar=SolarSystemConfig(),
            consumption=ConsumptionConfig(),
            degradation=DegradationConfig(),
            battery=BatteryConfig(
                capacity_kwh=80.0,  # Default
                power_kw=60.0,  # Default
            ),
            tariff=GridTariffConfig(),
            economic=EconomicConfig(),
        )
    return _global_legacy_config


def set_global_legacy_config(sim_config: SimulationConfig) -> None:
    """
    Set global legacy config from SimulationConfig.

    Args:
        sim_config: Simulation configuration to convert
    """
    global _global_legacy_config
    _global_legacy_config = create_legacy_config(sim_config)


# Alias for backward compatibility
config = get_global_legacy_config()


def generate_consumption_profile(
    timestamps: "pd.DatetimeIndex",
    consumption_config: ConsumptionConfig
) -> "np.ndarray":
    """
    Generate consumption profile from pattern parameters.

    Creates a commercial consumption profile based on time-of-day patterns:
    - Base load (60% of average)
    - Weekday business hours (180% of base)
    - Evening hours (130% of base)

    Args:
        timestamps: DatetimeIndex for which to generate consumption
        consumption_config: ConsumptionConfig with annual_kwh and pattern parameters

    Returns:
        Array of consumption values in kW matching timestamps length
    """
    import numpy as np

    hours_per_year = 8760
    avg_load = consumption_config.annual_kwh / hours_per_year
    load = np.zeros(len(timestamps))

    for i, ts in enumerate(timestamps):
        base = avg_load * consumption_config.base_multiplier

        # Weekday business hours
        if (ts.weekday() < 5 and
            consumption_config.business_hours_start <= ts.hour < consumption_config.business_hours_end):
            load[i] = base * consumption_config.weekday_business_multiplier

        # Evening hours
        elif (consumption_config.evening_hours_start <= ts.hour < consumption_config.evening_hours_end):
            load[i] = base * consumption_config.evening_multiplier

        # Off-peak hours
        else:
            load[i] = base

    return load
