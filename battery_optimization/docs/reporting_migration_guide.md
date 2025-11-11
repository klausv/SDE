# Report Framework Migration Guide

**Version**: v1.x → v2.0
**Date**: 2025-01-11
**Migration Type**: Non-breaking (with deprecation warnings)

---

## Overview

Version 2.0 of the battery optimization reporting framework introduces the Factory pattern for dynamic report discovery and instantiation, along with clean separation of Plotly and Matplotlib report generators.

**Key Changes**:
1. Factory pattern for report registration and instantiation
2. Matplotlib functionality moved to deprecated `MatplotlibReportGenerator`
3. New `PlotlyReportGenerator` base class for interactive reports
4. Theme parameter added to all report generators
5. `BatteryOperationReport` now extends `PlotlyReportGenerator`

---

## Migration Path

### For Report Users

**Old Way** (still works, but discouraged):
```python
from core.reporting import BatteryOperationReport
from pathlib import Path

report = BatteryOperationReport(
    result=simulation_result,
    output_dir=Path('results/yearly_2024'),
    period='3weeks'
)
output_path = report.generate()
```

**New Way** (recommended):
```python
from core.reporting import ReportFactory
from pathlib import Path

report = ReportFactory.create(
    'battery_operation',
    result=simulation_result,
    output_dir=Path('results/yearly_2024'),
    period='3weeks'
)
output_path = report.generate()
```

**Benefits**:
- No need to import specific report classes
- Easier CLI integration
- Dynamic report discovery
- Future plugin support

---

### For Report Developers

#### Creating New Reports

**Old Way**:
```python
from core.reporting.report_generator import ReportGenerator

class MyReport(ReportGenerator):
    def __init__(self, result, output_dir):
        super().__init__([result], output_dir)

    def generate(self):
        # ... implementation ...
        pass
```

**New Way** (use PlotlyReportGenerator):
```python
from core.reporting.plotly_report_generator import PlotlyReportGenerator
from core.reporting.factory import ReportFactory

@ReportFactory.register('my_report')
class MyReport(PlotlyReportGenerator):
    def __init__(self, result, output_dir, theme='light'):
        super().__init__([result], output_dir, theme=theme)

    def generate(self):
        fig = self._create_visualization()

        # Apply theme automatically
        self.apply_theme(fig, title='My Report')

        # Save using inherited method
        output_path = self.save_plotly_figure(
            fig,
            filename='my_report',
            subdir='reports',
            title='My Report'
        )
        return output_path
```

**Key Changes**:
1. ✅ Register with `@ReportFactory.register('my_report')`
2. ✅ Extend `PlotlyReportGenerator` instead of `ReportGenerator`
3. ✅ Add `theme` parameter to `__init__`
4. ✅ Use inherited `apply_theme()` instead of manual theme application
5. ✅ Use inherited `save_plotly_figure()` instead of manual save

---

#### Migrating Matplotlib Reports

**Old Way** (matplotlib in base class):
```python
from core.reporting.report_generator import ReportGenerator
import matplotlib.pyplot as plt

class MyMatplotlibReport(ReportGenerator):
    def generate(self):
        self.apply_standard_plot_style()  # No longer in base class!

        fig, ax = plt.subplots()
        # ... plotting ...

        self.save_figure(fig, 'plot.png')  # No longer in base class!
```

**New Way** (use deprecated class):
```python
from core.reporting.matplotlib_report_generator import MatplotlibReportGenerator
from core.reporting.factory import ReportFactory

@ReportFactory.register('my_matplotlib_report')
class MyMatplotlibReport(MatplotlibReportGenerator):
    """
    ⚠️ This report uses deprecated Matplotlib.
    Consider migrating to Plotly for interactive HTML output.
    """

    def generate(self):
        # No need to call apply_standard_plot_style() - done in __init__

        fig, ax = self.create_subplots()  # Inherited method
        # ... plotting ...

        self.save_figure(fig, 'plot.png')  # Now available from parent
```

**Deprecation Timeline**:
- v2.0: `MatplotlibReportGenerator` available with deprecation warning
- v2.1-v2.9: Continued support
- v3.0: Matplotlib reports removed (use Plotly)

---

## Breaking Changes

### 1. ReportGenerator Constructor Signature

**Old**:
```python
ReportGenerator.__init__(results, output_dir)
```

**New**:
```python
ReportGenerator.__init__(results, output_dir, theme='light')
```

**Impact**: Low (default value provided)

**Migration**: Add `theme` parameter if subclassing directly

---

### 2. Matplotlib Methods Removed from Base Class

**Removed Methods**:
- `ReportGenerator.save_figure()` → moved to `MatplotlibReportGenerator`
- `ReportGenerator.apply_standard_plot_style()` → moved to `MatplotlibReportGenerator`

**Impact**: Medium (affects matplotlib reports)

**Migration**: Change parent class to `MatplotlibReportGenerator`

---

### 3. BatteryOperationReport Inheritance Changed

**Old**:
```python
class BatteryOperationReport(SingleScenarioReport)
```

**New**:
```python
@ReportFactory.register('battery_operation')
class BatteryOperationReport(PlotlyReportGenerator)
```

**Impact**: Low (still works if using public API)

**Migration**: None needed unless subclassing `BatteryOperationReport`

---

## Checklist for Migrating Custom Reports

- [ ] Change parent class to `PlotlyReportGenerator` (or `MatplotlibReportGenerator` if matplotlib-based)
- [ ] Add `@ReportFactory.register('report_name')` decorator
- [ ] Add `theme` parameter to `__init__`
- [ ] Pass `theme` to `super().__init__()`
- [ ] Replace manual theme application with `self.apply_theme(fig)`
- [ ] Replace manual save with `self.save_plotly_figure()`
- [ ] Update tests to use factory instantiation
- [ ] Update documentation with factory usage examples

---

## Testing Your Migration

### 1. Test Factory Registration
```python
from core.reporting import ReportFactory

# Verify report is registered
reports = ReportFactory.list_reports()
assert 'my_report' in reports

# Test instantiation
report = ReportFactory.create('my_report', result=..., output_dir=...)
assert report is not None
```

### 2. Test Report Generation
```python
output_path = report.generate()
assert output_path.exists()
assert output_path.suffix == '.html'  # for Plotly reports
```

### 3. Run Framework Tests
```bash
pytest tests/reporting/test_report_framework.py -v
```

---

## FAQ

**Q: Do I need to migrate all my reports immediately?**
A: No. Old reports continue to work with deprecation warnings. Migrate at your convenience.

**Q: What if I have a matplotlib report that can't be converted to Plotly?**
A: Use `MatplotlibReportGenerator` as the parent class. It will be supported through v2.x.

**Q: Can I still import reports directly instead of using the factory?**
A: Yes, direct imports still work. The factory is optional but recommended.

**Q: How do I add my report to the factory if I can't modify the source?**
A: Create a plugin file and register after import:
```python
from core.reporting import ReportFactory
from my_module import MyReport

ReportFactory.register('my_report')(MyReport)
```

**Q: Will v3.0 remove matplotlib support entirely?**
A: Yes, but you'll have 1+ year to migrate (v2.0 → v3.0 transition period).

---

## Getting Help

- **Documentation**: See `docs/REPORT_STANDARDS.md` for architectural standards
- **Examples**: Check `scripts/examples/generate_battery_operation_report.py`
- **Tests**: Review `tests/reporting/test_report_framework.py` for usage patterns
- **Issues**: Open GitHub issue or contact Battery Optimization Team

---

## Migration Timeline

| Date | Event |
|------|-------|
| 2025-01-11 | v2.0 released with factory pattern |
| 2025-01-11 | `MatplotlibReportGenerator` marked deprecated |
| 2025-Q2 | All core reports migrated to Plotly |
| 2026-Q1 | v3.0 planning (matplotlib removal) |
| 2026-Q4 | v3.0 release (estimated) |

**Recommendation**: Migrate to `PlotlyReportGenerator` and factory pattern within 6 months to stay current with framework evolution.
