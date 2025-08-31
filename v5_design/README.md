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
   - Troubleshooting

7. **[08_paper_filtering.md](08_paper_filtering.md)** - Paper filtering strategy
   - Research papers vs books/proceedings
   - Why v5 excludes books
   - Automatic filtering implementation
   - PDF quality report integration
   - Success rates by document type

### Reference Implementations

- **[grobid_config.py](grobid_config.py)** - Maximum extraction configuration
- **[post_processor.py](post_processor.py)** - Post-processing implementation
- **[entity_extractor.py](entity_extractor.py)** - Entity extraction from Grobid XML
- **[quality_scorer.py](quality_scorer.py)** - Quality scoring implementation

### Working Implementations

- **[implementations/](implementations/)** - Directory with working scripts
  - `extract_zotero_library.py` - Successfully extracted 2,210/2,221 papers
  - `grobid_overnight_runner.py` - 7-file output strategy implementation
  - `grobid_post_processor.py` - Full post-processing pipeline (631 lines)
  - `retry_all_failed.py` - Retry script that recovered 10/11 failed papers
  - See [implementations/README.md](implementations/README.md) for details

### Quick Start

```bash
# 1. Read overview to understand the system
cat 01_overview.md

# 2. Check installation requirements
cat 06_installation_setup.md

# 3. Review Grobid configuration
cat 02_grobid_extraction.md

# 4. Understand post-processing
cat 03_post_processing.md

# 5. Check command reference
cat 05_commands_reference.md
```

### Key Insights

- **Philosophy**: Maximum extraction over speed (we run Grobid rarely)
- **Performance**: ~15s per paper average, 9.5 hours for 2,200 papers
- **Two-Pass Strategy**: 90s first pass (99.82% success), 180s retry for failures
- **Local Processing Only**: No Azure dependencies, full control
- **Document Focus**: Research papers only (99.95% success), books excluded
- **Storage**: 7 files per paper (~1-2MB) for maximum flexibility
- **Accuracy**: 99%+ abstract extraction, 85-90% section detection after post-processing
- **Empirical**: All recommendations based on 2,221 paper analysis

### Important Update (Aug 2025)

**Local Processing Strategy**: Based on empirical testing of 2,221 documents:
- Two-pass extraction (90s + 180s) achieves 99.95% success for research papers
- Books/proceedings excluded - they require different processing pipeline
- Local processing provides full control and predictable timing
- See [02_grobid_extraction.md](02_grobid_extraction.md) for complete strategy

### Version History

- **v5.0** (Current) - Three-system integration with maximum extraction
- **v4.6** - Previous version with reliability issues
- **v4.0** - Introduction of enhanced quality scoring
