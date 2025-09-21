"""
Load profile domain model for consumption patterns
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from domain.value_objects.energy import Energy, Power, EnergyTimeSeries


@dataclass
class LoadProfileCharacteristics:
    """Characteristics defining a load profile"""
    annual_consumption: Energy  # Total annual consumption
    profile_type: str  # commercial, residential, industrial
    peak_demand: Power  # Maximum demand
    base_load: Power  # Minimum continuous load
    load_factor: float  # Average load / peak load

    def __post_init__(self):
        """Validate characteristics"""
        if self.annual_consumption.kwh <= 0:
            raise ValueError("Annual consumption must be positive")
        if self.peak_demand.kw <= 0:
            raise ValueError("Peak demand must be positive")
        if self.base_load.kw < 0 or self.base_load.kw > self.peak_demand.kw:
            raise ValueError("Base load must be between 0 and peak demand")
        if not 0 < self.load_factor <= 1:
            raise ValueError("Load factor must be between 0 and 1")


class LoadProfileGenerator:
    """Generate synthetic load profiles based on patterns"""

    def __init__(self, characteristics: LoadProfileCharacteristics):
        self.characteristics = characteristics

    def generate_commercial_profile(self, year: int = 2024) -> pd.Series:
        """
        Generate commercial load profile (office/retail pattern)

        Patterns:
        - Higher consumption during business hours (07:00-18:00)
        - Lower on weekends
        - Seasonal variation (higher in winter due to heating/lighting)
        """
        # Create hourly timestamp index for full year
        start_date = pd.Timestamp(f'{year}-01-01')
        end_date = pd.Timestamp(f'{year}-12-31 23:00:00')
        timestamps = pd.date_range(start=start_date, end=end_date, freq='h')

        # Base hourly pattern (normalized 0-1)
        hourly_pattern = np.array([
            0.3, 0.3, 0.3, 0.3, 0.3, 0.4,  # 00-06: Night
            0.6, 0.8, 1.0, 1.0, 1.0, 0.9,  # 06-12: Morning/peak
            0.7, 0.8, 0.9, 1.0, 0.9, 0.7,  # 12-18: Afternoon
            0.5, 0.4, 0.3, 0.3, 0.3, 0.3   # 18-24: Evening
        ])

        # Weekly pattern (Mon=0, Sun=6)
        weekly_factors = np.array([
            1.0,   # Monday
            1.0,   # Tuesday
            1.0,   # Wednesday
            1.0,   # Thursday
            0.95,  # Friday
            0.5,   # Saturday
            0.4    # Sunday
        ])

        # Monthly/seasonal pattern
        monthly_factors = np.array([
            1.15,  # Jan - Winter peak
            1.12,  # Feb
            1.05,  # Mar
            0.95,  # Apr
            0.85,  # May
            0.80,  # Jun - Summer low
            0.80,  # Jul
            0.85,  # Aug
            0.90,  # Sep
            1.00,  # Oct
            1.10,  # Nov
            1.15   # Dec - Winter peak
        ])

        # Generate profile
        profile = np.zeros(len(timestamps))
        for i, ts in enumerate(timestamps):
            hour_factor = hourly_pattern[ts.hour]
            day_factor = weekly_factors[ts.dayofweek]
            month_factor = monthly_factors[ts.month - 1]

            # Combine factors
            combined_factor = hour_factor * day_factor * month_factor

            # Add some random variation (±5%)
            random_factor = 1 + np.random.normal(0, 0.05)
            combined_factor *= random_factor

            profile[i] = combined_factor

        # Normalize to match annual consumption
        profile_series = pd.Series(profile, index=timestamps)
        total_raw = profile_series.sum()
        scaling_factor = self.characteristics.annual_consumption.kwh / total_raw
        profile_series *= scaling_factor

        return profile_series

    def generate_residential_profile(self, year: int = 2024) -> pd.Series:
        """
        Generate residential load profile

        Patterns:
        - Morning peak (06:00-09:00)
        - Evening peak (17:00-22:00)
        - Higher on weekends
        - Seasonal variation
        """
        start_date = pd.Timestamp(f'{year}-01-01')
        end_date = pd.Timestamp(f'{year}-12-31 23:00:00')
        timestamps = pd.date_range(start=start_date, end=end_date, freq='h')

        # Residential hourly pattern
        hourly_pattern = np.array([
            0.4, 0.3, 0.3, 0.3, 0.3, 0.4,  # 00-06: Night
            0.7, 0.9, 0.8, 0.6, 0.5, 0.5,  # 06-12: Morning peak
            0.5, 0.5, 0.5, 0.6, 0.7, 0.9,  # 12-18: Afternoon rise
            1.0, 1.0, 0.9, 0.7, 0.5, 0.4   # 18-24: Evening peak
        ])

        # Weekly pattern - higher on weekends
        weekly_factors = np.array([
            0.9,   # Monday
            0.9,   # Tuesday
            0.9,   # Wednesday
            0.9,   # Thursday
            0.95,  # Friday
            1.1,   # Saturday
            1.05   # Sunday
        ])

        # Monthly pattern - heating/cooling needs
        monthly_factors = np.array([
            1.20,  # Jan
            1.15,  # Feb
            1.05,  # Mar
            0.95,  # Apr
            0.85,  # May
            0.90,  # Jun
            0.95,  # Jul - Some cooling
            0.95,  # Aug
            0.90,  # Sep
            1.00,  # Oct
            1.10,  # Nov
            1.20   # Dec
        ])

        profile = np.zeros(len(timestamps))
        for i, ts in enumerate(timestamps):
            hour_factor = hourly_pattern[ts.hour]
            day_factor = weekly_factors[ts.dayofweek]
            month_factor = monthly_factors[ts.month - 1]

            combined_factor = hour_factor * day_factor * month_factor
            random_factor = 1 + np.random.normal(0, 0.08)  # More variation
            combined_factor *= random_factor

            profile[i] = combined_factor

        profile_series = pd.Series(profile, index=timestamps)
        total_raw = profile_series.sum()
        scaling_factor = self.characteristics.annual_consumption.kwh / total_raw
        profile_series *= scaling_factor

        return profile_series

    def generate_industrial_profile(self, year: int = 2024) -> pd.Series:
        """
        Generate industrial load profile

        Patterns:
        - Constant high base load
        - Shift patterns
        - Lower on weekends (but not as low as commercial)
        """
        start_date = pd.Timestamp(f'{year}-01-01')
        end_date = pd.Timestamp(f'{year}-12-31 23:00:00')
        timestamps = pd.date_range(start=start_date, end=end_date, freq='h')

        # Industrial pattern - more constant
        hourly_pattern = np.array([
            0.7, 0.7, 0.7, 0.7, 0.7, 0.8,  # 00-06: Night shift
            0.9, 1.0, 1.0, 1.0, 1.0, 1.0,  # 06-12: Day shift
            1.0, 1.0, 1.0, 1.0, 0.9, 0.8,  # 12-18: Day shift cont.
            0.8, 0.8, 0.7, 0.7, 0.7, 0.7   # 18-24: Evening shift
        ])

        weekly_factors = np.array([
            1.0,   # Monday
            1.0,   # Tuesday
            1.0,   # Wednesday
            1.0,   # Thursday
            1.0,   # Friday
            0.8,   # Saturday
            0.7    # Sunday
        ])

        # Less seasonal variation
        monthly_factors = np.array([
            1.05,  # Jan
            1.03,  # Feb
            1.00,  # Mar
            0.98,  # Apr
            0.95,  # May
            0.95,  # Jun
            0.95,  # Jul
            0.95,  # Aug
            0.98,  # Sep
            1.00,  # Oct
            1.03,  # Nov
            1.05   # Dec
        ])

        profile = np.zeros(len(timestamps))
        for i, ts in enumerate(timestamps):
            hour_factor = hourly_pattern[ts.hour]
            day_factor = weekly_factors[ts.dayofweek]
            month_factor = monthly_factors[ts.month - 1]

            combined_factor = hour_factor * day_factor * month_factor
            random_factor = 1 + np.random.normal(0, 0.03)  # Less variation
            combined_factor *= random_factor

            profile[i] = combined_factor

        profile_series = pd.Series(profile, index=timestamps)
        total_raw = profile_series.sum()
        scaling_factor = self.characteristics.annual_consumption.kwh / total_raw
        profile_series *= scaling_factor

        return profile_series


class LoadProfile:
    """Load profile with analysis capabilities"""

    def __init__(self, profile_data: pd.Series, characteristics: LoadProfileCharacteristics):
        """
        Initialize load profile

        Args:
            profile_data: Hourly load data (kW)
            characteristics: Profile characteristics
        """
        self.data = profile_data
        self.characteristics = characteristics

    @classmethod
    def from_generator(
        cls,
        annual_consumption: Energy,
        profile_type: str = "commercial",
        year: int = 2024
    ) -> 'LoadProfile':
        """Create load profile using generator"""
        # Estimate characteristics based on type
        if profile_type == "commercial":
            peak_factor = 3.0  # Peak is 3x average
            load_factor = 0.4
        elif profile_type == "residential":
            peak_factor = 4.0  # More peaky
            load_factor = 0.3
        elif profile_type == "industrial":
            peak_factor = 1.5  # Flatter profile
            load_factor = 0.7
        else:
            raise ValueError(f"Unknown profile type: {profile_type}")

        average_load = annual_consumption.kwh / 8760
        peak_demand = Power.from_kw(average_load * peak_factor)
        base_load = Power.from_kw(average_load * 0.3)

        characteristics = LoadProfileCharacteristics(
            annual_consumption=annual_consumption,
            profile_type=profile_type,
            peak_demand=peak_demand,
            base_load=base_load,
            load_factor=load_factor
        )

        generator = LoadProfileGenerator(characteristics)

        if profile_type == "commercial":
            profile_data = generator.generate_commercial_profile(year)
        elif profile_type == "residential":
            profile_data = generator.generate_residential_profile(year)
        elif profile_type == "industrial":
            profile_data = generator.generate_industrial_profile(year)

        return cls(profile_data, characteristics)

    @property
    def peak_demand(self) -> Power:
        """Get actual peak demand from data"""
        return Power.from_kw(self.data.max())

    @property
    def average_demand(self) -> Power:
        """Get average demand"""
        return Power.from_kw(self.data.mean())

    @property
    def base_load(self) -> Power:
        """Get minimum load"""
        return Power.from_kw(self.data.min())

    @property
    def load_factor(self) -> float:
        """Calculate actual load factor"""
        return self.average_demand.kw / self.peak_demand.kw

    @property
    def total_consumption(self) -> Energy:
        """Get total energy consumption"""
        return Energy.from_kwh(self.data.sum())

    def get_monthly_peaks(self) -> pd.Series:
        """Get monthly peak demands"""
        return self.data.resample('ME').max()

    def get_monthly_consumption(self) -> pd.Series:
        """Get monthly consumption"""
        return self.data.resample('ME').sum()

    def get_duration_curve(self) -> pd.Series:
        """Get load duration curve"""
        return self.data.sort_values(ascending=False).reset_index(drop=True)

    def get_time_of_use_breakdown(
        self,
        peak_hours: Tuple[int, int] = (6, 22),
        peak_days: List[int] = [0, 1, 2, 3, 4]  # Monday-Friday
    ) -> Dict[str, Energy]:
        """
        Break down consumption by time-of-use periods

        Args:
            peak_hours: Start and end hour for peak period
            peak_days: Days of week that are peak (0=Monday)

        Returns:
            Dictionary with peak and off-peak consumption
        """
        peak_mask = (
            (self.data.index.hour >= peak_hours[0]) &
            (self.data.index.hour < peak_hours[1]) &
            (self.data.index.dayofweek.isin(peak_days))
        )

        peak_consumption = Energy.from_kwh(self.data[peak_mask].sum())
        offpeak_consumption = Energy.from_kwh(self.data[~peak_mask].sum())

        return {
            'peak': peak_consumption,
            'off_peak': offpeak_consumption,
            'peak_percentage': peak_consumption.kwh / self.total_consumption.kwh
        }

    def apply_demand_response(
        self,
        reduction_percentage: float,
        trigger_price: float,
        price_series: pd.Series
    ) -> pd.Series:
        """
        Apply demand response based on price signals

        Args:
            reduction_percentage: How much to reduce load (0-1)
            trigger_price: Price threshold to trigger response
            price_series: Electricity price series

        Returns:
            Modified load profile
        """
        modified_profile = self.data.copy()
        high_price_hours = price_series > trigger_price

        # Reduce load during high price hours
        modified_profile[high_price_hours] *= (1 - reduction_percentage)

        # Could redistribute to other hours, but keeping simple for now
        return modified_profile

    def calculate_coincident_peak(self, system_peak_hours: List[datetime]) -> Power:
        """Calculate demand during system peak hours"""
        peak_demands = [self.data.loc[hour] for hour in system_peak_hours if hour in self.data.index]
        return Power.from_kw(np.mean(peak_demands)) if peak_demands else Power.from_kw(0)