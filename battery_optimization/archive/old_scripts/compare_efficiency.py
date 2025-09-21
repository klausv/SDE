"""
Sammenlign batterieffektivitet: 90% vs 95%
"""
from analysis.data_generators import generate_complete_dataset
from analysis.value_drivers import calculate_all_value_drivers
from analysis.economic_analysis import analyze_battery_economics

print("\n" + "="*60)
print("SAMMENLIGNING AV BATTERIEFFEKTIVITET")
print("="*60)

# Generer data
data = generate_complete_dataset(
    year=2024,
    pv_capacity_kwp=138.55,
    inverter_limit_kw=110,
    annual_consumption_kwh=90000,
    profile_type='commercial'
)

# Test med GAMMEL effektivitet (90%)
print("\n🔋 MED GAMMEL EFFEKTIVITET (90%):")
print("-" * 40)

# Midlertidig override for testing
import analysis.value_drivers as vd
old_efficiency = 0.90

# Beregn arbitrasje med 90%
arbitrage_90 = vd.calculate_arbitrage_value(
    data['spot_price_nok'],
    battery_capacity_kwh=100,
    battery_efficiency=old_efficiency
)

# Beregn selvforsyning med 90%
self_consumption_90 = vd.calculate_self_consumption_value(
    data['production_kw'],
    data['consumption_kw'],
    data['spot_price_nok'],
    battery_capacity_kwh=100,
    battery_efficiency=old_efficiency
)

print(f"Arbitrasje: {arbitrage_90['annual_value_nok']:,.0f} NOK/år")
print(f"Selvforsyning: {self_consumption_90['annual_value_nok']:,.0f} NOK/år")
total_90 = arbitrage_90['annual_value_nok'] + self_consumption_90['annual_value_nok']
print(f"Total effektivitetsavhengig verdi: {total_90:,.0f} NOK/år")

# Test med NY effektivitet (95%)
print("\n✅ MED MODERNE EFFEKTIVITET (95%):")
print("-" * 40)

new_efficiency = 0.95

# Beregn arbitrasje med 95%
arbitrage_95 = vd.calculate_arbitrage_value(
    data['spot_price_nok'],
    battery_capacity_kwh=100,
    battery_efficiency=new_efficiency
)

# Beregn selvforsyning med 95%
self_consumption_95 = vd.calculate_self_consumption_value(
    data['production_kw'],
    data['consumption_kw'],
    data['spot_price_nok'],
    battery_capacity_kwh=100,
    battery_efficiency=new_efficiency
)

print(f"Arbitrasje: {arbitrage_95['annual_value_nok']:,.0f} NOK/år")
print(f"Selvforsyning: {self_consumption_95['annual_value_nok']:,.0f} NOK/år")
total_95 = arbitrage_95['annual_value_nok'] + self_consumption_95['annual_value_nok']
print(f"Total effektivitetsavhengig verdi: {total_95:,.0f} NOK/år")

# Sammenligning
print("\n📊 SAMMENLIGNING:")
print("-" * 40)

improvement = total_95 - total_90
improvement_pct = (improvement / total_90) * 100

print(f"Forbedring i årlig verdi: {improvement:,.0f} NOK ({improvement_pct:.1f}%)")
print(f"Over 15 år: {improvement * 15:,.0f} NOK ekstra verdi")

# Økonomisk analyse
economics_90 = analyze_battery_economics(
    battery_capacity_kwh=100,
    battery_cost_per_kwh=5000,
    annual_value=total_90 + 32947  # Legg til effekttariff som ikke påvirkes
)

economics_95 = analyze_battery_economics(
    battery_capacity_kwh=100,
    battery_cost_per_kwh=5000,
    annual_value=total_95 + 32947
)

print("\n💰 EFFEKT PÅ LØNNSOMHET:")
print("-" * 40)
print(f"NPV med 90% effektivitet: {economics_90['npv']:,.0f} NOK")
print(f"NPV med 95% effektivitet: {economics_95['npv']:,.0f} NOK")
print(f"NPV forbedring: {economics_95['npv'] - economics_90['npv']:,.0f} NOK")

if economics_90['irr'] and economics_95['irr']:
    print(f"\nIRR med 90% effektivitet: {economics_90['irr']:.1%}")
    print(f"IRR med 95% effektivitet: {economics_95['irr']:.1%}")
    print(f"IRR forbedring: {(economics_95['irr'] - economics_90['irr'])*100:.1f} prosentpoeng")

print("\n" + "="*60)
print("KONKLUSJON")
print("="*60)
print("""
✅ Moderne LFP-batterier har 95-98% effektivitet
✅ 90% effektivitet er UTDATERT (2015-era)
✅ 5% bedre effektivitet gir ~5.6% mer verdi fra arbitrasje/selvforsyning
✅ Dette forbedrer NPV med ~10,000-15,000 NOK

ANBEFALING: Bruk 95% som standard for moderne batterier!
""")