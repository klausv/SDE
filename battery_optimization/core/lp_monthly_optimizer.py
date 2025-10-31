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


class MonthlyLPOptimizer:
    """
    LP-based battery optimizer for one month with power tariff.

    Formulation:
    - Decision variables: P_charge, P_discharge, P_grid_import, P_grid_export, E_battery, P_peak, z[]
    - Objective: minimize total cost (energy + power tariff)
    - Constraints: energy balance, battery dynamics, SOC limits, power limits, peak tracking
    """

    def __init__(self, config):
        """
        Initialize optimizer with system configuration.

        Args:
            config: System configuration object with battery, tariff, and system parameters
        """
        self.config = config

        # Battery parameters
        self.E_nom = config.battery_capacity_kwh if hasattr(config, 'battery_capacity_kwh') else 100.0
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

        # Grid limit
        self.P_grid_limit = solar_config.grid_export_limit_kw if solar_config else 77.0

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

            # Export revenue (feed-in tariff)
            c_export[t] = 0.04  # Fixed feed-in tariff

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
        print(f"Optimizing Month {month_idx} - LP Formulation")
        print(f"{'='*70}")
        print(f"Time horizon: {T} hours")
        print(f"Initial battery energy: {E_initial:.2f} kWh ({E_initial/self.E_nom*100:.1f}% SOC)")

        # Get energy costs
        c_import, c_export = self.get_energy_costs(timestamps, spot_prices)

        # Build LP problem
        # Variables: [P_charge[0:T], P_discharge[0:T], P_grid_import[0:T], P_grid_export[0:T],
        #             E_battery[0:T], P_peak, z[0:N_trinn]]
        n_vars = 5*T + 1 + self.N_trinn

        # Cost vector c
        c = np.zeros(n_vars)
        c[2*T:3*T] = c_import  # P_grid_import costs
        c[3*T:4*T] = -c_export  # P_grid_export revenue (negative cost)
        c[5*T+1:5*T+1+self.N_trinn] = self.c_trinn  # Power tariff costs

        # Bounds
        bounds = []
        # P_charge
        for _ in range(T):
            bounds.append((0, self.P_max_charge))
        # P_discharge
        for _ in range(T):
            bounds.append((0, self.P_max_discharge))
        # P_grid_import
        for _ in range(T):
            bounds.append((0, self.P_grid_limit))
        # P_grid_export
        for _ in range(T):
            bounds.append((0, None))
        # E_battery
        for _ in range(T):
            bounds.append((self.SOC_min * self.E_nom, self.SOC_max * self.E_nom))
        # P_peak
        bounds.append((0, None))
        # z[i]
        for _ in range(self.N_trinn):
            bounds.append((0, 1))

        # Build constraint matrices
        A_eq, b_eq = self._build_equality_constraints(T, pv_production, load_consumption, E_initial)
        A_ub, b_ub = self._build_inequality_constraints(T)

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
        P_peak = x[5*T]
        z_trinn = x[5*T+1:5*T+1+self.N_trinn]

        # Calculate cost breakdown
        energy_cost = np.sum(c_import * P_grid_import - c_export * P_grid_export)
        power_cost = np.sum(self.c_trinn * z_trinn)

        print(f"✓ Optimization successful!")
        print(f"  Objective value: {result.fun:,.2f} NOK")
        print(f"  Energy cost: {energy_cost:,.2f} NOK")
        print(f"  Power cost: {power_cost:,.2f} NOK")
        print(f"  Peak power: {P_peak:.2f} kW")
        print(f"  Final SOC: {E_battery[-1]/self.E_nom*100:.1f}%")

        return MonthlyLPResult(
            P_charge=P_charge,
            P_discharge=P_discharge,
            P_grid_import=P_grid_import,
            P_grid_export=P_grid_export,
            E_battery=E_battery,
            P_peak=P_peak,
            z_trinn=z_trinn,
            objective_value=result.fun,
            energy_cost=energy_cost,
            power_cost=power_cost,
            success=True,
            message="Optimal solution found",
            E_battery_final=E_battery[-1]
        )

    def _build_equality_constraints(self, T: int, pv: np.ndarray, load: np.ndarray,
                                    E_initial: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build equality constraint matrices A_eq x = b_eq for:
        1. Energy balance at each timestep
        2. Battery dynamics at each timestep
        3. P_peak definition via z_trinn
        """
        n_vars = 5*T + 1 + self.N_trinn
        n_constraints = 2*T + 1

        A_eq = np.zeros((n_constraints, n_vars))
        b_eq = np.zeros(n_constraints)

        row = 0

        # Energy balance: Ppv + Pgrid_import + η_inv*Pdischarge = Pload + Pgrid_export + Pcharge/η_inv
        for t in range(T):
            A_eq[row, t] = -1.0 / self.eta_inv  # P_charge[t]
            A_eq[row, T+t] = self.eta_inv  # P_discharge[t]
            A_eq[row, 2*T+t] = 1.0  # P_grid_import[t]
            A_eq[row, 3*T+t] = -1.0  # P_grid_export[t]
            b_eq[row] = load[t] - pv[t]
            row += 1

        # Battery dynamics: E[t] = E[t-1] + η_charge*P_charge[t] - P_discharge[t]/η_discharge
        for t in range(T):
            A_eq[row, t] = -self.eta_charge  # P_charge[t]
            A_eq[row, T+t] = 1.0 / self.eta_discharge  # P_discharge[t]
            A_eq[row, 4*T+t] = 1.0  # E_battery[t]
            if t > 0:
                A_eq[row, 4*T+(t-1)] = -1.0  # E_battery[t-1]
            b_eq[row] = E_initial if t == 0 else 0
            row += 1

        # P_peak definition: P_peak = sum(p_trinn[i] * z[i])
        A_eq[row, 5*T] = 1.0  # P_peak
        for i in range(self.N_trinn):
            A_eq[row, 5*T+1+i] = -self.p_trinn[i]  # -p_trinn[i] * z[i]
        b_eq[row] = 0
        row += 1

        return A_eq, b_eq

    def _build_inequality_constraints(self, T: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build inequality constraint matrices A_ub x <= b_ub for:
        1. Peak tracking: P_peak >= P_grid_import[t] for all t
        2. Ordered z activation: z[i] <= z[i-1]
        """
        n_vars = 5*T + 1 + self.N_trinn
        n_constraints = T + (self.N_trinn - 1)

        A_ub = np.zeros((n_constraints, n_vars))
        b_ub = np.zeros(n_constraints)

        row = 0

        # Peak tracking: -P_peak + P_grid_import[t] <= 0  =>  P_peak >= P_grid_import[t]
        for t in range(T):
            A_ub[row, 2*T+t] = 1.0  # P_grid_import[t]
            A_ub[row, 5*T] = -1.0  # -P_peak
            b_ub[row] = 0
            row += 1

        # Ordered activation: z[i] - z[i-1] <= 0  =>  z[i] <= z[i-1]
        for i in range(1, self.N_trinn):
            A_ub[row, 5*T+1+i] = 1.0  # z[i]
            A_ub[row, 5*T+1+(i-1)] = -1.0  # -z[i-1]
            b_ub[row] = 0
            row += 1

        return A_ub, b_ub
