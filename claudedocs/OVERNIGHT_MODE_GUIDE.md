# Overnight Mode - Quick Start Guide

## Setup (One-time)

Rammeværket er nå installert:
- ✅ `/sc:overnight` kommando: `~/.claude/commands/sc/overnight.md`
- ✅ CLAUDE.md override seksjon for autonomous mode
- ✅ Task template: `claudedocs/overnight_task_template.md`

## Hvordan Bruke

### Steg 1: Forbered Task List

Skriv ned hva du vil at Claude skal gjøre over natten:

```
/sc:overnight

OVERNIGHT TASKS:
1. [Analysis] Run battery dimensioning grid search
   - Test grid limits: 60, 70, 80 kW
   - Battery sizes: 50-150 kWh (10 kWh steps)
   - Generate plots and summary

2. [Testing] Run pytest suite and fix failures
   - Run tests/
   - Fix any failing tests
   - Document fixes

3. [Documentation] Update analysis reports
   - Consolidate results
   - Generate FULLSTENDIG_RAPPORT.md

COMPLETION CRITERIA:
- All analysis complete with visualizations
- Tests passing
- Comprehensive report generated
- Git commits for completed work

EXPECTED RUNTIME: 4-6 hours
```

### Steg 2: Start Overnight Session

Bare kjør kommandoen - Claude vil:
1. ✅ Parse oppgavene
2. ✅ Lage detaljert TodoWrite
3. ✅ Starte utførelse UTEN confirmations
4. ✅ Checkpoint hvert 30. minutt
5. ✅ Automatisk retry ved feil (max 2x)
6. ✅ Generere comprehensive rapport

### Steg 3: Sjekk Resultater (Neste Morgen)

```bash
# Les overnight rapporten
cat claudedocs/overnight_report_$(date +%Y%m%d).md

# Sjekk detaljert log
cat claudedocs/overnight_logs/$(date +%Y%m%d)_*.md

# Se git commits
git log --oneline -10
```

## Hva Skjer Under Panseret?

### Autonomous Mode Aktiveres
- ❌ NO confirmations
- ✅ Parallel operations enabled (overrides sequential protocol)
- ✅ Auto-retry på errors
- ✅ Memory checkpoints hvert 30. minutt
- ✅ Verbose logging

### Progress Tracking
Claude bruker `mcp__memory` for å tracke:
```
overnight_session_[timestamp] → Session metadata
overnight_task_1 → "completed"
overnight_task_2 → "running"
overnight_task_3 → "pending"
overnight_checkpoint_2200 → State snapshot
overnight_errors → ["test_optimization.py import error"]
```

### Error Handling
```
Operation → Error
  ↓
Retry 1 → Error
  ↓
Retry 2 → Success?
  ↓ No
Log error → Continue to next task
```

## Beste Praksis

### ✅ Gode Overnight Tasks
- Lang-kjørende analyser (grid search, sensitivity)
- Batch testing og fixing
- Dokumentasjon generering
- Data processing pipelines
- Multi-step refactoring med tester

### ❌ Unngå Overnight
- Tasks som trenger user input
- Uklare requirements
- Eksperimentelle features uten spec
- Kritiske produksjons-deployments

## Eksempel: Battery Analysis Overnight

```
/sc:overnight

OVERNIGHT TASKS:
1. [Data] Fetch fresh PVGIS and ENTSO-E data for 2024
   - Download via APIs
   - Cache locally
   - Validate data quality

2. [Analysis] Complete dimensioning sweep
   - Grid: [60, 65, 70, 75, 80] kW
   - Battery: 40-160 kWh (5 kWh steps)
   - Generate 3D breakeven plots

3. [Optimization] Powell refinement on top 10
   - Detailed optimization runs
   - Save results to JSON
   - Generate comparison tables

4. [Reporting] Comprehensive analysis report
   - Include all plots
   - Executive summary
   - Technical appendices
   - Save to FULLSTENDIG_RAPPORT.md

5. [Git] Commit all completed work
   - Organized commits by task
   - Clear commit messages
   - Push to remote

COMPLETION CRITERIA:
- 125 grid search combinations analyzed
- Top 10 refined with Powell
- Complete report with visualizations
- All changes committed to git

EXPECTED RUNTIME: 6-8 hours
OUTPUT: claudedocs/overnight_report_YYYYMMDD.md
```

## Troubleshooting

### Hvis session disconnecter
```
/sc:overnight
"Resume previous overnight session - check mcp__memory for last checkpoint"
```

Claude vil:
1. Lese memory for `overnight_checkpoint_*`
2. Identifisere siste completed task
3. Continue fra der

### Hvis du vil stoppe midtveis
Bare avbryt session. Next time:
```
/sc:overnight
"Show me status from last overnight run and let me decide if we should continue"
```

## Performance Tips

- **Bruk cached data**: Set `use_cache=True` for PVGIS/ENTSO-E
- **Batch operations**: Group relaterte tasks
- **Parallel opportunities**: Claude vil automatisk parallellisere
- **Memory efficient**: Use `--uc` flag for large operations

## Output Struktur

```
claudedocs/
├── overnight_report_20251113.md          # Main summary
├── overnight_logs/
│   └── 20251113_2200.md                  # Detailed log
├── FULLSTENDIG_RAPPORT.md                # Analysis output
└── plots/                                 # Generated visualizations
```

## Sikkerhet

Overnight mode har fortsatt boundaries:
- ❌ NO force push to git
- ❌ NO system-wide changes
- ❌ NO production deployments
- ❌ NO data deletion uten explicit task

---

**Klar til å kjøre overnight? Bruk templaten og start med `/sc:overnight`!**
