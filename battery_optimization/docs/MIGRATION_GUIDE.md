# Migration Guide - Battery Optimization Refactoring

## Overview

This guide helps migrate from the old monolithic structure to the new Domain-Driven Design architecture.

## Architecture Changes

### Old Structure (Monolithic)
```
battery_optimization/
├── main.py
├── src/
│   ├── config.py
│   ├── data_fetchers/
│   ├── optimization/
│   └── analysis/
└── *.py (19 test scripts in root)
```

### New Structure (DDD)
```
battery_optimization/
├── config/                 # YAML configuration files
├── domain/                 # Core business logic
│   ├── models/            # Domain models
│   ├── value_objects/     # Type-safe values
│   └── services/          # Domain services
├── infrastructure/        # External dependencies
│   └── data_sources/      # API clients
├── application/           # Use cases
│   └── use_cases/        # Application services
├── lib/                   # Reusable components
│   └── energy_toolkit/   # Extract as library
├── tests/                 # Organized tests
├── scripts/              # Utility scripts
└── reports/              # Generated reports
```

## Migration Steps

### 1. Update Configuration

**Old Way:**
```python
# src/config.py
SITE_LATITUDE = 58.9700
BATTERY_COST_NOK_PER_KWH = 3000
```

**New Way:**
```yaml
# config/site_config.yaml
location:
  latitude: 58.9700

# config/economic_config.yaml
decision_variables:
  battery_cost_nok_per_kwh:
    default: 3000
```

```python
from config import ConfigurationManager

config = ConfigurationManager()
config.load()
latitude = config.site.latitude
```

### 2. Use Value Objects

**Old Way:**
```python
battery_capacity = 100  # kWh? kW? unclear
price = 1.5  # NOK? EUR? per kWh? per MWh?
```

**New Way:**
```python
from domain.value_objects.energy import Energy, Power
from domain.value_objects.money import CostPerUnit

battery_capacity = Energy.from_kwh(100)
battery_power = Power.from_kw(50)
price = CostPerUnit.nok_per_kwh(1.5)

# Type-safe operations
total_cost = price.calculate_total(battery_capacity.kwh)
```

### 3. Update Battery Model

**Old Way:**
```python
battery_capacity = 100
battery_soc = 0.5
energy_stored = battery_capacity * battery_soc
```

**New Way:**
```python
from domain.models.battery import Battery, BatterySpecification

spec = BatterySpecification(
    capacity=Energy.from_kwh(100),
    max_power=Power.from_kw(50),
    efficiency=0.90
)
battery = Battery(spec)

# Charge with proper accounting
energy_to_battery, energy_from_grid = battery.charge(
    power=Power.from_kw(20),
    duration_hours=1.0
)
```

### 4. Use Application Layer

**Old Way:**
```python
# Direct optimization in script
from scipy.optimize import differential_evolution

def optimize():
    # Complex logic mixed with infrastructure
    prices = fetch_prices()
    result = differential_evolution(...)
```

**New Way:**
```python
from application.use_cases import (
    OptimizeBatteryUseCase,
    OptimizeBatteryRequest
)

# Clean separation of concerns
use_case = OptimizeBatteryUseCase(config)
request = OptimizeBatteryRequest(
    battery_cost_nok_per_kwh=3000,
    optimization_metric='npv'
)
response = use_case.execute(request)

print(f"Optimal capacity: {response.optimal_capacity_kwh} kWh")
print(f"NPV: {response.npv_nok:,.0f} NOK")
```

### 5. Update Data Fetching

**Old Way:**
```python
import requests

def fetch_prices():
    response = requests.get(url)
    # Manual parsing
```

**New Way:**
```python
from infrastructure.data_sources import ENTSOEClient

client = ENTSOEClient()
prices = client.fetch_day_ahead_prices(
    start_date=start,
    end_date=end,
    bidding_zone='NO2',
    use_cache=True  # Automatic caching
)

# Convert to NOK
prices_nok = client.convert_to_nok(prices)
```

### 6. Use Tariff Structures

**Old Way:**
```python
# Hardcoded tariff logic
if 6 <= hour < 22 and weekday < 5:
    rate = 0.296
else:
    rate = 0.176
```

**New Way:**
```python
from lib.energy_toolkit.tariffs import LnettCommercialTariff

tariff = LnettCommercialTariff()
energy_cost = tariff.calculate_energy_charge(consumption)
demand_cost = tariff.calculate_demand_charge(peak_demand, month)
total_cost = tariff.calculate_total_cost(consumption, peaks)
```

### 7. Generate Reports

**Old Way:**
```python
# Manual plotting and report creation
import matplotlib.pyplot as plt
plt.plot(data)
plt.savefig('plot.png')
```

**New Way:**
```python
from application.use_cases import (
    GenerateReportUseCase,
    GenerateReportRequest
)

report_use_case = GenerateReportUseCase()
request = GenerateReportRequest(
    optimization_result=optimization_response,
    sensitivity_result=sensitivity_response,
    output_format='html',
    include_visualizations=True
)
response = report_use_case.execute(request)

print(f"Report saved to: {response.report_path}")
```

## Running the Migrated Code

### Basic Optimization
```python
from config import ConfigurationManager
from application.use_cases import OptimizeBatteryUseCase

# Load configuration
config = ConfigurationManager()
config.load()

# Run optimization
optimizer = OptimizeBatteryUseCase(config)
result = optimizer.execute(
    OptimizeBatteryRequest(
        battery_cost_nok_per_kwh=3000
    )
)
```

### Sensitivity Analysis
```python
from application.use_cases import SensitivityAnalysisUseCase

sensitivity = SensitivityAnalysisUseCase(config)
result = sensitivity.execute(
    SensitivityAnalysisRequest(
        base_battery_cost=3000,
        battery_cost_range=(1000, 5000),
        battery_cost_steps=10
    )
)

print(f"Break-even cost: {result.break_even_battery_cost} NOK/kWh")
```

## Testing

### Old Test Structure
```python
# test_analysis.py in root
def test_something():
    # Test mixed with implementation
```

### New Test Structure
```python
# tests/test_domain/test_battery.py
import pytest
from domain.models.battery import Battery

class TestBattery:
    def test_battery_charge(self):
        # Focused unit test
```

Run tests:
```bash
pytest tests/
pytest tests/test_domain/  # Domain tests only
pytest tests/test_infrastructure/  # Infrastructure tests
```

## Benefits of Migration

1. **Type Safety**: Value objects prevent unit conversion errors
2. **Configurability**: YAML configs for easy scenario testing
3. **Reusability**: Energy toolkit can be used in other projects
4. **Testability**: Clean separation enables better testing
5. **Maintainability**: Clear structure and responsibilities
6. **Extensibility**: Easy to add new tariffs, optimization strategies

## Quick Reference

### Import Changes

| Old Import | New Import |
|------------|------------|
| `from src.config import *` | `from config import ConfigurationManager` |
| `from src.optimization.optimizer import optimize` | `from application.use_cases import OptimizeBatteryUseCase` |
| `from src.data_fetchers.entsoe import fetch_prices` | `from infrastructure.data_sources import ENTSOEClient` |
| `battery_capacity = 100` | `battery_capacity = Energy.from_kwh(100)` |
| `price = 1.5` | `price = CostPerUnit.nok_per_kwh(1.5)` |

### Configuration Access

| Old Way | New Way |
|---------|---------|
| `SITE_LATITUDE` | `config.site.latitude` |
| `BATTERY_COST` | `config.decision_variables.battery_cost_default` |
| `DISCOUNT_RATE` | `config.economic.discount_rate` |

## Troubleshooting

### Issue: Import errors
**Solution**: Ensure PYTHONPATH includes the battery_optimization directory

### Issue: Missing ENTSO-E API key
**Solution**: Set environment variable or use cached/simulated data:
```bash
export ENTSOE_API_KEY=your_key
# Or in code:
client = ENTSOEClient(api_key="your_key")
```

### Issue: Configuration not found
**Solution**: Ensure config files exist in `config/` directory

## Next Steps

1. Extract `lib/energy_toolkit` as separate package
2. Add more comprehensive tests
3. Implement additional optimization strategies
4. Add support for multiple battery technologies
5. Integrate with monitoring systems