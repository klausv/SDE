#!/usr/bin/env python
"""
Plotter simuleringsresultater fra batterioptimalisering
Viser produksjon, forbruk, SOC og priser over hele året
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from core.pvgis_solar import PVGISProduction
from core.entso_e_prices import ENTSOEPrices
from core.optimizer import BatteryOptimizer

# Settings for nice plots
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (20, 12)
plt.rcParams['font.size'] = 10

print("📊 Genererer simuleringsdata...")

# 1. Load data (samme som run_analysis.py)
pvgis = PVGISProduction(lat=58.97, lon=5.73, pv_capacity_kwp=138.55)
production = pvgis.fetch_hourly_production(year=2020)

# Generate consumption
n_hours = len(production)
hourly_pattern = np.array([
    0.3, 0.3, 0.3, 0.3, 0.3, 0.4,  # Night
    0.6, 0.8, 1.0, 1.0, 1.0, 0.9,  # Morning
    0.7, 0.8, 0.9, 1.0, 0.9, 0.7,  # Afternoon
    0.5, 0.4, 0.3, 0.3, 0.3, 0.3   # Evening
])
base_load = 90000 / 8760 / 0.6
consumption_values = [base_load * hourly_pattern[i % 24] for i in range(n_hours)]
consumption = pd.Series(consumption_values, index=production.index, name='consumption_kw')

# Load prices
entsoe = ENTSOEPrices()
prices = entsoe.fetch_prices(year=2023, area='NO2')
if len(prices) != len(production):
    if len(prices) > len(production):
        prices = prices[:len(production)]
    else:
        extra_prices = pd.Series([prices.iloc[-1]] * (len(production) - len(prices)))
        prices = pd.concat([prices, extra_prices])
prices = pd.Series(prices.values, index=production.index, name='spot_price_nok')

# 2. Run simulation with optimal battery (20 kWh @ 10 kW)
print("🔋 Kjører batterisimulering (20 kWh @ 10 kW)...")
optimizer = BatteryOptimizer(grid_limit_kw=77, efficiency=0.95)
operation = optimizer._simulate_battery_operation(
    production=production,
    consumption=consumption,
    spot_prices=prices,
    capacity_kwh=20,
    power_kw=10
)

# 3. Calculate realized price for solar power
# This is the effective price/value the solar power achieves
realized_price = []
for i in range(len(operation)):
    prod = operation['production'].iloc[i]
    cons = operation['consumption'].iloc[i]
    spot = operation['spot_price'].iloc[i]

    if prod > 0:
        if prod <= cons:
            # All production is self-consumed
            # Value = spot price + avoided grid tariff (ca 0.30 NOK/kWh for Lnett)
            price = spot + 0.30
        else:
            # Mix of self-consumption and export
            self_consumed = cons
            exported = prod - cons

            # Weighted average price
            if exported > 0:
                # Export gets spot price (minus small fee)
                export_price = spot - 0.02  # Small export fee
                self_cons_price = spot + 0.30  # Avoided grid costs

                # Weighted average
                price = (self_consumed * self_cons_price + exported * export_price) / prod
            else:
                price = spot + 0.30
    else:
        # No production
        price = spot

    realized_price.append(price)

operation['realized_price'] = realized_price

# 4. Create plots
print("📈 Lager plots...")

# Convert index to datetime for better x-axis
operation.index = pd.to_datetime(operation.index)

# Create figure with 4 subplots
fig, axes = plt.subplots(4, 1, figsize=(20, 16), sharex=True)

# --- PLOT 1: Production, Consumption and SOC ---
ax1 = axes[0]
ax1.fill_between(operation.index, 0, operation['production'], alpha=0.3, color='orange', label='Produksjon')
ax1.plot(operation.index, operation['consumption'], color='blue', linewidth=1, label='Forbruk')
ax1.plot(operation.index, operation['soc'], color='green', linewidth=2, label='Batteri SOC')
ax1.set_ylabel('kW / kWh', fontsize=12)
ax1.legend(loc='upper right')
ax1.set_title('Solproduksjon, Forbruk og Batteri-SOC over året', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.set_ylim([0, max(operation['production'].max(), 130)])

# --- PLOT 2: Battery Charge/Discharge ---
ax2 = axes[1]
ax2.bar(operation.index, operation['charge'], width=0.04, color='green', alpha=0.5, label='Lading')
ax2.bar(operation.index, -operation['discharge'], width=0.04, color='red', alpha=0.5, label='Utlading')
ax2.axhline(y=0, color='black', linewidth=0.5)
ax2.set_ylabel('kW', fontsize=12)
ax2.legend(loc='upper right')
ax2.set_title('Batterilading og -utlading', fontsize=14, fontweight='bold')
ax2.grid(True, alpha=0.3)

# --- PLOT 3: Grid Import/Export ---
ax3 = axes[2]
ax3.fill_between(operation.index, 0, operation['grid_export'], alpha=0.5, color='green', label='Eksport til nett')
ax3.fill_between(operation.index, 0, -operation['grid_import'], alpha=0.5, color='red', label='Import fra nett')
ax3.axhline(y=0, color='black', linewidth=0.5)
ax3.set_ylabel('kW', fontsize=12)
ax3.legend(loc='upper right')
ax3.set_title('Nett-eksport og -import', fontsize=14, fontweight='bold')
ax3.grid(True, alpha=0.3)

# --- PLOT 4: Prices (dual y-axis) ---
ax4 = axes[3]
color1 = 'tab:blue'
ax4.plot(operation.index, operation['spot_price'], color=color1, linewidth=1, label='Spotpris', alpha=0.7)
ax4.set_ylabel('Spotpris (NOK/kWh)', color=color1, fontsize=12)
ax4.tick_params(axis='y', labelcolor=color1)
ax4.set_xlabel('Dato', fontsize=12)

# Second y-axis for realized price
ax4_2 = ax4.twinx()
color2 = 'tab:orange'
ax4_2.plot(operation.index, operation['realized_price'], color=color2, linewidth=1, label='Realisert pris', alpha=0.7)
ax4_2.set_ylabel('Realisert solkraftpris (NOK/kWh)', color=color2, fontsize=12)
ax4_2.tick_params(axis='y', labelcolor=color2)

ax4.set_title('Spotpris og realisert pris for solkraft', fontsize=14, fontweight='bold')
ax4.grid(True, alpha=0.3)
ax4.legend(loc='upper left')
ax4_2.legend(loc='upper right')

# Format x-axis
for ax in axes:
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax.xaxis.set_minor_locator(mdates.WeekdayLocator())

plt.tight_layout()

# Save and show
output_file = 'results/battery_simulation_full_year.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"💾 Lagret plot: {output_file}")

# --- Additional plot: Zoom in on one week ---
print("📊 Lager detaljplot for en uke...")

# Select a week in July (summer) for detail
week_start = pd.Timestamp('2020-07-06')
week_end = pd.Timestamp('2020-07-13')
week_data = operation[(operation.index >= week_start) & (operation.index < week_end)]

fig2, axes2 = plt.subplots(3, 1, figsize=(20, 12), sharex=True)

# Plot 1: Production, Consumption, SOC
ax1 = axes2[0]
ax1.fill_between(week_data.index, 0, week_data['production'], alpha=0.3, color='orange', label='Produksjon')
ax1.plot(week_data.index, week_data['consumption'], 'b-', linewidth=2, label='Forbruk')
ax1.plot(week_data.index, week_data['soc'], 'g-', linewidth=2, label='Batteri SOC')
ax1.set_ylabel('kW / kWh', fontsize=12)
ax1.legend(loc='upper right')
ax1.set_title('Uke 28 (6-12 juli 2020) - Detaljvisning', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)

# Plot 2: Battery activity
ax2 = axes2[1]
ax2.bar(week_data.index, week_data['charge'], width=0.02, color='green', alpha=0.7, label='Lading')
ax2.bar(week_data.index, -week_data['discharge'], width=0.02, color='red', alpha=0.7, label='Utlading')
ax2.axhline(y=0, color='black', linewidth=0.5)
ax2.set_ylabel('kW', fontsize=12)
ax2.legend(loc='upper right')
ax2.set_title('Batterilading og -utlading', fontsize=12)
ax2.grid(True, alpha=0.3)

# Plot 3: Prices
ax3 = axes2[2]
ax3.plot(week_data.index, week_data['spot_price'], 'b-', linewidth=2, label='Spotpris')
ax3_2 = ax3.twinx()
ax3_2.plot(week_data.index, week_data['realized_price'], 'orange', linewidth=2, label='Realisert pris')
ax3.set_ylabel('Spotpris (NOK/kWh)', color='blue', fontsize=12)
ax3_2.set_ylabel('Realisert pris (NOK/kWh)', color='orange', fontsize=12)
ax3.set_xlabel('Dato og tid', fontsize=12)
ax3.legend(loc='upper left')
ax3_2.legend(loc='upper right')
ax3.grid(True, alpha=0.3)

# Format x-axis
for ax in axes2:
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%a %d.%m'))
    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))

plt.tight_layout()

output_file2 = 'results/battery_simulation_week_detail.png'
plt.savefig(output_file2, dpi=150, bbox_inches='tight')
print(f"💾 Lagret detaljplot: {output_file2}")

# Print statistics
print("\n📊 SIMULERINGSSTATISTIKK:")
print(f"   • Total produksjon: {operation['production'].sum()/1000:.1f} MWh")
print(f"   • Total forbruk: {operation['consumption'].sum()/1000:.1f} MWh")
print(f"   • Total eksport: {operation['grid_export'].sum()/1000:.1f} MWh")
print(f"   • Total import: {operation['grid_import'].sum()/1000:.1f} MWh")
print(f"   • Total lading: {operation['charge'].sum()/1000:.1f} MWh")
print(f"   • Total utlading: {operation['discharge'].sum()/1000:.1f} MWh")
print(f"   • Avkortning: {operation['curtailment'].sum()/1000:.1f} MWh")
print(f"   • Gjennomsnittlig SOC: {operation['soc'].mean():.1f} kWh ({operation['soc'].mean()/20*100:.0f}%)")
print(f"   • Gjennomsnittlig spotpris: {operation['spot_price'].mean():.2f} NOK/kWh")
print(f"   • Gjennomsnittlig realisert pris: {operation['realized_price'].mean():.2f} NOK/kWh")

print("\n✅ Plots ferdig!")