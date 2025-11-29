"""
Infrastructure module for tariff management.

Provides unified tariff configuration through YAML files with dataclass-based models.
"""

from .loader import TariffProfile, TariffLoader

__all__ = ["TariffProfile", "TariffLoader"]
