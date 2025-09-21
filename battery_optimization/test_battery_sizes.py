#!/usr/bin/env python
"""
Test ulike batteristørrelser med 3500 NOK/kWh kostnad
"""
import pandas as pd
import numpy as np
from core import Battery, EconomicAnalyzer
from core.value_drivers import calculate_all_value_drivers
from core.pvgis_solar import PVGISProduction
from core.consumption_profiles import ConsumptionProfile

print("🔋 ANALYSE AV ULIKE BATTERISTØRRELSER (3500 NOK/kWh)")
print("="*60)

# Get production and consumption data
pvgis = PVGISProduction(lat=58.97, lon=5.73, pv_capacity_kwp=138.55)
production = pvgis.fetch_hourly_production(year=2020, refresh=False)

consumption = ConsumptionProfile.generate_annual_profile(
    profile_type='commercial_office',
    annual_kwh=90000,
    year=2020
)

# Get prices (using cached)
cache_file = 'data/spot_prices/spot_NO2_2023.csv'
prices_df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
prices = prices_df['price_nok'] if 'price_nok' in prices_df.columns else prices_df.iloc[:, 0]

# Align data
min_len = min(len(production), len(consumption), len(prices))
production = production[:min_len]
consumption = consumption[:min_len]
prices = prices[:min_len]

# Ensure same index
consumption.index = production.index
prices = pd.Series(prices.values, index=production.index, name='spot_price')

# Test different battery sizes
battery_configs = [
    (10, 5),    # 10 kWh, 5 kW (2.0h)
    (20, 10),   # 20 kWh, 10 kW (2.0h)
    (30, 15),   # 30 kWh, 15 kW (2.0h)
    (40, 20),   # 40 kWh, 20 kW (2.0h)
    (50, 25),   # 50 kWh, 25 kW (2.0h)
    (60, 30),   # 60 kWh, 30 kW (2.0h)
    (80, 40),   # 80 kWh, 40 kW (2.0h)
    (100, 50),  # 100 kWh, 50 kW (2.0h)
    (120, 40),  # 120 kWh, 40 kW (3.0h)
    (150, 50),  # 150 kWh, 50 kW (3.0h)
]

results = []
battery_cost_per_kwh = 3500  # NOK/kWh

print("\nBatteri  |  Invest.  |    NPV    |  IRR  | Payback | Verdi/år")
print("---------|-----------|-----------|-------|---------|----------")

for capacity_kwh, power_kw in battery_configs:
    # Create battery
    battery = Battery(
        capacity_kwh=capacity_kwh,
        power_kw=power_kw,
        efficiency=0.95
    )

    # Create DataFrame for value driver calculation
    data = pd.DataFrame({
        'production_kw': production,
        'consumption_kw': consumption,
        'spot_price_nok': prices
    })

    # Calculate value drivers
    value_drivers = calculate_all_value_drivers(
        data=data,
        battery_capacity_kwh=capacity_kwh,
        battery_power_kw=power_kw,
        grid_limit_kw=77
    )

    # Economic analysis
    investment = capacity_kwh * battery_cost_per_kwh
    annual_value = value_drivers['total_annual_value_nok']

    # Create analyzer
    analyzer = EconomicAnalyzer(
        discount_rate=0.05,
        project_years=15
    )

    # Simple economic calculation
    npv = 0
    for year in range(1, 16):
        discounted = annual_value / ((1 + 0.05) ** year)
        npv += discounted
    npv -= investment

    # IRR calculation (simplified)
    if npv > 0:
        irr = annual_value / investment - 0.02  # Degradation
    else:
        irr = -0.1

    # Payback period
    if annual_value > 0:
        payback = investment / annual_value
    else:
        payback = 999

    economics = {
        'npv': npv,
        'irr': irr,
        'payback_years': payback
    }

    # Store results
    result = {
        'capacity_kwh': capacity_kwh,
        'power_kw': power_kw,
        'c_rate': power_kw / capacity_kwh,
        'investment': investment,
        'annual_value': annual_value,
        'npv': economics['npv'],
        'irr': economics['irr'],
        'payback_years': economics['payback_years']
    }
    results.append(result)

    # Print row
    print(f"{capacity_kwh:3.0f}/{power_kw:2.0f}  | {investment/1000:6.0f}k | {economics['npv']/1000:+8.0f}k | {economics['irr']*100:4.1f}% | {economics['payback_years']:4.1f} år | {annual_value/1000:5.1f}k")

# Find optimal
df_results = pd.DataFrame(results)
optimal = df_results.loc[df_results['npv'].idxmax()]

print("\n" + "="*60)
print("🏆 OPTIMAL BATTERIKONFIGURASJON:")
print(f"   • Størrelse: {optimal['capacity_kwh']:.0f} kWh / {optimal['power_kw']:.0f} kW")
print(f"   • C-rate: {optimal['c_rate']:.2f} (timer: {1/optimal['c_rate']:.1f}h)")
print(f"   • Investering: {optimal['investment']/1000:.0f}k NOK")
print(f"   • NPV: {optimal['npv']/1000:+.0f}k NOK")
print(f"   • IRR: {optimal['irr']*100:.1f}%")
print(f"   • Tilbakebetaling: {optimal['payback_years']:.1f} år")
print(f"   • Årlig verdi: {optimal['annual_value']/1000:.1f}k NOK/år")

# Show value distribution for optimal
print("\n📊 VERDIDRIVERE FOR OPTIMAL KONFIGURASJON:")
battery_opt = Battery(
    capacity_kwh=optimal['capacity_kwh'],
    power_kw=optimal['power_kw'],
    efficiency=0.95
)

# Create DataFrame for optimal config
data_opt = pd.DataFrame({
    'production_kw': production,
    'consumption_kw': consumption,
    'spot_price_nok': prices
})

value_drivers_opt = calculate_all_value_drivers(
    data=data_opt,
    battery_capacity_kwh=optimal['capacity_kwh'],
    battery_power_kw=optimal['power_kw'],
    grid_limit_kw=77
)

print(f"   • Avkortning:      {value_drivers_opt['curtailment']['annual_value_nok']/1000:6.1f}k NOK/år ({value_drivers_opt['curtailment']['percentage_of_total']:3.0f}%)")
print(f"   • Arbitrasje:      {value_drivers_opt['arbitrage']['annual_value_nok']/1000:6.1f}k NOK/år ({value_drivers_opt['arbitrage']['percentage_of_total']:3.0f}%)")
print(f"   • Effekttariff:    {value_drivers_opt['demand_charge']['annual_value_nok']/1000:6.1f}k NOK/år ({value_drivers_opt['demand_charge']['percentage_of_total']:3.0f}%)")
print(f"   • Selvforsyning:   {value_drivers_opt['self_consumption']['annual_value_nok']/1000:6.1f}k NOK/år ({value_drivers_opt['self_consumption']['percentage_of_total']:3.0f}%)")
print(f"   ─────────────────────────────────────────────")
print(f"   TOTAL:            {value_drivers_opt['total_annual_value_nok']/1000:6.1f}k NOK/år")

print("\n💰 LØNNSOMHETSVURDERING:")
if optimal['npv'] > 0:
    print(f"   ✅ LØNNSOM INVESTERING!")
    print(f"   → NPV er positiv: +{optimal['npv']/1000:.0f}k NOK")
    print(f"   → Årlig avkastning: {optimal['irr']*100:.1f}%")
    print(f"   → Break-even på {optimal['payback_years']:.1f} år")
else:
    print(f"   ❌ IKKE LØNNSOM med {battery_cost_per_kwh} NOK/kWh")
    print(f"   → NPV er negativ: {optimal['npv']/1000:.0f}k NOK")

print("="*60)