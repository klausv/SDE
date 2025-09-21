"""
Solar PV system domain model with production calculations
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd
from datetime import datetime

from domain.value_objects.energy import Energy, Power, EnergyTimeSeries
from domain.value_objects.money import Money, CostPerUnit


@dataclass
class PVSystemSpecification:
    """Immutable PV system specifications"""
    installed_capacity: Power  # DC capacity (kWp)
    inverter_capacity: Power   # AC capacity (kW)
    azimuth: float = 180.0    # Degrees from north (180 = south)
    tilt: float = 30.0        # Degrees from horizontal

    # System losses
    soiling_loss: float = 0.02
    shading_loss: float = 0.03
    snow_loss: float = 0.00
    mismatch_loss: float = 0.02
    wiring_dc_loss: float = 0.02
    wiring_ac_loss: float = 0.01
    transformer_loss: float = 0.00
    availability_loss: float = 0.03
    inverter_efficiency: float = 0.97

    def __post_init__(self):
        """Validate specifications"""
        if self.installed_capacity.kw <= 0:
            raise ValueError(f"Installed capacity must be positive: {self.installed_capacity.kw}")
        if self.inverter_capacity.kw <= 0:
            raise ValueError(f"Inverter capacity must be positive: {self.inverter_capacity.kw}")
        if not 0 <= self.azimuth <= 360:
            raise ValueError(f"Azimuth must be between 0 and 360: {self.azimuth}")
        if not 0 <= self.tilt <= 90:
            raise ValueError(f"Tilt must be between 0 and 90: {self.tilt}")

    @property
    def dc_ac_ratio(self) -> float:
        """Get DC/AC ratio (oversizing factor)"""
        return self.installed_capacity.kw / self.inverter_capacity.kw

    @property
    def total_system_efficiency(self) -> float:
        """Calculate total system efficiency from all loss factors"""
        # DC losses (before inverter)
        dc_efficiency = (
            (1 - self.soiling_loss) *
            (1 - self.shading_loss) *
            (1 - self.snow_loss) *
            (1 - self.mismatch_loss) *
            (1 - self.wiring_dc_loss)
        )

        # AC losses (after inverter)
        ac_efficiency = (
            self.inverter_efficiency *
            (1 - self.wiring_ac_loss) *
            (1 - self.transformer_loss) *
            (1 - self.availability_loss)
        )

        return dc_efficiency * ac_efficiency

    @property
    def effective_capacity(self) -> Power:
        """Get effective AC capacity after losses"""
        # Limited by inverter and reduced by losses
        max_ac = min(self.installed_capacity.kw, self.inverter_capacity.kw)
        effective_kw = max_ac * self.total_system_efficiency
        return Power.from_kw(effective_kw)


@dataclass
class SolarIrradiance:
    """Solar irradiance data"""
    ghi: float  # Global horizontal irradiance (W/m²)
    dni: float  # Direct normal irradiance (W/m²)
    dhi: float  # Diffuse horizontal irradiance (W/m²)
    timestamp: datetime

    @property
    def total_irradiance(self) -> float:
        """Get total irradiance"""
        return self.ghi


class SolarProduction:
    """Calculate solar production based on irradiance and system specs"""

    def __init__(self, system: PVSystemSpecification):
        self.system = system
        self._temperature_coefficient = -0.004  # Power reduction per °C above 25°C
        self._reference_irradiance = 1000.0  # W/m² (STC conditions)

    def calculate_production(
        self,
        irradiance: float,
        ambient_temperature: float = 15.0,
        wind_speed: float = 1.0
    ) -> Power:
        """
        Calculate production for given conditions

        Args:
            irradiance: Solar irradiance (W/m²)
            ambient_temperature: Ambient temperature (°C)
            wind_speed: Wind speed (m/s) for cooling effect

        Returns:
            AC power output after all losses
        """
        if irradiance <= 0:
            return Power.from_kw(0)

        # Calculate cell temperature (simplified model)
        # NOCT (Nominal Operating Cell Temperature) model
        noct = 45  # °C at 800 W/m², 20°C ambient, 1 m/s wind
        cell_temp = ambient_temperature + (noct - 20) * (irradiance / 800) * (1 - wind_speed / 10)

        # Temperature derating
        temp_loss = self._temperature_coefficient * (cell_temp - 25)
        temp_efficiency = 1 + temp_loss

        # Power calculation
        # P = P_stc * (G / G_stc) * temp_efficiency * system_efficiency
        dc_power = (
            self.system.installed_capacity.kw *
            (irradiance / self._reference_irradiance) *
            temp_efficiency
        )

        # Limit by inverter capacity
        ac_power_before_losses = min(dc_power, self.system.inverter_capacity.kw)

        # Apply system losses
        ac_power = ac_power_before_losses * self.system.total_system_efficiency

        return Power.from_kw(ac_power)

    def calculate_production_series(
        self,
        irradiance_series: pd.Series,
        temperature_series: Optional[pd.Series] = None
    ) -> pd.Series:
        """
        Calculate production for time series data

        Args:
            irradiance_series: Hourly irradiance data (W/m²)
            temperature_series: Optional hourly temperature data (°C)

        Returns:
            Hourly production series (kW)
        """
        if temperature_series is None:
            # Use simplified temperature model based on hour of day
            hours = irradiance_series.index.hour
            # Simple sinusoidal temperature variation (10-20°C)
            temperature_series = 15 + 5 * np.sin((hours - 6) * np.pi / 12)

        production = []
        for i, irrad in enumerate(irradiance_series):
            temp = temperature_series.iloc[i] if isinstance(temperature_series, pd.Series) else temperature_series[i]
            power = self.calculate_production(irrad, temp)
            production.append(power.kw)

        return pd.Series(production, index=irradiance_series.index)


class PVSystem:
    """Solar PV system with production simulation"""

    def __init__(
        self,
        specification: PVSystemSpecification,
        location_latitude: float,
        location_longitude: float
    ):
        self.spec = specification
        self.latitude = location_latitude
        self.longitude = location_longitude
        self.production_calculator = SolarProduction(specification)
        self.lifetime_years = 25
        self.annual_degradation = 0.005  # 0.5% per year

    def estimate_annual_production(self, irradiance_data: pd.Series) -> Energy:
        """
        Estimate annual production from irradiance data

        Args:
            irradiance_data: Hourly irradiance for full year

        Returns:
            Total annual energy production
        """
        production_series = self.production_calculator.calculate_production_series(irradiance_data)
        total_kwh = production_series.sum()  # Assuming hourly data, kW * 1h = kWh
        return Energy.from_kwh(total_kwh)

    def calculate_capacity_factor(self, annual_production: Energy) -> float:
        """Calculate capacity factor"""
        theoretical_max = self.spec.installed_capacity.kw * 8760  # Hours in year
        return annual_production.kwh / theoretical_max

    def calculate_specific_yield(self, annual_production: Energy) -> float:
        """Calculate specific yield (kWh/kWp)"""
        return annual_production.kwh / self.spec.installed_capacity.kw

    def apply_curtailment(
        self,
        production: Power,
        grid_limit: Power,
        battery_available_capacity: Optional[Energy] = None
    ) -> tuple[Power, Power]:
        """
        Apply grid export limit with optional battery charging

        Args:
            production: Current production
            grid_limit: Maximum grid export
            battery_available_capacity: Available battery charge capacity

        Returns:
            Tuple of (grid_export, battery_charge)
        """
        if production.kw <= grid_limit.kw:
            # No curtailment needed
            return production, Power.from_kw(0)

        # Calculate excess
        excess = Power.from_kw(production.kw - grid_limit.kw)

        # Try to charge battery with excess
        if battery_available_capacity and battery_available_capacity.kwh > 0:
            # Assume 1 hour time step
            battery_charge = Power.from_kw(min(excess.kw, battery_available_capacity.kwh))
            remaining_curtailment = Power.from_kw(excess.kw - battery_charge.kw)
        else:
            battery_charge = Power.from_kw(0)
            remaining_curtailment = excess

        # Grid gets the limit, rest is curtailed or stored
        return grid_limit, battery_charge

    def calculate_degraded_production(self, year: int, base_production: Energy) -> Energy:
        """Calculate production after degradation"""
        degradation_factor = (1 - self.annual_degradation) ** year
        return Energy.from_kwh(base_production.kwh * degradation_factor)


@dataclass
class ProductionAnalysis:
    """Analysis results for solar production"""
    annual_production: Energy
    capacity_factor: float
    specific_yield: float
    peak_production: Power
    curtailed_energy: Energy
    self_consumption_rate: float
    grid_export: Energy

    def summary_dict(self) -> Dict[str, Any]:
        """Get summary as dictionary"""
        return {
            'annual_production_mwh': self.annual_production.mwh,
            'capacity_factor': self.capacity_factor,
            'specific_yield_kwh_per_kwp': self.specific_yield,
            'peak_production_kw': self.peak_production.kw,
            'curtailed_energy_mwh': self.curtailed_energy.mwh,
            'self_consumption_rate': self.self_consumption_rate,
            'grid_export_mwh': self.grid_export.mwh
        }