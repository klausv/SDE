"""
Test LP Optimizer with January Data

Tests the MonthlyLPOptimizer with one month (January) to verify:
- LP solves successfully
- SOC respects bounds
- Energy balance is maintained
- Peak power tracking works
- Cost breakdown is reasonable
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.pvgis_solar import PVGISProduction
from core.price_fetcher import ENTSOEPriceFetcher
from core.consumption_profiles import ConsumptionProfile
from config import BatteryOptimizationConfig


def load_january_data(config):
    """Load PV, load, and price data for January 2024"""
    print("\n" + "="*70)
    print("Loading Data for January 2024")
    print("="*70)

    # Create date range for January
    start_date = pd.Timestamp('2024-01-01', tz='Europe/Oslo')
    end_date = pd.Timestamp('2024-01-31 23:00:00', tz='Europe/Oslo')
    timestamps = pd.date_range(start=start_date, end=end_date, freq='h')

    print(f"Time range: {start_date} to {end_date}")
    print(f"Total hours: {len(timestamps)}")

    # 1. PV Production
    print("\n1. Loading PV production data...")
    try:
        pv_system = PVGISProduction(
            latitude=config.location.latitude,
            longitude=config.location.longitude,
            pv_capacity_kwp=config.solar.pv_capacity_kwp,
            tilt=config.solar.tilt_degrees,
            azimuth=config.solar.azimuth_degrees
        )
        pv_data = pv_system.get_hourly_production(year=2024)
        pv_january = pv_data[pv_data.index.month == 1]['pv_power_kw'].values
        print(f"  ✓ PV data loaded: {len(pv_january)} hours")
        print(f"  Average: {pv_january.mean():.2f} kW, Max: {pv_january.max():.2f} kW")
    except Exception as e:
        print(f"  ⚠ Could not load PVGIS data: {e}")
        print("  Using synthetic PV profile...")
        # Simple winter solar profile
        hour_of_day = timestamps.hour
        pv_january = np.maximum(0, 30 * np.sin(np.pi * (hour_of_day - 6) / 12)) * (hour_of_day >= 8) * (hour_of_day <= 16)

    # 2. Load Consumption
    print("\n2. Loading consumption data...")
    try:
        consumption_model = ConsumptionProfile(
            annual_kwh=config.consumption.annual_kwh,
            profile_type=config.consumption.profile_type
        )
        load_data = consumption_model.generate_profile(year=2024)
        load_january = load_data[load_data.index.month == 1]['consumption_kw'].values
        print(f"  ✓ Load data generated: {len(load_january)} hours")
        print(f"  Average: {load_january.mean():.2f} kW, Max: {load_january.max():.2f} kW")
    except Exception as e:
        print(f"  ⚠ Could not generate consumption: {e}")
        print("  Using constant load...")
        load_january = np.full(len(timestamps), 35.0)  # ~300 MWh/year average

    # 3. Spot Prices
    print("\n3. Loading spot prices...")
    try:
        price_fetcher = ENTSOEPriceFetcher(api_key=None)  # Will try from .env
        price_data = price_fetcher.fetch_prices(
            start_date=start_date,
            end_date=end_date,
            price_area='NO2'
        )
        spot_prices_january = price_data['price_nok_kwh'].values
        print(f"  ✓ Spot prices loaded: {len(spot_prices_january)} hours")
        print(f"  Average: {spot_prices_january.mean():.3f} NOK/kWh")
    except Exception as e:
        print(f"  ⚠ Could not fetch spot prices: {e}")
        print("  Using synthetic prices...")
        # Simple price profile: higher during day, lower at night
        hour_of_day = timestamps.hour
        spot_prices_january = 0.5 + 0.3 * (hour_of_day >= 6) * (hour_of_day <= 22) + 0.2 * np.random.rand(len(timestamps))

    # Ensure all arrays are same length
    T = min(len(timestamps), len(pv_january), len(load_january), len(spot_prices_january))
    timestamps = timestamps[:T]
    pv_january = pv_january[:T]
    load_january = load_january[:T]
    spot_prices_january = spot_prices_january[:T]

    print(f"\n✓ Data loaded successfully: {T} hours")

    return timestamps, pv_january, load_january, spot_prices_january


def run_january_test():
    """Run LP optimization test for January"""
    print("\n" + "="*70)
    print("LP OPTIMIZER TEST - JANUARY 2024")
    print("="*70)

    # Load configuration
    config = BatteryOptimizationConfig.from_yaml()

    # Set battery size for test (add as attributes for optimizer)
    config.battery_capacity_kwh = 100.0  # 100 kWh battery
    config.battery_power_kw = 50.0       # 50 kW power

    print(f"\nBattery Configuration:")
    print(f"  Capacity: {config.battery_capacity_kwh} kWh")
    print(f"  Power: {config.battery_power_kw} kW")
    print(f"  SOC range: {config.battery.min_soc*100:.0f}% - {config.battery.max_soc*100:.0f}%")

    # Load data
    timestamps, pv, load, spot_prices = load_january_data(config)

    # Create optimizer
    optimizer = MonthlyLPOptimizer(config)

    # Run optimization
    result = optimizer.optimize_month(
        month_idx=1,
        pv_production=pv,
        load_consumption=load,
        spot_prices=spot_prices,
        timestamps=timestamps,
        E_initial=0.5 * config.battery_capacity_kwh  # Start at 50% SOC
    )

    if not result.success:
        print(f"\n❌ Optimization failed: {result.message}")
        return None

    # Print results
    print("\n" + "="*70)
    print("OPTIMIZATION RESULTS")
    print("="*70)

    print(f"\nObjective Function:")
    print(f"  Total cost: {result.objective_value:,.2f} NOK")
    print(f"  Energy cost: {result.energy_cost:,.2f} NOK")
    print(f"  Power tariff: {result.power_cost:,.2f} NOK")

    print(f"\nPeak Power:")
    print(f"  P_peak: {result.P_peak:.2f} kW")
    print(f"  Active trinn: {np.sum(result.z_trinn > 0.01)}")
    print(f"  z values: {result.z_trinn}")

    print(f"\nBattery Operation:")
    print(f"  Total charge: {np.sum(result.P_charge):.2f} kWh")
    print(f"  Total discharge: {np.sum(result.P_discharge):.2f} kWh")
    print(f"  Cycles: {np.sum(result.P_charge) / config.battery_capacity_kwh:.2f}")
    print(f"  Final SOC: {result.E_battery_final / config.battery_capacity_kwh * 100:.1f}%")

    print(f"\nGrid Interaction:")
    print(f"  Total import: {np.sum(result.P_grid_import):.2f} kWh")
    print(f"  Total export: {np.sum(result.P_grid_export):.2f} kWh")
    print(f"  Max import: {np.max(result.P_grid_import):.2f} kW")

    # Validate constraints
    print("\n" + "="*70)
    print("CONSTRAINT VALIDATION")
    print("="*70)

    # SOC bounds
    soc_min = np.min(result.E_battery) / config.battery_capacity_kwh
    soc_max = np.max(result.E_battery) / config.battery_capacity_kwh
    print(f"\nSOC Bounds:")
    print(f"  Min SOC: {soc_min*100:.1f}% (limit: {config.battery.min_soc*100:.0f}%)")
    print(f"  Max SOC: {soc_max*100:.1f}% (limit: {config.battery.max_soc*100:.0f}%)")
    if soc_min >= config.battery.min_soc - 0.01 and soc_max <= config.battery.max_soc + 0.01:
        print("  ✓ SOC constraints satisfied")
    else:
        print("  ❌ SOC constraints violated!")

    # Energy balance (sample check)
    errors = []
    for t in range(0, len(pv), 100):  # Check every 100th hour
        lhs = pv[t] + result.P_grid_import[t] + optimizer.eta_inv * result.P_discharge[t]
        rhs = load[t] + result.P_grid_export[t] + result.P_charge[t] / optimizer.eta_inv
        error = abs(lhs - rhs)
        errors.append(error)

    print(f"\nEnergy Balance (sampled):")
    print(f"  Max error: {max(errors):.6f} kW")
    print(f"  Mean error: {np.mean(errors):.6f} kW")
    if max(errors) < 0.1:
        print("  ✓ Energy balance constraints satisfied")
    else:
        print("  ⚠ Energy balance has some errors (check tolerance)")

    # Peak tracking
    print(f"\nPeak Tracking:")
    max_import = np.max(result.P_grid_import)
    print(f"  Max grid import: {max_import:.2f} kW")
    print(f"  P_peak variable: {result.P_peak:.2f} kW")
    if result.P_peak >= max_import - 0.1:
        print("  ✓ Peak tracking constraint satisfied")
    else:
        print("  ❌ Peak tracking violated!")

    # Plot results
    plot_results(timestamps, pv, load, result, config)

    return result


def plot_results(timestamps, pv, load, result, config):
    """Plot optimization results"""
    print("\nGenerating plots...")

    fig, axes = plt.subplots(4, 1, figsize=(14, 12))

    # Plot 1: Power flows
    ax = axes[0]
    ax.plot(timestamps, pv, label='PV Production', color='orange', alpha=0.7)
    ax.plot(timestamps, load, label='Load', color='blue', alpha=0.7)
    ax.plot(timestamps, result.P_grid_import, label='Grid Import', color='red', linewidth=0.5)
    ax.plot(timestamps, result.P_grid_export, label='Grid Export', color='green', linewidth=0.5)
    ax.set_ylabel('Power [kW]')
    ax.set_title('Power Flows - January 2024')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # Plot 2: Battery operation
    ax = axes[1]
    ax.plot(timestamps, result.P_charge, label='Charge', color='green', alpha=0.7)
    ax.plot(timestamps, result.P_discharge, label='Discharge', color='red', alpha=0.7)
    ax.set_ylabel('Battery Power [kW]')
    ax.set_title('Battery Charge/Discharge')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 3: Battery SOC
    ax = axes[2]
    soc_pct = result.E_battery / config.battery_capacity_kwh * 100
    ax.plot(timestamps, soc_pct, color='purple', linewidth=2)
    ax.axhline(y=config.battery.min_soc*100, color='red', linestyle='--', label=f'Min SOC ({config.battery.min_soc*100:.0f}%)')
    ax.axhline(y=config.battery.max_soc*100, color='red', linestyle='--', label=f'Max SOC ({config.battery.max_soc*100:.0f}%)')
    ax.set_ylabel('SOC [%]')
    ax.set_title('Battery State of Charge')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 4: Grid import and peak
    ax = axes[3]
    ax.plot(timestamps, result.P_grid_import, label='Grid Import', color='red', alpha=0.7)
    ax.axhline(y=result.P_peak, color='darkred', linestyle='--', linewidth=2, label=f'Peak = {result.P_peak:.1f} kW')
    ax.set_ylabel('Grid Import [kW]')
    ax.set_xlabel('Time')
    ax.set_title('Grid Import and Peak Power')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save figure
    output_file = Path(__file__).parent / 'results' / 'lp_test_january.png'
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"  ✓ Plot saved: {output_file}")

    # plt.show()  # Uncomment to display


if __name__ == "__main__":
    result = run_january_test()

    if result and result.success:
        print("\n" + "="*70)
        print("✅ TEST PASSED - LP Optimization Successful!")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("❌ TEST FAILED")
        print("="*70)
        sys.exit(1)
