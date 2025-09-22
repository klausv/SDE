#!/usr/bin/env python
"""
Sjekk effektledd-tariffer og beregning
"""

print("📊 LNETT EFFEKTLEDD-TARIFFER (2024)")
print("="*60)

print("\n🏢 NÆRINGSKUNDER (ekskl. mva):")
print("Intervall         | Tariff")
print("-----------------|----------")
print("0-50 kW          | 72 kr/kW/mnd")
print("50-200 kW        | 68 kr/kW/mnd")
print("200-500 kW       | 64 kr/kW/mnd")
print("Over 500 kW      | 60 kr/kW/mnd")

print("\n💰 MED MVA (25%):")
print("Intervall         | Tariff inkl. mva")
print("-----------------|----------")
print("0-50 kW          | 90 kr/kW/mnd")
print("50-200 kW        | 85 kr/kW/mnd")
print("200-500 kW       | 80 kr/kW/mnd")
print("Over 500 kW      | 75 kr/kW/mnd")

print("\n📈 BEREGNINGSEKSEMPEL:")
print("-"*40)

# Anta 90 MWh årlig forbruk for kontor
annual_kwh = 90000
avg_monthly_kwh = annual_kwh / 12  # 7500 kWh/mnd

# Typisk lastfaktor for kontor: 30-40%
load_factor = 0.35
avg_power_kw = avg_monthly_kwh / (730 * load_factor)  # ~30 kW gjennomsnitt

# Men peak er høyere - typisk 2-3x gjennomsnitt
peak_kw = avg_power_kw * 2.5  # ~75 kW peak

print(f"Årlig forbruk:       {annual_kwh:,} kWh")
print(f"Månedlig forbruk:    {avg_monthly_kwh:,.0f} kWh")
print(f"Gjennomsnitt effekt: {avg_power_kw:.0f} kW")
print(f"Typisk peak effekt:  {peak_kw:.0f} kW")

# Beregn effekttariff
if peak_kw <= 50:
    tariff = 90
elif peak_kw <= 200:
    tariff = 85
else:
    tariff = 80

monthly_cost = peak_kw * tariff
print(f"\nEffekttariff:        {tariff} kr/kW/mnd")
print(f"Månedlig kostnad:    {monthly_cost:,.0f} kr")
print(f"Årlig kostnad:       {monthly_cost*12:,.0f} kr")

# Konverter til kr/kWh
cost_per_kwh = monthly_cost / avg_monthly_kwh
print(f"Kostnad per kWh:     {cost_per_kwh:.3f} kr/kWh")

print("\n📊 EFFEKTLEDD SOM ANDEL AV TOTAL NETTLEIE:")
print("-"*40)

# Total nettleie komponenter (gjennomsnittsverdier)
energiledd = 0.268  # kr/kWh (gjennomsnitt peak/off-peak)
forbruksavgift = 0.159  # kr/kWh
effektledd = cost_per_kwh  # Beregnet over

total_nettleie = energiledd + forbruksavgift + effektledd

print(f"Energiledd:          {energiledd:.3f} kr/kWh ({energiledd/total_nettleie*100:.1f}%)")
print(f"Forbruksavgift:      {forbruksavgift:.3f} kr/kWh ({forbruksavgift/total_nettleie*100:.1f}%)")
print(f"Effektledd:          {effektledd:.3f} kr/kWh ({effektledd/total_nettleie*100:.1f}%)")
print(f"TOTAL NETTLEIE:      {total_nettleie:.3f} kr/kWh (100%)")

print("\n💡 BATTERIPOTENSIALE:")
print("-"*40)

# Hvis batteri kan redusere peak med 30%
reduction = 0.3
new_peak = peak_kw * (1 - reduction)
new_monthly_cost = new_peak * tariff
savings_monthly = monthly_cost - new_monthly_cost

print(f"Peak uten batteri:   {peak_kw:.0f} kW")
print(f"Peak med batteri:    {new_peak:.0f} kW (-{reduction*100:.0f}%)")
print(f"Månedlig besparelse: {savings_monthly:,.0f} kr")
print(f"Årlig besparelse:    {savings_monthly*12:,.0f} kr")

print("\n📝 KONKLUSJON:")
print("-"*40)
print(f"• Effektledd utgjør ca {effektledd:.2f} kr/kWh")
print(f"• Dette er {effektledd/total_nettleie*100:.0f}% av total nettleie")
print(f"• Med 30% peak-reduksjon spares {savings_monthly*12/1000:.1f}k NOK/år")
print(f"• Dette tilsvarer {savings_monthly*12/annual_kwh:.3f} kr/kWh besparelse")
print("="*60)