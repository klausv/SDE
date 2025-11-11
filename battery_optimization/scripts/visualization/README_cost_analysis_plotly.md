# Interactive Cost Analysis Dashboard - Plotly

## Overview

**plot_costs_3weeks_plotly.py** - Interactive Plotly-based cost analysis dashboard for battery optimization scenarios. Provides comprehensive 6-panel visualization comparing reference (no battery) and battery scenarios over customizable time periods.

**Migration**: Replaces `plot_costs_3weeks.py` (matplotlib) with modern interactive Plotly dashboard.

---

## Features

### Interactive 6-Panel Dashboard

#### Panel 1 & 2: Cost Components Stacked Area Charts
- **Left**: Reference scenario (no battery) cost breakdown
- **Right**: Battery scenario cost breakdown
- **Components**:
  - Energy cost (orange) - Grid import/export with spot prices
  - Power tariff cost (blue) - Network capacity charges
  - Degradation cost (red) - Battery wear cost (battery only)
- **Interactive**: Hover to see exact hourly/daily costs

#### Panel 3: Cumulative Cost Comparison
- Running total comparison over the analysis period
- Reference line (dashed gray) vs Battery line (solid orange)
- Shaded green area shows cumulative savings
- **Interactive**: Range selector (1w, 2w, All)

#### Panel 4: Daily Savings Breakdown
- Bar chart showing daily savings (green = positive, red = negative)
- Quick identification of best/worst performing days
- **Interactive**: Hover for exact daily savings

#### Panel 5: Cost Metrics Summary Table
- Comprehensive cost breakdown comparison
- Rows: Energy, Power, Degradation, Total, Avg Daily
- Columns: Reference, Battery, Savings (absolute + percentage)
- Color-coded for quick assessment

#### Panel 6: Hourly Cost Heatmap
- 2D heatmap showing cost by date and hour of day
- Identifies expensive hours (red) vs cheap hours (green)
- Pattern recognition for peak demand periods
- **Interactive**: Hover for exact hourly costs

---

## Usage

### Basic Usage

```python
from pathlib import Path
from scripts.visualization.plot_costs_3weeks_plotly import generate_cost_report

# Generate report for 3-week period in June
report_path = generate_cost_report(
    trajectory_path=Path('results/yearly_2024/trajectory.csv'),
    reference_path=None,  # Optional, will be simulated if missing
    output_dir=Path('results'),
    period='3weeks_june',
    start_date='2024-06-01',
    period_days=21
)

# Opens in browser automatically
print(f"Report: {report_path}")
```

### Advanced Configuration

```python
# Custom time period (e.g., 2 weeks in winter)
report_path = generate_cost_report(
    trajectory_path=Path('results/yearly_2024/trajectory.csv'),
    reference_path=Path('results/yearly_2024/reference_trajectory.csv'),
    output_dir=Path('results'),
    period='2weeks_feb',
    start_date='2024-02-01',
    period_days=14
)

# Full year analysis (warning: large files)
report_path = generate_cost_report(
    trajectory_path=Path('results/yearly_2024/trajectory.csv'),
    output_dir=Path('results'),
    period='full_year',
    start_date='2024-01-01',
    period_days=365
)
```

### Programmatic Access to Data

```python
from scripts.visualization.plot_costs_3weeks_plotly import (
    prepare_cost_data,
    create_cost_dashboard
)
import pandas as pd

# Load data
trajectory_df = pd.read_csv('results/yearly_2024/trajectory.csv')
reference_df = pd.read_csv('results/yearly_2024/reference_trajectory.csv')
prices_df = pd.read_csv('data/spot_prices/NO2_2024_60min_real.csv')

# Prepare cost data
battery_costs, reference_costs = prepare_cost_data(
    trajectory_df, reference_df, prices_df,
    start_date='2024-06-01',
    period_days=21
)

# Access cost components
total_energy_cost = battery_costs['net_energy_cost'].sum()
total_degradation = battery_costs['degradation_cost'].sum()
daily_costs = battery_costs.groupby(
    battery_costs['timestamp'].dt.date
)['total_cost'].sum()

print(f"Total energy cost: {total_energy_cost:.2f} kr")
print(f"Total degradation: {total_degradation:.2f} kr")
```

---

## Configuration

### Tariff Rates (Lnett Commercial)

Configurable in `prepare_cost_data()` function:

```python
TARIFF_PEAK = 0.296      # kr/kWh (Mon-Fri 06:00-22:00)
TARIFF_OFFPEAK = 0.176   # kr/kWh (nights & weekends)
ENERGY_TAX = 0.1791      # kr/kWh (fixed)
FEED_IN_PREMIUM = 0.04   # kr/kWh (export bonus)
```

### Degradation Cost

Default: **0.05 kr/kWh** cycled (average of charge + discharge)

Based on:
- Battery cost: ~5000 kr/kWh
- Lifetime: 6000 cycles
- Degradation = 5000 / (2 × 6000) = 0.042 kr/kWh ≈ 0.05 kr/kWh

To customize, modify in `prepare_cost_data()`:

```python
DEGRADATION_COST_PER_KWH = 0.05  # Adjust based on battery economics
```

### Color Scheme (Norsk Solkraft Palette)

```python
COST_COLORS = {
    'energy': '#F5A621',      # Solenergi Oransje
    'power': '#00609F',       # Profesjonell Blå
    'degradation': '#B71C1C', # Mørk Rød
    'savings': '#A8D8A8',     # Mose Grønn
}
```

---

## Output Files

### HTML Report (Primary Output)

**Location**: `results/reports/cost_analysis_{period}.html`

**Features**:
- Fully interactive (zoom, pan, hover tooltips)
- Legend toggling (click to hide/show series)
- Range selector for time filtering
- Responsive layout (works on mobile/tablet)
- Shareable link (self-contained)

**Size**: ~20-50 KB (with CDN Plotly.js)

### PNG Export (Optional)

**Location**: `results/figures/cost_analysis/{period}.png`

**Features**:
- High-resolution export (1920x1400, 2x scale)
- Print-ready quality
- Suitable for reports/presentations

**Requirements**: `kaleido` package (install via conda/pip)

```bash
conda install -c conda-forge python-kaleido
```

---

## Data Requirements

### Trajectory CSV (Battery Scenario)

Required columns:
- `timestamp` - Hourly timestamps
- `P_charge_kw` - Battery charging power (kW)
- `P_discharge_kw` - Battery discharging power (kW)
- `P_grid_import_kw` - Grid import power (kW)
- `P_grid_export_kw` - Grid export power (kW)
- `E_battery_kwh` - Battery state of charge (kWh)
- `P_curtail_kw` - Curtailed power (kW)

### Reference CSV (Optional)

Same structure as trajectory CSV. If not provided, script will simulate reference scenario by zeroing battery actions:
- `P_charge_kw = 0`
- `P_discharge_kw = 0`
- `E_battery_kwh = 0`

### Prices CSV

Required columns:
- `timestamp` - Hourly timestamps (UTC with timezone)
- `price_nok` - Spot price in kr/kWh

**Note**: Script handles timezone conversion automatically.

---

## Interpretation Guide

### Cost Components

1. **Energy Cost** (Orange)
   - Import cost: `P_grid_import_kw × (spot + tariff + tax)`
   - Export revenue: `P_grid_export_kw × (spot + feed-in premium)`
   - Net energy cost = Import cost - Export revenue

2. **Power Tariff Cost** (Blue)
   - Monthly capacity charge based on peak demand
   - Progressive brackets (Lnett commercial):
     - 0-50 kW: 41.50 kr/kW/month
     - 50-100 kW: 50.00 kr/kW/month
     - 100-200 kW: 59.00 kr/kW/month
     - 200-300 kW: 84.00 kr/kW/month
     - >300 kW: 102.00 kr/kW/month

3. **Degradation Cost** (Red, Battery Only)
   - Battery wear cost from cycling
   - `(P_charge + P_discharge) / 2 × degradation_rate`
   - Represents economic value loss from battery aging

### Savings Interpretation

#### Positive Savings (Green)
- Battery scenario has **lower total cost** than reference
- Common during:
  - High peak demand periods (power tariff reduction)
  - High spot price periods (arbitrage opportunity)
  - Curtailment events (avoided production loss)

#### Negative Savings (Red)
- Battery scenario has **higher total cost** than reference
- Common during:
  - Low/stable spot prices (minimal arbitrage value)
  - Low demand periods (no peak shaving benefit)
  - High degradation relative to savings

#### Break-Even Analysis

Total savings over period should be **positive** for economic viability:
- 3-week period: Expect small savings (test period)
- Annual projection: Scale 3-week results × 17.3 (approximate)
- Compare to battery investment cost for payback calculation

---

## Performance

### Processing Time

- **3-week period**: ~2-5 seconds
- **Full year**: ~10-20 seconds
- **HTML generation**: <1 second
- **PNG export**: 2-4 seconds (if kaleido installed)

### File Sizes

- **HTML (CDN)**: 20-50 KB (lightweight, fast loading)
- **HTML (standalone)**: 3-5 MB (includes Plotly.js library)
- **PNG export**: 500-800 KB (high resolution)

---

## Comparison with Matplotlib Version

### Advantages of Plotly Version

| Feature | Matplotlib | Plotly |
|---------|-----------|--------|
| **Interactivity** | None | Full (zoom, pan, hover) |
| **Legend** | Static | Toggle series on/off |
| **Time Filtering** | Manual | Range selector |
| **Cost Breakdown** | 4 plots | 6 comprehensive panels |
| **Export** | PNG only | HTML + PNG |
| **Tooltips** | None | Detailed hover info |
| **Theme** | Basic | Norsk Solkraft branded |
| **Responsive** | Fixed | Adapts to screen size |
| **Shareable** | Image only | Interactive link |

### When to Use Matplotlib

- Print publications requiring exact control
- Legacy systems without web browser
- Simple static images for slides

### When to Use Plotly

- **Exploratory analysis** (zoom into interesting periods)
- **Presentations** (interactive demos)
- **Reports** (shareable HTML links)
- **Decision support** (stakeholders explore data)

---

## Troubleshooting

### Issue: Timezone Errors

**Error**: `TypeError: Cannot compare tz-naive and tz-aware timestamps`

**Solution**: Script handles this automatically, but ensure price data includes timezone info. Script converts all timestamps to tz-naive for comparison.

### Issue: Missing Price Data

**Error**: `FileNotFoundError: Price data not found`

**Solution**: Ensure price data exists at `data/spot_prices/NO2_2024_60min_real.csv`

### Issue: PNG Export Fails

**Error**: `kaleido not available`

**Solution**: Install kaleido for PNG export:
```bash
conda install -c conda-forge python-kaleido
```

Or skip PNG export (HTML is primary output).

### Issue: Empty/Partial Data

**Symptom**: Plots show gaps or missing data

**Solution**:
- Check trajectory CSV covers full analysis period
- Verify timestamp format: `YYYY-MM-DD HH:MM:SS`
- Ensure no missing hours (fill with zeros if needed)

---

## Future Enhancements

### Planned Features

1. **Cost per kWh Analysis** (Panel 7)
   - Effective cost per kWh over time
   - Compare to spot price baseline
   - Show arbitrage opportunities captured

2. **Weekly Aggregation View**
   - Weekly cost summaries for longer periods
   - Trend analysis over months

3. **Scenario Comparison**
   - Compare multiple battery configurations
   - Side-by-side cost breakdown

4. **Export to Excel**
   - Detailed cost tables
   - Ready for further analysis

5. **Custom Tariff Profiles**
   - User-configurable tariff structures
   - Regional variations

---

## References

### Related Scripts

- **plot_costs_3weeks.py** - Original matplotlib version (deprecated)
- **plotly_yearly_report_v6_optimized.py** - Full year comprehensive report
- **visualize_results.py** - Summary visualizations

### Documentation

- **Norsk Solkraft Theme**: `src/visualization/norsk_solkraft_theme.py`
- **Economic Model**: `src/optimization/economic_model.py`
- **Tariff Structure**: Lnett commercial rates (2024)

---

## Author & Changelog

**Author**: Klaus + Claude
**Date**: November 2025
**Version**: 1.0

### Changelog

**v1.0 (2025-11-10)**
- Initial release
- 6-panel interactive dashboard
- Norsk Solkraft theme integration
- HTML + PNG export
- Comprehensive cost breakdown
- Timezone handling
- Reference scenario simulation

---

## License

Part of Battery Optimization System - Norsk Solkraft
Internal use only
