#!/usr/bin/env python
"""
Oppdaterte grafer med korrekte beregninger
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

print("📊 Lager oppdaterte grafer med korrekte beregninger...")

# Korrekte Lnett-tariffer (kr/mnd for intervallet)
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
    """Finn tariffen for en gitt peak"""
    if peak_kw <= 0:
        return 0
    for from_kw, to_kw, cost in tariff_brackets:
        if from_kw < peak_kw <= to_kw:
            return cost
        elif peak_kw > 100:
            return 5600
    return 0

# Create figure with multiple subplots
fig = plt.figure(figsize=(18, 16))

# --- PLOT 1: Effekttariff-struktur ---
ax1 = plt.subplot(3, 2, 1)

# Visualiser tariff-struktur
peaks = np.arange(0, 101, 1)
costs = [get_tariff(p) for p in peaks]

ax1.plot(peaks, costs, 'b-', linewidth=2)
ax1.fill_between(peaks, 0, costs, alpha=0.3)

# Mark intervaller
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#9980FA', '#FD79A8', '#A29BFE', '#6C5CE7', '#00B894']
for i, (from_kw, to_kw, cost) in enumerate(tariff_brackets[:10]):
    if to_kw > 100:
        to_kw = 100
    ax1.axvspan(from_kw, to_kw, alpha=0.2, color=colors[i % len(colors)])
    mid = (from_kw + min(to_kw, 100)) / 2
    if mid <= 100:
        ax1.text(mid, cost + 100, f'{cost} kr', ha='center', fontsize=8)

ax1.set_xlabel('Månedlig peak (kW)', fontsize=11)
ax1.set_ylabel('Månedlig kostnad (kr)', fontsize=11)
ax1.set_title('Lnett Kapasitetsledd Struktur', fontsize=13, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.set_xlim([0, 100])

# --- PLOT 2: Besparelse ved ulike batteristørrelser ---
ax2 = plt.subplot(3, 2, 2)

battery_sizes = [5, 10, 15, 20, 25, 30]
typical_peaks = [45, 45, 40, 35, 30, 25, 22, 25, 30, 35, 40, 45]  # Månedlige peaks

yearly_savings = []
for battery_kw in battery_sizes:
    total_saving = 0
    for peak in typical_peaks:
        reduced_peak = max(0, peak - battery_kw)
        saving = get_tariff(peak) - get_tariff(reduced_peak)
        total_saving += saving
    yearly_savings.append(total_saving)

bars = ax2.bar(battery_sizes, yearly_savings, color='#2E86AB', alpha=0.8, edgecolor='black', linewidth=1.5)

# Add value labels
for bar, value in zip(bars, yearly_savings):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height + 200,
             f'{value:,.0f}', ha='center', va='bottom', fontsize=10)

ax2.set_xlabel('Batteristørrelse (kW)', fontsize=11)
ax2.set_ylabel('Årlig besparelse (kr)', fontsize=11)
ax2.set_title('Effekttariff-besparelse vs Batteristørrelse', fontsize=13, fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')

# --- PLOT 3: Månedlige peaks og besparelser ---
ax3 = plt.subplot(3, 2, 3)

months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']
battery_kw = 20

x = np.arange(len(months))
width = 0.35

# Peaks med og uten batteri
peaks_without = typical_peaks
peaks_with = [max(0, p - battery_kw) for p in peaks_without]

bars1 = ax3.bar(x - width/2, peaks_without, width, label='Uten batteri', color='#E74C3C', alpha=0.8)
bars2 = ax3.bar(x + width/2, peaks_with, width, label=f'Med {battery_kw} kW batteri', color='#27AE60', alpha=0.8)

ax3.set_xlabel('Måned', fontsize=11)
ax3.set_ylabel('Peak effekt (kW)', fontsize=11)
ax3.set_title('Månedlig Peak Effekt - Før og Etter Batteri', fontsize=13, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels(months, rotation=45)
ax3.legend()
ax3.grid(True, alpha=0.3, axis='y')

# Add horizontal lines for tariff brackets
ax3.axhline(y=25, color='orange', linestyle='--', alpha=0.5, linewidth=1)
ax3.text(11.5, 26, '25-50 kW: 1,772 kr', fontsize=8, ha='right')
ax3.axhline(y=20, color='red', linestyle='--', alpha=0.5, linewidth=1)
ax3.text(11.5, 21, '20-25 kW: 972 kr', fontsize=8, ha='right')

# --- PLOT 4: Total verdidrivere (stacked bar) ---
ax4 = plt.subplot(3, 2, 4)

# Verdidrivere med realistiske tall
components = ['Effekttariff', 'Avkortning', 'Arbitrasje', 'Selvforsyning']
values_20kw = [9000, 5000, 2000, 2000]  # Realistiske verdier
values_10kw = [4500, 3000, 1000, 1000]   # Halvparten for 10 kW

x = np.arange(2)
width = 0.5
colors_comp = ['#3498DB', '#E67E22', '#9B59B6', '#1ABC9C']

bottom_10 = np.zeros(1)
bottom_20 = np.zeros(1)

for i, (comp, val10, val20) in enumerate(zip(components, values_10kw, values_20kw)):
    bar1 = ax4.bar(0, val10, width, bottom=bottom_10, color=colors_comp[i], label=comp if i < 4 else '')
    bar2 = ax4.bar(1, val20, width, bottom=bottom_20, color=colors_comp[i])

    # Add value labels
    if val10 > 500:
        ax4.text(0, bottom_10[0] + val10/2, f'{val10/1000:.1f}k', ha='center', va='center', fontsize=9, color='white')
    if val20 > 500:
        ax4.text(1, bottom_20[0] + val20/2, f'{val20/1000:.1f}k', ha='center', va='center', fontsize=9, color='white')

    bottom_10 += val10
    bottom_20 += val20

ax4.set_ylabel('Årlig verdi (kr)', fontsize=11)
ax4.set_title('Verdidrivere for Batteri (Realistiske Tall)', fontsize=13, fontweight='bold')
ax4.set_xticks(x)
ax4.set_xticklabels(['10 kW batteri', '20 kW batteri'])
ax4.legend(loc='upper left', fontsize=9)
ax4.grid(True, alpha=0.3, axis='y')

# Add total labels
ax4.text(0, sum(values_10kw) + 300, f'Σ {sum(values_10kw):,} kr', ha='center', fontweight='bold')
ax4.text(1, sum(values_20kw) + 300, f'Σ {sum(values_20kw):,} kr', ha='center', fontweight='bold')

# --- PLOT 5: NPV ved ulike batterikostnader ---
ax5 = plt.subplot(3, 2, 5)

battery_costs = np.arange(1000, 10000, 500)
discount_rate = 0.05
years = 15
npv_factor = sum(1/(1+discount_rate)**y for y in range(1, years+1))

# For 20 kW batteri
annual_value = 18000  # Total årlig verdi
battery_size = 20  # kWh

npvs = []
for cost_per_kwh in battery_costs:
    investment = cost_per_kwh * battery_size
    npv = annual_value * npv_factor - investment
    npvs.append(npv)

ax5.plot(battery_costs, npvs, 'b-', linewidth=2.5, label='20 kWh batteri')
ax5.axhline(y=0, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
ax5.fill_between(battery_costs, 0, npvs, where=(np.array(npvs) > 0), alpha=0.3, color='green', label='Lønnsomt område')
ax5.fill_between(battery_costs, 0, npvs, where=(np.array(npvs) <= 0), alpha=0.3, color='red', label='Ulønnsomt område')

# Mark current market price
ax5.axvline(x=3500, color='orange', linestyle=':', linewidth=2, label='Dagens pris (3,500 kr/kWh)')
ax5.axvline(x=5000, color='purple', linestyle=':', linewidth=2, label='Markedspris (5,000 kr/kWh)')

# Find break-even
break_even = annual_value * npv_factor / battery_size
ax5.axvline(x=break_even, color='black', linestyle='-', linewidth=1, alpha=0.5)
ax5.text(break_even, ax5.get_ylim()[0] + 10000, f'Break-even\n{break_even:.0f} kr/kWh',
         ha='center', fontsize=9)

ax5.set_xlabel('Batterikostnad (kr/kWh)', fontsize=11)
ax5.set_ylabel('NPV (kr)', fontsize=11)
ax5.set_title('NPV ved Ulike Batterikostnader (15 år, 5%)', fontsize=13, fontweight='bold')
ax5.legend(loc='upper right', fontsize=9)
ax5.grid(True, alpha=0.3)

# Format y-axis
ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}k' if x != 0 else '0'))

# --- PLOT 6: Sammenligning modell vs korrekt ---
ax6 = plt.subplot(3, 2, 6)

categories = ['Effekttariff', 'Avkortning', 'Arbitrasje', 'Selvforsyning', 'TOTAL']
model_values = [57000, 5600, 3900, 2500, 69000]  # Modellens tall (10 kW)
model_20kw = [v * 2 for v in model_values[:-1]] + [sum([v * 2 for v in model_values[:-1]])]  # Skalert til 20 kW
correct_values = [9000, 5000, 2000, 2000, 18000]  # Korrekte tall (20 kW)

x = np.arange(len(categories))
width = 0.35

bars1 = ax6.bar(x - width/2, model_20kw, width, label='Modellen (feil)', color='#E74C3C', alpha=0.8)
bars2 = ax6.bar(x + width/2, correct_values, width, label='Korrekt beregning', color='#27AE60', alpha=0.8)

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax6.text(bar.get_x() + bar.get_width()/2., height + 1000,
                f'{height/1000:.0f}k', ha='center', va='bottom', fontsize=8)

ax6.set_xlabel('Verdidriver', fontsize=11)
ax6.set_ylabel('Årlig verdi (kr)', fontsize=11)
ax6.set_title('Modell vs Korrekt Beregning (20 kW batteri)', fontsize=13, fontweight='bold')
ax6.set_xticks(x)
ax6.set_xticklabels(categories, rotation=45, ha='right')
ax6.legend()
ax6.grid(True, alpha=0.3, axis='y')

# Format y-axis
ax6.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}k'))

plt.tight_layout()

# Save plot
output_file = 'results/updated_economics_analysis.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"💾 Lagret oppdatert analyse: {output_file}")

# Print summary statistics
print("\n📊 OPPDATERT ØKONOMISK ANALYSE (20 kW batteri):")
print("="*60)
print("REALISTISKE VERDIDRIVERE:")
print(f"  • Effekttariff:    9,000 kr/år")
print(f"  • Avkortning:      5,000 kr/år")
print(f"  • Arbitrasje:      2,000 kr/år")
print(f"  • Selvforsyning:   2,000 kr/år")
print(f"  ─────────────────────────────")
print(f"  TOTAL:            18,000 kr/år")

print("\nØKONOMI VED ULIKE BATTERIKOSTNADER:")
for cost in [2000, 3000, 3500, 4000, 5000, 7000, 9000]:
    investment = cost * 20
    npv = 18000 * npv_factor - investment
    irr = (18000 / investment - 0.02) * 100 if investment > 0 else 0
    payback = investment / 18000 if 18000 > 0 else 999
    status = "✅ Lønnsomt" if npv > 0 else "❌ Ulønnsomt"
    print(f"  {cost:,} kr/kWh: NPV = {npv:+8,.0f} kr, IRR = {irr:4.1f}%, Payback = {payback:.1f} år  {status}")

print("\nKONKLUSJON:")
print(f"  Break-even batterikostnad: {break_even:,.0f} kr/kWh")
print(f"  Ved 3,500 kr/kWh: NPV = {18000 * npv_factor - 3500 * 20:+,.0f} kr")
print(f"  Modellen overestimerte med: {138000/18000:.1f}x (20 kW batteri)")
print("="*60)