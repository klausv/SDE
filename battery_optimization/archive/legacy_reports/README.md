# Legacy Reports Archive

This directory contains deprecated report scripts that have been replaced by modern, standards-compliant alternatives.

**Last Updated**: 2025-01-11

---

## Archiving Policy

Reports are archived (not deleted) when:
1. A superior alternative exists following current standards
2. The report served a specific purpose but is no longer actively used
3. The report uses deprecated technologies (matplotlib → Plotly migration)
4. Consolidation replaces multiple scripts with unified solution

**Removal timeline**: Archived reports will be removed after 1 major version (e.g., v1.x → v2.0), allowing transition period.

---

## Archived Reports

### plotly_yearly_report_single_column.py
**Archived**: 2025-01-11
**Reason**: Replaced by `plotly_yearly_report_v6_optimized.py` (6×2 grid layout)
**Migration**:
```python
# Old
python scripts/visualization/plotly_yearly_report_single_column.py results/yearly_2024/

# New
python scripts/visualization/plotly_yearly_report_v6_optimized.py results/yearly_2024/
```

**Key differences**:
- v6_optimized: 6×2 grid (11 consolidated charts) vs single-column (11 stacked)
- v6_optimized: Auto-detects battery dimensions from metadata.csv
- v6_optimized: Theme-native legends inside top-right (no overlap)
- Both use same Norsk Solkraft theme and interactivity

---

## Migration Assistance

If you rely on an archived report and need help migrating:

1. Check `docs/available_reports.md` for current report catalog
2. Review `docs/REPORT_STANDARDS.md` for migration guidelines
3. See archived script's deprecation notice (top of file) for recommended alternative
4. Consult `docs/weekly_optimization_migration.md` for optimizer migration examples

For questions, open GitHub issue or contact Battery Optimization Team.

---

## Developer Notes

**Before archiving a report**:
1. Add deprecation warning to module docstring
2. Document migration path (old → new command)
3. Update this README with entry
4. Update `docs/available_reports.md` to reflect current state
5. Ensure replacement report exists and is tested

**File structure**:
```
archive/
└── legacy_reports/
    ├── README.md (this file)
    ├── plotly_yearly_report_single_column.py
    └── [future archived reports]
```

Keep archive organized - avoid becoming a dumping ground for unmaintained code.
