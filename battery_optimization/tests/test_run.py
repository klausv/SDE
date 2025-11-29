"""
Test run with actual data - use this in IPython.

Usage:
    %run test_run.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src.config.simulation_config import SimulationConfig
from src.simulation import RollingHorizonOrchestrator

print("\n" + "="*70)
print("🔋 Battery Optimization - Test Run with Real Data")
print("="*70)

print("\n📋 Loading configuration...")
config = SimulationConfig.from_yaml('configs/simulation_config.yaml')

print(f"   Mode: {config.mode}")
print(f"   Battery: {config.battery.capacity_kwh} kWh @ {config.battery.power_kw} kW")
print(f"   Period: {config.simulation_period.start_date} to {config.simulation_period.end_date}")
print(f"   Resolution: {config.time_resolution}")

print(f"\n📂 Data files:")
print(f"   Prices: {config.data_sources.prices_file}")
print(f"   Production: {config.data_sources.production_file}")
print(f"   Consumption: {config.data_sources.consumption_file}")

print("\n🏗️  Creating orchestrator...")
orchestrator = RollingHorizonOrchestrator(config)

print("\n🚀 Running simulation (this may take 1-2 minutes)...")
results = orchestrator.run()

print("\n" + "="*70)
print("✅ Simulation Complete!")
print("="*70)

print(f"\n📊 Results Summary:")
print(f"   Total timesteps: {len(results.trajectory)}")
print(f"   Final SOC: {results.battery_final_state.current_soc_percent:.1f}%")
print(f"   Monthly peak: {results.battery_final_state.current_monthly_peak_kw:.1f} kW")

if results.economic_metrics:
    print(f"\n💰 Economic Metrics:")
    print(f"   Total charged: {results.economic_metrics.get('total_charged_kwh', 0):.1f} kWh")
    print(f"   Total discharged: {results.economic_metrics.get('total_discharged_kwh', 0):.1f} kWh")
    print(f"   Grid import: {results.economic_metrics.get('total_import_kwh', 0):.1f} kWh")
    print(f"   Grid export: {results.economic_metrics.get('total_export_kwh', 0):.1f} kWh")
    print(f"   Curtailed: {results.economic_metrics.get('total_curtailed_kwh', 0):.1f} kWh")
    print(f"   Net cost: {results.economic_metrics.get('net_cost_nok', 0):.2f} NOK")

print(f"\n📈 Access results with:")
print(f"   results.trajectory  # Full DataFrame")
print(f"   results.trajectory['soc_percent'].plot()  # Plot SOC")
print(f"   results.economic_metrics  # All metrics")
print(f"   results.save_all('results/test_run')  # Save everything")

print("\n" + "="*70 + "\n")

# Make results available
__all__ = ['results', 'config', 'orchestrator']
