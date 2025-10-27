# Battery Optimization - Testing Strategy

**Purpose**: Systematic testing approach for validating battery optimization modules
**Framework**: pytest with comprehensive acceptance criteria
**Status**: 2/N modules tested (Price Data ✅, Solar Production ✅)

---

## 📋 Testing Philosophy

### Gradual Module Testing
Test modules individually before integration testing:
1. **Price Data** ✅ - Electricity prices from ENTSO-E
2. **Solar Production** ✅ - PV production from PVGIS
3. **Battery Simulation** - Battery state modeling
4. **Economic Analysis** - NPV, IRR, payback calculations
5. **Optimization** - Differential evolution optimizer
6. **Integration** - Full system end-to-end

### Acceptance Criteria Framework
Each module test suite organized by **5 Acceptance Criteria (AC)**:
- **AC1**: Core functionality and API integration
- **AC2**: Data quality and validation
- **AC3**: Edge cases and limits
- **AC4**: Calculations and algorithms
- **AC5**: Error handling and fallbacks

---

## ✅ Completed Module Tests

### 1. Price Data Module (`test_price_data_fetching.py`)

**Module**: `core/price_fetcher.py`
**Status**: ✅ 16/16 tests passing

**Acceptance Criteria**:
- AC1: EUR → NOK currency conversion (×11.5 ÷1000)
- AC2: Complete 2023 hourly data (8760 hours)
- AC3: 15-minute resolution investigation (documented as feasible)
- AC4: Timezone and DST handling (Europe/Oslo with transitions)
- AC5: Leap year handling (automatic via pandas)

**Key Findings**:
- ✅ Real ENTSO-E API data (not simulated)
- ✅ 174 hours of negative prices in 2023 (battery opportunity!)
- ✅ Mean price: 0.914 NOK/kWh
- ✅ Range: -0.711 to 3.011 NOK/kWh

**Test Duration**: 3.3 seconds
**Documentation**: `docs/PRICE_DATA_TEST_RESULTS_FINAL.md`

---

### 2. Solar Production Module (`test_solar_production.py`)

**Modules**: `core/pvgis_solar.py`, `core/solar.py`
**Status**: ✅ 19/19 tests passing

**Acceptance Criteria**:
- AC1: PVGIS API integration and caching
- AC2: Production data quality and validation
- AC3: Inverter limits and clipping detection
- AC4: Curtailment calculations (grid export limits)
- AC5: Fallback handling (simple solar model)

**Key Findings**:
- ✅ Annual production: 127.3 MWh (PVGIS 2020 data)
- ✅ Capacity factor: 10.5% (typical for Stavanger)
- ✅ Curtailment: 10.7 MWh at 77 kW grid limit (8.4%)
- ✅ Oversizing ratio: 1.39 (optimal for location)

**Test Duration**: 2.3 seconds
**Documentation**: `docs/SOLAR_PRODUCTION_TEST_RESULTS.md`

---

## 📝 Test Template Structure

### Standard Test File Organization

```python
"""
Comprehensive test suite for [Module Name]

Test Categories:
- AC1: [Primary functionality]
- AC2: [Data quality]
- AC3: [Edge cases]
- AC4: [Calculations]
- AC5: [Error handling]
"""

import pytest
import pandas as pd
from core.[module] import [Classes]
from config import [ConfigClasses]

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def config():
    """Load configuration"""
    return ConfigClass()

@pytest.fixture
def module_instance(config):
    """Create module instance"""
    return Module(config)

# ============================================================================
# AC1: [Primary Functionality]
# ============================================================================

class TestAC1_[Category]:
    """Test [primary functionality description]"""

    def test_[specific_functionality](self, module_instance):
        """Test description"""
        result = module_instance.method()

        assert result is not None
        print(f"\n✅ [Success message]")

# ... repeat for AC2-AC5 ...

# ============================================================================
# Summary Test
# ============================================================================

def test_module_summary(module_instance, config):
    """Generate comprehensive summary"""
    print("\n" + "="*70)
    print("[MODULE NAME] - TEST SUMMARY")
    print("="*70)

    # Run key operations and display results

    print("\n✅ ALL TESTS COMPLETE")
```

---

## 🔬 Test Development Process

### Step 1: Understand Module
```bash
# Read module source code
Read core/[module].py

# Check configuration
Read config.py | grep [Module]Config

# Check for existing data/cache
ls -la data/[module_directory]/
```

### Step 2: Define Acceptance Criteria
Based on module purpose, define 5 ACs:
1. What is the **core functionality**?
2. What **data quality** matters?
3. What **edge cases** exist?
4. What **calculations** need validation?
5. What **errors** can occur?

### Step 3: Create Test Fixtures
```python
@pytest.fixture
def config():
    """Module configuration from project config"""
    return ModuleConfig()

@pytest.fixture
def module_instance(config):
    """Module instance with test configuration"""
    return Module(**config.__dict__)
```

### Step 4: Write Test Classes
One class per AC:
```python
class TestAC1_CoreFunctionality:
    def test_method_returns_data(self, module_instance):
        result = module_instance.fetch_data()
        assert result is not None
        assert len(result) > 0
```

### Step 5: Add Summary Test
```python
def test_module_summary(module_instance):
    """Comprehensive summary with key metrics"""
    print("\n" + "="*70)
    print("[MODULE] TEST SUMMARY")
    print("="*70)
    # Display key results
```

### Step 6: Run and Fix
```bash
# Run tests
python -m pytest tests/test_[module].py -v

# Run with output
python -m pytest tests/test_[module].py -v -s

# Run summary only
python -m pytest tests/test_[module].py::test_module_summary -v -s
```

### Step 7: Document Results
Create `docs/[MODULE]_TEST_RESULTS.md`:
- Executive summary
- AC results (pass/fail)
- Key findings
- Data quality metrics
- Recommendations

---

## 🎯 Acceptance Criteria Guidelines

### AC1: Core Functionality
**Focus**: Does the module do what it's supposed to do?

**Examples**:
- API integration works
- Data fetching succeeds
- Core methods return expected types
- Configuration is loaded correctly

**Tests**:
- Test primary method execution
- Test with/without cache
- Test configuration validation
- Test API parameters

---

### AC2: Data Quality
**Focus**: Is the data correct, complete, and consistent?

**Examples**:
- Correct number of records
- No missing values (NaN)
- Values within realistic ranges
- Expected patterns present

**Tests**:
- Test data completeness (8760 hours, etc.)
- Test value ranges (min, max, mean)
- Test for NaN/missing data
- Test temporal patterns (seasonal, daily)

---

### AC3: Edge Cases and Limits
**Focus**: Does it handle boundaries correctly?

**Examples**:
- Maximum/minimum values
- Capacity limits (inverter, battery)
- Timezone transitions (DST)
- Leap years

**Tests**:
- Test at maximum capacity
- Test at zero/minimum
- Test DST transitions
- Test leap year handling

---

### AC4: Calculations and Algorithms
**Focus**: Are calculations mathematically correct?

**Examples**:
- Unit conversions (EUR→NOK, W→kW)
- Percentage calculations
- Cumulative sums
- Complex formulas (NPV, IRR)

**Tests**:
- Test with known inputs/outputs
- Test inverse operations
- Test edge case math (division by zero)
- Compare with manual calculations

---

### AC5: Error Handling and Fallbacks
**Focus**: What happens when things go wrong?

**Examples**:
- API unavailable
- Missing data files
- Invalid parameters
- Network timeouts

**Tests**:
- Test fallback mechanisms
- Test with invalid inputs
- Test error messages
- Test graceful degradation

---

## 📊 Test Metrics and Quality Gates

### Coverage Targets
- **Unit Test Coverage**: 100% of core functionality
- **AC Coverage**: All 5 ACs must have ≥3 tests each
- **Pass Rate**: 100% (all tests must pass)

### Performance Targets
- **Individual Tests**: <5 seconds each
- **Full Module Suite**: <10 seconds total
- **API Tests**: Use cache to stay <2 seconds

### Quality Indicators
✅ **Good Test Suite**:
- Clear test names describing what is tested
- Comprehensive print statements showing results
- Summary test showing key metrics
- Documentation with findings

❌ **Poor Test Suite**:
- Generic test names (test_1, test_2)
- Silent tests (no output)
- No summary or documentation
- Tests that always pass

---

## 🚀 Next Module Testing Plan

### 3. Battery Simulation Module (Next)

**Modules to Test**: `core/battery.py`

**Proposed Acceptance Criteria**:
- **AC1**: Battery state initialization and configuration
- **AC2**: Charge/discharge operations and efficiency
- **AC3**: State of Charge (SoC) limits and constraints
- **AC4**: Degradation modeling over lifetime
- **AC5**: Edge cases (full/empty, max C-rate)

**Test File**: `tests/test_battery_simulation.py`

**Key Metrics to Validate**:
- Round-trip efficiency (90%)
- SoC min/max (10%-90%)
- C-rate limits (charge/discharge)
- Degradation rate (2% per year)
- Lifetime cycles

---

### 4. Economic Analysis Module

**Modules to Test**: `core/economics.py`, `core/economic_analysis.py`

**Proposed Acceptance Criteria**:
- **AC1**: NPV calculation accuracy
- **AC2**: IRR and payback period calculations
- **AC3**: Cash flow modeling over 15 years
- **AC4**: Tariff cost calculations (energy + power)
- **AC5**: Sensitivity analysis ranges

---

### 5. Optimization Module

**Modules to Test**: `core/optimization/optimizer.py`, `core/optimization/milp_optimizer.py`

**Proposed Acceptance Criteria**:
- **AC1**: Optimizer convergence
- **AC2**: Optimal battery size determination
- **AC3**: Constraint satisfaction
- **AC4**: Performance metrics (runtime, iterations)
- **AC5**: Multiple solver compatibility (HiGHS, CBC)

---

## 📚 Best Practices

### 1. Test Naming
```python
# ✅ Good
def test_production_respects_inverter_limit()
def test_currency_conversion_formula()
def test_dst_spring_transition_2023()

# ❌ Bad
def test_1()
def test_production()
def test_data()
```

### 2. Assertions with Messages
```python
# ✅ Good
assert len(prices) == 8760, f"Expected 8760 hours, got {len(prices)}"

# ❌ Bad
assert len(prices) == 8760
```

### 3. Print Statements
```python
# ✅ Good
print(f"\n📊 Statistics:")
print(f"   Annual: {annual_mwh:.1f} MWh")
print(f"   Mean: {mean_kw:.2f} kW")

# ❌ Bad (no output)
mean_kw = data.mean()
```

### 4. Use Fixtures
```python
# ✅ Good
@pytest.fixture
def config():
    return SolarSystemConfig()

def test_with_config(config):
    assert config.pv_capacity_kwp == 138.55

# ❌ Bad (repeated setup)
def test_1():
    config = SolarSystemConfig()
    assert config.pv_capacity_kwp == 138.55

def test_2():
    config = SolarSystemConfig()  # Repeated!
```

### 5. Comprehensive Summary
```python
def test_module_summary(module_instance):
    print("\n" + "="*70)
    print("MODULE TEST SUMMARY")
    print("="*70)

    # Show key metrics
    # Show validation results
    # Show recommendations

    print("="*70)
    print("✅ ALL TESTS COMPLETE")
    print("="*70)
```

---

## 🔗 Integration Testing Strategy

After all modules tested individually:

### Phase 1: Pairwise Integration
- Price + Solar → Production value analysis
- Battery + Solar → Curtailment storage
- Economics + Battery → Cost-benefit analysis

### Phase 2: Full System Integration
- End-to-end simulation
- Realistic scenario validation
- Performance benchmarking

### Phase 3: Regression Testing
- Ensure changes don't break existing functionality
- Automated test suite for CI/CD
- Regular validation against new data

---

## 📈 Progress Tracking

| Module | Tests | Status | Coverage | Duration | Doc |
|--------|-------|--------|----------|----------|-----|
| Price Data | 16 | ✅ PASS | 100% | 3.3s | ✅ |
| Solar Production | 19 | ✅ PASS | 100% | 2.3s | ✅ |
| Battery Simulation | - | 📋 Planned | - | - | - |
| Economic Analysis | - | 📋 Planned | - | - | - |
| Optimization | - | 📋 Planned | - | - | - |
| Integration | - | 📋 Planned | - | - | - |

**Overall Progress**: 2/6 modules tested (33%)

---

## 🎓 Lessons Learned

### From Price Data Testing
1. ✅ Check for timezone-aware data in cache
2. ✅ Use `utc=True` when converting timezone-aware strings
3. ✅ Handle DST transitions with `ambiguous='NaT', nonexistent='NaT'`
4. ✅ Negative electricity prices are real and important!

### From Solar Production Testing
1. ✅ Remember leap years (8784 hours vs 8760)
2. ✅ PVGIS returns DC power (can exceed AC inverter)
3. ✅ Oversizing ratio (1.2-1.4) is normal and beneficial
4. ✅ Curtailment quantifies battery opportunity

---

**Document Created**: 2025-10-27
**Last Updated**: 2025-10-27
**Next Review**: After battery simulation testing
