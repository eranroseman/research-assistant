# Research Assistant v5.0

Advanced literature extraction and enrichment pipeline with GROBID TEI processing and multi-source metadata enrichment.

## Quick Start

```bash
# Setup
pip install -r requirements.txt

# V5 Pipeline - Full extraction and enrichment
python src/v5_extraction_pipeline.py         # Main pipeline
python src/extraction_pipeline_runner_checkpoint.py  # With checkpoint recovery

# Enrichment tools
python src/crossref_batch_enrichment_checkpoint.py  # DOI metadata
python src/openalex_enricher.py              # OpenAlex enrichment
python src/v5_unpaywall_pipeline.py          # Open access status
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
mypy src/
ruff check src/ --fix
pytest tests/ -v  # Tests in v4/tests/
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| GROBID connection | Ensure GROBID server running on port 8070 |
| TEI extraction fails | Check XML validity, use `comprehensive_tei_extractor.py` |
| API rate limits | Adjust delays in enricher scripts |
| Missing DOIs | Run `recover_dois_crossref.py` |
| Checkpoint recovery | Check `*_checkpoint.json` files |
| Memory issues | Process in smaller batches |

## Pipeline Performance

- **TEI Extraction**: ~10 hours for 2,210 papers (GROBID)
- **JSON Processing**: ~30 minutes
- **CrossRef Enrichment**: ~2 hours with rate limiting
- **Full Pipeline**: ~15 hours total
- **Success Rate**: ~85% papers fully enriched

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

## Migration from v4

```bash
# V4 code and data preserved in v4/ directory
v4/
├── src/          # V4 source code
├── kb_data/      # V4 knowledge base
├── tests/        # V4 tests
└── docs/         # V4 documentation
```

## Notes

- **v5.0 Changes**: Complete rewrite with GROBID extraction, multi-API enrichment
- **Data Preservation**: TEI XML in `extraction_pipeline/01_tei_xml/` (10 hours work)
- **Checkpoint System**: Automatic recovery from any stage
- **API Best Practices**: Rate limiting, retry logic, batch processing
