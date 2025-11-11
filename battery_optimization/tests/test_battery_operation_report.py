"""
Test suite for BatteryOperationReport class.

Validates:
- Data loading and filtering
- Period configuration (3weeks, 1month, 3months, custom)
- Theme application
- Interactive feature generation
- Export functionality (HTML, PNG)
- Summary metrics calculation
"""

import unittest
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.reporting import SimulationResult, BatteryOperationReport


class TestBatteryOperationReport(unittest.TestCase):
    """Test cases for BatteryOperationReport class."""

    @classmethod
    def setUpClass(cls):
        """Create synthetic test data once for all tests."""
        cls.temp_dir = Path(tempfile.mkdtemp())

        # Generate synthetic hourly data for full year
        start_date = pd.Timestamp('2024-01-01')
        timestamps = pd.date_range(start_date, periods=8760, freq='h')

        # Synthetic patterns
        hours = timestamps.hour
        days = timestamps.dayofyear

        # Solar production (sinusoidal with daily and seasonal variation)
        solar_base = 50 * np.sin(2 * np.pi * hours / 24) * np.sin(2 * np.pi * days / 365)
        solar_production = np.maximum(solar_base, 0)

        # Consumption (higher during business hours)
        consumption_base = 30 + 20 * np.sin(2 * np.pi * hours / 24)
        consumption = np.maximum(consumption_base, 10)

        # Spot price (higher during peak hours)
        spot_price = 0.5 + 0.3 * np.sin(2 * np.pi * hours / 24) + 0.1 * np.random.randn(len(timestamps))

        # Battery operations (simplified)
        battery_kwh = 80
        battery_kw = 40
        soc = np.zeros(len(timestamps))
        soc[0] = 0.5 * battery_kwh

        battery_power = np.zeros(len(timestamps))
        for i in range(1, len(timestamps)):
            net_power = solar_production[i] - consumption[i]
            if net_power > 0 and soc[i-1] < 0.8 * battery_kwh:
                # Charge
                charge_power = min(net_power, battery_kw, (0.8 * battery_kwh - soc[i-1]))
                battery_power[i] = charge_power
                soc[i] = soc[i-1] + charge_power * 0.9  # 90% efficiency
            elif net_power < 0 and soc[i-1] > 0.2 * battery_kwh:
                # Discharge
                discharge_power = min(-net_power, battery_kw, (soc[i-1] - 0.2 * battery_kwh))
                battery_power[i] = -discharge_power
                soc[i] = soc[i-1] - discharge_power / 0.9
            else:
                soc[i] = soc[i-1]

        # Grid power
        grid_power = consumption - solar_production - battery_power

        # Curtailment (simplified)
        curtailment = np.maximum(solar_production - consumption - battery_kw, 0)

        # Create SimulationResult
        cls.result = SimulationResult(
            scenario_name='test_battery_operation',
            timestamp=timestamps,
            production_dc_kw=solar_production * 1.05,  # DC slightly higher
            production_ac_kw=solar_production,
            consumption_kw=consumption,
            grid_power_kw=grid_power,
            battery_power_ac_kw=battery_power,
            battery_soc_kwh=soc,
            curtailment_kw=curtailment,
            spot_price=spot_price,
            cost_summary={
                'total_cost_nok': 50000,
                'energy_cost_nok': 35000,
                'power_cost_nok': 10000,
                'degradation_cost_nok': 5000
            },
            battery_config={
                'capacity_kwh': battery_kwh,
                'power_kw': battery_kw,
                'min_soc_pct': 20,
                'max_soc_pct': 80,
                'efficiency': 0.9
            },
            strategy_config={
                'type': 'RollingHorizon',
                'horizon_hours': 168
            },
            simulation_metadata={
                'grid_limit_kw': 77,
                'test_data': True
            }
        )

    @classmethod
    def tearDownClass(cls):
        """Clean up temporary directory."""
        shutil.rmtree(cls.temp_dir)

    def test_initialization_3weeks(self):
        """Test report initialization with 3-week period."""
        report = BatteryOperationReport(
            result=self.result,
            output_dir=self.temp_dir,
            period='3weeks'
        )

        self.assertEqual(report.period, '3weeks')
        self.assertEqual(report.battery_kwh, 80)
        self.assertEqual(report.battery_kw, 40)
        self.assertIsNotNone(report.df)
        self.assertGreater(len(report.df), 0)

    def test_initialization_1month(self):
        """Test report initialization with 1-month period."""
        report = BatteryOperationReport(
            result=self.result,
            output_dir=self.temp_dir,
            period='1month',
            start_date='2024-06-01'
        )

        self.assertEqual(report.period, '1month')
        # Should have ~720 hours (30 days)
        self.assertGreater(len(report.df), 700)
        self.assertLess(len(report.df), 750)

    def test_initialization_custom_period(self):
        """Test report initialization with custom period."""
        report = BatteryOperationReport(
            result=self.result,
            output_dir=self.temp_dir,
            period='custom',
            start_date='2024-03-01',
            end_date='2024-03-15'
        )

        self.assertEqual(report.period, 'custom')
        # Should have ~336 hours (14 days)
        self.assertGreater(len(report.df), 330)
        self.assertLess(len(report.df), 350)

    def test_invalid_period(self):
        """Test that invalid period raises ValueError."""
        with self.assertRaises(ValueError):
            BatteryOperationReport(
                result=self.result,
                output_dir=self.temp_dir,
                period='invalid_period'
            )

    def test_custom_period_missing_dates(self):
        """Test that custom period without dates raises ValueError."""
        with self.assertRaises(ValueError):
            BatteryOperationReport(
                result=self.result,
                output_dir=self.temp_dir,
                period='custom'
            )

    def test_battery_dimension_override(self):
        """Test manual battery dimension override."""
        report = BatteryOperationReport(
            result=self.result,
            output_dir=self.temp_dir,
            period='3weeks',
            battery_kwh=100,
            battery_kw=50
        )

        self.assertEqual(report.battery_kwh, 100)
        self.assertEqual(report.battery_kw, 50)

    def test_data_filtering(self):
        """Test that data is correctly filtered to period."""
        report = BatteryOperationReport(
            result=self.result,
            output_dir=self.temp_dir,
            period='3weeks',
            start_date='2024-06-01'
        )

        # Check date range
        start = report.df.index[0]
        end = report.df.index[-1]

        self.assertGreaterEqual(start, pd.Timestamp('2024-06-01'))
        self.assertLess(end, pd.Timestamp('2024-06-23'))  # 21 days later

    def test_calculated_columns(self):
        """Test that calculated columns are added correctly."""
        report = BatteryOperationReport(
            result=self.result,
            output_dir=self.temp_dir,
            period='3weeks'
        )

        # Check for calculated columns
        self.assertIn('soc_pct', report.df.columns)
        self.assertIn('hour', report.df.columns)
        self.assertIn('weekday', report.df.columns)
        self.assertIn('is_peak', report.df.columns)

        # Validate SOC percentage range
        self.assertGreaterEqual(report.df['soc_pct'].min(), 0)
        self.assertLessEqual(report.df['soc_pct'].max(), 100)

    def test_summary_metrics_calculation(self):
        """Test summary metrics calculation."""
        report = BatteryOperationReport(
            result=self.result,
            output_dir=self.temp_dir,
            period='1month'
        )

        metrics = report.get_summary_metrics()

        # Check required keys
        required_keys = [
            'period', 'timesteps', 'duration_hours',
            'production_kwh', 'consumption_kwh',
            'grid_import_kwh', 'grid_export_kwh',
            'battery_charge_kwh', 'battery_discharge_kwh',
            'equivalent_cycles', 'utilization_pct',
            'soc_min_pct', 'soc_max_pct', 'soc_mean_pct'
        ]

        for key in required_keys:
            self.assertIn(key, metrics)

        # Validate ranges
        self.assertGreaterEqual(metrics['equivalent_cycles'], 0)
        self.assertGreaterEqual(metrics['utilization_pct'], 0)
        self.assertLessEqual(metrics['utilization_pct'], 100)
        self.assertGreaterEqual(metrics['soc_min_pct'], 0)
        self.assertLessEqual(metrics['soc_max_pct'], 100)

    def test_html_generation(self):
        """Test HTML report generation."""
        report = BatteryOperationReport(
            result=self.result,
            output_dir=self.temp_dir,
            period='3weeks'
        )

        html_path = report.generate()

        # Check file exists
        self.assertTrue(html_path.exists())
        self.assertEqual(html_path.suffix, '.html')

        # Check file has content
        self.assertGreater(html_path.stat().st_size, 1000)  # At least 1KB

        # Check HTML structure (basic validation)
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('plotly', content.lower())
            self.assertIn('battery operation', content.lower())

    def test_figure_tracking(self):
        """Test that figures are tracked in report generator."""
        report = BatteryOperationReport(
            result=self.result,
            output_dir=self.temp_dir,
            period='3weeks'
        )

        html_path = report.generate()

        # Check figure is tracked
        self.assertIn(html_path, report.figures)

    def test_multiple_periods(self):
        """Test generating reports for multiple periods."""
        periods = ['3weeks', '1month', '3months']

        for period in periods:
            with self.subTest(period=period):
                report = BatteryOperationReport(
                    result=self.result,
                    output_dir=self.temp_dir,
                    period=period
                )

                html_path = report.generate()
                self.assertTrue(html_path.exists())

    def test_edge_case_empty_period(self):
        """Test that requesting data outside available range raises error."""
        with self.assertRaises(ValueError):
            report = BatteryOperationReport(
                result=self.result,
                output_dir=self.temp_dir,
                period='custom',
                start_date='2023-01-01',
                end_date='2023-01-31'
            )

    def test_soc_limits_respected(self):
        """Test that SOC data respects configured limits."""
        report = BatteryOperationReport(
            result=self.result,
            output_dir=self.temp_dir,
            period='1month'
        )

        soc_min_pct = report.result.battery_config.get('min_soc_pct', 20)
        soc_max_pct = report.result.battery_config.get('max_soc_pct', 80)

        # SOC should mostly respect limits (with small tolerance for dynamics)
        self.assertGreaterEqual(report.df['soc_pct'].min(), soc_min_pct - 5)
        self.assertLessEqual(report.df['soc_pct'].max(), soc_max_pct + 5)


class TestBatteryOperationReportIntegration(unittest.TestCase):
    """Integration tests with real data structure."""

    def test_integration_with_trajectory_format(self):
        """Test report generation with typical trajectory.csv format."""
        # Simulate loading from trajectory.csv
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Create minimal trajectory CSV
            timestamps = pd.date_range('2024-06-01', periods=504, freq='h')  # 3 weeks
            trajectory_data = {
                'timestamp': timestamps,
                'P_pv_kw': 50 * np.random.rand(len(timestamps)),
                'P_load_kw': 30 + 10 * np.random.rand(len(timestamps)),
                'P_charge_kw': 20 * np.random.rand(len(timestamps)),
                'P_discharge_kw': 20 * np.random.rand(len(timestamps)),
                'P_grid_import_kw': 10 * np.random.rand(len(timestamps)),
                'P_grid_export_kw': 10 * np.random.rand(len(timestamps)),
                'E_battery_kwh': 40 + 30 * np.random.rand(len(timestamps)),
                'P_curtail_kw': 5 * np.random.rand(len(timestamps)),
                'spot_price_nok': 0.5 + 0.3 * np.random.rand(len(timestamps))
            }

            df = pd.DataFrame(trajectory_data)

            # Create SimulationResult
            result = SimulationResult(
                scenario_name='integration_test',
                timestamp=df['timestamp'],
                production_dc_kw=df['P_pv_kw'].values * 1.05,
                production_ac_kw=df['P_pv_kw'].values,
                consumption_kw=df['P_load_kw'].values,
                grid_power_kw=df['P_grid_import_kw'].values - df['P_grid_export_kw'].values,
                battery_power_ac_kw=df['P_charge_kw'].values - df['P_discharge_kw'].values,
                battery_soc_kwh=df['E_battery_kwh'].values,
                curtailment_kw=df['P_curtail_kw'].values,
                spot_price=df['spot_price_nok'].values,
                cost_summary={'total_cost_nok': 10000},
                battery_config={'capacity_kwh': 80, 'power_kw': 40},
                strategy_config={'type': 'RollingHorizon'},
                simulation_metadata={}
            )

            # Generate report
            report = BatteryOperationReport(
                result=result,
                output_dir=temp_dir,
                period='3weeks'
            )

            html_path = report.generate()
            self.assertTrue(html_path.exists())

        finally:
            shutil.rmtree(temp_dir)


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()
