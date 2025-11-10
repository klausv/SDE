"""
Yearly Orchestrator for annual investment analysis.

Runs 52 weekly optimizations with persistent state for profitability analysis.
"""

from datetime import datetime
from typing import Optional
import pandas as pd
import numpy as np
from tqdm import tqdm

from src.config.simulation_config import SimulationConfig
from src.data.data_manager import DataManager, TimeSeriesData
from src.optimization.base_optimizer import BaseOptimizer
from src.optimization.optimizer_factory import OptimizerFactory
from src.operational.state_manager import BatterySystemState
from src.simulation.simulation_results import SimulationResults


class YearlyOrchestrator:
    """
    Orchestrator for yearly simulations.

    Executes 52 weekly optimizations with persistent battery state for
    annual investment analysis.
    """

    def __init__(self, config: SimulationConfig):
        """
        Initialize yearly orchestrator.

        Args:
            config: Simulation configuration
        """
        self.config = config
        self.data_manager = DataManager(config)
        self.optimizer: Optional[BaseOptimizer] = None
        self.battery_state: Optional[BatterySystemState] = None

    def run(self) -> SimulationResults:
        """
        Execute yearly simulation (52 weekly optimizations).

        Returns:
            SimulationResults with full trajectory and metrics

        Raises:
            RuntimeError: If simulation fails
        """
        print(f"\n{'='*70}")
        print(f"Yearly Simulation (52 Weekly Optimizations)")
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

        # Initialize battery state
        print("\nInitializing battery state...")
        initial_soc_kwh = self.config.battery.capacity_kwh * (self.config.battery.initial_soc_percent / 100.0)
        self.battery_state = BatterySystemState(
            current_soc_kwh=initial_soc_kwh,
            battery_capacity_kwh=self.config.battery.capacity_kwh,
        )
        print(f"  Initial SOC: {self.battery_state.current_soc_percent:.1f}%")

        # Get year from data
        year = data.timestamps[0].year

        # Run weekly optimizations
        print(f"\nRunning {self.config.yearly.weeks} weekly optimizations...")
        all_trajectories = []
        weekly_summaries = []

        for week in tqdm(range(1, self.config.yearly.weeks + 1), desc="Optimizing weeks"):
            try:
                # Extract week data
                week_data = data.get_week(year, week)

                # Run optimization
                result = self.optimizer.optimize(
                    timestamps=week_data.timestamps,
                    pv_production=week_data.pv_production_kw,
                    consumption=week_data.consumption_kw,
                    spot_prices=week_data.prices_nok_per_kwh,
                    battery_state=self.battery_state,
                )

                # Update battery state with final SOC from this week
                if result.E_battery_final is not None:
                    self.battery_state.current_soc_kwh = result.E_battery_final

                # Convert to DataFrame
                week_trajectory = result.to_dataframe(week_data.timestamps)
                all_trajectories.append(week_trajectory)

                # Calculate week summary
                timestep_hours = 1.0 if data.resolution == 'PT60M' else 0.25
                week_summary = {
                    'year': year,
                    'week': week,
                    'start_date': week_data.timestamps[0].date(),
                    'end_date': week_data.timestamps[-1].date(),
                    'total_charged_kwh': float(result.P_charge.sum() * timestep_hours),
                    'total_discharged_kwh': float(result.P_discharge.sum() * timestep_hours),
                    'total_import_kwh': float(result.P_grid_import.sum() * timestep_hours),
                    'total_export_kwh': float(result.P_grid_export.sum() * timestep_hours),
                    'energy_cost_nok': float(result.energy_cost),
                    'power_cost_nok': float(result.power_cost) if result.power_cost is not None else 0.0,
                    'degradation_cost_nok': float(result.degradation_cost) if result.degradation_cost is not None else 0.0,
                    'total_cost_nok': float(result.objective_value),
                    'final_soc_percent': self.battery_state.current_soc_percent,
                }
                weekly_summaries.append(week_summary)

            except ValueError as e:
                print(f"  Warning: Skipping week {week} - {e}")
                continue
            except Exception as e:
                print(f"  Error in week {week}: {e}")
                raise RuntimeError(f"Weekly optimization failed for week {week}: {e}")

        # Combine all trajectories
        trajectory_df = pd.concat(all_trajectories, axis=0)

        # Weekly summary DataFrame
        weekly_summary_df = pd.DataFrame(weekly_summaries)

        # Calculate monthly aggregates from weekly data
        monthly_summary_df = self._aggregate_to_monthly(weekly_summary_df)

        # Calculate overall economic metrics
        economic_metrics = self._calculate_economic_metrics(weekly_summary_df, monthly_summary_df)

        print(f"\nYearly simulation complete!")
        print(f"  Total weeks: {len(weekly_summaries)}")
        print(f"  Final SOC: {self.battery_state.current_soc_percent:.1f}%")
        print(f"  Annual cost: {economic_metrics['total_cost_nok']:,.0f} NOK")

        results = SimulationResults(
            mode='yearly',
            start_date=data.timestamps[0].to_pydatetime(),
            end_date=data.timestamps[-1].to_pydatetime(),
            trajectory=trajectory_df,
            monthly_summary=monthly_summary_df,
            economic_metrics=economic_metrics,
            battery_final_state=self.battery_state,
            metadata={
                'weeks_optimized': self.config.yearly.weeks,
                'horizon_hours': self.config.yearly.horizon_hours,
                'battery_capacity_kwh': self.config.battery.capacity_kwh,
                'battery_power_kw': self.config.battery.power_kw,
                'resolution': data.resolution,
            }
        )

        return results

    def _aggregate_to_monthly(self, weekly_summary: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate weekly summaries to monthly level.

        Args:
            weekly_summary: DataFrame with weekly results

        Returns:
            DataFrame with monthly aggregates
        """
        # Convert week to approximate month (rough grouping)
        weekly_summary['month'] = ((weekly_summary['week'] - 1) // 4) + 1
        weekly_summary['month'] = weekly_summary['month'].clip(upper=12)

        monthly = weekly_summary.groupby('month').agg({
            'total_charged_kwh': 'sum',
            'total_discharged_kwh': 'sum',
            'total_import_kwh': 'sum',
            'total_export_kwh': 'sum',
            'energy_cost_nok': 'sum',
            'power_cost_nok': 'sum',
            'degradation_cost_nok': 'sum',
            'total_cost_nok': 'sum',
        }).reset_index()

        monthly['year'] = weekly_summary['year'].iloc[0]

        return monthly

    def _calculate_economic_metrics(
        self,
        weekly_summary: pd.DataFrame,
        monthly_summary: pd.DataFrame
    ) -> dict:
        """
        Calculate overall economic metrics from weekly and monthly summaries.

        Args:
            weekly_summary: DataFrame with weekly results
            monthly_summary: DataFrame with monthly aggregates

        Returns:
            Dictionary of economic metrics
        """
        metrics = {
            'total_weeks': len(weekly_summary),
            'total_charged_kwh': float(weekly_summary['total_charged_kwh'].sum()),
            'total_discharged_kwh': float(weekly_summary['total_discharged_kwh'].sum()),
            'total_import_kwh': float(weekly_summary['total_import_kwh'].sum()),
            'total_export_kwh': float(weekly_summary['total_export_kwh'].sum()),
            'total_energy_cost_nok': float(weekly_summary['energy_cost_nok'].sum()),
            'total_power_cost_nok': float(weekly_summary['power_cost_nok'].sum()),
            'total_degradation_cost_nok': float(weekly_summary['degradation_cost_nok'].sum()),
            'total_cost_nok': float(weekly_summary['total_cost_nok'].sum()),
            'avg_weekly_cost_nok': float(weekly_summary['total_cost_nok'].mean()),
            'avg_monthly_cost_nok': float(monthly_summary['total_cost_nok'].mean()),
        }

        # Calculate roundtrip efficiency
        if metrics['total_charged_kwh'] > 0:
            metrics['roundtrip_efficiency'] = metrics['total_discharged_kwh'] / metrics['total_charged_kwh']
        else:
            metrics['roundtrip_efficiency'] = 0.0

        return metrics
