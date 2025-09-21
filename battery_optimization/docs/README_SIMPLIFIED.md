# 🔋 BATTERY OPTIMIZATION - SIMPLIFIED!

## 🎯 ONE WAY TO RUN EVERYTHING

```bash
# Just run this:
python run_analysis.py

# Or with options:
python run_analysis.py --battery-kwh 150 --battery-cost 3000 --sensitivity
```

## 📁 SIMPLE STRUCTURE

```
battery_optimization/
├── run_analysis.py      # ← START HERE!
├── config.yaml          # ← All settings
├── core/               # ← Core logic (5 files)
├── analysis/           # ← Calculations (4 files)
└── archive/            # ← Old stuff (ignore)
```

## 🚀 QUICK START

### Default analysis:
```bash
python run_analysis.py
```

### Test different battery:
```bash
python run_analysis.py --battery-kwh 50 --battery-kw 25
```

### Test different cost:
```bash
python run_analysis.py --battery-cost 3000
```

### Get help:
```bash
python run_analysis.py --help
```

## 📍 WHERE TO FIND THINGS

| What | Where | Why |
|------|-------|-----|
| **Main script** | `run_analysis.py` | Single entry point |
| **Settings** | `config.yaml` | All configuration |
| **Battery model** | `core/battery.py` | Simple & clean |
| **Economics** | `core/economics.py` | NPV, IRR, payback |
| **Value drivers** | `analysis/value_drivers.py` | All calculations |

## 📊 WHAT IT CALCULATES

1. **Avkortning** - Avoided curtailment when production > 77 kW
2. **Arbitrasje** - Buy low, sell high
3. **Effekttariff** - Peak demand reduction
4. **Selvforsyning** - Self-consumption increase
5. **NPV** - Net present value
6. **IRR** - Internal rate of return
7. **Break-even** - Maximum profitable battery cost

## ✨ IMPROVEMENTS

### Before (Messy):
- 65 Python files
- 15+ directories
- 12 different run scripts
- 3 parallel architectures
- Confusing navigation

### After (Clean):
- ~20 active files
- 5 main directories
- 1 run script
- 1 architecture
- Easy to navigate!

## 💡 SIMPLIFIED FROM 65 TO 20 FILES!

The old complex structure is archived in `archive/` folder.
You don't need it anymore!