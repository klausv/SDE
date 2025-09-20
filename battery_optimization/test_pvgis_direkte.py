#!/usr/bin/env python3
"""
Test PVGIS API direkte for å forstå hvorfor vi ikke får fornuftige tall
"""
import requests
import json

print("\n" + "="*70)
print("🔍 TESTER PVGIS API DIREKTE")
print("="*70)

# Eksakt lokasjon og system
LAT = 58.929644
LON = 5.623052
PEAKPOWER = 138.55  # kWp
LOSS = 14  # % tap (som i PVSol)
ANGLE = 15  # grader tilt (fra PVSol)
ASPECT = -9  # PVGIS bruker 0=sør, -9 = 171 grader

# Test 1: Hent hourly data
print("\n📊 Test 1: PVGIS hourly PV production...")
url = "https://re.jrc.ec.europa.eu/api/seriescalc"

params = {
    'lat': LAT,
    'lon': LON,
    'pvcalculation': 1,
    'peakpower': PEAKPOWER,
    'loss': LOSS,
    'angle': ANGLE,
    'aspect': ASPECT,
    'outputformat': 'json',
    'browser': 0
}

print(f"   Koordinater: {LAT}, {LON}")
print(f"   System: {PEAKPOWER} kWp")
print(f"   Tap: {LOSS}%")
print(f"   Tilt: {ANGLE}°")
print(f"   Orientering: {ASPECT}° (0=sør)")

try:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Sjekk output struktur
    if 'outputs' in data:
        outputs = data['outputs']

        # Sjekk fixed values
        if 'fixed' in outputs:
            fixed = outputs['fixed']
            print("\n✅ Fixed system outputs:")
            print(f"   E_y (yearly): {fixed.get('E_y', 'N/A')} kWh")
            print(f"   E_d (daily avg): {fixed.get('E_d', 'N/A')} kWh")
            print(f"   E_m (monthly avg): {fixed.get('E_m', 'N/A')} kWh")
            print(f"   H_y (yearly irradiation): {fixed.get('H_y', 'N/A')} kWh/m²")
            print(f"   SD_y (year-to-year variability): {fixed.get('SD_y', 'N/A')} kWh")

            # Beregn spesifikk produksjon
            if 'E_y' in fixed:
                specific = fixed['E_y'] / PEAKPOWER
                print(f"\n   📈 Spesifikk produksjon: {specific:.1f} kWh/kWp")

        # Sjekk hourly data
        if 'hourly' in outputs:
            hourly = outputs['hourly']
            print(f"\n   Timer med data: {len(hourly)}")

            # Analyser første 10 entries
            if len(hourly) > 0:
                print("\n   Første 5 datapunkter:")
                for i, h in enumerate(hourly[:5]):
                    print(f"   {h.get('time', 'N/A')}: P={h.get('P', 'N/A')} W")

                # Beregn total
                total_p = sum(h.get('P', 0) for h in hourly) / 1000
                årlig_snitt = total_p / (len(hourly) / 8760)
                print(f"\n   Total produksjon fra hourly: {total_p:.1f} kWh")
                print(f"   Antall år: {len(hourly) / 8760:.1f}")
                print(f"   Årlig snitt: {årlig_snitt:.1f} kWh/år")
                print(f"   Spesifikk årlig: {årlig_snitt/PEAKPOWER:.1f} kWh/kWp")

        # Sjekk totals struktur
        if 'totals' in outputs:
            totals = outputs['totals']
            print("\n📊 Totals struktur:")
            print(json.dumps(totals, indent=2)[:500])

except Exception as e:
    print(f"❌ Feil: {e}")
    print(f"   Response status: {response.status_code if 'response' in locals() else 'N/A'}")
    if 'response' in locals() and response.text:
        print(f"   Response text: {response.text[:500]}")

# Test 2: TMY data
print("\n" + "="*50)
print("📊 Test 2: PVGIS TMY radiation data...")

url = "https://re.jrc.ec.europa.eu/api/tmy"
params = {
    'lat': LAT,
    'lon': LON,
    'outputformat': 'json'
}

try:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if 'outputs' in data:
        outputs = data['outputs']

        # Sjekk location info
        if 'location' in outputs:
            loc = outputs['location']
            print(f"   Lokasjon: {loc.get('latitude', 'N/A')}, {loc.get('longitude', 'N/A')}")
            print(f"   Høyde: {loc.get('elevation', 'N/A')} m")

        # Sjekk meteo data
        if 'tmy_hourly' in outputs:
            tmy_hourly = outputs['tmy_hourly']
            print(f"   Timer TMY data: {len(tmy_hourly)}")

            if len(tmy_hourly) > 0:
                # Analyser årlig stråling
                ghi_total = sum(h.get('G(h)', 0) for h in tmy_hourly)
                print(f"   Total GHI: {ghi_total/1000:.1f} kWh/m²/år")

                # Enkel PV estimat
                pv_estimate = (ghi_total / 1000) * PEAKPOWER * 0.85 * (1 - LOSS/100)
                print(f"   Estimert PV (enkel): {pv_estimate/1000:.1f} MWh/år")
                print(f"   Spesifikk (enkel): {pv_estimate/PEAKPOWER:.1f} kWh/kWp")

except Exception as e:
    print(f"❌ Feil: {e}")

print("\n" + "="*70)
print("✅ Test fullført!")
print("="*70)