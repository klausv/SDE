"""
Beregn avkortning (curtailment) for solcelleanlegget
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

print("\n" + "="*60)
print("BEREGNING AV AVKORTNING (CURTAILMENT)")
print("="*60)

# Anleggsparametere
pv_capacity_kwp = 138.55  # kWp
inverter_capacity_kw = 110  # kW
grid_export_limit_kw = 77  # kW (70% av inverter)

print("\n📊 ANLEGGSDATA:")
print("-" * 40)
print(f"Solcelleanlegg: {pv_capacity_kwp} kWp")
print(f"Inverter: {inverter_capacity_kw} kW")
print(f"Netteksport grense: {grid_export_limit_kw} kW")

# Simuler timesproduksjon for et år (8760 timer)
# Bruk realistisk produksjonsprofil for Stavanger
hours_in_year = 8760
hourly_production = np.zeros(hours_in_year)

# Generer realistisk produksjonsprofil
for hour in range(hours_in_year):
    day_of_year = hour // 24
    hour_of_day = hour % 24

    # Sesongvariasjon (sommer høy, vinter lav)
    seasonal_factor = 0.5 + 0.5 * np.sin((day_of_year - 80) * 2 * np.pi / 365)

    # Daglig variasjon (sol midt på dagen)
    if 5 <= hour_of_day <= 20:  # Sol mellom 05:00 og 20:00
        sun_angle = np.sin((hour_of_day - 5) * np.pi / 15)
        daily_factor = max(0, sun_angle)
    else:
        daily_factor = 0

    # Skydekkevariasjon (tilfeldig)
    cloud_factor = 0.3 + 0.7 * np.random.random()

    # Beregn produksjon
    max_possible = pv_capacity_kwp  # kW
    production = max_possible * seasonal_factor * daily_factor * cloud_factor

    # Begrens til inverter kapasitet
    production = min(production, inverter_capacity_kw)

    hourly_production[hour] = production

# Finn timer med produksjon over nettgrensen
hours_above_limit = hourly_production > grid_export_limit_kw
curtailed_hours = np.sum(hours_above_limit)

# Beregn avkortning
curtailment_per_hour = np.maximum(0, hourly_production - grid_export_limit_kw)
total_curtailment_kwh = np.sum(curtailment_per_hour)

# Beregn total produksjon og prosent avkortet
total_production_kwh = np.sum(hourly_production)
curtailment_percentage = (total_curtailment_kwh / total_production_kwh) * 100

print("\n⚡ PRODUKSJONSSTATISTIKK:")
print("-" * 40)
print(f"Total årsproduksjon: {total_production_kwh:,.0f} kWh")
print(f"Maks timeproduksjon: {np.max(hourly_production):.1f} kW")
print(f"Timer over {grid_export_limit_kw} kW: {curtailed_hours:,} timer ({curtailed_hours/8760*100:.1f}%)")

print("\n🚫 AVKORTNING (CURTAILMENT):")
print("-" * 40)
print(f"Total avkortet energi: {total_curtailment_kwh:,.0f} kWh/år")
print(f"Andel av produksjon: {curtailment_percentage:.1f}%")
print(f"Gjennomsnittlig avkortning per time: {np.mean(curtailment_per_hour[hours_above_limit]):.1f} kW")
print(f"Maks avkortning i en time: {np.max(curtailment_per_hour):.1f} kW")

# Beregn økonomisk tap
spot_price_avg = 0.50  # NOK/kWh gjennomsnittlig spotpris
feed_in_tariff = 0.05  # NOK/kWh nettleie ved innmating
total_price = spot_price_avg - feed_in_tariff  # 0.45 NOK/kWh

economic_loss = total_curtailment_kwh * total_price

print("\n💰 ØKONOMISK TAP FRA AVKORTNING:")
print("-" * 40)
print(f"Spotpris (snitt): {spot_price_avg:.2f} NOK/kWh")
print(f"Nettleie innmating: -{feed_in_tariff:.2f} NOK/kWh")
print(f"Netto inntekt: {total_price:.2f} NOK/kWh")
print(f"Årlig tap: {economic_loss:,.0f} NOK")

# Månedlig fordeling
monthly_curtailment = []
monthly_production = []
months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
          'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des']

for month in range(12):
    if month in [0, 1, 10, 11]:  # Jan, Feb, Nov, Des
        days_in_month = 30
    elif month == 1:  # Februar
        days_in_month = 28
    else:
        days_in_month = 31 if month in [0, 2, 4, 6, 7, 9, 11] else 30

    start_hour = sum([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][:month]) * 24
    end_hour = start_hour + days_in_month * 24

    month_production = np.sum(hourly_production[start_hour:end_hour])
    month_curtailment = np.sum(curtailment_per_hour[start_hour:end_hour])

    monthly_production.append(month_production)
    monthly_curtailment.append(month_curtailment)

print("\n📅 MÅNEDLIG AVKORTNING:")
print("-" * 40)
print("Måned | Produksjon | Avkortning | %")
print("-" * 40)
for i, month in enumerate(months):
    prod = monthly_production[i] if i < len(monthly_production) else 0
    curt = monthly_curtailment[i] if i < len(monthly_curtailment) else 0
    pct = (curt / prod * 100) if prod > 0 else 0
    print(f"{month:5} | {prod:9,.0f} | {curt:10,.0f} | {pct:4.1f}%")

# Varighetskurve for produksjon
sorted_production = np.sort(hourly_production)[::-1]
hours_above_77kw = np.sum(sorted_production > 77)
hours_above_90kw = np.sum(sorted_production > 90)
hours_above_100kw = np.sum(sorted_production > 100)

print("\n📈 VARIGHETSKURVE:")
print("-" * 40)
print(f"Timer > 77 kW: {hours_above_77kw:,} timer ({hours_above_77kw/8760*100:.1f}%)")
print(f"Timer > 90 kW: {hours_above_90kw:,} timer ({hours_above_90kw/8760*100:.1f}%)")
print(f"Timer > 100 kW: {hours_above_100kw:,} timer ({hours_above_100kw/8760*100:.1f}%)")

# Batteriløsning
print("\n🔋 BATTERILØSNING FOR Å UNNGÅ AVKORTNING:")
print("-" * 40)

# Anta batteri kan lagre overskuddsproduksjon
battery_capacity_kwh = 100  # Eksempel batteristørrelse
battery_power_kw = 50  # Maks lade/utladingseffekt

# Simuler enkel batteridrift
battery_soc = 0  # State of charge (kWh)
avoided_curtailment = 0

for hour in range(hours_in_year):
    if hourly_production[hour] > grid_export_limit_kw:
        # Overskuddsproduksjon - lad batteri
        excess = hourly_production[hour] - grid_export_limit_kw
        charge = min(excess, battery_power_kw, battery_capacity_kwh - battery_soc)
        battery_soc += charge * 0.9  # 90% effektivitet
        avoided_curtailment += charge
    elif battery_soc > 0 and hourly_production[hour] < 50:  # Lav produksjon
        # Utlad batteri
        discharge = min(battery_soc, battery_power_kw)
        battery_soc -= discharge

avoided_curtailment_percentage = (avoided_curtailment / total_curtailment_kwh) * 100
economic_value_battery = avoided_curtailment * total_price

print(f"Batteristørrelse: {battery_capacity_kwh} kWh @ {battery_power_kw} kW")
print(f"Unngått avkortning: {avoided_curtailment:,.0f} kWh ({avoided_curtailment_percentage:.1f}%)")
print(f"Gjenværende avkortning: {total_curtailment_kwh - avoided_curtailment:,.0f} kWh")
print(f"Økonomisk verdi: {economic_value_battery:,.0f} NOK/år")

# Oppsummering
print("\n" + "="*60)
print("OPPSUMMERING")
print("="*60)

print(f"""
AVKORTNING UTEN BATTERI:
• Total avkortet energi: {total_curtailment_kwh:,.0f} kWh/år
• Økonomisk tap: {economic_loss:,.0f} NOK/år
• Andel av produksjon: {curtailment_percentage:.1f}%

AVKORTNING MED BATTERI (100 kWh):
• Unngått avkortning: {avoided_curtailment:,.0f} kWh/år
• Økonomisk gevinst: {economic_value_battery:,.0f} NOK/år
• Gjenværende tap: {(total_curtailment_kwh - avoided_curtailment) * total_price:,.0f} NOK/år

KONKLUSJON:
• Avkortning utgjør et betydelig tap
• Batteri kan redusere tap med {avoided_curtailment_percentage:.0f}%
• Størst avkortning i sommermånedene (mai-august)
""")

# Lag visualisering
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

# 1. Månedlig avkortning
x = np.arange(len(months))
ax1.bar(x, monthly_curtailment, color='red', alpha=0.7)
ax1.set_xlabel('Måned')
ax1.set_ylabel('Avkortning (kWh)')
ax1.set_title('Månedlig avkortning')
ax1.set_xticks(x)
ax1.set_xticklabels(months)
ax1.grid(True, alpha=0.3)

# 2. Varighetskurve
ax2.plot(sorted_production, linewidth=2)
ax2.axhline(y=grid_export_limit_kw, color='r', linestyle='--', label=f'Nettgrense ({grid_export_limit_kw} kW)')
ax2.axhline(y=inverter_capacity_kw, color='orange', linestyle='--', label=f'Inverter ({inverter_capacity_kw} kW)')
ax2.set_xlabel('Timer')
ax2.set_ylabel('Produksjon (kW)')
ax2.set_title('Varighetskurve for produksjon')
ax2.legend()
ax2.grid(True, alpha=0.3)

# 3. Timefordeling av avkortning
hours_of_day_curtailment = np.zeros(24)
for hour in range(hours_in_year):
    if curtailment_per_hour[hour] > 0:
        hour_of_day = hour % 24
        hours_of_day_curtailment[hour_of_day] += curtailment_per_hour[hour]

ax3.bar(range(24), hours_of_day_curtailment, color='orange', alpha=0.7)
ax3.set_xlabel('Time på døgnet')
ax3.set_ylabel('Total avkortning (kWh)')
ax3.set_title('Avkortning fordelt på døgnets timer')
ax3.grid(True, alpha=0.3)

# 4. Produksjon vs avkortning per måned
width = 0.35
x = np.arange(len(months))
ax4.bar(x - width/2, monthly_production, width, label='Total produksjon', color='green', alpha=0.7)
ax4.bar(x + width/2, monthly_curtailment, width, label='Avkortning', color='red', alpha=0.7)
ax4.set_xlabel('Måned')
ax4.set_ylabel('Energi (kWh)')
ax4.set_title('Produksjon vs avkortning')
ax4.set_xticks(x)
ax4.set_xticklabels(months)
ax4.legend()
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('curtailment_analysis.png', dpi=150)
print("\n✅ Visualisering lagret: curtailment_analysis.png")