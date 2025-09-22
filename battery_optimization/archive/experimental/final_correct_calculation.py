#!/usr/bin/env python
"""
ENDELIG KORREKT beregning av effekttariff-besparelse
"""

print("✅ ENDELIG KORREKT FORSTÅELSE AV EFFEKTTARIFF")
print("="*60)

print("\n📊 HVORDAN EFFEKTTARIFF FUNGERER:")
print("1. Hver måned måles MAKS effekt fra nettet (kW)")
print("2. Man betaler for det intervallet denne peak ligger i")
print("3. Batteri kan redusere peak med maks batteristørrelse (f.eks 20 kW)")

print("\n💡 EKSEMPEL:")
print("-"*40)
print("Måned: Januar")
print("Max effekt uten batteri: 45 kW → Intervall 25-50 kW = 1,772 kr/mnd")
print("Max effekt med 20 kW batteri: 25 kW → Intervall 20-25 kW = 972 kr/mnd")
print("Besparelse denne måneden: 1,772 - 972 = 800 kr")

print("\n📈 LNETT TARIFFER (for referanse):")
print("Intervall      | Månedlig kostnad")
print("---------------|------------------")
brackets = [
    (0, 2, 136),
    (2, 5, 232),
    (5, 10, 372),
    (10, 15, 572),
    (15, 20, 772),
    (20, 25, 972),
    (25, 50, 1772),
    (50, 75, 2572),
    (75, 100, 3372),
    (100, float('inf'), 5600)
]

for from_kw, to_kw, cost in brackets:
    if to_kw == float('inf'):
        print(f"{from_kw:3.0f}+ kW        | {cost:,} kr/mnd")
    else:
        print(f"{from_kw:3.0f}-{to_kw:3.0f} kW      | {cost:,} kr/mnd")

def get_tariff(peak_kw):
    """Finn tariffen for en gitt peak"""
    if peak_kw <= 0:
        return 0
    for from_kw, to_kw, cost in brackets:
        if from_kw < peak_kw <= to_kw:
            return cost
        elif peak_kw > 100:
            return 5600
    return 0

print("\n🔋 TEORETISK MAKSIMUM MED 20 kW BATTERI:")
print("-"*60)
print("Hvis peak hver måned går fra høyt til lavt intervall:")
print()

# Best case scenarios
best_cases = [
    ("45→25", 45, 25, "Fra 25-50 kW til 20-25 kW"),
    ("30→10", 30, 10, "Fra 25-50 kW til 5-10 kW"),
    ("25→5", 25, 5, "Fra 20-25 kW til 2-5 kW"),
    ("70→50", 70, 50, "Fra 50-75 kW til 25-50 kW"),
]

print("Scenario    | Før    | Etter  | Besparelse | Kommentar")
print("------------|--------|--------|------------|----------")
for name, before, after, comment in best_cases:
    cost_before = get_tariff(before)
    cost_after = get_tariff(after)
    saving = cost_before - cost_after
    print(f"{name:11s} | {cost_before:,} | {cost_after:,} | {saving:,} kr  | {comment}")

print("\n📊 REALISTISK SCENARIO - KONTORBYGG:")
print("-"*60)

# Månedlige peaks for typisk kontorbygg
months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']
peaks_without = [45, 45, 40, 35, 30, 25, 22, 25, 30, 35, 40, 45]
battery_kw = 20

print("Måned | Peak uten | Peak med | Tariff uten | Tariff med | Besparelse")
print("------|-----------|----------|-------------|------------|------------")

total_saving = 0
for month, peak_without in zip(months, peaks_without):
    peak_with = max(0, peak_without - battery_kw)
    tariff_without = get_tariff(peak_without)
    tariff_with = get_tariff(peak_with)
    saving = tariff_without - tariff_with
    total_saving += saving

    print(f"{month:5s} | {peak_without:9.0f} | {peak_with:8.0f} | {tariff_without:11,} | {tariff_with:10,} | {saving:10,}")

print(f"\nTOTAL ÅRLIG BESPARELSE: {total_saving:,} kr/år")

print("\n🎯 KONKLUSJON:")
print("-"*60)
print(f"Med 20 kW batteri og realistiske månedlige peaks:")
print(f"• Årlig besparelse: {total_saving:,} kr")
print(f"• Per måned gjennomsnitt: {total_saving/12:,.0f} kr")
print(f"• Dette forutsetter at batteriet ALLTID kan levere når peak inntreffer")

# NPV beregning
discount_rate = 0.05
years = 15
npv_factor = sum(1/(1+discount_rate)**y for y in range(1, years+1))
npv = total_saving * npv_factor

print(f"\n💰 ØKONOMI:")
print(f"• NPV over {years} år (5%): {npv:,.0f} kr")
print(f"• Break-even batterikostnad: {npv/battery_kw:,.0f} kr/kWh")

if npv/battery_kw > 3500:
    print(f"• ✅ Lønnsomt ved 3,500 kr/kWh")
else:
    print(f"• ❌ IKKE lønnsomt ved 3,500 kr/kWh")

print("\n⚠️ VIKTIGE FORBEHOLD:")
print("1. Batteriet må ha nok SOC når peak inntreffer")
print("2. Batteriet må kunne levere full effekt (20 kW)")
print("3. Peak-tidspunkt må være forutsigbart")
print("4. Realistisk er kanskje 70-80% av teoretisk besparelse")

realistic = total_saving * 0.75
print(f"\nRealistisk besparelse (75%): {realistic:,.0f} kr/år")
print(f"Realistisk NPV: {realistic * npv_factor:,.0f} kr")
print(f"Realistisk break-even: {realistic * npv_factor / battery_kw:,.0f} kr/kWh")

print("="*60)