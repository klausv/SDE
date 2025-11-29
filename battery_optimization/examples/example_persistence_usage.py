"""
Example usage of result persistence and metadata tracking.

Demonstrates how to:
- Save simulation results with comprehensive metadata
- Load results without re-running simulations
- List and filter stored results
- Use different storage formats
- Manage result storage

This enables report regeneration without expensive re-computation.
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Add parent directory to path
parent_path = Path(__file__).parent
sys.path.insert(0, str(parent_path))

from src.persistence import ResultStorage, StorageFormat, MetadataBuilder
from src.simulation.simulation_results import SimulationResults


def create_sample_results() -> SimulationResults:
    """Create sample simulation results for demonstration."""

    # Create sample trajectory data
    timestamps = pd.date_range('2024-01-01', periods=24*7, freq='h')  # 1 week hourly

    trajectory = pd.DataFrame({
        'timestamp': timestamps,
        'P_charge_kw': np.random.uniform(0, 50, len(timestamps)),
        'P_discharge_kw': np.random.uniform(0, 50, len(timestamps)),
        'P_grid_import_kw': np.random.uniform(0, 100, len(timestamps)),
        'P_grid_export_kw': np.random.uniform(0, 80, len(timestamps)),
        'P_curtail_kw': np.random.uniform(0, 10, len(timestamps)),
        'E_battery_kwh': np.random.uniform(20, 80, len(timestamps)),
    }).set_index('timestamp')

    # Create monthly summary
    monthly_summary = pd.DataFrame({
        'year': [2024],
        'month': [1],
        'P_charge_kw': [850.0],
        'P_discharge_kw': [780.0],
        'P_grid_import_kw': [1200.0],
        'P_grid_export_kw': [950.0],
        'P_curtail_kw': [45.0],
    })

    # Create economic metrics
    economic_metrics = {
        'total_cost_nok': 125000.0,
        'npv_nok': -45000.0,
        'irr': 0.032,
        'payback_years': 12.5,
        'battery_kwh': 80.0,
        'battery_kw': 60.0,
    }

    # Create basic metadata
    metadata = {
        'battery_kwh': 80.0,
        'battery_kw': 60.0,
        'optimizer_method': 'rolling_horizon',
        'execution_time_s': 125.4,
    }

    return SimulationResults(
        mode='rolling_horizon',
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 7),
        trajectory=trajectory,
        monthly_summary=monthly_summary,
        economic_metrics=economic_metrics,
        metadata=metadata
    )


def example_save_and_load():
    """Example: Save and load simulation results."""
    print("=" * 70)
    print("SAVE AND LOAD EXAMPLE")
    print("=" * 70)
    print()

    # Initialize storage
    storage = ResultStorage(results_dir="results/persistence_demo")

    # Create sample results
    print("1. Creating sample simulation results...")
    results = create_sample_results()
    print(f"   ✓ Created results for {results.mode} mode")
    print(f"   - Period: {results.start_date.date()} to {results.end_date.date()}")
    print(f"   - Trajectory points: {len(results.trajectory)}")
    print()

    # Save in Pickle format (default, most complete)
    print("2. Saving results in Pickle format...")
    result_id_pickle = results.save_to_storage(
        storage,
        format=StorageFormat.PICKLE,
        notes="Sample results - Pickle format demonstration"
    )
    print(f"   ✓ Saved as: {result_id_pickle}")
    print()

    # Save in JSON format (human-readable)
    print("3. Saving results in JSON format...")
    result_id_json = results.save_to_storage(
        storage,
        format=StorageFormat.JSON,
        notes="Sample results - JSON format demonstration"
    )
    print(f"   ✓ Saved as: {result_id_json}")
    print()

    # Save in Parquet format (efficient)
    print("4. Saving results in Parquet format...")
    result_id_parquet = results.save_to_storage(
        storage,
        format=StorageFormat.PARQUET,
        notes="Sample results - Parquet format demonstration"
    )
    print(f"   ✓ Saved as: {result_id_parquet}")
    print()

    # Load results back
    print("5. Loading results from Pickle storage...")
    loaded_results = SimulationResults.load_from_storage(storage, result_id_pickle)
    print(f"   ✓ Loaded successfully")
    print(f"   - Mode: {loaded_results.mode}")
    print(f"   - Trajectory points: {len(loaded_results.trajectory)}")
    print(f"   - Economic metrics: {len(loaded_results.economic_metrics)} values")
    print()


def example_list_and_filter():
    """Example: List and filter stored results."""
    print("=" * 70)
    print("LIST AND FILTER EXAMPLE")
    print("=" * 70)
    print()

    storage = ResultStorage(results_dir="results/persistence_demo")

    # List all results
    print("1. Listing all stored results...")
    all_results = storage.list_results()
    print(f"   ✓ Found {len(all_results)} stored results")
    print()

    for meta in all_results:
        print(f"   ID: {meta.result_id}")
        print(f"   - Created: {meta.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   - Mode: {meta.mode}")
        print(f"   - Battery: {meta.battery_kwh} kWh @ {meta.battery_kw} kW")
        print(f"   - Format: {meta.storage_format}")
        print(f"   - Size: {meta.file_size_mb:.2f} MB")
        if meta.notes:
            print(f"   - Notes: {meta.notes}")
        print()

    # Get storage statistics
    print("2. Storage statistics...")
    stats = storage.get_storage_stats()
    print(f"   - Total results: {stats['total_results']}")
    print(f"   - Total size: {stats['total_size_mb']:.2f} MB")
    print(f"   - Results by mode: {stats['results_by_mode']}")
    print(f"   - Storage directory: {stats['storage_dir']}")
    print()


def example_metadata_builder():
    """Example: Using MetadataBuilder for comprehensive tracking."""
    print("=" * 70)
    print("METADATA BUILDER EXAMPLE")
    print("=" * 70)
    print()

    print("1. Using MetadataBuilder for comprehensive metadata...")

    # Create metadata builder
    builder = MetadataBuilder()

    # Set optimizer metadata
    builder.set_optimizer(
        method='rolling_horizon',
        solver='HiGHS',
        horizon_hours=168,
        step_hours=24,
        mip_gap=0.01
    )

    # Simulate timing
    builder.start_timing()
    import time
    time.sleep(0.1)  # Simulate work
    builder.end_timing()

    # Build metadata
    metadata = builder.build()

    print(f"   ✓ Built metadata with {len(metadata)} sections")
    print()

    # Display metadata structure
    print("2. Metadata structure:")
    for section, content in metadata.items():
        if isinstance(content, dict):
            print(f"   - {section}: {len(content)} fields")
        else:
            print(f"   - {section}: {content}")
    print()

    # Quick metadata for simple cases
    print("3. Quick metadata (minimal overhead)...")
    quick_meta = MetadataBuilder.quick_metadata(
        mode='rolling_horizon',
        battery_kwh=80,
        battery_kw=60,
        optimizer_method='HiGHS_LP',
        execution_time_s=125.4
    )
    print(f"   ✓ Quick metadata: {len(quick_meta)} fields")
    print(f"   - Mode: {quick_meta['mode']}")
    print(f"   - Battery: {quick_meta['battery_kwh']} kWh")
    print(f"   - Optimizer: {quick_meta['optimizer_method']}")
    print()


def example_result_management():
    """Example: Managing stored results."""
    print("=" * 70)
    print("RESULT MANAGEMENT EXAMPLE")
    print("=" * 70)
    print()

    storage = ResultStorage(results_dir="results/persistence_demo")

    # Get metadata without loading full result
    print("1. Getting metadata without loading full result...")
    all_results = storage.list_results()
    if all_results:
        meta = storage.get_metadata(all_results[0].result_id)
        print(f"   ✓ Retrieved metadata for: {meta.result_id}")
        print(f"   - Created: {meta.created_at}")
        print(f"   - Size: {meta.file_size_mb:.2f} MB")
        print(f"   - Battery: {meta.battery_kwh} kWh @ {meta.battery_kw} kW")
        if meta.total_cost_nok:
            print(f"   - Total cost: {meta.total_cost_nok:,.0f} NOK")
    else:
        print("   (No results available - run save_and_load example first)")
    print()

    # Storage statistics
    print("2. Storage efficiency comparison...")
    results_by_format = {}
    for meta in all_results:
        if meta.storage_format not in results_by_format:
            results_by_format[meta.storage_format] = []
        results_by_format[meta.storage_format].append(meta.file_size_mb)

    for format_name, sizes in results_by_format.items():
        avg_size = sum(sizes) / len(sizes)
        print(f"   - {format_name}: {avg_size:.2f} MB average ({len(sizes)} results)")
    print()


def main():
    """Run all persistence examples."""
    print()
    print("═" * 70)
    print("RESULT PERSISTENCE AND METADATA TRACKING EXAMPLES")
    print("═" * 70)
    print()
    print("Demonstrates comprehensive result storage for report regeneration")
    print("without re-running expensive simulations.")
    print()

    example_save_and_load()
    print()

    example_list_and_filter()
    print()

    example_metadata_builder()
    print()

    example_result_management()

    print("=" * 70)
    print("BENEFITS OF RESULT PERSISTENCE")
    print("=" * 70)
    print()
    print("✓ Save expensive simulation results (10-20 minute runs)")
    print("✓ Regenerate reports instantly without re-computation")
    print("✓ Multiple storage formats (Pickle, JSON, Parquet)")
    print("✓ Comprehensive metadata for reproducibility")
    print("✓ Automatic indexing for fast searches")
    print("✓ Version tracking with timestamps")
    print("✓ Result comparison without re-running")
    print()
    print("USAGE IN WORKFLOW:")
    print()
    print("  from src.persistence import ResultStorage, StorageFormat")
    print("  from src.simulation.simulation_results import SimulationResults")
    print()
    print("  # Run expensive simulation once")
    print("  results = run_simulation(...)")
    print()
    print("  # Save for later")
    print("  storage = ResultStorage('results/')")
    print("  result_id = results.save_to_storage(storage, notes='Baseline config')")
    print()
    print("  # Load anytime for reporting")
    print("  loaded = SimulationResults.load_from_storage(storage, result_id)")
    print("  print(loaded.to_report())")
    print()


if __name__ == "__main__":
    main()
