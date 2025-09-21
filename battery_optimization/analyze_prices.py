#!/usr/bin/env python
"""
Analyser realisert pris for solkraft
"""
import pandas as pd
import numpy as np
from core.pvgis_solar import PVGISProduction
from core.entso_e_prices import ENTSOEPrices
from core.optimizer import BatteryOptimizer

# Load data
pvgis = PVGISProduction(lat=58.97, lon=5.73, pv_capacity_kwp=138.55)
production = pvgis.fetch_hourly_production(year=2020)

# Consumption
n_hours = len(production)
hourly_pattern = np.array([
    0.3, 0.3, 0.3, 0.3, 0.3, 0.4,
    0.6, 0.8, 1.0, 1.0, 1.0, 0.9,
    0.7, 0.8, 0.9, 1.0, 0.9, 0.7,
    0.5, 0.4, 0.3, 0.3, 0.3, 0.3
])
base_load = 90000 / 8760 / 0.6
consumption = pd.Series([base_load * hourly_pattern[i % 24] for i in range(n_hours)],
                       index=production.index)

# Prices
entsoe = ENTSOEPrices()
prices = entsoe.fetch_prices(year=2023)
# Align lengths
if len(prices) != len(production):
    if len(prices) > len(production):
        prices = prices[:len(production)]
    else:
        extra = pd.Series([prices.iloc[-1]] * (len(production) - len(prices)))
        prices = pd.concat([prices, extra])
prices.index = production.index

print("📊 ANALYSE AV SOLKRAFTVERDI\n" + "="*50)

# Calculate value components
total_production = production.sum()
print(f"\nTotal produksjon: {total_production/1000:.1f} MWh")

# Self-consumed vs exported
self_consumed = np.minimum(production, consumption)
exported = np.maximum(0, production - consumption)

total_self_consumed = self_consumed.sum()
total_exported = exported.sum()

print(f"Selvforbruk: {total_self_consumed/1000:.1f} MWh ({total_self_consumed/total_production*100:.1f}%)")
print(f"Eksport: {total_exported/1000:.1f} MWh ({total_exported/total_production*100:.1f}%)")

# Calculate values
avg_spot = prices.mean()
print(f"\nGjennomsnittlig spotpris: {avg_spot:.3f} NOK/kWh")

# Export value (spot price minus export fee)
export_fee = 0.02  # 2 øre/kWh
export_value = exported * (prices - export_fee)
total_export_value = export_value.sum()
avg_export_price = total_export_value / total_exported if total_exported > 0 else 0

print(f"\nEksportverdi:")
print(f"  Total: {total_export_value:.0f} NOK")
print(f"  Gjennomsnittspris: {avg_export_price:.3f} NOK/kWh")

# Self-consumption value (spot price + avoided grid tariff)
# Lnett tariff for < 100 MWh/år is approximately:
# Energy: 0.176 NOK/kWh (peak) / 0.126 NOK/kWh (off-peak)
# Plus elavgift: 0.1641 NOK/kWh
# Total avoided: ~0.30-0.34 NOK/kWh
avoided_grid_cost = 0.32  # Realistic for Lnett commercial

self_cons_value = self_consumed * (prices + avoided_grid_cost)
total_self_cons_value = self_cons_value.sum()
avg_self_cons_price = total_self_cons_value / total_self_consumed if total_self_consumed > 0 else 0

print(f"\nSelvforbruksverdi:")
print(f"  Total: {total_self_cons_value:.0f} NOK")
print(f"  Gjennomsnittspris: {avg_self_cons_price:.3f} NOK/kWh")

# Total value
total_value = total_export_value + total_self_cons_value
avg_realized_price = total_value / total_production

print(f"\n" + "="*50)
print(f"TOTAL VERDI: {total_value:.0f} NOK")
print(f"REALISERT PRIS: {avg_realized_price:.3f} NOK/kWh")
print(f"Premium over spot: {(avg_realized_price - avg_spot)*100/avg_spot:.1f}%")

# Time-of-day analysis
print(f"\n" + "="*50)
print("VERDI PER TIME PÅ DØGNET:")
hourly_values = []
for hour in range(24):
    mask = production.index.hour == hour
    hour_prod = production[mask].sum()
    hour_self_cons = self_consumed[mask].sum()
    hour_export = exported[mask].sum()

    if hour_prod > 0:
        hour_export_value = (exported[mask] * (prices[mask] - export_fee)).sum()
        hour_self_value = (self_consumed[mask] * (prices[mask] + avoided_grid_cost)).sum()
        hour_total_value = hour_export_value + hour_self_value
        hour_avg_price = hour_total_value / hour_prod

        print(f"  Time {hour:02d}: {hour_avg_price:.3f} NOK/kWh "
              f"(Prod: {hour_prod/1000:.1f} MWh, "
              f"Selv: {hour_self_cons/hour_prod*100:.0f}%)")
    else:
        print(f"  Time {hour:02d}: Ingen produksjon")