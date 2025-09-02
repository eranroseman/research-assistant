# Pipeline Output Volume Analysis for 2000 Papers

## Date: December 3, 2024

## Assumptions
- 2000 papers total
- Batch sizes per stage based on API limits
- Checkpoint saves every 500 papers for fast APIs, every 100 for medium, every 10 for slow
- ~5% failure rate per stage

## Output Lines Per Stage

### Stage 1: CrossRef Enrichment
```
Header:                     6 lines
Batch processing (500/batch = 4 batches):  8 lines (2 per batch)
Checkpoint saves (every 500 = 4 saves):    4 lines
Summary footer:             8 lines
----------------------------------------
Total:                     26 lines
```

### Stage 2: Semantic Scholar (S2) Enrichment
```
Header:                     6 lines
Skip report (if incremental): 2 lines
Batch processing (500/batch = 4 batches):  8 lines
Checkpoint saves (every 500 = 4 saves):    4 lines
Summary footer:             8 lines
----------------------------------------
Total:                     28 lines (26 if first run)
```

### Stage 3: OpenAlex Enrichment
```
Header:                     6 lines
Skip report (if incremental): 2 lines
Batch processing (50/batch = 40 batches): 80 lines
Checkpoint saves (every 500 = 4 saves):    4 lines
Summary footer:             8 lines
----------------------------------------
Total:                    100 lines (98 if first run)
```

### Stage 4: Unpaywall Enrichment
```
Header:                     6 lines
Skip report (if incremental): 2 lines
Batch processing (200/batch = 10 batches): 20 lines
Checkpoint saves (every 200 = 10 saves):   10 lines
Summary footer:             8 lines
----------------------------------------
Total:                     46 lines (44 if first run)
```

### Stage 5: PubMed Enrichment
```
Header:                     6 lines
Skip report (if incremental): 2 lines
Batch processing (100/batch = 20 batches): 40 lines
Checkpoint saves (every 100 = 20 saves):   20 lines
Summary footer:             8 lines
----------------------------------------
Total:                     76 lines (74 if first run)
```

### Stage 6: arXiv Enrichment (Individual Processing)
```
Header:                     6 lines
Skip report (if incremental): 2 lines
Progress updates (every 10 papers = 200):  200 lines*
Checkpoint saves (every 10 = 200 saves):   200 lines
Error messages (~100 papers not found):    100 lines
Summary footer:             8 lines
----------------------------------------
Total:                    516 lines (514 if first run)

* Note: Progress updates use \r carriage return,
  so only final line is visible, actual output: ~316 lines
```

### Stage 7: TEI Extraction (Local, Fast)
```
Header:                     6 lines
Progress bar (single line with \r):        1 line
Checkpoint saves (every 50 = 40 saves):   40 lines
Summary footer:             8 lines
----------------------------------------
Total:                     55 lines
```

### Stage 8: Post-Processing (Quality Scoring, Embeddings)
```
Header:                     6 lines
Skip report (if incremental): 2 lines
Progress bar with tqdm:     1 line (dynamic)
Checkpoint saves (every 50 = 40 saves):   40 lines
Quality filtering messages: ~20 lines
Embedding generation progress: 1 line (dynamic)
Summary footer:             8 lines
----------------------------------------
Total:                     78 lines (76 if first run)
```

## Total Output Volume

### First Run (Building from Scratch)
```
CrossRef:           26 lines
S2:                 26 lines
OpenAlex:           98 lines
Unpaywall:          44 lines
PubMed:             74 lines
arXiv:             316 lines (with \r compression)
TEI Extraction:     55 lines
Post-Processing:    76 lines
=====================================
TOTAL:             715 lines
```

### Incremental Run (All Already Processed)
```
CrossRef:           28 lines (with skip report)
S2:                 28 lines
OpenAlex:          100 lines
Unpaywall:          46 lines
PubMed:             76 lines
arXiv:             318 lines
TEI Extraction:     55 lines (local, always processes)
Post-Processing:    78 lines
=====================================
TOTAL:             729 lines
```

### Incremental Run (50 New Papers)
```
Each stage: ~15-20 lines (header + processing 1 batch + summary)
Total for 8 stages: ~140 lines
```

## Observations

### Verbose Stages
1. **arXiv**: 316 lines due to individual processing and frequent checkpoints
2. **OpenAlex**: 100 lines due to small batch size (50 papers)
3. **Post-Processing**: 78 lines with detailed progress

### Quiet Stages
1. **CrossRef**: 26 lines (large batches, few checkpoints)
2. **S2**: 26 lines (very efficient batch API)

### Mitigation Strategies

#### Option 1: Reduce Checkpoint Frequency
```
Fast APIs: Every 1000 instead of 500  (-50% checkpoint lines)
Medium APIs: Every 500 instead of 200  (-60% checkpoint lines)
Slow APIs: Every 50 instead of 10      (-80% checkpoint lines)

New Total: ~400 lines (down from 715)
```

#### Option 2: Compress Batch Reports
```
Instead of:
[10:45:23] Batch 1/5 (500 papers): Processing...
[10:45:28] Batch 1/5 (500 papers): ✓ 487 enriched, ✗ 13 failed

Single line:
[10:45:28] Batch 1/5: ✓ 487/500 enriched

Saves: ~200 lines total
New Total: ~500 lines
```

#### Option 3: Verbosity Levels
```python
# Add --verbose flag
parser.add_argument('--verbose', '-v', action='count', default=0,
                   help='Increase verbosity (-v, -vv, -vvv)')

# Verbosity levels:
# 0 (default): Headers + summaries only (~100 lines total)
# 1 (-v): Add batch progress (~300 lines)
# 2 (-vv): Add checkpoints (~500 lines)
# 3 (-vvv): Add individual progress + errors (~700 lines)
```

#### Option 4: Log to File, Summary to Console
```python
# Console (minimal):
STAGE 4: CROSSREF ENRICHMENT
Processing 2000 papers...
✓ Complete: 1950 enriched, 50 failed (4m 32s)

# Full details in crossref_enrichment.log
```

## Recommended Approach

### Default (Quiet) Mode: ~200 lines total
```
Each stage shows:
- Header (2 lines)
- Processing indicator (1 line)
- Summary (2 lines)
Total per stage: 5 lines × 8 stages = 40 lines

Plus key milestones:
- Major checkpoints every 1000 papers: 16 lines
- Errors/warnings: ~50 lines
- Final summary: 10 lines

Total: ~120-200 lines
```

### Verbose Mode (-v): ~700 lines
Full output as calculated above

### Example Implementation
```python
class ProgressReporter:
    def __init__(self, stage_name: str, verbosity: int = 0):
        self.verbosity = verbosity

    def batch_complete(self, ...):
        if self.verbosity >= 1:  # Only show in verbose mode
            print(f"Batch {batch_num}/{total}: ✓ {succeeded} ✗ {failed}")

    def checkpoint_saved(self, count):
        if self.verbosity >= 2:  # Only in very verbose mode
            print(f"💾 Checkpoint saved: {count} papers")
```

## Conclusion

For 2000 papers:
- **Current approach**: 700+ lines (too verbose)
- **With verbosity control**: 120-200 lines default, 700+ with -v
- **Best practice**: Default quiet with option for verbosity
- **Alternative**: Log to file, minimal console output

The key is making the default experience clean (~200 lines) while preserving detailed output for debugging via verbosity flags or log files.
