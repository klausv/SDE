"""
Use case for sensitivity analysis
"""
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

from config import ConfigurationManager
from application.use_cases.optimize_battery import (
    OptimizeBatteryUseCase,
    OptimizeBatteryRequest
)


@dataclass
class SensitivityAnalysisRequest:
    """Request for sensitivity analysis"""
    base_battery_cost: float
    battery_cost_range: Tuple[float, float] = (1000, 5000)
    battery_cost_steps: int = 10
    discount_rate_range: Tuple[float, float] = (0.03, 0.08)
    discount_rate_steps: int = 5
    electricity_price_multipliers: List[float] = None
    parallel_execution: bool = True
    max_workers: int = 4


@dataclass
class SensitivityAnalysisResponse:
    """Response from sensitivity analysis"""
    results_matrix: pd.DataFrame
    optimal_scenarios: pd.DataFrame
    break_even_battery_cost: float
    sensitivity_metrics: Dict[str, Any]


class SensitivityAnalysisUseCase:
    """Use case for running sensitivity analysis"""

    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        self.optimizer_use_case = OptimizeBatteryUseCase(config_manager)

    def execute(self, request: SensitivityAnalysisRequest) -> SensitivityAnalysisResponse:
        """
        Execute sensitivity analysis across multiple parameters

        Args:
            request: Sensitivity analysis parameters

        Returns:
            Analysis results with sensitivity metrics
        """
        # Generate parameter grid
        parameter_grid = self._generate_parameter_grid(request)

        # Run optimizations
        if request.parallel_execution:
            results = self._run_parallel_optimizations(
                parameter_grid,
                request.max_workers
            )
        else:
            results = self._run_sequential_optimizations(parameter_grid)

        # Analyze results
        results_df = pd.DataFrame(results)
        break_even_cost = self._find_break_even_cost(results_df)
        sensitivity_metrics = self._calculate_sensitivity_metrics(results_df)
        optimal_scenarios = self._identify_optimal_scenarios(results_df)

        return SensitivityAnalysisResponse(
            results_matrix=results_df,
            optimal_scenarios=optimal_scenarios,
            break_even_battery_cost=break_even_cost,
            sensitivity_metrics=sensitivity_metrics
        )

    def _generate_parameter_grid(
        self,
        request: SensitivityAnalysisRequest
    ) -> List[Dict[str, Any]]:
        """Generate parameter combinations for analysis"""
        battery_costs = np.linspace(
            request.battery_cost_range[0],
            request.battery_cost_range[1],
            request.battery_cost_steps
        )

        discount_rates = np.linspace(
            request.discount_rate_range[0],
            request.discount_rate_range[1],
            request.discount_rate_steps
        )

        if request.electricity_price_multipliers is None:
            price_multipliers = [0.8, 1.0, 1.2]
        else:
            price_multipliers = request.electricity_price_multipliers

        # Create all combinations
        grid = []
        for battery_cost in battery_costs:
            for discount_rate in discount_rates:
                for price_mult in price_multipliers:
                    grid.append({
                        'battery_cost_nok_per_kwh': battery_cost,
                        'discount_rate': discount_rate,
                        'electricity_price_multiplier': price_mult,
                        'scenario_id': len(grid)
                    })

        return grid

    def _run_parallel_optimizations(
        self,
        parameter_grid: List[Dict[str, Any]],
        max_workers: int
    ) -> List[Dict[str, Any]]:
        """Run optimizations in parallel"""
        results = []

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_params = {
                executor.submit(
                    self._run_single_optimization,
                    params
                ): params for params in parameter_grid
            }

            # Collect results as they complete
            for future in as_completed(future_to_params):
                params = future_to_params[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Optimization failed for {params}: {e}")
                    # Add failed result
                    results.append({
                        **params,
                        'status': 'failed',
                        'error': str(e)
                    })

        return results

    def _run_sequential_optimizations(
        self,
        parameter_grid: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Run optimizations sequentially"""
        results = []

        for params in parameter_grid:
            try:
                result = self._run_single_optimization(params)
                results.append(result)
            except Exception as e:
                print(f"Optimization failed for {params}: {e}")
                results.append({
                    **params,
                    'status': 'failed',
                    'error': str(e)
                })

        return results

    def _run_single_optimization(
        self,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run a single optimization with given parameters"""
        # Create temporary config with overrides
        temp_config = ConfigurationManager(self.config.loader.config_dir)
        temp_config.load()

        # Apply parameter overrides
        temp_config.economic.discount_rate = params['discount_rate']

        # Create optimizer with modified config
        optimizer = OptimizeBatteryUseCase(temp_config)

        # Run optimization
        request = OptimizeBatteryRequest(
            battery_cost_nok_per_kwh=params['battery_cost_nok_per_kwh'],
            optimization_metric='npv',
            use_cached_data=True
        )

        response = optimizer.execute(request)

        # Combine parameters with results
        return {
            **params,
            'status': 'success',
            'optimal_capacity_kwh': response.optimal_capacity_kwh,
            'optimal_power_kw': response.optimal_power_kw,
            'npv_nok': response.npv_nok,
            'irr_percentage': response.irr_percentage,
            'payback_years': response.payback_years,
            'annual_savings_nok': response.annual_savings_nok
        }

    def _find_break_even_cost(self, results_df: pd.DataFrame) -> float:
        """Find break-even battery cost where NPV = 0"""
        # Filter successful results with base scenario
        base_results = results_df[
            (results_df['status'] == 'success') &
            (results_df['electricity_price_multiplier'] == 1.0)
        ].copy()

        if base_results.empty:
            return None

        # Sort by battery cost
        base_results = base_results.sort_values('battery_cost_nok_per_kwh')

        # Find where NPV crosses zero
        positive_npv = base_results[base_results['npv_nok'] > 0]
        negative_npv = base_results[base_results['npv_nok'] <= 0]

        if positive_npv.empty or negative_npv.empty:
            # No crossing point found
            if positive_npv.empty:
                return base_results['battery_cost_nok_per_kwh'].min()
            else:
                return base_results['battery_cost_nok_per_kwh'].max()

        # Linear interpolation at crossing point
        last_positive = positive_npv.iloc[-1]
        first_negative = negative_npv.iloc[0]

        cost_diff = first_negative['battery_cost_nok_per_kwh'] - last_positive['battery_cost_nok_per_kwh']
        npv_diff = first_negative['npv_nok'] - last_positive['npv_nok']

        if npv_diff != 0:
            break_even = last_positive['battery_cost_nok_per_kwh'] - (
                last_positive['npv_nok'] * cost_diff / npv_diff
            )
        else:
            break_even = (
                last_positive['battery_cost_nok_per_kwh'] +
                first_negative['battery_cost_nok_per_kwh']
            ) / 2

        return break_even

    def _calculate_sensitivity_metrics(
        self,
        results_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Calculate sensitivity metrics for each parameter"""
        successful = results_df[results_df['status'] == 'success']

        if successful.empty:
            return {}

        metrics = {}

        # NPV sensitivity to battery cost
        if len(successful['battery_cost_nok_per_kwh'].unique()) > 1:
            cost_correlation = successful[['battery_cost_nok_per_kwh', 'npv_nok']].corr().iloc[0, 1]
            metrics['npv_sensitivity_to_battery_cost'] = abs(cost_correlation)

        # NPV sensitivity to discount rate
        if len(successful['discount_rate'].unique()) > 1:
            discount_correlation = successful[['discount_rate', 'npv_nok']].corr().iloc[0, 1]
            metrics['npv_sensitivity_to_discount_rate'] = abs(discount_correlation)

        # Optimal size sensitivity
        metrics['capacity_range_kwh'] = {
            'min': successful['optimal_capacity_kwh'].min(),
            'max': successful['optimal_capacity_kwh'].max(),
            'mean': successful['optimal_capacity_kwh'].mean(),
            'std': successful['optimal_capacity_kwh'].std()
        }

        # Best case scenario
        best_npv_row = successful.loc[successful['npv_nok'].idxmax()]
        metrics['best_scenario'] = {
            'battery_cost': best_npv_row['battery_cost_nok_per_kwh'],
            'discount_rate': best_npv_row['discount_rate'],
            'npv': best_npv_row['npv_nok'],
            'capacity': best_npv_row['optimal_capacity_kwh']
        }

        return metrics

    def _identify_optimal_scenarios(
        self,
        results_df: pd.DataFrame,
        top_n: int = 10
    ) -> pd.DataFrame:
        """Identify top performing scenarios"""
        successful = results_df[results_df['status'] == 'success'].copy()

        if successful.empty:
            return pd.DataFrame()

        # Rank by NPV
        successful['npv_rank'] = successful['npv_nok'].rank(ascending=False)

        # Rank by IRR
        successful['irr_rank'] = successful['irr_percentage'].rank(ascending=False)

        # Rank by payback period (lower is better)
        successful['payback_rank'] = successful['payback_years'].rank(ascending=True)

        # Combined score (equal weight)
        successful['combined_score'] = (
            successful['npv_rank'] +
            successful['irr_rank'] +
            successful['payback_rank']
        ) / 3

        # Sort by combined score
        optimal = successful.nsmallest(top_n, 'combined_score')

        return optimal[[
            'battery_cost_nok_per_kwh',
            'discount_rate',
            'electricity_price_multiplier',
            'optimal_capacity_kwh',
            'optimal_power_kw',
            'npv_nok',
            'irr_percentage',
            'payback_years',
            'combined_score'
        ]]