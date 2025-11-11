# Quick Start Guide - Plotly Input Validation Dashboard

**One-page reference for immediate usage**

---

## 🚀 Quick Usage

```bash
# Generate dashboard for 2024 (default)
python scripts/visualization/plot_input_data_plotly.py

# Output: results/reports/input_validation_2024.html
```

---

## 📊 What You Get

**12 Interactive Visualizations**:

| View | What It Shows | Why It Matters |
|------|---------------|----------------|
| **Price Timeseries** | Full year spot prices with mean | Identify price patterns for arbitrage |
| **Price Histogram** | Distribution + percentiles | Assess volatility and negative prices |
| **PV Timeseries** | Solar production with weekly avg | Verify seasonal patterns |
| **PV Heatmap** | Day × Hour production pattern | Identify daily curves and cloud impact |
| **Consumption Timeseries** | Load profile with baseload | Validate profile realism |
| **Duration Curve** | Load sorted high-to-low + grid limit | Battery sizing for peak shaving |
| **Net Load** | Consumption - Production | Import/export balance visualization |
| **Curtailment Scatter** | Production vs Consumption | Quantify curtailment risk (>77 kW) |
| **Monthly Balance** | Energy bars by month | Seasonal surplus/deficit |
| **Monthly Stats** | Max/avg/total table | Key metrics per month |
| **Completeness Heatmap** | Missing data by day | Data quality check |
| **Statistics Table** | Mean/median/std/min/max | Summary statistics |

---

## ✅ Quality Checks (Automatic)

Dashboard validates and reports:
- ✓ Missing data percentage (should be <5%)
- ✓ Timestamp alignment (all datasets synced)
- ✓ Negative price events (market anomalies)
- ✓ Unrealistic consumption (>1 MW spikes)
- ✓ Curtailment hours (production > 77 kW grid limit)
- ✓ Curtailment energy lost (kWh)

---

## 🎯 Key Business Insights

### 1. Curtailment Opportunity
**Where**: Row 4 Right (scatter plot)
**Look for**: Points in red zone (production > 77 kW)
**Action**: Battery sizing to capture excess solar

### 2. Arbitrage Potential
**Where**: Row 1 Right (histogram)
**Look for**: Negative prices, high volatility
**Action**: Energy trading strategy optimization

### 3. Peak Shaving Savings
**Where**: Row 3 Right (duration curve)
**Look for**: P90/P95 vs grid limit
**Action**: Battery sizing for power tariff reduction

### 4. Seasonal Patterns
**Where**: Row 2 Right (heatmap) + Row 5 Left (monthly bars)
**Look for**: Summer surplus, winter deficit
**Action**: Annual energy balance modeling

---

## 🔧 Command Options

```bash
# Custom year
python scripts/visualization/plot_input_data_plotly.py --year 2023

# Custom output directory
python scripts/visualization/plot_input_data_plotly.py --output ./analysis

# Generate and open in browser automatically
python scripts/visualization/plot_input_data_plotly.py --show

# Help
python scripts/visualization/plot_input_data_plotly.py --help
```

---

## 🐍 Python API

```python
from scripts.visualization.plot_input_data_plotly import (
    load_and_validate_input_data,
    generate_input_validation_report
)

# Load data
data = load_and_validate_input_data(year=2024)

# Check quality
quality = data['quality']
print(f"Missing prices: {quality['prices_missing_pct']:.2f}%")
print(f"Curtailment hours: {quality['curtailment_hours']}")

# Generate report
report = generate_input_validation_report(year=2024, output_dir='results')
print(f"Dashboard: {report}")
```

---

## 🚨 Troubleshooting

### Issue: "Missing data >5%"
```bash
# Re-fetch data
python scripts/data/refresh_prices.py --year 2024 --refresh
python scripts/data/refresh_pvgis.py --refresh

# Re-run dashboard
python scripts/visualization/plot_input_data_plotly.py --year 2024
```

### Issue: "High curtailment risk"
- **Not an error** - this is valuable insight
- Review Row 4 Right scatter plot
- Consider battery sizing to capture excess solar
- Or evaluate grid limit upgrade economics

### Issue: "Negative prices detected"
- **Not necessarily an error** - market can have negative prices
- Review Row 1 Right histogram
- Opportunity for battery charging strategy
- Verify with ENTSO-E source data

### Issue: "ENTSO-E API key required"
```bash
# Set up API key (one-time)
python battery_optimization/scripts/get_entsoe_token.py

# Or manually create .env file:
echo "ENTSOE_API_KEY=your_key_here" > .env
```

---

## 🎨 Interactive Features

**Zoom**: Click-drag on any plot
**Pan**: Shift + click-drag
**Hover**: Move mouse over data points
**Range Select**: Use buttons (1w/1m/3m/year)
**Reset**: Double-click on plot
**Export**: Click camera icon → Download PNG

**Synchronized Zoom**: All timeseries plots (Rows 1-4 Left) share x-axis

---

## 📏 Key Metrics Reference

| Metric | What It Means | Target |
|--------|---------------|--------|
| **Missing %** | Data completeness | <5% |
| **Curtailment Hours** | Hours production >77 kW | Minimize with battery |
| **P50 Load** | Median consumption | Baseload proxy |
| **P90 Load** | 90th percentile | Peak shaving target |
| **Negative Prices** | Market anomalies | Arbitrage opportunity |
| **Net Load** | Consumption - Production | Import/export balance |

---

## 📂 Output Location

```
results/
└── reports/
    └── input_validation_2024.html  # ~1.5 MB, interactive dashboard
```

**Share**: Upload to server or cloud (too large for email)
**View**: Any modern browser (Chrome, Firefox, Edge)

---

## ⏱️ Performance

- **Data loading**: ~2 seconds (with cache)
- **Dashboard generation**: ~1 second
- **Total runtime**: ~3.5 seconds
- **File size**: ~1.5 MB (HTML + embedded data)

---

## 🔗 Related Files

- **Main script**: `scripts/visualization/plot_input_data_plotly.py`
- **Test script**: `scripts/visualization/test_plotly_dashboard.py`
- **Full docs**: `scripts/visualization/README_plot_input_data_plotly.md`
- **Theme file**: `src/visualization/norsk_solkraft_theme.py`
- **Old matplotlib version**: `scripts/visualization/plot_input_data.py` (archived)

---

## ✨ What's New (vs matplotlib version)

| Feature | Old | New |
|---------|-----|-----|
| Plots | 2 | 12 |
| Data | 3 weeks | Full year |
| Interactive | ❌ | ✅ |
| Quality checks | Console | Visual |
| Curtailment analysis | ❌ | ✅ |
| Duration curves | ❌ | ✅ |
| Monthly stats | ❌ | ✅ |
| Heatmaps | ❌ | ✅ |
| Theme | Partial | Full |

---

## 📞 Support

- **Location**: `battery_optimization/scripts/visualization/`
- **Author**: Klaus + Claude (November 2025)
- **Status**: Production-ready ✅

---

**Ready to use! Generate your first dashboard now:**
```bash
python scripts/visualization/plot_input_data_plotly.py --show
```
