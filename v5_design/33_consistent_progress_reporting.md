# Consistent Progress Reporting Format for V5 Pipeline

## Date: December 3, 2024

## Current State

Each enrichment stage reports progress differently:
- Some use `print()`, others use `logger.info()`
- Different formats for similar information
- Inconsistent verbosity levels
- No standard for batch progress, errors, or completion

## Proposed Standard Format

### 1. Stage Header (Start of Processing)
```
================================================================================
STAGE 4: CROSSREF ENRICHMENT
================================================================================
Input:    crossref_input/          [2,205 papers]
Output:   crossref_enriched/
Settings: Batch size: 500 | Rate limit: 0.1s | Force: No
--------------------------------------------------------------------------------
```

### 2. Progress Updates (During Processing)

#### For Batch Processing
```
[10:45:23] Batch 1/5 (500 papers): Processing...
[10:45:28] Batch 1/5 (500 papers): ✓ 487 enriched, ✗ 13 failed
[10:45:33] Batch 2/5 (500 papers): Processing...
[10:45:38] Batch 2/5 (500 papers): ✓ 492 enriched, ✗ 8 failed
```

#### For Individual Processing
```
[10:45:23] Processing papers: 245/2205 (11.1%) | ✓ 230 | ✗ 15 | ETA: 4.2 min
```

#### For Skipped Papers (Incremental Mode)
```
[10:45:20] Skipping already enriched: 2,150 papers
[10:45:20] Processing new papers: 55
```

### 3. Error Reporting (When Issues Occur)
```
[10:45:35] ⚠ API Error (paper_12345): 429 Too Many Requests - retrying in 5s
[10:45:40] ✗ Failed (paper_12345): Invalid DOI format after 3 retries
```

### 4. Checkpoint Saves
```
[10:45:45] 💾 Checkpoint saved: 1,000 papers processed
```

### 5. Stage Footer (Completion)
```
--------------------------------------------------------------------------------
SUMMARY: CROSSREF ENRICHMENT COMPLETE
--------------------------------------------------------------------------------
✓ Enriched:     2,187 papers (99.2%)
✗ Failed:          18 papers (0.8%)
⏱ Time:         4 min 32 sec
📊 Rate:         8.1 papers/sec
💾 Output:       crossref_enriched/
📝 Report:       crossref_enrichment_report.json
================================================================================
```

## Implementation as Utility Class

Add to `pipeline_utils.py`:

```python
import sys
from datetime import datetime
from typing import Optional, Any

class ProgressReporter:
    """Consistent progress reporting for pipeline stages."""

    def __init__(self, stage_name: str, stage_number: Optional[int] = None):
        self.stage_name = stage_name.upper()
        self.stage_number = stage_number
        self.start_time = None
        self.total_items = 0
        self.processed = 0
        self.succeeded = 0
        self.failed = 0

    def start(self, input_dir: str, output_dir: str, total_items: int, **settings):
        """Print stage header."""
        self.start_time = datetime.now()
        self.total_items = total_items

        header = f"STAGE {self.stage_number}: {self.stage_name}" if self.stage_number else self.stage_name

        print("=" * 80)
        print(header)
        print("=" * 80)
        print(f"Input:    {input_dir:<25} [{total_items:,} papers]")
        print(f"Output:   {output_dir:<25}")

        if settings:
            settings_str = " | ".join(f"{k}: {v}" for k, v in settings.items())
            print(f"Settings: {settings_str}")

        print("-" * 80)
        sys.stdout.flush()

    def batch_start(self, batch_num: int, total_batches: int, batch_size: int):
        """Report batch processing start."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] Batch {batch_num}/{total_batches} ({batch_size} papers): Processing...")
        sys.stdout.flush()

    def batch_complete(self, batch_num: int, total_batches: int, batch_size: int,
                      succeeded: int, failed: int):
        """Report batch completion."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.succeeded += succeeded
        self.failed += failed
        self.processed += batch_size

        print(f"[{timestamp}] Batch {batch_num}/{total_batches} ({batch_size} papers): "
              f"✓ {succeeded} enriched, ✗ {failed} failed")
        sys.stdout.flush()

    def progress(self, current: int, succeeded: int, failed: int):
        """Report individual progress with ETA."""
        self.processed = current
        self.succeeded = succeeded
        self.failed = failed

        timestamp = datetime.now().strftime("%H:%M:%S")
        percent = (current / self.total_items * 100) if self.total_items else 0

        if self.start_time and current > 0:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            rate = current / elapsed
            remaining = (self.total_items - current) / rate if rate > 0 else 0
            eta = format_time_estimate(remaining)

            print(f"\r[{timestamp}] Processing papers: {current}/{self.total_items} "
                  f"({percent:.1f}%) | ✓ {succeeded} | ✗ {failed} | ETA: {eta}",
                  end="")
        else:
            print(f"\r[{timestamp}] Processing papers: {current}/{self.total_items} "
                  f"({percent:.1f}%) | ✓ {succeeded} | ✗ {failed}",
                  end="")

        sys.stdout.flush()

    def skip_report(self, skipped: int, processing: int):
        """Report skipped papers in incremental mode."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] Skipping already enriched: {skipped:,} papers")
        print(f"[{timestamp}] Processing new papers: {processing:,}")
        sys.stdout.flush()

    def error(self, paper_id: str, error_msg: str, retry: bool = False):
        """Report an error."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if retry:
            print(f"\n[{timestamp}] ⚠ API Error ({paper_id}): {error_msg} - retrying...")
        else:
            print(f"\n[{timestamp}] ✗ Failed ({paper_id}): {error_msg}")
        sys.stdout.flush()

    def checkpoint_saved(self, count: int):
        """Report checkpoint save."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] 💾 Checkpoint saved: {count:,} papers processed")
        sys.stdout.flush()

    def complete(self, output_dir: str, report_file: Optional[str] = None):
        """Print stage footer with summary."""
        if not self.start_time:
            return

        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.processed / elapsed if elapsed > 0 else 0
        success_rate = (self.succeeded / self.processed * 100) if self.processed else 0

        print("\n" + "-" * 80)
        print(f"SUMMARY: {self.stage_name} COMPLETE")
        print("-" * 80)
        print(f"✓ Enriched:     {self.succeeded:,} papers ({success_rate:.1f}%)")
        print(f"✗ Failed:       {self.failed:,} papers ({100-success_rate:.1f}%)")
        print(f"⏱ Time:         {format_duration(elapsed)}")
        print(f"📊 Rate:         {rate:.1f} papers/sec")
        print(f"💾 Output:       {output_dir}")

        if report_file:
            print(f"📝 Report:       {report_file}")

        print("=" * 80)
        sys.stdout.flush()

def format_duration(seconds: float) -> str:
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{seconds:.0f} sec"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes} min {secs} sec"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours} hr {minutes} min"
```

## Usage Examples

### CrossRef Enricher
```python
from pipeline_utils import ProgressReporter

def main():
    reporter = ProgressReporter("CrossRef Enrichment", stage_number=4)

    # Start
    reporter.start(
        input_dir="crossref_input/",
        output_dir="crossref_enriched/",
        total_items=2205,
        batch_size=500,
        rate_limit="0.1s",
        force="No"
    )

    # Skip report (incremental mode)
    reporter.skip_report(skipped=2150, processing=55)

    # Batch processing
    for batch_num, batch in enumerate(batches, 1):
        reporter.batch_start(batch_num, total_batches, len(batch))

        results = process_batch(batch)

        reporter.batch_complete(
            batch_num, total_batches, len(batch),
            succeeded=results.succeeded,
            failed=results.failed
        )

    # Checkpoint
    reporter.checkpoint_saved(1000)

    # Complete
    reporter.complete("crossref_enriched/", "crossref_enrichment_report.json")
```

### ArXiv Enricher (Individual Processing)
```python
from pipeline_utils import ProgressReporter

def main():
    reporter = ProgressReporter("ArXiv Enrichment", stage_number=9)

    reporter.start(
        input_dir="arxiv_input/",
        output_dir="arxiv_enriched/",
        total_items=500,
        rate_limit="3s"
    )

    succeeded = 0
    failed = 0

    for i, paper in enumerate(papers, 1):
        try:
            result = enrich_paper(paper)
            if result:
                succeeded += 1
            else:
                failed += 1

            # Update progress every 10 papers
            if i % 10 == 0:
                reporter.progress(i, succeeded, failed)

        except Exception as e:
            reporter.error(paper['id'], str(e), retry=True)
            # Retry logic...

    reporter.complete("arxiv_enriched/")
```

## Benefits

1. **Consistency**: All stages look and feel the same
2. **Clarity**: Easy to see what's happening at a glance
3. **Debugging**: Timestamps and detailed error messages
4. **Professional**: Clean, organized output
5. **Flexible**: Works for batch and individual processing
6. **Progress Tracking**: ETA calculation built-in
7. **Incremental Support**: Clear reporting of skipped papers

## Migration Path

1. Add `ProgressReporter` to `pipeline_utils.py`
2. Update one enricher as example
3. Gradually migrate others as they're touched
4. No need for big-bang migration

## Alternative: Simple Functions

If a class feels too heavy, use simple functions:

```python
def print_stage_header(stage: str, input_dir: str, output_dir: str, total: int, **settings):
    """Print consistent stage header."""
    print("=" * 80)
    print(f"STAGE: {stage.upper()}")
    print("=" * 80)
    # ...

def print_progress(current: int, total: int, succeeded: int, failed: int):
    """Print progress line."""
    percent = (current / total * 100) if total else 0
    print(f"\rProcessing: {current}/{total} ({percent:.1f}%) | "
          f"✓ {succeeded} | ✗ {failed}", end="")

def print_summary(stage: str, succeeded: int, failed: int, elapsed: float):
    """Print stage summary."""
    print("-" * 80)
    print(f"SUMMARY: {stage.upper()} COMPLETE")
    # ...
```

## Console Colors (Optional)

For better visibility, could add colors:

```python
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Usage
print(f"{Colors.GREEN}✓ Enriched:{Colors.END} 2,187 papers")
print(f"{Colors.RED}✗ Failed:{Colors.END} 18 papers")
```

## Conclusion

A consistent progress reporting format makes the pipeline:
- **Easier to monitor** - See at a glance what's happening
- **Easier to debug** - Consistent timestamps and error formats
- **More professional** - Clean, organized output
- **More maintainable** - Single place to update format

The `ProgressReporter` class provides all common patterns while remaining flexible enough for different processing styles (batch vs individual).
