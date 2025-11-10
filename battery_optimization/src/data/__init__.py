"""
Data management module for battery optimization.

Handles loading, windowing, and resampling of time-series data.
"""

from .data_manager import DataManager, TimeSeriesData
from .file_loaders import (
    load_price_data,
    load_production_data,
    load_consumption_data,
    resample_timeseries,
)

__all__ = [
    'DataManager',
    'TimeSeriesData',
    'load_price_data',
    'load_production_data',
    'load_consumption_data',
    'resample_timeseries',
]
