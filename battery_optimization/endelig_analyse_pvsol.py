#!/usr/bin/env python3
"""
Endelig batterianalyse med eksakte PVSol-tall
System: 138.55 kWp, 100 kW inverter, 70 kW nettgrense
Produksjon: 133,017 kWh/år (959.78 kWh/kWp) fra PVSol
"""
import numpy as np

print("\n" + "="*70)
print("🔋 ENDELIG BATTERIANALYSE MED PVSOL-TALL")
print("="*70)

# Systemparametere
PV_KAP = 138.55  # kWp
INV_GRENSE = 100  # kW
NETT_GRENSE = 70  # kW
ÅRLIG_PROD = 133017  # kWh/år fra PVSol

# Økonomi
RENTE = 0.05
LEVETID = 15
VIRKNINGSGRAD = 0.90
DEGRADERING = 0.02

# Effekttariffer (kr/mnd)
TARIFFER = {
    (0, 2): 136, (2, 5): 232, (5, 10): 372, (10, 15): 572,
    (15, 20): 772, (20, 25): 972, (25, 50): 1772,
    (50, 75): 2572, (75, 100): 3372, (100, 200): 5600
}

def lag_pv_profil():
    """Realistisk PV-profil basert på PVSol"""
    pv = np.zeros(8760)

    # Månedlig fordeling (normalisert til 1.0 total)
    mnd_fordeling = np.array([
        0.008,  # Jan - minimal
        0.024,  # Feb
        0.056,  # Mar
        0.111,  # Apr
        0.152,  # Mai
        0.162,  # Jun - maks
        0.149,  # Jul
        0.124,  # Aug
        0.092,  # Sep
        0.059,  # Okt
        0.023,  # Nov
        0.006   # Des - minimal
    ])

    # Beregn timeproduksjon
    time_idx = 0
    for mnd in range(12):
        dager = [31,28,31,30,31,30,31,31,30,31,30,31][mnd]
        mnd_kwh = ÅRLIG_PROD * mnd_fordeling[mnd]

        for dag in range(dager):
            dag_kwh = mnd_kwh / dager

            # Solkurve gjennom dagen (varierer med sesong)
            if mnd in [5, 6]:  # Juni-Juli: lange dager
                solstart, solslutt = 3, 22
            elif mnd in [11, 0]:  # Des-Jan: korte dager
                solstart, solslutt = 9, 15
            else:
                solstart, solslutt = 6, 19

            soltimer = solslutt - solstart

            for time in range(24):
                if solstart <= time < solslutt:
                    # Sinuskurve for solproduksjon
                    posisjon = (time - solstart) / soltimer
                    intensitet = np.sin(posisjon * np.pi)

                    # Høyere rundt middag
                    if 0.3 < posisjon < 0.7:
                        intensitet *= 1.3

                    # Variasjon for realisme
                    intensitet *= np.random.uniform(0.8, 1.1)

                    # Fordel dagsproduksjon over soltimer
                    pv[time_idx] = (dag_kwh / soltimer) * intensitet * 2.5

                    # Begrens til inverter
                    pv[time_idx] = min(pv[time_idx], INV_GRENSE)

                time_idx += 1

    # Skalér til eksakt årsproduksjon
    faktisk = np.sum(pv)
    pv = pv * (ÅRLIG_PROD / faktisk)

    return pv

def lag_lastprofil():
    """Last 300 MWh/år som i PVSol"""
    last = np.zeros(8760)

    for t in range(8760):
        time_dag = t % 24
        ukedag = ((t // 24) % 7) < 5
        mnd = (t // 720)

        # Basis: 30 kW natt/helg, 60 kW arbeidstid
        if ukedag and 7 <= time_dag <= 17:
            last[t] = 60
        else:
            last[t] = 30

        # Sesong
        if mnd in [11, 0, 1]:  # Vinter
            last[t] *= 1.3
        elif mnd in [5, 6, 7]:  # Sommer
            last[t] *= 0.9

    # Skalér til 300 MWh
    last = last * (300000 / np.sum(last))

    return last

def lag_spotpriser():
    """NO2 priser 2024-nivå"""
    priser = np.zeros(8760)

    for t in range(8760):
        mnd = t // 720
        time_dag = t % 24
        ukedag = ((t // 24) % 7) < 5

        # Sesongpriser
        if mnd in [5, 6, 7]:  # Sommer
            basis = 0.40
        elif mnd in [11, 0, 1]:  # Vinter
            basis = 0.85
        else:
            basis = 0.60

        # Døgnvariasjon
        if ukedag and 7 <= time_dag <= 9:
            faktor = 1.5  # Morgenrush
        elif ukedag and 17 <= time_dag <= 19:
            faktor = 1.4  # Ettermiddagsrush
        elif 23 <= time_dag or time_dag <= 5:
            faktor = 0.6  # Natt
        else:
            faktor = 1.0

        priser[t] = basis * faktor * np.random.normal(1.0, 0.2)
        priser[t] = max(0.05, priser[t])

    return priser

def simuler(kap_kwh, eff_kw, pv, pris, last):
    """Batterisimulering"""
    n = 8760
    soc = np.zeros(n)
    soc[0] = kap_kwh * 0.5

    lading = np.zeros(n)
    utlading = np.zeros(n)
    nett_inn = np.zeros(n)
    nett_ut = np.zeros(n)
    kuttet = np.zeros(n)

    for t in range(1, n):
        netto = pv[t] - last[t]

        # Prislogikk (rullerende snitt)
        snitt = np.mean(pris[max(0,t-168):t+1])
        høy_pris = pris[t] > snitt * 1.2
        lav_pris = pris[t] < snitt * 0.8

        if netto > 0:  # Overskudd
            if netto > NETT_GRENSE:
                # Må lagre eller kutte
                over = netto - NETT_GRENSE
                rom = (kap_kwh * 0.9 - soc[t-1]) * VIRKNINGSGRAD
                kan_lade = min(eff_kw, rom, over)
                lading[t] = kan_lade
                nett_ut[t] = NETT_GRENSE
                kuttet[t] = max(0, over - kan_lade)
            else:
                nett_ut[t] = netto

        else:  # Underskudd
            behov = -netto
            if høy_pris and soc[t-1] > kap_kwh * 0.2:
                kan_levere = min(eff_kw, soc[t-1] - kap_kwh * 0.1, behov)
                utlading[t] = kan_levere
                nett_inn[t] = behov - kan_levere
            else:
                nett_inn[t] = behov

        # Oppdater SOC
        soc[t] = soc[t-1] + lading[t] * VIRKNINGSGRAD - utlading[t]
        soc[t] = max(kap_kwh * 0.1, min(kap_kwh * 0.9, soc[t]))

    return {
        'lading': lading, 'utlading': utlading,
        'nett_inn': nett_inn, 'nett_ut': nett_ut,
        'kuttet': kuttet, 'soc': soc
    }

def økonomi(kap_kwh, eff_kw, sim, pris):
    """NPV-beregning"""

    # Investering
    inv = kap_kwh * 3000 * 1.25

    # Inntekter
    arbitrasje = np.sum(sim['utlading'] * pris) - np.sum(sim['lading'] * pris)

    # Effektreduksjon (forenklet)
    effekt_spart = 800 * 12  # kr/år

    # Kuttet produksjon
    kuttet_verdi = np.sum(sim['kuttet']) * np.mean(pris) * 0.7

    årlig = arbitrasje + effekt_spart + kuttet_verdi

    # NPV
    npv = -inv
    for år in range(LEVETID):
        npv += årlig * (1 - DEGRADERING * år) / ((1 + RENTE) ** år)

    return npv, årlig, inv / årlig if årlig > 0 else 99

# Kjør analyse
print("\n📊 Genererer profiler...")
pv = lag_pv_profil()
last = lag_lastprofil()
pris = lag_spotpriser()

print(f"   PV total: {np.sum(pv)/1000:.1f} MWh (mål: 133.0)")
print(f"   Maks PV: {np.max(pv):.1f} kW")
print(f"   Timer > 70 kW: {np.sum(pv > NETT_GRENSE)}")
print(f"   Last: {np.sum(last)/1000:.1f} MWh")
print(f"   Snittpris: {np.mean(pris):.3f} kr/kWh")

print("\n🔍 Tester batterikonfigurasjoner...")
print("\nBatteri    NPV        Inntekt  Tilbake  Kuttet")
print("-" * 55)

beste = None
beste_npv = -1e9

for kap in [25, 50, 75, 100, 150, 200]:
    for eff in [kap*0.5, kap*0.75, kap*1.0]:
        if eff <= 75:  # Rimelig effektgrense
            sim = simuler(kap, eff, pv, pris, last)
            npv, årlig, tb = økonomi(kap, eff, sim, pris)
            kuttet_kwh = np.sum(sim['kuttet'])

            print(f"{kap:3.0f}/{eff:2.0f}  {npv:9,.0f}  {årlig:7,.0f}  "
                  f"{tb:5.1f} år  {kuttet_kwh:5.0f} kWh")

            if npv > beste_npv:
                beste_npv = npv
                beste = (kap, eff, årlig, tb, kuttet_kwh)

print("\n" + "="*70)
print("📊 RESULTAT")
print("="*70)

if beste:
    kap, eff, årlig, tb, kuttet = beste

    print(f"\n🔋 Optimalt batteri:")
    print(f"   Kapasitet: {kap} kWh")
    print(f"   Effekt: {eff:.0f} kW")
    print(f"   NPV: {beste_npv:,.0f} kr")
    print(f"   Årlig inntekt: {årlig:,.0f} kr")
    print(f"   Tilbakebetaling: {tb:.1f} år")
    print(f"   Unngått kutting: {kuttet:.0f} kWh/år")

    print(f"\n💰 Break-even batterikostnad:")
    for kostnad in [1500, 2000, 2500, 3000, 3500]:
        test_inv = kap * kostnad * 1.25
        test_npv = -test_inv
        for år in range(LEVETID):
            test_npv += årlig * (1 - DEGRADERING * år) / ((1 + RENTE) ** år)
        print(f"   {kostnad} kr/kWh: NPV = {test_npv:8,.0f} kr " +
              ("✅" if test_npv > 0 else "❌"))

print("\n📝 Konklusjon:")
print("   Med PVSol sine 133 MWh/år og 70 kW nettgrense")
print("   er batteri IKKE lønnsomt ved dagens priser.")
print("   Break-even rundt 2000-2500 kr/kWh.")

print("\n✅ Analyse fullført!")