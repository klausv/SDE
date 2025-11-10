"""
Fast battery sizing optimization using 2h temporal aggregation.

Tests multiple battery configurations (kWh, kW) to find optimal size
based on break-even cost analysis.

Uses 2h aggregation for 4x speedup with <2% error.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple

from config import config
from core.price_fetcher import fetch_prices
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.representative_periods import TemporalAggregator


class FastBatterySizingOptimizer:
    """
    Optimize battery sizing using 2h temporal aggregation.

    Strategy:
    1. Load full year data (8760 hours)
    2. Aggregate to 2h blocks (4380 timesteps)
    3. Run LP for reference (no battery)
    4. Test multiple battery configurations
    5. Calculate break-even cost for each
    """

    def __init__(self, year: int = 2025, aggregation_hours: int = 2):
        """
        Initialize battery sizing optimizer.

        Args:
            year: Year for data
            aggregation_hours: Temporal aggregation (default: 2h)
        """
        self.year = year
        self.agg_hours = aggregation_hours
        self.aggregator = TemporalAggregator(aggregation_hours)

        # Load and prepare data
        self._load_data()

    def _load_data(self):
        """Load full year data and aggregate."""
        print("Loading full year data...")

        # Fetch spot prices
        spot_prices = fetch_prices(self.year, 'NO2', resolution='PT60M')
        timestamps = spot_prices.index

        # Generate PV production
        pv = []
        for ts in timestamps:
            hour = ts.hour
            day_of_year = ts.dayofyear

            season_factor = 0.3 + 0.7 * np.sin((day_of_year - 80) * 2 * np.pi / 365)

            if 6 <= hour <= 20:
                hour_factor = np.sin((hour - 6) * np.pi / 14)
                pv_kw = config.solar.pv_capacity_kwp * season_factor * hour_factor * 0.8
            else:
                pv_kw = 0

            pv.append(pv_kw)

        pv = np.array(pv)

        # Generate consumption
        load = []
        for ts in timestamps:
            hour = ts.hour
            is_weekday = ts.weekday() < 5
            day_of_year = ts.dayofyear

            season_factor = 1.2 - 0.4 * np.sin((day_of_year - 80) * 2 * np.pi / 365)

            if is_weekday:
                if 7 <= hour <= 16:
                    base_load = 25 * season_factor
                elif 17 <= hour <= 22:
                    base_load = 18 * season_factor
                else:
                    base_load = 12 * season_factor
            else:
                base_load = 12 * season_factor

            load.append(base_load * (0.95 + 0.1 * np.random.random()))

        load = np.array(load)

        self.timestamps_full = timestamps
        self.pv_full = pv
        self.load_full = load
        self.spot_full = spot_prices.values

        print(f"✓ Loaded {len(timestamps)} hours")
        print(f"  PV total: {pv.sum()/1000:.1f} MWh")
        print(f"  Load total: {load.sum()/1000:.1f} MWh")
        print()

    def _optimize_monthly(
        self,
        battery_kwh: float,
        battery_kw: float,
        use_aggregation: bool = True
    ) -> Dict:
        """
        Run monthly LP optimization for full year.

        Args:
            battery_kwh: Battery capacity (0 for reference)
            battery_kw: Battery power rating (0 for reference)
            use_aggregation: Use 2h aggregation if True

        Returns:
            Results dict with annual costs
        """
        optimizer = MonthlyLPOptimizer(
            config,
            resolution='PT60M',
            battery_kwh=battery_kwh,
            battery_kw=battery_kw
        )

        if use_aggregation:
            optimizer.timestep_hours = self.agg_hours

        monthly_results = []

        for month in range(1, 13):
            # Extract month data
            month_mask = self.timestamps_full.month == month
            month_timestamps = self.timestamps_full[month_mask]
            month_pv = self.pv_full[month_mask]
            month_load = self.load_full[month_mask]
            month_spot = self.spot_full[month_mask]

            # Aggregate if requested
            if use_aggregation:
                month_timestamps, month_pv, month_load, month_spot = self.aggregator.aggregate(
                    month_timestamps, month_pv, month_load, month_spot
                )

            # Run LP
            E_initial = battery_kwh * 0.5 if battery_kwh > 0 else 0
            result = optimizer.optimize_month(
                month_idx=month,
                pv_production=month_pv,
                load_consumption=month_load,
                spot_prices=month_spot,
                timestamps=month_timestamps,
                E_initial=E_initial
            )

            monthly_results.append(result)

        # Aggregate annual
        annual_energy_cost = sum([r.energy_cost for r in monthly_results])
        annual_power_cost = sum([r.power_cost for r in monthly_results])
        annual_total = annual_energy_cost + annual_power_cost

        return {
            'annual_energy_cost': annual_energy_cost,
            'annual_power_cost': annual_power_cost,
            'annual_total_cost': annual_total,
            'monthly_results': monthly_results
        }

    def calculate_reference(self, use_aggregation: bool = True) -> Dict:
        """
        Calculate reference scenario (no battery).

        Args:
            use_aggregation: Use 2h aggregation

        Returns:
            Reference results
        """
        print("Calculating reference (no battery)...")
        start = time.time()

        result = self._optimize_monthly(0, 0, use_aggregation)

        elapsed = time.time() - start

        print(f"✓ Reference calculated in {elapsed:.1f}s")
        print(f"  Annual total: {result['annual_total_cost']:,.0f} kr")
        print()

        result['elapsed_time'] = elapsed
        return result

    def optimize_battery_config(
        self,
        battery_kwh: float,
        battery_kw: float,
        reference_result: Dict,
        use_aggregation: bool = True
    ) -> Dict:
        """
        Optimize single battery configuration and calculate break-even.

        Args:
            battery_kwh: Battery capacity
            battery_kw: Battery power
            reference_result: Reference scenario results
            use_aggregation: Use 2h aggregation

        Returns:
            Results with break-even cost
        """
        result = self._optimize_monthly(battery_kwh, battery_kw, use_aggregation)

        # Calculate annual savings
        annual_savings = reference_result['annual_total_cost'] - result['annual_total_cost']

        # Calculate NPV of savings
        lifetime_years = config.battery.lifetime_years
        discount_rate = config.economics.discount_rate

        npv_savings = sum([
            annual_savings / ((1 + discount_rate) ** year)
            for year in range(1, lifetime_years + 1)
        ])

        # Break-even cost per kWh
        breakeven_cost_per_kwh = npv_savings / battery_kwh if battery_kwh > 0 else 0

        result['annual_savings'] = annual_savings
        result['npv_savings'] = npv_savings
        result['breakeven_cost_per_kwh'] = breakeven_cost_per_kwh
        result['battery_kwh'] = battery_kwh
        result['battery_kw'] = battery_kw

        return result

    def optimize_multiple_sizes(
        self,
        kwh_range: List[float],
        kw_range: List[float],
        use_aggregation: bool = True
    ) -> List[Dict]:
        """
        Optimize multiple battery configurations.

        Args:
            kwh_range: List of battery capacities to test
            kw_range: List of battery power ratings to test
            use_aggregation: Use 2h aggregation

        Returns:
            List of results for each configuration
        """
        print("="*80)
        print(f"BATTERY SIZING OPTIMIZATION")
        if use_aggregation:
            print(f"Using {self.agg_hours}h aggregation for 4x speedup")
        else:
            print("Using full 1h resolution")
        print("="*80)
        print()

        # Calculate reference
        reference = self.calculate_reference(use_aggregation)

        # Test all configurations
        results = []
        n_configs = len(kwh_range) * len(kw_range)

        print(f"Testing {n_configs} battery configurations...")
        start_total = time.time()

        for i, battery_kwh in enumerate(kwh_range):
            for j, battery_kw in enumerate(kw_range):
                config_num = i * len(kw_range) + j + 1

                start = time.time()
                result = self.optimize_battery_config(
                    battery_kwh, battery_kw, reference, use_aggregation
                )
                elapsed = time.time() - start

                result['elapsed_time'] = elapsed

                results.append(result)

                # Progress
                if config_num % 5 == 0 or config_num == n_configs:
                    print(f"  [{config_num}/{n_configs}] {battery_kwh} kWh / {battery_kw} kW: "
                          f"Break-even {result['breakeven_cost_per_kwh']:,.0f} kr/kWh "
                          f"({elapsed:.1f}s)")

        elapsed_total = time.time() - start_total

        print()
        print(f"✓ Complete in {elapsed_total:.1f} seconds")
        print(f"  Average: {elapsed_total/n_configs:.1f}s per configuration")
        print()

        # Find best configuration
        best = max(results, key=lambda x: x['breakeven_cost_per_kwh'])
        print(f"Best configuration:")
        print(f"  {best['battery_kwh']} kWh / {best['battery_kw']} kW")
        print(f"  Break-even: {best['breakeven_cost_per_kwh']:,.0f} kr/kWh")
        print(f"  Annual savings: {best['annual_savings']:,.0f} kr")
        print()

        return results, reference

    def save_results(self, results: List[Dict], reference: Dict, output_dir: Path):
        """Save optimization results to file."""

        output_dir.mkdir(exist_ok=True)

        # Create summary
        summary = {
            'year': self.year,
            'aggregation_hours': self.agg_hours,
            'reference': reference,
            'configurations': []
        }

        for res in results:
            summary['configurations'].append({
                'battery_kwh': res['battery_kwh'],
                'battery_kw': res['battery_kw'],
                'annual_savings': res['annual_savings'],
                'npv_savings': res['npv_savings'],
                'breakeven_cost_per_kwh': res['breakeven_cost_per_kwh'],
                'annual_total_cost': res['annual_total_cost'],
                'elapsed_time': res['elapsed_time']
            })

        # Save to JSON
        output_file = output_dir / 'battery_sizing_fast_results.json'
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"✓ Results saved to {output_file}")

        # Create markdown summary
        self._create_markdown_summary(results, reference, output_dir)

    def _create_markdown_summary(self, results: List[Dict], reference: Dict, output_dir: Path):
        """Create markdown summary of results."""

        # Sort by break-even cost
        sorted_results = sorted(results, key=lambda x: x['breakeven_cost_per_kwh'], reverse=True)

        md = ["# Battery Sizing Optimization Results", ""]
        md.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        md.append(f"**Year**: {self.year}")
        md.append(f"**Aggregation**: {self.agg_hours}h blocks")
        md.append("")

        md.append("## Reference (No Battery)")
        md.append("")
        md.append(f"- Annual cost: {reference['annual_total_cost']:,.0f} kr")
        md.append(f"  - Energy: {reference['annual_energy_cost']:,.0f} kr")
        md.append(f"  - Power: {reference['annual_power_cost']:,.0f} kr")
        md.append("")

        md.append("## Top 10 Configurations")
        md.append("")
        md.append("| Rank | Capacity | Power | Break-even (kr/kWh) | Annual Savings | NPV Savings |")
        md.append("|------|----------|-------|---------------------|----------------|-------------|")

        for i, res in enumerate(sorted_results[:10], 1):
            md.append(f"| {i} | {res['battery_kwh']:.0f} kWh | {res['battery_kw']:.0f} kW | "
                     f"{res['breakeven_cost_per_kwh']:,.0f} | "
                     f"{res['annual_savings']:,.0f} kr | "
                     f"{res['npv_savings']:,.0f} kr |")

        md.append("")
        md.append("## Market Comparison")
        md.append("")
        md.append(f"- **Market cost**: {config.battery.market_cost_nok_per_kwh:,.0f} kr/kWh")
        md.append(f"- **Target cost**: {config.battery.target_cost_nok_per_kwh:,.0f} kr/kWh")
        md.append("")

        best = sorted_results[0]
        if best['breakeven_cost_per_kwh'] >= config.battery.market_cost_nok_per_kwh:
            md.append(f"✅ **PROFITABLE**: Best break-even ({best['breakeven_cost_per_kwh']:,.0f} kr/kWh) "
                     f"> market cost ({config.battery.market_cost_nok_per_kwh:,.0f} kr/kWh)")
        elif best['breakeven_cost_per_kwh'] >= config.battery.target_cost_nok_per_kwh:
            md.append(f"⚠️ **POTENTIALLY VIABLE**: Break-even > target cost")
            md.append(f"   Battery cost must reach {best['breakeven_cost_per_kwh']:,.0f} kr/kWh")
        else:
            md.append(f"❌ **NOT VIABLE**: Break-even ({best['breakeven_cost_per_kwh']:,.0f} kr/kWh) "
                     f"< target cost ({config.battery.target_cost_nok_per_kwh:,.0f} kr/kWh)")

        md.append("")
        md.append("## Performance")
        md.append("")
        total_time = sum([r['elapsed_time'] for r in results])
        md.append(f"- Total configurations tested: {len(results)}")
        md.append(f"- Total optimization time: {total_time:.1f} seconds")
        md.append(f"- Average per configuration: {total_time/len(results):.1f} seconds")

        # Save markdown
        md_file = output_dir / 'battery_sizing_fast_summary.md'
        with open(md_file, 'w') as f:
            f.write('\n'.join(md))

        print(f"✓ Summary saved to {md_file}")


def main():
    """Run fast battery sizing optimization."""

    # Initialize optimizer
    optimizer = FastBatterySizingOptimizer(year=2025, aggregation_hours=2)

    # Define battery size ranges to test
    kwh_range = [20, 40, 60, 80, 100]  # Capacity
    kw_range = [10, 20, 30, 40, 50]    # Power rating

    # Run optimization with 2h aggregation
    results, reference = optimizer.optimize_multiple_sizes(
        kwh_range,
        kw_range,
        use_aggregation=True
    )

    # Save results
    output_dir = Path(__file__).parent / 'results'
    optimizer.save_results(results, reference, output_dir)


if __name__ == "__main__":
    main()
