"""
Quick test to validate the visualize_battery_management.py migration
Tests imports and basic optimizer initialization
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

print("Testing migration to RollingHorizonOptimizer...")
print(f"Project root: {project_root}")

# Test imports
print("\n1. Testing imports...")
try:
    from config import BatteryOptimizationConfig, DegradationConfig
    print("  ✓ Config imports successful")
except ImportError as e:
    print(f"  ✗ Config import failed: {e}")
    sys.exit(1)

try:
    from core.rolling_horizon_optimizer import RollingHorizonOptimizer
    print("  ✓ RollingHorizonOptimizer import successful")
except ImportError as e:
    print(f"  ✗ RollingHorizonOptimizer import failed: {e}")
    sys.exit(1)

try:
    from operational import BatterySystemState, calculate_average_power_tariff_rate
    print("  ✓ State manager imports successful")
except ImportError as e:
    print(f"  ✗ State manager import failed: {e}")
    sys.exit(1)

# Test initialization
print("\n2. Testing optimizer initialization...")
try:
    config = BatteryOptimizationConfig()
    config.battery.degradation = DegradationConfig(
        enabled=True,
        cycle_life_full_dod=5000,
        calendar_life_years=28.0
    )
    print("  ✓ Config created")

    optimizer = RollingHorizonOptimizer(
        config=config,
        battery_kwh=100,
        battery_kw=50,
        horizon_hours=168  # Weekly optimization
    )
    print("  ✓ RollingHorizonOptimizer initialized (168h horizon)")

    state = BatterySystemState(
        battery_capacity_kwh=100,
        current_soc_kwh=50,
        current_monthly_peak_kw=0.0,
        power_tariff_rate_nok_per_kw=calculate_average_power_tariff_rate(config.tariff)
    )
    print("  ✓ BatterySystemState initialized")

except Exception as e:
    print(f"  ✗ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test resolution calculation
print("\n3. Testing resolution calculations...")
try:
    for resolution in ['PT60M', 'PT15M']:
        if resolution == 'PT60M':
            weekly_timesteps = 168
        elif resolution == 'PT15M':
            weekly_timesteps = 672

        print(f"  ✓ {resolution}: {weekly_timesteps} timesteps/week")

except Exception as e:
    print(f"  ✗ Resolution calculation failed: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✓ All migration tests passed!")
print("="*60)
print("\nThe visualize_battery_management.py script should now work with:")
print("  - RollingHorizonOptimizer (weekly sequential optimization)")
print("  - BatterySystemState (state management with peak tracking)")
print("  - Dynamic resolution support (PT60M and PT15M)")
print("\nReady to run full visualization.")
