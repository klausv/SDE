"""
Data models for simulation results and analysis outputs.

This module defines standardized data structures for storing and
manipulating battery optimization simulation results.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import json
import pickle


@dataclass
class SimulationResult:
    """
    Structured simulation output with timeseries data and economic summary.

    This dataclass provides a standardized format for simulation results,
    enabling consistent storage, retrieval, and analysis across different
    battery strategies and configurations.

    Attributes:
        scenario_name: Descriptive name for this simulation scenario
        timestamp: DatetimeIndex for all timeseries data

        Timeseries data (all arrays must match timestamp length):
        production_dc_kw: DC solar production before inverter
        production_ac_kw: AC solar production after inverter
        consumption_kw: Building electricity consumption
        grid_power_kw: Net grid power (+ import, - export)
        battery_power_ac_kw: Battery AC power (+ charge, - discharge)
        battery_soc_kwh: Battery state of charge
        curtailment_kw: Curtailed solar production
        spot_price: Electricity spot price per timestep

        Economic summary:
        cost_summary: Dict with keys like 'total_cost_nok', 'energy_cost_nok', etc.

        Metadata:
        battery_config: Battery specifications (capacity_kwh, power_kw, efficiency, etc.)
        strategy_config: Control strategy parameters and settings
        simulation_metadata: Additional info (creation_date, duration, etc.)
    """

    scenario_name: str
    timestamp: pd.DatetimeIndex

    # Timeseries data
    production_dc_kw: np.ndarray
    production_ac_kw: np.ndarray
    consumption_kw: np.ndarray
    grid_power_kw: np.ndarray
    battery_power_ac_kw: np.ndarray
    battery_soc_kwh: np.ndarray
    curtailment_kw: np.ndarray
    spot_price: np.ndarray

    # Economic summary
    cost_summary: Dict[str, float]

    # Metadata
    battery_config: Dict[str, Any]
    strategy_config: Dict[str, Any]
    simulation_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate array lengths match timestamp."""
        expected_len = len(self.timestamp)
        arrays = {
            'production_dc_kw': self.production_dc_kw,
            'production_ac_kw': self.production_ac_kw,
            'consumption_kw': self.consumption_kw,
            'grid_power_kw': self.grid_power_kw,
            'battery_power_ac_kw': self.battery_power_ac_kw,
            'battery_soc_kwh': self.battery_soc_kwh,
            'curtailment_kw': self.curtailment_kw,
            'spot_price': self.spot_price
        }

        for name, arr in arrays.items():
            if len(arr) != expected_len:
                raise ValueError(
                    f"Array {name} length {len(arr)} does not match "
                    f"timestamp length {expected_len}"
                )

        # Set creation timestamp if not provided
        if 'creation_date' not in self.simulation_metadata:
            self.simulation_metadata['creation_date'] = datetime.now().isoformat()

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert timeseries data to pandas DataFrame.

        Returns:
            DataFrame with timestamp index and all timeseries columns
        """
        return pd.DataFrame({
            'production_dc_kw': self.production_dc_kw,
            'production_ac_kw': self.production_ac_kw,
            'consumption_kw': self.consumption_kw,
            'grid_power_kw': self.grid_power_kw,
            'battery_power_ac_kw': self.battery_power_ac_kw,
            'battery_soc_kwh': self.battery_soc_kwh,
            'curtailment_kw': self.curtailment_kw,
            'spot_price': self.spot_price
        }, index=self.timestamp)

    def save(self, base_path: Path) -> Path:
        """
        Save simulation results with versioned directory structure.

        Creates directory: base_path/simulations/YYYY-MM-DD_scenario_name/
        Saves:
        - timeseries.csv: All timeseries data with timestamps
        - summary.json: Economic summary and configuration metadata
        - full_result.pkl: Complete SimulationResult for exact reconstruction

        Args:
            base_path: Root directory for results (e.g., Path('results'))

        Returns:
            Path to created scenario directory
        """
        # Create timestamped scenario directory
        timestamp_str = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        scenario_dir = base_path / 'simulations' / f"{timestamp_str}_{self.scenario_name}"
        scenario_dir.mkdir(parents=True, exist_ok=True)

        # Save timeseries as CSV
        df = self.to_dataframe()
        df.to_csv(scenario_dir / 'timeseries.csv', index=True)

        # Save summary as JSON
        summary = {
            'scenario_name': self.scenario_name,
            'cost_summary': self.cost_summary,
            'battery_config': self.battery_config,
            'strategy_config': self.strategy_config,
            'simulation_metadata': self.simulation_metadata,
            'timestamp_range': {
                'start': str(self.timestamp[0]),
                'end': str(self.timestamp[-1]),
                'count': len(self.timestamp)
            }
        }

        with open(scenario_dir / 'summary.json', 'w') as f:
            json.dump(summary, f, indent=2)

        # Save complete object as pickle for exact reconstruction
        with open(scenario_dir / 'full_result.pkl', 'wb') as f:
            pickle.dump(self, f)

        return scenario_dir

    @classmethod
    def load(cls, scenario_path: Path) -> 'SimulationResult':
        """
        Load simulation result from saved directory.

        Args:
            scenario_path: Path to scenario directory containing saved files

        Returns:
            Reconstructed SimulationResult instance
        """
        # Try loading from pickle first (exact reconstruction)
        pkl_path = scenario_path / 'full_result.pkl'
        if pkl_path.exists():
            with open(pkl_path, 'rb') as f:
                return pickle.load(f)

        # Fallback: reconstruct from CSV + JSON
        # Load timeseries
        df = pd.read_csv(scenario_path / 'timeseries.csv', index_col=0, parse_dates=True)

        # Load summary
        with open(scenario_path / 'summary.json', 'r') as f:
            summary = json.load(f)

        # Reconstruct SimulationResult
        return cls(
            scenario_name=summary['scenario_name'],
            timestamp=df.index,
            production_dc_kw=df['production_dc_kw'].values,
            production_ac_kw=df['production_ac_kw'].values,
            consumption_kw=df['consumption_kw'].values,
            grid_power_kw=df['grid_power_kw'].values,
            battery_power_ac_kw=df['battery_power_ac_kw'].values,
            battery_soc_kwh=df['battery_soc_kwh'].values,
            curtailment_kw=df['curtailment_kw'].values,
            spot_price=df['spot_price'].values,
            cost_summary=summary['cost_summary'],
            battery_config=summary['battery_config'],
            strategy_config=summary['strategy_config'],
            simulation_metadata=summary['simulation_metadata']
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary (excludes large timeseries arrays).

        Useful for logging and debugging without excessive data size.

        Returns:
            Dict with metadata and summary info
        """
        return {
            'scenario_name': self.scenario_name,
            'timestamp_range': {
                'start': str(self.timestamp[0]),
                'end': str(self.timestamp[-1]),
                'count': len(self.timestamp)
            },
            'cost_summary': self.cost_summary,
            'battery_config': self.battery_config,
            'strategy_config': self.strategy_config,
            'simulation_metadata': self.simulation_metadata
        }

    def get_annual_metrics(self) -> Dict[str, float]:
        """
        Calculate key annual performance metrics.

        Returns:
            Dict with annual totals and averages
        """
        timestep_hours = (self.timestamp[1] - self.timestamp[0]).total_seconds() / 3600

        return {
            'production_dc_kwh': float(np.sum(self.production_dc_kw) * timestep_hours),
            'production_ac_kwh': float(np.sum(self.production_ac_kw) * timestep_hours),
            'consumption_kwh': float(np.sum(self.consumption_kw) * timestep_hours),
            'grid_import_kwh': float(np.sum(np.maximum(self.grid_power_kw, 0)) * timestep_hours),
            'grid_export_kwh': float(np.sum(np.maximum(-self.grid_power_kw, 0)) * timestep_hours),
            'curtailment_kwh': float(np.sum(self.curtailment_kw) * timestep_hours),
            'battery_throughput_kwh': float(np.sum(np.abs(self.battery_power_ac_kw)) * timestep_hours / 2),
            'self_consumption_rate': self._calculate_self_consumption_rate(),
            'self_sufficiency_rate': self._calculate_self_sufficiency_rate(),
        }

    def _calculate_self_consumption_rate(self) -> float:
        """Calculate fraction of solar production consumed locally."""
        total_production = np.sum(self.production_ac_kw)
        grid_export = np.sum(np.maximum(-self.grid_power_kw, 0))

        if total_production > 0:
            return float((total_production - grid_export) / total_production)
        return 0.0

    def _calculate_self_sufficiency_rate(self) -> float:
        """Calculate fraction of consumption met by local production."""
        total_consumption = np.sum(self.consumption_kw)
        grid_import = np.sum(np.maximum(self.grid_power_kw, 0))

        if total_consumption > 0:
            return float((total_consumption - grid_import) / total_consumption)
        return 0.0


@dataclass
class ComparisonResult:
    """
    Compare multiple simulation scenarios.

    Attributes:
        scenarios: List of SimulationResult instances to compare
        reference_scenario: Name of baseline scenario for delta calculations
    """

    scenarios: List[SimulationResult]
    reference_scenario: str

    def __post_init__(self):
        """Validate reference scenario exists."""
        scenario_names = [s.scenario_name for s in self.scenarios]
        if self.reference_scenario not in scenario_names:
            raise ValueError(
                f"Reference scenario '{self.reference_scenario}' not found. "
                f"Available: {scenario_names}"
            )

    def calculate_deltas(self) -> pd.DataFrame:
        """
        Calculate cost savings and key metrics vs reference scenario.

        Returns:
            DataFrame with one row per scenario showing deltas
        """
        ref = next(s for s in self.scenarios if s.scenario_name == self.reference_scenario)
        ref_cost = ref.cost_summary['total_cost_nok']
        ref_metrics = ref.get_annual_metrics()

        comparisons = []
        for scenario in self.scenarios:
            if scenario.scenario_name == self.reference_scenario:
                continue

            cost = scenario.cost_summary['total_cost_nok']
            savings = ref_cost - cost
            metrics = scenario.get_annual_metrics()

            comparisons.append({
                'scenario': scenario.scenario_name,
                'annual_cost_nok': cost,
                'annual_savings_nok': savings,
                'savings_pct': (savings / ref_cost * 100) if ref_cost > 0 else 0,
                'battery_capacity_kwh': scenario.battery_config.get('capacity_kwh', 0),
                'battery_power_kw': scenario.battery_config.get('power_kw', 0),
                'curtailment_reduction_kwh': ref_metrics['curtailment_kwh'] - metrics['curtailment_kwh'],
                'self_consumption_rate': metrics['self_consumption_rate'],
                'self_sufficiency_rate': metrics['self_sufficiency_rate']
            })

        return pd.DataFrame(comparisons)

    def get_reference(self) -> SimulationResult:
        """Get the reference scenario result."""
        return next(s for s in self.scenarios if s.scenario_name == self.reference_scenario)

    def get_scenario(self, name: str) -> Optional[SimulationResult]:
        """Get scenario by name."""
        for scenario in self.scenarios:
            if scenario.scenario_name == name:
                return scenario
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert comparison to dictionary."""
        return {
            'reference_scenario': self.reference_scenario,
            'scenarios': [s.to_dict() for s in self.scenarios],
            'deltas': self.calculate_deltas().to_dict(orient='records')
        }
