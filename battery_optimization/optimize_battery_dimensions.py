"""
Battery Sizing Optimization using Hybrid Grid Search + Powell Method

Optimizes battery dimensions (E_nom, P_max) to maximize NPV over 15 years.

Method:
1. Coarse grid search (8×8 = 64 combinations)
2. Powell's method refinement from best grid point
3. NPV surface visualization

Author: Claude Code
Date: 2025-11-08
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from pathlib import Path
import json
from datetime import datetime
from itertools import product
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
from joblib import Parallel, delayed
import multiprocessing

# Import existing modules
from config import BatteryOptimizationConfig
from core.lp_monthly_optimizer import MonthlyLPOptimizer
from core.price_fetcher import ENTSOEPriceFetcher


class BatterySizingOptimizer:
    """Optimize battery dimensions (E_nom, P_max) for maximum NPV"""

    def __init__(self, config, year=2024, resolution='PT60M'):
        """
        Initialize optimizer

        Args:
            config: BatteryOptimizationConfig instance
            year: Year for price/solar data
            resolution: Time resolution ('PT60M' or 'PT15M')
        """
        self.config = config
        self.year = year
        self.resolution = resolution
        self.discount_rate = config.economics.discount_rate
        self.project_years = config.economics.project_lifetime_years

        # Load data once (reused for all evaluations)
        print("Loading data...")
        self.data = self._load_annual_data()
        print(f"✓ Data loaded: {len(self.data['timestamps'])} timesteps")

        # Cache for NPV evaluations
        self.npv_cache = {}
        self.evaluation_count = 0

    def _load_annual_data(self):
        """Load full year of prices, solar production, and load consumption"""

        # Load spot prices from cached file
        if self.resolution == 'PT60M':
            price_file = Path(__file__).parent / 'data' / 'spot_prices' / f'NO2_{self.year}_60min_real.csv'
        else:
            price_file = Path(__file__).parent / 'data' / 'spot_prices' / f'NO2_{self.year}_15min_real.csv'

        if not price_file.exists():
            # Fallback to fetcher
            fetcher = ENTSOEPriceFetcher(
                bidding_zone='NO2',
                resolution=self.resolution,
                use_cache=True
            )
            price_data = fetcher.get_prices(
                start_date=f'{self.year}-01-01',
                end_date=f'{self.year}-12-31'
            )
        else:
            price_data = pd.read_csv(price_file)
            price_data['timestamp'] = pd.to_datetime(price_data['timestamp'])
            price_data.set_index('timestamp', inplace=True)

        if price_data is None or price_data.empty:
            raise ValueError(f"Failed to load price data for {self.year}")

        # Load solar production (from PVGIS data - 138.55 kWp system)
        solar_file = Path(__file__).parent / 'data' / 'pv_profiles' / 'pvgis_58.97_5.73_138.55kWp.csv'
        if not solar_file.exists():
            raise FileNotFoundError(f"Solar data not found: {solar_file}")

        solar_df = pd.read_csv(solar_file)

        # Check column names and adapt
        if 'P' in solar_df.columns:
            pv_col = 'P'  # PVGIS format
        elif 'production_kw' in solar_df.columns:
            pv_col = 'production_kw'  # Our cached format
        elif 'pv_power_kw' in solar_df.columns:
            pv_col = 'pv_power_kw'
        else:
            # Try to find power column
            power_cols = [col for col in solar_df.columns if 'power' in col.lower() or 'production' in col.lower() or col == 'P']
            if power_cols:
                pv_col = power_cols[0]
            else:
                raise ValueError(f"Cannot find PV power column in {solar_file.name}. Columns: {list(solar_df.columns)}")

        # PVGIS data is typically hourly with 8760 rows
        # Create hourly timestamps for full year
        timestamps_hourly = pd.date_range(
            start=f'{self.year}-01-01',
            periods=len(solar_df),
            freq='h'
        )

        # PV production in kW (PVGIS gives W, convert to kW)
        pv_production_hourly = solar_df[pv_col].values
        if pv_production_hourly.max() > 200:  # Likely in Watts
            pv_production_hourly = pv_production_hourly / 1000.0

        # Generate commercial load profile (hourly)
        load_consumption_hourly = self._generate_load_profile(timestamps_hourly)

        # Resample to target resolution if needed
        if self.resolution == 'PT15M':
            # Upsample to 15-minute resolution
            timestamps = pd.date_range(
                start=f'{self.year}-01-01',
                end=f'{self.year}-12-31 23:45',
                freq='15min'
            )

            # Linear interpolation for upsampling
            pv_production = np.interp(
                np.arange(len(timestamps)),
                np.arange(len(pv_production_hourly)) * 4,  # Every 4th point is hourly
                pv_production_hourly
            )

            load_consumption = np.interp(
                np.arange(len(timestamps)),
                np.arange(len(load_consumption_hourly)) * 4,
                load_consumption_hourly
            )
        else:
            # Use hourly data directly
            timestamps = timestamps_hourly
            pv_production = pv_production_hourly
            load_consumption = load_consumption_hourly

        # Align prices with timestamps
        price_cols = [col for col in price_data.columns if 'price' in col.lower()]
        if 'price_nok_per_kwh' in price_data.columns:
            spot_prices = price_data['price_nok_per_kwh'].values[:len(timestamps)]
        elif 'price_nok' in price_data.columns:
            spot_prices = price_data['price_nok'].values[:len(timestamps)]
        elif 'price' in price_data.columns:
            spot_prices = price_data['price'].values[:len(timestamps)]
        elif price_cols:
            spot_prices = price_data[price_cols[0]].values[:len(timestamps)]
        else:
            raise ValueError(f"Cannot find price column in {price_file.name}. Columns: {list(price_data.columns)}")

        # Ensure all arrays have same length
        min_len = min(len(timestamps), len(pv_production), len(load_consumption), len(spot_prices))

        return {
            'timestamps': timestamps[:min_len],
            'pv_production': pv_production[:min_len],
            'load_consumption': load_consumption[:min_len],
            'spot_prices': spot_prices[:min_len]
        }

    def _generate_load_profile(self, timestamps):
        """Generate realistic commercial load profile"""
        base_load = self.config.consumption.base_load_kw
        peak_load = self.config.consumption.peak_load_kw

        load = np.zeros(len(timestamps))

        for i, ts in enumerate(timestamps):
            hour = ts.hour
            weekday = ts.weekday()

            if weekday < 5:  # Weekday
                if 6 <= hour < 8:  # Morning ramp
                    load[i] = base_load + (peak_load - base_load) * 0.6
                elif 8 <= hour < 16:  # Peak hours
                    load[i] = peak_load
                elif 16 <= hour < 18:  # Evening ramp
                    load[i] = base_load + (peak_load - base_load) * 0.4
                else:  # Night
                    load[i] = base_load
            else:  # Weekend
                load[i] = base_load * 0.5

        # Add random variation (±10%)
        load *= (1 + np.random.normal(0, 0.1, len(load)))
        load = np.clip(load, base_load * 0.3, peak_load * 1.2)

        return load

    def evaluate_npv(self, E_nom, P_max, verbose=False, return_details=False):
        """
        Evaluate NPV for given battery dimensions

        Args:
            E_nom: Battery energy capacity [kWh]
            P_max: Battery power rating [kW]
            verbose: Print detailed output
            return_details: If True, return dict with NPV, break-even cost, and annual savings

        Returns:
            NPV over project lifetime [NOK], or dict if return_details=True
        """
        # Check cache
        cache_key = (round(E_nom, 2), round(P_max, 2))
        if cache_key in self.npv_cache:
            return self.npv_cache[cache_key]

        self.evaluation_count += 1

        # Handle reference case (no battery)
        if E_nom < 1 or P_max < 1:
            if verbose:
                print(f"[{self.evaluation_count}] Reference case (no battery)")
            npv = 0.0  # No investment, no savings
            self.npv_cache[cache_key] = npv
            return npv

        if verbose:
            print(f"\n[{self.evaluation_count}] Evaluating E_nom={E_nom:.1f} kWh, P_max={P_max:.1f} kW")

        try:
            # Calculate initial investment (battery system: cells + inverter + control)
            initial_cost = self.config.battery.get_total_battery_system_cost(E_nom, P_max)

            if verbose:
                print(f"  Initial cost: {initial_cost:,.0f} NOK")

            # Create optimizer with specific battery size
            optimizer = MonthlyLPOptimizer(
                config=self.config,
                resolution=self.resolution,
                battery_kwh=E_nom,
                battery_kw=P_max
            )

            # Split data by month
            annual_savings = 0.0
            monthly_results = []

            # TODO: LEVEL 2 PARALLELIZATION - Monthly Optimization
            # ===========================================================
            # POTENTIAL SPEEDUP: Additional 12x (combined with Level 1 = 144x total!)
            #
            # APPROACH:
            # 1. Run all 12 months in parallel with fixed SOC boundary conditions:
            #    - E_initial = 0.5 * E_nom (50% SOC) for all months
            #    - E_final = 0.5 * E_nom (50% SOC) enforced as constraint
            #
            # 2. SOC BOUNDARY HANDLING:
            #    - Fixed 50% start/end ensures continuity over year
            #    - Error from boundary mismatch ≈ 0.5 * 1/30 ≈ 1.67% per month
            #    - Annual error < 2% (acceptable for optimization)
            #
            # 3. ITERATIVE REFINEMENT (optional):
            #    - After parallel solve, update E_initial[m+1] = E_final[m]
            #    - Re-optimize months with SOC mismatches > 5%
            #    - Typically converges in 1-2 iterations
            #
            # 4. IMPLEMENTATION:
            #    results = Parallel(n_jobs=12)(
            #        delayed(optimize_month_with_boundary)(
            #            month, E_initial=0.5*E_nom, E_final_target=0.5*E_nom
            #        ) for month in range(1, 13)
            #    )
            #
            # 5. COMPUTATIONAL IMPACT:
            #    - Current: 12 months × 2.5 min/battery = 30 min per configuration
            #    - Level 1 parallel: 30 min / 12 CPUs ≈ 2.5 min per configuration (36 configs = 1.5 hrs total)
            #    - Level 1 + Level 2: 2.5 min / 12 CPUs ≈ 12 sec per configuration (36 configs = 7 min total!)
            #
            # 6. TRADE-OFFS:
            #    - Pro: 12x additional speedup
            #    - Pro: Simple implementation with fixed boundaries
            #    - Con: ~2% accuracy loss from boundary approximation
            #    - Con: Requires more memory (12 LP problems simultaneously)
            #
            # STATUS: Not implemented (Level 1 parallelization sufficient for now)
            # ===========================================================

            for month in range(1, 13):
                # Filter data for this month
                mask = self.data['timestamps'].month == month
                month_timestamps = self.data['timestamps'][mask]
                month_pv = self.data['pv_production'][mask]
                month_load = self.data['load_consumption'][mask]
                month_prices = self.data['spot_prices'][mask]

                # Get baseline cost (no battery)
                baseline_optimizer = MonthlyLPOptimizer(
                    config=self.config,
                    resolution=self.resolution,
                    battery_kwh=0,  # No battery
                    battery_kw=0
                )

                baseline_result = baseline_optimizer.optimize_month(
                    month_idx=month,
                    pv_production=month_pv,
                    load_consumption=month_load,
                    spot_prices=month_prices,
                    timestamps=month_timestamps,
                    E_initial=0
                )

                # Optimize with battery
                E_initial = 0.5 * E_nom if month == 1 else monthly_results[-1].E_battery_final

                result = optimizer.optimize_month(
                    month_idx=month,
                    pv_production=month_pv,
                    load_consumption=month_load,
                    spot_prices=month_prices,
                    timestamps=month_timestamps,
                    E_initial=E_initial
                )

                if not result.success:
                    if verbose:
                        print(f"  ⚠ Month {month} failed: {result.message}")
                    self.npv_cache[cache_key] = float('-inf')
                    return float('-inf')

                monthly_savings = baseline_result.objective_value - result.objective_value
                annual_savings += monthly_savings
                monthly_results.append(result)

                if verbose:
                    print(f"  Month {month:2d}: Savings = {monthly_savings:8,.0f} NOK")

            # Calculate NPV
            pv_factor = sum([1 / (1 + self.discount_rate)**y for y in range(1, self.project_years + 1)])
            npv = -initial_cost + annual_savings * pv_factor

            # Calculate break-even cost (NOK/kWh)
            # Break-even cost is the battery system cost per kWh where NPV = 0
            # NPV = 0 when: initial_cost = annual_savings * pv_factor
            # Break-even_cost = (annual_savings * pv_factor) / E_nom
            breakeven_cost_per_kwh = (annual_savings * pv_factor) / E_nom if E_nom > 0 else 0

            # Actual battery system cost per kWh (for comparison)
            actual_cost_per_kwh = initial_cost / E_nom if E_nom > 0 else 0

            if verbose:
                print(f"  Annual savings: {annual_savings:,.0f} NOK")
                print(f"  PV factor: {pv_factor:.2f}")
                print(f"  NPV: {npv:,.0f} NOK")
                print(f"  Break-even cost: {breakeven_cost_per_kwh:,.0f} NOK/kWh")
                print(f"  Actual cost: {actual_cost_per_kwh:,.0f} NOK/kWh")

            # Cache result
            self.npv_cache[cache_key] = npv

            if return_details:
                return {
                    'npv': npv,
                    'annual_savings': annual_savings,
                    'breakeven_cost_per_kwh': breakeven_cost_per_kwh,
                    'actual_cost_per_kwh': actual_cost_per_kwh,
                    'initial_cost': initial_cost
                }

            return npv

        except Exception as e:
            if verbose:
                print(f"  ⚠ Evaluation failed: {e}")
            self.npv_cache[cache_key] = float('-inf')
            return float('-inf')

    def grid_search_coarse(self, E_range, P_range, n_E=8, n_P=8, n_jobs=-1):
        """
        Coarse grid search over (E_nom, P_max) space using parallel processing

        Args:
            E_range: (E_min, E_max) in kWh
            P_range: (P_min, P_max) in kW
            n_E: Number of E_nom grid points
            n_P: Number of P_max grid points
            n_jobs: Number of parallel jobs (-1 = use all CPUs, 1 = sequential)

        Returns:
            dict with 'grid_results', 'best_E', 'best_P', 'best_npv'
        """
        print("\n" + "="*70)
        print("Phase 1: Coarse Grid Search (Parallel)")
        print("="*70)

        E_grid = np.linspace(E_range[0], E_range[1], n_E)
        P_grid = np.linspace(P_range[0], P_range[1], n_P)

        n_cpus = multiprocessing.cpu_count() if n_jobs == -1 else n_jobs
        print(f"Grid: {n_E}×{n_P} = {n_E * n_P} combinations")
        print(f"E_nom range: {E_range[0]:.0f} - {E_range[1]:.0f} kWh")
        print(f"P_max range: {P_range[0]:.0f} - {P_range[1]:.0f} kW")
        print(f"Parallel workers: {n_cpus} CPUs")

        # Create all (E, P) combinations
        combinations = [(E, P) for E in E_grid for P in P_grid]

        start_time = time.time()

        # Parallel evaluation using joblib
        print("Evaluating battery configurations in parallel...")
        results = Parallel(n_jobs=n_jobs, verbose=10)(
            delayed(self.evaluate_npv)(E, P, verbose=False, return_details=True)
            for E, P in combinations
        )

        # Reshape results back to grid format
        npv_list = [r['npv'] for r in results]
        breakeven_list = [r['breakeven_cost_per_kwh'] for r in results]

        npv_results = np.array(npv_list).reshape(n_E, n_P)
        breakeven_results = np.array(breakeven_list).reshape(n_E, n_P)

        # Find best configuration
        best_idx = np.argmax(npv_results.flat)
        best_i = best_idx // n_P
        best_j = best_idx % n_P
        best_E = E_grid[best_i]
        best_P = P_grid[best_j]
        best_npv = npv_results[best_i, best_j]

        elapsed = time.time() - start_time
        print(f"\n✓ Grid search complete in {elapsed/60:.1f} minutes")
        print(f"  Best: E={best_E:.1f} kWh, P={best_P:.1f} kW → NPV={best_npv:,.0f} NOK")
        print(f"  Speedup: ~{n_cpus}x faster than sequential")

        return {
            'E_grid': E_grid,
            'P_grid': P_grid,
            'npv_grid': npv_results,
            'breakeven_grid': breakeven_results,
            'best_E': best_E,
            'best_P': best_P,
            'best_npv': best_npv
        }

    def powell_refinement(self, x0, bounds):
        """
        Refine solution using Powell's method

        Args:
            x0: Starting point [E_nom, P_max]
            bounds: [(E_min, E_max), (P_min, P_max)]

        Returns:
            dict with 'optimal_E', 'optimal_P', 'optimal_npv'
        """
        print("\n" + "="*70)
        print("Phase 2: Powell's Method Refinement")
        print("="*70)
        print(f"Starting point: E={x0[0]:.1f} kWh, P={x0[1]:.1f} kW")

        def objective(x):
            """Objective function for minimization (negative NPV)"""
            E_nom, P_max = x[0], x[1]
            npv = self.evaluate_npv(E_nom, P_max, verbose=False)
            return -npv  # Minimize negative NPV = maximize NPV

        start_time = time.time()

        result = minimize(
            objective,
            x0=x0,
            method='Powell',
            bounds=bounds,
            options={
                'maxiter': 50,
                'ftol': 100,  # Tolerance in NOK
                'disp': True
            }
        )

        elapsed = time.time() - start_time

        optimal_E = result.x[0]
        optimal_P = result.x[1]
        optimal_npv = -result.fun

        print(f"✓ Powell refinement complete in {elapsed/60:.1f} minutes")
        print(f"  Optimal: E={optimal_E:.1f} kWh, P={optimal_P:.1f} kW → NPV={optimal_npv:,.0f} NOK")
        print(f"  Evaluations: {result.nfev}")
        print(f"  Message: {result.message}")

        return {
            'optimal_E': optimal_E,
            'optimal_P': optimal_P,
            'optimal_npv': optimal_npv,
            'success': result.success,
            'message': result.message,
            'iterations': result.nfev
        }

    def visualize_npv_surface(self, grid_results, powell_result, output_dir='results'):
        """
        Create NPV surface visualization

        Args:
            grid_results: Results from grid_search_coarse
            powell_result: Results from powell_refinement
            output_dir: Directory to save plots
        """
        print("\n" + "="*70)
        print("Generating Visualizations")
        print("="*70)

        output_path = Path(__file__).parent / output_dir
        output_path.mkdir(exist_ok=True)

        E_grid = grid_results['E_grid']
        P_grid = grid_results['P_grid']
        npv_grid = grid_results['npv_grid']

        # Create figure with subplots
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        # Plot 1: Contour plot
        ax = axes[0]
        E_mesh, P_mesh = np.meshgrid(E_grid, P_grid)

        # Convert to millions NOK for readability
        npv_plot = npv_grid.T / 1e6

        contour = ax.contourf(E_mesh, P_mesh, npv_plot, levels=20, cmap='RdYlGn')
        ax.contour(E_mesh, P_mesh, npv_plot, levels=10, colors='black', alpha=0.3, linewidths=0.5)

        # Mark grid best point
        ax.plot(grid_results['best_E'], grid_results['best_P'],
                'b*', markersize=20, label=f"Grid best: ({grid_results['best_E']:.0f}, {grid_results['best_P']:.0f})")

        # Mark Powell optimal point
        ax.plot(powell_result['optimal_E'], powell_result['optimal_P'],
                'r*', markersize=20, label=f"Powell optimal: ({powell_result['optimal_E']:.0f}, {powell_result['optimal_P']:.0f})")

        ax.set_xlabel('Battery Capacity (kWh)', fontsize=12)
        ax.set_ylabel('Battery Power (kW)', fontsize=12)
        ax.set_title('NPV Surface (Million NOK)', fontsize=14, fontweight='bold')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)

        # Colorbar
        cbar = plt.colorbar(contour, ax=ax)
        cbar.set_label('NPV (Million NOK)', fontsize=11)

        # Plot 2: Cross-sections
        ax = axes[1]

        # E_nom cross-section at optimal P_max
        P_idx = np.argmin(np.abs(P_grid - powell_result['optimal_P']))
        ax.plot(E_grid, npv_grid[:, P_idx] / 1e6, 'b-o', linewidth=2,
                label=f'P_max = {P_grid[P_idx]:.0f} kW (slice)')

        # P_max cross-section at optimal E_nom
        E_idx = np.argmin(np.abs(E_grid - powell_result['optimal_E']))
        ax.plot(P_grid, npv_grid[E_idx, :] / 1e6, 'r-s', linewidth=2,
                label=f'E_nom = {E_grid[E_idx]:.0f} kWh (slice)')

        ax.axvline(powell_result['optimal_E'], color='blue', linestyle='--', alpha=0.5)
        ax.axhline(powell_result['optimal_npv'] / 1e6, color='green', linestyle='--', alpha=0.5,
                   label=f'Optimal NPV = {powell_result["optimal_npv"]/1e6:.2f} M NOK')

        ax.set_xlabel('Battery Dimension (kWh or kW)', fontsize=12)
        ax.set_ylabel('NPV (Million NOK)', fontsize=12)
        ax.set_title('NPV Cross-Sections', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save figure
        fig_path = output_path / 'battery_sizing_optimization.png'
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved visualization: {fig_path}")

        plt.close()

        # Create 3D surface plot
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')

        surf = ax.plot_surface(E_mesh, P_mesh, npv_plot, cmap='RdYlGn', alpha=0.8)

        # Mark optimal point
        ax.scatter([powell_result['optimal_E']], [powell_result['optimal_P']],
                   [powell_result['optimal_npv']/1e6], color='red', s=100, marker='*',
                   label=f"Optimal: ({powell_result['optimal_E']:.0f}, {powell_result['optimal_P']:.0f})")

        ax.set_xlabel('Battery Capacity (kWh)', fontsize=11)
        ax.set_ylabel('Battery Power (kW)', fontsize=11)
        ax.set_zlabel('NPV (Million NOK)', fontsize=11)
        ax.set_title('NPV Surface - 3D View', fontsize=14, fontweight='bold')

        # Colorbar
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10)

        # Save 3D plot
        fig_path_3d = output_path / 'battery_sizing_optimization_3d.png'
        plt.savefig(fig_path_3d, dpi=300, bbox_inches='tight')
        print(f"✓ Saved 3D visualization: {fig_path_3d}")

        plt.close()

    def visualize_breakeven_costs(self, grid_results, powell_result, output_dir='results'):
        """
        Create break-even cost visualization

        Args:
            grid_results: Results from grid_search_coarse (must include 'breakeven_grid')
            powell_result: Results from powell_refinement
            output_dir: Directory to save plots
        """
        print("\nGenerating Break-even Cost Visualizations...")

        output_path = Path(__file__).parent / output_dir
        output_path.mkdir(exist_ok=True)

        E_grid = grid_results['E_grid']
        P_grid = grid_results['P_grid']
        breakeven_grid = grid_results['breakeven_grid']

        # Create figure with subplots
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        # Plot 1: Contour plot
        ax = axes[0]
        E_mesh, P_mesh = np.meshgrid(E_grid, P_grid)

        # Convert to NOK/kWh (keep as is, no scaling)
        breakeven_plot = breakeven_grid.T

        contour = ax.contourf(E_mesh, P_mesh, breakeven_plot, levels=20, cmap='RdYlGn')
        ax.contour(E_mesh, P_mesh, breakeven_plot, levels=10, colors='black', alpha=0.3, linewidths=0.5)

        # Mark grid best point
        ax.plot(grid_results['best_E'], grid_results['best_P'],
                'b*', markersize=20, label=f"Grid best: ({grid_results['best_E']:.0f}, {grid_results['best_P']:.0f})")

        # Mark Powell optimal point
        ax.plot(powell_result['optimal_E'], powell_result['optimal_P'],
                'r*', markersize=20, label=f"Powell optimal: ({powell_result['optimal_E']:.0f}, {powell_result['optimal_P']:.0f})")

        ax.set_xlabel('Battery Capacity (kWh)', fontsize=12)
        ax.set_ylabel('Battery Power (kW)', fontsize=12)
        ax.set_title('Break-even Battery System Cost (NOK/kWh)', fontsize=14, fontweight='bold')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)

        # Colorbar
        cbar = plt.colorbar(contour, ax=ax)
        cbar.set_label('Break-even Cost (NOK/kWh)', fontsize=11)

        # Plot 2: Cross-sections
        ax = axes[1]

        # E_nom cross-section at optimal P_max
        P_idx = np.argmin(np.abs(P_grid - powell_result['optimal_P']))
        ax.plot(E_grid, breakeven_grid[:, P_idx], 'b-o', linewidth=2,
                label=f'P_max = {P_grid[P_idx]:.0f} kW (slice)')

        # P_max cross-section at optimal E_nom
        E_idx = np.argmin(np.abs(E_grid - powell_result['optimal_E']))
        ax.plot(P_grid, breakeven_grid[E_idx, :], 'r-s', linewidth=2,
                label=f'E_nom = {E_grid[E_idx]:.0f} kWh (slice)')

        # Add reference lines for market costs
        ax.axhline(5000, color='orange', linestyle='--', alpha=0.7, label='Market cost: 5000 NOK/kWh')
        ax.axhline(2500, color='green', linestyle='--', alpha=0.7, label='Target cost: 2500 NOK/kWh')

        ax.set_xlabel('Battery Dimension (kWh or kW)', fontsize=12)
        ax.set_ylabel('Break-even Cost (NOK/kWh)', fontsize=12)
        ax.set_title('Break-even Cost Cross-Sections', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save figure
        fig_path = output_path / 'battery_sizing_breakeven_costs.png'
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved break-even visualization: {fig_path}")

        plt.close()

        # Create 3D surface plot
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')

        surf = ax.plot_surface(E_mesh, P_mesh, breakeven_plot, cmap='RdYlGn', alpha=0.8)

        # Mark optimal point - get break-even at optimal
        optimal_breakeven = breakeven_grid[E_idx, P_idx]
        ax.scatter([powell_result['optimal_E']], [powell_result['optimal_P']],
                   [optimal_breakeven], color='red', s=100, marker='*',
                   label=f"Optimal: {optimal_breakeven:.0f} NOK/kWh")

        ax.set_xlabel('Battery Capacity (kWh)', fontsize=11)
        ax.set_ylabel('Battery Power (kW)', fontsize=11)
        ax.set_zlabel('Break-even Cost (NOK/kWh)', fontsize=11)
        ax.set_title('Break-even Cost Surface - 3D View', fontsize=14, fontweight='bold')
        ax.legend()

        # Colorbar
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10)

        # Save 3D plot
        fig_path_3d = output_path / 'battery_sizing_breakeven_costs_3d.png'
        plt.savefig(fig_path_3d, dpi=300, bbox_inches='tight')
        print(f"✓ Saved 3D break-even visualization: {fig_path_3d}")

        plt.close()

    def generate_report(self, grid_results, powell_result, output_dir='results'):
        """Generate comprehensive optimization report"""

        output_path = Path(__file__).parent / output_dir
        output_path.mkdir(exist_ok=True)

        report = {
            'optimization_metadata': {
                'timestamp': datetime.now().isoformat(),
                'year': self.year,
                'resolution': self.resolution,
                'discount_rate': self.discount_rate,
                'project_years': self.project_years,
                'total_evaluations': self.evaluation_count
            },
            'grid_search': {
                'E_range': [float(grid_results['E_grid'].min()), float(grid_results['E_grid'].max())],
                'P_range': [float(grid_results['P_grid'].min()), float(grid_results['P_grid'].max())],
                'grid_size': [len(grid_results['E_grid']), len(grid_results['P_grid'])],
                'best_E_nom_kwh': float(grid_results['best_E']),
                'best_P_max_kw': float(grid_results['best_P']),
                'best_npv_nok': float(grid_results['best_npv'])
            },
            'powell_refinement': {
                'optimal_E_nom_kwh': float(powell_result['optimal_E']),
                'optimal_P_max_kw': float(powell_result['optimal_P']),
                'optimal_npv_nok': float(powell_result['optimal_npv']),
                'success': powell_result['success'],
                'iterations': powell_result['iterations']
            },
            'optimal_solution': {
                'battery_capacity_kwh': float(powell_result['optimal_E']),
                'battery_power_kw': float(powell_result['optimal_P']),
                'npv_nok': float(powell_result['optimal_npv']),
                'npv_million_nok': float(powell_result['optimal_npv'] / 1e6),
                'initial_investment_nok': float(
                    self.config.battery.get_total_battery_system_cost(powell_result['optimal_E'], powell_result['optimal_P'])
                ),
                'c_rate': float(powell_result['optimal_P'] / powell_result['optimal_E'])
            }
        }

        # Save JSON
        json_path = output_path / 'battery_sizing_optimization_results.json'
        with open(json_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"✓ Saved report: {json_path}")

        return report


def main():
    """Run battery sizing optimization"""

    # Load configuration
    config = BatteryOptimizationConfig()

    # Create optimizer
    optimizer = BatterySizingOptimizer(
        config=config,
        year=2024,
        resolution='PT60M'
    )

    # Phase 1: Coarse grid search (reduced for speed: 6x6)
    print("\n" + "="*70)
    print("BATTERY SIZING OPTIMIZATION - Hybrid Method")
    print("="*70)
    print("Method: Grid Search (coarse) + Powell (refinement)")
    print(f"Range: E_nom ∈ [0, 200] kWh, P_max ∈ [0, 100] kW")
    print("="*70)

    grid_results = optimizer.grid_search_coarse(
        E_range=(10, 200),  # Skip 0 to avoid reference case
        P_range=(10, 100),
        n_E=6,  # Reduced from 8 for faster evaluation
        n_P=6
    )

    # Phase 2: Powell refinement
    powell_result = optimizer.powell_refinement(
        x0=[grid_results['best_E'], grid_results['best_P']],
        bounds=[(10, 200), (5, 100)]
    )

    # Phase 3: Visualization
    optimizer.visualize_npv_surface(grid_results, powell_result)
    optimizer.visualize_breakeven_costs(grid_results, powell_result)

    # Phase 4: Report generation
    report = optimizer.generate_report(grid_results, powell_result)

    # Print summary
    print("\n" + "="*70)
    print("OPTIMIZATION SUMMARY")
    print("="*70)
    print(f"Total evaluations: {optimizer.evaluation_count}")
    print(f"\nOptimal Battery Dimensions:")
    print(f"  Capacity: {powell_result['optimal_E']:.1f} kWh")
    print(f"  Power:    {powell_result['optimal_P']:.1f} kW")
    print(f"  C-rate:   {powell_result['optimal_P']/powell_result['optimal_E']:.2f}")
    print(f"\nEconomics:")
    print(f"  NPV: {powell_result['optimal_npv']:,.0f} NOK ({powell_result['optimal_npv']/1e6:.2f} M NOK)")
    print(f"  Initial investment: {report['optimal_solution']['initial_investment_nok']:,.0f} NOK")

    # Calculate economics metrics
    annual_savings = (powell_result['optimal_npv'] + report['optimal_solution']['initial_investment_nok']) / \
                     sum([1 / (1.05)**y for y in range(1, 16)])

    print(f"  Annual savings: {annual_savings:,.0f} NOK/year")
    print(f"  Payback (simple): {report['optimal_solution']['initial_investment_nok'] / annual_savings:.1f} years")
    print("="*70)


if __name__ == '__main__':
    main()
