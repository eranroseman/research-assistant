# Complete Extraction Pipeline Workflow Guide

## Overview

This document provides a complete, step-by-step workflow for the extraction pipeline, from initial setup to final knowledge base building. The pipeline now uses an organized directory structure with all outputs in a single `extraction_pipeline_YYYYMMDD/` directory.

## Visual Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     INPUT: 2,221 PDFs                        │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│   STAGE 1: Grobid Extraction (9.5 hours)                     │
│   • Two-pass strategy (90s + 180s timeouts)                  │
│   • 7 files per paper (TEI XML + 6 extracts)                 │
│   • Result: 2,210 extracted (99.5% success)                  │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│   STAGE 2: Full Text Recovery (Bug Fix)                      │
│   • Re-process TEI XML with p.itertext()                     │
│   • Recovers section content, not just titles                │
│   • Result: +83.8M characters recovered                      │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│   STAGE 3: Quality Filtering                                 │
│   • Remove abstract-only papers (3)                          │
│   • Remove empty papers (6)                                  │
│   • Remove papers without title AND DOI (30)                 │
│   • Result: 2,170 papers kept                                │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│   STAGE 4: CrossRef Enrichment                               │
│   • Recover missing titles via DOI lookup                    │
│   • Find missing DOIs via bibliographic search               │
│   • Result: 74/82 titles recovered (90.2%)                   │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│   STAGE 5: Non-Article Filtering                             │
│   • Remove supplemental materials (2)                        │
│   • Remove datasets (7)                                      │
│   • Remove editorials/comments (10)                          │
│   • Result: 2,151 research articles                          │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│   STAGE 6: Malformed DOI Cleaning                            │
│   • Clean DOIs with appended text                            │
│   • Retry CrossRef for remaining papers                      │
│   • Result: 4/5 additional titles recovered                  │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│   STAGE 7: Final Cleanup                                     │
│   • Remove last paper without title                          │
│   • Add to PDF quality report                                │
│   • Result: 2,150 articles (100% with titles)                │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              OUTPUT: 2,150 Research Articles                 │
│   • 100% title coverage                                      │
│   • 98.4% DOI coverage                                       │
│   • 83.8M characters of full text                            │
│   • Ready for KB building                                    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start Commands

### Option 1: Master Pipeline Runner (Recommended)
```bash
# Prerequisites
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full

# Run complete pipeline with organized structure
python extraction_pipeline_runner.py

# Or continue from a specific stage
python extraction_pipeline_runner.py \
  --pipeline-dir extraction_pipeline_20250901 \
  --start-from crossref

# Run specific stages only
python extraction_pipeline_runner.py \
  --pipeline-dir extraction_pipeline_20250901 \
  --start-from s2 \
  --stop-after openalex
```

### Option 2: Manual Step-by-Step with Organized Structure
```bash
# Create pipeline directory
mkdir -p extraction_pipeline_$(date +%Y%m%d)/{01_tei_xml,02_json_extraction,03_zotero_recovery,04_crossref_enrichment,05_s2_enrichment,06_openalex_enrichment,07_unpaywall_enrichment,08_pubmed_enrichment,09_arxiv_enrichment,10_final_output}

# Stage 1: TEI to JSON extraction
python comprehensive_tei_extractor.py \
  --output extraction_pipeline_20250901/02_json_extraction

# Stage 2: Zotero recovery
python run_full_zotero_recovery.py \
  --input extraction_pipeline_20250901/02_json_extraction \
  --output extraction_pipeline_20250901/03_zotero_recovery

# Stage 3: CrossRef batch enrichment
python crossref_batch_enrichment.py \
  --input extraction_pipeline_20250901/03_zotero_recovery \
  --output extraction_pipeline_20250901/04_crossref_enrichment \
  --batch-size 50

# Stage 4: S2 enrichment
python s2_batch_enrichment.py \
  --input extraction_pipeline_20250901/04_crossref_enrichment \
  --output extraction_pipeline_20250901/05_s2_enrichment

# Stage 5: Extended API enrichments
python v5_openalex_pipeline.py \
  --input extraction_pipeline_20250901/05_s2_enrichment \
  --output extraction_pipeline_20250901/06_openalex_enrichment

# Build KB
python src/build_kb.py --input kb_final_cleaned_*/
```

## Prerequisites Checklist

### System Requirements
- [ ] Python 3.11+
- [ ] Docker installed and running
- [ ] 10GB free disk space
- [ ] 8GB RAM (4GB minimum)
- [ ] Internet connection for CrossRef API

### Software Setup
```bash
# Install requirements
pip install -r requirements.txt
pip install -r requirements_grobid.txt

# Start Grobid
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full

# Verify Grobid
curl http://localhost:8070/api/isalive
```

### Zotero Setup
- [ ] Zotero running
- [ ] PDF files attached to references
- [ ] Sync completed

## Stage Details

### Stage 1: Grobid Extraction
**Time**: ~9.5 hours for 2,200 papers
**Success Rate**: 99.5% for research papers

```python
# What happens:
- Connects to Zotero library
- Extracts each PDF with Grobid
- Two-pass strategy (90s first, 180s retry)
- Saves 7 files per paper
- Creates checkpoint for resume

# Output:
zotero_extraction_TIMESTAMP/
├── tei_xml/       # Full TEI XML
├── json/          # Extracted data
├── headers/       # Title, authors
├── figures/       # Figure metadata
├── citations/     # Reference parsing
├── fulltext/      # Section extraction
└── checkpoint.json
```

### Stage 2: Full Text Recovery
**Time**: ~30 minutes
**Impact**: Recovers 83.8M characters

```python
# What happens:
- Reads TEI XML files
- Extracts full paragraph text (not just titles)
- Updates JSON files with complete content

# Key fix:
for p in div.findall('tei:p', ns):
    text = ' '.join(p.itertext()).strip()  # Gets all text, not just direct
```

### Stage 3: Quality Filtering
**Time**: ~5 minutes
**Filters**: 42 papers (1.9%)

```python
# Exclusion criteria:
- Abstract-only (no full text): 3 papers
- No content at all: 6 papers
- Text < 1000 chars: 3 papers
- Missing BOTH title AND DOI: 30 papers

# Important: Papers with DOI but no title are KEPT for recovery
```

### Stage 4: CrossRef Enrichment
**Time**: ~20 minutes (with API delays)
**Success**: 90.2% title recovery

```python
# What happens:
- For papers missing titles: DOI lookup
- For papers missing DOIs: Bibliographic search
- Updates metadata with found information

# API usage:
- Rate limited to 0.2s between requests
- Polite pool with email header
```

### Stage 5: Non-Article Filtering
**Time**: ~2 minutes
**Removes**: 19 non-articles

```python
# Detected patterns:
- Supplemental materials: "suppl", "supplement"
- Datasets: figshare.com, osf.io, zenodo.org
- Editorials: "editorial", "comment", "reply"
```

### Stage 6: DOI Cleaning
**Time**: ~2 minutes
**Recovers**: 4/5 titles

```python
# Malformed DOI patterns fixed:
- "10.1234/abc.pdf" → "10.1234/abc"
- "10.1234/abcREvIEWS" → "10.1234/abc"
- "10.1234/abc." → "10.1234/abc"
```

### Stage 7: Final Cleanup
**Time**: ~1 minute
**Result**: 100% title coverage

```python
# What happens:
- Identifies remaining paper without title
- Moves to PDF quality report
- Creates final clean directory
```

## Output Structure

### Final Directory
```
kb_final_cleaned_TIMESTAMP/
├── *.json                    # 2,150 article files
├── pdf_quality_report.json   # Excluded papers
└── extraction_summary.md     # Statistics
```

### JSON Structure per Paper
```json
{
  "paper_id": "ABCD1234",
  "title": "Paper Title",
  "doi": "10.1234/example",
  "authors": ["Author 1", "Author 2"],
  "year": 2023,
  "abstract": "Abstract text...",
  "sections": [
    {
      "title": "Introduction",
      "text": "Full section text..."
    }
  ],
  "references": [...],
  "entities": {
    "sample_sizes": ["n=500"],
    "p_values": ["p<0.001"],
    "software": ["Python", "R"]
  }
}
```

## Validation Commands

### Check Extraction Quality
```bash
python analyze_grobid_extraction.py
```

### Verify Final Statistics
```python
import json
from pathlib import Path

kb_dir = Path('kb_final_cleaned_*')
files = list(kb_dir.glob('*.json'))
print(f"Total articles: {len(files) - 1}")  # -1 for report

# Check title coverage
missing_titles = 0
for f in files:
    if 'report' not in f.name:
        with open(f) as file:
            data = json.load(file)
            if not data.get('title'):
                missing_titles += 1
print(f"Title coverage: {100 - (missing_titles/len(files)*100):.1f}%")
```

## Time Estimates

| Stage | Papers | Time | Per Paper |
|-------|--------|------|-----------|
| Grobid Extraction | 2,221 | 9.5 hours | 15.4s |
| Text Recovery | 2,203 | 30 min | 0.8s |
| Quality Filter | 2,203 | 5 min | 0.1s |
| CrossRef | 261 | 20 min | 4.6s |
| Non-Article Filter | 2,170 | 2 min | 0.05s |
| DOI Cleaning | 5 | 2 min | 24s |
| Final Cleanup | 2,151 | 1 min | 0.03s |
| **Total** | **2,221→2,150** | **~10.5 hours** | **17s avg** |

## Common Issues

### If Extraction Fails
```bash
# Check Grobid
curl http://localhost:8070/api/isalive

# Check last checkpoint
cat zotero_extraction_*/checkpoint.json

# Resume from checkpoint
python v5_design/implementations/extract_zotero_library.py
```

### If Pipeline Stops
```bash
# Resume with consolidated script
python v5_extraction_pipeline.py --skip-extraction

# Or continue manually from last completed stage
```

### If Quality is Poor
```bash
# Analyze what went wrong
python analyze_grobid_extraction.py

# Check error logs
ls zotero_extraction_*/errors/

# Review sample papers
python -c "
import json
import random
from pathlib import Path

for f in random.sample(list(Path('kb_final_cleaned_*').glob('*.json')), 5):
    with open(f) as file:
        d = json.load(file)
        print(f\"{f.name}: {d.get('title', 'NO TITLE')[:50]}...\")
"
```

## Best Practices

1. **Run overnight**: Use `caffeinate` (Mac) or `systemd-inhibit` (Linux)
2. **Monitor progress**: Check `checkpoint.json` periodically
3. **Keep logs**: Save terminal output for debugging
4. **Validate results**: Always run `analyze_grobid_extraction.py`
5. **Backup final KB**: Copy `kb_final_cleaned_*` before building

## Next Steps

After successful extraction:

```bash
# Build the knowledge base
python src/build_kb.py --input kb_final_cleaned_*/

# Test the KB
python src/cli.py search "machine learning" --show-quality

# Run gap analysis
python src/analyze_gaps.py
```

## Support Resources

- **Troubleshooting**: See [07_troubleshooting.md](07_troubleshooting.md)
- **Technical details**: See [02_grobid_extraction.md](02_grobid_extraction.md)
- **Post-processing**: See [03_post_processing.md](03_post_processing.md)
- **Results analysis**: See [09_final_pipeline_results.md](09_final_pipeline_results.md)
