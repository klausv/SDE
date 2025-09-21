#!/usr/bin/env python3
"""
Varighetskurve basert på FAKTISKE PVGIS-data
Henter reelle timedata fra PVGIS API
"""
import numpy as np
import matplotlib.pyplot as plt
import requests

print("\n" + "="*70)
print("📊 VARIGHETSKURVE - BASERT PÅ PVGIS TIMEDATA")
print("="*70)

# Systemparametere
PV_KWP = 138.55  # kWp installert DC
INV_GRENSE = 100  # kW AC invertergrense
NETT_GRENSE = 70  # kW netteksport grense

# Lokasjon (Snødevegen 122, Tananger)
LAT = 58.929644
LON = 5.623052
TILT = 15  # Fra PVSol
AZIMUTH = -9  # 171° = -9 i PVGIS (0=sør)

def hent_pvgis_timedata():
    """Hent faktiske timedata fra PVGIS"""
    print("\n📡 Henter timedata fra PVGIS...")

    url = "https://re.jrc.ec.europa.eu/api/seriescalc"

    params = {
        'lat': LAT,
        'lon': LON,
        'pvcalculation': 1,
        'peakpower': PV_KWP,
        'loss': 7,  # Bruk realistiske tap (ikke 14% default)
        'angle': TILT,
        'aspect': AZIMUTH,
        'outputformat': 'json',
        'browser': 0
    }

    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()

        if 'outputs' in data and 'hourly' in data['outputs']:
            hourly = data['outputs']['hourly']
            print(f"   ✅ Hentet {len(hourly)} timer med data")

            # Ekstraher AC power (W) og konverter til kW
            pv_ac = np.array([h.get('P', 0) / 1000 for h in hourly])

            # PVGIS gir typisk 5 år med data, ta gjennomsnitt
            years = len(pv_ac) / 8760
            if years > 1:
                # Reshape til år x 8760 og ta gjennomsnitt
                n_years = int(years)
                pv_ac = pv_ac[:n_years*8760].reshape(n_years, 8760).mean(axis=0)
                print(f"   📊 Bruker gjennomsnitt av {n_years} år")

            return pv_ac
        else:
            print("   ❌ Ingen hourly data funnet")
            return None

    except Exception as e:
        print(f"   ❌ Feil ved henting: {e}")
        return None

def hent_pvgis_tmy():
    """Alternativ: Hent TMY (Typical Meteorological Year) data"""
    print("\n📡 Prøver TMY data som alternativ...")

    url = "https://re.jrc.ec.europa.eu/api/tmy"

    params = {
        'lat': LAT,
        'lon': LON,
        'outputformat': 'json'
    }

    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()

        if 'outputs' in data and 'tmy_hourly' in data['outputs']:
            tmy = data['outputs']['tmy_hourly']
            print(f"   ✅ Hentet TMY med {len(tmy)} timer")

            # Beregn PV produksjon fra stråling
            pv_ac = []
            for hour in tmy:
                # Global tilted irradiance (W/m²)
                gti = hour.get('G(i)', 0)
                # Enkel PV modell: P = GTI * kWp * performance_ratio
                # Performance ratio inkluderer inverter efficiency, temperatur etc
                pr = 0.85  # Typisk performance ratio
                power_ac = (gti / 1000) * PV_KWP * pr
                # Begrens til inverter
                power_ac = min(power_ac, INV_GRENSE)
                pv_ac.append(power_ac)

            return np.array(pv_ac)
        else:
            print("   ❌ Ingen TMY data funnet")
            return None

    except Exception as e:
        print(f"   ❌ Feil ved TMY henting: {e}")
        return None

# Hent data
pv_ac = hent_pvgis_timedata()

# Hvis standard API feiler, prøv TMY
if pv_ac is None or len(pv_ac) != 8760:
    print("   ⚠️ Prøver TMY som fallback...")
    pv_ac = hent_pvgis_tmy()

if pv_ac is None or len(pv_ac) == 0:
    print("\n❌ Kunne ikke hente PVGIS data. Avbryter.")
    exit(1)

# Skalér til PVSol produksjon hvis ønskelig
PVSOL_ÅRLIG = 133017  # kWh fra PVSol
pvgis_årlig = np.sum(pv_ac)
print(f"\n📊 Årlig produksjon:")
print(f"   PVGIS rå: {pvgis_årlig:.0f} kWh")
print(f"   PVSol: {PVSOL_ÅRLIG} kWh")

# Spør om skalering
skalering = PVSOL_ÅRLIG / pvgis_årlig if pvgis_årlig > 0 else 1.0
print(f"   Skaleringsfaktor: {skalering:.2f}")

if skalering > 1.1:  # Hvis PVGIS er mer enn 10% lavere
    print("   📈 Skalerer opp til PVSol-nivå...")
    pv_ac = pv_ac * skalering

# Statistikk
print(f"\n📈 Produksjonsstatistikk (etter evt. skalering):")
print(f"   Total årsproduksjon: {np.sum(pv_ac):.0f} kWh")
print(f"   Spesifikk produksjon: {np.sum(pv_ac)/PV_KWP:.1f} kWh/kWp")
print(f"   Maks AC effekt: {np.max(pv_ac):.1f} kW")
print(f"   Timer > 0 kW: {np.sum(pv_ac > 0.1)}")
print(f"   Timer > 50 kW: {np.sum(pv_ac > 50)}")
print(f"   Timer > 70 kW: {np.sum(pv_ac > NETT_GRENSE)}")
print(f"   Timer > 80 kW: {np.sum(pv_ac > 80)}")
print(f"   Timer > 90 kW: {np.sum(pv_ac > 90)}")
print(f"   Timer ≥ 99 kW: {np.sum(pv_ac >= 99)}")

# Lag varighetskurve
pv_sortert = np.sort(pv_ac)[::-1]  # Sorter høy til lav
timer = np.arange(8760)

# Plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [3, 1]})

# ØVRE PLOT - Full varighetskurve
ax1.fill_between(timer, 0, pv_sortert, color='gold', alpha=0.3, label='PV Produksjon AC')
ax1.plot(timer, pv_sortert, color='darkorange', linewidth=2)

# Markér kritiske grenser
# 1. kWp (138.55 kW) - Teoretisk DC maks
ax1.axhline(y=PV_KWP, color='blue', linestyle=':', linewidth=1.5, alpha=0.5)
ax1.text(200, PV_KWP + 2, f'DC kWp (STC): {PV_KWP:.1f} kW',
         fontsize=9, color='blue', style='italic')

# 2. Invertergrense (100 kW)
ax1.axhline(y=INV_GRENSE, color='red', linestyle='-', linewidth=2.5, alpha=0.8)
ax1.text(200, INV_GRENSE - 3, f'Inverter AC maks: {INV_GRENSE} kW',
         fontsize=10, fontweight='bold', color='red')

# 3. Nettgrense (70 kW)
ax1.axhline(y=NETT_GRENSE, color='darkgreen', linestyle='-', linewidth=2.5, alpha=0.8)
ax1.text(200, NETT_GRENSE - 3, f'Nett eksportgrense: {NETT_GRENSE} kW',
         fontsize=10, fontweight='bold', color='darkgreen')

# Fargelegg områder
# Over invertergrense (skulle være kuttet av inverter)
if np.any(pv_sortert > INV_GRENSE):
    ax1.fill_between(timer, INV_GRENSE, np.minimum(pv_sortert, PV_KWP),
                     where=(pv_sortert > INV_GRENSE),
                     color='red', alpha=0.2, label='Over inverter (teoretisk)')

# Mellom nett og inverter (potensielt kuttet)
ax1.fill_between(timer, NETT_GRENSE, np.minimum(pv_sortert, INV_GRENSE),
                 where=(pv_sortert > NETT_GRENSE),
                 color='orange', alpha=0.3, label='Kan kuttes ved nettgrense (70-100 kW)')

# Under nettgrense (går direkte ut)
ax1.fill_between(timer, 0, np.minimum(pv_sortert, NETT_GRENSE),
                 where=(pv_sortert > 0.1),
                 color='green', alpha=0.2, label='Direkte til nett (≤70 kW)')

# Timer-markeringer
timer_70 = np.sum(pv_ac > NETT_GRENSE)
timer_90 = np.sum(pv_ac > 90)
timer_99 = np.sum(pv_ac >= 99)

if timer_70 > 0:
    ax1.axvline(x=timer_70, color='darkgreen', linestyle=':', alpha=0.5)
    ax1.annotate(f'{timer_70} timer\n>70 kW',
                xy=(timer_70, 35), xytext=(timer_70 + 150, 35),
                fontsize=9, color='darkgreen',
                arrowprops=dict(arrowstyle='->', color='darkgreen', alpha=0.5))

if timer_90 > 0:
    ax1.axvline(x=timer_90, color='darkorange', linestyle=':', alpha=0.5)
    ax1.annotate(f'{timer_90} timer\n>90 kW',
                xy=(timer_90, 50), xytext=(timer_90 + 150, 50),
                fontsize=9, color='darkorange',
                arrowprops=dict(arrowstyle='->', color='darkorange', alpha=0.5))

if timer_99 > 0:
    ax1.axvline(x=timer_99, color='red', linestyle=':', alpha=0.5)
    ax1.annotate(f'{timer_99} timer\n≥99 kW',
                xy=(timer_99, 65), xytext=(timer_99 + 150, 65),
                fontsize=9, color='red',
                arrowprops=dict(arrowstyle='->', color='red', alpha=0.5))

# Beregn kuttet energi
kuttet_nett = np.sum(np.maximum(0, np.minimum(pv_sortert, INV_GRENSE) - NETT_GRENSE))
kuttet_inverter = np.sum(np.maximum(0, pv_sortert - INV_GRENSE))

# Tekstboks med statistikk
stats_text = (
    f'Data: PVGIS med {7}% tap\n'
    f'Årlig produksjon: {np.sum(pv_ac):.0f} kWh\n'
    f'Spesifikk: {np.sum(pv_ac)/PV_KWP:.1f} kWh/kWp\n'
    f'Maks AC: {np.max(pv_ac):.1f} kW\n'
    f'Kuttet >70kW: {kuttet_nett:.0f} kWh/år\n'
    f'Kuttet >100kW: {kuttet_inverter:.0f} kWh/år\n'
    f'Kapasitetsfaktor: {np.sum(pv_ac)/(INV_GRENSE*8760)*100:.1f}%'
)
ax1.text(0.98, 0.97, stats_text,
        transform=ax1.transAxes,
        fontsize=10,
        verticalalignment='top',
        horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))

# Formatting øvre plot
ax1.set_ylabel('AC Effekt [kW]', fontsize=12, fontweight='bold')
ax1.set_title(f'Varighetskurve - PVGIS Timedata\nSnødevegen 122: {PV_KWP:.1f} kWp / {INV_GRENSE} kW inverter / {NETT_GRENSE} kW nettgrense',
             fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3, linestyle='--')
ax1.set_xlim(0, 8760)
ax1.set_ylim(0, max(150, np.max(pv_ac) * 1.1))
ax1.legend(loc='upper right', fontsize=10)

# Sekundær x-akse med prosent
ax1_twin = ax1.twiny()
ax1_twin.set_xlim(0, 100)
ax1_twin.set_xlabel('Prosent av året [%]', fontsize=11)

# NEDRE PLOT - Zoom på topp 1000 timer
top_1000 = min(1000, np.sum(pv_ac > 10))  # Ikke vis timer med ~0 produksjon
ax2.fill_between(timer[:top_1000], 0, pv_sortert[:top_1000], color='gold', alpha=0.3)
ax2.plot(timer[:top_1000], pv_sortert[:top_1000], color='darkorange', linewidth=2)
ax2.axhline(y=INV_GRENSE, color='red', linestyle='-', linewidth=2, alpha=0.8, label='Inverter 100 kW')
ax2.axhline(y=NETT_GRENSE, color='darkgreen', linestyle='-', linewidth=2, alpha=0.8, label='Nett 70 kW')
ax2.fill_between(timer[:top_1000], NETT_GRENSE, np.minimum(pv_sortert[:top_1000], INV_GRENSE),
                 where=(pv_sortert[:top_1000] > NETT_GRENSE),
                 color='orange', alpha=0.3)

ax2.set_xlabel('Timer i året', fontsize=12, fontweight='bold')
ax2.set_ylabel('AC Effekt [kW]', fontsize=11, fontweight='bold')
ax2.set_title(f'Zoom: Topp {top_1000} timer med høyest produksjon', fontsize=12)
ax2.grid(True, alpha=0.3, linestyle='--')
ax2.set_xlim(0, top_1000)
ax2.set_ylim(max(0, pv_sortert[min(top_1000-1, 8759)] - 5), min(110, np.max(pv_ac) * 1.05))
ax2.legend(loc='upper right', fontsize=9)

plt.tight_layout()

# Lagre figur
output_file = '/mnt/c/Users/klaus/klauspython/offgrid2/battery_optimization/varighetskurve_pvgis.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"\n✅ Varighetskurve lagret: {output_file}")

# plt.show()  # Kommentert ut for å unngå timeout

print("\n" + "="*70)
print("✅ ANALYSE FULLFØRT")
print("="*70)