"""
Time Aggregation Utilities for Multi-Resolution Optimization

Handles bidirectional conversion between 15-minute and hourly time resolutions:
- Aggregate 15-min to hourly peaks (for power tariff calculation)
- Upsample hourly to 15-min (for PV production and consumption profiles)
- Validation and alignment checking

Key Use Cases:
1. Power tariff billing: Aggregate 15-min grid import to hourly peaks
2. Data preparation: Upsample hourly PVGIS data to 15-min for optimization
3. Mixed-resolution optimization: 15-min spot trading with hourly power tariffs
"""

import numpy as np
import pandas as pd
from typing import Tuple, Union


def aggregate_15min_to_hourly_peak(
    power_15min: Union[np.ndarray, pd.Series],
    timestamps_15min: pd.DatetimeIndex = None
) -> Union[np.ndarray, pd.Series]:
    """
    Aggregate 15-minute power data to hourly peaks.

    Takes the MAXIMUM of each 4 consecutive 15-minute intervals to represent
    the hourly peak. This is used for power tariff calculation where billing
    is based on hourly peak demand.

    Args:
        power_15min: Power values at 15-minute resolution
        timestamps_15min: Optional DatetimeIndex for validation

    Returns:
        Hourly peak power values (length = len(power_15min) / 4)

    Example:
        15-min data: [10, 12, 15, 11] kW → hourly peak: 15 kW
        15-min data: [20, 18, 22, 19] kW → hourly peak: 22 kW
    """
    # Convert to numpy array if needed
    if isinstance(power_15min, pd.Series):
        values = power_15min.values
        has_index = True
        original_index = power_15min.index
    else:
        values = power_15min
        has_index = False

    # Validate length
    if len(values) % 4 != 0:
        raise ValueError(
            f"15-minute data length must be divisible by 4, got {len(values)}"
        )

    # Validate timestamps if provided
    if timestamps_15min is not None:
        if len(timestamps_15min) != len(values):
            raise ValueError(
                f"Timestamp length {len(timestamps_15min)} != data length {len(values)}"
            )

        # Check resolution
        if len(timestamps_15min) > 1:
            median_diff = pd.Series(timestamps_15min).diff().median()
            expected_diff = pd.Timedelta(minutes=15)
            if abs(median_diff - expected_diff) > pd.Timedelta(seconds=60):
                raise ValueError(
                    f"Expected 15-minute intervals, got median {median_diff}"
                )

    # Reshape to (n_hours, 4) and take max along axis 1
    n_hours = len(values) // 4
    reshaped = values.reshape(n_hours, 4)
    hourly_peaks = reshaped.max(axis=1)

    # Return as Series if input was Series
    if has_index and timestamps_15min is not None:
        # Create hourly index (take first timestamp of each hour)
        hourly_index = timestamps_15min[::4]
        return pd.Series(hourly_peaks, index=hourly_index)

    return hourly_peaks


def upsample_hourly_to_15min(
    hourly_data: Union[np.ndarray, pd.Series],
    timestamps_hourly: pd.DatetimeIndex = None
) -> Union[np.ndarray, pd.Series]:
    """
    Upsample hourly data to 15-minute resolution by repeating each value 4 times.

    This is used to prepare hourly PVGIS production and consumption data for
    15-minute resolution optimization. Each hourly value is assumed constant
    across the four 15-minute intervals within that hour.

    Args:
        hourly_data: Data values at hourly resolution
        timestamps_hourly: Optional DatetimeIndex for creating 15-min index

    Returns:
        15-minute resolution data (length = len(hourly_data) * 4)

    Example:
        Hourly: [100, 120, 110] kW
        15-min: [100, 100, 100, 100, 120, 120, 120, 120, 110, 110, 110, 110] kW
    """
    # Convert to numpy array if needed
    if isinstance(hourly_data, pd.Series):
        values = hourly_data.values
        has_index = True
        original_index = hourly_data.index
    else:
        values = hourly_data
        has_index = False

    # Validate timestamps if provided
    if timestamps_hourly is not None:
        if len(timestamps_hourly) != len(values):
            raise ValueError(
                f"Timestamp length {len(timestamps_hourly)} != data length {len(values)}"
            )

        # Check resolution (allow some tolerance for DST transitions)
        if len(timestamps_hourly) > 1:
            median_diff = pd.Series(timestamps_hourly).diff().median()
            expected_diff = pd.Timedelta(hours=1)
            if abs(median_diff - expected_diff) > pd.Timedelta(minutes=5):
                raise ValueError(
                    f"Expected hourly intervals, got median {median_diff}"
                )

    # Repeat each value 4 times
    upsampled = np.repeat(values, 4)

    # Return as Series if input was Series and timestamps provided
    if has_index and timestamps_hourly is not None:
        # Create 15-minute index
        start = timestamps_hourly[0]
        end = timestamps_hourly[-1] + pd.Timedelta(hours=1)
        index_15min = pd.date_range(
            start=start,
            end=end,
            freq='15min',
            tz=timestamps_hourly.tz
        )[:-1]  # Exclude last point (end of period)

        # Trim to exact length (handle DST edge cases)
        index_15min = index_15min[:len(upsampled)]

        return pd.Series(upsampled, index=index_15min)

    return upsampled


def aggregate_15min_to_hourly_mean(
    data_15min: Union[np.ndarray, pd.Series],
    timestamps_15min: pd.DatetimeIndex = None
) -> Union[np.ndarray, pd.Series]:
    """
    Aggregate 15-minute data to hourly means.

    Takes the AVERAGE of each 4 consecutive 15-minute intervals. This is used
    for energy quantities where averaging is appropriate (e.g., comparing
    average power consumption between resolutions).

    Args:
        data_15min: Data values at 15-minute resolution
        timestamps_15min: Optional DatetimeIndex for validation

    Returns:
        Hourly mean values (length = len(data_15min) / 4)
    """
    # Convert to numpy array if needed
    if isinstance(data_15min, pd.Series):
        values = data_15min.values
        has_index = True
        original_index = data_15min.index
    else:
        values = data_15min
        has_index = False

    # Validate length
    if len(values) % 4 != 0:
        raise ValueError(
            f"15-minute data length must be divisible by 4, got {len(values)}"
        )

    # Reshape and take mean
    n_hours = len(values) // 4
    reshaped = values.reshape(n_hours, 4)
    hourly_means = reshaped.mean(axis=1)

    # Return as Series if input was Series
    if has_index and timestamps_15min is not None:
        hourly_index = timestamps_15min[::4]
        return pd.Series(hourly_means, index=hourly_index)

    return hourly_means


def validate_resolution(
    data: Union[np.ndarray, pd.Series],
    timestamps: pd.DatetimeIndex,
    expected_resolution: str
) -> Tuple[bool, str]:
    """
    Validate that data matches expected time resolution.

    Args:
        data: Data array or series
        timestamps: Corresponding timestamps
        expected_resolution: 'PT60M' or 'PT15M'

    Returns:
        (is_valid, message): Validation result and message
    """
    if expected_resolution not in ['PT60M', 'PT15M']:
        return False, f"Invalid resolution: {expected_resolution}"

    # Check data and timestamp lengths match
    if len(data) != len(timestamps):
        return False, f"Data length {len(data)} != timestamp length {len(timestamps)}"

    # Check minimum data points
    min_points = 96 if expected_resolution == 'PT15M' else 24  # At least 1 day
    if len(data) < min_points:
        return False, f"Too few data points: {len(data)} < {min_points}"

    # Calculate median time difference
    if len(timestamps) > 1:
        time_diffs = pd.Series(timestamps).diff().dropna()
        median_diff = time_diffs.median()

        if expected_resolution == 'PT15M':
            expected_diff = pd.Timedelta(minutes=15)
            tolerance = pd.Timedelta(minutes=1)
        else:  # PT60M
            expected_diff = pd.Timedelta(hours=1)
            tolerance = pd.Timedelta(minutes=5)

        if abs(median_diff - expected_diff) > tolerance:
            return False, (
                f"Time resolution mismatch: expected {expected_resolution}, "
                f"got median interval {median_diff}"
            )

    return True, "Validation passed"


def get_resolution_info(timestamps: pd.DatetimeIndex) -> dict:
    """
    Analyze timestamps and return resolution information.

    Args:
        timestamps: DatetimeIndex to analyze

    Returns:
        Dictionary with resolution statistics:
        - detected_resolution: 'PT15M', 'PT60M', or 'UNKNOWN'
        - median_interval: Median time between consecutive timestamps
        - expected_points_per_day: Expected data points for 24 hours
        - actual_points: Number of timestamps provided
    """
    if len(timestamps) < 2:
        return {
            'detected_resolution': 'UNKNOWN',
            'median_interval': None,
            'expected_points_per_day': None,
            'actual_points': len(timestamps)
        }

    # Calculate time differences
    time_diffs = pd.Series(timestamps).diff().dropna()
    median_interval = time_diffs.median()

    # Detect resolution
    if abs(median_interval - pd.Timedelta(minutes=15)) < pd.Timedelta(minutes=1):
        detected_resolution = 'PT15M'
        expected_per_day = 96
    elif abs(median_interval - pd.Timedelta(hours=1)) < pd.Timedelta(minutes=5):
        detected_resolution = 'PT60M'
        expected_per_day = 24
    else:
        detected_resolution = 'UNKNOWN'
        expected_per_day = None

    return {
        'detected_resolution': detected_resolution,
        'median_interval': median_interval,
        'expected_points_per_day': expected_per_day,
        'actual_points': len(timestamps)
    }


# Utility functions for common operations

def ensure_15min_resolution(
    data: Union[np.ndarray, pd.Series],
    timestamps: pd.DatetimeIndex,
    current_resolution: str = None
) -> Tuple[Union[np.ndarray, pd.Series], pd.DatetimeIndex]:
    """
    Ensure data is at 15-minute resolution, upsampling if necessary.

    Args:
        data: Data array or series
        timestamps: Corresponding timestamps
        current_resolution: 'PT60M', 'PT15M', or None (auto-detect)

    Returns:
        (data_15min, timestamps_15min): Data and timestamps at 15-min resolution
    """
    # Auto-detect resolution if not provided
    if current_resolution is None:
        info = get_resolution_info(timestamps)
        current_resolution = info['detected_resolution']

    if current_resolution == 'PT15M':
        # Already at 15-minute resolution
        return data, timestamps
    elif current_resolution == 'PT60M':
        # Upsample from hourly
        data_15min = upsample_hourly_to_15min(data, timestamps)
        if isinstance(data_15min, pd.Series):
            return data_15min.values, data_15min.index
        else:
            # Generate 15-min timestamps
            start = timestamps[0]
            end = timestamps[-1] + pd.Timedelta(hours=1)
            timestamps_15min = pd.date_range(
                start=start, end=end, freq='15min', tz=timestamps.tz
            )[:-1]
            return data_15min, timestamps_15min[:len(data_15min)]
    else:
        raise ValueError(f"Unknown resolution: {current_resolution}")


def ensure_hourly_resolution(
    data: Union[np.ndarray, pd.Series],
    timestamps: pd.DatetimeIndex,
    current_resolution: str = None,
    aggregation: str = 'peak'
) -> Tuple[Union[np.ndarray, pd.Series], pd.DatetimeIndex]:
    """
    Ensure data is at hourly resolution, aggregating if necessary.

    Args:
        data: Data array or series
        timestamps: Corresponding timestamps
        current_resolution: 'PT60M', 'PT15M', or None (auto-detect)
        aggregation: 'peak' or 'mean' for aggregation method

    Returns:
        (data_hourly, timestamps_hourly): Data and timestamps at hourly resolution
    """
    # Auto-detect resolution if not provided
    if current_resolution is None:
        info = get_resolution_info(timestamps)
        current_resolution = info['detected_resolution']

    if current_resolution == 'PT60M':
        # Already at hourly resolution
        return data, timestamps
    elif current_resolution == 'PT15M':
        # Aggregate from 15-minute
        if aggregation == 'peak':
            data_hourly = aggregate_15min_to_hourly_peak(data, timestamps)
        elif aggregation == 'mean':
            data_hourly = aggregate_15min_to_hourly_mean(data, timestamps)
        else:
            raise ValueError(f"Invalid aggregation method: {aggregation}")

        if isinstance(data_hourly, pd.Series):
            return data_hourly.values, data_hourly.index
        else:
            # Generate hourly timestamps
            timestamps_hourly = timestamps[::4]
            return data_hourly, timestamps_hourly[:len(data_hourly)]
    else:
        raise ValueError(f"Unknown resolution: {current_resolution}")
