"""
Quick run script for battery optimization.

Usage in IPython:
    %run quick_run.py
"""

from src.config.simulation_config import SimulationConfig
from src.simulation import RollingHorizonOrchestrator

print("\n🔋 Loading configuration...")
config = SimulationConfig.from_yaml('configs/simulation_config.yaml')

print(f"   Mode: {config.mode}")
print(f"   Battery: {config.battery.capacity_kwh} kWh, {config.battery.power_kw} kW")
print(f"   Period: {config.simulation_period.start_date} to {config.simulation_period.end_date}")

print("\n🚀 Creating orchestrator...")
orchestrator = RollingHorizonOrchestrator(config)

print("\n⚡ Running simulation...")
results = orchestrator.run()

print(f"\n✅ Simulation complete!")
print(f"   Final SOC: {results.battery_final_state.current_soc_percent:.1f}%")
print(f"   Total timesteps: {len(results.trajectory)}")
print(f"   Net cost: {results.economic_metrics.get('net_cost_nok', 0):.2f} NOK")

# Make results available in IPython namespace
print("\n💾 Results saved to 'results' variable")
print("   Access with: results.trajectory, results.economic_metrics, etc.")
