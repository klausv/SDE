"""
Configuration management for battery optimization system
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import os

class ConfigLoader:
    """Load and validate configuration files"""

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path(__file__).parent
        self.config_dir = Path(config_dir)

    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load a YAML configuration file"""
        filepath = self.config_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        with open(filepath, 'r') as f:
            return yaml.safe_load(f)

    def load_all_configs(self) -> Dict[str, Dict]:
        """Load all configuration files"""
        return {
            'site': self.load_yaml('site_config.yaml'),
            'system': self.load_yaml('system_config.yaml'),
            'economic': self.load_yaml('economic_config.yaml'),
            'optimization': self.load_yaml('optimization_config.yaml'),
            'tariff': self.load_yaml('tariff_config.yaml')
        }


@dataclass
class SiteConfig:
    """Site configuration with validation"""
    name: str
    latitude: float
    longitude: float
    altitude: float
    timezone: str
    grid_max_import_kw: float
    grid_max_export_kw: float
    annual_consumption_kwh: float
    profile_type: str = "commercial"

    @classmethod
    def from_yaml(cls, yaml_dict: Dict[str, Any]) -> 'SiteConfig':
        """Create from YAML dictionary"""
        site = yaml_dict['site']
        location = yaml_dict['location']
        grid = yaml_dict['grid_connection']
        consumption = yaml_dict['consumption_profile']

        return cls(
            name=site['name'],
            latitude=location['latitude'],
            longitude=location['longitude'],
            altitude=location['altitude'],
            timezone=location['timezone'],
            grid_max_import_kw=grid['max_import_kw'],
            grid_max_export_kw=grid['max_export_kw'],
            annual_consumption_kwh=consumption['annual_consumption_kwh'],
            profile_type=consumption.get('profile_type', 'commercial')
        )

    def validate(self):
        """Validate configuration values"""
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Invalid longitude: {self.longitude}")
        if self.grid_max_import_kw <= 0:
            raise ValueError("Grid import capacity must be positive")
        if self.annual_consumption_kwh <= 0:
            raise ValueError("Annual consumption must be positive")


@dataclass
class SystemConfig:
    """Solar system configuration"""
    installed_capacity_kwp: float
    inverter_capacity_kw: float
    azimuth: float
    tilt: float
    losses: Dict[str, float]

    @classmethod
    def from_yaml(cls, yaml_dict: Dict[str, Any]) -> 'SystemConfig':
        """Create from YAML dictionary"""
        solar = yaml_dict['solar_system']
        losses = yaml_dict['losses']

        return cls(
            installed_capacity_kwp=solar['installed_capacity_kwp'],
            inverter_capacity_kw=solar['inverter_capacity_kw'],
            azimuth=solar['azimuth'],
            tilt=solar['tilt'],
            losses=losses
        )

    def get_total_losses(self) -> float:
        """Calculate total system losses"""
        # Multiplicative losses
        dc_losses = ['soiling', 'shading', 'snow', 'mismatch', 'wiring_dc']
        ac_losses = ['wiring_ac', 'transformer', 'availability']

        total_efficiency = 1.0

        for loss_type in dc_losses + ac_losses:
            if loss_type in self.losses:
                total_efficiency *= (1 - self.losses[loss_type])

        # Inverter efficiency is already a factor, not a loss
        if 'inverter_efficiency' in self.losses:
            total_efficiency *= self.losses['inverter_efficiency']

        return 1 - total_efficiency


@dataclass
class BatteryDecisionVariables:
    """Battery optimization decision variables"""
    capacity_kwh_min: float
    capacity_kwh_max: float
    capacity_kwh_step: float
    power_kw_min: float
    power_kw_max: float
    power_kw_step: float
    cost_scenarios: Dict[str, float]

    @classmethod
    def from_yaml(cls, yaml_dict: Dict[str, Any]) -> 'BatteryDecisionVariables':
        """Create from YAML dictionary"""
        dv = yaml_dict['decision_variables']

        return cls(
            capacity_kwh_min=dv['battery_capacity_kwh']['min'],
            capacity_kwh_max=dv['battery_capacity_kwh']['max'],
            capacity_kwh_step=dv['battery_capacity_kwh']['step'],
            power_kw_min=dv['battery_power_kw']['min'],
            power_kw_max=dv['battery_power_kw']['max'],
            power_kw_step=dv['battery_power_kw']['step'],
            cost_scenarios=dv['battery_cost_nok_per_kwh']['scenarios']
        )

    def get_capacity_range(self):
        """Get range of capacity values to test"""
        import numpy as np
        return np.arange(
            self.capacity_kwh_min,
            self.capacity_kwh_max + self.capacity_kwh_step,
            self.capacity_kwh_step
        )

    def get_power_range(self):
        """Get range of power values to test"""
        import numpy as np
        return np.arange(
            self.power_kw_min,
            self.power_kw_max + self.power_kw_step,
            self.power_kw_step
        )


@dataclass
class EconomicConfig:
    """Economic parameters configuration"""
    discount_rate: float
    project_lifetime_years: int
    electricity_price_inflation: float
    battery_cost_default: float
    min_irr: float
    max_payback_years: float
    battery_efficiency: float
    battery_degradation_annual: float

    @classmethod
    def from_yaml(cls, yaml_dict: Dict[str, Any]) -> 'EconomicConfig':
        """Create from YAML dictionary"""
        financial = yaml_dict['financial']
        battery = yaml_dict['battery']
        constraints = yaml_dict['constraints']
        dv = yaml_dict['decision_variables']

        return cls(
            discount_rate=financial['discount_rate'],
            project_lifetime_years=financial['project_lifetime_years'],
            electricity_price_inflation=financial['electricity_price_inflation'],
            battery_cost_default=dv['battery_cost_nok_per_kwh']['default'],
            min_irr=constraints['min_irr'],
            max_payback_years=constraints['max_payback_years'],
            battery_efficiency=battery['round_trip_efficiency'],
            battery_degradation_annual=battery['degradation']['calendar_degradation']
        )


class ConfigurationManager:
    """Central configuration management"""

    def __init__(self, config_dir: Optional[Path] = None):
        self.loader = ConfigLoader(config_dir)
        self._configs = None
        self._site_config = None
        self._system_config = None
        self._economic_config = None
        self._decision_variables = None

    def load(self):
        """Load all configurations"""
        self._configs = self.loader.load_all_configs()
        self._site_config = SiteConfig.from_yaml(self._configs['site'])
        self._system_config = SystemConfig.from_yaml(self._configs['system'])
        self._economic_config = EconomicConfig.from_yaml(self._configs['economic'])
        self._decision_variables = BatteryDecisionVariables.from_yaml(self._configs['economic'])

        # Validate
        self._site_config.validate()

        return self

    @property
    def site(self) -> SiteConfig:
        if self._site_config is None:
            self.load()
        return self._site_config

    @property
    def system(self) -> SystemConfig:
        if self._system_config is None:
            self.load()
        return self._system_config

    @property
    def economic(self) -> EconomicConfig:
        if self._economic_config is None:
            self.load()
        return self._economic_config

    @property
    def decision_variables(self) -> BatteryDecisionVariables:
        if self._decision_variables is None:
            self.load()
        return self._decision_variables

    @property
    def tariff(self) -> Dict[str, Any]:
        if self._configs is None:
            self.load()
        return self._configs['tariff']

    @property
    def optimization(self) -> Dict[str, Any]:
        if self._configs is None:
            self.load()
        return self._configs['optimization']

    def get_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """Get a specific optimization scenario"""
        scenarios = self.optimization['scenarios']
        for scenario in scenarios:
            if scenario['name'] == scenario_name:
                return scenario
        raise ValueError(f"Scenario not found: {scenario_name}")

    def override_with_scenario(self, scenario_name: str):
        """Apply scenario overrides to configuration"""
        scenario = self.get_scenario(scenario_name)
        overrides = scenario.get('overrides', {})

        # Apply overrides
        for key, value in overrides.items():
            if hasattr(self._economic_config, key):
                setattr(self._economic_config, key, value)
            elif hasattr(self._decision_variables, key):
                setattr(self._decision_variables, key, value)

        return self