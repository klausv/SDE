#!/usr/bin/env python
"""
Realistisk beregning basert på faktisk forbruksprofil
for 150 kWp solcelleanlegg i Stavanger
"""
import numpy as np

print("📊 REALISTISK EFFEKTTARIFF-BEREGNING FOR STAVANGER-ANLEGGET")
print("="*80)

# Lnett tariffer
tariff_brackets = [
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

def get_tariff(peak_kw):
    """Finn månedlig kostnad for gitt peak"""
    if peak_kw <= 0:
        return 0
    for from_kw, to_kw, cost in tariff_brackets:
        if from_kw < peak_kw <= to_kw:
            return cost
    return 5600

print("\n🏭 ANLEGGSDATA:")
print("-"*60)
print("PV installert:     150 kWp")
print("Inverter:          110 kW")
print("Grid limit:        77 kW")
print("Forventet årsprod: 90 MWh")
print("Typisk forbruk:    Kontorbygg/lett industri")

print("\n📈 REALISTISKE MÅNEDLIGE PEAKS (basert på typisk forbruk):")
print("-"*60)

# Mer realistisk profil for kontorbygg/lett industri i Norge
# Høyere forbruk vinter, lavere sommer
months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
          'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']

# Realistiske peaks for 90 MWh årlig forbruk
# Vinter: høyt forbruk (oppvarming, lys)
# Sommer: lavt forbruk
peaks_realistic = [42, 40, 36, 32, 28, 24, 20, 22, 28, 34, 38, 42]

print("Måned:    " + "  ".join(f"{m:>4s}" for m in months))
print("Peak kW:  " + "  ".join(f"{p:>4.0f}" for p in peaks_realistic))

# Test ulike batteristørrelser
battery_sizes = [10, 15, 20, 25, 30, 40]

print("\n💰 EFFEKTTARIFF-BESPARELSE VED ULIKE BATTERISTØRRELSER:")
print("-"*80)
print("Batteri | Jan | Feb | Mar | Apr | Mai | Jun | Jul | Aug | Sep | Okt | Nov | Des | TOTAL")
print("--------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------")

for battery_kw in battery_sizes:
    monthly_savings = []
    for peak in peaks_realistic:
        peak_with = max(0, peak - battery_kw)
        saving = get_tariff(peak) - get_tariff(peak_with)
        monthly_savings.append(saving)

    total = sum(monthly_savings)

    # Format output
    row = f"{battery_kw:2.0f} kW   |"
    for saving in monthly_savings:
        row += f"{saving:5.0f}|"
    row += f"{total:7.0f}"
    print(row)

print("\n📊 DETALJERT ANALYSE FOR 20 kW BATTERI:")
print("-"*80)

battery_kw = 20
print(f"Batteristørrelse: {battery_kw} kW")
print("\nMåned | Peak uten | Intervall      | Tariff | Peak med | Intervall     | Tariff | Besparelse")
print("------|-----------|----------------|--------|----------|---------------|--------|------------")

total_without = 0
total_with = 0

for month, peak in zip(months, peaks_realistic):
    peak_with = max(0, peak - battery_kw)
    tariff_without = get_tariff(peak)
    tariff_with = get_tariff(peak_with)
    saving = tariff_without - tariff_with

    total_without += tariff_without
    total_with += tariff_with

    # Finn intervaller
    interval_without = ""
    interval_with = ""
    for from_kw, to_kw, _ in tariff_brackets:
        if from_kw < peak <= to_kw:
            interval_without = f"{from_kw:2.0f}-{to_kw:3.0f} kW"
            if to_kw == float('inf'):
                interval_without = f"{from_kw}+ kW"
            break

    for from_kw, to_kw, _ in tariff_brackets:
        if peak_with == 0:
            interval_with = "0 kW"
            break
        if from_kw < peak_with <= to_kw:
            interval_with = f"{from_kw:2.0f}-{to_kw:3.0f} kW"
            if to_kw == float('inf'):
                interval_with = f"{from_kw}+ kW"
            break

    print(f"{month:5s} | {peak:4.0f} kW  | {interval_without:14s} | {tariff_without:6.0f} | "
          f"{peak_with:4.0f} kW  | {interval_with:13s} | {tariff_with:6.0f} | {saving:10.0f}")

annual_saving = total_without - total_with

print(f"\nÅRSOVERSIKT:")
print(f"  Årlig kostnad UTEN batteri: {total_without:,} kr")
print(f"  Årlig kostnad MED batteri:  {total_with:,} kr")
print(f"  ─────────────────────────────────────")
print(f"  ÅRLIG BESPARELSE:           {annual_saving:,} kr")

print("\n💡 ØKONOMISK ANALYSE:")
print("-"*60)

# NPV beregning
discount_rate = 0.05
years = 15
npv_factor = sum(1/(1+discount_rate)**y for y in range(1, years+1))

print(f"Diskonteringsrente: {discount_rate*100:.0f}%")
print(f"Levetid:            {years} år")
print(f"NPV-faktor:         {npv_factor:.3f}")

# Beregn for ulike batterikostnader
print(f"\nØkonomi for {battery_kw} kW batteri (kun effekttariff):")
print("Batterikostnad | Investment | NPV        | Payback | Status")
print("---------------|------------|------------|---------|--------")

for cost_per_kw in [2000, 2500, 3000, 3500, 4000, 5000]:
    investment = cost_per_kw * battery_kw
    npv = annual_saving * npv_factor - investment
    payback = investment / annual_saving if annual_saving > 0 else 999
    status = "✅" if npv > 0 else "❌"

    print(f"{cost_per_kw:,} kr/kW    | {investment:,} kr | {npv:+10,.0f} | {payback:7.1f} | {status}")

break_even = annual_saving * npv_factor / battery_kw
print(f"\nBreak-even batterikostnad: {break_even:,.0f} kr/kW")

print("\n⚠️ VIKTIGE FORBEHOLD:")
print("-"*60)
print("1. Dette er KUN effekttariff-besparelse")
print("2. Kommer I TILLEGG TIL:")
print(f"   • Avkortning unngått:  ~5,000-10,000 kr/år")
print(f"   • Arbitrasje:          ~2,000-4,000 kr/år")
print(f"   • Økt selvforsyning:   ~2,000-3,000 kr/år")
print("3. Forutsetter at batteri kan levere når peak inntreffer")
print("4. Realistisk realisering: 70-80% av teoretisk")

realistic_saving = annual_saving * 0.75
print(f"\nRealistisk årlig besparelse (75%): {realistic_saving:,.0f} kr")
print(f"Total med andre verdidrivere:      ~{realistic_saving + 9000:,.0f} kr/år")

print("="*80)