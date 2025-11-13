#!/usr/bin/env python3
"""
Visualisering av nettariff-struktur for Snødevegen-prosjektet.
Viser trappekurve for Lnett bedriftstariff.
"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Output directory
output_dir = Path('results/battery_dimensioning_PT60M/plots')
output_dir.mkdir(parents=True, exist_ok=True)

# Tariff structure (Lnett bedrift)
# Format: (upper_limit_kw, price_nok_per_kw_per_month)
tariff_brackets = [
    (50, 48),
    (100, 52),
    (200, 63),
    (300, 121),
    (500, 213)  # Extended beyond 300 for visualization
]

# Create power range for plotting
power_levels = np.linspace(0, 350, 1000)

# Calculate tariff for each power level (using marginal rate approach)
def calculate_marginal_tariff(power_kw):
    """Calculate marginal tariff rate for given power level."""
    for upper_limit, price in tariff_brackets:
        if power_kw <= upper_limit:
            return price
    return tariff_brackets[-1][1]  # Return highest rate for power above max

tariff_values = [calculate_marginal_tariff(p) for p in power_levels]

# Create figure with two subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# =============================
# Left plot: Marginal tariff (step function)
# =============================
ax1.plot(power_levels, tariff_values, linewidth=2.5, color='#2E86AB', drawstyle='steps-post')
ax1.fill_between(power_levels, 0, tariff_values, alpha=0.2, color='#2E86AB', step='post')

# Add vertical lines at boundaries
for upper_limit, _ in tariff_brackets[:-1]:
    ax1.axvline(upper_limit, color='gray', linestyle='--', alpha=0.4, linewidth=1)

# Annotate price levels
for i, (upper_limit, price) in enumerate(tariff_brackets):
    if i == 0:
        x_pos = upper_limit / 2
    else:
        x_pos = (tariff_brackets[i-1][0] + upper_limit) / 2

    ax1.annotate(
        f'{price} kr/kW/mnd',
        xy=(x_pos, price),
        xytext=(0, 10),
        textcoords='offset points',
        ha='center',
        fontsize=10,
        fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='gray', alpha=0.8)
    )

ax1.set_xlabel('Månedens makseffekt (kW)', fontsize=12, fontweight='bold')
ax1.set_ylabel('Marginal nettariff (NOK/kW/mnd)', fontsize=12, fontweight='bold')
ax1.set_title('Marginal Nettariff - Lnett Bedrift\n(Trinn for hver effektgrense)', fontsize=13, fontweight='bold')
ax1.grid(True, alpha=0.3, linestyle='--')
ax1.set_xlim(0, 350)
ax1.set_ylim(0, 230)

# =============================
# Right plot: Total monthly cost
# =============================
def calculate_total_cost(peak_power_kw):
    """Calculate total monthly power tariff cost using progressive brackets."""
    total_cost = 0
    remaining_power = peak_power_kw

    previous_limit = 0
    for upper_limit, price in tariff_brackets:
        if remaining_power <= 0:
            break

        # Power in this bracket
        power_in_bracket = min(remaining_power, upper_limit - previous_limit)
        total_cost += power_in_bracket * price

        remaining_power -= power_in_bracket
        previous_limit = upper_limit

    return total_cost

total_costs = [calculate_total_cost(p) for p in power_levels]

ax2.plot(power_levels, total_costs, linewidth=2.5, color='#A23B72')
ax2.fill_between(power_levels, 0, total_costs, alpha=0.2, color='#A23B72')

# Add reference lines for common power levels
reference_levels = [50, 77, 100, 200, 300]
for ref_power in reference_levels:
    ref_cost = calculate_total_cost(ref_power)
    ax2.axvline(ref_power, color='gray', linestyle='--', alpha=0.3, linewidth=1)
    ax2.plot(ref_power, ref_cost, 'o', markersize=8, color='#A23B72', zorder=5)

    if ref_power == 77:
        # Highlight the grid limit
        ax2.annotate(
            f'Nettgrense\n{ref_power} kW\n{ref_cost:.0f} kr/mnd',
            xy=(ref_power, ref_cost),
            xytext=(20, 20),
            textcoords='offset points',
            ha='left',
            fontsize=10,
            fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', edgecolor='orange', alpha=0.9),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.3', color='orange', lw=2)
        )

ax2.set_xlabel('Månedens makseffekt (kW)', fontsize=12, fontweight='bold')
ax2.set_ylabel('Total månedlig nettariff (NOK/mnd)', fontsize=12, fontweight='bold')
ax2.set_title('Total Månedlig Kostnad - Lnett Bedrift\n(Progressiv beregning)', fontsize=13, fontweight='bold')
ax2.grid(True, alpha=0.3, linestyle='--')
ax2.set_xlim(0, 350)

# Add info box
info_text = (
    'NETTARIFF BEREGNING\n'
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
    'Trinn 1 (0-50 kW):      48 kr/kW\n'
    'Trinn 2 (50-100 kW):    52 kr/kW\n'
    'Trinn 3 (100-200 kW):   63 kr/kW\n'
    'Trinn 4 (200-300 kW):  121 kr/kW\n'
    'Trinn 5 (>300 kW):     213 kr/kW\n'
    '━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
    'Progressiv: Betaler kun\n'
    'høyere pris for effekt\n'
    'over hver grense'
)

ax2.text(
    0.98, 0.97,
    info_text,
    transform=ax2.transAxes,
    fontsize=9,
    verticalalignment='top',
    horizontalalignment='right',
    bbox=dict(boxstyle='round,pad=0.8', facecolor='lightgray', edgecolor='black', alpha=0.9),
    family='monospace'
)

plt.tight_layout()

# Save figure
output_file = output_dir / 'nettariff_struktur.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"✓ Lagret: {output_file}")

plt.show()
