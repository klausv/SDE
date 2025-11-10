"""
Rolling Horizon Battery Optimizer for Operational Control.

Implements 24-hour LP optimization with state-based peak penalty for real-time
battery dispatch. Uses perfect foresight over 24h window (simulates operational mode).

Based on:
- OPERATIONAL_OPTIMIZATION_STRATEGY.md: 24h horizon, 15-min updates
- PEAK_PENALTY_METHODOLOGY.md: State-based adaptive penalty
- COMMERCIAL_SYSTEMS_COMPARISON.md: Industry validation

Key differences from Monthly LP:
1. Fixed 24-hour horizon (96 timesteps @ 15min) instead of full month
2. State-based peak penalty instead of monthly peak optimization variable
3. Returns next control action + planned trajectory
4. Designed for frequent re-optimization (every 15-30 min)
"""

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

# Import state manager for peak penalty calculation
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from src.operational.state_manager import BatterySystemState


@dataclass
class RollingHorizonResult:
    """Results from 24-hour rolling horizon optimization."""
    # Decision variables (96 timesteps @ 15min)
    P_charge: np.ndarray          # Charging power [kW]
    P_discharge: np.ndarray       # Discharging power [kW]
    P_grid_import: np.ndarray     # Grid import [kW]
    P_grid_export: np.ndarray     # Grid export [kW]
    E_battery: np.ndarray         # Battery energy [kWh]
    P_curtail: np.ndarray         # Solar curtailment [kW]

    # Degradation variables (96 timesteps @ 15min)
    E_delta_pos: np.ndarray       # Positive energy change [kWh]
    E_delta_neg: np.ndarray       # Negative energy change [kWh]
    DOD_abs: np.ndarray           # Absolute depth of discharge [0-1]
    DP_cyc: np.ndarray            # Cyclic degradation [%]
    DP_total: np.ndarray          # Total degradation [%]

    # Aggregated metrics (using progressive LP approximation)
    objective_value: float        # Total cost [NOK] - uses progressive tariff
    energy_cost: float            # Energy cost component [NOK]
    peak_penalty_cost: float      # Peak penalty [NOK] - progressive approximation
    degradation_cost: float       # Degradation cost [NOK]

    # Actual costs (post-processing with step function)
    peak_penalty_actual: float    # Actual step function peak penalty [NOK]
    objective_value_actual: float # Actual total cost [NOK] - energy + actual penalty (excludes degradation)

    # Degradation metrics
    dp_cal_per_timestep: float    # Calendar degradation per timestep [%]
    equivalent_cycles: float      # Total equivalent full cycles (sum of DOD_abs)

    # Status
    success: bool
    message: str
    solve_time_seconds: float

    # Next control action (first timestep only)
    @property
    def next_battery_setpoint_kw(self) -> float:
        """Battery power setpoint for next timestep (P_charge - P_discharge)."""
        return self.P_charge[0] - self.P_discharge[0]

    @property
    def E_battery_final(self) -> float:
        """Final battery SOC at end of 24h horizon."""
        return self.E_battery[-1]


class RollingHorizonOptimizer:
    """
    24-hour LP optimizer for rolling horizon battery control.

    Formulation:
    - Horizon: 24 hours (96 timesteps @ 15min resolution)
    - Variables: P_charge, P_discharge, P_grid_import, P_grid_export, E_battery, P_curtail, P_peak_violation
    - Objective: minimize (energy_cost + adaptive_peak_penalty × peak_violations)
    - Constraints: energy balance, battery dynamics, SOC limits, power limits, grid limits
    """

    def __init__(self, config, battery_kwh: float = None, battery_kw: float = None):
        """
        Initialize rolling horizon optimizer.

        Args:
            config: System configuration object
            battery_kwh: Battery capacity [kWh] (overrides config)
            battery_kw: Battery power rating [kW] (overrides config)
        """
        self.config = config

        # Fixed resolution: 15 minutes (industry standard)
        self.resolution = 'PT15M'
        self.timestep_hours = 0.25

        # Fixed horizon: 24 hours = 96 timesteps
        self.horizon_hours = 24
        self.T = 96  # Number of timesteps

        print(f"\n{'='*70}")
        print(f"Rolling Horizon Optimizer")
        print(f"{'='*70}")
        print(f"  Horizon: {self.horizon_hours} hours")
        print(f"  Resolution: {self.resolution} ({self.timestep_hours} hours)")
        print(f"  Timesteps: {self.T}")

        # Battery parameters
        if battery_kwh is not None:
            self.E_nom = battery_kwh
        else:
            self.E_nom = config.battery_capacity_kwh if hasattr(config, 'battery_capacity_kwh') else 100.0

        if battery_kw is not None:
            self.P_max_charge = battery_kw
            self.P_max_discharge = battery_kw
        else:
            self.P_max_charge = config.battery_power_kw if hasattr(config, 'battery_power_kw') else 50.0
            self.P_max_discharge = config.battery_power_kw if hasattr(config, 'battery_power_kw') else 50.0

        # Efficiency parameters
        battery_config = config.battery if hasattr(config, 'battery') else None
        if battery_config:
            eta_rt = battery_config.efficiency_roundtrip
            self.eta_charge = np.sqrt(eta_rt)
            self.eta_discharge = np.sqrt(eta_rt)
            self.SOC_min = battery_config.min_soc
            self.SOC_max = battery_config.max_soc
        else:
            self.eta_charge = 0.95
            self.eta_discharge = 0.95
            self.SOC_min = 0.1
            self.SOC_max = 0.9

        # Grid limits
        solar_config = config.solar if hasattr(config, 'solar') else None
        self.P_grid_import_limit = solar_config.grid_import_limit_kw if (solar_config and hasattr(solar_config, 'grid_import_limit_kw')) else 70.0
        self.P_grid_export_limit = solar_config.grid_export_limit_kw if solar_config else 70.0

        # Power tariff configuration (bracketed structure)
        # Match monthly LP logic: convert cumulative costs to incremental costs
        tariff_config = config.tariff if hasattr(config, 'tariff') else None
        if tariff_config and hasattr(tariff_config, 'power_brackets'):
            brackets = tariff_config.power_brackets
            self.N_trinn = len(brackets)
            self.p_trinn = []
            self.c_trinn = []

            prev_cost = 0
            for (from_kw, to_kw, cost) in brackets:
                # Width of this bracket
                width = to_kw - from_kw if to_kw != float('inf') else 100  # Cap last bracket
                self.p_trinn.append(width)

                # Incremental cost (difference from previous bracket's cumulative cost)
                incremental_cost = cost - prev_cost
                self.c_trinn.append(incremental_cost)

                prev_cost = cost

            self.p_trinn = np.array(self.p_trinn)
            self.c_trinn = np.array(self.c_trinn)
        else:
            # Fallback: simple single-bracket tariff
            self.N_trinn = 1
            self.p_trinn = np.array([100.0])  # Single 100 kW bracket
            self.c_trinn = np.array([50.0])   # 50 NOK/kW/month default

        # LFP degradation model parameters
        degradation_config = battery_config.degradation if (battery_config and hasattr(battery_config, 'degradation')) else None
        if degradation_config:
            self.cycle_life_full_dod = degradation_config.cycle_life_full_dod
            self.calendar_life_years = degradation_config.calendar_life_years
            self.eol_degradation_pct = degradation_config.eol_degradation_percent
        else:
            # Fallback defaults for LFP battery
            self.cycle_life_full_dod = 5000  # cycles @ 100% DOD
            self.calendar_life_years = 28.0  # years
            self.eol_degradation_pct = 20.0  # % (80% SOH at EOL)

        # Derived degradation rates
        self.rho_constant = self.eol_degradation_pct / self.cycle_life_full_dod  # %/cycle
        self.dp_cal_per_hour = self.eol_degradation_pct / (self.calendar_life_years * 365 * 24)  # %/hour
        self.dp_cal_per_timestep = self.dp_cal_per_hour * self.timestep_hours  # %/timestep

        # Battery cost for degradation calculation
        if battery_config and hasattr(battery_config, 'cost_per_kwh'):
            self.battery_cost_nok_per_kwh = battery_config.cost_per_kwh
        else:
            self.battery_cost_nok_per_kwh = 3054  # NOK/kWh (Skanbatt default)

        print(f"  Battery: {self.E_nom:.1f} kWh, {self.P_max_charge:.1f} kW")
        print(f"  SOC limits: [{self.SOC_min*100:.0f}%, {self.SOC_max*100:.0f}%]")
        print(f"  Grid limits: Import {self.P_grid_import_limit:.0f} kW, Export {self.P_grid_export_limit:.0f} kW")
        print(f"  Power tariff: {self.N_trinn} brackets")
        print(f"  Degradation: LFP model (ρ={self.rho_constant:.6f}%/cycle, cal={self.dp_cal_per_hour:.8f}%/hour)")
        print(f"{'='*70}\n")

    def get_energy_costs(self, timestamps: pd.DatetimeIndex, spot_prices: np.ndarray):
        """
        Calculate energy import costs and export revenues.

        Args:
            timestamps: DatetimeIndex for 24-hour window
            spot_prices: Spot prices [NOK/kWh]

        Returns:
            (c_import, c_export): Cost arrays per timestep
        """
        tariff_config = self.config.tariff if hasattr(self.config, 'tariff') else None

        T = len(timestamps)
        c_import = np.zeros(T)
        c_export = np.zeros(T)

        for t, ts in enumerate(timestamps):
            if isinstance(ts, np.datetime64):
                ts = pd.Timestamp(ts)

            # Energy tariff (peak/off-peak)
            if tariff_config and tariff_config.is_peak_hours(ts):
                energy_tariff = tariff_config.energy_peak
            elif tariff_config:
                energy_tariff = tariff_config.energy_offpeak
            else:
                energy_tariff = 0.296 if (6 <= ts.hour < 22 and ts.weekday() < 5) else 0.176

            # Consumption tax
            if tariff_config and hasattr(tariff_config, 'consumption_tax_monthly'):
                cons_tax = tariff_config.consumption_tax_monthly.get(ts.month, 0.15)
            else:
                cons_tax = 0.15

            # Import cost
            c_import[t] = spot_prices[t] + energy_tariff + cons_tax

            # Export revenue (spot + feed-in tariff)
            c_export[t] = spot_prices[t] + 0.04

        return c_import, c_export

    def _allocate_to_brackets(self, P_kw: float) -> np.ndarray:
        """
        Allocate power across tariff brackets.

        Args:
            P_kw: Total power demand [kW]

        Returns:
            z: Bracket fill fractions [0-1], shape (N_trinn,)
                z[i] = 1.0 if bracket i is full, partial fill otherwise
        """
        z = np.zeros(self.N_trinn)
        remaining = P_kw

        for i in range(self.N_trinn):
            if remaining <= 0:
                break
            # Fill fraction: min(remaining / bracket_width, 1.0)
            fill_kw = min(remaining, self.p_trinn[i])
            z[i] = fill_kw / self.p_trinn[i]  # Convert to fraction
            remaining -= fill_kw

        return z

    def _calculate_tariff_cost(self, z: np.ndarray) -> float:
        """
        Calculate monthly power tariff cost from bracket fill fractions.

        Args:
            z: Bracket fill fractions [0-1], shape (N_trinn,)

        Returns:
            Monthly tariff cost [NOK/month]
        """
        # Cost = Σ c_trinn[i] × z[i]
        # where z[i] is fill fraction and c_trinn[i] is incremental cost for bracket i
        return np.sum(self.c_trinn * z)

    def _build_degradation_equality_constraints(self, T: int, n_vars: int, E_initial: float) -> tuple:
        """
        Build degradation equality constraints for LP formulation.

        Constraints (3*T total):
        1. Energy delta balance: E_delta_pos[t] - E_delta_neg[t] = E[t] - E[t-1]  (T constraints)
        2. DOD definition: DOD_abs[t] * E_nom - E_delta_pos[t] - E_delta_neg[t] = 0  (T constraints)
        3. Cyclic degradation: DP_cyc[t] - rho_constant * DOD_abs[t] = 0  (T constraints)

        Args:
            T: Number of timesteps
            n_vars: Total number of LP variables
            E_initial: Initial battery energy [kWh]

        Returns:
            (A_eq_degradation, b_eq_degradation): Constraint matrix and RHS vector
        """
        A_eq_rows = []
        b_eq_rows = []

        # Constraint 1: Energy delta balance (T constraints)
        # E_delta_pos[t] - E_delta_neg[t] - E[t] + E[t-1] = 0 for t > 0
        # E_delta_pos[0] - E_delta_neg[0] - E[0] = -E_initial for t = 0
        for t in range(T):
            row = np.zeros(n_vars)
            row[6*T + t] = 1.0    # E_delta_pos[t]
            row[7*T + t] = -1.0   # -E_delta_neg[t]
            row[4*T + t] = -1.0   # -E[t]

            if t == 0:
                # E_delta_pos[0] - E_delta_neg[0] - E[0] = -E_initial
                b_eq_rows.append(-E_initial)
            else:
                # E_delta_pos[t] - E_delta_neg[t] - E[t] + E[t-1] = 0
                row[4*T + t - 1] = 1.0  # +E[t-1]
                b_eq_rows.append(0)

            A_eq_rows.append(row)

        # Constraint 2: DOD definition (T constraints)
        # DOD_abs[t] * E_nom = E_delta_pos[t] + E_delta_neg[t]
        # Rearrange: DOD_abs[t] * E_nom - E_delta_pos[t] - E_delta_neg[t] = 0
        for t in range(T):
            row = np.zeros(n_vars)
            row[8*T + t] = self.E_nom  # DOD_abs[t] * E_nom
            row[6*T + t] = -1.0        # -E_delta_pos[t]
            row[7*T + t] = -1.0        # -E_delta_neg[t]
            A_eq_rows.append(row)
            b_eq_rows.append(0)

        # Constraint 3: Cyclic degradation (T constraints)
        # DP_cyc[t] = rho_constant * DOD_abs[t]
        # Rearrange: DP_cyc[t] - rho_constant * DOD_abs[t] = 0
        for t in range(T):
            row = np.zeros(n_vars)
            row[9*T + t] = 1.0                    # DP_cyc[t]
            row[8*T + t] = -self.rho_constant     # -rho_constant * DOD_abs[t]
            A_eq_rows.append(row)
            b_eq_rows.append(0)

        return np.array(A_eq_rows), np.array(b_eq_rows)

    def _build_degradation_inequality_constraints(self, T: int, n_vars: int) -> tuple:
        """
        Build degradation inequality constraints for LP formulation.

        Constraints (2*T total):
        1. DP_total[t] >= DP_cyc[t]: Total degradation must exceed cyclic  (T constraints)
        2. DP_total[t] >= dp_cal_per_timestep: Total degradation must exceed calendar  (T constraints)

        These implement: DP_total[t] = max(DP_cyc[t], dp_cal_per_timestep)

        Args:
            T: Number of timesteps
            n_vars: Total number of LP variables

        Returns:
            (A_ub_degradation, b_ub_degradation): Constraint matrix and RHS vector
        """
        A_ub_rows = []
        b_ub_rows = []

        # Constraint 1: DP_total[t] >= DP_cyc[t]
        # Rearrange: -DP_total[t] + DP_cyc[t] <= 0
        for t in range(T):
            row = np.zeros(n_vars)
            row[10*T + t] = -1.0  # -DP_total[t]
            row[9*T + t] = 1.0    # +DP_cyc[t]
            A_ub_rows.append(row)
            b_ub_rows.append(0)

        # Constraint 2: DP_total[t] >= dp_cal_per_timestep
        # Rearrange: -DP_total[t] <= -dp_cal_per_timestep
        for t in range(T):
            row = np.zeros(n_vars)
            row[10*T + t] = -1.0  # -DP_total[t]
            A_ub_rows.append(row)
            b_ub_rows.append(-self.dp_cal_per_timestep)

        return np.array(A_ub_rows), np.array(b_ub_rows)

    def optimize_24h(self,
                     current_state: BatterySystemState,
                     pv_production: np.ndarray,
                     load_consumption: np.ndarray,
                     spot_prices: np.ndarray,
                     timestamps: pd.DatetimeIndex,
                     verbose: bool = False) -> RollingHorizonResult:
        """
        Optimize battery dispatch over next 24 hours.

        Args:
            current_state: Current system state (SOC, monthly peak, etc.)
            pv_production: PV forecast [kW], shape (96,)
            load_consumption: Load forecast [kW], shape (96,)
            spot_prices: Spot prices [NOK/kWh], shape (96,)
            timestamps: DatetimeIndex for 24-hour window
            verbose: Print detailed output

        Returns:
            RollingHorizonResult with optimal schedule
        """
        import time
        start_time = time.time()

        T = len(timestamps)  # Use actual window size (flexible: 24 for hourly, 96 for 15-min)

        if verbose:
            print(f"\n{'='*70}")
            print(f"Rolling Horizon Optimization - 24h Window")
            print(f"{'='*70}")
            print(f"  Start: {timestamps[0]}")
            print(f"  End: {timestamps[-1]}")
            print(f"  Current SOC: {current_state.current_soc_kwh:.2f} kWh ({current_state.current_soc_percent:.1f}%)")
            print(f"  Monthly peak: {current_state.current_monthly_peak_kw:.1f} kW")
            print(f"  Days remaining: {current_state.days_remaining_in_month}")

        # Get energy costs
        c_import, c_export = self.get_energy_costs(timestamps, spot_prices)

        # Calculate adaptive peak penalty coefficient
        # Use first forecasted grid import as "current" (conservative)
        P_grid_forecast_initial = load_consumption[0] - pv_production[0]  # Net import
        P_grid_forecast_24h = load_consumption - pv_production  # Approximate forecast

        adaptive_peak_penalty = current_state.calculate_adaptive_peak_penalty(
            current_grid_import_kw=max(0, P_grid_forecast_initial),
            forecast_grid_import_24h=np.maximum(0, P_grid_forecast_24h)
        )

        if verbose:
            print(f"  Adaptive peak penalty: {adaptive_peak_penalty:.2f} NOK/kW")

        # Calculate baseline tariff cost for current monthly peak
        z_current = self._allocate_to_brackets(current_state.current_monthly_peak_kw)
        baseline_tariff_cost = self._calculate_tariff_cost(z_current)

        if verbose:
            print(f"  Current monthly peak: {current_state.current_monthly_peak_kw:.2f} kW")
            print(f"  Baseline tariff cost: {baseline_tariff_cost:.2f} NOK/month")

        # LP Problem Setup
        # Decision variables: [P_charge, P_discharge, P_grid_import, P_grid_export, E_battery, P_curtail,
        #                      E_delta_pos, E_delta_neg, DOD_abs, DP_cyc, DP_total,
        #                      P_monthly_peak_new, z[0..N_trinn-1]]
        # Shape: (T, T, T, T, T, T, T, T, T, T, T, 1, N_trinn) = 11*T + 1 + N_trinn variables
        n_vars = 11 * T + 1 + self.N_trinn

        # Cost vector c
        # minimize: energy_cost + degradation_cost + peak_tariff_cost
        c = np.zeros(n_vars)

        # P_charge cost: 0 (just energy transfer)
        c[0:T] = 0

        # P_discharge cost: 0
        c[T:2*T] = 0

        # P_grid_import cost: c_import × Δt
        c[2*T:3*T] = c_import * self.timestep_hours

        # P_grid_export revenue: -c_export × Δt (negative = profit)
        c[3*T:4*T] = -c_export * self.timestep_hours

        # E_battery cost: 0 (state variable)
        c[4*T:5*T] = 0

        # P_curtail penalty: small cost to discourage unnecessary curtailment
        c[5*T:6*T] = 0.01  # 0.01 NOK/kWh penalty

        # E_delta_pos cost: 0 (intermediate variable)
        c[6*T:7*T] = 0

        # E_delta_neg cost: 0 (intermediate variable)
        c[7*T:8*T] = 0

        # DOD_abs cost: 0 (intermediate variable)
        c[8*T:9*T] = 0

        # DP_cyc cost: 0 (intermediate variable)
        c[9*T:10*T] = 0

        # DP_total cost: degradation cost per percent
        # Cost = (battery_cost_per_kwh * E_nom / eol_degradation_pct) NOK per % degradation
        degradation_cost_per_percent = (self.battery_cost_nok_per_kwh * self.E_nom) / self.eol_degradation_pct
        c[10*T:11*T] = degradation_cost_per_percent

        # P_monthly_peak_new: no direct cost (just used in constraints)
        c[11*T] = 0.0

        # Tariff bracket costs: c_trinn[i] for z[i]
        # Objective: Σ c_trinn[i] × z[i] - baseline_tariff_cost
        # The baseline offset doesn't affect optimization, only final cost calculation
        idx_z = 11*T + 1  # Start of z variables
        c[idx_z : idx_z + self.N_trinn] = self.c_trinn  # NOK/kW/month per bracket

        # Bounds
        bounds = []

        # P_charge: [0, P_max_charge]
        for t in range(T):
            bounds.append((0, self.P_max_charge))

        # P_discharge: [0, P_max_discharge]
        for t in range(T):
            bounds.append((0, self.P_max_discharge))

        # P_grid_import: [0, P_grid_import_limit]
        for t in range(T):
            bounds.append((0, self.P_grid_import_limit))

        # P_grid_export: [0, P_grid_export_limit]
        for t in range(T):
            bounds.append((0, self.P_grid_export_limit))

        # E_battery: [SOC_min × E_nom, SOC_max × E_nom]
        for t in range(T):
            bounds.append((self.SOC_min * self.E_nom, self.SOC_max * self.E_nom))

        # P_curtail: [0, infinity] (allow any curtailment needed)
        for t in range(T):
            bounds.append((0, None))

        # E_delta_pos: [0, E_nom] (max single-step energy change)
        for t in range(T):
            bounds.append((0, self.E_nom))

        # E_delta_neg: [0, E_nom] (max single-step energy change)
        for t in range(T):
            bounds.append((0, self.E_nom))

        # DOD_abs: [0, 1] (normalized depth of discharge)
        for t in range(T):
            bounds.append((0, 1))

        # DP_cyc: [0, eol_degradation_pct] (max cyclic degradation)
        for t in range(T):
            bounds.append((0, self.eol_degradation_pct))

        # DP_total: [0, eol_degradation_pct] (max total degradation)
        for t in range(T):
            bounds.append((0, self.eol_degradation_pct))

        # P_monthly_peak_new: [current_monthly_peak_kw, infinity]
        # Must be at least current peak (can't reduce retroactively)
        # Will be set to max(current_peak, max(P_grid_import[t])) by LP solver
        bounds.append((current_state.current_monthly_peak_kw, None))

        # Tariff bracket variables z[i]: [0, 1]
        # z[i] represents fill fraction of bracket i (0 = empty, 1 = full)
        # Match monthly LP formulation
        for i in range(self.N_trinn):
            bounds.append((0, 1))

        # Equality constraints (Ax = b)
        A_eq_rows = []
        b_eq_rows = []

        # Energy balance at each timestep: P_grid_import - P_grid_export + pv_production = load + (P_charge - P_discharge) + P_curtail
        # Rearrange: P_grid_import - P_grid_export - P_charge + P_discharge - P_curtail = load - pv_production
        for t in range(T):
            row = np.zeros(n_vars)
            row[2*T + t] = 1  # P_grid_import[t]
            row[3*T + t] = -1  # P_grid_export[t]
            row[0*T + t] = -1  # P_charge[t]
            row[1*T + t] = 1  # P_discharge[t]
            row[5*T + t] = -1  # P_curtail[t]
            A_eq_rows.append(row)
            b_eq_rows.append(load_consumption[t] - pv_production[t])

        # Battery dynamics: E[t+1] = E[t] + (P_charge[t] × η_charge - P_discharge[t] / η_discharge) × Δt
        # Rearrange: -E[t+1] + E[t] + P_charge[t] × η × Δt - P_discharge[t] / η × Δt = 0
        for t in range(T-1):
            row = np.zeros(n_vars)
            row[4*T + t + 1] = -1  # -E[t+1]
            row[4*T + t] = 1  # +E[t]
            row[0*T + t] = self.eta_charge * self.timestep_hours  # P_charge × η × Δt
            row[1*T + t] = -self.timestep_hours / self.eta_discharge  # -P_discharge / η × Δt
            A_eq_rows.append(row)
            b_eq_rows.append(0)

        # Initial condition: E[0] = E_initial
        row = np.zeros(n_vars)
        row[4*T + 0] = 1  # E[0]
        A_eq_rows.append(row)
        b_eq_rows.append(current_state.current_soc_kwh)

        # Peak definition: P_monthly_peak_new = Σ p_trinn[i] × z[i]
        # Rearrange: P_monthly_peak_new - Σ p_trinn[i] × z[i] = 0
        row = np.zeros(n_vars)
        row[11*T] = 1.0  # P_monthly_peak_new (shifted index)
        idx_z = 11*T + 1
        for i in range(self.N_trinn):
            row[idx_z + i] = -self.p_trinn[i]  # -p_trinn[i] × z[i]
        A_eq_rows.append(row)
        b_eq_rows.append(0)

        # Degradation equality constraints (3*T constraints)
        A_eq_degradation, b_eq_degradation = self._build_degradation_equality_constraints(
            T, n_vars, current_state.current_soc_kwh
        )
        A_eq_rows.extend(A_eq_degradation)
        b_eq_rows.extend(b_eq_degradation)

        A_eq = np.array(A_eq_rows)
        b_eq = np.array(b_eq_rows)

        # Inequality constraints (A_ub × x <= b_ub)
        A_ub_rows = []
        b_ub_rows = []

        # Peak tracking: P_monthly_peak_new >= P_grid_import[t] for all t
        # This forces the new peak to be at least the max grid import in this 24h window
        # Rearrange: P_grid_import[t] - P_monthly_peak_new <= 0
        for t in range(T):
            row = np.zeros(n_vars)
            row[2*T + t] = 1   # P_grid_import[t]
            row[11*T] = -1     # -P_monthly_peak_new (shifted index, scalar)
            A_ub_rows.append(row)
            b_ub_rows.append(0)  # RHS = 0

        # Ordered activation constraints: z[i] <= z[i-1] for i > 0
        # Ensures lower brackets fill first (like progressive tax brackets)
        # Rearrange: z[i] - z[i-1] <= 0
        idx_z = 11*T + 1  # Shifted index
        for i in range(1, self.N_trinn):
            row = np.zeros(n_vars)
            row[idx_z + i] = 1.0      # z[i]
            row[idx_z + i - 1] = -1.0  # -z[i-1]
            A_ub_rows.append(row)
            b_ub_rows.append(0)

        # Degradation inequality constraints (2*T constraints)
        A_ub_degradation, b_ub_degradation = self._build_degradation_inequality_constraints(T, n_vars)
        A_ub_rows.extend(A_ub_degradation)
        b_ub_rows.extend(b_ub_degradation)

        A_ub = np.array(A_ub_rows) if A_ub_rows else None
        b_ub = np.array(b_ub_rows) if b_ub_rows else None

        # Solve LP
        if verbose:
            print(f"\n  LP problem: {n_vars} variables, {len(A_eq_rows)} eq constraints, {len(A_ub_rows) if A_ub_rows else 0} ineq constraints")
            print(f"  Solving with HiGHS...")

        result = linprog(
            c=c,
            A_eq=A_eq,
            b_eq=b_eq,
            A_ub=A_ub,
            b_ub=b_ub,
            bounds=bounds,
            method='highs',
            options={'disp': verbose}
        )

        solve_time = time.time() - start_time

        if not result.success:
            if verbose:
                print(f"  ❌ Optimization failed: {result.message}")
            return RollingHorizonResult(
                P_charge=np.zeros(T),
                P_discharge=np.zeros(T),
                P_grid_import=np.zeros(T),
                P_grid_export=np.zeros(T),
                E_battery=np.zeros(T),
                P_curtail=np.zeros(T),
                E_delta_pos=np.zeros(T),
                E_delta_neg=np.zeros(T),
                DOD_abs=np.zeros(T),
                DP_cyc=np.zeros(T),
                DP_total=np.zeros(T),
                objective_value=float('inf'),
                energy_cost=0.0,
                peak_penalty_cost=0.0,
                peak_penalty_actual=0.0,
                objective_value_actual=float('inf'),
                degradation_cost=0.0,
                dp_cal_per_timestep=self.dp_cal_per_timestep,
                equivalent_cycles=0.0,
                success=False,
                message=result.message,
                solve_time_seconds=solve_time
            )

        # Extract solution
        x = result.x
        P_charge = x[0:T]
        P_discharge = x[T:2*T]
        P_grid_import = x[2*T:3*T]
        P_grid_export = x[3*T:4*T]
        E_battery = x[4*T:5*T]
        P_curtail = x[5*T:6*T]
        E_delta_pos = x[6*T:7*T]
        E_delta_neg = x[7*T:8*T]
        DOD_abs = x[8*T:9*T]
        DP_cyc = x[9*T:10*T]
        DP_total = x[10*T:11*T]
        P_monthly_peak_new = x[11*T]  # Scalar: consequential monthly peak after this 24h window

        # Extract bracket allocations
        idx_z = 11*T + 1  # Shifted index
        z_new = x[idx_z : idx_z + self.N_trinn]

        # Calculate cost breakdown
        energy_cost = np.sum(c_import * P_grid_import * self.timestep_hours - c_export * P_grid_export * self.timestep_hours)

        # Degradation cost: sum of degradation over 24h window
        degradation_cost = np.sum(degradation_cost_per_percent * DP_total)

        # Equivalent full cycles: sum of absolute depth of discharge
        equivalent_cycles = np.sum(DOD_abs)

        # Power tariff penalty: differential cost using bracketed tariff (progressive LP approximation)
        # LP uses progressive approximation: Cost_progressive = Σ c_trinn[i] × z[i]
        new_tariff_cost_progressive = self._calculate_tariff_cost(z_new)
        peak_penalty_cost_progressive = new_tariff_cost_progressive - baseline_tariff_cost

        # Calculate ACTUAL step function cost for reporting (post-processing)
        baseline_tariff_actual = self.config.tariff.get_power_cost(current_state.current_monthly_peak_kw)
        new_tariff_actual = self.config.tariff.get_power_cost(P_monthly_peak_new)
        peak_penalty_actual = new_tariff_actual - baseline_tariff_actual

        if verbose:
            print(f"\n  ✓ Optimization successful!")
            print(f"  Objective: {result.fun:,.2f} NOK")
            print(f"  Energy cost: {energy_cost:,.2f} NOK")
            print(f"  Degradation cost: {degradation_cost:,.2f} NOK")
            print(f"  Equivalent cycles (24h): {equivalent_cycles:.4f} cycles")
            print(f"  Peak demand: {current_state.current_monthly_peak_kw:.2f} kW → {P_monthly_peak_new:.2f} kW")
            print(f"  Baseline tariff (progressive): {baseline_tariff_cost:.2f} NOK/month")
            print(f"  New tariff (progressive): {new_tariff_cost_progressive:.2f} NOK/month")
            print(f"  Peak penalty (progressive): {peak_penalty_cost_progressive:,.2f} NOK")
            print(f"  ---")
            print(f"  Baseline tariff (actual step): {baseline_tariff_actual:.2f} NOK/month")
            print(f"  New tariff (actual step): {new_tariff_actual:.2f} NOK/month")
            print(f"  Peak penalty (actual step): {peak_penalty_actual:,.2f} NOK")
            print(f"  Solve time: {solve_time:.3f} seconds")
            print(f"  Next action: {P_charge[0] - P_discharge[0]:.2f} kW")
            print(f"  Final SOC: {E_battery[-1]:.2f} kWh ({E_battery[-1]/self.E_nom*100:.1f}%)")

        # Calculate true objective: energy cost + degradation cost + marginal peak penalty
        # Progressive LP uses approximate tariff for optimization
        true_objective_progressive = energy_cost + degradation_cost + peak_penalty_cost_progressive

        # Actual objective with step function tariff for reporting
        true_objective_actual = energy_cost + degradation_cost + peak_penalty_actual

        return RollingHorizonResult(
            P_charge=P_charge,
            P_discharge=P_discharge,
            P_grid_import=P_grid_import,
            P_grid_export=P_grid_export,
            E_battery=E_battery,
            P_curtail=P_curtail,
            E_delta_pos=E_delta_pos,
            E_delta_neg=E_delta_neg,
            DOD_abs=DOD_abs,
            DP_cyc=DP_cyc,
            DP_total=DP_total,
            objective_value=true_objective_progressive,  # Progressive LP cost
            energy_cost=energy_cost,
            peak_penalty_cost=peak_penalty_cost_progressive,  # Progressive LP penalty
            peak_penalty_actual=peak_penalty_actual,  # Actual step function penalty
            objective_value_actual=true_objective_actual,  # Actual total cost
            degradation_cost=degradation_cost,
            dp_cal_per_timestep=self.dp_cal_per_timestep,
            equivalent_cycles=equivalent_cycles,
            success=True,
            message="Optimization successful",
            solve_time_seconds=solve_time
        )
