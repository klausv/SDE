#!/usr/bin/env python3
"""
Realistic battery optimization test with proper constraints
Post energy-crisis NO2 prices (2023-2025 levels)
"""
import numpy as np
from datetime import datetime

print("\n" + "="*70)
print("🔋 REALISTIC BATTERY OPTIMIZATION - NO2 (2023-2025)")
print("="*70)

# System parameters
PV_CAPACITY = 150  # kWp
INVERTER_CAPACITY = 110  # kW
GRID_LIMIT = 77  # kW
DISCOUNT_RATE = 0.05
BATTERY_LIFETIME = 15
EFFICIENCY = 0.90
DEGRADATION_RATE = 0.02  # 2% per year

# Lnett tariff structure (NOK/month per power bracket)
POWER_TARIFFS = {
    (0, 2): 136, (2, 5): 232, (5, 10): 372, (10, 15): 572,
    (15, 20): 772, (20, 25): 972, (25, 50): 1772,
    (50, 75): 2572, (75, 100): 3372, (100, 200): 5600
}

def get_power_tariff(peak_kw):
    """Get monthly tariff based on peak power"""
    for (lower, upper), cost in POWER_TARIFFS.items():
        if lower <= peak_kw < upper:
            return cost
    return 5600

def generate_realistic_profiles():
    """Generate realistic annual profiles"""
    hours = 8760

    # PV production (Stavanger realistic)
    pv = np.zeros(hours)
    for h in range(hours):
        month = min(12, (h // 720) + 1)  # Ensure month stays within 1-12
        hour_of_day = h % 24

        # Monthly production factors (realistic for Stavanger)
        monthly_factors = {
            1: 0.02, 2: 0.05, 3: 0.12, 4: 0.18, 5: 0.22, 6: 0.24,
            7: 0.23, 8: 0.20, 9: 0.14, 10: 0.08, 11: 0.03, 12: 0.01
        }

        if 4 <= hour_of_day <= 20:
            # Sun hours
            sun_position = np.sin((hour_of_day - 4) * np.pi / 16)
            base_prod = PV_CAPACITY * monthly_factors[month] * sun_position

            # Weather variability
            weather = np.random.uniform(0.3, 1.0)  # Cloud cover
            pv[h] = min(base_prod * weather, INVERTER_CAPACITY)

    # Spot prices (realistic NO2 post-crisis)
    prices = np.zeros(hours)
    for h in range(hours):
        month = min(12, (h // 720) + 1)  # Ensure month stays within 1-12
        hour_of_day = h % 24
        weekday = ((h // 24) % 7) < 5

        # Seasonal base prices
        if 5 <= month <= 9:  # Summer
            base = 0.45
        elif month in [12, 1, 2]:  # Winter
            base = 0.95
        else:  # Spring/autumn
            base = 0.70

        # Hourly pattern
        if weekday:
            if hour_of_day in [7, 8, 17, 18, 19]:  # Peak hours
                factor = 1.4
            elif 9 <= hour_of_day <= 16:  # Day
                factor = 1.1
            elif 22 <= hour_of_day or hour_of_day <= 5:  # Night
                factor = 0.7
            else:
                factor = 0.9
        else:  # Weekend
            factor = 0.8

        # Add volatility
        volatility = np.random.normal(1.0, 0.2)
        prices[h] = max(0.1, base * factor * volatility)

    # Load profile (commercial building)
    load = np.zeros(hours)
    base_load = 20  # kW minimum

    for h in range(hours):
        hour_of_day = h % 24
        weekday = ((h // 24) % 7) < 5
        month = min(12, (h // 720) + 1)  # Ensure month stays within 1-12

        if weekday and 7 <= hour_of_day <= 18:
            # Working hours
            load[h] = base_load + 30  # 50 kW during work
        else:
            load[h] = base_load

        # Seasonal adjustment (heating/cooling)
        if month in [12, 1, 2]:  # Winter heating
            load[h] *= 1.3
        elif month in [6, 7, 8]:  # Summer cooling
            load[h] *= 1.1

    return pv, prices, load

def simulate_battery(capacity_kwh, power_kw, pv, prices, load):
    """Realistic battery simulation"""
    n_hours = len(pv)

    # Initialize
    soc = np.zeros(n_hours)
    soc[0] = capacity_kwh * 0.5
    charge = np.zeros(n_hours)
    discharge = np.zeros(n_hours)
    grid_import = np.zeros(n_hours)
    grid_export = np.zeros(n_hours)

    eff = np.sqrt(EFFICIENCY)

    for t in range(1, n_hours):
        # Net position
        net = pv[t] - load[t]

        # Price signals (simple strategy)
        price_percentile = np.percentile(prices[:t+1], [25, 75])
        is_cheap = prices[t] < price_percentile[0]
        is_expensive = prices[t] > price_percentile[1]

        if net > 0:
            # Excess generation
            if net > GRID_LIMIT:
                # Must store excess or curtail
                excess = net - GRID_LIMIT
                max_charge = min(power_kw, (capacity_kwh * 0.9 - soc[t-1]) / eff)
                charge[t] = min(excess, max_charge)
                grid_export[t] = GRID_LIMIT
            else:
                # Can export all
                grid_export[t] = net
                # Charge if price is low
                if is_cheap and soc[t-1] < capacity_kwh * 0.7:
                    max_charge = min(power_kw, (capacity_kwh * 0.9 - soc[t-1]) / eff, net)
                    charge[t] = max_charge * 0.5  # Charge some
                    grid_export[t] = net - charge[t]

        else:
            # Net consumption
            deficit = -net
            # Discharge if price is high and SOC sufficient
            if is_expensive and soc[t-1] > capacity_kwh * 0.3:
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
        'grid_import': grid_import,
        'grid_export': grid_export,
        'soc': soc,
        'curtailment': np.maximum(0, pv - load - grid_export - charge)
    }

def calculate_npv(capacity_kwh, power_kw, sim, prices, battery_cost_per_kwh):
    """Calculate realistic NPV"""

    investment = capacity_kwh * battery_cost_per_kwh * 1.25  # Add 25% for installation

    yearly_cash_flows = []

    for year in range(BATTERY_LIFETIME):
        # Degradation
        deg_factor = 1 - DEGRADATION_RATE * year

        # 1. Energy arbitrage
        charge_cost = np.sum(sim['charge'] * prices) * deg_factor
        discharge_revenue = np.sum(sim['discharge'] * prices) * deg_factor
        arbitrage = discharge_revenue - charge_cost

        # 2. Peak power reduction
        monthly_peaks_with = []
        monthly_peaks_without = []
        for month in range(12):
            month_hours = range(month * 730, min((month + 1) * 730, 8760))
            # With battery
            daily_peaks = []
            for day in range(30):
                day_hours = [month * 730 + day * 24 + h for h in range(24) if month * 730 + day * 24 + h < 8760]
                if day_hours:
                    daily_peaks.append(np.max([sim['grid_import'][h] for h in day_hours]))
            if daily_peaks:
                monthly_peaks_with.append(np.mean(sorted(daily_peaks)[-3:]))  # Top 3 days

            # Without battery (estimated)
            daily_peaks_no_batt = []
            for day in range(30):
                day_hours = [month * 730 + day * 24 + h for h in range(24) if month * 730 + day * 24 + h < 8760]
                if day_hours:
                    peak_no_batt = np.max([max(0, load[h] - pv[h]) for h in day_hours])
                    daily_peaks_no_batt.append(peak_no_batt)
            if daily_peaks_no_batt:
                monthly_peaks_without.append(np.mean(sorted(daily_peaks_no_batt)[-3:]))

        # Calculate tariff savings
        tariff_with = sum([get_power_tariff(p) for p in monthly_peaks_with])
        tariff_without = sum([get_power_tariff(p) for p in monthly_peaks_without])
        peak_savings = (tariff_without - tariff_with) * deg_factor

        # 3. Avoided curtailment
        curtailment_value = np.sum(sim['curtailment']) * np.mean(prices) * 0.8 * deg_factor

        # Total annual cash flow
        annual_cf = arbitrage + peak_savings + curtailment_value
        yearly_cash_flows.append(annual_cf)

    # NPV calculation
    npv = -investment
    for year, cf in enumerate(yearly_cash_flows):
        npv += cf / ((1 + DISCOUNT_RATE) ** year)

    # Simple payback
    cumulative = -investment
    payback = None
    for year, cf in enumerate(yearly_cash_flows):
        cumulative += cf
        if cumulative > 0 and payback is None:
            payback = year + 1

    return {
        'npv': npv,
        'payback': payback,
        'annual_revenue': np.mean(yearly_cash_flows[:5]),  # First 5 years average
        'arbitrage': arbitrage,
        'peak_savings': peak_savings
    }

def optimize():
    """Simple optimization loop"""
    print("\n📊 Generating realistic 2024 profiles...")
    pv, prices, load = generate_realistic_profiles()

    print(f"   • PV total: {np.sum(pv)/1000:.1f} MWh/year")
    print(f"   • PV capacity factor: {np.mean(pv)/PV_CAPACITY:.1%}")
    print(f"   • Price mean: {np.mean(prices):.3f} NOK/kWh")
    print(f"   • Price volatility (std): {np.std(prices):.3f}")
    print(f"   • Load total: {np.sum(load)/1000:.1f} MWh/year")

    print("\n🔍 Testing battery configurations...")

    best_npv = -float('inf')
    best_config = None

    # Test grid of configurations
    capacities = [30, 50, 75, 100, 125, 150]
    powers = [20, 30, 40, 50, 60, 75]

    for cap in capacities:
        for pow in powers:
            c_rate = pow / cap
            if 0.3 <= c_rate <= 1.5:  # Realistic C-rate range
                sim = simulate_battery(cap, pow, pv, prices, load)
                eco = calculate_npv(cap, pow, sim, prices, 3000)

                if eco['npv'] > best_npv:
                    best_npv = eco['npv']
                    best_config = (cap, pow, eco)

    return best_config, pv, prices, load

# Run optimization
config, pv, prices, load = optimize()
optimal_capacity, optimal_power, economics = config

print("\n" + "="*70)
print("✅ OPTIMIZATION RESULTS")
print("="*70)

print(f"\n🔋 Optimal Battery Configuration:")
print(f"   • Capacity: {optimal_capacity:.0f} kWh")
print(f"   • Power: {optimal_power:.0f} kW")
print(f"   • C-rate: {optimal_power/optimal_capacity:.2f}")

print(f"\n💰 Economics at 3000 NOK/kWh:")
print(f"   • NPV (15 years): {economics['npv']:,.0f} NOK")
print(f"   • Annual revenue: {economics['annual_revenue']:,.0f} NOK/year")
if economics['payback']:
    print(f"   • Payback period: {economics['payback']} years")
else:
    print(f"   • Payback period: >15 years")

# Find break-even
print(f"\n🎯 Testing break-even battery cost...")
sim = simulate_battery(optimal_capacity, optimal_power, pv, prices, load)

test_costs = [2000, 2500, 3000, 3500, 4000, 4500, 5000]
npvs = []
for cost in test_costs:
    eco = calculate_npv(optimal_capacity, optimal_power, sim, prices, cost)
    npvs.append(eco['npv'])
    if eco['npv'] > 0:
        print(f"   {cost} NOK/kWh: NPV = {eco['npv']:,.0f} NOK ✅")
    else:
        print(f"   {cost} NOK/kWh: NPV = {eco['npv']:,.0f} NOK ❌")

# Interpolate break-even
for i in range(len(npvs) - 1):
    if npvs[i] > 0 and npvs[i + 1] < 0:
        breakeven = test_costs[i] + (test_costs[i + 1] - test_costs[i]) * (0 - npvs[i]) / (npvs[i + 1] - npvs[i])
        print(f"\n   💡 Break-even battery cost: ~{breakeven:.0f} NOK/kWh")
        break

print("\n" + "="*70)
print("🎯 INVESTMENT RECOMMENDATION")
print("="*70)

if economics['npv'] > 0:
    roi = (economics['npv'] / (optimal_capacity * 3000 * 1.25)) * 100
    print(f"\n✅ POSITIVE NPV at current prices (3000 NOK/kWh)")
    print(f"   • Return on investment: {roi:.0f}%")
    print(f"   • Main value driver: Peak power reduction + arbitrage")
    print(f"   • Grid constraint (77 kW) adds curtailment value")
else:
    print(f"\n⚠️ NEGATIVE NPV at current prices")
    print(f"   • Wait for battery prices to drop")
    print(f"   • Or explore alternative financing/subsidies")

print("\n📝 Key assumptions:")
print("   • 15-year lifetime with 2% annual degradation")
print("   • 90% round-trip efficiency")
print("   • 25% installation cost markup")
print("   • NO2 prices: 0.45-0.95 NOK/kWh (seasonal)")
print("   • Lnett tariff structure with døgnmaks")

print("\n✅ Analysis complete!")