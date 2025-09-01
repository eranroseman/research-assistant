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

10. **[10_complete_workflow.md](10_complete_workflow.md)** - Step-by-step workflow guide (NEW)
    - Visual pipeline flow diagram
    - Quick start commands
    - Stage-by-stage details
    - Time estimates and validation
    - Best practices

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
  - `v5_extraction_pipeline.py` - Consolidated pipeline runner (all stages)
  - `reprocess_tei_xml.py` - Bug fix for full text extraction
  - `pdf_quality_filter.py` - Quality filtering
  - `crossref_enrichment.py` - Title/DOI recovery
  - `filter_non_articles.py` - Non-article removal
  - `fix_malformed_dois.py` - DOI cleaning
  - `final_cleanup_no_title.py` - Final cleanup for 100% coverage

### Quick Start

```bash
# Option 1: Run complete pipeline (recommended)
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full
python v5_extraction_pipeline.py

# Option 2: Step-by-step guide
cat 10_complete_workflow.md

# Understanding the system:
cat 01_overview.md           # System architecture
cat 09_final_pipeline_results.md  # What to expect
cat 07_troubleshooting.md    # If things go wrong
```

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

### Important Update (Aug 31, 2025)

**Final Pipeline Results**: Based on complete processing of 2,221 documents:
- 7-stage pipeline achieves 100% title coverage for research papers
- Final output: 2,150 articles with complete metadata and full text
- Books/proceedings excluded - they require different processing pipeline
- Bug fixes recovered 83.8M characters of previously lost text
- See [09_final_pipeline_results.md](09_final_pipeline_results.md) for complete results

### Version History

- **v5.0** (Current) - Three-system integration with maximum extraction
- **v4.6** - Previous version with reliability issues
- **v4.0** - Introduction of enhanced quality scoring
