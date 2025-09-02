# Logging vs Display Strategy for V5 Pipeline

## Date: December 3, 2024

## Current State
- Most stages use `print()` for everything
- Some use `logger.info()` but inconsistently
- No separation between user display and diagnostic logging
- Verbose output makes it hard to tail log files

## Proposed Dual-Output Strategy

### 1. Screen Display (Interactive)
**Purpose**: Real-time progress for human monitoring
**Content**: 40-line dashboard that updates in place
**Level**: Only essential information

### 2. Log Files (Diagnostic)
**Purpose**: Debugging, audit trail, post-mortem analysis
**Content**: Detailed operations, API responses, errors
**Level**: Everything that might be useful later

## Implementation Design

```python
import logging
from pathlib import Path
from datetime import datetime

class PipelineLogger:
    """Separate logging from display."""

    def __init__(self, stage_name: str, log_dir: Path = Path("logs")):
        self.stage_name = stage_name
        self.log_dir = log_dir
        self.log_dir.mkdir(exist_ok=True)

        # Create stage-specific log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"{stage_name}_{timestamp}.log"

        # File logger - EVERYTHING goes here
        self.file_logger = logging.getLogger(f"{stage_name}_file")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.file_logger.addHandler(file_handler)
        self.file_logger.setLevel(logging.DEBUG)

        # Console logger - Only important stuff
        self.console_logger = logging.getLogger(f"{stage_name}_console")
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('[%(name)s] %(message)s')
        )
        self.console_logger.addHandler(console_handler)
        self.console_logger.setLevel(logging.INFO)

        # Master log file for all stages
        master_log = self.log_dir / f"pipeline_{timestamp}.log"
        self.master_logger = logging.getLogger("pipeline")
        master_handler = logging.FileHandler(master_log, mode='a')
        master_handler.setFormatter(
            logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
        )
        self.master_logger.addHandler(master_handler)
        self.master_logger.setLevel(logging.INFO)
```

## Log File Structure

```
logs/
├── pipeline_20241203_104500.log          # Master log (all stages)
├── crossref_20241203_104500.log          # Stage-specific detailed log
├── s2_20241203_104515.log
├── openalex_20241203_104530.log
├── unpaywall_20241203_104545.log
├── pubmed_20241203_104600.log
├── arxiv_20241203_104615.log
├── tei_20241203_105100.log
└── postprocessing_20241203_105130.log
```

## What Goes Where

### Screen Display Only
- Progress bars
- Current file being processed
- Success/failure counts
- ETA and elapsed time
- Recent important events (last 5)

### Log File Only
- API request/response details
- Full error stack traces
- Checkpoint save details
- Individual paper processing details
- Retry attempts with full context
- Performance metrics
- Memory/CPU usage

### Both (Different Formats)
| Event | Screen | Log File |
|-------|--------|----------|
| **Success** | `✓ paper_123` | `INFO: Successfully enriched paper_123 with 15 fields from CrossRef` |
| **Failure** | `✗ paper_456` | `ERROR: Failed paper_456: DOI not found (404) after 3 retries` |
| **Checkpoint** | `💾 1000` | `INFO: Checkpoint saved: 1000 papers, file: checkpoint_1000.json` |
| **API Error** | `⚠ Retry 2/3` | `WARNING: API timeout for paper_789, attempt 2/3, waiting 5s` |

## Example Implementation

```python
# In crossref_enricher.py
class CrossRefEnricher:
    def __init__(self):
        self.logger = PipelineLogger("crossref")
        self.display = PipelineDashboard("crossref")

    def process_paper(self, paper):
        paper_id = paper['paper_id']

        # Log detailed info
        self.logger.file_logger.debug(f"Processing paper {paper_id}: {paper}")

        try:
            # Make API call
            self.logger.file_logger.debug(f"Querying CrossRef for DOI: {paper['doi']}")
            result = self.api_call(paper['doi'])
            self.logger.file_logger.debug(f"CrossRef response: {result}")

            # Update display (minimal)
            self.display.update_progress(current=self.processed, total=self.total)

            # Log success
            self.logger.file_logger.info(f"Enriched {paper_id} with {len(result)} fields")
            self.logger.master_logger.info(f"[CrossRef] ✓ {paper_id}")

            return result

        except Exception as e:
            # Detailed error to log
            self.logger.file_logger.error(
                f"Failed to process {paper_id}: {e}",
                exc_info=True  # Full stack trace
            )

            # Simple error to screen
            self.display.add_event(f"✗ {paper_id}")

            # Summary to master log
            self.logger.master_logger.error(f"[CrossRef] ✗ {paper_id}: {str(e)[:50]}")
```

## Log File Examples

### Master Pipeline Log (pipeline_20241203_104500.log)
```
2024-12-03 10:45:00 - [pipeline] - INFO - Starting V5 pipeline with 2000 papers
2024-12-03 10:45:00 - [crossref] - INFO - Starting CrossRef enrichment
2024-12-03 10:45:05 - [crossref] - INFO - [CrossRef] ✓ paper_001
2024-12-03 10:45:06 - [crossref] - INFO - [CrossRef] ✓ paper_002
2024-12-03 10:45:07 - [crossref] - ERROR - [CrossRef] ✗ paper_003: DOI not found
2024-12-03 10:49:32 - [crossref] - INFO - CrossRef complete: 1950/2000 enriched
2024-12-03 10:49:33 - [s2] - INFO - Starting S2 enrichment
...
```

### Stage-Specific Log (crossref_20241203_104500.log)
```
2024-12-03 10:45:00 - DEBUG - Loading papers from input directory
2024-12-03 10:45:00 - DEBUG - Found 2000 JSON files
2024-12-03 10:45:00 - INFO - Starting batch 1/4 (500 papers)
2024-12-03 10:45:05 - DEBUG - Processing paper_001: {'doi': '10.1234/test', 'title': '...'}
2024-12-03 10:45:05 - DEBUG - Querying CrossRef API: https://api.crossref.org/works/10.1234/test
2024-12-03 10:45:05 - DEBUG - Response status: 200, size: 4567 bytes
2024-12-03 10:45:05 - DEBUG - Extracted fields: ['title', 'authors', 'venue', ...]
2024-12-03 10:45:05 - INFO - Successfully enriched paper_001 with 25 fields
...
```

## Log Rotation and Management

```python
# Configure log rotation
from logging.handlers import RotatingFileHandler

def setup_rotating_logs():
    handler = RotatingFileHandler(
        'logs/pipeline.log',
        maxBytes=100_000_000,  # 100MB per file
        backupCount=10  # Keep 10 old versions
    )

# Cleanup old logs
def cleanup_old_logs(days=30):
    """Remove logs older than N days."""
    import os
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(days=days)
    for log_file in Path("logs").glob("*.log"):
        if datetime.fromtimestamp(os.path.getmtime(log_file)) < cutoff:
            log_file.unlink()
```

## Benefits of Dual Approach

### For Users
1. **Clean display** - Just see what matters now
2. **No scrolling** - 40-line dashboard updates in place
3. **Quick status** - Instantly see if things are working
4. **Professional** - Looks polished, not spammy

### For Debugging
1. **Complete history** - Everything is in the logs
2. **Searchable** - grep through logs for specific papers
3. **Post-mortem** - Analyze failures after the fact
4. **API debugging** - Full request/response for troubleshooting

### For Operations
1. **Monitoring** - Tail master log for high-level view
2. **Alerting** - Watch for ERROR/WARNING in logs
3. **Metrics** - Parse logs for performance analysis
4. **Audit trail** - Complete record of what was processed

## Log Analysis Tools

```bash
# See all failures across all stages
grep "ERROR" logs/pipeline_*.log | grep "✗"

# Count successes per stage
grep "✓" logs/pipeline_*.log | awk '{print $4}' | sort | uniq -c

# Find slow papers (took >10s)
grep "Processing time:" logs/*_*.log | awk '$3 > 10'

# Extract API error patterns
grep "API.*error" logs/*.log | cut -d: -f4- | sort | uniq -c | sort -rn

# Monitor in real-time
tail -f logs/pipeline_*.log | grep -E "(ERROR|WARNING|✓|✗)"
```

## Configuration via Environment/Args

```python
# Control logging verbosity
parser.add_argument('--log-level',
                   choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                   default='INFO',
                   help='Log file verbosity')

parser.add_argument('--quiet', action='store_true',
                   help='Minimal console output')

parser.add_argument('--no-log', action='store_true',
                   help='Disable file logging')

parser.add_argument('--log-dir', default='logs',
                   help='Directory for log files')
```

## Summary

The optimal approach is:

1. **Screen**: Clean 40-line dashboard that updates in place
2. **Logs**: Detailed file logs for everything
3. **Master log**: High-level timeline across all stages
4. **Stage logs**: Deep dive into specific stage issues

This gives users a clean, professional experience while preserving all diagnostic information for when things go wrong.
