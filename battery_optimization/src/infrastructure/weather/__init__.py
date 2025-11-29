"""
Weather infrastructure module for solar production and weather data management.

Provides unified interface for loading and managing weather/solar data
from various sources (files, PVGIS API, PVLib, etc.).
"""

from .solar_loader import SolarProductionData, SolarProductionLoader

__all__ = ['SolarProductionData', 'SolarProductionLoader']
