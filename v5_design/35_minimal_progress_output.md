# Minimal Progress Output Design

## Date: December 3, 2024

## Goal: Reduce 700+ lines to <50 lines while keeping essential information

## Current Problem
- 8 stages × ~90 lines each = 700+ lines
- Too much scrolling, hard to see overall progress
- Checkpoint saves alone generate 200+ lines
- Batch progress updates add 100+ lines

## Proposed Solution: Single-Line Updates with Status Indicators

### Design 1: One Line Per Stage (8 lines total)

```
[CrossRef]    ████████████████████ 2000/2000 ✓ 1950 ✗ 50 [4m 32s]
[S2]          ████████████████████ 2000/2000 ✓ 1980 ✗ 20 [1m 15s]
[OpenAlex]    ████████████████████ 2000/2000 ✓ 1960 ✗ 40 [3m 45s]
[Unpaywall]   ████████████████████ 2000/2000 ✓ 1990 ✗ 10 [2m 20s]
[PubMed]      ████████████████████ 2000/2000 ✓ 1850 ✗ 150 [6m 10s]
[arXiv]       ████████████████████ 2000/2000 ✓ 250 ✗ 1750 [45m 00s]
[TEI]         ████████████████████ 2000/2000 ✓ 2000 ✗ 0 [1m 30s]
[PostProc]    ████████████████████ 2000/2000 ✓ 1680 ✗ 320 [8m 15s]
```

**Total: 8 lines!**

### Design 2: Compact Multi-Stage Display (15 lines)

```
V5 PIPELINE PROCESSING
══════════════════════════════════════════════════════════════════
Input:  extraction_pipeline/  [2000 papers]
Output: kb_output/

Stage Progress:
  CrossRef    [████████████████████] 100% ✓1950 ✗50   4m32s
  S2          [████████████████████] 100% ✓1980 ✗20   1m15s
  OpenAlex    [████████████████████] 100% ✓1960 ✗40   3m45s
  Unpaywall   [████████████████████] 100% ✓1990 ✗10   2m20s
  PubMed      [████████████████████] 100% ✓1850 ✗150  6m10s
  arXiv       [████████████████████] 100% ✓250  ✗1750 45m00s
  TEI         [████████████████████] 100% ✓2000 ✗0    1m30s
  PostProc    [████████████████████] 100% ✓1680 ✗320  8m15s

Total: 1h 12m 47s | Success rate: 89.2%
══════════════════════════════════════════════════════════════════
```

### Design 3: Live Dashboard (25 lines, updates in place)

```
╔══════════════════════════════════════════════════════════════════╗
║                    V5 PIPELINE DASHBOARD                         ║
╠══════════════════════════════════════════════════════════════════╣
║ Input:  extraction_pipeline/20250901  [2000 papers]              ║
║ Started: 2024-12-03 10:45:00  | Elapsed: 1h 12m                  ║
╚══════════════════════════════════════════════════════════════════╝

┌─────────────┬──────────┬───────────┬─────────┬─────────┬────────┐
│ Stage       │ Progress │ Processed │ Success │ Failed  │ Time   │
├─────────────┼──────────┼───────────┼─────────┼─────────┼────────┤
│ CrossRef    │ ████████ │ 2000/2000 │ 1950    │ 50      │ 4m32s  │
│ S2          │ ████████ │ 2000/2000 │ 1980    │ 20      │ 1m15s  │
│ OpenAlex    │ ████████ │ 2000/2000 │ 1960    │ 40      │ 3m45s  │
│ Unpaywall   │ ████████ │ 2000/2000 │ 1990    │ 10      │ 2m20s  │
│ PubMed      │ ████████ │ 2000/2000 │ 1850    │ 150     │ 6m10s  │
│ arXiv       │ ███░░░░░ │  450/2000 │ 60      │ 390     │ 12m15s │
│ TEI         │ ░░░░░░░░ │    0/2000 │ -       │ -       │ -      │
│ PostProc    │ ░░░░░░░░ │    0/2000 │ -       │ -       │ -      │
└─────────────┴──────────┴───────────┴─────────┴─────────┴────────┘

Current: arXiv enrichment (3s delay per paper)
Status:  ✓ Running | Rate: 0.3 papers/sec | ETA: 1h 30m

[✓] Checkpoint saved (450 papers)
[⚠] Retrying paper_12345: API timeout
```

### Design 4: Incremental Mode - Ultra Minimal (10 lines)

```
V5 PIPELINE: Processing 55 new papers (2150 already in KB)
────────────────────────────────────────────────────────────
CrossRef    ✓ 53/55 enriched   [8s]
S2          ✓ 54/55 enriched   [3s]
OpenAlex    ✓ 52/55 enriched   [5s]
Unpaywall   ✓ 55/55 enriched   [6s]
PubMed      ✓ 12/55 enriched   [10s]
arXiv       ✓ 5/55 enriched    [2m 45s]
────────────────────────────────────────────────────────────
Complete: 55 papers processed in 3m 17s
```

## Implementation Strategy

### Use Python's Rich Library for Live Updates

```python
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.live import Live

console = Console()

def create_pipeline_table(stages_data):
    """Create a rich table showing all stages."""
    table = Table(title="V5 Pipeline Progress")
    table.add_column("Stage", style="cyan", width=12)
    table.add_column("Progress", width=20)
    table.add_column("Status", width=15)
    table.add_column("Time", style="yellow")

    for stage in stages_data:
        progress_bar = "█" * int(stage['percent']/5) + "░" * (20 - int(stage['percent']/5))
        status = f"✓{stage['success']} ✗{stage['failed']}"
        table.add_row(stage['name'], progress_bar, status, stage['time'])

    return table

# Use with Live display that updates in place
with Live(create_pipeline_table(stages), refresh_per_second=1) as live:
    for update in pipeline_process():
        live.update(create_pipeline_table(update))
```

### Or Simple ANSI Escape Codes

```python
import sys

class MinimalReporter:
    """Ultra-minimal progress reporter using ANSI codes."""

    def __init__(self, total_stages=8):
        self.stages = {}
        self.total_stages = total_stages

    def update_stage(self, stage_name, current, total, succeeded, failed, elapsed):
        """Update a single stage's progress."""
        self.stages[stage_name] = {
            'current': current,
            'total': total,
            'succeeded': succeeded,
            'failed': failed,
            'elapsed': elapsed
        }
        self._redraw()

    def _redraw(self):
        """Redraw all stages (overwrites previous output)."""
        # Move cursor up to overwrite
        lines_up = len(self.stages) + 2
        sys.stdout.write(f'\033[{lines_up}A')  # Move up
        sys.stdout.write('\033[J')  # Clear from cursor down

        # Redraw all stages
        for name, data in self.stages.items():
            percent = (data['current'] / data['total'] * 100) if data['total'] else 0
            bar_width = 20
            filled = int(percent / 100 * bar_width)
            bar = '█' * filled + '░' * (bar_width - filled)

            line = f"[{name:12}] {bar} {data['current']:4}/{data['total']:4} "
            line += f"✓{data['succeeded']:4} ✗{data['failed']:4} [{self._format_time(data['elapsed'])}]"
            print(line)

        sys.stdout.flush()

    def _format_time(self, seconds):
        """Format seconds as compact time string."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m{int(seconds%60)}s"
        else:
            hours = int(seconds/3600)
            mins = int((seconds % 3600) / 60)
            return f"{hours}h{mins}m"
```

## Comparison of Approaches

| Design | Lines | Pros | Cons |
|--------|-------|------|------|
| **One-liner per stage** | 8 | Absolute minimum, very clean | Less detail, no headers |
| **Compact display** | 15 | Good balance, clear structure | Static, doesn't show live progress |
| **Live dashboard** | 25 | Rich information, live updates | Requires terminal that supports ANSI |
| **Incremental minimal** | 10 | Perfect for small updates | Different format for full vs incremental |

## Recommended Approach

### For Full Pipeline Runs: **Live Dashboard (25 lines)**
- Shows all stages simultaneously
- Updates in place (no scrolling)
- Rich information without clutter
- Professional appearance

### For Incremental Updates: **Ultra Minimal (10 lines)**
- Just what changed
- Total time
- Clear success/failure counts

### Implementation with Fallback

```python
def get_reporter(verbose=0, fancy=True):
    """Get appropriate reporter based on terminal capabilities."""
    try:
        if fancy and sys.stdout.isatty():
            # Try rich library for fancy output
            from rich.console import Console
            return RichReporter()
    except ImportError:
        pass

    if verbose > 0:
        return VerboseReporter()  # Traditional verbose output
    else:
        return MinimalReporter()  # Simple 8-line output

# Usage
reporter = get_reporter(verbose=args.verbose, fancy=not args.no_fancy)
```

## Benefits of Minimal Approach

1. **Entire pipeline visible at once** - No scrolling needed
2. **Live updates** - See progress without spam
3. **Clean logs** - When piped to file, shows clean output
4. **Responsive** - Updates in place, no terminal flooding
5. **Informative** - Still shows success/failure/time
6. **Scalable** - Same 8-25 lines whether processing 50 or 5000 papers

## Example: Full Pipeline in 25 Lines

```
╔══════════════════════════════════════════════════════════════════╗
║                    V5 PIPELINE PROCESSING                        ║
╠══════════════════════════════════════════════════════════════════╣
║ Papers: 2000 | Started: 10:45 | Elapsed: 1h 12m | ETA: 30m      ║
╚══════════════════════════════════════════════════════════════════╝

Stage         Progress              Success  Failed  Time
─────────────────────────────────────────────────────────────
CrossRef      ████████████████████  1950     50      4m32s   ✓
S2            ████████████████████  1980     20      1m15s   ✓
OpenAlex      ████████████████████  1960     40      3m45s   ✓
Unpaywall     ████████████████████  1990     10      2m20s   ✓
PubMed        ████████████████████  1850     150     6m10s   ✓
arXiv         ████████░░░░░░░░░░░░  250      1750    45m00s  ⟳
TEI           ░░░░░░░░░░░░░░░░░░░░  -        -       -       ⋯
PostProc      ░░░░░░░░░░░░░░░░░░░░  -        -       -       ⋯

[Current] arXiv: Processing paper 251/2000 (rate: 0.3/sec)
[Warning] Retry 2/3 for paper_12345: Connection timeout
[Info] Checkpoint saved at paper 250

Summary: 1h 12m elapsed | 89% success rate | 30m remaining
─────────────────────────────────────────────────────────────
Total output: 25 lines (updates in place)
```

## Conclusion

We can reduce output from **700+ lines to just 8-25 lines** by:
1. Using single-line progress bars per stage
2. Updating in place instead of appending
3. Showing only essential information
4. Using compact time formats
5. Eliminating redundant checkpoint messages

The key insight: **Update in place, don't append**. This gives us a live dashboard feel with minimal screen real estate.
