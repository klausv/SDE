#!/usr/bin/env python
"""
Korrekt forståelse av effekttariffer
"""

print("✅ KORREKT FORSTÅELSE AV EFFEKTTARIFFER")
print("="*60)

print("\n📊 MODELLENS TARIFFER (som faktisk er korrekte!):")
print("Intervall      | Kostnad for intervallet")
print("---------------|------------------------")
print("Første 2 kW    | 136 kr/mnd TOTALT for disse 2 kW")
print("Neste 3 kW     | 232 kr/mnd TOTALT for disse 3 kW")
print("Neste 5 kW     | 372 kr/mnd TOTALT for disse 5 kW")
print("Neste 5 kW     | 572 kr/mnd TOTALT for disse 5 kW")
print("Neste 5 kW     | 772 kr/mnd TOTALT for disse 5 kW")
print("Neste 5 kW     | 972 kr/mnd TOTALT for disse 5 kW")
print("Neste 25 kW    | 1772 kr/mnd TOTALT for disse 25 kW")
print("Neste 25 kW    | 2572 kr/mnd TOTALT for disse 25 kW")
print("Neste 25 kW    | 3372 kr/mnd TOTALT for disse 25 kW")
print("Over 100 kW    | 5600 kr/mnd TOTALT")

print("\n💡 DETTE GIR GJENNOMSNITTSPRIS PER kW:")
print("kW    | Total kr/mnd | Kr per kW")
print("------|--------------|----------")

def calculate_tariff(peak_kw):
    """Beregn total månedlig kostnad"""
    brackets = [
        (0, 2, 136),      # 136 kr for 2 kW = 68 kr/kW
        (2, 5, 232),      # 232 kr for 3 kW = 77 kr/kW
        (5, 10, 372),     # 372 kr for 5 kW = 74 kr/kW
        (10, 15, 572),    # 572 kr for 5 kW = 114 kr/kW
        (15, 20, 772),    # 772 kr for 5 kW = 154 kr/kW
        (20, 25, 972),    # 972 kr for 5 kW = 194 kr/kW
        (25, 50, 1772),   # 1772 kr for 25 kW = 71 kr/kW
        (50, 75, 2572),   # 2572 kr for 25 kW = 103 kr/kW
        (75, 100, 3372),  # 3372 kr for 25 kW = 135 kr/kW
        (100, 9999, 5600) # 5600 kr flat
    ]

    monthly_charge = 0
    for from_kw, to_kw, rate in brackets:
        if peak_kw > from_kw:
            bracket_kw = min(peak_kw - from_kw, to_kw - from_kw)
            monthly_charge += bracket_kw * (rate / (to_kw - from_kw))
        if peak_kw <= to_kw:
            break
    return monthly_charge

# Test noen verdier
test_values = [10, 20, 30, 50, 75, 100]
for kw in test_values:
    total = calculate_tariff(kw)
    per_kw = total / kw if kw > 0 else 0
    print(f"{kw:5.0f} | {total:12,.0f} | {per_kw:9.0f}")

print("\n🔍 SAMMENLIGNING MED LNETT STANDARD:")
print("-"*40)
print("Lnett standard næring (inkl. mva):")
print("  0-50 kW:   90 kr/kW/mnd")
print("  50-200 kW: 85 kr/kW/mnd")
print("  200+ kW:   80 kr/kW/mnd")

print("\n📊 EKSEMPEL: 30 kW PEAK")
print("-"*40)

# Modellens tariff (progressiv)
peak = 30
cost_model = 0
cost_model += 136  # Første 2 kW
cost_model += 232  # Neste 3 kW (2-5)
cost_model += 372  # Neste 5 kW (5-10)
cost_model += 572  # Neste 5 kW (10-15)
cost_model += 772  # Neste 5 kW (15-20)
cost_model += 972  # Neste 5 kW (20-25)
cost_model += (30-25) * (1772/25)  # Neste 5 kW (25-30)

# Lnett standard
cost_lnett = 30 * 90

print(f"Modellens tariff: {cost_model:,.0f} kr/mnd")
print(f"Lnett standard:   {cost_lnett:,.0f} kr/mnd")
print(f"Forskjell:        {cost_model-cost_lnett:+,.0f} kr/mnd")

print("\n💰 BESPARELSE MED 10 kW BATTERI:")
print("-"*40)

# Fra 30 til 20 kW
cost_30 = calculate_tariff(30)
cost_20 = calculate_tariff(20)
saving_model = cost_30 - cost_20

# Lnett standard
saving_lnett = 10 * 90

print(f"Modellens tariff: {saving_model:,.0f} kr/mnd = {saving_model*12:,.0f} kr/år")
print(f"Lnett standard:   {saving_lnett:,.0f} kr/mnd = {saving_lnett*12:,.0f} kr/år")

print("\n⚠️ VIKTIG OBSERVASJON:")
print("-"*40)
print("Modellens tariffer ser ut til å være en gammel/annen struktur")
print("Den gir HØYERE besparelser enn Lnett standard for små peaks")
print("Men strukturen er riktig forstått - det er kr/mnd per intervall")

print("\n📈 REELL EFFEKT AV 20 kW BATTERI:")
monthly_peaks = [24, 24, 21, 21, 21, 18, 18, 18, 21, 21, 21, 24]  # Typisk kontor
battery_kw = 20

# Med modellens tariff
original = sum(calculate_tariff(p) for p in monthly_peaks)
reduced = sum(calculate_tariff(max(0, p-battery_kw)) for p in monthly_peaks)
saving_model_year = original - reduced

# Med Lnett standard (alle peaks under 50 kW)
original_lnett = sum(p * 90 for p in monthly_peaks)
reduced_lnett = sum(max(0, p-battery_kw) * 90 for p in monthly_peaks)
saving_lnett_year = original_lnett - reduced_lnett

print(f"ÅRLIG BESPARELSE:")
print(f"  Modellens tariff: {saving_model_year:,.0f} kr/år")
print(f"  Lnett standard:   {saving_lnett_year:,.0f} kr/år")
print(f"  Ratio:            {saving_model_year/saving_lnett_year if saving_lnett_year > 0 else 0:.1f}x")

print("="*60)