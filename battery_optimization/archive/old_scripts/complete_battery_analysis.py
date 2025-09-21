"""
KOMPLETT BATTERIANALYSE MED ALLE VERDIDRIVERE
"""
import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

print("\n" + "="*60)
print("KOMPLETT BATTERIANALYSE - ALLE BEREGNINGER")
print("="*60)

# ====================================
# 1. SIMULER TIMESDATA FOR ETT ÅR
# ====================================

hours = 8760
timestamps = pd.date_range('2024-01-01', periods=hours, freq='h')

# SOLPRODUKSJON
pv_capacity = 138.55  # kWp
inverter_limit = 110  # kW
grid_export_limit = 77  # kW

production = []
for hour in range(hours):
    day = hour // 24
    hour_of_day = hour % 24
    month = timestamps[hour].month

    # Sesongfaktor (høyere om sommeren)
    if month in [6, 7]:  # Juni, juli
        season_factor = 1.0
    elif month in [5, 8]:  # Mai, august
        season_factor = 0.9
    elif month in [4, 9]:  # April, september
        season_factor = 0.7
    elif month in [3, 10]:  # Mars, oktober
        season_factor = 0.4
    elif month in [2, 11]:  # Februar, november
        season_factor = 0.2
    else:  # Desember, januar
        season_factor = 0.1

    # Daglig mønster
    if 10 <= hour_of_day <= 14:  # Midt på dagen
        daily_factor = 1.0
    elif 8 <= hour_of_day <= 16:  # Dagtid
        daily_factor = 0.7
    elif 6 <= hour_of_day <= 18:  # Morgen/kveld
        daily_factor = 0.3
    else:  # Natt
        daily_factor = 0

    # Beregn produksjon
    base_production = pv_capacity * season_factor * daily_factor
    # Tilfeldig variasjon (skyer etc)
    random_factor = 0.5 + 0.5 * np.random.random()
    hourly_production = min(base_production * random_factor, inverter_limit)
    production.append(hourly_production)

production_df = pd.DataFrame({
    'timestamp': timestamps,
    'production_kw': production
})

# FORBRUK (90 MWh/år)
annual_consumption = 90000  # kWh
base_load = annual_consumption / hours  # Gjennomsnitt per time

consumption = []
for hour in range(hours):
    hour_of_day = hour % 24
    day_of_week = timestamps[hour].dayofweek
    month = timestamps[hour].month

    # Kontortid på hverdager
    if day_of_week < 5:  # Mandag-fredag
        if 7 <= hour_of_day <= 17:
            load_factor = 1.5
        elif 6 <= hour_of_day <= 18:
            load_factor = 1.0
        else:
            load_factor = 0.5
    else:  # Helg
        load_factor = 0.3

    # Sesongvariasjon (høyere om vinteren pga oppvarming)
    if month in [12, 1, 2]:
        season_factor = 1.2
    elif month in [6, 7, 8]:
        season_factor = 0.8
    else:
        season_factor = 1.0

    hourly_consumption = base_load * load_factor * season_factor
    consumption.append(hourly_consumption)

consumption_df = pd.DataFrame({
    'timestamp': timestamps,
    'consumption_kw': consumption
})

# STRØMPRISER (realistisk variasjon)
prices = []
for hour in range(hours):
    hour_of_day = hour % 24
    day_of_week = timestamps[hour].dayofweek
    month = timestamps[hour].month

    # Grunnpris
    base_price = 0.50  # NOK/kWh

    # Time-of-day variasjon
    if 17 <= hour_of_day <= 20:  # Kveldspeak
        tod_factor = 2.0
    elif 7 <= hour_of_day <= 9:  # Morgenpeak
        tod_factor = 1.5
    elif 10 <= hour_of_day <= 16:
        tod_factor = 1.0
    else:  # Natt
        tod_factor = 0.6

    # Sesongvariasjon
    if month in [12, 1, 2]:  # Vinter
        season_factor = 1.5
    elif month in [6, 7, 8]:  # Sommer
        season_factor = 0.7
    else:
        season_factor = 1.0

    # Tilfeldig variasjon
    random_factor = 0.8 + 0.4 * np.random.random()

    spot_price = base_price * tod_factor * season_factor * random_factor
    prices.append(spot_price)

price_df = pd.DataFrame({
    'timestamp': timestamps,
    'spot_price': prices
})

# ====================================
# 2. BEREGN VERDIDRIVERE
# ====================================

print("\n📊 VERDIDRIVERE FOR BATTERI:")
print("="*60)

# A. UNNGÅTT AVKORTNING
curtailment_hours = production_df[production_df['production_kw'] > grid_export_limit]
total_curtailment_kwh = sum(
    curtailment_hours['production_kw'] - grid_export_limit
)
curtailment_value = total_curtailment_kwh * 0.45  # NOK/kWh netto innmating

print(f"\n1️⃣ UNNGÅTT AVKORTNING:")
print(f"   • Avkortet energi: {total_curtailment_kwh:,.0f} kWh/år")
print(f"   • Timer med avkortning: {len(curtailment_hours)}")
print(f"   • Verdi: {curtailment_value:,.0f} NOK/år")

# B. ENERGIARBITRASJE (kjøp billig, selg dyrt)
# Finn timer med lav og høy pris
low_price_threshold = price_df['spot_price'].quantile(0.25)  # Billigste 25%
high_price_threshold = price_df['spot_price'].quantile(0.75)  # Dyreste 25%

low_price_hours = price_df[price_df['spot_price'] < low_price_threshold]
high_price_hours = price_df[price_df['spot_price'] > high_price_threshold]

# Anta batteri på 100 kWh kan arbitrere daglig
battery_capacity = 100  # kWh
daily_arbitrage_potential = battery_capacity * 0.8  # 80% DoD
days_in_year = 365

# Gjennomsnittlig prisdifferanse
avg_price_diff = high_price_hours['spot_price'].mean() - low_price_hours['spot_price'].mean()
arbitrage_value = daily_arbitrage_potential * days_in_year * avg_price_diff * 0.9  # 90% effektivitet

print(f"\n2️⃣ ENERGIARBITRASJE:")
print(f"   • Lavpris (snitt): {low_price_hours['spot_price'].mean():.2f} NOK/kWh")
print(f"   • Høypris (snitt): {high_price_hours['spot_price'].mean():.2f} NOK/kWh")
print(f"   • Prisdifferanse: {avg_price_diff:.2f} NOK/kWh")
print(f"   • Verdi: {arbitrage_value:,.0f} NOK/år")

# C. REDUSERT EFFEKTTARIFF
# Finn månedlige effekttopper
monthly_peaks = []
for month in range(1, 13):
    month_data = consumption_df[pd.to_datetime(consumption_df['timestamp']).dt.month == month]
    peak_kw = month_data['consumption_kw'].max()
    monthly_peaks.append(peak_kw)

avg_monthly_peak = np.mean(monthly_peaks)

# Batteri kan redusere topper
peak_reduction_kw = min(50, avg_monthly_peak * 0.3)  # Reduser 30% av topp, maks 50 kW

# Lnett tariff (progressiv)
def calculate_demand_charge(peak_kw):
    """Beregn månedlig effekttariff basert på Lnett-struktur"""
    charge = 0
    brackets = [
        (0, 2, 136),
        (2, 5, 232),
        (5, 10, 372),
        (10, 15, 572),
        (15, 20, 772),
        (20, 25, 972),
        (25, 50, 1772),
        (50, 75, 2572),
        (75, 100, 3372),
        (100, 9999, 5600)
    ]

    for from_kw, to_kw, rate in brackets:
        if peak_kw > from_kw:
            bracket_kw = min(peak_kw - from_kw, to_kw - from_kw)
            charge += bracket_kw * rate
        if peak_kw <= to_kw:
            break

    return charge

# Beregn besparelse
charge_without_battery = sum(calculate_demand_charge(peak) for peak in monthly_peaks)
charge_with_battery = sum(calculate_demand_charge(peak - peak_reduction_kw) for peak in monthly_peaks)
demand_charge_savings = charge_without_battery - charge_with_battery

print(f"\n3️⃣ REDUSERT EFFEKTTARIFF:")
print(f"   • Gjennomsnittlig topp: {avg_monthly_peak:.1f} kW")
print(f"   • Toppreduksjon: {peak_reduction_kw:.1f} kW")
print(f"   • Tariff uten batteri: {charge_without_battery:,.0f} NOK/år")
print(f"   • Tariff med batteri: {charge_with_battery:,.0f} NOK/år")
print(f"   • Besparelse: {demand_charge_savings:,.0f} NOK/år")

# D. SELVFORSYNING (unngå kjøp fra nett)
# Finn timer hvor produksjon < forbruk
net_import_df = pd.DataFrame({
    'net_import': consumption_df['consumption_kw'].values - production_df['production_kw'].values,
    'spot_price': price_df['spot_price'].values
})
net_import_df['net_import'] = net_import_df['net_import'].clip(lower=0)

# Batteri kan forsyne når det er underskudd
battery_discharge_potential = min(
    net_import_df['net_import'].sum(),
    battery_capacity * 365 * 0.8  # Daglig sykling
)
self_supply_value = battery_discharge_potential * net_import_df['spot_price'].mean()

print(f"\n4️⃣ ØKT SELVFORSYNING:")
print(f"   • Nettimport uten batteri: {net_import_df['net_import'].sum():,.0f} kWh/år")
print(f"   • Batteri kan dekke: {battery_discharge_potential:,.0f} kWh/år")
print(f"   • Gjennomsnittspris: {net_import_df['spot_price'].mean():.2f} NOK/kWh")
print(f"   • Verdi: {self_supply_value:,.0f} NOK/år")

# ====================================
# 3. TOTAL ØKONOMISK ANALYSE
# ====================================

print("\n" + "="*60)
print("TOTAL ØKONOMISK ANALYSE")
print("="*60)

# Summer alle verdidrivere
total_annual_value = (
    curtailment_value +
    arbitrage_value +
    demand_charge_savings +
    self_supply_value
)

print(f"\n💰 ÅRLIGE BESPARELSER:")
print(f"   • Unngått avkortning:    {curtailment_value:8,.0f} NOK")
print(f"   • Energiarbitrasje:       {arbitrage_value:8,.0f} NOK")
print(f"   • Redusert effekttariff:  {demand_charge_savings:8,.0f} NOK")
print(f"   • Økt selvforsyning:      {self_supply_value:8,.0f} NOK")
print(f"   • TOTAL:                  {total_annual_value:8,.0f} NOK/år")

# Beregn NPV for forskjellige batterikostnader
battery_costs = [2000, 2500, 3000, 3500, 4000, 4500, 5000]
battery_size = 100  # kWh
discount_rate = 0.05
project_years = 15

print(f"\n📈 NPV-ANALYSE (100 kWh batteri, 15 år):")
print("-" * 50)
print("Batterikost | Investering | NPV        | Status")
print("-" * 50)

for cost_per_kwh in battery_costs:
    investment = battery_size * cost_per_kwh

    # NPV-beregning
    npv = -investment
    for year in range(1, project_years + 1):
        annual_cash = total_annual_value * (0.98 ** year)  # 2% årlig degradering
        npv += annual_cash / ((1 + discount_rate) ** year)

    status = "✅" if npv > 0 else "❌"
    print(f"{cost_per_kwh:,} kr/kWh | {investment:,} kr | {npv:10,.0f} | {status}")

# Finn break-even
break_even_cost = 0
for cost in range(5000, 1000, -100):
    investment = battery_size * cost
    npv = -investment
    for year in range(1, project_years + 1):
        annual_cash = total_annual_value * (0.98 ** year)
        npv += annual_cash / ((1 + discount_rate) ** year)
    if npv > 0:
        break_even_cost = cost
        break

print(f"\n🎯 BREAK-EVEN BATTERIKOSTNAD: {break_even_cost:,} NOK/kWh")

# ====================================
# 4. OPPSUMMERING
# ====================================

print("\n" + "="*60)
print("KONKLUSJON")
print("="*60)

print(f"""
ANLEGGSDATA:
• Solcelleanlegg: {pv_capacity} kWp
• Årsproduksjon: {sum(production)/1000:.1f} MWh
• Årsforbruk: {sum(consumption)/1000:.1f} MWh
• Avkortning: {total_curtailment_kwh:,.0f} kWh ({total_curtailment_kwh/sum(production)*100:.1f}%)

BATTERIVERDIER (100 kWh batteri):
• Total årlig besparelse: {total_annual_value:,.0f} NOK
• Break-even kostnad: {break_even_cost:,} NOK/kWh
• NPV ved 3000 NOK/kWh: {npv:,.0f} NOK

FORDELING AV VERDI:
• Unngått avkortning: {curtailment_value/total_annual_value*100:.0f}%
• Energiarbitrasje: {arbitrage_value/total_annual_value*100:.0f}%
• Effekttariff: {demand_charge_savings/total_annual_value*100:.0f}%
• Selvforsyning: {self_supply_value/total_annual_value*100:.0f}%

ANBEFALING:
{"✅ INVESTER - batteriet er lønnsomt!" if break_even_cost > 3000 else "⏳ VENT - batterikostnadene må ned til " + str(break_even_cost) + " NOK/kWh"}
""")

print("="*60)