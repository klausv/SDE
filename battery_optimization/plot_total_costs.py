#!/usr/bin/env python
"""
Plott kraftpris og totalkostnad inkludert nettleie
Time-for-time gjennom året
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from core.entso_e_prices import ENTSOEPrices
from core.consumption_profiles import ConsumptionProfile

print("📊 Lager plot for kraftpris og totalkostnad med nettleie...")

# Hent spotpriser for 2024 - bruk cached data
cache_file = 'data/spot_prices/NO2_2024_real.csv'
if pd.io.common.file_exists(cache_file):
    print(f"📁 Bruker cached 2024 priser: {cache_file}")
    prices_df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
    spot_prices = prices_df['price_nok'] if 'price_nok' in prices_df.columns else prices_df.iloc[:, 0]
else:
    # Fallback til ENTSO-E
    entsoe = ENTSOEPrices()
    spot_prices = entsoe.fetch_prices(year=2023, area='NO2', refresh=False)

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

# Effekttariff (basert på månedlig maksimumseffekt)
# For enkelhets skyld bruker vi gjennomsnittlig effekttariff
def calculate_power_tariff(monthly_peak_kw):
    """Beregn effekttariff basert på månedlig peak"""
    # Lnett commercial tariffer (kr/kW/måned)
    if monthly_peak_kw <= 50:
        return 90  # kr/kW/måned
    elif monthly_peak_kw <= 200:
        return 85  # kr/kW/måned
    else:
        return 80  # kr/kW/måned

# Beregn totalkostnader time for time
total_costs = []
energy_tariffs = []
spot_only = []

# Beregn månedlige peaks for effekttariff
monthly_peaks = consumption.resample('ME').max()

for ts, spot_price in spot_prices.items():
    # Spotpris
    spot_only.append(spot_price)

    # Energiledd
    energy_tariff = get_energy_tariff(ts)
    energy_tariffs.append(energy_tariff)

    # Månedlig peak for denne måneden
    month_key = f"{ts.year}-{ts.month:02d}"
    month_peaks_dict = monthly_peaks.to_dict()
    # Find the peak for this month
    month_peak = None
    for peak_ts, peak_val in month_peaks_dict.items():
        if peak_ts.strftime('%Y-%m') == month_key:
            month_peak = peak_val
            break

    if month_peak is None:
        month_peak = 30  # Default value if not found

    power_tariff_monthly = calculate_power_tariff(month_peak)

    # Konverter månedlig effekttariff til kr/kWh
    # Antar at effekttariffen fordeles på månedlig forbruk
    month_mask = (consumption.index.month == ts.month) & (consumption.index.year == ts.year)
    month_consumption = consumption[month_mask].sum()

    if month_consumption > 0:
        power_tariff_per_kwh = (power_tariff_monthly * month_peak) / month_consumption
    else:
        power_tariff_per_kwh = 0

    # Total kostnad per kWh
    total_cost = spot_price + energy_tariff + FORBRUKSAVGIFT + power_tariff_per_kwh
    total_costs.append(total_cost)

# Convert to series
spot_series = pd.Series(spot_only, index=timestamps)
total_series = pd.Series(total_costs, index=timestamps)
tariff_series = pd.Series(energy_tariffs, index=timestamps)

# Create figure with subplots
fig, axes = plt.subplots(3, 1, figsize=(18, 14))

# --- PLOT 1: Time-for-time hele året ---
ax1 = axes[0]

# Plot both series
ax1.plot(timestamps, spot_series.values, linewidth=0.5, color='blue',
         alpha=0.7, label='Spotpris')
ax1.plot(timestamps, total_series.values, linewidth=0.5, color='red',
         alpha=0.7, label='Totalkostnad (spot + nettleie)')

# Fill between for visualization
ax1.fill_between(timestamps, spot_series.values, total_series.values,
                 alpha=0.2, color='orange', label='Nettleie komponenter')

ax1.set_ylabel('Pris (NOK/kWh)', fontsize=12)
ax1.set_title('Kraftpris og totalkostnad med nettleie - Time for time 2024',
              fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper right')
ax1.set_xlim([timestamps[0], timestamps[-1]])

# Format x-axis
ax1.xaxis.set_major_locator(mdates.MonthLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b'))

# --- PLOT 2: Gjennomsnittlig døgnprofil ---
ax2 = axes[1]

# Calculate hourly averages
hourly_spot = spot_series.groupby(spot_series.index.hour).mean()
hourly_total = total_series.groupby(total_series.index.hour).mean()
hourly_tariff = tariff_series.groupby(tariff_series.index.hour).mean()

hours = range(24)
width = 0.35
x1 = np.arange(24) - width/2
x2 = np.arange(24) + width/2

# Bar plot
bars1 = ax2.bar(x1, hourly_spot.values, width, label='Spotpris',
                color='blue', alpha=0.7)
bars2 = ax2.bar(x2, hourly_total.values, width, label='Totalkostnad',
                color='red', alpha=0.7)

# Add tariff line
ax2.plot(hours, hourly_tariff.values, 'g--', linewidth=2,
         label='Energiledd', alpha=0.7)

ax2.set_xlabel('Time på døgnet', fontsize=12)
ax2.set_ylabel('Gjennomsnittspris (NOK/kWh)', fontsize=12)
ax2.set_title('Gjennomsnittlig døgnprofil - Spotpris vs Totalkostnad',
              fontsize=14, fontweight='bold')
ax2.set_xticks(range(0, 24, 2))
ax2.legend()
ax2.grid(True, alpha=0.3)

# --- PLOT 3: Månedlig sammenligning ---
ax3 = axes[2]

# Monthly averages
monthly_spot = spot_series.resample('ME').mean()
monthly_total = total_series.resample('ME').mean()
monthly_diff = monthly_total - monthly_spot

months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
          'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']

x = np.arange(len(months))
width = 0.35

# Stacked bar chart
bars1 = ax3.bar(x, monthly_spot.values, width, label='Spotpris',
                color='blue', alpha=0.7)
bars2 = ax3.bar(x, monthly_diff.values, width, bottom=monthly_spot.values,
                label='Nettleie (inkl. alle avgifter)', color='orange', alpha=0.7)

# Add values on bars
for i, (spot, total) in enumerate(zip(monthly_spot.values, monthly_total.values)):
    ax3.text(i, spot/2, f'{spot:.2f}', ha='center', va='center',
             fontsize=9, color='white', fontweight='bold')
    ax3.text(i, total + 0.05, f'{total:.2f}', ha='center', va='bottom',
             fontsize=9)

ax3.set_xlabel('Måned', fontsize=12)
ax3.set_ylabel('Pris (NOK/kWh)', fontsize=12)
ax3.set_title('Månedlig gjennomsnitt - Spotpris og totalkostnad',
              fontsize=14, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels(months)
ax3.legend()
ax3.grid(True, alpha=0.3)

plt.tight_layout()

# Save plot
output_file = 'results/total_costs_2024.png'
plt.savefig(output_file, dpi=150, bbox_inches='tight')
print(f"💾 Lagret plot: {output_file}")

# Print statistics
print("\n📊 KOSTNADSSTATISTIKK 2024:")
print("="*60)

print("\nÅRSGJENNOMSNITT:")
print(f"  Spotpris:                    {spot_series.mean():.3f} NOK/kWh")
print(f"  Energiledd (nettleie):       {tariff_series.mean():.3f} NOK/kWh")
print(f"  Forbruksavgift:              {FORBRUKSAVGIFT:.3f} NOK/kWh")
print(f"  Totalkostnad:                {total_series.mean():.3f} NOK/kWh")
print(f"  Nettleie andel:              {((total_series.mean()-spot_series.mean())/total_series.mean()*100):.1f}%")

print("\nVARIASJON:")
print(f"  Spotpris min/max:            {spot_series.min():.2f} - {spot_series.max():.2f} NOK/kWh")
print(f"  Totalkostnad min/max:        {total_series.min():.2f} - {total_series.max():.2f} NOK/kWh")

print("\nPEAK VS OFF-PEAK (gjennomsnitt):")
# Peak hours mask
peak_mask = [(ts.weekday() < 5 and 6 <= ts.hour < 22) for ts in timestamps]
offpeak_mask = [not p for p in peak_mask]

print(f"  Peak timer (hverdager 06-22):")
print(f"    Spotpris:                  {spot_series[peak_mask].mean():.3f} NOK/kWh")
print(f"    Totalkostnad:              {total_series[peak_mask].mean():.3f} NOK/kWh")
print(f"  Off-peak timer:")
print(f"    Spotpris:                  {spot_series[offpeak_mask].mean():.3f} NOK/kWh")
print(f"    Totalkostnad:              {total_series[offpeak_mask].mean():.3f} NOK/kWh")

print("\nMÅNEDLIG DETALJER:")
print("Måned  | Spot  | Nettleie | Total | Økning")
print("-------|-------|----------|-------|--------")
for i, month in enumerate(months):
    spot = monthly_spot.iloc[i]
    total = monthly_total.iloc[i]
    diff = total - spot
    increase = (total/spot - 1) * 100
    print(f"{month:6s} | {spot:.3f} | {diff:.3f}    | {total:.3f} | +{increase:.1f}%")

print("="*60)