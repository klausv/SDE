#!/usr/bin/env python3
"""
Analyse med RIKTIGE tap fra PVSol (ikke PVGIS-sjablonger)
PVSol viser 959.78 kWh/kWp med Ares nøyaktige modellering
Dette betyr REELL produksjon, ikke teoretisk
"""
import numpy as np

print("\n" + "="*70)
print("🔋 BATTERIANALYSE MED PVSOL REELLE TAP")
print("="*70)

# PVSol viser FAKTISK produksjon med alle tap inkludert
SYSTEM_KWP = 138.55
ÅRLIG_AC = 133017  # kWh/år ETTER alle tap
SPESIFIKK = 959.78  # kWh/kWp FAKTISK

print("\n📊 PVSol vs PVGIS tap:")
print("   PVGIS: 826 kWh/kWp (sjablongtap 14%)")
print("   PVSol: 960 kWh/kWp (reelle tap, Ares erfaring)")
print("   Forskjell: PVSol gir 16% HØYERE produksjon")

# Fra PVSol energibalanse (side 8):
print("\n🔍 PVSol detaljerte tap:")
print("   • Forurensning: -2.25%")
print("   • Temperatur: -0.21%")
print("   • Mismatch: -0.53%")
print("   • DC/AC konvertering: -1.78%")
print("   • Kabler: -0.70%")
print("   • TOTALT: ~7% reelle tap (ikke 14% sjablong)")

# Med 960 kWh/kWp betyr det HØYERE toppeffekt
print("\n⚡ Konsekvens for toppeffekt:")
print("   Med bedre virkningsgrad får vi høyere toppeffekt")
print("   Estimert maks AC: 90-100 kW (ikke 80 kW)")
print("   Timer > 70 kW: ~1200-1500 (ikke 600)")

def generer_pvsol_optimert_pv():
    """PV med PVSols lave tap og høye virkningsgrad"""
    pv = np.zeros(8760)

    # Månedlig fra PVSol (side 7 graf)
    månedlig = {
        1: 1.5, 2: 4.0, 3: 9.0, 4: 15.0, 5: 19.5,
        6: 20.5, 7: 19.0, 8: 16.0, 9: 12.5,
        10: 8.0, 11: 3.5, 12: 1.0
    }

    total_mnd = sum(månedlig.values())
    skaler = ÅRLIG_AC / (total_mnd * 1000)

    time_idx = 0
    for mnd in range(1, 13):
        dager = [31,28,31,30,31,30,31,31,30,31,30,31][mnd-1]
        mnd_kwh = månedlig[mnd] * 1000 * skaler

        for dag in range(dager):
            # Værfaktor
            vær = np.random.choice([0.3, 0.6, 0.9, 1.0, 1.1],
                                  p=[0.1, 0.2, 0.3, 0.3, 0.1])
            dag_kwh = (mnd_kwh / dager) * vær

            # Soltimer
            if mnd in [6, 7]:  # Sommer
                sol_timer = range(4, 21)
                topp_effekt = 95 if vær >= 1.0 else 85
            elif mnd in [12, 1]:  # Vinter
                sol_timer = range(9, 15)
                topp_effekt = 60
            else:
                sol_timer = range(6, 18)
                topp_effekt = 80 if vær >= 0.9 else 70

            for time in range(24):
                if time in sol_timer:
                    pos = (time - sol_timer[0]) / len(sol_timer)
                    intensitet = np.sin(pos * np.pi)

                    # Middag boost
                    if 0.3 < pos < 0.7:
                        intensitet *= 1.3

                    # MED LAVERE TAP får vi høyere effekt!
                    if mnd in [5, 6, 7] and 10 <= time <= 14 and vær >= 1.0:
                        # Sommerdager KAN nå 95-100 kW
                        pv[time_idx] = min(intensitet * topp_effekt * 1.2, 100)
                    else:
                        pv[time_idx] = intensitet * topp_effekt

                    # Juster for total
                    pv[time_idx] *= (dag_kwh / (len(sol_timer) * 0.6))

                time_idx += 1

    # Skalér eksakt
    pv = pv * (ÅRLIG_AC / np.sum(pv))
    return pv

def simuler_med_kutting(kap_kwh, eff_kw, pv, pris, last):
    """Batteri med REELL kutting pga høyere toppeffekt"""
    n = 8760
    soc = np.zeros(n)
    soc[0] = kap_kwh * 0.5

    lading = np.zeros(n)
    utlading = np.zeros(n)
    kuttet = np.zeros(n)

    NETT_GRENSE = 70
    eff_rt = 0.95  # Høy virkningsgrad moderne batteri

    for t in range(1, n):
        netto = pv[t] - last[t]

        # Prisanalyse
        if t > 24:
            snitt = np.mean(pris[t-24:t])
            høy = pris[t] > snitt * 1.3
            lav = pris[t] < snitt * 0.7
        else:
            høy = lav = False

        if pv[t] > NETT_GRENSE:  # KUTTING!
            overskudd = pv[t] - NETT_GRENSE
            rom = (kap_kwh * 0.9 - soc[t-1]) / eff_rt
            kan_lagre = min(eff_kw, rom, overskudd)
            lading[t] = kan_lagre
            kuttet[t] = overskudd - kan_lagre

        elif netto > 0:  # Overskudd under grense
            if lav and soc[t-1] < kap_kwh * 0.7:
                # Opportunistisk lading
                kan_lade = min(eff_kw, (kap_kwh * 0.9 - soc[t-1]) / eff_rt, netto * 0.5)
                lading[t] = kan_lade

        else:  # Underskudd
            if høy and soc[t-1] > kap_kwh * 0.2:
                behov = -netto
                kan_levere = min(eff_kw, (soc[t-1] - kap_kwh * 0.1) * eff_rt, behov)
                utlading[t] = kan_levere

        # Oppdater SOC
        soc[t] = soc[t-1] + lading[t] * eff_rt - utlading[t] / eff_rt
        soc[t] = np.clip(soc[t], kap_kwh * 0.1, kap_kwh * 0.9)

    return {'lading': lading, 'utlading': utlading, 'kuttet': kuttet}

def økonomi_analyse(kap_kwh, eff_kw, sim, pris):
    """Økonomi med alle inntektskilder"""

    # Arbitrasje
    arbitrasje = np.sum(sim['utlading'] * pris) - np.sum(sim['lading'] * pris)

    # Effektreduksjon (20 kW reduksjon døgnmaks)
    effekt_spart = 800 * 12  # månedlig saving * 12

    # Unngått kutting - VIKTIG VERDI!
    kuttet_kwh = np.sum(sim['kuttet'])
    kuttet_verdi = kuttet_kwh * np.mean(pris)

    årlig = arbitrasje + effekt_spart + kuttet_verdi

    # NPV over 15 år
    inv = kap_kwh * 3000 * 1.25  # Batterikost + installasjon
    npv = -inv
    for år in range(15):
        npv += årlig * (1 - 0.02 * år) / (1.05 ** år)

    return npv, årlig, kuttet_kwh

# Generer data
print("\n📊 Genererer PV med riktige tap...")
pv = generer_pvsol_optimert_pv()
last = np.ones(8760) * 34.25  # 300 MWh/år jevnt fordelt

# NO2 priser
pris = np.zeros(8760)
for t in range(8760):
    mnd = (t // 720) + 1
    if mnd in [6,7,8]:
        pris[t] = np.random.normal(0.40, 0.15)
    elif mnd in [12,1,2]:
        pris[t] = np.random.normal(0.75, 0.25)
    else:
        pris[t] = np.random.normal(0.55, 0.20)
    pris[t] = max(0.05, min(2.0, pris[t]))

# Analyse
print(f"\n📈 Systemanalyse med riktige tap:")
print(f"   PV total: {np.sum(pv)/1000:.1f} MWh/år")
print(f"   Maks PV: {np.max(pv):.1f} kW")
print(f"   Timer > 70 kW: {np.sum(pv > 70)}")
print(f"   Timer > 80 kW: {np.sum(pv > 80)}")
print(f"   Timer > 90 kW: {np.sum(pv > 90)}")
print(f"   Potensiell kutting: {np.sum(np.maximum(0, pv - 70))/1000:.1f} MWh/år")

print("\n🔋 Batterikonfigurasjoner:")
print("\nKapasitet  Effekt   NPV        Årlig    Kuttet   Break-even")
print("-" * 70)

beste = None
for kap in [30, 50, 75, 100, 150]:
    for c_rate in [0.5, 0.75, 1.0]:
        eff = kap * c_rate
        if eff <= 75:
            sim = simuler_med_kutting(kap, eff, pv, pris, last)
            npv, årlig, kuttet = økonomi_analyse(kap, eff, sim, pris)

            # Beregn break-even
            for be_kost in range(2000, 6000, 100):
                test_inv = kap * be_kost * 1.25
                test_npv = -test_inv
                for år in range(15):
                    test_npv += årlig * (1 - 0.02 * år) / (1.05 ** år)
                if test_npv > 0:
                    break_even = be_kost
                else:
                    break

            print(f"{kap:3.0f} kWh  {eff:2.0f} kW  {npv:8,.0f}  {årlig:7,.0f}  "
                  f"{kuttet:5.0f} kWh  {break_even:4.0f} kr/kWh")

            if beste is None or npv > beste[2]:
                beste = (kap, eff, npv, årlig, kuttet, break_even)

if beste:
    kap, eff, npv, årlig, kuttet, be = beste
    print("\n" + "="*70)
    print("✅ OPTIMALT MED RIKTIGE TAP:")
    print(f"   Batteri: {kap} kWh / {eff:.0f} kW")
    print(f"   NPV @ 3000 kr/kWh: {npv:,.0f} kr")
    print(f"   Årlig inntekt: {årlig:,.0f} kr")
    print(f"   Unngått kutting: {kuttet:.0f} kWh/år")
    print(f"   Break-even: {be} kr/kWh")

    print("\n💰 Ved markedspris 5000 kr/kWh:")
    marked_inv = kap * 5000 * 1.25
    marked_npv = -marked_inv
    for år in range(15):
        marked_npv += årlig * (1 - 0.02 * år) / (1.05 ** år)
    print(f"   NPV: {marked_npv:,.0f} kr")
    print(f"   Status: {'Fortsatt ulønnsomt' if marked_npv < 0 else 'Lønnsomt'}")

print("\n✅ Analyse fullført!")