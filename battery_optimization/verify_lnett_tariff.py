#!/usr/bin/env python
"""
Verifiser Lnett kapasitetsledd-beregning
Korrekte satser fra Lnett 2024
"""

print("📊 LNETT KAPASITETSLEDD (EFFEKTTARIFF) 2024")
print("="*60)

print("\n✅ KORREKTE SATSER (inkl. mva):")
print("Intervall         | Kostnad for intervallet")
print("------------------|------------------------")
print("0-2 kW           | 136 kr/mnd")
print("2-5 kW           | 232 kr/mnd")
print("5-10 kW          | 372 kr/mnd")
print("10-15 kW         | 572 kr/mnd")
print("15-20 kW         | 772 kr/mnd")
print("20-25 kW         | 972 kr/mnd")
print("25-50 kW         | 1,772 kr/mnd")
print("50-75 kW         | 2,572 kr/mnd")
print("75-100 kW        | 3,372 kr/mnd")
print("100+ kW          | 5,600 kr/mnd")

def calculate_lnett_tariff(peak_kw):
    """
    Beregn månedlig kapasitetsledd etter Lnett tariffer
    Dette er PROGRESSIV - man betaler for alle intervaller opp til peak
    """
    brackets = [
        (0, 2, 136),      # 136 kr for intervallet 0-2 kW
        (2, 5, 232),      # 232 kr for intervallet 2-5 kW
        (5, 10, 372),     # 372 kr for intervallet 5-10 kW
        (10, 15, 572),    # 572 kr for intervallet 10-15 kW
        (15, 20, 772),    # 772 kr for intervallet 15-20 kW
        (20, 25, 972),    # 972 kr for intervallet 20-25 kW
        (25, 50, 1772),   # 1772 kr for intervallet 25-50 kW
        (50, 75, 2572),   # 2572 kr for intervallet 50-75 kW
        (75, 100, 3372),  # 3372 kr for intervallet 75-100 kW
        (100, float('inf'), 5600)  # 5600 kr for alt over 100 kW
    ]

    monthly_charge = 0
    remaining_kw = peak_kw

    for from_kw, to_kw, interval_cost in brackets:
        if peak_kw > from_kw:
            # Hvor mange kW i dette intervallet?
            interval_width = min(to_kw - from_kw, remaining_kw)
            if from_kw >= 100:  # Spesialtilfelle for 100+ kW
                monthly_charge += interval_cost
                break
            else:
                # Hele intervallkostnaden legges til hvis vi bruker hele intervallet
                if peak_kw >= to_kw:
                    monthly_charge += interval_cost
                else:
                    # Proporsjonal del av intervallet
                    fraction = (peak_kw - from_kw) / (to_kw - from_kw)
                    monthly_charge += interval_cost * fraction
                    break

    return monthly_charge

print("\n📈 EKSEMPLER PÅ MÅNEDLIGE KOSTNADER:")
print("Peak kW | Månedlig kostnad | Årlig kostnad | Kr per kW/mnd")
print("--------|------------------|---------------|---------------")

test_peaks = [5, 10, 15, 20, 25, 30, 50, 75, 100]
for peak in test_peaks:
    monthly = calculate_lnett_tariff(peak)
    yearly = monthly * 12
    per_kw = monthly / peak if peak > 0 else 0
    print(f"{peak:7.0f} | {monthly:16,.0f} | {yearly:13,.0f} | {per_kw:14.0f}")

print("\n💰 EFFEKT AV BATTERI - EKSEMPLER:")
print("-"*60)

scenarios = [
    (30, 20, 10),  # 30 kW peak, 20 kW batteri, redusert til 10 kW
    (50, 20, 30),  # 50 kW peak, 20 kW batteri, redusert til 30 kW
    (75, 30, 45),  # 75 kW peak, 30 kW batteri, redusert til 45 kW
]

for original, battery, reduced in scenarios:
    cost_before = calculate_lnett_tariff(original)
    cost_after = calculate_lnett_tariff(reduced)
    monthly_saving = cost_before - cost_after
    yearly_saving = monthly_saving * 12

    print(f"\nPeak {original} kW → {reduced} kW (batteri {battery} kW):")
    print(f"  Før:       {cost_before:8,.0f} kr/mnd")
    print(f"  Etter:     {cost_after:8,.0f} kr/mnd")
    print(f"  Besparelse:{monthly_saving:8,.0f} kr/mnd = {yearly_saving:,.0f} kr/år")

print("\n🎯 REALISTISK SCENARIO FOR KONTORBYGG:")
print("-"*60)

# Typiske månedlige peaks for kontorbygg (90 MWh/år)
monthly_peaks = [35, 35, 30, 28, 25, 22, 20, 22, 25, 28, 32, 35]
battery_kw = 20

print(f"Månedlige peaks UTEN batteri (kW):")
print("Jan  Feb  Mar  Apr  Mai  Jun  Jul  Aug  Sep  Okt  Nov  Des")
print(" ".join(f"{p:3.0f}" for p in monthly_peaks))

# Beregn kostnader uten batteri
yearly_cost_without = sum(calculate_lnett_tariff(p) for p in monthly_peaks)

# Beregn kostnader med batteri
monthly_peaks_reduced = [max(0, p - battery_kw) for p in monthly_peaks]
yearly_cost_with = sum(calculate_lnett_tariff(p) for p in monthly_peaks_reduced)

print(f"\nMånedlige peaks MED {battery_kw} kW batteri:")
print(" ".join(f"{p:3.0f}" for p in monthly_peaks_reduced))

yearly_saving = yearly_cost_without - yearly_cost_with

print(f"\nÅRLIG ØKONOMI:")
print(f"  Kostnad uten batteri: {yearly_cost_without:,.0f} kr/år")
print(f"  Kostnad med batteri:  {yearly_cost_with:,.0f} kr/år")
print(f"  BESPARELSE:           {yearly_saving:,.0f} kr/år")

# NPV-beregning
discount_rate = 0.05
years = 15
npv_factor = sum(1/(1+discount_rate)**y for y in range(1, years+1))
npv_savings = yearly_saving * npv_factor

print(f"\nØKONOMISK POTENSIALE:")
print(f"  Årlig besparelse:     {yearly_saving:,.0f} kr")
print(f"  NPV over {years} år (5%):  {npv_savings:,.0f} kr")
print(f"  Break-even batteri:   {npv_savings/battery_kw:,.0f} kr/kWh")

print("="*60)