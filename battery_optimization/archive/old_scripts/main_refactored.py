"""
Main entry point for refactored battery optimization system
"""
import argparse
import logging
from pathlib import Path
from datetime import datetime

from config import ConfigurationManager
from application.use_cases import (
    OptimizeBatteryUseCase,
    OptimizeBatteryRequest,
    SensitivityAnalysisUseCase,
    SensitivityAnalysisRequest,
    GenerateReportUseCase,
    GenerateReportRequest
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_optimization(args):
    """Run battery optimization"""
    logger.info("Starting battery optimization...")

    # Load configuration
    config = ConfigurationManager()
    config.load()

    # Apply scenario if specified
    if args.scenario:
        logger.info(f"Applying scenario: {args.scenario}")
        config.override_with_scenario(args.scenario)

    # Create use case
    optimizer = OptimizeBatteryUseCase(config)

    # Run optimization
    request = OptimizeBatteryRequest(
        battery_cost_nok_per_kwh=args.battery_cost,
        optimization_metric=args.metric,
        max_battery_capacity_kwh=args.max_capacity,
        max_battery_power_kw=args.max_power,
        use_cached_data=not args.fresh_data
    )

    logger.info("Running optimization...")
    response = optimizer.execute(request)

    # Display results
    print("\n" + "="*60)
    print("OPTIMIZATION RESULTS")
    print("="*60)
    print(f"Optimal Battery Capacity: {response.optimal_capacity_kwh:.1f} kWh")
    print(f"Optimal Battery Power:    {response.optimal_power_kw:.1f} kW")
    print(f"Net Present Value (NPV):  {response.npv_nok:,.0f} NOK")
    print(f"Internal Rate of Return:  {response.irr_percentage:.1f}%")
    print(f"Payback Period:          {response.payback_years:.1f} years")
    print(f"Annual Savings:          {response.annual_savings_nok:,.0f} NOK")
    print(f"Self-Consumption Rate:   {response.self_consumption_rate:.1%}")
    print(f"Peak Reduction:          {response.peak_reduction_percentage:.1%}")
    print("="*60)

    return response


def run_sensitivity_analysis(args):
    """Run sensitivity analysis"""
    logger.info("Starting sensitivity analysis...")

    # Load configuration
    config = ConfigurationManager()
    config.load()

    # Create use case
    sensitivity = SensitivityAnalysisUseCase(config)

    # Run analysis
    request = SensitivityAnalysisRequest(
        base_battery_cost=args.battery_cost,
        battery_cost_range=(args.cost_min, args.cost_max),
        battery_cost_steps=args.cost_steps,
        discount_rate_range=(args.discount_min, args.discount_max),
        discount_rate_steps=args.discount_steps,
        parallel_execution=not args.sequential,
        max_workers=args.workers
    )

    logger.info(f"Analyzing {request.battery_cost_steps * request.discount_rate_steps * 3} scenarios...")
    response = sensitivity.execute(request)

    # Display results
    print("\n" + "="*60)
    print("SENSITIVITY ANALYSIS RESULTS")
    print("="*60)
    print(f"Break-even Battery Cost: {response.break_even_battery_cost:.0f} NOK/kWh")
    print(f"Scenarios Analyzed:      {len(response.results_matrix)}")
    print("\nTop 5 Optimal Scenarios:")
    print("-"*60)

    if not response.optimal_scenarios.empty:
        for idx, row in response.optimal_scenarios.head(5).iterrows():
            print(f"Battery Cost: {row['battery_cost_nok_per_kwh']:.0f} NOK/kWh, "
                  f"NPV: {row['npv_nok']:,.0f} NOK, "
                  f"IRR: {row['irr_percentage']:.1f}%")

    print("="*60)

    return response


def generate_report(optimization_result=None, sensitivity_result=None, args=None):
    """Generate analysis report"""
    logger.info("Generating report...")

    # Create use case
    report_generator = GenerateReportUseCase()

    # Generate report
    request = GenerateReportRequest(
        optimization_result=optimization_result,
        sensitivity_result=sensitivity_result,
        output_format=args.format if args else 'html',
        output_directory=Path(args.output if args else 'reports'),
        include_visualizations=True,
        include_recommendations=True
    )

    response = report_generator.execute(request)

    print(f"\nReport generated: {response.report_path}")
    print(f"Visualizations created: {len(response.visualizations_created)}")

    return response


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Battery Optimization System for Solar Installation'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Optimization command
    opt_parser = subparsers.add_parser('optimize', help='Run battery optimization')
    opt_parser.add_argument('--battery-cost', type=float, default=3000,
                           help='Battery cost in NOK/kWh (default: 3000)')
    opt_parser.add_argument('--metric', choices=['npv', 'irr', 'payback'],
                           default='npv', help='Optimization metric')
    opt_parser.add_argument('--max-capacity', type=float, default=200,
                           help='Maximum battery capacity in kWh')
    opt_parser.add_argument('--max-power', type=float, default=100,
                           help='Maximum battery power in kW')
    opt_parser.add_argument('--scenario', type=str,
                           help='Configuration scenario to apply')
    opt_parser.add_argument('--fresh-data', action='store_true',
                           help='Fetch fresh data instead of using cache')
    opt_parser.add_argument('--report', action='store_true',
                           help='Generate report after optimization')

    # Sensitivity analysis command
    sens_parser = subparsers.add_parser('sensitivity',
                                        help='Run sensitivity analysis')
    sens_parser.add_argument('--battery-cost', type=float, default=3000,
                            help='Base battery cost')
    sens_parser.add_argument('--cost-min', type=float, default=1000,
                            help='Minimum battery cost to analyze')
    sens_parser.add_argument('--cost-max', type=float, default=5000,
                            help='Maximum battery cost to analyze')
    sens_parser.add_argument('--cost-steps', type=int, default=10,
                            help='Number of cost steps')
    sens_parser.add_argument('--discount-min', type=float, default=0.03,
                            help='Minimum discount rate')
    sens_parser.add_argument('--discount-max', type=float, default=0.08,
                            help='Maximum discount rate')
    sens_parser.add_argument('--discount-steps', type=int, default=5,
                            help='Number of discount rate steps')
    sens_parser.add_argument('--sequential', action='store_true',
                            help='Run sequentially instead of parallel')
    sens_parser.add_argument('--workers', type=int, default=4,
                            help='Number of parallel workers')
    sens_parser.add_argument('--report', action='store_true',
                            help='Generate report after analysis')

    # Report command
    report_parser = subparsers.add_parser('report',
                                          help='Generate analysis report')
    report_parser.add_argument('--format', choices=['html', 'markdown'],
                              default='html', help='Report format')
    report_parser.add_argument('--output', type=str, default='reports',
                              help='Output directory for report')

    # Full analysis command
    full_parser = subparsers.add_parser('full',
                                        help='Run full analysis (optimization + sensitivity + report)')
    full_parser.add_argument('--battery-cost', type=float, default=3000,
                            help='Battery cost in NOK/kWh')

    args = parser.parse_args()

    if args.command == 'optimize':
        result = run_optimization(args)
        if args.report:
            generate_report(optimization_result=result, args=args)

    elif args.command == 'sensitivity':
        result = run_sensitivity_analysis(args)
        if args.report:
            generate_report(sensitivity_result=result, args=args)

    elif args.command == 'report':
        generate_report(args=args)

    elif args.command == 'full':
        # Run complete analysis
        logger.info("Running full analysis...")

        # Run optimization
        opt_args = argparse.Namespace(
            battery_cost=args.battery_cost,
            metric='npv',
            max_capacity=200,
            max_power=100,
            scenario=None,
            fresh_data=False
        )
        opt_result = run_optimization(opt_args)

        # Run sensitivity
        sens_args = argparse.Namespace(
            battery_cost=args.battery_cost,
            cost_min=1000,
            cost_max=5000,
            cost_steps=10,
            discount_min=0.03,
            discount_max=0.08,
            discount_steps=5,
            sequential=False,
            workers=4
        )
        sens_result = run_sensitivity_analysis(sens_args)

        # Generate comprehensive report
        report_args = argparse.Namespace(
            format='html',
            output='reports'
        )
        generate_report(opt_result, sens_result, report_args)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()