# Research Assistant v4.7.0

**🏗️ NEW: Modular Architecture for Better Maintainability!**

A streamlined academic literature search tool featuring Multi-QA MPNet embeddings for semantic search, smart incremental updates, and Claude Code integration.

## Table of Contents

- [Quick Start](#quick-start) - Get up and running in 5 minutes
- [Quick Reference](#quick-reference) - Essential commands at a glance
- [Key Features](#key-features) - Core capabilities
- [Usage Guide](#usage-guide) - Common tasks and commands
- [Building Knowledge Base](#building-your-knowledge-base) - Setup with Zotero
- [Documentation](#documentation) - API reference and technical details
- [Troubleshooting](#troubleshooting) - Common issues and solutions
- [Contributing](#contributing) - Development setup

## Latest Features (Unreleased)

**📄 PragmaticSectionExtractor - Intelligent Three-Tier Section Extraction**
- **75-80% accuracy** improvement (up from 43%) with progressive enhancement
- **Tier 1**: Fast pattern matching for 65% of papers (~2ms)
  - Now handles Title Case headers (65% of papers)
  - Supports numbered sections (e.g., "1. Introduction")
  - Case-insensitive matching for better coverage
- **Tier 2**: Fuzzy matching with RapidFuzz for clinical formats (+10% coverage)
- **Tier 3**: PDFPlumber structure analysis recovers lost formatting (remaining 25%)
- **Performance**: Average ~23ms per paper, batch processing with 4-8x speedup
- **Smart Exit**: Stops processing early when sufficient sections found
- **Production Ready**: Caching, error handling, graceful fallbacks

**📝 Enhanced Abstract Extraction**
- Multi-strategy fallback system for papers with missing abstracts
- Automatically tries 4 different extraction methods in priority order
- Resolves empty abstract issues for papers without clear headers
- Integrated seamlessly into the main extraction pipeline

**🎯 Advanced Extraction Improvements**
- **Section-Specific Length Limits**: Prevents over-extraction with intelligent truncation
  - Abstract limited to 5000 chars (~1000 words) to prevent capturing entire papers
  - Methods/Results/Discussion limited to 15000 chars (~3000 words)
  - References allowed up to 50000 chars for comprehensive citation coverage
- **Improved Boundary Detection**: Smarter section boundary identification
  - Detects double newlines followed by uppercase as section boundaries
  - Handles numbered sections (1. Introduction, 2. Methods, etc.)
  - Prevents content bleeding between sections
- **Post-Processing Validation**: Ensures extraction quality
  - Removes leaked section headers from content
  - Fixes section contamination (other headers appearing in wrong sections)
  - Validates minimum content requirements per section type
  - Cleans and normalizes extracted text

## v4.7.0 New Features

**🏗️ Modular Architecture**
- Extracted quality scoring to dedicated `kb_quality.py` module (490 lines)
- Extracted FAISS indexing to `kb_indexer.py` module (437 lines)
- Reduced `build_kb.py` from 4,293 to 3,660 lines (15% reduction)
- Improved separation of concerns and testability
- No breaking changes - all existing functionality preserved

## v4.6 Features

**🎯 Batch API Processing & Production-Ready Reliability**
- Semantic Scholar batch endpoint integration reduces API calls by 400x (2,100 → 5 requests)
- 96.9% enhanced scoring success rate in real production deployments
- Fixed critical venue format bugs that caused 0% success rates in previous versions
- Smart quality score fallback with clear user explanations and automatic upgrades

**🔧 Enhanced Quality Score Architecture**
- Enhanced scoring: API-powered with citations, venue rankings, author h-index (comprehensive)
- Basic scoring: Local metadata fallback with study type, recency, full-text availability (reliable)
- Automatic upgrades: Basic scores seamlessly upgraded when API becomes available
- Immediate persistence: Quality scores saved before embedding generation (prevents data loss)

**📊 Privacy-Protected Analytics & Monitoring**
- Smart error sanitization removes sensitive data while preserving debugging value
- Standardized event logging across all modules with consistent attribution
- Session correlation for comprehensive user workflow analysis
- Daily log rotation with JSONL format for structured analytics

**🎨 Unified User Experience**
- Consistent error messages with context-aware suggestions and actionable guidance
- Standardized help text with examples, notes, and cross-references across all commands
- Unified progress indicators, result displays, and status formatting
- 100% test coverage for all formatting modules ensuring reliability


## Quick Start

Get Research Assistant running in under 5 minutes:

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Build Knowledge Base

```bash
# Option A: Demo database (5 sample papers)
python src/build_kb.py --demo

# Option B: From your Zotero library (safe incremental by default)
python src/build_kb.py          # Safe incremental update
python src/build_kb.py --rebuild   # Force complete rebuild
```

### 3. Test the System

```bash
python src/cli.py info
python src/cli.py search "digital health"
```

### 4. Use in Claude Code

```
/research barriers to digital health adoption in elderly populations
/discover "AI medical diagnosis"
```

**That's it!** You're ready to search academic literature. Continue to the [Usage Guide](#usage-guide) for more examples.

## Quick Reference

### Essential Commands

```bash
# Build/Update KB
python src/build_kb.py --demo        # 5-paper demo
python src/build_kb.py               # Safe incremental update (auto-prompts gap analysis)
python src/build_kb.py --rebuild     # Force complete rebuild

# Network Gap Analysis (Auto-prompted after builds - Production-Ready v4.7)
python src/analyze_gaps.py                            # Comprehensive analysis (~66 sec, executive dashboard)
python src/analyze_gaps.py --min-citations 50        # High-impact papers with smart filtering
python src/analyze_gaps.py --year-from 2024 --limit 50   # Recent work + research area clustering
python src/analyze_gaps.py --min-citations 20 --year-from 2020 --limit 100  # Balanced with batch processing

# External Paper Discovery
python src/discover.py --keywords "topic,keywords"    # Discover external papers
python src/discover.py --keywords "AI,healthcare" --quality-threshold HIGH  # High-quality only
python src/discover.py --coverage-info               # Database coverage guide

# Search Papers
python src/cli.py search "topic"                      # Basic search
python src/cli.py search "topic" --show-quality       # With quality scores
python src/cli.py search "topic" --quality-min 70     # High-quality only
python src/cli.py search "topic" --years 2020-2024    # Filter by year range
python src/cli.py search "topic" --group-by year      # Group by year/journal/study_type
python src/cli.py search "topic" --contains "SGLT2"   # Must contain term
python src/cli.py search "topic" --exclude "mice"     # Exclude term
python src/cli.py search "topic" --export results.csv # Export to CSV
python src/cli.py smart-search "topic" -k 30          # Handle many papers

# Multi-query Search
python src/cli.py search "diabetes" --queries "glucose" --queries "insulin"

# Batch Operations (10-20x faster for multiple commands)
python src/cli.py batch --preset research "diabetes"   # Comprehensive research
python src/cli.py batch --preset review "cancer"       # Systematic reviews
python src/cli.py batch commands.json                  # Custom batch from file
echo '[{"cmd":"search","query":"AI","k":10}]' | python src/cli.py batch -

# Get Papers
python src/cli.py get 0001                            # Full paper
python src/cli.py get 0001 --sections abstract methods # Specific sections
python src/cli.py get-batch 0001 0002 0003            # Multiple papers at once
python src/cli.py get-batch 0001 0234 --format json   # JSON output

# Author Search
python src/cli.py author "Smith J"                    # Find by author
python src/cli.py author "Chen" --exact               # Exact match only

# Utilities
python src/cli.py info                                # KB status
python src/cli.py diagnose                            # Health check
python src/cli.py cite 0001 0002 0003                 # Generate IEEE citations
```

### Claude Code Commands

```
/research <your research question or topic>    # Comprehensive literature research
/discover [report.md] or ["topic"]             # External paper discovery
```

- Literature review reports are saved to the `reviews/` directory
- Discovery reports are saved to the `exports/` directory with `discovery_` prefix

## Usage Guide

### Searching Papers

#### Basic Search
```bash
# Simple, direct search with Multi-QA MPNet embeddings
python src/cli.py search "telemedicine"
python src/cli.py search "diabetes complications"
python src/cli.py search "digital therapeutics" -k 20
```

#### Advanced Search Options

##### Year Filtering
```bash
# Papers from specific year range
python src/cli.py search "COVID-19" --years 2020-2024
python src/cli.py search "AI in medicine" --years 2023

# Combine with --after for minimum year
python src/cli.py search "telemedicine" --after 2020
```

##### Term Filtering
```bash
# Must contain specific term (in title/abstract)
python src/cli.py search "diabetes" --contains "SGLT2"
python src/cli.py search "cancer" --contains "immunotherapy"

# Exclude papers with specific term
python src/cli.py search "treatment" --exclude "mice"
python src/cli.py search "therapy" --exclude "animal model"

# Full-text search (slower but comprehensive)
python src/cli.py search "insulin pump" --contains "closed-loop" --full-text
```

##### Multi-Query Search
```bash
# Search multiple topics and combine results
python src/cli.py search "diabetes" --queries "glucose monitoring" --queries "insulin therapy"
python src/cli.py search "COVID" --queries "long COVID" --queries "post-acute sequelae"
```

##### Grouping Results
```bash
# Group by year, journal, or study type
python src/cli.py search "digital health" --group-by year
python src/cli.py search "clinical trials" --group-by journal
python src/cli.py search "treatment" --group-by study_type
```

##### Export to CSV
```bash
# Export results for Excel analysis (saved to exports/ directory)
python src/cli.py search "hypertension" --export results.csv
python src/cli.py search "obesity" -k 50 --export obesity_papers.csv

# Combine with quality filtering
python src/cli.py search "diabetes" --quality-min 70 --export high_quality.csv

# Files are saved in exports/ directory with search_ prefix
# Example: exports/search_results.csv
```

#### Quality Filters with Enhanced Scoring
```bash
# High-quality evidence only (enhanced score ≥70)
python src/cli.py search "metabolic syndrome" --quality-min 70 --show-quality

# Exceptional quality papers (enhanced score ≥85: A+)
python src/cli.py search "diabetes" --quality-min 90 --show-quality

# Recent RCTs and systematic reviews with quality indicators
python src/cli.py search "diabetes" --after 2020 --type rct --type systematic_review --show-quality

# Get comprehensive results with visual quality indicators
python src/cli.py search "AI diagnosis" -k 30 --show-quality
```

#### Smart Search with Chunking (v4.0)
```bash
# Handle 20+ papers without context overflow
python src/cli.py smart-search "diabetes treatment" -k 30

# Prioritize specific sections based on query
python src/cli.py smart-search "clinical outcomes" --sections results conclusion
```

### Retrieving Papers

```bash
# Get specific sections
python src/cli.py get 0001 --sections abstract methods results

# Full paper
python src/cli.py get 0001 -o paper.md
```

### Retrieving Papers

#### Single Paper
```bash
# Get full paper by ID
python src/cli.py get 0001
python src/cli.py get 0234

# Get specific sections only
python src/cli.py get 0001 --sections abstract methods
python src/cli.py get 0234 --sections introduction conclusion

# Save to file
python src/cli.py get 0001 --output paper.md
```

#### Batch Retrieval
```bash
# Get multiple papers at once
python src/cli.py get-batch 0001 0002 0003
python src/cli.py get-batch 0001 0234 1426

# JSON format for processing
python src/cli.py get-batch 0001 0002 --format json

# Combine with redirection
python src/cli.py get-batch 0001 0002 0003 > papers.txt
```

### Author Search

```bash
# Find papers by author (partial match)
python src/cli.py author "Smith"
python src/cli.py author "Chen M"

# Exact author name match
python src/cli.py author "John Smith" --exact
python src/cli.py author "Michael Chen" --exact
```

### Batch Operations (New in v4.1)

The batch command dramatically improves performance by loading the model once for multiple operations:

```bash
# Use presets for common workflows
python src/cli.py batch --preset research "diabetes"    # 5 searches + top papers
python src/cli.py batch --preset review "hypertension"  # Focus on reviews/meta-analyses
python src/cli.py batch --preset author-scan "Smith J"  # All papers by author

# Custom batch operations
cat > commands.json << EOF
[
  {"cmd": "search", "query": "COVID-19", "k": 30, "show_quality": true},
  {"cmd": "search", "query": "long COVID", "k": 20},
  {"cmd": "merge"},
  {"cmd": "filter", "min_quality": 70},
  {"cmd": "auto-get-top", "limit": 10}
]
EOF
python src/cli.py batch commands.json

# Performance: 10-20x faster than individual commands
# Individual: 4-5 seconds × N commands
# Batch: 5-6 seconds total
```

### Managing Your Knowledge Base

```bash
# Updates (v4.0 - safe incremental by default)
python src/build_kb.py                     # Safe incremental update
python src/build_kb.py --rebuild           # Force complete rebuild

# Sync between computers
python src/build_kb.py --export kb_backup.tar.gz
python src/build_kb.py --import kb_backup.tar.gz
```

### External Paper Discovery (New in v4.6)

Discover external papers using Semantic Scholar's comprehensive database (214M papers, 85% digital health coverage):

```bash
# Basic discovery with keywords
python src/discover.py --keywords "diabetes,mobile health"

# Advanced filtering for high-quality research
python src/discover.py --keywords "AI,diagnostics" --quality-threshold HIGH --population-focus pediatric

# Population-specific discovery
python src/discover.py --keywords "telemedicine" --population-focus elderly --year-from 2020

# Coverage guidance and database information
python src/discover.py --coverage-info

# Include existing KB papers in results (normally filtered out)
python src/discover.py --keywords "treatment" --include-kb-papers
```

**Key Features:**
- Traffic light coverage assessment (🟢🟡🔴) to evaluate KB completeness
- Basic quality scoring (no API delays) with confidence indicators
- Population-specific term expansion (pediatric, elderly, etc.)
- Study type filtering and relevance scoring
- DOI lists formatted for Zotero bulk import
- Comprehensive search coverage via Semantic Scholar

**Report Generation:** Results saved to `exports/discovery_YYYY_MM_DD.md` with organized DOI lists

### Gap-Based Discovery via Claude Code (New)

The `/discover` slash command provides intelligent external paper discovery with gap analysis:

```
/discover                           # Analyzes latest research report for gaps
/discover "AI medical diagnosis"    # Direct topic search
/discover diabetes_review_2024.md   # Analysis of specific report
```

**Key Features:**
- **Automatic Gap Detection**: Analyzes research reports to identify literature gaps
- **Intelligent Search Strategy**: Adapts parameters based on research context
- **Web Research Integration**: Supplements Semantic Scholar when specialized sources needed
- **Coverage Assessment**: Traffic light indicators (🟢🟡🔴) for KB completeness
- **Integrated Workflow**: Seamless integration with existing research commands

**Output:** Comprehensive reports saved to `exports/discovery_YYYY_MM_DD.md` with DOI lists for Zotero import.

### Integrated Research Workflow

The `/research` and `/discover` commands work together for comprehensive literature analysis:

**Step 1: Internal Analysis**
```bash
/research barriers to digital health adoption in elderly populations
```
- Analyzes existing knowledge base (~2,100 papers)
- Generates comprehensive literature review in `reviews/` directory
- Identifies evidence patterns and potential gaps

**Step 2: External Discovery**
```bash
/discover    # Analyzes the research report for gaps
```
- Automatically detects gaps from the research report
- Searches 214M external papers via Semantic Scholar
- Provides coverage assessment and new paper recommendations
- Generates discovery report in `exports/` directory

**Step 3: Knowledge Base Expansion**
```bash
# Import discovered papers via Zotero DOI lists
python src/build_kb.py    # Update KB with new papers
```

This integrated approach ensures comprehensive coverage from initial analysis through external discovery to knowledge base expansion.

### Network Gap Analysis (Production-Ready in v4.7)

**Systematic literature gap detection with 58-65x efficiency improvement and executive dashboard**

After successful KB builds, you'll be automatically prompted to run comprehensive gap analysis to discover missing papers in your collection. This production-ready feature identifies literature gaps through two optimized algorithms with batch processing and smart filtering.

#### **🎯 Executive Dashboard & Smart Organization**

**New in v4.7**: Executive dashboard format provides actionable insights at a glance:
- **Top 5 Critical Gaps**: Highest-impact papers (50K+ citations) for immediate import
- **Research Area Breakdown**: Automatic clustering (🤖 AI, 🏃 Physical Activity, ⚕️ Clinical Methods, etc.)
- **Quick Import Workflows**: Copy-paste DOI lists organized by priority and research area
- **Smart Filtering**: Automatically removes 50+ low-quality items (book reviews, duplicates, opinion pieces)
- **Progressive Disclosure**: Summary → Areas → Complete catalog for optimal usability

#### **🚀 Performance Improvements (v4.7)**

**Batch Processing Excellence**:
- **58-65x efficiency**: 500 papers per API call vs individual requests
- **Completion time**: ~66 seconds for 200 gaps vs previous timeouts
- **API calls**: Reduced from 2,180+ to ~5 batch requests
- **Zero rate limiting**: Controlled pacing with 2-second delays prevents 429 errors

**Smart Author Selection**:
- **Top 10 authors by KB frequency** vs 50 random authors (maximum ROI)
- **Author prioritization**: Focus on most prolific researchers in your KB
- **Quality over quantity**: Higher relevance with targeted approach

#### **Gap Detection Algorithms (Optimized)**

**1. Citation Network Analysis** (Primary - Batch Optimized)
- Identifies papers frequently cited by your KB but missing from collection
- **Batch processing**: Processes 500 papers per API call for 400x efficiency
- Prioritizes gaps by citation frequency × confidence scores
- Auto-organized by research areas for strategic decision-making

**2. Author Network Analysis** (Secondary - Frequency Optimized)
- Finds recent work from your KB's most prolific authors
- **Smart selection**: Top 10 authors by paper count in your KB
- **Controlled pacing**: 2-second delays prevent API throttling
- Emphasizes recency and topical relevance

#### **Usage Examples (Updated)**

```bash
# Comprehensive analysis (recommended - completes in ~66 seconds)
python src/analyze_gaps.py

# High-impact established papers with executive dashboard
python src/analyze_gaps.py --min-citations 50

# Recent cutting-edge work with manageable results
python src/analyze_gaps.py --year-from 2024 --limit 50

# Balanced approach with quality filtering
python src/analyze_gaps.py --min-citations 20 --year-from 2020 --limit 100

# Custom KB with specific parameters
python src/analyze_gaps.py --kb-path /custom/path/kb_data --limit 200
```

#### **Advanced Filtering Options**

```bash
# Parameter Guide (Updated for v4.7):
# --min-citations N    : Citation threshold (0=all, 20-50=moderate, 100+=influential)
# --year-from YYYY     : Author recency (2024=cutting-edge, 2022=balanced, 2020=comprehensive)
# --limit N           : Results per algorithm (50=focused, 100=balanced, 200+=comprehensive)
# --kb-path PATH      : Custom KB directory (must be v4.0+ with ≥20 papers)
```

#### **Output & Integration (Enhanced)**

**Executive Dashboard Reports**: Generated as `exports/gap_analysis_YYYY_MM_DD_HHMM.md` with:
- **🎯 Immediate Action Required**: Top 5 critical gaps with quick import DOIs
- **📊 Research Area Breakdown**: Organized by domain with statistics
- **🚀 Power User Import**: Pre-formatted DOI lists for bulk Zotero import
- **🔧 Import Workflows**: Step-by-step instructions (5min → 15min → 30min approaches)
- **📋 Complete Catalog**: Expandable sections with full gap details

**New Features**:
- **File overwrite prevention**: Timestamp includes hour/minute (`_1612.md`)
- **Research area clustering**: Automatic organization by domain
- **Smart filtering indicators**: Shows removed low-quality items count
- **Progressive disclosure**: Executive summary → details on demand

**Priority Classification** (Unchanged):
- **HIGH Priority**: Strong relevance evidence (confidence ≥0.8)
- **MEDIUM Priority**: Moderate confidence (0.6-0.8)
- **LOW Priority**: Potentially valuable (0.4-0.6)

#### **Performance Characteristics (v4.7)**

- **Duration**: ~66 seconds for comprehensive analysis (vs 15-25 min timeout previously)
- **API Efficiency**: ~5 batch calls + 10 author searches (vs 2,180+ individual calls)
- **Memory Usage**: <2GB during analysis, results streamed
- **Success Rate**: 100% completion rate (vs frequent timeouts)
- **Rate Limiting**: Zero 429 errors with controlled pacing
- **Resumable**: 7-day cache for interrupted sessions

#### **Requirements & Validation**

- **KB Version**: v4.0+ required (no legacy support)
- **Minimum Papers**: 20+ papers with complete metadata
- **Enhanced Scoring**: Preferred for optimal confidence calculations
- **API Access**: Semantic Scholar API required
- **Fail-Fast Validation**: Clear error messages with remediation guidance

### Generating Citations

```bash
# Generate IEEE citations for specific papers
python src/cli.py cite 0001 0002 0003
python src/cli.py cite 0234 1426 --format json
```

## Building Your Knowledge Base

### From Zotero Library

1. **Enable Zotero API**
   - Open Zotero → Edit → Settings → Advanced
   - Check "Allow other applications to communicate with Zotero"
   - Restart Zotero if needed

2. **Run Builder**
   ```bash
   python src/build_kb.py
   ```

   **Automatic behavior:**
   - **Enhanced Quality Scoring**: Tests Semantic Scholar API availability
   - **Smart Incremental Update**: Reuses existing embeddings (~40x faster)
   - **Index Validation**: Automatically fixes embedding/metadata mismatches
   - **User Choice**: If API unavailable, prompts with clear consequences
   - **Gap Analysis**: Auto-prompts after successful builds (≥20 papers + enhanced scoring)

3. **Performance** (v4.6 optimized)
   - Initial build: ~17 minutes for 2,180 papers with 96.9% enhanced scoring success
   - Batch API processing: 400x fewer API calls (2,100 → 5 requests for large datasets)
   - Smart incremental updates: ~40x faster than full rebuild (embeddings reused)
   - Quality score reliability: 96.9% enhanced, 3.1% basic fallback, 0% failures
   - Smart caching: Quality upgrades preserve embeddings (30x faster incremental)
   - Storage: ~305MB for ~2,000 papers (~150MB per 1000 papers)

## Key Features

### Intelligent Search
- **Multi-QA MPNet Embeddings** - Optimized for healthcare and scientific literature
- **Smart Search Modes** - Auto-detects questions vs. exploration
- **Query Expansion** - Automatic synonym expansion
- **Enhanced Quality Scoring** - 0-100 using Semantic Scholar API: citations (25pts), venue prestige (15pts), author authority (10pts), cross-validation (10pts), plus core factors (40pts)
- **Smart Fallback System** - Basic scoring (study type, recency, full-text) when API unavailable, automatic upgrades when API returns
- **Visual Quality Indicators** - Instant assessment with A+ A B C D F grades and [Enhanced scoring] markers
- **Full Content Preservation** - Complete paper sections with zero information loss, no truncation of methodology or results

### Performance
- **O(1) Paper Lookups** - Instant access via optimized index
- **Full Content Processing** - Multi-QA MPNet handles complete sections efficiently
- **Optimized Storage** - Complete sections with intelligent caching
- **Smart Incremental Updates** - 40x faster than full rebuild with embedding reuse
- **Index Validation** - Automatically detects and fixes inconsistencies
- **GPU Acceleration** - Faster embedding generation when available

### Productivity
- **KB Export/Import** - Sync between computers
- **Claude Integration** - `/research` and `/discover` slash commands
- **Offline Operation** - No internet needed after setup
- **Report Generation** - Automatic reports for missing/small PDFs

### Analytics & Monitoring
- **Command Usage Analytics** - Privacy-protected usage pattern tracking for system optimization
- **Smart Error Sanitization** - Removes sensitive data (paths, keys, emails) while preserving debug value
- **Session Correlation** - Tracks user workflows across commands for UX improvements
- **Daily Log Rotation** - Organized analytics in `system/command_usage_YYYYMMDD.jsonl`
- **Privacy by Design** - Local logs only, automatically disabled during testing

## Documentation

- **[API Reference](docs/api-reference.md)** - Complete CLI command reference
- **[Technical Specs](docs/technical-specs.md)** - Architecture, modules, and implementation
- **[Advanced Usage](docs/advanced-usage.md)** - GPU setup, custom models, performance tuning
- **[Changelog](CHANGELOG.md)** - Version history and updates

### Project Structure

```
src/
├── build_kb.py         # Knowledge base builder from Zotero (3,660 lines)
├── kb_quality.py       # Quality scoring module (490 lines) [NEW - v4.7]
├── kb_indexer.py       # FAISS indexing and embeddings (437 lines) [NEW - v4.7]
├── pragmatic_section_extractor.py # Three-tier section extraction (711 lines) [NEW]
├── cli.py              # Command-line interface for search
├── cli_kb_index.py     # O(1) paper lookups and index operations
├── discover.py         # External paper discovery via Semantic Scholar
├── analyze_gaps.py     # Network gap analysis CLI interface
├── gap_detection.py    # Core gap detection algorithms (citation + author networks)
├── api_utils.py        # API retry logic with exponential backoff
├── error_formatting.py # Unified error message formatting with context-aware suggestions
├── help_formatting.py  # Standardized help text templates and command documentation
├── output_formatting.py # Consistent progress indicators, results display, and status formatting
└── config.py           # Configuration constants

exports/                # User-valuable analysis and exports
├── analysis_pdf_quality.md    # KB quality analysis
├── discovery_*.md             # External paper discovery reports
├── gap_analysis_YYYY_MM_DD_HHMM.md  # Gap analysis with executive dashboard & DOI lists
├── search_*.csv               # Search result exports
└── paper_*.md                 # Individual paper exports

reviews/                # Literature review reports
└── *.md               # Generated by /research slash command

.claude/commands/       # Claude Code slash commands
├── research.md         # /research - Literature research and review generation
└── discover.md         # /discover - Gap-based external paper discovery

system/                 # Development and system artifacts
├── command_usage_*.jsonl  # Command usage analytics (daily rotation, privacy-protected)
└── dev_*.csv          # Test results and system data

tests/
├── unit/                           # Component tests (160+ tests)
│   ├── test_unit_citation_system.py      # IEEE citation formatting
│   ├── test_unit_cli_batch_commands.py   # CLI batch operations
│   ├── test_unit_cli_interface.py        # CLI utility functions
│   ├── test_unit_knowledge_base.py       # KB building, indexing, caching
│   ├── test_unit_quality_scoring.py      # Paper quality algorithms
│   ├── test_unit_search_engine.py        # Search, embedding, ranking
│   ├── test_unit_command_usage.py        # Command usage logging
│   ├── test_unit_pragmatic_extractor.py  # Three-tier section extraction [NEW]
│   ├── test_unit_error_formatting.py     # Unified error message formatting (100% coverage)
│   ├── test_unit_help_formatting.py      # Standardized help text formatting (100% coverage)
│   └── test_unit_output_formatting.py    # Consistent output formatting (96.9% coverage)
├── integration/                    # Workflow tests (58+ tests)
│   ├── test_integration_batch_operations.py
│   ├── test_integration_incremental_updates.py
│   ├── test_integration_kb_building.py
│   ├── test_integration_reports.py
│   ├── test_integration_search_workflow.py
│   └── test_integration_formatting.py    # Cross-module formatting consistency tests
├── e2e/                           # End-to-end tests (23 tests)
│   ├── test_e2e_cite_command.py
│   └── test_e2e_cli_commands.py
└── performance/                   # Benchmarks (7 tests)
    └── test_performance_benchmarks.py
```

## System Requirements

- **Python**: 3.11+ required
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 1GB + ~150MB per 1000 papers
- **GPU**: Optional (10x speedup for embeddings)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **"Knowledge base not found"** | `python src/build_kb.py --demo` |
| **"Invalid paper ID"** | Use 4-digit format: 0001, not 1 |
| **Zotero connection failed** | 1. Start Zotero<br>2. Enable API in Settings → Advanced<br>3. [WSL setup guide](docs/advanced-usage.md#wsl-specific-setup-zotero-on-windows-host) |
| **Slow performance** | Check GPU: `python -c "import torch; print(torch.cuda.is_available())"` |
| **Model download issues** | `pip install --upgrade sentence-transformers` |
| **Build interrupted** | Fixed in v4.6.1 - Automatic checkpoint recovery on restart |
| **API rate limiting errors** | Fixed in v4.6.1 - Exponential backoff prevents 429 errors |
| **Checkpoint file corrupted** | Delete `.checkpoint.json` and restart (will process all papers) |
| **"Gap analysis not available"** | Requires enhanced quality scoring and ≥20 papers in KB |
| **"Gap detection module not found"** | Run from correct directory: `python src/analyze_gaps.py` |
| **Gap analysis times out/rate limited** | Fixed in v4.7 - batch processing completes in ~66 seconds |
| **Gap analysis file overwrites** | Fixed in v4.7 - timestamp includes hour/minute (`_HHMM`) |
| **Gap analysis cache issues** | Delete `.gap_analysis_cache.json` and retry with batch processing |
| **Index/metadata mismatch** | Automatically fixed by incremental update (shows "Reusing X embeddings") |
| **Enhanced scoring unavailable** | User prompted to continue with basic build or fix API connectivity |

## Contributing

### Development Setup

1. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Set up pre-commit hooks** (optional but recommended)
   ```bash
   pre-commit install
   ```

   This will automatically:
   - Fix trailing whitespace and file endings
   - Check YAML/TOML syntax
   - Run ruff linting and formatting
   - Catch debug statements

3. **Run tests** (338+ tests covering all functionality)
   ```bash
   pytest tests/ -v                                    # All tests (338+ total)
   pytest tests/unit/ -v                               # Unit tests (150+ tests, fast)
   pytest tests/e2e/test_e2e_cli_commands.py::TestCriticalE2EFunctionality -v  # Critical tests
   pytest tests/ --cov=src                             # With coverage report
   ```

4. **Quality checks**
   ```bash
   ruff check src/ tests/        # Linting
   ruff check src/ tests/ --fix  # Auto-fix issues
   mypy src/                     # Type checking
   ```

### Test Coverage

The test suite comprehensively covers all functionality with 469 tests:

- **Unit Tests** (287 tests): Component-focused testing including formatting modules with 100% coverage
  - Comprehensive quality scoring tests (`test_unit_quality_scoring.py`)
  - API retry logic tests (`test_unit_api_utils.py`)
- **Integration Tests** (136 tests): Workflow validation including cross-module formatting consistency
  - Checkpoint recovery tests (`test_integration_checkpoint_recovery.py`)
  - Incremental update tests updated for modular architecture
- **E2E Tests** (39 tests): End-to-end functionality testing critical user workflows
- **Performance Tests** (7 tests): Speed and memory benchmarks

All tests are currently passing and reflect production behavior including:
- 96.9% enhanced scoring success rate
- Gap analysis batch processing (58-65x efficiency improvement)
- Smart filtering and research area clustering
- Executive dashboard generation and file overwrite prevention
- Unified formatting system with consistent error messages, help text, and output displays

Contributions welcome! Priority areas:
- Additional citation formats (APA, MLA)
- Web UI for knowledge base management
- Integration with other reference managers
- Multi-language support
- Performance optimizations for large libraries (10k+ papers)

## License

MIT License - See LICENSE file for details

**Note**: PyMuPDF (PDF extraction) is AGPL-licensed. For commercial use, consider purchasing a PyMuPDF license or using alternative libraries.

## Acknowledgments

- [FAISS](https://github.com/facebookresearch/faiss) by Facebook Research
- [Sentence Transformers](https://www.sbert.net/) by UKPLab
- [Claude Code](https://claude.ai/code) by Anthropic

## Support

1. Check [troubleshooting](#-troubleshooting) above
2. Review [API Reference](docs/api-reference.md) for command details
3. See [Advanced Usage](docs/advanced-usage.md) for complex scenarios
4. Open an issue with error messages and steps to reproduce
