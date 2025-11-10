"""
Simulation results dataclass with export capabilities.

Provides unified result structure for all simulation modes.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime

from src.operational.state_manager import BatterySystemState


@dataclass
class SimulationResults:
    """
    Unified simulation results for all modes.

    Contains full trajectory data, aggregated metrics, and economic analysis.
    """
    # Metadata
    mode: str  # 'rolling_horizon', 'monthly', or 'yearly'
    start_date: datetime
    end_date: datetime

    # Full time-series trajectory
    trajectory: pd.DataFrame

    # Monthly aggregated summary
    monthly_summary: pd.DataFrame

    # Economic metrics
    economic_metrics: Dict[str, float] = field(default_factory=dict)

    # Final battery state
    battery_final_state: Optional[BatterySystemState] = None

    # Metadata about simulation
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and compute derived metrics."""
        if self.trajectory.empty:
            raise ValueError("Trajectory DataFrame is empty")

        # Ensure monthly_summary exists
        if self.monthly_summary is None or self.monthly_summary.empty:
            self.monthly_summary = self._compute_monthly_summary()

    def _compute_monthly_summary(self) -> pd.DataFrame:
        """Compute monthly summary from trajectory."""
        if 'timestamp' not in self.trajectory.columns:
            df = self.trajectory.copy()
        else:
            df = self.trajectory.set_index('timestamp') if 'timestamp' in self.trajectory.columns else self.trajectory.copy()

        # Group by year-month
        monthly = df.groupby([df.index.year, df.index.month]).agg({
            'P_charge_kw': 'sum',
            'P_discharge_kw': 'sum',
            'P_grid_import_kw': 'sum',
            'P_grid_export_kw': 'sum',
            'P_curtail_kw': 'sum',
        })

        monthly.index.names = ['year', 'month']
        return monthly.reset_index()

    def to_csv(self, output_dir: Path) -> None:
        """
        Export results to CSV files.

        Args:
            output_dir: Directory to save CSV files
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save trajectory
        trajectory_path = output_dir / 'trajectory.csv'
        self.trajectory.to_csv(trajectory_path, index=True)

        # Save monthly summary
        monthly_path = output_dir / 'monthly_summary.csv'
        self.monthly_summary.to_csv(monthly_path, index=False)

        # Save economic metrics
        metrics_path = output_dir / 'economic_metrics.csv'
        pd.DataFrame([self.economic_metrics]).to_csv(metrics_path, index=False)

        # Save metadata
        metadata_path = output_dir / 'metadata.csv'
        pd.DataFrame([self.metadata]).to_csv(metadata_path, index=False)

    def to_plots(self, output_dir: Path) -> None:
        """
        Generate and save visualization plots.

        Args:
            output_dir: Directory to save plot files
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("Warning: matplotlib not available, skipping plots")
            return

        # Plot 1: Battery SOC over time
        if 'E_battery_kwh' in self.trajectory.columns:
            fig, ax = plt.subplots(figsize=(12, 4))
            self.trajectory['E_battery_kwh'].plot(ax=ax)
            ax.set_ylabel('Battery SOC (kWh)')
            ax.set_title('Battery State of Charge')
            ax.grid(True)
            plt.tight_layout()
            plt.savefig(output_dir / 'battery_soc.png', dpi=150)
            plt.close()

        # Plot 2: Power flows
        fig, ax = plt.subplots(figsize=(12, 6))
        cols = ['P_charge_kw', 'P_discharge_kw', 'P_grid_import_kw', 'P_grid_export_kw']
        available_cols = [c for c in cols if c in self.trajectory.columns]
        if available_cols:
            self.trajectory[available_cols].plot(ax=ax)
            ax.set_ylabel('Power (kW)')
            ax.set_title('Power Flows')
            ax.legend(['Charge', 'Discharge', 'Grid Import', 'Grid Export'])
            ax.grid(True)
            plt.tight_layout()
            plt.savefig(output_dir / 'power_flows.png', dpi=150)
            plt.close()

        # Plot 3: Monthly summary
        if not self.monthly_summary.empty:
            fig, ax = plt.subplots(figsize=(10, 5))
            self.monthly_summary['P_grid_import_kw'].plot(kind='bar', ax=ax)
            ax.set_ylabel('Grid Import (kWh)')
            ax.set_title('Monthly Grid Import')
            ax.grid(True, axis='y')
            plt.tight_layout()
            plt.savefig(output_dir / 'monthly_import.png', dpi=150)
            plt.close()

    def to_report(self) -> str:
        """
        Generate markdown summary report.

        Returns:
            Markdown-formatted report string
        """
        report = f"# Battery Optimization Results\n\n"
        report += f"**Mode:** {self.mode}\n\n"
        report += f"**Period:** {self.start_date.date()} to {self.end_date.date()}\n\n"

        # Economic metrics
        if self.economic_metrics:
            report += "## Economic Metrics\n\n"
            for key, value in self.economic_metrics.items():
                if isinstance(value, (int, float)):
                    report += f"- **{key}**: {value:,.2f}\n"
                else:
                    report += f"- **{key}**: {value}\n"
            report += "\n"

        # Trajectory summary
        report += "## Simulation Summary\n\n"
        report += f"- **Total timesteps**: {len(self.trajectory)}\n"

        if 'P_charge_kw' in self.trajectory.columns:
            total_charged = self.trajectory['P_charge_kw'].sum()
            total_discharged = self.trajectory['P_discharge_kw'].sum()
            report += f"- **Total charged**: {total_charged:,.1f} kWh\n"
            report += f"- **Total discharged**: {total_discharged:,.1f} kWh\n"

        if 'P_grid_import_kw' in self.trajectory.columns:
            total_import = self.trajectory['P_grid_import_kw'].sum()
            total_export = self.trajectory['P_grid_export_kw'].sum()
            report += f"- **Total grid import**: {total_import:,.1f} kWh\n"
            report += f"- **Total grid export**: {total_export:,.1f} kWh\n"

        # Monthly summary
        if not self.monthly_summary.empty:
            report += "\n## Monthly Breakdown\n\n"
            report += self.monthly_summary.to_markdown(index=False)
            report += "\n"

        return report

    def save_all(self, output_dir: Path, save_plots: bool = True) -> None:
        """
        Save all results to directory.

        Args:
            output_dir: Directory to save all results
            save_plots: Whether to generate and save plots
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save CSV files
        self.to_csv(output_dir)

        # Save plots
        if save_plots:
            self.to_plots(output_dir)

        # Save report
        report_path = output_dir / 'report.md'
        with open(report_path, 'w') as f:
            f.write(self.to_report())

        print(f"Results saved to: {output_dir.absolute()}")
