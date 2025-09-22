# 🧹 BATTERY OPTIMIZATION CLEANUP PLAN

## IMMEDIATE ACTIONS (Safe to execute now)

### 1. DELETE EMPTY/UNUSED DIRECTORIES
```bash
rm -rf data/prices/                    # Empty directory
rm -rf data/cache/pvgis/               # Old JSON format, replaced by CSV
rm -rf data/historical_prices/         # Contains only unused 458-byte file
```

### 2. STANDARDIZE PRICE FILE NAMES
```bash
# Rename for consistency
mv data/spot_prices/spot_NO2_2023.csv data/spot_prices/NO2_2023_real.csv
```

### 3. CONSOLIDATE SIMULATION SCRIPTS
Merge these files:
- `run_report_simulation.py`
- `run_report_simulation_dc.py`

Into single file: `run_simulation.py` with parameters:
- `--dc-tracking`: Enable DC/AC separate tracking
- `--report`: Generate detailed report
- `--data-source`: synthetic|pvgis|pvsol

### 4. CREATE MAIN ENTRY POINT
Create `main.py` that provides clear interface:
```python
# main.py
"""
Battery Optimization System for 150kWp Solar Installation
Usage: python main.py [optimize|simulate|analyze] [options]
"""
```

### 5. DATA STRUCTURE REORGANIZATION
```
data/
├── spot_prices/         # All electricity prices
│   ├── NO2_2023_real.csv
│   └── NO2_2024_real.csv
└── pv_profiles/         # All PV production data
    ├── pvgis_58.97_5.73_138.55kWp.csv
    └── pvgis_58.97_5.73_150kWp.csv
```

## VERIFICATION CHECKLIST
- [ ] Backup created before cleanup
- [ ] All active scripts still function
- [ ] Tests pass after cleanup
- [ ] Git status clean
- [ ] No broken imports

## FILES TO KEEP (Critical)
- `config.py` - Centralized configuration
- `core/` - All core functionality
- `run_realistic_simulation.py` - Real data simulation
- Active data files in standardized locations

## ARCHIVE NOTE
The `archive/` folder contains 30+ experimental variants.
Consider secondary cleanup to organize by:
- archive/experiments/
- archive/validation/
- archive/legacy/