# V5 Script Consolidation & Renaming - December 2024

## Overview

This document describes the script consolidation effort to simplify the v5 pipeline codebase by removing redundant scripts, creating unified versions with all features, and standardizing naming conventions.

## Date: 2024-12-02
## Updated: 2024-12-03 - Added clean naming convention without v5 prefix

## Scripts Consolidated

### 1. CrossRef Enrichment Scripts

#### Removed Scripts
- `crossref_enrichment.py` - Basic single-paper enrichment (redundant)
- `crossref_batch_enrichment.py` - Batch without checkpoint (superseded)
- `crossref_batch_enrichment_checkpoint.py` - Batch with checkpoint but basic fields only
- `crossref_enrichment_comprehensive.py` - Comprehensive fields but no batch/checkpoint
- `crossref_enrichment_with_validation.py` - Validation features (can be added if needed)

#### New Unified Script
**`crossref_enricher.py`** (was `crossref_v5_unified.py`) - Combines ALL features:
- ✅ Comprehensive field extraction (50+ fields)
- ✅ Batch processing for efficiency
- ✅ Checkpoint recovery support
- ✅ Funding DOI filtering (removes 10.13039/*)
- ✅ Title search fallback for missing DOIs
- ✅ Detailed statistics and reporting

#### Fields Extracted by Unified Script
- Basic: DOI, title, authors, year, journal, volume, issue, pages
- Enhanced: Abstract, keywords, subjects
- Author details: ORCID IDs, affiliations
- Metrics: Citation count, reference count
- Funding: Funders, grant numbers
- Clinical: Trial registrations
- Licensing: Open access status
- Dates: Published online/print, accepted, created
- Relations: Updates, versions
- Quality indicators: Peer review status

### 2. TEI Extraction Scripts

#### Removed Scripts
- `comprehensive_tei_extractor.py` - No checkpoint support (redundant)

#### Kept Script (Renamed)
**`tei_extractor.py`** (was `comprehensive_tei_extractor_checkpoint.py`) - Production version with:
- ✅ Full TEI XML to JSON extraction
- ✅ Checkpoint recovery support
- ✅ Processes 2000+ files reliably
- ✅ Saves progress every 50 files

### 3. Zotero Recovery Scripts

#### Removed Scripts
- `zotero_metadata_recovery.py` - Uses pyzotero library, requires API key

#### Kept Script (Renamed)
**`zotero_recovery.py`** (was `run_full_zotero_recovery.py`) - Uses local Zotero API:
- ✅ No authentication required
- ✅ Checkpoint support
- ✅ Faster (local API)
- ✅ Simpler setup

### 4. Extraction Pipeline Runners

#### Removed Scripts
- `extraction_pipeline_runner.py` - Basic version without synchronization
- `extraction_pipeline_runner_fixed.py` - Fixed version with synchronization but no checkpoint
- `v5_extraction_pipeline.py` - Class-based implementation with different workflow

#### Kept Script (Renamed)
**`pipeline_runner.py`** (was `extraction_pipeline_runner_checkpoint.py`) - Production version with:
- ✅ Full checkpoint support for all stages
- ✅ 8 enrichment stages (TEI, Zotero, CrossRef, S2, OpenAlex, Unpaywall, PubMed, arXiv)
- ✅ Stage completion monitoring
- ✅ Automatic resume after interruption
- ✅ Synchronous execution with timeouts

### 5. OpenAlex Enrichment Scripts

#### Removed Scripts
- `openalex_enricher.py` (old version) - Core library with OpenAlexEnricher class
- `v5_openalex_pipeline.py` - Pipeline wrapper that imported the enricher

#### New Unified Script
**`openalex_enricher.py`** (was `openalex_v5_unified.py`) - Single-file implementation with:
- ✅ Checkpoint recovery support
- ✅ Batch processing (50 papers per API call)
- ✅ Topic classification and SDG mapping
- ✅ Citation metrics and venue information
- ✅ Same pattern as other pipeline stages
- ✅ No unnecessary separation of concerns

## Utility Scripts Retained

These scripts serve specific purposes and were kept:

### CrossRef Utilities
- `explore_crossref_fields.py` - Development tool to discover available API fields
- `recover_dois_crossref.py` - Finds missing DOIs using title/author search

### Other Utilities
- `fix_malformed_dois.py` - Cleans malformed DOI strings
- `filter_non_articles.py` - Removes non-article content
- `final_cleanup_no_title.py` - Final quality check

## Benefits of Consolidation

### 1. Simplified Maintenance
- Fewer scripts to maintain
- Single source of truth for each operation
- Consistent coding patterns

### 2. Feature Completeness
- Unified scripts have ALL features from individual versions
- No need to choose between features
- Best practices incorporated

### 3. Production Ready
- All main scripts now have checkpoint support
- Comprehensive error handling
- Detailed progress reporting

### 4. Cleaner Pipeline
```bash
# Before: Multiple scripts for same task
crossref_enrichment.py OR
crossref_batch_enrichment.py OR
crossref_batch_enrichment_checkpoint.py OR
crossref_enrichment_comprehensive.py

# After: Single unified script
crossref_v5_unified.py
```

### 6. arXiv Enrichment Scripts

#### Removed Scripts
- `arxiv_enricher.py` (old version) - Core library with ArXivEnricher class
- `v5_arxiv_pipeline.py` - Pipeline wrapper that imported the enricher

#### New Unified Script
**`arxiv_enricher.py`** (was `arxiv_v5_unified.py`) - Single-file implementation with:
- ✅ Checkpoint recovery support
- ✅ Title and author-based search
- ✅ Category and version tracking
- ✅ Rate limiting (3-second delays)
- ✅ Same pattern as other pipeline stages

### 7. Other Enrichment Scripts Renamed

| Old Name | New Name | Description |
|----------|----------|-------------|
| `s2_batch_enrichment.py` | `semantic_scholar_enricher.py` | Semantic Scholar API |
| `v5_unpaywall_pipeline.py` | `unpaywall_enricher.py` | Open Access discovery |
| `v5_pubmed_pipeline.py` | `pubmed_enricher.py` | PubMed biomedical data |

## Final Naming Convention (December 3, 2024)

### Clean Service-First Pattern
All v5 pipeline scripts now follow a consistent naming pattern without version prefixes:

- **Extraction**: `tei_extractor.py`, `zotero_recovery.py`
- **Enrichment**: `[service]_enricher.py` (e.g., `crossref_enricher.py`)
- **Orchestration**: `pipeline_runner.py`

## Updated Pipeline Commands

### Core Pipeline
```bash
# 1. TEI Extraction (with checkpoint)
python src/tei_extractor.py \
    --input extraction_pipeline/01_tei_xml \
    --output extraction_pipeline/02_json_extraction

# 2. Zotero Recovery (local API, checkpoint)
python src/zotero_recovery.py \
    --input extraction_pipeline/02_json_extraction \
    --output extraction_pipeline/03_zotero_recovery

# 3. CrossRef Enrichment (comprehensive + checkpoint)
python src/crossref_enricher.py \
    --input extraction_pipeline/03_zotero_recovery \
    --output extraction_pipeline/04_crossref_enrichment \
    --email your.email@university.edu

# 4. Continue with other enrichment stages...
python src/semantic_scholar_enricher.py
python src/openalex_enricher.py
python src/unpaywall_enricher.py
python src/pubmed_enricher.py
python src/arxiv_enricher.py
```

### Resume from Checkpoint
All scripts automatically resume from their last checkpoint:
```bash
# Just run the same command - it will detect and load checkpoint
python src/crossref_enricher.py --input ... --output ...
```

### Reset Checkpoint
```bash
# TEI Extractor - delete checkpoint file
rm extraction_pipeline/02_json_extraction/.tei_extraction_checkpoint.json

# Zotero Recovery
python src/zotero_recovery.py --reset ...

# CrossRef and other enrichers
python src/crossref_enricher.py --reset ...
```

## Migration Guide

### For Existing Pipelines

Replace old script calls with new ones:

| Old Script | New Script | Notes |
|------------|------------|-------|
| `comprehensive_tei_extractor_checkpoint.py` | `tei_extractor.py` | Same functionality, cleaner name |
| `run_full_zotero_recovery.py` | `zotero_recovery.py` | Same functionality, cleaner name |
| `crossref_v5_unified.py` | `crossref_enricher.py` | Same functionality, cleaner name |
| `s2_batch_enrichment.py` | `semantic_scholar_enricher.py` | Same functionality, cleaner name |
| `openalex_v5_unified.py` | `openalex_enricher.py` | Consolidated single-file implementation |
| `v5_unpaywall_pipeline.py` | `unpaywall_enricher.py` | Same functionality, cleaner name |
| `v5_pubmed_pipeline.py` | `pubmed_enricher.py` | Same functionality, cleaner name |
| `arxiv_v5_unified.py` | `arxiv_enricher.py` | Consolidated single-file implementation |
| `extraction_pipeline_runner_checkpoint.py` | `pipeline_runner.py` | Same functionality, cleaner name |

### For New Installations

Use only the consolidated scripts listed above. Ignore any references to the removed scripts in older documentation.

## Testing

### Verify Consolidation
```bash
# Verify new clean-named scripts exist
ls src/tei_extractor.py
ls src/zotero_recovery.py
ls src/crossref_enricher.py
ls src/semantic_scholar_enricher.py
ls src/openalex_enricher.py
ls src/unpaywall_enricher.py
ls src/pubmed_enricher.py
ls src/arxiv_enricher.py
ls src/pipeline_runner.py
```

### Test Unified Scripts
```bash
# Test with small batch
python src/crossref_enricher.py \
    --input test_input \
    --output test_output \
    --max-papers 10

# Run full pipeline
python src/pipeline_runner.py
```

## Future Improvements

### Potential Next Steps
1. Create unified S2 enrichment script (combine batch + checkpoint)
2. Add checkpoint support to OpenAlex, PubMed, arXiv scripts
3. Create single `v5_pipeline.py` that runs all stages
4. Add parallel processing within checkpoint boundaries

### Design Principles for Future Scripts
1. Always include checkpoint support for long-running processes
2. Extract comprehensive data in single pass
3. Provide clear progress reporting
4. Include `--reset` flag for checkpoint clearing
5. Support `--max-papers` for testing
6. Save detailed statistics and reports

## Conclusion

The v5 script consolidation and renaming effort successfully:

1. **Reduced redundancy** - Eliminated multiple versions of the same functionality
2. **Unified implementations** - Created single-file implementations for OpenAlex and arXiv
3. **Standardized naming** - All scripts now follow clean, consistent patterns without version prefixes
4. **Improved maintainability** - Cleaner codebase with self-documenting names
5. **Preserved functionality** - All features retained with checkpoint support

The pipeline now uses professionally-named, production-ready scripts that are easier to understand, maintain, and extend.
