# Migration Guide: Legacy to Unified System
**Date:** 2025-01-09
**Status:** Legacy code archived - unified system active

---

## ✅ What Changed

### Legacy System Archived

The old entry points have been archived to reduce confusion:

```
archive/legacy_entry_points/
├── main_legacy.py      # Old main.py
├── config_legacy.py    # Old config.py
└── config_legacy.yaml  # Old config.yaml
```

### New Unified System

**Single entry point:** `main.py` (was `main_new.py`)

```bash
# One command, three modes
python main.py rolling   # Real-time operation
python main.py monthly   # Monthly analysis
python main.py yearly    # Investment analysis
```

---

## 🔄 Migration Steps

### If You Used the Old `main.py`

**Old way:**
```bash
python main.py
```

**New way:**
```bash
# Choose the mode that fits your needs
python main.py rolling --battery-kwh 80 --battery-kw 60
python main.py monthly --months 1,2,3
python main.py yearly --weeks 52
```

### If You Used the Old `config.py`

**Old way:**
```python
# Edit config.py
pv_capacity_kwp = 150.0
battery_capacity_kwh = 50
```

**New way:**
```yaml
# Create configs/my_config.yaml
battery:
  capacity_kwh: 50
  power_kw: 40

# Run with config
python main.py run --config configs/my_config.yaml
```

---

## 📋 Quick Command Reference

### Rolling Horizon (Real-time)
```bash
# Old: python main.py (with edited config.py)
# New:
python main.py rolling \
    --battery-kwh 80 \
    --battery-kw 60 \
    --start-date 2024-01-01 \
    --end-date 2024-01-31
```

### Monthly Analysis
```bash
# New command
python main.py monthly \
    --months 1,2,3 \
    --resolution PT60M \
    --battery-kwh 100 \
    --battery-kw 75
```

### Yearly Investment
```bash
# New command
python main.py yearly \
    --weeks 52 \
    --resolution PT60M \
    --battery-kwh 80 \
    --battery-kw 60
```

### YAML Config (Recommended)
```bash
# Create your config
cp configs/examples/rolling_horizon_realtime.yaml configs/my_analysis.yaml

# Edit it
nano configs/my_analysis.yaml

# Run it
python main.py run --config configs/my_analysis.yaml
```

---

## 🎯 Benefits of New System

1. **No Confusion** - Single entry point, no legacy vs new
2. **Clear Modes** - Explicit choice between rolling/monthly/yearly
3. **YAML Config** - Version-controlled, shareable configurations
4. **Better Testing** - 46 tests passing, validated functionality
5. **Performance** - 3-5x faster with critical fixes applied
6. **Security** - Path traversal vulnerability fixed

---

## 🔍 Finding Old Functionality

| Old Feature | New Location |
|-------------|--------------|
| `main.py` | `archive/legacy_entry_points/main_legacy.py` |
| `config.py` | `archive/legacy_entry_points/config_legacy.py` |
| Test scripts | `scripts/testing/` |
| Analysis scripts | `scripts/analysis/` |
| Plotting scripts | `scripts/visualization/` |

---

## ⚠️ Breaking Changes

### Removed from Root
- ❌ `main_new.py` → Now `main.py`
- ❌ Old `config.py` → Archived
- ❌ Old `config.yaml` → Archived

### Still in Root
- ✅ `main.py` - Unified entry point
- ✅ `.env` - Environment variables
- ✅ `environment.yml` - Conda environment
- ✅ Documentation files

---

## 🆘 Help

### Get All Available Commands
```bash
python main.py --help
python main.py rolling --help
python main.py monthly --help
python main.py yearly --help
```

### See Example Configs
```bash
ls configs/examples/
cat configs/examples/rolling_horizon_realtime.yaml
```

### Check What's Archived
```bash
ls archive/legacy_entry_points/
```

---

## 💡 Recommended Workflow

1. **Choose your mode** (rolling/monthly/yearly)
2. **Create YAML config** from examples
3. **Run analysis** with `python main.py run --config your_config.yaml`
4. **Check results** in `results/` directory

**Example:**
```bash
# Copy example
cp configs/examples/monthly_analysis.yaml configs/q1_2024.yaml

# Edit for Q1 analysis
nano configs/q1_2024.yaml
# Change: months: [1, 2, 3]

# Run
python main.py run --config configs/q1_2024.yaml

# Check results
ls results/monthly/
```

---

## 🎉 You're Done!

The system is simpler now:
- ✅ One entry point: `main.py`
- ✅ Three clear modes: rolling, monthly, yearly
- ✅ YAML config: Shareable, version-controlled
- ✅ No legacy confusion!

For questions, see:
- `README.md` - Full documentation
- `IMPLEMENTATION_COMPLETE.md` - Technical details
- `configs/examples/` - Configuration examples
