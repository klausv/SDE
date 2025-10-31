"""
Break-even battery cost analysis report.

Determines the maximum battery cost (NOK/kWh) that results in NPV = 0,
including sensitivity analysis for lifetime and discount rate variations.
"""

from pathlib import Path
from typing import Optional
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from core.reporting.report_generator import ComparisonReport
from core.reporting.result_models import SimulationResult


class BreakevenReport(ComparisonReport):
    """
    Generate comprehensive break-even cost analysis for battery investment.

    This report calculates the maximum battery cost per kWh that results in
    zero net present value (NPV = 0) given the annual savings from the battery
    strategy compared to a reference scenario.

    Includes:
    - NPV calculations and break-even cost determination
    - Sensitivity analysis for lifetime and discount rate
    - Market comparison with current battery prices
    - Visualizations of NPV vs cost and break-even vs parameters

    Assumptions:
    - Constant annual savings (no degradation adjustment)
    - No residual value at end of life
    - Annual savings calculated from simulation are representative
    """

    def __init__(
        self,
        reference: SimulationResult,
        battery_scenario: SimulationResult,
        output_dir: Path,
        battery_lifetime_years: int = 10,
        discount_rate: float = 0.05,
        market_cost_per_kwh: float = 5000.0
    ):
        """
        Initialize break-even analysis report.

        Args:
            reference: Reference scenario (no battery or baseline)
            battery_scenario: Scenario with battery strategy
            output_dir: Base directory for outputs
            battery_lifetime_years: Expected battery lifetime in years
            discount_rate: Annual discount rate for NPV calculation (e.g., 0.05 = 5%)
            market_cost_per_kwh: Current market battery cost for comparison (NOK/kWh)
        """
        super().__init__(
            results=[reference, battery_scenario],
            reference_scenario=reference.scenario_name,
            output_dir=output_dir
        )

        self.battery_scenario = battery_scenario
        self.lifetime = battery_lifetime_years
        self.discount_rate = discount_rate
        self.market_cost = market_cost_per_kwh

        # Calculate key metrics
        self.annual_savings = self._calculate_annual_savings()
        self.battery_capacity = battery_scenario.battery_config.get('capacity_kwh', 0)
        self.battery_power = battery_scenario.battery_config.get('power_kw', 0)

    def generate(self) -> Path:
        """
        Generate complete break-even analysis report.

        Returns:
            Path to the main markdown report file
        """
        print("\n" + "="*80)
        print(" GENERATING BREAK-EVEN ANALYSIS REPORT")
        print("="*80)

        # Apply standard plotting style
        self.apply_standard_plot_style()

        # Calculate break-even cost
        breakeven_cost = self._calculate_breakeven_cost(
            self.annual_savings,
            self.battery_capacity,
            self.lifetime,
            self.discount_rate
        )

        print(f"\n✓ Break-even cost calculated: {breakeven_cost:,.0f} NOK/kWh")

        # Generate visualizations
        print("\nGenerating visualizations...")
        self._plot_npv_sensitivity(breakeven_cost)
        self._plot_lifetime_sensitivity()
        self._plot_discount_rate_sensitivity()
        print("✓ Visualizations complete")

        # Generate markdown report
        print("\nGenerating markdown report...")
        report_path = self._write_markdown_report(breakeven_cost)
        print(f"✓ Report saved: {report_path}")

        # Create index
        self.create_index(
            title="Break-Even Battery Cost Analysis",
            additional_sections={
                'Key Findings': self._generate_key_findings_markdown(breakeven_cost)
            }
        )

        print("\n" + "="*80)
        print(f" REPORT COMPLETE: {report_path}")
        print("="*80 + "\n")

        return report_path

    def _calculate_annual_savings(self) -> float:
        """Calculate annual cost savings: reference - battery."""
        ref_cost = self.reference.cost_summary.get('total_cost_nok', 0)
        battery_cost = self.battery_scenario.cost_summary.get('total_cost_nok', 0)
        return ref_cost - battery_cost

    @staticmethod
    def _calculate_npv(
        initial_investment: float,
        annual_savings: float,
        lifetime_years: int,
        discount_rate: float
    ) -> float:
        """
        Calculate Net Present Value (NPV).

        NPV = -Initial_Investment + Σ(Annual_Savings / (1 + r)^t) for t=1 to lifetime

        Args:
            initial_investment: Battery cost (NOK)
            annual_savings: Annual electricity cost savings (NOK/year)
            lifetime_years: Battery lifetime (years)
            discount_rate: Annual discount rate (e.g., 0.05 for 5%)

        Returns:
            Net present value (NOK)
        """
        # Present value of future savings
        pv_savings = sum(
            annual_savings / (1 + discount_rate) ** year
            for year in range(1, lifetime_years + 1)
        )

        # NPV = PV of benefits - Initial cost
        return pv_savings - initial_investment

    @staticmethod
    def _calculate_breakeven_cost(
        annual_savings: float,
        battery_capacity_kwh: float,
        lifetime_years: int,
        discount_rate: float
    ) -> float:
        """
        Calculate break-even battery cost per kWh.

        Break-even when NPV = 0:
        0 = PV_savings - Initial_Investment
        Initial_Investment = PV_savings
        Cost_per_kWh = PV_savings / Capacity

        Args:
            annual_savings: Annual electricity cost savings (NOK/year)
            battery_capacity_kwh: Battery capacity (kWh)
            lifetime_years: Battery lifetime (years)
            discount_rate: Annual discount rate

        Returns:
            Break-even cost per kWh (NOK/kWh)
        """
        # Calculate present value of annual savings
        pv_savings = sum(
            annual_savings / (1 + discount_rate) ** year
            for year in range(1, lifetime_years + 1)
        )

        # Break-even cost
        return pv_savings / battery_capacity_kwh

    @staticmethod
    def _calculate_annuity_factor(lifetime_years: int, discount_rate: float) -> float:
        """
        Calculate annuity factor for present value calculation.

        Annuity factor = Σ(1 / (1+r)^t) for t=1 to n
                       = (1 - (1+r)^-n) / r

        Args:
            lifetime_years: Number of years
            discount_rate: Discount rate

        Returns:
            Present value factor for annuity
        """
        if discount_rate == 0:
            return float(lifetime_years)

        return (1 - (1 + discount_rate) ** -lifetime_years) / discount_rate

    def _plot_npv_sensitivity(self, breakeven_cost: float):
        """
        Plot NPV vs battery cost with break-even point highlighted.

        Args:
            breakeven_cost: Calculated break-even cost (NOK/kWh)
        """
        # Range of battery costs to evaluate
        costs = np.linspace(1000, 7000, 100)

        # Calculate NPV for each cost
        npvs = np.array([
            self._calculate_npv(
                initial_investment=cost * self.battery_capacity,
                annual_savings=self.annual_savings,
                lifetime_years=self.lifetime,
                discount_rate=self.discount_rate
            )
            for cost in costs
        ])

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 7))

        # Main NPV curve
        ax.plot(costs, npvs, linewidth=2.5, color='#2E86AB', label='NPV')

        # Zero line (break-even)
        ax.axhline(0, color='red', linestyle='--', linewidth=1.5,
                   alpha=0.7, label='Break-even (NPV=0)')

        # Break-even point
        ax.axvline(breakeven_cost, color='green', linestyle='--', linewidth=1.5,
                   alpha=0.7, label=f'Break-even cost: {breakeven_cost:,.0f} NOK/kWh')

        # Market cost reference
        market_npv = self._calculate_npv(
            self.market_cost * self.battery_capacity,
            self.annual_savings,
            self.lifetime,
            self.discount_rate
        )
        ax.plot(self.market_cost, market_npv, 'ro', markersize=10,
                label=f'Market price: {self.market_cost:,.0f} NOK/kWh')

        # Styling
        ax.set_xlabel('Battery Cost (NOK/kWh)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Net Present Value (NOK)', fontsize=12, fontweight='bold')
        ax.set_title(
            f'NPV Sensitivity to Battery Cost\n'
            f'(Lifetime: {self.lifetime} years, Discount rate: {self.discount_rate*100:.1f}%)',
            fontsize=14,
            fontweight='bold'
        )
        ax.legend(fontsize=10, loc='best')
        ax.grid(True, alpha=0.3)

        # Add annotation for market NPV
        ax.annotate(
            f'NPV at market price:\n{market_npv:,.0f} NOK',
            xy=(self.market_cost, market_npv),
            xytext=(self.market_cost + 500, market_npv - 50000),
            arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
            fontsize=9,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7)
        )

        # Save figure
        self.save_figure(fig, 'npv_sensitivity.png', subdir='breakeven')

    def _plot_lifetime_sensitivity(self):
        """Plot break-even cost vs battery lifetime."""
        lifetimes = np.arange(5, 21)

        breakeven_costs = np.array([
            self._calculate_breakeven_cost(
                self.annual_savings,
                self.battery_capacity,
                int(life),
                self.discount_rate
            )
            for life in lifetimes
        ])

        fig, ax = plt.subplots(figsize=(12, 7))

        # Main curve
        ax.plot(lifetimes, breakeven_costs, marker='o', linewidth=2.5,
                markersize=8, color='#A23B72', label='Break-even cost')

        # Current lifetime reference
        current_breakeven = self._calculate_breakeven_cost(
            self.annual_savings,
            self.battery_capacity,
            self.lifetime,
            self.discount_rate
        )
        ax.plot(self.lifetime, current_breakeven, 'go', markersize=12,
                label=f'Current assumption: {self.lifetime} years')

        # Market cost reference
        ax.axhline(self.market_cost, color='red', linestyle='--',
                   linewidth=1.5, alpha=0.7,
                   label=f'Market cost: {self.market_cost:,.0f} NOK/kWh')

        # Styling
        ax.set_xlabel('Battery Lifetime (years)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Break-even Cost (NOK/kWh)', fontsize=12, fontweight='bold')
        ax.set_title(
            f'Break-even Cost vs Battery Lifetime\n'
            f'(Annual savings: {self.annual_savings:,.0f} NOK, Discount rate: {self.discount_rate*100:.1f}%)',
            fontsize=14,
            fontweight='bold'
        )
        ax.legend(fontsize=10, loc='best')
        ax.grid(True, alpha=0.3)

        # Save figure
        self.save_figure(fig, 'breakeven_vs_lifetime.png', subdir='breakeven')

    def _plot_discount_rate_sensitivity(self):
        """Plot break-even cost vs discount rate."""
        discount_rates = np.linspace(0.01, 0.15, 50)

        breakeven_costs = np.array([
            self._calculate_breakeven_cost(
                self.annual_savings,
                self.battery_capacity,
                self.lifetime,
                rate
            )
            for rate in discount_rates
        ])

        fig, ax = plt.subplots(figsize=(12, 7))

        # Main curve
        ax.plot(discount_rates * 100, breakeven_costs, linewidth=2.5,
                color='#F18F01', label='Break-even cost')

        # Current discount rate reference
        current_breakeven = self._calculate_breakeven_cost(
            self.annual_savings,
            self.battery_capacity,
            self.lifetime,
            self.discount_rate
        )
        ax.plot(self.discount_rate * 100, current_breakeven, 'go',
                markersize=12, label=f'Current rate: {self.discount_rate*100:.1f}%')

        # Market cost reference
        ax.axhline(self.market_cost, color='red', linestyle='--',
                   linewidth=1.5, alpha=0.7,
                   label=f'Market cost: {self.market_cost:,.0f} NOK/kWh')

        # Styling
        ax.set_xlabel('Discount Rate (%)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Break-even Cost (NOK/kWh)', fontsize=12, fontweight='bold')
        ax.set_title(
            f'Break-even Cost vs Discount Rate\n'
            f'(Annual savings: {self.annual_savings:,.0f} NOK, Lifetime: {self.lifetime} years)',
            fontsize=14,
            fontweight='bold'
        )
        ax.legend(fontsize=10, loc='best')
        ax.grid(True, alpha=0.3)

        # Save figure
        self.save_figure(fig, 'breakeven_vs_discount_rate.png', subdir='breakeven')

    def _write_markdown_report(self, breakeven_cost: float) -> Path:
        """
        Write comprehensive markdown report.

        Args:
            breakeven_cost: Calculated break-even cost (NOK/kWh)

        Returns:
            Path to generated markdown file
        """
        report_path = self.output_dir / 'reports' / self.get_timestamped_filename('breakeven_analysis')

        # Calculate additional metrics
        annuity_factor = self._calculate_annuity_factor(self.lifetime, self.discount_rate)
        pv_savings = self.annual_savings * annuity_factor
        breakeven_total = breakeven_cost * self.battery_capacity

        market_total = self.market_cost * self.battery_capacity
        market_npv = self._calculate_npv(market_total, self.annual_savings,
                                         self.lifetime, self.discount_rate)

        # Start report
        self.write_markdown_header(
            report_path,
            "Break-Even Battery Cost Analysis",
            summary_points=[
                f"**Annual Savings:** {self.format_currency(self.annual_savings)}",
                f"**Break-even Cost:** {self.format_currency(breakeven_cost, 'NOK/kWh')}",
                f"**Market Price:** {self.format_currency(self.market_cost, 'NOK/kWh')}",
                f"**Required Price Reduction:** {self.format_percentage((1 - breakeven_cost/self.market_cost) * 100)}",
                f"**NPV at Market Prices:** {self.format_currency(market_npv)} ({'Viable' if market_npv > 0 else 'Not Viable'})"
            ]
        )

        # Append detailed sections
        with open(report_path, 'a') as f:
            # Assumptions
            f.write("## Assumptions\n\n")
            f.write(f"| Parameter | Value |\n")
            f.write(f"|-----------|-------|\n")
            f.write(f"| Battery capacity | {self.battery_capacity:.0f} kWh |\n")
            f.write(f"| Battery power | {self.battery_power:.0f} kW |\n")
            f.write(f"| Battery lifetime | {self.lifetime} years |\n")
            f.write(f"| Discount rate | {self.discount_rate*100:.1f}% |\n")
            f.write(f"| Reference scenario | {self.reference.scenario_name} |\n")
            f.write(f"| Battery scenario | {self.battery_scenario.scenario_name} |\n")
            f.write("\n")

            # Annual savings
            f.write("## 1. Annual Savings\n\n")
            ref_cost = self.reference.cost_summary.get('total_cost_nok', 0)
            battery_cost = self.battery_scenario.cost_summary.get('total_cost_nok', 0)
            f.write(f"| Cost Component | Value |\n")
            f.write(f"|----------------|-------|\n")
            f.write(f"| Reference case cost | {self.format_currency(ref_cost)}/year |\n")
            f.write(f"| Battery strategy cost | {self.format_currency(battery_cost)}/year |\n")
            f.write(f"| **Annual savings** | **{self.format_currency(self.annual_savings)}/year** |\n")
            f.write("\n")

            # Present value calculations
            f.write("## 2. Present Value Calculations\n\n")
            f.write(f"| Metric | Value |\n")
            f.write(f"|--------|-------|\n")
            f.write(f"| Annuity factor (PV of 1 NOK/year) | {annuity_factor:.4f} |\n")
            f.write(f"| PV of total savings | {self.format_currency(pv_savings)} |\n")
            f.write("\n")

            # Break-even cost
            f.write("## 3. Break-Even Battery Cost\n\n")
            f.write(f"| Metric | Value |\n")
            f.write(f"|--------|-------|\n")
            f.write(f"| **Break-even cost (total)** | **{self.format_currency(breakeven_total)}** |\n")
            f.write(f"| **Break-even cost (per kWh)** | **{self.format_currency(breakeven_cost, 'NOK/kWh')}** |\n")
            f.write(f"| **Break-even cost (per kW)** | **{self.format_currency(breakeven_total/self.battery_power, 'NOK/kW')}** |\n")
            f.write("\n")

            # Market comparison
            f.write("## 4. Market Comparison\n\n")
            f.write(f"| Metric | Value |\n")
            f.write(f"|--------|-------|\n")
            f.write(f"| Current market price | {self.format_currency(self.market_cost, 'NOK/kWh')} |\n")
            f.write(f"| Current market cost (total) | {self.format_currency(market_total)} |\n")
            f.write(f"| Required price reduction | {self.format_currency(self.market_cost - breakeven_cost, 'NOK/kWh')} ({self.format_percentage((1 - breakeven_cost/self.market_cost) * 100)}) |\n")
            f.write(f"| NPV at market prices | {self.format_currency(market_npv)} |\n")
            f.write(f"| **Investment viability** | **{'✓ Viable (NPV > 0)' if market_npv > 0 else '✗ Not Viable (NPV < 0)'}** |\n")
            f.write("\n")

            # Sensitivity analysis
            f.write("## 5. Sensitivity Analysis\n\n")

            # Lifetime sensitivity
            f.write("### Break-even Cost vs Lifetime\n\n")
            f.write(f"| Lifetime (years) | Annuity Factor | Break-even (NOK/kWh) |\n")
            f.write(f"|------------------|----------------|---------------------|\n")
            for life in [5, 10, 15, 20]:
                af = self._calculate_annuity_factor(life, self.discount_rate)
                be = self._calculate_breakeven_cost(self.annual_savings, self.battery_capacity,
                                                   life, self.discount_rate)
                f.write(f"| {life} | {af:.4f} | {be:,.0f} |\n")
            f.write("\n")

            # Discount rate sensitivity
            f.write("### Break-even Cost vs Discount Rate\n\n")
            f.write(f"| Discount Rate (%) | Annuity Factor | Break-even (NOK/kWh) |\n")
            f.write(f"|-------------------|----------------|---------------------|\n")
            for rate in [0.03, 0.05, 0.07, 0.10]:
                af = self._calculate_annuity_factor(self.lifetime, rate)
                be = self._calculate_breakeven_cost(self.annual_savings, self.battery_capacity,
                                                   self.lifetime, rate)
                f.write(f"| {rate*100:.1f} | {af:.4f} | {be:,.0f} |\n")
            f.write("\n")

            # Visualizations
            f.write("## Visualizations\n\n")
            f.write("### NPV Sensitivity to Battery Cost\n\n")
            f.write("![NPV Sensitivity](../figures/breakeven/npv_sensitivity.png)\n\n")
            f.write("### Break-even Cost vs Battery Lifetime\n\n")
            f.write("![Lifetime Sensitivity](../figures/breakeven/breakeven_vs_lifetime.png)\n\n")
            f.write("### Break-even Cost vs Discount Rate\n\n")
            f.write("![Discount Rate Sensitivity](../figures/breakeven/breakeven_vs_discount_rate.png)\n\n")

            # Summary and recommendations
            f.write("## Summary and Recommendations\n\n")
            f.write(f"With the current battery strategy saving **{self.format_currency(self.annual_savings)}/year**, ")
            f.write(f"the maximum viable battery cost is **{self.format_currency(breakeven_cost, 'NOK/kWh')}**.\n\n")

            if market_npv < 0:
                reduction_pct = (1 - breakeven_cost/self.market_cost) * 100
                savings_multiplier = self.market_cost / breakeven_cost
                f.write(f"Current market prices ({self.format_currency(self.market_cost, 'NOK/kWh')}) result in **negative NPV**, requiring either:\n\n")
                f.write(f"- **{savings_multiplier:.1f}x higher annual savings** (optimize strategy), OR\n")
                f.write(f"- **{self.format_percentage(reduction_pct)} battery cost reduction** (wait for price drop)\n\n")
                f.write("### Potential Paths to Viability:\n\n")
                f.write("1. **Implement advanced optimization** (LP/MPC) for higher savings\n")
                f.write("2. **Wait for battery prices to fall** below break-even threshold\n")
                f.write("3. **Explore additional revenue streams** (grid services, demand response)\n")
                f.write("4. **Increase battery lifetime** through proper operation and maintenance\n")
                f.write("5. **Combine strategies** (e.g., solar + battery + EV charging)\n")
            else:
                f.write("✓ **Investment is viable** at current market prices with positive NPV!\n\n")
                f.write("### Optimization Opportunities:\n\n")
                f.write("1. Implement advanced control strategies to increase annual savings\n")
                f.write("2. Negotiate better battery prices to improve NPV\n")
                f.write("3. Explore extended lifetime through proper O&M\n")

            f.write("\n")

        return report_path

    def _generate_key_findings_markdown(self, breakeven_cost: float) -> str:
        """Generate key findings section for index."""
        market_npv = self._calculate_npv(
            self.market_cost * self.battery_capacity,
            self.annual_savings,
            self.lifetime,
            self.discount_rate
        )

        findings = f"- Annual savings from battery: **{self.format_currency(self.annual_savings)}**\n"
        findings += f"- Break-even battery cost: **{self.format_currency(breakeven_cost, 'NOK/kWh')}**\n"
        findings += f"- Market price: **{self.format_currency(self.market_cost, 'NOK/kWh')}**\n"
        findings += f"- Investment viability: **{'✓ Viable' if market_npv > 0 else '✗ Not Viable'}**\n"

        if market_npv < 0:
            reduction = (1 - breakeven_cost/self.market_cost) * 100
            findings += f"- Required price reduction: **{self.format_percentage(reduction)}**\n"

        return findings
