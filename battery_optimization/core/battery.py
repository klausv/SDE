"""
Simple battery model - no over-engineering
"""
import numpy as np
from typing import Tuple


class Battery:
    """Simple battery model with the essentials"""

    def __init__(
        self,
        capacity_kwh: float,
        power_kw: float,
        efficiency: float = 0.95,  # Modern LFP batteries
        min_soc: float = 0.1,
        max_soc: float = 0.9
    ):
        self.capacity_kwh = capacity_kwh
        self.power_kw = power_kw
        self.efficiency = efficiency
        self.min_soc = min_soc
        self.max_soc = max_soc

        # State
        self.soc = 0.5  # Start at 50%
        self.energy_kwh = self.soc * capacity_kwh

    @property
    def available_charge_kwh(self) -> float:
        """How much we can charge"""
        return (self.max_soc - self.soc) * self.capacity_kwh

    @property
    def available_discharge_kwh(self) -> float:
        """How much we can discharge"""
        return (self.soc - self.min_soc) * self.capacity_kwh

    def charge(self, power_kw: float, hours: float = 1.0) -> Tuple[float, float]:
        """
        Charge battery
        Returns: (energy_stored_kwh, energy_from_grid_kwh)
        """
        # Limit by power rating
        power_kw = min(power_kw, self.power_kw)

        # Energy to store (accounting for efficiency)
        energy_to_store = power_kw * hours * self.efficiency
        energy_from_grid = power_kw * hours

        # Limit by available capacity
        energy_to_store = min(energy_to_store, self.available_charge_kwh)

        # Update state
        self.energy_kwh += energy_to_store
        self.soc = self.energy_kwh / self.capacity_kwh

        return energy_to_store, energy_from_grid

    def discharge(self, power_kw: float, hours: float = 1.0) -> Tuple[float, float]:
        """
        Discharge battery
        Returns: (energy_delivered_kwh, energy_from_battery_kwh)
        """
        # Limit by power rating
        power_kw = min(power_kw, self.power_kw)

        # Energy from battery
        energy_from_battery = min(
            power_kw * hours / self.efficiency,
            self.available_discharge_kwh
        )

        # Energy delivered (accounting for efficiency)
        energy_delivered = energy_from_battery * self.efficiency

        # Update state
        self.energy_kwh -= energy_from_battery
        self.soc = self.energy_kwh / self.capacity_kwh

        return energy_delivered, energy_from_battery

    def reset(self, soc: float = 0.5):
        """Reset battery to given state of charge"""
        self.soc = soc
        self.energy_kwh = self.soc * self.capacity_kwh