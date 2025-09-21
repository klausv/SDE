#!/usr/bin/env python3
"""
Visualisering av forbruksprofil for 90 MWh årlig forbruk
Viser sesongprofiler, døgnprofiler og årsvariasjon
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Bruk ikke-interaktiv backend
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import matplotlib.dates as mdates

def generate_load_profile_90mwh(n_hours=8760):
    """Generer lastprofil som summerer til NØYAKTIG 90 MWh/år"""
    # Kommersielt lastmønster
    hourly_pattern = np.array([
        0.3, 0.3, 0.3, 0.3, 0.3, 0.4,  # 00-06: Natt
        0.6, 0.8, 1.0, 1.0, 1.0, 0.9,  # 06-12: Morgen
        0.7, 0.8, 0.9, 1.0, 0.9, 0.7,  # 12-18: Ettermiddag
        0.5, 0.4, 0.3, 0.3, 0.3, 0.3   # 18-24: Kveld
    ])

    # Beregn base_load for å oppnå 90 MWh/år
    avg_pattern_factor = hourly_pattern.mean()
    target_annual_kwh = 90_000
    base_load = target_annual_kwh / (n_hours * avg_pattern_factor)

    loads = []
    timestamps = pd.date_range('2024-01-01', periods=n_hours, freq='h')

    for i in range(n_hours):
        hour = i % 24
        day = i // 24

        # Sesongvariasjon (høyere forbruk om vinteren)
        seasonal_factor = 1.0 + 0.2 * np.cos((day - 15) * 2 * np.pi / 365)

        # Helgevariasjon (lavere i helger)
        weekday = timestamps[i].weekday()
        if weekday >= 5:  # Lørdag eller søndag
            weekend_factor = 0.7
        else:
            weekend_factor = 1.0

        load = base_load * hourly_pattern[hour] * seasonal_factor * weekend_factor
        loads.append(max(1, load))

    loads = np.array(loads)

    # Juster til NØYAKTIG 90 MWh
    actual_sum = loads.sum()
    adjustment_factor = target_annual_kwh / actual_sum
    loads = loads * adjustment_factor

    return pd.Series(loads, index=timestamps)

# Generer data
print("Genererer lastprofil for 90 MWh årlig forbruk...")
load_profile = generate_load_profile_90mwh()

# Opprett figure med flere subplots
fig = plt.figure(figsize=(16, 12))
fig.suptitle('Forbruksprofil - 90 MWh Årlig Forbruk', fontsize=16, fontweight='bold')

# ==========================================
# 1. ÅRSPROFIL (daglig gjennomsnitt)
# ==========================================
ax1 = plt.subplot(3, 2, 1)
daily_avg = load_profile.resample('D').mean()
daily_max = load_profile.resample('D').max()
daily_min = load_profile.resample('D').min()

ax1.plot(daily_avg.index, daily_avg.values, 'b-', linewidth=1, label='Daglig gjennomsnitt')
ax1.fill_between(daily_avg.index, daily_min.values, daily_max.values, alpha=0.3, label='Min-Maks område')
ax1.set_title('Årsprofil - Daglige Gjennomsnitt', fontweight='bold')
ax1.set_xlabel('Måned')
ax1.set_ylabel('Effekt (kW)')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper right')
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
ax1.xaxis.set_major_locator(mdates.MonthLocator())

# ==========================================
# 2. SESONGVARIASJON (månedlig gjennomsnitt)
# ==========================================
ax2 = plt.subplot(3, 2, 2)
monthly_avg = load_profile.resample('ME').mean()
monthly_consumption = load_profile.resample('ME').sum() / 1000  # MWh

ax2_twin = ax2.twinx()
bars = ax2.bar(range(1, 13), monthly_avg.values, color='skyblue', alpha=0.7, label='Gjennomsnittlig effekt')
line = ax2_twin.plot(range(1, 13), monthly_consumption.values, 'r-', marker='o', linewidth=2, label='Månedlig forbruk')

ax2.set_title('Sesongvariasjon', fontweight='bold')
ax2.set_xlabel('Måned')
ax2.set_ylabel('Gjennomsnittlig effekt (kW)', color='b')
ax2_twin.set_ylabel('Månedlig forbruk (MWh)', color='r')
ax2.set_xticks(range(1, 13))
ax2.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des'])
ax2.grid(True, alpha=0.3)

# Legg til legendene
lines1, labels1 = ax2.get_legend_handles_labels()
lines2, labels2 = ax2_twin.get_legend_handles_labels()
ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

# ==========================================
# 3. TYPISK VINTERDØGN (januar)
# ==========================================
ax3 = plt.subplot(3, 2, 3)
winter_days = load_profile[(load_profile.index.month == 1) & (load_profile.index.weekday < 5)]
winter_hourly = winter_days.groupby(winter_days.index.hour).agg(['mean', 'min', 'max'])

ax3.plot(range(24), winter_hourly['mean'], 'b-', linewidth=2, label='Gjennomsnitt')
ax3.fill_between(range(24), winter_hourly['min'], winter_hourly['max'], alpha=0.3, label='Variasjon')
ax3.axhline(y=winter_hourly['mean'].mean(), color='r', linestyle='--', alpha=0.5, label='Døgnsnitt')
ax3.set_title('Vinterdøgn (Januar - Hverdager)', fontweight='bold')
ax3.set_xlabel('Time på døgnet')
ax3.set_ylabel('Effekt (kW)')
ax3.set_xlim(0, 23)
ax3.set_xticks(range(0, 24, 3))
ax3.grid(True, alpha=0.3)
ax3.legend()

# ==========================================
# 4. TYPISK SOMMERDØGN (juli)
# ==========================================
ax4 = plt.subplot(3, 2, 4)
summer_days = load_profile[(load_profile.index.month == 7) & (load_profile.index.weekday < 5)]
summer_hourly = summer_days.groupby(summer_days.index.hour).agg(['mean', 'min', 'max'])

ax4.plot(range(24), summer_hourly['mean'], 'orange', linewidth=2, label='Gjennomsnitt')
ax4.fill_between(range(24), summer_hourly['min'], summer_hourly['max'], alpha=0.3, color='orange', label='Variasjon')
ax4.axhline(y=summer_hourly['mean'].mean(), color='r', linestyle='--', alpha=0.5, label='Døgnsnitt')
ax4.set_title('Sommerdøgn (Juli - Hverdager)', fontweight='bold')
ax4.set_xlabel('Time på døgnet')
ax4.set_ylabel('Effekt (kW)')
ax4.set_xlim(0, 23)
ax4.set_xticks(range(0, 24, 3))
ax4.grid(True, alpha=0.3)
ax4.legend()

# ==========================================
# 5. HVERDAG VS HELG (årlig gjennomsnitt)
# ==========================================
ax5 = plt.subplot(3, 2, 5)
weekday_profile = load_profile[load_profile.index.weekday < 5].groupby(load_profile[load_profile.index.weekday < 5].index.hour).mean()
weekend_profile = load_profile[load_profile.index.weekday >= 5].groupby(load_profile[load_profile.index.weekday >= 5].index.hour).mean()

ax5.plot(range(24), weekday_profile.values, 'b-', linewidth=2, label='Hverdag', marker='o', markersize=4)
ax5.plot(range(24), weekend_profile.values, 'r--', linewidth=2, label='Helg', marker='s', markersize=4)
ax5.set_title('Døgnprofil - Hverdag vs Helg (Årsgjennomsnitt)', fontweight='bold')
ax5.set_xlabel('Time på døgnet')
ax5.set_ylabel('Effekt (kW)')
ax5.set_xlim(0, 23)
ax5.set_xticks(range(0, 24, 3))
ax5.grid(True, alpha=0.3)
ax5.legend()

# Marker arbeidsperiode
ax5.axvspan(6, 18, alpha=0.1, color='yellow', label='Arbeidstid')

# ==========================================
# 6. VARIGHETSKURVE
# ==========================================
ax6 = plt.subplot(3, 2, 6)
sorted_load = np.sort(load_profile.values)[::-1]
hours = np.arange(len(sorted_load))

ax6.plot(hours, sorted_load, 'b-', linewidth=2)
ax6.fill_between(hours, 0, sorted_load, alpha=0.3)
ax6.set_title('Varighetskurve', fontweight='bold')
ax6.set_xlabel('Timer per år')
ax6.set_ylabel('Effekt (kW)')
ax6.grid(True, alpha=0.3)

# Legg til nøkkelverdier
ax6.axhline(y=sorted_load[0], color='r', linestyle='--', alpha=0.5)
ax6.text(7000, sorted_load[0] + 0.5, f'Maks: {sorted_load[0]:.1f} kW', fontsize=9)
ax6.axhline(y=np.mean(sorted_load), color='g', linestyle='--', alpha=0.5)
ax6.text(7000, np.mean(sorted_load) + 0.5, f'Snitt: {np.mean(sorted_load):.1f} kW', fontsize=9)
ax6.axhline(y=sorted_load[-1], color='orange', linestyle='--', alpha=0.5)
ax6.text(7000, sorted_load[-1] + 0.5, f'Min: {sorted_load[-1]:.1f} kW', fontsize=9)

# Juster layout
plt.tight_layout()

# Lagre figur
plt.savefig('results/forbruksprofil_90mwh.png', dpi=300, bbox_inches='tight')
print("Figur lagret som 'results/forbruksprofil_90mwh.png'")

# Vis statistikk
print("\n" + "="*60)
print("STATISTIKK FOR FORBRUKSPROFILEN")
print("="*60)
print(f"Årlig forbruk: {load_profile.sum()/1000:.1f} MWh")
print(f"Gjennomsnittlig last: {load_profile.mean():.1f} kW")
print(f"Maksimal last: {load_profile.max():.1f} kW")
print(f"Minimal last: {load_profile.min():.1f} kW")
print(f"Lastfaktor: {load_profile.mean()/load_profile.max():.2%}")

# Månedlig statistikk
print("\nMånedlig forbruk:")
for month in range(1, 13):
    month_data = load_profile[load_profile.index.month == month]
    month_name = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des'][month-1]
    print(f"  {month_name}: {month_data.sum()/1000:>6.2f} MWh ({month_data.mean():>5.1f} kW snitt)")

# plt.show()  # Kommentert ut siden vi bruker Agg backend