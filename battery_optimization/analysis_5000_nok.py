#!/usr/bin/env python
"""
Økonomisk analyse med 5000 NOK/kWh batterikostnad
Inkluderer batteri-inverter i kostnaden
Antar smartstyring sikrer batteri er tilgjengelig ved peak
"""
import numpy as np
import matplotlib.pyplot as plt

print("📊 ØKONOMISK ANALYSE MED MARKEDSPRIS 5000 NOK/kWh")
print("="*80)

# System parametere
print("\n⚙️ SYSTEMKONFIGURASJON:")
print("-"*60)
print("PV installert:        150 kWp")
print("PV inverter:          110 kW")
print("Grid limit:           77 kW")
print("Batterikostnad:       5000 NOK/kWh (inkl. batteri-inverter)")
print("Smartstyring:         JA - sikrer batteri tilgjengelig ved peak")

# Lnett tariffer
tariff_brackets = [
    (0, 2, 136),
    (2, 5, 232),
    (5, 10, 372),
    (10, 15, 572),
    (15, 20, 772),
    (20, 25, 972),
    (25, 50, 1772),
    (50, 75, 2572),
    (75, 100, 3372),
    (100, float('inf'), 5600)
]

def get_tariff(peak_kw):
    """Finn månedlig kostnad for gitt peak"""
    if peak_kw <= 0:
        return 0
    for from_kw, to_kw, cost in tariff_brackets:
        if from_kw < peak_kw <= to_kw:
            return cost
    return 5600

# Realistiske månedlige peaks
months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']
peaks_realistic = [42, 40, 36, 32, 28, 24, 20, 22, 28, 34, 38, 42]

# Økonomiske parametere
discount_rate = 0.05
years = 15
npv_factor = sum(1/(1+discount_rate)**y for y in range(1, years+1))
battery_cost = 5000  # NOK/kWh

print(f"\n💰 ØKONOMISKE FORUTSETNINGER:")
print("-"*60)
print(f"Batterikostnad:       {battery_cost:,} NOK/kWh")
print(f"Diskonteringsrente:   {discount_rate*100:.0f}%")
print(f"Levetid:              {years} år")
print(f"NPV-faktor:           {npv_factor:.3f}")

# Test ulike batteristørrelser
battery_sizes = [10, 20, 30, 40, 50, 60, 80, 100]

print("\n📈 VERDIDRIVERE OG NPV ANALYSE:")
print("-"*80)
print("Batteri | Effekt- | Avkort- | Arbi-  | Selv-   | TOTAL  | Invest-  |   NPV    | Payback | Status")
print("(kWh)   | tariff  | ning    | trasje | forsyning| årlig  | ment     |          | (år)    |")
print("--------|---------|---------|--------|----------|--------|----------|----------|---------|-------")

results = []
for battery_kwh in battery_sizes:
    # Anta 0.5C rate (2-timers batteri)
    battery_kw = battery_kwh / 2

    # Effekttariff-besparelse
    tariff_saving = 0
    for peak in peaks_realistic:
        peak_with = max(0, peak - battery_kw)
        tariff_saving += get_tariff(peak) - get_tariff(peak_with)

    # Andre verdidrivere (skalert etter batteristørrelse)
    # Baseverdier for 40 kWh batteri
    curtailment_base = 9000
    arbitrage_base = 3500
    self_consumption_base = 3500

    scale_factor = battery_kwh / 40

    # Avkortning - øker med størrelse men avtar marginalt
    curtailment = curtailment_base * min(scale_factor, 1.5) * (1 - 0.1 * max(0, scale_factor - 1))

    # Arbitrasje - lineær med størrelse opp til et punkt
    arbitrage = arbitrage_base * min(scale_factor, 1.8)

    # Selvforsyning - øker med størrelse men platåer
    self_consumption = self_consumption_base * min(scale_factor, 1.5)

    total_annual = tariff_saving + curtailment + arbitrage + self_consumption
    investment = battery_cost * battery_kwh
    npv = total_annual * npv_factor - investment
    payback = investment / total_annual if total_annual > 0 else 999
    status = "✅" if npv > 0 else "❌"

    print(f"{battery_kwh:6.0f}  | {tariff_saving:7.0f} | {curtailment:7.0f} | {arbitrage:6.0f} | {self_consumption:8.0f} | {total_annual:6.0f} | {investment:8.0f} | {npv:+8.0f} | {payback:7.1f} | {status}")

    results.append({
        'size': battery_kwh,
        'tariff': tariff_saving,
        'curtailment': curtailment,
        'arbitrage': arbitrage,
        'self_consumption': self_consumption,
        'total': total_annual,
        'investment': investment,
        'npv': npv,
        'payback': payback
    })

# Finn optimal størrelse
best_npv = max(results, key=lambda x: x['npv'])
print(f"\n🎯 OPTIMAL BATTERISTØRRELSE:")
print("-"*60)
print(f"Størrelse:            {best_npv['size']} kWh")
print(f"NPV:                  {best_npv['npv']:+,.0f} NOK")
print(f"Årlig verdi:          {best_npv['total']:,.0f} NOK")
print(f"Tilbakebetalingstid:  {best_npv['payback']:.1f} år")

# Sensitivitetsanalyse
print("\n📊 SENSITIVITETSANALYSE - BATTERIKOSTNAD:")
print("-"*60)
print("Ved optimal størrelse ({} kWh):".format(best_npv['size']))
print("Batterikostnad | NPV         | IRR    | Status")
print("---------------|-------------|--------|--------")

for cost in [2000, 2500, 3000, 3500, 4000, 4500, 5000, 6000, 7000, 8000]:
    investment = cost * best_npv['size']
    npv = best_npv['total'] * npv_factor - investment
    irr = (best_npv['total'] / investment - 0.02) * 100 if investment > 0 else 0
    status = "✅ Lønnsomt" if npv > 0 else "❌ Ulønnsomt"
    print(f"{cost:,} NOK/kWh  | {npv:+11,.0f} | {irr:6.1f}% | {status}")

break_even = best_npv['total'] * npv_factor / best_npv['size']
print(f"\nBreak-even batterikostnad: {break_even:,.0f} NOK/kWh")

# Lag visualisering
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))

# Plot 1: NPV vs batteristørrelse
sizes = [r['size'] for r in results]
npvs = [r['npv'] for r in results]
ax1.plot(sizes, npvs, 'b-', linewidth=2, marker='o', markersize=8)
ax1.axhline(y=0, color='r', linestyle='--', alpha=0.5)
ax1.fill_between(sizes, 0, npvs, where=(np.array(npvs) > 0), alpha=0.3, color='green')
ax1.fill_between(sizes, 0, npvs, where=(np.array(npvs) <= 0), alpha=0.3, color='red')
ax1.set_xlabel('Batteristørrelse (kWh)')
ax1.set_ylabel('NPV (NOK)')
ax1.set_title(f'NPV ved {battery_cost:,} NOK/kWh', fontweight='bold')
ax1.grid(True, alpha=0.3)

# Marker optimal punkt
optimal_idx = npvs.index(max(npvs))
ax1.plot(sizes[optimal_idx], npvs[optimal_idx], 'go', markersize=12, label=f'Optimal: {sizes[optimal_idx]} kWh')
ax1.legend()

# Plot 2: Verdidrivere stacked bar
x = np.arange(len(sizes))
width = 0.8
tariffs = [r['tariff'] for r in results]
curtailments = [r['curtailment'] for r in results]
arbitrages = [r['arbitrage'] for r in results]
self_consumptions = [r['self_consumption'] for r in results]

ax2.bar(x, tariffs, width, label='Effekttariff', color='#3498db')
ax2.bar(x, curtailments, width, bottom=tariffs, label='Avkortning', color='#e74c3c')
ax2.bar(x, arbitrages, width, bottom=np.array(tariffs)+np.array(curtailments),
        label='Arbitrasje', color='#2ecc71')
ax2.bar(x, self_consumptions, width,
        bottom=np.array(tariffs)+np.array(curtailments)+np.array(arbitrages),
        label='Selvforsyning', color='#f39c12')

ax2.set_xlabel('Batteristørrelse (kWh)')
ax2.set_ylabel('Årlig verdi (NOK)')
ax2.set_title('Verdidrivere ved ulike batteristørrelser', fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels([f'{s}' for s in sizes])
ax2.legend()
ax2.grid(True, alpha=0.3, axis='y')

# Plot 3: Payback periode
paybacks = [r['payback'] for r in results if r['payback'] < 20]
valid_sizes = [r['size'] for r in results if r['payback'] < 20]
ax3.plot(valid_sizes, paybacks, 'r-', linewidth=2, marker='s', markersize=8)
ax3.axhline(y=5, color='green', linestyle='--', alpha=0.5, label='5 år')
ax3.axhline(y=10, color='orange', linestyle='--', alpha=0.5, label='10 år')
ax3.axhline(y=15, color='red', linestyle='--', alpha=0.5, label='15 år (levetid)')
ax3.set_xlabel('Batteristørrelse (kWh)')
ax3.set_ylabel('Tilbakebetalingstid (år)')
ax3.set_title('Tilbakebetalingstid', fontweight='bold')
ax3.legend()
ax3.grid(True, alpha=0.3)
ax3.set_ylim([0, 20])

# Plot 4: NPV ved ulike batterikostnader
battery_costs = np.arange(2000, 8000, 500)
npv_lines = {}
for size in [20, 40, 60, 80]:
    result = next((r for r in results if r['size'] == size), None)
    if result:
        npv_line = []
        for cost in battery_costs:
            npv = result['total'] * npv_factor - cost * size
            npv_line.append(npv)
        npv_lines[size] = npv_line
        ax4.plot(battery_costs, npv_line, linewidth=2, label=f'{size} kWh')

ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax4.axvline(x=5000, color='purple', linestyle='--', linewidth=2, alpha=0.7, label='Dagens pris')
ax4.set_xlabel('Batterikostnad (NOK/kWh)')
ax4.set_ylabel('NPV (NOK)')
ax4.set_title('NPV-sensitivitet for batterikostnad', fontweight='bold')
ax4.legend()
ax4.grid(True, alpha=0.3)

plt.suptitle(f'Batterøkonomi med {battery_cost:,} NOK/kWh (inkl. inverter)',
             fontsize=14, fontweight='bold')
plt.tight_layout()

# Lagre figur
output_file = 'results/analysis_5000_nok.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"\n💾 Lagret analyse: {output_file}")

print("\n✅ KONKLUSJON MED 5000 NOK/kWh:")
print("="*80)
print(f"• Optimal batteristørrelse: {best_npv['size']} kWh")
print(f"• NPV ved optimal størrelse: {best_npv['npv']:+,.0f} NOK")
print(f"• Break-even batterikostnad: {break_even:,.0f} NOK/kWh")

if best_npv['npv'] > 0:
    print(f"• Status: LØNNSOMT selv med 5000 NOK/kWh")
    print(f"• Anbefaling: Installer {best_npv['size']} kWh batteri")
else:
    print(f"• Status: IKKE lønnsomt med 5000 NOK/kWh")
    print(f"• Batterikostnad må ned til {break_even:,.0f} NOK/kWh for lønnsomhet")

print("="*80)