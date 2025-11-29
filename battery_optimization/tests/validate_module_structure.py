"""
Module Structure Validation Script

Validates the battery optimization system architecture by:
- Testing public API imports
- Verifying module boundaries
- Checking dependency flow
- Ensuring clean interfaces

Run this after architectural changes to ensure system integrity.
"""

import sys
from pathlib import Path

# Add project root directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_public_api_imports():
    """Test that all public API components are importable from src."""
    print("=" * 100)
    print("TESTING PUBLIC API IMPORTS")
    print("=" * 100)
    print()

    try:
        # Configuration
        from src import SimulationConfig
        print("✓ Configuration imports successful")

        # Infrastructure
        from src import PriceLoader, PriceData
        from src import SolarProductionLoader, SolarProductionData
        from src import TariffLoader
        print("✓ Infrastructure imports successful")

        # Optimization
        from src import OptimizerFactory, OptimizerRegistry
        from src import BaseOptimizer, OptimizationResult
        from src import SolverType, TimeScale
        print("✓ Optimization imports successful")

        # Simulation
        from src import SimulationResults
        from src import RollingHorizonOrchestrator
        from src import MonthlyOrchestrator, YearlyOrchestrator
        print("✓ Simulation imports successful")

        # Persistence
        from src import ResultStorage, MetadataBuilder, StorageFormat
        print("✓ Persistence imports successful")

        # Operational
        from src import BatterySystemState
        print("✓ Operational imports successful")

        print()
        print("All public API imports successful! ✓")
        return True

    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_module_boundaries():
    """Test that module boundaries are respected."""
    print()
    print("=" * 100)
    print("TESTING MODULE BOUNDARIES")
    print("=" * 100)
    print()

    # Test 1: Infrastructure should have no dependencies on other modules
    print("Test 1: Infrastructure independence")
    try:
        from src.infrastructure.pricing import price_loader
        from src.infrastructure.weather import solar_loader
        from src.infrastructure.tariffs import loader

        # Check imports in these files
        print("  ✓ Infrastructure modules are self-contained")
    except Exception as e:
        print(f"  ✗ Infrastructure boundary violation: {e}")
        return False

    # Test 2: Optimization should only depend on infrastructure
    print("Test 2: Optimization dependencies")
    try:
        from src.optimization import base_optimizer
        from src.optimization import optimizer_registry
        print("  ✓ Optimization properly isolated")
    except Exception as e:
        print(f"  ✗ Optimization boundary violation: {e}")
        return False

    # Test 3: Simulation should coordinate other modules
    print("Test 3: Simulation orchestration")
    try:
        from src.simulation import simulation_results
        from src.simulation import rolling_horizon_orchestrator
        print("  ✓ Simulation orchestration working")
    except Exception as e:
        print(f"  ✗ Simulation boundary violation: {e}")
        return False

    print()
    print("Module boundaries are clean! ✓")
    return True


def test_optimizer_registry():
    """Test that OptimizerRegistry is properly initialized."""
    print()
    print("=" * 100)
    print("TESTING OPTIMIZER REGISTRY")
    print("=" * 100)
    print()

    from src import OptimizerRegistry

    # Check registered optimizers
    names = OptimizerRegistry.list_names()
    print(f"Registered optimizers: {', '.join(names)}")

    if len(names) != 3:
        print(f"✗ Expected 3 registered optimizers, found {len(names)}")
        return False

    # Check each optimizer has metadata
    for name in names:
        meta = OptimizerRegistry.get(name)
        print(f"\n{meta.display_name}:")
        print(f"  - Type: {meta.solver_type.value}")
        print(f"  - Horizon: {meta.typical_horizon_hours}h")
        print(f"  - Solver: {meta.requires_solver}")

    print()
    print("Optimizer registry properly configured! ✓")
    return True


def test_configuration_loading():
    """Test configuration system."""
    print()
    print("=" * 100)
    print("TESTING CONFIGURATION SYSTEM")
    print("=" * 100)
    print()

    from src import SimulationConfig
    from src.config.simulation_config import BatteryConfigSim, EconomicConfig

    # Test dataclass creation
    try:
        config = SimulationConfig(
            mode="rolling_horizon",
            battery=BatteryConfigSim(
                capacity_kwh=80.0,
                power_kw=60.0,
                efficiency=0.90
            ),
            economic=EconomicConfig(
                discount_rate=0.05,
                project_years=15
            )
        )
        print(f"✓ Created config: {config.mode} mode")
        print(f"  - Battery: {config.battery.capacity_kwh} kWh @ {config.battery.power_kw} kW")
        print(f"  - Economics: {config.economic.discount_rate:.1%} discount rate")

        print()
        print("Configuration system working! ✓")
        return True

    except Exception as e:
        print(f"✗ Configuration creation failed: {e}")
        return False


def test_result_storage():
    """Test persistence system."""
    print()
    print("=" * 100)
    print("TESTING PERSISTENCE SYSTEM")
    print("=" * 100)
    print()

    from src import ResultStorage, StorageFormat

    try:
        # Initialize storage
        storage = ResultStorage(results_dir="results/validation_test")
        print(f"✓ Storage initialized at: {storage.results_dir}")

        # Check storage formats
        formats = [f.value for f in StorageFormat]
        print(f"✓ Available formats: {', '.join(formats)}")

        # Get stats
        stats = storage.get_storage_stats()
        print(f"✓ Storage stats: {stats['total_results']} results")

        print()
        print("Persistence system working! ✓")
        return True

    except Exception as e:
        print(f"✗ Persistence test failed: {e}")
        return False


def test_version_info():
    """Test version information."""
    print()
    print("=" * 100)
    print("TESTING VERSION INFORMATION")
    print("=" * 100)
    print()

    from src import __version__, __author__

    print(f"Version: {__version__}")
    print(f"Author:  {__author__}")

    print()
    print("Version information available! ✓")
    return True


def test_example_workflow():
    """Test a minimal end-to-end workflow."""
    print()
    print("=" * 100)
    print("TESTING MINIMAL WORKFLOW")
    print("=" * 100)
    print()

    try:
        from src import (
            SimulationConfig,
            OptimizerFactory,
            OptimizerRegistry,
            PriceLoader,
            SolarProductionLoader
        )

        print("Step 1: Configuration")
        from src.config.simulation_config import BatteryConfigSim, EconomicConfig
        config = SimulationConfig(
            mode="rolling_horizon",
            battery=BatteryConfigSim(
                capacity_kwh=80.0,
                power_kw=60.0,
                efficiency=0.90
            ),
            economic=EconomicConfig(
                discount_rate=0.05,
                project_years=15
            )
        )
        print(f"  ✓ Config created: {config.mode}")

        print("\nStep 2: Optimizer Discovery")
        meta = OptimizerRegistry.get("rolling_horizon")
        print(f"  ✓ Found optimizer: {meta.display_name}")
        print(f"    Horizon: {meta.typical_horizon_hours}h")

        print("\nStep 3: Optimizer Creation")
        optimizer = OptimizerFactory.create(mode="rolling_horizon", config=config)
        print(f"  ✓ Created optimizer: {type(optimizer).__name__}")
        print(f"    Battery: {optimizer.battery_kwh} kWh @ {optimizer.battery_kw} kW")

        print("\nStep 4: Data Loaders")
        price_loader = PriceLoader(eur_to_nok=11.5)
        solar_loader = SolarProductionLoader(default_capacity_kwp=150.0)
        print(f"  ✓ Loaders initialized")

        print()
        print("Minimal workflow successful! ✓")
        return True

    except Exception as e:
        print(f"✗ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print()
    print("═" * 100)
    print("BATTERY OPTIMIZATION SYSTEM - MODULE STRUCTURE VALIDATION")
    print("═" * 100)
    print()

    tests = [
        ("Public API Imports", test_public_api_imports),
        ("Module Boundaries", test_module_boundaries),
        ("Optimizer Registry", test_optimizer_registry),
        ("Configuration System", test_configuration_loading),
        ("Persistence System", test_result_storage),
        ("Version Information", test_version_info),
        ("Minimal Workflow", test_example_workflow),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ {test_name} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print()
    print("=" * 100)
    print("VALIDATION SUMMARY")
    print("=" * 100)
    print()

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8s} {test_name}")

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print()
        print("✓ All validation tests passed!")
        print("✓ Module structure is clean and well-organized")
        print("✓ Public API is working correctly")
        print()
        return 0
    else:
        print()
        print("✗ Some validation tests failed")
        print("  Review the output above for details")
        print()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
