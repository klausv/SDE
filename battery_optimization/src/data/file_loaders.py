"""
File loading utilities for battery optimization data.

Supports loading electricity prices, PV production, and consumption from CSV files.
"""

from pathlib import Path
from typing import Tuple, Optional
import pandas as pd
import numpy as np


def load_price_data(file_path: str) -> Tuple[pd.DatetimeIndex, np.ndarray]:
    """
    Load electricity price data from CSV file.

    Expected format:
    - Column 1: timestamp (datetime) or index as datetime
    - Column 2: price in NOK/kWh

    Args:
        file_path: Path to CSV file with price data

    Returns:
        Tuple of (timestamps, prices_nok_per_kwh)

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Price data file not found: {file_path}")

    # Read CSV and handle timezone-aware timestamps (pattern from legacy code)
    df = pd.read_csv(file_path)

    # Parse timestamp column (first column) with UTC
    timestamp_col = df.columns[0]
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)

    # Set as index
    df.set_index(timestamp_col, inplace=True)

    # Convert to Oslo time then remove timezone (makes it timezone-naive local time)
    df.index = df.index.tz_convert('Europe/Oslo').tz_localize(None)

    # Remove duplicate timestamps (DST transitions create duplicates)
    df = df[~df.index.duplicated(keep='first')]

    if df.empty:
        raise ValueError(f"Price data file is empty: {file_path}")

    # Get price column (should be first data column)
    price_col = df.columns[0] if len(df.columns) > 0 else df.columns
    prices = df[price_col].values

    # Index is already timezone-naive after processing above
    timestamps = pd.DatetimeIndex(df.index)

    return timestamps, prices


def load_production_data(file_path: str) -> Tuple[pd.DatetimeIndex, np.ndarray]:
    """
    Load PV production data from CSV file.

    Expected format:
    - Column 1: timestamp (datetime) or index as datetime
    - Column 2: production in kW

    Args:
        file_path: Path to CSV file with production data

    Returns:
        Tuple of (timestamps, production_kw)

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Production data file not found: {file_path}")

    try:
        df = pd.read_csv(file_path, parse_dates=[0], index_col=0)
    except Exception as e:
        raise ValueError(f"Failed to read production data from {file_path}: {e}")

    if df.empty:
        raise ValueError(f"Production data file is empty: {file_path}")

    # Get production column (should be first data column)
    prod_col = df.columns[0] if len(df.columns) > 0 else df.columns

    timestamps = pd.DatetimeIndex(df.index)

    # PV data is often a representative year (e.g., 2020)
    # Shift to 2024 if it's from a different year (preserves month/day/hour pattern)
    if timestamps[0].year != 2024:
        year_diff = 2024 - timestamps[0].year
        timestamps = timestamps + pd.DateOffset(years=year_diff)

    # PVGIS data often has :11 minute offset - resample to full hours
    df.index = timestamps
    df_hourly = df.resample('h').mean()  # Average if multiple values per hour

    timestamps = pd.DatetimeIndex(df_hourly.index)
    production = df_hourly[prod_col].values

    return timestamps, production


def load_consumption_data(file_path: str) -> Tuple[pd.DatetimeIndex, np.ndarray]:
    """
    Load consumption data from CSV file.

    Expected format:
    - Column 1: timestamp (datetime) or index as datetime
    - Column 2: consumption in kW

    Args:
        file_path: Path to CSV file with consumption data

    Returns:
        Tuple of (timestamps, consumption_kw)

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Consumption data file not found: {file_path}")

    try:
        df = pd.read_csv(file_path, parse_dates=[0], index_col=0)
    except Exception as e:
        raise ValueError(f"Failed to read consumption data from {file_path}: {e}")

    if df.empty:
        raise ValueError(f"Consumption data file is empty: {file_path}")

    # Get consumption column (should be first data column)
    cons_col = df.columns[0] if len(df.columns) > 0 else df.columns
    consumption = df[cons_col].values

    timestamps = pd.DatetimeIndex(df.index)

    return timestamps, consumption


def resample_timeseries(
    timestamps: pd.DatetimeIndex,
    values: np.ndarray,
    target_resolution: str,
    method: str = "mean"
) -> Tuple[pd.DatetimeIndex, np.ndarray]:
    """
    Resample time series to different resolution.

    Args:
        timestamps: Original timestamps
        values: Original values
        target_resolution: Target resolution ('PT60M' for hourly, 'PT15M' for 15-min)
        method: Resampling method ('mean', 'sum', 'max', 'interpolate')

    Returns:
        Tuple of (resampled_timestamps, resampled_values)

    Raises:
        ValueError: If target resolution is invalid or resampling fails
    """
    # Convert ISO 8601 duration to pandas frequency
    resolution_map = {
        'PT60M': '60T',
        'PT15M': '15T',
        'PT30M': '30T',
        'PT5M': '5T',
    }

    if target_resolution not in resolution_map:
        raise ValueError(
            f"Invalid target_resolution '{target_resolution}'. "
            f"Must be one of: {list(resolution_map.keys())}"
        )

    freq = resolution_map[target_resolution]

    # Create DataFrame for resampling
    df = pd.DataFrame({'value': values}, index=timestamps)

    # Resample based on method
    if method == "mean":
        resampled = df.resample(freq).mean()
    elif method == "sum":
        resampled = df.resample(freq).sum()
    elif method == "max":
        resampled = df.resample(freq).max()
    elif method == "interpolate":
        # Upsample first, then interpolate
        resampled = df.resample(freq).asfreq()
        resampled = resampled.interpolate(method='linear')
    else:
        raise ValueError(
            f"Invalid resampling method '{method}'. "
            f"Must be one of: ['mean', 'sum', 'max', 'interpolate']"
        )

    resampled_timestamps = pd.DatetimeIndex(resampled.index)
    resampled_values = resampled['value'].values

    return resampled_timestamps, resampled_values


def align_timeseries(
    timestamps_list: list[pd.DatetimeIndex],
    values_list: list[np.ndarray]
) -> Tuple[pd.DatetimeIndex, list[np.ndarray]]:
    """
    Align multiple time series to common timestamp index.

    Uses intersection of all timestamps.

    Args:
        timestamps_list: List of DatetimeIndex objects
        values_list: List of value arrays corresponding to timestamps

    Returns:
        Tuple of (common_timestamps, list of aligned value arrays)

    Raises:
        ValueError: If timestamp lists have no common overlap
    """
    if len(timestamps_list) != len(values_list):
        raise ValueError("timestamps_list and values_list must have same length")

    if len(timestamps_list) == 0:
        raise ValueError("Cannot align empty list of time series")

    # Find common timestamps (intersection)
    common_timestamps = timestamps_list[0]
    for ts in timestamps_list[1:]:
        common_timestamps = common_timestamps.intersection(ts)

    if len(common_timestamps) == 0:
        raise ValueError("Time series have no overlapping timestamps")

    # Align all values to common timestamps
    aligned_values = []
    for timestamps, values in zip(timestamps_list, values_list):
        df = pd.DataFrame({'value': values}, index=timestamps)
        aligned = df.reindex(common_timestamps)
        aligned_values.append(aligned['value'].values)

    return common_timestamps, aligned_values


def detect_resolution(timestamps: pd.DatetimeIndex) -> str:
    """
    Detect time resolution from timestamps.

    Args:
        timestamps: DatetimeIndex to analyze

    Returns:
        Resolution string ('PT60M', 'PT15M', etc.)

    Raises:
        ValueError: If resolution cannot be determined
    """
    if len(timestamps) < 2:
        raise ValueError("Need at least 2 timestamps to detect resolution")

    # Calculate time differences
    diffs = pd.Series(timestamps[1:]) - pd.Series(timestamps[:-1])
    median_diff = diffs.median()

    # Map to standard resolutions
    minutes = median_diff.total_seconds() / 60

    if abs(minutes - 60) < 1:
        return 'PT60M'
    elif abs(minutes - 15) < 1:
        return 'PT15M'
    elif abs(minutes - 30) < 1:
        return 'PT30M'
    elif abs(minutes - 5) < 1:
        return 'PT5M'
    else:
        raise ValueError(f"Unsupported resolution: {minutes:.1f} minutes")
