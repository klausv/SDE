"""
Result presenter for battery analysis - standardized output formatting
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class BatteryAnalysisResults:
    """Container for all analysis results"""
    # System parameters
    pv_capacity_kwp: float
    inverter_limit_kw: float
    battery_capacity_kwh: float
    battery_power_kw: float
    grid_limit_kw: float
    annual_consumption_kwh: float

    # Data summary
    annual_production_mwh: float
    annual_consumption_mwh: float
    avg_spot_price: float

    # Value drivers
    curtailment_kwh: float
    curtailment_value_nok: float
    arbitrage_value_nok: float
    demand_charge_value_nok: float
    self_consumption_value_nok: float
    total_annual_value_nok: float

    # Economics
    battery_cost_per_kwh: float
    initial_investment: float
    npv: float
    irr: Optional[float]
    payback_years: float
    break_even_cost: Optional[float] = None

    # Optional sensitivity analysis
    sensitivity_results: Optional[List[Dict]] = None


class ResultPresenter:
    """Presenter for battery analysis results with different output formats"""

    def __init__(self, results: BatteryAnalysisResults):
        self.results = results

    def print_header(self, title: str = "BATTERIANALYSE"):
        """Print standardized header"""
        print("\n" + "="*60)
        print(f"🔋 {title}")
        print("="*60)

    def print_system_parameters(self):
        """Print system configuration"""
        print("\n📊 SYSTEMPARAMETERE:")
        print(f"   • Solceller: {self.results.pv_capacity_kwp} kWp")
        print(f"   • Inverter: {self.results.inverter_limit_kw} kW")
        print(f"   • Batteri: {self.results.battery_capacity_kwh} kWh / {self.results.battery_power_kw} kW")
        print(f"   • Nettgrense: {self.results.grid_limit_kw} kW")
        print(f"   • Årlig forbruk: {self.results.annual_consumption_kwh:,} kWh")

    def print_data_summary(self):
        """Print data generation summary"""
        print("\n📈 DATASUMMERING:")
        print(f"   • Årsproduksjon: {self.results.annual_production_mwh:.1f} MWh")
        print(f"   • Årsforbruk: {self.results.annual_consumption_mwh:.1f} MWh")
        print(f"   • Gjennomsnittspris: {self.results.avg_spot_price:.2f} NOK/kWh")

    def print_value_drivers(self, detailed: bool = True):
        """Print value driver analysis"""
        print("\n💰 VERDIDRIVERE:")

        # Calculate percentages
        total = self.results.total_annual_value_nok
        curt_pct = (self.results.curtailment_value_nok / total * 100) if total > 0 else 0
        arb_pct = (self.results.arbitrage_value_nok / total * 100) if total > 0 else 0
        demand_pct = (self.results.demand_charge_value_nok / total * 100) if total > 0 else 0
        self_pct = (self.results.self_consumption_value_nok / total * 100) if total > 0 else 0

        if detailed:
            print(f"   • Avkortning: {self.results.curtailment_value_nok:8,.0f} NOK/år ({curt_pct:3.0f}%)")
            print(f"     └─ {self.results.curtailment_kwh:,.0f} kWh/år unngått tap")
            print(f"   • Arbitrasje: {self.results.arbitrage_value_nok:8,.0f} NOK/år ({arb_pct:3.0f}%)")
            print(f"   • Effekttariff: {self.results.demand_charge_value_nok:8,.0f} NOK/år ({demand_pct:3.0f}%)")
            print(f"   • Selvforsyning: {self.results.self_consumption_value_nok:8,.0f} NOK/år ({self_pct:3.0f}%)")
        else:
            print(f"   • Avkortning: {self.results.curtailment_value_nok:,.0f} NOK ({self.results.curtailment_kwh:,.0f} kWh)")
            print(f"   • Arbitrasje: {self.results.arbitrage_value_nok:,.0f} NOK")
            print(f"   • Effekttariff: {self.results.demand_charge_value_nok:,.0f} NOK")
            print(f"   • Selvforsyning: {self.results.self_consumption_value_nok:,.0f} NOK")

        print(f"   {'─'*35}")
        print(f"   TOTAL: {self.results.total_annual_value_nok:,.0f} NOK/år")

    def print_economics(self, show_investment: bool = True):
        """Print economic analysis"""
        print(f"\n📊 ØKONOMI ({self.results.battery_cost_per_kwh:,} NOK/kWh):")

        if show_investment:
            print(f"   • Investering: {self.results.initial_investment:,.0f} NOK")

        print(f"   • NPV: {self.results.npv:,.0f} NOK")

        if self.results.irr:
            print(f"   • IRR: {self.results.irr:.1%}")
        else:
            print(f"   • IRR: Ikke kalkulerbar")

        if self.results.payback_years < 50:
            print(f"   • Tilbakebetalingstid: {self.results.payback_years:.1f} år")
        else:
            print(f"   • Tilbakebetalingstid: > 50 år")

    def print_conclusion(self):
        """Print investment conclusion"""
        print("\n🎯 KONKLUSJON:")

        if self.results.npv > 0:
            print(f"   ✅ LØNNSOMT! NPV er positiv ({self.results.npv:,.0f} NOK)")
            if self.results.irr:
                print(f"   → Investeringen gir {self.results.irr:.1%} årlig avkastning")
            print(f"   → Tilbakebetalt på {self.results.payback_years:.1f} år")
        else:
            print(f"   ❌ ULØNNSOMT! NPV er negativ ({self.results.npv:,.0f} NOK)")
            print(f"   → Batterikostnaden må reduseres for lønnsomhet")

    def print_break_even(self):
        """Print break-even analysis"""
        if self.results.break_even_cost:
            print(f"\n💡 BREAK-EVEN ANALYSE:")
            print(f"   • Maks lønnsom batterikost: {self.results.break_even_cost:,.0f} NOK/kWh")

            diff = self.results.battery_cost_per_kwh - self.results.break_even_cost
            if diff > 0:
                print(f"   • Status: {diff:,.0f} NOK/kWh over break-even")
                reduction_pct = (diff / self.results.battery_cost_per_kwh) * 100
                print(f"   • Kostnad må ned {reduction_pct:.0f}% for lønnsomhet")
            else:
                print(f"   • Status: {-diff:,.0f} NOK/kWh under break-even")
                print(f"   • God margin for lønnsomhet!")

    def print_sensitivity(self):
        """Print sensitivity analysis if available"""
        if not self.results.sensitivity_results:
            return

        print("\n📉 SENSITIVITETSANALYSE:")
        print("Kostnad | NPV        | IRR   | Status")
        print("-" * 40)

        for result in self.results.sensitivity_results:
            status = "✅" if result['profitable'] else "❌"
            irr_str = f"{result['irr']:.1%}" if result['irr'] else "  N/A"
            print(f"{result['cost_per_kwh']:,} kr | {result['npv']:10,.0f} | {irr_str} | {status}")

    def print_recommendations(self):
        """Print investment recommendations"""
        print("\n💡 ANBEFALINGER:")

        if self.results.npv > 0:
            print("   ✅ Investeringen er lønnsom med dagens parametere")
            if self.results.payback_years < 7:
                print("   ✅ Kort tilbakebetalingstid - sterk investering")
            elif self.results.payback_years < 10:
                print("   ⚠️ Moderat tilbakebetalingstid - vurder risiko")
            else:
                print("   ⚠️ Lang tilbakebetalingstid - vurder alternativer")
        else:
            if self.results.break_even_cost:
                cost_reduction_needed = self.results.battery_cost_per_kwh - self.results.break_even_cost
                print(f"   ⏳ Vent til batterikost faller under {self.results.break_even_cost:,.0f} NOK/kWh")
                print(f"   📉 Kostnad må ned {cost_reduction_needed:,.0f} NOK/kWh")

            # Suggest smaller battery
            smaller_battery_kwh = self.results.battery_capacity_kwh * 0.5
            print(f"   💡 Vurder mindre batteri ({smaller_battery_kwh:.0f} kWh) for bedre lønnsomhet")

    def print_full_report(self, title: str = "BATTERIANALYSE"):
        """Print complete analysis report"""
        self.print_header(title)
        self.print_system_parameters()
        self.print_data_summary()
        self.print_value_drivers(detailed=True)
        self.print_economics()
        self.print_conclusion()
        self.print_break_even()
        self.print_sensitivity()
        self.print_recommendations()
        print("\n" + "="*60)

    def print_summary(self, title: str = "BATTERIANALYSE"):
        """Print concise summary"""
        self.print_header(title)
        self.print_system_parameters()
        self.print_value_drivers(detailed=False)
        self.print_economics(show_investment=False)
        self.print_conclusion()
        print("\n" + "="*60)

    def get_dict(self) -> Dict[str, Any]:
        """Return results as dictionary"""
        return {
            'system': {
                'pv_kwp': self.results.pv_capacity_kwp,
                'inverter_kw': self.results.inverter_limit_kw,
                'battery_kwh': self.results.battery_capacity_kwh,
                'battery_kw': self.results.battery_power_kw,
                'grid_limit_kw': self.results.grid_limit_kw
            },
            'value_drivers': {
                'curtailment_nok': self.results.curtailment_value_nok,
                'arbitrage_nok': self.results.arbitrage_value_nok,
                'demand_charge_nok': self.results.demand_charge_value_nok,
                'self_consumption_nok': self.results.self_consumption_value_nok,
                'total_nok': self.results.total_annual_value_nok
            },
            'economics': {
                'npv': self.results.npv,
                'irr': self.results.irr,
                'payback_years': self.results.payback_years,
                'break_even_cost': self.results.break_even_cost,
                'profitable': self.results.npv > 0
            }
        }