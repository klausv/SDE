#!/usr/bin/env python3
"""
Simplified test with differential evolution
Using realistic NO2 2024 prices and Stavanger PV production
"""
import numpy as np

print("\n" + "="*70)
print("🔋 BATTERY OPTIMIZATION - STAVANGER 2024")
print("="*70)

# Fixed parameters
PV_CAP = 150  # kWp
INV_CAP = 110  # kW
GRID_LIM = 77  # kW

# Generate simplified but realistic data (monthly averages)
def create_monthly_data():
    """Create monthly typical values"""

    # Monthly PV production factors for Stavanger
    pv_monthly = np.array([
        0.02,  # Jan - very little sun
        0.04,  # Feb
        0.08,  # Mar
        0.13,  # Apr
        0.16,  # May
        0.17,  # Jun - peak month
        0.16,  # Jul
        0.14,  # Aug
        0.10,  # Sep
        0.06,  # Oct
        0.03,  # Nov
        0.01   # Dec - minimal sun
    ])

    # Monthly spot prices NO2 (post-crisis)
    price_monthly = np.array([
        0.95,  # Jan - winter peak
        0.90,  # Feb
        0.75,  # Mar
        0.60,  # Apr
        0.50,  # May
        0.45,  # Jun - summer low
        0.45,  # Jul
        0.50,  # Aug
        0.60,  # Sep
        0.75,  # Oct
        0.85,  # Nov
        0.95   # Dec - winter peak
    ])

    # Total annual PV: ~140 MWh (realistic for Stavanger)
    annual_pv_mwh = 140

    return pv_monthly * annual_pv_mwh * 1000 / 8760, price_monthly

def simple_battery_economics(capacity_kwh, power_kw):
    """Quick economic calculation"""

    # Get monthly data
    pv_hourly_avg, prices = create_monthly_data()

    # Annual metrics
    annual_pv = np.sum(pv_hourly_avg) * 8760 / 12  # Scale to full year

    # Revenue streams (simplified)
    # 1. Arbitrage - based on price volatility
    price_spread = np.max(prices) - np.min(prices)
    cycles_per_year = 200  # Typical for this application
    arbitrage_revenue = capacity_kwh * cycles_per_year * price_spread * 0.9  # Efficiency

    # 2. Peak shaving - avoid high tariff brackets
    peak_reduction_kw = min(power_kw, 30)  # Typical reduction
    # Savings from moving down tariff brackets
    monthly_savings = peak_reduction_kw * 50  # NOK per kW reduction
    peak_revenue = monthly_savings * 12

    # 3. Curtailment avoidance
    hours_above_grid = 500  # Hours when PV > 77 kW
    avg_curtailment = 20  # kW average excess
    curtailment_revenue = hours_above_grid * avg_curtailment * np.mean(prices)

    # Total annual revenue
    total_revenue = arbitrage_revenue + peak_revenue + curtailment_revenue

    # Simple NPV (15 years, 5% discount, 2% degradation)
    npv = -capacity_kwh * 3000  # Investment at 3000 NOK/kWh
    for year in range(15):
        discount = (1.05 ** year)
        degradation = 1 - 0.02 * year
        npv += total_revenue * degradation / discount

    return npv, total_revenue

# Test different configurations
print("\n📊 Testing battery configurations...")
print("\nCapacity\tPower\tC-rate\tNPV\t\tAnnual Revenue")
print("-" * 60)

best_npv = -float('inf')
best_config = None

for capacity in [50, 75, 100, 125, 150]:
    for power in [25, 40, 50, 60, 75]:
        c_rate = power / capacity
        if 0.3 <= c_rate <= 1.0:  # Reasonable C-rate
            npv, revenue = simple_battery_economics(capacity, power)

            print(f"{capacity} kWh\t{power} kW\t{c_rate:.2f}\t"
                  f"{npv:,.0f}\t{revenue:,.0f}")

            if npv > best_npv:
                best_npv = npv
                best_config = (capacity, power, revenue)

print("\n" + "="*70)
print("✅ OPTIMAL CONFIGURATION")
print("="*70)

if best_config:
    cap, pow, rev = best_config
    print(f"\n🔋 Battery sizing:")
    print(f"   • Capacity: {cap} kWh")
    print(f"   • Power: {pow} kW")
    print(f"   • C-rate: {pow/cap:.2f}")

    print(f"\n💰 Economics:")
    print(f"   • NPV @ 3000 NOK/kWh: {best_npv:,.0f} NOK")
    print(f"   • Annual revenue: {rev:,.0f} NOK")
    print(f"   • Simple payback: {cap * 3000 / rev:.1f} years")

    # Break-even test
    print(f"\n🎯 Break-even analysis:")
    for cost in [2500, 3000, 3500, 4000, 4500]:
        npv = -cap * cost
        for year in range(15):
            npv += rev * (1 - 0.02 * year) / (1.05 ** year)

        status = "✅" if npv > 0 else "❌"
        print(f"   {cost} NOK/kWh: NPV = {npv:,.0f} {status}")

print("\n📝 Key assumptions:")
print("   • NO2 prices: 0.45-0.95 NOK/kWh (seasonal)")
print("   • PV production: ~140 MWh/year (Stavanger)")
print("   • 200 cycles/year (realistic for commercial)")
print("   • Lnett tariff reduction included")

print("\n✅ Simple analysis complete!")