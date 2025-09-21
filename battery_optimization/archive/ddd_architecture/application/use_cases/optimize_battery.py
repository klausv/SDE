"""
Use case for battery optimization
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional
import pandas as pd
from pathlib import Path

from config import ConfigurationManager
from domain.models.battery import BatterySpecification
from domain.models.solar_system import PVSystem, PVSystemSpecification
from domain.models.load_profile import LoadProfile
from domain.value_objects.energy import Energy, Power
from domain.value_objects.money import Money, CostPerUnit
from domain.services.optimization_service import (
    BatteryOptimizationService,
    OptimizationObjective,
    OptimizationConstraints,
    OptimizationResult
)
from infrastructure.data_sources import ENTSOEClient, PVGISClient
from lib.energy_toolkit.tariffs import LnettCommercialTariff


@dataclass
class OptimizeBatteryRequest:
    """Request for battery optimization"""
    battery_cost_nok_per_kwh: float
    optimization_metric: str = 'npv'  # 'npv', 'irr', 'payback'
    max_battery_capacity_kwh: float = 200
    max_battery_power_kw: float = 100
    use_cached_data: bool = True


@dataclass
class OptimizeBatteryResponse:
    """Response from battery optimization"""
    optimal_capacity_kwh: float
    optimal_power_kw: float
    npv_nok: float
    irr_percentage: float
    payback_years: float
    annual_savings_nok: float
    self_consumption_rate: float
    peak_reduction_percentage: float
    detailed_results: Dict[str, Any]


class OptimizeBatteryUseCase:
    """Use case for optimizing battery size"""

    def __init__(self, config_manager: ConfigurationManager):
        self.config = config_manager
        self.entsoe_client = ENTSOEClient()
        self.pvgis_client = PVGISClient()
        self.tariff = LnettCommercialTariff()

    def execute(self, request: OptimizeBatteryRequest) -> OptimizeBatteryResponse:
        """
        Execute battery optimization

        Args:
            request: Optimization request parameters

        Returns:
            Optimization results
        """
        # 1. Load configuration
        site_config = self.config.site
        system_config = self.config.system
        economic_config = self.config.economic

        # 2. Fetch electricity prices
        prices = self._fetch_electricity_prices(request.use_cached_data)

        # 3. Fetch solar production data
        pv_production = self._fetch_pv_production(
            site_config.latitude,
            site_config.longitude,
            system_config,
            request.use_cached_data
        )

        # 4. Generate load profile
        load_profile = self._generate_load_profile(
            site_config.annual_consumption_kwh,
            site_config.profile_type
        )

        # 5. Setup PV system
        pv_system_spec = PVSystemSpecification(
            installed_capacity=Power.from_kw(system_config.installed_capacity_kwp),
            inverter_capacity=Power.from_kw(system_config.inverter_capacity_kw),
            azimuth=system_config.azimuth,
            tilt=system_config.tilt,
            soiling_loss=system_config.losses.get('soiling', 0.02),
            shading_loss=system_config.losses.get('shading', 0.03),
            inverter_efficiency=system_config.losses.get('inverter_efficiency', 0.97)
        )

        pv_system = PVSystem(
            pv_system_spec,
            site_config.latitude,
            site_config.longitude
        )

        # 6. Setup optimization
        objective = OptimizationObjective(
            metric=request.optimization_metric,
            minimize=request.optimization_metric == 'payback'
        )

        constraints = OptimizationConstraints(
            max_battery_capacity=Energy.from_kwh(request.max_battery_capacity_kwh),
            max_battery_power=Power.from_kw(request.max_battery_power_kw),
            min_battery_capacity=Energy.from_kwh(0),
            min_battery_power=Power.from_kw(0),
            grid_export_limit=Power.from_kw(site_config.grid_max_export_kw)
        )

        battery_cost = CostPerUnit.nok_per_kwh(request.battery_cost_nok_per_kwh)

        # 7. Run optimization
        optimizer = BatteryOptimizationService(
            pv_system,
            load_profile,
            prices,
            self._get_tariff_structure(),
            economic_config.discount_rate
        )

        result = optimizer.optimize_battery_size(
            objective,
            constraints,
            battery_cost,
            economic_config.project_lifetime_years
        )

        # 8. Prepare response
        return OptimizeBatteryResponse(
            optimal_capacity_kwh=result.optimal_capacity.kwh,
            optimal_power_kw=result.optimal_power.kw,
            npv_nok=result.npv.amount,
            irr_percentage=result.irr * 100,
            payback_years=result.payback_years,
            annual_savings_nok=result.annual_savings.amount,
            self_consumption_rate=result.self_consumption_rate,
            peak_reduction_percentage=result.peak_reduction_percentage,
            detailed_results=result.summary_dict()
        )

    def _fetch_electricity_prices(self, use_cache: bool) -> pd.Series:
        """Fetch electricity prices from ENTSO-E"""
        import datetime

        # Get prices for current year
        year = datetime.datetime.now().year
        start_date = datetime.datetime(year, 1, 1)
        end_date = datetime.datetime(year, 12, 31, 23)

        # Fetch EUR prices
        prices_eur = self.entsoe_client.fetch_day_ahead_prices(
            start_date,
            end_date,
            bidding_zone='NO2',  # Stavanger
            use_cache=use_cache
        )

        # Convert to NOK/kWh
        prices_nok = self.entsoe_client.convert_to_nok(prices_eur)

        return prices_nok

    def _fetch_pv_production(
        self,
        latitude: float,
        longitude: float,
        system_config: Any,
        use_cache: bool
    ) -> pd.Series:
        """Fetch PV production data from PVGIS"""
        pv_spec = PVSystemSpecification(
            installed_capacity=Power.from_kw(system_config.installed_capacity_kwp),
            inverter_capacity=Power.from_kw(system_config.inverter_capacity_kw),
            azimuth=system_config.azimuth,
            tilt=system_config.tilt
        )

        production = self.pvgis_client.fetch_hourly_production(
            latitude,
            longitude,
            pv_spec,
            year=2019,  # PVGIS typical year
            use_cache=use_cache
        )

        return production

    def _generate_load_profile(
        self,
        annual_consumption_kwh: float,
        profile_type: str
    ) -> LoadProfile:
        """Generate load profile"""
        return LoadProfile.from_generator(
            annual_consumption=Energy.from_kwh(annual_consumption_kwh),
            profile_type=profile_type,
            year=2024
        )

    def _get_tariff_structure(self) -> Dict[str, Any]:
        """Get tariff structure configuration"""
        return self.config.tariff