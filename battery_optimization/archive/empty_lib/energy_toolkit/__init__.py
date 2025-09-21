"""
Energy Toolkit - Reusable energy system components

A library of reusable components for energy system analysis and optimization.
Can be extracted and published as a separate package.
"""

__version__ = "0.1.0"

# Value objects for type safety
from domain.value_objects.energy import Energy, Power, EnergyPrice, EnergyTimeSeries
from domain.value_objects.money import Money, CostPerUnit, CashFlow

# External data clients
from infrastructure.data_sources.entsoe_client import ENTSOEClient, PriceForecaster
from infrastructure.data_sources.pvgis_client import PVGISClient

# Grid tariff structures
from .tariffs import (
    TariffStructure,
    TimeOfUseTariff,
    DemandChargeTariff,
    TieredTariff,
    LnettCommercialTariff,
    TensioCommercialTariff
)

# Utility functions
from .utils import (
    calculate_npv,
    calculate_irr,
    calculate_payback_period,
    calculate_lcoe,
    calculate_capacity_factor
)

__all__ = [
    # Value objects
    'Energy',
    'Power',
    'EnergyPrice',
    'EnergyTimeSeries',
    'Money',
    'CostPerUnit',
    'CashFlow',

    # Data clients
    'ENTSOEClient',
    'PriceForecaster',
    'PVGISClient',

    # Tariffs
    'TariffStructure',
    'TimeOfUseTariff',
    'DemandChargeTariff',
    'TieredTariff',
    'LnettCommercialTariff',
    'TensioCommercialTariff',

    # Utils
    'calculate_npv',
    'calculate_irr',
    'calculate_payback_period',
    'calculate_lcoe',
    'calculate_capacity_factor'
]