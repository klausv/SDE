"""
Metadata builder for comprehensive simulation result tracking.

Generates rich metadata for simulation results including:
- Configuration details (battery, economic assumptions)
- Data sources (price data, production data)
- Optimizer method and parameters
- Execution performance metrics
- System information
- Version information

Enables full reproducibility and traceability of simulation results.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional
import platform
import sys
from pathlib import Path


@dataclass
class ConfigurationMetadata:
    """Configuration details used in simulation."""
    # Battery configuration
    battery_capacity_kwh: float
    battery_power_kw: float
    battery_efficiency: float
    initial_soc_percent: float
    min_soc_percent: float
    max_soc_percent: float

    # Economic assumptions
    discount_rate: float
    project_years: int
    eur_to_nok: float
    installation_markup: float
    degradation_annual_rate: float
    degradation_capacity_floor: float

    # Simulation settings
    time_resolution: str  # 'PT60M', 'PT15M', etc.
    mode: str             # 'rolling_horizon', 'monthly', etc.

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DataSourceMetadata:
    """Data sources used in simulation."""
    price_data_source: str          # File path or 'entsoe_api'
    production_data_source: str     # File path or 'pvgis_api'
    consumption_data_source: str    # File path or 'generated'

    # Data statistics
    price_min_nok_kwh: Optional[float] = None
    price_max_nok_kwh: Optional[float] = None
    price_mean_nok_kwh: Optional[float] = None

    production_max_kw: Optional[float] = None
    production_annual_kwh: Optional[float] = None

    consumption_max_kw: Optional[float] = None
    consumption_annual_kwh: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class OptimizerMetadata:
    """Optimizer method and parameters."""
    method: str                     # 'rolling_horizon', 'milp', 'weekly', etc.
    solver: Optional[str] = None    # 'HiGHS', 'CBC', 'GLPK', etc.

    # Optimizer parameters
    horizon_hours: Optional[int] = None
    step_hours: Optional[int] = None
    mip_gap: Optional[float] = None
    time_limit_s: Optional[float] = None

    # Performance metrics
    solve_time_s: Optional[float] = None
    iterations: Optional[int] = None
    status: Optional[str] = None    # 'optimal', 'feasible', 'infeasible', etc.

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ExecutionMetadata:
    """Execution performance and system information."""
    # Timing
    start_time: datetime
    end_time: datetime
    execution_time_s: float

    # System information
    python_version: str
    platform: str
    hostname: str

    # Package versions
    numpy_version: Optional[str] = None
    pandas_version: Optional[str] = None
    pulp_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        # Convert datetime to ISO format
        d['start_time'] = self.start_time.isoformat()
        d['end_time'] = self.end_time.isoformat()
        return d


class MetadataBuilder:
    """
    Builder for comprehensive simulation result metadata.

    Usage:
        builder = MetadataBuilder()
        builder.set_configuration(config)
        builder.set_data_sources(price_data, production_data, consumption_data)
        builder.set_optimizer(method='rolling_horizon', solver='HiGHS')
        builder.start_timing()
        # ... run simulation ...
        builder.end_timing()
        metadata = builder.build()
    """

    def __init__(self):
        """Initialize metadata builder."""
        self.config_meta: Optional[ConfigurationMetadata] = None
        self.data_meta: Optional[DataSourceMetadata] = None
        self.optimizer_meta: Optional[OptimizerMetadata] = None
        self.execution_meta: Optional[ExecutionMetadata] = None

        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None

    def set_configuration(
        self,
        config: "SimulationConfig"  # Forward reference
    ) -> "MetadataBuilder":
        """
        Set configuration metadata from SimulationConfig.

        Args:
            config: SimulationConfig object

        Returns:
            self for method chaining
        """
        self.config_meta = ConfigurationMetadata(
            battery_capacity_kwh=config.battery.capacity_kwh,
            battery_power_kw=config.battery.power_kw,
            battery_efficiency=config.battery.efficiency,
            initial_soc_percent=config.battery.initial_soc_percent,
            min_soc_percent=config.battery.min_soc_percent,
            max_soc_percent=config.battery.max_soc_percent,
            discount_rate=config.economic.discount_rate,
            project_years=config.economic.project_years,
            eur_to_nok=config.economic.eur_to_nok,
            installation_markup=config.battery_economics.installation_markup,
            degradation_annual_rate=config.battery_economics.degradation.annual_rate,
            degradation_capacity_floor=config.battery_economics.degradation.capacity_floor,
            time_resolution=config.time_resolution,
            mode=config.mode
        )
        return self

    def set_data_sources(
        self,
        price_data: "PriceData",
        production_data: "SolarProductionData",
        consumption_data: Optional[Any] = None
    ) -> "MetadataBuilder":
        """
        Set data source metadata.

        Args:
            price_data: PriceData object
            production_data: SolarProductionData object
            consumption_data: Optional consumption data

        Returns:
            self for method chaining
        """
        price_stats = price_data.get_statistics()
        prod_stats = production_data.get_statistics()

        self.data_meta = DataSourceMetadata(
            price_data_source=price_data.source,
            production_data_source=production_data.source,
            consumption_data_source="provided" if consumption_data is not None else "none",
            price_min_nok_kwh=price_stats['min'],
            price_max_nok_kwh=price_stats['max'],
            price_mean_nok_kwh=price_stats['mean'],
            production_max_kw=prod_stats['max_kw'],
            production_annual_kwh=prod_stats['annual_kwh_estimate'],
            consumption_max_kw=None,  # TODO: Extract from consumption data if available
            consumption_annual_kwh=None
        )
        return self

    def set_optimizer(
        self,
        method: str,
        solver: Optional[str] = None,
        **kwargs
    ) -> "MetadataBuilder":
        """
        Set optimizer metadata.

        Args:
            method: Optimizer method name
            solver: Solver name (if applicable)
            **kwargs: Additional optimizer parameters

        Returns:
            self for method chaining

        Example:
            >>> builder.set_optimizer(
            ...     method='rolling_horizon',
            ...     solver='HiGHS',
            ...     horizon_hours=168,
            ...     step_hours=24
            ... )
        """
        self.optimizer_meta = OptimizerMetadata(
            method=method,
            solver=solver,
            **{k: v for k, v in kwargs.items() if hasattr(OptimizerMetadata, k)}
        )
        return self

    def start_timing(self) -> "MetadataBuilder":
        """
        Start execution timing.

        Returns:
            self for method chaining
        """
        self._start_time = datetime.now()
        return self

    def end_timing(self) -> "MetadataBuilder":
        """
        End execution timing and capture system information.

        Returns:
            self for method chaining
        """
        self._end_time = datetime.now()

        if self._start_time is None:
            raise RuntimeError("start_timing() must be called before end_timing()")

        execution_time_s = (self._end_time - self._start_time).total_seconds()

        # Get package versions
        numpy_version = None
        pandas_version = None
        pulp_version = None

        try:
            import numpy
            numpy_version = numpy.__version__
        except ImportError:
            pass

        try:
            import pandas
            pandas_version = pandas.__version__
        except ImportError:
            pass

        try:
            import pulp
            pulp_version = pulp.__version__
        except ImportError:
            pass

        self.execution_meta = ExecutionMetadata(
            start_time=self._start_time,
            end_time=self._end_time,
            execution_time_s=execution_time_s,
            python_version=sys.version,
            platform=platform.platform(),
            hostname=platform.node(),
            numpy_version=numpy_version,
            pandas_version=pandas_version,
            pulp_version=pulp_version
        )

        return self

    def build(self) -> Dict[str, Any]:
        """
        Build comprehensive metadata dictionary.

        Returns:
            Dictionary with all metadata sections

        Raises:
            RuntimeError: If required metadata not set
        """
        metadata = {
            'metadata_version': '1.0',
            'generated_at': datetime.now().isoformat()
        }

        if self.config_meta is not None:
            metadata['configuration'] = self.config_meta.to_dict()

        if self.data_meta is not None:
            metadata['data_sources'] = self.data_meta.to_dict()

        if self.optimizer_meta is not None:
            metadata['optimizer'] = self.optimizer_meta.to_dict()

        if self.execution_meta is not None:
            metadata['execution'] = self.execution_meta.to_dict()
        else:
            # Add warning if execution timing not captured
            metadata['warning'] = 'Execution metadata not captured (start_timing/end_timing not called)'

        return metadata

    @classmethod
    def quick_metadata(
        cls,
        mode: str,
        battery_kwh: float,
        battery_kw: float,
        optimizer_method: str,
        execution_time_s: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate minimal metadata quickly without full builder workflow.

        Args:
            mode: Simulation mode
            battery_kwh: Battery capacity
            battery_kw: Battery power
            optimizer_method: Optimizer method used
            execution_time_s: Optional execution time

        Returns:
            Minimal metadata dictionary

        Example:
            >>> metadata = MetadataBuilder.quick_metadata(
            ...     mode='rolling_horizon',
            ...     battery_kwh=80,
            ...     battery_kw=60,
            ...     optimizer_method='HiGHS_LP'
            ... )
        """
        return {
            'metadata_version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'mode': mode,
            'battery_kwh': battery_kwh,
            'battery_kw': battery_kw,
            'optimizer_method': optimizer_method,
            'execution_time_s': execution_time_s,
            'quick_metadata': True  # Flag to indicate this is minimal metadata
        }
