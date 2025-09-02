# Research Assistant v5.0

Advanced literature extraction and enrichment pipeline with GROBID TEI processing and multi-source metadata enrichment.

## Project Status
- ✅ Type annotations complete (mypy passing)
- ✅ Code formatting standardized (ruff/black)
- ✅ Configuration centralized (src/config.py)
- ✅ Checkpoint recovery implemented
- 📊 ~85% extraction success rate

## Quick Start

```bash
# Setup
pip install -r requirements.txt

# Start GROBID server (required)
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.7.3

# V5 Pipeline - Full extraction and enrichment
python src/extraction_pipeline_runner_checkpoint.py  # Complete pipeline with checkpoints

# Or run individual stages
python src/crossref_batch_enrichment_checkpoint.py  # DOI metadata
python src/openalex_enricher.py                     # OpenAlex enrichment
python src/s2_batch_enrichment.py                   # Semantic Scholar
python src/v5_unpaywall_pipeline.py                 # Open access status
python src/pubmed_enricher.py                       # PubMed biomedical
python src/arxiv_enricher.py                        # arXiv preprints
```

## Architecture Overview

```text
Zotero Library → GROBID Server → TEI XML → JSON Extraction
                                     ↓
         CrossRef/S2/OpenAlex/Unpaywall → Enriched Metadata
                                     ↓
                        Final Quality-Filtered Dataset

extraction_pipeline/
├── 01_tei_xml/        # GROBID TEI XML (2,210 papers, ~10 hours)
├── 02_json_extraction/
├── 03_zotero_recovery/
├── 04_crossref_enrichment/
├── 05_s2_enrichment/
├── 06_openalex_enrichment/
├── 07_unpaywall_enrichment/
├── 08_pubmed_enrichment/
├── 09_arxiv_enrichment/
└── 10_final_output/
```

## Key Features

| Feature | Description |
|---------|------------|
| **GROBID Processing** | Full-text extraction with TEI XML structure preservation |
| **Multi-API Enrichment** | CrossRef, S2, OpenAlex, Unpaywall, PubMed, arXiv |
| **Checkpoint Recovery** | Resume from any stage after interruption |
| **Quality Filtering** | Automatic removal of non-articles, duplicates |
| **Batch Processing** | Efficient API calls with rate limiting |
| **Completeness Analysis** | Track extraction success rates per stage |

## V5 Pipeline Commands

### Core Extraction

```bash
# Extract from Zotero and process with GROBID
python src/extract_zotero_library.py
python src/grobid_overnight_runner.py --input pdfs/ --output tei_xml/

# Post-process TEI XML to JSON
python src/comprehensive_tei_extractor.py
python src/grobid_post_processor.py
```

### Enrichment Pipeline

```bash
# Run complete enrichment with checkpoints
python src/extraction_pipeline_runner_checkpoint.py

# Individual enrichment stages
python src/crossref_batch_enrichment_checkpoint.py
python src/s2_batch_enrichment.py
python src/openalex_enricher.py
python src/v5_unpaywall_pipeline.py
python src/pubmed_enricher.py
python src/v5_arxiv_pipeline.py
```

### Analysis & Cleanup

```bash
# Analyze pipeline completeness
python src/analyze_pipeline_completeness.py

# Identify and fix problematic papers
python src/analyze_problematic_papers.py
python src/analyze_failed_papers.py

# Quality filtering
python src/filter_non_articles.py
python src/final_cleanup_no_title.py
```

## Development

```bash
# Type checking (all passing)
mypy src/

# Code formatting & linting
ruff check src/ --fix
black src/

# Pre-commit hooks
pre-commit run --all-files

# Tests (v4 tests preserved)
pytest v4/tests/ -v
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| GROBID connection | `docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.7.3` |
| TEI extraction fails | Use `comprehensive_tei_extractor_checkpoint.py` for recovery |
| API rate limits | Built-in delays: CrossRef 0.5s, arXiv 3s, OpenAlex polite pool |
| Missing DOIs | Run `recover_dois_crossref.py` or `fix_malformed_dois.py` |
| Checkpoint recovery | Auto-resumes from `extraction_pipeline/*_checkpoint.json` |
| Memory issues | Batch size configurable in `src/config.py` |
| Type errors | Run `mypy src/` - all issues resolved |

## Pipeline Performance

| Stage | Time | Success Rate | Notes |
|-------|------|-------------|--------|
| **GROBID TEI** | ~10 hours | 100% | 2,210 papers, parallelizable |
| **JSON Extraction** | ~30 min | 86% | Structure parsing |
| **CrossRef** | ~2 hours | 72% | DOI matching, 0.5s delay |
| **OpenAlex** | ~1 hour | 65% | Batch API, polite pool |
| **S2** | ~1.5 hours | 60% | Batch processing |
| **Unpaywall** | ~45 min | 55% | Open access data |
| **PubMed** | ~1 hour | 30% | Biomedical subset |
| **arXiv** | ~2 hours | 15% | STEM papers, 3s delay |
| **Total Pipeline** | ~15 hours | ~85% enriched | With checkpoints |

## Quality Metrics

- **Input**: 2,210 Zotero papers
- **TEI XML Generated**: 2,210 (100%)
- **Successfully Extracted**: ~1,900 (86%)
- **CrossRef Enriched**: ~1,600 (72%)
- **Final Filtered**: ~1,500 research articles

## System Requirements

- Python 3.11+
- GROBID server (Docker recommended)
- 16GB RAM recommended
- ~10GB disk space for full pipeline
- Internet for API enrichment

## Code Quality Standards

### Required for All Changes
```bash
# Before committing
mypy src/                    # Type checking
ruff check src/ --fix        # Linting
pre-commit run --all-files   # All hooks
```

### Import Organization
```python
# Standard library
import json
from pathlib import Path

# Third party
import requests
from typing import Any

# Local imports
from src import config
from src.pipeline_utils import clean_doi
```

### Error Handling Pattern
```python
try:
    result = api_call()
except requests.RequestException as e:
    logger.error(f"API failed: {e}")
    stats["errors"] += 1
    return None
```

## Important Conventions

### File Operations
- ALWAYS prefer editing existing files over creating new ones
- Use atomic writes for critical data (temp file + rename)
- Preserve existing data when enriching

### Coding Standards
- Type hints required (mypy must pass)
- Constants in `src/config.py`
- Logging via `PipelineLogger` class
- Checkpoint recovery for long operations

### Testing & Validation
- Run mypy before committing
- Use pre-commit hooks
- Test with small datasets first (`--max-papers 10`)
- Verify checkpoint recovery works

## Key Implementation Details

### Configuration (`src/config.py`)
- Centralized constants for all modules
- API rate limits and delays
- Batch sizes and thresholds
- File paths and directories

### Type Safety
- Full mypy type annotations
- `dict[str, Any]` for JSON data
- Proper error handling types
- No type errors (mypy passing)

### Checkpoint System
- Atomic writes with temp files
- Per-stage checkpoint files
- Automatic resume on interruption
- Progress tracking in JSON

### API Best Practices
- Exponential backoff retry
- Rate limiting per service
- Batch processing where available
- Polite pool headers (OpenAlex)
- Session reuse for efficiency

### Data Preservation
- TEI XML preserved (10 hours GROBID work)
- Incremental enrichment (no data loss)
- Each stage adds fields, preserves existing
- Version tracking for updates
