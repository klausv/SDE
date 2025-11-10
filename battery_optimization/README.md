# 🔋 Battery Optimization - Clean & Simple

## ✨ One Command to Run Everything

```bash
python run_analysis.py
```

That's it! Everything else is optional.

## 🎯 Project Overview

Battery optimization for a 138.55 kWp solar installation in Stavanger, Norway. Analyzes economic viability considering:
- **Curtailment**: Avoiding loss when production > 77 kW grid limit
- **Arbitrage**: Buy low, sell high based on spot prices
- **Demand Charges**: Reducing monthly peak power costs
- **Self-Consumption**: Using own solar instead of grid

## 📊 System Specifications

- **PV System**: 150 kWp, south-facing, 25° tilt
- **Inverter**: 110 kW (oversizing ratio 1.36)
- **Grid Limit**: 77 kW (70% of inverter capacity)
- **Location**: Stavanger (58.97°N, 5.73°E)
- **Tariff**: Lnett commercial < 100 MWh/year

## 🚀 Quick Start

### 1. Installation

```bash
# Navigate to project
cd battery_optimization

# Create conda environment
conda env create -f environment.yml

# Activate environment
conda activate battery_opt
```

### 2. Configure ENTSO-E API

Get your free API key from [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/):

1. Register for free account
2. Go to "My Account Settings"
3. Generate security token
4. Add to `.env` file:

```env
ENTSOE_API_KEY=your_api_key_here
```

### 3. Run Analysis

```bash
# Run from YAML config (recommended for complex setups)
python main.py run --config configs/examples/rolling_horizon_realtime.yaml

# Or use quick CLI modes for simple analysis
python main.py rolling --battery-kwh 80 --battery-kw 60
python main.py monthly --months 1,2,3 --resolution PT60M
python main.py yearly --weeks 52 --resolution PT60M
```

## 📁 Project Structure

```
battery_optimization/
├── src/
│   ├── config/                      # 🆕 Configuration system
│   │   └── simulation_config.py     #     YAML-based config with validation
│   ├── data/                        # 🆕 Data management layer
│   │   ├── data_manager.py          #     Unified data loading & windowing
│   │   └── file_loaders.py          #     CSV loaders with resampling
│   ├── optimization/                # 🆕 Optimizer abstraction
│   │   ├── base_optimizer.py        #     Abstract interface
│   │   ├── rolling_horizon_adapter.py  #  24h rolling horizon
│   │   ├── monthly_lp_adapter.py    #     Monthly LP optimization
│   │   ├── weekly_optimizer.py      #     Weekly (yearly mode)
│   │   └── optimizer_factory.py     #     Factory pattern
│   ├── simulation/                  # 🆕 Orchestration layer
│   │   ├── simulation_results.py    #     Results with export
│   │   ├── rolling_horizon_orchestrator.py  # Real-time mode
│   │   ├── monthly_orchestrator.py  #     Monthly analysis mode
│   │   └── yearly_orchestrator.py   #     Yearly investment mode
│   └── [legacy modules...]          # Original optimizers (still working)
├── configs/                         # 🆕 YAML configuration files
│   └── examples/                    #     Rolling, monthly, yearly examples
├── tests/                           # 🆕 Test suite (46 tests)
│   ├── config/                      #     Config tests (28 passing)
│   ├── integration/                 #     Integration tests (18 passing)
│   └── fixtures/                    #     Test data
├── scripts/                         # 🆕 Organized scripts
│   ├── analysis/                    #     Analysis scripts (14)
│   ├── testing/                     #     Test scripts (16)
│   └── visualization/               #     Plotting scripts (8)
├── logs/                            # 🆕 Log files (11)
├── docs/                            # Documentation
├── archive/                         # Legacy/deprecated code
│   └── legacy_entry_points/         # Old main.py and config.py
├── data/                            # Cached data
├── results/                         # Analysis outputs
└── main.py                          # 🎯 Unified CLI (3 modes)
```

**Recent Updates (2025-01-09):**
- ✅ Major refactoring complete with 3 simulation modes
- ✅ Critical performance, security, and validation fixes applied
- ✅ 46 tests passing (config + data integration)
- ✅ YAML-first configuration approach
- ✅ Project reorganized for better maintainability
- ✅ Legacy code archived - single unified entry point (main.py)

## 🔋 Key Features

### 1. Three Simulation Modes (🆕)

**Rolling Horizon** (Real-time Operation)
- Persistent battery state across optimization windows
- Configurable update frequency (default: 60 min)
- 24-hour lookahead horizon
- Monthly peak tracking
- Use case: Real-time operational control

**Monthly** (Analysis & Planning)
- Single or multi-month optimization
- Full-month horizon per solve
- Proper power tariff modeling
- Cost breakdown by month
- Use case: Monthly performance analysis

**Yearly** (Investment Analysis)
- 52 weekly optimizations (168-hour horizon)
- Persistent state across weeks
- Annual economic metrics
- Use case: Profitability and investment decisions

### 2. Battery Operation Strategies
- **Peak Shaving**: Minimize curtailment from grid limits
- **Arbitrage**: Optimize based on price differentials
- **Combined**: Intelligent priority-based control

### 3. Economic Analysis
- Net Present Value (NPV) calculation
- Internal Rate of Return (IRR)
- Payback period analysis
- Break-even battery cost determination

### 4. Sensitivity Analysis
- Battery size optimization (kWh and kW independently)
- Price volatility impact
- Tariff rate sensitivity
- Degradation rate effects

### 5. Data Sources
- **ENTSO-E**: Real-time NO2 electricity prices
- **Lnett**: Actual grid tariffs for Stavanger
- **PVLib**: Accurate solar production modeling

## 📈 Outputs

### Optimization Results
- **Optimal battery size** (kWh and kW)
- **Maximum viable battery cost** (NOK/kWh)
- **Revenue breakdown** by source
- **Operation metrics** (cycles, self-consumption, etc.)

### Visualizations
- NPV heatmap for different battery configurations
- Break-even cost surface plot
- Sensitivity analysis curves
- Battery operation profiles

### Reports
- HTML summary report with all key metrics
- Excel export of detailed results
- Sensitivity analysis tables

## 🛠️ Configuration

Create or edit YAML configuration files in `configs/` directory:

```yaml
# Example: configs/my_analysis.yaml
mode: rolling_horizon  # or 'monthly' or 'yearly'
time_resolution: PT60M  # PT60M (hourly) or PT15M (15-min)

simulation_period:
  start_date: "2024-01-01"
  end_date: "2024-12-31"

battery:
  capacity_kwh: 80
  power_kw: 60
  efficiency: 0.90
  initial_soc_percent: 50.0
  min_soc_percent: 10.0
  max_soc_percent: 90.0

data_sources:
  prices_file: "data/spot_prices/2024_NO2_hourly.csv"
  production_file: "data/pv_profiles/pvgis_stavanger_2024.csv"
  consumption_file: "data/consumption/commercial_2024.csv"

mode_specific:
  rolling_horizon:
    horizon_hours: 24
    update_frequency_minutes: 60
    persistent_state: true
  monthly:
    months: [1, 2, 3]  # or "all"
  yearly:
    horizon_hours: 168  # 1 week
    weeks: 52
```

See `configs/examples/` for complete configuration examples.

## 📊 Analysis Methodology

### 1. Data Collection
- Fetch hourly spot prices from ENTSO-E
- Model PV production using location and system specs
- Apply Lnett tariff structure

### 2. Optimization
- Use hybrid grid search + Powell method to find optimal battery size
- Simulate hourly operation over full year with rolling horizon
- Calculate NPV for each configuration
- Parallel evaluation for fast convergence (15-20 minutes)

### 3. Sensitivity Analysis
- Vary key parameters systematically
- Identify critical factors for profitability
- Generate break-even surfaces

## 🎯 Key Results (Example)

Based on current analysis:

- **Optimal Battery**: ~80-100 kWh @ 40-60 kW
- **Break-even Cost**: ~3500-4000 NOK/kWh
- **Annual Savings**: ~50,000-70,000 NOK
- **Payback Period**: 8-10 years (at 3000 NOK/kWh)

## 📝 Assumptions & Limitations

### Assumptions
- 5% discount rate
- 15-year battery lifetime
- 2% annual degradation
- 90% round-trip efficiency

### Limitations
- Simplified weather model (use historical average)
- Fixed load profile (customize for your facility)
- No detailed grid constraints modeling
- Tax effects not included

## 🤝 Contributing

Improvements welcome! Key areas:

1. Real weather data integration
2. Machine learning for price forecasting
3. Detailed grid constraint modeling
4. Multi-year optimization
5. Stochastic optimization

## 📜 License

MIT License - See LICENSE file

## 📧 Contact

For questions or support regarding this battery optimization system.

---

**Note**: This tool provides economic analysis for decision support. Always consult with qualified engineers and financial advisors before making investment decisions.