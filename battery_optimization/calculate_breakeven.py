"""
Calculate Break-Even Battery Cost

Determines the maximum battery cost (NOK/kWh) that results in NPV = 0
for the heuristic battery strategy.

Assumptions:
- Battery lifetime: 10 years
- Discount rate: 5%
- Annual savings from simulation are representative
- No degradation adjustment (constant annual savings)
- No residual value at end of life
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


def calculate_npv(initial_investment: float,
                  annual_savings: float,
                  lifetime_years: int,
                  discount_rate: float) -> float:
    """
    Calculate Net Present Value (NPV)

    NPV = -Initial_Investment + Σ(Annual_Savings / (1 + r)^t) for t=1 to lifetime

    Args:
        initial_investment: Battery cost (NOK)
        annual_savings: Annual electricity cost savings (NOK/year)
        lifetime_years: Battery lifetime (years)
        discount_rate: Annual discount rate (e.g., 0.05 for 5%)

    Returns:
        npv: Net present value (NOK)
    """
    # Present value of future savings
    pv_savings = 0.0
    for year in range(1, lifetime_years + 1):
        pv_savings += annual_savings / (1 + discount_rate) ** year

    # NPV = PV of benefits - Initial cost
    npv = pv_savings - initial_investment

    return npv


def calculate_breakeven_cost(annual_savings: float,
                             battery_capacity_kwh: float,
                             lifetime_years: int,
                             discount_rate: float) -> float:
    """
    Calculate break-even battery cost per kWh

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
        breakeven_cost_per_kwh: Maximum cost per kWh for NPV=0 (NOK/kWh)
    """
    # Calculate present value of annual savings
    pv_savings = 0.0
    for year in range(1, lifetime_years + 1):
        pv_savings += annual_savings / (1 + discount_rate) ** year

    # Break-even cost
    breakeven_cost_per_kwh = pv_savings / battery_capacity_kwh

    return breakeven_cost_per_kwh


def calculate_annuity_factor(lifetime_years: int, discount_rate: float) -> float:
    """
    Calculate annuity factor for present value calculation

    Annuity factor = Σ(1 / (1+r)^t) for t=1 to n
                   = (1 - (1+r)^-n) / r

    Args:
        lifetime_years: Number of years
        discount_rate: Discount rate

    Returns:
        annuity_factor: Present value factor for annuity
    """
    if discount_rate == 0:
        return lifetime_years

    annuity_factor = (1 - (1 + discount_rate) ** -lifetime_years) / discount_rate
    return annuity_factor


def main():
    print("\n" + "="*80)
    print(" BREAK-EVEN BATTERY COST ANALYSIS")
    print("="*80)

    # Parameters
    battery_capacity_kwh = 20.0
    battery_power_kw = 10.0
    lifetime_years = 10
    discount_rate = 0.05

    print("\nAssumptions:")
    print("-" * 80)
    print(f"   Battery capacity:              {battery_capacity_kwh:>8.0f} kWh")
    print(f"   Battery power:                 {battery_power_kw:>8.0f} kW")
    print(f"   Battery lifetime:              {lifetime_years:>8.0f} years")
    print(f"   Discount rate:                 {discount_rate*100:>8.1f} %")

    # Load data and run simulations
    print("\nLoading data and running simulations...")

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
        capacity_kwh=battery_capacity_kwh,
        power_kw=battery_power_kw,
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

    # Calculate costs
    costs_ref = calculate_total_cost(
        grid_import_power=results_ref['grid_power_kw'].clip(lower=0).values,
        grid_export_power=(-results_ref['grid_power_kw'].clip(upper=0)).values,
        timestamps=timestamps,
        spot_prices=spot_prices.values,
        timestep_hours=1.0
    )

    costs_heur = calculate_total_cost(
        grid_import_power=results_heur['grid_power_kw'].clip(lower=0).values,
        grid_export_power=(-results_heur['grid_power_kw'].clip(upper=0)).values,
        timestamps=timestamps,
        spot_prices=spot_prices.values,
        timestep_hours=1.0
    )

    annual_savings = costs_ref['total_cost_nok'] - costs_heur['total_cost_nok']

    print("  ✓ Simulations complete")

    # Calculate break-even cost
    print("\n" + "="*80)
    print(" BREAK-EVEN ANALYSIS")
    print("="*80)

    print("\n1. ANNUAL SAVINGS")
    print("-" * 80)
    print(f"   Reference case cost:           {costs_ref['total_cost_nok']:>12,.0f} NOK/year")
    print(f"   Heuristic strategy cost:       {costs_heur['total_cost_nok']:>12,.0f} NOK/year")
    print(f"   Annual savings:                {annual_savings:>12,.0f} NOK/year")

    # Calculate annuity factor
    annuity_factor = calculate_annuity_factor(lifetime_years, discount_rate)

    print("\n2. PRESENT VALUE CALCULATIONS")
    print("-" * 80)
    print(f"   Annuity factor (PV of $1/year): {annuity_factor:>11.4f}")
    print(f"   PV of total savings:            {annual_savings * annuity_factor:>12,.0f} NOK")

    # Calculate break-even cost
    breakeven_cost_per_kwh = calculate_breakeven_cost(
        annual_savings=annual_savings,
        battery_capacity_kwh=battery_capacity_kwh,
        lifetime_years=lifetime_years,
        discount_rate=discount_rate
    )

    breakeven_total_cost = breakeven_cost_per_kwh * battery_capacity_kwh

    print("\n3. BREAK-EVEN BATTERY COST")
    print("-" * 80)
    print(f"   Break-even cost (total):       {breakeven_total_cost:>12,.0f} NOK")
    print(f"   Break-even cost (per kWh):     {breakeven_cost_per_kwh:>12,.0f} NOK/kWh")
    print(f"   Break-even cost (per kW):      {breakeven_total_cost/battery_power_kw:>12,.0f} NOK/kW")

    # Market comparison
    market_cost_per_kwh = 5000  # Current market price
    market_total_cost = market_cost_per_kwh * battery_capacity_kwh

    print("\n4. MARKET COMPARISON")
    print("-" * 80)
    print(f"   Current market price:          {market_cost_per_kwh:>12,.0f} NOK/kWh")
    print(f"   Current market cost (total):   {market_total_cost:>12,.0f} NOK")
    print(f"   Required price reduction:      {market_cost_per_kwh - breakeven_cost_per_kwh:>12,.0f} NOK/kWh "
          f"({(1 - breakeven_cost_per_kwh/market_cost_per_kwh)*100:>.1f}%)")

    # NPV at market prices
    npv_market = calculate_npv(
        initial_investment=market_total_cost,
        annual_savings=annual_savings,
        lifetime_years=lifetime_years,
        discount_rate=discount_rate
    )

    print(f"\n   NPV at market prices:          {npv_market:>12,.0f} NOK")
    if npv_market < 0:
        print(f"   → Investment NOT viable (NPV < 0)")
    else:
        print(f"   → Investment IS viable (NPV > 0)")

    # NPV at break-even prices
    npv_breakeven = calculate_npv(
        initial_investment=breakeven_total_cost,
        annual_savings=annual_savings,
        lifetime_years=lifetime_years,
        discount_rate=discount_rate
    )

    print(f"\n   NPV at break-even prices:      {npv_breakeven:>12,.0f} NOK")
    print(f"   → Verification: NPV should be ~0")

    # Sensitivity analysis
    print("\n5. SENSITIVITY ANALYSIS")
    print("-" * 80)
    print(f"\n   Break-even cost for different lifetimes:")
    print(f"   {'Lifetime':<12} {'Annuity Factor':<18} {'Break-even (NOK/kWh)':<22}")
    print("-" * 80)

    for life in [5, 10, 15, 20]:
        af = calculate_annuity_factor(life, discount_rate)
        be_cost = calculate_breakeven_cost(annual_savings, battery_capacity_kwh, life, discount_rate)
        print(f"   {life:>2d} years     {af:>15.4f}     {be_cost:>18,.0f}")

    print(f"\n   Break-even cost for different discount rates ({lifetime_years}-year lifetime):")
    print(f"   {'Discount Rate':<15} {'Annuity Factor':<18} {'Break-even (NOK/kWh)':<22}")
    print("-" * 80)

    for rate in [0.03, 0.05, 0.07, 0.10]:
        af = calculate_annuity_factor(lifetime_years, rate)
        be_cost = calculate_breakeven_cost(annual_savings, battery_capacity_kwh, lifetime_years, rate)
        print(f"   {rate*100:>5.1f}%          {af:>15.4f}     {be_cost:>18,.0f}")

    # Summary
    print("\n" + "="*80)
    print(" SUMMARY")
    print("="*80)

    print(f"\n   With the current heuristic strategy saving {annual_savings:,.0f} NOK/year,")
    print(f"   the maximum viable battery cost is {breakeven_cost_per_kwh:,.0f} NOK/kWh.")
    print()
    print(f"   Current market prices ({market_cost_per_kwh:,.0f} NOK/kWh) would require:")
    print(f"   • {(market_cost_per_kwh/breakeven_cost_per_kwh):.1f}x higher annual savings, OR")
    print(f"   • {(1-breakeven_cost_per_kwh/market_cost_per_kwh)*100:.1f}% battery cost reduction")
    print()
    print("   Potential paths to viability:")
    print("   1. Implement LP optimization for higher savings")
    print("   2. Wait for battery prices to fall below ~900 NOK/kWh")
    print("   3. Explore additional revenue streams (grid services, etc.)")
    print("   4. Increase battery lifetime through proper O&M")

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
