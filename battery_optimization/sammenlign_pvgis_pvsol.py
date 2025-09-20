#!/usr/bin/env python3
"""
Sammenlign PVGIS og PVSol tall for å forstå forskjellen
"""
import requests
import numpy as np

print("\n" + "="*70)
print("📊 SAMMENLIGNING: PVGIS vs PVSOL")
print("="*70)

# Systemspesifikasjoner
LAT = 58.929644
LON = 5.623052
SYSTEM_KWP = 138.55

print("\n📍 Lokasjon og system:")
print(f"   Koordinater: {LAT:.6f}, {LON:.6f}")
print(f"   System: {SYSTEM_KWP} kWp")

# 1. PVSol resultater (fra PDF)
print("\n🔷 PVSol resultater (fra PDF):")
print("   Årlig AC produksjon: 133,017 kWh")
print("   Spesifikk produksjon: 959.78 kWh/kWp")
print("   Performance Ratio: 92.62%")
print("   Tilt: 15°, Azimuth: 171° (Sør)")
print("   System tap: 14%")
print("   Klimadata: Meteonorm 8.2 (2001-2020)")

# 2. Test PVGIS med ulike parametere
print("\n🔷 PVGIS tester:")

configs = [
    {"name": "Som PVSol (15° tilt, 171° azimuth)", "angle": 15, "aspect": -9, "loss": 14},
    {"name": "Optimal tilt for Stavanger", "angle": 39, "aspect": 0, "loss": 14},
    {"name": "Flat tak (5° tilt)", "angle": 5, "aspect": 0, "loss": 14},
    {"name": "Som PVSol med lavere tap", "angle": 15, "aspect": -9, "loss": 10},
]

for config in configs:
    print(f"\n   📊 {config['name']}:")

    url = "https://re.jrc.ec.europa.eu/api/seriescalc"
    params = {
        'lat': LAT,
        'lon': LON,
        'pvcalculation': 1,
        'peakpower': SYSTEM_KWP,
        'loss': config['loss'],
        'angle': config['angle'],
        'aspect': config['aspect'],
        'outputformat': 'json',
        'browser': 0
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()

            # Hent årlig produksjon
            if 'outputs' in data and 'hourly' in data['outputs']:
                hourly = data['outputs']['hourly']
                total_kwh = sum(h.get('P', 0) for h in hourly) / 1000
                years = len(hourly) / 8760
                årlig = total_kwh / years
                spesifikk = årlig / SYSTEM_KWP

                print(f"      Tilt: {config['angle']}°, Azimuth: {180 + config['aspect']}°")
                print(f"      Tap: {config['loss']}%")
                print(f"      Årlig produksjon: {årlig:.0f} kWh")
                print(f"      Spesifikk: {spesifikk:.1f} kWh/kWp")
                print(f"      Forskjell fra PVSol: {(spesifikk/959.78 - 1)*100:+.1f}%")
    except:
        print(f"      ❌ Kunne ikke hente data")

# 3. Mulige årsaker til forskjell
print("\n🔍 Mulige årsaker til forskjell mellom PVGIS og PVSol:")
print("   1. Klimadata: PVSol bruker Meteonorm 8.2 (2001-2020)")
print("      PVGIS bruker SARAH-2 (2005-2020) eller ERA5")
print("   2. Skyggeberegning: PVSol har detaljert 3D-modell")
print("   3. Temperaturmodell: Ulike modeller for temperatureffekt")
print("   4. Invertertap: PVSol kan ha mer detaljert invertermodell")
print("   5. Kabling/mismatch: PVSol inkluderer detaljerte DC-tap")

# 4. Anbefaling
print("\n💡 Anbefaling:")
print("   PVSol er profesjonell programvare med detaljert modellering.")
print("   For batteridimensjonering bør vi bruke PVSol-tallene:")
print("   - 133 MWh/år total produksjon")
print("   - 960 kWh/kWp spesifikk produksjon")
print("   Dette gir mer konservativ og realistisk batteridimensjonering.")

print("\n" + "="*70)