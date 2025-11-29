"""
Tariff configuration loader using dataclasses.

Provides unified tariff management with YAML-based configuration.
"""

from dataclasses import dataclass, field
from typing import List, Dict
from pathlib import Path
import yaml
import pandas as pd


@dataclass
class EnergyTariffConfig:
    """Energy tariff configuration (time-of-use pricing)."""

    peak_rate: float  # NOK/kWh for peak hours
    offpeak_rate: float  # NOK/kWh for off-peak hours
    peak_schedule: str = "Mon-Fri 06:00-22:00"
    offpeak_schedule: str = "Mon-Fri 22:00-06:00 + weekends"

    def get_rate(self, timestamp: pd.Timestamp) -> float:
        """
        Get energy tariff rate for given timestamp.

        Args:
            timestamp: pandas Timestamp

        Returns:
            rate: NOK/kWh
        """
        # Check if weekday (0=Monday, 6=Sunday)
        is_weekday = timestamp.weekday() < 5

        # Check if peak hours (06:00-22:00)
        is_peak_hours = 6 <= timestamp.hour < 22

        if is_weekday and is_peak_hours:
            return self.peak_rate
        else:
            return self.offpeak_rate


@dataclass
class PowerBracket:
    """Single power tariff bracket."""

    min_kw: float
    max_kw: float
    cost_nok_month: float


@dataclass
class PowerTariffConfig:
    """Power tariff configuration (monthly capacity charges)."""

    brackets: List[PowerBracket]
    method: str = "single_bracket"
    peak_calculation: str = "top_3_daily_avg"

    def get_cost(self, peak_kw: float) -> float:
        """
        Get monthly power cost for given peak demand.

        Args:
            peak_kw: Monthly peak power in kW

        Returns:
            cost: NOK/month
        """
        for bracket in self.brackets:
            if bracket.min_kw <= peak_kw < bracket.max_kw:
                return bracket.cost_nok_month

        # If peak exceeds all brackets, return highest
        return self.brackets[-1].cost_nok_month


@dataclass
class ConsumptionTaxSeason:
    """Consumption tax for a specific season."""

    months: List[int]
    rate: float  # NOK/kWh
    season_name: str


@dataclass
class ConsumptionTaxConfig:
    """Seasonal consumption tax configuration."""

    winter: ConsumptionTaxSeason
    summer: ConsumptionTaxSeason
    fall: ConsumptionTaxSeason

    def get_rate(self, month: int) -> float:
        """
        Get consumption tax rate for given month.

        Args:
            month: Month number (1-12)

        Returns:
            rate: NOK/kWh
        """
        if month in self.winter.months:
            return self.winter.rate
        elif month in self.summer.months:
            return self.summer.rate
        elif month in self.fall.months:
            return self.fall.rate
        else:
            raise ValueError(f"Invalid month: {month}")


@dataclass
class FeedInTariffConfig:
    """Feed-in tariff configuration (export compensation)."""

    rate: float  # NOK/kWh
    description: str = "Grid tariff reduction for export"


@dataclass
class TariffProfile:
    """Complete tariff profile."""

    name: str
    year: int
    version: str
    energy: EnergyTariffConfig
    power: PowerTariffConfig
    consumption_tax: ConsumptionTaxConfig
    feed_in: FeedInTariffConfig
    valid_from: str = ""
    valid_until: str = ""

    def get_energy_tariff(self, timestamp: pd.Timestamp) -> float:
        """Get energy tariff for timestamp."""
        return self.energy.get_rate(timestamp)

    def get_power_tariff(self, peak_kw: float) -> float:
        """Get power tariff for peak demand."""
        return self.power.get_cost(peak_kw)

    def get_consumption_tax(self, month: int) -> float:
        """Get consumption tax for month."""
        return self.consumption_tax.get_rate(month)

    def get_feed_in_tariff(self) -> float:
        """Get feed-in tariff rate."""
        return self.feed_in.rate


class TariffLoader:
    """Loader for tariff configuration from YAML files."""

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> TariffProfile:
        """
        Load tariff configuration from YAML file.

        Args:
            yaml_path: Path to tariff YAML file

        Returns:
            TariffProfile instance

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            ValueError: If YAML structure is invalid
        """
        yaml_path = Path(yaml_path)

        if not yaml_path.exists():
            raise FileNotFoundError(f"Tariff file not found: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if "tariff_profile" not in data:
            raise ValueError("YAML must contain 'tariff_profile' root key")

        profile_data = data["tariff_profile"]

        # Parse energy tariff
        energy_data = profile_data["energy"]
        energy_config = EnergyTariffConfig(
            peak_rate=energy_data["peak"]["rate"],
            offpeak_rate=energy_data["offpeak"]["rate"],
            peak_schedule=energy_data["peak"].get(
                "schedule", "Mon-Fri 06:00-22:00"
            ),
            offpeak_schedule=energy_data["offpeak"].get(
                "schedule", "Mon-Fri 22:00-06:00 + weekends"
            ),
        )

        # Parse power tariff brackets
        power_data = profile_data["power"]
        brackets = [
            PowerBracket(
                min_kw=b["min_kw"],
                max_kw=float("inf") if b["max_kw"] == ".inf" else b["max_kw"],
                cost_nok_month=b["cost_nok_month"],
            )
            for b in power_data["brackets"]
        ]
        power_config = PowerTariffConfig(
            brackets=brackets,
            method=power_data.get("method", "single_bracket"),
            peak_calculation=power_data.get("peak_calculation", "top_3_daily_avg"),
        )

        # Parse consumption tax
        tax_data = profile_data["consumption_tax"]
        consumption_tax_config = ConsumptionTaxConfig(
            winter=ConsumptionTaxSeason(
                months=tax_data["winter"]["months"],
                rate=tax_data["winter"]["rate"],
                season_name=tax_data["winter"].get("season_name", "Winter"),
            ),
            summer=ConsumptionTaxSeason(
                months=tax_data["summer"]["months"],
                rate=tax_data["summer"]["rate"],
                season_name=tax_data["summer"].get("season_name", "Summer"),
            ),
            fall=ConsumptionTaxSeason(
                months=tax_data["fall"]["months"],
                rate=tax_data["fall"]["rate"],
                season_name=tax_data["fall"].get("season_name", "Fall"),
            ),
        )

        # Parse feed-in tariff
        feed_in_data = profile_data["feed_in"]
        feed_in_config = FeedInTariffConfig(
            rate=feed_in_data["rate"],
            description=feed_in_data.get(
                "description", "Grid tariff reduction for export"
            ),
        )

        # Create tariff profile
        return TariffProfile(
            name=profile_data["name"],
            year=profile_data["year"],
            version=profile_data["version"],
            valid_from=profile_data.get("valid_from", ""),
            valid_until=profile_data.get("valid_until", ""),
            energy=energy_config,
            power=power_config,
            consumption_tax=consumption_tax_config,
            feed_in=feed_in_config,
        )

    @classmethod
    def get_default_tariff(cls) -> TariffProfile:
        """
        Get default Lnett 2024 tariff.

        Returns:
            TariffProfile for Lnett Commercial < 100 MWh/year (2024)
        """
        # Default path relative to this file
        default_path = (
            Path(__file__).parent.parent.parent.parent
            / "configs"
            / "infrastructure"
            / "tariffs_lnett_2024.yaml"
        )

        return cls.from_yaml(default_path)
