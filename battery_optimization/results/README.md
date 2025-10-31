# Results Directory Structure

This directory contains organized outputs from battery optimization analyses.

## Directory Organization

```
results/
├── simulations/          # Simulation result data files
│   └── YYYY-MM-DD_HHMMSS_scenario_name/
│       ├── timeseries.csv      # Hourly timeseries data
│       ├── summary.json        # Economic summary and config
│       └── full_result.pkl     # Complete SimulationResult object
│
├── figures/             # Generated visualizations
│   ├── breakeven/       # Break-even analysis plots
│   ├── battery_operation/  # Battery SOC, power, curtailment plots
│   ├── cost_analysis/   # Cost breakdown and comparison plots
│   └── sensitivity/     # Sensitivity analysis plots
│
└── reports/             # Final analysis reports
    ├── YYYY-MM-DD_HHMMSS_breakeven_analysis.md
    ├── YYYY-MM-DD_HHMMSS_strategy_diagnostics.md
    └── YYYY-MM-DD_HHMMSS_index.md

```

## Using the New Report System

### Generate Reports Programmatically

```python
from pathlib import Path
from core.reporting import SimulationResult
from reports import BreakevenReport

# Load simulation results
reference = SimulationResult.load(Path('results/simulations/2024-10-30_reference'))
battery = SimulationResult.load(Path('results/simulations/2024-10-30_battery'))

# Generate break-even analysis
report = BreakevenReport(
    reference=reference,
    battery_scenario=battery,
    output_dir=Path('results'),
    battery_lifetime_years=10,
    discount_rate=0.05
)

report_path = report.generate()
print(f"Report generated: {report_path}")
```

### Factory Pattern Usage

```python
from reports import generate_report, list_available_reports

# List available report types
print(list_available_reports())

# Generate report using factory
report_path = generate_report(
    'breakeven',
    reference=reference,
    battery_scenario=battery,
    output_dir=Path('results')
)
```

## Legacy Files

Files in the root of `results/` are from older analysis scripts and will be gradually migrated to the new structure or moved to an archive directory. Current root-level files include:

- `*.md` - Analysis summary reports
- `*.png` - Visualization files
- `*.pkl` - Pickled simulation results
- `*.json` - JSON result summaries

**Note**: New analyses should use the structured subdirectories above. Legacy scripts will continue to work but are being phased out in favor of the reporting framework.

## File Naming Conventions

### Simulations
- Format: `YYYY-MM-DD_HHMMSS_scenario_name/`
- Example: `2024-10-30_143522_simplerule_20kwh/`

### Figures
- Subdirectories by analysis type (breakeven, battery_operation, etc.)
- Descriptive filenames: `npv_sensitivity.png`, `battery_soc_june.png`

### Reports
- Format: `YYYY-MM-DD_HHMMSS_report_type.md`
- Example: `2024-10-30_143522_breakeven_analysis.md`

## Migration Status

- ✅ Directory structure created
- ✅ `SimulationResult` dataclass for standardized results
- ✅ `ReportGenerator` base class for consistent reporting
- ✅ `BreakevenReport` implementation (migrated from `calculate_breakeven.py`)
- 🔄 Legacy scripts being gradually migrated
- ⏳ Strategy diagnostics report (planned)
- ⏳ Scenario comparison report (planned)
- ⏳ Executive summary report (planned)

## Questions?

See the main project CLAUDE.md for architecture details or consult the reporting framework source code in `core/reporting/` and `reports/`.
