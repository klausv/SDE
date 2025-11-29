"""
Battery Optimization System

A comprehensive battery energy storage system (BESS) optimization framework
for analyzing economic viability through peak shaving, energy arbitrage,
and power tariff reduction strategies.

Main Components:
- Configuration: Simulation and economic configuration management
- Infrastructure: Shared data infrastructure (pricing, weather, tariffs)
- Optimization: Battery optimization algorithms with registry system
- Simulation: Orchestration of simulations over various time horizons
- Persistence: Result storage and metadata tracking
- Operational: Battery state management and control

Quick Start:
    >>> from src.config import SimulationConfig
    >>> from src.optimization import OptimizerFactory
    >>> from src.simulation import RollingHorizonOrchestrator
    >>>
    >>> # Load configuration
    >>> config = SimulationConfig.from_yaml("configs/rolling_horizon.yaml")
    >>>
    >>> # Create optimizer
    >>> optimizer = OptimizerFactory.create_from_config(config)
    >>>
    >>> # Run simulation
    >>> orchestrator = RollingHorizonOrchestrator(config, optimizer)
    >>> results = orchestrator.run(price_data, production_data)
    >>>
    >>> # Save results
    >>> from src.persistence import ResultStorage
    >>> storage = ResultStorage("results/")
    >>> result_id = results.save_to_storage(storage)

Public API Exports:
    Configuration:
        - SimulationConfig: Main configuration dataclass
        - LegacyConfigAdapter: Adapter for old config files

    Infrastructure:
        - PriceLoader, PriceData: Electricity price management
        - SolarProductionLoader, SolarProductionData: Solar production management
        - TariffLoader: Grid tariff management

    Optimization:
        - OptimizerFactory: Create optimizers from configuration
        - OptimizerRegistry: Discover and filter optimization methods
        - BaseOptimizer, OptimizationResult: Base classes

    Simulation:
        - SimulationResults: Result container with persistence
        - RollingHorizonOrchestrator: Rolling horizon simulation
        - MonthlyOrchestrator: Monthly simulation
        - YearlyOrchestrator: Yearly simulation

    Persistence:
        - ResultStorage: Result storage and retrieval
        - MetadataBuilder: Comprehensive metadata generation
        - StorageFormat: Storage format options

    Operational:
        - BatterySystemState: Battery state management

Architecture Principles:
    1. Layered Architecture:
       - Infrastructure layer: Shared data services
       - Domain layer: Core battery optimization logic
       - Application layer: Simulation orchestration
       - Persistence layer: Result storage

    2. Dependency Flow:
       Application → Domain → Infrastructure
       (Higher layers depend on lower layers, never reverse)

    3. Module Boundaries:
       - infrastructure/: No dependencies on other modules
       - optimization/: Depends only on infrastructure
       - simulation/: Depends on optimization and infrastructure
       - persistence/: Standalone, used by simulation

    4. Configuration:
       - Dataclass-based for type safety
       - YAML-based for human readability
       - Validation on construction

    5. Extensibility:
       - Registry pattern for optimizers
       - Factory pattern for creation
       - Adapter pattern for legacy compatibility
"""

# Version information
__version__ = "2.0.0"
__author__ = "Klaus"

# Configuration
from src.config.simulation_config import SimulationConfig

# Infrastructure
from src.infrastructure.pricing import PriceLoader, PriceData
from src.infrastructure.weather import SolarProductionLoader, SolarProductionData
from src.infrastructure.tariffs import TariffLoader

# Optimization
from src.optimization import (
    OptimizerFactory,
    OptimizerRegistry,
    OptimizerMetadata,
    BaseOptimizer,
    OptimizationResult,
    SolverType,
    TimeScale,
)

# Simulation
from src.simulation.simulation_results import SimulationResults
from src.simulation.rolling_horizon_orchestrator import RollingHorizonOrchestrator
from src.simulation.monthly_orchestrator import MonthlyOrchestrator
from src.simulation.yearly_orchestrator import YearlyOrchestrator

# Persistence
from src.persistence import (
    ResultStorage,
    MetadataBuilder,
    StorageFormat,
)

# Operational
from src.operational import BatterySystemState

# Public API
__all__ = [
    # Version
    "__version__",
    "__author__",

    # Configuration
    "SimulationConfig",

    # Infrastructure
    "PriceLoader",
    "PriceData",
    "SolarProductionLoader",
    "SolarProductionData",
    "TariffLoader",

    # Optimization
    "OptimizerFactory",
    "OptimizerRegistry",
    "OptimizerMetadata",
    "BaseOptimizer",
    "OptimizationResult",
    "SolverType",
    "TimeScale",

    # Simulation
    "SimulationResults",
    "RollingHorizonOrchestrator",
    "MonthlyOrchestrator",
    "YearlyOrchestrator",

    # Persistence
    "ResultStorage",
    "MetadataBuilder",
    "StorageFormat",

    # Operational
    "BatterySystemState",
]
