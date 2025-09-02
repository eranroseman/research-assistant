# 40-Line Pipeline Display Design

## Date: December 3, 2024

## Goal: Optimal information density in 40 lines (fits on one screen)

## Proposed Layout: Complete Pipeline Status Dashboard

```
╔══════════════════════════════════════════════════════════════════════════╗
║                        V5 PIPELINE PROCESSING                            ║
╠══════════════════════════════════════════════════════════════════════════╣
║ Input:   extraction_pipeline/20250901/  [2,000 papers]                   ║
║ Output:  kb_output/                                                      ║
║ Started: 2024-12-03 10:45:00 | Elapsed: 1h 12m 47s | ETA: 33m 15s       ║
╚══════════════════════════════════════════════════════════════════════════╝

┌─────────────┬────────────────────────┬──────────┬─────────┬────────┬──────┐
│ Stage       │ Progress               │ Status   │ Success │ Failed │ Time │
├─────────────┼────────────────────────┼──────────┼─────────┼────────┼──────┤
│ 1.CrossRef  │ ████████████████████ │ Complete │  1,950  │   50   │ 4m32s│
│ 2.S2        │ ████████████████████ │ Complete │  1,980  │   20   │ 1m15s│
│ 3.OpenAlex  │ ████████████████████ │ Complete │  1,960  │   40   │ 3m45s│
│ 4.Unpaywall │ ████████████████████ │ Complete │  1,990  │   10   │ 2m20s│
│ 5.PubMed    │ ████████████████████ │ Complete │  1,850  │  150   │ 6m10s│
│ 6.arXiv     │ ███████████░░░░░░░░░ │ Running  │    312  │  238   │ 27m5s│
│ 7.TEI       │ ░░░░░░░░░░░░░░░░░░░░ │ Waiting  │      -  │    -   │   -  │
│ 8.PostProc  │ ░░░░░░░░░░░░░░░░░░░░ │ Waiting  │      -  │    -   │   -  │
└─────────────┴────────────────────────┴──────────┴─────────┴────────┴──────┘

CURRENT ACTIVITY
────────────────────────────────────────────────────────────────────────────
Stage:    arXiv Enrichment (550/2000 papers - 27.5%)
Rate:     0.34 papers/sec | API delay: 3s per request
Batch:    Processing papers 541-560

RECENT EVENTS (last 5)
────────────────────────────────────────────────────────────────────────────
[11:57:42] ✓ paper_2024_ai_advances: Found on arXiv (cs.AI)
[11:57:39] ✗ paper_clinical_trial_2023: Not found on arXiv
[11:57:36] ✓ paper_quantum_computing: Found on arXiv (quant-ph)
[11:57:33] ⚠ paper_12345: Retry 2/3 - Connection timeout
[11:57:30] 💾 Checkpoint saved (540 papers processed)

OVERALL STATISTICS
────────────────────────────────────────────────────────────────────────────
│ Total Processed:  10,582 / 16,000 (66.1%)     Success Rate: 89.4%        │
│ Papers/hour:      8,765                        Disk Used:    1.2 GB       │
│ API Calls:        12,453                       Cost Est:     $0.00        │
│ Checkpoints:      42                           Failures:     1,128        │
└────────────────────────────────────────────────────────────────────────────┘

[Press Ctrl+C to pause] [Press v for verbose mode] [Press h for help]
```

## Alternative Layout: Compact with More Details (40 lines)

```
================================================================================
                         V5 ENRICHMENT PIPELINE
================================================================================
Input:  extraction_pipeline/20250901/ [2,000 papers]
Output: kb_output/ [1.2 GB]
Mode:   Incremental | Checkpoint: Every 500 papers | Verbose: OFF
================================================================================

STAGE PROGRESS
────────────────────────────────────────────────────────────────────────
  #  Stage        Papers    Progress Bar            Success  Fail   Time
────────────────────────────────────────────────────────────────────────
  1  CrossRef     2000/2000 [████████████████████]   1950    50    4m32s  ✓
  2  S2           2000/2000 [████████████████████]   1980    20    1m15s  ✓
  3  OpenAlex     2000/2000 [████████████████████]   1960    40    3m45s  ✓
  4  Unpaywall    2000/2000 [████████████████████]   1990    10    2m20s  ✓
  5  PubMed       2000/2000 [████████████████████]   1850   150    6m10s  ✓
  6  arXiv         550/2000 [███████░░░░░░░░░░░░░]    312   238   27m05s  ⟳
  7  TEI             0/2000 [░░░░░░░░░░░░░░░░░░░░]      0     0        -  ⋯
  8  PostProc        0/2000 [░░░░░░░░░░░░░░░░░░░░]      0     0        -  ⋯
────────────────────────────────────────────────────────────────────────

CURRENT: arXiv Enrichment
────────────────────────────────────────────────────────────────────────
▶ Processing:  paper_550_quantum_mechanics.json
▶ Rate:        0.34 papers/sec (3s API delay)
▶ Batch:       28/100 | Checkpoint in: 450 papers
▶ Memory:      1.2 GB / 16 GB | CPU: 12% | Network: ↓ 1.2 MB/s

RECENT ACTIVITY (newest first)
────────────────────────────────────────────────────────────────────────
11:57:42  ✓  Found: paper_2024_ai_advances → cs.AI, cs.LG
11:57:39  ✗  Not found: paper_clinical_trial_2023
11:57:36  ✓  Found: paper_quantum_computing → quant-ph
11:57:33  ⚠  Retry 2/3: paper_12345 (timeout)
11:57:30  💾 Checkpoint: 540 papers saved

SUMMARY
────────────────────────────────────────────────────────────────────────
Started:   10:45:00 (1h 12m ago)    │  Papers/hour:  8,765
ETA:       33m 15s remaining        │  API calls:    12,453
Progress:  66.1% complete            │  Success rate: 89.4%
Estimate:  ~1,785 papers in final KB │  Disk usage:   1.2 GB
────────────────────────────────────────────────────────────────────────
```

## Minimal But Complete: Exactly 40 Lines

```
V5 PIPELINE | extraction_pipeline/20250901 → kb_output/ | 2000 papers
═══════════════════════════════════════════════════════════════════════
Start: 10:45:00 | Now: 11:57:47 | Elapsed: 1h 12m 47s | ETA: 33m 15s
───────────────────────────────────────────────────────────────────────

STAGE           PROGRESS                     DONE   OK    FAIL  TIME
───────────────────────────────────────────────────────────────────────
1. CrossRef     ████████████████████  100%   2000   1950    50  4m32s
2. S2           ████████████████████  100%   2000   1980    20  1m15s
3. OpenAlex     ████████████████████  100%   2000   1960    40  3m45s
4. Unpaywall    ████████████████████  100%   2000   1990    10  2m20s
5. PubMed       ████████████████████  100%   2000   1850   150  6m10s
6. arXiv        ███████░░░░░░░░░░░░░   28%    550    312   238  27m5s
7. TEI          ░░░░░░░░░░░░░░░░░░░░    0%      0      0     0     -
8. PostProc     ░░░░░░░░░░░░░░░░░░░░    0%      0      0     0     -
───────────────────────────────────────────────────────────────────────

► ACTIVE: arXiv Enrichment (Stage 6 of 8)
  Current:  paper_550_quantum_mechanics.json
  Speed:    0.34 papers/sec | API: 3s delay | Batch: 28/100
  Next checkpoint in 450 papers

► RECENT LOG:
  11:57:42 [SUCCESS] paper_2024_ai_advances → arXiv:2024.12345 (cs.AI)
  11:57:39 [SKIPPED] paper_clinical_trial_2023 - Not on arXiv
  11:57:36 [SUCCESS] paper_quantum_computing → arXiv:2024.98765 (quant-ph)
  11:57:33 [WARNING] paper_12345 - Retry 2/3 (connection timeout)
  11:57:30 [CHECKPOINT] Saved at 540 papers

► STATISTICS:
  Total:    10,582/16,000 papers (66%)  |  Success: 89.4%
  Rate:     8,765 papers/hour            |  API calls: 12,453
  Memory:   1.2 GB used                  |  Failures: 1,128

► PROJECTIONS:
  Completion: ~12:31:02 (33m remaining)
  Final KB: ~1,785 papers (after quality filtering)
  Total time: ~1h 46m (estimated)

═══════════════════════════════════════════════════════════════════════
[Ctrl+C: Pause] [V: Verbose] [S: Skip stage] [R: Retry failures]
```

## Implementation with Rich Library

```python
from rich.console import Console
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.live import Live

class PipelineDashboard:
    """40-line dashboard that updates in place."""

    def __init__(self):
        self.console = Console()
        self.stages = {}
        self.current_stage = None
        self.recent_events = []

    def create_display(self):
        """Create the 40-line display."""
        layout = Layout()
        layout.split_column(
            Layout(self.create_header(), size=7),
            Layout(self.create_progress_table(), size=10),
            Layout(self.create_current_activity(), size=6),
            Layout(self.create_recent_events(), size=8),
            Layout(self.create_statistics(), size=7),
            Layout(self.create_footer(), size=2)
        )
        return layout

    def create_progress_table(self):
        """Create the stage progress table."""
        table = Table(box=None, padding=0)
        table.add_column("Stage", width=12)
        table.add_column("Progress", width=24)
        table.add_column("Status", width=10)
        table.add_column("Success", width=8, justify="right")
        table.add_column("Failed", width=8, justify="right")
        table.add_column("Time", width=8, justify="right")

        for stage_num, (name, data) in enumerate(self.stages.items(), 1):
            progress = self.create_progress_bar(data['current'], data['total'])
            status = self.get_status_symbol(data['status'])
            table.add_row(
                f"{stage_num}.{name}",
                progress,
                status,
                str(data['success']),
                str(data['failed']),
                data['time']
            )

        return Panel(table, title="STAGE PROGRESS", border_style="blue")

    def update(self, stage_data):
        """Update the display with new data."""
        self.stages.update(stage_data)
        return self.create_display()
```

## Benefits of 40-Line Display

1. **Everything visible at once** - No scrolling needed
2. **Rich information** - Current activity, recent events, statistics
3. **Professional appearance** - Clean tables and progress bars
4. **Live updates** - Refreshes in place without scrolling
5. **User controls** - Shows keyboard shortcuts
6. **Predictive** - Shows ETA and projected final count
7. **Diagnostic info** - Memory, CPU, network usage
8. **Context aware** - Shows batch info, checkpoint timing

## Responsive Design Features

### During Active Processing
- Show current file being processed
- Display rate and API delays
- Show recent successes and failures
- Update progress bars smoothly

### During Waiting/Errors
- Show retry attempts with countdown
- Display error messages clearly
- Show which stages are blocked
- Estimate time to recovery

### At Completion
- Final statistics summary
- Total time and success rate
- Papers added to KB
- Next recommended action

## Color Coding (Optional)

```python
# Status colors
"Complete": green
"Running": yellow
"Waiting": gray
"Failed": red
"Retrying": orange

# Progress bars
100%: green
50-99%: yellow
<50%: cyan
0%: gray

# Events
Success: green ✓
Failure: red ✗
Warning: yellow ⚠
Checkpoint: blue 💾
```

## Conclusion

A 40-line display provides the perfect balance:
- **Complete visibility** of all 8 stages
- **Current activity** details
- **Recent events** log (last 5)
- **Statistics** and projections
- **Clean and professional** appearance
- **Updates in place** without scrolling

This is much better than 700+ lines of scrolling output, while providing even MORE useful information in a format that's easy to scan and understand at a glance.
