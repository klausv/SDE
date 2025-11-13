# Battery Optimization - Todo List

## 🔴 CRITICAL - Hardcoded Configuration Values

**Problem**: ALL simulation scripts ignore configuration files and use hardcoded consumption values instead of reading from `config_legacy.yaml` or `config.yaml`.

**Impact**:
- Analysis runs with wrong parameters (e.g., 241,200 kWh instead of configured 70,000 kWh)
- Results are meaningless and misleading
- User configuration changes have no effect on simulations

**Affected Files**:
1. `run_battery_dimensioning_PT60M.py` - Line 82: `annual_kwh = 300000`
2. `run_yearly_weekly_168h_PT60M.py` - Likely similar hardcoded values
3. Other `run_*.py` scripts that generate consumption profiles

**Root Cause**:
Scripts create consumption profiles with hardcoded values instead of using:
```python
from core.consumption_profiles import ConsumptionProfile
import yaml

# CORRECT approach:
with open('archive/legacy_entry_points/config_legacy.yaml', 'r') as f:
    config = yaml.safe_load(f)

profile = ConsumptionProfile.commercial_office(
    annual_kwh=config['consumption']['annual_kwh']
)
consumption = ConsumptionProfile.generate_annual_profile(
    profile_type=config['consumption']['profile_type'],
    annual_kwh=config['consumption']['annual_kwh'],
    year=2024
)
```

**Required Fix**:
- [ ] Systematically refactor ALL `run_*.py` scripts
- [ ] Replace hardcoded `annual_kwh` with config file reading
- [ ] Use `ConsumptionProfile.generate_annual_profile()` consistently
- [ ] Verify all scripts respect configuration parameters
- [ ] Add validation to ensure consumption matches config

**Priority**: CRITICAL - Must be fixed before any further analysis

---

## ✅ RESOLVED - Powell Optimization Replaced with SLSQP

**Issue**: Powell optimizer converged to physically unrealistic local optimum (5 kWh @ 105 kW = 21C-rate).

**Solution**: Replaced Powell with SLSQP optimizer with proper constraints
- SLSQP supports explicit bounds on (E_nom, P_max)
- Added C-rate constraint: P_max/E_nom ≤ 3.0 (physically realistic)
- Proper constraint handling prevents unrealistic solutions

**Files Updated** (2025-11-13):
- `scripts/analysis/optimize_battery_dimensions.py` - Replaced `powell_refinement()` with `slsqp_refinement()`
- `src/config/simulation_config.py` - Updated DimensioningConfig to use slsqp_ parameters

**Status**: RESOLVED ✅

---

## 🟢 IMPROVEMENTS - General

### Code Quality
- [ ] Add comprehensive unit tests for all modules
- [ ] Implement integration tests for full workflows
- [ ] Add type hints throughout codebase
- [ ] Improve error handling and logging

### Documentation
- [ ] Document all configuration parameters
- [ ] Add examples for common use cases
- [ ] Create architecture documentation
- [ ] Document economic model assumptions

### Performance
- [ ] Profile optimization bottlenecks
- [ ] Consider parallel processing for grid search
- [ ] Optimize data loading and caching
- [ ] Reduce memory footprint for large datasets

---

**Last Updated**: 2025-11-11
**Reported By**: User during battery dimensioning analysis session
