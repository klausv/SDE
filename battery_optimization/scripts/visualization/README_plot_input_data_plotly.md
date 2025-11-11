# Interactive Input Data Validation Dashboard

**Migration Status**: ✅ Complete - Replaces matplotlib `plot_input_data.py`

## Overview

Comprehensive Plotly-based validation dashboard for battery optimization input data. Provides 12 interactive visualizations across 6 analysis areas to validate data quality before running optimizations.

## Features

### 🎨 **Theme Compliance**
- Norsk Solkraft Light theme (hvit bakgrunn)
- Brand colors: Oransje (solar), Blå (grid), Gul (highlights)
- Professional layout with consistent typography

### 📊 **12 Validation Visualizations**

**Row 1: Spot Price Analysis**
- Timeseries with tariff zone highlights
- Distribution histogram with percentiles
- Negative price detection

**Row 2: Solar Production Analysis**
- Annual production curve with weekly averages
- Day × Hour heatmap showing seasonal patterns
- Summer peak identification

**Row 3: Consumption Analysis**
- Load profile with baseload indicators
- Duration curve with grid limit markers
- Percentile analysis (P50, P90, P95)

**Row 4: Net Load Analysis**
- Net load (consumption - production) timeseries
- Curtailment risk scatter plot
- Grid limit boundary visualization

**Row 5: Monthly Aggregates**
- Energy balance (solar, consumption, net import)
- Statistics table (max, average, totals)
- Curtailment hours per month

**Row 6: Data Quality Indicators**
- Completeness heatmap by day
- Statistics summary table
- Missing data detection

### ⚡ **Interactive Features**
- **Synchronized Zoom**: All timeseries plots share x-axis zoom
- **Range Selectors**: Quick 1w/1m/3m/year views
- **Hover Cross-Hair**: Unified hover across synchronized plots
- **Export**: PNG download with configurable resolution
- **Responsive**: Adapts to browser window size

## Usage

### Basic Usage
```bash
# Generate dashboard for 2024 (default)
python scripts/visualization/plot_input_data_plotly.py

# Custom year
python scripts/visualization/plot_input_data_plotly.py --year 2023

# Custom output directory
python scripts/visualization/plot_input_data_plotly.py --output ./custom_output

# Generate and open in browser
python scripts/visualization/plot_input_data_plotly.py --show
```

### Output
```
results/
└── reports/
    └── input_validation_2024.html  # Interactive dashboard
```

### Python API Usage
```python
from scripts.visualization.plot_input_data_plotly import (
    load_and_validate_input_data,
    generate_input_validation_report
)

# Load and validate data
data = load_and_validate_input_data(year=2024)

# Access quality metrics
print(data['quality'])
# {
#   'prices_missing_pct': 0.0,
#   'production_missing_pct': 0.0,
#   'consumption_missing_pct': 0.0,
#   'curtailment_hours': 234,
#   'curtailment_energy_kwh': 1856.3,
#   ...
# }

# Generate report
report_path = generate_input_validation_report(year=2024, output_dir='results')
print(f"Report: {report_path}")
```

## Data Quality Checks

The dashboard performs comprehensive validation:

### ✅ **Completeness Checks**
- Missing data percentage per dataset
- Timestamp alignment verification
- Data point count validation

### ⚠️ **Anomaly Detection**
- Negative spot prices (unusual market conditions)
- Negative production values (sensor errors)
- Unrealistic consumption (>1 MW spikes)

### 📈 **Operational Metrics**
- Curtailment risk hours (production > 77 kW grid limit)
- Curtailment energy lost (kWh)
- Baseload analysis (minimum consumption)

### 📊 **Statistical Validation**
- Mean, median, std dev for all datasets
- Percentile analysis (P25, P50, P75, P90, P95)
- Monthly aggregates and trends

## Comparison: matplotlib vs Plotly

| Feature | matplotlib (old) | Plotly (new) |
|---------|-----------------|--------------|
| **Interactivity** | ❌ Static PNG | ✅ Zoom, pan, hover |
| **Visualizations** | 2 plots (3-week sample) | 12 plots (full year) |
| **Data Coverage** | 3 weeks | Full year (8760 hours) |
| **Range Selection** | ❌ No | ✅ 1w/1m/3m/year buttons |
| **Quality Checks** | ❌ Console only | ✅ Visual + tables |
| **Duration Curves** | ❌ No | ✅ Yes |
| **Heatmaps** | ❌ No | ✅ Production patterns |
| **Monthly Stats** | ❌ No | ✅ Tables + charts |
| **Curtailment Analysis** | ❌ No | ✅ Scatter + risk zones |
| **Completeness Check** | ❌ No | ✅ Heatmap by day |
| **Export Format** | PNG | HTML (shareable) |
| **File Size** | ~200 KB | ~1.5 MB (includes JS) |
| **Theme Compliance** | Partial | ✅ Full Norsk Solkraft |

## Dependencies

```yaml
# From environment.yml
- plotly>=5.0
- pandas>=1.3
- numpy>=1.20
```

All dependencies already present in `battery_opt` conda environment.

## Technical Details

### Dashboard Layout
```
6 rows × 2 columns = 12 subplots
Total height: 2800px (scrollable)
Row heights: [0.15, 0.15, 0.15, 0.15, 0.15, 0.25]
Spacing: 8% vertical, 10% horizontal
```

### Color Mapping
```python
# Solar/Production: Yellow theme
SOLAR_COLOR = colors['gul']  # #FCC808

# Grid/Consumption: Blue theme
GRID_COLOR = colors['blå']  # #00609F

# Price: Orange theme
PRICE_COLOR = colors['oransje']  # #F5A621

# Alerts: Red theme
ALERT_COLOR = colors['mørk_rød']  # #B71C1C

# Success: Green theme
SUCCESS_COLOR = colors['mose_grønn']  # #A8D8A8
```

### Performance
- Initial load: ~2 seconds (2024 full year = 8760 data points)
- Dashboard render: ~1 second
- File size: ~1.5 MB (HTML with embedded Plotly CDN)
- Browser memory: ~50 MB (Chrome/Firefox)

## Validation Workflow

**Before Running Optimization**:
```bash
# Step 1: Generate validation dashboard
python scripts/visualization/plot_input_data_plotly.py --year 2024

# Step 2: Review dashboard in browser
# - Check for missing data (Row 6 Left heatmap)
# - Verify curtailment risk (Row 4 Right scatter)
# - Confirm price ranges (Row 1 Right histogram)
# - Validate monthly patterns (Row 5)

# Step 3: If quality issues found, re-fetch data
python scripts/data/refresh_prices.py --year 2024
python scripts/data/refresh_pvgis.py

# Step 4: Re-run validation
python scripts/visualization/plot_input_data_plotly.py --year 2024

# Step 5: Proceed to optimization if all checks pass
python main.py
```

## Troubleshooting

### Issue: Missing Data Detected
```
⚠️ Missing data: Prices: 5.2%
```
**Solution**: Re-fetch data
```bash
python scripts/data/refresh_prices.py --year 2024 --refresh
```

### Issue: High Curtailment Risk
```
⚠️ Curtailment risk: 234 hours (1856 kWh)
```
**Analysis**: Review Row 4 Right scatter plot
- Red zone = production > 77 kW grid limit
- Consider: Battery sizing to capture excess solar
- Or: Grid limit upgrade analysis

### Issue: Negative Prices
```
⚠️ Negative prices: 12 events
```
**Analysis**: Review Row 1 Right histogram
- Not necessarily errors (market can have negative prices)
- Opportunity for battery charging strategy
- Verify with ENTSO-E data source

### Issue: Unrealistic Consumption
```
⚠️ Unrealistic consumption: 3 events (>1000 kW)
```
**Analysis**: Review Row 3 Left timeseries
- Zoom to spikes
- Check consumption profile generation
- May need to regenerate synthetic profile

## Future Enhancements

Potential additions (not yet implemented):

1. **Weather Overlay**: Add temperature/irradiance data to production heatmap
2. **Tariff Zones**: Visual shading for peak/off-peak periods on price chart
3. **Comparison Mode**: Side-by-side comparison of multiple years
4. **Export CSV**: Download filtered data ranges as CSV
5. **Dark Theme**: Add `--dark` flag for Norsk Solkraft dark theme
6. **Custom Grid Limit**: Parameterize 77 kW grid limit for different installations

## Integration

### With Main Analysis Pipeline
```python
# main.py integration example
from scripts.visualization.plot_input_data_plotly import load_and_validate_input_data

# Step 1: Validate input data
data = load_and_validate_input_data(year=2024)

# Step 2: Check quality gate
if data['quality']['prices_missing_pct'] > 5.0:
    raise ValueError("Price data quality insufficient (>5% missing)")

if not data['quality']['timestamps_aligned']:
    raise ValueError("Timestamp alignment failed")

# Step 3: Proceed with optimization
optimizer = BatteryOptimizer(
    prices=data['prices'],
    production=data['production'],
    consumption=data['consumption']
)
results = optimizer.optimize()
```

### With Sensitivity Analysis
```python
# sensitivity_analysis.py integration
from scripts.visualization.plot_input_data_plotly import generate_input_validation_report

# Generate validation report before sensitivity sweep
report = generate_input_validation_report(year=2024, output_dir='results/sensitivity')

# Run sensitivity analysis (knowing input data is validated)
for battery_cost in range(2000, 6000, 500):
    results = run_optimization(battery_cost_nok_kwh=battery_cost)
    # ...
```

## Known Limitations

1. **PVGIS Typical Year**: Always returns 2020 data (by design)
   - Not an error - this is how PVGIS provides "typical year" profiles
   - Spot prices are from requested year (e.g., 2024)
   - Years are aligned internally for compatibility

2. **Large File Size**: HTML dashboard is ~1.5 MB
   - Due to Plotly JavaScript library (CDN version used)
   - Consider hosting on server for sharing (not email-friendly)

3. **Browser Compatibility**: Requires modern browser
   - Chrome/Firefox/Edge (2020+) recommended
   - IE11 not supported

4. **Memory Usage**: Large datasets can be slow
   - 8760 hours (1 year) = fast
   - Multiple years concatenated = may be slow
   - Consider splitting into separate reports

## Contact

Questions or issues:
- Script location: `battery_optimization/scripts/visualization/plot_input_data_plotly.py`
- Theme file: `battery_optimization/src/visualization/norsk_solkraft_theme.py`
- Original matplotlib version: `scripts/visualization/plot_input_data.py` (archived)

---

**Status**: Production-ready ✅
**Last Updated**: November 2025
**Author**: Klaus + Claude
**License**: Internal use (Norsk Solkraft)
