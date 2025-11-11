"""
Batterisimulator for årssimulering med valgbar kontrollstrategi
"""
import pandas as pd
import numpy as np
from typing import Optional
from .battery import Battery
from .strategies import ControlStrategy


class BatterySimulator:
    """
    Simuler batteridrift over tid med valgbar kontrollstrategi

    Simulator er strategy-agnostisk: samme simulator kan brukes
    med NoControl, SimpleRule, eller LP-optimering.
    """

    def __init__(self, strategy: ControlStrategy, battery: Optional[Battery] = None):
        """
        Initialiser simulator

        Args:
            strategy: Kontrollstrategi (NoControl, SimpleRule, LP, etc.)
            battery: Battery-objekt (None for referanse uten batteri)
        """
        self.strategy = strategy
        self.battery = battery

    def simulate_year(
        self,
        production: pd.Series,
        consumption: pd.Series,
        spot_prices: pd.Series,
        solar_inverter_capacity_kw: float = 110.0,
        grid_export_limit_kw: float = 70.0,
        battery_inverter_efficiency: float = 0.98
    ) -> pd.DataFrame:
        """
        Simuler batteridrift time-for-time over hele året med inverter-topologi

        Energiflyt:
        Solar PV (DC) → Solar Inverter (clipping @ 110 kW) → AC Bus
                                                                 ↕
        Battery (DC) ←→ Battery Inverter (bi-directional) ←→ AC Bus
                                                                 ↕
        Grid (export limit @ 70 kW, curtailment hvis overskudd)

        Args:
            production: Solkraftproduksjon DC (kW) med datetime index
            consumption: Forbruk AC (kW) med datetime index
            spot_prices: Spotpriser (NOK/kWh) med datetime index
            solar_inverter_capacity_kw: Maks AC fra solcelle-inverter (default 110)
            grid_export_limit_kw: Maks eksport til nett (default 70)
            battery_inverter_efficiency: Batteriets inverter efficiency (default 0.98)

        Returns:
            pd.DataFrame med kolonner:
                - timestamp: Tidspunkt
                - production_dc_kw: Solkraftproduksjon DC
                - production_ac_kw: Solkraft etter inverter clipping
                - inverter_clipping_kw: Tap ved inverter clipping
                - consumption_kw: Forbruk
                - spot_price: Spotpris
                - battery_power_dc_kw: Batteribeslutning DC (+ lading, - utlading)
                - battery_soc_kwh: Battery state of charge
                - grid_power_kw: Nettimport/eksport (+ import, - eksport)
                - curtailment_kw: Curtailment pga grid export limit
        """
        # Valider input
        if len(production) != len(consumption) or len(production) != len(spot_prices):
            raise ValueError("Production, consumption og spot_prices må ha samme lengde")

        # Reset batteri til initial state
        if self.battery:
            self.battery.reset()

        results = []

        # Simuler time-for-time
        for t in range(len(production)):
            # Steg 1: Solar DC → AC via solar inverter (med clipping)
            prod_dc = production.iloc[t]
            prod_ac = min(prod_dc, solar_inverter_capacity_kw)
            inverter_clipping = max(0, prod_dc - solar_inverter_capacity_kw)

            # Steg 2: Strategien bestemmer batterihandling på AC-siden
            # (batteriet har egen inverter som håndterer DC/AC konvertering)
            p_battery_ac = self.strategy.decide_battery_power(
                t=t,
                production=production,  # Strategy ser original DC produksjon
                consumption=consumption,
                spot_prices=spot_prices,
                battery=self.battery
            )

            # Steg 3: Utfør batterihandling via battery inverter
            p_battery_dc = 0.0  # Actual DC power fra/til batteri
            if self.battery and p_battery_ac != 0:
                if p_battery_ac > 0:  # Lading (AC → DC)
                    # AC power inn i inverter → DC power til batteri
                    p_battery_dc_request = p_battery_ac * battery_inverter_efficiency
                    energy_stored = self.battery.charge(p_battery_dc_request)
                    p_battery_dc = energy_stored  # Actual DC power
                    p_battery_ac = p_battery_dc / battery_inverter_efficiency  # Recalculate AC
                elif p_battery_ac < 0:  # Utlading (DC → AC)
                    # DC power fra batteri → AC power ut av inverter
                    p_battery_dc_request = -p_battery_ac / battery_inverter_efficiency
                    energy_delivered_dc = self.battery.discharge(p_battery_dc_request)
                    p_battery_dc = -energy_delivered_dc  # Negative = discharge
                    p_battery_ac = -energy_delivered_dc * battery_inverter_efficiency

            # Steg 4: AC Bus balanse
            # AC_available = prod_ac - p_battery_ac (negative p_battery_ac = discharge = adds to AC)
            # Net power: AC_available - consumption
            ac_net = prod_ac - p_battery_ac - consumption.iloc[t]

            # Steg 5: Grid connection med export limit
            if ac_net <= 0:  # Import fra nett
                p_grid = -ac_net
                curtailment = 0.0
            else:  # Eksport til nett
                if ac_net <= grid_export_limit_kw:
                    p_grid = -ac_net  # Negative = export
                    curtailment = 0.0
                else:
                    p_grid = -grid_export_limit_kw  # Max export
                    curtailment = ac_net - grid_export_limit_kw

            # Lagre resultat
            results.append({
                'timestamp': production.index[t],
                'production_dc_kw': prod_dc,
                'production_ac_kw': prod_ac,
                'inverter_clipping_kw': inverter_clipping,
                'consumption_kw': consumption.iloc[t],
                'spot_price': spot_prices.iloc[t],
                'battery_power_dc_kw': p_battery_dc,
                'battery_power_ac_kw': p_battery_ac,
                'battery_soc_kwh': self.battery.soc_kwh if self.battery else 0.0,
                'grid_power_kw': p_grid,
                'curtailment_kw': curtailment
            })

        return pd.DataFrame(results)

    def __repr__(self):
        battery_str = repr(self.battery) if self.battery else "None"
        return f"BatterySimulator(strategy={self.strategy}, battery={battery_str})"


if __name__ == "__main__":
    from .strategies import NoControlStrategy, SimpleRuleStrategy
    print("=== SIMULATOR TEST ===\n")

    # Mock data: 7 dager
    timestamps = pd.date_range('2024-01-01', periods=24*7, freq='h')

    # Enkel solkurveprofil (repetert hver dag)
    daily_prod = [0, 0, 0, 0, 0, 0, 5, 20, 40, 60, 70, 75,
                  70, 65, 55, 40, 20, 5, 0, 0, 0, 0, 0, 0]
    production = pd.Series(daily_prod * 7, index=timestamps, name='production_kw')

    # Enkel forbruksprofil
    daily_cons = [30, 30, 30, 30, 30, 35, 40, 50, 55, 60, 60, 50,
                  45, 55, 60, 65, 70, 65, 55, 45, 40, 35, 30, 30]
    consumption = pd.Series(daily_cons * 7, index=timestamps, name='consumption_kw')

    # Enkel prisprofil
    daily_price = [0.3, 0.25, 0.2, 0.2, 0.25, 0.4, 0.6, 0.8, 1.0, 1.2, 1.3, 1.2,
                   1.0, 1.1, 1.2, 1.3, 1.4, 1.3, 1.0, 0.8, 0.6, 0.5, 0.4, 0.3]
    spot_prices = pd.Series(daily_price * 7, index=timestamps, name='spot_price')

    # Test 1: Referanse uten batteri
    print("1. Simulering med NoControlStrategy (referanse):")
    strategy_ref = NoControlStrategy()
    sim_ref = BatterySimulator(strategy=strategy_ref, battery=None)
    results_ref = sim_ref.simulate_year(production, consumption, spot_prices)

    print(f"   Antall timesteg: {len(results_ref)}")
    print(f"   Total nettimport: {results_ref['grid_power_kw'].sum():.2f} kWh")
    print(f"   Maks nettimport: {results_ref['grid_power_kw'].max():.2f} kW")
    print(f"   Total eksport: {results_ref[results_ref['grid_power_kw'] < 0]['grid_power_kw'].sum():.2f} kWh")

    # Test 2: Med SimpleRuleStrategy
    print("\n2. Simulering med SimpleRuleStrategy:")
    battery = Battery(capacity_kwh=100, power_kw=50)
    strategy_simple = SimpleRuleStrategy(cheap_price_threshold=0.5, expensive_price_threshold=1.0)
    sim_simple = BatterySimulator(strategy=strategy_simple, battery=battery)
    results_simple = sim_simple.simulate_year(production, consumption, spot_prices)

    print(f"   Antall timesteg: {len(results_simple)}")
    print(f"   Total batterilading: {results_simple[results_simple['battery_power_kw'] > 0]['battery_power_kw'].sum():.2f} kWh")
    print(f"   Total batteriutlading: {results_simple[results_simple['battery_power_kw'] < 0]['battery_power_kw'].sum():.2f} kWh")
    print(f"   Final SOC: {results_simple['battery_soc_kwh'].iloc[-1]:.2f} kWh")
    print(f"   Total nettimport: {results_simple['grid_power_kw'].sum():.2f} kWh")
    print(f"   Maks nettimport: {results_simple['grid_power_kw'].max():.2f} kW")

    # Sammenligning
    print("\n3. Sammenligning:")
    grid_cost_ref = (results_ref['grid_power_kw'] * results_ref['spot_price']).sum()
    grid_cost_simple = (results_simple['grid_power_kw'] * results_simple['spot_price']).sum()
    savings = grid_cost_ref - grid_cost_simple

    print(f"   Nettkostnad uten batteri: {grid_cost_ref:.2f} NOK")
    print(f"   Nettkostnad med batteri: {grid_cost_simple:.2f} NOK")
    print(f"   Besparelse: {savings:.2f} NOK ({savings/grid_cost_ref*100:.1f}%)")
