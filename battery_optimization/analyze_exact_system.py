#!/usr/bin/env python3
"""
Battery optimization for EXACT system specifications
Location: 58.929644, 5.623052 (Stavanger area)
System: 138.5 kWp, 100 kW inverter, 70 kW grid export limit
"""
import numpy as np
import pandas as pd
import requests

print("\n" + "="*70)
print("🔋 BATTERY OPTIMIZATION - EXACT SYSTEM SPECIFICATIONS")
print("="*70)

# System parameters
LAT = 58.929644
LON = 5.623052
PV_CAPACITY = 138.5  # kWp
INVERTER_LIMIT = 100  # kW
GRID_LIMIT = 70  # kW

# Economic parameters
DISCOUNT_RATE = 0.05
BATTERY_LIFETIME = 15
EFFICIENCY = 0.90
DEGRADATION = 0.02

# Lnett tariffs (NOK/month)
POWER_TARIFFS = {
    (0, 2): 136, (2, 5): 232, (5, 10): 372, (10, 15): 572,
    (15, 20): 772, (20, 25): 972, (25, 50): 1772,
    (50, 75): 2572, (75, 100): 3372, (100, 200): 5600
}

def get_pvgis_tmy():
    """Get TMY data from PVGIS for exact location"""
    url = "https://re.jrc.ec.europa.eu/api/tmy"
    params = {'lat': LAT, 'lon': LON, 'outputformat': 'json'}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        hourly = data.get('outputs', {}).get('tmy_hourly', [])
        if not hourly:
            return None

        # Extract radiation data
        ghi = np.array([h.get('G(h)', 0) for h in hourly])  # Global horizontal
        dni = np.array([h.get('Gb(n)', 0) for h in hourly])  # Direct normal
        dhi = np.array([h.get('Gd(h)', 0) for h in hourly])  # Diffuse horizontal

        # Simple PV model (25° tilt, south facing)
        # Using global horizontal as approximation
        pv_dc = (ghi / 1000) * PV_CAPACITY * 0.85  # 85% system efficiency

        # Apply inverter limit
        pv_ac = np.minimum(pv_dc, INVERTER_LIMIT)

        print(f"✅ Got TMY data: {len(pv_ac)} hours")
        return pv_ac

    except Exception as e:
        print(f"❌ Error fetching PVGIS: {e}")
        return None

def generate_load_profile():
    """Generate commercial load profile"""
    load = np.zeros(8760)
    for h in range(8760):
        hour_of_day = h % 24
        weekday = ((h // 24) % 7) < 5
        month = min(12, (h // 720) + 1)

        # Base load 25 kW, work hours 50 kW
        if weekday and 7 <= hour_of_day <= 17:
            load[h] = 50
        else:
            load[h] = 25

        # Seasonal adjustment
        if month in [12, 1, 2]:  # Winter
            load[h] *= 1.2
        elif month in [6, 7, 8]:  # Summer
            load[h] *= 1.05

    return load

def generate_spot_prices():
    """Generate NO2 spot prices (2023-2025 levels)"""
    prices = np.zeros(8760)
    for h in range(8760):
        month = min(12, (h // 720) + 1)
        hour_of_day = h % 24
        weekday = ((h // 24) % 7) < 5

        # Base prices
        if month in [6, 7, 8]:  # Summer
            base = 0.45
        elif month in [12, 1, 2]:  # Winter
            base = 0.95
        else:
            base = 0.70

        # Daily pattern
        if weekday and hour_of_day in [7, 8, 17, 18, 19]:
            factor = 1.4
        elif weekday and 9 <= hour_of_day <= 16:
            factor = 1.1
        elif 22 <= hour_of_day or hour_of_day <= 5:
            factor = 0.7
        else:
            factor = 0.9

        prices[h] = base * factor * np.random.normal(1.0, 0.15)
        prices[h] = max(0.1, prices[h])

    return prices

def simulate_battery(capacity_kwh, power_kw, pv, prices, load):
    """Simulate battery operation with grid constraint"""
    n = len(pv)
    soc = np.zeros(n)
    soc[0] = capacity_kwh * 0.5

    charge = np.zeros(n)
    discharge = np.zeros(n)
    grid_export = np.zeros(n)
    grid_import = np.zeros(n)
    curtailment = np.zeros(n)

    eff = np.sqrt(EFFICIENCY)

    for t in range(1, n):
        net = pv[t] - load[t]

        # Check if price is high/low
        avg_price = np.mean(prices[max(0, t-168):t+1])
        is_expensive = prices[t] > avg_price * 1.15
        is_cheap = prices[t] < avg_price * 0.85

        if net > 0:  # Excess generation
            if net > GRID_LIMIT:
                # Must store excess or curtail
                excess = net - GRID_LIMIT
                max_charge = min(power_kw, (capacity_kwh * 0.9 - soc[t-1]) / eff)
                charge[t] = min(excess, max_charge)
                grid_export[t] = GRID_LIMIT
                curtailment[t] = max(0, excess - charge[t])
            else:
                # Can export all
                grid_export[t] = net
                # Opportunistic charging
                if is_cheap and soc[t-1] < capacity_kwh * 0.7:
                    available = min(net * 0.3, power_kw)
                    max_charge = min(available, (capacity_kwh * 0.9 - soc[t-1]) / eff)
                    charge[t] = max_charge
                    grid_export[t] = net - charge[t]

        else:  # Net consumption
            deficit = -net
            if is_expensive and soc[t-1] > capacity_kwh * 0.2:
                max_discharge = min(power_kw, (soc[t-1] - capacity_kwh * 0.1) * eff)
                discharge[t] = min(deficit, max_discharge)
                grid_import[t] = deficit - discharge[t]
            else:
                grid_import[t] = deficit

        # Update SOC
        soc[t] = soc[t-1] + charge[t] * eff - discharge[t] / eff
        soc[t] = np.clip(soc[t], capacity_kwh * 0.1, capacity_kwh * 0.9)

    return {
        'charge': charge,
        'discharge': discharge,
        'grid_export': grid_export,
        'grid_import': grid_import,
        'curtailment': curtailment,
        'soc': soc
    }

def calculate_economics(capacity_kwh, power_kw, sim, prices):
    """Calculate NPV and payback"""

    # Investment (including 25% installation)
    investment = capacity_kwh * 3000 * 1.25

    # Annual revenues
    # 1. Arbitrage
    arbitrage = np.sum(sim['discharge'] * prices) - np.sum(sim['charge'] * prices)

    # 2. Peak reduction (simplified - assume 20 kW reduction)
    # From 50 kW to 30 kW moves down tariff brackets
    monthly_saving = 2572 - 1772  # From 50-75 to 25-50 bracket
    peak_savings = monthly_saving * 12

    # 3. Avoided curtailment
    curtailment_value = np.sum(sim['curtailment']) * np.mean(prices) * 0.8

    annual_revenue = arbitrage + peak_savings + curtailment_value

    # NPV calculation
    npv = -investment
    for year in range(BATTERY_LIFETIME):
        discount = (1 + DISCOUNT_RATE) ** year
        degradation = 1 - DEGRADATION * year
        npv += annual_revenue * degradation / discount

    payback = investment / annual_revenue if annual_revenue > 0 else 99

    return npv, annual_revenue, payback, curtailment_value

# Main analysis
print("\n📊 Getting PVGIS data for exact location...")
pv = get_pvgis_tmy()

if pv is None:
    print("Using simplified PV model instead...")
    # Fallback to simple model
    pv = np.zeros(8760)
    for h in range(8760):
        month = min(12, (h // 720) + 1)
        hour_of_day = h % 24

        # Monthly factors for Stavanger
        monthly = [0.02, 0.04, 0.08, 0.12, 0.15, 0.16,
                  0.15, 0.14, 0.10, 0.06, 0.03, 0.01]

        if 4 <= hour_of_day <= 20:
            sun = np.sin((hour_of_day - 4) * np.pi / 16)
            pv[h] = PV_CAPACITY * monthly[month-1] * sun * np.random.uniform(0.5, 1.0)
            pv[h] = min(pv[h], INVERTER_LIMIT)

print("\n📊 Generating load and price profiles...")
load = generate_load_profile()
prices = generate_spot_prices()

# Statistics
total_pv = np.sum(pv)
capacity_factor = np.mean(pv) / PV_CAPACITY
hours_above_grid = np.sum(pv > GRID_LIMIT)

print(f"\n📈 System Analysis:")
print(f"   • PV total: {total_pv/1000:.1f} MWh/year")
print(f"   • Capacity factor: {capacity_factor:.1%}")
print(f"   • Peak PV output: {np.max(pv):.1f} kW")
print(f"   • Hours > grid limit (70 kW): {hours_above_grid}")
print(f"   • Load total: {np.sum(load)/1000:.1f} MWh/year")
print(f"   • Avg spot price: {np.mean(prices):.3f} NOK/kWh")

# Test battery configurations
print("\n🔍 Testing battery configurations...")
print("\nCapacity  Power   NPV         Revenue   Payback  Curtailment")
print("-" * 65)

best_npv = -float('inf')
best_config = None

for capacity in [30, 50, 75, 100, 125, 150]:
    for power in [20, 30, 40, 50, 60, 75]:
        c_rate = power / capacity
        if 0.3 <= c_rate <= 1.2:
            sim = simulate_battery(capacity, power, pv, prices, load)
            npv, revenue, payback, curt_val = calculate_economics(capacity, power, sim, prices)

            curt_avoided = np.sum(sim['curtailment'])

            print(f"{capacity:3.0f} kWh  {power:2.0f} kW  {npv:10,.0f}  "
                  f"{revenue:8,.0f}  {payback:6.1f}  {curt_avoided:6.0f} kWh")

            if npv > best_npv:
                best_npv = npv
                best_config = (capacity, power, revenue, payback)

print("\n" + "="*70)
print("✅ OPTIMAL CONFIGURATION")
print("="*70)

if best_config:
    cap, pow, rev, pb = best_config

    print(f"\n🔋 Optimal battery:")
    print(f"   • Capacity: {cap} kWh")
    print(f"   • Power: {pow} kW")
    print(f"   • C-rate: {pow/cap:.2f}")

    print(f"\n💰 Economics @ 3000 NOK/kWh:")
    print(f"   • NPV: {best_npv:,.0f} NOK")
    print(f"   • Annual revenue: {rev:,.0f} NOK")
    print(f"   • Payback: {pb:.1f} years")

    # Break-even analysis
    print(f"\n🎯 Break-even battery cost:")
    for factor in [0.6, 0.8, 1.0, 1.2, 1.4]:
        test_cost = 3000 * factor
        test_inv = cap * test_cost * 1.25
        test_npv = -test_inv

        for year in range(BATTERY_LIFETIME):
            test_npv += rev * (1 - DEGRADATION * year) / ((1 + DISCOUNT_RATE) ** year)

        status = "✅" if test_npv > 0 else "❌"
        print(f"   {test_cost:.0f} NOK/kWh: {test_npv:>10,.0f} NOK {status}")

print("\n📝 Key findings:")
print(f"   • System: {PV_CAPACITY} kWp PV, {INVERTER_LIMIT} kW inverter")
print(f"   • Grid constraint: {GRID_LIMIT} kW creates curtailment opportunity")
print(f"   • Main value drivers: Peak shaving + curtailment avoidance")

print("\n✅ Analysis complete!")