"""
Optimization service for battery sizing and operation strategy
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
from scipy.optimize import linprog, differential_evolution
import logging

from domain.models.battery import Battery, BatterySpecification
from domain.models.solar_system import PVSystem, ProductionAnalysis
from domain.models.load_profile import LoadProfile
from domain.value_objects.energy import Energy, Power
from domain.value_objects.money import Money, CostPerUnit, CashFlow


logger = logging.getLogger(__name__)


@dataclass
class OptimizationObjective:
    """Optimization objective configuration"""
    metric: str  # 'npv', 'irr', 'payback', 'self_consumption', 'peak_reduction'
    minimize: bool = False
    weight: float = 1.0
    constraints: Dict[str, Any] = None

    def __post_init__(self):
        if self.constraints is None:
            self.constraints = {}


@dataclass
class OptimizationConstraints:
    """System constraints for optimization"""
    max_battery_capacity: Energy
    max_battery_power: Power
    min_battery_capacity: Energy = None
    min_battery_power: Power = None
    grid_import_limit: Power = None
    grid_export_limit: Power = None
    min_soc: float = 0.1
    max_soc: float = 0.95

    def __post_init__(self):
        if self.min_battery_capacity is None:
            self.min_battery_capacity = Energy.from_kwh(0)
        if self.min_battery_power is None:
            self.min_battery_power = Power.from_kw(0)


@dataclass
class OptimizationResult:
    """Results from optimization"""
    optimal_capacity: Energy
    optimal_power: Power
    annual_savings: Money
    npv: Money
    irr: float
    payback_years: float
    self_consumption_rate: float
    peak_reduction_percentage: float
    energy_arbitrage_revenue: Money
    demand_charge_savings: Money
    curtailment_avoided: Energy
    operation_schedule: pd.DataFrame = None

    def summary_dict(self) -> Dict[str, Any]:
        """Get summary as dictionary"""
        return {
            'optimal_capacity_kwh': self.optimal_capacity.kwh,
            'optimal_power_kw': self.optimal_power.kw,
            'annual_savings_nok': self.annual_savings.amount,
            'npv_nok': self.npv.amount,
            'irr_percentage': self.irr * 100,
            'payback_years': self.payback_years,
            'self_consumption_rate': self.self_consumption_rate,
            'peak_reduction_percentage': self.peak_reduction_percentage,
            'arbitrage_revenue_nok': self.energy_arbitrage_revenue.amount,
            'demand_charge_savings_nok': self.demand_charge_savings.amount,
            'curtailment_avoided_kwh': self.curtailment_avoided.kwh
        }


class BatteryOptimizationService:
    """Service for optimizing battery size and operation"""

    def __init__(
        self,
        pv_system: PVSystem,
        load_profile: LoadProfile,
        electricity_prices: pd.Series,
        tariff_structure: Dict[str, Any],
        discount_rate: float = 0.05
    ):
        self.pv_system = pv_system
        self.load_profile = load_profile
        self.prices = electricity_prices
        self.tariff = tariff_structure
        self.discount_rate = discount_rate

    def optimize_battery_size(
        self,
        objective: OptimizationObjective,
        constraints: OptimizationConstraints,
        battery_cost_per_kwh: CostPerUnit,
        project_lifetime_years: int = 15
    ) -> OptimizationResult:
        """
        Optimize battery size based on objective and constraints

        Args:
            objective: Optimization objective
            constraints: System constraints
            battery_cost_per_kwh: Battery cost per kWh
            project_lifetime_years: Project evaluation period

        Returns:
            Optimization results
        """
        # Define decision variable bounds
        bounds = [
            (constraints.min_battery_capacity.kwh, constraints.max_battery_capacity.kwh),  # Capacity
            (constraints.min_battery_power.kw, constraints.max_battery_power.kw)  # Power
        ]

        # Objective function
        def objective_function(x):
            capacity_kwh, power_kw = x

            # Create battery with these specs
            spec = BatterySpecification(
                capacity=Energy.from_kwh(capacity_kwh),
                max_power=Power.from_kw(power_kw)
            )
            battery = Battery(spec)

            # Simulate operation
            results = self._simulate_battery_operation(battery)

            # Calculate economic metrics
            metrics = self._calculate_economic_metrics(
                battery,
                results,
                battery_cost_per_kwh,
                project_lifetime_years
            )

            # Return objective value
            if objective.metric == 'npv':
                return -metrics['npv'].amount if not objective.minimize else metrics['npv'].amount
            elif objective.metric == 'irr':
                return -metrics['irr'] if not objective.minimize else metrics['irr']
            elif objective.metric == 'payback':
                return metrics['payback_years']
            elif objective.metric == 'self_consumption':
                return -results['self_consumption_rate']
            else:
                raise ValueError(f"Unknown objective metric: {objective.metric}")

        # Run optimization
        result = differential_evolution(
            objective_function,
            bounds,
            seed=42,
            maxiter=100,
            popsize=15,
            tol=0.01
        )

        # Get optimal values
        optimal_capacity_kwh, optimal_power_kw = result.x

        # Create optimal battery and get detailed results
        optimal_spec = BatterySpecification(
            capacity=Energy.from_kwh(optimal_capacity_kwh),
            max_power=Power.from_kw(optimal_power_kw)
        )
        optimal_battery = Battery(optimal_spec)

        simulation_results = self._simulate_battery_operation(optimal_battery)
        economic_metrics = self._calculate_economic_metrics(
            optimal_battery,
            simulation_results,
            battery_cost_per_kwh,
            project_lifetime_years
        )

        return OptimizationResult(
            optimal_capacity=Energy.from_kwh(optimal_capacity_kwh),
            optimal_power=Power.from_kw(optimal_power_kw),
            annual_savings=economic_metrics['annual_savings'],
            npv=economic_metrics['npv'],
            irr=economic_metrics['irr'],
            payback_years=economic_metrics['payback_years'],
            self_consumption_rate=simulation_results['self_consumption_rate'],
            peak_reduction_percentage=simulation_results['peak_reduction'],
            energy_arbitrage_revenue=economic_metrics['arbitrage_revenue'],
            demand_charge_savings=economic_metrics['demand_savings'],
            curtailment_avoided=simulation_results['curtailment_avoided'],
            operation_schedule=simulation_results.get('schedule')
        )

    def _simulate_battery_operation(self, battery: Battery) -> Dict[str, Any]:
        """
        Simulate battery operation for a full year

        Returns:
            Dictionary with simulation results
        """
        # This is a simplified simulation - real implementation would be more detailed
        n_hours = min(len(self.prices), len(self.load_profile.data), 8760)

        # Initialize tracking variables
        battery_soc = []
        grid_import = []
        grid_export = []
        battery_charge = []
        battery_discharge = []
        curtailment = []

        # Assume we have PV production data
        pv_production = self._get_pv_production()

        for hour in range(n_hours):
            # Get current values
            load = self.load_profile.data.iloc[hour]
            pv = pv_production[hour] if hour < len(pv_production) else 0
            price = self.prices.iloc[hour]

            # Net load (negative means excess PV)
            net_load = load - pv

            # Simple self-consumption strategy
            if net_load > 0:  # Deficit - try to discharge
                # Check battery availability
                available_discharge = min(
                    battery.available_discharge_capacity.kwh,
                    net_load,
                    battery.spec.max_discharge_power.kw
                )

                if available_discharge > 0:
                    discharged, delivered = battery.discharge(
                        Power.from_kw(available_discharge),
                        1.0
                    )
                    battery_discharge.append(delivered.kwh)
                    battery_charge.append(0)
                    grid_import.append(max(0, net_load - delivered.kwh))
                    grid_export.append(0)
                else:
                    battery_discharge.append(0)
                    battery_charge.append(0)
                    grid_import.append(net_load)
                    grid_export.append(0)

            else:  # Surplus - try to charge
                surplus = -net_load

                # Check for curtailment (if PV > grid limit)
                grid_limit = 77  # kW - from config
                if pv > grid_limit:
                    potential_curtailment = pv - grid_limit

                    # Try to store in battery
                    available_charge = min(
                        battery.available_charge_capacity.kwh,
                        potential_curtailment,
                        battery.spec.max_charge_power.kw
                    )

                    if available_charge > 0:
                        charged, drawn = battery.charge(
                            Power.from_kw(available_charge),
                            1.0
                        )
                        battery_charge.append(charged.kwh)
                        battery_discharge.append(0)
                        curtailment.append(potential_curtailment - charged.kwh)
                        grid_export.append(min(surplus, grid_limit))
                    else:
                        battery_charge.append(0)
                        battery_discharge.append(0)
                        curtailment.append(potential_curtailment)
                        grid_export.append(grid_limit)
                else:
                    # No curtailment risk
                    battery_charge.append(0)
                    battery_discharge.append(0)
                    curtailment.append(0)
                    grid_export.append(surplus)

                grid_import.append(0)

            battery_soc.append(battery.soc)

            # Reset battery state for next hour
            battery.idle()

        # Calculate metrics
        total_self_consumption = sum(battery_discharge)
        total_pv_production = sum(pv_production[:n_hours])
        self_consumption_rate = total_self_consumption / total_pv_production if total_pv_production > 0 else 0

        # Peak reduction
        original_peak = max(self.load_profile.data)
        peak_with_battery = max([self.load_profile.data.iloc[i] - battery_discharge[i] for i in range(n_hours)])
        peak_reduction = (original_peak - peak_with_battery) / original_peak

        return {
            'self_consumption_rate': self_consumption_rate,
            'peak_reduction': peak_reduction,
            'curtailment_avoided': Energy.from_kwh(sum(curtailment)),
            'total_charge': Energy.from_kwh(sum(battery_charge)),
            'total_discharge': Energy.from_kwh(sum(battery_discharge)),
            'grid_import': Energy.from_kwh(sum(grid_import)),
            'grid_export': Energy.from_kwh(sum(grid_export))
        }

    def _calculate_economic_metrics(
        self,
        battery: Battery,
        simulation_results: Dict[str, Any],
        battery_cost_per_kwh: CostPerUnit,
        project_lifetime_years: int
    ) -> Dict[str, Any]:
        """Calculate economic metrics from simulation results"""
        # Initial investment
        investment = battery_cost_per_kwh.calculate_total(battery.spec.capacity.kwh)

        # Annual revenues/savings
        # 1. Avoided curtailment value
        curtailment_value = simulation_results['curtailment_avoided'].kwh * 0.5  # NOK/kWh

        # 2. Self-consumption value (avoid buying from grid)
        self_consumption_value = simulation_results['total_discharge'].kwh * 1.0  # NOK/kWh

        # 3. Peak demand charge reduction
        peak_reduction_kw = simulation_results['peak_reduction'] * self.load_profile.peak_demand.kw
        demand_charge_savings = peak_reduction_kw * 45 * 12  # NOK/kW/month * 12 months

        # Total annual savings
        annual_savings = Money.nok(
            curtailment_value + self_consumption_value + demand_charge_savings
        )

        # Cash flow analysis
        cash_flows = [-investment.amount]  # Year 0
        for year in range(1, project_lifetime_years + 1):
            # Degradation factor
            degradation = (1 - 0.02) ** year  # 2% annual degradation
            yearly_savings = annual_savings.amount * degradation
            cash_flows.append(yearly_savings)

        # NPV calculation
        npv = 0
        for year, cf in enumerate(cash_flows):
            npv += cf / ((1 + self.discount_rate) ** year)

        # IRR calculation
        irr = self._calculate_irr(cash_flows)

        # Payback period
        cumulative = 0
        payback_years = project_lifetime_years
        for year, cf in enumerate(cash_flows[1:], 1):
            cumulative += cf
            if cumulative >= abs(cash_flows[0]):
                payback_years = year
                break

        return {
            'annual_savings': annual_savings,
            'npv': Money.nok(npv),
            'irr': irr,
            'payback_years': payback_years,
            'arbitrage_revenue': Money.nok(0),  # Simplified
            'demand_savings': Money.nok(demand_charge_savings)
        }

    def _calculate_irr(self, cash_flows: List[float]) -> float:
        """Calculate internal rate of return"""
        # Newton's method for IRR
        rate = 0.1
        tolerance = 1e-6
        max_iterations = 100

        for _ in range(max_iterations):
            # Calculate NPV and its derivative
            npv = 0
            dnpv = 0
            for i, cf in enumerate(cash_flows):
                npv += cf / ((1 + rate) ** i)
                if i > 0:
                    dnpv -= i * cf / ((1 + rate) ** (i + 1))

            # Check convergence
            if abs(npv) < tolerance:
                return rate

            # Newton's method update
            if dnpv != 0:
                rate = rate - npv / dnpv

        return 0  # Failed to converge

    def _get_pv_production(self) -> List[float]:
        """Get PV production data (placeholder)"""
        # In real implementation, this would come from PVGIS or PVLib
        # For now, return synthetic data
        n_hours = 8760
        production = []

        for hour in range(n_hours):
            # Simple sinusoidal pattern
            hour_of_day = hour % 24
            day_of_year = hour // 24

            # Seasonal variation
            seasonal_factor = 1 + 0.3 * np.cos(2 * np.pi * day_of_year / 365)

            # Daily pattern
            if 6 <= hour_of_day <= 18:
                daily_factor = np.sin(np.pi * (hour_of_day - 6) / 12)
            else:
                daily_factor = 0

            # Calculate production
            max_production = self.pv_system.spec.installed_capacity.kw
            hourly_production = max_production * daily_factor * seasonal_factor * 0.2

            production.append(max(0, hourly_production))

        return production