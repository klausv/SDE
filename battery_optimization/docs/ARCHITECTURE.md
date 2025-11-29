# Battery Optimization System Architecture

## Overview

This document describes the architecture of the Battery Optimization System, a comprehensive framework for analyzing the economic viability of battery energy storage systems (BESS) through peak shaving, energy arbitrage, and power tariff reduction.

## Architecture Principles

### 1. Layered Architecture

The system is organized into distinct layers with clear responsibilities:

```
┌─────────────────────────────────────────┐
│         Application Layer               │
│  (Simulation Orchestration, CLI)        │
└─────────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────┐
│          Domain Layer                   │
│   (Optimization Algorithms, Models)     │
└─────────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────┐
│      Infrastructure Layer               │
│  (Data Services, Persistence)           │
└─────────────────────────────────────────┘
```

**Dependency Flow:** Application → Domain → Infrastructure

- Higher layers depend on lower layers
- Lower layers NEVER depend on higher layers
- Each layer has well-defined interfaces

### 2. Module Boundaries

Clear separation of concerns with minimal coupling:

- **infrastructure/**: Shared data services (pricing, weather, tariffs)
- **optimization/**: Battery optimization algorithms and registry
- **simulation/**: Orchestration of simulations over time
- **persistence/**: Result storage and metadata tracking
- **operational/**: Battery state management and control
- **config/**: Configuration management (YAML, dataclasses)

### 3. Design Patterns

- **Registry Pattern**: OptimizerRegistry for method discovery
- **Factory Pattern**: OptimizerFactory for object creation
- **Adapter Pattern**: LegacyConfigAdapter for compatibility
- **Builder Pattern**: MetadataBuilder for complex object construction
- **Strategy Pattern**: BaseOptimizer for algorithm swapping

## Module Structure

### Infrastructure Layer (`src/infrastructure/`)

**Purpose**: Provide shared data services independent of domain logic

**Modules**:
- `pricing/`: Electricity price data management
  - `PriceLoader`: Load prices from CSV or ENTSO-E API
  - `PriceData`: Type-safe price data container
  - `ENTSOEClient`: ENTSO-E Transparency Platform API client

- `weather/`: Solar production data management
  - `SolarProductionLoader`: Load production from CSV or PVGIS API
  - `SolarProductionData`: Type-safe production data container
  - Capacity scaling and temporal filtering

- `tariffs/`: Grid tariff management
  - `TariffLoader`: Load tariff structures from YAML
  - Support for time-of-use and power tariffs

**Dependencies**: None (self-contained)

**Key Features**:
- Dataclass-based for type safety
- Automatic data validation
- Multiple data sources (files, APIs)
- Caching for API responses
- Timezone handling

### Domain Layer (Optimization)

#### Optimization (`src/optimization/`)

**Purpose**: Battery optimization algorithms with comprehensive method traceability

**Components**:
- `base_optimizer.py`: Abstract base class defining optimizer interface
- `optimizer_registry.py`: Registry system for method discovery
- `optimizer_factory.py`: Factory for creating optimizers from config
- Adapter classes: `rolling_horizon_adapter.py`, `monthly_lp_adapter.py`, `weekly_optimizer.py`

**OptimizerRegistry Features**:
- Rich metadata for each optimization method
- Capability-based filtering
- Performance characteristics
- Academic references
- Selection guidance

**Dependencies**: infrastructure (for battery state)

**Key Principles**:
- Common interface via `BaseOptimizer`
- Consistent result structure via `OptimizationResult`
- Method traceability via registry
- Extensible via registration

#### Operational (`src/operational/`)

**Purpose**: Battery state management for real-time control

**Components**:
- `state_manager.py`: `BatterySystemState` for persistent state tracking

**Dependencies**: None

### Application Layer

#### Simulation (`src/simulation/`)

**Purpose**: Orchestrate optimization over various time horizons

**Orchestrators**:
- `RollingHorizonOrchestrator`: Real-time operation with persistent state
- `MonthlyOrchestrator`: Single or multi-month analysis
- `YearlyOrchestrator`: Annual investment analysis

**Results**:
- `SimulationResults`: Comprehensive result container
  - Full time-series trajectory
  - Monthly aggregated summary
  - Economic metrics
  - Metadata integration
  - Persistence capabilities

**Dependencies**: optimization, infrastructure, persistence

**Workflow**:
```python
config → Orchestrator → Optimizer → Results → Storage
```

#### Configuration (`src/config/`)

**Purpose**: Type-safe configuration management

**Components**:
- `SimulationConfig`: Main dataclass with nested configurations
  - `BatteryConfig`: Battery parameters
  - `EconomicConfig`: Economic assumptions
  - `RollingHorizonConfig`: Rolling horizon settings
  - `YearlyConfig`: Yearly simulation settings

- `LegacyConfigAdapter`: Adapter for old JSON/dict configs

**Dependencies**: None

**Features**:
- YAML-based for human readability
- Dataclass-based for type safety
- Validation on construction
- Backwards compatibility via adapter

### Persistence Layer (`src/persistence/`)

**Purpose**: Result storage, retrieval, and metadata tracking

**Components**:
- `ResultStorage`: Multi-format result storage
  - Pickle (full object serialization)
  - JSON (human-readable)
  - Parquet (efficient columnar)

- `MetadataBuilder`: Comprehensive metadata generation
  - Configuration metadata
  - Data source metadata
  - Optimizer metadata
  - Execution metadata

**Dependencies**: None (standalone)

**Key Features**:
- Automatic result indexing
- Filtering and search
- Version tracking
- Reproducibility support

## Data Flow

### Typical Simulation Workflow

```
1. Configuration Loading
   ├─ SimulationConfig.from_yaml()
   └─ Validate configuration

2. Data Loading
   ├─ PriceLoader.from_entsoe_api() → PriceData
   ├─ SolarProductionLoader.from_pvgis_api() → SolarProductionData
   └─ Optional: consumption data

3. Optimizer Creation
   ├─ OptimizerFactory.create_from_config()
   └─ Registry provides metadata

4. Simulation Execution
   ├─ Orchestrator.run(price_data, production_data)
   ├─ Optimizer solves over time horizon
   └─ Results aggregation

5. Result Persistence
   ├─ MetadataBuilder.build() → metadata
   ├─ SimulationResults.save_to_storage()
   └─ ResultStorage manages files and index

6. Reporting (decoupled from execution)
   ├─ ResultStorage.load(result_id)
   ├─ Generate reports/plots
   └─ No re-computation needed
```

## Extensibility Points

### Adding New Optimization Methods

1. Implement `BaseOptimizer` interface
2. Register in `OptimizerRegistry` with metadata
3. Add factory method to `OptimizerFactory`
4. Create adapter if needed

Example:
```python
from src.optimization import OptimizerRegistry, OptimizerMetadata

OptimizerRegistry.register(OptimizerMetadata(
    name="new_method",
    display_name="New Optimization Method",
    description="...",
    solver_type=SolverType.LP,
    # ... other metadata
))
```

### Adding New Data Sources

1. Create loader class in `infrastructure/`
2. Return dataclass container (e.g., `PriceData`)
3. Follow naming convention: `{Type}Loader.from_{source}()`

### Adding New Storage Formats

1. Extend `StorageFormat` enum
2. Add save/load logic in `ResultStorage`
3. Update `result_index.json` schema if needed

## Testing Strategy

### Unit Tests
- Each module independently testable
- Mock external dependencies (APIs)
- Test data validation and edge cases

### Integration Tests
- Full workflow from config to results
- Use cached/sample data for reproducibility
- Validate result correctness

### Performance Tests
- Benchmark optimization solve times
- Memory usage profiling
- Scalability testing

## Future Enhancements

### Planned Improvements
1. **Real-time Integration**: Connect to actual battery management systems
2. **Forecast Integration**: Weather and price forecast APIs
3. **Multi-objective Optimization**: Pareto frontiers for tradeoffs
4. **Uncertainty Quantification**: Stochastic optimization variants
5. **Web Interface**: Interactive dashboard for configuration and analysis

### Architecture Considerations
- Maintain layer separation
- Avoid tight coupling
- Extensibility through registration patterns
- Backwards compatibility for configs

## Dependencies

### External Libraries
- **Core**: numpy, pandas, scipy
- **Optimization**: PuLP, HiGHS solver
- **Data**: requests (API clients)
- **Storage**: pickle, json, pyarrow (parquet)
- **Visualization**: matplotlib, plotly
- **Configuration**: PyYAML, dataclasses

### Dependency Hierarchy
```
infrastructure → (numpy, pandas, requests)
optimization → (infrastructure, scipy, pulp)
simulation → (optimization, infrastructure)
persistence → (pandas, numpy, pickle, json)
```

## Performance Considerations

### Computational Bottlenecks
1. **Optimization Solve**: Dominant cost (seconds to minutes)
2. **Data Loading**: Negligible with caching
3. **Result Storage**: Fast with efficient formats

### Optimization Strategies
- Use appropriate time resolution (hourly vs 15-min)
- Select optimizer based on horizon length
- Enable rolling horizon for long periods
- Cache API responses

### Memory Management
- Stream large datasets when possible
- Use Parquet for efficient DataFrame storage
- Clear solver instances after use
- Limit result indexing overhead

## Maintenance

### Code Organization
- Follow module boundaries strictly
- Keep dependencies minimal
- Document public APIs thoroughly
- Use type hints consistently

### Configuration Management
- Version configs with simulation code
- Validate on construction
- Provide sensible defaults
- Document all parameters

### Result Management
- Regular cleanup of old results
- Archive important benchmarks
- Track optimizer versions
- Maintain reproducibility

## References

### Academic
- Mayne et al. (2000): Constrained model predictive control
- Rawlings & Mayne (2009): Model Predictive Control

### Technical
- ENTSO-E Transparency Platform API
- PVGIS (Photovoltaic Geographical Information System)
- HiGHS: High-performance LP/MIP solver

### Internal
- `configs/`: Sample configuration files
- `example_*.py`: Usage demonstrations
- `scripts/`: CLI tools and utilities
