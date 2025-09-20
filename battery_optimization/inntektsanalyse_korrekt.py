#!/usr/bin/env python3
"""
Korrekt analyse av inntektskilder for batteri
Med riktig effekttariff-beregning
"""
import numpy as np
import matplotlib.pyplot as plt

print("\n" + "="*70)
print("💰 DETALJERT INNTEKTSANALYSE - BATTERI")
print("="*70)

# Systemparametere
PV_KWP = 138.55
INV_GRENSE = 100
NETT_GRENSE = 70
ÅRLIG_PROD = 133017  # kWh fra PVSol
ÅRLIG_LAST = 300000  # kWh

# Økonomi
VIRKNINGSGRAD = 0.90

# Effekttariffer Lnett (kr/mnd per kW døgnmaks)
def finn_effekttariff(kw):
    """Finn effekttariff basert på døgnmaks"""
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

def generer_profiler():
    """Generer enkle men realistiske profiler"""
    pv = np.zeros(8760)
    last = np.zeros(8760)
    pris = np.zeros(8760)

    # Månedlig PV-fordeling (MWh)
    månedlig_pv = [1.5, 4.0, 9.0, 15.0, 19.5, 20.5, 19.0, 16.0, 12.5, 8.0, 3.5, 1.0]

    time_idx = 0
    for mnd in range(12):
        dager_i_mnd = [31,28,31,30,31,30,31,31,30,31,30,31][mnd]
        mnd_pv_kwh = (månedlig_pv[mnd] / sum(månedlig_pv)) * ÅRLIG_PROD

        for dag in range(dager_i_mnd):
            dag_pv = mnd_pv_kwh / dager_i_mnd

            # Soltimer per sesong
            if mnd in [5, 6]:  # Juni-juli
                sol_timer = range(4, 21)
                maks_eff = 90
            elif mnd in [11, 0]:  # Des-jan
                sol_timer = range(9, 15)
                maks_eff = 30
            else:
                sol_timer = range(6, 18)
                maks_eff = 70

            for time in range(24):
                # PV-produksjon
                if time in sol_timer:
                    pos = (time - sol_timer[0]) / len(sol_timer)
                    intensitet = np.sin(pos * np.pi) * 1.3 if 0.3 < pos < 0.7 else np.sin(pos * np.pi)
                    pv[time_idx] = min(intensitet * maks_eff * np.random.uniform(0.8, 1.2), INV_GRENSE)

                # Last (kommersiell profil)
                time_dag = time
                ukedag = ((time_idx // 24) % 7) < 5

                if ukedag and 7 <= time_dag <= 17:
                    last[time_idx] = 60  # Dagtid arbeid
                elif ukedag and (6 <= time_dag < 7 or 17 < time_dag <= 20):
                    last[time_idx] = 45  # Morgen/kveld
                else:
                    last[time_idx] = 30  # Natt/helg

                # Sesongvariasjon last
                if mnd in [11, 0, 1]:  # Vinter
                    last[time_idx] *= 1.3
                elif mnd in [5, 6, 7]:  # Sommer
                    last[time_idx] *= 0.9

                # Spotpris
                if mnd in [5, 6, 7]:  # Sommer
                    basis_pris = 0.35
                elif mnd in [11, 0, 1]:  # Vinter
                    basis_pris = 0.75
                else:
                    basis_pris = 0.55

                # Døgnvariasjon pris
                if ukedag and 7 <= time_dag <= 9:
                    pris_faktor = 1.5  # Morgentopp
                elif ukedag and 17 <= time_dag <= 19:
                    pris_faktor = 1.4  # Kveldtopp
                elif 23 <= time_dag or time_dag <= 5:
                    pris_faktor = 0.6  # Natt
                else:
                    pris_faktor = 1.0

                pris[time_idx] = basis_pris * pris_faktor * np.random.normal(1.0, 0.15)
                pris[time_idx] = max(0.05, min(2.0, pris[time_idx]))

                time_idx += 1

    # Skalér til riktige årsverdier
    pv = pv * (ÅRLIG_PROD / np.sum(pv))
    last = last * (ÅRLIG_LAST / np.sum(last))

    return pv, last, pris

def simuler_med_inntektsanalyse(kap_kwh, eff_kw, pv, last, pris):
    """Simuler batteri med detaljert inntektssporing"""
    n = 8760
    soc = np.zeros(n)
    soc[0] = kap_kwh * 0.5

    # Energiflyt
    batteri_lading = np.zeros(n)
    batteri_utlading = np.zeros(n)
    nett_import = np.zeros(n)
    nett_eksport = np.zeros(n)
    kuttet_prod = np.zeros(n)

    # Inntektskategorier
    arbitrasje_kjøp = np.zeros(n)  # Når vi lader fra nett ved lav pris
    arbitrasje_salg = np.zeros(n)  # Når vi selger til nett ved høy pris
    kutting_unngått = np.zeros(n)  # Produksjon over 70kW som lagres
    peak_shaving_kwh = np.zeros(n)  # Reduksjon av import-topper

    for t in range(1, n):
        produksjon = pv[t]
        forbruk = last[t]
        netto = produksjon - forbruk

        # Prisanalyse (24t rullerende)
        if t >= 24:
            pris_snitt = np.mean(pris[t-24:t])
            høy_pris = pris[t] > pris_snitt * 1.2
            lav_pris = pris[t] < pris_snitt * 0.8
        else:
            høy_pris = lav_pris = False

        if produksjon > NETT_GRENSE:
            # MÅ lagre eller kutte produksjon over 70 kW
            over_grense = produksjon - NETT_GRENSE
            ledig_kap = (kap_kwh * 0.9 - soc[t-1]) / VIRKNINGSGRAD
            kan_lagre = min(eff_kw, ledig_kap, over_grense)

            batteri_lading[t] = kan_lagre
            kutting_unngått[t] = kan_lagre  # Dette er verdien av unngått kutting
            kuttet_prod[t] = max(0, over_grense - kan_lagre)

            # Resten av produksjonen
            if netto - kan_lagre > 0:
                nett_eksport[t] = min(NETT_GRENSE, netto - kan_lagre)
            else:
                nett_import[t] = -(netto - kan_lagre)

        elif netto > 0:
            # Overskuddsproduksjon under 70 kW
            nett_eksport[t] = netto

            # Opportunistisk lading ved lav pris
            if lav_pris and soc[t-1] < kap_kwh * 0.7:
                ledig = (kap_kwh * 0.9 - soc[t-1]) / VIRKNINGSGRAD
                kjøp_kwh = min(eff_kw, ledig, 20)  # Maks 20 kW fra nett
                batteri_lading[t] += kjøp_kwh
                arbitrasje_kjøp[t] = kjøp_kwh
                nett_import[t] += kjøp_kwh

        else:
            # Underskudd - forbruk større enn produksjon
            behov = -netto

            # Sjekk om vi kan bruke batteri
            if soc[t-1] > kap_kwh * 0.2:
                tilgjengelig = (soc[t-1] - kap_kwh * 0.1) * VIRKNINGSGRAD
                kan_levere = min(eff_kw, tilgjengelig, behov)

                if høy_pris:
                    # Arbitrasje - selg ved høy pris
                    batteri_utlading[t] = kan_levere
                    arbitrasje_salg[t] = kan_levere * 0.5  # Halvparten regnes som arbitrasje
                    peak_shaving_kwh[t] = kan_levere * 0.5  # Resten er peak shaving
                else:
                    # Peak shaving - reduser import-topp
                    batteri_utlading[t] = kan_levere * 0.7  # Bruk 70% kapasitet
                    peak_shaving_kwh[t] = kan_levere * 0.7

                nett_import[t] = behov - batteri_utlading[t]
            else:
                nett_import[t] = behov

        # Oppdater SOC
        soc[t] = soc[t-1] + batteri_lading[t] * VIRKNINGSGRAD - batteri_utlading[t] / VIRKNINGSGRAD
        soc[t] = np.clip(soc[t], kap_kwh * 0.1, kap_kwh * 0.9)

    # Beregn inntekter

    # 1. Arbitrasje (kjøp lavt, selg høyt)
    arbitrasje_kostnad = np.sum(arbitrasje_kjøp * pris)
    arbitrasje_inntekt = np.sum(arbitrasje_salg * pris)
    arbitrasje_netto = arbitrasje_inntekt - arbitrasje_kostnad

    # 2. Unngått kutting (produksjon over 70 kW som ellers ville gått tapt)
    kutting_verdi = np.sum(kutting_unngått) * np.mean(pris)

    # 3. Effekttariff reduksjon
    # Beregn månedlige døgnmaks med og uten batteri
    månedsmaks_uten = []
    månedsmaks_med = []

    dag_start = 0
    for mnd in range(12):
        dager = [31,28,31,30,31,30,31,31,30,31,30,31][mnd]
        mnd_maks_uten = 0
        mnd_maks_med = 0

        for dag in range(dager):
            dag_idx = dag_start + dag
            start = dag_idx * 24
            slutt = start + 24

            # Døgnmaks UTEN batteri (all peak shaving legges tilbake)
            import_uten = nett_import[start:slutt] + peak_shaving_kwh[start:slutt]
            døgnmaks_uten = np.max(import_uten)

            # Døgnmaks MED batteri (faktisk import)
            døgnmaks_med = np.max(nett_import[start:slutt])

            # Månedsmaks er høyeste døgnmaks i måneden
            mnd_maks_uten = max(mnd_maks_uten, døgnmaks_uten)
            mnd_maks_med = max(mnd_maks_med, døgnmaks_med)

        månedsmaks_uten.append(mnd_maks_uten)
        månedsmaks_med.append(mnd_maks_med)
        dag_start += dager

    # Beregn årlig effektkostnad
    effekt_uten = sum(finn_effekttariff(maks) for maks in månedsmaks_uten)
    effekt_med = sum(finn_effekttariff(maks) for maks in månedsmaks_med)
    effekt_spart = effekt_uten - effekt_med

    # 4. Økt selvforbruk/tidsforskyvning
    # Verdi av å flytte forbruk fra høy til lav pris
    selvforbruk_verdi = np.sum(batteri_utlading) * np.std(pris) * 0.5  # Proporsjonal med prisvolatilitet

    # Total årlig inntekt
    total = arbitrasje_netto + kutting_verdi + effekt_spart + selvforbruk_verdi

    return {
        'arbitrasje': arbitrasje_netto,
        'kutting': kutting_verdi,
        'effekttariff': effekt_spart,
        'selvforbruk': selvforbruk_verdi,
        'total': total,
        'månedsmaks_uten': månedsmaks_uten,
        'månedsmaks_med': månedsmaks_med,
        'kuttet_kwh': np.sum(kuttet_prod),
        'sykluser': np.sum(batteri_utlading) / kap_kwh
    }

# Hovedanalyse
print("\n📊 Genererer realistiske profiler...")
pv, last, pris = generer_profiler()

print(f"   PV total: {np.sum(pv)/1000:.1f} MWh/år")
print(f"   Last total: {np.sum(last)/1000:.1f} MWh/år")
print(f"   Snittpris: {np.mean(pris):.3f} kr/kWh")
print(f"   Prisvolatilitet (std): {np.std(pris):.3f} kr/kWh")
print(f"   Timer PV > 70 kW: {np.sum(pv > NETT_GRENSE)}")
print(f"   Timer PV > 90 kW: {np.sum(pv > 90)}")

# Analyser ulike batteristørrelser
print("\n💰 INNTEKTSANALYSE PER BATTERIKONFIGURASJON:")
print("="*70)

resultater = []
for kap in [30, 50, 75, 100, 150]:
    for c_rate in [0.5, 0.75, 1.0]:
        eff = kap * c_rate
        if eff <= 75:  # Rimelig effektgrense
            res = simuler_med_inntektsanalyse(kap, eff, pv, last, pris)
            resultater.append({'kap': kap, 'eff': eff, **res})

            if c_rate == 0.75:  # Vis detaljer for 0.75C
                print(f"\n🔋 {kap} kWh / {eff:.0f} kW (C={c_rate:.2f}):")
                print(f"   Arbitrasje: {res['arbitrasje']:>8,.0f} kr ({res['arbitrasje']/res['total']*100:>5.1f}%)")
                print(f"   Unngått kutting: {res['kutting']:>8,.0f} kr ({res['kutting']/res['total']*100:>5.1f}%)")
                print(f"   Effekttariff: {res['effekttariff']:>8,.0f} kr ({res['effekttariff']/res['total']*100:>5.1f}%)")
                print(f"   Tidsforskyvning: {res['selvforbruk']:>8,.0f} kr ({res['selvforbruk']/res['total']*100:>5.1f}%)")
                print(f"   ─────────────────────────────────────────")
                print(f"   TOTAL: {res['total']:>14,.0f} kr/år")
                print(f"   \n   Effektreduksjon: {np.mean([u-m for u,m in zip(res['månedsmaks_uten'], res['månedsmaks_med'])]):>5.1f} kW snitt")
                print(f"   Sykluser/år: {res['sykluser']:>8.0f}")
                print(f"   Fortsatt kuttet: {res['kuttet_kwh']:>5.0f} kWh/år")

# Finn beste konfigurasjon
beste = max(resultater, key=lambda x: x['total'])

print("\n" + "="*70)
print("🏆 OPTIMAL KONFIGURASJON:")
print(f"   Batteri: {beste['kap']} kWh / {beste['eff']:.0f} kW")
print(f"   Total årsinntekt: {beste['total']:,.0f} kr")

print("\n📊 INNTEKTSFORDELING:")
print(f"   1. Effekttariff reduksjon: {beste['effekttariff']:>7,.0f} kr ({beste['effekttariff']/beste['total']*100:>4.1f}%)")
print(f"   2. Unngått kutting (>70kW): {beste['kutting']:>7,.0f} kr ({beste['kutting']/beste['total']*100:>4.1f}%)")
print(f"   3. Spotmarked arbitrasje: {beste['arbitrasje']:>7,.0f} kr ({beste['arbitrasje']/beste['total']*100:>4.1f}%)")
print(f"   4. Tidsforskyvning/økt verdi: {beste['selvforbruk']:>7,.0f} kr ({beste['selvforbruk']/beste['total']*100:>4.1f}%)")

# Visualisering
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

# 1. Stacked bar - alle konfigurasjoner
konfigurasjoner = [f"{r['kap']}kWh\n{r['eff']:.0f}kW" for r in resultater[:6]]
arbitrasje_vals = [r['arbitrasje'] for r in resultater[:6]]
kutting_vals = [r['kutting'] for r in resultater[:6]]
tariff_vals = [r['effekttariff'] for r in resultater[:6]]
selv_vals = [r['selvforbruk'] for r in resultater[:6]]

x_pos = np.arange(len(konfigurasjoner))
ax1.bar(x_pos, tariff_vals, label='Effekttariff', color='green')
ax1.bar(x_pos, kutting_vals, bottom=tariff_vals, label='Unngått kutting', color='orange')
ax1.bar(x_pos, arbitrasje_vals, bottom=[t+k for t,k in zip(tariff_vals, kutting_vals)],
        label='Arbitrasje', color='blue')
ax1.bar(x_pos, selv_vals, bottom=[t+k+a for t,k,a in zip(tariff_vals, kutting_vals, arbitrasje_vals)],
        label='Tidsforskyvning', color='purple')

ax1.set_xticks(x_pos)
ax1.set_xticklabels(konfigurasjoner, fontsize=8)
ax1.set_ylabel('Årlig inntekt [kr]')
ax1.set_title('Inntektsfordeling per batterikonfigurasjon')
ax1.legend(loc='upper left')
ax1.grid(True, alpha=0.3, axis='y')

# 2. Pie chart - beste konfigurasjon
sizes = [beste['effekttariff'], beste['kutting'], beste['arbitrasje'], beste['selvforbruk']]
sizes = [max(0, s) for s in sizes]  # Sikre positive verdier
labels = ['Effekttariff', 'Unngått kutting', 'Arbitrasje', 'Tidsforskyvning']
colors = ['green', 'orange', 'blue', 'purple']
explode = (0.1, 0, 0, 0)  # Fremhev effekttariff

wedges, texts, autotexts = ax2.pie(sizes, labels=labels, colors=colors,
                                    autopct='%1.1f%%', explode=explode, startangle=45)
ax2.set_title(f'Optimal: {beste["kap"]} kWh / {beste["eff"]:.0f} kW\nTotal: {beste["total"]:,.0f} kr/år')

# 3. Effektreduksjon
effekt_data = [(r['kap'], np.mean([u-m for u,m in zip(r['månedsmaks_uten'], r['månedsmaks_med'])]))
               for r in resultater if r['eff'] == r['kap'] * 0.75]
if effekt_data:
    kap_vals, red_vals = zip(*effekt_data)
    ax3.bar(range(len(kap_vals)), red_vals, color='darkgreen', alpha=0.7)
    ax3.set_xticks(range(len(kap_vals)))
    ax3.set_xticklabels([f"{k} kWh" for k in kap_vals])
    ax3.set_ylabel('Effektreduksjon [kW]')
    ax3.set_title('Gjennomsnittlig effektreduksjon (døgnmaks)')
    ax3.grid(True, alpha=0.3, axis='y')

# 4. NPV analyse
npv_data = []
for r in resultater[:6]:
    inv = r['kap'] * 3000 * 1.25
    npv = -inv
    for år in range(15):
        npv += r['total'] * (1 - 0.02*år) / (1.05**år)
    npv_data.append(npv)

ax4.bar(x_pos, npv_data, color=['red' if n < 0 else 'green' for n in npv_data], alpha=0.7)
ax4.axhline(y=0, color='black', linestyle='--', linewidth=1)
ax4.set_xticks(x_pos)
ax4.set_xticklabels(konfigurasjoner, fontsize=8)
ax4.set_ylabel('NPV [kr]')
ax4.set_title('NPV @ 3000 kr/kWh (15 år, 5% rente)')
ax4.grid(True, alpha=0.3, axis='y')

# Legg til verdier på stolpene
for i, v in enumerate(npv_data):
    ax4.text(i, v + 1000 if v > 0 else v - 1000, f'{v:,.0f}',
            ha='center', va='bottom' if v > 0 else 'top', fontsize=8)

plt.suptitle('Batterisystem - Detaljert Inntektsanalyse', fontsize=14, fontweight='bold')
plt.tight_layout()

output_file = '/mnt/c/Users/klaus/klauspython/offgrid2/battery_optimization/inntektsfordeling_korrekt.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"\n✅ Figur lagret: {output_file}")

print("\n" + "="*70)
print("✅ ANALYSE FULLFØRT!")
print("="*70)