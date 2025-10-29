"""
Kontrollstrategier for batteristyring

Strategy Pattern for å kunne velge mellom ulike kontrollmetoder:
- NoControlStrategy: Referanse uten batteri
- SimpleRuleStrategy: HEMS-lignende regelbasert styring
- LPOptimizationStrategy: LP-basert optimering (kommer senere)
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional
from .battery import Battery


class ControlStrategy(ABC):
    """Base class for batterikontrollstrategier"""

    @abstractmethod
    def decide_battery_power(
        self,
        t: int,
        production: pd.Series,
        consumption: pd.Series,
        spot_prices: pd.Series,
        battery: Optional[Battery],
        **kwargs
    ) -> float:
        """
        Bestem batteribeslutning for timestep t

        Args:
            t: Timestep index
            production: Solkraftproduksjon timeserie (kW)
            consumption: Forbruk timeserie (kW)
            spot_prices: Spotpriser timeserie (NOK/kWh)
            battery: Battery-objekt (kan være None for referanse)
            **kwargs: Ekstra parametere (f.eks. forecast for LP)

        Returns:
            float: Batteribeslutning (kW)
                - Positiv = lading
                - Negativ = utlading
                - 0 = ingen handling
        """
        pass


class NoControlStrategy(ControlStrategy):
    """
    Referansealternativ: Ingen batteri

    Brukes for å simulere systemet uten batterilagring
    for å kunne beregne verdien av batteriet.
    """

    def decide_battery_power(
        self,
        t: int,
        production: pd.Series,
        consumption: pd.Series,
        spot_prices: pd.Series,
        battery: Optional[Battery],
        **kwargs
    ) -> float:
        """Returner alltid 0 (ingen batterihandling)"""
        return 0.0

    def __repr__(self):
        return "NoControlStrategy()"


class SimpleRuleStrategy(ControlStrategy):
    """
    HEMS-lignende regelbasert batteristyring

    Regler (typisk for kommersielle batterisystemer):
    1. Lad ved overskudd av solstrøm (egenforbruksoptimering)
    2. Lad fra nett på natta ved billig strøm (arbitrasje)
    3. Utlad ved høyt forbruk og dyr strøm (peak shaving)
    4. Unngå lading/utlading ved middels forhold

    Parametere:
        cheap_price_threshold: Pris under hvilken vi lader fra nett (NOK/kWh)
        expensive_price_threshold: Pris over hvilken vi prioriterer utlading (NOK/kWh)
        night_hours: Timetall for "natt" (typisk 0-6)
    """

    def __init__(
        self,
        cheap_price_threshold: float = 0.5,
        expensive_price_threshold: float = 1.0,
        night_hours: tuple = (0, 6)
    ):
        self.cheap_threshold = cheap_price_threshold
        self.expensive_threshold = expensive_price_threshold
        self.night_start, self.night_end = night_hours

    def decide_battery_power(
        self,
        t: int,
        production: pd.Series,
        consumption: pd.Series,
        spot_prices: pd.Series,
        battery: Optional[Battery],
        **kwargs
    ) -> float:
        """
        Regelbasert beslutning

        Prioritering:
        1. Overskudd av solstrøm → lad (egenforbruk)
        2. Billig strøm på natt → lad (arbitrasje)
        3. Underskudd + dyr strøm → utlad (reduser nettimport)
        4. Ellers → ingen handling
        """
        # Ingen batteri = ingen handling
        if battery is None or battery.capacity_kwh == 0:
            return 0.0

        # Hent verdier for timestep t
        prod = production.iloc[t]
        cons = consumption.iloc[t]
        price = spot_prices.iloc[t]
        timestamp = production.index[t]
        hour = timestamp.hour

        # Beregn surplus/deficit
        surplus = prod - cons

        # REGEL 1: Overskudd av solstrøm → lad batteri
        if surplus > 5.0:  # Terskel for å unngå små fluktuasjoner
            charge_power = min(surplus, battery.get_available_charge_power())
            return charge_power

        # REGEL 2: Billig strøm på natt → lad fra nett
        if price < self.cheap_threshold and self.night_start <= hour < self.night_end:
            return battery.get_available_charge_power()

        # REGEL 3: Underskudd + dyr strøm → utlad batteri
        if surplus < -5.0 and price > self.expensive_threshold:
            deficit = -surplus
            discharge_power = min(deficit, battery.get_available_discharge_power())
            return -discharge_power

        # REGEL 4: Ellers ingen handling (unngå unødvendig syklisering)
        return 0.0

    def __repr__(self):
        return (f"SimpleRuleStrategy(cheap<{self.cheap_threshold:.2f}, "
                f"expensive>{self.expensive_threshold:.2f})")


if __name__ == "__main__":
    import numpy as np
    from datetime import datetime, timedelta

    print("=== STRATEGY TEST ===\n")

    # Mock data for testing
    timestamps = pd.date_range('2024-01-01', periods=24, freq='h')
    production = pd.Series(
        [0, 0, 0, 0, 0, 0, 5, 20, 40, 60, 70, 75,
         70, 65, 55, 40, 20, 5, 0, 0, 0, 0, 0, 0],
        index=timestamps,
        name='production_kw'
    )
    consumption = pd.Series(
        [30, 30, 30, 30, 30, 35, 40, 50, 55, 60, 60, 50,
         45, 55, 60, 65, 70, 65, 55, 45, 40, 35, 30, 30],
        index=timestamps,
        name='consumption_kw'
    )
    spot_prices = pd.Series(
        [0.3, 0.25, 0.2, 0.2, 0.25, 0.4, 0.6, 0.8, 1.0, 1.2, 1.3, 1.2,
         1.0, 1.1, 1.2, 1.3, 1.4, 1.3, 1.0, 0.8, 0.6, 0.5, 0.4, 0.3],
        index=timestamps,
        name='spot_price'
    )

    # Test NoControlStrategy
    print("1. NoControlStrategy:")
    strategy_none = NoControlStrategy()
    battery_none = Battery(capacity_kwh=100, power_kw=50)

    for t in [6, 10, 18]:  # Morgen, middag, kveld
        decision = strategy_none.decide_battery_power(
            t, production, consumption, spot_prices, battery_none
        )
        print(f"   t={t:2d} (kl {timestamps[t].hour:02d}): decision={decision:6.2f} kW")

    # Test SimpleRuleStrategy
    print("\n2. SimpleRuleStrategy:")
    strategy_simple = SimpleRuleStrategy(
        cheap_price_threshold=0.5,
        expensive_price_threshold=1.0
    )
    battery_simple = Battery(capacity_kwh=100, power_kw=50)

    print(f"   {strategy_simple}\n")
    for t in [2, 10, 16, 20]:  # Natt, formiddag, ettermiddag, kveld
        decision = strategy_simple.decide_battery_power(
            t, production, consumption, spot_prices, battery_simple
        )
        surplus = production.iloc[t] - consumption.iloc[t]
        price = spot_prices.iloc[t]

        print(f"   t={t:2d} (kl {timestamps[t].hour:02d}): "
              f"prod={production.iloc[t]:5.1f}, cons={consumption.iloc[t]:5.1f}, "
              f"surplus={surplus:6.1f}, price={price:.2f} → decision={decision:7.2f} kW")
