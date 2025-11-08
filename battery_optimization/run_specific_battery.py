#!/usr/bin/env python3
"""
Run battery simulation with specific battery configuration
30 kWh capacity, 15 kW power
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from run_simulation import (
    load_real_solar_production,
    generate_realistic_consumption_profile,
    get_electricity_prices,
    simulate_battery_operation,
    calculate_economics,
    SYSTEM_CONFIG,
    ECONOMIC_PARAMS
)

# Specific battery configuration
BATTERY_KWH = 30
BATTERY_KW = 15

print("="*70)
print(f"BATTERY SIMULATION: {BATTERY_KWH} kWh, {BATTERY_KW} kW")
print("="*70)

# Load real data
print("\nLoading PVGIS data...")
production_dc, production_ac, inverter_clipping = load_real_solar_production()
consumption = generate_realistic_consumption_profile(production_dc.index)
prices = get_electricity_prices(production_dc.index)

print(f"Data loaded: {len(production_dc)} hours")
print(f"Max DC production: {production_dc.max():.1f} kW")
print(f"Max AC production: {production_ac.max():.1f} kW")
print(f"Average consumption: {consumption.mean():.1f} kW")

# Run simulation
print(f"\nSimulating battery operation...")
results = simulate_battery_operation(
    production_dc,
    production_ac,
    consumption,
    prices,
    BATTERY_KWH,
    BATTERY_KW
)

# Calculate economics for both cost scenarios
print(f"\n=== ECONOMIC ANALYSIS ===")
for cost_name, cost_per_kwh in [
    ('market', ECONOMIC_PARAMS['battery_cost_market']),
    ('target', ECONOMIC_PARAMS['battery_cost_target'])
]:
    economics = calculate_economics(results, BATTERY_KWH, cost_per_kwh)

    print(f"\n{cost_name.upper()} COST ({cost_per_kwh} NOK/kWh):")
    print(f"  Investment: {economics['investment']:,.0f} NOK")
    print(f"  Annual savings: {economics['annual_savings']:,.0f} NOK")
    print(f"    - Curtailment value: {economics['curtailment_value']:,.0f} NOK")
    print(f"    - Arbitrage value: {economics['arbitrage_value']:,.0f} NOK")
    print(f"    - Power tariff savings: {economics['power_savings']:,.0f} NOK")
    print(f"  NPV: {economics['npv']:,.0f} NOK")
    print(f"  IRR: {economics['irr']*100:.1f}%")
    print(f"  Payback: {economics['payback']:.1f} years")

# Calculate production statistics
total_dc_production = production_dc.sum()
total_ac_production = production_ac.sum()
total_inverter_clipping = inverter_clipping.sum()
total_grid_curtailment = results['grid_curtailment'].sum()
total_consumption = consumption.sum()
total_battery_charge = results['battery_charge'].sum()
total_battery_discharge = results['battery_discharge'].sum()

print(f"\n=== PRODUCTION & CONSUMPTION ===")
print(f"Total DC production: {total_dc_production:,.0f} kWh/year")
print(f"Total AC production: {total_ac_production:,.0f} kWh/year")
print(f"Total consumption: {total_consumption:,.0f} kWh/year")
print(f"Inverter clipping: {total_inverter_clipping:,.0f} kWh ({total_inverter_clipping/total_dc_production*100:.1f}%)")
print(f"Grid curtailment: {total_grid_curtailment:,.0f} kWh ({total_grid_curtailment/total_ac_production*100:.1f}%)")

print(f"\n=== BATTERY UTILIZATION ===")
print(f"Total battery charge: {total_battery_charge:,.0f} kWh/year")
print(f"Total battery discharge: {total_battery_discharge:,.0f} kWh/year")
print(f"Battery cycles: {total_battery_charge/BATTERY_KWH:.1f} full cycles/year")
print(f"Max SOC reached: {results['soc'].max():.1f} kWh ({results['soc'].max()/BATTERY_KWH*100:.1f}%)")
print(f"Min SOC reached: {results['soc'].min():.1f} kWh ({results['soc'].min()/BATTERY_KWH*100:.1f}%)")
print(f"Average SOC: {results['soc'].mean():.1f} kWh ({results['soc'].mean()/BATTERY_KWH*100:.1f}%)")

# Save detailed results
output_file = f'results/battery_{BATTERY_KWH}kwh_{BATTERY_KW}kw_results.json'
summary = {
    'battery_configuration': {
        'capacity_kwh': BATTERY_KWH,
        'power_kw': BATTERY_KW,
        'c_rate': BATTERY_KW / BATTERY_KWH
    },
    'market_cost_scenario': {
        'cost_per_kwh': ECONOMIC_PARAMS['battery_cost_market'],
        **calculate_economics(results, BATTERY_KWH, ECONOMIC_PARAMS['battery_cost_market'])
    },
    'target_cost_scenario': {
        'cost_per_kwh': ECONOMIC_PARAMS['battery_cost_target'],
        **calculate_economics(results, BATTERY_KWH, ECONOMIC_PARAMS['battery_cost_target'])
    },
    'production_statistics': {
        'total_dc_production_kwh': float(total_dc_production),
        'total_ac_production_kwh': float(total_ac_production),
        'total_consumption_kwh': float(total_consumption),
        'inverter_clipping_kwh': float(total_inverter_clipping),
        'grid_curtailment_kwh': float(total_grid_curtailment)
    },
    'battery_utilization': {
        'total_charge_kwh': float(total_battery_charge),
        'total_discharge_kwh': float(total_battery_discharge),
        'full_cycles_per_year': float(total_battery_charge/BATTERY_KWH),
        'max_soc_kwh': float(results['soc'].max()),
        'min_soc_kwh': float(results['soc'].min()),
        'avg_soc_kwh': float(results['soc'].mean())
    },
    'timestamp': datetime.now().isoformat()
}

with open(output_file, 'w') as f:
    json.dump(summary, f, indent=2)

print(f"\n✅ Results saved to {output_file}")
