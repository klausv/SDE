#!/usr/bin/env python3
"""
Batterianalyse med RIKTIG forbruksprofil
Kritisk for korrekt effekttariff-beregning!
"""
import numpy as np
import matplotlib.pyplot as plt

print("\n" + "="*70)
print("🔋 BATTERIANALYSE MED KORREKT FORBRUKSPROFIL")
print("="*70)

# System
PV_KWP = 138.55
INV_GRENSE = 100
NETT_GRENSE = 70
ÅRLIG_PROD = 133017  # Fra PVSol

# VIKTIG: SPESIFISER RIKTIG FORBRUK HER!
print("\n⚠️ FORBRUKSPROFIL-ALTERNATIVER:")
print("1. Ingen forbruk (ren eksport)")
print("2. Kontorbygg (høyt dagtid)")
print("3. Industri (konstant høyt)")
print("4. Bolig (høyt morgen/kveld)")
print("5. Egendefinert")

# For nå, test ulike scenarier
FORBRUKSTYPE = "ingen"  # "ingen", "kontor", "industri", "bolig"

def lag_forbruksprofil(type_forbruk, årlig_kwh=0):
    """Generer forbruksprofil basert på type"""
    last = np.zeros(8760)

    if type_forbruk == "ingen":
        # Ingen forbruk - ren eksport
        return last

    elif type_forbruk == "kontor":
        # Kontorbygg - høyt dagtid på hverdager
        for t in range(8760):
            time_dag = t % 24
            ukedag = ((t // 24) % 7) < 5
            mnd = (t // 720)

            if ukedag and 7 <= time_dag <= 17:
                last[t] = 60  # Arbeidstid
            elif ukedag and (6 <= time_dag < 7 or 17 < time_dag <= 19):
                last[t] = 30  # Oppstart/avslutning
            else:
                last[t] = 10  # Standby natt/helg

            # Vintertopp
            if mnd in [11, 0, 1]:
                last[t] *= 1.3

    elif type_forbruk == "industri":
        # Industri - konstant høyt hele døgnet
        for t in range(8760):
            last[t] = 40  # Konstant grunnlast

            # Litt variasjon for produksjon
            time_dag = t % 24
            if 6 <= time_dag <= 22:
                last[t] *= 1.1

    elif type_forbruk == "bolig":
        # Boligområde - høyt morgen og kveld
        for t in range(8760):
            time_dag = t % 24
            mnd = (t // 720)

            if 6 <= time_dag <= 9:
                last[t] = 50  # Morgentopp
            elif 16 <= time_dag <= 22:
                last[t] = 60  # Kveldtopp
            elif 22 <= time_dag or time_dag <= 6:
                last[t] = 20  # Natt
            else:
                last[t] = 30  # Dag

            # Vintertopp (oppvarming)
            if mnd in [11, 0, 1, 2]:
                last[t] *= 1.5

    # Skaler til ønsket årlig forbruk
    if årlig_kwh > 0 and np.sum(last) > 0:
        last = last * (årlig_kwh / np.sum(last))

    return last

def lag_pv():
    """PV-profil basert på PVSol"""
    pv = np.zeros(8760)

    # Månedlig fra PVSol (MWh)
    mnd_mwh = [1.5, 4.0, 9.0, 15.0, 19.5, 20.5, 19.0, 16.0, 12.5, 8.0, 3.5, 1.0]

    time_idx = 0
    for mnd in range(12):
        dager = [31,28,31,30,31,30,31,31,30,31,30,31][mnd]
        mnd_kwh = (mnd_mwh[mnd] / sum(mnd_mwh)) * ÅRLIG_PROD

        for dag in range(dager):
            # Værfaktor
            if mnd in [5, 6]:  # Sommer
                vær = np.random.choice([0.3, 0.7, 1.0, 1.2], p=[0.1, 0.2, 0.5, 0.2])
            else:
                vær = np.random.choice([0.2, 0.5, 0.8, 1.0], p=[0.2, 0.3, 0.3, 0.2])

            dag_kwh = (mnd_kwh / dager) * vær

            # Soltimer og effekt
            if mnd in [5, 6]:  # Juni-juli
                sol_start, sol_slutt = 3, 21
                maks = 90 if vær >= 1.0 else 75
            elif mnd in [11, 0]:  # Des-jan
                sol_start, sol_slutt = 9, 15
                maks = 30
            else:
                sol_start, sol_slutt = 6, 18
                maks = 65

            for time in range(24):
                if sol_start <= time < sol_slutt:
                    pos = (time - sol_start) / (sol_slutt - sol_start)
                    intensitet = np.sin(pos * np.pi)

                    if 0.3 < pos < 0.7:  # Middagsboost
                        intensitet *= 1.3

                    pv[time_idx] = min(intensitet * maks * vær, INV_GRENSE)

                time_idx += 1

    # Sikre noen timer over 70 kW
    timer_over_70 = np.sum(pv > 70)
    if timer_over_70 < 500:
        høye_idx = np.where((pv > 60) & (pv < 70))[0]
        if len(høye_idx) > 0:
            boost_idx = np.random.choice(høye_idx, min(500-timer_over_70, len(høye_idx)), replace=False)
            pv[boost_idx] = np.random.uniform(70, 85, len(boost_idx))

    # Skaler til eksakt produksjon
    pv = pv * (ÅRLIG_PROD / np.sum(pv))

    return pv

def simuler_batteri(kap_kwh, eff_kw, pv, last, pris):
    """Batterisimulering med effektsporing"""
    n = 8760
    soc = np.zeros(n)
    soc[0] = kap_kwh * 0.5

    lading = np.zeros(n)
    utlading = np.zeros(n)
    import_nett = np.zeros(n)
    eksport_nett = np.zeros(n)
    kuttet = np.zeros(n)

    VIRKNINGSGRAD = 0.90

    for t in range(1, n):
        prod = pv[t]
        forb = last[t]
        netto = prod - forb

        # Prislogikk
        if t >= 24:
            snitt = np.mean(pris[t-24:t])
            høy = pris[t] > snitt * 1.2
            lav = pris[t] < snitt * 0.8
        else:
            høy = lav = False

        if prod > NETT_GRENSE:
            # Må lagre eller kutte
            over = prod - NETT_GRENSE
            rom = (kap_kwh * 0.9 - soc[t-1]) / VIRKNINGSGRAD
            lagre = min(eff_kw, rom, over)

            lading[t] = lagre
            kuttet[t] = over - lagre

            # Nettflyt
            rest_prod = prod - lagre - kuttet[t]
            if rest_prod > forb:
                eksport_nett[t] = min(rest_prod - forb, NETT_GRENSE)
            else:
                import_nett[t] = forb - rest_prod

        elif netto > 0:
            # Overskudd under grense
            eksport_nett[t] = netto

            # Opportunistisk lading
            if lav and soc[t-1] < kap_kwh * 0.6:
                rom = (kap_kwh * 0.9 - soc[t-1]) / VIRKNINGSGRAD
                lade = min(eff_kw, rom, 20)
                lading[t] += lade
                import_nett[t] += lade

        else:
            # Underskudd
            behov = -netto

            if soc[t-1] > kap_kwh * 0.2:
                # Bruk batteri
                tilgj = (soc[t-1] - kap_kwh * 0.1) * VIRKNINGSGRAD
                levere = min(eff_kw, tilgj, behov)

                # Prioriter peak shaving over arbitrasje
                time_dag = t % 24
                if (7 <= time_dag <= 9 or 17 <= time_dag <= 19) or høy:
                    utlading[t] = levere
                    import_nett[t] = behov - levere
                else:
                    utlading[t] = levere * 0.5
                    import_nett[t] = behov - levere * 0.5
            else:
                import_nett[t] = behov

        # Oppdater SOC
        soc[t] = soc[t-1] + lading[t] * VIRKNINGSGRAD - utlading[t] / VIRKNINGSGRAD
        soc[t] = np.clip(soc[t], kap_kwh * 0.1, kap_kwh * 0.9)

    return {
        'lading': lading,
        'utlading': utlading,
        'import': import_nett,
        'eksport': eksport_nett,
        'kuttet': kuttet,
        'soc': soc
    }

def beregn_økonomi(sim, pris):
    """Økonomiberegning med effekttariff"""

    # Effekttariff Lnett
    tariffer = {
        (0, 2): 136, (2, 5): 232, (5, 10): 372, (10, 15): 572,
        (15, 20): 772, (20, 25): 972, (25, 50): 1772,
        (50, 75): 2572, (75, 100): 3372, (100, 200): 5600
    }

    def finn_tariff(kw):
        for (min_kw, maks_kw), t in tariffer.items():
            if min_kw <= kw < maks_kw:
                return t
        return 5600

    # Beregn månedlige døgnmaks
    månedsmaks_med = []
    månedsmaks_uten = []

    dag_idx = 0
    for mnd in range(12):
        dager = [31,28,31,30,31,30,31,31,30,31,30,31][mnd]
        mnd_maks_med = 0
        mnd_maks_uten = 0

        for dag in range(dager):
            start = (dag_idx + dag) * 24
            slutt = start + 24

            # Med batteri
            døgn_med = np.max(sim['import'][start:slutt])
            mnd_maks_med = max(mnd_maks_med, døgn_med)

            # Uten batteri (legg tilbake batteribidrag)
            døgn_uten = np.max(sim['import'][start:slutt] + sim['utlading'][start:slutt])
            mnd_maks_uten = max(mnd_maks_uten, døgn_uten)

        månedsmaks_med.append(mnd_maks_med)
        månedsmaks_uten.append(mnd_maks_uten)
        dag_idx += dager

    # Effektkostnad
    effekt_med = sum(finn_tariff(m) for m in månedsmaks_med)
    effekt_uten = sum(finn_tariff(m) for m in månedsmaks_uten)
    effekt_spart = effekt_uten - effekt_med

    # Andre inntekter
    kutting_verdi = np.sum(sim['kuttet']) * np.mean(pris)
    arbitrasje = np.sum(sim['utlading'] * pris) - np.sum(sim['lading'] * pris)

    total = effekt_spart + kutting_verdi + arbitrasje

    return {
        'effekt_spart': effekt_spart,
        'kutting_verdi': kutting_verdi,
        'arbitrasje': arbitrasje,
        'total': total,
        'månedsmaks_med': månedsmaks_med,
        'månedsmaks_uten': månedsmaks_uten
    }

# Test ulike forbruksscenarier
print("\n📊 Tester ulike forbruksscenarier...")

# Generer felles data
pv = lag_pv()
pris = np.random.normal(0.5, 0.2, 8760)
pris = np.clip(pris, 0.1, 2.0)

print(f"\nPV-produksjon: {np.sum(pv)/1000:.1f} MWh/år")
print(f"Timer > 70 kW: {np.sum(pv > 70)}")

scenarier = [
    ("Ingen forbruk (ren eksport)", "ingen", 0),
    ("Kontorbygg (200 MWh/år)", "kontor", 200000),
    ("Industri (500 MWh/år)", "industri", 500000),
    ("Boligområde (150 MWh/år)", "bolig", 150000)
]

print("\n" + "="*70)
print("RESULTATER FOR ULIKE FORBRUKSPROFILER")
print("="*70)

for navn, type_forb, årlig in scenarier:
    print(f"\n🏢 {navn}:")

    last = lag_forbruksprofil(type_forb, årlig)
    print(f"   Årlig forbruk: {np.sum(last)/1000:.1f} MWh")
    print(f"   Maks last: {np.max(last):.1f} kW")

    # Test 75 kWh / 50 kW batteri
    kap = 75
    eff = 50

    sim = simuler_batteri(kap, eff, pv, last, pris)
    øko = beregn_økonomi(sim, pris)

    print(f"\n   Med {kap} kWh / {eff} kW batteri:")
    print(f"   • Effekttariff spart: {øko['effekt_spart']:,.0f} kr/år")
    print(f"   • Unngått kutting: {øko['kutting_verdi']:,.0f} kr/år")
    print(f"   • Arbitrasje: {øko['arbitrasje']:,.0f} kr/år")
    print(f"   • TOTAL: {øko['total']:,.0f} kr/år")

    if øko['effekt_spart'] > 0:
        print(f"   • Effektreduksjon: {np.mean([u-m for u,m in zip(øko['månedsmaks_uten'], øko['månedsmaks_med'])]):.1f} kW snitt")

    # NPV
    inv = kap * 3000 * 1.25
    npv = -inv
    for år in range(15):
        npv += øko['total'] * (1 - 0.02*år) / (1.05**år)

    print(f"   • NPV @ 3000 kr/kWh: {npv:,.0f} kr")

    if øko['total'] > 0:
        be = inv / øko['total']
        print(f"   • Tilbakebetaling: {be:.1f} år")

print("\n" + "="*70)
print("📝 KONKLUSJON:")
print("="*70)
print("\n⚠️ Forbruksprofilen har STOR betydning for batterilønnsomhet!")
print("   • Ingen forbruk = kun unngått kutting")
print("   • Høyt dagtidsforbruk = bedre selvforbruk")
print("   • Høyt kveld/natt = bedre effekttariff-reduksjon")
print("\n💡 Vennligst spesifiser faktisk forbruksprofil for nøyaktig analyse!")

print("\n✅ Analyse fullført!")