#!/usr/bin/env python
"""
Verifiser effekttariff-besparelser med realistiske forutsetninger
"""
import pandas as pd
import numpy as np
from core.pvgis_solar import PVGISProduction
from core.consumption_profiles import ConsumptionProfile

print("🔍 VERIFISERING AV EFFEKTTARIFF-BESPARELSER")
print("="*60)

# Hent forbruksprofil
consumption = ConsumptionProfile.generate_annual_profile(
    profile_type='commercial_office',
    annual_kwh=90000,
    year=2020
)

# Beregn månedlige peaks UTEN batteri
monthly_peaks_original = consumption.resample('ME').max()

print("\n📊 MÅNEDLIGE EFFEKTTOPPER UTEN BATTERI:")
print("-"*40)
months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
          'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']

for i, (date, peak) in enumerate(monthly_peaks_original.items()):
    print(f"{months[i % 12]:3s}: {peak:5.1f} kW")

avg_peak = monthly_peaks_original.mean()
max_peak = monthly_peaks_original.max()
min_peak = monthly_peaks_original.min()

print(f"\nGjennomsnitt: {avg_peak:.1f} kW")
print(f"Maks: {max_peak:.1f} kW")
print(f"Min: {min_peak:.1f} kW")

# Beregn effekttariff uten batteri
def calculate_power_tariff(peak_kw):
    """Beregn månedlig effekttariff basert på peak"""
    if peak_kw <= 50:
        return peak_kw * 90
    elif peak_kw <= 200:
        return peak_kw * 85
    else:
        return peak_kw * 80

yearly_cost_original = sum(calculate_power_tariff(peak) for peak in monthly_peaks_original)

print(f"\n💰 EFFEKTTARIFF UTEN BATTERI:")
print(f"Årlig kostnad: {yearly_cost_original:,.0f} kr")
print(f"Per kWh: {yearly_cost_original/90000:.3f} kr/kWh")

# Simuler batteri-effekt (20 kW / 20 kWh)
print("\n🔋 SIMULERING MED 20 kW BATTERI:")
print("-"*40)

# REALISTISKE forutsetninger:
# 1. Batteriet kan ikke alltid være fullt når peak inntreffer
# 2. Batteriet må lades opp igjen etterpå (øker forbruk andre timer)
# 3. Effektivitetstap ved lading/utlading

battery_power = 20  # kW
battery_capacity = 20  # kWh (1 times batteri)
efficiency = 0.95

# Anta at batteriet kan redusere peak med:
# - Best case: full 20 kW reduksjon
# - Realistisk: 60-80% av kapasitet pga SOC-begrensninger
# - Worst case: 40% pga dårlig timing

scenarios = {
    'Optimistisk (100%)': 1.0,
    'Realistisk (70%)': 0.7,
    'Konservativ (50%)': 0.5,
    'Pessimistisk (40%)': 0.4
}

print("\nSCENARIO-ANALYSE:")
print("Scenario           | Reduksjon | Årlig besparelse | kr/kWh")
print("-------------------|-----------|------------------|--------")

for scenario_name, effectiveness in scenarios.items():
    # Beregn nye peaks med batteri
    reduction = battery_power * effectiveness
    monthly_peaks_new = monthly_peaks_original - reduction
    monthly_peaks_new = monthly_peaks_new.clip(lower=0)  # Kan ikke gå under 0

    # Beregn ny effekttariff
    yearly_cost_new = sum(calculate_power_tariff(peak) for peak in monthly_peaks_new)
    yearly_savings = yearly_cost_original - yearly_cost_new
    savings_per_kwh = yearly_savings / 90000

    print(f"{scenario_name:18s} | {reduction:5.1f} kW | {yearly_savings:11,.0f} kr | {savings_per_kwh:.3f}")

# Sjekk mot enkel beregning
print("\n✅ KONTROLLREGNING (forenklet):")
print("-"*40)
simple_savings = 85 * 20 * 12  # kr/kW/mnd * kW * måneder
print(f"Enkel beregning (85 kr × 20 kW × 12 mnd): {simple_savings:,.0f} kr")
print("Dette forutsetter 100% effektivitet og perfekt timing!")

# Hva sa analysen?
print("\n📈 HVA VISTE ANALYSEN?")
print("-"*40)
print("Fra test_battery_sizes.py med 20 kWh/10 kW:")
print("• Effekttariff besparelse: 56,900 kr/år")
print("• Total verdi: 68,900 kr/år")
print("")
print("MEN dette er med 10 kW, ikke 20 kW!")
print("Forventet med 20 kW (dobbelt): ~40,000 kr/år")

# Realistisk vurdering
print("\n💡 REALISTISK VURDERING:")
print("-"*40)
print("1. TEORETISK MAKSIMUM (20 kW × 85 kr × 12 mnd): 20,400 kr")
print("2. REALISTISK (70% effektivitet): ~14,000 kr")
print("3. ANALYSEN VISTE (skalert til 20 kW): ~40,000 kr")
print("")
print("⚠️ ANALYSEN OVERESTIMERER med faktor 2-3x!")
print("Trolig fordi:")
print("• Antar perfekt prediksjon av peaks")
print("• Ignorerer SOC-begrensninger")
print("• Ikke tar hensyn til at batteri må lades")

print("\n📊 REELL FORVENTET BESPARELSE:")
realistic_savings = 85 * 20 * 12 * 0.7  # 70% effectiveness
print(f"20 kW batteri: {realistic_savings:,.0f} kr/år")
print(f"Per kWh batteri: {realistic_savings/20:,.0f} kr/kWh/år")
print(f"Over 15 år (NPV 5%): {realistic_savings * 10.38:,.0f} kr")
print(f"Break-even batterikost: {realistic_savings * 10.38 / 20:,.0f} kr/kWh")

print("="*60)