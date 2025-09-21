#!/usr/bin/env python3
"""
Comprehensive battery optimization simulation for report generation
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
import pickle
import json

warnings.filterwarnings('ignore')

# System configuration
SYSTEM_CONFIG = {
    'pv_capacity_kwp': 138.55,
    'inverter_capacity_kw': 100,
    'grid_limit_kw': 77,
    'location': 'Stavanger',
    'latitude': 58.97,
    'longitude': 5.73,
    'tilt': 15,
    'azimuth': 171,
    'annual_consumption_kwh': 300000,
    'battery_efficiency': 0.90,
    'discount_rate': 0.05,
    'battery_lifetime_years': 15,
    'eur_to_nok': 11.5
}

# Economic parameters
ECONOMIC_PARAMS = {
    'spot_price_avg_2024': 0.85,  # NOK/kWh
    'grid_tariff_peak': 0.296,     # NOK/kWh (06-22 weekdays)
    'grid_tariff_offpeak': 0.176,  # NOK/kWh (nights/weekends)
    'energy_tariff': 0.054,         # NOK/kWh
    'consumption_tax': 0.154,       # NOK/kWh
    'battery_cost_market': 5000,    # NOK/kWh
    'battery_cost_target': 2500,    # NOK/kWh
}

# Power tariff structure (NOK/kW/month)
POWER_TARIFF = [
    (0, 50, 125),
    (50, 100, 95),
    (100, 200, 85),
    (200, 500, 75),
    (500, 1000, 65),
    (1000, float('inf'), 55)
]

def generate_solar_production():
    """Generate realistic solar production profile"""
    hours = pd.date_range(start='2024-01-01', end='2024-12-31 23:00', freq='h')
    production = np.zeros(len(hours))

    for i, hour in enumerate(hours):
        # Day of year for seasonal variation
        day_of_year = hour.dayofyear
        hour_of_day = hour.hour

        # Seasonal factor (peak in summer)
        seasonal = 0.5 + 0.5 * np.cos((day_of_year - 172) * 2 * np.pi / 365)

        # Daily pattern (peak at noon)
        if 4 <= hour_of_day <= 20:
            daily = np.sin((hour_of_day - 4) * np.pi / 16)
        else:
            daily = 0

        # Base production
        base_production = SYSTEM_CONFIG['pv_capacity_kwp'] * seasonal * daily

        # Add some randomness for clouds
        weather_factor = 0.7 + 0.3 * np.random.random()

        production[i] = min(base_production * weather_factor, SYSTEM_CONFIG['inverter_capacity_kw'])

    return pd.Series(production, index=hours, name='production_kw')

def generate_consumption_profile():
    """Generate realistic consumption profile"""
    hours = pd.date_range(start='2024-01-01', end='2024-12-31 23:00', freq='h')
    annual_consumption = SYSTEM_CONFIG['annual_consumption_kwh']
    base_load = annual_consumption / 8760

    consumption = []
    for hour in hours:
        hour_of_day = hour.hour
        is_weekday = hour.weekday() < 5
        month = hour.month

        # Seasonal variation (higher in winter)
        seasonal = 1.2 if month in [11, 12, 1, 2] else 0.9

        # Daily pattern
        if is_weekday:
            if 6 <= hour_of_day <= 9:
                daily_factor = 1.3
            elif 10 <= hour_of_day <= 16:
                daily_factor = 1.1
            elif 17 <= hour_of_day <= 22:
                daily_factor = 1.2
            else:
                daily_factor = 0.7
        else:
            daily_factor = 0.9

        consumption.append(base_load * seasonal * daily_factor)

    return pd.Series(consumption, index=hours, name='consumption_kw')

def get_electricity_prices():
    """Generate electricity price profile"""
    hours = pd.date_range(start='2024-01-01', end='2024-12-31 23:00', freq='h')
    prices = []

    for hour in hours:
        base_price = ECONOMIC_PARAMS['spot_price_avg_2024']
        hour_of_day = hour.hour
        month = hour.month

        # Seasonal variation
        if month in [12, 1, 2]:  # Winter
            seasonal = 1.3
        elif month in [6, 7, 8]:  # Summer
            seasonal = 0.7
        else:
            seasonal = 1.0

        # Daily variation
        if 17 <= hour_of_day <= 20:  # Peak hours
            daily = 1.4
        elif 23 <= hour_of_day or hour_of_day <= 5:  # Night
            daily = 0.6
        else:
            daily = 1.0

        # Add randomness
        random_factor = 0.8 + 0.4 * np.random.random()

        spot_price = base_price * seasonal * daily * random_factor

        # Add grid tariff
        is_peak = hour.weekday() < 5 and 6 <= hour_of_day <= 22
        grid_tariff = ECONOMIC_PARAMS['grid_tariff_peak'] if is_peak else ECONOMIC_PARAMS['grid_tariff_offpeak']

        total_price = spot_price + grid_tariff + ECONOMIC_PARAMS['energy_tariff'] + ECONOMIC_PARAMS['consumption_tax']
        prices.append(total_price)

    return pd.Series(prices, index=hours, name='electricity_price')

def simulate_battery_operation(production, consumption, prices, battery_kwh, battery_kw):
    """Simulate battery operation for a full year"""
    hours = len(production)
    soc = np.zeros(hours)  # State of charge
    battery_charge = np.zeros(hours)
    battery_discharge = np.zeros(hours)
    curtailment = np.zeros(hours)
    grid_import = np.zeros(hours)
    grid_export = np.zeros(hours)

    soc[0] = battery_kwh * 0.5  # Start at 50% charge
    efficiency = SYSTEM_CONFIG['battery_efficiency']

    for i in range(1, hours):
        net_production = production.iloc[i] - consumption.iloc[i]

        if net_production > 0:
            # Excess production
            if production.iloc[i] > SYSTEM_CONFIG['grid_limit_kw']:
                # Need to curtail or store
                excess = production.iloc[i] - SYSTEM_CONFIG['grid_limit_kw']

                # Try to charge battery
                charge_available = min(excess, battery_kw)
                charge_possible = min(charge_available, (battery_kwh - soc[i-1]) / efficiency)

                battery_charge[i] = charge_possible
                soc[i] = soc[i-1] + charge_possible * efficiency
                curtailment[i] = excess - charge_possible

                # Export remaining to grid (up to limit)
                export_available = production.iloc[i] - consumption.iloc[i] - curtailment[i] - battery_charge[i]
                grid_export[i] = min(export_available, SYSTEM_CONFIG['grid_limit_kw'])
            else:
                # No curtailment needed
                charge_available = min(net_production, battery_kw)
                charge_possible = min(charge_available, (battery_kwh - soc[i-1]) / efficiency)

                battery_charge[i] = charge_possible
                soc[i] = soc[i-1] + charge_possible * efficiency
                grid_export[i] = net_production - battery_charge[i]
        else:
            # Net consumption
            deficit = -net_production

            # Try to discharge battery
            discharge_available = min(deficit, battery_kw)
            discharge_possible = min(discharge_available, soc[i-1])

            battery_discharge[i] = discharge_possible
            soc[i] = soc[i-1] - discharge_possible

            # Import remaining from grid
            grid_import[i] = deficit - discharge_possible

    results = pd.DataFrame({
        'production': production,
        'consumption': consumption,
        'prices': prices,
        'soc': soc,
        'battery_charge': battery_charge,
        'battery_discharge': battery_discharge,
        'curtailment': curtailment,
        'grid_import': grid_import,
        'grid_export': grid_export
    })

    return results

def calculate_economics(results, battery_kwh, battery_cost_per_kwh):
    """Calculate economic metrics"""
    # Energy savings from avoided curtailment
    curtailment_value = results['curtailment'].sum() * ECONOMIC_PARAMS['spot_price_avg_2024']

    # Arbitrage value (simplified)
    arbitrage_value = (results['battery_discharge'] * results['prices']).sum() - \
                     (results['battery_charge'] * results['prices']).sum()

    # Power tariff savings (simplified)
    monthly_peaks_no_battery = results.groupby(pd.Grouper(freq='ME'))['grid_import'].max()
    monthly_peaks_with_battery = (results['grid_import'] - results['battery_discharge']).groupby(pd.Grouper(freq='ME')).max()

    power_savings = 0
    for peak_no, peak_with in zip(monthly_peaks_no_battery, monthly_peaks_with_battery):
        tariff_no = get_power_tariff(peak_no)
        tariff_with = get_power_tariff(peak_with)
        power_savings += (tariff_no - tariff_with) * max(peak_no, peak_with)

    # Total annual savings
    annual_savings = curtailment_value + arbitrage_value + power_savings * 12

    # Investment
    investment = battery_kwh * battery_cost_per_kwh

    # NPV calculation
    discount_rate = SYSTEM_CONFIG['discount_rate']
    lifetime = SYSTEM_CONFIG['battery_lifetime_years']

    npv = -investment
    for year in range(1, lifetime + 1):
        npv += annual_savings / (1 + discount_rate) ** year

    # IRR calculation (simplified)
    if annual_savings > 0:
        irr = (annual_savings / investment) - (1 / lifetime)
    else:
        irr = -1

    # Payback period
    if annual_savings > 0:
        payback = investment / annual_savings
    else:
        payback = float('inf')

    return {
        'npv': npv,
        'irr': irr,
        'payback': payback,
        'annual_savings': annual_savings,
        'curtailment_value': curtailment_value,
        'arbitrage_value': arbitrage_value,
        'power_savings': power_savings * 12,
        'investment': investment
    }

def get_power_tariff(peak_kw):
    """Get power tariff based on peak demand"""
    for min_kw, max_kw, tariff in POWER_TARIFF:
        if min_kw <= peak_kw < max_kw:
            return tariff
    return POWER_TARIFF[-1][2]

def optimize_battery_size():
    """Find optimal battery size"""
    battery_sizes = np.arange(10, 201, 10)  # 10 to 200 kWh
    results_list = []

    # Generate data once
    production = generate_solar_production()
    consumption = generate_consumption_profile()
    prices = get_electricity_prices()

    for battery_kwh in battery_sizes:
        battery_kw = battery_kwh * 0.5  # C-rate of 0.5

        # Simulate operation
        sim_results = simulate_battery_operation(production, consumption, prices, battery_kwh, battery_kw)

        # Calculate economics at different price points
        for cost_name, cost_per_kwh in [('market', ECONOMIC_PARAMS['battery_cost_market']),
                                        ('target', ECONOMIC_PARAMS['battery_cost_target'])]:
            economics = calculate_economics(sim_results, battery_kwh, cost_per_kwh)

            results_list.append({
                'battery_kwh': battery_kwh,
                'battery_kw': battery_kw,
                'cost_scenario': cost_name,
                'cost_per_kwh': cost_per_kwh,
                **economics
            })

    return pd.DataFrame(results_list), production, consumption, prices

# Run optimization
print("Running battery optimization simulation...")
optimization_results, production, consumption, prices = optimize_battery_size()

# Find optimal size
optimal_target = optimization_results[optimization_results['cost_scenario'] == 'target'].nlargest(1, 'npv').iloc[0]
optimal_market = optimization_results[optimization_results['cost_scenario'] == 'market'].nlargest(1, 'npv').iloc[0]

# Run detailed simulation for base case (50 kWh, 25 kW)
base_battery_kwh = 50
base_battery_kw = 25
base_results = simulate_battery_operation(production, consumption, prices, base_battery_kwh, base_battery_kw)
base_economics = calculate_economics(base_results, base_battery_kwh, ECONOMIC_PARAMS['battery_cost_target'])

# Save results
results_package = {
    'system_config': SYSTEM_CONFIG,
    'economic_params': ECONOMIC_PARAMS,
    'optimization_results': optimization_results,
    'base_results': base_results,
    'base_economics': base_economics,
    'optimal_target': optimal_target.to_dict(),
    'optimal_market': optimal_market.to_dict(),
    'production': production,
    'consumption': consumption,
    'prices': prices,
    'timestamp': datetime.now().isoformat()
}

# Save as pickle for easy loading
with open('results/simulation_results.pkl', 'wb') as f:
    pickle.dump(results_package, f)

# Save summary as JSON
summary = {
    'optimal_battery_kwh': float(optimal_target['battery_kwh']),
    'optimal_battery_kw': float(optimal_target['battery_kw']),
    'npv_at_target_cost': float(optimal_target['npv']),
    'npv_at_market_cost': float(optimal_market['npv']),
    'payback_years': float(optimal_target['payback']),
    'annual_savings': float(optimal_target['annual_savings']),
    'break_even_cost': float(ECONOMIC_PARAMS['battery_cost_target']),
    'market_cost': float(ECONOMIC_PARAMS['battery_cost_market']),
    'base_case_npv': float(base_economics['npv'])
}

with open('results/simulation_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print(f"Simulation complete!")
print(f"Optimal battery size: {optimal_target['battery_kwh']:.0f} kWh @ {optimal_target['battery_kw']:.0f} kW")
print(f"NPV at target cost ({ECONOMIC_PARAMS['battery_cost_target']} NOK/kWh): {optimal_target['npv']:,.0f} NOK")
print(f"NPV at market cost ({ECONOMIC_PARAMS['battery_cost_market']} NOK/kWh): {optimal_market['npv']:,.0f} NOK")
print(f"Payback period: {optimal_target['payback']:.1f} years")
print(f"Results saved to battery_optimization/results/")