"""
Beregn break-even batterikostnad for kontorbygg-scenarioet.

Bruker eksakte verdier fra begge simuleringer:
- MED batteri: run_kontorbygg_analyse_korrekt.py
- UTEN batteri: run_kontorbygg_uten_batteri.py

Antagelser:
- 5% diskonteringsrente
- 15 års levetid
"""

import pandas as pd
from pathlib import Path
import numpy as np

project_root = Path(__file__).parent

# Load results from BOTH simulations
results_with_battery = project_root / 'results' / 'kontorbygg_korrekt_results.csv'
results_without_battery = project_root / 'results' / 'kontorbygg_uten_batteri_results.csv'

df_with = pd.read_csv(results_with_battery)
df_without = pd.read_csv(results_without_battery)

# Annual totals WITH battery
annual_pv_with = df_with['pv_total_kwh'].sum()
annual_export_with = df_with['grid_export_kwh'].sum()
annual_import_with = df_with['grid_import_kwh'].sum()
annual_load_with = df_with['load_total_kwh'].sum()
annual_energy_cost_with = df_with['energy_cost_nok'].sum()
annual_power_cost_with = df_with['power_cost_nok'].sum()
annual_total_cost_with = df_with['total_cost_nok'].sum()

# Battery usage
battery_charge_kwh = df_with['battery_charge_kwh'].sum()
battery_discharge_kwh = df_with['battery_discharge_kwh'].sum()
battery_cycles = battery_charge_kwh / 40.0  # 40 kWh battery

# Annual totals WITHOUT battery
annual_pv_without = df_without['pv_total_kwh'].sum()
annual_export_without = df_without['grid_export_kwh'].sum()
annual_import_without = df_without['grid_import_kwh'].sum()
annual_load_without = df_without['load_total_kwh'].sum()
annual_energy_cost_without = df_without['energy_cost_nok'].sum()
annual_power_cost_without = df_without['power_cost_nok'].sum()
annual_total_cost_without = df_without['total_cost_nok'].sum()

# EXACT annual savings
annual_savings = annual_total_cost_without - annual_total_cost_with

print("="*80)
print("BREAK-EVEN ANALYSE - BATTERIKOSTNAD (EKSAKTE VERDIER)")
print("="*80)

print("\n📊 Systemparametere:")
print(f"   Batteri: 40 kWh / 40 kW")
print(f"   Solkraft: 100 kWp")
print(f"   Forbruk: {annual_load_with:,.0f} kWh/år")
print(f"   Levetid: 15 år")
print(f"   Diskonteringsrente: 5%")

print("\n🔋 Batteridrift:")
print(f"   Årlig lading: {battery_charge_kwh:,.0f} kWh")
print(f"   Årlig utlading: {battery_discharge_kwh:,.0f} kWh")
print(f"   Sykluser per år: {battery_cycles:.0f}")
print(f"   Total sykluser (15 år): {battery_cycles * 15:.0f}")

print(f"\n💰 Årlige kostnader (SIMULERT):")
print(f"\n   MED batteri (40 kWh, 40 kW):")
print(f"     - Energikostnad: {annual_energy_cost_with:,.0f} NOK")
print(f"     - Effekttariff: {annual_power_cost_with:,.0f} NOK")
print(f"     - Total: {annual_total_cost_with:,.0f} NOK")
print(f"     - Import: {annual_import_with:,.0f} kWh")
print(f"     - Eksport: {annual_export_with:,.0f} kWh ({annual_export_with/annual_pv_with*100:.1f}% av sol)")

print(f"\n   UTEN batteri:")
print(f"     - Energikostnad: {annual_energy_cost_without:,.0f} NOK")
print(f"     - Effekttariff: {annual_power_cost_without:,.0f} NOK")
print(f"     - Total: {annual_total_cost_without:,.0f} NOK")
print(f"     - Import: {annual_import_without:,.0f} kWh")
print(f"     - Eksport: {annual_export_without:,.0f} kWh ({annual_export_without/annual_pv_without*100:.1f}% av sol)")

print(f"\n   📈 ÅRLIG BESPARELSE: {annual_savings:,.0f} NOK/år")

# Breakdown of savings
energy_cost_savings = annual_energy_cost_without - annual_energy_cost_with
power_cost_savings = annual_power_cost_without - annual_power_cost_with
export_diff = (annual_export_without - annual_export_with) * 0.50  # Simplified

print(f"\n   Fordeling av besparelser:")
print(f"     - Energikostnad: {energy_cost_savings:,.0f} NOK/år ({energy_cost_savings/annual_savings*100:.1f}%)")
print(f"     - Effekttariff: {power_cost_savings:,.0f} NOK/år ({power_cost_savings/annual_savings*100:.1f}%)")

# NPV calculation
discount_rate = 0.05
lifetime_years = 15

def npv_battery(battery_cost_per_kwh, annual_savings, discount_rate, lifetime):
    """Calculate NPV of battery investment."""
    battery_capacity = 40.0  # kWh
    initial_investment = battery_capacity * battery_cost_per_kwh

    # NPV of annual savings
    pv_savings = 0
    for year in range(1, lifetime + 1):
        pv_savings += annual_savings / ((1 + discount_rate) ** year)

    npv = pv_savings - initial_investment
    return npv, initial_investment, pv_savings

# Find break-even battery cost
def find_breakeven():
    """Binary search for break-even battery cost."""
    low = 0
    high = 20000  # NOK/kWh (unrealistically high)
    tolerance = 10  # NOK

    while high - low > tolerance:
        mid = (low + high) / 2
        npv_val, _, _ = npv_battery(mid, annual_savings, discount_rate, lifetime_years)

        if npv_val > 0:
            low = mid
        else:
            high = mid

    return (low + high) / 2

breakeven_cost = find_breakeven()
npv_breakeven, investment_breakeven, pv_savings_breakeven = npv_battery(
    breakeven_cost, annual_savings, discount_rate, lifetime_years
)

print(f"\n🎯 BREAK-EVEN ANALYSE:")
print(f"   PV av besparelser (15 år, 5%): {pv_savings_breakeven:,.0f} NOK")
print(f"   Break-even batterikostnad: {breakeven_cost:,.0f} NOK/kWh")
print(f"   Break-even investering (40 kWh): {investment_breakeven:,.0f} NOK")
print(f"   NPV ved break-even: {npv_breakeven:.0f} NOK (≈0)")

# Test with current market prices
market_costs = [5000, 4000, 3000, 2500, 2000, 1500, 1000]

print(f"\n📈 NPV ved ulike batterikostnader:")
print(f"   {'Kostnad':>12}  {'Investering':>12}  {'NPV':>12}  {'IRR':>8}  {'Status':>6}")
print(f"   {'-'*12}  {'-'*12}  {'-'*12}  {'-'*8}  {'-'*6}")

for cost in market_costs:
    npv_val, investment, pv_savings = npv_battery(cost, annual_savings, discount_rate, lifetime_years)

    # Calculate approximate IRR
    def npv_for_irr(rate):
        pv = sum(annual_savings / ((1 + rate) ** year) for year in range(1, lifetime_years + 1))
        return pv - investment

    # Binary search for IRR
    low_rate, high_rate = -0.5, 1.0
    while high_rate - low_rate > 0.001:
        mid_rate = (low_rate + high_rate) / 2
        if npv_for_irr(mid_rate) > 0:
            low_rate = mid_rate
        else:
            high_rate = mid_rate
    irr = (low_rate + high_rate) / 2

    marker = "✓" if npv_val > 0 else "✗"
    print(f"   {cost:>9,.0f} kr  {investment:>11,.0f} kr  {npv_val:>11,.0f} kr  {irr*100:>6.1f}%  {marker:>6}")

print(f"\n{'='*80}")
print(f"KONKLUSJON:")
print(f"{'='*80}")
print(f"Med {annual_savings:,.0f} NOK/år i besparelser over 15 år (5% rente):")
print(f"  • Break-even batterikostnad: {breakeven_cost:,.0f} NOK/kWh")
print(f"  • Markedspris i dag: ~5,000 NOK/kWh")
print(f"  • Nødvendig kostnadsreduksjon: {5000 - breakeven_cost:,.0f} NOK/kWh ({((5000-breakeven_cost)/5000)*100:.0f}%)")
print(f"\n  VURDERING:")
if annual_savings > 0:
    print(f"  ✓ Batteriet gir positive besparelser ({annual_savings:,.0f} NOK/år)")
    print(f"  ✗ Men markedspris ({5000:.0f} NOK/kWh) er {5000/breakeven_cost:.1f}x for høy")
    print(f"  → Batterikostnad må reduseres til {breakeven_cost:,.0f} NOK/kWh for lønnsomhet")
else:
    print(f"  ✗ Batteriet gir NEGATIVE besparelser (koster {abs(annual_savings):,.0f} NOK/år ekstra)")
    print(f"  → Ikke lønnsomt under nåværende forutsetninger")
print(f"{'='*80}")
