#!/usr/bin/env python
"""
Plott kraftpris og totalkostnad inkludert nettleie
Med detaljert stacked bar for døgnprofil
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from core.consumption_profiles import ConsumptionProfile

print("📊 Lager detaljert plot for kraftpris og totalkostnad med nettleie...")

# Hent spotpriser for 2024 - bruk cached data
cache_file = 'data/spot_prices/NO2_2024_real.csv'
if pd.io.common.file_exists(cache_file):
    print(f"📁 Bruker cached 2024 priser: {cache_file}")
    prices_df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
    spot_prices = prices_df['price_nok'] if 'price_nok' in prices_df.columns else prices_df.iloc[:, 0]
else:
    print("❌ Ingen cached 2024 priser funnet!")
    exit(1)

# Generer forbruksprofil (commercial office)
consumption = ConsumptionProfile.generate_annual_profile(
    profile_type='commercial_office',
    annual_kwh=90000,
    year=2024
)

# Align indices
if len(spot_prices) != len(consumption):
    min_len = min(len(spot_prices), len(consumption))
    spot_prices = spot_prices[:min_len]
    consumption = consumption[:min_len]

# Create timestamps
timestamps = pd.date_range('2024-01-01', periods=len(spot_prices), freq='h')
spot_prices.index = timestamps
consumption.index = timestamps

# --- LNETT COMMERCIAL TARIFFER (2024) ---
# Energiledd (varierer med tid på døgnet og sesong)
def get_energy_tariff(timestamp):
    """Hent energiledd basert på tid og sesong"""
    hour = timestamp.hour
    month = timestamp.month
    weekday = timestamp.weekday()

    # Sommer (april-september) vs vinter (oktober-mars)
    is_summer = 4 <= month <= 9

    # Peak hours: man-fre 06:00-22:00
    is_peak = weekday < 5 and 6 <= hour < 22

    if is_summer:
        # Sommer
        return 0.176 if not is_peak else 0.296  # kr/kWh
    else:
        # Vinter - høyere tariffer
        return 0.216 if not is_peak else 0.396  # kr/kWh

# Forbruksavgift (fast)
FORBRUKSAVGIFT = 0.1591  # kr/kWh inkl mva

# Effekttariff per kW
def get_power_tariff_per_kw():
    """Hent effekttariff kr per kW per måned"""
    # Gjennomsnittlig for kommersielle kunder
    return 85  # kr/kW/måned

# Beregn alle komponenter time for time
components_data = []

for ts, spot_price in spot_prices.items():
    hour_consumption = consumption[ts]  # kW (siden det er per time = kWh)

    # Spotpris
    spot_component = spot_price

    # Energiledd nettleie
    energy_tariff = get_energy_tariff(ts)

    # Forbruksavgift
    consumption_tax = FORBRUKSAVGIFT

    # Effektledd - basert på faktisk kW forbruk denne timen
    # Konverter månedlig tariff til kr/kWh
    # 85 kr/kW/måned ÷ 730 timer/måned ≈ 0.116 kr/kWh
    power_tariff_per_kwh = (get_power_tariff_per_kw() / 730) * (hour_consumption / 10)  # Skalert til forbruk

    components_data.append({
        'timestamp': ts,
        'hour': ts.hour,
        'spotpris': spot_component,
        'forbruksavgift': consumption_tax,
        'energiledd': energy_tariff,
        'effektledd': power_tariff_per_kwh,
        'total': spot_component + consumption_tax + energy_tariff + power_tariff_per_kwh,
        'consumption_kw': hour_consumption
    })

# Create DataFrame
df = pd.DataFrame(components_data)

# Create figure with subplots
fig, axes = plt.subplots(3, 1, figsize=(18, 14))

# --- PLOT 1: Time-for-time hele året ---
ax1 = axes[0]

# Plot both series
ax1.plot(df['timestamp'], df['spotpris'], linewidth=0.5, color='blue',
         alpha=0.7, label='Spotpris')
ax1.plot(df['timestamp'], df['total'], linewidth=0.5, color='red',
         alpha=0.7, label='Totalkostnad (alle komponenter)')

# Fill between for visualization
ax1.fill_between(df['timestamp'], df['spotpris'], df['total'],
                 alpha=0.2, color='orange', label='Nettleie og avgifter')

ax1.set_ylabel('Pris (NOK/kWh)', fontsize=12)
ax1.set_title('Kraftpris og totalkostnad med nettleie - Time for time 2024',
              fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper right')
ax1.set_xlim([df['timestamp'].iloc[0], df['timestamp'].iloc[-1]])

# Format x-axis
ax1.xaxis.set_major_locator(mdates.MonthLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b'))

# --- PLOT 2: Gjennomsnittlig døgnprofil - STACKED BAR ---
ax2 = axes[1]

# Calculate hourly averages for each component
hourly_avg = df.groupby('hour')[['spotpris', 'forbruksavgift', 'energiledd', 'effektledd']].mean()

hours = range(24)
width = 0.8

# Create stacked bar chart
p1 = ax2.bar(hours, hourly_avg['spotpris'], width,
             label='Spotpris', color='#2E86AB', alpha=0.9)
p2 = ax2.bar(hours, hourly_avg['forbruksavgift'], width,
             bottom=hourly_avg['spotpris'],
             label='Forbruksavgift (elavgift)', color='#A23B72', alpha=0.9)
p3 = ax2.bar(hours, hourly_avg['energiledd'], width,
             bottom=hourly_avg['spotpris'] + hourly_avg['forbruksavgift'],
             label='Energiledd nettleie', color='#F18F01', alpha=0.9)
p4 = ax2.bar(hours, hourly_avg['effektledd'], width,
             bottom=hourly_avg['spotpris'] + hourly_avg['forbruksavgift'] + hourly_avg['energiledd'],
             label='Effektledd nettleie', color='#C73E1D', alpha=0.9)

# Add total line
hourly_total = hourly_avg.sum(axis=1)
ax2.plot(hours, hourly_total, 'k--', linewidth=2, label='Total', alpha=0.6)

# Add value labels for peak hours
peak_hours = [8, 12, 17, 20]
for h in peak_hours:
    total = hourly_total.iloc[h]
    ax2.text(h, total + 0.02, f'{total:.2f}', ha='center', va='bottom',
             fontsize=8, fontweight='bold')

ax2.set_xlabel('Time på døgnet', fontsize=12)
ax2.set_ylabel('Pris (NOK/kWh)', fontsize=12)
ax2.set_title('Gjennomsnittlig døgnprofil - Detaljert kostnadsfordeling',
              fontsize=14, fontweight='bold')
ax2.set_xticks(range(0, 24, 2))
ax2.legend(loc='upper right', ncol=2)
ax2.grid(True, alpha=0.3, axis='y')

# --- PLOT 3: Månedlig sammenligning med komponenter ---
ax3 = axes[2]

# Add month column
df['month'] = df['timestamp'].dt.month

# Monthly averages per component
monthly_avg = df.groupby('month')[['spotpris', 'forbruksavgift', 'energiledd', 'effektledd']].mean()

months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
          'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']

x = np.arange(len(months))
width = 0.6

# Stacked bar chart
p1 = ax3.bar(x, monthly_avg['spotpris'], width,
             label='Spotpris', color='#2E86AB', alpha=0.9)
p2 = ax3.bar(x, monthly_avg['forbruksavgift'], width,
             bottom=monthly_avg['spotpris'],
             label='Forbruksavgift', color='#A23B72', alpha=0.9)
p3 = ax3.bar(x, monthly_avg['energiledd'], width,
             bottom=monthly_avg['spotpris'] + monthly_avg['forbruksavgift'],
             label='Energiledd', color='#F18F01', alpha=0.9)
p4 = ax3.bar(x, monthly_avg['effektledd'], width,
             bottom=monthly_avg['spotpris'] + monthly_avg['forbruksavgift'] + monthly_avg['energiledd'],
             label='Effektledd', color='#C73E1D', alpha=0.9)

# Add total values on top
monthly_total = monthly_avg.sum(axis=1)
for i, total in enumerate(monthly_total):
    ax3.text(i, total + 0.02, f'{total:.2f}', ha='center', va='bottom',
             fontsize=9)

ax3.set_xlabel('Måned', fontsize=12)
ax3.set_ylabel('Pris (NOK/kWh)', fontsize=12)
ax3.set_title('Månedlig gjennomsnitt - Detaljert kostnadsfordeling',
              fontsize=14, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels(months)
ax3.legend(loc='upper right', ncol=2)
ax3.grid(True, alpha=0.3, axis='y')

plt.tight_layout()

# Save plot
output_file = 'results/total_costs_detailed_2024.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"💾 Lagret plot: {output_file}")

# Print detailed statistics
print("\n📊 DETALJERT KOSTNADSSTATISTIKK 2024:")
print("="*60)

print("\nÅRSGJENNOMSNITT PER KOMPONENT:")
yearly_avg = df[['spotpris', 'forbruksavgift', 'energiledd', 'effektledd']].mean()
yearly_total = yearly_avg.sum()

print(f"  Spotpris:              {yearly_avg['spotpris']:.3f} NOK/kWh ({yearly_avg['spotpris']/yearly_total*100:.1f}%)")
print(f"  Forbruksavgift:        {yearly_avg['forbruksavgift']:.3f} NOK/kWh ({yearly_avg['forbruksavgift']/yearly_total*100:.1f}%)")
print(f"  Energiledd nettleie:   {yearly_avg['energiledd']:.3f} NOK/kWh ({yearly_avg['energiledd']/yearly_total*100:.1f}%)")
print(f"  Effektledd nettleie:   {yearly_avg['effektledd']:.3f} NOK/kWh ({yearly_avg['effektledd']/yearly_total*100:.1f}%)")
print(f"  TOTALKOSTNAD:          {yearly_total:.3f} NOK/kWh (100%)")

print("\nDØGNVARIASJON (timer med høyest/lavest kostnad):")
hourly_summary = hourly_avg.sum(axis=1).sort_values()
print(f"  Billigste time:  kl {hourly_summary.index[0]:02d}:00 - {hourly_summary.iloc[0]:.3f} NOK/kWh")
print(f"  Dyreste time:    kl {hourly_summary.index[-1]:02d}:00 - {hourly_summary.iloc[-1]:.3f} NOK/kWh")
print(f"  Forskjell:       {hourly_summary.iloc[-1] - hourly_summary.iloc[0]:.3f} NOK/kWh")

print("\nPEAK HOURS DETALJER (hverdager 06:00-22:00):")
peak_mask = df['timestamp'].apply(lambda x: x.weekday() < 5 and 6 <= x.hour < 22)
peak_avg = df[peak_mask][['spotpris', 'forbruksavgift', 'energiledd', 'effektledd']].mean()
print(f"  Spotpris:        {peak_avg['spotpris']:.3f} NOK/kWh")
print(f"  Forbruksavgift:  {peak_avg['forbruksavgift']:.3f} NOK/kWh")
print(f"  Energiledd:      {peak_avg['energiledd']:.3f} NOK/kWh")
print(f"  Effektledd:      {peak_avg['effektledd']:.3f} NOK/kWh")
print(f"  Total peak:      {peak_avg.sum():.3f} NOK/kWh")

print("\nOFF-PEAK DETALJER:")
offpeak_avg = df[~peak_mask][['spotpris', 'forbruksavgift', 'energiledd', 'effektledd']].mean()
print(f"  Spotpris:        {offpeak_avg['spotpris']:.3f} NOK/kWh")
print(f"  Forbruksavgift:  {offpeak_avg['forbruksavgift']:.3f} NOK/kWh")
print(f"  Energiledd:      {offpeak_avg['energiledd']:.3f} NOK/kWh")
print(f"  Effektledd:      {offpeak_avg['effektledd']:.3f} NOK/kWh")
print(f"  Total off-peak:  {offpeak_avg.sum():.3f} NOK/kWh")

print("\nSESSONGVARIASJON:")
# Vinter vs sommer
winter_mask = df['month'].isin([12, 1, 2])
summer_mask = df['month'].isin([6, 7, 8])

winter_avg = df[winter_mask][['spotpris', 'forbruksavgift', 'energiledd', 'effektledd']].mean()
summer_avg = df[summer_mask][['spotpris', 'forbruksavgift', 'energiledd', 'effektledd']].mean()

print(f"  Vinter total:    {winter_avg.sum():.3f} NOK/kWh")
print(f"  Sommer total:    {summer_avg.sum():.3f} NOK/kWh")
print(f"  Forskjell:       {winter_avg.sum() - summer_avg.sum():.3f} NOK/kWh")

print("="*60)