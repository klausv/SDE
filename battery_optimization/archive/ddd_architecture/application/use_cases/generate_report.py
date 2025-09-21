"""
Use case for generating analysis reports
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import seaborn as sns
from pathlib import Path
from datetime import datetime

from application.use_cases.optimize_battery import OptimizeBatteryResponse
from application.use_cases.sensitivity_analysis import SensitivityAnalysisResponse


@dataclass
class GenerateReportRequest:
    """Request for report generation"""
    optimization_result: Optional[OptimizeBatteryResponse] = None
    sensitivity_result: Optional[SensitivityAnalysisResponse] = None
    output_format: str = 'html'  # 'html', 'pdf', 'markdown'
    output_directory: Path = Path('reports')
    include_visualizations: bool = True
    include_recommendations: bool = True


@dataclass
class GenerateReportResponse:
    """Response from report generation"""
    report_path: Path
    visualizations_created: List[str]
    summary_metrics: Dict[str, Any]


class GenerateReportUseCase:
    """Use case for generating comprehensive analysis reports"""

    def __init__(self):
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    def execute(self, request: GenerateReportRequest) -> GenerateReportResponse:
        """
        Generate comprehensive analysis report

        Args:
            request: Report generation parameters

        Returns:
            Report generation results
        """
        # Create output directory
        request.output_directory.mkdir(parents=True, exist_ok=True)
        report_dir = request.output_directory / f"report_{self.timestamp}"
        report_dir.mkdir(exist_ok=True)

        # Generate visualizations
        visualizations = []
        if request.include_visualizations:
            if request.optimization_result:
                visualizations.extend(
                    self._create_optimization_visualizations(
                        request.optimization_result,
                        report_dir
                    )
                )

            if request.sensitivity_result:
                visualizations.extend(
                    self._create_sensitivity_visualizations(
                        request.sensitivity_result,
                        report_dir
                    )
                )

        # Generate report content
        if request.output_format == 'html':
            report_path = self._generate_html_report(
                request,
                report_dir,
                visualizations
            )
        elif request.output_format == 'markdown':
            report_path = self._generate_markdown_report(
                request,
                report_dir,
                visualizations
            )
        else:
            raise ValueError(f"Unsupported output format: {request.output_format}")

        # Calculate summary metrics
        summary_metrics = self._calculate_summary_metrics(request)

        return GenerateReportResponse(
            report_path=report_path,
            visualizations_created=visualizations,
            summary_metrics=summary_metrics
        )

    def _create_optimization_visualizations(
        self,
        result: OptimizeBatteryResponse,
        output_dir: Path
    ) -> List[str]:
        """Create visualizations for optimization results"""
        visualizations = []

        # 1. Economic metrics bar chart
        fig, ax = plt.subplots(figsize=(10, 6))
        metrics = {
            'NPV': result.npv_nok / 1000,  # Convert to thousands
            'Annual Savings': result.annual_savings_nok / 1000,
            'Investment': result.optimal_capacity_kwh * 3000 / 1000  # Assuming cost
        }
        bars = ax.bar(metrics.keys(), metrics.values())
        ax.set_ylabel('Value (1000 NOK)')
        ax.set_title('Economic Metrics Summary')

        # Color bars based on value
        colors = ['green' if v > 0 else 'red' for v in metrics.values()]
        for bar, color in zip(bars, colors):
            bar.set_color(color)

        plt.tight_layout()
        viz_path = output_dir / 'economic_metrics.png'
        plt.savefig(viz_path, dpi=150)
        plt.close()
        visualizations.append('economic_metrics.png')

        # 2. Battery specifications pie chart
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Capacity utilization
        capacity_data = [
            result.optimal_capacity_kwh,
            200 - result.optimal_capacity_kwh  # Assuming max 200 kWh
        ]
        ax1.pie(
            capacity_data,
            labels=['Optimal Capacity', 'Unused Potential'],
            autopct='%1.1f%%',
            startangle=90,
            colors=['#2E86AB', '#E0E0E0']
        )
        ax1.set_title('Battery Capacity Utilization')

        # Performance metrics
        performance_metrics = {
            'Self-Consumption': result.self_consumption_rate * 100,
            'Peak Reduction': result.peak_reduction_percentage * 100,
            'Grid Import': 100 - result.self_consumption_rate * 100
        }
        ax2.bar(performance_metrics.keys(), performance_metrics.values())
        ax2.set_ylabel('Percentage (%)')
        ax2.set_title('Performance Metrics')
        ax2.set_ylim(0, 100)

        plt.tight_layout()
        viz_path = output_dir / 'battery_specifications.png'
        plt.savefig(viz_path, dpi=150)
        plt.close()
        visualizations.append('battery_specifications.png')

        # 3. Payback timeline
        fig, ax = plt.subplots(figsize=(12, 6))
        years = list(range(16))
        cumulative_cashflow = []
        annual_saving = result.annual_savings_nok
        investment = result.optimal_capacity_kwh * 3000  # Assuming cost

        cumulative = -investment
        for year in years:
            if year > 0:
                cumulative += annual_saving * (0.98 ** year)  # With degradation
            cumulative_cashflow.append(cumulative)

        ax.plot(years, cumulative_cashflow, linewidth=2, marker='o')
        ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        ax.fill_between(years, cumulative_cashflow, 0,
                         where=[cf > 0 for cf in cumulative_cashflow],
                         alpha=0.3, color='green', label='Profit')
        ax.fill_between(years, cumulative_cashflow, 0,
                         where=[cf <= 0 for cf in cumulative_cashflow],
                         alpha=0.3, color='red', label='Loss')

        ax.set_xlabel('Year')
        ax.set_ylabel('Cumulative Cash Flow (NOK)')
        ax.set_title('Payback Timeline')
        ax.grid(True, alpha=0.3)
        ax.legend()

        # Mark payback year
        if result.payback_years < 15:
            ax.axvline(x=result.payback_years, color='g', linestyle=':',
                      label=f'Payback: {result.payback_years:.1f} years')

        plt.tight_layout()
        viz_path = output_dir / 'payback_timeline.png'
        plt.savefig(viz_path, dpi=150)
        plt.close()
        visualizations.append('payback_timeline.png')

        return visualizations

    def _create_sensitivity_visualizations(
        self,
        result: SensitivityAnalysisResponse,
        output_dir: Path
    ) -> List[str]:
        """Create visualizations for sensitivity analysis"""
        visualizations = []

        # 1. NPV heatmap
        if not result.results_matrix.empty:
            fig, ax = plt.subplots(figsize=(12, 8))

            # Pivot data for heatmap
            pivot_data = result.results_matrix.pivot_table(
                values='npv_nok',
                index='battery_cost_nok_per_kwh',
                columns='discount_rate',
                aggfunc='mean'
            )

            sns.heatmap(
                pivot_data / 1000,  # Convert to thousands
                annot=True,
                fmt='.0f',
                cmap='RdYlGn',
                center=0,
                cbar_kws={'label': 'NPV (1000 NOK)'},
                ax=ax
            )

            ax.set_xlabel('Discount Rate')
            ax.set_ylabel('Battery Cost (NOK/kWh)')
            ax.set_title('NPV Sensitivity Analysis')

            plt.tight_layout()
            viz_path = output_dir / 'sensitivity_heatmap.png'
            plt.savefig(viz_path, dpi=150)
            plt.close()
            visualizations.append('sensitivity_heatmap.png')

        # 2. Optimal capacity vs battery cost
        if not result.results_matrix.empty:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

            # Group by battery cost
            cost_groups = result.results_matrix.groupby('battery_cost_nok_per_kwh')

            # Optimal capacity
            avg_capacity = cost_groups['optimal_capacity_kwh'].mean()
            ax1.plot(avg_capacity.index, avg_capacity.values, marker='o', linewidth=2)
            ax1.set_xlabel('Battery Cost (NOK/kWh)')
            ax1.set_ylabel('Optimal Capacity (kWh)')
            ax1.set_title('Optimal Battery Size vs Cost')
            ax1.grid(True, alpha=0.3)

            # IRR
            avg_irr = cost_groups['irr_percentage'].mean()
            ax2.plot(avg_irr.index, avg_irr.values, marker='s', linewidth=2, color='orange')
            ax2.set_xlabel('Battery Cost (NOK/kWh)')
            ax2.set_ylabel('IRR (%)')
            ax2.set_title('Internal Rate of Return vs Cost')
            ax2.axhline(y=10, color='r', linestyle='--', alpha=0.5, label='10% threshold')
            ax2.grid(True, alpha=0.3)
            ax2.legend()

            plt.tight_layout()
            viz_path = output_dir / 'capacity_vs_cost.png'
            plt.savefig(viz_path, dpi=150)
            plt.close()
            visualizations.append('capacity_vs_cost.png')

        # 3. Break-even analysis
        if result.break_even_battery_cost:
            fig, ax = plt.subplots(figsize=(10, 6))

            # Create break-even visualization
            costs = result.results_matrix['battery_cost_nok_per_kwh'].unique()
            costs = sorted(costs)

            npvs = []
            for cost in costs:
                cost_data = result.results_matrix[
                    result.results_matrix['battery_cost_nok_per_kwh'] == cost
                ]
                npvs.append(cost_data['npv_nok'].mean())

            ax.plot(costs, npvs, linewidth=2, marker='o')
            ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
            ax.axvline(x=result.break_even_battery_cost, color='g', linestyle=':',
                      label=f'Break-even: {result.break_even_battery_cost:.0f} NOK/kWh')

            ax.set_xlabel('Battery Cost (NOK/kWh)')
            ax.set_ylabel('NPV (NOK)')
            ax.set_title('Break-Even Analysis')
            ax.grid(True, alpha=0.3)
            ax.legend()

            # Shade profitable region
            ax.fill_between(costs, npvs, 0,
                           where=[npv > 0 for npv in npvs],
                           alpha=0.3, color='green', label='Profitable')

            plt.tight_layout()
            viz_path = output_dir / 'break_even_analysis.png'
            plt.savefig(viz_path, dpi=150)
            plt.close()
            visualizations.append('break_even_analysis.png')

        return visualizations

    def _generate_html_report(
        self,
        request: GenerateReportRequest,
        output_dir: Path,
        visualizations: List[str]
    ) -> Path:
        """Generate HTML report"""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Battery Optimization Analysis Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #2E86AB; }
        h2 { color: #555; margin-top: 30px; }
        .metric { display: inline-block; margin: 10px 20px; padding: 10px;
                  background: #f0f0f0; border-radius: 5px; }
        .metric-label { font-weight: bold; color: #666; }
        .metric-value { font-size: 1.2em; color: #2E86AB; }
        img { max-width: 100%; margin: 20px 0; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #2E86AB; color: white; }
        .recommendation { background: #e8f4f8; padding: 15px;
                         border-left: 4px solid #2E86AB; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Battery Optimization Analysis Report</h1>
    <p>Generated: {timestamp}</p>
"""

        # Add optimization results
        if request.optimization_result:
            result = request.optimization_result
            html_content += f"""
    <h2>Optimization Results</h2>
    <div class="metrics">
        <div class="metric">
            <div class="metric-label">Optimal Capacity</div>
            <div class="metric-value">{result.optimal_capacity_kwh:.1f} kWh</div>
        </div>
        <div class="metric">
            <div class="metric-label">Optimal Power</div>
            <div class="metric-value">{result.optimal_power_kw:.1f} kW</div>
        </div>
        <div class="metric">
            <div class="metric-label">NPV</div>
            <div class="metric-value">{result.npv_nok:,.0f} NOK</div>
        </div>
        <div class="metric">
            <div class="metric-label">IRR</div>
            <div class="metric-value">{result.irr_percentage:.1f}%</div>
        </div>
        <div class="metric">
            <div class="metric-label">Payback</div>
            <div class="metric-value">{result.payback_years:.1f} years</div>
        </div>
    </div>
"""

        # Add visualizations
        if visualizations:
            html_content += "<h2>Analysis Visualizations</h2>"
            for viz in visualizations:
                html_content += f'<img src="{viz}" alt="{viz}">\n'

        # Add sensitivity results
        if request.sensitivity_result:
            html_content += f"""
    <h2>Sensitivity Analysis</h2>
    <p>Break-even battery cost: <strong>{request.sensitivity_result.break_even_battery_cost:.0f} NOK/kWh</strong></p>
"""

        # Add recommendations
        if request.include_recommendations:
            html_content += self._generate_recommendations_html(request)

        html_content += """
</body>
</html>
"""

        # Write report
        report_path = output_dir / 'report.html'
        report_path.write_text(html_content.format(timestamp=self.timestamp))

        return report_path

    def _generate_markdown_report(
        self,
        request: GenerateReportRequest,
        output_dir: Path,
        visualizations: List[str]
    ) -> Path:
        """Generate Markdown report"""
        md_content = f"""# Battery Optimization Analysis Report

Generated: {self.timestamp}

## Executive Summary

"""

        # Add optimization results
        if request.optimization_result:
            result = request.optimization_result
            md_content += f"""## Optimization Results

### Key Metrics

| Metric | Value |
|--------|-------|
| Optimal Capacity | {result.optimal_capacity_kwh:.1f} kWh |
| Optimal Power | {result.optimal_power_kw:.1f} kW |
| Net Present Value | {result.npv_nok:,.0f} NOK |
| Internal Rate of Return | {result.irr_percentage:.1f}% |
| Payback Period | {result.payback_years:.1f} years |
| Annual Savings | {result.annual_savings_nok:,.0f} NOK |

### Performance Metrics

- **Self-Consumption Rate**: {result.self_consumption_rate:.1%}
- **Peak Reduction**: {result.peak_reduction_percentage:.1%}

"""

        # Add visualizations
        if visualizations:
            md_content += "## Visualizations\n\n"
            for viz in visualizations:
                md_content += f"![{viz}](./{viz})\n\n"

        # Add sensitivity analysis
        if request.sensitivity_result:
            md_content += f"""## Sensitivity Analysis

**Break-even Battery Cost**: {request.sensitivity_result.break_even_battery_cost:.0f} NOK/kWh

This is the maximum battery cost at which the investment remains profitable.

"""

        # Add recommendations
        if request.include_recommendations:
            md_content += self._generate_recommendations_markdown(request)

        # Write report
        report_path = output_dir / 'report.md'
        report_path.write_text(md_content)

        return report_path

    def _generate_recommendations_html(
        self,
        request: GenerateReportRequest
    ) -> str:
        """Generate recommendations section for HTML"""
        recommendations = self._generate_recommendations(request)

        html = "<h2>Recommendations</h2>"
        for rec in recommendations:
            html += f"""
    <div class="recommendation">
        <strong>{rec['title']}</strong><br>
        {rec['description']}
    </div>
"""
        return html

    def _generate_recommendations_markdown(
        self,
        request: GenerateReportRequest
    ) -> str:
        """Generate recommendations section for Markdown"""
        recommendations = self._generate_recommendations(request)

        md = "## Recommendations\n\n"
        for rec in recommendations:
            md += f"### {rec['title']}\n\n{rec['description']}\n\n"

        return md

    def _generate_recommendations(
        self,
        request: GenerateReportRequest
    ) -> List[Dict[str, str]]:
        """Generate recommendations based on analysis results"""
        recommendations = []

        if request.optimization_result:
            result = request.optimization_result

            # NPV recommendation
            if result.npv_nok > 0:
                recommendations.append({
                    'title': 'Investment Recommendation',
                    'description': f'The battery investment is economically viable with a positive NPV of {result.npv_nok:,.0f} NOK.'
                })
            else:
                recommendations.append({
                    'title': 'Investment Caution',
                    'description': 'The battery investment shows negative NPV at current costs. Wait for cost reductions or improved incentives.'
                })

            # Payback recommendation
            if result.payback_years < 7:
                recommendations.append({
                    'title': 'Quick Payback',
                    'description': f'With a payback period of {result.payback_years:.1f} years, this is an attractive investment.'
                })
            elif result.payback_years < 10:
                recommendations.append({
                    'title': 'Moderate Payback',
                    'description': f'The {result.payback_years:.1f} year payback period is acceptable for long-term investors.'
                })

        if request.sensitivity_result:
            if request.sensitivity_result.break_even_battery_cost:
                recommendations.append({
                    'title': 'Cost Target',
                    'description': f'Battery costs need to fall below {request.sensitivity_result.break_even_battery_cost:.0f} NOK/kWh for profitability.'
                })

        return recommendations

    def _calculate_summary_metrics(
        self,
        request: GenerateReportRequest
    ) -> Dict[str, Any]:
        """Calculate summary metrics for the report"""
        metrics = {}

        if request.optimization_result:
            metrics['optimization'] = {
                'optimal_capacity_kwh': request.optimization_result.optimal_capacity_kwh,
                'npv_nok': request.optimization_result.npv_nok,
                'irr_percentage': request.optimization_result.irr_percentage,
                'payback_years': request.optimization_result.payback_years
            }

        if request.sensitivity_result:
            metrics['sensitivity'] = {
                'break_even_cost': request.sensitivity_result.break_even_battery_cost,
                'scenarios_analyzed': len(request.sensitivity_result.results_matrix)
            }

        return metrics