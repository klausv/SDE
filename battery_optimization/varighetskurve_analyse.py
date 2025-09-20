#!/usr/bin/env python3
"""
Varighetskurve for solkraftproduksjon
Viser timer over året sortert etter effekt
Med markering av kritiske grenser
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches

print("\n" + "="*70)
print("📊 VARIGHETSKURVE - SOLKRAFTPRODUKSJON")
print("="*70)

# Systemparametere
PV_KWP = 138.55  # kWp installert
DC_MAKS = 138.55  # Teoretisk DC maks (samme som kWp)
INV_GRENSE = 100  # kW AC invertergrense
NETT_GRENSE = 70  # kW netteksport grense
ÅRLIG_PROD = 133017  # kWh/år fra PVSol

def generer_pvsol_tidsserie():
    """Generer realistisk PV-tidsserie basert på PVSol"""
    pv = np.zeros(8760)

    # Månedlig fordeling fra PVSol (normalisert)
    mnd_andel = np.array([
        0.011,  # Jan - 1.5 MWh
        0.030,  # Feb - 4.0 MWh
        0.068,  # Mar - 9.0 MWh
        0.113,  # Apr - 15.0 MWh
        0.146,  # Mai - 19.5 MWh
        0.154,  # Jun - 20.5 MWh - topp
        0.143,  # Jul - 19.0 MWh
        0.120,  # Aug - 16.0 MWh
        0.094,  # Sep - 12.5 MWh
        0.060,  # Okt - 8.0 MWh
        0.026,  # Nov - 3.5 MWh
        0.008   # Des - 1.0 MWh
    ])

    time_idx = 0
    for mnd in range(12):
        dager = [31,28,31,30,31,30,31,31,30,31,30,31][mnd]
        mnd_kwh = ÅRLIG_PROD * mnd_andel[mnd]

        for dag in range(dager):
            # Daglig variasjon (været)
            vær_faktor = np.random.choice(
                [0.1, 0.3, 0.6, 0.9, 1.1],
                p=[0.1, 0.2, 0.3, 0.3, 0.1]
            )
            dag_kwh = (mnd_kwh / dager) * vær_faktor

            # Soltimer avhengig av sesong
            if mnd in [5, 6]:  # Juni-juli
                sol_start, sol_slutt = 3, 22
                maks_dc = 130 if vær_faktor > 0.9 else 110
            elif mnd in [11, 0]:  # Des-jan
                sol_start, sol_slutt = 9, 15
                maks_dc = 50
            else:
                sol_start, sol_slutt = 6, 19
                maks_dc = 100 if vær_faktor > 0.8 else 85

            sol_timer = sol_slutt - sol_start

            for time in range(24):
                if sol_start <= time < sol_slutt:
                    # Solkurve
                    pos = (time - sol_start) / sol_timer
                    intensitet = np.sin(pos * np.pi)

                    # Middagsboost
                    if 0.35 < pos < 0.65:
                        intensitet *= 1.35

                    # DC produksjon (før inverter)
                    dc_prod = intensitet * maks_dc

                    # Sjeldne toppverdier på fine sommerdager
                    if mnd in [4, 5, 6] and 10 <= time <= 14 and vær_faktor >= 1.0:
                        if np.random.random() < 0.05:  # 5% sjanse
                            dc_prod = min(dc_prod * 1.15, DC_MAKS)

                    # AC etter inverter (med tap og begrensning)
                    ac_prod = min(dc_prod * 0.98, INV_GRENSE)  # 98% inverter efficiency

                    pv[time_idx] = ac_prod

                time_idx += 1

    # Skalér til eksakt årsproduksjon
    pv = pv * (ÅRLIG_PROD / np.sum(pv))

    return pv

# Generer data
print("\n📊 Genererer tidsserie...")
pv_ac = generer_pvsol_tidsserie()

# Statistikk
print(f"\n📈 Produksjonsstatistikk:")
print(f"   Total årsproduksjon: {np.sum(pv_ac)/1000:.1f} MWh")
print(f"   Maks AC effekt: {np.max(pv_ac):.1f} kW")
print(f"   Timer > 0 kW: {np.sum(pv_ac > 0)}")
print(f"   Timer > 70 kW: {np.sum(pv_ac > NETT_GRENSE)}")
print(f"   Timer > 90 kW: {np.sum(pv_ac > 90)}")
print(f"   Timer = 100 kW: {np.sum(pv_ac >= 99.5)}")

# Lag varighetskurve
print("\n📊 Lager varighetskurve...")
pv_sortert = np.sort(pv_ac)[::-1]  # Sorter høy til lav
timer = np.arange(8760)

# Plot
fig, ax = plt.subplots(figsize=(14, 8))

# Hovedkurve
ax.fill_between(timer, 0, pv_sortert, color='gold', alpha=0.3, label='PV Produksjon')
ax.plot(timer, pv_sortert, color='darkorange', linewidth=2)

# Markér kritiske grenser
# 1. kWp (138.55 kW) - Teoretisk DC maks
ax.axhline(y=PV_KWP, color='blue', linestyle='--', linewidth=2, alpha=0.7)
ax.text(100, PV_KWP + 2, f'DC kWp: {PV_KWP:.1f} kW',
        fontsize=10, fontweight='bold', color='blue')

# 2. Invertergrense (100 kW)
ax.axhline(y=INV_GRENSE, color='red', linestyle='-', linewidth=2.5, alpha=0.8)
ax.text(100, INV_GRENSE + 2, f'Inverter AC: {INV_GRENSE} kW',
        fontsize=10, fontweight='bold', color='red')

# 3. Nettgrense (70 kW)
ax.axhline(y=NETT_GRENSE, color='darkgreen', linestyle='-', linewidth=2.5, alpha=0.8)
ax.text(100, NETT_GRENSE + 2, f'Nett eksport: {NETT_GRENSE} kW',
        fontsize=10, fontweight='bold', color='darkgreen')

# Fargelegg områder
# Område over invertergrense (kuttet av inverter)
ax.fill_between(timer, INV_GRENSE, np.minimum(pv_sortert, PV_KWP),
                where=(pv_sortert > INV_GRENSE),
                color='red', alpha=0.2, label='Inverter clipping')

# Område mellom nett og inverter (potensielt kuttet til nett)
ax.fill_between(timer, NETT_GRENSE, np.minimum(pv_sortert, INV_GRENSE),
                where=(pv_sortert > NETT_GRENSE),
                color='orange', alpha=0.3, label='Potensielt kuttet (batteri kan lagre)')

# Område under nettgrense (går rett ut)
ax.fill_between(timer, 0, np.minimum(pv_sortert, NETT_GRENSE),
                color='green', alpha=0.2, label='Direkte til nett')

# Timer-markeringer
timer_70 = np.sum(pv_ac > NETT_GRENSE)
timer_90 = np.sum(pv_ac > 90)
timer_100 = np.sum(pv_ac >= 99.5)

ax.axvline(x=timer_70, color='darkgreen', linestyle=':', alpha=0.5)
ax.text(timer_70 - 50, 5, f'{timer_70} timer\n>70 kW',
        fontsize=9, ha='right', color='darkgreen')

if timer_90 > 0:
    ax.axvline(x=timer_90, color='darkorange', linestyle=':', alpha=0.5)
    ax.text(timer_90 - 50, 15, f'{timer_90} timer\n>90 kW',
            fontsize=9, ha='right', color='darkorange')

if timer_100 > 0:
    ax.axvline(x=timer_100, color='red', linestyle=':', alpha=0.5)
    ax.text(timer_100 + 50, 25, f'{timer_100} timer\n≥100 kW',
            fontsize=9, ha='left', color='red')

# Beregn kuttet energi
kuttet_inverter = np.sum(np.maximum(0, pv_sortert - INV_GRENSE))
kuttet_nett = np.sum(np.maximum(0, np.minimum(pv_sortert, INV_GRENSE) - NETT_GRENSE))

# Tekstboks med statistikk
stats_text = (
    f'Årlig produksjon: {np.sum(pv_ac)/1000:.1f} MWh\n'
    f'Maks AC effekt: {np.max(pv_ac):.1f} kW\n'
    f'Kuttet av inverter: {kuttet_inverter:.0f} kWh/år\n'
    f'Potensielt kuttet til nett: {kuttet_nett:.0f} kWh/år\n'
    f'Kapasitetsfaktor: {np.sum(pv_ac)/(INV_GRENSE*8760)*100:.1f}%'
)
ax.text(0.98, 0.97, stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment='top',
        horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

# Formatting
ax.set_xlabel('Timer i året', fontsize=12, fontweight='bold')
ax.set_ylabel('AC Effekt [kW]', fontsize=12, fontweight='bold')
ax.set_title('Varighetskurve - Solkraftproduksjon Snødevegen 122\n138.55 kWp / 100 kW inverter / 70 kW nettgrense',
             fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xlim(0, 8760)
ax.set_ylim(0, max(PV_KWP, np.max(pv_ac)) * 1.1)

# Legend
handles = [
    mpatches.Patch(color='green', alpha=0.3, label='Direkte til nett (≤70 kW)'),
    mpatches.Patch(color='orange', alpha=0.3, label='Kan kuttes til nett (70-100 kW)'),
    mpatches.Patch(color='red', alpha=0.2, label='Inverter clipping (>100 kW)'),
    plt.Line2D([0], [0], color='blue', linestyle='--', label='DC kWp installert'),
    plt.Line2D([0], [0], color='red', linestyle='-', linewidth=2, label='Inverter AC grense'),
    plt.Line2D([0], [0], color='darkgreen', linestyle='-', linewidth=2, label='Nett eksportgrense')
]
ax.legend(handles=handles, loc='upper right', fontsize=10)

# Sekundær x-akse med prosent
ax2 = ax.twiny()
ax2.set_xlim(0, 100)
ax2.set_xlabel('Prosent av året [%]', fontsize=11, fontweight='bold')

plt.tight_layout()

# Lagre figur
output_file = '/mnt/c/Users/klaus/klauspython/offgrid2/battery_optimization/varighetskurve.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"\n✅ Varighetskurve lagret: {output_file}")

plt.show()

print("\n" + "="*70)
print("📊 ANALYSE FULLFØRT")
print("="*70)