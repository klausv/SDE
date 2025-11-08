"""
Break-even Battery Cost Analysis with CORRECTED Degradation Formula

Runs full-year LP optimization with:
- 30 kWh battery capacity
- 15 kW power rating
- PT60M (hourly) resolution
- CORRECTED degradation costs (divide by 20%, not 100%)

Calculates:
1. Annual savings (energy + power - degradation)
2. Endogenous battery lifetime from cumulative degradation
3. Break-even battery cost with proper replacement accounting
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from config import BatteryOptimizationConfig
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.price_fetcher import fetch_nordpool_prices
from core.solar_production import get_hourly_pv_production
from core.load_profile import generate_commercial_load_profile

# Configuration
BATTERY_KWH = 30.0
BATTERY_KW = 15.0
RESOLUTION = 'PT60M'
YEAR = 2024

# Economic parameters
DISCOUNT_RATE = 0.05
ANALYSIS_HORIZON = 15  # years
EOL_DEGRADATION = 20.0  # % degradation = end of life (80% SOH)

def calculate_annuity_factor(rate: float, periods: int) -> float:
    """Calculate present value annuity factor"""
    return (1 - (1 + rate)**(-periods)) / rate

def calculate_npv_with_replacements(annual_savings: float,
                                    battery_cost: float,
                                    lifetime_years: float,
                                    analysis_horizon: int = 15,
                                    discount_rate: float = 0.05) -> float:
    """
    Calculate NPV accounting for battery replacements.

    Args:
        annual_savings: Annual net savings (NOK/year)
        battery_cost: Battery system cost (NOK)
        lifetime_years: Battery lifetime until 80% SOH (years)
        analysis_horizon: Analysis period (years)
        discount_rate: Discount rate (%)

    Returns:
        NPV (NOK)
    """
    # PV of annual savings
    pv_savings = annual_savings * calculate_annuity_factor(discount_rate, analysis_horizon)

    # PV of battery replacements
    replacement_years = []
    year = lifetime_years
    while year < analysis_horizon:
        replacement_years.append(year)
        year += lifetime_years

    pv_replacements = sum(
        battery_cost / (1 + discount_rate)**year
        for year in replacement_years
    )

    total_investment = battery_cost + pv_replacements

    return pv_savings - total_investment

def calculate_breakeven_cost(annual_savings: float,
                             lifetime_years: float,
                             battery_kwh: float,
                             analysis_horizon: int = 15,
                             discount_rate: float = 0.05) -> float:
    """
    Calculate break-even battery cost (NOK/kWh) where NPV = 0.

    Accounts for battery replacements over analysis horizon.
    """
    # PV of annual savings
    pv_savings = annual_savings * calculate_annuity_factor(discount_rate, analysis_horizon)

    # Number of batteries needed over analysis horizon
    num_batteries = 1 + int((analysis_horizon - 1) / lifetime_years)

    # PV factor for each replacement
    pv_factors = [1.0]  # First battery at t=0
    year = lifetime_years
    while year < analysis_horizon:
        pv_factors.append(1 / (1 + discount_rate)**year)
        year += lifetime_years

    total_pv_factor = sum(pv_factors)

    # Break-even: PV(savings) = Total investment
    # Total investment = battery_cost_per_kwh × battery_kwh × total_pv_factor
    breakeven_cost_per_kwh = pv_savings / (battery_kwh * total_pv_factor)

    return breakeven_cost_per_kwh

print("="*80)
print("BREAK-EVEN BATTERY COST ANALYSIS")
print("With CORRECTED Degradation Formula (÷20%, not ÷100%)")
print("="*80)
print(f"\nConfiguration:")
print(f"  Battery: {BATTERY_KWH} kWh @ {BATTERY_KW} kW")
print(f"  E/P ratio: {BATTERY_KWH/BATTERY_KW:.1f} hours")
print(f"  Resolution: {RESOLUTION}")
print(f"  Year: {YEAR}")
print(f"  Analysis horizon: {ANALYSIS_HORIZON} years")
print(f"  Discount rate: {DISCOUNT_RATE*100:.0f}%")

# Initialize configuration
config = BatteryOptimizationConfig()
config.battery.degradation.enabled = True  # Enable degradation modeling

print(f"\nDegradation Model:")
print(f"  Type: LFP (Lithium Iron Phosphate)")
print(f"  Cycle life: {config.battery.degradation.cycle_life_full_dod:,} cycles @ 100% DOD")
print(f"  Calendar life: {config.battery.degradation.calendar_life_years:.1f} years")
print(f"  EOL threshold: {config.battery.degradation.eol_degradation_percent}% degradation (80% SOH)")
print(f"  ρ_constant: {config.battery.degradation.rho_constant:.6f} %/cycle")
print(f"  Battery cell cost: {config.battery.get_battery_cost():,.0f} NOK/kWh")

# Initialize optimizer
optimizer = MonthlyLPOptimizer(
    config=config,
    resolution=RESOLUTION,
    battery_kwh=BATTERY_KWH,
    battery_kw=BATTERY_KW
)

print(f"\n{'='*80}")
print("FETCHING DATA")
print("="*80)

# Fetch spot prices for entire year
print(f"\nFetching spot prices for {YEAR}...")
spot_prices_df = fetch_nordpool_prices(
    year=YEAR,
    area='NO2',
    resolution=RESOLUTION
)
print(f"  Loaded {len(spot_prices_df)} hourly prices")

# Generate PV production
print(f"\nGenerating PV production profile...")
pv_production_df = get_hourly_pv_production(
    year=YEAR,
    pv_capacity_kw=config.solar.pv_capacity_kwp,
    latitude=config.location.latitude,
    longitude=config.location.longitude,
    tilt=config.solar.tilt_degrees,
    azimuth=config.solar.azimuth_degrees
)
print(f"  Generated {len(pv_production_df)} hourly values")

# Generate load profile
print(f"\nGenerating load consumption profile...")
load_profile_df = generate_commercial_load_profile(
    year=YEAR,
    annual_kwh=config.consumption.annual_kwh,
    base_load_kw=config.consumption.base_load_kw,
    peak_load_kw=config.consumption.peak_load_kw
)
print(f"  Generated {len(load_profile_df)} hourly values")

# Combine data
print(f"\nCombining datasets...")
data = pd.DataFrame({
    'spot_price': spot_prices_df['price'],
    'pv_production': pv_production_df['power_kw'],
    'load_consumption': load_profile_df['load_kw']
}, index=spot_prices_df.index)

# Remove any NaN values
data = data.dropna()
print(f"  Final dataset: {len(data)} hours")

print(f"\n{'='*80}")
print("RUNNING MONTHLY OPTIMIZATIONS")
print("="*80)

monthly_results = []
E_initial = BATTERY_KWH * 0.5  # Start at 50% SOC

for month in range(1, 13):
    print(f"\n{'─'*80}")
    print(f"Month {month}")

    # Filter data for this month
    month_data = data[data.index.month == month].copy()

    if len(month_data) == 0:
        print(f"  ⚠️  No data for month {month}, skipping...")
        continue

    # Run optimization
    result = optimizer.optimize_month(
        month_idx=month,
        pv_production=month_data['pv_production'].values,
        load_consumption=month_data['load_consumption'].values,
        spot_prices=month_data['spot_price'].values,
        timestamps=month_data.index,
        E_initial=E_initial
    )

    if result.success:
        monthly_results.append({
            'month': month,
            'energy_cost': result.energy_cost,
            'power_cost': result.power_cost,
            'degradation_cost': result.degradation_cost,
            'total_cost': result.objective_value,
            'P_peak': result.P_peak,
            'degradation_total': np.sum(result.DP_total) if result.DP_total is not None else 0,
            'degradation_cyclic': np.sum(result.DP_cyc) if result.DP_cyc is not None else 0,
            'equivalent_cycles': np.sum(result.DOD_abs) if result.DOD_abs is not None else 0,
        })

        # Update initial SOC for next month
        E_initial = result.E_battery_final
    else:
        print(f"  ⚠️  Optimization failed: {result.message}")

print(f"\n{'='*80}")
print("REFERENCE CASE (No Battery)")
print("="*80)

# Calculate reference case
ref_optimizer = MonthlyLPOptimizer(
    config=config,
    resolution=RESOLUTION,
    battery_kwh=0,  # No battery
    battery_kw=0
)

ref_total_cost = 0
for month in range(1, 13):
    month_data = data[data.index.month == month].copy()
    if len(month_data) == 0:
        continue

    ref_result = ref_optimizer.optimize_month(
        month_idx=month,
        pv_production=month_data['pv_production'].values,
        load_consumption=month_data['load_consumption'].values,
        spot_prices=month_data['spot_price'].values,
        timestamps=month_data.index,
        E_initial=0
    )

    if ref_result.success:
        ref_total_cost += ref_result.objective_value

print(f"\nReference case (no battery) annual cost: {ref_total_cost:,.0f} NOK")

print(f"\n{'='*80}")
print("ANNUAL RESULTS SUMMARY")
print("="*80)

# Aggregate annual results
results_df = pd.DataFrame(monthly_results)

annual_energy_cost = results_df['energy_cost'].sum()
annual_power_cost = results_df['power_cost'].sum()
annual_degradation_cost = results_df['degradation_cost'].sum()
annual_total_cost = results_df['total_cost'].sum()
annual_degradation = results_df['degradation_total'].sum()
annual_degradation_cyclic = results_df['degradation_cyclic'].sum()
annual_cycles = results_df['equivalent_cycles'].sum()

print(f"\nBattery Case Annual Costs:")
print(f"  Energy cost:        {annual_energy_cost:>12,.0f} NOK")
print(f"  Power cost:         {annual_power_cost:>12,.0f} NOK")
print(f"  Degradation cost:   {annual_degradation_cost:>12,.0f} NOK")
print(f"  ─────────────────────────────────")
print(f"  Total cost:         {annual_total_cost:>12,.0f} NOK")

annual_savings = ref_total_cost - annual_total_cost

print(f"\nSavings Comparison:")
print(f"  Reference case:     {ref_total_cost:>12,.0f} NOK")
print(f"  Battery case:       {annual_total_cost:>12,.0f} NOK")
print(f"  ─────────────────────────────────")
print(f"  Annual savings:     {annual_savings:>12,.0f} NOK", end="")
if annual_savings > 0:
    print(" ✓")
else:
    print(" ❌")

print(f"\nDegradation Metrics:")
print(f"  Total degradation:  {annual_degradation:>12.2f} %")
print(f"  Cyclic degradation: {annual_degradation_cyclic:>12.2f} %")
print(f"  Calendar degradation: {annual_degradation - annual_degradation_cyclic:>10.2f} %")
print(f"  Equivalent cycles:  {annual_cycles:>12.0f} cycles/year")

# Calculate endogenous lifetime
endogenous_lifetime = EOL_DEGRADATION / annual_degradation
print(f"\nEndogenous Battery Lifetime:")
print(f"  Annual degradation rate: {annual_degradation:.2f}%/year")
print(f"  Lifetime to 80% SOH:     {endogenous_lifetime:.1f} years")

# Number of replacements needed
num_replacements = int((ANALYSIS_HORIZON - 1) / endogenous_lifetime)
print(f"  Replacements needed over {ANALYSIS_HORIZON} years: {num_replacements}")

print(f"\n{'='*80}")
print("BREAK-EVEN ANALYSIS")
print("="*80)

# Calculate break-even cost
breakeven_cost = calculate_breakeven_cost(
    annual_savings=annual_savings,
    lifetime_years=endogenous_lifetime,
    battery_kwh=BATTERY_KWH,
    analysis_horizon=ANALYSIS_HORIZON,
    discount_rate=DISCOUNT_RATE
)

print(f"\nBreak-Even Battery Cost:")
print(f"  Cost per kWh:       {breakeven_cost:>12,.0f} NOK/kWh")
print(f"  Total system cost:  {breakeven_cost * BATTERY_KWH:>12,.0f} NOK")

# Compare to market
market_cost = config.battery.battery_cell_cost_nok_per_kwh
system_cost = config.battery.get_system_cost_per_kwh(BATTERY_KWH)

print(f"\nMarket Comparison:")
print(f"  Battery cells only: {market_cost:>12,.0f} NOK/kWh")
print(f"  Full system cost:   {system_cost:>12,.0f} NOK/kWh")
print(f"  Break-even cost:    {breakeven_cost:>12,.0f} NOK/kWh")
print(f"  ─────────────────────────────────")
gap_cells = market_cost - breakeven_cost
gap_system = system_cost - breakeven_cost
print(f"  Gap (cells only):   {gap_cells:>12,.0f} NOK/kWh ({gap_cells/market_cost*100:+.1f}%)")
print(f"  Gap (full system):  {gap_system:>12,.0f} NOK/kWh ({gap_system/system_cost*100:+.1f}%)")

# NPV at market prices
npv_cells = calculate_npv_with_replacements(
    annual_savings=annual_savings,
    battery_cost=market_cost * BATTERY_KWH,
    lifetime_years=endogenous_lifetime,
    analysis_horizon=ANALYSIS_HORIZON,
    discount_rate=DISCOUNT_RATE
)

npv_system = calculate_npv_with_replacements(
    annual_savings=annual_savings,
    battery_cost=system_cost * BATTERY_KWH,
    lifetime_years=endogenous_lifetime,
    analysis_horizon=ANALYSIS_HORIZON,
    discount_rate=DISCOUNT_RATE
)

print(f"\nNPV at Market Prices:")
print(f"  Cells only:         {npv_cells:>12,.0f} NOK", end="")
if npv_cells > 0:
    print(" ✓ Profitable")
else:
    print(" ❌ Not profitable")

print(f"  Full system:        {npv_system:>12,.0f} NOK", end="")
if npv_system > 0:
    print(" ✓ Profitable")
else:
    print(" ❌ Not profitable")

print(f"\n{'='*80}")
print("DETAILED CASH FLOW ANALYSIS")
print("="*80)

print(f"\nAssumptions:")
print(f"  Annual savings:     {annual_savings:,.0f} NOK/year")
print(f"  Battery lifetime:   {endogenous_lifetime:.1f} years")
print(f"  Analysis horizon:   {ANALYSIS_HORIZON} years")
print(f"  Discount rate:      {DISCOUNT_RATE*100:.0f}%")

print(f"\nReplacement Schedule (at system cost {system_cost:,.0f} NOK/kWh):")
print(f"  Initial battery (Year 0):  {system_cost * BATTERY_KWH:>12,.0f} NOK")

year = endogenous_lifetime
replacement_num = 1
while year < ANALYSIS_HORIZON:
    cost_nominal = system_cost * BATTERY_KWH
    cost_pv = cost_nominal / (1 + DISCOUNT_RATE)**year
    print(f"  Replacement {replacement_num} (Year {year:.1f}): {cost_nominal:>12,.0f} NOK (PV: {cost_pv:,.0f} NOK)")
    year += endogenous_lifetime
    replacement_num += 1

total_investment_pv = system_cost * BATTERY_KWH * (
    1 + sum(1 / (1 + DISCOUNT_RATE)**(i * endogenous_lifetime)
            for i in range(1, num_replacements + 1))
)

pv_savings = annual_savings * calculate_annuity_factor(DISCOUNT_RATE, ANALYSIS_HORIZON)

print(f"\nPresent Value Summary:")
print(f"  PV of annual savings ({ANALYSIS_HORIZON} years): {pv_savings:>12,.0f} NOK")
print(f"  PV of total investment:          {total_investment_pv:>12,.0f} NOK")
print(f"  ─────────────────────────────────")
print(f"  NPV:                             {pv_savings - total_investment_pv:>12,.0f} NOK")

print(f"\n{'='*80}")
print("SENSITIVITY ANALYSIS")
print("="*80)

print(f"\nBreak-even cost at different cycle rates:")

for cycle_rate_multiplier in [0.5, 0.75, 1.0, 1.25, 1.5]:
    adj_cycles = annual_cycles * cycle_rate_multiplier
    adj_degradation = annual_degradation_cyclic * cycle_rate_multiplier + (annual_degradation - annual_degradation_cyclic)
    adj_lifetime = EOL_DEGRADATION / adj_degradation

    # Approximate savings adjustment (rough estimate)
    adj_savings = annual_savings * cycle_rate_multiplier * 0.8  # Revenue scales with cycling

    adj_breakeven = calculate_breakeven_cost(
        annual_savings=adj_savings,
        lifetime_years=adj_lifetime,
        battery_kwh=BATTERY_KWH,
        analysis_horizon=ANALYSIS_HORIZON,
        discount_rate=DISCOUNT_RATE
    )

    print(f"  {adj_cycles:>5.0f} cycles/year ({adj_degradation:>4.1f}%/year, {adj_lifetime:>4.1f}yr): {adj_breakeven:>6,.0f} NOK/kWh")

print(f"\n{'='*80}")
print("CONCLUSION")
print("="*80)

if annual_savings > 0:
    print(f"\n✓ Battery operation is PROFITABLE at {annual_cycles:.0f} cycles/year")
    print(f"  Annual savings: {annual_savings:,.0f} NOK")
else:
    print(f"\n❌ Battery operation is NOT PROFITABLE at {annual_cycles:.0f} cycles/year")
    print(f"  Annual loss: {-annual_savings:,.0f} NOK")

print(f"\n  Break-even battery cost: {breakeven_cost:,.0f} NOK/kWh")

if breakeven_cost > system_cost:
    print(f"  ✓ Above market price ({system_cost:,.0f} NOK/kWh) - Investment is viable!")
elif breakeven_cost > market_cost:
    print(f"  ⚠️ Above cell cost ({market_cost:,.0f} NOK/kWh) but below system cost")
    print(f"     Need to reduce inverter/BMS costs for profitability")
else:
    print(f"  ❌ Below market price - Need {system_cost - breakeven_cost:,.0f} NOK/kWh cost reduction")

print(f"\n  Endogenous lifetime: {endogenous_lifetime:.1f} years")
print(f"  Optimal cycle rate: {annual_cycles:.0f} cycles/year")

print(f"\n{'='*80}")
print("SCRIPT COMPLETE")
print("="*80)
