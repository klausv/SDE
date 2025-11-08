"""
Visualize battery management with realistic LFP degradation model.

Creates comprehensive plots showing:
- Battery SOC and charge/discharge behavior
- Spot prices and solar production
- Degradation accumulation over time
- Economic performance metrics
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for WSL
import matplotlib.pyplot as plt
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from config import BatteryOptimizationConfig, DegradationConfig
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.price_fetcher import ENTSOEPriceFetcher
from core.pvgis_solar import PVGISProduction


def load_real_data(month=1, year=2024):
    """Load real spot prices and solar production data"""

    # Load spot prices
    fetcher = ENTSOEPriceFetcher(resolution='PT60M')
    prices_series = fetcher.fetch_prices(year=year, area='NO2', resolution='PT60M')
    prices_df = prices_series.to_frame('price_nok_per_kwh')

    # Filter for specific month
    prices_df['month'] = prices_df.index.month
    month_data = prices_df[prices_df['month'] == month].copy()

    timestamps = month_data.index
    spot_prices = month_data['price_nok_per_kwh'].values

    # Load solar production
    pvgis = PVGISProduction(
        lat=58.97,
        lon=5.73,
        pv_capacity_kwp=138.55,
        tilt=30.0,
        azimuth=173.0
    )

    pvgis_series = pvgis.fetch_hourly_production(year=year)
    pvgis_data = pvgis_series.to_frame('production_kw')
    pvgis_data.rename(columns={'production_kw': 'pv_power_kw'}, inplace=True)

    # Extract month data
    pvgis_data['month'] = pvgis_data.index.month
    solar_month = pvgis_data[pvgis_data['month'] == month].copy()

    # Match timestamps
    pv_production = np.zeros(len(timestamps))
    for i, ts in enumerate(timestamps):
        matching = solar_month[
            (solar_month.index.month == ts.month) &
            (solar_month.index.day == ts.day) &
            (solar_month.index.hour == ts.hour)
        ]
        if len(matching) > 0:
            pv_production[i] = matching['pv_power_kw'].values[0]

    return timestamps, spot_prices, pv_production


def create_synthetic_load(timestamps, annual_kwh=300000):
    """Create realistic commercial load profile"""
    hours_per_year = 8760
    avg_load = annual_kwh / hours_per_year

    load = np.zeros(len(timestamps))
    for i, ts in enumerate(timestamps):
        base = avg_load * 0.6

        if ts.weekday() < 5 and 6 <= ts.hour < 18:
            load[i] = base * 1.8
        elif 18 <= ts.hour < 22:
            load[i] = base * 1.3
        else:
            load[i] = base

    return load


def run_and_visualize(battery_kwh=100, battery_kw=50, month=1, year=2024):
    """Run optimization and create comprehensive visualizations"""

    print(f"\n{'='*70}")
    print(f"BATTERY MANAGEMENT VISUALIZATION - Month {month}/{year}")
    print(f"{'='*70}")
    print(f"Battery: {battery_kwh} kWh, {battery_kw} kW")
    print()

    # Create config with degradation
    config = BatteryOptimizationConfig()
    config.battery.degradation = DegradationConfig(
        enabled=True,
        cycle_life_full_dod=5000,
        calendar_life_years=28.0
    )

    # Load data
    timestamps, spot_prices, pv_production = load_real_data(month=month, year=year)
    load = create_synthetic_load(timestamps, annual_kwh=300000)

    # Run optimization
    optimizer = MonthlyLPOptimizer(
        config,
        resolution='PT60M',
        battery_kwh=battery_kwh,
        battery_kw=battery_kw
    )

    result = optimizer.optimize_month(
        month_idx=month,
        pv_production=pv_production,
        load_consumption=load,
        spot_prices=spot_prices,
        timestamps=timestamps,
        E_initial=battery_kwh * 0.5
    )

    if not result.success:
        print(f"❌ Optimization failed: {result.message}")
        return None

    # Create visualizations
    fig = plt.figure(figsize=(16, 12))

    # 1. Battery SOC and charge/discharge power
    ax1 = plt.subplot(4, 1, 1)
    ax1_twin = ax1.twinx()

    # SOC
    soc_pct = (result.E_battery / battery_kwh) * 100
    ax1.plot(timestamps, soc_pct, 'b-', linewidth=2, label='Battery SOC')
    ax1.axhline(y=20, color='r', linestyle='--', alpha=0.5, label='Min SOC (20%)')
    ax1.axhline(y=80, color='g', linestyle='--', alpha=0.5, label='Max SOC (80%)')
    ax1.set_ylabel('State of Charge (%)', fontsize=12, color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.set_ylim([0, 100])
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')

    # Charge/discharge power
    net_power = result.P_charge - result.P_discharge
    colors = ['green' if p > 0 else 'red' for p in net_power]
    ax1_twin.bar(timestamps, net_power, color=colors, alpha=0.3, width=1/24)
    ax1_twin.set_ylabel('Battery Power (kW)\nGreen=Charge, Red=Discharge', fontsize=12)
    ax1_twin.set_ylim([-battery_kw, battery_kw])

    ax1.set_title(f'Battery Management - {battery_kwh} kWh / {battery_kw} kW (Month {month}/{year})',
                  fontsize=14, fontweight='bold')

    # 2. Spot prices
    ax2 = plt.subplot(4, 1, 2, sharex=ax1)
    ax2.fill_between(timestamps, spot_prices, alpha=0.4, color='orange', label='Spot Price')
    ax2.plot(timestamps, spot_prices, 'orange', linewidth=1.5)
    ax2.set_ylabel('Spot Price (NOK/kWh)', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right')
    ax2.set_title('Electricity Spot Prices (NO2)', fontsize=12, fontweight='bold')

    # 3. Solar production and load
    ax3 = plt.subplot(4, 1, 3, sharex=ax1)
    ax3.fill_between(timestamps, pv_production, alpha=0.3, color='gold', label='PV Production')
    ax3.plot(timestamps, pv_production, 'gold', linewidth=1.5)
    ax3.plot(timestamps, load, 'navy', linewidth=1.5, label='Load Consumption')
    ax3.set_ylabel('Power (kW)', fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc='upper right')
    ax3.set_title('Solar Production and Load Profile', fontsize=12, fontweight='bold')

    # 4. Degradation accumulation
    ax4 = plt.subplot(4, 1, 4, sharex=ax1)

    if result.DP_total is not None:
        cumulative_deg = np.cumsum(result.DP_total)
        cyclic_cum = np.cumsum(result.DP_cyc)
        calendar_cum = result.DP_cal * np.arange(1, len(timestamps) + 1)

        ax4.plot(timestamps, cumulative_deg, 'r-', linewidth=2, label='Total Degradation')
        ax4.plot(timestamps, cyclic_cum, 'orange', linewidth=1.5, linestyle='--',
                label='Cyclic Degradation')
        ax4.plot(timestamps, calendar_cum, 'gray', linewidth=1.5, linestyle=':',
                label='Calendar Degradation')

        ax4.set_ylabel('Cumulative Degradation (%)', fontsize=12)
        ax4.grid(True, alpha=0.3)
        ax4.legend(loc='upper left')
        ax4.set_title('Battery Degradation Accumulation (LFP Model)', fontsize=12, fontweight='bold')

    ax4.set_xlabel('Date', fontsize=12)

    plt.tight_layout()

    # Save figure
    output_file = Path(__file__).parent / 'results' / 'figures' / f'battery_management_month{month}.png'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved visualization: {output_file}")

    # Create summary metrics figure
    fig2, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Cost breakdown - handle negative energy cost (from exports)
    ax_cost = axes[0, 0]

    if result.energy_cost < 0:
        # Revenue from exports - show as separate bar chart
        ax_cost.axis('off')
        costs_text = f"""
        COST/REVENUE BREAKDOWN
        {'─'*30}

        Energy Revenue:  {-result.energy_cost:>8,.0f} NOK
        Power Tariff:    {result.power_cost:>8,.0f} NOK
        Degradation:     {result.degradation_cost:>8,.0f} NOK
        {'─'*30}
        Net Cost:        {result.objective_value:>8,.0f} NOK

        (Positive solar exports
         exceed grid imports)
        """
        ax_cost.text(0.5, 0.5, costs_text, fontsize=10, family='monospace',
                    verticalalignment='center', horizontalalignment='center',
                    transform=ax_cost.transAxes)
    else:
        # Normal positive costs - show pie chart
        costs = [result.energy_cost, result.power_cost, result.degradation_cost]
        labels = ['Energy Cost', 'Power Tariff', 'Degradation Cost']
        colors_pie = ['#ff9999', '#66b3ff', '#99ff99']
        ax_cost.pie(costs, labels=labels, autopct='%1.1f%%', colors=colors_pie, startangle=90)
        ax_cost.set_title('Cost Breakdown', fontsize=12, fontweight='bold')

    # Battery utilization
    ax_util = axes[0, 1]
    charge_hours = np.sum(result.P_charge > 0)
    discharge_hours = np.sum(result.P_discharge > 0)
    idle_hours = len(timestamps) - charge_hours - discharge_hours

    utilization = [charge_hours, discharge_hours, idle_hours]
    labels_util = ['Charging', 'Discharging', 'Idle']
    colors_util = ['green', 'red', 'gray']
    ax_util.pie(utilization, labels=labels_util, autopct='%1.1f%%', colors=colors_util, startangle=90)
    ax_util.set_title('Battery Operational Time', fontsize=12, fontweight='bold')

    # Degradation breakdown
    ax_deg = axes[1, 0]
    total_deg = np.sum(result.DP_total) if result.DP_total is not None else 0
    cyclic_deg = np.sum(result.DP_cyc) if result.DP_cyc is not None else 0
    calendar_deg = result.DP_cal * len(timestamps) if result.DP_cal is not None else 0

    deg_data = [cyclic_deg, calendar_deg]
    labels_deg = ['Cyclic', 'Calendar']
    colors_deg = ['orange', 'gray']
    ax_deg.bar(labels_deg, deg_data, color=colors_deg, alpha=0.7)
    ax_deg.set_ylabel('Degradation (%)', fontsize=12)
    ax_deg.set_title('Degradation Sources', fontsize=12, fontweight='bold')
    ax_deg.grid(True, alpha=0.3, axis='y')

    # Key metrics table
    ax_metrics = axes[1, 1]
    ax_metrics.axis('off')

    equiv_cycles = cyclic_deg / (20.0 / 5000) if cyclic_deg > 0 else 0
    annual_cycles = equiv_cycles * (365 / (len(timestamps) / 24))

    metrics_text = f"""
    PERFORMANCE METRICS
    {'─'*35}

    Energy Economics:
      Energy Cost:        {result.energy_cost:>8,.0f} NOK
      Power Tariff:       {result.power_cost:>8,.0f} NOK
      Degradation Cost:   {result.degradation_cost:>8,.0f} NOK
      Total Cost:         {result.objective_value:>8,.0f} NOK

    Battery Performance:
      Total Degradation:  {total_deg:>8.3f} %
      Equiv. Cycles:      {equiv_cycles:>8.1f} cycles
      Projected Annual:   {annual_cycles:>8.0f} cycles/year
      Avg Charge Power:   {np.mean(result.P_charge[result.P_charge > 0]):>8.1f} kW
      Avg Discharge Pwr:  {np.mean(result.P_discharge[result.P_discharge > 0]):>8.1f} kW

    System Operations:
      Peak Power:         {result.P_peak:>8.1f} kW
      Final SOC:          {result.E_battery_final/battery_kwh*100:>8.1f} %
      Hours Charging:     {charge_hours:>8.0f} hrs
      Hours Discharging:  {discharge_hours:>8.0f} hrs
    """

    ax_metrics.text(0.1, 0.5, metrics_text, fontsize=10, family='monospace',
                   verticalalignment='center', transform=ax_metrics.transAxes)

    plt.tight_layout()

    # Save metrics figure
    output_file2 = Path(__file__).parent / 'results' / 'figures' / f'battery_metrics_month{month}.png'
    plt.savefig(output_file2, dpi=300, bbox_inches='tight')
    print(f"✓ Saved metrics: {output_file2}")
    plt.close('all')

    return result


def main():
    """Generate battery management visualizations"""

    print("\n" + "="*70)
    print("BATTERY MANAGEMENT VISUALIZATION WITH LFP DEGRADATION")
    print("="*70)
    print()

    # Run for January 2024
    result = run_and_visualize(
        battery_kwh=100,
        battery_kw=50,
        month=1,
        year=2024
    )

    if result is None:
        print("\n❌ Visualization failed")
        return 1

    print("\n" + "="*70)
    print("✓ VISUALIZATION COMPLETED")
    print("="*70)
    print("\nCheck 'results/figures/' directory for output files:")
    print("  - battery_management_month1.png")
    print("  - battery_metrics_month1.png")

    return 0


if __name__ == "__main__":
    sys.exit(main())
