#!/usr/bin/env python
"""
KORREKT forståelse av Lnett kapasitetsledd
"""

print("🔍 KORREKT BEREGNING AV LNETT KAPASITETSLEDD")
print("="*60)

print("\n❌ FEIL FORSTÅELSE (det jeg gjorde):")
print("Jeg trodde man betalte for ALLE intervaller opp til peak")
print("Eksempel 30 kW: 136 + 232 + 372 + 572 + 772 + 972 + (5/25)*1772 = 3,410 kr/mnd")

print("\n✅ KORREKT FORSTÅELSE:")
print("Man betaler KUN for det intervallet peak ligger i!")
print("Eksempel 30 kW: Ligger i 25-50 kW bracket = 1,772 kr/mnd")

print("\n📊 LNETT TARIFFER:")
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

def calculate_lnett_correct(peak_kw):
    """KORREKT beregning - kun betale for intervallet peak ligger i"""
    for from_kw, to_kw, cost in brackets:
        if from_kw < peak_kw <= to_kw:
            return cost
        elif from_kw >= 100 and peak_kw > 100:
            return cost
    return 0

print("\n💡 EKSEMPLER PÅ KORREKT BEREGNING:")
print("Peak | Intervall    | Månedlig kost")
print("-----|--------------|---------------")
test_peaks = [8, 12, 18, 24, 30, 45, 60, 80]
for peak in test_peaks:
    cost = calculate_lnett_correct(peak)
    # Finn hvilket intervall
    interval = ""
    for from_kw, to_kw, c in brackets:
        if from_kw < peak <= to_kw:
            interval = f"{from_kw}-{to_kw} kW"
            break
    print(f"{peak:4.0f} | {interval:12s} | {cost:,} kr/mnd")

print("\n💰 EFFEKT AV 20 kW BATTERI:")
print("-"*60)

scenarios = [
    (25, 5),   # Fra 25 til 5 kW
    (30, 10),  # Fra 30 til 10 kW
    (45, 25),  # Fra 45 til 25 kW
    (50, 30),  # Fra 50 til 30 kW
    (75, 55),  # Fra 75 til 55 kW
]

print("Før → Etter | Kostnad før | Kostnad etter | Besparelse/mnd | År")
print("------------|-------------|---------------|----------------|--------")

for before, after in scenarios:
    cost_before = calculate_lnett_correct(before)
    cost_after = calculate_lnett_correct(after)
    saving_month = cost_before - cost_after
    saving_year = saving_month * 12

    print(f"{before:3.0f} → {after:3.0f} kW | {cost_before:11,} | {cost_after:13,} | {saving_month:14,} | {saving_year:,}")

print("\n🎯 REALISTISK EKSEMPEL:")
print("-"*60)
print("Kontorbygg med varierende månedlige peaks:")
print()

# Månedlige peaks
months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']
peaks_without = [35, 35, 30, 28, 26, 22, 20, 22, 26, 28, 32, 35]
battery_kw = 20

print("Måned | Uten batteri | Med batteri | Besparelse")
print("------|--------------|-------------|------------")

total_without = 0
total_with = 0

for month, peak in zip(months, peaks_without):
    peak_with = max(0, peak - battery_kw)
    cost_without = calculate_lnett_correct(peak)
    cost_with = calculate_lnett_correct(peak_with)
    saving = cost_without - cost_with

    total_without += cost_without
    total_with += cost_with

    print(f"{month:5s} | {peak:2.0f} kW ({cost_without:,}) | {peak_with:2.0f} kW ({cost_with:,}) | {saving:,} kr")

annual_saving = total_without - total_with

print(f"\nÅRSRESULTAT:")
print(f"  Uten batteri:  {total_without:,} kr/år")
print(f"  Med batteri:   {total_with:,} kr/år")
print(f"  BESPARELSE:    {annual_saving:,} kr/år")

print("\n📝 VIKTIG KONKLUSJON:")
print("-"*60)
print("Med KORREKT forståelse av Lnett-tariffen:")
print(f"• 20 kW batteri gir ca {annual_saving:,} kr/år besparelse")
print(f"• Dette er LAVERE enn modellens beregning")
print(f"• Men fortsatt betydelig besparelse")

# NPV
npv_factor = sum(1/(1.05)**y for y in range(1, 16))
npv = annual_saving * npv_factor
print(f"\nNPV over 15 år (5%): {npv:,.0f} kr")
print(f"Break-even batterikostnad: {npv/battery_kw:,.0f} kr/kWh")

if npv/battery_kw > 3500:
    print(f"✅ Lønnsomt ved 3,500 kr/kWh!")
else:
    print(f"❌ IKKE lønnsomt ved 3,500 kr/kWh")

print("="*60)