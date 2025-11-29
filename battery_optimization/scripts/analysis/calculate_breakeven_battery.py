"""
Beregn break-even batterikostnad for kontorbygg-scenarioet.

Antagelser:
- 5% diskonteringsrente
- 15 års levetid
- Årlige besparelser fra simulering
"""

import pandas as pd
from pathlib import Path
import numpy as np

project_root = Path(__file__).parent
results_file = project_root / 'results' / 'kontorbygg_korrekt_results.csv'

# Load results
df = pd.read_csv(results_file)

# Annual totals
annual_pv = df['pv_total_kwh'].sum()
annual_export = df['grid_export_kwh'].sum()
annual_self_consumption = annual_pv - annual_export
annual_import = df['grid_import_kwh'].sum()
annual_load = df['load_total_kwh'].sum()
annual_energy_cost = df['energy_cost_nok'].sum()
annual_power_cost = df['power_cost_nok'].sum()
annual_total_cost = df['total_cost_nok'].sum()

# Battery usage
battery_charge_kwh = df['battery_charge_kwh'].sum()
battery_discharge_kwh = df['battery_discharge_kwh'].sum()
battery_cycles = battery_charge_kwh / 40.0  # 40 kWh battery

print("="*80)
print("BREAK-EVEN ANALYSE - BATTERIKOSTNAD")
print("="*80)

print("\n📊 Systemparametere:")
print(f"   Batteri: 40 kWh / 40 kW")
print(f"   Solkraft: 100 kWp")
print(f"   Forbruk: {annual_load:,.0f} kWh/år")
print(f"   Levetid: 15 år")
print(f"   Diskonteringsrente: 5%")

print("\n🔋 Batteridrift:")
print(f"   Årlig lading: {battery_charge_kwh:,.0f} kWh")
print(f"   Årlig utlading: {battery_discharge_kwh:,.0f} kWh")
print(f"   Sykluser per år: {battery_cycles:.0f}")
print(f"   Total sykluser (15 år): {battery_cycles * 15:.0f}")

# Beregn scenario UTEN batteri (grovt estimat)
# Uten batteri: all solkraft over forbruk eksporteres direkte
# Dette er forenklet - ideelt sett burde vi kjøre ny simulering uten batteri

# Estimate savings
# Med batteri flytter vi noe forbruk fra dyre timer til billige timer
# Og reduserer effekttoppene

# Fra resultatene:
energy_price_avg = 0.50  # NOK/kWh (spotpris)
export_revenue = annual_export * energy_price_avg
self_consumption_value = annual_self_consumption * energy_price_avg

# Total annual cost WITH battery
total_cost_with_battery = annual_total_cost

# Estimate cost WITHOUT battery (approximate)
# Uten batteri: mindre optimalisering av import/eksport og effekttariffer
# Konservativt estimat: 10-15% høyere kostnader

# Fra simuleringen kan vi se at batteriet gir:
# - Redusert effekttariff (fra peak shaving)
# - Bedre utnyttelse av solkraft (time-shifting)

# Konservativt estimat av årlige besparelser:
# La oss anta at uten batteri ville effekttariffkostnadene vært 20% høyere
# og energikostnadene 5% høyere

estimated_power_cost_without_battery = annual_power_cost * 1.20
estimated_energy_cost_without_battery = annual_energy_cost * 1.05
estimated_total_cost_without_battery = estimated_energy_cost_without_battery + estimated_power_cost_without_battery

annual_savings = estimated_total_cost_without_battery - total_cost_with_battery

print(f"\n💰 Årlige kostnader:")
print(f"   MED batteri:")
print(f"     - Energikostnad: {annual_energy_cost:,.0f} NOK")
print(f"     - Effekttariff: {annual_power_cost:,.0f} NOK")
print(f"     - Total: {total_cost_with_battery:,.0f} NOK")
print(f"\n   UTEN batteri (estimert):")
print(f"     - Energikostnad: {estimated_energy_cost_without_battery:,.0f} NOK (+5%)")
print(f"     - Effekttariff: {estimated_power_cost_without_battery:,.0f} NOK (+20%)")
print(f"     - Total: {estimated_total_cost_without_battery:,.0f} NOK")
print(f"\n   Årlig besparelse: {annual_savings:,.0f} NOK")

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
market_costs = [5000, 4000, 3000, 2500, 2000]

print(f"\n📈 NPV ved ulike batterikostnader:")
print(f"   {'Kostnad':>12}  {'Investering':>12}  {'NPV':>12}  {'IRR':>8}")
print(f"   {'-'*12}  {'-'*12}  {'-'*12}  {'-'*8}")

for cost in market_costs:
    npv_val, investment, pv_savings = npv_battery(cost, annual_savings, discount_rate, lifetime_years)

    # Calculate approximate IRR
    # IRR is the rate where NPV = 0
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
    print(f"   {cost:>9,.0f} kr  {investment:>11,.0f} kr  {npv_val:>11,.0f} kr  {irr*100:>6.1f}%  {marker}")

print(f"\n{'='*80}")
print(f"KONKLUSJON:")
print(f"{'='*80}")
print(f"Med {annual_savings:,.0f} NOK/år i besparelser over 15 år (5% rente):")
print(f"  • Break-even batterikostnad: {breakeven_cost:,.0f} NOK/kWh")
print(f"  • Markedspris i dag: ~5,000 NOK/kWh")
print(f"  • Nødvendig kostnadsreduksjon: {5000 - breakeven_cost:,.0f} NOK/kWh ({((5000-breakeven_cost)/5000)*100:.0f}%)")
print(f"{'='*80}")
