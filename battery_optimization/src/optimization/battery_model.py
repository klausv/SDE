"""
Battery model with constraints and operation strategies
"""
import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class BatterySpec:
    """Battery specification"""
    capacity_kwh: float  # Battery energy capacity
    power_kw: float  # Maximum charge/discharge power
    efficiency: float = 0.90  # Round-trip efficiency (sqrt applied for one-way)
    min_soc: float = 0.10  # Minimum state of charge
    max_soc: float = 0.90  # Maximum state of charge
    degradation_rate: float = 0.02  # Annual capacity degradation
    cycles_warranty: int = 6000  # Warranty cycles

class BatteryModel:
    """Battery operation model with multiple control strategies"""

    def __init__(self, spec: BatterySpec):
        """
        Initialize battery model

        Args:
            spec: Battery specification
        """
        self.spec = spec
        self.one_way_efficiency = np.sqrt(spec.efficiency)
        self.usable_capacity = spec.capacity_kwh * (spec.max_soc - spec.min_soc)

    def simulate_operation(
        self,
        pv_production: pd.Series,
        spot_prices: pd.Series,
        load_profile: pd.Series,
        grid_limit: float,
        strategy: str = 'combined'
    ) -> Dict[str, pd.Series]:
        """
        Simulate battery operation for given inputs

        Args:
            pv_production: PV production (kW)
            spot_prices: Electricity spot prices (NOK/kWh)
            load_profile: Load consumption (kW)
            grid_limit: Grid export limit (kW)
            strategy: Operation strategy ('peak_shave', 'arbitrage', 'combined')

        Returns:
            Dictionary with operation results
        """
        n_hours = len(pv_production)

        # Initialize arrays
        soc = np.zeros(n_hours + 1)  # State of charge
        soc[0] = self.spec.min_soc * self.spec.capacity_kwh  # Start at min SOC

        battery_charge = np.zeros(n_hours)  # Positive = charging
        battery_discharge = np.zeros(n_hours)  # Positive = discharging
        grid_export = np.zeros(n_hours)
        grid_import = np.zeros(n_hours)
        curtailment = np.zeros(n_hours)

        for t in range(n_hours):
            # Net generation (PV - Load)
            net_gen = pv_production.iloc[t] - load_profile.iloc[t]

            if strategy == 'peak_shave':
                charge, discharge = self._peak_shave_strategy(
                    net_gen, soc[t], grid_limit
                )
            elif strategy == 'arbitrage':
                charge, discharge = self._arbitrage_strategy(
                    net_gen, soc[t], spot_prices.iloc[t],
                    spot_prices.iloc[max(0, t-12):min(n_hours, t+12)]
                )
            else:  # combined
                charge, discharge = self._combined_strategy(
                    net_gen, soc[t], grid_limit,
                    spot_prices.iloc[t],
                    spot_prices.iloc[max(0, t-12):min(n_hours, t+12)]
                )

            # Apply battery constraints
            charge, discharge = self._apply_constraints(charge, discharge, soc[t])

            # Update battery state
            battery_charge[t] = charge
            battery_discharge[t] = discharge
            soc[t + 1] = soc[t] + charge * self.one_way_efficiency - discharge / self.one_way_efficiency

            # Calculate grid flows
            net_after_battery = net_gen - charge + discharge

            if net_after_battery > 0:
                # Excess generation
                if net_after_battery > grid_limit:
                    grid_export[t] = grid_limit
                    curtailment[t] = net_after_battery - grid_limit
                else:
                    grid_export[t] = net_after_battery
            else:
                # Net consumption
                grid_import[t] = -net_after_battery

        # Create result series
        index = pv_production.index
        results = {
            'soc': pd.Series(soc[:-1], index=index),
            'battery_charge': pd.Series(battery_charge, index=index),
            'battery_discharge': pd.Series(battery_discharge, index=index),
            'grid_export': pd.Series(grid_export, index=index),
            'grid_import': pd.Series(grid_import, index=index),
            'curtailment': pd.Series(curtailment, index=index),
            'net_battery_flow': pd.Series(battery_discharge - battery_charge, index=index)
        }

        return results

    def _peak_shave_strategy(
        self,
        net_generation: float,
        current_soc: float,
        grid_limit: float
    ) -> Tuple[float, float]:
        """
        Peak shaving strategy - minimize curtailment

        Args:
            net_generation: Net generation (PV - Load) in kW
            current_soc: Current battery SOC in kWh
            grid_limit: Grid export limit in kW

        Returns:
            Tuple of (charge_kw, discharge_kw)
        """
        charge = 0.0
        discharge = 0.0

        if net_generation > grid_limit:
            # Excess generation - charge battery
            excess = net_generation - grid_limit
            max_charge = min(
                excess,
                self.spec.power_kw,
                (self.spec.capacity_kwh * self.spec.max_soc - current_soc) / self.one_way_efficiency
            )
            charge = max_charge

        elif net_generation < 0:
            # Net consumption - discharge if beneficial
            required = -net_generation
            max_discharge = min(
                required,
                self.spec.power_kw,
                (current_soc - self.spec.capacity_kwh * self.spec.min_soc) * self.one_way_efficiency
            )
            discharge = max_discharge

        return charge, discharge

    def _arbitrage_strategy(
        self,
        net_generation: float,
        current_soc: float,
        current_price: float,
        price_window: pd.Series
    ) -> Tuple[float, float]:
        """
        Price arbitrage strategy - buy low, sell high

        Args:
            net_generation: Net generation (PV - Load) in kW
            current_soc: Current battery SOC in kWh
            current_price: Current electricity price
            price_window: Price window for decision making

        Returns:
            Tuple of (charge_kw, discharge_kw)
        """
        charge = 0.0
        discharge = 0.0

        # Calculate price thresholds
        price_mean = price_window.mean()
        price_std = price_window.std()

        # Charge threshold (low price)
        charge_threshold = price_mean - 0.5 * price_std

        # Discharge threshold (high price)
        discharge_threshold = price_mean + 0.5 * price_std

        if current_price < charge_threshold:
            # Low price - charge battery
            max_charge = min(
                self.spec.power_kw,
                (self.spec.capacity_kwh * self.spec.max_soc - current_soc) / self.one_way_efficiency
            )
            # Consider net generation
            if net_generation < 0:
                # Already importing - can charge more
                charge = max_charge
            else:
                # Reduce export to charge
                charge = min(max_charge, net_generation)

        elif current_price > discharge_threshold:
            # High price - discharge battery
            max_discharge = min(
                self.spec.power_kw,
                (current_soc - self.spec.capacity_kwh * self.spec.min_soc) * self.one_way_efficiency
            )
            discharge = max_discharge

        return charge, discharge

    def _combined_strategy(
        self,
        net_generation: float,
        current_soc: float,
        grid_limit: float,
        current_price: float,
        price_window: pd.Series
    ) -> Tuple[float, float]:
        """
        Combined strategy - peak shaving with price optimization

        Args:
            net_generation: Net generation (PV - Load) in kW
            current_soc: Current battery SOC in kWh
            grid_limit: Grid export limit in kW
            current_price: Current electricity price
            price_window: Price window for decision making

        Returns:
            Tuple of (charge_kw, discharge_kw)
        """
        # First priority: Peak shaving
        charge_ps, discharge_ps = self._peak_shave_strategy(
            net_generation, current_soc, grid_limit
        )

        # Second priority: Price arbitrage (if peak shaving not needed)
        if charge_ps == 0 and discharge_ps == 0:
            charge_arb, discharge_arb = self._arbitrage_strategy(
                net_generation, current_soc, current_price, price_window
            )
            return charge_arb, discharge_arb

        return charge_ps, discharge_ps

    def _apply_constraints(
        self,
        charge: float,
        discharge: float,
        current_soc: float
    ) -> Tuple[float, float]:
        """
        Apply battery constraints

        Args:
            charge: Requested charge (kW)
            discharge: Requested discharge (kW)
            current_soc: Current SOC (kWh)

        Returns:
            Constrained (charge, discharge) in kW
        """
        # Power constraints
        charge = min(charge, self.spec.power_kw)
        discharge = min(discharge, self.spec.power_kw)

        # SOC constraints
        max_charge_energy = (self.spec.capacity_kwh * self.spec.max_soc - current_soc) / self.one_way_efficiency
        max_discharge_energy = (current_soc - self.spec.capacity_kwh * self.spec.min_soc) * self.one_way_efficiency

        charge = min(charge, max_charge_energy)
        discharge = min(discharge, max_discharge_energy)

        # Cannot charge and discharge simultaneously
        if charge > 0 and discharge > 0:
            if charge > discharge:
                discharge = 0
            else:
                charge = 0

        return max(0, charge), max(0, discharge)

    def calculate_degradation(
        self,
        operation_results: Dict[str, pd.Series],
        years: int
    ) -> float:
        """
        Calculate battery degradation over time

        Args:
            operation_results: Battery operation results
            years: Number of years

        Returns:
            Remaining capacity factor (0-1)
        """
        # Calendar aging
        calendar_degradation = 1 - (self.spec.degradation_rate * years)

        # Cycle aging (simplified)
        total_throughput = (
            operation_results['battery_charge'].sum() +
            operation_results['battery_discharge'].sum()
        ) * years
        equivalent_cycles = total_throughput / (2 * self.spec.capacity_kwh)
        cycle_degradation = max(0, 1 - (equivalent_cycles / self.spec.cycles_warranty) * 0.2)

        # Combined degradation
        total_degradation = calendar_degradation * cycle_degradation

        return max(0.7, total_degradation)  # Minimum 70% capacity

    def calculate_battery_metrics(
        self,
        operation_results: Dict[str, pd.Series]
    ) -> Dict[str, float]:
        """
        Calculate battery operation metrics

        Args:
            operation_results: Battery operation results

        Returns:
            Dictionary with metrics
        """
        metrics = {
            'total_charge_kwh': operation_results['battery_charge'].sum(),
            'total_discharge_kwh': operation_results['battery_discharge'].sum(),
            'avg_soc': operation_results['soc'].mean() / self.spec.capacity_kwh,
            'max_soc': operation_results['soc'].max() / self.spec.capacity_kwh,
            'min_soc': operation_results['soc'].min() / self.spec.capacity_kwh,
            'cycles': (operation_results['battery_charge'].sum() +
                      operation_results['battery_discharge'].sum()) / (2 * self.spec.capacity_kwh),
            'curtailment_avoided_kwh': operation_results['curtailment'].sum(),
            'self_consumption_rate': 1 - (operation_results['grid_export'].sum() /
                                         (operation_results['grid_export'].sum() +
                                          operation_results['battery_charge'].sum()))
        }

        return metrics