"""
Tests for battery domain model
"""
import pytest
from domain.models.battery import (
    Battery,
    BatterySpecification,
    BatteryState,
    BatteryDegradation
)
from domain.value_objects.energy import Energy, Power


class TestBatterySpecification:
    """Test BatterySpecification"""

    def test_valid_specification(self):
        """Test creating valid battery specification"""
        spec = BatterySpecification(
            capacity=Energy.from_kwh(100),
            max_power=Power.from_kw(50),
            efficiency=0.95,
            min_soc=0.10,
            max_soc=0.95
        )

        assert spec.capacity.kwh == 100
        assert spec.max_power.kw == 50
        assert spec.efficiency == 0.95

    def test_invalid_efficiency(self):
        """Test that invalid efficiency raises error"""
        with pytest.raises(ValueError):
            BatterySpecification(
                capacity=Energy.from_kwh(100),
                max_power=Power.from_kw(50),
                efficiency=1.5  # Invalid > 1
            )

    def test_invalid_soc_limits(self):
        """Test that invalid SOC limits raise error"""
        with pytest.raises(ValueError):
            BatterySpecification(
                capacity=Energy.from_kwh(100),
                max_power=Power.from_kw(50),
                min_soc=0.5,
                max_soc=0.3  # min > max
            )

    def test_usable_capacity(self):
        """Test usable capacity calculation"""
        spec = BatterySpecification(
            capacity=Energy.from_kwh(100),
            max_power=Power.from_kw(50),
            min_soc=0.10,
            max_soc=0.90
        )

        assert spec.usable_capacity.kwh == 80  # (0.90 - 0.10) * 100

    def test_c_rate_limits(self):
        """Test C-rate limited power"""
        spec = BatterySpecification(
            capacity=Energy.from_kwh(100),
            max_power=Power.from_kw(200),  # High power
            max_c_rate_charge=0.5,  # But limited by C-rate
            max_c_rate_discharge=0.5
        )

        assert spec.max_charge_power.kw == 50  # Limited by C-rate
        assert spec.max_discharge_power.kw == 50


class TestBatteryDegradation:
    """Test BatteryDegradation model"""

    def test_degradation_update(self):
        """Test degradation calculation"""
        degradation = BatteryDegradation(
            calendar_degradation_rate=0.02,  # 2% per year
            cycle_degradation_rate=0.0001,  # 0.01% per cycle
            current_capacity_retention=1.0
        )

        # Apply 1 year and 365 cycles
        degradation.update(cycles=365, time_elapsed_years=1.0)

        # Should lose ~2% from calendar + 3.65% from cycles
        expected_retention = 1.0 - 0.02 - (365 * 0.0001)
        assert abs(degradation.current_capacity_retention - expected_retention) < 0.001

    def test_minimum_capacity_retention(self):
        """Test that capacity retention doesn't go below 70%"""
        degradation = BatteryDegradation()

        # Apply extreme degradation
        degradation.update(cycles=50000, time_elapsed_years=20)

        assert degradation.current_capacity_retention >= 0.7


class TestBattery:
    """Test Battery model"""

    def test_battery_initialization(self):
        """Test battery initialization"""
        spec = BatterySpecification(
            capacity=Energy.from_kwh(100),
            max_power=Power.from_kw(50)
        )
        battery = Battery(spec)

        assert battery.state == BatteryState.IDLE
        assert battery.soc == 0.5  # Default 50% SOC
        assert battery.current_energy.kwh == 50

    def test_battery_charge(self):
        """Test battery charging"""
        spec = BatterySpecification(
            capacity=Energy.from_kwh(100),
            max_power=Power.from_kw(50),
            efficiency=0.90
        )
        battery = Battery(spec)

        # Charge at 20 kW for 1 hour
        energy_to_battery, energy_from_grid = battery.charge(
            power=Power.from_kw(20),
            duration_hours=1.0
        )

        # Should charge 20 kWh to battery
        assert energy_to_battery.kwh == 20
        # Should draw more from grid due to efficiency
        assert energy_from_grid.kwh == pytest.approx(20 / 0.90, rel=0.01)
        # SOC should increase
        assert battery.soc > 0.5

    def test_battery_discharge(self):
        """Test battery discharging"""
        spec = BatterySpecification(
            capacity=Energy.from_kwh(100),
            max_power=Power.from_kw(50),
            efficiency=0.90
        )
        battery = Battery(spec)

        # Discharge at 20 kW for 1 hour
        energy_from_battery, energy_to_grid = battery.discharge(
            power=Power.from_kw(20),
            duration_hours=1.0
        )

        # Should discharge 20 kWh from battery
        assert energy_from_battery.kwh == 20
        # Should deliver less to grid due to efficiency
        assert energy_to_grid.kwh == pytest.approx(20 * 0.90, rel=0.01)
        # SOC should decrease
        assert battery.soc < 0.5

    def test_charge_limit_by_capacity(self):
        """Test that charging is limited by available capacity"""
        spec = BatterySpecification(
            capacity=Energy.from_kwh(100),
            max_power=Power.from_kw(50),
            max_soc=0.90
        )
        battery = Battery(spec)
        battery.soc = 0.85  # Near full

        # Try to charge 20 kWh
        energy_to_battery, _ = battery.charge(
            power=Power.from_kw(20),
            duration_hours=1.0
        )

        # Should only charge to max SOC (5 kWh available)
        assert energy_to_battery.kwh == 5
        assert battery.soc == 0.90

    def test_discharge_limit_by_capacity(self):
        """Test that discharging is limited by available energy"""
        spec = BatterySpecification(
            capacity=Energy.from_kwh(100),
            max_power=Power.from_kw(50),
            min_soc=0.10
        )
        battery = Battery(spec)
        battery.soc = 0.15  # Near empty

        # Try to discharge 20 kWh
        energy_from_battery, _ = battery.discharge(
            power=Power.from_kw(20),
            duration_hours=1.0
        )

        # Should only discharge to min SOC (5 kWh available)
        assert energy_from_battery.kwh == 5
        assert battery.soc == 0.10

    def test_cannot_charge_while_discharging(self):
        """Test that charging is prevented during discharge"""
        spec = BatterySpecification(
            capacity=Energy.from_kwh(100),
            max_power=Power.from_kw(50)
        )
        battery = Battery(spec)

        # Start discharging
        battery.state = BatteryState.DISCHARGING

        # Try to charge
        with pytest.raises(ValueError):
            battery.charge(Power.from_kw(20), 1.0)

    def test_available_capacities(self):
        """Test available charge and discharge capacity calculations"""
        spec = BatterySpecification(
            capacity=Energy.from_kwh(100),
            max_power=Power.from_kw(50),
            min_soc=0.10,
            max_soc=0.90
        )
        battery = Battery(spec)
        battery.soc = 0.5  # 50% SOC

        # Available for charging: 90% - 50% = 40%
        assert battery.available_charge_capacity.kwh == 40

        # Available for discharging: 50% - 10% = 40%
        assert battery.available_discharge_capacity.kwh == 40

    def test_battery_aging(self):
        """Test battery aging over one year"""
        spec = BatterySpecification(
            capacity=Energy.from_kwh(100),
            max_power=Power.from_kw(50)
        )
        battery = Battery(spec)

        # Simulate daily cycling for tracking
        battery.cycles_today = 1.0

        # Age one year
        battery.age_one_year()

        # Degradation should have been applied
        assert battery.degradation.age_years == 1.0
        assert battery.degradation.current_capacity_retention < 1.0

        # Daily counter should be reset
        assert battery.cycles_today == 0.0

    def test_energy_throughput_tracking(self):
        """Test that energy throughput is tracked"""
        spec = BatterySpecification(
            capacity=Energy.from_kwh(100),
            max_power=Power.from_kw(50)
        )
        battery = Battery(spec)

        initial_throughput = battery.energy_throughput_kwh

        # Charge and discharge
        battery.charge(Power.from_kw(20), 1.0)
        battery.idle()
        battery.discharge(Power.from_kw(20), 1.0)

        # Throughput should increase
        assert battery.energy_throughput_kwh > initial_throughput