"""
Value objects for monetary values with currency handling
"""
from dataclasses import dataclass
from typing import Optional, Union
import numpy as np


@dataclass(frozen=True)
class Money:
    """Immutable monetary value with currency"""

    amount: float
    currency: str = "NOK"

    @classmethod
    def nok(cls, amount: float) -> 'Money':
        """Create NOK amount"""
        return cls(amount, "NOK")

    @classmethod
    def eur(cls, amount: float) -> 'Money':
        """Create EUR amount"""
        return cls(amount, "EUR")

    @classmethod
    def zero(cls, currency: str = "NOK") -> 'Money':
        """Create zero amount"""
        return cls(0.0, currency)

    def to_nok(self, exchange_rate: Optional[float] = None) -> 'Money':
        """Convert to NOK"""
        if self.currency == "NOK":
            return self
        elif self.currency == "EUR":
            rate = exchange_rate or 11.5  # Default EUR/NOK rate
            return Money.nok(self.amount * rate)
        else:
            raise ValueError(f"Cannot convert {self.currency} to NOK without exchange rate")

    def __add__(self, other: 'Money') -> 'Money':
        if not isinstance(other, Money):
            raise TypeError(f"Cannot add Money and {type(other)}")
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: 'Money') -> 'Money':
        if not isinstance(other, Money):
            raise TypeError(f"Cannot subtract {type(other)} from Money")
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract different currencies: {self.currency} and {other.currency}")
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, scalar: float) -> 'Money':
        if not isinstance(scalar, (int, float)):
            raise TypeError(f"Cannot multiply Money by {type(scalar)}")
        return Money(self.amount * scalar, self.currency)

    def __truediv__(self, scalar: float) -> 'Money':
        if not isinstance(scalar, (int, float)):
            raise TypeError(f"Cannot divide Money by {type(scalar)}")
        return Money(self.amount / scalar, self.currency)

    def __neg__(self) -> 'Money':
        """Negate the amount"""
        return Money(-self.amount, self.currency)

    def __abs__(self) -> 'Money':
        """Absolute value"""
        return Money(abs(self.amount), self.currency)

    def __lt__(self, other: 'Money') -> bool:
        if not isinstance(other, Money):
            raise TypeError(f"Cannot compare Money with {type(other)}")
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount < other.amount

    def __le__(self, other: 'Money') -> bool:
        return self < other or self == other

    def __gt__(self, other: 'Money') -> bool:
        if not isinstance(other, Money):
            raise TypeError(f"Cannot compare Money with {type(other)}")
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount > other.amount

    def __ge__(self, other: 'Money') -> bool:
        return self > other or self == other

    def __eq__(self, other) -> bool:
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def __str__(self) -> str:
        return f"{self.amount:,.2f} {self.currency}"

    def __repr__(self) -> str:
        return f"Money({self.amount}, '{self.currency}')"


@dataclass(frozen=True)
class CostPerUnit:
    """Cost per unit (e.g., NOK/kWh, NOK/kW)"""

    value: float
    currency: str = "NOK"
    unit: str = "kWh"

    @classmethod
    def nok_per_kwh(cls, value: float) -> 'CostPerUnit':
        """Create NOK/kWh"""
        return cls(value, "NOK", "kWh")

    @classmethod
    def nok_per_kw(cls, value: float) -> 'CostPerUnit':
        """Create NOK/kW"""
        return cls(value, "NOK", "kW")

    def calculate_total(self, quantity: float) -> Money:
        """Calculate total cost for given quantity"""
        return Money(self.value * quantity, self.currency)

    def __str__(self) -> str:
        return f"{self.value:,.2f} {self.currency}/{self.unit}"


class CashFlow:
    """Cash flow over time"""

    def __init__(self, flows: list[Money], periods: list[int]):
        """
        Initialize cash flow

        Args:
            flows: List of money amounts
            periods: List of period indices (e.g., years)
        """
        if len(flows) != len(periods):
            raise ValueError("Flows and periods must have same length")

        # Ensure all same currency
        currency = flows[0].currency if flows else "NOK"
        for flow in flows:
            if flow.currency != currency:
                raise ValueError("All cash flows must have same currency")

        self.flows = flows
        self.periods = periods
        self.currency = currency

    def npv(self, discount_rate: float) -> Money:
        """Calculate Net Present Value"""
        total = 0.0
        for flow, period in zip(self.flows, self.periods):
            discount_factor = (1 + discount_rate) ** period
            total += flow.amount / discount_factor
        return Money(total, self.currency)

    def irr(self) -> Optional[float]:
        """Calculate Internal Rate of Return"""
        if not self.flows:
            return None

        # Convert to numpy array of amounts
        amounts = np.array([f.amount for f in self.flows])

        # Use numpy's IRR calculation
        try:
            return np.irr(amounts)
        except:
            # Fallback to manual calculation if numpy.irr not available
            # Binary search for IRR
            def npv_at_rate(rate):
                total = 0
                for amount, period in zip(amounts, self.periods):
                    total += amount / ((1 + rate) ** period)
                return total

            # Binary search
            low, high = -0.99, 10.0
            tolerance = 1e-6
            max_iterations = 100

            for _ in range(max_iterations):
                mid = (low + high) / 2
                npv_mid = npv_at_rate(mid)

                if abs(npv_mid) < tolerance:
                    return mid

                if npv_mid > 0:
                    low = mid
                else:
                    high = mid

            return None  # Did not converge

    def payback_period(self) -> Optional[float]:
        """Calculate payback period in years"""
        cumulative = 0.0
        for flow, period in zip(self.flows, self.periods):
            cumulative += flow.amount
            if cumulative >= 0:
                # Linear interpolation for partial year
                if period > 0 and cumulative - flow.amount < 0:
                    partial_year = -((cumulative - flow.amount) / flow.amount)
                    return period - 1 + partial_year
                return float(period)
        return None  # Never pays back

    def total(self) -> Money:
        """Get total undiscounted cash flow"""
        total = sum(f.amount for f in self.flows)
        return Money(total, self.currency)