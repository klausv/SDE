#!/usr/bin/env python3
"""
Final inntektsanalyse med realistiske tall
Basert på PVSol: 133 MWh/år, topper opp til 95 kW
"""
import numpy as np
import matplotlib.pyplot as plt

print("\n" + "="*70)
print("💰 INNTEKTSANALYSE MED REALISTISK PRODUKSJON")
print("="*70)

# System
PV_KWP = 138.55
INV_GRENSE = 100
NETT_GRENSE = 70
ÅRLIG_PROD = 133017  # Fra PVSol
ÅRLIG_LAST = 300000

# Økonomi
VIRKNINGSGRAD = 0.90
RENTE = 0.05
LEVETID = 15

def finn_effekttariff(kw):
    """Lnett effekttariff"""
    if kw <= 2: return 136
    elif kw <= 5: return 232
    elif kw <= 10: return 372
    elif kw <= 15: return 572
    elif kw <= 20: return 772
    elif kw <= 25: return 972
    elif kw <= 50: return 1772
    elif kw <= 75: return 2572
    elif kw <= 100: return 3372
    else: return 5600

def lag_realistisk_pv():
    """PV med realistiske topper basert på PVSol"""
    pv = np.zeros(8760)

    # Månedlig (MWh) fra PVSol
    mnd_mwh = [1.5, 4.0, 9.0, 15.0, 19.5, 20.5, 19.0, 16.0, 12.5, 8.0, 3.5, 1.0]

    time_idx = 0
    for mnd in range(12):
        dager = [31,28,31,30,31,30,31,31,30,31,30,31][mnd]
        mnd_kwh = (mnd_mwh[mnd] / sum(mnd_mwh)) * ÅRLIG_PROD

        for dag in range(dager):
            # Værfaktor varierer
            if mnd in [5, 6]:  # Juni-juli
                vær = np.random.choice([0.3, 0.6, 0.9, 1.1, 1.2],
                                      p=[0.05, 0.15, 0.40, 0.30, 0.10])
            elif mnd in [11, 0]:  # Des-jan
                vær = np.random.choice([0.1, 0.3, 0.5, 0.7],
                                      p=[0.3, 0.4, 0.2, 0.1])
            else:
                vær = np.random.choice([0.2, 0.5, 0.8, 1.0, 1.1],
                                      p=[0.1, 0.2, 0.35, 0.25, 0.1])

            (mnd_kwh / dager) * vær

            # Soltimer og maks effekt
            if mnd in [5, 6]:  # Juni-juli kan nå høye verdier
                sol_start, sol_slutt = 3, 21
                if vær >= 1.1:  # Perfekte dager
                    maks_dag = np.random.uniform(85, 95)
                elif vær >= 0.9:
                    maks_dag = np.random.uniform(75, 85)
                else:
                    maks_dag = np.random.uniform(50, 70)
            elif mnd in [4, 7]:  # Mai, august
                sol_start, sol_slutt = 4, 20
                maks_dag = np.random.uniform(60, 80) if vær > 0.8 else np.random.uniform(40, 60)
            elif mnd in [3, 8]:  # April, september
                sol_start, sol_slutt = 5, 19
                maks_dag = np.random.uniform(50, 70) if vær > 0.8 else np.random.uniform(30, 50)
            elif mnd in [11, 0]:  # Des-jan
                sol_start, sol_slutt = 9, 15
                maks_dag = np.random.uniform(15, 30)
            else:
                sol_start, sol_slutt = 6, 17
                maks_dag = np.random.uniform(40, 60)

            for time in range(24):
                if sol_start <= time < sol_slutt:
                    pos = (time - sol_start) / (sol_slutt - sol_start)
                    intensitet = np.sin(pos * np.pi)

                    # Middagsboost
                    if 0.3 < pos < 0.7:
                        intensitet *= 1.3

                    # Spesielle sommerdager med høy produksjon
                    if mnd in [5, 6] and 10 <= time <= 14 and vær >= 1.0:
                        intensitet *= 1.15

                    pv[time_idx] = min(intensitet * maks_dag, INV_GRENSE)

                time_idx += 1

    # Juster til eksakt årsproduksjon
    pv = pv * (ÅRLIG_PROD / np.sum(pv))

    # Sikre at vi har noen timer med høy produksjon (realistisk fra PVSol)
    # PVSol viser ~600-1000 timer over 70 kW for dette systemet
    timer_over_70_mål = 800
    timer_over_70_nå = np.sum(pv > 70)

    if timer_over_70_nå < timer_over_70_mål:
        # Boost de høyeste timene
        kandidater = np.where((pv > 60) & (pv < 70))[0]
        if len(kandidater) > 0:
            for _ in range(min(timer_over_70_mål - timer_over_70_nå, len(kandidater))):
                idx = np.random.choice(kandidater)
                pv[idx] = np.random.uniform(70, 95)
                kandidater = kandidater[kandidater != idx]  # Fjern brukt indeks
                if len(kandidater) == 0:
                    break

    # Re-skalér
    pv = pv * (ÅRLIG_PROD / np.sum(pv))

    return pv

def lag_last():
    """Kommersiell last 300 MWh/år"""
    last = np.zeros(8760)

    for t in range(8760):
        time_dag = t % 24
        ukedag = ((t // 24) % 7) < 5
        mnd = (t // 720)

        # Grunnlast
        if ukedag and 7 <= time_dag <= 17:
            last[t] = 55
        elif ukedag and (6 <= time_dag < 7 or 17 < time_dag <= 20):
            last[t] = 40
        else:
            last[t] = 25

        # Sesong
        if mnd in [11, 0, 1]:  # Vinter
            last[t] *= 1.25
        elif mnd in [5, 6, 7]:  # Sommer
            last[t] *= 0.9

        # Variasjon
        last[t] *= np.random.uniform(0.9, 1.1)

    last = last * (ÅRLIG_LAST / np.sum(last))
    return last

def lag_spotpriser():
    """NO2 spotpriser 2024-nivå"""
    pris = np.zeros(8760)

    for t in range(8760):
        mnd = t // 720
        time_dag = t % 24
        ukedag = ((t // 24) % 7) < 5

        # Sesongpris
        if mnd in [5, 6, 7]:  # Sommer
            basis = 0.35
        elif mnd in [11, 0, 1]:  # Vinter
            basis = 0.75
        else:
            basis = 0.55

        # Døgnvariasjon
        if ukedag:
            if 7 <= time_dag <= 9:
                faktor = 1.5
            elif 17 <= time_dag <= 19:
                faktor = 1.4
            elif 22 <= time_dag or time_dag <= 5:
                faktor = 0.6
            else:
                faktor = 1.0
        else:
            faktor = 0.8

        pris[t] = basis * faktor * np.random.normal(1.0, 0.2)
        pris[t] = max(0.05, min(2.0, pris[t]))

    return pris

def simuler_batteri(kap_kwh, eff_kw, pv, last, pris):
    """Detaljert simulering med inntektssporing"""
    n = 8760
    soc = np.zeros(n)
    soc[0] = kap_kwh * 0.5

    # Flyt
    lading = np.zeros(n)
    utlading = np.zeros(n)
    import_nett = np.zeros(n)
    eksport_nett = np.zeros(n)
    kuttet = np.zeros(n)

    # Inntektssporing
    kutting_lagret = np.zeros(n)  # kWh som ellers ville blitt kuttet
    arbitrasje_lad = np.zeros(n)  # Lading ved lav pris
    arbitrasje_utlad = np.zeros(n)  # Utlading ved høy pris
    effekt_reduksjon = np.zeros(n)  # Peak shaving

    for t in range(1, n):
        prod = pv[t]
        forb = last[t]
        netto = prod - forb

        # Prisanalyse
        if t >= 24:
            snitt = np.mean(pris[t-24:t])
            høy = pris[t] > snitt * 1.2
            lav = pris[t] < snitt * 0.8
        else:
            høy = lav = False

        # SCENARIO 1: Produksjon over nettgrense
        if prod > NETT_GRENSE:
            over = prod - NETT_GRENSE
            rom = (kap_kwh * 0.9 - soc[t-1]) / VIRKNINGSGRAD
            lagre = min(eff_kw, rom, over)

            lading[t] = lagre
            kutting_lagret[t] = lagre  # Dette ville blitt kuttet
            kuttet[t] = max(0, over - lagre)

            # Nettflyt
            if netto - lagre > 0:
                eksport_nett[t] = min(NETT_GRENSE, netto - lagre)
            else:
                import_nett[t] = -(netto - lagre)

        # SCENARIO 2: Overskudd under nettgrense
        elif netto > 0:
            eksport_nett[t] = netto

            # Opportunistisk lading
            if lav and soc[t-1] < kap_kwh * 0.6:
                rom = (kap_kwh * 0.9 - soc[t-1]) / VIRKNINGSGRAD
                lade = min(eff_kw, rom, 20)
                lading[t] += lade
                arbitrasje_lad[t] = lade
                import_nett[t] += lade

        # SCENARIO 3: Underskudd
        else:
            behov = -netto

            if soc[t-1] > kap_kwh * 0.25:
                tilgj = (soc[t-1] - kap_kwh * 0.1) * VIRKNINGSGRAD
                levere = min(eff_kw, tilgj, behov * 0.8)

                if høy:
                    # Prioritér arbitrasje ved høy pris
                    utlading[t] = levere
                    arbitrasje_utlad[t] = levere * 0.6
                    effekt_reduksjon[t] = levere * 0.4
                else:
                    # Peak shaving
                    time_dag = t % 24
                    if 7 <= time_dag <= 19:
                        utlading[t] = levere * 0.7
                        effekt_reduksjon[t] = levere * 0.7

                import_nett[t] = behov - utlading[t]
            else:
                import_nett[t] = behov

        # Oppdater SOC
        soc[t] = soc[t-1] + lading[t] * VIRKNINGSGRAD - utlading[t] / VIRKNINGSGRAD
        soc[t] = np.clip(soc[t], kap_kwh * 0.1, kap_kwh * 0.9)

    # Beregn inntekter

    # 1. Unngått kutting
    kutting_verdi = np.sum(kutting_lagret) * np.mean(pris)

    # 2. Arbitrasje
    arb_kostnad = np.sum(arbitrasje_lad * pris)
    arb_inntekt = np.sum(arbitrasje_utlad * pris)
    arb_netto = arb_inntekt - arb_kostnad

    # 3. Effekttariff
    månedsmaks_uten = []
    månedsmaks_med = []

    dag_idx = 0
    for mnd in range(12):
        dager = [31,28,31,30,31,30,31,31,30,31,30,31][mnd]
        mnd_maks_uten = 0
        mnd_maks_med = 0

        for dag in range(dager):
            start = (dag_idx + dag) * 24
            slutt = start + 24

            # Uten batteri
            import_uten = import_nett[start:slutt] + effekt_reduksjon[start:slutt]
            mnd_maks_uten = max(mnd_maks_uten, np.max(import_uten))

            # Med batteri
            mnd_maks_med = max(mnd_maks_med, np.max(import_nett[start:slutt]))

        månedsmaks_uten.append(mnd_maks_uten)
        månedsmaks_med.append(mnd_maks_med)
        dag_idx += dager

    effekt_uten = sum(finn_effekttariff(m) for m in månedsmaks_uten)
    effekt_med = sum(finn_effekttariff(m) for m in månedsmaks_med)
    effekt_spart = effekt_uten - effekt_med

    # 4. Økt verdi (tidsforskyvning)
    tidsforskyvning = np.sum(utlading) * np.std(pris) * 0.3

    total = kutting_verdi + arb_netto + effekt_spart + tidsforskyvning

    return {
        'kutting': kutting_verdi,
        'arbitrasje': arb_netto,
        'effekttariff': effekt_spart,
        'tidsforskyvning': tidsforskyvning,
        'total': total,
        'kuttet_kwh': np.sum(kuttet),
        'sykluser': np.sum(utlading) / kap_kwh if kap_kwh > 0 else 0,
        'effekt_red': np.mean([u-m for u,m in zip(månedsmaks_uten, månedsmaks_med)])
    }

# Hovedanalyse
print("\n📊 Genererer profiler...")
pv = lag_realistisk_pv()
last = lag_last()
pris = lag_spotpriser()

print(f"   PV total: {np.sum(pv)/1000:.1f} MWh/år")
print(f"   Last: {np.sum(last)/1000:.1f} MWh/år")
print(f"   Snittpris: {np.mean(pris):.3f} kr/kWh")
print(f"   Prisvolatilitet: {np.std(pris):.3f} kr/kWh")
print(f"   Timer > 70 kW: {np.sum(pv > 70)}")
print(f"   Timer > 80 kW: {np.sum(pv > 80)}")
print(f"   Timer > 90 kW: {np.sum(pv > 90)}")

print("\n💰 INNTEKTSANALYSE:")
print("="*70)

resultater = []
beste = None
beste_total = -float('inf')

for kap in [30, 50, 75, 100, 150]:
    eff = kap * 0.75  # 0.75C standard
    if eff <= 75:
        res = simuler_batteri(kap, eff, pv, last, pris)
        res['kap'] = kap
        res['eff'] = eff
        resultater.append(res)

        if res['total'] > beste_total:
            beste_total = res['total']
            beste = res

        print(f"\n🔋 {kap} kWh / {eff:.0f} kW:")

        # Vis inntekter i rekkefølge etter størrelse
        inntekter = [
            ('Unngått kutting', res['kutting']),
            ('Effekttariff', res['effekttariff']),
            ('Arbitrasje', res['arbitrasje']),
            ('Tidsforskyvning', res['tidsforskyvning'])
        ]
        inntekter.sort(key=lambda x: abs(x[1]), reverse=True)

        for navn, verdi in inntekter:
            if res['total'] != 0:
                prosent = verdi / res['total'] * 100
            else:
                prosent = 0
            print(f"   {navn:20s}: {verdi:8,.0f} kr ({prosent:5.1f}%)")

        print(f"   {'─'*45}")
        print(f"   {'TOTAL':20s}: {res['total']:8,.0f} kr/år")
        print(f"   \n   Effektreduksjon: {res['effekt_red']:.1f} kW")
        print(f"   Kuttet fortsatt: {res['kuttet_kwh']:.0f} kWh/år")
        print(f"   Sykluser: {res['sykluser']:.0f}/år")

if beste:
    print("\n" + "="*70)
    print("🏆 OPTIMAL KONFIGURASJON:")
    print(f"   {beste['kap']} kWh / {beste['eff']:.0f} kW")
    print(f"   Total inntekt: {beste['total']:,.0f} kr/år")

    # NPV
    inv = beste['kap'] * 3000 * 1.25
    npv = -inv
    for år in range(15):
        npv += beste['total'] * (1 - 0.02*år) / (1.05**år)

    print(f"   NPV @ 3000 kr/kWh: {npv:,.0f} kr")
    print(f"   Break-even: {inv/beste['total']:.1f} år" if beste['total'] > 0 else "   Break-even: Aldri (negativ inntekt)")

    print("\n📊 INNTEKTSFORDELING:")

    # Sorter etter størrelse
    fordeling = [
        ('Unngått kutting (>70kW)', beste['kutting']),
        ('Effekttariff reduksjon', beste['effekttariff']),
        ('Spotmarked arbitrasje', beste['arbitrasje']),
        ('Tidsforskyvning', beste['tidsforskyvning'])
    ]
    fordeling.sort(key=lambda x: abs(x[1]), reverse=True)

    for i, (navn, verdi) in enumerate(fordeling, 1):
        prosent = verdi / beste['total'] * 100 if beste['total'] != 0 else 0
        print(f"   {i}. {navn:25s}: {verdi:7,.0f} kr ({prosent:4.1f}%)")

# Visualisering
if resultater:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # 1. Inntektsfordeling
    kap_str = [f"{r['kap']} kWh" for r in resultater]
    x_pos = np.arange(len(kap_str))

    kutting = [r['kutting'] for r in resultater]
    effekt = [r['effekttariff'] for r in resultater]
    arb = [r['arbitrasje'] for r in resultater]
    tid = [r['tidsforskyvning'] for r in resultater]

    # Stack positive først
    bottom = np.zeros(len(resultater))

    # Positive inntekter
    for data, label, color in [
        (kutting, 'Unngått kutting', 'orange'),
        (effekt, 'Effekttariff', 'green'),
        (tid, 'Tidsforskyvning', 'purple')
    ]:
        positive = [max(0, d) for d in data]
        ax1.bar(x_pos, positive, bottom=bottom, label=label, color=color, alpha=0.7)
        bottom += positive

    # Arbitrasje (kan være negativ)
    ax1.bar(x_pos, arb, bottom=bottom if all(a >= 0 for a in arb) else 0,
            label='Arbitrasje', color='blue', alpha=0.7)

    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(kap_str)
    ax1.set_ylabel('Årlig inntekt [kr]')
    ax1.set_title('Inntektskilder per batteristørrelse')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3, axis='y')

    # 2. NPV
    npv_vals = []
    for r in resultater:
        inv = r['kap'] * 3000 * 1.25
        npv = -inv
        for år in range(15):
            npv += r['total'] * (1 - 0.02*år) / (1.05**år)
        npv_vals.append(npv)

    colors = ['red' if n < 0 else 'green' for n in npv_vals]
    ax2.bar(x_pos, npv_vals, color=colors, alpha=0.7)
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=1)
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(kap_str)
    ax2.set_ylabel('NPV [kr]')
    ax2.set_title('NPV @ 3000 kr/kWh (15 år, 5% rente)')
    ax2.grid(True, alpha=0.3, axis='y')

    # Verdier på stolper
    for i, v in enumerate(npv_vals):
        ax2.text(i, v + 2000 if v > 0 else v - 2000,
                f'{v:,.0f}', ha='center', va='bottom' if v > 0 else 'top',
                fontsize=9)

    plt.suptitle('Batterisystem - Inntektsanalyse', fontsize=14, fontweight='bold')
    plt.tight_layout()

    output_file = '/mnt/c/Users/klaus/klauspython/SDE/battery_optimization/inntekt_final.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✅ Figur lagret: {output_file}")

print("\n" + "="*70)
print("✅ ANALYSE FULLFØRT")
print("="*70)