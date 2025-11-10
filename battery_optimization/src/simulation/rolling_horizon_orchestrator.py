"""
Rolling Horizon Orchestrator for real-time battery optimization.

Manages persistent state and executes rolling 24h optimizations with configurable
update frequency.
"""

from datetime import datetime, timedelta
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


class RollingHorizonOrchestrator:
    """
    Orchestrator for rolling horizon simulations.

    Executes rolling 24h optimizations with persistent battery state tracking
    across the entire simulation period.
    """

    def __init__(self, config: SimulationConfig):
        """
        Initialize rolling horizon orchestrator.

        Args:
            config: Simulation configuration
        """
        self.config = config
        self.data_manager = DataManager(config)
        self.optimizer: Optional[BaseOptimizer] = None
        self.battery_state: Optional[BatterySystemState] = None

    def run(self) -> SimulationResults:
        """
        Execute rolling horizon simulation.

        Returns:
            SimulationResults with full trajectory and metrics

        Raises:
            RuntimeError: If simulation fails
        """
        print(f"\n{'='*70}")
        print(f"Rolling Horizon Simulation")
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
        start_datetime = data.timestamps[0].to_pydatetime()
        self.battery_state = BatterySystemState(
            current_soc_kwh=initial_soc_kwh,
            battery_capacity_kwh=self.config.battery.capacity_kwh,
            month_start_date=start_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            last_update=start_datetime,
        )
        print(f"  Initial SOC: {self.battery_state.current_soc_percent:.1f}%")

        # Run rolling horizon iterations
        print("\nRunning rolling horizon optimization...")

        # Calculate number of iterations
        horizon_hours = self.config.rolling_horizon.horizon_hours
        update_freq_hours = self.config.rolling_horizon.update_frequency_minutes / 60.0
        end_datetime = data.timestamps[-1].to_pydatetime()
        total_hours = (end_datetime - start_datetime).total_seconds() / 3600

        num_iterations = int(total_hours / update_freq_hours)

        # Pre-allocate arrays for better performance (C1 fix)
        trajectory_arrays = {
            'timestamp': np.empty(num_iterations, dtype='datetime64[ns]'),
            'P_charge_kw': np.zeros(num_iterations),
            'P_discharge_kw': np.zeros(num_iterations),
            'P_grid_import_kw': np.zeros(num_iterations),
            'P_grid_export_kw': np.zeros(num_iterations),
            'E_battery_kwh': np.zeros(num_iterations),
            'P_curtail_kw': np.zeros(num_iterations),
            'soc_percent': np.zeros(num_iterations),
        }

        current_time = start_datetime
        completed_iterations = 0

        for i in tqdm(range(num_iterations), desc="Optimizing"):
            # Extract window
            try:
                # Allow partial windows to handle DST transitions (spring forward/fall back)
                window_data = data.get_window(current_time, horizon_hours, allow_partial=True)
            except ValueError:
                # Reached end of data
                break

            # Run optimization
            try:
                result = self.optimizer.optimize(
                    timestamps=window_data.timestamps,
                    pv_production=window_data.pv_production_kw,
                    consumption=window_data.consumption_kw,
                    spot_prices=window_data.prices_nok_per_kwh,
                    battery_state=self.battery_state,
                )
            except Exception as e:
                print(f"\nOptimization failed at {current_time}: {e}")
                break

            # Execute first control action
            if len(result.P_charge) > 0:
                # Update battery state with first timestep
                timestep_hours = 1.0 if data.resolution == 'PT60M' else 0.25

                # Calculate net power and energy change
                net_power_kw = result.P_charge[0] - result.P_discharge[0]
                energy_change_kwh = net_power_kw * timestep_hours * self.config.battery.efficiency

                # Update SOC
                new_soc = self.battery_state.current_soc_kwh + energy_change_kwh
                new_soc = np.clip(
                    new_soc,
                    self.config.battery.capacity_kwh * self.config.battery.min_soc_percent / 100.0,
                    self.config.battery.capacity_kwh * self.config.battery.max_soc_percent / 100.0
                )

                # Update state
                self.battery_state.current_soc_kwh = new_soc

                # Track monthly peak (simplified - actual implementation would need tariff logic)
                grid_import = result.P_grid_import[0]
                if current_time.month != self.battery_state.month_start_date.month:
                    # Month boundary - reset peak
                    self.battery_state.current_monthly_peak_kw = grid_import
                    self.battery_state.month_start_date = current_time
                else:
                    self.battery_state.current_monthly_peak_kw = max(
                        self.battery_state.current_monthly_peak_kw,
                        grid_import
                    )

                # Store first timestep result in pre-allocated arrays
                trajectory_arrays['timestamp'][i] = np.datetime64(window_data.timestamps[0])
                trajectory_arrays['P_charge_kw'][i] = result.P_charge[0]
                trajectory_arrays['P_discharge_kw'][i] = result.P_discharge[0]
                trajectory_arrays['P_grid_import_kw'][i] = result.P_grid_import[0]
                trajectory_arrays['P_grid_export_kw'][i] = result.P_grid_export[0]
                trajectory_arrays['E_battery_kwh'][i] = result.E_battery[0]
                trajectory_arrays['P_curtail_kw'][i] = result.P_curtail[0]
                trajectory_arrays['soc_percent'][i] = (result.E_battery[0] / self.config.battery.capacity_kwh) * 100.0

                completed_iterations += 1

            # Advance time by update frequency
            current_time += timedelta(hours=update_freq_hours)

        # Trim arrays to actual completed iterations
        if completed_iterations < num_iterations:
            for key in trajectory_arrays:
                trajectory_arrays[key] = trajectory_arrays[key][:completed_iterations]

        # Convert to DataFrame
        trajectory_df = pd.DataFrame(trajectory_arrays)
        trajectory_df.set_index('timestamp', inplace=True)

        # Create results
        print(f"\nSimulation complete!")
        print(f"  Total timesteps: {len(trajectory_df)}")
        print(f"  Final SOC: {self.battery_state.current_soc_percent:.1f}%")

        # Calculate economic metrics (simplified)
        economic_metrics = self._calculate_economic_metrics(trajectory_df, data)

        results = SimulationResults(
            mode='rolling_horizon',
            start_date=start_datetime,
            end_date=current_time,
            trajectory=trajectory_df,
            monthly_summary=pd.DataFrame(),  # Will be computed in __post_init__
            economic_metrics=economic_metrics,
            battery_final_state=self.battery_state,
            metadata={
                'horizon_hours': horizon_hours,
                'update_frequency_minutes': self.config.rolling_horizon.update_frequency_minutes,
                'battery_capacity_kwh': self.config.battery.capacity_kwh,
                'battery_power_kw': self.config.battery.power_kw,
            }
        )

        return results

    def _calculate_economic_metrics(
        self,
        trajectory: pd.DataFrame,
        data: TimeSeriesData
    ) -> dict:
        """
        Calculate economic metrics from trajectory.

        Args:
            trajectory: Simulation trajectory DataFrame
            data: Input time series data

        Returns:
            Dictionary of economic metrics
        """
        timestep_hours = 1.0 if data.resolution == 'PT60M' else 0.25

        # Calculate energy flows
        total_charged_kwh = trajectory['P_charge_kw'].sum() * timestep_hours
        total_discharged_kwh = trajectory['P_discharge_kw'].sum() * timestep_hours
        total_import_kwh = trajectory['P_grid_import_kw'].sum() * timestep_hours
        total_export_kwh = trajectory['P_grid_export_kw'].sum() * timestep_hours
        total_curtailed_kwh = trajectory['P_curtail_kw'].sum() * timestep_hours

        # Get average prices (simplified)
        aligned_prices = data.prices_nok_per_kwh[:len(trajectory)]
        avg_price = np.mean(aligned_prices) if len(aligned_prices) > 0 else 0.0

        # Estimate costs (simplified - actual would need full tariff calculation)
        estimated_cost_nok = total_import_kwh * avg_price
        estimated_revenue_nok = total_export_kwh * avg_price

        metrics = {
            'total_charged_kwh': float(total_charged_kwh),
            'total_discharged_kwh': float(total_discharged_kwh),
            'total_import_kwh': float(total_import_kwh),
            'total_export_kwh': float(total_export_kwh),
            'total_curtailed_kwh': float(total_curtailed_kwh),
            'avg_price_nok_per_kwh': float(avg_price),
            'estimated_cost_nok': float(estimated_cost_nok),
            'estimated_revenue_nok': float(estimated_revenue_nok),
            'net_cost_nok': float(estimated_cost_nok - estimated_revenue_nok),
        }

        return metrics
