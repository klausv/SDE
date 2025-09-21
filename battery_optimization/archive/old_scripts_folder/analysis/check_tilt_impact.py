#!/usr/bin/env python3
"""
Sjekke hvordan takvinkel påvirker PV-produksjon i Stavanger
"""
import numpy as np

def calculate_tilt_factor(tilt_angle, latitude=58.97):
    """
    Beregn relativ produksjon for ulike takvinkler
    Optimal vinkel for Stavanger er ca 35-40° for årsproduksjon
    """
    optimal_tilt = latitude - 15  # Tommelfingerregel for årlig optimum

    # Relativ produksjon basert på avvik fra optimal vinkel
    deviation = abs(tilt_angle - optimal_tilt)

    # Produksjonstap ca 0.3-0.5% per grad avvik
    loss_per_degree = 0.004
    relative_production = 1.0 - (deviation * loss_per_degree)

    return max(0.7, relative_production)  # Minimum 70% produksjon

print("=" * 60)
print("TAKVINKELENS PÅVIRKNING PÅ PV-PRODUKSJON I STAVANGER")
print("=" * 60)

print("\nLokasjon: Stavanger (58.97°N)")
print("Optimal takvinkel for årsproduksjon: ~44° (breddegrad - 15)")

print("\n📊 Relativ produksjon for ulike takvinkler:")
print("-" * 40)

angles = [15, 20, 25, 30, 35, 40, 45, 50]
for angle in angles:
    factor = calculate_tilt_factor(angle)
    print(f"  {angle}°: {factor:.1%} av maksimal produksjon")

print("\n🔍 Analyse for vårt system:")
print("-" * 40)

# Sammenlign takvinkler
tilt_15 = calculate_tilt_factor(15)
tilt_25 = calculate_tilt_factor(25)
tilt_30 = calculate_tilt_factor(30)

print(f"\nTidligere antakelser:")
print(f"  • 15° takvinkel: {tilt_15:.1%} produksjon")
print(f"  • 25° takvinkel: {tilt_25:.1%} produksjon")

print(f"\nKorrekt takvinkel:")
print(f"  • 30° takvinkel: {tilt_30:.1%} produksjon")

print(f"\nForskjell:")
print(f"  • 30° vs 15°: +{(tilt_30/tilt_15 - 1)*100:.1f}% produksjon")
print(f"  • 30° vs 25°: +{(tilt_30/tilt_25 - 1)*100:.1f}% produksjon")

# Hvis vi har 133 MWh med 30°, hva ville det vært med andre vinkler?
base_production = 133_017  # kWh med 30°

production_15 = base_production * (tilt_15 / tilt_30)
production_25 = base_production * (tilt_25 / tilt_30)

print(f"\n💡 Estimert årsproduksjon med ulike takvinkler:")
print(f"  • 15°: {production_15/1000:.1f} MWh/år")
print(f"  • 25°: {production_25/1000:.1f} MWh/år")
print(f"  • 30°: {base_production/1000:.1f} MWh/år (faktisk)")

print("\n⚠️ MERK:")
print("  • Faktisk produksjonsforskjell avhenger også av:")
print("    - Skyggeforhold")
print("    - Snødekke om vinteren (brattere tak = mindre snø)")
print("    - Fordeling sommer/vinter produksjon")
print("  • 30° gir bedre vinterproduksjon enn lavere vinkler")