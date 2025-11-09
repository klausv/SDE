"""
Diagnostic Analysis: Why Is Heuristic Strategy Underperforming?

Investigates:
1. When does the battery charge/discharge?
2. Is the strategy properly exploiting price differentials?
3. Is the battery constrained by capacity or power limits?
4. What opportunities are being missed?
"""

import numpy as np
import pandas as pd

from core.battery import Battery
from core.strategies import NoControlStrategy, SimpleRuleStrategy
from core.simulator import BatterySimulator
from core.economic_cost import calculate_total_cost
from core.pvgis_solar import PVGISProduction
from core.price_fetcher import ENTSOEPriceFetcher
from core.consumption_profiles import ConsumptionProfile


def analyze_battery_operation(results_heur, spot_prices, timestamps):
    """
    Analyze when and why the battery operates
    """
    print("\n" + "="*80)
    print(" BATTERY OPERATION ANALYSIS")
    print("="*80)

    # Extract battery operations
    battery_power = results_heur['battery_power_ac_kw'].values
    battery_soc = results_heur['battery_soc_kwh'].values
    grid_power = results_heur['grid_power_kw'].values

    # Identify charging and discharging periods
    charging = battery_power > 0.01  # Charging (positive power)
    discharging = battery_power < -0.01  # Discharging (negative power)
    idle = ~charging & ~discharging

    # Statistics
    total_hours = len(battery_power)
    charging_hours = np.sum(charging)
    discharging_hours = np.sum(discharging)
    idle_hours = np.sum(idle)

    print("\n1. OPERATING TIME DISTRIBUTION")
    print("-" * 80)
    print(f"   Total hours:                   {total_hours:>8,d} hours")
    print(f"   Charging hours:                {charging_hours:>8,d} hours ({charging_hours/total_hours*100:>5.1f}%)")
    print(f"   Discharging hours:             {discharging_hours:>8,d} hours ({discharging_hours/total_hours*100:>5.1f}%)")
    print(f"   Idle hours:                    {idle_hours:>8,d} hours ({idle_hours/total_hours*100:>5.1f}%)")

    # Price statistics during operations
    prices = spot_prices.values

    print("\n2. PRICE STATISTICS DURING OPERATIONS")
    print("-" * 80)
    print(f"{'Operation':<20} {'Count':>8} {'Avg Price':>12} {'Min Price':>12} {'Max Price':>12}")
    print("-" * 80)
    print(f"{'All hours':<20} {total_hours:>8,d} {prices.mean():>12.4f} {prices.min():>12.4f} {prices.max():>12.4f}")
    print(f"{'Charging':<20} {charging_hours:>8,d} {prices[charging].mean():>12.4f} {prices[charging].min():>12.4f} {prices[charging].max():>12.4f}")
    print(f"{'Discharging':<20} {discharging_hours:>8,d} {prices[discharging].mean():>12.4f} {prices[discharging].min():>12.4f} {prices[discharging].max():>12.4f}")
    print(f"{'Idle':<20} {idle_hours:>8,d} {prices[idle].mean():>12.4f} {prices[idle].min():>12.4f} {prices[idle].max():>12.4f}")

    # Price differential analysis
    avg_charge_price = prices[charging].mean() if charging_hours > 0 else 0
    avg_discharge_price = prices[discharging].mean() if discharging_hours > 0 else 0
    price_differential = avg_discharge_price - avg_charge_price

    print("\n3. ARBITRAGE EFFECTIVENESS")
    print("-" * 80)
    print(f"   Average charging price:        {avg_charge_price:>12.4f} NOK/kWh")
    print(f"   Average discharge price:       {avg_discharge_price:>12.4f} NOK/kWh")
    print(f"   Price differential:            {price_differential:>12.4f} NOK/kWh")
    print(f"   Arbitrage effectiveness:       {price_differential/avg_charge_price*100:>12.1f} %")

    # Calculate optimal potential (what could have been achieved)
    # Sort hours by price
    sorted_prices = np.sort(prices)
    n_cheap = int(total_hours * 0.25)  # Bottom 25% of hours
    n_expensive = int(total_hours * 0.25)  # Top 25% of hours

    optimal_charge_price = sorted_prices[:n_cheap].mean()
    optimal_discharge_price = sorted_prices[-n_expensive:].mean()
    optimal_differential = optimal_discharge_price - optimal_charge_price

    print("\n4. MISSED ARBITRAGE OPPORTUNITIES")
    print("-" * 80)
    print(f"   Optimal charging price (25%):  {optimal_charge_price:>12.4f} NOK/kWh")
    print(f"   Optimal discharge price (25%): {optimal_discharge_price:>12.4f} NOK/kWh")
    print(f"   Optimal price differential:    {optimal_differential:>12.4f} NOK/kWh")
    print(f"   → Potential improvement:       {(optimal_differential - price_differential)/price_differential*100:>12.1f} %")

    # SOC utilization
    print("\n5. BATTERY STATE OF CHARGE (SOC) UTILIZATION")
    print("-" * 80)
    print(f"   Average SOC:                   {battery_soc.mean():>12.2f} kWh")
    print(f"   Minimum SOC:                   {battery_soc.min():>12.2f} kWh")
    print(f"   Maximum SOC:                   {battery_soc.max():>12.2f} kWh")
    print(f"   SOC range utilized:            {battery_soc.max() - battery_soc.min():>12.2f} kWh")
    print(f"   Hours at minimum SOC (2 kWh):  {np.sum(battery_soc < 2.5):>12,d} ({np.sum(battery_soc < 2.5)/total_hours*100:>5.1f}%)")
    print(f"   Hours at maximum SOC (18 kWh): {np.sum(battery_soc > 17.5):>12,d} ({np.sum(battery_soc > 17.5)/total_hours*100:>5.1f}%)")

    # Power constraints
    print("\n6. POWER CONSTRAINT ANALYSIS")
    print("-" * 80)
    max_charge_power = 10.0  # kW
    max_discharge_power = -10.0  # kW

    constrained_charge = np.sum(battery_power > 9.9)
    constrained_discharge = np.sum(battery_power < -9.9)

    print(f"   Hours constrained by charge power (10 kW): {constrained_charge:>8,d} ({constrained_charge/total_hours*100:>5.1f}%)")
    print(f"   Hours constrained by discharge power (10 kW): {constrained_discharge:>8,d} ({constrained_discharge/total_hours*100:>5.1f}%)")
    print(f"   Average charge power:          {battery_power[charging].mean():>12.2f} kW")
    print(f"   Average discharge power:       {battery_power[discharging].mean():>12.2f} kW")

    return {
        'avg_charge_price': avg_charge_price,
        'avg_discharge_price': avg_discharge_price,
        'price_differential': price_differential,
        'optimal_differential': optimal_differential,
        'charging_hours': charging_hours,
        'discharging_hours': discharging_hours,
        'idle_hours': idle_hours
    }


def analyze_missed_opportunities(results_ref, results_heur, spot_prices, timestamps):
    """
    Identify specific opportunities missed by heuristic strategy
    """
    print("\n" + "="*80)
    print(" MISSED OPPORTUNITIES ANALYSIS")
    print("="*80)

    # Calculate what value could have been captured
    prices = spot_prices.values
    battery_power = results_heur['battery_power_ac_kw'].values

    # Find hours with highest price differentials
    # Sort by price
    price_rank = np.argsort(prices)

    # Bottom 10% (cheapest hours for charging)
    n_cheap = int(len(prices) * 0.10)
    cheap_hours = price_rank[:n_cheap]
    cheap_prices = prices[cheap_hours]

    # Top 10% (most expensive hours for discharging)
    n_expensive = int(len(prices) * 0.10)
    expensive_hours = price_rank[-n_expensive:]
    expensive_prices = prices[expensive_hours]

    # Check how much battery actually operated during these periods
    charging_during_cheap = np.sum(battery_power[cheap_hours] > 0.01)
    discharging_during_expensive = np.sum(battery_power[expensive_hours] < -0.01)

    print("\n1. OPERATION DURING EXTREME PRICE PERIODS")
    print("-" * 80)
    print(f"   Cheapest 10% of hours:")
    print(f"   - Average price:               {cheap_prices.mean():>12.4f} NOK/kWh")
    print(f"   - Battery charging:            {charging_during_cheap:>12,d} hours ({charging_during_cheap/n_cheap*100:>5.1f}%)")
    print(f"\n   Most expensive 10% of hours:")
    print(f"   - Average price:               {expensive_prices.mean():>12.4f} NOK/kWh")
    print(f"   - Battery discharging:         {discharging_during_expensive:>12,d} hours ({discharging_during_expensive/n_expensive*100:>5.1f}%)")

    # Peak shaving analysis
    grid_power_ref = results_ref['grid_power_kw'].values
    grid_power_heur = results_heur['grid_power_kw'].values

    # Monthly peak analysis
    df = pd.DataFrame({
        'timestamp': timestamps,
        'grid_ref': grid_power_ref,
        'grid_heur': grid_power_heur
    })
    df['month'] = df['timestamp'].dt.month

    print("\n2. PEAK SHAVING EFFECTIVENESS")
    print("-" * 80)
    print(f"{'Month':<10} {'Ref Peak (kW)':>15} {'Heur Peak (kW)':>16} {'Reduction (kW)':>16} {'% Reduction':>13}")
    print("-" * 80)

    total_peak_reduction = 0.0
    for month in range(1, 13):
        month_data = df[df['month'] == month]
        peak_ref = month_data['grid_ref'].clip(lower=0).max()
        peak_heur = month_data['grid_heur'].clip(lower=0).max()
        reduction = peak_ref - peak_heur
        reduction_pct = (reduction / peak_ref * 100) if peak_ref > 0 else 0
        total_peak_reduction += reduction

        month_name = pd.Timestamp(2020, month, 1).strftime('%B')
        print(f"{month_name:<10} {peak_ref:>15.2f} {peak_heur:>16.2f} {reduction:>16.2f} {reduction_pct:>12.1f}%")

    avg_peak_reduction = total_peak_reduction / 12
    print("-" * 80)
    print(f"{'Average':<10} {'':<15} {'':<16} {avg_peak_reduction:>16.2f}")

    # Grid export reduction (curtailment prevention)
    grid_export_ref = np.sum(-grid_power_ref * (grid_power_ref < 0))
    grid_export_heur = np.sum(-grid_power_heur * (grid_power_heur < 0))
    export_reduction = grid_export_ref - grid_export_heur

    print("\n3. CURTAILMENT PREVENTION")
    print("-" * 80)
    print(f"   Reference export:              {grid_export_ref:>12,.0f} kWh")
    print(f"   Heuristic export:              {grid_export_heur:>12,.0f} kWh")
    print(f"   Export reduction:              {export_reduction:>12,.0f} kWh ({export_reduction/grid_export_ref*100:>5.1f}%)")
    print(f"   → Stored in battery instead of exporting at low prices")


def main():
    print("\n" + "="*80)
    print(" BATTERY STRATEGY DIAGNOSTIC ANALYSIS")
    print(" Why is the heuristic strategy underperforming?")
    print("="*80)

    # Load data
    print("\nLoading data...")

    pvgis = PVGISProduction(
        lat=58.97, lon=5.73, pv_capacity_kwp=138.55,
        tilt=30, azimuth=173, system_loss=14
    )
    production = pvgis.fetch_hourly_production(2024, refresh=False)
    year = production.index[0].year

    consumption = ConsumptionProfile.generate_annual_profile(
        profile_type='commercial_office',
        annual_kwh=300000,
        year=year
    )

    price_fetcher = ENTSOEPriceFetcher()
    spot_prices = price_fetcher.fetch_prices(2024, 'NO2', refresh=False)
    spot_prices.index = spot_prices.index.map(lambda x: x.replace(year=year))

    if spot_prices.isna().any():
        spot_prices = spot_prices.ffill().bfill()

    min_len = min(len(production), len(consumption), len(spot_prices))
    production = production[:min_len]
    consumption = consumption[:min_len]
    spot_prices = spot_prices[:min_len]
    timestamps = production.index

    print(f"  ✓ Data loaded: {min_len} hours")

    # Run simulations
    print("\nRunning simulations...")

    # Reference case
    strategy_ref = NoControlStrategy()
    sim_ref = BatterySimulator(strategy=strategy_ref, battery=None)
    results_ref = sim_ref.simulate_year(
        production, consumption, spot_prices,
        solar_inverter_capacity_kw=110,
        grid_export_limit_kw=77,
        battery_inverter_efficiency=0.98
    )

    # Heuristic strategy
    battery = Battery(
        capacity_kwh=20.0,
        power_kw=10.0,
        efficiency=0.90,
        min_soc=0.1,
        max_soc=0.9,
        max_c_rate_charge=1.0,
        max_c_rate_discharge=1.0
    )

    strategy_heur = SimpleRuleStrategy(
        cheap_price_threshold=0.3,
        expensive_price_threshold=0.8,
        night_hours=(0, 6)
    )

    sim_heur = BatterySimulator(strategy=strategy_heur, battery=battery)
    results_heur = sim_heur.simulate_year(
        production, consumption, spot_prices,
        solar_inverter_capacity_kw=110,
        grid_export_limit_kw=77,
        battery_inverter_efficiency=0.98
    )

    print("  ✓ Simulations complete")

    # Diagnostic analyses
    operation_stats = analyze_battery_operation(results_heur, spot_prices, timestamps)
    analyze_missed_opportunities(results_ref, results_heur, spot_prices, timestamps)

    # Price volatility analysis
    print("\n" + "="*80)
    print(" PRICE VOLATILITY ANALYSIS")
    print("="*80)

    prices = spot_prices.values
    price_std = prices.std()
    price_range = prices.max() - prices.min()
    price_cv = price_std / prices.mean()  # Coefficient of variation

    print("\n   Price statistics:")
    print(f"   - Mean:                        {prices.mean():>12.4f} NOK/kWh")
    print(f"   - Std deviation:               {price_std:>12.4f} NOK/kWh")
    print(f"   - Coefficient of variation:    {price_cv:>12.2%}")
    print(f"   - Range (min-max):             {price_range:>12.4f} NOK/kWh")
    print(f"   - Min price:                   {prices.min():>12.4f} NOK/kWh")
    print(f"   - Max price:                   {prices.max():>12.4f} NOK/kWh")

    # Key findings summary
    print("\n" + "="*80)
    print(" KEY FINDINGS & RECOMMENDATIONS")
    print("="*80)

    print("\n1. ROOT CAUSES OF POOR PERFORMANCE:")
    print("-" * 80)

    if operation_stats['price_differential'] < 0.1:
        print("   ❌ CRITICAL: Battery is NOT effectively arbitraging prices")
        print(f"      - Price differential: {operation_stats['price_differential']:.4f} NOK/kWh")
        print("      - Strategy charges/discharges at nearly same prices")

    if operation_stats['idle_hours'] / len(spot_prices) > 0.7:
        print("   ❌ Battery is idle most of the time ({:.1f}%)".format(
            operation_stats['idle_hours'] / len(spot_prices) * 100))
        print("      - Not enough charging/discharging activity")

    if operation_stats['optimal_differential'] > operation_stats['price_differential'] * 1.5:
        print("   ❌ Strategy is missing significant arbitrage opportunities")
        print(f"      - Achieved: {operation_stats['price_differential']:.4f} NOK/kWh")
        print(f"      - Potential: {operation_stats['optimal_differential']:.4f} NOK/kWh")

    print("\n2. RECOMMENDED IMPROVEMENTS:")
    print("-" * 80)
    print("   ✓ Implement LP optimization model")
    print("     - Perfect foresight optimization to maximize arbitrage")
    print("     - Coordinate charging/discharging with price forecasts")
    print("   ✓ Increase battery size to 80-100 kWh")
    print("     - More capacity for storing cheap energy")
    print("   ✓ Better price threshold tuning")
    print("     - Current thresholds (0.3, 0.8) may not match price distribution")
    print("   ✓ Include peak tariff optimization")
    print("     - Current strategy doesn't explicitly minimize monthly peaks")

    print("\n" + "="*80)
    print(" Analysis Complete")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
