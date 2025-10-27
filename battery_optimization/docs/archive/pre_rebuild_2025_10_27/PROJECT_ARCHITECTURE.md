# Battery Optimization Project - Architecture Overview

**Project**: Battery Storage Economic Analysis for 150 kWp Solar Installation
**Location**: Stavanger, Norway
**Last Updated**: 2025-10-27

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         MAIN ENTRY POINT                         │
│                           main.py                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │run_simulation│  │run_optimization│ │ run_analysis │          │
│  └──────┬───────┘  └──────┬────────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CONFIGURATION LAYER                          │
│                          config.py                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ BatteryOptimizationConfig (from config.yaml)             │  │
│  ├──────────────┬─────────────┬──────────────┬──────────────┤  │
│  │LocationConfig│SolarConfig  │ConsumptionCfg│TariffConfig  │  │
│  │BatteryConfig │EconomicConfig│AnalysisConfig│             │  │
│  └──────────────┴─────────────┴──────────────┴──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐
│   DATA LAYER     │  │ OPTIMIZATION │  │  ANALYSIS LAYER  │
└──────────────────┘  └──────────────┘  └──────────────────┘
```

---

## Detailed Component Map

### 1️⃣ DATA FETCHING & GENERATION LAYER

#### 📊 Price Data (`core/price_fetcher.py`)
```
ENTSOEPriceFetcher
├── fetch_day_ahead_prices()      # Get spot prices from ENTSO-E API
├── fetch_prices()                 # Main entry point
├── _convert_to_nok()              # EUR → NOK conversion
└── _validate_data()               # Data quality checks

Output: DataFrame [timestamp, price_nok_per_kwh]
Cache: data/spot_prices/NO2_YYYY_real.csv
Tests: tests/test_price_data_fetching.py (16/16 ✅)
```

#### ☀️ Solar Production (`core/pvgis_solar.py`)
```
PVGISProduction
├── fetch_hourly_production()     # Get production from PVGIS API
├── get_production_data()          # Main entry point
├── calculate_annual_production()  # Sum yearly output
└── _validate_data()               # Data quality checks

Output: DataFrame [timestamp, production_kwh]
Cache: data/pv_profiles/pvgis_LAT_LON_CAPkWp.csv
Tests: tests/test_solar_production.py (19/19 ✅)
```

#### 🏭 Consumption Profiles (`core/consumption_profiles.py`)
```
ConsumptionProfile
├── generate_hourly_profile()      # Create realistic load profile
├── _base_pattern()                # Diurnal variation
├── _weekly_pattern()              # Weekday/weekend
├── _seasonal_pattern()            # Summer/winter
└── _add_noise()                   # Realistic variability

Output: DataFrame [timestamp, consumption_kwh]
Pattern: Commercial building (low baseline, daytime peaks)
```

#### ⚡ Solar System Model (`core/solar.py`)
```
SolarSystem
├── calculate_production()         # Apply losses and limits
├── calculate_curtailment()        # Export limitation (77 kW)
├── apply_inverter_clipping()      # Inverter limit (110 kW)
├── apply_shading_losses()         # Environmental losses
└── get_usable_production()        # Net available energy

Parameters:
- PV Capacity: 138.55 kWp
- Inverter: 110 kW
- Grid Export Limit: 77 kW
- Tilt: 30°, Azimuth: 173°
```

---

### 2️⃣ BATTERY MODELING LAYER

#### 🔋 Battery Model (`core/battery.py`)
```
Battery
├── charge()                       # Charge operation with efficiency
├── discharge()                    # Discharge with efficiency
├── get_state()                    # Current SoC, capacity
├── step()                         # Hourly simulation step
├── apply_degradation()            # Lifetime degradation model
└── reset()                        # Reset to initial state

Properties:
- Capacity (kWh): 20-200 kWh range
- Power (kW): 10-100 kW range
- Efficiency: 90% round-trip
- Degradation: 2%/year
- Lifetime: 15 years
```

#### 🔋 MILP Battery Model (`core/optimization_real/battery_model.py`)
```
BatteryModel
├── create_variables()             # LP decision variables
├── add_constraints()              # Physical/operational limits
├── calculate_operating_cost()     # Degradation costs
└── get_solution()                 # Extract optimal schedule

Variables:
- charge_power[t], discharge_power[t]
- soc[t]: State of charge
- grid_import[t], grid_export[t]
```

---

### 3️⃣ OPTIMIZATION LAYER

#### 🎯 Differential Evolution Optimizer (`core/optimizer.py`)
```
BatteryOptimizer
├── optimize()                     # Main optimization loop
├── _objective_function()          # NPV calculation
├── _simulate_year()               # Hourly simulation
├── _calculate_revenue()           # All revenue streams
└── _sensitivity_analysis()        # Parameter variation

Algorithm: scipy.optimize.differential_evolution
Search Space:
- capacity_kwh: 20-200 kWh
- power_kw: 10-100 kW
Objective: Maximize NPV @ 5% discount rate
```

#### 🎯 MILP Optimizer (`core/optimization_real/milp_optimizer.py`)
```
MILPBatteryOptimizer
├── optimize_operation()           # Optimal dispatch
├── _build_model()                 # Construct LP problem
├── _add_objectives()              # Revenue maximization
├── _solve()                       # Call solver (HiGHS/CBC)
└── _extract_results()             # Parse solution

Solver: HiGHS (default) or CBC
Objective: max(revenue - costs) over horizon
Constraints: Battery physics, grid limits, tariffs
```

#### 🎯 Real Optimizer (`core/optimization_real/optimizer.py`)
```
BatteryOptimizer (Real)
├── optimize_battery_size()        # Find optimal capacity/power
├── optimize_operation()           # Dispatch for given size
├── calculate_economics()          # NPV/IRR/payback
└── sensitivity_analysis()         # Parameter sweeps

Integration: Uses MILPBatteryOptimizer for dispatch
Output: OptimizationResult with full economics
```

---

### 4️⃣ ECONOMIC ANALYSIS LAYER

#### 💰 Economic Model (`core/optimization_real/economic_model.py`)
```
EconomicModel
├── calculate_annual_revenue()     # All revenue streams
├── calculate_annual_costs()       # O&M, degradation
├── calculate_npv()                # Net present value
├── calculate_irr()                # Internal rate of return
├── calculate_payback()            # Simple payback period
└── sensitivity_analysis()         # Parameter variations

Revenue Streams:
1. Peak Shaving (curtailment reduction)
2. Energy Arbitrage (buy low, sell high)
3. Demand Charge Reduction (power tariff)
4. Self-consumption (avoid grid charges)
```

#### 💰 Economic Analysis (`core/economic_analysis.py`)
```
EconomicAnalyzer
├── analyze_battery_economics()    # Full economic analysis
├── calculate_npv()                # NPV calculation
├── calculate_irr()                # IRR solver
├── calculate_payback_period()     # Payback calculation
└── find_break_even_cost()         # Break-even battery price

Functions:
- sensitivity_analysis()           # Multi-parameter sweep
- calculate_all_value_drivers()    # Revenue breakdown
```

#### 💎 Value Drivers (`core/value_drivers.py`)
```
Value Driver Functions
├── calculate_curtailment_value()  # Avoided curtailment
├── calculate_arbitrage_value()    # Price arbitrage
├── calculate_demand_charge_savings() # Power tariff reduction
└── calculate_self_consumption_value() # Grid charge avoidance

Analysis: Breakdown of battery value by source
Used for: Investment decision, sensitivity analysis
```

---

### 5️⃣ RESULTS & REPORTING LAYER

#### 📊 Result Presenter (`core/result_presenter.py`)
```
ResultPresenter
├── create_report()                # Generate full report
├── plot_monthly_production()      # Solar production chart
├── plot_daily_profile()           # Typical day analysis
├── plot_duration_curve()          # Production/demand curves
├── plot_power_tariff()            # Tariff bracket analysis
├── plot_economics()               # NPV/IRR/payback charts
└── export_to_html()               # Interactive HTML report

Output Formats:
- HTML (Plotly interactive charts)
- Markdown (text report)
- JSON (structured data)
```

#### 📈 Visualization Scripts (`results/generate_visualizations.py`)
```
Standalone Visualization Functions
├── fig1_monthly_production()      # Monthly bars
├── fig2_daily_profile()           # Hourly patterns
├── fig3_duration_curve()          # Load duration
├── fig4_power_tariff()            # Tariff brackets
├── fig5_may_analysis()            # Curtailment example
├── fig6_june15()                  # Single day detail
├── fig8_cashflow()                # NPV over time
└── fig9_value_drivers()           # Revenue breakdown

Output: results/figN_*.html (Plotly)
```

---

## Data Flow Diagram

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  ENTSO-E    │────────▶│Price Fetcher│────────▶│   Cached    │
│     API     │         │             │         │ Price Data  │
└─────────────┘         └─────────────┘         └──────┬──────┘
                                                       │
┌─────────────┐         ┌─────────────┐               │
│  PVGIS API  │────────▶│Solar Fetcher│───────────────┤
└─────────────┘         └─────────────┘               │
                                                       │
┌─────────────┐         ┌─────────────┐               │
│config.yaml  │────────▶│Consumption  │               │
│             │         │  Generator  │               │
└─────────────┘         └─────────────┘               │
                                                       │
                                                       ▼
                        ┌──────────────────────────────────┐
                        │      HOURLY TIME SERIES          │
                        │  [8760 hours × 3 columns]        │
                        │  - price_nok_per_kwh             │
                        │  - solar_production_kwh          │
                        │  - consumption_kwh               │
                        └──────────────┬───────────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────────┐
                        │     OPTIMIZATION ENGINE          │
                        │  - Differential Evolution OR     │
                        │  - MILP Solver                   │
                        └──────────────┬───────────────────┘
                                       │
                        ┌──────────────┴───────────────┐
                        ▼                              ▼
            ┌──────────────────┐          ┌──────────────────┐
            │ Optimal Battery  │          │ Economic Results │
            │ - Size (kWh)     │          │ - NPV            │
            │ - Power (kW)     │          │ - IRR            │
            │ - Schedule       │          │ - Payback        │
            └──────────────────┘          └──────────────────┘
                        │                              │
                        └──────────────┬───────────────┘
                                       ▼
                        ┌──────────────────────────────────┐
                        │         REPORTING                │
                        │  - HTML Reports                  │
                        │  - Interactive Charts            │
                        │  - Sensitivity Analysis          │
                        └──────────────────────────────────┘
```

---

## Configuration System

### YAML → Python Architecture

```
config.yaml (Data Source)
├── site: {location, latitude, longitude}
├── solar: {pv_capacity, inverter, tilt, azimuth, grid_limit}
├── consumption: {annual_kwh, profile_type}
├── battery: {capacity_range, power_range, efficiency, lifetime}
├── economics: {discount_rate, project_years}
└── analysis: {start_year, end_year}
         │
         ▼
config.py (Type Safety & Structure)
├── LocationConfig (dataclass)
├── SolarSystemConfig (dataclass)
├── ConsumptionConfig (dataclass)
├── BatteryConfig (dataclass)
├── TariffConfig (dataclass)
│   ├── power_brackets: [(kW_min, kW_max, NOK/month)]
│   ├── energy_peak: 0.296 kr/kWh
│   ├── energy_offpeak: 0.176 kr/kWh
│   └── consumption_tax_monthly: {month: kr/kWh}
├── EconomicConfig (dataclass)
├── AnalysisConfig (dataclass)
└── BatteryOptimizationConfig (main config)
    └── from_yaml() → Load YAML into dataclasses
```

**Design Pattern**:
- YAML = Human-editable data
- Python = Type safety + validation + complex structures
- Loading: `config = BatteryOptimizationConfig.from_yaml()`

---

## Testing Architecture

### Test Coverage Map

```
tests/
├── test_price_data_fetching.py (16 tests ✅)
│   ├── test_fetch_prices_2023_structure
│   ├── test_fetch_prices_2023_quality
│   ├── test_price_range_validation
│   ├── test_negative_prices_detected
│   ├── test_currency_conversion
│   └── test_caching_mechanism
│
├── test_solar_production.py (19 tests ✅)
│   ├── test_pvgis_data_structure
│   ├── test_annual_production_realistic
│   ├── test_monthly_distribution
│   ├── test_inverter_clipping
│   ├── test_curtailment_calculation
│   └── test_caching_works
│
└── [PENDING]
    ├── test_battery_model.py
    ├── test_optimizer.py
    ├── test_economic_analysis.py
    └── test_integration.py
```

**Testing Strategy**: See `docs/TESTING_STRATEGY.md`

---

## Key Algorithms

### 1. Differential Evolution Battery Sizing

```python
# Search space
bounds = [
    (20, 200),   # capacity_kwh
    (10, 100)    # power_kw
]

# Objective function
def npv(x):
    capacity, power = x
    revenue = simulate_year(capacity, power)
    capex = capacity * battery_cost_per_kwh
    return calculate_npv(revenue, capex, 15_years, 5%)

# Optimize
result = differential_evolution(
    func=lambda x: -npv(x),  # Minimize -NPV = Maximize NPV
    bounds=bounds,
    strategy='best1bin',
    maxiter=100
)
```

### 2. MILP Battery Dispatch

```python
# Variables (for each hour t)
charge[t] ∈ [0, power_kw]
discharge[t] ∈ [0, power_kw]
soc[t] ∈ [0, capacity_kwh]

# Constraints
soc[t+1] = soc[t] + charge[t]*η - discharge[t]/η
charge[t] * discharge[t] = 0  # Can't charge and discharge
grid_export[t] ≤ 77 kW

# Objective
maximize: Σ(revenue[t] - cost[t])
where revenue = arbitrage + peak_shaving + demand_charge_reduction
```

### 3. Economic Metrics

```python
# NPV Calculation
npv = -capex + Σ(cash_flow[year] / (1 + discount_rate)^year)

# IRR Calculation
0 = -capex + Σ(cash_flow[year] / (1 + irr)^year)
# Solve for irr using scipy.optimize.newton

# Payback Period
cumulative_cashflow = cumsum(cash_flow)
payback_years = first year where cumulative_cashflow > capex
```

---

## Revenue Streams Breakdown

### 1️⃣ Peak Shaving (Curtailment Reduction)
```
Without Battery:
PV > 77 kW → Curtailed (lost revenue)

With Battery:
PV > 77 kW → Charge battery → Export later
Value: curtailed_kwh × spot_price
```

### 2️⃣ Energy Arbitrage
```
Low Price Hours (night):
Charge from grid @ low_price

High Price Hours (day):
Discharge to grid @ high_price

Value: (high_price - low_price) × kwh × efficiency
```

### 3️⃣ Demand Charge Reduction
```
Without Battery:
Monthly peak = 85 kW → 3372 NOK/month

With Battery:
Battery shaves peak to 70 kW → 2572 NOK/month

Value: 800 NOK/month × 12 = 9600 NOK/year
```

### 4️⃣ Self-Consumption Increase
```
Without Battery:
Export @ spot_price, Import @ (spot + grid_tariff)

With Battery:
Store excess → Use during consumption peaks
Avoid: grid_tariff (peak 0.296 kr/kWh)

Value: avoided_import_kwh × grid_tariff
```

---

## File Structure

```
offgrid2/
├── battery_optimization/
│   ├── config.yaml                     # Configuration data
│   ├── config.py                       # Configuration dataclasses
│   ├── main.py                         # Main entry point
│   ├── run_simulation.py               # Simulation runner
│   │
│   ├── core/                           # Core modules
│   │   ├── price_fetcher.py            # ENTSO-E price data
│   │   ├── pvgis_solar.py              # PVGIS solar data
│   │   ├── solar.py                    # Solar system model
│   │   ├── battery.py                  # Battery model
│   │   ├── consumption_profiles.py     # Load profile generation
│   │   ├── optimizer.py                # DE optimizer
│   │   ├── economic_analysis.py        # NPV/IRR calculations
│   │   ├── value_drivers.py            # Revenue breakdown
│   │   ├── result_presenter.py         # Report generation
│   │   │
│   │   └── optimization_real/          # MILP optimization
│   │       ├── battery_model.py        # LP battery model
│   │       ├── milp_optimizer.py       # MILP solver
│   │       ├── optimizer.py            # Real optimizer
│   │       └── economic_model.py       # Economic model
│   │
│   ├── data/                           # Cached data
│   │   ├── spot_prices/                # ENTSO-E price cache
│   │   └── pv_profiles/                # PVGIS production cache
│   │
│   ├── tests/                          # Test suites
│   │   ├── test_price_data_fetching.py # Price tests (16/16 ✅)
│   │   └── test_solar_production.py    # Solar tests (19/19 ✅)
│   │
│   ├── docs/                           # Documentation
│   │   ├── TESTING_STRATEGY.md         # Testing approach
│   │   ├── CODE_DUPLICATION_ANALYSIS.md# Cleanup analysis
│   │   ├── PRICE_FETCHER_CONSOLIDATION.md
│   │   ├── TARIFF_MAINTENANCE.md       # Tariff update guide
│   │   └── PROJECT_ARCHITECTURE.md     # This file
│   │
│   ├── results/                        # Output files
│   │   ├── fig*.html                   # Plotly visualizations
│   │   └── generate_visualizations.py  # Viz scripts
│   │
│   ├── archive/                        # Deprecated code
│   │   ├── deprecated_generators/      # Old data generators
│   │   ├── deprecated_price_fetchers/  # Old price modules
│   │   ├── legacy_reports/             # Old report scripts
│   │   └── notebooks/                  # Jupyter notebooks
│   │
│   └── scripts/                        # Utility scripts
│       └── update_cache_metadata.py    # Cache management
│
└── docs/                               # Project-level docs
    └── *.png                           # Presentation materials
```

---

## External Dependencies

### Data Sources (APIs)
```
ENTSO-E Transparency Platform
├── URL: https://transparency.entsoe.eu/
├── Purpose: Day-ahead electricity prices (NO2 bidding zone)
├── Authentication: API key required (free registration)
└── Rate Limit: Reasonable use (cached locally)

PVGIS (Photovoltaic Geographical Information System)
├── URL: https://re.jrc.ec.europa.eu/pvg_tools/en/
├── Purpose: Solar production estimates (TMY data)
├── Authentication: None (free public API)
└── Rate Limit: Reasonable use (cached locally)
```

### Python Libraries
```
Core Scientific Stack:
- numpy: Numerical computations
- pandas: Time series data handling
- scipy: Optimization algorithms, IRR solver

Optimization:
- pulp: MILP modeling framework
- scipy.optimize: Differential evolution

Visualization:
- plotly: Interactive charts
- matplotlib: Static plots

API & Data:
- requests: HTTP API calls
- pyyaml: Configuration loading
- python-dotenv: Environment variables

Testing:
- pytest: Testing framework
- pytest-cov: Coverage reporting
```

### Solvers (for MILP)
```
HiGHS (Primary)
├── Type: Open-source LP/MIP solver
├── Installation: Bundled with scipy ≥1.9
├── Performance: Excellent for medium problems
└── License: MIT

CBC (Coin-or Branch and Cut)
├── Type: Open-source MIP solver
├── Installation: conda install coin-or-cbc
├── Performance: Robust, good for large problems
└── License: EPL (Eclipse Public License)

Google OR-Tools (Optional)
├── Type: Google optimization toolkit
├── Installation: pip install ortools
├── Performance: Fast, production-ready
└── License: Apache 2.0
```

---

## Performance Characteristics

### Computation Time

```
Data Fetching (with cache):
- Price data (1 year): ~0.5s (cached) / ~5s (API)
- Solar data (1 year): ~0.3s (cached) / ~3s (API)
- Consumption generation: ~0.1s

Optimization:
- DE battery sizing (100 iterations): ~60-120s
- MILP dispatch (8760 hours): ~5-15s
- Sensitivity analysis (10×10 grid): ~10-15 min

Reporting:
- Generate all plots: ~5-10s
- HTML report creation: ~2-3s
```

### Memory Usage

```
Data Storage:
- Price time series (8760 hours): ~70 KB
- Solar production (8760 hours): ~70 KB
- Full simulation results: ~500 KB
- Cached data (5 years): ~2 MB

Runtime:
- Base simulation: ~50 MB
- DE optimization: ~200 MB
- MILP optimization: ~500 MB
- Sensitivity analysis: ~1 GB
```

---

## Known Issues & Limitations

### ⚠️ Current Limitations

1. **No Real-Time Updates**
   - Tariffs manually hardcoded (see `docs/TARIFF_MAINTENANCE.md`)
   - Battery costs manually entered
   - No automatic updates when utilities change rates

2. **Testing Gaps**
   - Battery module: No tests yet
   - Economic analysis: No tests yet
   - Integration tests: None
   - End-to-end: Not tested

3. **Configuration Discrepancies**
   - Two different consumption_tax values found in codebase
   - config.py: Jan-Mar 0.0979, Apr-Sep 0.1693, Oct-Dec 0.1253
   - archived tariffs.py: Jan-Mar 0.1541, Apr-Sep 0.0891
   - **Needs verification against Lnett/Skatteetaten**

4. **Data Quality**
   - 2023 price data shows anomalies (negative prices)
   - No validation against actual utility bills
   - PVGIS TMY may not match specific year conditions

### 🔧 Planned Improvements

1. **Testing**
   - Add battery model unit tests
   - Add economic calculation tests
   - Add integration tests for main.py
   - Add regression tests for economics

2. **Validation**
   - Verify consumption_tax rates
   - Cross-check with utility bills
   - Validate against real system performance

3. **Features**
   - Automated tariff updates (web scraping)
   - Multi-year weather data
   - Battery degradation uncertainty
   - Real-time vs day-ahead optimization

---

## Development Workflow

### Adding New Features

```
1. Update config.yaml (if new parameters)
2. Update config.py dataclasses
3. Implement feature in core/
4. Write tests in tests/
5. Run test suite: pytest tests/ -v
6. Update documentation
7. Commit with clear message
```

### Running Analysis

```bash
# Full optimization
cd battery_optimization
python main.py

# Quick simulation with defaults
python run_simulation.py

# Generate visualizations only
python results/generate_visualizations.py
```

### Testing

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/test_price_data_fetching.py -v
pytest tests/test_solar_production.py -v

# With coverage
pytest tests/ --cov=core --cov-report=html
```

---

## References

### Documentation
- [Testing Strategy](TESTING_STRATEGY.md)
- [Price Fetcher Consolidation](PRICE_FETCHER_CONSOLIDATION.md)
- [Tariff Maintenance Guide](TARIFF_MAINTENANCE.md)
- [Code Duplication Analysis](CODE_DUPLICATION_ANALYSIS.md)

### External Resources
- [ENTSO-E API Documentation](https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html)
- [PVGIS User Manual](https://joint-research-centre.ec.europa.eu/pvgis-photovoltaic-geographical-information-system/pvgis-user-manual_en)
- [Lnett Nettleie](https://www.lnett.no/nettleie/bedrift/)
- [PuLP Documentation](https://coin-or.github.io/pulp/)

---

**Last Updated**: 2025-10-27
**Status**: Active Development (Testing Phase)
**Test Coverage**: 35/35 tests passing (price + solar modules only)
