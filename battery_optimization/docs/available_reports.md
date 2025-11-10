# Available Report Types in Battery Optimization System

**Last Updated**: 2025-01-10

## Overview

The battery optimization system provides multiple types of reports and visualizations for analyzing battery performance, economics, and operational strategies. Reports are generated from simulation results and can be exported in various formats.

---

## 📊 Report Categories

### 1. Interactive HTML Reports (Plotly) ⭐ Recommended

**Location**: `scripts/visualization/plotly_yearly_report_v6_optimized.py`

**Description**: Comprehensive interactive yearly report with 11 consolidated visualizations using Plotly. Features Norsk Solkraft branded theme with professional styling.

**Outputs**:
- `results/yearly_2024/plotly_optimized_v6.html` - Interactive HTML report

**Charts Included**:
1. **SOC & Curtailment** - Battery state of charge and curtailed power over time
2. **Battery Power** - Charge/discharge power with grid limits
3. **Grid Power Flows** - Import/export consolidated (positive=import, negative=export)
4. **Spot Price** - Electricity price overlay with tariff zones
5. **Curtailment Comparison** - With/without battery curtailment comparison
6. **Cost Components** - Stacked area chart of cost breakdown
7. **Cumulative Costs** - Running total comparison (reference vs battery)
8. **Economic Savings** - Daily, weekly, monthly savings visualization
9. **Monthly Summary Table** - Peak demand, energy flows, costs by month
10. **Monthly Peak Analysis** - Peak demand with/without battery + peak reduction chart
11. **Economic Metrics Table** - NPV, payback period, IRR, ROI summary

**Features**:
- Fully interactive (zoom, pan, hover tooltips)
- Responsive design (works on mobile/tablet/desktop)
- Theme-native legends (inside top-right, no overlap)
- Strong color contrast for accessibility
- Export to PNG capability

**Usage**:
```bash
python scripts/visualization/plotly_yearly_report_v6_optimized.py results/yearly_2024/
```

**Example Output**: `results/yearly_2024/plotly_optimized_v6.html` (~5 MB)

---

### 2. Battery Dimensioning Reports

**Location**: `scripts/analysis/optimize_battery_dimensions.py`

**Description**: Optimal battery sizing analysis using hybrid grid search + Powell method with weekly sequential optimization.

**Outputs**:
- `results/battery_sizing_optimization.png` - NPV heatmap (E_nom vs P_max)
- `results/battery_sizing_optimization_3d.png` - 3D NPV surface
- `results/battery_sizing_breakeven_costs.png` - Break-even cost heatmap
- `results/battery_sizing_breakeven_costs_3d.png` - 3D break-even surface
- `results/battery_sizing_optimization_results.json` - Optimal dimensions and metrics

**Metrics Provided**:
- Optimal battery capacity (kWh)
- Optimal battery power rating (kW)
- Maximum NPV
- Break-even battery cost (NOK/kWh)
- Annual savings
- Payback period

**Performance**: ~7.5× faster than previous monthly approach (1.6s vs 12s per year)

**Usage**:
```python
from scripts.analysis.optimize_battery_dimensions import BatterySizingOptimizer
from config import BatteryOptimizationConfig

config = BatteryOptimizationConfig.load('config.yaml')
optimizer = BatterySizingOptimizer(config, year=2024, resolution='PT60M')

# Grid search boundaries
E_nom_range = (20, 200)  # kWh
P_max_range = (10, 100)  # kW

results = optimizer.optimize_hybrid_grid_powell(
    E_nom_range=E_nom_range,
    P_max_range=P_max_range,
    grid_resolution=8  # 8×8 grid = 64 evaluations
)
```

---

### 3. Break-Even Analysis Reports

**Location**: `core/reporting/` + legacy `scripts/analysis/calculate_breakeven.py`

**Description**: Economic analysis determining maximum viable battery cost for profitability.

**Outputs**:
- `results/reports/YYYY-MM-DD_HHMMSS_breakeven_analysis.md` - Markdown report
- `results/figures/breakeven/npv_sensitivity.png` - NPV vs battery cost
- `results/figures/breakeven/payback_period.png` - Payback vs battery cost
- `results/annual_breakeven_analysis.json` - JSON summary

**Analysis Includes**:
- Break-even battery cost (NOK/kWh)
- NPV sensitivity to battery cost
- Payback period calculations
- IRR (Internal Rate of Return)
- Sensitivity to discount rate

**Usage** (New Framework):
```python
from pathlib import Path
from core.reporting import SimulationResult
from reports import BreakevenReport

reference = SimulationResult.load(Path('results/simulations/2024-10-30_reference'))
battery = SimulationResult.load(Path('results/simulations/2024-10-30_battery'))

report = BreakevenReport(
    reference=reference,
    battery_scenario=battery,
    output_dir=Path('results'),
    battery_lifetime_years=15,
    discount_rate=0.05
)

report_path = report.generate()
```

---

### 4. Monthly Summary Reports

**Description**: Aggregated monthly statistics for battery operation and economics.

**Outputs**:
- `results/yearly_2024/monthly_summary.csv` - CSV with monthly metrics
- `results/annual_monthly_summary_2024.json` - JSON format

**Metrics per Month**:
- Peak demand (with/without battery)
- Peak reduction (kW and %)
- Total energy import/export (kWh)
- Curtailment (with/without battery)
- Energy cost
- Power tariff cost
- Total monthly cost
- Monthly savings

**Generated by**: `plotly_yearly_report_v6_optimized.py` during report creation

---

### 5. Static Visualization Reports (Matplotlib)

**Location**: `scripts/visualization/`

**Description**: Traditional matplotlib-based static visualizations for publication/documentation.

**Available Plots**:

1. **Battery SOC** (`battery_soc.png`)
   - State of charge over time
   - Min/max SOC limits
   - Charging/discharging patterns

2. **Power Flows** (`power_flows.png`)
   - Grid import/export
   - Battery charge/discharge
   - PV production
   - Consumption

3. **Cost Comparison** (`plot_costs_3weeks.py`)
   - 3-week detailed cost breakdown
   - Reference vs battery costs
   - Component-level analysis

4. **Battery Operation** (`plot_battery_simulation.py`)
   - Detailed battery behavior
   - SOC, power, efficiency
   - Grid interaction

5. **Input Data Visualization** (`plot_input_data.py`)
   - Spot prices
   - PV production
   - Load consumption
   - Duration curves

**Usage**:
```bash
# Individual plots
python scripts/visualization/plot_battery_simulation.py
python scripts/visualization/plot_input_data.py
python scripts/visualization/plot_costs_3weeks.py

# Comprehensive visualization suite
python scripts/visualization/visualize_results.py
```

---

### 6. Sensitivity Analysis Reports

**Description**: Analyze how battery performance varies with key parameters.

**Parameters Analyzed**:
- Battery cost (NOK/kWh)
- Discount rate (%)
- Degradation rate (%/year)
- Spot price volatility
- Grid tariff rates

**Outputs**:
- NPV sensitivity curves
- Break-even surfaces
- Tornado diagrams
- Parameter importance ranking

**Location**: Built into `optimize_battery_dimensions.py` via sensitivity sweeps

---

### 7. Strategy Diagnostics Reports (Planned)

**Status**: 🔄 In Development

**Planned Features**:
- Battery operation strategy analysis
- Peak shaving effectiveness
- Arbitrage opportunity utilization
- Curtailment reduction metrics
- Charge/discharge cycle analysis

---

### 8. Comparison Reports (Planned)

**Status**: ⏳ Planned

**Planned Features**:
- Multi-scenario comparison
- Battery size comparison (e.g., 50kWh vs 100kWh)
- Strategy comparison (peak shaving vs arbitrage)
- Economic metric comparison tables

---

## 📁 Report Output Structure

```
results/
├── simulations/                    # Raw simulation data
│   └── YYYY-MM-DD_HHMMSS_scenario/
│       ├── trajectory.csv          # Hourly timeseries
│       ├── summary.json            # Economic summary
│       └── full_result.pkl         # Complete result object
│
├── figures/                        # Static visualizations
│   ├── breakeven/                  # Break-even plots
│   ├── battery_operation/          # SOC, power plots
│   ├── cost_analysis/              # Cost breakdown
│   └── sensitivity/                # Sensitivity analysis
│
├── reports/                        # Markdown/HTML reports
│   ├── YYYY-MM-DD_HHMMSS_breakeven_analysis.md
│   └── YYYY-MM-DD_HHMMSS_index.md
│
└── yearly_2024/                    # Year-specific results
    ├── plotly_optimized_v6.html    # Interactive HTML report
    ├── trajectory.csv              # Full year timeseries
    ├── monthly_summary.csv         # Monthly aggregates
    └── economic_metrics.csv        # Summary metrics
```

---

## 🚀 Quick Start Guide

### Generate Complete Yearly Analysis

```bash
# 1. Run yearly optimization (rolling horizon)
python main.py yearly --battery-kwh 80 --battery-kw 60 --output-dir results/yearly_2024

# 2. Generate interactive HTML report
python scripts/visualization/plotly_yearly_report_v6_optimized.py results/yearly_2024/

# 3. Open report in browser
open results/yearly_2024/plotly_optimized_v6.html
```

### Optimize Battery Dimensions

```bash
# Run sizing optimization (finds optimal kWh and kW)
python scripts/analysis/optimize_battery_dimensions.py

# Outputs: NPV heatmaps, break-even costs, optimal dimensions
# Check results/battery_sizing_optimization.png
```

### Generate Break-Even Analysis

```python
from pathlib import Path
from core.reporting import SimulationResult
from reports import BreakevenReport

# Load results
reference = SimulationResult.load(Path('results/simulations/reference'))
battery = SimulationResult.load(Path('results/simulations/battery_80kwh'))

# Generate report
report = BreakevenReport(
    reference=reference,
    battery_scenario=battery,
    output_dir=Path('results'),
    battery_lifetime_years=15,
    discount_rate=0.05
)

report_path = report.generate()
print(f"Report: {report_path}")
```

---

## 📈 Report Types by Use Case

### Investment Decision Making
- ✅ Battery Dimensioning Report (optimal size)
- ✅ Break-Even Analysis Report (max viable cost)
- ✅ Interactive Yearly Report (operational preview)

### Operational Planning
- ✅ Interactive Yearly Report (full year simulation)
- ✅ Monthly Summary Report (seasonal patterns)
- ✅ Strategy Diagnostics (coming soon)

### Technical Documentation
- ✅ Static Matplotlib Plots (publication quality)
- ✅ Battery Operation Plots (technical details)
- ✅ Sensitivity Analysis (parameter impacts)

### Executive Summary
- ✅ Interactive HTML Report (high-level overview)
- ✅ Economic Metrics Table (key numbers)
- ⏳ Executive Summary Report (planned)

---

## 🔧 Customization Options

### Theme Customization

Reports use Norsk Solkraft branded theme by default. To customize:

```python
from src.visualization.norsk_solkraft_theme import apply_light_theme

fig = go.Figure()
apply_light_theme(fig)
fig.update_layout(
    title="Custom Report",
    font=dict(family="Arial", size=12)
)
```

### Export Formats

Interactive Plotly reports support multiple export formats:
- HTML (default, ~5 MB)
- PNG (static image via browser export)
- PDF (via print-to-PDF in browser)
- JSON (data export for further analysis)

Static matplotlib plots can be exported as:
- PNG (default, 150 DPI)
- SVG (vector format for publications)
- PDF (publication quality)

---

## 🐛 Troubleshooting

### Report Generation Fails

**Problem**: `FileNotFoundError: trajectory.csv not found`
**Solution**: Ensure simulation has completed successfully before generating reports.

**Problem**: `ModuleNotFoundError: No module named 'plotly'`
**Solution**: Install dependencies: `pip install plotly kaleido`

### Large HTML Files

**Problem**: Interactive reports are 5-7 MB
**Solution**: This is normal for Plotly with full year data. For smaller files, use monthly detail reports or static plots.

### Missing Data

**Problem**: Some plots show NaN values
**Solution**: Check that input data files exist:
- `data/spot_prices/NO2_2024_60min_real.csv`
- `data/pv_profiles/pvgis_58.97_5.73_138.55kWp.csv`
- `data/consumption/commercial_2024.csv`

---

## 📚 Related Documentation

- **Architecture**: `README.md` - Project overview
- **Configuration**: `configs/examples/` - YAML configuration examples
- **Migration Guide**: `docs/weekly_optimization_migration.md` - Performance improvements
- **Report Framework**: `core/reporting/report_generator.py` - Base classes

---

## 🎯 Recommended Workflow

1. **Initial Analysis**: Run `optimize_battery_dimensions.py` to find optimal battery size
2. **Detailed Simulation**: Run `main.py yearly` with optimal dimensions
3. **Interactive Report**: Generate `plotly_optimized_v6.html` for stakeholder review
4. **Economic Analysis**: Generate break-even report for investment decision
5. **Documentation**: Export static plots for technical documentation

This workflow provides comprehensive coverage from initial sizing to final investment decision documentation.
