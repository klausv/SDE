"""
Monthly Orchestrator for monthly battery optimization analysis.

Runs single-solve optimizations for one or more months.
"""

from datetime import datetime
from typing import List
import pandas as pd
import numpy as np
from tqdm import tqdm

from src.config.simulation_config import SimulationConfig
from src.data.data_manager import DataManager, TimeSeriesData
from src.optimization.base_optimizer import BaseOptimizer
from src.optimization.optimizer_factory import OptimizerFactory
from src.simulation.simulation_results import SimulationResults


class MonthlyOrchestrator:
    """
    Orchestrator for monthly optimizations.

    Runs full-month single-solve optimizations for specified months.
    """

    def __init__(self, config: SimulationConfig):
        """
        Initialize monthly orchestrator.

        Args:
            config: Simulation configuration
        """
        self.config = config
        self.data_manager = DataManager(config)
        self.optimizer: Optional[BaseOptimizer] = None

    def run(self) -> SimulationResults:
        """
        Execute monthly optimization.

        Returns:
            SimulationResults with full trajectory and metrics

        Raises:
            RuntimeError: If simulation fails
        """
        print(f"\n{'='*70}")
        print(f"Monthly Optimization")
        print(f"{'='*70}")

        # Load data
        print("Loading data...")
        data = self.data_manager.load_data()
        print(f"  Loaded {len(data)} timesteps")
        print(f"  Period: {data.timestamps[0]} to {data.timestamps[-1]}")
        print(f"  Resolution: {data.resolution}")

        # Create optimizer
        print("\nCreating optimizer...")
        self.optimizer = OptimizerFactory.create_from_config(self.config)

        # Get list of months to optimize
        months_to_run = self.config.monthly.get_month_list()
        year = self.config.simulation_period.get_start_datetime().year

        print(f"\nOptimizing months: {months_to_run}")

        # Run optimization for each month
        all_trajectories = []
        monthly_summaries = []

        for month in tqdm(months_to_run, desc="Optimizing months"):
            try:
                # Extract month data
                month_data = data.get_month(year, month)

                # Initial SOC (50% by default, or from config)
                initial_soc_kwh = self.config.battery.capacity_kwh * (
                    self.config.battery.initial_soc_percent / 100.0
                )

                # Run optimization
                result = self.optimizer.optimize(
                    timestamps=month_data.timestamps,
                    pv_production=month_data.pv_production_kw,
                    consumption=month_data.consumption_kw,
                    spot_prices=month_data.prices_nok_per_kwh,
                    initial_soc_kwh=initial_soc_kwh,
                )

                # Convert to DataFrame
                month_trajectory = result.to_dataframe(month_data.timestamps)
                all_trajectories.append(month_trajectory)

                # Calculate month summary
                timestep_hours = 1.0 if data.resolution == 'PT60M' else 0.25
                month_summary = {
                    'year': year,
                    'month': month,
                    'total_charged_kwh': float(result.P_charge.sum() * timestep_hours),
                    'total_discharged_kwh': float(result.P_discharge.sum() * timestep_hours),
                    'total_import_kwh': float(result.P_grid_import.sum() * timestep_hours),
                    'total_export_kwh': float(result.P_grid_export.sum() * timestep_hours),
                    'energy_cost_nok': float(result.energy_cost),
                    'power_cost_nok': float(result.power_cost) if result.power_cost is not None else 0.0,
                    'degradation_cost_nok': float(result.degradation_cost) if result.degradation_cost is not None else 0.0,
                    'total_cost_nok': float(result.objective_value),
                }
                monthly_summaries.append(month_summary)

                print(f"  Month {month}: Total cost = {result.objective_value:,.0f} NOK")

            except ValueError as e:
                print(f"  Warning: Skipping month {month} - {e}")
                continue
            except Exception as e:
                print(f"  Error in month {month}: {e}")
                raise RuntimeError(f"Monthly optimization failed for month {month}: {e}")

        # Combine all trajectories
        trajectory_df = pd.concat(all_trajectories, axis=0)

        # Monthly summary DataFrame
        monthly_summary_df = pd.DataFrame(monthly_summaries)

        # Calculate overall economic metrics
        economic_metrics = self._calculate_economic_metrics(monthly_summary_df)

        print(f"\nOptimization complete!")
        print(f"  Total months: {len(monthly_summaries)}")
        print(f"  Total cost: {economic_metrics['total_cost_nok']:,.0f} NOK")

        results = SimulationResults(
            mode='monthly',
            start_date=data.timestamps[0].to_pydatetime(),
            end_date=data.timestamps[-1].to_pydatetime(),
            trajectory=trajectory_df,
            monthly_summary=monthly_summary_df,
            economic_metrics=economic_metrics,
            battery_final_state=None,
            metadata={
                'months_optimized': months_to_run,
                'battery_capacity_kwh': self.config.battery.capacity_kwh,
                'battery_power_kw': self.config.battery.power_kw,
                'resolution': data.resolution,
            }
        )

        return results

    def _calculate_economic_metrics(self, monthly_summary: pd.DataFrame) -> dict:
        """
        Calculate overall economic metrics from monthly summaries.

        Args:
            monthly_summary: DataFrame with monthly results

        Returns:
            Dictionary of economic metrics
        """
        metrics = {
            'total_charged_kwh': float(monthly_summary['total_charged_kwh'].sum()),
            'total_discharged_kwh': float(monthly_summary['total_discharged_kwh'].sum()),
            'total_import_kwh': float(monthly_summary['total_import_kwh'].sum()),
            'total_export_kwh': float(monthly_summary['total_export_kwh'].sum()),
            'total_energy_cost_nok': float(monthly_summary['energy_cost_nok'].sum()),
            'total_power_cost_nok': float(monthly_summary['power_cost_nok'].sum()),
            'total_degradation_cost_nok': float(monthly_summary['degradation_cost_nok'].sum()),
            'total_cost_nok': float(monthly_summary['total_cost_nok'].sum()),
            'avg_monthly_cost_nok': float(monthly_summary['total_cost_nok'].mean()),
        }

        return metrics
