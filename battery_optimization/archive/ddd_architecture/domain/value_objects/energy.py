"""
Value objects for energy units with type safety and conversions
"""
from dataclasses import dataclass
from typing import Union, Optional
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Energy:
    """Immutable energy value with unit conversions"""

    value: float  # Always stored in kWh internally

    @classmethod
    def from_kwh(cls, value: float) -> 'Energy':
        """Create from kilowatt-hours"""
        return cls(value)

    @classmethod
    def from_mwh(cls, value: float) -> 'Energy':
        """Create from megawatt-hours"""
        return cls(value * 1000)

    @classmethod
    def from_wh(cls, value: float) -> 'Energy':
        """Create from watt-hours"""
        return cls(value / 1000)

    @property
    def kwh(self) -> float:
        """Get value in kWh"""
        return self.value

    @property
    def mwh(self) -> float:
        """Get value in MWh"""
        return self.value / 1000

    @property
    def wh(self) -> float:
        """Get value in Wh"""
        return self.value * 1000

    def __add__(self, other: 'Energy') -> 'Energy':
        if not isinstance(other, Energy):
            raise TypeError(f"Cannot add Energy and {type(other)}")
        return Energy(self.value + other.value)

    def __sub__(self, other: 'Energy') -> 'Energy':
        if not isinstance(other, Energy):
            raise TypeError(f"Cannot subtract {type(other)} from Energy")
        return Energy(self.value - other.value)

    def __mul__(self, scalar: float) -> 'Energy':
        if not isinstance(scalar, (int, float)):
            raise TypeError(f"Cannot multiply Energy by {type(scalar)}")
        return Energy(self.value * scalar)

    def __truediv__(self, scalar: float) -> 'Energy':
        if not isinstance(scalar, (int, float)):
            raise TypeError(f"Cannot divide Energy by {type(scalar)}")
        return Energy(self.value / scalar)

    def __str__(self) -> str:
        if self.value >= 1000:
            return f"{self.mwh:.2f} MWh"
        elif self.value < 1:
            return f"{self.wh:.0f} Wh"
        else:
            return f"{self.kwh:.2f} kWh"

    def __repr__(self) -> str:
        return f"Energy({self.value} kWh)"


@dataclass(frozen=True)
class Power:
    """Immutable power value with unit conversions"""

    value: float  # Always stored in kW internally

    @classmethod
    def from_kw(cls, value: float) -> 'Power':
        """Create from kilowatts"""
        return cls(value)

    @classmethod
    def from_mw(cls, value: float) -> 'Power':
        """Create from megawatts"""
        return cls(value * 1000)

    @classmethod
    def from_w(cls, value: float) -> 'Power':
        """Create from watts"""
        return cls(value / 1000)

    @property
    def kw(self) -> float:
        """Get value in kW"""
        return self.value

    @property
    def mw(self) -> float:
        """Get value in MW"""
        return self.value / 1000

    @property
    def w(self) -> float:
        """Get value in W"""
        return self.value * 1000

    def to_energy(self, hours: float) -> Energy:
        """Convert to energy given duration in hours"""
        return Energy.from_kwh(self.value * hours)

    def __add__(self, other: 'Power') -> 'Power':
        if not isinstance(other, Power):
            raise TypeError(f"Cannot add Power and {type(other)}")
        return Power(self.value + other.value)

    def __sub__(self, other: 'Power') -> 'Power':
        if not isinstance(other, Power):
            raise TypeError(f"Cannot subtract {type(other)} from Power")
        return Power(self.value - other.value)

    def __mul__(self, scalar: float) -> 'Power':
        if not isinstance(scalar, (int, float)):
            raise TypeError(f"Cannot multiply Power by {type(scalar)}")
        return Power(self.value * scalar)

    def __truediv__(self, scalar: float) -> 'Power':
        if not isinstance(scalar, (int, float)):
            raise TypeError(f"Cannot divide Power by {type(scalar)}")
        return Power(self.value / scalar)

    def __str__(self) -> str:
        if self.value >= 1000:
            return f"{self.mw:.2f} MW"
        elif self.value < 1:
            return f"{self.w:.0f} W"
        else:
            return f"{self.kw:.2f} kW"

    def __repr__(self) -> str:
        return f"Power({self.value} kW)"


@dataclass(frozen=True)
class EnergyPrice:
    """Energy price with currency"""

    value: float  # NOK/kWh
    currency: str = "NOK"

    @classmethod
    def from_nok_per_kwh(cls, value: float) -> 'EnergyPrice':
        return cls(value, "NOK")

    @classmethod
    def from_ore_per_kwh(cls, value: float) -> 'EnergyPrice':
        """Create from øre/kWh (100 øre = 1 NOK)"""
        return cls(value / 100, "NOK")

    @classmethod
    def from_eur_per_mwh(cls, value: float, exchange_rate: float = 11.5) -> 'EnergyPrice':
        """Create from EUR/MWh with exchange rate to NOK"""
        nok_per_mwh = value * exchange_rate
        nok_per_kwh = nok_per_mwh / 1000
        return cls(nok_per_kwh, "NOK")

    @property
    def nok_per_kwh(self) -> float:
        if self.currency != "NOK":
            raise ValueError(f"Currency is {self.currency}, not NOK")
        return self.value

    @property
    def ore_per_kwh(self) -> float:
        if self.currency != "NOK":
            raise ValueError(f"Currency is {self.currency}, not NOK")
        return self.value * 100

    def total_cost(self, energy: Energy) -> float:
        """Calculate total cost for given energy amount"""
        return self.value * energy.kwh

    def __str__(self) -> str:
        return f"{self.value:.3f} {self.currency}/kWh"


class EnergyTimeSeries:
    """Time series of energy values with pandas integration"""

    def __init__(self, data: Union[pd.Series, np.ndarray], unit: str = "kWh"):
        """Initialize from pandas Series or numpy array"""
        if isinstance(data, pd.Series):
            self.series = data
        else:
            self.series = pd.Series(data)

        # Convert to kWh if needed
        if unit == "MWh":
            self.series *= 1000
        elif unit == "Wh":
            self.series /= 1000
        elif unit != "kWh":
            raise ValueError(f"Unknown unit: {unit}")

    @property
    def total(self) -> Energy:
        """Get total energy"""
        return Energy.from_kwh(self.series.sum())

    @property
    def mean(self) -> Power:
        """Get average power (assuming hourly data)"""
        return Power.from_kw(self.series.mean())

    @property
    def peak(self) -> Power:
        """Get peak power (assuming hourly data)"""
        return Power.from_kw(self.series.max())

    def resample(self, freq: str) -> 'EnergyTimeSeries':
        """Resample to different frequency"""
        resampled = self.series.resample(freq).sum()
        return EnergyTimeSeries(resampled)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame"""
        return pd.DataFrame({'energy_kwh': self.series})

    def __len__(self) -> int:
        return len(self.series)

    def __getitem__(self, key):
        """Support indexing"""
        return Energy.from_kwh(self.series[key])