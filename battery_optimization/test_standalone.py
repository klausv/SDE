#!/usr/bin/env python3
"""
Standalone test of battery optimization - no external dependencies needed
Tests differential evolution with realistic 2024 NO2 prices
"""
import numpy as np
from datetime import datetime
import json

print("\n" + "="*70)
print("🔋 BATTERY OPTIMIZATION - STANDALONE TEST")
print("   Post Energy-Crisis Analysis (2023-2025 price levels)")
print("="*70)

# System configuration
PV_CAPACITY = 150  # kWp
INVERTER_CAPACITY = 110  # kW
GRID_LIMIT = 77  # kW
DISCOUNT_RATE = 0.05
BATTERY_LIFETIME = 15  # years
EFFICIENCY = 0.90  # Round-trip

def generate_annual_profiles():
    """Generate realistic annual profiles for 2024"""
    hours_per_year = 8760

    # PV production pattern (Stavanger)
    pv_production = np.zeros(hours_per_year)
    for hour in range(hours_per_year):
        day_of_year = hour // 24
        hour_of_day = hour % 24

        # Seasonal variation
        seasonal_factor = 0.5 + 0.5 * np.sin((day_of_year - 80) * 2 * np.pi / 365)

        # Daily pattern
        if 4 <= hour_of_day <= 20:
            sun_angle = np.sin((hour_of_day - 4) * np.pi / 16)
            daily_production = sun_angle * PV_CAPACITY * seasonal_factor
            # Apply inverter clipping
            pv_production[hour] = min(daily_production, INVERTER_CAPACITY)
        else:
            pv_production[hour] = 0

    # Spot prices (NO2 post-crisis levels)
    spot_prices = np.zeros(hours_per_year)
    for hour in range(hours_per_year):
        month = (hour // 720) + 1  # Approximate month
        hour_of_day = hour % 24

        # Base price: summer 0.5, winter 0.85 NOK/kWh
        if 4 <= month <= 9:
            base_price = 0.50
        else:
            base_price = 0.85

        # Daily pattern
        hourly_factors = [
            0.85, 0.82, 0.80, 0.78, 0.77, 0.80,  # 00-05
            0.90, 1.05, 1.15, 1.10, 1.05, 1.00,  # 06-11
            0.95, 0.93, 0.95, 1.00, 1.08, 1.20,  # 12-17
            1.25, 1.22, 1.15, 1.05, 0.95, 0.88   # 18-23
        ]

        spot_prices[hour] = base_price * hourly_factors[hour_of_day] * np.random.uniform(0.8, 1.2)

    # Commercial load profile
    load_profile = np.zeros(hours_per_year)
    base_load = 25  # kW
    for hour in range(hours_per_year):
        hour_of_day = hour % 24
        day_of_week = (hour // 24) % 7

        if day_of_week < 5:  # Weekday
            if 8 <= hour_of_day <= 17:
                load_profile[hour] = base_load * 2.0
            else:
                load_profile[hour] = base_load * 0.4
        else:  # Weekend
            load_profile[hour] = base_load * 0.3

    return pv_production, spot_prices, load_profile

def simulate_battery_operation(capacity_kwh, power_kw, pv_prod, spot_prices, load):
    """Simple battery operation simulation"""
    n_hours = len(pv_prod)
    soc = np.zeros(n_hours)
    soc[0] = capacity_kwh * 0.5  # Start at 50% SOC

    grid_import = np.zeros(n_hours)
    grid_export = np.zeros(n_hours)
    curtailment = np.zeros(n_hours)

    one_way_eff = np.sqrt(EFFICIENCY)

    for t in range(1, n_hours):
        # Net generation
        net_gen = pv_prod[t] - load[t]

        # Simple control strategy
        if net_gen > GRID_LIMIT:
            # Excess - charge battery
            excess = net_gen - GRID_LIMIT
            max_charge = min(power_kw, (capacity_kwh * 0.9 - soc[t-1]) / one_way_eff)
            charge = min(excess, max_charge)

            soc[t] = soc[t-1] + charge * one_way_eff
            grid_export[t] = GRID_LIMIT
            curtailment[t] = max(0, excess - charge)

        elif net_gen > 0:
            # Export within limit
            grid_export[t] = net_gen
            soc[t] = soc[t-1]

        else:
            # Net consumption - discharge if profitable
            required = -net_gen
            max_discharge = min(power_kw, (soc[t-1] - capacity_kwh * 0.1) * one_way_eff)

            # Discharge if price is high
            if spot_prices[t] > np.mean(spot_prices):
                discharge = min(required, max_discharge)
                soc[t] = soc[t-1] - discharge / one_way_eff
                grid_import[t] = required - discharge
            else:
                soc[t] = soc[t-1]
                grid_import[t] = required

    return {
        'grid_import': grid_import,
        'grid_export': grid_export,
        'curtailment': curtailment,
        'soc': soc
    }

def calculate_economics(capacity_kwh, power_kw, operation, spot_prices, battery_cost_per_kwh):
    """Calculate NPV and economic metrics"""

    # Investment
    investment = capacity_kwh * battery_cost_per_kwh

    # Annual revenues
    annual_revenues = []

    # Arbitrage (simplified)
    price_diff = np.diff(spot_prices)
    arbitrage_annual = np.sum(np.abs(price_diff)) * power_kw * 100  # Rough estimate

    # Peak reduction (simplified)
    peak_without = np.max(operation['grid_import'] + power_kw)
    peak_with = np.max(operation['grid_import'])
    peak_saving = (peak_without - peak_with) * 200 * 12  # Monthly saving

    # Curtailment value
    curtailment_value = np.sum(operation['curtailment']) * np.mean(spot_prices)

    annual_revenue = arbitrage_annual + peak_saving + curtailment_value

    # NPV calculation
    npv = -investment
    for year in range(BATTERY_LIFETIME):
        discount = (1 + DISCOUNT_RATE) ** year
        degradation = 1 - 0.02 * year
        npv += (annual_revenue * degradation) / discount

    return {
        'npv': npv,
        'annual_revenue': annual_revenue,
        'arbitrage': arbitrage_annual,
        'peak_savings': peak_saving,
        'curtailment_value': curtailment_value
    }

def differential_evolution_optimize(pv_prod, spot_prices, load):
    """Simple differential evolution implementation"""

    # Search space
    capacity_min, capacity_max = 10, 200
    power_min, power_max = 10, 100

    # DE parameters
    population_size = 20
    max_generations = 30
    F = 0.8  # Differential weight
    CR = 0.7  # Crossover probability

    # Initialize population
    population = np.random.rand(population_size, 2)
    population[:, 0] = population[:, 0] * (capacity_max - capacity_min) + capacity_min
    population[:, 1] = population[:, 1] * (power_max - power_min) + power_min

    # Evaluate initial population
    fitness = np.zeros(population_size)
    for i in range(population_size):
        cap, pow = population[i]
        if pow / cap > 2.0 or pow / cap < 0.2:  # C-rate constraint
            fitness[i] = -1e9
        else:
            op = simulate_battery_operation(cap, pow, pv_prod, spot_prices, load)
            eco = calculate_economics(cap, pow, op, spot_prices, 3000)
            fitness[i] = eco['npv']

    best_idx = np.argmax(fitness)
    best_solution = population[best_idx].copy()
    best_fitness = fitness[best_idx]

    print(f"\n🔄 Running differential evolution optimization...")
    print(f"   Population: {population_size}, Generations: {max_generations}")

    # Evolution loop
    for gen in range(max_generations):
        for i in range(population_size):
            # Mutation
            indices = [j for j in range(population_size) if j != i]
            a, b, c = np.random.choice(indices, 3, replace=False)
            mutant = population[a] + F * (population[b] - population[c])

            # Clip to bounds
            mutant[0] = np.clip(mutant[0], capacity_min, capacity_max)
            mutant[1] = np.clip(mutant[1], power_min, power_max)

            # Crossover
            trial = population[i].copy()
            for j in range(2):
                if np.random.rand() < CR:
                    trial[j] = mutant[j]

            # Evaluate trial
            cap, pow = trial
            if pow / cap > 2.0 or pow / cap < 0.2:
                trial_fitness = -1e9
            else:
                op = simulate_battery_operation(cap, pow, pv_prod, spot_prices, load)
                eco = calculate_economics(cap, pow, op, spot_prices, 3000)
                trial_fitness = eco['npv']

            # Selection
            if trial_fitness > fitness[i]:
                population[i] = trial
                fitness[i] = trial_fitness

                if trial_fitness > best_fitness:
                    best_fitness = trial_fitness
                    best_solution = trial.copy()

        if (gen + 1) % 10 == 0:
            print(f"   Generation {gen+1}: Best NPV = {best_fitness:,.0f} NOK")

    return best_solution, best_fitness

def find_breakeven_cost(capacity_kwh, power_kw, pv_prod, spot_prices, load):
    """Binary search for break-even battery cost"""
    low, high = 100, 10000

    while high - low > 10:
        mid = (low + high) / 2
        op = simulate_battery_operation(capacity_kwh, power_kw, pv_prod, spot_prices, load)
        eco = calculate_economics(capacity_kwh, power_kw, op, spot_prices, mid)

        if eco['npv'] > 0:
            low = mid
        else:
            high = mid

    return (low + high) / 2

# Main execution
print("\n📊 Generating 2024 profiles...")
pv_prod, spot_prices, load = generate_annual_profiles()

print(f"   • PV total: {np.sum(pv_prod)/1000:.1f} MWh/year")
print(f"   • Spot price mean: {np.mean(spot_prices):.3f} NOK/kWh")
print(f"   • Price range: {np.min(spot_prices):.3f} - {np.max(spot_prices):.3f} NOK/kWh")
print(f"   • Load total: {np.sum(load)/1000:.1f} MWh/year")

# Run optimization
best_solution, best_npv = differential_evolution_optimize(pv_prod, spot_prices, load)
optimal_capacity, optimal_power = best_solution

print("\n" + "="*70)
print("✅ OPTIMIZATION RESULTS")
print("="*70)

print(f"\n🔋 Optimal Battery Configuration:")
print(f"   • Capacity: {optimal_capacity:.1f} kWh")
print(f"   • Power: {optimal_power:.1f} kW")
print(f"   • C-rate: {optimal_power/optimal_capacity:.2f}")

# Calculate final economics
operation = simulate_battery_operation(optimal_capacity, optimal_power, pv_prod, spot_prices, load)
economics = calculate_economics(optimal_capacity, optimal_power, operation, spot_prices, 3000)

print(f"\n💰 Economics at 3000 NOK/kWh:")
print(f"   • NPV: {economics['npv']:,.0f} NOK")
print(f"   • Annual revenue: {economics['annual_revenue']:,.0f} NOK/year")
print(f"   • Payback: {(optimal_capacity * 3000) / economics['annual_revenue']:.1f} years")

print(f"\n📈 Revenue breakdown:")
print(f"   • Arbitrage: {economics['arbitrage']:,.0f} NOK/year")
print(f"   • Peak reduction: {economics['peak_savings']:,.0f} NOK/year")
print(f"   • Curtailment: {economics['curtailment_value']:,.0f} NOK/year")

# Find break-even cost
print(f"\n🎯 Finding break-even battery cost...")
breakeven = find_breakeven_cost(optimal_capacity, optimal_power, pv_prod, spot_prices, load)
print(f"   • Break-even: {breakeven:.0f} NOK/kWh")

if breakeven > 3000:
    margin = (breakeven - 3000) / 3000 * 100
    print(f"   ✅ Current prices leave {margin:.0f}% margin")
    print(f"   → Investment is PROFITABLE")
else:
    gap = (3000 - breakeven) / 3000 * 100
    print(f"   ⚠️ Prices need to drop {gap:.0f}% for profitability")
    print(f"   → WAIT for better prices")

print("\n" + "="*70)
print("🎯 KEY INSIGHTS")
print("="*70)

print("\nWith 2023-2025 'new normal' electricity prices:")
print(f"• Summer: ~0.50 NOK/kWh")
print(f"• Winter: ~0.85 NOK/kWh")
print(f"• Price volatility creates arbitrage opportunities")
print(f"• Grid constraint (77 kW) creates curtailment value")
print(f"• Lnett tariff structure rewards peak reduction")

if breakeven > 3500:
    print(f"\n✅ STRONG BUY - Robust profitability")
elif breakeven > 3000:
    print(f"\n✅ BUY - Positive NPV with current prices")
elif breakeven > 2500:
    print(f"\n⚠️ WAIT - Monitor battery price trends")
else:
    print(f"\n❌ NOT VIABLE - Need major cost reductions")

print("\n✅ Standalone test complete!")