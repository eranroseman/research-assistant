# Research Assistant v5.0 Design Documentation

## 📚 Documentation Structure

This directory contains the complete design documentation for Research Assistant v5.0, organized into focused, easy-to-navigate sections.

### Core Documents

1. **[01_overview.md](01_overview.md)** - System overview and architecture
   - What is v5.0 and why it matters
   - Three-system integration (Zotero + Grobid + Semantic Scholar)
   - Breaking changes from v4.6
   - Success metrics and goals

2. **[02_grobid_extraction.md](02_grobid_extraction.md)** - Grobid configuration and extraction strategy
   - Maximum extraction philosophy
   - Configuration parameters
   - Entity types extracted
   - 7-file output strategy
   - Performance expectations

3. **[03_post_processing.md](03_post_processing.md)** - Post-processing strategies
   - 5 critical fixes with proven impact
   - Paper classification system
   - Abstract recovery strategies
   - Section mapping improvements
   - Real-world performance metrics

4. **[04_implementation_guide.md](04_implementation_guide.md)** - Implementation details
   - Shared libraries architecture
   - Build process philosophy
   - Collection processing
   - Progress monitoring
   - Error recovery

5. **[05_commands_reference.md](05_commands_reference.md)** - Command reference
   - build.py - Knowledge base building
   - kbq.py - Knowledge base queries
   - discover.py - External paper discovery
   - gaps.py - Gap analysis
   - Migration from v4.6

6. **[06_installation_setup.md](06_installation_setup.md)** - Installation and setup
   - Prerequisites
   - System requirements
   - First build workflow
   - Basic troubleshooting

7. **[07_troubleshooting.md](07_troubleshooting.md)** - Comprehensive troubleshooting (NEW)
   - Common issues and solutions
   - Error messages explained
   - Best practices
   - Diagnostic commands

8. **[08_paper_filtering.md](08_paper_filtering.md)** - Paper filtering strategy (UPDATED Aug 31)
   - Research papers vs books/proceedings
   - Why v5 excludes books
   - Complete 7-stage filtering workflow
   - PDF quality report integration
   - Success rates by document type

9. **[09_final_pipeline_results.md](09_final_pipeline_results.md)** - Complete pipeline results (FINAL)
   - Full extraction results: 2,150 articles from 2,221 PDFs
   - Bug fixes and their impacts
   - 100% title coverage achieved (after final cleanup)
   - 7-stage pipeline with all scripts
   - Final statistics: 83.8M chars extracted

10. **[10_complete_workflow.md](10_complete_workflow.md)** - Step-by-step workflow guide
    - Visual pipeline flow diagram
    - Quick start commands
    - Stage-by-stage details
    - Time estimates and validation
    - Best practices

11. **[11_comprehensive_extraction_fix.md](11_comprehensive_extraction_fix.md)** - Critical metadata extraction fix (NEW Sep 1)
    - Root cause: 100% of papers missing year
    - Solution: Complete TEI XML extraction
    - Results: 97.4% year coverage, 92.8% journal coverage
    - Technical details and implementation

12. **[12_pipeline_architecture.md](12_pipeline_architecture.md)** - Complete pipeline architecture (NEW Sep 1)
    - Full pipeline: PDF → GROBID → XML → JSON → CrossRef → KB
    - Stage-by-stage statistics and coverage metrics
    - CrossRef enrichment: 35+ additional fields
    - Final coverage: >99% possible for all critical fields
    - Quality control and validation measures

13. **[13_quality_filtering_stage.md](13_quality_filtering_stage.md)** - Quality filtering and paper classification (NEW Sep 1)
    - Stage 4 of the pipeline: Removing problematic/non-research papers
    - 7-stage filtering process removing 71 papers (3.2%)
    - Document type classification (articles vs books/supplements/datasets)
    - Content sufficiency and metadata completeness checks
    - Final output: 2,150 clean research articles (96.8% success rate)

14. **[14_filtering_rationale.md](14_filtering_rationale.md)** - Detailed rationale for 7-stage filtering (NEW Sep 1)
    - Explains reasoning behind each filtering stage
    - Efficiency cascade: cheap filters first, expensive last
    - Real examples of filtered papers
    - Stage 4.5: Zotero recovery before metadata completeness check

15. **[15_zotero_integration.md](15_zotero_integration.md)** - Zotero metadata recovery implementation (NEW Sep 1)
    - Stage 3 of pipeline: Zero-cost metadata recovery
    - 90.9% recovery rate (2,008/2,210 papers improved)
    - Addresses GROBID's journal extraction weakness
    - Match strategies: DOI, title fuzzy matching
    - Performance: <5 seconds for entire library

16. **[16_s2_optimization_complete.md](16_s2_optimization_complete.md)** - S2 batch enrichment optimization (NEW Sep 1)
    - Achieved 93.7% enrichment rate (2,000/2,134 papers)
    - 426.8 papers per API call efficiency
    - Removed preemptive rate limiting
    - Added checkpoint recovery
    - 15.3 new fields per paper on average

17. **[17_extended_enrichment_pipeline.md](17_extended_enrichment_pipeline.md)** - Extended API enrichment plan (UPDATED Sep 1)
    - Adds 5 new APIs: OpenAlex, Unpaywall, PubMed, CORE, arXiv
    - Universal identifier resolver for multi-API compatibility
    - 100% topic classification via OpenAlex
    - 52% OA discovery via Unpaywall
    - Implementation timeline and priority matrix
    - Additional API evaluations: DBLP and ORCID analysis

18. **[18_api_evaluation_summary.md](18_api_evaluation_summary.md)** - Comprehensive API evaluation (NEW Sep 1)
    - Evaluation of 7 potential enrichment APIs
    - Decision matrix with coverage, performance, and value metrics
    - Final recommendations: 4 production APIs optimal
    - ORCID valuable for gap analysis, not enrichment
    - DBLP redundant with existing APIs
    - Performance comparison and implementation structure

### Reference Implementations

- **[grobid_config.py](grobid_config.py)** - Maximum extraction configuration
- **[post_processor.py](post_processor.py)** - Post-processing implementation
- **[entity_extractor.py](entity_extractor.py)** - Entity extraction from Grobid XML
- **[quality_scorer.py](quality_scorer.py)** - Quality scoring implementation (NEW)

### Working Implementations

- **[implementations/](implementations/)** - Directory with working scripts
  - `extract_zotero_library.py` - Successfully extracted 2,210/2,221 papers (bug fixed)
  - `grobid_overnight_runner.py` - 7-file output strategy implementation
  - `grobid_post_processor.py` - Full post-processing pipeline (631 lines)
  - `retry_all_failed.py` - Retry script that recovered 10/11 failed papers
  - See [implementations/README.md](implementations/README.md) for details

### Production Scripts (Root Directory)
  - `extraction_pipeline_runner.py` - Master pipeline script with organized directory structure
  - `comprehensive_tei_extractor.py` - Complete TEI XML extraction (97.4% year coverage)
  - `run_full_zotero_recovery.py` - Zotero metadata recovery (90.9% recovery rate)
  - `crossref_enrichment_comprehensive.py` - Full CrossRef enrichment (35+ fields)
  - `openalex_enricher.py` - OpenAlex API enrichment class (98% success rate)
  - `v5_openalex_pipeline.py` - OpenAlex pipeline integration
  - `unpaywall_enricher.py` - Unpaywall OA discovery class (98% success rate)
  - `v5_unpaywall_pipeline.py` - Unpaywall pipeline integration
  - `pubmed_enricher.py` - PubMed biomedical enrichment class (87% for medical papers)
  - `v5_pubmed_pipeline.py` - PubMed pipeline integration
  - `arxiv_enricher.py` - arXiv preprint enrichment class (10-15% for STEM papers)
  - `v5_arxiv_pipeline.py` - arXiv pipeline integration
  - `reprocess_tei_xml.py` - Bug fix for full text extraction
  - `pdf_quality_filter.py` - Quality filtering
  - `filter_non_articles.py` - Non-article removal
  - `fix_malformed_dois.py` - DOI cleaning
  - `final_cleanup_no_title.py` - Final cleanup for 100% coverage

### Experimental/Optional Scripts
  - `core_enricher.py` - CORE repository enrichment (NOT RECOMMENDED: 6s/request rate limit)
  - `v5_core_pipeline.py` - CORE pipeline integration (use only for specific grey literature needs)

### Quick Start

```bash
# Option 1: Run complete pipeline with organized structure (recommended)
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full
python extraction_pipeline_runner.py

# Option 2: Continue from existing pipeline
python extraction_pipeline_runner.py \
  --pipeline-dir extraction_pipeline_20250901 \
  --start-from crossref

# Option 3: Step-by-step guide
cat 10_complete_workflow.md

# Understanding the system:
cat 01_overview.md           # System architecture
cat 09_final_pipeline_results.md  # What to expect
cat 07_troubleshooting.md    # If things go wrong
```

### Pipeline Directory Structure (NEW - Sep 1, 2025)

All pipeline outputs are now organized in a single directory with numbered stages:

```
extraction_pipeline_YYYYMMDD/
├── 01_tei_xml/              # GROBID TEI XML output
├── 02_json_extraction/      # Comprehensive TEI → JSON
├── 03_zotero_recovery/      # Zotero metadata recovery
├── 04_crossref_enrichment/  # CrossRef batch enrichment
├── 05_s2_enrichment/        # Semantic Scholar enrichment
├── 06_openalex_enrichment/  # OpenAlex topics & SDGs
├── 07_unpaywall_enrichment/ # Open access discovery
├── 08_pubmed_enrichment/    # Biomedical metadata
├── 09_arxiv_enrichment/     # Preprint tracking
├── 10_final_output/         # Final merged output
└── README.md               # Pipeline documentation
```

Benefits:
- Clean organization with clear data flow
- Easy to backup and version control
- Simple to resume from any stage
- No scattered directories at root level

### Key Insights

- **Philosophy**: Maximum extraction over speed (we run Grobid rarely)
- **Performance**: ~15s per paper average, 9.5 hours for 2,200 papers
- **Two-Pass Strategy**: 90s first pass (99.82% success), 180s retry for failures
- **Local Processing Only**: No Azure dependencies, full control
- **Document Focus**: Research papers only (100% success after cleanup), books excluded
- **Storage**: 7 files per paper (~1-2MB) for maximum flexibility
- **Accuracy**: 100% title coverage, 98.4% DOI coverage, 100% full text
- **Empirical**: All recommendations based on 2,221 paper analysis
- **Final Quality**: 2,150 articles, 83.8M chars, all with titles

### Critical Update (Sep 1, 2025)

**Root Cause Analysis - Missing Metadata**: Investigation revealed widespread missing metadata, particularly journals (GROBID's weakness).

**Solution**: Complete v5 pipeline with four stages:
1. **`comprehensive_tei_extractor.py`**: Extracts ALL information from TEI XML
   - Year extraction: 0% → 97.4% coverage
   - Complete metadata extraction from all XML paths

2. **`run_full_zotero_recovery.py`**: NEW - Recovers metadata from Zotero library
   - 90.9% recovery rate (2,008/2,210 papers improved)
   - Journal recovery: 2,006 papers (addresses GROBID's main weakness)
   - Zero API cost, instant processing

3. **`crossref_batch_enrichment.py`**: Batch processing for fast enrichment (RECOMMENDED)
   - Processes up to 50 DOIs per API call (60x speedup)
   - Adds 35+ fields including citations, ISSN, volume/issue, funding
   - Alternative: `crossref_enrichment_comprehensive.py` for individual queries

**Final Results**:
- >99% coverage for all critical fields after full pipeline
- Journal coverage: 99.6% (Zotero recovery + CrossRef)
- Only 17 papers (0.8%) unrecoverable (complete GROBID failures)
- See [12_pipeline_architecture.md](12_pipeline_architecture.md) for complete details

### Important Update (Aug 31, 2025)

**Final Pipeline Results**: Based on complete processing of 2,221 documents:
- 7-stage pipeline achieves 100% title coverage for research papers
- Final output: 2,150 articles with complete metadata and full text
- Books/proceedings excluded - they require different processing pipeline
- Bug fixes recovered 83.8M characters of previously lost text
- See [09_final_pipeline_results.md](09_final_pipeline_results.md) for complete results

### Latest Updates

#### Sep 1, 2025 - Extended API Enrichment (4 Production APIs)

**OpenAlex** - Topic classification and SDG mapping
- 98% enrichment rate, 98.9% topic coverage
- Implementation: `openalex_enricher.py`, `v5_openalex_pipeline.py`

**Unpaywall** - Open access discovery
- 98% enrichment rate, 69.4% OA discovery
- Implementation: `unpaywall_enricher.py`, `v5_unpaywall_pipeline.py`

**PubMed** - Biomedical metadata
- 87% enrichment for medical papers, MeSH terms
- Implementation: `pubmed_enricher.py`, `v5_pubmed_pipeline.py`

**arXiv** - Preprint tracking for STEM papers
- ~10-15% enrichment expected, version tracking
- Implementation: `arxiv_enricher.py`, `v5_arxiv_pipeline.py`

See [17_extended_enrichment_pipeline.md](17_extended_enrichment_pipeline.md) for details

#### Sep 1, 2025 - Extended Enrichment Pipeline

**[17_extended_enrichment_pipeline.md](17_extended_enrichment_pipeline.md)** - Complete plan for v5 pipeline extension
- Adds 5 new API integrations (OpenAlex ✅, Unpaywall, PubMed, CORE, arXiv)
- Universal identifier resolver for multi-API compatibility
- Expected outcomes: 100% topic classification, 52% OA discovery, 30% MeSH coverage
- Implementation timeline and priority matrix
- Processing time: ~30 minutes additional for all enrichments

#### Sep 1, 2025 - S2 Optimization Complete

**[16_s2_optimization_complete.md](16_s2_optimization_complete.md)** - Semantic Scholar batch enrichment optimization
- Achieved 93.7% enrichment rate (2,000/2,134 papers)
- 426.8 papers per API call efficiency
- Removed preemptive rate limiting based on build_kb.py patterns
- Added checkpoint recovery and comprehensive field import
- 15.3 new fields per paper on average
- Total processing: 1.5 minutes (vs hours with individual queries)

### Version History

- **v5.0** (Current) - Three-system integration with maximum extraction
  - Sep 1: S2 optimization complete, full pipeline operational
  - Aug 31: Zotero recovery + CrossRef batch processing added
- **v4.6** - Previous version with reliability issues
- **v4.0** - Introduction of enhanced quality scoring
