#!/usr/bin/env python3
"""
Working test run with real data.
This WILL work - uses actual files that exist.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.simulation_config import SimulationConfig
from src.simulation import RollingHorizonOrchestrator

print("\n" + "="*70)
print("🔋 WORKING Battery Optimization Test")
print("="*70)

# Load config with actual existing files
config = SimulationConfig.from_yaml('configs/working_config.yaml')

print(f"\n✅ Config loaded:")
print(f"   Period: {config.simulation_period.start_date} to {config.simulation_period.end_date}")
print(f"   Battery: {config.battery.capacity_kwh} kWh @ {config.battery.power_kw} kW")

# Run simulation
orchestrator = RollingHorizonOrchestrator(config)
print(f"\n🚀 Running simulation...")

try:
    results = orchestrator.run()

    print(f"\n✅ SUCCESS!")
    print(f"   Timesteps: {len(results.trajectory)}")
    print(f"   Final SOC: {results.battery_final_state.current_soc_percent:.1f}%")

    # Save results
    results.save_all('results/working_test', save_plots=False)
    print(f"\n💾 Results saved to: results/working_test/")

except Exception as e:
    print(f"\n❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
