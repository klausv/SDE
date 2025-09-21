#!/usr/bin/env python3
"""
Main execution script for battery optimization analysis
"""
import logging
import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import SystemConfig, LnettTariff, BatteryConfig, EconomicConfig
from src.optimization.optimizer import BatteryOptimizer
from src.analysis.sensitivity import SensitivityAnalyzer
from src.analysis.visualization import ResultVisualizer
from src.data_fetchers.entso_e_client import create_sample_env_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run comprehensive battery optimization analysis"""

    print("\n" + "="*60)
    print("🔋 BATTERY OPTIMIZATION FOR STAVANGER SOLAR INSTALLATION")
    print("="*60)

    # System specifications
    print("\n📊 System Specifications:")
    print(f"  • PV Capacity: 150 kWp")
    print(f"  • Inverter: 110 kW")
    print(f"  • Grid Limit: 77 kW (70% of inverter)")
    print(f"  • Location: Stavanger (58.97°N, 5.73°E)")
    print(f"  • Tilt: 25°, South-facing")

    # Initialize configurations
    system_config = SystemConfig()
    # Overstyr med korrekte verdier fra PVsol
    system_config.pv_capacity_kwp = 138.55  # Fra PVsol
    system_config.inverter_capacity_kw = 100  # Fra PVsol
    system_config.grid_capacity_kw = 70  # 70% av inverter
    lnett_tariff = LnettTariff()
    battery_config = BatteryConfig()
    economic_config = EconomicConfig()

    # Create optimizer
    optimizer = BatteryOptimizer(
        system_config,
        lnett_tariff,
        battery_config,
        economic_config
    )

    # Create analyzers
    sensitivity_analyzer = SensitivityAnalyzer(
        system_config,
        lnett_tariff,
        battery_config,
        economic_config
    )
    visualizer = ResultVisualizer()

    print("\n🔄 Running optimization analysis...")

    try:
        # Run comprehensive analysis
        results = optimizer.run_comprehensive_analysis(year=2024, use_cache=True)

        # Extract optimization results
        opt_result = results['optimization']

        print("\n✅ OPTIMIZATION RESULTS")
        print("="*40)

        print(f"\n🎯 Optimal Battery Configuration:")
        print(f"  • Capacity: {opt_result.optimal_capacity_kwh:.1f} kWh")
        print(f"  • Power: {opt_result.optimal_power_kw:.1f} kW")
        print(f"  • C-Rate: {opt_result.optimal_c_rate:.2f}")

        print(f"\n💰 Economic Analysis (at 3000 NOK/kWh):")
        print(f"  • NPV: {opt_result.npv_at_target_cost:,.0f} NOK")
        if opt_result.economic_results.irr:
            print(f"  • IRR: {opt_result.economic_results.irr:.1%}")
        if opt_result.economic_results.payback_years:
            print(f"  • Payback: {opt_result.economic_results.payback_years:.1f} years")
        print(f"  • Annual Savings: {opt_result.economic_results.annual_savings:,.0f} NOK")

        print(f"\n🎯 Break-even Analysis:")
        print(f"  • Maximum Battery Cost: {opt_result.max_battery_cost_per_kwh:.0f} NOK/kWh")
        print(f"    (for NPV = 0)")

        print(f"\n📈 Revenue Breakdown (15 years):")
        for source, value in opt_result.economic_results.revenue_breakdown.items():
            print(f"  • {source.replace('_', ' ').title()}: {value:,.0f} NOK")

        print(f"\n⚡ Operation Metrics:")
        print(f"  • Annual Cycles: {opt_result.operation_metrics.get('cycles', 0):.0f}")
        print(f"  • Self-Consumption: {opt_result.operation_metrics.get('self_consumption_rate', 0):.1%}")
        print(f"  • Curtailment Avoided: {opt_result.operation_metrics.get('curtailment_avoided_kwh', 0):,.0f} kWh/year")

        # PV Statistics
        print(f"\n☀️ PV Production Statistics:")
        pv_stats = results['pv_statistics']
        print(f"  • Annual Production: {pv_stats['total_production_mwh']:.1f} MWh")
        print(f"  • Capacity Factor: {pv_stats['capacity_factor']:.1%}")
        print(f"  • Hours at Inverter Limit: {pv_stats['hours_at_inverter_limit']:.0f}")
        print(f"  • Estimated Clipping Loss: {pv_stats['clipping_loss_mwh']:.1f} MWh")

        # Generate visualizations
        print("\n📊 Generating visualizations...")

        # Sensitivity analysis
        if opt_result.sensitivity_data is not None and not opt_result.sensitivity_data.empty:
            # Create NPV heatmap
            fig_heatmap = visualizer.plot_npv_heatmap(
                opt_result.sensitivity_data,
                battery_cost=3000,
                save_name='npv_heatmap'
            )

        # Generate summary report
        print("\n📄 Generating summary report...")
        visualizer.generate_summary_report(opt_result, 'optimization_summary')

        print("\n✅ Analysis complete! Results saved in 'results/reports/'")

        # Key recommendations
        print("\n" + "="*60)
        print("🎯 KEY RECOMMENDATIONS")
        print("="*60)

        print(f"\n1. OPTIMAL BATTERY SIZE:")
        print(f"   Install a {opt_result.optimal_capacity_kwh:.0f} kWh battery with {opt_result.optimal_power_kw:.0f} kW power rating")

        print(f"\n2. INVESTMENT THRESHOLD:")
        if opt_result.max_battery_cost_per_kwh > 3000:
            print(f"   ✅ Current market prices (~3000 NOK/kWh) are BELOW break-even")
            print(f"   → Investment is PROFITABLE")
        else:
            print(f"   ⚠️ Current market prices (~3000 NOK/kWh) are ABOVE break-even")
            print(f"   → Wait for prices to drop below {opt_result.max_battery_cost_per_kwh:.0f} NOK/kWh")

        print(f"\n3. REVENUE OPTIMIZATION:")
        revenue_sorted = sorted(
            opt_result.economic_results.revenue_breakdown.items(),
            key=lambda x: x[1],
            reverse=True
        )
        print(f"   Primary revenue: {revenue_sorted[0][0].replace('_', ' ').title()}")
        print(f"   Focus on maximizing this revenue stream")

        print(f"\n4. RISK FACTORS:")
        print(f"   • Monitor electricity price volatility")
        print(f"   • Consider future tariff changes")
        print(f"   • Account for battery degradation in planning")

        print("\n" + "="*60)

    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        print("\nPlease check:")
        print("1. ENTSO-E API key is configured (if using real data)")
        print("2. All required packages are installed")
        print("3. Check logs for detailed error information")

if __name__ == "__main__":
    # Create sample .env file if needed
    create_sample_env_file()

    # Run main analysis
    main()