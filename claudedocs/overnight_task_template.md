# Overnight Task Template

Use this template when setting up overnight autonomous runs with `/sc:overnight`

## Example Usage

```
/sc:overnight

OVERNIGHT TASKS:
1. [Analysis] Run complete battery dimensioning sweep for 2024 data
   - Grid limits: 60, 70, 80 kW
   - Battery sizes: 50-150 kWh in 10 kWh steps
   - Generate 3D plots and reports

2. [Optimization] Refine Powell optimization for top 5 candidates
   - Run detailed refinement on grid search winners
   - Generate comparison reports
   - Update dimensioning_summary.json

3. [Testing] Run full test suite and fix any failures
   - pytest tests/ -v
   - Fix any failing tests
   - Update test documentation

4. [Documentation] Generate comprehensive analysis report
   - Consolidate all results into FULLSTENDIG_RAPPORT.md
   - Include all plots and tables
   - Add executive summary

COMPLETION CRITERIA:
- All tasks completed or logged as failed with reason
- Comprehensive overnight report generated
- No uncommitted changes (create git commits for completed work)
- Detailed error log if any failures occurred

EXPECTED RUNTIME: 4-6 hours
OUTPUT LOCATION: claudedocs/overnight_report_$(date +%Y%m%d).md
```

## Task Categories

**[Analysis]** - Data analysis, statistical operations, report generation
**[Optimization]** - Long-running optimization sweeps
**[Testing]** - Test execution and fixing
**[Refactoring]** - Code improvements and restructuring
**[Documentation]** - Doc generation and updates
**[Data]** - Data fetching, processing, caching

## Best Practices

### ✅ Good Overnight Tasks
- Long-running computations (grid searches, sensitivity analysis)
- Batch testing and fixing
- Comprehensive documentation generation
- Data pipeline processing
- Multi-step refactoring with validation

### ❌ Avoid for Overnight
- Tasks requiring user input or decision-making
- Ambiguous requirements needing clarification
- Experimental features without clear spec
- Operations on unclear/untested code paths

## Progress Tracking

During overnight run, Claude will:
1. Create memory checkpoints every 30 minutes
2. Log all operations to `claudedocs/overnight_logs/YYYYMMDD_HHmm.md`
3. Update task status in memory
4. Generate final report with statistics

You can resume interrupted sessions by:
```
/sc:overnight
"Resume previous overnight session - check memory for last checkpoint"
```

## Example Overnight Session Output

```markdown
# Overnight Report - 2025-11-13

## Session Summary
- Start: 2025-11-13 22:00:00
- End: 2025-11-14 03:45:32
- Duration: 5h 45m 32s
- Tasks: 4 total (3 completed, 1 failed)

## Task Results

### ✅ Task 1: Battery dimensioning sweep
- Status: Completed
- Duration: 3h 12m
- Output: 45 grid search combinations analyzed
- Files: plots/ directory with 12 new visualizations

### ✅ Task 2: Powell optimization refinement
- Status: Completed
- Duration: 1h 45m
- Output: Top 5 candidates refined
- Files: powell_refinement_results.json updated

### ❌ Task 3: Full test suite
- Status: Failed after 2 retries
- Error: Import error in test_optimization.py
- Action: Logged for manual review
- Files: test_errors.log

### ✅ Task 4: Analysis report generation
- Status: Completed
- Duration: 28m
- Output: FULLSTENDIG_RAPPORT.md (15 pages)
- Files: Multiple supporting documents

## Statistics
- Total operations: 247
- File operations: 89 (56 Read, 23 Edit, 10 Write)
- Bash commands: 45
- MCP operations: 113
- Errors encountered: 3 (2 recovered, 1 logged)

## Git Commits Created
1. `feat: complete battery dimensioning grid search for 2024`
2. `docs: generate comprehensive analysis report`

## Next Steps
1. Review test failure in test_optimization.py
2. Validate dimensioning results
3. Consider extending analysis to 2025 data
```
