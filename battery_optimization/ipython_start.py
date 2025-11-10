"""
Battery Optimization - IPython Setup Script
============================================

Usage in IPython:
    cd /mnt/c/Users/klaus/klauspython/SDE/battery_optimization
    ipython
    %run ipython_start.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add project to path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

print("\n" + "="*70)
print("🔋 Battery Optimization System - IPython Environment")
print("="*70)

# Import all commonly used modules
from src.config.simulation_config import SimulationConfig
from src.data.data_manager import DataManager, TimeSeriesData
from src.simulation.rolling_horizon_orchestrator import RollingHorizonOrchestrator
from src.simulation.battery_simulation import BatterySimulation  # NEW: Pythonic API
from src.operational.state_manager import BatterySystemState

print("\n✅ All modules imported successfully!")
print("\nAvailable objects:")
print("  - SimulationConfig    : Configuration class")
print("  - BatterySimulation   : Main facade (NEW Pythonic API)")
print("  - DataManager         : Data loading and management")
print("  - TimeSeriesData      : Data container")
print("  - RollingHorizonOrchestrator : Low-level orchestrator")
print("  - pandas as pd, numpy as np")

print("\n" + "-"*70)
print("Quick Examples:")
print("-"*70)

print("""
# ═══ NEW PYTHONIC API (Recommended for IPython) ═══

# 1️⃣  File-based (YAML + CSV files):
sim = BatterySimulation.from_config('configs/working_config.yaml')
results = sim.run()

# 2️⃣  DataFrame-based (pandas):
df = pd.read_csv('data/combined_data.csv', index_col=0, parse_dates=True)
sim = BatterySimulation.from_dataframe(df, battery_kwh=80, battery_kw=60)
results = sim.run()

# 3️⃣  Array-based (numpy):
timestamps = pd.date_range('2024-06-01', periods=720, freq='h')
prices = np.random.uniform(0.5, 1.5, 720)
production = np.random.uniform(0, 100, 720)
consumption = np.random.uniform(20, 50, 720)
sim = BatterySimulation.from_arrays(
    timestamps, prices, production, consumption,
    battery_kwh=80, battery_kw=60
)
results = sim.run()

# ═══ RESULTS ACCESS ═══

results.trajectory                        # DataFrame with all timesteps
results.trajectory['soc_percent'].plot()  # Plot SOC
results.final_soc_percent                 # Final SOC
len(results.trajectory)                   # Number of timesteps

# ═══ OLD API (still works) ═══

# Load existing config and run:
config = SimulationConfig.from_yaml('configs/working_config.yaml')
orchestrator = RollingHorizonOrchestrator(config)
results = orchestrator.run()

# Load and explore data only:
config = SimulationConfig.from_yaml('configs/working_config.yaml')
dm = DataManager(config)
data = dm.load_data()
print(f"Data period: {data.timestamps[0]} to {data.timestamps[-1]}")
data.to_dataframe().head()
""")

print("="*70)
print("Ready to optimize! 🚀")
print("="*70 + "\n")
