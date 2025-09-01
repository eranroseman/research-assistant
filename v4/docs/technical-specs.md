# Technical Specifications

> **Navigation**: [Home](../README.md) | [API Reference](api-reference.md) | [Advanced Usage](advanced-usage.md)

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [v4.0 Features](#new-features-in-v40)
- [Core Modules](#core-modules)
- [Implementation Details](#implementation)
- [Data Formats](#data-formats)
- [Performance](#technical-specifications-1)
- [Testing](#testing)
- [Dependencies](#dependencies)

---

## Overview

A production-ready academic literature search tool featuring modular architecture (v4.7.0), checkpoint recovery, batch API processing, smart quality scoring fallbacks, and Claude Code integration for evidence-based research using Multi-QA MPNet embeddings. Achieves 100% build success rate with checkpoint recovery and exponential backoff retry logic.

## New Features in v4.6.1

### Checkpoint Recovery System
- **Zero Data Loss**: Automatic checkpoint saving every 50 papers during batch processing
- **Resume Capability**: Restart from exact interruption point with `.checkpoint.json` file
- **Graceful Recovery**: Handles corrupted checkpoint files with fallback to fresh start
- **Automatic Cleanup**: Checkpoint file removed on successful completion
- **Progress Tracking**: Preserves both successful and error results during processing

### API Retry Improvements
- **Exponential Backoff**: Retry delays increase exponentially (0.1s → 10s max) to prevent rate limiting
- **Fixed Import Paths**: Corrected `api_utils` import handling for both module and direct execution
- **Better Error Handling**: Distinguishes between rate limiting (429) and other API failures
- **100% Success Rate**: Eliminates v4.4-v4.6 build failures caused by API rate limiting

## New Features in v4.6

### External Paper Discovery Tool
- **Comprehensive Discovery**: New `discover.py` tool accessing 214M papers via Semantic Scholar
- **Coverage Assessment**: Traffic light system (🟢🟡🔴) evaluates KB completeness
- **Population Focus**: Automatic term expansion for elderly, pediatric, adult, women, men
- **Quality Filtering**: Basic scoring with confidence levels (HIGH/MEDIUM/LOW thresholds)
- **Study Type Filtering**: Target specific research types (RCT, systematic reviews, etc.)
- **Report Generation**: Markdown reports with Zotero-compatible DOI lists
- **Integration Workflow**: Discovery → Import → KB Update → Enhanced Search

### Batch API Processing & Production Reliability
- **Semantic Scholar Batch Endpoint**: Reduces API calls from ~2,100 to ~5 for large datasets (400x efficiency gain)
- **96.9% Enhanced Scoring Success**: Production-tested reliability with comprehensive error handling
- **Smart Fallback Architecture**: Basic scoring (study type, recency, full-text) when API unavailable
- **Automatic Quality Upgrades**: Basic scores seamlessly upgraded when API returns online
- **Venue Format Bug Fix**: Fixed critical bug handling both dict/string venue responses from API

### Enhanced Quality Score Architecture
- **Dual Scoring System**: Enhanced (API-powered) vs Basic (local metadata) scoring
- **Immediate Persistence**: Quality scores saved before embedding generation prevents data loss
- **Visual Indicators**: [Enhanced scoring] markers distinguish scoring types
- **Smart Caching**: Quality upgrades preserve embeddings (30x faster incremental builds)
- **Zero Failures**: 100% papers receive quality scores (enhanced or basic fallback)

## New Features (Unreleased)

### PragmaticSectionExtractor - Three-Tier Section Extraction System

**Purpose**: Intelligent extraction of academic paper sections with 75-80% accuracy improvement

**Architecture**:
- **Tier 1 (Fast Pattern Matching)**: Handles 65% of papers in ~2ms using ALL CAPS, Title Case, and numbered sections
- **Tier 2 (Fuzzy Enhancement)**: Additional 10% coverage using RapidFuzz for clinical formats and typos
- **Tier 3 (Structure Analysis)**: Remaining 25% using PDFPlumber to recover lost formatting

**Key Features**:
- **Improved Pattern Recognition**:
  - Case-insensitive matching for Title Case headers (65% of papers)
  - Support for numbered sections (e.g., "1. Introduction", "2. Methods")
  - Better section boundary detection to prevent content overlap
- **Abstract Extraction Fallback**:
  - 4-strategy system for papers with missing abstracts
  - Uses metadata, text patterns, and heuristics
  - Integrated into main extraction pipeline
- **Section-Specific Length Limits**:
  - Prevents over-extraction with intelligent truncation
  - Abstract limited to 5000 chars (~1000 words)
  - Methods/Results/Discussion limited to 15000 chars (~3000 words)
  - References allowed up to 50000 chars
- **Advanced Boundary Detection**:
  - Detects double newlines followed by uppercase as section boundaries
  - Handles numbered sections (1. Introduction, 2. Methods)
  - Prevents content bleeding between sections
- **Post-Processing Validation**:
  - Removes leaked section headers from content
  - Fixes section contamination (headers in wrong sections)
  - Validates minimum content requirements per section
  - Cleans and normalizes extracted text
- **Progressive Enhancement**: Fast path for easy cases, expensive operations only when needed
- **Smart Exit Conditions**: Stops early when sufficient sections found (≥4 for Tier 1, ≥3 for Tier 2)
- **Batch Processing**: Parallel execution with 4-8x speedup for multiple PDFs
- **Caching Mechanism**: MD5-based cache prevents reprocessing of unchanged PDFs
- **Graceful Fallback**: Always returns usable content, falls back to old method if unavailable
- **Production Ready**: Comprehensive error handling and validation

**Performance Characteristics**:
- Average: ~23ms per paper overall
- Tier 1: ~2ms for well-formatted papers (65%)
- Tier 2: Additional 1ms for fuzzy matching (10%)
- Tier 3: ~50ms for structure analysis (25%)
- Batch: ~52 seconds for 2,220 papers with 4 workers

**Dependencies**:
- `rapidfuzz>=3.0.0` - Fast fuzzy string matching (required for Tier 2)
- `pdfplumber>=0.9.0` - PDF structure analysis (optional but recommended for Tier 3)

**Configuration** (in `config.py`):
```python
FUZZY_THRESHOLD = 70  # Fuzzy match score threshold (lowered for better matching)
MIN_SECTION_LENGTH = {
    'abstract': 50,      # Lowered from 100 for better extraction
    'introduction': 50,  # More permissive thresholds
    'methods': 50,
    'results': 50,
    'discussion': 50,
    'conclusion': 30,
    'references': 20,
}
MAX_SECTION_LENGTH = {
    'abstract': 5000,       # ~1000 words max to prevent over-extraction
    'introduction': 10000,  # ~2000 words
    'methods': 15000,       # ~3000 words
    'results': 15000,       # ~3000 words
    'discussion': 15000,    # ~3000 words
    'conclusion': 8000,     # ~1600 words
    'references': 50000,    # Can be very long
}
TIER1_EXIT_THRESHOLD = 4  # Sections needed to exit Tier 1
TIER2_EXIT_THRESHOLD = 3  # Sections needed to exit Tier 2
SECTION_EXTRACTION_TIMEOUT = 1.0  # Max time per paper
SECTION_EXTRACTION_N_WORKERS = 4  # Parallel processing workers
```

## Previous Features (v4.0-4.5)

### Performance & Security

- **Optimized Searches**: O(1) cache lookups and dynamic batch sizing
- **Enhanced Security**: Command injection prevention, path traversal protection, safe JSON/NPY serialization
- **Optimized Batch Processing**: Dynamic sizing based on available memory (64-256 batch size)
- **Instant Cache Lookups**: Hash-based dictionary for O(1) embedding retrieval

### Multi-QA MPNet Intelligence

- **Smart Search Modes**: Auto-detects query intent (question, similar, explore)
- **Query Preprocessing**: Optimizes embeddings based on search type
- **Healthcare & Scientific Optimization**: Multi-QA MPNet model optimized for diverse question-answering including scientific literature

### Quality Assessment

- **Paper Quality Scores**: 0-100 scoring based on study type, recency, sample size
- **Quality Filtering**: `--quality-min` parameter to filter low-quality papers
- **Visual Quality Indicators**: ⭐ (80-100), ● (60-79), ○ (40-59), · (<40)

### Enhanced Features

- **Study Type Classification**: Automatically identifies systematic reviews, RCTs, cohort studies, etc.
- **RCT Sample Size Extraction**: Shows participant counts (n=487) for randomized controlled trials
- **Advanced Filtering**: Filter by publication year and study type
- **Evidence Hierarchy**: Visual markers showing study quality
- **Smart Incremental Updates**: Automatic change detection, 10x faster than full rebuild
- **Smart Section Retrieval**: 70% context reduction with intelligent section chunking
- **Sections Index**: O(1) section retrieval for instant access to paper sections
- **Integrity Checking**: Automatic detection of corrupted or duplicate paper IDs
- **Export/Import**: Portable knowledge base with tar.gz export/import

## Architecture

```
Setup Phase (once):     Zotero → Build Script → Portable KB
Runtime Phase (always): /research command → Search → Analyze → Report
```

### Module Structure (v4.7.0 - Modular Architecture)

```
src/
├── build_kb.py          # Knowledge base builder from Zotero (3,660 lines, 15% reduction from v4.6)
├── kb_quality.py        # Quality scoring module (490 lines) [NEW - v4.7]
├── kb_indexer.py        # FAISS indexing and embeddings (437 lines) [NEW - v4.7]
├── cli.py               # Command-line interface for search and retrieval
├── cli_kb_index.py      # O(1) paper lookups and index operations
├── discover.py          # External paper discovery via Semantic Scholar
├── analyze_gaps.py      # Network gap analysis CLI for literature gap discovery
├── gap_detection.py     # Core gap detection algorithms and analysis engine
├── api_utils.py         # API retry logic with exponential backoff
└── config.py            # Configuration constants and settings
```

#### Modular Architecture (v4.7.0)

The codebase has been refactored into modular components for better maintainability and testability:

- **`kb_quality.py`**: All quality scoring logic extracted from build_kb.py
  - Basic quality scoring (local metadata only)
  - Enhanced quality scoring (with Semantic Scholar API)
  - Component scoring functions (citations, venue, authors, etc.)
  - Custom exception: `QualityScoringError`
  - Supports both standalone operation and integration with build_kb.py

- **`kb_indexer.py`**: FAISS indexing and embedding generation
  - `KBIndexer` class handles all FAISS operations
  - Multi-QA MPNet embedding model management
  - GPU/CPU device detection and optimization
  - Embedding cache management for performance
  - Index creation and incremental updates
  - Custom exception: `EmbeddingGenerationError`
  - Methods: `generate_embeddings()`, `create_index()`, `update_index_incrementally()`

- **`api_utils.py`**: Centralized API handling
  - Exponential backoff retry logic
  - Rate limiting management
  - Checkpoint recovery support

**Benefits of v4.7.0 Architecture**:
- **Easier debugging**: Separated concerns allow focused troubleshooting
- **Faster development**: Modular code enables parallel development
- **Better test isolation**: Each module can be tested independently
- **Reduced cognitive load**: Smaller, focused files (~500 lines each vs 4,293 lines)

## Data Structure

```
kb_data/
├── index.faiss              # Semantic search index (~15KB for 2146 papers)
├── metadata.json            # Paper metadata with model version (~4MB)
├── sections_index.json      # Section locations for smart retrieval (~7KB)
├── .pdf_text_cache.json     # PDF extraction cache (metadata-based, ~156MB)
├── .embedding_cache.json    # Embedding metadata (hashes, model info)
├── .embedding_data.npy      # Embedding vectors (safe NPY format)
├── .fingerprint_cache.json  # Content fingerprints for change detection
├── papers/                  # Individual paper markdown files
│   ├── paper_0001.md        # Full text in markdown (4-digit IDs)
│   ├── paper_0002.md        # One file per paper
│   └── ...                  # 2146 files
exports/                     # User-valuable analysis and exports
├── analysis_pdf_quality.md  # Unified PDF quality analysis
├── search_*.csv             # Search result exports
├── paper_*.md               # Individual paper exports
└── gap_analysis_YYYY_MM_DD.md # Network gap analysis reports with DOI lists

reviews/                     # Literature review reports
└── *.md                     # Generated by /research command

system/                      # Development and system artifacts
└── dev_*.csv                # Test results and system data
```

**Security Note**: v4.0 uses safe JSON/NPY format instead of pickle serialization

## Core Modules

### O(1) Paper Index (`cli_kb_index.py`)

**Purpose**: Provides constant-time paper lookups to avoid O(n) searches

**Features**:
- Dictionary-based ID to index mapping
- Paper lookup by ID or FAISS index
- Author search with partial matching
- Year range filtering
- Consistency validation

**Usage**:
```python
from cli_kb_index import KnowledgeBaseIndex

kb_index = KnowledgeBaseIndex()
paper = kb_index.get_paper_by_id("0042")  # O(1) lookup
papers = kb_index.search_by_author("Smith")  # Author search
papers = kb_index.search_by_year_range(2020, 2024)  # Year filter
```

## Implementation

### 1. Knowledge Base Builder (`build_kb.py`)

**Purpose**: One-time conversion of Zotero library to portable format

**Process**:

1. Extract papers from Zotero (local API)
2. Convert PDFs to markdown files (with caching)
3. Build FAISS index from title+abstract embeddings using Multi-QA MPNet
4. Save metadata as JSON

**Features**:

- Multi-QA MPNet embeddings optimized for healthcare and scientific literature (sentence-transformers/multi-qa-mpnet-base-dot-v1)
- Automatic study type classification (RCTs, systematic reviews, cohort studies, etc.)
- RCT sample size extraction (n=487)
- PyMuPDF for fast PDF text extraction (estimated ~13 papers/second with cache)
- Metadata-based caching with automatic backups
- `--clear-cache` flag for fresh extraction

**Usage**:

```bash
python build_kb.py              # Smart incremental update (default)
python build_kb.py --rebuild    # Force complete rebuild
python build_kb.py --clear-cache # Clear caches and rebuild
python build_kb.py --demo       # Quick demo with 5 papers
python build_kb.py --export kb_backup.tar.gz  # Export knowledge base
python build_kb.py --import kb_backup.tar.gz  # Import knowledge base
```

### 2. CLI Tool (`cli.py`)

**Commands**:

```bash
python cli.py search "query"              # Basic search with Multi-QA MPNet embeddings
python cli.py search "query" --after 2020  # Filter by year
python cli.py search "query" --type rct --type systematic_review  # Filter by study type
python cli.py search "query" --show-quality --quality-min 70  # Quality filtering
python cli.py search "query" --mode question  # Optimize for research questions
python cli.py get <paper_id>              # Returns full paper text
python cli.py smart-search "query" -k 30        # Smart search with automatic chunking
python cli.py get <paper_id> --sections abstract methods results  # Specific sections
python cli.py info                        # Check knowledge base status
python cli.py cite 0001 0002 0003         # Generate IEEE citations for specific papers
```

### 3. External Paper Discovery Tool (`discover.py`)

**Purpose**: Discover external papers using Semantic Scholar's comprehensive database

**Key Features**:

- **214M Paper Database**: Access to Semantic Scholar's complete academic corpus
- **Coverage Assessment**: Traffic light system (🟢🟡🔴) evaluating KB completeness
- **Population-Specific Discovery**: Automatic keyword expansion for target populations
- **Quality Filtering**: Basic scoring with HIGH/MEDIUM/LOW confidence thresholds
- **Study Type Filtering**: Focus on specific research methodologies
- **Rate Limiting**: Proactive 1 RPS limiting respecting API constraints

**Usage**:

```bash
python discover.py --keywords "diabetes,mobile health"                   # Basic discovery
python discover.py --keywords "AI,diagnostics" --quality-threshold HIGH # High-quality only
python discover.py --keywords "telemedicine" --population-focus elderly # Population-specific
python discover.py --coverage-info                                      # Coverage guidance
```

**Architecture**:

1. **Query Generation**: Builds comprehensive OR queries from keywords and population terms
2. **Paper Discovery**: Executes Semantic Scholar API calls with rate limiting
3. **Analysis & Reporting**: Applies basic quality scoring and generates markdown reports

**Integration Workflow**: Discovery → Zotero Import → KB Update → Enhanced Search

### 4. Network Gap Analysis System (`analyze_gaps.py` & `gap_detection.py`)

**Purpose**: Systematic identification of literature gaps through network analysis

**Architecture Overview**:

The gap analysis system implements a two-phase algorithm approach designed for comprehensive literature discovery with optimal resource utilization.

**Core Components**:

1. **analyze_gaps.py** - Command-line interface and orchestration
   - **KB Validation**: Comprehensive requirement checking with fail-fast error handling
   - **Workflow Orchestration**: Sequential algorithm execution with progress tracking
   - **Report Generation**: Structured markdown output with DOI lists for Zotero import
   - **CLI Interface**: Rich help system with parameter validation and usage examples

2. **gap_detection.py** - Core analysis algorithms and caching system
   - **Citation Network Analysis**: Primary algorithm identifying papers cited by KB but missing
   - **Simplified Author Networks**: Secondary algorithm finding recent work from KB authors
   - **Adaptive Rate Limiting**: Token bucket implementation with exponential backoff
   - **Response Caching**: 7-day TTL cache reducing API dependency and enabling rapid re-analysis
   - **Confidence Scoring**: HIGH/MEDIUM/LOW classification based on citation patterns and recency

**Phase 1 Implementation** (Current):
- **Citation Networks**: Highest ROI algorithm with clear relevance signals
- **Author Networks**: Simplified approach using existing Semantic Scholar author IDs from KB
- **Performance**: 15-25 minutes for 2000-paper KB with <2GB memory usage

**Key Features**:

- **Two-Part Workflow Integration**:
  - **Part 1**: One-time baseline analysis after KB building (analyze_gaps.py)
  - **Part 2**: Research-driven discovery during active research (/research → /doi)
- **Production-Ready Reliability**: Comprehensive error handling with actionable error messages
- **Semantic Scholar Integration**: ~1 API request per KB paper + ~1 per 10 unique authors
- **Smart Caching**: 7-day response cache enables rapid re-analysis and development iterations
- **DOI List Generation**: Zotero-compatible bulk import format organized by gap type

**Usage Examples**:

```bash
python src/analyze_gaps.py                          # Comprehensive analysis
python src/analyze_gaps.py --min-citations 50      # High-impact papers only
python src/analyze_gaps.py --year-from 2020        # Recent author work
python src/analyze_gaps.py --limit 100             # Top 100 gaps by priority
```

**Algorithm Details**:

- **Citation Network Analysis**:
  - Analyzes reference lists from KB papers
  - Identifies frequently cited papers missing from collection
  - Confidence scoring based on citation frequency and KB relevance
  - Filters by citation count threshold for quality control

- **Author Network Analysis**:
  - Uses existing Semantic Scholar author IDs from KB metadata
  - Discovers recent publications from known researchers
  - Year-based filtering for recency vs comprehensiveness control
  - No author disambiguation needed due to existing ID infrastructure

**Output Structure**:
- Executive summary with gap counts and priority breakdown
- Detailed gap descriptions with confidence scores and relevance explanations
- Complete DOI lists organized by gap type for bulk Zotero import
- Step-by-step import instructions and workflow integration guidance

**Study Type Categories:**

- `systematic_review` - Systematic reviews and meta-analyses (⭐)
- `rct` - Randomized controlled trials (●)
- `cohort` - Cohort studies (◐)
- `case_control` - Case-control studies (○)
- `cross_sectional` - Cross-sectional studies (◔)
- `case_report` - Case reports and series (·)
- `study` - Generic/unclassified studies (·)

### 5. Claude Slash Command

#### How Slash Commands Work in Claude Code

Slash commands are custom commands that extend Claude's capabilities. They are defined as markdown files in the `.claude/commands/` directory and are automatically discovered by Claude Code.

**Key Concepts:**

- **Location**: Place command files in `.claude/commands/` (project-level) or `~/.claude/commands/` (user-level)
- **Format**: Markdown files with optional YAML frontmatter
- **Variables**: `$ARGUMENTS` contains everything typed after the command
- **Execution**: Lines starting with `!` run as bash commands
- **File Access**: `@filename` reads file contents into context

#### Creating the Research Command

**File**: `.claude/commands/research.md`

```markdown
---
description: Research literature using local knowledge base
argument-hint: <topic>
---

Research the topic: $ARGUMENTS

Use the CLI to search papers, analyze the most relevant ones, and generate a comprehensive report with IEEE-style citations.
```

**How It Works:**

1. User types: `/research digital health barriers`
2. Claude Code loads the command file
3. Replaces `$ARGUMENTS` with "digital health barriers"
4. Claude executes the instructions
5. Claude uses available tools (Bash, Read, Write) to complete the task

## Data Formats

### metadata.json

```json
{
  "papers": [
    {
      "id": "0001",                    // 4-digit format (v4.0)
      "doi": "10.1234/example",
      "title": "Paper Title",
      "authors": ["Smith J", "Doe A"],
      "year": 2023,
      "journal": "Nature",
      "volume": "500",
      "issue": "7461",
      "pages": "190-195",
      "abstract": "Abstract text...",
      "study_type": "rct",
      "sample_size": 487,
      "has_full_text": true,
      "filename": "paper_0001.md",      // 4-digit format
      "zotero_key": "ABC123",           // For cache tracking
      "pdf_info": {                     // PDF metadata for caching
        "size": 1234567,
        "mtime": 1642256400.0
      }
    }
  ],
  "total_papers": 2146,
  "last_updated": "2025-08-19T14:42:00Z",
  "embedding_model": "sentence-transformers/multi-qa-mpnet-base-dot-v1", // Healthcare & scientific embeddings
  "model_version": "Multi-QA MPNet",        // Optimized for healthcare & scientific literature
  "embedding_dimensions": 768,
  "version": "4.0"
}
```

### papers/paper_0001.md

```markdown
# Paper Title

**Authors:** Smith J, Doe A
**Year:** 2023
**Journal:** Nature
**Volume:** 500
**Issue:** 7461
**Pages:** 190-195
**DOI:** 10.1234/example

## Abstract
[Abstract text]

## Full Text
[Complete paper content converted from PDF]
```

## Workflow

### User Experience

1. User types: `/research digital health interventions`
2. Claude searches knowledge base
3. Claude analyzes top 10-20 relevant papers
4. Claude generates research report with findings

### Technical Flow

1. **Search Phase**: Query → FAISS → Relevant paper IDs
2. **Retrieval Phase**: Read markdown files for selected papers
3. **Analysis Phase**: Claude evaluates evidence quality and extracts findings
4. **Report Phase**: Generate structured report with citations

## Research Report Format

```markdown
# Research Report: [Topic]
Date: [YYYY-MM-DD]

## Executive Summary
[Brief overview of findings]

## Key Findings
1. [Finding] [1], [2]
2. [Finding] [3]-[5]
3. [Finding] [6]

## Evidence Quality
- High confidence: [Topics with strong evidence]
- Medium confidence: [Topics with moderate evidence]
- Low confidence: [Topics needing more research]

## References (IEEE Style)
[1] J. Smith and A. Doe, "Paper Title," Nature, vol. 500, no. 7461, pp. 190-195, 2023.
[2] M. Johnson et al., "Another Paper," Science, vol. 380, no. 6641, pp. 123-128, 2024.
[3] L. Williams, "Study Title," IEEE Trans. Med. Imaging, vol. 42, no. 3, pp. 678-690, Mar. 2023.
```

### IEEE Citation Format

The system formats citations as:

```
[#] Author(s), "Title," Journal, vol. X, no. Y, pp. ZZZ-ZZZ, Month Year.
```

**In-text citations**: Use bracketed numbers [1], [2], [3]
**Multiple citations**: Use ranges [1]-[3] or lists [1], [4], [7]

## Testing

### Test Organization

The project includes comprehensive test coverage with 469 tests organized by type (updated for v4.7.0):

```
tests/
├── unit/                           # Component tests (200+ tests)
│   ├── test_unit_api_utils.py          # API retry logic (10 tests) - NEW in v4.6.1
│   ├── test_unit_citation_system.py    # IEEE citation formatting
│   ├── test_unit_cli_interface.py      # CLI utility functions
│   ├── test_unit_knowledge_base.py     # KB building, indexing, caching (updated for v4.7.0 modules)
│   ├── test_unit_quality_scoring.py    # Paper quality algorithms (tests kb_quality.py)
│   └── test_unit_search_engine.py      # Search, embedding, ranking (tests kb_indexer.py)
├── integration/                    # Workflow tests (120+ tests)
│   ├── test_integration_checkpoint_recovery.py  # Checkpoint system (9 tests) - NEW in v4.6.1
│   ├── test_integration_batch_operations.py     # Batch command workflows
│   ├── test_integration_kb_building.py          # KB building processes (updated for modular architecture)
│   ├── test_integration_incremental_updates.py  # Incremental update workflows (tests KBIndexer)
│   └── test_integration_search_workflow.py      # Search workflows
├── e2e/                           # End-to-end tests (23 tests)
│   ├── test_e2e_cite_command.py        # Citation command E2E
│   └── test_e2e_cli_commands.py        # Core CLI commands E2E
└── performance/                   # Benchmarks (10+ tests)
    └── test_performance_benchmarks.py   # Speed and memory tests (updated for KBIndexer)
```

**Total**: 469 tests covering all major functionality including modular architecture (v4.7.0), checkpoint recovery, and API retry logic

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_critical.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Quality Checks

```bash
# Type checking
mypy src/

# Linting
ruff check src/ tests/

# Auto-fix issues
ruff check src/ tests/ --fix
```

## Technical Specifications

### Dependencies

- `faiss-cpu`: Semantic search
- `sentence-transformers`: Multi-QA MPNet embeddings for healthcare and scientific papers
- `transformers`: Required by sentence-transformers
- `torch`: Deep learning framework for Multi-QA MPNet (GPU support if available)
- `PyMuPDF`: Fast PDF text extraction (significantly faster than pdfplumber)
- `click`: CLI framework
- `tqdm`: Progress bars
- `requests`: Zotero API access

### Performance Characteristics (v4.6)

- **KB build**: Adaptive rate limiting with real checkpoint recovery
  - Initial build: ~17 minutes for 2,000+ papers (sequential quality scoring)
  - Adaptive delays: 100ms → 500ms+ after 400 papers
  - Real checkpoint system: Resume from exact interruption point with zero data loss
  - Quality scores saved to disk every 50 papers during processing
  - Smart incremental updates: ~10x faster than full rebuild
  - Cache utilization: Dramatically reduces rebuild time
  - O(1) embedding cache lookups via hash-based dictionary
- **Reliability**: 100% build success rate vs 0% in v4.4 parallel approach
- **Search**: Sub-second response times for most queries
  - O(1) paper lookups by ID using dictionary index
  - FAISS provides log(n) similarity search
- **Storage**: Current KB (2146 papers): ~305MB total
  - Papers: ~145MB markdown files
  - PDF cache: ~156MB cached text
  - Metadata: ~4MB JSON
  - Index: ~15KB FAISS vectors
- **Cache efficiency**: Persistent across sessions
  - PDF text cache avoids re-extraction
  - Embedding cache preserves computed vectors
  - Fingerprint cache enables change detection

### Embedding Model

- **Model**: sentence-transformers/multi-qa-mpnet-base-dot-v1 (current implementation)
- **Dimensions**: 768
- **Context**: 512 tokens (processes title + abstract)
- **Advantages**: Optimized for diverse question-answering including healthcare and scientific literature
- **GPU Support**: Automatic detection, 10x speedup when available
- **Current implementation**: Uses Multi-QA MPNet model consistently

## Advantages of This Approach

1. **Portable**: Copy kb_data/ folder anywhere
2. **Evidence-Based**: Automatic study type classification and quality indicators
3. **No Runtime Dependencies**: Doesn't need Zotero after setup
4. **Fast**: O(1) lookups, direct file access with advanced filtering
5. **Offline**: Works without internet
6. **Version Control**: Text files can be tracked in git
7. **Visual Hierarchy**: Clear markers showing evidence quality (⭐ for reviews, ● for RCTs)
8. **Debuggable**: Can manually read/edit papers
9. **Maintainable**: Clean module separation with focused responsibilities (v4.7.0 modular architecture)
10. **Well-Tested**: 469 tests covering all major functionality including modular components
11. **Modular (v4.7.0)**: Separated quality scoring and indexing for easier debugging and development

## Command Usage Analytics & Logging

### Architecture
- **Centralized Logging**: `cli.py` provides `_log_command_usage_event()` function used across all modules
- **JSON Structured Format**: JSONL format with timestamp, session ID, and event metadata
- **Daily Rotation**: Log files named `command_usage_YYYYMMDD.jsonl` for organized storage
- **Privacy Protection**: Smart error sanitization removes sensitive patterns while preserving debug value

### Event Structure
```json
{
  "timestamp": "2025-08-23T15:30:02.031508+00:00",
  "session_id": "5eec012e",
  "level": "INFO",
  "event_type": "command_success",
  "module": "cli",
  "command": "search",
  "execution_time_ms": 83,
  "results_found": 10
}
```

### Event Types
- **Generic Events**: `command_start`, `command_success`, `command_error` across all modules
- **Module Context**: `"module": "cli"` or `"module": "discover"` for clear attribution
- **Session Tracking**: 8-character session IDs for workflow correlation
- **Performance Metrics**: Execution time, result counts, error diagnostics

### Privacy Features
- **Smart Sanitization**: Removes file paths (`<path>/file.py`), API keys (`<redacted>`), emails (`<email>`)
- **Intelligent Truncation**: 500-character limit after sanitization (preserves more debug info than simple truncation)
- **Local Only**: No external transmission, automatically disabled during testing
- **Pattern Matching**: Regex-based removal of sensitive data patterns

### Usage Patterns Tracked
- **Command Usage**: Frequency, parameters, execution time, success rates
- **Search Patterns**: Query types, result counts, filter usage, export requests
- **Error Analysis**: Failure patterns, user workflow interruptions, recovery paths
- **Performance Monitoring**: Response times, resource usage, optimization opportunities

## Error Handling

- **Missing KB**: "Knowledge base not found. Run build_kb.py first."
- **Version Mismatch**: "Knowledge base version 3.x detected. Please rebuild with: rm -rf kb_data && python src/build_kb.py"
- **No results**: "No relevant papers found. Try broader search terms."
- **File errors**: Gracefully skip corrupted files, log issues
- **Invalid Paper ID**: Validates 4-digit format, prevents path traversal
- **Cache Corruption**: Automatic detection and recovery
