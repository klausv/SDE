# Battery Optimization System - Quick Start Guide

## Installation

```bash
# Create conda environment
conda env create -f environment.yml
conda activate battery_opt

# Configure ENTSO-E API key (optional, for real price data)
echo "ENTSOE_API_KEY=your_key_here" > .env
```

## Baseline Mode (No Battery)

**New in v2.0**: Calculate economic baseline without battery for ROI comparison.

```bash
# Run baseline calculation (instant, no solver overhead)
python main.py run --config configs/baseline_monthly.yaml
```

**Why baseline mode?**
- Establishes economic reference point for battery ROI
- Instant calculation (~1ms) vs 30-60s optimization
- Same infrastructure (pricing, weather, tariffs)
- Critical for investment analysis

**Usage**:
```python
from src import SimulationConfig
from src.simulation import MonthlyOrchestrator

# Baseline via YAML
config = SimulationConfig.from_yaml("configs/baseline_monthly.yaml")
orchestrator = MonthlyOrchestrator(config)
baseline_results = orchestrator.run()

# Or programmatic with battery_kwh=0
config.battery.capacity_kwh = 0.0
config.battery.power_kw = 0.0
# Factory auto-detects and uses BaselineCalculator
```

See `examples/example_baseline_usage.py` for complete examples.

## Basic Usage

### 1. Load Configuration

```python
from src import SimulationConfig

# Load from YAML
config = SimulationConfig.from_yaml("configs/rolling_horizon.yaml")

# Or create programmatically
from src.config.simulation_config import (
    BatteryConfig,
    EconomicConfig,
    RollingHorizonConfig
)

config = SimulationConfig(
    mode="rolling_horizon",
    battery=BatteryConfig(
        capacity_kwh=80.0,
        power_kw=60.0,
        efficiency=0.90
    ),
    economic=EconomicConfig(
        discount_rate=0.05,
        project_years=15
    ),
    rolling_horizon=RollingHorizonConfig(
        horizon_hours=168  # 1 week
    )
)
```

### 2. Load Data

```python
from src import PriceLoader, SolarProductionLoader

# Load electricity prices
price_loader = PriceLoader(eur_to_nok=11.5, default_area_code="NO2")
prices = price_loader.from_csv("data/spot_prices/NO2_2024_60min.csv")

# Or fetch from ENTSO-E API
# prices = price_loader.from_entsoe_api(
#     start_date=datetime(2024, 1, 1),
#     end_date=datetime(2024, 12, 31)
# )

# Load solar production
solar_loader = SolarProductionLoader(default_capacity_kwp=150.0)
production = solar_loader.from_csv("data/pv_profiles/pvgis_stavanger_150kwp.csv")

# Or fetch from PVGIS API
# production = solar_loader.from_pvgis_api(
#     latitude=58.97,
#     longitude=5.73,
#     capacity_kwp=150.0
# )
```

### 3. Create Optimizer

```python
from src import OptimizerFactory, OptimizerRegistry

# Discover available optimizers
OptimizerRegistry.print_summary()

# Create optimizer from config
optimizer = OptimizerFactory.create_from_config(config)

# Or specify mode explicitly
optimizer = OptimizerFactory.create(mode="rolling_horizon", config=config)
```

### 4. Run Simulation

```python
from src.simulation import RollingHorizonOrchestrator

# Create orchestrator
orchestrator = RollingHorizonOrchestrator(config, optimizer)

# Run simulation
results = orchestrator.run(
    price_data=prices,
    production_data=production,
    # Optional: consumption_data=consumption
)

print(f"Simulation complete: {len(results.trajectory)} timesteps")
print(f"Total cost: {results.economic_metrics['total_cost_nok']:,.0f} NOK")
```

### 5. Save Results

```python
from src import ResultStorage, MetadataBuilder

# Initialize storage
storage = ResultStorage(results_dir="results/")

# Build comprehensive metadata
metadata = results.build_metadata(
    config=config,
    price_data=prices,
    production_data=production,
    optimizer_method="rolling_horizon",
    optimizer_solver="HiGHS"
)

# Update result metadata
results.metadata.update(metadata)

# Save results
result_id = results.save_to_storage(
    storage,
    notes="Baseline configuration test"
)

print(f"Results saved as: {result_id}")
```

### 6. Load and Report (Later, Without Re-running)

```python
from src import ResultStorage, SimulationResults

# Initialize storage
storage = ResultStorage(results_dir="results/")

# List available results
for meta in storage.list_results():
    print(f"{meta.result_id}: {meta.total_cost_nok:,.0f} NOK")

# Load specific result
results = SimulationResults.load_from_storage(storage, result_id)

# Generate report
print(results.to_report())

# Export visualizations
results.to_plots(output_dir="results/plots/")

# Export CSV
results.to_csv(output_dir="results/csv/")
```

## Command-Line Interface

```bash
# List stored results
python scripts/report_cli.py list

# Show result details
python scripts/report_cli.py show <result_id>

# Generate markdown report
python scripts/report_cli.py report <result_id> -o report.md

# Generate plots
python scripts/report_cli.py plots <result_id> -o plots/

# Compare two results
python scripts/report_cli.py compare <id1> <id2>

# Storage statistics
python scripts/report_cli.py stats
```

## Advanced Usage

### Optimizer Discovery and Selection

```python
from src import OptimizerRegistry, SolverType

# Filter optimizers by capability
mpc_optimizers = OptimizerRegistry.filter_by(solver_type=SolverType.MPC)
fast_optimizers = OptimizerRegistry.filter_by(max_solve_time_s=1.0)
degradation_capable = OptimizerRegistry.filter_by(supports_degradation=True)

# Get detailed metadata
meta = OptimizerRegistry.get("rolling_horizon")
print(f"Horizon: {meta.typical_horizon_hours} hours")
print(f"Best for: {meta.best_for}")
print(f"Limitations: {meta.limitations}")
```

### Custom Storage Formats

```python
from src import ResultStorage, StorageFormat

storage = ResultStorage(results_dir="results/")

# Save in different formats
result_id = results.save_to_storage(
    storage,
    format=StorageFormat.PICKLE,  # Full object (default)
    # format=StorageFormat.JSON,    # Human-readable
    # format=StorageFormat.PARQUET, # Efficient
    notes="Format comparison test"
)
```

### Batch Processing

```python
from pathlib import Path

# Process multiple configurations
config_dir = Path("configs/")
for config_file in config_dir.glob("*.yaml"):
    print(f"Processing {config_file.name}...")

    # Load config
    config = SimulationConfig.from_yaml(config_file)

    # Create optimizer
    optimizer = OptimizerFactory.create_from_config(config)

    # Run simulation
    orchestrator = RollingHorizonOrchestrator(config, optimizer)
    results = orchestrator.run(prices, production)

    # Save with config name
    result_id = results.save_to_storage(
        storage,
        notes=f"Config: {config_file.stem}"
    )

    print(f"  → Saved as {result_id}")
```

### Result Comparison

```python
# Load multiple results for comparison
result_ids = ["baseline_id", "optimized_id"]
all_results = [storage.load(rid) for rid in result_ids]

# Compare economic metrics
for rid, res in zip(result_ids, all_results):
    print(f"{rid}:")
    print(f"  Total cost: {res.economic_metrics['total_cost_nok']:,.0f} NOK")
    print(f"  NPV: {res.economic_metrics['npv_nok']:,.0f} NOK")
    print(f"  IRR: {res.economic_metrics['irr']:.2%}")
```

## Troubleshooting

### Missing API Key
```python
# Error: ENTSOE_API_KEY not found
# Solution: Use CSV data or register for free API key
# https://transparency.entsoe.eu/

price_loader = PriceLoader(eur_to_nok=11.5)
prices = price_loader.from_csv("data/spot_prices/NO2_2024.csv")
```

### Solver Not Found
```python
# Error: Solver 'HiGHS' not available
# Solution: Install solver via conda
# conda install -c conda-forge scipy>=1.9  # Includes HiGHS

# Or use alternative solver
# config.rolling_horizon.solver = "CBC"
```

### Memory Issues
```python
# For large simulations, use chunking or reduce resolution
config.time_resolution = "PT60M"  # Use hourly instead of 15-min

# Or use monthly mode for yearly analysis
config.mode = "monthly"
optimizer = OptimizerFactory.create(mode="monthly", config=config)
```

### Import Errors
```python
# Ensure you're in the correct directory
import sys
from pathlib import Path

repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from src import SimulationConfig  # Now works
```

## Examples

See the following example scripts for complete workflows:

- `example_infrastructure_usage.py`: Data loading demonstrations
- `example_persistence_usage.py`: Result storage demonstrations
- `example_optimizer_registry.py`: Optimizer discovery and selection
- `scripts/report_cli.py`: Command-line reporting

## Next Steps

- **Configuration**: Review `configs/` for sample YAML files
- **Architecture**: Read `docs/ARCHITECTURE.md` for system design
- **Optimization**: Explore `src/optimization/` for available methods
- **Visualization**: Check `src/visualization/` for plotting themes

## Support

For issues or questions:
1. Check `docs/ARCHITECTURE.md` for design details
2. Review example scripts for usage patterns
3. Examine unit tests for edge cases
4. Inspect source code for implementation details
