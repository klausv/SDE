#!/usr/bin/env python
"""
MAIN ENTRY POINT FOR BATTERY ANALYSIS
Simple, clean, one way to run everything
"""
import argparse
import pandas as pd
import numpy as np
from core import Battery, EconomicAnalyzer
from core.value_drivers import calculate_all_value_drivers
from core.result_presenter import BatteryAnalysisResults, ResultPresenter
from core.optimizer import BatteryOptimizer  # REAL optimizer!
from core.pvgis_solar import PVGISProduction  # REAL solar data!
from core.entso_e_prices import ENTSOEPrices  # REAL prices!


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Battery Optimization Analysis')

    # Battery parameters
    parser.add_argument('--battery-kwh', type=float, default=50,
                        help='Battery capacity in kWh (default: 50)')
    parser.add_argument('--battery-kw', type=float, default=20,
                        help='Battery power in kW (default: 20)')
    parser.add_argument('--battery-cost', type=float, default=3500,
                        help='Battery cost NOK/kWh (default: 3500)')

    # System parameters
    parser.add_argument('--pv-kwp', type=float, default=138.55,
                        help='PV capacity in kWp (default: 138.55)')
    parser.add_argument('--consumption', type=float, default=90000,
                        help='Annual consumption in kWh (default: 90000)')
    parser.add_argument('--grid-limit', type=float, default=77,
                        help='Grid export limit in kW (default: 77)')

    # Analysis options
    parser.add_argument('--format', choices=['full', 'summary'], default='full',
                        help='Output format (default: full)')
    parser.add_argument('--sensitivity', action='store_true',
                        help='Include sensitivity analysis')
    parser.add_argument('--optimize', action='store_true',
                        help='Run REAL optimization (not simplified)')
    parser.add_argument('--refresh-data', action='store_true',
                        help='Hent nye data fra API selv om cache finnes')
    parser.add_argument('--refresh-prices', action='store_true',
                        help='Hent nye prisdata selv om cached priser finnes')

    args = parser.parse_args()

    # 1. Get REAL solar production from PVGIS
    print("\n☀️ Solproduksjon fra PVGIS...")
    pvgis = PVGISProduction(
        lat=58.97,  # Stavanger
        lon=5.73,
        pv_capacity_kwp=args.pv_kwp,
        tilt=30,
        azimuth=180
    )
    production = pvgis.fetch_hourly_production(year=2020, refresh=args.refresh_data)

    # Generate realistic consumption profile
    hourly_pattern = np.array([
        0.3, 0.3, 0.3, 0.3, 0.3, 0.4,  # 00-06: night
        0.6, 0.8, 1.0, 1.0, 1.0, 0.9,  # 06-12: morning
        0.7, 0.8, 0.9, 1.0, 0.9, 0.7,  # 12-18: afternoon
        0.5, 0.4, 0.3, 0.3, 0.3, 0.3   # 18-24: evening
    ])

    # Adjust for actual hours in production data
    n_hours = len(production)
    base_load = args.consumption / 8760 / 0.6  # Still base on standard year
    consumption_values = []
    for i in range(n_hours):
        hour = i % 24
        consumption_values.append(base_load * hourly_pattern[hour])

    consumption = pd.Series(
        consumption_values,
        index=production.index,
        name='consumption_kw'
    )

    # 2. Get REAL spot prices from ENTSO-E
    print("\n💶 Spotpriser fra ENTSO-E...")
    entsoe = ENTSOEPrices()
    # Use separate flag for price refresh
    prices = entsoe.fetch_prices(year=2023, area='NO2', refresh=args.refresh_prices or args.refresh_data)

    # Align price with production length
    if len(prices) != len(production):
        print(f"⚠️ Justerer lengde: {len(production)} timer produksjon, {len(prices)} timer priser")
        if len(prices) > len(production):
            prices = prices[:len(production)]
        else:
            # Repeat last values if needed
            last_price = prices.iloc[-1]
            extra_hours = len(production) - len(prices)
            extra_prices = pd.Series([last_price] * extra_hours)
            prices = pd.concat([prices, extra_prices])

    prices = pd.Series(prices.values, index=production.index, name='spot_price_nok')

    # Check if we should run REAL optimization
    if args.optimize:
        print("\n🚀 KJØRER EKTE OPTIMALISERING MED TIME-FOR-TIME SIMULERING!")
        print("   Dette tar 30-60 sekunder...")

        optimizer = BatteryOptimizer(
            grid_limit_kw=args.grid_limit,
            efficiency=0.95  # Modern LFP
        )

        opt_result = optimizer.optimize(
            production=production,
            consumption=consumption,
            spot_prices=prices,
            target_battery_cost=args.battery_cost
        )

        print(f"\n✅ OPTIMAL BATTERISTØRRELSE FUNNET:")
        print(f"   • Kapasitet: {opt_result.optimal_capacity_kwh:.0f} kWh")
        print(f"   • Effekt: {opt_result.optimal_power_kw:.0f} kW")
        print(f"   • Timer: {opt_result.optimal_capacity_kwh/opt_result.optimal_power_kw:.1f}h batteri")
        print(f"   • C-rate: {opt_result.optimal_c_rate:.2f}")
        print(f"   • NPV: {opt_result.npv_at_target_cost:,.0f} NOK")
        print(f"   • Break-even: {opt_result.max_battery_cost_per_kwh:,.0f} NOK/kWh")

        # Use optimized values for rest of analysis
        args.battery_kwh = opt_result.optimal_capacity_kwh
        args.battery_kw = opt_result.optimal_power_kw

        # Store optimization metrics
        optimization_metrics = opt_result.operation_metrics
    else:
        print("\n⏳ Kjører batterianalyse...")
        print(f"   Batteri: {args.battery_kwh} kWh / {args.battery_kw} kW")
        print(f"   Kostnad: {args.battery_cost:,} NOK/kWh")
        print("   (Bruk --optimize for EKTE optimalisering)")
        optimization_metrics = None

    # Create dataframe
    data = pd.DataFrame({
        'production_kw': production,
        'consumption_kw': consumption,
        'spot_price_nok': prices
    })

    # 2. Calculate value drivers
    value_drivers = calculate_all_value_drivers(
        data=data,
        battery_capacity_kwh=args.battery_kwh,
        battery_power_kw=args.battery_kw,
        grid_limit_kw=args.grid_limit
    )

    # 3. Economic analysis
    analyzer = EconomicAnalyzer()
    economics = analyzer.analyze_battery(
        battery_capacity_kwh=args.battery_kwh,
        battery_cost_per_kwh=args.battery_cost,
        annual_value=value_drivers['total_annual_value_nok']
    )

    # 4. Break-even
    break_even = analyzer.find_break_even_cost(
        battery_capacity_kwh=args.battery_kwh,
        annual_value=value_drivers['total_annual_value_nok']
    )

    # 5. Optional sensitivity analysis
    sensitivity_results = None
    if args.sensitivity:
        from core.economic_analysis import sensitivity_analysis
        sensitivity_results = sensitivity_analysis(
            base_capacity_kwh=args.battery_kwh,
            base_annual_value=value_drivers['total_annual_value_nok'],
            cost_range=(2000, 6000),
            cost_steps=9
        )

    # 6. Create results object
    results = BatteryAnalysisResults(
        # System parameters
        pv_capacity_kwp=args.pv_kwp,
        inverter_limit_kw=110,  # Fixed for now
        battery_capacity_kwh=args.battery_kwh,
        battery_power_kw=args.battery_kw,
        grid_limit_kw=args.grid_limit,
        annual_consumption_kwh=args.consumption,

        # Data summary
        annual_production_mwh=production.sum() / 1000,
        annual_consumption_mwh=consumption.sum() / 1000,
        avg_spot_price=prices.mean(),

        # Value drivers
        curtailment_kwh=value_drivers['curtailment']['total_kwh'],
        curtailment_value_nok=value_drivers['curtailment']['annual_value_nok'],
        arbitrage_value_nok=value_drivers['arbitrage']['annual_value_nok'],
        demand_charge_value_nok=value_drivers['demand_charge']['annual_value_nok'],
        self_consumption_value_nok=value_drivers['self_consumption']['annual_value_nok'],
        total_annual_value_nok=value_drivers['total_annual_value_nok'],

        # Economics
        battery_cost_per_kwh=args.battery_cost,
        initial_investment=economics['initial_investment'],
        npv=economics['npv'],
        irr=economics['irr'],
        payback_years=economics['payback_years'],
        break_even_cost=break_even,
        sensitivity_results=sensitivity_results
    )

    # 7. Present results
    presenter = ResultPresenter(results)
    if args.format == 'full':
        presenter.print_full_report()
    else:
        presenter.print_summary()

    return results


if __name__ == '__main__':
    import numpy as np  # Needed for price generation
    results = main()