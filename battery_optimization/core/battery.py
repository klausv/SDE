"""
Fysisk batterimodell for energilagring
"""
import numpy as np


class Battery:
    """
    Fysisk batterimodell med SOC-tracking og effektivitetstap

    Parametere:
        capacity_kwh: Nominal batterikapasitet (kWh)
        power_kw: Maksimal ladeeffekt/utladingseffekt (kW)
        efficiency: Roundtrip efficiency (0-1)
        min_soc: Minimum state of charge (0-1)
        max_soc: Maksimum state of charge (0-1)
        max_c_rate_charge: Maksimal C-rate for lading (1.0 = 1C)
        max_c_rate_discharge: Maksimal C-rate for utlading (1.0 = 1C)
    """

    def __init__(
        self,
        capacity_kwh: float,
        power_kw: float,
        efficiency: float = 0.9,
        min_soc: float = 0.1,
        max_soc: float = 0.9,
        max_c_rate_charge: float = 1.0,
        max_c_rate_discharge: float = 1.0
    ):
        # Konfigurasjon
        self.capacity_kwh = capacity_kwh
        self.power_kw = power_kw
        self.efficiency = efficiency
        self.min_soc = min_soc
        self.max_soc = max_soc
        self.max_c_rate_charge = max_c_rate_charge
        self.max_c_rate_discharge = max_c_rate_discharge

        # State - direkte attributter
        self.soc_kwh = capacity_kwh * 0.5  # Start ved 50%

    def charge(self, power_kw: float, duration_h: float = 1.0) -> float:
        """
        Lad batteriet

        Args:
            power_kw: Ønsket ladeeffekt (kW)
            duration_h: Varighet (timer, default 1.0)

        Returns:
            float: Faktisk energi lagret i batteriet (kWh)
        """
        if self.capacity_kwh == 0:
            return 0.0

        # Begrens til maks ladeeffekt (power rating og C-rate)
        max_power_c_rate = self.capacity_kwh * self.max_c_rate_charge
        max_power = min(power_kw, self.power_kw, max_power_c_rate)

        # Energi inn (før effektivitetstap)
        energy_in = max_power * duration_h

        # Energi lagret (etter effektivitetstap)
        energy_stored = energy_in * self.efficiency

        # Sjekk SOC-grense
        max_storage = self.capacity_kwh * self.max_soc - self.soc_kwh
        energy_stored = min(energy_stored, max_storage)

        # Oppdater SOC
        self.soc_kwh += energy_stored

        return energy_stored

    def discharge(self, power_kw: float, duration_h: float = 1.0) -> float:
        """
        Utlad batteriet

        Args:
            power_kw: Ønsket utladingseffekt (kW)
            duration_h: Varighet (timer, default 1.0)

        Returns:
            float: Faktisk energi levert fra batteriet (kWh)
        """
        if self.capacity_kwh == 0:
            return 0.0

        # Begrens til maks utladingseffekt (power rating og C-rate)
        max_power_c_rate = self.capacity_kwh * self.max_c_rate_discharge
        max_power = min(power_kw, self.power_kw, max_power_c_rate)

        # Energi ønsket ut
        energy_needed = max_power * duration_h

        # Sjekk SOC-grense
        max_discharge = self.soc_kwh - self.capacity_kwh * self.min_soc

        # Energi tilgjengelig (etter effektivitetstap)
        energy_available = max_discharge * self.efficiency

        # Faktisk energi levert
        energy_out = min(energy_needed, energy_available)

        # Oppdater SOC (energi tatt fra batteri inkluderer tap)
        self.soc_kwh -= energy_out / self.efficiency

        return energy_out

    def get_available_charge_power(self) -> float:
        """
        Beregn tilgjengelig ladeeffekt (kW)
        Begrenset av power rating, C-rate og SOC headroom

        Returns:
            float: Maksimal ladeeffekt (kW)
        """
        if self.capacity_kwh == 0:
            return 0.0

        headroom = self.capacity_kwh * self.max_soc - self.soc_kwh
        max_power_from_soc = headroom / self.efficiency
        max_power_c_rate = self.capacity_kwh * self.max_c_rate_charge

        return min(self.power_kw, max_power_from_soc, max_power_c_rate)

    def get_available_discharge_power(self) -> float:
        """
        Beregn tilgjengelig utladingseffekt (kW)
        Begrenset av power rating, C-rate og tilgjengelig SOC

        Returns:
            float: Maksimal utladingseffekt (kW)
        """
        if self.capacity_kwh == 0:
            return 0.0

        available = self.soc_kwh - self.capacity_kwh * self.min_soc
        max_power_from_soc = available * self.efficiency
        max_power_c_rate = self.capacity_kwh * self.max_c_rate_discharge

        return min(self.power_kw, max_power_from_soc, max_power_c_rate)

    def get_soc_fraction(self) -> float:
        """
        Returner SOC som fraksjon (0-1)

        Returns:
            float: SOC som fraksjon av kapasitet
        """
        if self.capacity_kwh == 0:
            return 0.0
        return self.soc_kwh / self.capacity_kwh

    def reset(self, initial_soc_fraction: float = 0.5):
        """
        Reset batteritilstand til initial verdi

        Args:
            initial_soc_fraction: Initial SOC som fraksjon (0-1)
        """
        self.soc_kwh = self.capacity_kwh * initial_soc_fraction

    def __repr__(self):
        return (f"Battery(capacity={self.capacity_kwh:.1f}kWh, "
                f"power={self.power_kw:.1f}kW, "
                f"SOC={self.soc_kwh:.1f}kWh ({self.get_soc_fraction()*100:.1f}%))")


if __name__ == "__main__":
    # Test batterifunksjonalitet
    print("=== BATTERY TEST ===\n")

    battery = Battery(capacity_kwh=100, power_kw=50, efficiency=0.9)
    print(f"Initial: {battery}")

    # Test lading
    stored = battery.charge(power_kw=30, duration_h=1.0)
    print(f"\nLadet med 30kW i 1h → lagret {stored:.2f} kWh")
    print(f"After charge: {battery}")

    # Test utlading
    delivered = battery.discharge(power_kw=20, duration_h=1.0)
    print(f"\nUtladet med 20kW i 1h → levert {delivered:.2f} kWh")
    print(f"After discharge: {battery}")

    # Test grenser
    print(f"\nTilgjengelig ladeeffekt: {battery.get_available_charge_power():.2f} kW")
    print(f"Tilgjengelig utladingseffekt: {battery.get_available_discharge_power():.2f} kW")

    # Test reset
    battery.reset()
    print(f"\nEtter reset: {battery}")
