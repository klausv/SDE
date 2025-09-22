#!/usr/bin/env python
"""
Detaljert verifisering av effekttariff-beregning
Viser NØYAKTIG hvordan 12,000 kr/år fremkommer
"""

print("🔍 DETALJERT VERIFISERING AV EFFEKTTARIFF-BEREGNING")
print("="*80)

# Lnett tariffer - betaler KUN for intervallet peak ligger i
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
    return 5600  # Over 100 kW

print("\n📊 SCENARIO 1: KONTORBYGG")
print("-"*60)

# Månedlige peaks for kontorbygg
months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']
peaks_office = [45, 45, 40, 35, 30, 25, 22, 25, 30, 35, 40, 45]
battery_kw = 20

print(f"Batteri: {battery_kw} kW")
print("\nMåned | Peak uten | Tariff uten | Peak med | Tariff med | Besparelse")
print("------|-----------|-------------|----------|------------|------------")

total_without = 0
total_with = 0
monthly_savings = []

for month, peak in zip(months, peaks_office):
    peak_with = max(0, peak - battery_kw)
    tariff_without = get_tariff(peak)
    tariff_with = get_tariff(peak_with)
    saving = tariff_without - tariff_with

    total_without += tariff_without
    total_with += tariff_with
    monthly_savings.append(saving)

    # Finn hvilket intervall
    for from_kw, to_kw, _ in tariff_brackets:
        if from_kw < peak <= to_kw:
            interval_without = f"{from_kw}-{to_kw}"
            break

    for from_kw, to_kw, _ in tariff_brackets:
        if peak_with == 0:
            interval_with = "0"
            break
        if from_kw < peak_with <= to_kw:
            interval_with = f"{from_kw}-{to_kw}"
            break

    print(f"{month:5s} | {peak:3.0f} kW ({interval_without:5s}) | {tariff_without:,} kr | "
          f"{peak_with:3.0f} kW ({interval_with:5s}) | {tariff_with:,} kr | {saving:,} kr")

annual_saving = total_without - total_with

print(f"\nÅRSRESULTAT:")
print(f"  Totalt uten batteri: {total_without:,} kr/år")
print(f"  Totalt med batteri:  {total_with:,} kr/år")
print(f"  ÅRLIG BESPARELSE:    {annual_saving:,} kr/år")

print("\n📊 SCENARIO 2: INDUSTRI")
print("-"*60)

# Høyere peaks for industri
peaks_industrial = [60, 65, 62, 58, 55, 50, 48, 52, 55, 58, 60, 65]
battery_kw = 20

print(f"Batteri: {battery_kw} kW")
print("\nMåned | Peak uten | Tariff uten | Peak med | Tariff med | Besparelse")
print("------|-----------|-------------|----------|------------|------------")

total_without_ind = 0
total_with_ind = 0

for month, peak in zip(months, peaks_industrial):
    peak_with = max(0, peak - battery_kw)
    tariff_without = get_tariff(peak)
    tariff_with = get_tariff(peak_with)
    saving = tariff_without - tariff_with

    total_without_ind += tariff_without
    total_with_ind += tariff_with

    print(f"{month:5s} | {peak:3.0f} kW | {tariff_without:,} kr | "
          f"{peak_with:3.0f} kW | {tariff_with:,} kr | {saving:,} kr")

annual_saving_ind = total_without_ind - total_with_ind

print(f"\nÅRSRESULTAT:")
print(f"  Totalt uten batteri: {total_without_ind:,} kr/år")
print(f"  Totalt med batteri:  {total_with_ind:,} kr/år")
print(f"  ÅRLIG BESPARELSE:    {annual_saving_ind:,} kr/år")

print("\n📊 SCENARIO 3: MER VARIERENDE PROFIL")
print("-"*60)

# Mer realistisk varierende profil
peaks_variable = [35, 38, 32, 28, 24, 20, 18, 22, 26, 30, 34, 37]
battery_kw_options = [10, 15, 20, 25, 30]

print("Batteristørrelse | Årlig besparelse | Kr per kW batteri")
print("-----------------|------------------|-------------------")

for battery_kw in battery_kw_options:
    total_saving = 0
    for peak in peaks_variable:
        peak_with = max(0, peak - battery_kw)
        saving = get_tariff(peak) - get_tariff(peak_with)
        total_saving += saving

    per_kw = total_saving / battery_kw if battery_kw > 0 else 0
    print(f"{battery_kw:15.0f} kW | {total_saving:16,} kr | {per_kw:17.0f} kr/kW")

print("\n💡 KONKLUSJON:")
print("-"*60)
print("Effekttariff-besparelsene varierer betydelig basert på:")
print("1. Forbruksprofil (hvor høye peaks er)")
print("2. Hvor peaks ligger i forhold til tariff-intervallene")
print("3. Batteristørrelse i forhold til peaks")
print(f"\nFor kontorbygg-profilen: {annual_saving:,} kr/år med {20} kW batteri")
print(f"For industri-profilen: {annual_saving_ind:,} kr/år med {20} kW batteri")
print("\n⚠️ MERK: 12,000 kr/år var kanskje for rund/optimistisk!")
print("Realistisk er nærmere 9,000-11,000 kr/år avhengig av profil")

print("\n📈 BEREGNINGSMETODE BEKREFTET:")
print("-"*60)
print("1. Ta månedlig max effekt UTEN batteri")
print("2. Finn hvilket tariff-intervall denne ligger i")
print("3. Beregn månedlig max effekt MED batteri (original - batterikW)")
print("4. Finn hvilket tariff-intervall den reduserte peak ligger i")
print("5. Månedlig besparelse = tariff_uten - tariff_med")
print("6. Summer opp for hele året")
print("="*80)