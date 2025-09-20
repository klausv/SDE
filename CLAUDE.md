# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Battery optimization system for a 150 kWp solar installation in Stavanger, Norway. Analyzes economic viability of battery storage through peak shaving, energy arbitrage, and power tariff reduction strategies.

## Development Environment Setup

### Initial Setup
```bash
# Create and activate conda environment
conda env create -f battery_optimization/environment.yml
conda activate battery_opt

# Configure ENTSO-E API (required for real data)
python battery_optimization/scripts/get_entsoe_token.py
# Or manually create .env file with: ENTSOE_API_KEY=your_key
```

### Common Commands
```bash
# Main analysis execution
cd battery_optimization
python main.py

# Run specific test scripts
python test_analysis.py        # Test basic analysis functions
python test_realistic.py        # Test with realistic parameters
python run_test_simple.py       # Simplified test run

# PVGIS data analysis scripts
python get_pvgis_data.py        # Fetch solar production data
python optimize_with_pvgis.py   # Run optimization with PVGIS data
```

## Architecture & Key Components

### Core System Flow
1. **Data Fetching** → `src/data_fetchers/` fetches electricity prices (ENTSO-E) and solar production (PVGIS/PVLib)
2. **Optimization** → `src/optimization/optimizer.py` runs differential evolution to find optimal battery size
3. **Economic Analysis** → `src/optimization/economic_model.py` calculates NPV, IRR, and payback periods
4. **Sensitivity Analysis** → `src/analysis/sensitivity.py` explores parameter variations
5. **Visualization** → `src/analysis/visualization.py` generates heatmaps and reports

### Key Configuration Points

**System Parameters** (`src/config.py`):
- PV: 150 kWp, south-facing, 25° tilt
- Inverter: 110 kW (oversizing ratio 1.36)
- Grid limit: 77 kW (70% of inverter)
- Location: Stavanger (58.97°N, 5.73°E)

**Economic Assumptions**:
- Discount rate: 5%
- Battery lifetime: 15 years
- EUR/NOK: 11.5
- Battery efficiency: 90%

**Tariff Structure** (Lnett commercial):
- Peak hours: Mon-Fri 06:00-22:00 (0.296 kr/kWh)
- Off-peak: Nights/weekends (0.176 kr/kWh)
- Power tariff: Progressive brackets based on monthly peak

### Critical Analysis Scripts

The repository contains multiple analysis variants for validation:
- `analyser_med_pvsol_tall.py` - Analysis using PVsol production data
- `endelig_analyse_pvsol.py` - Final PVsol-based analysis
- `inntekt_final_analyse.py` - Detailed revenue analysis
- `varighetskurve_*.py` - Duration curve analysis variants

## Key Technical Details

### Battery Optimization Strategy
The optimizer evaluates three modes:
1. **Peak Shaving**: Prevents curtailment when production > 77 kW grid limit
2. **Energy Arbitrage**: Buy low (nights) and sell high (peak hours)
3. **Power Tariff Reduction**: Minimize monthly peak demand charges

### Solver Configuration
Uses multiple free solvers (configured in `environment.yml`):
- HiGHS (via scipy ≥1.9)
- CBC (via PuLP)
- Google OR-Tools

### Data Caching
- ENTSO-E price data cached in `data/` directory
- PVGIS solar data cached after first fetch
- Use `use_cache=True` in main.py to avoid API calls

## Important Considerations

### Analysis Context
This is an investment analysis tool for evaluating battery economics at the specific Stavanger location. Current analysis shows:
- Optimal battery: ~80-100 kWh @ 40-60 kW
- Break-even cost: ~3500-4000 NOK/kWh
- Market batteries (5000 NOK/kWh) require cost reduction to 2500 NOK/kWh for viability

### API Requirements
- ENTSO-E API key required for real electricity prices (free registration)
- PVGIS API used for solar data (no key required)
- Fallback to simulated data if APIs unavailable

### Performance Notes
- Full year optimization takes ~1-2 minutes
- Sensitivity analysis can take 10-15 minutes
- Use cached data to speed up development iterations