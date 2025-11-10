"""
IPython/Jupyter Setup Script for Battery Optimization

Run this at the start of your interactive session:
    %run ipython_setup.py

Or from regular Python:
    exec(open('ipython_setup.py').read())
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("🔋 Battery Optimization - Interactive Setup")
print("=" * 60)

# Import commonly used modules
from src.config.simulation_config import SimulationConfig
from src.simulation import (
    RollingHorizonOrchestrator,
    MonthlyOrchestrator,
    YearlyOrchestrator,
)
from src.data.data_manager import DataManager
from src.optimization.optimizer_factory import OptimizerFactory

print("✅ Imports loaded successfully\n")

# Quick examples
print("Quick Start Examples:")
print("-" * 60)
print("# 1. Load configuration from YAML:")
print("config = SimulationConfig.from_yaml('configs/rolling_horizon_realtime.yaml')")
print()
print("# 2. Create orchestrator and run simulation:")
print("orchestrator = RollingHorizonOrchestrator(config)")
print("results = orchestrator.run()")
print()
print("# 3. Access results:")
print("results.trajectory  # DataFrame with all timesteps")
print("results.economic_metrics  # Dict with costs/revenues")
print("results.battery_final_state  # Final battery state")
print()
print("# 4. Save results:")
print("results.save_all('results/my_simulation')")
print("=" * 60)
