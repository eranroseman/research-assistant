# Extraction Pipeline - September 1, 2025

## Directory Structure

This directory contains all outputs from the paper extraction and enrichment pipeline, organized by processing stage:

```
extraction_pipeline_20250901/
├── 01_tei_xml/           # GROBID TEI XML output (2,210 files)
├── 02_json_extraction/   # Comprehensive TEI → JSON extraction (2,210 files)
├── 03_zotero_recovery/   # Zotero metadata recovery (2,211 files)
├── 04_crossref_enrichment/ # CrossRef batch enrichment (101 files - test run)
├── 05_s2_enrichment/     # Semantic Scholar enrichment (pending)
├── 06_openalex_enrichment/ # OpenAlex enrichment (pending)
├── 07_unpaywall_enrichment/ # Unpaywall OA discovery (pending)
├── 08_pubmed_enrichment/ # PubMed biomedical enrichment (pending)
├── 09_arxiv_enrichment/  # arXiv preprint tracking (pending)
└── 10_final_output/      # Final merged and validated output (pending)
```

## Pipeline Stages

### Stage 1: GROBID Extraction
- **Input**: PDF files from Zotero
- **Output**: `01_tei_xml/*.xml`
- **Tool**: GROBID v0.8.2
- **Status**: ✅ Complete (2,210 files)

### Stage 2: TEI to JSON Extraction
- **Input**: `01_tei_xml/*.xml`
- **Output**: `02_json_extraction/*.json`
- **Script**: `comprehensive_tei_extractor.py`
- **Status**: ✅ Complete (2,210 files)
- **Coverage**: 97.4% year, 98.7% DOI, 98.5% title

### Stage 3: Zotero Recovery
- **Input**: `02_json_extraction/*.json`
- **Output**: `03_zotero_recovery/*.json`
- **Script**: `run_full_zotero_recovery.py`
- **Status**: ✅ Complete (2,211 files)
- **Recovery Rate**: 90.9% (2,008 papers improved)

### Stage 4: CrossRef Enrichment
- **Input**: `03_zotero_recovery/*.json`
- **Output**: `04_crossref_enrichment/*.json`
- **Script**: `crossref_batch_enrichment.py` (batch, 50x faster)
- **Status**: ⚠️ Test run only (101 files)
- **TODO**: Run full dataset

### Stage 5: Semantic Scholar Enrichment
- **Input**: `04_crossref_enrichment/*.json`
- **Output**: `05_s2_enrichment/*.json`
- **Script**: `s2_batch_enrichment.py`
- **Status**: ⏳ Pending

### Stage 6-9: Extended API Enrichment
- **OpenAlex**: Topics, SDGs, institutions
- **Unpaywall**: Open access status and links
- **PubMed**: MeSH terms, clinical metadata
- **arXiv**: Preprint versions and updates
- **Status**: ⏳ Pending

### Stage 10: Final Output
- **Input**: All enrichment stages
- **Output**: `10_final_output/*.json`
- **Process**: Merge, validate, and deduplicate
- **Status**: ⏳ Pending

## Data Flow

Each paper maintains the same filename (paper ID) through all stages:
```
Example: Paper "22FYFR7M"
01_tei_xml/22FYFR7M.xml
  ↓
02_json_extraction/22FYFR7M.json (22 fields)
  ↓
03_zotero_recovery/22FYFR7M.json (26 fields)
  ↓
04_crossref_enrichment/22FYFR7M.json (50+ fields)
  ↓
... (additional enrichments)
  ↓
10_final_output/22FYFR7M.json (100+ fields)
```

## Running the Pipeline

```bash
# Complete the CrossRef enrichment (full dataset)
python crossref_batch_enrichment.py \
  --input v5_pipeline_20250901/03_zotero_recovery \
  --output v5_pipeline_20250901/04_crossref_enrichment \
  --batch-size 50

# Run S2 enrichment
python s2_batch_enrichment.py \
  --input v5_pipeline_20250901/04_crossref_enrichment \
  --output v5_pipeline_20250901/05_s2_enrichment

# Continue with extended APIs...
```

## Statistics

- **Total papers**: 2,210
- **Successfully extracted**: 2,210 (100%)
- **Zotero recovered**: 2,008 (90.9%)
- **CrossRef enriched**: 101 (test run - need to complete)
- **Final expected**: ~2,150 (after quality filtering)

## Notes

- Each enrichment stage preserves all previous data and adds new fields
- JSON files grow progressively: ~5KB → ~10KB → ~20KB → ~50KB
- Total pipeline time: ~2-3 hours for all stages
- Storage requirement: ~500MB for complete pipeline
