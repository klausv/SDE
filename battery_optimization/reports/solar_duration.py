"""
Solar duration curve report for battery optimization analysis.

This module creates duration curve visualization showing solar production
distribution over a year with system capacity limits.
"""

from pathlib import Path
from typing import Optional, Union
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from core.reporting.report_generator import ReportGenerator
from core.reporting.result_models import SimulationResult
from config import config


class SolarDurationCurveReport(ReportGenerator):
    """
    Generate solar production duration curve with capacity markers.

    Shows solar production distribution sorted from highest to lowest,
    with markers for:
    - PV capacity (kWp DC)
    - Inverter limit (kW AC) - red marker
    - Grid export limit (kW AC) - green marker

    X-axis shows percentage of time (0-100%)
    Y-axis shows power output (kW)
    """

    def __init__(
        self,
        results: Union[SimulationResult, list],
        output_dir: Path = Path("results"),
        pv_capacity_kwp: Optional[float] = None,
        inverter_limit_kw: Optional[float] = None,
        grid_limit_kw: Optional[float] = None
    ):
        """
        Initialize solar duration curve report.

        Args:
            results: SimulationResult(s) containing solar production data
            output_dir: Base directory for outputs
            pv_capacity_kwp: PV DC capacity (defaults to config)
            inverter_limit_kw: Inverter AC limit (defaults to config)
            grid_limit_kw: Grid export limit (defaults to config)
        """
        super().__init__(results, output_dir)

        # System capacities
        self.pv_capacity_kwp = pv_capacity_kwp or config.solar.pv_capacity_kwp
        self.inverter_limit_kw = inverter_limit_kw or config.solar.inverter_capacity_kw
        self.grid_limit_kw = grid_limit_kw or config.solar.grid_export_limit_kw

    def generate(self) -> Path:
        """
        Generate solar duration curve report.

        Returns:
            Path to generated markdown report file
        """
        # Extract production data from first result
        result = self.results[0]
        production_ac = result.production_ac_kw
        production_dc = result.production_dc_kw

        if len(production_ac) == 0:
            raise ValueError("No production data available in simulation result")

        # Create duration curve (sorted high to low)
        production_sorted = np.sort(production_ac)[::-1]

        # Calculate statistics
        stats = self._calculate_statistics(production_ac, production_dc)

        # Generate visualizations
        self._plot_duration_curve_full(production_sorted, stats)

        # Generate markdown report
        report_path = self._write_markdown_report(stats)

        return report_path

    def _calculate_statistics(
        self,
        production_ac: np.ndarray,
        production_dc: np.ndarray
    ) -> dict:
        """Calculate key statistics for the report."""

        total_hours = len(production_ac)

        # Production statistics
        annual_production_kwh = np.sum(production_ac)
        max_ac_kw = np.max(production_ac)
        max_dc_kw = np.max(production_dc)

        # Capacity factors
        capacity_factor_ac = annual_production_kwh / (self.inverter_limit_kw * total_hours)
        capacity_factor_dc = np.sum(production_dc) / (self.pv_capacity_kwp * total_hours)

        # Hours above limits
        hours_above_grid = np.sum(production_ac > self.grid_limit_kw)
        hours_above_inverter = np.sum(production_ac > self.inverter_limit_kw * 0.99)

        # Curtailment calculations
        curtailment_at_grid = np.sum(np.maximum(0, production_ac - self.grid_limit_kw))
        curtailment_at_inverter = np.sum(np.maximum(0, production_dc - self.inverter_limit_kw))

        # Percentages
        pct_above_grid = (hours_above_grid / total_hours) * 100
        pct_above_inverter = (hours_above_inverter / total_hours) * 100
        curtailment_pct = (curtailment_at_grid / annual_production_kwh) * 100 if annual_production_kwh > 0 else 0

        return {
            'total_hours': total_hours,
            'annual_production_kwh': annual_production_kwh,
            'annual_production_mwh': annual_production_kwh / 1000,
            'max_ac_kw': max_ac_kw,
            'max_dc_kw': max_dc_kw,
            'capacity_factor_ac': capacity_factor_ac,
            'capacity_factor_dc': capacity_factor_dc,
            'hours_above_grid': hours_above_grid,
            'hours_above_inverter': hours_above_inverter,
            'pct_above_grid': pct_above_grid,
            'pct_above_inverter': pct_above_inverter,
            'curtailment_at_grid_kwh': curtailment_at_grid,
            'curtailment_at_inverter_kwh': curtailment_at_inverter,
            'curtailment_pct': curtailment_pct,
            'specific_yield': annual_production_kwh / self.pv_capacity_kwp
        }

    def _plot_duration_curve_full(
        self,
        production_sorted: np.ndarray,
        stats: dict
    ) -> Path:
        """
        Plot full duration curve with percentage x-axis.

        Args:
            production_sorted: Solar production sorted high to low
            stats: Statistics dictionary

        Returns:
            Path to saved figure
        """
        fig, ax = plt.subplots(figsize=(14, 8))

        # X-axis: percentage of time (0-100%)
        total_hours = len(production_sorted)
        hours = np.arange(total_hours)
        percent_of_time = (hours / total_hours) * 100

        # Plot duration curve
        ax.fill_between(
            percent_of_time,
            0,
            production_sorted,
            color='gold',
            alpha=0.3,
            label='AC Production'
        )
        ax.plot(
            percent_of_time,
            production_sorted,
            color='darkorange',
            linewidth=2
        )

        # Marker for makseffekt - RED circle on y-axis
        max_production = np.max(production_sorted)
        ax.scatter(
            [0],  # On y-axis (0% of time)
            [max_production],
            s=250,
            color='red',
            marker='o',
            edgecolors='darkred',
            linewidths=2.5,
            zorder=10,
            label=f'Max effekt: {max_production:.1f} kW',
            clip_on=False
        )

        # Annotation for max effect
        ax.annotate(
            f'{max_production:.1f} kW',
            xy=(0, max_production),
            xytext=(3, max_production),
            fontsize=13,
            color='red',
            fontweight='bold',
            va='center'
        )

        # Marker 1: PV capacity (DC kWp) - blue dashed line with RED circle
        ax.axhline(
            y=self.pv_capacity_kwp,
            color='blue',
            linestyle=':',
            linewidth=2,
            alpha=0.7
        )

        # Find where production crosses kWp capacity
        if np.any(production_sorted >= self.pv_capacity_kwp * 0.99):
            kwp_x_idx = np.where(production_sorted >= self.pv_capacity_kwp * 0.99)[0][-1]
            kwp_x = (kwp_x_idx / total_hours) * 100

            # RED circle marker at kWp intersection
            ax.scatter(
                [kwp_x],
                [self.pv_capacity_kwp],
                s=200,
                color='red',
                marker='o',
                edgecolors='darkred',
                linewidths=2,
                zorder=5,
                label=f'PV Capacity: {self.pv_capacity_kwp:.1f} kWp (DC)'
            )

            # Annotation for kWp
            ax.annotate(
                f'{self.pv_capacity_kwp:.1f} kWp',
                xy=(kwp_x, self.pv_capacity_kwp),
                xytext=(kwp_x + 5, self.pv_capacity_kwp + 5),
                fontsize=15,  # 50% increase from 10
                color='red',
                fontweight='bold',
                arrowprops=dict(
                    arrowstyle='->',
                    color='red',
                    lw=2.0  # Thicker arrow
                )
            )
        else:
            # Just label if never reached
            ax.text(
                95, self.pv_capacity_kwp + 2,
                f'PV: {self.pv_capacity_kwp:.1f} kWp',
                fontsize=14,  # 50% increase from 9
                color='blue',
                style='italic',
                ha='right'
            )

        # Marker 2: Inverter limit - RED circle/marker
        inverter_y = self.inverter_limit_kw
        # Find where production crosses inverter limit
        if np.any(production_sorted >= inverter_y * 0.99):
            inverter_x_idx = np.where(production_sorted >= inverter_y * 0.99)[0][-1]
            inverter_x = (inverter_x_idx / total_hours) * 100

            # Red horizontal line
            ax.axhline(
                y=inverter_y,
                color='red',
                linestyle='-',
                linewidth=2.5,
                alpha=0.8
            )

            # Red circle marker at intersection
            ax.scatter(
                [inverter_x],
                [inverter_y],
                s=200,
                color='red',
                marker='o',
                edgecolors='darkred',
                linewidths=2,
                zorder=5,
                label=f'Inverter Limit: {inverter_y:.0f} kW (AC)'
            )

            # Annotation for inverter
            ax.annotate(
                f'{inverter_y:.0f} kW\n({stats["hours_above_inverter"]:.0f} timer)',
                xy=(inverter_x, inverter_y),
                xytext=(inverter_x + 5, inverter_y + 5),
                fontsize=15,  # 50% increase from 10
                color='red',
                fontweight='bold',
                arrowprops=dict(
                    arrowstyle='->',
                    color='red',
                    lw=2.0  # Thicker arrow
                )
            )
        else:
            # Just horizontal line if never reached
            ax.axhline(
                y=inverter_y,
                color='red',
                linestyle='-',
                linewidth=2.5,
                alpha=0.8,
                label=f'Inverter Limit: {inverter_y:.0f} kW (AC)'
            )

        # Marker 3: Grid export limit - green
        grid_y = self.grid_limit_kw
        # Find where production crosses grid limit
        if np.any(production_sorted >= grid_y):
            grid_x_idx = np.where(production_sorted >= grid_y)[0][-1]
            grid_x = (grid_x_idx / total_hours) * 100

            # Green horizontal line
            ax.axhline(
                y=grid_y,
                color='darkgreen',
                linestyle='-',
                linewidth=2.5,
                alpha=0.8
            )

            # Green circle marker
            ax.scatter(
                [grid_x],
                [grid_y],
                s=200,
                color='green',
                marker='o',
                edgecolors='darkgreen',
                linewidths=2,
                zorder=5,
                label=f'Grid Limit: {grid_y:.0f} kW'
            )

            # Annotation for grid limit
            ax.annotate(
                f'{grid_y:.0f} kW\n({stats["hours_above_grid"]:.0f} timer)',
                xy=(grid_x, grid_y),
                xytext=(grid_x + 5, grid_y - 8),
                fontsize=15,  # 50% increase from 10
                color='darkgreen',
                fontweight='bold',
                arrowprops=dict(
                    arrowstyle='->',
                    color='darkgreen',
                    lw=2.0  # Thicker arrow
                )
            )
        else:
            ax.axhline(
                y=grid_y,
                color='darkgreen',
                linestyle='-',
                linewidth=2.5,
                alpha=0.8,
                label=f'Grid Limit: {grid_y:.0f} kW'
            )

        # Shaded regions
        # Area above grid limit (potential curtailment)
        ax.fill_between(
            percent_of_time,
            grid_y,
            np.minimum(production_sorted, self.inverter_limit_kw),
            where=(production_sorted > grid_y),
            color='orange',
            alpha=0.3,
            label='Potensiell avkorting'
        )

        # Statistics text box
        stats_text = (
            f'Årsproduksjon: {stats["annual_production_mwh"]:.1f} MWh\n'
            f'Spesifikk: {stats["specific_yield"]:.0f} kWh/kWp\n'
            f'Kapasitetsfaktor: {stats["capacity_factor_ac"]*100:.1f}%\n'
            f'Maks AC: {stats["max_ac_kw"]:.1f} kW\n'
            f'Timer > {grid_y:.0f} kW: {stats["hours_above_grid"]:.0f} ({stats["pct_above_grid"]:.1f}%)\n'
            f'Avkorting: {stats["curtailment_at_grid_kwh"]:.0f} kWh ({stats["curtailment_pct"]:.1f}%)'
        )

        ax.text(
            0.98,
            0.97,
            stats_text,
            transform=ax.transAxes,
            fontsize=17,  # 50% increase from 11
            verticalalignment='top',
            horizontalalignment='right',
            bbox=dict(
                boxstyle='round',
                facecolor='wheat',
                alpha=0.9,
                edgecolor='black'
            )
        )

        # Formatting with 50% larger fonts
        ax.set_xlabel('% av tiden', fontsize=20, fontweight='bold')  # 50% increase from 13
        ax.set_ylabel('Effekt [kW]', fontsize=20, fontweight='bold')  # 50% increase from 13
        ax.set_title(
            f'Varighetskurve - Solproduksjon\n'
            f'{self.pv_capacity_kwp:.1f} kWp / {self.inverter_limit_kw:.0f} kW inverter / '
            f'{self.grid_limit_kw:.0f} kW nettgrense',
            fontsize=21,  # 50% increase from 14
            fontweight='bold'
        )
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim(0, 100)
        ax.set_ylim(0, max(self.pv_capacity_kwp * 1.1, np.max(production_sorted) * 1.1))

        # Increase tick label font sizes
        ax.tick_params(axis='both', which='major', labelsize=15)  # 50% increase from 10

        # Get all handles and labels, remove duplicates
        handles, labels = ax.get_legend_handles_labels()

        # Remove duplicates while preserving order
        unique_labels = []
        unique_handles = []
        for handle, label in zip(handles, labels):
            if label not in unique_labels:
                unique_labels.append(label)
                unique_handles.append(handle)

        # Single combined legend with deduplicated items
        ax.legend(
            unique_handles,
            unique_labels,
            loc='upper right',
            fontsize=15,  # 50% increase from 10
            framealpha=0.95,
            edgecolor='black',
            fancybox=True,
            shadow=True
        )

        plt.tight_layout()

        # Save figure
        figure_path = self.save_figure(fig, 'duration_curve_full.png', 'solar_duration')
        plt.close(fig)

        return figure_path

    def _plot_duration_curve_zoom(
        self,
        production_sorted: np.ndarray,
        stats: dict
    ) -> Path:
        """
        Plot zoomed duration curve showing top production hours.

        Args:
            production_sorted: Solar production sorted high to low
            stats: Statistics dictionary

        Returns:
            Path to saved figure
        """
        fig, ax = plt.subplots(figsize=(14, 7))

        # Zoom to top 10% of hours
        total_hours = len(production_sorted)
        zoom_hours = int(total_hours * 0.1)  # Top 10%

        hours_zoom = np.arange(zoom_hours)
        percent_zoom = (hours_zoom / total_hours) * 100
        production_zoom = production_sorted[:zoom_hours]

        # Plot
        ax.fill_between(
            percent_zoom,
            0,
            production_zoom,
            color='gold',
            alpha=0.3
        )
        ax.plot(
            percent_zoom,
            production_zoom,
            color='darkorange',
            linewidth=2,
            label='AC Production'
        )

        # Limits
        ax.axhline(
            y=self.inverter_limit_kw,
            color='red',
            linestyle='-',
            linewidth=2.5,
            alpha=0.8,
            label=f'Inverter: {self.inverter_limit_kw:.0f} kW'
        )
        ax.axhline(
            y=self.grid_limit_kw,
            color='darkgreen',
            linestyle='-',
            linewidth=2.5,
            alpha=0.8,
            label=f'Grid: {self.grid_limit_kw:.0f} kW'
        )

        # Shaded curtailment zone
        ax.fill_between(
            percent_zoom,
            self.grid_limit_kw,
            np.minimum(production_zoom, self.inverter_limit_kw),
            where=(production_zoom > self.grid_limit_kw),
            color='orange',
            alpha=0.3,
            label='Curtailment Zone'
        )

        # Formatting with 50% larger fonts
        ax.set_xlabel('% av tiden', fontsize=20, fontweight='bold')  # 50% increase
        ax.set_ylabel('Effekt [kW]', fontsize=20, fontweight='bold')  # 50% increase
        ax.set_title(
            f'Varighetskurve - Zoom på topp 10% ({zoom_hours} timer)',
            fontsize=21,  # 50% increase
            fontweight='bold'
        )
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim(0, 10)

        # Increase tick label font sizes
        ax.tick_params(axis='both', which='major', labelsize=15)  # 50% increase

        # Single legend for zoom plot (simpler, fewer items)
        ax.legend(loc='upper right', fontsize=16, framealpha=0.95, edgecolor='black')  # 50% increase

        plt.tight_layout()

        # Save
        figure_path = self.save_figure(fig, 'duration_curve_zoom.png', 'solar_duration')
        plt.close(fig)

        return figure_path

    def _write_markdown_report(self, stats: dict) -> Path:
        """
        Write markdown report with statistics and figure links.

        Args:
            stats: Statistics dictionary

        Returns:
            Path to markdown report
        """
        timestamp_str = self.report_timestamp.strftime("%Y-%m-%d %H:%M:%S")

        report_lines = [
            "# Varighetskurve - Solproduksjon",
            "",
            f"**Generert:** {timestamp_str}",
            "",
            "## Systemspesifikasjoner",
            "",
            f"- **PV Kapasitet (DC):** {self.pv_capacity_kwp:.1f} kWp",
            f"- **Inverter Grense (AC):** {self.inverter_limit_kw:.0f} kW",
            f"- **Netteksport Grense:** {self.grid_limit_kw:.0f} kW",
            "",
            "## Produksjonsstatistikk",
            "",
            f"- **Årsproduksjon:** {stats['annual_production_mwh']:.1f} MWh ({stats['annual_production_kwh']:.0f} kWh)",
            f"- **Spesifikk produksjon:** {stats['specific_yield']:.0f} kWh/kWp",
            f"- **Kapasitetsfaktor (AC):** {stats['capacity_factor_ac']*100:.1f}%",
            f"- **Kapasitetsfaktor (DC):** {stats['capacity_factor_dc']*100:.1f}%",
            f"- **Maksimal AC effekt:** {stats['max_ac_kw']:.1f} kW",
            f"- **Maksimal DC effekt:** {stats['max_dc_kw']:.1f} kW",
            "",
            "## Avkortingsanalyse",
            "",
            f"### Over Nettgrense ({self.grid_limit_kw:.0f} kW)",
            f"- **Timer over grense:** {stats['hours_above_grid']:.0f} ({stats['pct_above_grid']:.1f}% av året)",
            f"- **Potensiell avkorting:** {stats['curtailment_at_grid_kwh']:.0f} kWh ({stats['curtailment_pct']:.1f}% av produksjon)",
            "",
            f"### Over Invertergrense ({self.inverter_limit_kw:.0f} kW)",
            f"- **Timer over grense:** {stats['hours_above_inverter']:.0f} ({stats['pct_above_inverter']:.1f}% av året)",
            f"- **Avkorting ved inverter:** {stats['curtailment_at_inverter_kwh']:.0f} kWh",
            "",
            "## Varighetskurve",
            "",
            f"![Varighetskurve]({self.figures[0].relative_to(self.output_dir)})",
            "",
            "Varighetskurven viser solproduksjonen sortert fra høyest til lavest over året.",
            "X-aksen viser prosent av tiden (0-100%), Y-aksen viser effekt i kW.",
            "",
            "**Markører:**",
            f"- **Rød sirkel (y-akse):** Maksimal effekt = {stats['max_ac_kw']:.1f} kW",
            f"- **Rød sirkel (kurve):** PV kapasitet (DC) = {self.pv_capacity_kwp:.1f} kWp",
            f"- **Rød sirkel (kurve):** Inverter grense = {self.inverter_limit_kw:.0f} kW",
            f"- **Grønn sirkel (kurve):** Netteksport grense = {self.grid_limit_kw:.0f} kW",
            "- **Oransje område:** Potensielt avkortet energi (over nettgrense)",
            "",
            "## Analyse og anbefalinger",
            "",
            f"Med {stats['hours_above_grid']:.0f} timer ({stats['pct_above_grid']:.1f}%) over nettgrensen på {self.grid_limit_kw:.0f} kW, ",
            f"mister systemet potensielt {stats['curtailment_at_grid_kwh']:.0f} kWh ({stats['curtailment_pct']:.1f}%) av produksjonen til avkorting.",
            "",
        ]

        # Add battery recommendation if significant curtailment
        if stats['curtailment_pct'] > 5:
            curtailment_mwh = stats['curtailment_at_grid_kwh'] / 1000
            report_lines.extend([
                "### Batterianlegg for å redusere avkorting",
                "",
                f"Med {curtailment_mwh:.1f} MWh potensielt avkortet energi, kan et batterianlegg:",
                f"- Lagre overskuddsproduksjon når produksjon > {self.grid_limit_kw:.0f} kW",
                "- Utlade på kveldstid for peak shaving og energiarbitrasje",
                f"- Redusere effekttariff ved å glatte ut effekttopper",
                "",
            ])

        report_lines.append("---")
        report_lines.append(f"*Rapport generert av Battery Optimization System - {timestamp_str}*")

        # Write report
        report_dir = self.output_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        report_filename = f"{self.report_timestamp.strftime('%Y-%m-%d_%H%M%S')}_solar_duration.md"
        report_path = report_dir / report_filename

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        return report_path
