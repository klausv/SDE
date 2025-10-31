"""
Yearly LP Optimization with Real Data

Uses:
- PVGIS for solar production data
- ENTSO-E for spot prices
- ConsumptionProfile for realistic commercial load

Generates comprehensive visualizations and compares with reference case (no battery).
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.economic_cost import calculate_total_cost
from config import BatteryOptimizationConfig


def load_real_yearly_data(config):
    """
    Load real yearly data for 2024.

    Uses:
    - PVGIS for solar production
    - ENTSO-E for spot prices
    - ConsumptionProfile for load (synthetic but realistic)
    """
    print("\n" + "="*70)
    print("Loading Real Yearly Data for 2024")
    print("="*70)

    # Date range for 2024
    start_date = pd.Timestamp('2024-01-01', tz='Europe/Oslo')
    end_date = pd.Timestamp('2024-12-31 23:00:00', tz='Europe/Oslo')
    timestamps = pd.date_range(start=start_date, end=end_date, freq='h')

    print(f"Time range: {start_date} to {end_date}")
    print(f"Total hours: {len(timestamps)}")

    # 1. Solar Production (PVGIS)
    print("\n1. Loading PVGIS solar production data...")
    try:
        from core.pvgis_solar import PVGISProduction

        pv_system = PVGISProduction(
            lat=config.location.latitude,
            lon=config.location.longitude,
            pv_capacity_kwp=config.solar.pv_capacity_kwp,
            tilt=config.solar.tilt_degrees,
            azimuth=config.solar.azimuth_degrees
        )
        # Correct method: fetch_hourly_production (uses cache if available)
        pv_data = pv_system.fetch_hourly_production(year=2024, refresh=False)

        # pv_data is a Series with production values
        # Ensure we have full year
        if len(pv_data) < len(timestamps):
            print(f"  ⚠ PVGIS returned {len(pv_data)} hours, padding to {len(timestamps)}")
            pv_array = np.zeros(len(timestamps))
            pv_array[:len(pv_data)] = pv_data.values
        else:
            pv_array = pv_data.values[:len(timestamps)]

        print(f"  ✓ PVGIS data loaded successfully")
        print(f"    Mean: {pv_array.mean():.2f} kW")
        print(f"    Max: {pv_array.max():.2f} kW")
        print(f"    Annual: {pv_array.sum():,.0f} kWh")

    except Exception as e:
        print(f"  ⚠ Could not load PVGIS data: {e}")
        print("  Using synthetic solar profile...")
        # Fallback to synthetic
        day_of_year = timestamps.dayofyear.values
        hour_of_day = timestamps.hour.values
        seasonal_factor = 1 + 0.8 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
        daily_factor = np.maximum(0, np.sin(np.pi * (hour_of_day - 6) / 12))
        pv_array = config.solar.pv_capacity_kwp * seasonal_factor * daily_factor * 0.7
        pv_array = np.maximum(0, pv_array)

    # 2. Load Consumption (ConsumptionProfile)
    print("\n2. Generating consumption profile...")
    try:
        # Use ConsumptionProfile from core module
        # This should generate a realistic commercial profile

        # Simple commercial profile for now
        hour_of_day = timestamps.hour.values
        is_daytime = (hour_of_day >= 6) & (hour_of_day <= 22)
        is_weekend = timestamps.weekday.values >= 5

        base_load = 8.0  # kW base load
        daytime_boost = 4.0 * is_daytime  # Higher during business hours
        weekend_reduction = -2.0 * is_weekend  # Lower on weekends

        # Add hourly variation
        load_array = base_load + daytime_boost + weekend_reduction + np.random.normal(0, 1, len(timestamps))
        load_array = np.maximum(2, load_array)

        # Scale to match annual target
        annual_target = config.consumption.annual_kwh
        current_annual = load_array.sum()
        load_array *= (annual_target / current_annual)

        print(f"  ✓ Load profile generated")
        print(f"    Annual target: {annual_target:,.0f} kWh")
        print(f"    Mean: {load_array.mean():.2f} kW")
        print(f"    Max: {load_array.max():.2f} kW")
        print(f"    Annual: {load_array.sum():,.0f} kWh")

    except Exception as e:
        print(f"  ⚠ Could not generate consumption: {e}")
        load_array = np.full(len(timestamps), config.consumption.annual_kwh / 8760)

    # 3. Spot Prices (ENTSO-E)
    print("\n3. Loading spot prices from ENTSO-E...")
    try:
        from core.price_fetcher import ENTSOEPriceFetcher

        fetcher = ENTSOEPriceFetcher()
        # Correct method signature: fetch_prices(year, area, refresh, use_fallback)
        price_data = fetcher.fetch_prices(
            year=2024,
            area='NO2',
            refresh=False,
            use_fallback=True
        )

        # price_data is a Series with timezone-aware index
        # Reindex to match our timestamps exactly
        price_data_aligned = price_data.reindex(timestamps)

        # Fill any NaN values (from timezone mismatches or missing hours)
        if price_data_aligned.isna().any():
            n_missing = price_data_aligned.isna().sum()
            print(f"  ⚠ {n_missing} hours with missing prices, filling with forward fill")
            price_data_aligned = price_data_aligned.fillna(method='ffill').fillna(method='bfill')

        spot_array = price_data_aligned.values

        print(f"  ✓ Spot prices loaded successfully")
        print(f"    Mean: {spot_array.mean():.3f} NOK/kWh")
        print(f"    Min: {spot_array.min():.3f} NOK/kWh")
        print(f"    Max: {spot_array.max():.3f} NOK/kWh")

    except Exception as e:
        print(f"  ⚠ Could not fetch spot prices: {e}")
        print("  Using synthetic prices...")
        # Fallback to synthetic with realistic patterns
        hour_of_day = timestamps.hour.values
        month = timestamps.month.values
        is_daytime = (hour_of_day >= 6) & (hour_of_day <= 22)

        # Seasonal (winter expensive)
        seasonal_price = 0.6 + 0.4 * ((month <= 3) | (month >= 11))
        # Daily (peak hours expensive)
        daily_price = 1.0 + 0.3 * is_daytime
        # Random volatility
        random_price = np.random.lognormal(0, 0.3, len(timestamps))

        spot_array = 0.5 * seasonal_price * daily_price * random_price

    # Create DataFrame
    data = pd.DataFrame({
        'pv_production': pv_array,
        'load': load_array,
        'spot_price': spot_array
    }, index=timestamps)

    print(f"\n✓ Data loaded successfully")
    print(f"  Total hours: {len(data)}")

    return data


def run_reference_case(data, config):
    """Reference case: no battery"""
    print("\n" + "="*70)
    print("Running Reference Case (No Battery)")
    print("="*70)

    net = data['pv_production'] - data['load']
    grid_import = np.maximum(0, -net)
    grid_export_uncapped = np.maximum(0, net)
    grid_export = np.minimum(grid_export_uncapped, config.solar.grid_export_limit_kw)
    curtailment = grid_export_uncapped - grid_export

    print(f"Grid import: {grid_import.sum():,.0f} kWh")
    print(f"Grid export: {grid_export.sum():,.0f} kWh")
    print(f"Curtailment: {curtailment.sum():,.0f} kWh ({curtailment.sum()/data['pv_production'].sum()*100:.1f}% of PV)")

    cost_result = calculate_total_cost(
        grid_import_power=grid_import,
        grid_export_power=grid_export,
        timestamps=data.index,
        spot_prices=data['spot_price'].values
    )

    print(f"\nReference Costs:")
    print(f"  Total: {cost_result['total_cost_nok']:,.0f} NOK/year")
    print(f"  Energy: {cost_result['energy_cost_nok']:,.0f} NOK/year")
    print(f"  Peak: {cost_result['peak_cost_nok']:,.0f} NOK/year")

    return cost_result, grid_import, grid_export, curtailment


def run_yearly_lp_optimization(data, config):
    """Run 12 monthly LP optimizations"""
    print("\n" + "="*70)
    print("Running Yearly LP Optimization (12 Months)")
    print("="*70)

    optimizer = MonthlyLPOptimizer(config)
    E_initial = 0.5 * config.battery_capacity_kwh

    monthly_results = []
    all_arrays = {
        'P_charge': [],
        'P_discharge': [],
        'P_grid_import': [],
        'P_grid_export': [],
        'E_battery': [],
        'P_peak': []
    }

    for month in range(1, 13):
        print(f"\n--- Month {month}/12 ---")
        month_data = data[data.index.month == month]

        result = optimizer.optimize_month(
            month_idx=month,
            pv_production=month_data['pv_production'].values,
            load_consumption=month_data['load'].values,
            spot_prices=month_data['spot_price'].values,
            timestamps=month_data.index,
            E_initial=E_initial
        )

        if not result.success:
            print(f"❌ Month {month} failed: {result.message}")
            return None

        monthly_results.append(result)
        all_arrays['P_charge'].append(result.P_charge)
        all_arrays['P_discharge'].append(result.P_discharge)
        all_arrays['P_grid_import'].append(result.P_grid_import)
        all_arrays['P_grid_export'].append(result.P_grid_export)
        all_arrays['E_battery'].append(result.E_battery)
        all_arrays['P_peak'].append(result.P_peak)

        E_initial = result.E_battery_final
        print(f"✓ Month {month}: {result.objective_value:,.0f} NOK, Peak: {result.P_peak:.1f} kW")

    # Concatenate results
    yearly_results = {
        'P_charge': np.concatenate(all_arrays['P_charge']),
        'P_discharge': np.concatenate(all_arrays['P_discharge']),
        'P_grid_import': np.concatenate(all_arrays['P_grid_import']),
        'P_grid_export': np.concatenate(all_arrays['P_grid_export']),
        'E_battery': np.concatenate(all_arrays['E_battery']),
        'monthly_peaks': all_arrays['P_peak']
    }

    # Calculate total cost
    cost_result = calculate_total_cost(
        grid_import_power=yearly_results['P_grid_import'],
        grid_export_power=yearly_results['P_grid_export'],
        timestamps=data.index,
        spot_prices=data['spot_price'].values
    )

    print("\n" + "="*70)
    print(f"LP Total Costs: {cost_result['total_cost_nok']:,.0f} NOK/year")
    print(f"  Energy: {cost_result['energy_cost_nok']:,.0f} NOK/year")
    print(f"  Peak: {cost_result['peak_cost_nok']:,.0f} NOK/year")
    print(f"\nBattery:")
    print(f"  Total charge: {yearly_results['P_charge'].sum():,.0f} kWh")
    print(f"  Total discharge: {yearly_results['P_discharge'].sum():,.0f} kWh")
    print(f"  Cycles: {yearly_results['P_charge'].sum() / config.battery_capacity_kwh:.1f}")

    return yearly_results, cost_result, monthly_results


def plot_comprehensive_results(data, ref_results, lp_results, config):
    """Generate comprehensive visualization"""
    print("\nGenerating comprehensive plots...")

    timestamps = data.index

    fig = plt.figure(figsize=(16, 20))
    gs = fig.add_gridspec(6, 2, hspace=0.3, wspace=0.3)

    # 1. PV and Load (full year)
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(timestamps, data['pv_production'], label='PV Production', color='orange', alpha=0.7, linewidth=0.5)
    ax1.plot(timestamps, data['load'], label='Load', color='blue', alpha=0.7, linewidth=0.5)
    ax1.set_ylabel('Power [kW]')
    ax1.set_title('PV Production and Load - Full Year 2024', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)

    # 2. Spot Prices (full year)
    ax2 = fig.add_subplot(gs[1, :])
    ax2.plot(timestamps, data['spot_price'], color='green', linewidth=0.5)
    ax2.set_ylabel('Price [NOK/kWh]')
    ax2.set_title('Spot Prices - Full Year 2024', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    # 3. Grid Import Comparison (Reference vs LP)
    ax3 = fig.add_subplot(gs[2, 0])
    ax3.plot(timestamps, ref_results['grid_import'], label='Reference (no battery)',
             color='red', alpha=0.6, linewidth=0.5)
    ax3.plot(timestamps, lp_results['P_grid_import'], label='LP with battery',
             color='darkred', alpha=0.8, linewidth=0.5)
    ax3.set_ylabel('Grid Import [kW]')
    ax3.set_title('Grid Import Comparison', fontsize=12, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. Grid Export Comparison
    ax4 = fig.add_subplot(gs[2, 1])
    ax4.plot(timestamps, ref_results['grid_export'], label='Reference (no battery)',
             color='green', alpha=0.6, linewidth=0.5)
    ax4.plot(timestamps, lp_results['P_grid_export'], label='LP with battery',
             color='darkgreen', alpha=0.8, linewidth=0.5)
    ax4.set_ylabel('Grid Export [kW]')
    ax4.set_title('Grid Export Comparison', fontsize=12, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. Battery Charge/Discharge
    ax5 = fig.add_subplot(gs[3, :])
    ax5.fill_between(timestamps, 0, lp_results['P_charge'], label='Charge',
                     color='green', alpha=0.5)
    ax5.fill_between(timestamps, 0, -lp_results['P_discharge'], label='Discharge',
                     color='red', alpha=0.5)
    ax5.set_ylabel('Battery Power [kW]')
    ax5.set_title('Battery Charge/Discharge Power - Full Year', fontsize=14, fontweight='bold')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    ax5.axhline(y=0, color='black', linewidth=0.5)

    # 6. Battery SOC
    ax6 = fig.add_subplot(gs[4, :])
    soc_pct = lp_results['E_battery'] / config.battery_capacity_kwh * 100
    ax6.plot(timestamps, soc_pct, color='purple', linewidth=1)
    ax6.axhline(y=config.battery.min_soc*100, color='red', linestyle='--',
                label=f'Min SOC ({config.battery.min_soc*100:.0f}%)')
    ax6.axhline(y=config.battery.max_soc*100, color='red', linestyle='--',
                label=f'Max SOC ({config.battery.max_soc*100:.0f}%)')
    ax6.fill_between(timestamps, config.battery.min_soc*100, config.battery.max_soc*100,
                     color='gray', alpha=0.1)
    ax6.set_ylabel('SOC [%]')
    ax6.set_title('Battery State of Charge - Full Year', fontsize=14, fontweight='bold')
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    # 7. Monthly Peak Powers
    ax7 = fig.add_subplot(gs[5, :])
    months = np.arange(1, 13)
    ref_monthly_peaks = []
    for month in months:
        month_import = ref_results['grid_import'][data.index.month == month]
        ref_monthly_peaks.append(month_import.max())

    x = np.arange(len(months))
    width = 0.35
    ax7.bar(x - width/2, ref_monthly_peaks, width, label='Reference (no battery)', color='red', alpha=0.7)
    ax7.bar(x + width/2, lp_results['monthly_peaks'], width, label='LP with battery', color='darkred', alpha=0.9)
    ax7.set_xlabel('Month')
    ax7.set_ylabel('Peak Power [kW]')
    ax7.set_title('Monthly Peak Powers - Comparison', fontsize=14, fontweight='bold')
    ax7.set_xticks(x)
    ax7.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    ax7.legend()
    ax7.grid(True, alpha=0.3, axis='y')

    plt.suptitle('LP Battery Optimization - Comprehensive Results 2024',
                 fontsize=16, fontweight='bold', y=0.995)

    # Save
    battery_label = f"{int(config.battery_capacity_kwh)}kWh_{int(config.battery_power_kw)}kW"
    output_file = Path(__file__).parent / 'results' / f'lp_yearly_comprehensive_{battery_label}.png'
    output_file.parent.mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"  ✓ Comprehensive plot saved: {output_file}")

    # Also create zoomed plots for specific months
    plot_january_detail(data, lp_results, config)
    plot_may_detail(data, lp_results, config)


def plot_january_detail(data, lp_results, config):
    """Detailed plot for January"""
    print("  Generating January detail plot...")

    # Extract January data
    jan_mask = data.index.month == 1
    jan_timestamps = data.index[jan_mask]

    fig, axes = plt.subplots(4, 1, figsize=(14, 12))

    # 1. PV, Load, Grid
    ax = axes[0]
    ax.plot(jan_timestamps, data.loc[jan_mask, 'pv_production'], label='PV', color='orange', linewidth=1.5)
    ax.plot(jan_timestamps, data.loc[jan_mask, 'load'], label='Load', color='blue', linewidth=1.5)
    ax.plot(jan_timestamps, lp_results['P_grid_import'][jan_mask], label='Grid Import',
            color='red', linewidth=1, alpha=0.7)
    ax.set_ylabel('Power [kW]')
    ax.set_title('January 2024 - Power Flows', fontsize=12, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # 2. Battery Power
    ax = axes[1]
    ax.fill_between(jan_timestamps, 0, lp_results['P_charge'][jan_mask],
                    label='Charge', color='green', alpha=0.6)
    ax.fill_between(jan_timestamps, 0, -lp_results['P_discharge'][jan_mask],
                    label='Discharge', color='red', alpha=0.6)
    ax.axhline(y=0, color='black', linewidth=0.5)
    ax.set_ylabel('Battery Power [kW]')
    ax.set_title('Battery Charge/Discharge', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. Battery SOC
    ax = axes[2]
    soc_pct = lp_results['E_battery'][jan_mask] / config.battery_capacity_kwh * 100
    ax.plot(jan_timestamps, soc_pct, color='purple', linewidth=2)
    ax.axhline(y=config.battery.min_soc*100, color='red', linestyle='--', linewidth=1)
    ax.axhline(y=config.battery.max_soc*100, color='red', linestyle='--', linewidth=1)
    ax.fill_between(jan_timestamps, config.battery.min_soc*100, config.battery.max_soc*100,
                    color='gray', alpha=0.1)
    ax.set_ylabel('SOC [%]')
    ax.set_title('Battery State of Charge', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # 4. Spot Prices
    ax = axes[3]
    ax.plot(jan_timestamps, data.loc[jan_mask, 'spot_price'], color='green', linewidth=1.5)
    ax.set_ylabel('Price [NOK/kWh]')
    ax.set_xlabel('Date')
    ax.set_title('Spot Prices', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    battery_label = f"{int(config.battery_capacity_kwh)}kWh_{int(config.battery_power_kw)}kW"
    output_file = Path(__file__).parent / 'results' / f'lp_january_detail_{battery_label}.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"  ✓ January detail plot saved: {output_file}")


def plot_may_detail(data, lp_results, config):
    """Detailed plot for May"""
    print("  Generating May detail plot...")

    # Extract May data
    may_mask = data.index.month == 5
    may_timestamps = data.index[may_mask]

    fig, axes = plt.subplots(4, 1, figsize=(14, 12))

    # 1. PV, Load, Grid
    ax = axes[0]
    ax.plot(may_timestamps, data.loc[may_mask, 'pv_production'], label='PV', color='orange', linewidth=1.5)
    ax.plot(may_timestamps, data.loc[may_mask, 'load'], label='Load', color='blue', linewidth=1.5)
    ax.plot(may_timestamps, lp_results['P_grid_import'][may_mask], label='Grid Import',
            color='red', linewidth=1, alpha=0.7)
    ax.set_ylabel('Power [kW]')
    ax.set_title('May 2024 - Power Flows', fontsize=12, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # 2. Battery Power
    ax = axes[1]
    ax.fill_between(may_timestamps, 0, lp_results['P_charge'][may_mask],
                    label='Charge', color='green', alpha=0.6)
    ax.fill_between(may_timestamps, 0, -lp_results['P_discharge'][may_mask],
                    label='Discharge', color='red', alpha=0.6)
    ax.axhline(y=0, color='black', linewidth=0.5)
    ax.set_ylabel('Battery Power [kW]')
    ax.set_title('Battery Charge/Discharge', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. Battery SOC
    ax = axes[2]
    soc_pct = lp_results['E_battery'][may_mask] / config.battery_capacity_kwh * 100
    ax.plot(may_timestamps, soc_pct, color='purple', linewidth=2)
    ax.axhline(y=config.battery.min_soc*100, color='red', linestyle='--', linewidth=1)
    ax.axhline(y=config.battery.max_soc*100, color='red', linestyle='--', linewidth=1)
    ax.fill_between(may_timestamps, config.battery.min_soc*100, config.battery.max_soc*100,
                    color='gray', alpha=0.1)
    ax.set_ylabel('SOC [%]')
    ax.set_title('Battery State of Charge', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # 4. Spot Prices
    ax = axes[3]
    ax.plot(may_timestamps, data.loc[may_mask, 'spot_price'], color='green', linewidth=1.5)
    ax.set_ylabel('Price [NOK/kWh]')
    ax.set_xlabel('Date')
    ax.set_title('Spot Prices', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    battery_label = f"{int(config.battery_capacity_kwh)}kWh_{int(config.battery_power_kw)}kW"
    output_file = Path(__file__).parent / 'results' / f'lp_may_detail_{battery_label}.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"  ✓ May detail plot saved: {output_file}")


def analyze_revenue_streams(data, lp_results, cost_ref, cost_lp,
                            grid_import_ref, grid_export_ref, curtailment_ref):
    """
    Detailed breakdown of revenue streams:
    1. Reduced power tariff (peak shaving)
    2. Spot price arbitrage
    3. Increased self-consumption
    4. Reduced curtailment
    """
    print("\n" + "="*70)
    print("REVENUE STREAM ANALYSIS")
    print("="*70)

    # Extract LP grid flows
    P_grid_import_lp = lp_results['P_grid_import']
    P_grid_export_lp = lp_results['P_grid_export']

    # PV and Load
    pv_production = data['pv_production'].values
    load = data['load'].values
    spot_prices = data['spot_price'].values

    # Calculate curtailment with LP
    # Curtailment = PV that couldn't be used or exported due to grid limit
    # Net without battery: pv - load
    # Grid export is capped, so curtailment = max(0, net - grid_limit) when net > 0
    net_ref = pv_production - load
    grid_limit = 77.0  # kW

    # With battery, curtailment is reduced
    # Total PV usage = self-consumption + export + battery charging
    pv_to_battery = lp_results['P_charge']  # PV that goes to battery (simplified)
    curtailment_lp = np.sum(np.maximum(0, pv_production - load - P_grid_export_lp - pv_to_battery/0.98))
    curtailment_lp = max(0, curtailment_lp)

    # 1. REDUCED POWER TARIFF
    peak_savings = cost_ref['peak_cost_nok'] - cost_lp['peak_cost_nok']

    print(f"\n1. REDUCED POWER TARIFF (Peak Shaving)")
    print(f"  Reference peak cost: {cost_ref['peak_cost_nok']:,.0f} NOK")
    print(f"  LP peak cost: {cost_lp['peak_cost_nok']:,.0f} NOK")
    print(f"  → Savings: {peak_savings:,.0f} NOK/year")

    # 2. SPOT PRICE ARBITRAGE
    # Energy bought/sold at different prices
    # Simplified: battery enables buying cheap and selling expensive
    energy_cost_reduction = cost_ref['energy_cost_nok'] - cost_lp['energy_cost_nok']

    # More detailed: compare import/export values
    # Reference import cost
    import_cost_ref = np.sum(grid_import_ref * spot_prices)  # Simplified, no tariffs
    export_revenue_ref = np.sum(grid_export_ref * 0.04)  # Feed-in tariff

    # LP import/export
    import_cost_lp = np.sum(P_grid_import_lp * spot_prices)
    export_revenue_lp = np.sum(P_grid_export_lp * 0.04)

    # Arbitrage benefit (rough estimate)
    # Difference in net energy cost beyond what's explained by self-consumption
    arbitrage_benefit = (import_cost_ref - import_cost_lp) - (export_revenue_ref - export_revenue_lp)

    print(f"\n2. ENERGY COST REDUCTION (includes arbitrage and self-consumption)")
    print(f"  Reference energy cost: {cost_ref['energy_cost_nok']:,.0f} NOK")
    print(f"  LP energy cost: {cost_lp['energy_cost_nok']:,.0f} NOK")
    print(f"  → Savings: {energy_cost_reduction:,.0f} NOK/year")

    # 3. INCREASED SELF-CONSUMPTION
    # PV used directly or via battery instead of exporting
    # Reference: all PV surplus exported at spot + 0.04 NOK/kWh
    # With battery: some PV stored and used later, saves import cost

    pv_export_ref = np.sum(grid_export_ref)
    pv_export_lp = np.sum(P_grid_export_lp)
    reduced_export = pv_export_ref - pv_export_lp

    # This PV was stored in battery and used later instead of:
    # - Exporting at spot + 0.04 NOK/kWh (~0.616 NOK/kWh)
    # - Later importing at spot + tariffs (~1.02 NOK/kWh)
    avg_spot_price = np.mean(spot_prices)
    avg_import_price = avg_spot_price + 0.296 + 0.15  # spot + tariff + tax (simplified)
    avg_export_price = avg_spot_price + 0.04  # spot + plusskunde
    self_consumption_value = reduced_export * (avg_import_price - avg_export_price)

    print(f"\n3. INCREASED SELF-CONSUMPTION")
    print(f"  Reference grid export: {pv_export_ref:,.0f} kWh")
    print(f"  LP grid export: {pv_export_lp:,.0f} kWh")
    print(f"  Reduced export (stored for later use): {reduced_export:,.0f} kWh")
    print(f"  Value (avoided import @ {avg_import_price:.2f} - lost export @ {avg_export_price:.2f}): {self_consumption_value:,.0f} NOK/year")

    # 4. REDUCED CURTAILMENT
    curtailment_ref_total = np.sum(curtailment_ref)
    curtailment_reduction = curtailment_ref_total - curtailment_lp
    # Value: PV that was wasted is now used (either direct or via battery)
    curtailment_value = curtailment_reduction * avg_import_price

    print(f"\n4. REDUCED CURTAILMENT")
    print(f"  Reference curtailment: {curtailment_ref_total:,.0f} kWh")
    print(f"  LP curtailment: {curtailment_lp:,.0f} kWh")
    print(f"  Recovered energy: {curtailment_reduction:,.0f} kWh")
    print(f"  → Value: {curtailment_value:,.0f} NOK/year")

    # TOTAL CHECK
    total_breakdown = peak_savings + energy_cost_reduction
    total_actual = cost_ref['total_cost_nok'] - cost_lp['total_cost_nok']

    print(f"\n" + "="*70)
    print(f"TOTAL SAVINGS BREAKDOWN:")
    print(f"  1. Reduced power tariff: {peak_savings:,.0f} NOK ({peak_savings/total_actual*100:.1f}%)")
    print(f"  2. Energy cost reduction: {energy_cost_reduction:,.0f} NOK ({energy_cost_reduction/total_actual*100:.1f}%)")
    print(f"     - Arbitrage component: ~{arbitrage_benefit:,.0f} NOK")
    print(f"     - Self-consumption: ~{self_consumption_value:,.0f} NOK")
    print(f"     - Curtailment recovery: ~{curtailment_value:,.0f} NOK")
    print(f"  → TOTAL: {total_actual:,.0f} NOK/year")

    # AVERAGE PRICE ACHIEVED FOR SOLAR
    print(f"\n" + "="*70)
    print(f"AVERAGE PRICE ACHIEVED FOR SOLAR POWER:")
    print(f"="*70)

    total_pv = np.sum(pv_production)

    # Reference case: all solar either self-consumed or exported
    # Self-consumed: saves import cost
    # Exported: gets spot price + feed-in tariff (plusskunde-støtte)
    avg_spot_price = np.mean(spot_prices)
    avg_export_price = avg_spot_price + 0.04  # spot + plusskunde-støtte

    pv_self_consumed_ref = total_pv - pv_export_ref - curtailment_ref_total
    revenue_ref = pv_self_consumed_ref * avg_import_price + pv_export_ref * avg_export_price
    avg_price_ref = revenue_ref / (total_pv - curtailment_ref_total) if (total_pv - curtailment_ref_total) > 0 else 0

    print(f"\nREFERENCE CASE (no battery):")
    print(f"  Total PV production: {total_pv:,.0f} kWh")
    print(f"  Self-consumed: {pv_self_consumed_ref:,.0f} kWh @ ~{avg_import_price:.2f} NOK/kWh (avoided import)")
    print(f"  Exported: {pv_export_ref:,.0f} kWh @ ~{avg_export_price:.2f} NOK/kWh (spot + plusskunde)")
    print(f"  Curtailed (lost): {curtailment_ref_total:,.0f} kWh @ 0.00 NOK/kWh")
    print(f"  → Average price achieved: {avg_price_ref:.3f} NOK/kWh")

    # With battery: better utilization
    pv_self_consumed_lp = total_pv - pv_export_lp - curtailment_lp
    revenue_lp = pv_self_consumed_lp * avg_import_price + pv_export_lp * avg_export_price
    avg_price_lp = revenue_lp / (total_pv - curtailment_lp) if (total_pv - curtailment_lp) > 0 else 0

    print(f"\nWITH BATTERY (20 kWh / 10 kW):")
    print(f"  Total PV production: {total_pv:,.0f} kWh")
    print(f"  Self-consumed: {pv_self_consumed_lp:,.0f} kWh @ ~{avg_import_price:.2f} NOK/kWh (avoided import)")
    print(f"  Exported: {pv_export_lp:,.0f} kWh @ ~{avg_export_price:.2f} NOK/kWh (spot + plusskunde)")
    print(f"  Curtailed (lost): {curtailment_lp:,.0f} kWh @ 0.00 NOK/kWh")
    print(f"  → Average price achieved: {avg_price_lp:.3f} NOK/kWh")

    print(f"\n  IMPROVEMENT: {(avg_price_lp - avg_price_ref):.3f} NOK/kWh (+{(avg_price_lp/avg_price_ref - 1)*100:.1f}%)")


def calculate_break_even(annual_savings, battery_capacity_kwh, lifetime_years=15, discount_rate=0.05):
    """Calculate break-even battery cost"""
    if annual_savings <= 0:
        return 0
    annuity_factor = (1 - (1 + discount_rate)**(-lifetime_years)) / discount_rate
    pv_savings = annual_savings * annuity_factor
    return pv_savings / battery_capacity_kwh


def main():
    """Main execution"""
    print("\n" + "="*70)
    print("YEARLY LP BATTERY OPTIMIZATION - REAL DATA")
    print("="*70)

    config = BatteryOptimizationConfig.from_yaml()

    # Battery configuration
    config.battery_capacity_kwh = 20.0  # Smaller battery
    config.battery_power_kw = 10.0      # Lower power rating

    print(f"\nSystem Configuration:")
    print(f"  Location: {config.location.name} ({config.location.latitude}°N, {config.location.longitude}°E)")
    print(f"  PV: {config.solar.pv_capacity_kwp} kWp")
    print(f"  Inverter: {config.solar.inverter_capacity_kw} kW")
    print(f"  Grid Limit: {config.solar.grid_export_limit_kw} kW")
    print(f"  Battery: {config.battery_capacity_kwh} kWh / {config.battery_power_kw} kW")
    print(f"  Annual Load: {config.consumption.annual_kwh:,.0f} kWh")

    # Load data
    data = load_real_yearly_data(config)

    # Run reference
    cost_ref, grid_import_ref, grid_export_ref, curtailment_ref = run_reference_case(data, config)

    # Run LP
    lp_results, cost_lp, monthly_results = run_yearly_lp_optimization(data, config)

    if lp_results is None:
        print("\n❌ Optimization failed!")
        return

    # Calculate savings
    annual_savings = cost_ref['total_cost_nok'] - cost_lp['total_cost_nok']

    print("\n" + "="*70)
    print("ECONOMIC ANALYSIS")
    print("="*70)
    print(f"\nAnnual Costs:")
    print(f"  Reference (no battery): {cost_ref['total_cost_nok']:,.0f} NOK")
    print(f"    Energy: {cost_ref['energy_cost_nok']:,.0f} NOK")
    print(f"    Peak: {cost_ref['peak_cost_nok']:,.0f} NOK")
    print(f"  LP with battery: {cost_lp['total_cost_nok']:,.0f} NOK")
    print(f"    Energy: {cost_lp['energy_cost_nok']:,.0f} NOK")
    print(f"    Peak: {cost_lp['peak_cost_nok']:,.0f} NOK")
    print(f"  Annual savings: {annual_savings:,.0f} NOK ({annual_savings/cost_ref['total_cost_nok']*100:.1f}%)")

    # Break-even
    breakeven_cost = calculate_break_even(annual_savings, config.battery_capacity_kwh)

    print("\n" + "="*70)
    print("BREAK-EVEN ANALYSIS")
    print("="*70)
    print(f"  Break-even cost: {breakeven_cost:,.0f} NOK/kWh")
    print(f"  Market cost: 5,000 NOK/kWh")
    print(f"  Gap: {5000 - breakeven_cost:,.0f} NOK/kWh ({(1-breakeven_cost/5000)*100:.1f}% reduction needed)")

    # Detailed revenue stream analysis
    analyze_revenue_streams(data, lp_results, cost_ref, cost_lp,
                            grid_import_ref, grid_export_ref, curtailment_ref)

    # Generate plots
    ref_results = {
        'grid_import': grid_import_ref,
        'grid_export': grid_export_ref,
        'curtailment': curtailment_ref
    }
    plot_comprehensive_results(data, ref_results, lp_results, config)

    print("\n" + "="*70)
    print("✅ SUCCESS - Analysis Complete!")
    print("="*70)
    print(f"  Annual savings: {annual_savings:,.0f} NOK")
    print(f"  Break-even cost: {breakeven_cost:,.0f} NOK/kWh")
    print(f"  Plots saved in results/")

    return {
        'config': config,
        'data': data,
        'cost_ref': cost_ref,
        'cost_lp': cost_lp,
        'lp_results': lp_results,
        'annual_savings': annual_savings,
        'breakeven_cost': breakeven_cost
    }


if __name__ == "__main__":
    results = main()
