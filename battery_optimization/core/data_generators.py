"""
Data generators for battery analysis
"""
import numpy as np
import pandas as pd
from typing import Tuple


def generate_solar_production(
    pv_capacity_kwp: float = 138.55,
    inverter_limit_kw: float = 110,
    year: int = 2024,
    location: str = 'stavanger'
) -> pd.Series:
    """
    Generate hourly solar production for a year

    Args:
        pv_capacity_kwp: PV system capacity in kWp
        inverter_limit_kw: Inverter max power in kW
        year: Year to generate data for
        location: Location preset (affects seasonal patterns)

    Returns:
        Hourly production series with datetime index
    """
    hours = 8760
    timestamps = pd.date_range(f'{year}-01-01', periods=hours, freq='h')

    # Location-specific parameters
    if location == 'stavanger':
        # Stavanger at 59°N has extreme seasonal variation
        seasonal_factors = [0.1, 0.2, 0.4, 0.7, 0.9, 1.0,
                           1.0, 0.9, 0.7, 0.4, 0.2, 0.1]  # Jan-Dec
    else:
        seasonal_factors = [0.5] * 12  # Default flat profile

    production = []
    for hour, timestamp in enumerate(timestamps):
        month = timestamp.month
        hour_of_day = timestamp.hour

        # Seasonal factor
        season_factor = seasonal_factors[month - 1]

        # Daily solar pattern (simplified)
        if 10 <= hour_of_day <= 14:  # Peak hours
            daily_factor = 1.0
        elif 8 <= hour_of_day <= 16:  # Daylight hours
            daily_factor = 0.7
        elif 6 <= hour_of_day <= 18:  # Dawn/dusk
            daily_factor = 0.3
        else:  # Night
            daily_factor = 0

        # Weather variation (cloud cover)
        weather_factor = 0.5 + 0.5 * np.random.random()

        # Calculate production
        production_kw = pv_capacity_kwp * season_factor * daily_factor * weather_factor
        production_kw = min(production_kw, inverter_limit_kw)  # Limit to inverter capacity

        production.append(production_kw)

    return pd.Series(production, index=timestamps, name='production_kw')


def generate_consumption_profile(
    annual_consumption_kwh: float = 90000,
    profile_type: str = 'commercial',
    year: int = 2024
) -> pd.Series:
    """
    Generate hourly consumption profile

    Args:
        annual_consumption_kwh: Total annual consumption
        profile_type: Type of profile ('commercial', 'residential', 'industrial')
        year: Year to generate data for

    Returns:
        Hourly consumption series with datetime index
    """
    hours = 8760
    timestamps = pd.date_range(f'{year}-01-01', periods=hours, freq='h')
    base_load = annual_consumption_kwh / hours

    consumption = []
    for timestamp in timestamps:
        hour = timestamp.hour
        weekday = timestamp.dayofweek < 5  # Monday-Friday
        month = timestamp.month

        if profile_type == 'commercial':
            # Office/retail pattern
            if weekday:
                if 7 <= hour <= 17:
                    load_factor = 1.5
                elif 6 <= hour <= 18:
                    load_factor = 1.0
                else:
                    load_factor = 0.5
            else:  # Weekend
                load_factor = 0.3

        elif profile_type == 'residential':
            # Home consumption pattern
            if 6 <= hour <= 9:  # Morning peak
                load_factor = 1.5
            elif 17 <= hour <= 22:  # Evening peak
                load_factor = 1.8
            elif 10 <= hour <= 16:  # Daytime low
                load_factor = 0.5
            else:  # Night
                load_factor = 0.3

        else:  # industrial
            # Constant high base load
            if weekday and 6 <= hour <= 18:
                load_factor = 1.2
            else:
                load_factor = 0.8

        # Seasonal variation (heating/cooling)
        if month in [12, 1, 2]:  # Winter
            season_factor = 1.2
        elif month in [6, 7, 8]:  # Summer
            season_factor = 0.8
        else:
            season_factor = 1.0

        hourly_consumption = base_load * load_factor * season_factor
        consumption.append(hourly_consumption)

    return pd.Series(consumption, index=timestamps, name='consumption_kw')


def generate_electricity_prices(
    year: int = 2024,
    base_price: float = 0.50,
    volatility: float = 0.4
) -> pd.Series:
    """
    Generate hourly electricity spot prices

    Args:
        year: Year to generate prices for
        base_price: Average base price in NOK/kWh
        volatility: Price volatility factor (0-1)

    Returns:
        Hourly price series with datetime index
    """
    hours = 8760
    timestamps = pd.date_range(f'{year}-01-01', periods=hours, freq='h')

    prices = []
    for timestamp in timestamps:
        hour = timestamp.hour
        month = timestamp.month
        weekday = timestamp.dayofweek < 5

        # Time-of-day factors
        if 17 <= hour <= 20:  # Evening peak
            tod_factor = 2.0
        elif 7 <= hour <= 9:  # Morning peak
            tod_factor = 1.5
        elif 10 <= hour <= 16:
            tod_factor = 1.0
        else:  # Night
            tod_factor = 0.6

        # Seasonal factors
        if month in [12, 1, 2]:  # Winter
            season_factor = 1.5
        elif month in [6, 7, 8]:  # Summer
            season_factor = 0.7
        else:
            season_factor = 1.0

        # Weekend discount
        weekend_factor = 0.8 if not weekday else 1.0

        # Random variation
        random_factor = 1 - volatility + (2 * volatility * np.random.random())

        price = base_price * tod_factor * season_factor * weekend_factor * random_factor
        prices.append(max(0, price))  # Ensure non-negative

    return pd.Series(prices, index=timestamps, name='spot_price_nok')


def generate_complete_dataset(
    year: int = 2024,
    pv_capacity_kwp: float = 138.55,
    inverter_limit_kw: float = 110,
    annual_consumption_kwh: float = 90000,
    profile_type: str = 'commercial'
) -> pd.DataFrame:
    """
    Generate complete dataset with all time series

    Returns:
        DataFrame with columns: production_kw, consumption_kw, spot_price_nok, net_load_kw
    """
    # Generate individual series
    production = generate_solar_production(pv_capacity_kwp, inverter_limit_kw, year=year)
    consumption = generate_consumption_profile(annual_consumption_kwh, profile_type, year)
    prices = generate_electricity_prices(year)

    # Combine into DataFrame
    df = pd.DataFrame({
        'production_kw': production,
        'consumption_kw': consumption,
        'spot_price_nok': prices,
        'net_load_kw': consumption - production
    })

    return df


def calculate_curtailment(
    production: pd.Series,
    grid_limit_kw: float = 77
) -> Tuple[pd.Series, float]:
    """
    Calculate curtailed energy

    Args:
        production: Hourly production series
        grid_limit_kw: Grid export limit

    Returns:
        Tuple of (hourly curtailment series, total annual curtailment)
    """
    curtailment = production.clip(lower=grid_limit_kw) - grid_limit_kw
    curtailment = curtailment.clip(lower=0)

    total_curtailment_kwh = curtailment.sum()

    return curtailment, total_curtailment_kwh