"""
Visualization module for battery optimization results
"""
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path

class ResultVisualizer:
    """Generate visualizations for battery optimization results"""

    def __init__(self, output_dir: str = 'results/reports'):
        """
        Initialize visualizer

        Args:
            output_dir: Directory for saving visualizations
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def plot_npv_heatmap(
        self,
        sensitivity_data: pd.DataFrame,
        battery_cost: float,
        save_name: Optional[str] = None
    ) -> go.Figure:
        """
        Create NPV heatmap for different battery sizes

        Args:
            sensitivity_data: DataFrame with sensitivity analysis
            battery_cost: Battery cost for filtering
            save_name: Optional filename for saving

        Returns:
            Plotly figure
        """
        # Filter for specific battery cost
        data = sensitivity_data[sensitivity_data['battery_cost_per_kwh'] == battery_cost]

        # Pivot data for heatmap
        pivot = data.pivot_table(
            values='npv',
            index='power_kw',
            columns='capacity_kwh',
            aggfunc='mean'
        )

        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale='RdYlGn',
            text=np.round(pivot.values / 1000, 0),  # Show in kNOK
            texttemplate='%{text}k',
            textfont={'size': 10},
            colorbar=dict(title='NPV (kNOK)')
        ))

        fig.update_layout(
            title=f'NPV Heatmap - Battery Cost: {battery_cost} NOK/kWh',
            xaxis_title='Battery Capacity (kWh)',
            yaxis_title='Battery Power (kW)',
            width=800,
            height=600
        )

        if save_name:
            fig.write_html(self.output_dir / f'{save_name}.html')

        return fig

    def plot_break_even_surface(
        self,
        break_even_data: pd.DataFrame,
        save_name: Optional[str] = None
    ) -> go.Figure:
        """
        Create 3D surface plot of break-even battery costs

        Args:
            break_even_data: DataFrame with break-even analysis
            save_name: Optional filename for saving

        Returns:
            Plotly figure
        """
        # Pivot data for surface plot
        pivot = break_even_data.pivot_table(
            values='break_even_cost',
            index='power_kw',
            columns='capacity_kwh',
            aggfunc='mean'
        )

        fig = go.Figure(data=[go.Surface(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale='Viridis',
            colorbar=dict(title='Break-even Cost<br>(NOK/kWh)')
        )])

        fig.update_layout(
            title='Break-even Battery Cost Surface',
            scene=dict(
                xaxis_title='Battery Capacity (kWh)',
                yaxis_title='Battery Power (kW)',
                zaxis_title='Break-even Cost (NOK/kWh)'
            ),
            width=900,
            height=700
        )

        if save_name:
            fig.write_html(self.output_dir / f'{save_name}.html')

        return fig

    def plot_sensitivity_curves(
        self,
        price_sensitivity: pd.DataFrame,
        tariff_sensitivity: pd.DataFrame,
        degradation_sensitivity: pd.DataFrame,
        save_name: Optional[str] = None
    ) -> go.Figure:
        """
        Create multi-panel sensitivity analysis curves

        Args:
            price_sensitivity: Price volatility sensitivity data
            tariff_sensitivity: Tariff sensitivity data
            degradation_sensitivity: Degradation sensitivity data
            save_name: Optional filename for saving

        Returns:
            Plotly figure
        """
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Price Volatility Impact',
                'Tariff Rate Impact',
                'Degradation Rate Impact',
                'Combined NPV Summary'
            )
        )

        # Price volatility
        fig.add_trace(
            go.Scatter(
                x=price_sensitivity['volatility_factor'],
                y=price_sensitivity['npv'] / 1000,
                mode='lines+markers',
                name='Price Volatility',
                line=dict(color='blue', width=2)
            ),
            row=1, col=1
        )

        # Tariff rates
        fig.add_trace(
            go.Scatter(
                x=tariff_sensitivity['tariff_multiplier'],
                y=tariff_sensitivity['npv'] / 1000,
                mode='lines+markers',
                name='Tariff Rate',
                line=dict(color='green', width=2)
            ),
            row=1, col=2
        )

        # Degradation
        fig.add_trace(
            go.Scatter(
                x=degradation_sensitivity['degradation_rate'],
                y=degradation_sensitivity['npv'] / 1000,
                mode='lines+markers',
                name='Degradation',
                line=dict(color='red', width=2)
            ),
            row=2, col=1
        )

        # Combined summary
        fig.add_trace(
            go.Bar(
                x=['Price Vol.', 'Tariff', 'Degradation'],
                y=[
                    price_sensitivity['npv'].std() / 1000,
                    tariff_sensitivity['npv'].std() / 1000,
                    degradation_sensitivity['npv'].std() / 1000
                ],
                name='NPV Sensitivity',
                marker_color=['blue', 'green', 'red']
            ),
            row=2, col=2
        )

        # Update axes
        fig.update_xaxes(title_text='Volatility Factor', row=1, col=1)
        fig.update_xaxes(title_text='Tariff Multiplier', row=1, col=2)
        fig.update_xaxes(title_text='Degradation Rate (%/year)', row=2, col=1)
        fig.update_xaxes(title_text='Parameter', row=2, col=2)

        fig.update_yaxes(title_text='NPV (kNOK)', row=1, col=1)
        fig.update_yaxes(title_text='NPV (kNOK)', row=1, col=2)
        fig.update_yaxes(title_text='NPV (kNOK)', row=2, col=1)
        fig.update_yaxes(title_text='Std Dev (kNOK)', row=2, col=2)

        fig.update_layout(
            title='Comprehensive Sensitivity Analysis',
            showlegend=False,
            height=800,
            width=1200
        )

        if save_name:
            fig.write_html(self.output_dir / f'{save_name}.html')

        return fig

    def plot_operation_profile(
        self,
        operation_results: Dict[str, pd.Series],
        pv_production: pd.Series,
        spot_prices: pd.Series,
        days_to_plot: int = 7,
        save_name: Optional[str] = None
    ) -> go.Figure:
        """
        Plot battery operation profile over time

        Args:
            operation_results: Battery operation results
            pv_production: PV production
            spot_prices: Electricity prices
            days_to_plot: Number of days to plot
            save_name: Optional filename for saving

        Returns:
            Plotly figure
        """
        # Limit to specified days
        hours_to_plot = days_to_plot * 24
        slice_end = min(hours_to_plot, len(pv_production))

        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            subplot_titles=(
                'PV Production & Grid Flows',
                'Battery State of Charge',
                'Battery Power Flow',
                'Spot Prices'
            ),
            vertical_spacing=0.05
        )

        # Time index
        time_index = pv_production.index[:slice_end]

        # PV and grid flows
        fig.add_trace(
            go.Scatter(
                x=time_index,
                y=pv_production.iloc[:slice_end],
                name='PV Production',
                line=dict(color='orange', width=2)
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=time_index,
                y=operation_results['grid_export'].iloc[:slice_end],
                name='Grid Export',
                line=dict(color='green', width=1)
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=time_index,
                y=-operation_results['grid_import'].iloc[:slice_end],
                name='Grid Import',
                line=dict(color='red', width=1)
            ),
            row=1, col=1
        )

        # Battery SOC
        fig.add_trace(
            go.Scatter(
                x=time_index,
                y=operation_results['soc'].iloc[:slice_end],
                name='SOC',
                fill='tozeroy',
                line=dict(color='blue', width=2)
            ),
            row=2, col=1
        )

        # Battery power flow
        fig.add_trace(
            go.Scatter(
                x=time_index,
                y=operation_results['battery_charge'].iloc[:slice_end],
                name='Charging',
                line=dict(color='lightblue', width=1)
            ),
            row=3, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=time_index,
                y=-operation_results['battery_discharge'].iloc[:slice_end],
                name='Discharging',
                line=dict(color='darkblue', width=1)
            ),
            row=3, col=1
        )

        # Spot prices
        fig.add_trace(
            go.Scatter(
                x=time_index,
                y=spot_prices.iloc[:slice_end],
                name='Spot Price',
                line=dict(color='purple', width=2)
            ),
            row=4, col=1
        )

        # Update axes
        fig.update_yaxes(title_text='Power (kW)', row=1, col=1)
        fig.update_yaxes(title_text='SOC (kWh)', row=2, col=1)
        fig.update_yaxes(title_text='Power (kW)', row=3, col=1)
        fig.update_yaxes(title_text='Price (NOK/kWh)', row=4, col=1)
        fig.update_xaxes(title_text='Time', row=4, col=1)

        fig.update_layout(
            title=f'Battery Operation Profile - {days_to_plot} Days',
            showlegend=True,
            height=1000,
            width=1200
        )

        if save_name:
            fig.write_html(self.output_dir / f'{save_name}.html')

        return fig

    def generate_summary_report(
        self,
        optimization_result,
        save_name: str = 'optimization_summary'
    ) -> None:
        """
        Generate HTML summary report

        Args:
            optimization_result: Optimization results object
            save_name: Filename for report
        """
        html_content = f"""
        <html>
        <head>
            <title>Battery Optimization Summary Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #3498db; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .metric {{ background-color: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .positive {{ color: #27ae60; font-weight: bold; }}
                .negative {{ color: #e74c3c; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>🔋 Battery System Optimization Report</h1>

            <h2>Optimal Configuration</h2>
            <div class="metric">
                <p><strong>Battery Capacity:</strong> {optimization_result.optimal_capacity_kwh:.1f} kWh</p>
                <p><strong>Battery Power:</strong> {optimization_result.optimal_power_kw:.1f} kW</p>
                <p><strong>C-Rate:</strong> {optimization_result.optimal_c_rate:.2f}</p>
                <p><strong>Maximum Battery Cost for Profitability:</strong>
                   <span class="positive">{optimization_result.max_battery_cost_per_kwh:.0f} NOK/kWh</span></p>
            </div>

            <h2>Economic Analysis</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Net Present Value (NPV)</td>
                    <td class="{'positive' if optimization_result.economic_results.npv > 0 else 'negative'}">
                        {optimization_result.economic_results.npv:,.0f} NOK
                    </td>
                </tr>
                <tr>
                    <td>Internal Rate of Return (IRR)</td>
                    <td>{optimization_result.economic_results.irr:.1% if optimization_result.economic_results.irr else 'N/A'}</td>
                </tr>
                <tr>
                    <td>Payback Period</td>
                    <td>{optimization_result.economic_results.payback_years:.1f if optimization_result.economic_results.payback_years else 15.0} years</td>
                </tr>
                <tr>
                    <td>Annual Savings</td>
                    <td>{optimization_result.economic_results.annual_savings:,.0f} NOK/year</td>
                </tr>
            </table>

            <h2>Revenue Breakdown</h2>
            <table>
                <tr>
                    <th>Revenue Stream</th>
                    <th>Total (15 years)</th>
                </tr>
                <tr>
                    <td>Peak Reduction (Effekttariff)</td>
                    <td>{optimization_result.economic_results.revenue_breakdown['peak_reduction']:,.0f} NOK</td>
                </tr>
                <tr>
                    <td>Energy Arbitrage</td>
                    <td>{optimization_result.economic_results.revenue_breakdown['arbitrage']:,.0f} NOK</td>
                </tr>
                <tr>
                    <td>Avoided Curtailment</td>
                    <td>{optimization_result.economic_results.revenue_breakdown['curtailment_avoided']:,.0f} NOK</td>
                </tr>
            </table>

            <h2>Operation Metrics</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Annual Charge/Discharge Cycles</td>
                    <td>{optimization_result.operation_metrics.get('cycles', 0):.0f}</td>
                </tr>
                <tr>
                    <td>Average State of Charge</td>
                    <td>{optimization_result.operation_metrics.get('avg_soc', 0):.1%}</td>
                </tr>
                <tr>
                    <td>Self-Consumption Rate</td>
                    <td>{optimization_result.operation_metrics.get('self_consumption_rate', 0):.1%}</td>
                </tr>
                <tr>
                    <td>Curtailment Avoided</td>
                    <td>{optimization_result.operation_metrics.get('curtailment_avoided_kwh', 0):,.0f} kWh/year</td>
                </tr>
            </table>

            <h2>Key Findings</h2>
            <div class="metric">
                <ul>
                    <li>The optimal battery configuration balances capacity and power for maximum economic benefit</li>
                    <li>Break-even battery cost provides a target for investment decisions</li>
                    <li>Multiple revenue streams contribute to overall profitability</li>
                    <li>System performance depends on price volatility and tariff structure</li>
                </ul>
            </div>

            <p><em>Report generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</em></p>
        </body>
        </html>
        """

        with open(self.output_dir / f'{save_name}.html', 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"Summary report saved to: {self.output_dir / save_name}.html")