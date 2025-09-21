"""
Tests for domain value objects
"""
import pytest
from domain.value_objects.energy import Energy, Power, EnergyPrice
from domain.value_objects.money import Money, CostPerUnit, CashFlow


class TestEnergy:
    """Test Energy value object"""

    def test_energy_creation(self):
        """Test creating energy values"""
        energy = Energy.from_kwh(100)
        assert energy.kwh == 100
        assert energy.mwh == 0.1
        assert energy.wh == 100000

    def test_energy_arithmetic(self):
        """Test energy arithmetic operations"""
        e1 = Energy.from_kwh(100)
        e2 = Energy.from_kwh(50)

        # Addition
        result = e1 + e2
        assert result.kwh == 150

        # Subtraction
        result = e1 - e2
        assert result.kwh == 50

        # Multiplication
        result = e1 * 2
        assert result.kwh == 200

        # Division
        result = e1 / 2
        assert result.kwh == 50

    def test_energy_immutability(self):
        """Test that Energy is immutable"""
        energy = Energy.from_kwh(100)
        with pytest.raises(AttributeError):
            energy.value = 200

    def test_energy_string_representation(self):
        """Test string representation"""
        assert "kWh" in str(Energy.from_kwh(100))
        assert "MWh" in str(Energy.from_kwh(5000))
        assert "Wh" in str(Energy.from_kwh(0.5))


class TestPower:
    """Test Power value object"""

    def test_power_creation(self):
        """Test creating power values"""
        power = Power.from_kw(50)
        assert power.kw == 50
        assert power.mw == 0.05
        assert power.w == 50000

    def test_power_to_energy(self):
        """Test converting power to energy"""
        power = Power.from_kw(10)
        energy = power.to_energy(hours=5)
        assert energy.kwh == 50

    def test_power_arithmetic(self):
        """Test power arithmetic operations"""
        p1 = Power.from_kw(100)
        p2 = Power.from_kw(50)

        # Addition
        result = p1 + p2
        assert result.kw == 150

        # Subtraction
        result = p1 - p2
        assert result.kw == 50

        # Multiplication
        result = p1 * 2
        assert result.kw == 200

        # Division
        result = p1 / 2
        assert result.kw == 50


class TestMoney:
    """Test Money value object"""

    def test_money_creation(self):
        """Test creating money values"""
        money = Money.nok(1000)
        assert money.amount == 1000
        assert money.currency == "NOK"

        money = Money.eur(100)
        assert money.amount == 100
        assert money.currency == "EUR"

    def test_money_arithmetic(self):
        """Test money arithmetic operations"""
        m1 = Money.nok(1000)
        m2 = Money.nok(500)

        # Addition
        result = m1 + m2
        assert result.amount == 1500
        assert result.currency == "NOK"

        # Subtraction
        result = m1 - m2
        assert result.amount == 500

        # Multiplication
        result = m1 * 2
        assert result.amount == 2000

        # Division
        result = m1 / 2
        assert result.amount == 500

    def test_money_currency_mismatch(self):
        """Test that operations with different currencies fail"""
        m1 = Money.nok(1000)
        m2 = Money.eur(100)

        with pytest.raises(ValueError):
            m1 + m2

        with pytest.raises(ValueError):
            m1 - m2

    def test_money_comparison(self):
        """Test money comparison operations"""
        m1 = Money.nok(1000)
        m2 = Money.nok(500)
        m3 = Money.nok(1000)

        assert m1 > m2
        assert m2 < m1
        assert m1 == m3
        assert m1 >= m3
        assert m2 <= m1

    def test_money_conversion(self):
        """Test currency conversion"""
        eur = Money.eur(100)
        nok = eur.to_nok(exchange_rate=11.5)
        assert nok.amount == 1150
        assert nok.currency == "NOK"


class TestCostPerUnit:
    """Test CostPerUnit value object"""

    def test_cost_per_unit_creation(self):
        """Test creating cost per unit"""
        cost = CostPerUnit.nok_per_kwh(2.5)
        assert cost.value == 2.5
        assert cost.currency == "NOK"
        assert cost.unit == "kWh"

    def test_calculate_total(self):
        """Test calculating total cost"""
        cost = CostPerUnit.nok_per_kwh(2.5)
        total = cost.calculate_total(quantity=100)
        assert total.amount == 250
        assert total.currency == "NOK"


class TestCashFlow:
    """Test CashFlow class"""

    def test_cash_flow_creation(self):
        """Test creating cash flow"""
        flows = [Money.nok(-10000), Money.nok(3000), Money.nok(3000), Money.nok(3000)]
        periods = [0, 1, 2, 3]
        cf = CashFlow(flows, periods)

        assert len(cf.flows) == 4
        assert cf.currency == "NOK"

    def test_npv_calculation(self):
        """Test NPV calculation"""
        flows = [Money.nok(-10000), Money.nok(3000), Money.nok(3000), Money.nok(3000), Money.nok(3000)]
        periods = [0, 1, 2, 3, 4]
        cf = CashFlow(flows, periods)

        npv = cf.npv(discount_rate=0.1)
        assert npv.currency == "NOK"
        # NPV should be negative for this cash flow at 10% discount
        assert npv.amount < 0

        # With 0% discount rate, NPV should equal sum
        npv_zero = cf.npv(discount_rate=0)
        assert npv_zero.amount == 2000  # -10000 + 4*3000

    def test_payback_period(self):
        """Test payback period calculation"""
        flows = [Money.nok(-10000), Money.nok(3000), Money.nok(3000), Money.nok(4000), Money.nok(2000)]
        periods = [0, 1, 2, 3, 4]
        cf = CashFlow(flows, periods)

        payback = cf.payback_period()
        assert payback is not None
        assert 3 < payback < 4  # Should be between year 3 and 4

    def test_total_cash_flow(self):
        """Test total cash flow calculation"""
        flows = [Money.nok(-10000), Money.nok(3000), Money.nok(3000), Money.nok(3000)]
        periods = [0, 1, 2, 3]
        cf = CashFlow(flows, periods)

        total = cf.total()
        assert total.amount == -1000  # -10000 + 9000
        assert total.currency == "NOK"


class TestEnergyPrice:
    """Test EnergyPrice value object"""

    def test_energy_price_creation(self):
        """Test creating energy price"""
        price = EnergyPrice.from_nok_per_kwh(1.5)
        assert price.nok_per_kwh == 1.5
        assert price.ore_per_kwh == 150

    def test_energy_price_from_ore(self):
        """Test creating from øre"""
        price = EnergyPrice.from_ore_per_kwh(150)
        assert price.nok_per_kwh == 1.5

    def test_energy_price_from_eur(self):
        """Test creating from EUR/MWh"""
        price = EnergyPrice.from_eur_per_mwh(50, exchange_rate=11.5)
        # 50 EUR/MWh * 11.5 = 575 NOK/MWh = 0.575 NOK/kWh
        assert abs(price.nok_per_kwh - 0.575) < 0.001

    def test_total_cost_calculation(self):
        """Test calculating total cost for energy"""
        price = EnergyPrice.from_nok_per_kwh(1.5)
        energy = Energy.from_kwh(100)
        total = price.total_cost(energy)
        assert total == 150