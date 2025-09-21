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
python main.py
```

## 📁 Project Structure

```
battery_optimization/
├── src/
│   ├── config.py                    # System configuration
│   ├── data_fetchers/
│   │   ├── entso_e_client.py       # ENTSO-E API for spot prices
│   │   └── solar_production.py      # PV production modeling
│   ├── optimization/
│   │   ├── battery_model.py        # Battery dynamics
│   │   ├── economic_model.py       # NPV calculations
│   │   └── optimizer.py            # Main optimization engine
│   └── analysis/
│       ├── sensitivity.py          # Sensitivity analysis
│       └── visualization.py        # Result visualization
├── data/                           # Cached data
├── results/                        # Analysis outputs
└── main.py                        # Entry point
```

## 🔋 Key Features

### 1. Battery Operation Strategies
- **Peak Shaving**: Minimize curtailment from grid limits
- **Arbitrage**: Optimize based on price differentials
- **Combined**: Intelligent priority-based control

### 2. Economic Analysis
- Net Present Value (NPV) calculation
- Internal Rate of Return (IRR)
- Payback period analysis
- Break-even battery cost determination

### 3. Sensitivity Analysis
- Battery size optimization (kWh and kW independently)
- Price volatility impact
- Tariff rate sensitivity
- Degradation rate effects

### 4. Data Sources
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

Edit `src/config.py` to adjust:

```python
# System parameters
pv_capacity_kwp = 150.0
inverter_capacity_kw = 110.0
grid_capacity_kw = 77.0

# Economic assumptions
discount_rate = 0.05  # 5% annual
battery_lifetime_years = 15
eur_to_nok = 11.5

# Battery constraints
round_trip_efficiency = 0.95

# Battery sizing defaults
battery_capacity_kwh = 50  # Updated default
battery_power_kw = 20      # Updated default
min_soc = 0.10
max_soc = 0.90
```

## 📊 Analysis Methodology

### 1. Data Collection
- Fetch hourly spot prices from ENTSO-E
- Model PV production using location and system specs
- Apply Lnett tariff structure

### 2. Optimization
- Use differential evolution to find optimal battery size
- Simulate hourly operation over full year
- Calculate NPV for each configuration

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