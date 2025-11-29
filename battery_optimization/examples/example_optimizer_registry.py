"""
Example usage of OptimizerRegistry for method discovery and traceability.

Demonstrates how to:
- Discover available optimization methods
- Get detailed metadata about each method
- Filter optimizers by capabilities
- Document which optimizer was used for simulations
- Make informed selection based on requirements

This enables transparent method traceability and informed decision-making.
"""

import sys
from pathlib import Path

# Add parent directory to path
parent_path = Path(__file__).parent
sys.path.insert(0, str(parent_path))

from src.optimization import OptimizerRegistry, SolverType, TimeScale


def example_list_all():
    """Example: List all registered optimizers."""
    print("=" * 100)
    print("LIST ALL REGISTERED OPTIMIZERS")
    print("=" * 100)
    print()

    # Get all optimizer names
    print("1. Available optimizer names:")
    names = OptimizerRegistry.list_names()
    for name in names:
        print(f"   - {name}")
    print()

    # Get detailed metadata for each
    print("2. Detailed information:")
    print()

    for name in names:
        meta = OptimizerRegistry.get(name)
        print(f"{meta.display_name}")
        print(f"  ID:           {meta.name}")
        print(f"  Type:         {meta.solver_type.value}")
        print(f"  Time Scale:   {meta.time_scale.value}")
        print(f"  Description:  {meta.description[:80]}...")
        print()


def example_get_metadata():
    """Example: Get detailed metadata for specific optimizer."""
    print("=" * 100)
    print("GET OPTIMIZER METADATA")
    print("=" * 100)
    print()

    print("Fetching metadata for 'rolling_horizon' optimizer...")
    meta = OptimizerRegistry.get("rolling_horizon")

    print(f"\n{meta.display_name}")
    print("-" * 100)
    print(f"Version:          {meta.version}")
    print(f"Solver Type:      {meta.solver_type.value}")
    print(f"Time Scale:       {meta.time_scale.value}")
    print(f"Optimization:     {meta.optimization_scope}")
    print()

    print(f"Description:")
    print(f"  {meta.description}")
    print()

    print(f"Capabilities:")
    print(f"  - Degradation tracking:    {meta.supports_degradation}")
    print(f"  - Power tariff:            {meta.supports_power_tariff}")
    print(f"  - Forecasting:             {meta.supports_forecasting}")
    print(f"  - Rolling execution:       {meta.supports_rolling_execution}")
    print()

    print(f"Requirements:")
    print(f"  - External solver:         {meta.requires_solver}")
    print(f"  - Horizon range:           {meta.min_horizon_hours}-{meta.max_horizon_hours} hours")
    print(f"  - Typical horizon:         {meta.typical_horizon_hours} hours")
    print()

    print(f"Performance:")
    print(f"  - Solve time (typical):    {meta.typical_solve_time_s}s")
    print(f"  - Memory usage:            {meta.memory_usage_mb} MB")
    print(f"  - Scales linearly:         {meta.scales_linearly}")
    print()

    if meta.best_for:
        print(f"Best For:")
        for use_case in meta.best_for:
            print(f"  - {use_case}")
        print()

    if meta.limitations:
        print(f"Limitations:")
        for limitation in meta.limitations:
            print(f"  - {limitation}")
        print()

    if meta.references:
        print(f"References:")
        for ref in meta.references:
            print(f"  - {ref}")
        print()


def example_filter_optimizers():
    """Example: Filter optimizers by capabilities."""
    print("=" * 100)
    print("FILTER OPTIMIZERS BY CAPABILITIES")
    print("=" * 100)
    print()

    # Filter 1: Optimizers with degradation support
    print("1. Optimizers supporting degradation tracking:")
    degradation_optimizers = OptimizerRegistry.filter_by(supports_degradation=True)
    for meta in degradation_optimizers:
        print(f"   - {meta.display_name} ({meta.name})")
    if not degradation_optimizers:
        print("   (None found)")
    print()

    # Filter 2: MPC-based optimizers
    print("2. MPC-based optimizers:")
    mpc_optimizers = OptimizerRegistry.filter_by(solver_type=SolverType.MPC)
    for meta in mpc_optimizers:
        print(f"   - {meta.display_name} ({meta.name})")
        print(f"     Typical solve time: {meta.typical_solve_time_s}s")
    print()

    # Filter 3: Fast optimizers (< 1s typical)
    print("3. Fast optimizers (solve time < 1s):")
    fast_optimizers = OptimizerRegistry.filter_by(max_solve_time_s=1.0)
    for meta in fast_optimizers:
        print(f"   - {meta.display_name}: {meta.typical_solve_time_s}s")
    if not fast_optimizers:
        print("   (None found)")
    print()

    # Filter 4: Global optimization with power tariff
    print("4. Global optimizers with power tariff support:")
    global_tariff = OptimizerRegistry.filter_by(supports_power_tariff=True)
    global_tariff = [m for m in global_tariff if m.optimization_scope == "global"]
    for meta in global_tariff:
        print(f"   - {meta.display_name}")
    print()


def example_selection_guidance():
    """Example: Selecting optimizer based on requirements."""
    print("=" * 100)
    print("OPTIMIZER SELECTION GUIDANCE")
    print("=" * 100)
    print()

    # Scenario 1: Real-time operation
    print("Scenario 1: Real-time operation with forecast updates")
    print("-" * 100)
    print("Requirements:")
    print("  - Supports forecasting")
    print("  - Rolling execution capability")
    print("  - Fast solve time for real-time response")
    print()

    candidates = OptimizerRegistry.filter_by(
        supports_forecasting=True,
        max_solve_time_s=2.0
    )
    candidates = [m for m in candidates if m.supports_rolling_execution]

    print("Recommended optimizers:")
    for meta in candidates:
        print(f"  ✓ {meta.display_name}")
        print(f"    - Solve time: {meta.typical_solve_time_s}s")
        print(f"    - Horizon: {meta.typical_horizon_hours} hours")
    print()

    # Scenario 2: Economic analysis
    print("Scenario 2: Annual economic analysis")
    print("-" * 100)
    print("Requirements:")
    print("  - Power tariff optimization")
    print("  - Suitable for yearly simulation")
    print("  - Global optimization preferred")
    print()

    candidates = OptimizerRegistry.filter_by(supports_power_tariff=True)

    print("Recommended optimizers:")
    for meta in candidates:
        suitability = "Excellent" if meta.optimization_scope == "global" else "Good"
        print(f"  {suitability}: {meta.display_name}")
        print(f"    - Scope: {meta.optimization_scope}")
        print(f"    - Time scale: {meta.time_scale.value}")
    print()

    # Scenario 3: Battery degradation study
    print("Scenario 3: Battery degradation impact study")
    print("-" * 100)
    print("Requirements:")
    print("  - Degradation tracking")
    print("  - Long simulation periods")
    print()

    candidates = OptimizerRegistry.filter_by(supports_degradation=True)

    print("Recommended optimizers:")
    if candidates:
        for meta in candidates:
            print(f"  ✓ {meta.display_name}")
            print(f"    - Horizon: {meta.typical_horizon_hours} hours")
    else:
        print("  ⚠ No optimizers currently support degradation tracking")
        print("  Consider implementing degradation as separate analysis")
    print()


def example_method_traceability():
    """Example: Document optimizer used for simulation traceability."""
    print("=" * 100)
    print("METHOD TRACEABILITY")
    print("=" * 100)
    print()

    print("Recording optimizer metadata for simulation traceability...")
    print()

    # Simulate selecting an optimizer
    optimizer_name = "rolling_horizon"
    meta = OptimizerRegistry.get(optimizer_name)

    # Create traceability record
    traceability_record = {
        'optimizer_name': meta.name,
        'optimizer_version': meta.version,
        'display_name': meta.display_name,
        'solver_type': meta.solver_type.value,
        'requires_solver': meta.requires_solver,
        'horizon_hours': meta.typical_horizon_hours,
        'capabilities': {
            'degradation': meta.supports_degradation,
            'power_tariff': meta.supports_power_tariff,
            'forecasting': meta.supports_forecasting,
            'rolling_execution': meta.supports_rolling_execution,
        },
        'references': meta.references,
    }

    print("Traceability Record:")
    print("-" * 100)
    for key, value in traceability_record.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for k, v in value.items():
                print(f"  {k:20s} = {v}")
        elif isinstance(value, list):
            print(f"{key}:")
            for item in value:
                print(f"  - {item}")
        else:
            print(f"{key:25s} = {value}")
    print()

    print("This metadata can be stored with simulation results for:")
    print("  ✓ Full reproducibility")
    print("  ✓ Method comparison studies")
    print("  ✓ Audit and verification")
    print("  ✓ Academic publication")
    print()


def main():
    """Run all optimizer registry examples."""
    print()
    print("═" * 100)
    print("OPTIMIZER REGISTRY EXAMPLES")
    print("═" * 100)
    print()
    print("Demonstrating method discovery, filtering, and traceability")
    print()

    example_list_all()
    print()

    example_get_metadata()
    print()

    example_filter_optimizers()
    print()

    example_selection_guidance()
    print()

    example_method_traceability()

    # Print full summary
    OptimizerRegistry.print_summary()

    print()
    print("=" * 100)
    print("BENEFITS OF OPTIMIZER REGISTRY")
    print("=" * 100)
    print()
    print("✓ Transparent method documentation")
    print("✓ Informed optimizer selection based on requirements")
    print("✓ Full traceability of which method was used")
    print("✓ Easy comparison of optimizer capabilities")
    print("✓ Academic references for citation")
    print("✓ Reproducibility for research and verification")
    print()
    print("USAGE IN WORKFLOW:")
    print()
    print("  from src.optimization import OptimizerRegistry")
    print()
    print("  # Discover available methods")
    print("  OptimizerRegistry.print_summary()")
    print()
    print("  # Filter by requirements")
    print("  fast_optimizers = OptimizerRegistry.filter_by(max_solve_time_s=1.0)")
    print()
    print("  # Get metadata for traceability")
    print("  meta = OptimizerRegistry.get('rolling_horizon')")
    print("  results.metadata['optimizer'] = meta.name")
    print("  results.metadata['optimizer_version'] = meta.version")
    print()


if __name__ == "__main__":
    main()
