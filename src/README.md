# v5.0 Reference Implementations

This directory contains working implementations that were used to successfully extract 2,221 papers from the Zotero library. These serve as reference implementations for the v5.0 design.

## Files

### 1. extract_zotero_library.py
**The successful extraction script**
- Successfully extracted 2,210/2,221 papers (99.5% success rate)
- Processing time: 9.4 hours for 2,221 papers
- Uses consolidation=2 (biblio-glutton) for maximum enrichment
- Single-pass with 120s timeout per paper
- Checkpoint/resume capability every 50 papers
- Saves both TEI XML and JSON output

**Key features:**
- Automatic checkpoint recovery
- Progress tracking with estimated completion time
- Detailed statistics per paper (processing time, success/failure)
- Smart path resolution for Zotero storage

### 2. grobid_overnight_runner.py
**Overnight extraction with 7-file output strategy**
- Implements the "7-file output strategy" from v5 design
- Uses 300s timeout for complex papers
- Saves multiple output formats for maximum flexibility:
  1. TEI XML - Raw Grobid output
  2. Complete JSON - All extracted data
  3. Entities JSON - Just the entities
  4. Metadata JSON - Quick-access metadata
  5. Sections text - Full text by sections
  6. Coordinates JSON - Spatial analysis data
  7. Statistics JSON - Extraction metrics

**Philosophy:** Maximum data extraction since Grobid runs are infrequent

### 3. grobid_post_processor.py
**Post-processing pipeline for Grobid output**
- 631 lines of post-processing logic
- Implements case-insensitive section matching
- Content aggregation from subsections
- Statistical entity detection
- Paper classification (research vs non-research)

**Key improvements:**
- Recovers 44-49% more Results sections through case-insensitive matching
- Aggregates content from numbered subsections
- Detects hidden statistical results in non-standard sections

### 4. retry_all_failed.py
**Retry script for failed extractions**
- Successfully recovered 10/11 failed papers
- Implements basic two-tier strategy:
  - Header-only extraction for large files (>10MB)
  - Full extraction for smaller files
- Extended timeouts: 300s for headers, 600s for full
- Used to identify that most failures were books/proceedings

## Implementation Status vs v5 Design

### Implemented:
✅ Maximum extraction parameters (consolidation=2, all entities)
✅ Checkpoint/resume capability
✅ 7-file output strategy (in overnight_runner)
✅ Post-processing improvements
✅ Paper vs book classification

### Not Yet Implemented (from v5 design):
❌ Two-pass strategy (90s + 180s timeouts)
❌ Automatic book/proceedings filtering
❌ Semantic Scholar integration
❌ Multi-level embeddings
❌ Gap analysis integration

## Usage Examples

### Run full extraction:
```bash
# Start Grobid
sudo docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full

# Run extraction
python extract_zotero_library.py
```

### Run overnight extraction with 7-file output:
```bash
python grobid_overnight_runner.py
```

### Post-process existing Grobid output:
```bash
python grobid_post_processor.py --input grobid_output/ --output processed/
```

### Retry failed papers:
```bash
python retry_all_failed.py
```

## Performance Metrics (Actual Results)

Based on real extraction of 2,221 papers:

| Metric | Value |
|--------|-------|
| Total papers | 2,221 |
| Successfully extracted | 2,210 (99.5%) |
| Failed (books/corrupted) | 11 (0.5%) |
| Total time | 9.4 hours |
| Average time per paper | 14.8 seconds |
| Fastest paper | 1.0 seconds |
| Slowest paper | 113.6 seconds |

## Notes

1. These implementations use **single-pass extraction** with various timeouts (120s-600s), not the two-pass strategy (90s + 180s) proposed in v5 design.

2. The high success rate (99.5%) was achieved by **excluding books and proceedings**, which consistently failed extraction.

3. **Consolidation=2 (biblio-glutton)** adds only ~1 second overhead despite enriching citations and metadata significantly.

4. The **checkpoint system** saves every 50 papers, allowing safe interruption and resumption without data loss.

5. These scripts were tested on August 30-31, 2025, with Grobid 0.8.2-full running locally.
