#!/usr/bin/env python3
"""
Analyze achieved price for solar power (oppnådd pris for solkraft)
"""

import pandas as pd
import numpy as np
from run_simulation import (
    load_real_solar_production,
    generate_realistic_consumption_profile,
    get_electricity_prices,
    simulate_battery_operation,
    SYSTEM_CONFIG,
    ECONOMIC_PARAMS
)

# Battery configuration
BATTERY_KWH = 30
BATTERY_KW = 15

print("="*70)
print("SOLKRAFT INNTEKTSANALYSE - OPPNÅDD PRIS")
print("="*70)

# Load data
production_dc, production_ac, inverter_clipping = load_real_solar_production()
consumption = generate_realistic_consumption_profile(production_dc.index)
prices = get_electricity_prices(production_dc.index)

# Simulate with battery
results = simulate_battery_operation(
    production_dc, production_ac, consumption, prices,
    BATTERY_KWH, BATTERY_KW
)

# Calculate self-consumption and export
# Self-consumption = production used directly (not exported or curtailed)
total_production_ac = production_ac.sum()
total_consumption = consumption.sum()
total_grid_export = results['grid_export'].sum()
total_grid_curtailment = results['grid_curtailment'].sum()
total_battery_charge = results['battery_charge'].sum()

# Self-consumption = consumption covered by solar (not grid import)
self_consumption = total_consumption - results['grid_import'].sum()

print(f"\n=== SOLKRAFT FORDELING ===")
print(f"Total AC produksjon: {total_production_ac:,.0f} kWh/år")
print(f"  - Egenforbruk: {self_consumption:,.0f} kWh ({self_consumption/total_production_ac*100:.1f}%)")
print(f"  - Eksport til nett: {total_grid_export:,.0f} kWh ({total_grid_export/total_production_ac*100:.1f}%)")
print(f"  - Curtailment (tapt): {total_grid_curtailment:,.0f} kWh ({total_grid_curtailment/total_production_ac*100:.1f}%)")
print(f"  - Batterilading: {total_battery_charge:,.0f} kWh ({total_battery_charge/total_production_ac*100:.1f}%)")

# Calculate value of solar power
# Self-consumption value = avoided cost (full retail price)
avg_consumption_price = prices.mean()
self_consumption_value = self_consumption * avg_consumption_price

# Export value = spot price only (no grid tariff when exporting)
# Export price is typically spot price minus grid tariff
export_price_avg = ECONOMIC_PARAMS['spot_price_avg_2024']
export_value = total_grid_export * export_price_avg

# Battery discharge value (energy that was stored and later used)
total_battery_discharge = results['battery_discharge'].sum()
battery_discharge_value = total_battery_discharge * avg_consumption_price

# Total solar value
total_solar_value = self_consumption_value + export_value + battery_discharge_value

print(f"\n=== SOLKRAFT VERDI ===")
print(f"Egenforbruk verdi (unngått kostnad): {self_consumption_value:,.0f} NOK/år")
print(f"  @ gjennomsnittspris: {avg_consumption_price:.2f} NOK/kWh")
print(f"")
print(f"Eksport verdi (spotpris): {export_value:,.0f} NOK/år")
print(f"  @ spotpris: {export_price_avg:.2f} NOK/kWh")
print(f"")
print(f"Batteri utlading verdi: {battery_discharge_value:,.0f} NOK/år")
print(f"  @ gjennomsnittspris: {avg_consumption_price:.2f} NOK/kWh")
print(f"")
print(f"TOTAL SOLKRAFT VERDI: {total_solar_value:,.0f} NOK/år")

# Calculate achieved price per kWh
achieved_price = total_solar_value / total_production_ac

print(f"\n=== OPPNÅDD PRIS FOR SOLKRAFT ===")
print(f"Total verdi: {total_solar_value:,.0f} NOK/år")
print(f"Total produksjon: {total_production_ac:,.0f} kWh/år")
print(f"")
print(f"OPPNÅDD PRIS: {achieved_price:.3f} NOK/kWh")
print(f"")
print(f"Sammenlignet med:")
print(f"  Gjennomsnittlig strømpris (inkl. tariffer): {avg_consumption_price:.3f} NOK/kWh")
print(f"  Spotpris (kun eksport): {export_price_avg:.3f} NOK/kWh")
print(f"  Peak tariff: {ECONOMIC_PARAMS['grid_tariff_peak']:.3f} NOK/kWh")
print(f"  Off-peak tariff: {ECONOMIC_PARAMS['grid_tariff_offpeak']:.3f} NOK/kWh")

# Calculate monthly breakdown
print(f"\n=== MÅNEDLIG OVERSIKT ===")
monthly_production = production_ac.groupby(pd.Grouper(freq='ME')).sum()
monthly_export = results['grid_export'].groupby(pd.Grouper(freq='ME')).sum()
monthly_curtailment = results['grid_curtailment'].groupby(pd.Grouper(freq='ME')).sum()

for month in monthly_production.index:
    prod = monthly_production.loc[month]
    exp = monthly_export.loc[month]
    curt = monthly_curtailment.loc[month]
    self_cons = prod - exp - curt

    print(f"{month.strftime('%B %Y'):15s}: "
          f"Prod: {prod:6,.0f} kWh | "
          f"Egen: {self_cons:6,.0f} ({self_cons/prod*100:4.1f}%) | "
          f"Eksport: {exp:6,.0f} ({exp/prod*100:4.1f}%) | "
          f"Curtail: {curt:5,.0f} ({curt/prod*100:4.1f}%)")

print(f"\n" + "="*70)
