"""
Sensitivity analysis for battery optimization
"""
import numpy as np
import pandas as pd
from typing import List, Tuple
import logging

from ..optimization.battery_model import BatteryModel, BatterySpec
from ..optimization.economic_model import EconomicModel
from ..config import SystemConfig, LnettTariff, BatteryConfig, EconomicConfig

logger = logging.getLogger(__name__)

class SensitivityAnalyzer:
    """Comprehensive sensitivity analysis for battery system"""

    def __init__(
        self,
        system_config: SystemConfig,
        tariff: LnettTariff,
        battery_config: BatteryConfig,
        economic_config: EconomicConfig
    ):
        """
        Initialize sensitivity analyzer

        Args:
            system_config: PV system configuration
            tariff: Grid tariff
            battery_config: Battery parameters
            economic_config: Economic parameters
        """
        self.system_config = system_config
        self.tariff = tariff
        self.battery_config = battery_config
        self.economic_config = economic_config
        self.economic_model = EconomicModel(tariff, economic_config)

    def analyze_battery_sizing(
        self,
        pv_production: pd.Series,
        spot_prices: pd.Series,
        load_profile: pd.Series,
        capacity_range: Tuple[float, float] = (10, 200),
        power_range: Tuple[float, float] = (10, 100),
        n_points: int = 20
    ) -> pd.DataFrame:
        """
        Analyze NPV across different battery sizes

        Args:
            pv_production: PV production profile
            spot_prices: Electricity prices
            load_profile: Load consumption
            capacity_range: Range of battery capacities to test
            power_range: Range of battery power ratings to test
            n_points: Number of points in each dimension

        Returns:
            DataFrame with sizing analysis results
        """
        capacities = np.linspace(capacity_range[0], capacity_range[1], n_points)
        powers = np.linspace(power_range[0], power_range[1], n_points)

        results = []

        for capacity in capacities:
            for power in powers:
                # Skip unrealistic combinations
                c_rate = power / capacity
                if c_rate < 0.2 or c_rate > 2.0:
                    continue

                spec = BatterySpec(
                    capacity_kwh=capacity,
                    power_kw=power,
                    efficiency=self.battery_config.round_trip_efficiency,
                    min_soc=self.battery_config.min_soc,
                    max_soc=self.battery_config.max_soc
                )

                battery = BatteryModel(spec)
                operation_results = battery.simulate_operation(
                    pv_production,
                    spot_prices,
                    load_profile,
                    self.system_config.grid_capacity_kw,
                    strategy='combined'
                )

                # Calculate economics for different battery costs
                for battery_cost in [2000, 3000, 4000, 5000]:
                    economic_results = self.economic_model.calculate_npv(
                        operation_results,
                        spot_prices,
                        load_profile,
                        battery_cost,
                        capacity,
                        power
                    )

                    results.append({
                        'capacity_kwh': capacity,
                        'power_kw': power,
                        'c_rate': c_rate,
                        'battery_cost_per_kwh': battery_cost,
                        'npv': economic_results.npv,
                        'irr': economic_results.irr,
                        'payback_years': economic_results.payback_years,
                        'annual_savings': economic_results.annual_savings
                    })

        return pd.DataFrame(results)

    def analyze_price_sensitivity(
        self,
        pv_production: pd.Series,
        spot_prices: pd.Series,
        load_profile: pd.Series,
        optimal_capacity: float,
        optimal_power: float,
        volatility_factors: List[float] = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    ) -> pd.DataFrame:
        """
        Analyze sensitivity to electricity price volatility

        Args:
            pv_production: PV production
            spot_prices: Base spot prices
            load_profile: Load consumption
            optimal_capacity: Optimal battery capacity
            optimal_power: Optimal battery power
            volatility_factors: Multipliers for price volatility

        Returns:
            DataFrame with price sensitivity results
        """
        results = []
        base_mean = spot_prices.mean()

        for vol_factor in volatility_factors:
            # Adjust price volatility while maintaining mean
            adjusted_prices = base_mean + (spot_prices - base_mean) * vol_factor
            adjusted_prices = adjusted_prices.clip(lower=0.1)  # Ensure positive prices

            spec = BatterySpec(
                capacity_kwh=optimal_capacity,
                power_kw=optimal_power,
                efficiency=self.battery_config.round_trip_efficiency
            )

            battery = BatteryModel(spec)
            operation_results = battery.simulate_operation(
                pv_production,
                adjusted_prices,
                load_profile,
                self.system_config.grid_capacity_kw,
                strategy='combined'
            )

            economic_results = self.economic_model.calculate_npv(
                operation_results,
                adjusted_prices,
                load_profile,
                3000,  # Fixed battery cost
                optimal_capacity,
                optimal_power
            )

            results.append({
                'volatility_factor': vol_factor,
                'price_std': adjusted_prices.std(),
                'price_mean': adjusted_prices.mean(),
                'npv': economic_results.npv,
                'irr': economic_results.irr,
                'arbitrage_revenue': economic_results.revenue_breakdown['arbitrage']
            })

        return pd.DataFrame(results)

    def analyze_tariff_sensitivity(
        self,
        pv_production: pd.Series,
        spot_prices: pd.Series,
        load_profile: pd.Series,
        optimal_capacity: float,
        optimal_power: float,
        tariff_multipliers: List[float] = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    ) -> pd.DataFrame:
        """
        Analyze sensitivity to grid tariff changes

        Args:
            pv_production: PV production
            spot_prices: Spot prices
            load_profile: Load consumption
            optimal_capacity: Optimal battery capacity
            optimal_power: Optimal battery power
            tariff_multipliers: Multipliers for tariff rates

        Returns:
            DataFrame with tariff sensitivity results
        """
        results = []
        original_tariff = self.tariff.power_tariff_brackets.copy()

        for multiplier in tariff_multipliers:
            # Adjust tariff rates
            for key in self.tariff.power_tariff_brackets:
                self.tariff.power_tariff_brackets[key] = original_tariff[key] * multiplier

            spec = BatterySpec(
                capacity_kwh=optimal_capacity,
                power_kw=optimal_power,
                efficiency=self.battery_config.round_trip_efficiency
            )

            battery = BatteryModel(spec)
            operation_results = battery.simulate_operation(
                pv_production,
                spot_prices,
                load_profile,
                self.system_config.grid_capacity_kw,
                strategy='combined'
            )

            economic_results = self.economic_model.calculate_npv(
                operation_results,
                spot_prices,
                load_profile,
                3000,
                optimal_capacity,
                optimal_power
            )

            results.append({
                'tariff_multiplier': multiplier,
                'npv': economic_results.npv,
                'irr': economic_results.irr,
                'peak_reduction_savings': economic_results.revenue_breakdown['peak_reduction']
            })

        # Restore original tariff
        self.tariff.power_tariff_brackets = original_tariff

        return pd.DataFrame(results)

    def analyze_degradation_impact(
        self,
        pv_production: pd.Series,
        spot_prices: pd.Series,
        load_profile: pd.Series,
        optimal_capacity: float,
        optimal_power: float,
        degradation_rates: List[float] = [0.01, 0.015, 0.02, 0.025, 0.03]
    ) -> pd.DataFrame:
        """
        Analyze impact of battery degradation rates

        Args:
            pv_production: PV production
            spot_prices: Spot prices
            load_profile: Load consumption
            optimal_capacity: Optimal battery capacity
            optimal_power: Optimal battery power
            degradation_rates: Annual degradation rates to test

        Returns:
            DataFrame with degradation impact results
        """
        results = []
        original_rate = self.economic_config.degradation_rate_yearly

        for deg_rate in degradation_rates:
            self.economic_config.degradation_rate_yearly = deg_rate

            spec = BatterySpec(
                capacity_kwh=optimal_capacity,
                power_kw=optimal_power,
                efficiency=self.battery_config.round_trip_efficiency,
                degradation_rate=deg_rate
            )

            battery = BatteryModel(spec)
            operation_results = battery.simulate_operation(
                pv_production,
                spot_prices,
                load_profile,
                self.system_config.grid_capacity_kw,
                strategy='combined'
            )

            economic_results = self.economic_model.calculate_npv(
                operation_results,
                spot_prices,
                load_profile,
                3000,
                optimal_capacity,
                optimal_power
            )

            # Calculate capacity after 10 years
            capacity_10y = optimal_capacity * (1 - deg_rate * 10)

            results.append({
                'degradation_rate': deg_rate * 100,  # Convert to percentage
                'npv': economic_results.npv,
                'irr': economic_results.irr,
                'capacity_10y': capacity_10y,
                'capacity_retention_10y': capacity_10y / optimal_capacity
            })

        # Restore original rate
        self.economic_config.degradation_rate_yearly = original_rate

        return pd.DataFrame(results)

    def generate_break_even_surface(
        self,
        pv_production: pd.Series,
        spot_prices: pd.Series,
        load_profile: pd.Series,
        capacity_range: Tuple[float, float] = (20, 150),
        power_range: Tuple[float, float] = (10, 80),
        n_points: int = 15
    ) -> pd.DataFrame:
        """
        Generate break-even battery cost surface

        Args:
            pv_production: PV production
            spot_prices: Spot prices
            load_profile: Load consumption
            capacity_range: Range of capacities
            power_range: Range of power ratings
            n_points: Number of points in each dimension

        Returns:
            DataFrame with break-even costs
        """
        capacities = np.linspace(capacity_range[0], capacity_range[1], n_points)
        powers = np.linspace(power_range[0], power_range[1], n_points)

        results = []

        for capacity in capacities:
            for power in powers:
                c_rate = power / capacity
                if c_rate < 0.2 or c_rate > 2.0:
                    continue

                spec = BatterySpec(
                    capacity_kwh=capacity,
                    power_kw=power,
                    efficiency=self.battery_config.round_trip_efficiency
                )

                battery = BatteryModel(spec)
                operation_results = battery.simulate_operation(
                    pv_production,
                    spot_prices,
                    load_profile,
                    self.system_config.grid_capacity_kw,
                    strategy='combined'
                )

                # Binary search for break-even cost
                low_cost = 100
                high_cost = 10000

                while high_cost - low_cost > 10:
                    mid_cost = (low_cost + high_cost) / 2

                    economic_results = self.economic_model.calculate_npv(
                        operation_results,
                        spot_prices,
                        load_profile,
                        mid_cost,
                        capacity,
                        power
                    )

                    if economic_results.npv > 0:
                        low_cost = mid_cost
                    else:
                        high_cost = mid_cost

                break_even_cost = (low_cost + high_cost) / 2

                results.append({
                    'capacity_kwh': capacity,
                    'power_kw': power,
                    'c_rate': c_rate,
                    'break_even_cost': break_even_cost
                })

        return pd.DataFrame(results)