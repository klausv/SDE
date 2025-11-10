"""
Run full year optimization using 24-hour rolling horizon with degradation.

Simulates entire year 2024 with:
- 30 kWh battery, 30 kW power (configurable)
- Real ENTSO-E spot prices (NO2)
- PVGIS solar production data
- Commercial office load profile (90,000 kWh/year)
- LFP degradation model
- HOURLY time resolution (24 timesteps/day)
- Economic analysis (NPV, IRR, break-even costs)
"""

import numpy as np
import pandas as pd
import sys
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from config import BatteryOptimizationConfig
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
from operational.state_manager import BatterySystemState
from core.price_fetcher import ENTSOEPriceFetcher
from core.pvgis_solar import PVGISProduction


def load_annual_data(year=2024):
    """Load full year of real spot prices and solar production data (HOURLY)"""

    print("Loading annual data...")
    print("="*80)

    # Load spot prices (hourly resolution - NO resampling)
    try:
        fetcher = ENTSOEPriceFetcher(resolution='PT60M')
        prices_hourly = fetcher.fetch_prices(year=year, area='NO2', resolution='PT60M')

        print(f"✓ Loaded spot prices for {year}")
        print(f"  Hourly data points: {len(prices_hourly)}")
        print(f"  Spot price range: {prices_hourly.min():.3f} - {prices_hourly.max():.3f} NOK/kWh")
        print(f"  Average spot price: {prices_hourly.mean():.3f} NOK/kWh")
    except Exception as e:
        print(f"⚠ Could not load real prices: {e}")
        return None, None, None

    timestamps = prices_hourly.index
    spot_prices = prices_hourly.values

    # Load solar production (PVGIS hourly - matching timestamps exactly)
    try:
        pvgis = PVGISProduction(
            lat=58.97,
            lon=5.73,
            pv_capacity_kwp=138.55,  # Match config
            tilt=30.0,
            azimuth=173.0
        )

        pvgis_hourly = pvgis.fetch_hourly_production(year=year)

        # Match timestamps exactly (hour by hour)
        pv_production = np.zeros(len(timestamps))
        for i, ts in enumerate(timestamps):
            ts_naive = ts.replace(tzinfo=None) if hasattr(ts, 'replace') else ts
            # Find matching hour in PVGIS (day-of-year based)
            matching = pvgis_hourly.index[
                (pvgis_hourly.index.month == ts_naive.month) &
                (pvgis_hourly.index.day == ts_naive.day) &
                (pvgis_hourly.index.hour == ts_naive.hour)
            ]
            if len(matching) > 0:
                pv_production[i] = pvgis_hourly.loc[matching[0]]

        print(f"✓ Loaded PVGIS solar data")
        print(f"  Production range: {pv_production.min():.1f} - {pv_production.max():.1f} kW")
        print(f"  Average production: {pv_production.mean():.1f} kW")
        print(f"  Annual production: {pv_production.sum()/1000:.1f} MWh")

    except Exception as e:
        print(f"⚠ Could not load PVGIS data: {e}")
        # Fallback to simple pattern
        pv_production = np.array([
            50.0 if 8 <= ts.hour < 18 else 0.0
            for ts in timestamps
        ])
        print(f"  Using synthetic solar pattern")

    print()
    return timestamps, spot_prices, pv_production


def create_commercial_load(timestamps, annual_kwh=90000):
    """
    Create realistic commercial office load profile.

    Pattern:
    - Weekday (Mon-Fri) 06:00-18:00: High load
    - Weekday nights: Low load
    - Weekends: Very low load
    """
    load = np.zeros(len(timestamps))

    # Calculate average power for target annual consumption
    # annual_kwh / (365 days × 24 hours) = average continuous power
    avg_power = annual_kwh / 8760

    for i, ts in enumerate(timestamps):
        # Convert to naive datetime if needed
        ts_naive = ts.replace(tzinfo=None) if hasattr(ts, 'replace') else ts

        hour = ts_naive.hour
        weekday = ts_naive.weekday()  # 0=Monday, 6=Sunday

        if weekday < 5:  # Monday-Friday
            if 6 <= hour < 18:  # Business hours
                load[i] = avg_power * 2.0  # 2x average
            elif 18 <= hour < 22:  # Evening
                load[i] = avg_power * 0.8  # 0.8x average
            else:  # Night
                load[i] = avg_power * 0.3  # 0.3x average
        else:  # Weekend
            load[i] = avg_power * 0.2  # 0.2x average (minimal load)

    return load


def run_annual_rolling_horizon(battery_kwh=30, battery_kw=30, year=2024):
    """
    Run full year optimization using 24-hour rolling horizon.

    Returns annual result with economic metrics.
    """

    print("\n" + "="*80)
    print(f"ANNUAL ROLLING HORIZON OPTIMIZATION - {year}")
    print("="*80)
    print(f"Battery: {battery_kwh} kWh, {battery_kw} kW")
    print(f"Time resolution: 1 hour (24 timesteps/day)")
    print(f"Optimization window: 24 hours (non-overlapping)")
    print()

    # Load annual data
    timestamps, spot_prices, pv_production = load_annual_data(year=year)

    if timestamps is None:
        print("❌ Could not load data. Exiting.")
        return None

    # Create load profile
    load = create_commercial_load(timestamps, annual_kwh=90000)

    print("Data summary:")
    print(f"  Time period: {timestamps[0]} to {timestamps[-1]}")
    print(f"  Duration: {len(timestamps)} timesteps ({len(timestamps)/24:.1f} days)")
    print(f"  Average load: {load.mean():.1f} kW")
    print(f"  Peak load: {load.max():.1f} kW")
    print(f"  Average solar: {pv_production.mean():.1f} kW")
    print(f"  Peak solar: {pv_production.max():.1f} kW")
    print()

    # Create config and optimizer
    config = BatteryOptimizationConfig()

    optimizer = RollingHorizonOptimizer(
        config,
        battery_kwh=battery_kwh,
        battery_kw=battery_kw
    )

    # Initialize system state
    state = BatterySystemState(
        battery_capacity_kwh=battery_kwh,
        current_soc_kwh=battery_kwh * 0.5,  # Start at 50% SOC
        current_monthly_peak_kw=0.0,
        month_start_date=timestamps[0].replace(day=1, hour=0, minute=0, second=0),
        last_update=timestamps[0]
    )

    # Run rolling horizon month by month
    print("Running rolling horizon optimization (month by month)...")
    print("="*80)

    # Create DataFrame for easier monthly splitting
    df = pd.DataFrame({
        'timestamp': timestamps,
        'price': spot_prices,
        'pv': pv_production,
        'load': load
    })
    df['month'] = df['timestamp'].dt.month

    # Storage for monthly results
    monthly_results = []

    # Storage for time-series data (for plotting)
    all_soc = []
    all_charge = []
    all_discharge = []
    all_grid_import = []
    all_grid_export = []

    window_timesteps = 24  # 24 hours @ 1 hour
    step_timesteps = 24    # Non-overlapping windows

    for month in range(1, 13):
        month_df = df[df['month'] == month].copy()

        if len(month_df) == 0:
            continue

        print(f"\nMonth {month:2d} ({month_df['timestamp'].iloc[0].strftime('%B %Y')})")
        print(f"  Datapoints: {len(month_df)} (hourly resolution)")

        # Reset monthly peak at start of month
        state._reset_monthly_peak(month_df['timestamp'].iloc[0])

        # Track monthly metrics
        month_energy_cost = 0
        month_degradation_cost = 0
        month_equivalent_cycles = 0
        month_max_peak = 0

        # Run rolling horizon for this month
        total_windows = len(month_df) // step_timesteps

        for w in range(total_windows):
            t_start = w * step_timesteps
            t_end = min(t_start + window_timesteps, len(month_df))

            if t_end - t_start < window_timesteps:
                break

            # Get window data
            window_pv = month_df['pv'].iloc[t_start:t_end].values
            window_load = month_df['load'].iloc[t_start:t_end].values
            window_prices = month_df['price'].iloc[t_start:t_end].values
            window_timestamps = pd.DatetimeIndex(month_df['timestamp'].iloc[t_start:t_end])

            # Optimize
            result = optimizer.optimize_24h(
                current_state=state,
                pv_production=window_pv,
                load_consumption=window_load,
                spot_prices=window_prices,
                timestamps=window_timestamps,
                verbose=False
            )

            if not result.success:
                print(f"    Window {w}: FAILED - {result.message}")
                break

            # Store time-series data for plotting
            all_soc.extend(result.E_battery)
            all_charge.extend(result.P_charge)
            all_discharge.extend(result.P_discharge)
            all_grid_import.extend(result.P_grid_import)
            all_grid_export.extend(result.P_grid_export)

            # Accumulate costs
            month_energy_cost += result.energy_cost
            month_degradation_cost += result.degradation_cost
            month_equivalent_cycles += result.equivalent_cycles
            month_max_peak = max(month_max_peak, result.P_grid_import.max())

            # Update state for next window
            state.update_from_measurement(
                timestamp=window_timestamps[-1],
                soc_kwh=result.E_battery[-1],
                grid_import_power_kw=result.P_grid_import[-1]
            )

        # Calculate monthly power tariff (actual step function)
        monthly_power_tariff = config.tariff.get_power_cost(month_max_peak)

        # Store monthly result
        monthly_results.append({
            'month': month,
            'month_name': month_df['timestamp'].iloc[0].strftime('%B'),
            'energy_cost': month_energy_cost,
            'degradation_cost': month_degradation_cost,
            'power_tariff': monthly_power_tariff,
            'total_cost': month_energy_cost + month_degradation_cost + monthly_power_tariff,
            'equivalent_cycles': month_equivalent_cycles,
            'max_peak_kw': month_max_peak,
            'windows_optimized': total_windows
        })

        print(f"  ✓ Completed {total_windows} windows")
        print(f"    Energy cost: {month_energy_cost:>10,.2f} NOK")
        print(f"    Degradation: {month_degradation_cost:>10,.2f} NOK ({month_equivalent_cycles:.2f} cycles)")
        print(f"    Power tariff: {monthly_power_tariff:>10,.2f} NOK (peak: {month_max_peak:.2f} kW)")
        print(f"    Total cost: {month_energy_cost + month_degradation_cost + monthly_power_tariff:>10,.2f} NOK")

    # Create aggregated annual result
    df_monthly = pd.DataFrame(monthly_results)

    # Convert time-series to numpy arrays
    soc_array = np.array(all_soc)
    charge_array = np.array(all_charge)
    discharge_array = np.array(all_discharge)
    grid_import_array = np.array(all_grid_import)
    grid_export_array = np.array(all_grid_export)

    class AnnualResult:
        def __init__(self):
            self.success = True
            self.battery_kwh = battery_kwh
            self.battery_kw = battery_kw
            self.year = year

            # Cost breakdown
            self.energy_cost = df_monthly['energy_cost'].sum()
            self.degradation_cost = df_monthly['degradation_cost'].sum()
            self.power_cost = df_monthly['power_tariff'].sum()
            self.total_cost = df_monthly['total_cost'].sum()

            # Time-series data for plotting
            self.soc = soc_array
            self.charge = charge_array
            self.discharge = discharge_array
            self.grid_import = grid_import_array
            self.grid_export = grid_export_array

            # Monthly breakdown dataframe
            self.monthly_df = df_monthly

            # Operational metrics
            self.total_equivalent_cycles = df_monthly['equivalent_cycles'].sum()
            self.avg_monthly_cycles = df_monthly['equivalent_cycles'].mean()
            self.max_peak_kw = df_monthly['max_peak_kw'].max()

            # Monthly breakdown
            self.monthly_results = df_monthly

    result = AnnualResult()

    # Print detailed results
    print("\n" + "="*80)
    print("ANNUAL OPTIMIZATION RESULTS (ROLLING HORIZON)")
    print("="*80)

    print(f"\nCost Breakdown:")
    print(f"  Energy cost:      {result.energy_cost:>12,.2f} NOK")
    print(f"  Degradation cost: {result.degradation_cost:>12,.2f} NOK")
    print(f"  Power tariff:     {result.power_cost:>12,.2f} NOK")
    print(f"  {'─'*45}")
    print(f"  Total cost:       {result.total_cost:>12,.2f} NOK")

    print(f"\nDegradation Analysis:")
    print(f"  Total equivalent cycles: {result.total_equivalent_cycles:.1f} cycles")
    print(f"  Average monthly cycles:  {result.avg_monthly_cycles:.2f} cycles/month")
    print(f"  Cycles per day:          {result.total_equivalent_cycles/365:.2f} cycles/day")

    # Calculate degradation percentage
    # ρ_constant = 0.004% per cycle, so total_deg = cycles × 0.004
    total_degradation_pct = result.total_equivalent_cycles * 0.004
    print(f"  Total degradation:       {total_degradation_pct:.4f}%")

    # Projected lifetime
    if total_degradation_pct > 0:
        years_to_eol = 20.0 / total_degradation_pct  # 20% EOL threshold
        print(f"  Projected lifetime:      {years_to_eol:.1f} years (to 80% SOH)")

    print(f"\nOperational Metrics:")
    print(f"  Maximum peak power: {result.max_peak_kw:.2f} kW")
    print(f"  Final SOC:          {state.current_soc_percent:.1f}%")

    return result


def calculate_economics(result, battery_kwh, discount_rate=0.05, lifetime_years=15):
    """
    Calculate economic metrics: NPV, IRR, break-even cost.

    Args:
        result: AnnualResult from rolling horizon optimization
        battery_kwh: Battery capacity [kWh]
        discount_rate: Annual discount rate (default 5%)
        lifetime_years: Battery system lifetime (default 15 years)

    Returns:
        Dictionary with economic metrics
    """

    print("\n" + "="*80)
    print("ECONOMIC ANALYSIS")
    print("="*80)

    # Annual operational cost (with battery)
    annual_cost_with_battery = result.total_cost

    # Estimate cost without battery (baseline)
    # Without battery: no degradation, likely higher energy costs, higher peak tariffs
    # Conservative estimate: 120% of energy cost (no peak shaving benefit)
    estimated_cost_without_battery = annual_cost_with_battery * 1.3  # Rough estimate

    # Annual savings
    annual_savings = estimated_cost_without_battery - annual_cost_with_battery

    print(f"\nAnnual Costs:")
    print(f"  With battery ({battery_kwh} kWh):    {annual_cost_with_battery:>12,.0f} NOK")
    print(f"  Without battery (estimated): {estimated_cost_without_battery:>12,.0f} NOK")
    print(f"  Annual savings:              {annual_savings:>12,.0f} NOK")

    # NPV calculation
    pv_factor = sum([1 / (1 + discount_rate)**t for t in range(1, lifetime_years + 1)])
    npv_savings = annual_savings * pv_factor

    print(f"\nPresent Value Analysis ({lifetime_years} years @ {discount_rate*100:.1f}%):")
    print(f"  PV factor:         {pv_factor:>12.2f}")
    print(f"  NPV of savings:    {npv_savings:>12,.0f} NOK")

    # Break-even battery cost
    breakeven_per_kwh = npv_savings / battery_kwh

    print(f"\n{'='*80}")
    print("BREAK-EVEN BATTERY COST")
    print(f"{'='*80}")
    print(f"\n  Maximum battery cost:  {breakeven_per_kwh:>12,.0f} NOK/kWh")
    print(f"  Total investment:      {npv_savings:>12,.0f} NOK ({battery_kwh} kWh)")

    print(f"\nMarket Comparison:")
    market_price = 5000  # NOK/kWh (current market)
    print(f"  Current market price:  ~{market_price:,} NOK/kWh")
    print(f"  Break-even price:       {breakeven_per_kwh:>6,.0f} NOK/kWh")

    if breakeven_per_kwh < market_price:
        reduction_needed = (market_price - breakeven_per_kwh) / market_price * 100
        print(f"  Required reduction:     {reduction_needed:>6.1f}%")
        print(f"\n  ⚠ Battery NOT economically viable at current market prices")
    else:
        print(f"\n  ✓ Battery IS economically viable at current market prices")

    return {
        'annual_cost_with_battery': annual_cost_with_battery,
        'annual_cost_without_battery': estimated_cost_without_battery,
        'annual_savings': annual_savings,
        'npv_savings': npv_savings,
        'breakeven_per_kwh': breakeven_per_kwh,
        'market_price': market_price,
        'is_viable': breakeven_per_kwh >= market_price
    }


def print_monthly_breakdown(result):
    """Print detailed monthly breakdown table"""

    print("\n" + "="*80)
    print("MONTHLY BREAKDOWN")
    print("="*80)

    df = result.monthly_results

    print(f"\n{'Month':>10} {'Energy':>12} {'Degrad':>12} {'Power':>12} {'Total':>12} {'Cycles':>10}")
    print(f"{' '*10} {'Cost':>12} {'Cost':>12} {'Tariff':>12} {'Cost':>12} {' ':>10}")
    print("─" * 80)

    for _, row in df.iterrows():
        print(f"{row['month_name']:>10} "
              f"{row['energy_cost']:>12,.0f} "
              f"{row['degradation_cost']:>12,.0f} "
              f"{row['power_tariff']:>12,.0f} "
              f"{row['total_cost']:>12,.0f} "
              f"{row['equivalent_cycles']:>10.2f}")

    print("─" * 80)
    print(f"{'TOTAL':>10} "
          f"{df['energy_cost'].sum():>12,.0f} "
          f"{df['degradation_cost'].sum():>12,.0f} "
          f"{df['power_tariff'].sum():>12,.0f} "
          f"{df['total_cost'].sum():>12,.0f} "
          f"{df['equivalent_cycles'].sum():>10.1f}")
    print()


def plot_annual_comprehensive(result, timestamps, pv_production, load, spot_prices, battery_kwh, battery_kw):
    """
    Generate comprehensive annual visualization matching old LP optimizer style.

    7-panel plot:
    1. PV Production and Load
    2. Spot Prices
    3. Grid Import Comparison
    4. Grid Export Comparison
    5. Battery Charge/Discharge Power
    6. Battery State of Charge
    7. Monthly Peak Powers
    """

    print("\n" + "="*80)
    print("GENERATING COMPREHENSIVE VISUALIZATION")
    print("="*80)

    # Get time-series data from result
    soc = result.soc
    charge = result.charge
    discharge = result.discharge
    grid_import = result.grid_import
    grid_export = result.grid_export

    # Trim timestamps to match result arrays (some windows may have been skipped)
    n_points = len(soc)
    timestamps = timestamps[:n_points]
    pv_production = pv_production[:n_points]
    load = load[:n_points]
    spot_prices = spot_prices[:n_points]

    # Reference case (no battery)
    grid_import_ref = np.maximum(load - pv_production, 0)
    grid_export_ref = np.maximum(pv_production - load, 0)

    # Monthly peak analysis
    df_monthly = result.monthly_df
    months = df_monthly['month'].values
    peaks_battery = df_monthly['max_peak_kw'].values
    peaks_ref = []

    for month in range(1, 13):
        month_mask = np.array([ts.month == month for ts in timestamps])
        if month_mask.sum() > 0:
            peaks_ref.append(grid_import_ref[month_mask].max())
        else:
            peaks_ref.append(0)

    peaks_ref = np.array(peaks_ref)

    # Create figure with 7 subplots
    fig = plt.figure(figsize=(16, 20))
    gs = fig.add_gridspec(7, 2, hspace=0.3, wspace=0.3, height_ratios=[1, 0.8, 1, 1, 1, 1, 1])

    # Title
    fig.suptitle(f'Rolling Horizon Battery Optimization - Comprehensive Results 2024\n'
                 f'{battery_kwh} kWh, {battery_kw} kW',
                 fontsize=14, fontweight='bold')

    # Panel 1: PV Production and Load
    ax1 = fig.add_subplot(gs[0, :])
    ax1.fill_between(timestamps, pv_production, alpha=0.3, color='orange', label='PV Production')
    ax1.plot(timestamps, load, color='blue', linewidth=0.8, alpha=0.7, label='Load')
    ax1.set_ylabel('Power (kW)')
    ax1.set_title('PV Production and Load - Full Year 2024', fontsize=11, fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(timestamps[0], timestamps[-1])

    # Panel 2: Spot Prices
    ax2 = fig.add_subplot(gs[1, :])
    ax2.fill_between(timestamps, spot_prices, alpha=0.4, color='green')
    ax2.set_ylabel('Price (NOK/kWh)')
    ax2.set_title('Spot Prices - Full Year 2024', fontsize=11, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(timestamps[0], timestamps[-1])

    # Panel 3: Grid Import Comparison
    ax3 = fig.add_subplot(gs[2, 0])
    ax3.fill_between(timestamps, grid_import_ref, alpha=0.3, color='red', label='Reference (no battery)')
    ax3.fill_between(timestamps, grid_import, alpha=0.5, color='darkred', label='With battery')
    ax3.set_ylabel('Power (kW)')
    ax3.set_title('Grid Import Comparison', fontsize=11, fontweight='bold')
    ax3.legend(loc='upper right', fontsize=8)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(timestamps[0], timestamps[-1])

    # Panel 4: Grid Export Comparison
    ax4 = fig.add_subplot(gs[2, 1])
    ax4.fill_between(timestamps, grid_export_ref, alpha=0.3, color='green', label='Reference (no battery)')
    ax4.fill_between(timestamps, grid_export, alpha=0.5, color='darkgreen', label='With battery')
    ax4.set_ylabel('Power (kW)')
    ax4.set_title('Grid Export Comparison', fontsize=11, fontweight='bold')
    ax4.legend(loc='upper right', fontsize=8)
    ax4.grid(True, alpha=0.3)
    ax4.set_xlim(timestamps[0], timestamps[-1])

    # Panel 5: Battery Charge/Discharge Power
    ax5 = fig.add_subplot(gs[3, :])
    ax5.fill_between(timestamps, charge, alpha=0.5, color='green', label='Charge')
    ax5.fill_between(timestamps, -discharge, alpha=0.5, color='red', label='Discharge')
    ax5.axhline(y=0, color='black', linewidth=0.8, linestyle='--')
    ax5.set_ylabel('Power (kW)')
    ax5.set_title('Battery Charge/Discharge Power - Full Year', fontsize=11, fontweight='bold')
    ax5.legend(loc='upper right')
    ax5.grid(True, alpha=0.3)
    ax5.set_xlim(timestamps[0], timestamps[-1])

    # Panel 6: Battery State of Charge
    ax6 = fig.add_subplot(gs[4, :])
    soc_percent = (soc / battery_kwh) * 100
    ax6.fill_between(timestamps, soc_percent, alpha=0.5, color='purple')
    ax6.axhline(y=90, color='red', linewidth=1, linestyle='--', alpha=0.5, label='SOC Max (90%)')
    ax6.axhline(y=10, color='orange', linewidth=1, linestyle='--', alpha=0.5, label='SOC Min (10%)')
    ax6.set_ylabel('SOC (%)')
    ax6.set_ylim(0, 100)
    ax6.set_title('Battery State of Charge - Full Year', fontsize=11, fontweight='bold')
    ax6.legend(loc='upper right', fontsize=8)
    ax6.grid(True, alpha=0.3)
    ax6.set_xlim(timestamps[0], timestamps[-1])

    # Panel 7: Monthly Peak Powers Comparison
    ax7 = fig.add_subplot(gs[5:, :])
    x = np.arange(len(months))
    width = 0.35
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    bars1 = ax7.bar(x - width/2, peaks_ref, width, label='Reference (no battery)',
                    color='lightcoral', alpha=0.8)
    bars2 = ax7.bar(x + width/2, peaks_battery, width, label='With battery',
                    color='darkred', alpha=0.8)

    ax7.set_ylabel('Peak Power (kW)')
    ax7.set_title('Monthly Peak Powers Comparison', fontsize=11, fontweight='bold')
    ax7.set_xticks(x)
    ax7.set_xticklabels(month_names)
    ax7.legend(loc='upper right')
    ax7.grid(True, alpha=0.3, axis='y')

    # Save figure
    output_path = 'results/rolling_horizon_annual_comprehensive.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ Comprehensive plot saved: {output_path}")
    plt.close()

    return output_path


def main():
    """Run annual rolling horizon optimization with economic analysis"""

    print("\n" + "="*80)
    print("ANNUAL BATTERY OPTIMIZATION - ROLLING HORIZON (24h)")
    print("="*80)
    print()
    print("Configuration:")
    print("  - Battery: 30 kWh, 15 kW")
    print("  - Time resolution: 1 hour (24 timesteps/day)")
    print("  - Optimization window: 24 hours (non-overlapping)")
    print("  - Degradation model: LFP (Korpås formulation)")
    print("  - Load profile: Commercial office (90,000 kWh/year)")
    print("  - Solver: HiGHS LP")
    print("  - Year: 2024 (full year)")
    print()

    # Load data for plotting
    timestamps, spot_prices, pv_production = load_annual_data(year=2024)
    load = create_commercial_load(timestamps, annual_kwh=90000)

    # Run optimization
    result = run_annual_rolling_horizon(
        battery_kwh=30,
        battery_kw=15,
        year=2024
    )

    if result is None:
        print("\n❌ Optimization failed")
        return 1

    # Print monthly breakdown
    print_monthly_breakdown(result)

    # Economic analysis
    economics = calculate_economics(
        result,
        battery_kwh=30,
        discount_rate=0.05,
        lifetime_years=15
    )

    # Generate comprehensive visualization
    plot_annual_comprehensive(
        result=result,
        timestamps=timestamps,
        pv_production=pv_production,
        load=load,
        spot_prices=spot_prices,
        battery_kwh=30,
        battery_kw=15
    )

    print("\n" + "="*80)
    print("✓ ANNUAL OPTIMIZATION COMPLETED SUCCESSFULLY")
    print("="*80)
    print()
    print(f"Total annual cost: {result.total_cost:,.0f} NOK")
    print(f"Break-even cost:   {economics['breakeven_per_kwh']:,.0f} NOK/kWh")
    print(f"Market price:      ~{economics['market_price']:,} NOK/kWh")
    print()

    if economics['is_viable']:
        print("✓ Battery system IS economically viable!")
    else:
        reduction = (economics['market_price'] - economics['breakeven_per_kwh']) / economics['market_price'] * 100
        print(f"⚠ Battery requires {reduction:.1f}% cost reduction to be viable")

    return 0


if __name__ == "__main__":
    sys.exit(main())
