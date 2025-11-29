"""
Pricing infrastructure module for electricity price data management.

Provides unified interface for loading, fetching, and managing electricity price data
from various sources (files, APIs, etc.).
"""

from .price_loader import PriceData, PriceLoader

__all__ = ['PriceData', 'PriceLoader']
