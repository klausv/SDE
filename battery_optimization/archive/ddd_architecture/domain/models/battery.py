"""
Battery domain model with state management and constraints
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from enum import Enum
import numpy as np
import pandas as pd

from domain.value_objects.energy import Energy, Power
from domain.value_objects.money import Money, CostPerUnit


class BatteryState(Enum):
    """Battery operational state"""
    IDLE = "idle"
    CHARGING = "charging"
    DISCHARGING = "discharging"
    ERROR = "error"


@dataclass
class BatterySpecification:
    """Immutable battery specifications"""
    capacity: Energy
    max_power: Power
    efficiency: float = 0.90
    min_soc: float = 0.10  # Minimum state of charge (0-1)
    max_soc: float = 0.95  # Maximum state of charge (0-1)
    max_c_rate_charge: float = 1.0
    max_c_rate_discharge: float = 1.0
    cycle_life: int = 6000
    calendar_life_years: int = 15

    def __post_init__(self):
        """Validate specifications"""
        if self.efficiency <= 0 or self.efficiency > 1:
            raise ValueError(f"Efficiency must be between 0 and 1: {self.efficiency}")
        if self.min_soc < 0 or self.min_soc >= self.max_soc:
            raise ValueError(f"Invalid SOC limits: {self.min_soc} to {self.max_soc}")
        if self.max_c_rate_charge <= 0:
            raise ValueError(f"Invalid C-rate: {self.max_c_rate_charge}")

    @property
    def usable_capacity(self) -> Energy:
        """Get usable capacity considering SOC limits"""
        usable_fraction = self.max_soc - self.min_soc
        return Energy.from_kwh(self.capacity.kwh * usable_fraction)

    @property
    def max_charge_power(self) -> Power:
        """Maximum charging power based on C-rate"""
        c_rate_limit = Power.from_kw(self.capacity.kwh * self.max_c_rate_charge)
        return Power.from_kw(min(self.max_power.kw, c_rate_limit.kw))

    @property
    def max_discharge_power(self) -> Power:
        """Maximum discharging power based on C-rate"""
        c_rate_limit = Power.from_kw(self.capacity.kwh * self.max_c_rate_discharge)
        return Power.from_kw(min(self.max_power.kw, c_rate_limit.kw))


@dataclass
class BatteryDegradation:
    """Battery degradation model"""
    calendar_degradation_rate: float = 0.02  # per year
    cycle_degradation_rate: float = 0.0001  # per cycle
    current_capacity_retention: float = 1.0
    total_cycles: int = 0
    age_years: float = 0.0

    def update(self, cycles: int, time_elapsed_years: float):
        """Update degradation based on cycles and time"""
        # Calendar aging
        calendar_loss = self.calendar_degradation_rate * time_elapsed_years

        # Cycle aging
        self.total_cycles += cycles
        cycle_loss = self.cycle_degradation_rate * cycles

        # Combined degradation (simplified - could use more complex models)
        total_loss = calendar_loss + cycle_loss
        self.current_capacity_retention = max(0.7, self.current_capacity_retention - total_loss)
        self.age_years += time_elapsed_years

    @property
    def effective_capacity_factor(self) -> float:
        """Get current capacity as fraction of original"""
        return self.current_capacity_retention


class Battery:
    """Battery with state management"""

    def __init__(self, specification: BatterySpecification):
        self.spec = specification
        self.degradation = BatteryDegradation()
        self.state = BatteryState.IDLE
        self.soc = 0.5  # Start at 50% SOC
        self.cycles_today = 0.0
        self.energy_throughput_kwh = 0.0

    @property
    def current_energy(self) -> Energy:
        """Get current stored energy"""
        effective_capacity = self.spec.capacity.kwh * self.degradation.effective_capacity_factor
        return Energy.from_kwh(effective_capacity * self.soc)

    @property
    def available_charge_capacity(self) -> Energy:
        """Energy that can be charged"""
        effective_capacity = self.spec.capacity.kwh * self.degradation.effective_capacity_factor
        max_energy = effective_capacity * self.spec.max_soc
        current = effective_capacity * self.soc
        return Energy.from_kwh(max_energy - current)

    @property
    def available_discharge_capacity(self) -> Energy:
        """Energy that can be discharged"""
        effective_capacity = self.spec.capacity.kwh * self.degradation.effective_capacity_factor
        min_energy = effective_capacity * self.spec.min_soc
        current = effective_capacity * self.soc
        return Energy.from_kwh(current - min_energy)

    def charge(self, power: Power, duration_hours: float) -> Tuple[Energy, Energy]:
        """
        Charge the battery

        Returns:
            Tuple of (energy charged into battery, energy drawn from grid)
        """
        if self.state == BatteryState.DISCHARGING:
            raise ValueError("Cannot charge while discharging")

        # Limit by power and capacity
        max_power = min(power.kw, self.spec.max_charge_power.kw)
        max_energy = min(
            max_power * duration_hours,
            self.available_charge_capacity.kwh
        )

        # Account for efficiency (draw more from grid than stored)
        energy_from_grid = Energy.from_kwh(max_energy / self.spec.efficiency)
        energy_to_battery = Energy.from_kwh(max_energy)

        # Update SOC
        effective_capacity = self.spec.capacity.kwh * self.degradation.effective_capacity_factor
        self.soc += energy_to_battery.kwh / effective_capacity

        # Update state and statistics
        self.state = BatteryState.CHARGING
        self.energy_throughput_kwh += energy_to_battery.kwh

        return energy_to_battery, energy_from_grid

    def discharge(self, power: Power, duration_hours: float) -> Tuple[Energy, Energy]:
        """
        Discharge the battery

        Returns:
            Tuple of (energy from battery, energy to grid after losses)
        """
        if self.state == BatteryState.CHARGING:
            raise ValueError("Cannot discharge while charging")

        # Limit by power and capacity
        max_power = min(power.kw, self.spec.max_discharge_power.kw)
        max_energy = min(
            max_power * duration_hours,
            self.available_discharge_capacity.kwh
        )

        # Account for efficiency
        energy_from_battery = Energy.from_kwh(max_energy)
        energy_to_grid = Energy.from_kwh(max_energy * self.spec.efficiency)

        # Update SOC
        effective_capacity = self.spec.capacity.kwh * self.degradation.effective_capacity_factor
        self.soc -= energy_from_battery.kwh / effective_capacity

        # Update state and statistics
        self.state = BatteryState.DISCHARGING
        self.energy_throughput_kwh += energy_from_battery.kwh
        self.cycles_today = self.energy_throughput_kwh / (2 * effective_capacity)

        return energy_from_battery, energy_to_grid

    def idle(self):
        """Set battery to idle state"""
        self.state = BatteryState.IDLE

    def reset_daily_counters(self):
        """Reset daily cycle counter"""
        self.cycles_today = 0.0

    def age_one_year(self):
        """Apply one year of aging"""
        annual_cycles = self.cycles_today * 365
        self.degradation.update(int(annual_cycles), 1.0)
        self.reset_daily_counters()


class BatterySimulator:
    """Simulate battery operation over time series"""

    def __init__(self, battery: Battery):
        self.battery = battery

    def simulate(
        self,
        pv_generation: pd.Series,
        load: pd.Series,
        spot_prices: pd.Series,
        strategy: str = "self_consumption"
    ) -> pd.DataFrame:
        """
        Simulate battery operation

        Args:
            pv_generation: PV generation time series (kW)
            load: Load time series (kW)
            spot_prices: Electricity spot prices (NOK/kWh)
            strategy: Operation strategy

        Returns:
            DataFrame with battery operation results
        """
        results = []

        for i in range(len(pv_generation)):
            net_load = load.iloc[i] - pv_generation.iloc[i]
            price = spot_prices.iloc[i]

            # Simple self-consumption strategy
            if strategy == "self_consumption":
                if net_load > 0:  # Deficit - discharge
                    power_need = Power.from_kw(net_load)
                    discharged, delivered = self.battery.discharge(power_need, 1.0)
                    battery_power = -delivered.kwh
                elif net_load < 0:  # Surplus - charge
                    power_available = Power.from_kw(-net_load)
                    charged, drawn = self.battery.charge(power_available, 1.0)
                    battery_power = drawn.kwh
                else:
                    self.battery.idle()
                    battery_power = 0

            # Energy arbitrage strategy
            elif strategy == "arbitrage":
                # Charge when cheap, discharge when expensive
                price_threshold_charge = 0.5  # NOK/kWh
                price_threshold_discharge = 1.0  # NOK/kWh

                if price < price_threshold_charge:
                    # Charge from grid
                    max_power = Power.from_kw(self.battery.spec.max_charge_power.kw)
                    charged, drawn = self.battery.charge(max_power, 1.0)
                    battery_power = drawn.kwh
                elif price > price_threshold_discharge:
                    # Discharge to grid
                    max_power = Power.from_kw(self.battery.spec.max_discharge_power.kw)
                    discharged, delivered = self.battery.discharge(max_power, 1.0)
                    battery_power = -delivered.kwh
                else:
                    self.battery.idle()
                    battery_power = 0

            else:
                raise ValueError(f"Unknown strategy: {strategy}")

            results.append({
                'timestamp': pv_generation.index[i],
                'pv_kw': pv_generation.iloc[i],
                'load_kw': load.iloc[i],
                'net_load_kw': net_load,
                'battery_power_kw': battery_power,
                'battery_soc': self.battery.soc,
                'battery_energy_kwh': self.battery.current_energy.kwh,
                'spot_price': price
            })

        return pd.DataFrame(results)