#!/usr/bin/env python3
"""
Batterioptimering med PVSol-produksjonstall
Lokasjon: 58.929644, 5.623052 (Snødevegen 122, Tananger)
System: 138.55 kWp, 100 kW inverter, 70 kW nettbegrensning
PVSol produksjon: 133,017 kWh/år (959.78 kWh/kWp)
"""
import numpy as np
import pandas as pd

print("\n" + "="*70)
print("🔋 BATTERIOPTIMERING MED PVSOL-PRODUKSJONSTALL")
print("="*70)

# Systemparametere fra PVSol
PV_KAPASITET = 138.55  # kWp
INVERTER_GRENSE = 100  # kW
NETT_GRENSE = 70  # kW
ÅRLIG_PRODUKSJON = 133017  # kWh/år fra PVSol

# Økonomiske parametere
RENTE = 0.05
BATTERIETS_LEVETID = 15
VIRKNINGSGRAD = 0.90
DEGRADERING = 0.02

# Lnett-tariffer (NOK/måned) - døgnmaks-basert
EFFEKTTARIFFER = {
    (0, 2): 136, (2, 5): 232, (5, 10): 372, (10, 15): 572,
    (15, 20): 772, (20, 25): 972, (25, 50): 1772,
    (50, 75): 2572, (75, 100): 3372, (100, 200): 5600
}

def generer_pv_profil_fra_pvsol():
    """Generer timeproduksjon basert på PVSol månedlig fordeling"""
    # Månedlig produksjon estimert fra PVSol-graf (side 7)
    månedlig_mwh = {
        1: 1.0,   # Januar - veldig lite
        2: 3.2,   # Februar
        3: 7.5,   # Mars
        4: 14.8,  # April
        5: 20.2,  # Mai - høy produksjon
        6: 21.5,  # Juni - topproduksjon
        7: 19.8,  # Juli
        8: 16.5,  # August
        9: 12.3,  # September
        10: 7.8,  # Oktober
        11: 3.1,  # November
        12: 0.8   # Desember - minimal
    }

    # Skalér til riktig årlig total
    total_estimert = sum(månedlig_mwh.values())
    skaleringsfaktor = ÅRLIG_PRODUKSJON / (total_estimert * 1000)

    pv = np.zeros(8760)
    time = 0

    for måned in range(1, 13):
        dager_i_måned = [31,28,31,30,31,30,31,31,30,31,30,31][måned-1]
        måneds_kwh = månedlig_mwh[måned] * 1000 * skaleringsfaktor

        for dag in range(dager_i_måned):
            for time_i_dag in range(24):
                # Solprofil gjennom dagen
                if 4 <= time_i_dag <= 20:
                    sol_faktor = np.sin((time_i_dag - 4) * np.pi / 16)
                    # Høyere produksjon midt på dagen
                    if 10 <= time_i_dag <= 14:
                        sol_faktor *= 1.2
                    daglig_snitt = måneds_kwh / dager_i_måned
                    pv[time] = daglig_snitt * sol_faktor * 3 / 24  # Juster for riktig total
                    # Begrens til inverter
                    pv[time] = min(pv[time], INVERTER_GRENSE)

                time += 1

    # Verifiser total
    faktisk_total = np.sum(pv)
    print(f"✅ PV-profil generert: {faktisk_total/1000:.1f} MWh/år")
    print(f"   Maks effekt: {np.max(pv):.1f} kW")
    print(f"   Timer > nettgrense (70 kW): {np.sum(pv > NETT_GRENSE)}")

    return pv

def generer_lastprofil():
    """Kommersiell lastprofil basert på PVSol (300 MWh/år)"""
    last = np.zeros(8760)
    for t in range(8760):
        time_på_dagen = t % 24
        ukedag = ((t // 24) % 7) < 5
        måned = min(12, (t // 720) + 1)

        # Grunnlast 25 kW, arbeidstid 50 kW
        if ukedag and 7 <= time_på_dagen <= 17:
            last[t] = 50
        else:
            last[t] = 25

        # Sesongvariasjon
        if måned in [12, 1, 2]:  # Vinter
            last[t] *= 1.3
        elif måned in [6, 7, 8]:  # Sommer
            last[t] *= 1.05

    # Skalér til 300 MWh/år som i PVSol
    last = last * 300000 / np.sum(last)

    return last

def generer_spotpriser():
    """NO2 spotpriser 2023-2025 nivå"""
    priser = np.zeros(8760)
    for t in range(8760):
        måned = min(12, (t // 720) + 1)
        time_på_dagen = t % 24
        ukedag = ((t // 24) % 7) < 5

        # Grunnpriser
        if måned in [6, 7, 8]:  # Sommer
            basis = 0.45
        elif måned in [12, 1, 2]:  # Vinter
            basis = 0.95
        else:
            basis = 0.70

        # Døgnvariasjon
        if ukedag and time_på_dagen in [7, 8, 17, 18, 19]:
            faktor = 1.4  # Rush
        elif ukedag and 9 <= time_på_dagen <= 16:
            faktor = 1.1
        elif 22 <= time_på_dagen or time_på_dagen <= 5:
            faktor = 0.7  # Natt
        else:
            faktor = 0.9

        priser[t] = basis * faktor * np.random.normal(1.0, 0.15)
        priser[t] = max(0.1, priser[t])

    return priser

def simuler_batteri(kapasitet_kwh, effekt_kw, pv, priser, last):
    """Simuler batteridrift med nettbegrensning"""
    n = len(pv)
    soc = np.zeros(n)
    soc[0] = kapasitet_kwh * 0.5

    lading = np.zeros(n)
    utlading = np.zeros(n)
    nett_eksport = np.zeros(n)
    nett_import = np.zeros(n)
    avkapping = np.zeros(n)

    eff = np.sqrt(VIRKNINGSGRAD)

    for t in range(1, n):
        netto = pv[t] - last[t]

        # Sjekk om prisen er høy/lav
        snitt_pris = np.mean(priser[max(0, t-168):t+1])
        er_dyrt = priser[t] > snitt_pris * 1.15
        er_billig = priser[t] < snitt_pris * 0.85

        if netto > 0:  # Overskuddsproduksjon
            if netto > NETT_GRENSE:
                # Må lagre overskudd eller kappe
                overskudd = netto - NETT_GRENSE
                maks_lading = min(effekt_kw, (kapasitet_kwh * 0.9 - soc[t-1]) / eff)
                lading[t] = min(overskudd, maks_lading)
                nett_eksport[t] = NETT_GRENSE
                avkapping[t] = max(0, overskudd - lading[t])
            else:
                # Kan eksportere alt
                nett_eksport[t] = netto
                # Opportunistisk lading hvis billig
                if er_billig and soc[t-1] < kapasitet_kwh * 0.7:
                    tilgjengelig = min(netto * 0.3, effekt_kw)
                    maks_lading = min(tilgjengelig, (kapasitet_kwh * 0.9 - soc[t-1]) / eff)
                    lading[t] = maks_lading
                    nett_eksport[t] = netto - lading[t]

        else:  # Netto forbruk
            underskudd = -netto
            if er_dyrt and soc[t-1] > kapasitet_kwh * 0.2:
                maks_utlading = min(effekt_kw, (soc[t-1] - kapasitet_kwh * 0.1) * eff)
                utlading[t] = min(underskudd, maks_utlading)
                nett_import[t] = underskudd - utlading[t]
            else:
                nett_import[t] = underskudd

        # Oppdater SOC
        soc[t] = soc[t-1] + lading[t] * eff - utlading[t] / eff
        soc[t] = np.clip(soc[t], kapasitet_kwh * 0.1, kapasitet_kwh * 0.9)

    return {
        'lading': lading,
        'utlading': utlading,
        'nett_eksport': nett_eksport,
        'nett_import': nett_import,
        'avkapping': avkapping,
        'soc': soc
    }

def beregn_økonomi(kapasitet_kwh, effekt_kw, sim, priser):
    """Beregn NPV og tilbakebetalingstid"""

    # Investering (inkl. 25% installasjon)
    investering = kapasitet_kwh * 3000 * 1.25

    # Årlige inntekter
    # 1. Arbitrasje
    arbitrasje = np.sum(sim['utlading'] * priser) - np.sum(sim['lading'] * priser)

    # 2. Effektreduksjon (forenklet - anta 20 kW reduksjon)
    # Fra 50 kW til 30 kW flytter ned tarifftrinn
    månedlig_besparelse = 1772 - 972  # Fra 25-50 til 20-25 trinn
    effekt_besparelse = månedlig_besparelse * 12

    # 3. Unngått avkapping
    avkappingsverdi = np.sum(sim['avkapping']) * np.mean(priser) * 0.8

    årlig_inntekt = arbitrasje + effekt_besparelse + avkappingsverdi

    # NPV-beregning
    npv = -investering
    for år in range(BATTERIETS_LEVETID):
        diskontering = (1 + RENTE) ** år
        degradering_faktor = 1 - DEGRADERING * år
        npv += årlig_inntekt * degradering_faktor / diskontering

    tilbakebetaling = investering / årlig_inntekt if årlig_inntekt > 0 else 99

    return npv, årlig_inntekt, tilbakebetaling, avkappingsverdi

# Hovedanalyse
print("\n📊 Genererer PV-profil basert på PVSol...")
pv = generer_pv_profil_fra_pvsol()

print("\n📊 Genererer last- og prisprofiler...")
last = generer_lastprofil()
priser = generer_spotpriser()

# Statistikk
total_pv = np.sum(pv)
kapasitetsfaktor = np.mean(pv) / PV_KAPASITET
timer_over_nett = np.sum(pv > NETT_GRENSE)

print(f"\n📈 Systemanalyse:")
print(f"   • PV total: {total_pv/1000:.1f} MWh/år (mål: 133.0)")
print(f"   • Kapasitetsfaktor: {kapasitetsfaktor:.1%}")
print(f"   • Topp PV-effekt: {np.max(pv):.1f} kW")
print(f"   • Timer > nettgrense (70 kW): {timer_over_nett}")
print(f"   • Last total: {np.sum(last)/1000:.1f} MWh/år")
print(f"   • Snitt spotpris: {np.mean(priser):.3f} NOK/kWh")

# Test batterikonfigurasjoner
print("\n🔍 Tester batterikonfigurasjoner...")
print("\nKapasitet  Effekt  NPV         Inntekt   Tilbake  Avkapping")
print("-" * 65)

beste_npv = -float('inf')
beste_konfig = None

for kapasitet in [30, 50, 75, 100, 125, 150, 200]:
    for effekt in [20, 30, 40, 50, 60, 75]:
        c_rate = effekt / kapasitet
        if 0.3 <= c_rate <= 1.2:
            sim = simuler_batteri(kapasitet, effekt, pv, priser, last)
            npv, inntekt, tilbakebetaling, avk_verdi = beregn_økonomi(kapasitet, effekt, sim, priser)

            avk_unngått = np.sum(sim['avkapping'])

            print(f"{kapasitet:3.0f} kWh  {effekt:2.0f} kW  {npv:10,.0f}  "
                  f"{inntekt:8,.0f}  {tilbakebetaling:6.1f}  {avk_unngått:6.0f} kWh")

            if npv > beste_npv:
                beste_npv = npv
                beste_konfig = (kapasitet, effekt, inntekt, tilbakebetaling)

print("\n" + "="*70)
print("✅ OPTIMAL KONFIGURASJON")
print("="*70)

if beste_konfig:
    kap, eff, innt, tb = beste_konfig

    print(f"\n🔋 Optimalt batteri:")
    print(f"   • Kapasitet: {kap} kWh")
    print(f"   • Effekt: {eff} kW")
    print(f"   • C-rate: {eff/kap:.2f}")

    print(f"\n💰 Økonomi @ 3000 NOK/kWh:")
    print(f"   • NPV: {beste_npv:,.0f} NOK")
    print(f"   • Årlig inntekt: {innt:,.0f} NOK")
    print(f"   • Tilbakebetalingstid: {tb:.1f} år")

    # Break-even analyse
    print(f"\n🎯 Break-even batterikostnad:")
    for faktor in [0.6, 0.8, 1.0, 1.2, 1.4]:
        test_kostnad = 3000 * faktor
        test_inv = kap * test_kostnad * 1.25
        test_npv = -test_inv

        for år in range(BATTERIETS_LEVETID):
            test_npv += innt * (1 - DEGRADERING * år) / ((1 + RENTE) ** år)

        status = "✅" if test_npv > 0 else "❌"
        print(f"   {test_kostnad:.0f} NOK/kWh: {test_npv:>10,.0f} NOK {status}")

print("\n📝 Hovedfunn basert på PVSol:")
print(f"   • System: {PV_KAPASITET} kWp PV, {INVERTER_GRENSE} kW inverter")
print(f"   • Produksjon: 133 MWh/år (959.78 kWh/kWp)")
print(f"   • Nettbegrensning: {NETT_GRENSE} kW skaper avkappingsmulighet")
print(f"   • Hoveddrivere: Effektreduksjon + avkapping + arbitrasje")

print("\n✅ Analyse fullført med PVSol-tall!")