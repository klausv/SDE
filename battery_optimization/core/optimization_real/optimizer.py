"""
Main optimization engine for battery sizing and economic analysis
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple
from dataclasses import dataclass
import logging
from scipy.optimize import differential_evolution

from .battery_model import BatteryModel, BatterySpec
from .economic_model import EconomicModel, EconomicResults
from ..config import SystemConfig, LnettTariff, BatteryConfig, EconomicConfig
from ..data_fetchers.solar_production import SolarProductionModel

logger = logging.getLogger(__name__)

@dataclass
class OptimizationResult:
    """Optimization result container"""
    optimal_capacity_kwh: float
    optimal_power_kw: float
    optimal_c_rate: float
    max_battery_cost_per_kwh: float
    npv_at_target_cost: float
    economic_results: EconomicResults
    operation_metrics: Dict[str, float]
    sensitivity_data: pd.DataFrame

class BatteryOptimizer:
    """Main optimization class for battery system sizing"""

    def __init__(
        self,
        system_config: SystemConfig,
        tariff: LnettTariff,
        battery_config: BatteryConfig,
        economic_config: EconomicConfig
    ):
        """
        Initialize optimizer

        Args:
            system_config: PV system configuration
            tariff: Grid tariff structure
            battery_config: Battery technical parameters
            economic_config: Economic parameters
        """
        self.system_config = system_config
        self.tariff = tariff
        self.battery_config = battery_config
        self.economic_config = economic_config

        # Initialize models
        self.pv_model = SolarProductionModel(
            pv_capacity_kwp=system_config.pv_capacity_kwp,
            inverter_capacity_kw=system_config.inverter_capacity_kw,
            latitude=system_config.location_lat,
            longitude=system_config.location_lon,
            tilt=system_config.tilt,
            azimuth=system_config.azimuth
        )

        self.economic_model = EconomicModel(tariff, economic_config)

    def optimize_battery_size(
        self,
        pv_production: pd.Series,
        spot_prices: pd.Series,
        load_profile: pd.Series,
        target_battery_cost: float = 3000,  # NOK/kWh
        capacity_range: Tuple[float, float] = (10, 200),
        power_range: Tuple[float, float] = (10, 100),
        strategy: str = 'combined'
    ) -> OptimizationResult:
        """
        Optimize battery size for maximum NPV

        Args:
            pv_production: PV production profile (kW)
            spot_prices: Spot prices (NOK/kWh)
            load_profile: Load consumption (kW)
            target_battery_cost: Target battery cost for optimization (NOK/kWh)
            capacity_range: Min/max battery capacity (kWh)
            power_range: Min/max battery power (kW)
            strategy: Operation strategy

        Returns:
            Optimization results
        """
        logger.info("Starting battery optimization...")

        # Define objective function
        def objective(x):
            """
            This Python function named "objective" takes a tuple x as input containing two values
            (capacity_kwh and power_kw) and does not have any specific implementation provided.
            
            :param x: The `objective` function takes a tuple `x` as input, where `x` contains two
            elements: `capacity_kwh` and `power_kw`. These elements represent the capacity in
            kilowatt-hours and power in kilowatts, respectively
            """
            capacity_kwh, power_kw = x

            # Create battery spec
            spec = BatterySpec(
                capacity_kwh=capacity_kwh,
                power_kw=power_kw,
                efficiency=self.battery_config.round_trip_efficiency,
                min_soc=self.battery_config.min_soc,
                max_soc=self.battery_config.max_soc,
                degradation_rate=self.battery_config.degradation_rate_yearly
            )

            # Simulate battery operation
            battery = BatteryModel(spec)
            operation_results = battery.simulate_operation(
                pv_production,
                spot_prices,
                load_profile,
                self.system_config.grid_capacity_kw,
                strategy
            )

            # Calculate NPV
            economic_results = self.economic_model.calculate_npv(
                operation_results,
                spot_prices,
                load_profile,
                target_battery_cost,
                capacity_kwh,
                power_kw
            )

            # Return negative NPV for minimization
            return -economic_results.npv

        # Optimization bounds
        bounds = [capacity_range, power_range]

        # Run optimization
        result = differential_evolution(
            objective,
            bounds,
            maxiter=50,
            popsize=15,
            workers=-1,  # Use all available cores
            seed=42
        )

        # Extract optimal values
        optimal_capacity, optimal_power = result.x
        optimal_c_rate = optimal_power / optimal_capacity

        logger.info(f"Optimal battery size: {optimal_capacity:.1f} kWh, {optimal_power:.1f} kW")

        # Run final simulation with optimal parameters
        optimal_spec = BatterySpec(
            capacity_kwh=optimal_capacity,
            power_kw=optimal_power,
            efficiency=self.battery_config.round_trip_efficiency,
            min_soc=self.battery_config.min_soc,
            max_soc=self.battery_config.max_soc
        )

        battery = BatteryModel(optimal_spec)
        operation_results = battery.simulate_operation(
            pv_production,
            spot_prices,
            load_profile,
            self.system_config.grid_capacity_kw,
            strategy
        )

        # Calculate final economics
        economic_results = self.economic_model.calculate_npv(
            operation_results,
            spot_prices,
            load_profile,
            target_battery_cost,
            optimal_capacity,
            optimal_power
        )

        # Calculate operation metrics
        operation_metrics = battery.calculate_battery_metrics(operation_results)

        # Find break-even battery cost
        max_battery_cost = self._find_breakeven_cost(
            operation_results,
            spot_prices,
            load_profile,
            optimal_capacity,
            optimal_power
        )

        # Run sensitivity analysis
        sensitivity_data = self._run_sensitivity_analysis(
            pv_production,
            spot_prices,
            load_profile,
            optimal_capacity,
            optimal_power,
            strategy
        )

        return OptimizationResult(
            optimal_capacity_kwh=optimal_capacity,
            optimal_power_kw=optimal_power,
            optimal_c_rate=optimal_c_rate,
            max_battery_cost_per_kwh=max_battery_cost,
            npv_at_target_cost=economic_results.npv,
            economic_results=economic_results,
            operation_metrics=operation_metrics,
            sensitivity_data=sensitivity_data
        )

    def _find_breakeven_cost(
        self,
        operation_results: Dict[str, pd.Series],
        spot_prices: pd.Series,
        load_profile: pd.Series,
        capacity_kwh: float,
        power_kw: float,
        tolerance: float = 10
    ) -> float:
        """
        Find break-even battery cost (NPV = 0)

        Args:
            operation_results: Battery operation results
            spot_prices: Spot prices
            load_profile: Load profile
            capacity_kwh: Battery capacity
            power_kw: Battery power
            tolerance: Cost tolerance (NOK/kWh)

        Returns:
            Break-even battery cost (NOK/kWh)
        """
        low_cost = 100
        high_cost = 10000

        while high_cost - low_cost > tolerance:
            mid_cost = (low_cost + high_cost) / 2

            economic_results = self.economic_model.calculate_npv(
                operation_results,
                spot_prices,
                load_profile,
                mid_cost,
                capacity_kwh,
                power_kw
            )

            if economic_results.npv > 0:
                low_cost = mid_cost
            else:
                high_cost = mid_cost

        return (low_cost + high_cost) / 2

    def _run_sensitivity_analysis(
        self,
        pv_production: pd.Series,
        spot_prices: pd.Series,
        load_profile: pd.Series,
        optimal_capacity: float,
        optimal_power: float,
        strategy: str
    ) -> pd.DataFrame:
        """
        Run sensitivity analysis on key parameters

        Args:
            pv_production: PV production
            spot_prices: Spot prices
            load_profile: Load profile
            optimal_capacity: Optimal battery capacity
            optimal_power: Optimal battery power
            strategy: Operation strategy

        Returns:
            DataFrame with sensitivity results
        """
        results = []

        # Battery cost sensitivity
        for battery_cost in range(1000, 6000, 500):
            spec = BatterySpec(
                capacity_kwh=optimal_capacity,
                power_kw=optimal_power,
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
                strategy
            )

            economic_results = self.economic_model.calculate_npv(
                operation_results,
                spot_prices,
                load_profile,
                battery_cost,
                optimal_capacity,
                optimal_power
            )

            results.append({
                'parameter': 'battery_cost',
                'value': battery_cost,
                'npv': economic_results.npv,
                'irr': economic_results.irr,
                'payback_years': economic_results.payback_years
            })

        # Discount rate sensitivity
        for discount_rate in [0.03, 0.04, 0.05, 0.06, 0.07]:
            # Temporarily change discount rate
            original_rate = self.economic_config.discount_rate
            self.economic_config.discount_rate = discount_rate

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
                strategy
            )

            economic_results = self.economic_model.calculate_npv(
                operation_results,
                spot_prices,
                load_profile,
                3000,  # Fixed battery cost for this analysis
                optimal_capacity,
                optimal_power
            )

            results.append({
                'parameter': 'discount_rate',
                'value': discount_rate * 100,  # Convert to percentage
                'npv': economic_results.npv,
                'irr': economic_results.irr,
                'payback_years': economic_results.payback_years
            })

            # Restore original rate
            self.economic_config.discount_rate = original_rate

        return pd.DataFrame(results)

    def run_comprehensive_analysis(
        self,
        year: int = 2024,
        use_cache: bool = True
    ) -> Dict:
        """
        Run comprehensive battery optimization analysis

        Args:
            year: Year for analysis
            use_cache: Whether to use cached data

        Returns:
            Comprehensive analysis results
        """
        logger.info(f"Running comprehensive analysis for year {year}")

        # Fetch data
        logger.info("Fetching PV production data...")
        pv_production, pv_stats = self.pv_model.calculate_annual_production(year, use_cache)

        logger.info("Fetching spot price data...")
        # This would normally fetch from ENTSO-E API
        # For now, create sample data
        spot_prices = self._generate_sample_spot_prices(len(pv_production))

        logger.info("Generating load profile...")
        load_profile = self._generate_sample_load_profile(len(pv_production))

        # Run optimization
        logger.info("Running optimization...")
        optimization_result = self.optimize_battery_size(
            pv_production,
            spot_prices,
            load_profile,
            target_battery_cost=3000
        )

        # Compile results
        comprehensive_results = {
            'pv_statistics': pv_stats,
            'optimization': optimization_result,
            'spot_price_stats': {
                'mean': spot_prices.mean(),
                'std': spot_prices.std(),
                'min': spot_prices.min(),
                'max': spot_prices.max()
            },
            'load_stats': {
                'total_consumption_mwh': load_profile.sum() / 1000,
                'peak_demand_kw': load_profile.max(),
                'average_demand_kw': load_profile.mean()
            }
        }

        return comprehensive_results

    def _generate_sample_spot_prices(self, n_hours: int) -> pd.Series:
        """Generate sample spot prices for testing"""
        # Create realistic price pattern
        base_price = 0.8  # NOK/kWh
        hourly_pattern = np.array([
            0.7, 0.7, 0.7, 0.7, 0.8, 0.9,  # 00-06
            1.0, 1.2, 1.3, 1.2, 1.1, 1.0,  # 06-12
            0.9, 0.9, 1.0, 1.1, 1.3, 1.4,  # 12-18
            1.3, 1.1, 0.9, 0.8, 0.7, 0.7   # 18-24
        ])

        prices = []
        for i in range(n_hours):
            hour = i % 24
            daily_var = np.random.normal(0, 0.1)
            price = base_price * hourly_pattern[hour] * (1 + daily_var)
            prices.append(max(0.1, price))

        return pd.Series(prices)

    def _generate_sample_load_profile(self, n_hours: int) -> pd.Series:
        """Generate sample load profile for testing"""
        # Commercial load pattern
        base_load = 30  # kW
        hourly_pattern = np.array([
            0.3, 0.3, 0.3, 0.3, 0.3, 0.4,  # 00-06
            0.6, 0.8, 1.0, 1.0, 1.0, 0.9,  # 06-12
            0.7, 0.8, 0.9, 1.0, 0.9, 0.7,  # 12-18
            0.5, 0.4, 0.3, 0.3, 0.3, 0.3   # 18-24
        ])

        loads = []
        for i in range(n_hours):
            hour = i % 24
            daily_var = np.random.normal(0, 0.05)
            load = base_load * hourly_pattern[hour] * (1 + daily_var)
            loads.append(max(5, load))

        return pd.Series(loads)