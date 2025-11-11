# Battery Operation Report - Documentation

## Overview

The `BatteryOperationReport` class provides a unified, interactive Plotly-based visualization system for battery operation data. It consolidates three existing matplotlib scripts into a comprehensive, theme-native dashboard with configurable time periods.

**Consolidates:**
- `plot_battery_simulation.py` (3 weeks, June focus, 2-row layout)
- `visualize_results.py` (3 weeks, configurable start, 4×2 layout)
- `visualize_battery_management.py` (monthly detail, comprehensive metrics)

**Key Features:**
- Configurable time periods (3 weeks, 1 month, 3 months, custom range)
- Automatic battery dimension detection from metadata
- Norsk Solkraft themed visualizations (light theme by default)
- Interactive features: zoom, pan, unified hover tooltips
- Multiple export formats: HTML (primary), PNG via kaleido (optional)
- Comprehensive operational metrics and summary tables

---

## Architecture

### Layout Structure

**2 columns × 6 rows = 12 subplots**

| Row | Column 1 | Column 2 |
|-----|----------|----------|
| 1 | Battery State of Charge | Curtailed Power |
| 2 | Battery Power Flow | C-Rate Indicator |
| 3 | Grid Power Flow | Tariff Zones |
| 4 | Spot Price & Solar (dual-axis) | Solar Production |
| 5 | Cost Components (stacked) | Cumulative Cost |
| 6 | Daily Metrics Table | Weekly Aggregates Table |

### Data Flow

```
SimulationResult (trajectory data)
    ↓
BatteryOperationReport.__init__()
    ↓ (filter to period)
DataFrame (self.df) with calculated columns
    ↓
_create_figure() → 12 subplots
    ↓
generate() → HTML report
```

---

## Installation & Setup

### Prerequisites

```bash
# Core dependencies (already in environment.yml)
pip install plotly pandas numpy

# Optional: for PNG export
pip install kaleido
```

### Theme Integration

The report uses the Norsk Solkraft light theme by default:

```python
from src.visualization.norsk_solkraft_theme import apply_light_theme

# Theme applied automatically during report generation
# Manual application (if needed):
apply_light_theme()
```

**Theme Colors:**
- Primary data: `#F5A621` (Solenergi Oransje)
- Comparison: `#00609F` (Profesjonell Blå)
- Success/Positive: `#A8D8A8` (Mose-grønn)
- Warning/Critical: `#B71C1C` (Mørk Rød)
- Spot price: `#4CAF50` (Green, thick 2.5px line)

---

## Usage Examples

### 1. Basic Usage (3-week report)

```python
from pathlib import Path
from core.reporting import SimulationResult, BatteryOperationReport

# Load simulation results
result = SimulationResult.load(Path('results/yearly_2024'))

# Generate 3-week report (default: June 1-21)
report = BatteryOperationReport(
    result=result,
    output_dir=Path('results'),
    period='3weeks'
)

html_path = report.generate()
print(f"Report: {html_path}")
```

### 2. Custom Time Period

```python
# Generate report for specific date range
report = BatteryOperationReport(
    result=result,
    output_dir=Path('results'),
    period='custom',
    start_date='2024-03-01',
    end_date='2024-05-31'
)

html_path = report.generate()
```

### 3. Export to PNG

```python
# Export both HTML and PNG (requires kaleido)
report = BatteryOperationReport(
    result=result,
    output_dir=Path('results'),
    period='1month',
    export_png=True
)

html_path = report.generate()
# Creates: results/reports/battery_operation_1month.html
# Creates: results/figures/battery_operation/1month.png
```

### 4. Manual Battery Dimensions

```python
# Override battery dimensions (ignore metadata)
report = BatteryOperationReport(
    result=result,
    output_dir=Path('results'),
    period='3weeks',
    battery_kwh=100,  # Override capacity
    battery_kw=50     # Override power rating
)
```

### 5. Get Summary Metrics

```python
report = BatteryOperationReport(
    result=result,
    output_dir=Path('results'),
    period='1month'
)

# Generate report
html_path = report.generate()

# Get summary metrics
metrics = report.get_summary_metrics()

print(f"Equivalent cycles: {metrics['equivalent_cycles']:.2f}")
print(f"Utilization: {metrics['utilization_pct']:.1f}%")
print(f"Roundtrip efficiency: {metrics['roundtrip_efficiency_pct']:.1f}%")
```

---

## Command-Line Interface

Use the provided example script for quick report generation:

```bash
# Generate 3-week report (default)
python scripts/examples/generate_battery_operation_report.py

# Generate 1-month report
python scripts/examples/generate_battery_operation_report.py --period 1month

# Generate 3-month report starting January
python scripts/examples/generate_battery_operation_report.py \
    --period 3months \
    --start 2024-01-01

# Generate custom period with PNG export
python scripts/examples/generate_battery_operation_report.py \
    --period custom \
    --start 2024-06-01 \
    --end 2024-08-31 \
    --export-png

# Use different results directory
python scripts/examples/generate_battery_operation_report.py \
    --results-dir results/my_simulation \
    --period 1month
```

---

## Configuration Options

### Period Configurations

| Period | Duration | Default Start | Use Case |
|--------|----------|---------------|----------|
| `3weeks` | 21 days | 2024-06-01 | Summer analysis, detailed operations |
| `1month` | 30 days | 2024-06-01 | Monthly performance review |
| `3months` | 90 days | 2024-01-01 | Seasonal analysis |
| `custom` | User-defined | Required | Specific date ranges |

### Battery Configuration

**Auto-detection** (reads from `metadata.csv`):
```python
# Looks for columns:
# - battery_capacity_kwh
# - battery_power_kw
```

**Manual override**:
```python
report = BatteryOperationReport(
    result=result,
    output_dir=Path('results'),
    period='3weeks',
    battery_kwh=80,   # kWh capacity
    battery_kw=40     # kW power rating
)
```

---

## Data Requirements

### SimulationResult Format

The report expects a `SimulationResult` instance with the following attributes:

**Required timeseries data** (must match `timestamp` length):
- `production_ac_kw`: AC solar production [kW]
- `consumption_kw`: Load consumption [kW]
- `grid_power_kw`: Net grid power (+ import, - export) [kW]
- `battery_power_ac_kw`: Battery AC power (+ charge, - discharge) [kW]
- `battery_soc_kwh`: Battery state of charge [kWh]
- `curtailment_kw`: Curtailed solar production [kW]
- `spot_price`: Electricity spot price [NOK/kWh]

**Required metadata**:
- `battery_config`: Dict with `capacity_kwh`, `power_kw`, `min_soc_pct`, `max_soc_pct`
- `strategy_config`: Dict with strategy details
- `simulation_metadata`: Dict with `grid_limit_kw`

### Alternative: Load from Trajectory CSV

If you have raw `trajectory.csv` data:

```python
import pandas as pd
import numpy as np
from core.reporting import SimulationResult

# Load trajectory
df = pd.read_csv('results/yearly_2024/trajectory.csv', parse_dates=['timestamp'])
df.set_index('timestamp', inplace=True)

# Load metadata
metadata = pd.read_csv('results/yearly_2024/metadata.csv')
battery_kwh = float(metadata['battery_capacity_kwh'].iloc[0])
battery_kw = float(metadata['battery_power_kw'].iloc[0])

# Create SimulationResult
result = SimulationResult(
    scenario_name='battery_operation',
    timestamp=df.index,
    production_dc_kw=df['P_pv_kw'].values * 1.05,  # Estimate DC
    production_ac_kw=df['P_pv_kw'].values,
    consumption_kw=df['P_load_kw'].values,
    grid_power_kw=df['P_grid_import_kw'].values - df['P_grid_export_kw'].values,
    battery_power_ac_kw=df['P_charge_kw'].values - df['P_discharge_kw'].values,
    battery_soc_kwh=df['E_battery_kwh'].values,
    curtailment_kw=df['P_curtail_kw'].values,
    spot_price=df['spot_price_nok'].values,
    cost_summary={'total_cost_nok': 0},
    battery_config={'capacity_kwh': battery_kwh, 'power_kw': battery_kw},
    strategy_config={'type': 'RollingHorizon'},
    simulation_metadata={'grid_limit_kw': 77}
)

# Generate report
report = BatteryOperationReport(result=result, output_dir=Path('results'))
html_path = report.generate()
```

---

## Visualization Details

### Row 1: Battery SOC + Curtailment

**Left (SOC):**
- Area fill: Green with transparency
- Line: `#4CAF50`, 2px
- Horizontal lines: Min SOC (20%, red dashed), Max SOC (80%, teal dashed)
- Y-axis: 0-100%

**Right (Curtailment):**
- Area fill: Red with transparency
- Line: `#C62828`, 1.5px
- Shows power lost due to grid limits

### Row 2: Battery Power + C-Rate

**Left (Battery Power):**
- Bar chart: Green (charge), Red (discharge)
- Horizontal lines: Power limits (±battery_kw)
- Y-axis: -battery_kw to +battery_kw

**Right (C-Rate):**
- Line chart: Power/Capacity ratio
- Horizontal line: 1C reference (yellow dashed)
- Indicates stress on battery

### Row 3: Grid Flow + Tariff Zones

**Left (Grid Power):**
- Consolidated net flow (positive=import, negative=export)
- Import: Amber fill (#FF8F00)
- Export: Teal fill (#00897B)
- Horizontal line: Grid limit (77 kW, gray dashed)

**Right (Tariff Zones):**
- Stacked bars showing peak/off-peak hours
- Peak: Red (Mon-Fri 06:00-22:00)
- Off-peak: Green (nights/weekends)

### Row 4: Spot Price + Solar

**Left (Spot Price):**
- Dual y-axis configuration
- Primary: Spot price (thick green line, 2.5px)
- Secondary: (reserved for solar overlay if needed)

**Right (Solar Production):**
- Area fill: Yellow with transparency (#FCC808)
- Shows PV power generation profile

### Row 5: Cost Components + Cumulative

**Left (Cost Components):**
- Stacked area: Energy cost, power tariff, degradation
- Colors: Amber, teal, gray
- Shows cost breakdown per timestep

**Right (Cumulative Cost):**
- Line chart: Running total cost
- Color: `#1B263B` (Indigo), 2.5px
- Shows cost accumulation over period

### Row 6: Metrics Tables

**Left (Daily Metrics):**
- Date, Production, Consumption, Grid Import
- Limited to 10 most recent days for readability

**Right (Weekly Aggregates):**
- Week, Production, Cycles, Curtailment
- Shows weekly operational summary

---

## Interactive Features

### Zoom & Pan
- **Box select**: Click and drag to zoom to region
- **Double-click**: Reset to original view
- **Scroll wheel**: Zoom in/out at cursor position
- **Drag**: Pan horizontally/vertically

### Unified Hover
- **Crosshair mode**: Shows all subplot values at selected time
- **Tooltip**: Formatted values with units
- **Format**: `%{y:.1f} kW`, `%{y:.2f} NOK/kWh`, etc.

### Legend Controls
- **Click**: Toggle series visibility
- **Double-click**: Isolate single series
- **Hover**: Highlight corresponding traces

### Export Controls (built-in)
- **Camera icon**: Download PNG snapshot
- **Zoom controls**: Reset axes, pan, zoom box
- **Compare**: Spike lines on hover

---

## Output Structure

### Directory Layout

```
results/
├── reports/
│   ├── battery_operation_3weeks.html      # Interactive HTML report
│   ├── battery_operation_1month.html
│   └── battery_operation_custom.html
├── figures/
│   └── battery_operation/
│       ├── 3weeks.png                     # Optional PNG exports
│       ├── 1month.png
│       └── custom.png
└── simulations/
    └── 2024-11-10_scenario_name/
        ├── trajectory.csv                  # Source data
        ├── metadata.csv                    # Battery config
        └── full_result.pkl                 # Complete result
```

### File Naming Convention

- **HTML**: `battery_operation_{period}.html`
- **PNG**: `{period}.png` (in `figures/battery_operation/`)

**Period values:**
- `3weeks`, `1month`, `3months`, `custom`

---

## Performance Considerations

### Data Volume

| Period | Timesteps (hourly) | Timesteps (15-min) | HTML Size | Load Time |
|--------|-------------------:|-------------------:|----------:|----------:|
| 3 weeks | 504 | 2,016 | ~1.5 MB | < 1s |
| 1 month | 720 | 2,880 | ~2 MB | < 2s |
| 3 months | 2,160 | 8,640 | ~5 MB | < 3s |
| 1 year | 8,760 | 35,040 | ~15 MB | ~5s |

**Recommendations:**
- Use 3-week or 1-month periods for detailed analysis
- Use 3-month periods for seasonal trends
- Avoid full-year periods in 15-minute resolution (use aggregation)

### Optimization Techniques

**Built-in optimizations:**
1. **Data filtering**: Only loads requested period (not full year)
2. **Calculated columns**: Pre-computed during initialization
3. **Efficient traces**: Uses native Plotly trace types (no custom loops)
4. **Cached theme**: Theme registered once, reused

**User optimizations:**
```python
# Downsample for faster rendering (hourly → 3-hourly)
df_resampled = df.resample('3h').mean()

# Or aggregate to daily for long periods
df_daily = df.resample('D').agg({
    'battery_soc_kwh': 'mean',
    'grid_power_kw': 'sum',
    'spot_price': 'mean'
})
```

---

## Troubleshooting

### Common Issues

#### 1. "No data found in period"

**Cause**: Requested date range outside available data

**Solution**:
```python
# Check available data range
print(f"Data range: {result.timestamp[0]} to {result.timestamp[-1]}")

# Adjust period to available data
report = BatteryOperationReport(
    result=result,
    output_dir=Path('results'),
    period='custom',
    start_date='2024-01-01',  # Within data range
    end_date='2024-03-31'
)
```

#### 2. "Array length mismatch"

**Cause**: Inconsistent array lengths in SimulationResult

**Solution**:
```python
# Validate all arrays match timestamp length
print(f"Timestamps: {len(result.timestamp)}")
print(f"SOC: {len(result.battery_soc_kwh)}")
print(f"Grid: {len(result.grid_power_kw)}")

# Trim to shortest
min_len = min(len(result.timestamp), len(result.battery_soc_kwh), ...)
result.timestamp = result.timestamp[:min_len]
result.battery_soc_kwh = result.battery_soc_kwh[:min_len]
# ... repeat for all arrays
```

#### 3. PNG export fails

**Cause**: Kaleido not installed

**Solution**:
```bash
pip install kaleido

# Or install specific version if issues persist
pip install kaleido==0.2.1
```

#### 4. Theme not applied

**Cause**: Theme import issue or manual override

**Solution**:
```python
# Ensure theme module is accessible
from src.visualization.norsk_solkraft_theme import apply_light_theme

# Apply globally before report generation
apply_light_theme()

# Then create report
report = BatteryOperationReport(...)
```

#### 5. Memory error with large datasets

**Cause**: Too many timesteps (e.g., 15-min resolution for full year)

**Solution**:
```python
# Downsample before creating SimulationResult
df_hourly = df.resample('h').mean()

# Or use shorter period
report = BatteryOperationReport(
    result=result,
    period='1month',  # Instead of full year
    start_date='2024-06-01'
)
```

---

## API Reference

### Class: `BatteryOperationReport`

```python
class BatteryOperationReport(SingleScenarioReport):
    """Unified battery operation visualization with configurable periods."""

    def __init__(
        self,
        result: SimulationResult,
        output_dir: Path,
        period: str = '3weeks',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        export_png: bool = False,
        battery_kwh: Optional[float] = None,
        battery_kw: Optional[float] = None
    ):
        """
        Initialize report generator.

        Args:
            result: SimulationResult with trajectory data
            output_dir: Base output directory
            period: '3weeks', '1month', '3months', 'custom'
            start_date: Start date for custom period (YYYY-MM-DD)
            end_date: End date for custom period (YYYY-MM-DD)
            export_png: Export PNG in addition to HTML
            battery_kwh: Battery capacity override
            battery_kw: Battery power override

        Raises:
            ValueError: Invalid period or missing custom dates
        """
```

### Method: `generate()`

```python
def generate(self) -> Path:
    """
    Generate battery operation report.

    Returns:
        Path to main HTML report file

    Side effects:
        - Creates HTML file in output_dir/reports/
        - Creates PNG file in output_dir/figures/ (if export_png=True)
        - Tracks figure in self.figures list
    """
```

### Method: `get_summary_metrics()`

```python
def get_summary_metrics(self) -> Dict[str, Any]:
    """
    Calculate summary metrics for reporting period.

    Returns:
        Dictionary with keys:
        - period: Date range string
        - timesteps: Number of timesteps
        - duration_hours: Total hours in period
        - production_kwh: Total solar production
        - consumption_kwh: Total load consumption
        - grid_import_kwh: Total grid import
        - grid_export_kwh: Total grid export
        - curtailment_kwh: Total curtailed power
        - battery_charge_kwh: Total battery charging
        - battery_discharge_kwh: Total battery discharging
        - equivalent_cycles: Number of full cycles
        - roundtrip_efficiency_pct: Battery efficiency
        - charge_hours: Hours spent charging
        - discharge_hours: Hours spent discharging
        - idle_hours: Hours idle
        - utilization_pct: Percentage of time active
        - soc_min_pct: Minimum SOC
        - soc_max_pct: Maximum SOC
        - soc_mean_pct: Average SOC
        - soc_start_pct: Starting SOC
        - soc_end_pct: Ending SOC
        - peak_grid_import_kw: Peak import power
        - peak_grid_export_kw: Peak export power
        - peak_production_kw: Peak solar production
    """
```

---

## Testing

### Run Unit Tests

```bash
# Run all tests
python tests/test_battery_operation_report.py

# Run specific test
python -m unittest tests.test_battery_operation_report.TestBatteryOperationReport.test_html_generation

# Run with verbose output
python tests/test_battery_operation_report.py -v
```

### Test Coverage

Tests validate:
- ✓ Period configurations (3weeks, 1month, 3months, custom)
- ✓ Data filtering and time range selection
- ✓ Battery dimension auto-detection and override
- ✓ Calculated column generation (SOC%, hour, weekday, is_peak)
- ✓ Summary metrics calculation
- ✓ HTML report generation and file structure
- ✓ Figure tracking in report generator
- ✓ Edge cases (empty periods, invalid dates)
- ✓ SOC limit validation
- ✓ Integration with trajectory CSV format

---

## Comparison with Legacy Scripts

### Feature Comparison

| Feature | plot_battery_simulation.py | visualize_results.py | visualize_battery_management.py | BatteryOperationReport |
|---------|---------------------------|---------------------|----------------------------------|------------------------|
| **Technology** | Matplotlib | Matplotlib | Matplotlib | Plotly |
| **Interactive** | No | No | No | Yes |
| **Period config** | Fixed 3 weeks | 3 weeks (configurable) | 1 month | Flexible (3w/1m/3m/custom) |
| **Layout** | 2 rows | 4×2 grid | 4 rows | 6×2 grid (12 subplots) |
| **Theme** | Default matplotlib | Default matplotlib | Default matplotlib | Norsk Solkraft |
| **Export formats** | PNG only | PNG only | PNG only | HTML + PNG (optional) |
| **Cost breakdown** | No | No | Pie charts | Stacked area + cumulative |
| **Summary tables** | Console output | Console output | Text annotations | Interactive tables |
| **Zoom/Pan** | No | No | No | Yes |
| **Unified hover** | No | No | No | Yes |
| **Auto battery detect** | No | No | No | Yes (from metadata) |

### Migration Guide

**From `plot_battery_simulation.py`:**
```python
# Old:
plot_battery_simulation(start_date='2024-06-01', weeks=3)

# New:
from core.reporting import SimulationResult, BatteryOperationReport
result = SimulationResult.load(Path('results/yearly_2024'))
report = BatteryOperationReport(result, Path('results'), period='3weeks')
html_path = report.generate()
```

**From `visualize_results.py`:**
```python
# Old:
plot_three_weeks(start_date='2024-06-01', weeks=3)

# New:
report = BatteryOperationReport(
    result=result,
    output_dir=Path('results'),
    period='3weeks',
    start_date='2024-06-01'
)
html_path = report.generate()
```

**From `visualize_battery_management.py`:**
```python
# Old:
run_and_visualize(battery_kwh=100, battery_kw=50, year=2024)

# New:
report = BatteryOperationReport(
    result=result,
    output_dir=Path('results'),
    period='1month',
    battery_kwh=100,
    battery_kw=50
)
html_path = report.generate()
metrics = report.get_summary_metrics()
```

---

## Best Practices

### 1. Period Selection

- **3 weeks**: Detailed operational analysis, daily patterns
- **1 month**: Monthly performance review, billing cycle analysis
- **3 months**: Seasonal trends, quarterly reports
- **Custom**: Specific events, outage analysis, upgrade comparison

### 2. Data Preparation

```python
# Before creating report, validate data quality
print(f"Data range: {result.timestamp[0]} to {result.timestamp[-1]}")
print(f"Timesteps: {len(result.timestamp)}")
print(f"Missing values: {pd.DataFrame(result.to_dataframe()).isnull().sum()}")

# Fill missing values if needed
df = result.to_dataframe()
df['spot_price'] = df['spot_price'].ffill().bfill()
```

### 3. Performance Optimization

```python
# For large datasets, use shorter periods
report = BatteryOperationReport(
    result=result,
    period='1month',  # Not full year
    start_date='2024-06-01'
)

# Or downsample to hourly if using 15-min data
df_hourly = df.resample('h').mean()
```

### 4. Export Strategy

```python
# HTML for interactive exploration (default)
report = BatteryOperationReport(result, Path('results'), period='3weeks')
html_path = report.generate()

# PNG for presentations/reports (requires kaleido)
report = BatteryOperationReport(
    result, Path('results'),
    period='3weeks',
    export_png=True
)
html_path = report.generate()
```

### 5. Integration with Analysis Workflow

```python
# Step 1: Run simulation
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
optimizer = RollingHorizonOptimizer(config, battery_kwh=80, battery_kw=40)
result = optimizer.optimize_full_year(...)

# Step 2: Save results
result.save(Path('results'))

# Step 3: Generate multiple reports for different periods
for period in ['3weeks', '1month', '3months']:
    report = BatteryOperationReport(result, Path('results'), period=period)
    html_path = report.generate()
    print(f"Generated: {html_path}")

# Step 4: Extract metrics for comparison
metrics_3w = BatteryOperationReport(result, Path('results'), period='3weeks').get_summary_metrics()
metrics_1m = BatteryOperationReport(result, Path('results'), period='1month').get_summary_metrics()

print(f"3-week cycles: {metrics_3w['equivalent_cycles']:.2f}")
print(f"1-month cycles: {metrics_1m['equivalent_cycles']:.2f}")
```

---

## Future Enhancements

### Planned Features

1. **Dark theme support** (Norsk Solkraft dark)
2. **Range slider** for time navigation (Plotly native)
3. **Comparison mode** (overlay multiple scenarios)
4. **Export to PDF** (via plotly-orca or kaleido)
5. **Animated transitions** (between periods)
6. **Statistical annotations** (mean, median, std dev overlays)
7. **Custom subplot selection** (user-defined layout)
8. **Real-time updates** (for live monitoring dashboards)

### Contribution Guidelines

To contribute enhancements:

1. Create feature branch: `git checkout -b feature/enhanced-report`
2. Add tests: `tests/test_battery_operation_report.py`
3. Update documentation: `docs/battery_operation_report.md`
4. Submit PR with:
   - Clear description of enhancement
   - Before/after comparison (screenshots)
   - Performance impact analysis
   - Updated examples

---

## Support & Resources

### Documentation
- **Theme Guide**: `src/visualization/norsk_solkraft_theme.py`
- **Report Base Class**: `core/reporting/report_generator.py`
- **Result Models**: `core/reporting/result_models.py`

### Examples
- **CLI Script**: `scripts/examples/generate_battery_operation_report.py`
- **Test Suite**: `tests/test_battery_operation_report.py`
- **Legacy Scripts**: `scripts/visualization/` (for comparison)

### External Resources
- [Plotly Python Documentation](https://plotly.com/python/)
- [Plotly Subplots Guide](https://plotly.com/python/subplots/)
- [Norsk Solkraft Color Palette](docs/FARGEPALETT_NORSK_SOLKRAFT_FINAL_V4.md)

### Contact
For issues or questions:
- **GitHub Issues**: `battery_optimization` repository
- **Email**: klaus@norsksolkraft.no
- **Developer**: Klaus + Claude (AI-assisted development)

---

**Last Updated**: November 2025
**Version**: 1.0.0
**License**: MIT
