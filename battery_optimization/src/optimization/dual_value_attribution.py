"""
Dual Variable-Based Value Attribution for Battery Optimization

Uses shadow prices (dual variables) from LP optimization to attribute
battery economic value to specific functions:
1. Peak shaving (power tariff reduction)
2. Energy arbitrage (time-shifting)
3. Curtailment avoidance
4. Self-consumption enhancement
5. Battery degradation (cost)
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class DualVariables:
    """Container for extracted dual variables from LP solution."""
    peak_constraints: List[float]  # λ_peak[t]
    soc_dynamics: List[float]  # μ_soc[t]
    soc_upper_bounds: List[float]  # Upper bound on SOC
    soc_lower_bounds: List[float]  # Lower bound on SOC
    export_limits: List[float]  # λ_curtail[t]
    energy_balance: List[float]  # ν_balance[t]
    charge_limits: List[float]  # Power limit on charging
    discharge_limits: List[float]  # Power limit on discharging


@dataclass
class ValueAttribution:
    """Economic value breakdown for battery operation."""
    peak_shaving: float  # kr/year
    arbitrage: float  # kr/year
    curtailment_avoidance: float  # kr/year
    self_consumption: float  # kr/year
    degradation_cost: float  # kr/year (negative)

    @property
    def total_net_value(self) -> float:
        """Total value after degradation."""
        return (self.peak_shaving + self.arbitrage +
                self.curtailment_avoidance + self.self_consumption +
                self.degradation_cost)

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for reporting."""
        return {
            'Peak Shaving': self.peak_shaving,
            'Energy Arbitrage': self.arbitrage,
            'Curtailment Avoidance': self.curtailment_avoidance,
            'Self-Consumption': self.self_consumption,
            'Degradation Cost': self.degradation_cost,
            'Total Net Value': self.total_net_value
        }


class DualValueAttributor:
    """
    Attributes battery economic value using dual variables from LP optimization.

    Theory:
    -------
    Shadow prices (dual variables) represent the marginal value of relaxing
    each constraint. By analyzing which constraints bind when and their duals,
    we can attribute value to specific battery functions.

    Key Insights:
    - Peak constraint dual > 0: Battery is actively reducing monthly peak
    - Export limit dual > 0: Battery storing curtailed PV energy
    - SOC dynamics dual: Opportunity cost of energy storage
    - Price spread ≠ dual spread: Battery doing arbitrage

    Usage:
    ------
    >>> attributor = DualValueAttributor(power_tariff_rate=60.0)
    >>> duals = attributor.extract_duals_from_pulp(prob)
    >>> values = attributor.attribute_weekly_value(
    ...     duals=duals,
    ...     solution_data=solution,
    ...     spot_prices=prices,
    ...     pv_production=pv
    ... )
    """

    def __init__(self, power_tariff_rate: float = 60.0,
                 efficiency: float = 0.90,
                 eur_to_nok: float = 11.5):
        """
        Initialize dual value attributor.

        Parameters:
        -----------
        power_tariff_rate : float
            Power tariff in NOK/kW/month for peak demand
        efficiency : float
            Battery round-trip efficiency (e.g., 0.90 = 90%)
        eur_to_nok : float
            Exchange rate for EUR to NOK conversion
        """
        self.power_tariff_rate = power_tariff_rate
        self.efficiency = efficiency
        self.eur_to_nok = eur_to_nok

    def extract_duals_from_pulp(self, prob) -> DualVariables:
        """
        Extract dual variables from solved PuLP problem.

        Parameters:
        -----------
        prob : pulp.LpProblem
            Solved LP problem with dual variables available

        Returns:
        --------
        DualVariables
            Container with organized dual variables by constraint type
        """
        duals = {
            'peak': [],
            'soc_dynamics': [],
            'soc_upper': [],
            'soc_lower': [],
            'export_limit': [],
            'energy_balance': [],
            'charge_limit': [],
            'discharge_limit': []
        }

        # Extract duals from PuLP constraints
        for name, constraint in prob.constraints.items():
            dual_value = constraint.pi  # Shadow price

            # Categorize by constraint name pattern
            if 'peak_month' in name.lower() or 'peak_track' in name.lower():
                duals['peak'].append(dual_value)
            elif 'soc_dynamics' in name.lower() or 'battery_dynamics' in name.lower():
                duals['soc_dynamics'].append(dual_value)
            elif 'soc_max' in name.lower() or 'soc_upper' in name.lower():
                duals['soc_upper'].append(dual_value)
            elif 'soc_min' in name.lower() or 'soc_lower' in name.lower():
                duals['soc_lower'].append(dual_value)
            elif 'export_limit' in name.lower() or 'grid_limit' in name.lower():
                duals['export_limit'].append(dual_value)
            elif 'energy_balance' in name.lower() or 'power_balance' in name.lower():
                duals['energy_balance'].append(dual_value)
            elif 'charge_limit' in name.lower() or 'max_charge' in name.lower():
                duals['charge_limit'].append(dual_value)
            elif 'discharge_limit' in name.lower() or 'max_discharge' in name.lower():
                duals['discharge_limit'].append(dual_value)

        return DualVariables(
            peak_constraints=np.array(duals['peak']),
            soc_dynamics=np.array(duals['soc_dynamics']),
            soc_upper_bounds=np.array(duals['soc_upper']),
            soc_lower_bounds=np.array(duals['soc_lower']),
            export_limits=np.array(duals['export_limit']),
            energy_balance=np.array(duals['energy_balance']),
            charge_limits=np.array(duals['charge_limit']),
            discharge_limits=np.array(duals['discharge_limit'])
        )

    def calculate_peak_shaving_value(self, duals: DualVariables,
                                     num_months: int = 12) -> float:
        """
        Calculate value from peak power tariff reduction.

        Method:
        -------
        When peak constraint is binding (dual > 0), battery is limiting
        monthly peak demand. Sum all positive peak duals and multiply by
        power tariff rate.

        Parameters:
        -----------
        duals : DualVariables
            Extracted dual variables
        num_months : int
            Number of months in optimization horizon (usually 12)

        Returns:
        --------
        float
            Annual value from peak shaving (NOK)
        """
        # Sum positive duals from peak constraints
        binding_peak_duals = duals.peak_constraints[duals.peak_constraints > 0]

        if len(binding_peak_duals) == 0:
            return 0.0

        # Each binding dual represents marginal value of reducing peak
        # Multiply by power tariff rate to get NOK value
        peak_value = np.sum(binding_peak_duals) * self.power_tariff_rate

        # Annualize if optimization horizon < 12 months
        if num_months < 12:
            peak_value *= (12 / num_months)

        return peak_value

    def calculate_curtailment_value(self, duals: DualVariables,
                                   charge_power: np.ndarray,
                                   spot_prices: np.ndarray) -> float:
        """
        Calculate value from avoiding PV curtailment.

        Method:
        -------
        When export limit constraint binds (dual > 0), grid export is at max.
        If battery is charging during these hours, it's storing energy that
        would otherwise be curtailed. Value = stored energy × spot price.

        Parameters:
        -----------
        duals : DualVariables
            Extracted dual variables
        charge_power : np.ndarray
            Battery charging power profile [kW]
        spot_prices : np.ndarray
            Spot electricity prices [NOK/kWh]

        Returns:
        --------
        float
            Annual value from curtailment avoidance (NOK)
        """
        curtailment_value = 0.0

        for t, dual in enumerate(duals.export_limits):
            if dual > 0 and t < len(charge_power):
                # Export limit binding + battery charging = curtailment avoided
                energy_stored = charge_power[t]  # kWh
                price = spot_prices[t]  # NOK/kWh

                # Value = energy that would have been curtailed × its price
                curtailment_value += energy_stored * price

        return curtailment_value

    def calculate_arbitrage_value(self, duals: DualVariables,
                                 charge_power: np.ndarray,
                                 discharge_power: np.ndarray,
                                 spot_prices: np.ndarray,
                                 pv_production: np.ndarray) -> float:
        """
        Calculate value from energy arbitrage (time-shifting).

        Method:
        -------
        Arbitrage occurs when battery charges from grid during low prices
        and discharges during high prices. Use SOC dynamics duals to identify
        time-shifting that's driven by price spreads (not curtailment avoidance).

        Theory:
        - SOC dual μ[t] = marginal value of 1 kWh stored at time t
        - If μ[t+1] - μ[t] > 0: Battery should store energy (future value higher)
        - If price[t+1] - price[t] > 0 and same sign as dual spread: Arbitrage

        Parameters:
        -----------
        duals : DualVariables
            Extracted dual variables
        charge_power : np.ndarray
            Battery charging power profile [kW]
        discharge_power : np.ndarray
            Battery discharging power profile [kW]
        spot_prices : np.ndarray
            Spot electricity prices [NOK/kWh]
        pv_production : np.ndarray
            PV production profile [kW] (to exclude curtailment-driven charging)

        Returns:
        --------
        float
            Annual value from arbitrage (NOK)
        """
        arbitrage_value = 0.0

        # Need at least 2 time steps for price spreads
        if len(duals.soc_dynamics) < 2:
            return 0.0

        for t in range(len(duals.soc_dynamics) - 1):
            # Calculate price spread and dual spread
            price_spread = spot_prices[t+1] - spot_prices[t]
            dual_spread = duals.soc_dynamics[t+1] - duals.soc_dynamics[t]

            # Arbitrage condition: Both spreads same sign (buy low, sell high)
            if np.sign(price_spread) == np.sign(dual_spread) and dual_spread != 0:

                # Charging during low prices for future discharge
                if charge_power[t] > 0:
                    # Check if charging from grid (not curtailment storage)
                    grid_charge = charge_power[t] - min(charge_power[t], pv_production[t])

                    if grid_charge > 0:
                        # This is arbitrage: buying low for future high-price discharge
                        arbitrage_value += grid_charge * abs(dual_spread)

                # Discharging during high prices (completing arbitrage cycle)
                elif discharge_power[t] > 0:
                    # Value realized from previous low-price storage
                    arbitrage_value += discharge_power[t] * abs(dual_spread)

        return arbitrage_value

    def calculate_self_consumption_value(self, duals: DualVariables,
                                        discharge_power: np.ndarray,
                                        spot_prices: np.ndarray,
                                        energy_tariff: np.ndarray,
                                        pv_production: np.ndarray,
                                        charge_power: np.ndarray) -> float:
        """
        Calculate value from PV self-consumption enhancement.

        Method:
        -------
        Self-consumption: Battery stores PV energy and discharges later to avoid
        importing grid power. Different from arbitrage (which uses grid charging).

        Trace battery SOC source:
        - If energy came from PV → self-consumption
        - If energy came from grid → arbitrage (already counted)

        Parameters:
        -----------
        duals : DualVariables
            Extracted dual variables
        discharge_power : np.ndarray
            Battery discharging power profile [kW]
        spot_prices : np.ndarray
            Spot electricity prices [NOK/kWh]
        energy_tariff : np.ndarray
            Energy tariff [NOK/kWh]
        pv_production : np.ndarray
            PV production profile [kW]
        charge_power : np.ndarray
            Battery charging power profile [kW]

        Returns:
        --------
        float
            Annual value from self-consumption (NOK)
        """
        self_consumption_value = 0.0

        # Simple heuristic: If battery charged during PV production hours
        # and discharges later, it's self-consumption
        lookback_window = 24  # hours

        for t in range(lookback_window, len(discharge_power)):
            if discharge_power[t] > 0:
                # Calculate recent PV vs grid charging
                recent_pv_charge = sum(
                    min(charge_power[t-i], pv_production[t-i])
                    for i in range(1, lookback_window + 1)
                )
                recent_grid_charge = sum(
                    max(0, charge_power[t-i] - pv_production[t-i])
                    for i in range(1, lookback_window + 1)
                )

                total_recent_charge = recent_pv_charge + recent_grid_charge
                if total_recent_charge > 0:
                    pv_fraction = recent_pv_charge / total_recent_charge
                else:
                    pv_fraction = 0

                # Portion from PV = self-consumption value
                self_consumption_discharge = discharge_power[t] * pv_fraction

                # Value = avoided import cost
                avoided_cost = spot_prices[t] + energy_tariff[t]
                self_consumption_value += self_consumption_discharge * avoided_cost

        return self_consumption_value

    def calculate_degradation_cost(self, charge_power: np.ndarray,
                                  discharge_power: np.ndarray,
                                  battery_capacity_kwh: float,
                                  cost_per_cycle_per_kwh: float = 0.05) -> float:
        """
        Calculate battery degradation cost based on cycling.

        Method:
        -------
        - Count equivalent full cycles: sum(throughput) / (2 × capacity)
        - Multiply by degradation cost per cycle

        Parameters:
        -----------
        charge_power : np.ndarray
            Battery charging power profile [kW]
        discharge_power : np.ndarray
            Battery discharging power profile [kW]
        battery_capacity_kwh : float
            Battery capacity [kWh]
        cost_per_cycle_per_kwh : float
            Degradation cost per full cycle per kWh (NOK/kWh/cycle)
            Default: 0.05 NOK/kWh/cycle ≈ 2% of 2500 NOK/kWh battery cost

        Returns:
        --------
        float
            Annual degradation cost (NOK) - returned as NEGATIVE value
        """
        # Total energy throughput (charge + discharge)
        total_throughput = np.sum(charge_power) + np.sum(discharge_power)

        # Equivalent full cycles
        cycles = total_throughput / (2 * battery_capacity_kwh)

        # Degradation cost
        degradation_cost = cycles * battery_capacity_kwh * cost_per_cycle_per_kwh

        return -degradation_cost  # Negative because it's a cost

    def attribute_weekly_value(self, duals: DualVariables,
                              solution_data: Dict,
                              spot_prices: np.ndarray,
                              energy_tariff: np.ndarray,
                              pv_production: np.ndarray,
                              battery_capacity_kwh: float) -> ValueAttribution:
        """
        Complete value attribution for one week's optimization.

        Parameters:
        -----------
        duals : DualVariables
            Extracted dual variables from LP solution
        solution_data : Dict
            Solution with keys: 'P_charge', 'P_discharge', 'SOC'
        spot_prices : np.ndarray
            Spot electricity prices [NOK/kWh]
        energy_tariff : np.ndarray
            Energy tariff [NOK/kWh]
        pv_production : np.ndarray
            PV production profile [kW]
        battery_capacity_kwh : float
            Battery capacity [kWh]

        Returns:
        --------
        ValueAttribution
            Breakdown of economic value by category
        """
        charge_power = solution_data['P_charge']
        discharge_power = solution_data['P_discharge']

        # Calculate each value component using dual variables
        peak_shaving = self.calculate_peak_shaving_value(duals, num_months=12)

        curtailment = self.calculate_curtailment_value(
            duals, charge_power, spot_prices
        )

        arbitrage = self.calculate_arbitrage_value(
            duals, charge_power, discharge_power, spot_prices, pv_production
        )

        self_consumption = self.calculate_self_consumption_value(
            duals, discharge_power, spot_prices, energy_tariff,
            pv_production, charge_power
        )

        degradation = self.calculate_degradation_cost(
            charge_power, discharge_power, battery_capacity_kwh
        )

        return ValueAttribution(
            peak_shaving=peak_shaving,
            arbitrage=arbitrage,
            curtailment_avoidance=curtailment,
            self_consumption=self_consumption,
            degradation_cost=degradation
        )

    def aggregate_annual_attribution(self, weekly_attributions: List[ValueAttribution]) -> ValueAttribution:
        """
        Aggregate weekly value attributions to annual totals.

        Parameters:
        -----------
        weekly_attributions : List[ValueAttribution]
            List of 52 weekly value attributions

        Returns:
        --------
        ValueAttribution
            Annual totals across all categories
        """
        annual = ValueAttribution(
            peak_shaving=sum(w.peak_shaving for w in weekly_attributions),
            arbitrage=sum(w.arbitrage for w in weekly_attributions),
            curtailment_avoidance=sum(w.curtailment_avoidance for w in weekly_attributions),
            self_consumption=sum(w.self_consumption for w in weekly_attributions),
            degradation_cost=sum(w.degradation_cost for w in weekly_attributions)
        )

        return annual


def demonstrate_dual_attribution():
    """Example usage of dual variable attribution."""

    # Initialize attributor
    attributor = DualValueAttributor(
        power_tariff_rate=60.0,  # NOK/kW/month
        efficiency=0.90,
        eur_to_nok=11.5
    )

    # After solving weekly LP problem:
    # prob.solve(PULP_CBC_CMD())  # or HiGHS

    # Extract duals
    # duals = attributor.extract_duals_from_pulp(prob)

    # Get solution data
    # solution_data = {
    #     'P_charge': np.array([...]),
    #     'P_discharge': np.array([...]),
    #     'SOC': np.array([...])
    # }

    # Attribute value for this week
    # week_values = attributor.attribute_weekly_value(
    #     duals=duals,
    #     solution_data=solution_data,
    #     spot_prices=spot_prices,
    #     energy_tariff=energy_tariff,
    #     pv_production=pv_production,
    #     battery_capacity_kwh=100.0
    # )

    # print(week_values.to_dict())

    # Aggregate 52 weeks to annual
    # annual_values = attributor.aggregate_annual_attribution(all_weekly_values)

    print("Dual variable attribution system initialized.")
    print("See docstrings and examples above for usage.")


if __name__ == "__main__":
    demonstrate_dual_attribution()
