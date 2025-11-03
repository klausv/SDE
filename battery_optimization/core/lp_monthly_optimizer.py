"""
Linear Programming Monthly Battery Optimizer

Implements LP-based battery optimization for one month at a time with:
- Energy balance constraints
- Battery SOC (State of Charge) limits and dynamics
- Charge/discharge power limits
- Peak power tracking with linear incremental formulation
- Power tariff cost modeling

Uses scipy.optimize.linprog with HiGHS solver for fast, reliable LP solving.
"""

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MonthlyLPResult:
    """Results from monthly LP optimization"""
    # Decision variables
    P_charge: np.ndarray          # Charging power [kW]
    P_discharge: np.ndarray       # Discharging power [kW]
    P_grid_import: np.ndarray     # Grid import [kW]
    P_grid_export: np.ndarray     # Grid export [kW]
    E_battery: np.ndarray         # Battery energy [kWh]
    P_curtail: np.ndarray         # Solar curtailment [kW]

    # Peak power variables
    P_peak: float                 # Monthly peak power [kW]
    z_trinn: np.ndarray           # Trinn activation levels [0-1]

    # Cost breakdown
    objective_value: float        # Total objective function value [NOK]
    energy_cost: float            # Energy cost component [NOK]
    power_cost: float             # Power tariff component [NOK]

    # Status
    success: bool
    message: str
    E_battery_final: float        # Final SOC for next month [kWh]

    # Degradation variables (LFP battery degradation model) - with defaults
    DOD_abs: Optional[np.ndarray] = None      # Absolute depth of discharge per timestep [0-1]
    DP_cyc: Optional[np.ndarray] = None       # Cyclic degradation per timestep [%]
    DP_cal: Optional[float] = None            # Calendric degradation per timestep [%]
    DP_total: Optional[np.ndarray] = None     # Total degradation per timestep [%]
    degradation_cost: float = 0.0             # Battery degradation cost component [NOK]


class MonthlyLPOptimizer:
    """
    LP-based battery optimizer for one month with power tariff.

    Formulation:
    - Decision variables: P_charge, P_discharge, P_grid_import, P_grid_export, E_battery, P_peak, z[]
    - Objective: minimize total cost (energy + power tariff)
    - Constraints: energy balance, battery dynamics, SOC limits, power limits, peak tracking
    """

    def __init__(self, config, resolution='PT60M', battery_kwh=None, battery_kw=None):
        """
        Initialize optimizer with system configuration and time resolution.

        Args:
            config: System configuration object with battery, tariff, and system parameters
            resolution: Time resolution - 'PT60M' (hourly) or 'PT15M' (15-minute)
            battery_kwh: Battery energy capacity [kWh] (optional, overrides config)
            battery_kw: Battery power rating [kW] (optional, overrides config)
        """
        # Validate resolution
        if resolution not in ['PT60M', 'PT15M']:
            raise ValueError(
                f"Resolution must be 'PT60M' or 'PT15M', got '{resolution}'"
            )

        self.config = config
        self.resolution = resolution

        # Calculate timestep in hours for battery dynamics
        self.timestep_hours = 0.25 if resolution == 'PT15M' else 1.0

        print(f"Initializing LP optimizer with {resolution} resolution")
        print(f"  Timestep: {self.timestep_hours} hours")

        # Battery parameters (with optional override)
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

        # Inverter efficiency
        solar_config = config.solar if hasattr(config, 'solar') else None
        self.eta_inv = solar_config.inverter_efficiency if solar_config else 0.98

        # Grid limits (both import and export)
        self.P_grid_import_limit = solar_config.grid_import_limit_kw if (solar_config and hasattr(solar_config, 'grid_import_limit_kw')) else 70.0
        self.P_grid_export_limit = solar_config.grid_export_limit_kw if solar_config else 70.0

        # Degradation modeling parameters (LFP battery)
        self.degradation_enabled = False
        if battery_config and hasattr(battery_config, 'degradation'):
            degradation_config = battery_config.degradation
            self.degradation_enabled = degradation_config.enabled

            if self.degradation_enabled:
                # LFP degradation parameters
                self.rho_constant = degradation_config.rho_constant  # %/cycle
                self.dp_cal_per_timestep = degradation_config.dp_cal_per_hour * self.timestep_hours  # %/timestep
                self.C_bat = battery_config.get_battery_cost()  # NOK/kWh (battery cells only)

                print(f"\n{'='*70}")
                print(f"Battery Degradation Modeling: ENABLED (LFP)")
                print(f"{'='*70}")
                print(f"  Cycle life: {degradation_config.cycle_life_full_dod:,} cycles @ 100% DOD")
                print(f"  Calendar life: {degradation_config.calendar_life_years:.1f} years")
                print(f"  ρ_constant: {self.rho_constant:.6f} %/cycle")
                print(f"  DP_cal: {self.dp_cal_per_timestep:.6f} %/timestep")
                print(f"  C_bat: {self.C_bat:,.0f} NOK/kWh (battery cells only)")
                print(f"{'='*70}\n")
            else:
                print(f"Battery Degradation Modeling: DISABLED")
        else:
            print(f"Battery Degradation Modeling: DISABLED (no degradation config)")

        # Setup power tariff data (convert to incremental formulation)
        self.setup_power_tariff_incremental()

    def setup_power_tariff_incremental(self):
        """
        Convert config power brackets to incremental formulation:
        - p_trinn[i]: Width of bracket i [kW]
        - c_trinn[i]: Incremental cost for bracket i [NOK/month]
        """
        tariff_config = self.config.tariff if hasattr(self.config, 'tariff') else None
        if not tariff_config or not hasattr(tariff_config, 'power_brackets'):
            # Default brackets if not in config
            brackets = [
                (0, 2, 136),
                (2, 5, 232),
                (5, 10, 372),
                (10, 15, 572),
                (15, 20, 772),
                (20, 25, 972),
                (25, 50, 1772),
                (50, 75, 2572),
                (75, 100, 3372),
                (100, 200, 5600)
            ]
        else:
            brackets = tariff_config.power_brackets

        self.N_trinn = len(brackets)
        self.p_trinn = []
        self.c_trinn = []

        prev_power = 0
        prev_cost = 0

        for (from_kw, to_kw, cost) in brackets:
            # Width of this bracket
            width = to_kw - from_kw if to_kw != float('inf') else 100  # Cap last bracket
            self.p_trinn.append(width)

            # Incremental cost (difference from previous bracket)
            incremental_cost = cost - prev_cost
            self.c_trinn.append(incremental_cost)

            prev_power = to_kw
            prev_cost = cost

        self.p_trinn = np.array(self.p_trinn)
        self.c_trinn = np.array(self.c_trinn)

        print(f"Power tariff: {self.N_trinn} brackets configured")
        print(f"  p_trinn: {self.p_trinn}")
        print(f"  c_trinn: {self.c_trinn}")

    def get_energy_costs(self, timestamps: pd.DatetimeIndex, spot_prices: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate energy import costs and export revenues for each timestep.

        Args:
            timestamps: DatetimeIndex for the month
            spot_prices: Spot prices [NOK/kWh]

        Returns:
            (c_import, c_export): Cost arrays per timestep
        """
        tariff_config = self.config.tariff if hasattr(self.config, 'tariff') else None

        T = len(timestamps)
        c_import = np.zeros(T)
        c_export = np.zeros(T)

        for t, ts in enumerate(timestamps):
            # Convert numpy datetime64 to pandas Timestamp if needed
            if isinstance(ts, np.datetime64):
                ts = pd.Timestamp(ts)

            # Energy tariff (day/night)
            if tariff_config and tariff_config.is_peak_hours(ts):
                energy_tariff = tariff_config.energy_peak
            elif tariff_config:
                energy_tariff = tariff_config.energy_offpeak
            else:
                energy_tariff = 0.296 if (6 <= ts.hour < 22 and ts.weekday() < 5) else 0.176

            # Consumption tax (seasonal)
            if tariff_config and hasattr(tariff_config, 'consumption_tax_monthly'):
                cons_tax = tariff_config.consumption_tax_monthly.get(ts.month, 0.15)
            else:
                cons_tax = 0.15  # Default

            # Total import cost
            c_import[t] = spot_prices[t] + energy_tariff + cons_tax

            # Export revenue (spot price + innmatingstariff)
            # Total export revenue = spot price + 0.04 kr/kWh feed-in tariff
            c_export[t] = spot_prices[t] + 0.04

        return c_import, c_export

    def optimize_month(self,
                       month_idx: int,
                       pv_production: np.ndarray,
                       load_consumption: np.ndarray,
                       spot_prices: np.ndarray,
                       timestamps: pd.DatetimeIndex,
                       E_initial: float = None) -> MonthlyLPResult:
        """
        Solve LP optimization for one month.

        Args:
            month_idx: Month number (1-12)
            pv_production: PV production [kW], shape (T,)
            load_consumption: Load consumption [kW], shape (T,)
            spot_prices: Spot prices [NOK/kWh], shape (T,)
            timestamps: DatetimeIndex for the month
            E_initial: Initial battery energy [kWh], defaults to 50% SOC

        Returns:
            MonthlyLPResult with optimal schedule and costs
        """
        T = len(pv_production)

        if E_initial is None:
            E_initial = 0.5 * self.E_nom

        print(f"\n{'='*70}")
        print(f"Optimizing Month {month_idx} - LP Formulation ({self.resolution})")
        print(f"{'='*70}")
        print(f"Time horizon: {T} intervals ({T * self.timestep_hours:.0f} hours)")
        if self.E_nom > 0:
            print(f"Initial battery energy: {E_initial:.2f} kWh ({E_initial/self.E_nom*100:.1f}% SOC)")
        else:
            print(f"No battery (reference scenario)")
        print(f"Resolution: {self.resolution} (Δt = {self.timestep_hours} hours)")

        # Get energy costs
        c_import, c_export = self.get_energy_costs(timestamps, spot_prices)

        # Build LP problem
        # Variables depend on degradation modeling:
        # - Without degradation: [P_charge, P_discharge, P_grid_import, P_grid_export, E_battery, P_curtail, P_peak, z]
        # - With degradation: [... E_battery, E_delta_pos, E_delta_neg, DOD_abs, DP_cyc, DP, P_curtail, P_peak, z]
        # P_curtail represents solar curtailment (dumped energy) to ensure feasibility
        if self.degradation_enabled:
            n_vars = 10*T + T + 1 + self.N_trinn  # Added T for P_curtail
        else:
            n_vars = 5*T + T + 1 + self.N_trinn  # Added T for P_curtail

        # Cost vector c
        # IMPORTANT: Scale energy costs by timestep_hours (kW * kr/kWh * hours = kr)
        c = np.zeros(n_vars)
        c[2*T:3*T] = c_import * self.timestep_hours  # P_grid_import costs [kr]
        c[3*T:4*T] = -c_export * self.timestep_hours  # P_grid_export revenue [kr]
        # c[5*T:6*T] = 0.0  # P_curtail has zero cost (dumped energy)

        if self.degradation_enabled:
            # Degradation cost: DP[t] in % → convert to NOK
            # Cost = C_bat [NOK/kWh] × E_nom [kWh] × DP[t] / 100
            c[9*T:10*T] = self.C_bat * self.E_nom / 100.0
            # P_curtail at index 10*T:11*T (already zero from np.zeros)
            idx_peak = 11*T  # P_peak after curtailment
            idx_z = 11*T + 1  # z_trinn after P_peak
        else:
            idx_peak = 6*T  # P_peak after curtailment (no degradation vars)
            idx_z = 6*T + 1  # z_trinn after P_peak

        c[idx_z:idx_z + self.N_trinn] = self.c_trinn  # Power tariff costs [kr/month]

        # Bounds (use helper method)
        bounds = self._build_bounds(T)

        # Build constraint matrices
        A_eq, b_eq = self._build_equality_constraints(T, pv_production, load_consumption, E_initial)
        A_ub, b_ub = self._build_inequality_constraints(T)

        # Add degradation constraints if enabled
        if self.degradation_enabled:
            A_eq_deg, b_eq_deg, A_ub_deg, b_ub_deg = self._build_degradation_constraints(T, E_initial)

            # Combine constraints
            A_eq = np.vstack([A_eq, A_eq_deg])
            b_eq = np.concatenate([b_eq, b_eq_deg])
            A_ub = np.vstack([A_ub, A_ub_deg])
            b_ub = np.concatenate([b_ub, b_ub_deg])

        print(f"LP problem size: {n_vars} variables, {len(b_eq)} equality constraints, {len(b_ub)} inequality constraints")

        # Solve LP
        print("Solving LP with HiGHS...")
        result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                         bounds=bounds, method='highs', options={'disp': True})

        if not result.success:
            print(f"⚠ LP optimization failed: {result.message}")
            return MonthlyLPResult(
                P_charge=np.zeros(T),
                P_discharge=np.zeros(T),
                P_grid_import=load_consumption,
                P_grid_export=np.zeros(T),
                E_battery=np.full(T, E_initial),
                P_peak=0,
                z_trinn=np.zeros(self.N_trinn),
                objective_value=float('inf'),
                energy_cost=0,
                power_cost=0,
                success=False,
                message=result.message,
                E_battery_final=E_initial
            )

        # Extract solution
        x = result.x
        P_charge = x[0:T]
        P_discharge = x[T:2*T]
        P_grid_import = x[2*T:3*T]
        P_grid_export = x[3*T:4*T]
        E_battery = x[4*T:5*T]

        if self.degradation_enabled:
            # Extract degradation variables
            E_delta_pos = x[5*T:6*T]
            E_delta_neg = x[6*T:7*T]
            DOD_abs = x[7*T:8*T]
            DP_cyc = x[8*T:9*T]
            DP = x[9*T:10*T]
            P_curtail = x[10*T:11*T]
            P_peak = x[11*T]
            z_trinn = x[11*T+1:11*T+1+self.N_trinn]

            # Calculate degradation cost
            degradation_cost = np.sum(DP * self.C_bat * self.E_nom / 100.0)
        else:
            DOD_abs = None
            DP_cyc = None
            DP = None
            P_curtail = x[5*T:6*T]
            P_peak = x[6*T]
            z_trinn = x[6*T+1:6*T+1+self.N_trinn]
            degradation_cost = 0.0

        # Calculate cost breakdown
        # Energy cost must be scaled by timestep_hours (0.25 for PT15M, 1.0 for PT60M)
        energy_cost = np.sum((c_import * P_grid_import - c_export * P_grid_export) * self.timestep_hours)
        power_cost = np.sum(self.c_trinn * z_trinn)

        print(f"✓ Optimization successful!")
        print(f"  Objective value: {result.fun:,.2f} NOK")
        print(f"  Energy cost: {energy_cost:,.2f} NOK")
        print(f"  Power cost: {power_cost:,.2f} NOK")
        if self.degradation_enabled:
            print(f"  Degradation cost: {degradation_cost:,.2f} NOK")
            print(f"  Total degradation: {np.sum(DP):.4f}%")
            print(f"  Cyclic degradation: {np.sum(DP_cyc):.4f}%")
            print(f"  Calendar degradation: {self.dp_cal_per_timestep * T:.4f}%")

            # Validate equivalent cycles
            equivalent_cycles = np.sum(DOD_abs)
            cycles_per_year = equivalent_cycles * (8760.0 / T)  # Extrapolate to annual

            print(f"  Equivalent cycles (this period): {equivalent_cycles:.1f}")
            print(f"  Extrapolated annual rate: {cycles_per_year:.0f} cycles/year")

            # Warnings
            if cycles_per_year > 400:
                print(f"  ⚠️  WARNING: Very high cycle rate!")
                print(f"      Expected for peak shaving: 100-200 cycles/year")
                print(f"      Current rate suggests aggressive arbitrage trading")

            # Compare cyclic vs calendar
            cyclic_monthly = np.sum(DP_cyc)
            calendar_monthly = self.dp_cal_per_timestep * T

            if cyclic_monthly < calendar_monthly * 0.5:
                print(f"  ⚠️  Battery under-utilized (calendar degradation dominates)")
            elif cyclic_monthly > calendar_monthly * 5:
                print(f"  ⚠️  Battery over-utilized (cyclic degradation dominates)")

        print(f"  Peak power: {P_peak:.2f} kW")
        print(f"  Final SOC: {E_battery[-1]/self.E_nom*100:.1f}%")

        # Report curtailment if any
        total_curtailment = np.sum(P_curtail) * self.timestep_hours
        if total_curtailment > 0.1:  # Only report if significant
            print(f"  Solar curtailment: {total_curtailment:.1f} kWh ({total_curtailment/(np.sum(pv_production)*self.timestep_hours)*100:.1f}% of solar)")

        return MonthlyLPResult(
            P_charge=P_charge,
            P_discharge=P_discharge,
            P_grid_import=P_grid_import,
            P_grid_export=P_grid_export,
            E_battery=E_battery,
            P_curtail=P_curtail,
            P_peak=P_peak,
            z_trinn=z_trinn,
            DOD_abs=DOD_abs,
            DP_cyc=DP_cyc,
            DP_cal=self.dp_cal_per_timestep if self.degradation_enabled else None,
            DP_total=DP,
            objective_value=result.fun,
            energy_cost=energy_cost,
            power_cost=power_cost,
            degradation_cost=degradation_cost,
            success=True,
            message="Optimal solution found",
            E_battery_final=E_battery[-1]
        )

    def get_power_tariff_peak(self, P_grid_import: np.ndarray, timestamps: pd.DatetimeIndex) -> float:
        """
        Calculate the peak power for tariff billing with resolution awareness.

        For hourly resolution (PT60M):
            Returns max of P_grid_import directly

        For 15-minute resolution (PT15M):
            Aggregates to hourly peaks first (max of each 4 consecutive intervals),
            then returns the maximum hourly peak

        Args:
            P_grid_import: Grid import power [kW] at optimization resolution
            timestamps: Corresponding timestamps

        Returns:
            Peak power [kW] for power tariff calculation
        """
        if self.resolution == 'PT60M':
            # Already hourly - return max directly
            return P_grid_import.max()

        # 15-minute resolution - aggregate to hourly peaks
        from core.time_aggregation import aggregate_15min_to_hourly_peak

        hourly_peaks = aggregate_15min_to_hourly_peak(P_grid_import, timestamps)
        return hourly_peaks.max() if isinstance(hourly_peaks, np.ndarray) else hourly_peaks.values.max()

    def _build_equality_constraints(self, T: int, pv: np.ndarray, load: np.ndarray,
                                    E_initial: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build equality constraint matrices A_eq x = b_eq for:
        1. Energy balance at each timestep (now includes P_curtail)
        2. Battery dynamics at each timestep
        3. P_peak definition via z_trinn

        Variable count adapts based on degradation_enabled flag.
        """
        if self.degradation_enabled:
            n_vars = 10*T + T + 1 + self.N_trinn  # Added T for P_curtail
            idx_curtail = 10*T
            idx_peak = 11*T
            idx_z = 11*T + 1
        else:
            n_vars = 5*T + T + 1 + self.N_trinn  # Added T for P_curtail
            idx_curtail = 5*T
            idx_peak = 6*T
            idx_z = 6*T + 1

        n_constraints = 2*T + 1

        A_eq = np.zeros((n_constraints, n_vars))
        b_eq = np.zeros(n_constraints)

        row = 0

        # Energy balance: Ppv + Pgrid_import + η_inv*Pdischarge = Pload + Pgrid_export + Pcharge/η_inv + Pcurtail
        # Pcurtail allows dumping excess solar when battery full and grid export limited
        for t in range(T):
            A_eq[row, t] = -1.0 / self.eta_inv  # P_charge[t]
            A_eq[row, T+t] = self.eta_inv  # P_discharge[t]
            A_eq[row, 2*T+t] = 1.0  # P_grid_import[t]
            A_eq[row, 3*T+t] = -1.0  # P_grid_export[t]
            A_eq[row, idx_curtail+t] = -1.0  # P_curtail[t] (dump excess)
            b_eq[row] = load[t] - pv[t]
            row += 1

        # Battery dynamics: E[t] = E[t-1] + η_charge*P_charge[t]*Δt - P_discharge[t]/η_discharge*Δt
        # where Δt = timestep_hours (0.25 for 15-min, 1.0 for hourly)
        for t in range(T):
            A_eq[row, t] = -self.eta_charge * self.timestep_hours  # P_charge[t] * Δt
            A_eq[row, T+t] = (1.0 / self.eta_discharge) * self.timestep_hours  # P_discharge[t] * Δt
            A_eq[row, 4*T+t] = 1.0  # E_battery[t]
            if t > 0:
                A_eq[row, 4*T+(t-1)] = -1.0  # E_battery[t-1]
            b_eq[row] = E_initial if t == 0 else 0
            row += 1

        # P_peak definition: P_peak = sum(p_trinn[i] * z[i])
        A_eq[row, idx_peak] = 1.0  # P_peak
        for i in range(self.N_trinn):
            A_eq[row, idx_z+i] = -self.p_trinn[i]  # -p_trinn[i] * z[i]
        b_eq[row] = 0
        row += 1

        return A_eq, b_eq

    def _build_inequality_constraints(self, T: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build inequality constraint matrices A_ub x <= b_ub for:
        1. Peak tracking: P_peak >= P_grid_import[t] for all t
        2. Ordered z activation: z[i] <= z[i-1]

        Variable count adapts based on degradation_enabled flag.
        """
        if self.degradation_enabled:
            n_vars = 10*T + T + 1 + self.N_trinn  # Added T for P_curtail
            idx_peak = 11*T
            idx_z = 11*T + 1
        else:
            n_vars = 5*T + T + 1 + self.N_trinn  # Added T for P_curtail
            idx_peak = 6*T
            idx_z = 6*T + 1

        n_constraints = T + (self.N_trinn - 1)

        A_ub = np.zeros((n_constraints, n_vars))
        b_ub = np.zeros(n_constraints)

        row = 0

        # Peak tracking: -P_peak + P_grid_import[t] <= 0  =>  P_peak >= P_grid_import[t]
        for t in range(T):
            A_ub[row, 2*T+t] = 1.0  # P_grid_import[t]
            A_ub[row, idx_peak] = -1.0  # -P_peak
            b_ub[row] = 0
            row += 1

        # Ordered activation: z[i] - z[i-1] <= 0  =>  z[i] <= z[i-1]
        for i in range(1, self.N_trinn):
            A_ub[row, idx_z+i] = 1.0  # z[i]
            A_ub[row, idx_z+(i-1)] = -1.0  # -z[i-1]
            b_ub[row] = 0
            row += 1

        return A_ub, b_ub

    def _build_degradation_constraints(self, T: int, E_initial: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Build degradation constraint matrices for LP (LFP battery model).

        Implements Korpås degradation model with LP formulation:
        1. Energy delta decomposition: E_delta_pos - E_delta_neg = ΔE
        2. DOD calculation: DOD_abs × E_nom = E_delta_pos + E_delta_neg
        3. Cyclic degradation: DP_cyc = ρ × DOD_abs
        4. Max operator: DP ≥ max(DP_cyc, DP_cal)

        Variable indexing for degradation-enabled LP (10*T + T + 1 + N_trinn):
        - [0:T]: P_charge
        - [T:2T]: P_discharge
        - [2T:3T]: P_grid_import
        - [3T:4T]: P_grid_export
        - [4T:5T]: E_battery
        - [5T:6T]: E_delta_pos (NEW)
        - [6T:7T]: E_delta_neg (NEW)
        - [7T:8T]: DOD_abs (NEW)
        - [8T:9T]: DP_cyc (NEW)
        - [9T:10T]: DP (NEW)
        - [10T:11T]: P_curtail (NEW - allows dumping excess solar)
        - [11T]: P_peak
        - [11T+1:11T+1+N_trinn]: z_trinn

        Args:
            T: Number of timesteps
            E_initial: Initial battery energy [kWh]

        Returns:
            (A_eq_deg, b_eq_deg, A_ub_deg, b_ub_deg): Constraint matrices
        """
        n_vars = 10*T + T + 1 + self.N_trinn  # Added T for P_curtail

        # Equality constraints: 3*T (delta decomp + DOD calc + cyclic deg)
        A_eq_deg = np.zeros((3*T, n_vars))
        b_eq_deg = np.zeros(3*T)

        # Inequality constraints: 2*T (DP ≥ DP_cyc, DP ≥ DP_cal)
        A_ub_deg = np.zeros((2*T, n_vars))
        b_ub_deg = np.zeros(2*T)

        row_eq = 0
        row_ub = 0

        for t in range(T):
            # 1. Energy delta decomposition: E_delta_pos[t] - E_delta_neg[t] = E[t] - E[t-1]
            A_eq_deg[row_eq, 5*T + t] = 1.0       # E_delta_pos[t]
            A_eq_deg[row_eq, 6*T + t] = -1.0      # -E_delta_neg[t]
            A_eq_deg[row_eq, 4*T + t] = -1.0      # -E[t]
            if t > 0:
                A_eq_deg[row_eq, 4*T + (t-1)] = 1.0   # +E[t-1]
                b_eq_deg[row_eq] = 0
            else:
                # t=0: E_delta_pos[0] - E_delta_neg[0] = E[0] - E_initial
                b_eq_deg[row_eq] = -E_initial
            row_eq += 1

            # 2. DOD calculation: DOD_abs[t] × E_nom - E_delta_pos[t] - E_delta_neg[t] = 0
            A_eq_deg[row_eq, 7*T + t] = self.E_nom    # DOD_abs[t] × E_nom
            A_eq_deg[row_eq, 5*T + t] = -1.0          # -E_delta_pos[t]
            A_eq_deg[row_eq, 6*T + t] = -1.0          # -E_delta_neg[t]
            b_eq_deg[row_eq] = 0
            row_eq += 1

            # 3. Cyclic degradation: DP_cyc[t] - ρ_constant × DOD_abs[t] = 0
            A_eq_deg[row_eq, 8*T + t] = 1.0                   # DP_cyc[t]
            A_eq_deg[row_eq, 7*T + t] = -self.rho_constant    # -ρ × DOD_abs[t]
            b_eq_deg[row_eq] = 0
            row_eq += 1

            # 4a. DP[t] ≥ DP_cyc[t]  →  -DP[t] + DP_cyc[t] ≤ 0
            A_ub_deg[row_ub, 9*T + t] = -1.0      # -DP[t]
            A_ub_deg[row_ub, 8*T + t] = 1.0       # +DP_cyc[t]
            b_ub_deg[row_ub] = 0
            row_ub += 1

            # 4b. DP[t] ≥ DP_cal  →  -DP[t] ≤ -DP_cal
            A_ub_deg[row_ub, 9*T + t] = -1.0
            b_ub_deg[row_ub] = -self.dp_cal_per_timestep
            row_ub += 1

        return A_eq_deg, b_eq_deg, A_ub_deg, b_ub_deg

    def _build_bounds(self, T: int) -> list:
        """
        Build variable bounds for LP problem.

        Bounds depend on whether degradation modeling is enabled.

        Args:
            T: Number of timesteps

        Returns:
            List of (lower, upper) bounds for each variable
        """
        bounds = []

        # P_charge bounds
        for _ in range(T):
            bounds.append((0, self.P_max_charge))

        # P_discharge bounds
        for _ in range(T):
            bounds.append((0, self.P_max_discharge))

        # P_grid_import bounds
        for _ in range(T):
            bounds.append((0, self.P_grid_import_limit))

        # P_grid_export bounds
        for _ in range(T):
            bounds.append((0, self.P_grid_export_limit))

        # E_battery bounds
        for _ in range(T):
            bounds.append((self.SOC_min * self.E_nom, self.SOC_max * self.E_nom))

        if self.degradation_enabled:
            # E_delta_pos bounds (unbounded positive, but limited by E_nom change)
            for _ in range(T):
                bounds.append((0, self.E_nom))

            # E_delta_neg bounds (unbounded positive, but limited by E_nom change)
            for _ in range(T):
                bounds.append((0, self.E_nom))

            # DOD_abs bounds (0 to 1.0 = 100% DOD)
            for _ in range(T):
                bounds.append((0, 1.0))

            # DP_cyc bounds (0 to ρ_constant = max degradation per full cycle)
            for _ in range(T):
                bounds.append((0, self.rho_constant))

            # DP bounds (0 to reasonable maximum)
            # Maximum is the larger of: max cyclic degradation or 2× calendar degradation
            max_dp = max(self.rho_constant, self.dp_cal_per_timestep * 2)
            for _ in range(T):
                bounds.append((0, max_dp))

        # P_curtail bounds (can dump unlimited solar curtailment)
        for _ in range(T):
            bounds.append((0, None))  # No upper limit on curtailment

        # P_peak bounds
        bounds.append((0, None))

        # z_trinn bounds (0 to 1, continuous relaxation)
        for _ in range(self.N_trinn):
            bounds.append((0, 1))

        return bounds
