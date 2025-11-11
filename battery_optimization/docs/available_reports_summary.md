# Available Battery Optimization Reports

**Last Updated**: 2025-01-11
**System Version**: 2.0 (Factory Pattern)

---

## 📊 Report Categories

### 1. Factory-Registered Reports (NEW v2.0)

These reports use the modern factory pattern for dynamic instantiation:

#### **battery_operation** ⭐ RECOMMENDED
- **Class**: `BatteryOperationReport`
- **Type**: Interactive HTML (Plotly)
- **Time Periods**: 3weeks, 1month, 3months, custom
- **Visualizations**: 6×2 grid (12 panels)
  - Battery SOC & Curtailment
  - Power flows & C-Rate
  - Grid interaction & Tariffs
  - Spot price & Solar production
  - Cost breakdown & Cumulative costs
  - Daily/Weekly metrics tables

**Usage**:
```python
from core.reporting import ReportFactory
from pathlib import Path

report = ReportFactory.create(
    'battery_operation',
    result=simulation_result,
    output_dir=Path('results/yearly_2024_24h_15kW_30kWh'),
    period='3weeks'  # or '1month', '3months', 'custom'
)
output_path = report.generate()
```

**Output**: `battery_operation_{period}.html` (Interactive, 2-8 MB)

---

### 2. Standalone Plotly Reports (Not Yet Factory-Registered)

#### **plotly_yearly_report_v6_optimized.py**
- **Type**: Interactive HTML (Plotly)
- **Scope**: Full year comprehensive analysis
- **Visualizations**: 11 consolidated charts
  - SOC & Curtailment
  - Battery Power & Grid flows
  - Cost components & Economic savings
  - Monthly peak analysis
  - Economic metrics table (NPV, IRR, payback)

**Usage**:
```bash
python scripts/visualization/plotly_yearly_report_v6_optimized.py results/yearly_2024/
```

**Output**: `plotly_optimized_v6.html` (~5 MB)

**Note**: Refactoring 4 (migration to factory) pending

---

#### **plot_costs_3weeks_plotly.py**
- **Type**: Interactive HTML (Plotly)
- **Scope**: Detailed 3-week cost breakdown
- **Focus**: Energy vs power tariff vs degradation costs

**Usage**:
```bash
python scripts/visualization/plot_costs_3weeks_plotly.py
```

---

#### **plot_input_data_plotly.py**
- **Type**: Interactive HTML (Plotly)
- **Scope**: Input validation dashboard
- **Shows**: Prices, solar production, consumption, tariff structure

**Usage**:
```bash
python scripts/visualization/plot_input_data_plotly.py
```

---

### 3. Analysis & Comparison Scripts

#### **visualize_resolution_comparison.py**
- **Type**: Matplotlib PNG comparison
- **Scope**: PT60M vs PT15M resolution comparison
- **Metrics**: Annual cost, SOC patterns, solve time, peak tracking

**Usage**:
```bash
python scripts/visualization/visualize_resolution_comparison.py
```

---

#### **visualize_battery_management.py**
- **Type**: Matplotlib PNG
- **Scope**: Monthly detail analysis
- **Focus**: Battery operation patterns, degradation tracking

**Usage**:
```bash
python scripts/visualization/visualize_battery_management.py
```

---

### 4. Economic Analysis Reports

#### **Battery Dimensioning** (`optimize_battery_dimensions.py`)
- **Type**: Heatmaps (PNG) + JSON metrics
- **Outputs**:
  - NPV heatmap (E_nom vs P_max)
  - Break-even cost heatmap
  - 3D surfaces
  - Optimal dimensions JSON

**Usage**:
```python
from scripts.analysis.optimize_battery_dimensions import BatterySizingOptimizer

optimizer = BatterySizingOptimizer(config, year=2024, resolution='PT60M')
results = optimizer.optimize_hybrid_grid_powell(
    E_nom_range=(20, 200),  # kWh
    P_max_range=(10, 100),  # kW
    grid_resolution=8
)
```

---

### 5. Legacy Reports (Deprecated)

**Location**: `archive/legacy_reports/`

- `plotly_yearly_report_single_column.py` (archived, use v6_optimized instead)
- Various matplotlib-based reports (being phased out)

**Migration**: See `docs/reporting_migration_guide.md`

---

## 🎯 Quick Selection Guide

| Your Need | Recommended Report |
|-----------|-------------------|
| **Quick operational overview** | `battery_operation` (factory, period='3weeks') |
| **Full year economic analysis** | `plotly_yearly_report_v6_optimized.py` |
| **Cost breakdown detail** | `plot_costs_3weeks_plotly.py` |
| **Input data validation** | `plot_input_data_plotly.py` |
| **Resolution sensitivity** | `visualize_resolution_comparison.py` |
| **Battery sizing analysis** | `optimize_battery_dimensions.py` |

---

## 📖 Report Comparison Table

| Report | Type | Scope | Time | Interactive | Factory |
|--------|------|-------|------|-------------|---------|
| battery_operation | Plotly HTML | 3w-3m | Fast | ✅ | ✅ |
| v6_optimized | Plotly HTML | Year | Medium | ✅ | ⏳ Pending |
| costs_3weeks | Plotly HTML | 3 weeks | Fast | ✅ | ❌ |
| input_data | Plotly HTML | Config | Instant | ✅ | ❌ |
| resolution_comp | PNG | Year | Slow | ❌ | ❌ |
| battery_mgmt | PNG | Month | Medium | ❌ | ❌ |
| dimensions | PNG+JSON | Grid | Very Slow | ❌ | ❌ |

---

##  💡 Usage Patterns

### For Operations Team
1. **Weekly review**: `battery_operation` (period='week')
2. **Monthly summary**: `battery_operation` (period='month')
3. **Quarterly analysis**: `battery_operation` (period='3months')

### For Management/Board
1. **Annual comprehensive**: `plotly_yearly_report_v6_optimized.py`
2. **Economic metrics focus**: Filter to NPV, IRR, payback period from yearly report

### For Engineers
1. **Input validation**: `plot_input_data_plotly.py` before simulation
2. **Detailed cost breakdown**: `plot_costs_3weeks_plotly.py`
3. **Resolution testing**: `visualize_resolution_comparison.py`

### For Investment Analysis
1. **Battery sizing**: `optimize_battery_dimensions.py`
2. **Break-even analysis**: From dimensioning outputs
3. **Sensitivity testing**: Vary battery costs in dimensioning script

---

## 🔮 Future Reports (Roadmap)

- **Refactoring 4**: Migrate `v6_optimized` to factory as `yearly_comprehensive`
- **Degradation Report**: Dedicated SOH/cycle tracking visualization
- **Economic Dashboard**: Real-time NPV/savings tracker
- **Comparative Analysis**: Multi-scenario side-by-side comparison
- **Forecast Report**: Price/production forecasting visualization

---

## 📚 Documentation

- **Architecture**: `docs/REPORT_STANDARDS.md`
- **Migration Guide**: `docs/reporting_migration_guide.md`
- **Detailed Catalog**: `docs/available_reports.md`
- **Refactoring Summary**: `docs/refactoring_summary_2025_01_11.md`

---

## ⚙️ Technical Details

### Data Requirements

All reports expect a results directory containing:
- `trajectory.csv` - Timestep-by-timestep operational data
- `metadata.csv` - Battery configuration and simulation parameters
- `summary.json` - Economic aggregates (optional)

### Performance Notes

- **Plotly HTML reports**: 2-10 MB file size, instant browser loading
- **Matplotlib PNG reports**: Higher resolution, slower generation
- **Factory pattern**: Enables CLI integration and automated report generation

---

**For questions or report requests, see:** `docs/REPORT_STANDARDS.md` section 1.2
