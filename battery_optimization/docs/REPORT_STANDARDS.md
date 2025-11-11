# Report Framework Standards

**Version**: 1.0
**Last Updated**: 2025-01-11
**Status**: ✅ Active

## Purpose

This document establishes architectural standards, design patterns, and best practices for the battery optimization report framework. All new reports and report modifications MUST adhere to these standards.

---

## 1. Architecture Principles

### 1.1 Separation of Concerns

**Reports are independent of simulation execution:**
- Reports read from `results/` directory (trajectory.csv, metadata.csv, summary.json)
- Reports NEVER run optimizations directly
- Reports can be regenerated without re-running simulations
- This enables report design iteration without costly re-computation

**File Structure:**
```
results/
├── yearly_2024/
│   ├── trajectory.csv          # Hourly timeseries (8760 rows)
│   ├── metadata.csv            # Battery config, economic params
│   ├── summary.json            # Economic metrics (NPV, IRR, etc.)
│   └── reports/                # Generated HTML/PNG reports
│       ├── plotly_optimized_v6.html
│       ├── battery_operation_3weeks.html
│       └── cost_analysis_june.html
```

### 1.2 Report Generator Pattern

All reports MUST extend `ReportGenerator` (or technology-specific subclass):

**Inheritance Hierarchy:**
```
ReportGenerator (base)
├── PlotlyReportGenerator (for interactive HTML reports) ✅ PREFERRED
├── MatplotlibReportGenerator (for static PNG/PDF) ⚠️ DEPRECATED
└── Custom subclasses (if needed)
```

**Technology Selection:**
- ✅ **Plotly**: Use `PlotlyReportGenerator` for all new reports
- ⚠️ **Matplotlib**: Use `MatplotlibReportGenerator` only for legacy compatibility

**Factory Registration (REQUIRED for all new reports):**

```python
from core.reporting.plotly_report_generator import PlotlyReportGenerator
from core.reporting.factory import ReportFactory
from core.reporting.result_models import SimulationResult
from pathlib import Path

@ReportFactory.register('my_custom_report')  # ← Register with factory
class MyCustomReport(PlotlyReportGenerator):
    """Custom report description"""

    def __init__(
        self,
        result: SimulationResult,
        output_dir: Path,
        custom_param: str = "default",
        theme: str = 'light'
    ):
        super().__init__([result], output_dir, theme=theme)
        self.custom_param = custom_param

    def generate(self) -> Path:
        """Generate report and return output path"""
        # 1. Extract data from self.results[0]
        # 2. Create visualizations using Plotly
        # 3. Apply theme: self.apply_theme(fig)
        # 4. Save: self.save_plotly_figure(fig, filename)
        # 5. Return Path to generated file

        output_path = self.save_plotly_figure(
            fig,
            filename='my_report',
            subdir='reports',
            title='My Custom Report'
        )
        return output_path
```

**Factory Usage:**
```python
from core.reporting import ReportFactory

# Create report by name (instead of direct import)
report = ReportFactory.create(
    'my_custom_report',
    result=simulation_result,
    output_dir=Path('results'),
    custom_param='value'
)
output_path = report.generate()

# List all registered reports
reports = ReportFactory.list_reports()
# ['battery_operation', 'my_custom_report', ...]

# Get report metadata
info = ReportFactory.get_report_info('my_custom_report')
print(info['docstring'])
```

**Benefits:**
- Consistent interface across all reports
- Dynamic report discovery (enables CLI integration)
- Built-in theme and path handling utilities
- Standard error handling
- Automatic registration for factory instantiation

### 1.3 Data Loading Pattern

**ALWAYS read battery config from metadata.csv:**

```python
def read_battery_config_from_metadata(results_dir: Path) -> BatteryConfig:
    """Read battery configuration from metadata.csv"""
    metadata_path = results_dir / "metadata.csv"

    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata not found: {metadata_path}")

    df = pd.read_csv(metadata_path)
    return BatteryConfig(
        battery_kwh=df['battery_kwh'].iloc[0],
        battery_kw=df['battery_kw'].iloc[0],
        # ... other fields
    )
```

**NEVER hardcode battery dimensions or economic parameters** in report code.

---

## 2. Technology Standards

### 2.1 Visualization Framework: Plotly

**All new reports MUST use Plotly** (not matplotlib):

**Rationale:**
- Interactive HTML reports (zoom, pan, hover)
- Shareable via email/web without dependencies
- Mobile-friendly responsive design
- Built-in export to PNG via kaleido
- Consistent with Norsk Solkraft theme

**Matplotlib is deprecated** for new reports (exception: legacy compatibility).

### 2.2 Norsk Solkraft Theme

**All Plotly figures MUST apply Norsk Solkraft theme:**

```python
from src.visualization.norsk_solkraft_theme import apply_light_theme

fig = go.Figure()
# ... add traces ...

apply_light_theme(fig)
fig.update_layout(
    title="Report Title",
    height=800,
    hovermode='x unified'  # Recommended for timeseries
)
```

**Theme Features:**
- **Primary colors**: Norsk Solkraft blue (#00609F), orange (#F5A621)
- **Neutral palette**: Gray scale (#F5F5F5 to #212121)
- **Semantic colors**: Green (success), red (warnings), blue (info)
- **Accessibility**: WCAG AA compliant (4.5:1 text contrast, 3:1 UI contrast)
- **Typography**: Clear sans-serif hierarchy

**Color Usage Guidelines:**
```python
colors = {
    'blå': '#00609F',        # Primary - brand, comparison baseline
    'oransje': '#F5A621',    # Accent - energy costs, key metrics
    'grønn': '#4CAF50',      # Success - savings, positive results
    'rød': '#E53935',        # Warning - high costs, risks
    'grå': '#757575',        # Neutral - reference scenarios
    'lys_grå': '#F5F5F5',    # Backgrounds
    'karbonsvart': '#212121' # Text
}
```

**NEVER use >4 colors in a single visualization** - maintains clarity.

### 2.3 Export Formats

**Primary format: HTML**
```python
fig.write_html(
    output_path,
    include_plotlyjs='cdn',  # Lightweight, cached by browser
    config={
        'displayModeBar': True,
        'displaylogo': False,
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'battery_report',
            'height': 1080,
            'width': 1920,
            'scale': 2
        }
    }
)
```

**Secondary format: PNG** (optional, via kaleido)
```python
try:
    fig.write_image(output_path.with_suffix('.png'), width=1920, height=1080)
except Exception as e:
    logger.warning(f"PNG export failed: {e}. Install kaleido for PNG support.")
```

**File size targets:**
- HTML: <10 MB (typical: 3-7 MB for full year data)
- PNG: <5 MB at 1920×1080, 150 DPI

---

## 3. Design Standards

### 3.1 Layout Hierarchy

**Information Hierarchy (from ChatGPT Phase 2 Review):**

```
Tier 1 (Primary - 500px height):
  Critical decision metrics that drive actions
  Example: SOC + Curtailment, NPV Heatmap, Cumulative Savings

Tier 2 (Secondary - 350px height):
  Supporting analysis and breakdowns
  Example: Power flows, Daily costs, Timeseries validation

Tier 3 (Detail - 250px height, collapsible):
  Auxiliary metrics, statistics tables, raw data
  Example: Weekly aggregates, summary statistics
```

**Maximum panels per report:**
- **Recommended**: 8-9 panels (fits on 2 screens @ 1080p)
- **Maximum**: 12 panels (only if essential, use collapsible sections)
- **Avoid**: >12 panels = information overload

### 3.2 Panel Structure Standard

**Every panel MUST follow this structure:**

```python
# Panel title with metadata
subplot_title = "State of Charge (SOC) - 3 weeks from 2024-06-01"

# Add trace with descriptive name
fig.add_trace(
    go.Scatter(
        x=df.timestamp,
        y=df.soc_kwh,
        mode='lines',
        name='Battery SOC',
        line=dict(color=colors['blå'], width=2),
        hovertemplate='<b>SOC</b>: %{y:.1f} kWh<br>Time: %{x}<extra></extra>'
    ),
    row=1, col=1
)

# Update axes with units
fig.update_xaxes(title_text="Time", row=1, col=1)
fig.update_yaxes(title_text="SOC (kWh)", row=1, col=1)
```

**Hover tooltip requirements:**
- Include variable name in bold: `<b>Variable</b>`
- Show value with appropriate precision: `%{y:.1f}` (1 decimal) or `%{y:,.0f}` (thousands separator)
- Include units explicitly: `kWh`, `kW`, `kr`, `%`
- Add timestamp for timeseries: `Time: %{x}`
- End with `<extra></extra>` to remove trace name redundancy

### 3.3 Responsive Design

**Breakpoint strategy** (from ChatGPT recommendations):

```python
# Desktop (>1200px): 6×2 grid as-is
# Tablet (768-1199px): 3×4 grid (merge panels, increase height)
# Mobile (<767px): 1×12 stacked (single-column, 400px/panel)

# Example responsive height
fig.update_layout(
    height=2400,  # Desktop: 6 rows × 400px
    # Future: Add media queries via CSS for tablet/mobile
)
```

**Current limitation**: Plotly doesn't support CSS media queries directly. Responsive design requires:
1. Generate separate figures for mobile/tablet/desktop, OR
2. Use flexible layouts with percentage heights (future enhancement)

### 3.4 Accessibility Standards

**WCAG AA Compliance (Minimum):**
- Text contrast: ≥4.5:1 (normal text), ≥3.0:1 (large text 18pt+)
- UI element contrast: ≥3.0:1 (buttons, controls)
- Color redundancy: Never rely on color alone (use shapes, patterns, labels)

**WCAG AAA Compliance (Target):**
- Text contrast: ≥7:1
- Colorblind-safe palettes: RdYlBu, PuOr (avoid RdYlGn)

**Validation checklist:**
- [ ] All text passes contrast checker (WebAIM)
- [ ] Colorblind simulation tested (Coblis)
- [ ] Hover tooltips include explicit labels (not just color-coded)
- [ ] Legends positioned clearly (not overlapping data)

---

## 4. Performance Standards

### 4.1 Render Time Targets

**Initial load:**
- Target: <1.5 seconds
- Maximum: 3.0 seconds
- Current: 2-3 seconds for 12-panel dashboards (needs optimization)

**Optimization strategies:**
- Lazy loading: Render panels on scroll (Intersection Observer)
- Data sampling: Show 500 points initially, load full resolution on zoom
- Web workers: Offload data aggregation to background threads

### 4.2 Data Volume Guidelines

**Timeseries data:**
- Hourly (PT60M): 8,760 points/year → OK for direct plotting
- 15-minute (PT15M): 35,040 points/year → Consider sampling for overview charts

**File sizes:**
- trajectory.csv: ~5 MB for full year @ PT15M
- HTML reports: <10 MB target (include CDN Plotly, not embedded)

### 4.3 Memory Management

**Avoid:**
- Loading entire dataframes for small date ranges (filter first)
- Duplicating timeseries data across panels (reference shared dataframe)
- Generating figures in loops without cleanup

**Prefer:**
```python
# Good: Filter before processing
df_period = df[(df.timestamp >= start) & (df.timestamp < end)]
fig = create_report(df_period)

# Bad: Load all, process later
df_all = pd.read_csv('trajectory.csv')  # 5 MB
fig = create_report(df_all, start, end)  # Wastes memory
```

---

## 5. Testing Standards

### 5.1 Unit Tests Required

**Every report class MUST have:**

```python
# tests/test_my_custom_report.py
import pytest
from pathlib import Path
from my_custom_report import MyCustomReport
from core.reporting import SimulationResult

def test_report_generation(tmp_path, sample_result):
    """Test report generates without errors"""
    report = MyCustomReport(sample_result, tmp_path)
    output_path = report.generate()

    assert output_path.exists()
    assert output_path.suffix == '.html'
    assert output_path.stat().st_size > 1000  # Not empty

def test_missing_metadata_raises_error(tmp_path):
    """Test graceful error when metadata.csv missing"""
    # Create result without metadata
    result = SimulationResult.load(tmp_path / 'incomplete_results')

    with pytest.raises(FileNotFoundError, match="Metadata not found"):
        report = MyCustomReport(result, tmp_path)
        report.generate()

def test_custom_parameter_validation(tmp_path, sample_result):
    """Test custom parameter validation"""
    with pytest.raises(ValueError, match="Invalid parameter"):
        report = MyCustomReport(sample_result, tmp_path, custom_param="invalid")
```

**Minimum coverage: 80%** for all report modules.

### 5.2 Integration Tests

**Test with multiple scenarios:**
- Different battery sizes (30 kWh, 80 kWh, 150 kWh)
- Different time periods (3 weeks, 1 month, full year)
- Edge cases (no curtailment, high curtailment, negative prices)

### 5.3 Visual Regression Tests

**Validate theme compliance:**
```python
def test_norsk_solkraft_theme_applied(sample_report_figure):
    """Test Norsk Solkraft theme colors present"""
    layout = sample_report_figure.layout

    # Check background colors
    assert layout.plot_bgcolor == '#FFFFFF'
    assert layout.paper_bgcolor == '#F5F5F5'

    # Check font
    assert layout.font.family == 'Arial, sans-serif'
    assert layout.font.color == '#212121'  # karbonsvart

    # Check brand colors used in traces
    trace_colors = [trace.line.color for trace in sample_report_figure.data if hasattr(trace, 'line')]
    assert '#00609F' in trace_colors or '#F5A621' in trace_colors
```

---

## 6. Documentation Standards

### 6.1 Module Docstrings

**Every report module MUST include:**

```python
"""
Battery Operation Report - Unified Dashboard

Consolidates battery operation analysis into single interactive Plotly dashboard.
Replaces legacy matplotlib scripts: plot_battery_simulation.py, plot_power_flows.py, plot_soc.py.

**Features:**
- 12 interactive subplots (6 rows × 2 columns)
- Configurable periods: 3weeks, 1month, 3months, custom
- Auto-detection of battery dimensions from metadata.csv
- Full Norsk Solkraft theme integration

**Usage:**
    from core.reporting import SimulationResult, BatteryOperationReport

    result = SimulationResult.load(Path('results/yearly_2024'))
    report = BatteryOperationReport(result, Path('results'), period='3weeks')
    output_path = report.generate()
    print(f"Report generated: {output_path}")

**Outputs:**
- HTML: results/reports/battery_operation_3weeks.html (~3 MB)
- Optional PNG: results/reports/battery_operation_3weeks.png (via kaleido)

**Dependencies:**
- plotly>=5.18.0
- pandas>=2.0.0
- numpy>=1.24.0
- src.visualization.norsk_solkraft_theme

**Author**: Battery Optimization Team
**Created**: 2025-01-10
**Last Modified**: 2025-01-11
"""
```

### 6.2 Function Docstrings

**All public methods MUST document:**
- Purpose (one-line summary)
- Parameters with types and descriptions
- Returns with type and description
- Raises with exception types and conditions
- Example usage (if non-trivial)

```python
def generate(self) -> Path:
    """
    Generate battery operation dashboard with 12 interactive panels.

    Reads trajectory.csv and metadata.csv from result directory, creates
    Plotly dashboard with SOC, power flows, costs, and metrics panels.

    Returns:
        Path: Absolute path to generated HTML file

    Raises:
        FileNotFoundError: If trajectory.csv or metadata.csv missing
        ValueError: If period parameter invalid

    Example:
        >>> report = BatteryOperationReport(result, output_dir, period='1month')
        >>> output_path = report.generate()
        >>> print(f"Generated: {output_path}")
        Generated: /results/reports/battery_operation_1month.html
    """
```

### 6.3 README Updates

**When adding new report, update docs/available_reports.md:**

```markdown
### X. New Report Type

**Location**: `path/to/new_report.py`

**Description**: Brief description of what the report shows and why it's useful.

**Outputs**:
- `results/reports/new_report.html` - Interactive HTML dashboard
- `results/reports/new_report.png` - Static PNG (optional)

**Features**:
- Feature 1 (with explanation)
- Feature 2
- Feature 3

**Usage**:
\```python
from new_report import NewReport
# ... example code
\```

**Example Output**: `results/yearly_2024/new_report.html`
```

---

## 7. Common Patterns & Anti-Patterns

### 7.1 ✅ DO

**Read from results directory:**
```python
df = pd.read_csv(results_dir / 'trajectory.csv', parse_dates=['timestamp'])
config = read_battery_config_from_metadata(results_dir)
```

**Use BatteryConfig dataclass:**
```python
@dataclass
class BatteryConfig:
    battery_kwh: float = None
    battery_kw: float = None
    tariff_peak: float = 0.296
    # ... other fields
```

**Apply theme consistently:**
```python
from src.visualization.norsk_solkraft_theme import apply_light_theme
fig = go.Figure()
# ... add traces
apply_light_theme(fig)
```

**Provide clear hover tooltips:**
```python
hovertemplate='<b>SOC</b>: %{y:.1f} kWh<br>Time: %{x}<extra></extra>'
```

**Handle errors gracefully:**
```python
if not metadata_path.exists():
    raise FileNotFoundError(f"Metadata not found: {metadata_path}")
```

### 7.2 ❌ DON'T

**Hardcode battery dimensions:**
```python
# BAD
battery_kwh = 30  # ❌ What if user tests 80 kWh battery?
degradation_cost = 0.05  # ❌ What if using different chemistry?
```

**Run optimizations in report code:**
```python
# BAD
from core.rolling_horizon_optimizer import RollingHorizonOptimizer
optimizer = RollingHorizonOptimizer(...)  # ❌ Reports should only read results
result = optimizer.optimize_window(...)   # ❌ Violates separation of concerns
```

**Ignore theme:**
```python
# BAD
fig = go.Figure()
fig.update_layout(
    paper_bgcolor='white',      # ❌ Should use theme
    font=dict(family='Comic Sans')  # ❌ Inconsistent typography
)
```

**Use matplotlib for new reports:**
```python
# BAD (deprecated)
import matplotlib.pyplot as plt  # ❌ Use Plotly instead
plt.plot(x, y)
plt.savefig('report.png')
```

**Overwhelm with panels:**
```python
# BAD
fig = make_subplots(rows=15, cols=2)  # ❌ Too many panels (30 total!)
```

---

## 8. Migration Path (Legacy → Standards-Compliant)

### 8.1 Assessment Checklist

For each existing report, evaluate:

- [ ] **Uses Plotly?** (If matplotlib → migrate to Plotly)
- [ ] **Applies Norsk Solkraft theme?** (If not → apply `apply_light_theme()`)
- [ ] **Reads from results directory?** (If runs optimizer → refactor to read trajectory.csv)
- [ ] **Uses BatteryConfig?** (If hardcoded params → migrate to dataclass)
- [ ] **Extends ReportGenerator?** (If not → refactor to base class)
- [ ] **Has unit tests?** (If not → create test coverage)
- [ ] **Documented in available_reports.md?** (If not → add documentation)

### 8.2 Migration Priority

**Tier 1 (Critical - Migrate first):**
- Most-used reports (yearly report, battery sizing)
- Reports with hardcoded values
- Reports using deprecated MonthlyLPOptimizer

**Tier 2 (Important - Migrate next):**
- Frequently-used analysis scripts
- Reports lacking interactivity

**Tier 3 (Nice-to-have - Migrate later):**
- Rarely-used utility scripts
- One-off analysis tools

### 8.3 Deprecation Process

1. **Mark as deprecated** in docstring:
   ```python
   """
   DEPRECATED: Use BatteryOperationReport instead.
   This script will be removed in v2.0.
   """
   ```

2. **Add migration guide** in docs:
   ```markdown
   ## Migration: plot_battery_simulation.py → BatteryOperationReport

   **Old usage:**
   ```python
   python scripts/visualization/plot_battery_simulation.py
   ```

   **New usage:**
   ```python
   from core.reporting import BatteryOperationReport
   report = BatteryOperationReport(result, output_dir, period='3weeks')
   report.generate()
   ```
   ```

3. **Archive to `archive/legacy_reports/`** when replacement confirmed working

4. **Remove after 1 major version** (allow transition period)

---

## 9. Review Process

### 9.1 Pre-Commit Checklist

Before submitting report code for review:

- [ ] Extends `ReportGenerator` base class
- [ ] Uses Plotly with Norsk Solkraft theme applied
- [ ] Reads battery config from metadata.csv (no hardcoded values)
- [ ] Includes comprehensive docstrings (module + all public methods)
- [ ] Has unit tests with ≥80% coverage
- [ ] Passes all existing tests (`pytest tests/`)
- [ ] Updated `docs/available_reports.md`
- [ ] Follows naming convention: `{purpose}_report.py` or `plot_{analysis}_plotly.py`

### 9.2 Code Review Criteria

**Reviewers MUST verify:**

1. **Architecture compliance**: Separates report generation from simulation
2. **Theme consistency**: Norsk Solkraft theme applied correctly
3. **Accessibility**: WCAG AA contrast ratios validated
4. **Performance**: Initial render <3 seconds (test with full year data)
5. **Documentation**: Clear docstrings and usage examples
6. **Testing**: Adequate test coverage and edge case handling

### 9.3 ChatGPT Review Integration

For significant changes (new report types, major refactors):

1. **Generate report** with current implementation
2. **Request ChatGPT UI/UX review** via chatgpt-proxy agent
3. **Address critical feedback** (High priority issues)
4. **Document decisions** in code comments if deviating from recommendations
5. **Iterate** until ChatGPT assessment ≥B+ grade

**Example review prompt:**
> "Review this new battery degradation report for UI/UX quality, accessibility, and consistency with Norsk Solkraft design system. Provide actionable feedback prioritized by impact/effort ratio."

---

## 10. Future Enhancements

### 10.1 Planned Improvements

**From ChatGPT Phase 2 Review (Priority Ranked):**

1. **Linked brushing & cross-panel filtering** (High impact, 4-5 days)
   - Synchronize x-axis ranges across timeseries panels
   - Dashboard-level date range selector

2. **Mobile responsive layouts** (Medium impact, 3-4 days)
   - Breakpoints: desktop (6×2) → tablet (3×4) → mobile (1×12)
   - Test on real devices

3. **Performance optimization** (Medium impact, 2-3 days)
   - Lazy loading with Intersection Observer
   - Data sampling for initial render

4. **Progressive disclosure** (Medium impact, 2-3 days)
   - Collapsible detail panels
   - 3-tier visual hierarchy implementation

5. **Enhanced accessibility** (High impact, 1 day)
   - WCAG AAA compliance (7:1 contrast)
   - Colorblind-safe palettes (RdYlBu)

### 10.2 Research Directions

- **Real-time updates**: WebSocket integration for live battery monitoring
- **Collaborative annotations**: Allow users to add notes on charts (shared via JSON)
- **Export templates**: "Board Report" (top 4 panels) vs "Full Technical" (all panels)
- **Theme variants**: Dark mode, high-contrast mode, print-optimized mode
- **Localization**: English translations for international stakeholders

---

## 11. Version History

| Version | Date       | Changes                                                    |
|---------|------------|------------------------------------------------------------|
| 1.0     | 2025-01-11 | Initial standards document based on Phase 1-2 migrations  |

**Next review**: 2025-04-01 (quarterly update cycle)

---

## 12. References

### Internal Documentation
- `docs/available_reports.md` - Catalog of all report types
- `docs/weekly_optimization_migration.md` - Performance optimization guide
- `README.md` - Project overview and setup

### External Standards
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/) - Accessibility compliance
- [Plotly Documentation](https://plotly.com/python/) - Visualization framework
- [Material Design](https://material.io/design) - UI/UX principles

### Design Resources
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) - Validate text contrast
- [Coblis Color Blindness Simulator](https://www.color-blindness.com/coblis-color-blindness-simulator/) - Test colorblind accessibility
- [Plotly Color Scales](https://plotly.com/python/builtin-colorscales/) - Reference for colorblind-safe palettes

---

**Maintained by**: Battery Optimization Team
**Questions**: See `docs/` or open GitHub issue
