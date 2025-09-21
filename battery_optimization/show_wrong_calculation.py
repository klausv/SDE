#!/usr/bin/env python
"""
Vis hvordan modellen FEILAKTIG beregner effekttariff
"""
import pandas as pd
import numpy as np

print("🔴 FEIL I MODELLENS EFFEKTTARIFF-BEREGNING")
print("="*60)

print("\n❌ MODELLEN BRUKER DISSE TARIFFENE (FEIL!):")
print("Fra kW | Til kW | NOK/kW/måned")
print("-------|--------|-------------")
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
    (100, 9999, 5600)
]

for from_kw, to_kw, rate in brackets:
    print(f"{from_kw:6.0f} | {to_kw:6.0f} | {rate:,}")

print("\nDETTE ER PROGRESSIV TARIFF (som strøm-skatt)")
print("Hver kW i høyere bracket koster mer!")

def calculate_wrong_tariff(peak_kw):
    """Modellens feilaktige beregning"""
    monthly_charge = 0
    for from_kw, to_kw, rate in brackets:
        if peak_kw > from_kw:
            bracket_kw = min(peak_kw - from_kw, to_kw - from_kw)
            monthly_charge += bracket_kw * rate
        if peak_kw <= to_kw:
            break
    return monthly_charge

# Test med eksempel
test_peaks = [20, 30, 50, 75, 100]

print("\n📊 EKSEMPEL PÅ FEILBEREGNING:")
print("Peak kW | Feil modell | Korrekt Lnett | Avvik")
print("--------|-------------|---------------|-------")

for peak in test_peaks:
    wrong = calculate_wrong_tariff(peak)
    # Korrekt Lnett tariff
    if peak <= 50:
        correct = peak * 90
    elif peak <= 200:
        correct = peak * 85
    else:
        correct = peak * 80

    diff = wrong - correct
    print(f"{peak:7.0f} | {wrong:11,.0f} | {correct:13,.0f} | {diff:+6,.0f}")

print("\n🔍 HVA SKJER MED 20 kW BATTERI?")
print("-"*40)

# Eksempel: Peak reduseres fra 30 til 10 kW
original_peak = 30
reduced_peak = 10

original_wrong = calculate_wrong_tariff(original_peak)
reduced_wrong = calculate_wrong_tariff(reduced_peak)
savings_wrong = original_wrong - reduced_wrong

original_correct = original_peak * 85
reduced_correct = reduced_peak * 90
savings_correct = original_correct - reduced_correct

print(f"Peak uten batteri: {original_peak} kW")
print(f"Peak med batteri:  {reduced_peak} kW")
print("")
print(f"FEIL MODELL (progressiv):")
print(f"  Kostnad før:  {original_wrong:,.0f} kr/mnd")
print(f"  Kostnad etter: {reduced_wrong:,.0f} kr/mnd")
print(f"  Besparelse:    {savings_wrong:,.0f} kr/mnd")
print(f"  Årlig:         {savings_wrong*12:,.0f} kr/år")
print("")
print(f"KORREKT LNETT (flat per kW):")
print(f"  Kostnad før:  {original_correct:,.0f} kr/mnd")
print(f"  Kostnad etter: {reduced_correct:,.0f} kr/mnd")
print(f"  Besparelse:    {savings_correct:,.0f} kr/mnd")
print(f"  Årlig:         {savings_correct*12:,.0f} kr/år")

print("\n💡 KONKLUSJON:")
print("-"*40)
print("Modellen overestimerer besparelsene dramatisk!")
print(f"Faktor: {savings_wrong/savings_correct:.1f}x for høyt")

print("\n📊 MED REALISTISK FORBRUKSPROFIL (20 kW peaks):")
monthly_peaks = [24, 24, 21, 21, 21, 18, 18, 18, 21, 21, 21, 24]
battery_reduction = 10  # 10 kW batteri

original_cost_wrong = sum(calculate_wrong_tariff(p) for p in monthly_peaks)
reduced_cost_wrong = sum(calculate_wrong_tariff(max(0, p-battery_reduction)) for p in monthly_peaks)
savings_wrong_annual = original_cost_wrong - reduced_cost_wrong

original_cost_correct = sum(p * 90 for p in monthly_peaks)  # Alle under 50 kW
reduced_cost_correct = sum(max(0, p-battery_reduction) * 90 for p in monthly_peaks)
savings_correct_annual = original_cost_correct - reduced_cost_correct

print(f"MODELLEN sier: {savings_wrong_annual:,.0f} kr/år besparelse")
print(f"KORREKT er:    {savings_correct_annual:,.0f} kr/år besparelse")
print(f"Overestimering: {savings_wrong_annual/savings_correct_annual:.1f}x")

print("="*60)