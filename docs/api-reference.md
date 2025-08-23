# API Reference

> **Navigation**: [Home](../README.md) | [Technical Specs](technical-specs.md) | [Advanced Usage](advanced-usage.md)

## Table of Contents

### Search & Analysis

- [`search`](#clipy-search) - Semantic search with Multi-QA MPNet embeddings
- [`smart-search`](#clipy-smart-search) - Smart search with automatic section chunking
- [`get`](#clipy-get) - Retrieve full papers or sections
- [`get-batch`](#clipy-get-batch) - Retrieve multiple papers efficiently
- [`batch`](#clipy-batch) - Execute multiple commands efficiently
- [`cite`](#clipy-cite) - Generate IEEE citations
- [`author`](#clipy-author) - Search papers by author name

### Knowledge Base

- [`info`](#clipy-info) - Display KB information
- [`diagnose`](#clipy-diagnose) - Check KB health and integrity
- [`build_kb.py`](#build_kbpy) - Build/update knowledge base
- [`analyze_gaps.py`](#analyze_gapspy) - Network gap analysis with executive dashboard (v4.7 - production-ready)
- [`discover.py`](#discoverpy) - Discover external papers via Semantic Scholar

### Slash Commands

- [`/research`](#research-slash-command) - Comprehensive literature research and review generation
- [`/discover`](#discover-slash-command) - Gap-based external paper discovery via Semantic Scholar

### Data Structure & System

- [KB Data Directory](#kb-data-directory-structure) - Complete folder structure
- [Data Formats](#data-formats) - File specifications
- [Cache Files](#cache-files) - Performance optimization files
- [Error Codes](#error-codes) - Troubleshooting
- [Formatting System](#formatting-system) - Unified error, help, and output formatting

---

## CLI Commands

### `cli.py search`

Search the knowledge base for relevant papers with Multi-QA MPNet embeddings.

```bash
python src/cli.py search [OPTIONS] QUERY
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--top-k` | `-k` | INT | 10 | Number of results to return |
| `--verbose` | `-v` | FLAG | False | Show abstracts in results |
| `--show-quality` | | FLAG | False | Display quality scores (0-100) |
| `--json` | | FLAG | False | Output results as JSON |
| `--after` | | INT | None | Filter papers published after this year |
| `--type` | | MULTI | None | Filter by study type (can specify multiple) |
| `--group-by` | | CHOICE | None | Group results by year/journal/study_type |
| `--years` | | STRING | None | Filter by year range (e.g., 2020-2024 or 2023) |
| `--contains` | | STRING | None | Filter by term in title/abstract |
| `--exclude` | | STRING | None | Exclude papers with this term |
| `--full-text` | | FLAG | False | Search in full text (slower but comprehensive) |
| `--queries` | | MULTI | None | Additional search queries for comprehensive results |
| `--min-quality` | | INT | None | Minimum quality score (0-100) |
| `--export` | | PATH | None | Export results to CSV file |

#### Study Type Filters

- `systematic_review` - Systematic reviews and meta-analyses (⭐)
- `rct` - Randomized controlled trials (●)
- `cohort` - Cohort studies (◐)
- `case_control` - Case-control studies (○)
- `cross_sectional` - Cross-sectional studies (◔)
- `case_report` - Case reports and series (·)
- `study` - Generic/unclassified studies (·)

#### Enhanced Quality Scores

Papers are scored 0-100 using Semantic Scholar API integration:

**API-powered factors (60 points):**
- Citation Impact: 25 points (based on citation count and growth)
- Venue Prestige: 15 points (journal ranking and reputation)
- Author Authority: 10 points (H-index and research standing)
- Cross-validation: 10 points (DOI, PubMed, publication types)

**Core factors (40 points):**
- Study Type: 20 points (systematic review > RCT > cohort > case report)
- Recency: 10 points (publication year relevance)
- Sample Size: 5 points (statistical power indicator)
- Full Text: 5 points (complete content availability)

**Visual indicators:**

- 🌟 Exceptional (90-100): High-impact systematic reviews/meta-analyses
- ⭐ Excellent (80-89): Top-tier venues, highly cited
- ● Very Good (70-79): Quality RCTs, established venues
- ◐ Good (60-69): Solid studies, decent citations
- ○ Moderate (50-59): Cohort studies, emerging work
- · Basic (0-49): Case reports, limited validation

#### Examples

```bash
# Basic search
python src/cli.py search "digital health"

# With quality scores
python src/cli.py search "diabetes" --show-quality

# High-quality evidence only
python src/cli.py search "metabolic syndrome" --min-quality 70 --show-quality

# Comprehensive review with quality scores
python src/cli.py search "AI diagnosis" -k 30 --show-quality --after 2020

# Filter by study type and quality
python src/cli.py search "diabetes" --type systematic_review --type rct --min-quality 60

# Year range filtering
python src/cli.py search "telemedicine" --years 2020-2024

# Term filtering
python src/cli.py search "cancer" --contains "immunotherapy" --exclude "pediatric"

# Full text search
python src/cli.py search "methods" --full-text --contains "LSTM"

# Multi-query comprehensive search
python src/cli.py search "diabetes" --queries "glucose monitoring" --queries "insulin therapy"

# Group results by year
python src/cli.py search "AI healthcare" --group-by year

# Export to CSV
python src/cli.py search "hypertension" --export results.csv

# JSON output with quality scores
python src/cli.py search "wearables" --json --show-quality > results.json
```

### `cli.py get`

Retrieve the full text of a specific paper or specific sections. All sections are preserved in complete form with zero information loss.

```bash
python src/cli.py get [OPTIONS] PAPER_ID
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | PATH | None | Save output to file (saves to exports/ directory) |
| `--sections` | `-s` | MULTI | all | Specific sections to retrieve |
| `--add-citation` | | FLAG | False | Append IEEE citation to paper content |

#### Available Sections

All sections are extracted with complete content preservation - no truncation applied:

- `abstract` - Paper abstract (complete)
- `introduction` - Introduction/background (complete)
- `methods` - Methods/methodology (complete - full intervention descriptions)
- `results` - Results/findings (complete - all outcome data)
- `discussion` - Discussion section (complete)
- `conclusion` - Conclusions (complete)
- `references` - Bibliography
- `all` - Complete paper (default)

#### Paper ID Format

**Security Note**: Paper IDs must be exactly 4 digits (e.g., 0001, 0234, 1999)

- Path traversal attempts are blocked
- Invalid formats raise clear error messages
- IDs are zero-padded (1 becomes 0001)

#### Examples

```bash
# Display full paper in terminal
python src/cli.py get 0001

# Get specific sections only
python src/cli.py get 0001 --sections abstract methods results
python src/cli.py get 0001 --sections introduction discussion

# Save to file
python src/cli.py get 0001 -o paper.md
python src/cli.py get 0001 --output my_paper.md

# Multiple sections
python src/cli.py get 0042 -s abstract -s methods -s conclusion

# With IEEE citation
python src/cli.py get 0001 --add-citation
python src/cli.py get 0001 --sections abstract --add-citation

# Invalid formats (blocked)
python src/cli.py get 1        # Error: Must be 4 digits
python src/cli.py get abc      # Error: Must be 4 digits
python src/cli.py get ../etc   # Error: Invalid format
```

### `cli.py get-batch`

Retrieve multiple papers by their IDs in a single batch operation.

```bash
python src/cli.py get-batch [OPTIONS] PAPER_IDS...
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format` | CHOICE | text | Output format (text or json) |
| `--add-citation` | FLAG | False | Append IEEE citation to each paper (numbered sequentially) |

**Note**: `get-batch` retrieves complete papers and does NOT support the `--sections` flag. To get specific sections from multiple papers, use the batch command with individual get commands.

#### Examples

```bash
# Get multiple papers
python src/cli.py get-batch 0001 0002 0003

# Get specific papers
python src/cli.py get-batch 0234 1426 0888

# JSON output for processing
python src/cli.py get-batch 0001 0002 --format json

# With numbered IEEE citations
python src/cli.py get-batch 0001 0002 0003 --add-citation

# JSON format with citations
python src/cli.py get-batch 0001 0002 --format json --add-citation

# Many papers at once
python src/cli.py get-batch 0010 0020 0030 0040 0050
```

### `cli.py batch`

Execute multiple commands efficiently with a single model load for 10-20x performance improvement.

```bash
python src/cli.py batch [OPTIONS] [INPUT]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--preset` | CHOICE | None | Use workflow preset (research, review, author-scan) |
| `--output` | CHOICE | json | Output format (json or text) |

#### Preset Workflows

- **research**: Comprehensive topic analysis with 5 searches + top 10 papers
- **review**: Focus on systematic reviews and meta-analyses
- **author-scan**: Get all papers by author with abstracts

#### Command Structure

Commands are provided as JSON with the following structure:

```json
[
  {"cmd": "search", "query": "topic", "k": 10, "show_quality": true},
  {"cmd": "get", "id": "0001", "sections": ["abstract", "methods"]},
  {"cmd": "smart-search", "query": "topic", "k": 30},
  {"cmd": "cite", "ids": ["0001", "0002", "0003"]},
  {"cmd": "author", "name": "Smith J", "exact": true}
]
```

#### Meta-Commands

Special commands that operate on previous results:

- **merge**: Combine and deduplicate all previous search results
- **filter**: Filter by quality score or year
- **auto-get-top**: Automatically fetch top N papers from searches
- **auto-get-all**: Fetch all papers from author search

#### Examples

```bash
# Use research preset for comprehensive analysis
python src/cli.py batch --preset research "diabetes management"

# Use review preset for systematic reviews
python src/cli.py batch --preset review "hypertension"

# Custom batch from JSON file
python src/cli.py batch commands.json

# Pipe commands from stdin
echo '[{"cmd":"search","query":"AI healthcare","k":20}]' | python src/cli.py batch -

# Complex batch with meta-commands
echo '[
  {"cmd": "search", "query": "diabetes", "k": 30, "show_quality": true},
  {"cmd": "search", "query": "diabetes treatment", "k": 20},
  {"cmd": "merge"},
  {"cmd": "filter", "min_quality": 70},
  {"cmd": "auto-get-top", "limit": 10}
]' | python src/cli.py batch -

# Text output format
python src/cli.py batch --preset research "COVID-19" --output text
```

#### Performance

- **Individual commands**: ~4-5 seconds per command (model reload each time)
- **Batch command**: 5-6 seconds total for entire workflow
- **Speedup**: 3-20x faster depending on number of operations

### `cli.py author`

Find all papers by a specific author.

```bash
python src/cli.py author [OPTIONS] AUTHOR_NAME
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--exact` | FLAG | False | Exact match only (case-sensitive) |

#### Examples

```bash
# Find all papers by Smith (partial match)
python src/cli.py author "Smith"

# Find specific author
python src/cli.py author "John Smith"

# Exact match only
python src/cli.py author "Zhang" --exact

# Partial match (default)
python src/cli.py author "Lee"
```

### `cli.py smart-search`

Smart search with automatic section chunking to handle 20+ papers without context overflow.

```bash
python src/cli.py smart-search [OPTIONS] QUERY_TEXT
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--top-k` | `-k` | INT | 20 | Number of papers to retrieve |
| `--max-tokens` | | INT | 10000 | Max tokens to load (~40k chars) |
| `--sections` | `-s` | MULTI | auto | Sections to prioritize |

#### Section Prioritization

The system automatically prioritizes sections based on query:

- Methods queries: Prioritizes methods, abstract
- Results queries: Prioritizes results, conclusion, abstract
- Review queries: Prioritizes abstract, conclusion, discussion
- Default: Abstract, introduction, conclusion

#### Examples

```bash
# Smart search with chunking (handles 20+ papers)
python src/cli.py smart-search "diabetes treatment methods" -k 30

# Prioritize specific sections
python src/cli.py smart-search "clinical outcomes" --sections results conclusion
python src/cli.py smart-search "methodology" -s methods -s abstract

# High token limit for comprehensive analysis
python src/cli.py smart-search "AI healthcare" --max-tokens 20000

# Automatic section detection
python src/cli.py smart-search "how to implement LSTM"  # Prioritizes methods
python src/cli.py smart-search "treatment outcomes"      # Prioritizes results
```

Output is sent to stdout as JSON for further processing.

### `cli.py cite`

Generate IEEE-style citations for specific papers by their IDs.

```bash
python src/cli.py cite [OPTIONS] PAPER_IDS...
```

#### Arguments

- `PAPER_IDS`: One or more 4-digit paper IDs (e.g., 0001, 0234, 1426)

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format` | CHOICE | text | Output format (text or json) |

#### Examples

```bash
# Generate citations for specific papers
python src/cli.py cite 0001 0002 0003

# Generate citations with JSON output
python src/cli.py cite 0234 1426 --format json

# Generate a single citation
python src/cli.py cite 0042
```

#### Output

- **Text format (default)**: Formatted IEEE citations with sequential numbering
- **JSON format**: Structured data with citations, errors, and count

### `cli.py info`

Display comprehensive information about the knowledge base.

```bash
python src/cli.py info
```

#### Output includes

- Total number of papers
- Last update timestamp
- KB version (should be 4.0)
- Storage location (absolute path)
- Index file size
- Papers directory size
- Sample paper listings

#### Example

```bash
$ python src/cli.py info

Knowledge Base Information
==================================================
Total papers: 2150
Last updated: 2025-08-19T19:42:19.834831+00:00
Version: 4.0
Location: /home/user/research-assistant/kb_data
Index size: 15.2 MB
Papers: 2150 files, 152.0 MB

Sample papers:
  - [0001] Digital Health Interventions for Depression...
  - [0002] Barriers to Digital Health Adoption...
  - [0003] Artificial Intelligence in Clinical Decision...
  - [0004] Telemedicine Effectiveness During COVID-19...
  - [0005] Wearable Devices for Continuous Health...
```

### `cli.py diagnose`

Run comprehensive health checks on the knowledge base.

```bash
python src/cli.py diagnose
```

#### Checks performed

- KB directory exists
- Metadata file present and valid
- FAISS index file exists
- Papers directory exists
- Version compatibility (v4.0)
- Total paper count
- Sequential ID validation (warns about gaps)
- File consistency checks

#### Example

```bash
$ python src/cli.py diagnose

Knowledge Base Diagnostics
==================================================
✓ KB exists
✓ Metadata present
✓ Index present
✓ Papers directory
✓ Version 4.0
✓ Papers: 2150
✓ Sequential IDs

✅ Knowledge base is healthy
```

If there are issues:

```bash
✗ Version 4.0
⚠️  Knowledge base version mismatch
   Run: python src/build_kb.py --rebuild
```

## Build Script

### `build_kb.py`

Build and maintain knowledge base from Zotero library for semantic search.

**DEFAULT BEHAVIOR (SAFE-BY-DEFAULT):**
- No KB exists → Full build from Zotero library
- KB exists → Safe incremental update (only new/changed papers)
- Connection errors → Safe exit with guidance (never auto-rebuild)
- Automatically detects: new papers, updated PDFs, deleted papers

**SAFETY FEATURES:**
- Never automatically rebuilds on errors (preserves existing data)
- Requires explicit --rebuild flag for destructive operations
- Multi-layer cache preservation during all operations
- Safe error handling with clear user guidance

**FEATURES:**
- **Adaptive Rate Limiting (v4.6)**: Smart delays that adjust to API throttling patterns
- **Real Checkpoint System**: Quality scores saved to disk every 50 papers with automatic recovery
- **True Recovery**: Resume processing from exact point of interruption
- **Zero Data Loss**: All completed work preserved even during process interruptions
- Extracts full text from PDF attachments in Zotero
- Generates Multi-QA MPNet embeddings optimized for healthcare & scientific papers
- Creates FAISS index for ultra-fast similarity search
- Detects study types (RCT, systematic review, cohort, etc.)
- Extracts sample sizes from RCT abstracts
- Aggressive caching for faster rebuilds
- Generates reports for missing/small PDFs
- **Auto-prompts gap analysis after successful builds** (≥20 papers with enhanced scoring)

**GENERATED REPORTS**:
- `exports/analysis_pdf_quality.md` - Comprehensive analysis of missing and small PDFs
- `exports/gap_analysis_YYYY_MM_DD.md` - Literature gap analysis with DOI lists for Zotero import
- `reviews/*.md` - Literature review reports from /research command

**REQUIREMENTS:**
- Zotero must be running (for non-demo builds)
- Enable "Allow other applications" in Zotero Settings → Advanced
- PDFs should be attached to papers in Zotero

```bash
python src/build_kb.py [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--demo` | FLAG | False | Build demo KB with 5 sample papers (no Zotero needed) |
| `--rebuild` | FLAG | False | Force complete rebuild, ignore existing KB and cached data |
| `--api-url` | STRING | http://localhost:23119/api | Custom Zotero API URL for WSL/Docker |
| `--knowledge-base-path` | PATH | kb_data | Directory to store KB files |
| `--zotero-data-dir` | PATH | ~/Zotero | Path to Zotero data folder with PDFs |
| `--export` | PATH | None | Export KB to tar.gz for backup/sharing (e.g., my_kb.tar.gz) |
| `--import` | PATH | None | Import KB from tar.gz archive (replaces existing KB) |

#### Build Modes

1. **Default (Safe Incremental)**: Detects changes and only processes new/updated papers, never auto-rebuilds on errors
2. **Rebuild**: Forces complete reconstruction of the knowledge base (destructive, requires explicit flag)
3. **Demo**: Creates a 5-paper demo KB for testing

#### Examples

```bash
# Smart incremental update (default)
python src/build_kb.py

# Build demo database for testing
python src/build_kb.py --demo

# Force complete rebuild
python src/build_kb.py --rebuild

# WSL with Windows Zotero
python src/build_kb.py --api-url http://172.20.1.1:23119/api

# Custom paths
python src/build_kb.py --knowledge-base-path /data/kb --zotero-data-dir /mnt/c/Users/name/Zotero

# Export knowledge base for backup/sharing
python src/build_kb.py --export kb_backup_$(date +%Y%m%d).tar.gz

# Import knowledge base on another machine
python src/build_kb.py --import kb_backup.tar.gz
```

#### Process Flow (v4.6)

1. **Connection**: Connects to Zotero via local API (port 23119)
2. **Detection**: Identifies new, updated, and deleted papers
3. **Checkpoint Recovery**: Automatically detect completed work from previous runs
4. **Extraction**: Extracts text from PDFs using PyMuPDF
5. **Quality Scoring**: Sequential processing with adaptive rate limiting (100ms → 500ms+ delays)
6. **Real Progress Saves**: Quality scores saved to disk every 50 papers
7. **True Recovery**: Resume from exact interruption point with zero data loss
8. **Caching**: Uses persistent caches for PDF text and embeddings
9. **Embedding**: Generates Multi-QA MPNet embeddings (768-dimensional)
10. **Indexing**: Builds FAISS index for similarity search
11. **Validation**: Verifies integrity and reports statistics

### `analyze_gaps.py`

**Network Gap Analysis - Production-Ready Literature Gap Detection (v4.7)**

**🎯 Executive Dashboard | 🚀 58-65x Efficiency | 🔧 Smart Filtering | 📊 Research Area Clustering**

Discover missing papers through systematic gap analysis with production-ready reliability and executive dashboard format. Auto-prompted after successful builds, featuring batch processing and smart organization.

#### **🚀 Performance Improvements (v4.7)**

- **58-65x Efficiency**: Batch processing (500 papers per API call vs individual requests)
- **~66 Second Completion**: Comprehensive analysis vs previous timeouts
- **Zero Rate Limiting**: Controlled pacing with 2-second delays prevents 429 errors
- **100% Success Rate**: Reliable completion vs frequent timeout failures

#### **🎯 Executive Dashboard & Smart Features**

- **Top 5 Critical Gaps**: Highest-impact papers (50K+ citations) for immediate import
- **Research Area Clustering**: Auto-organized by domain (🤖 AI, 🏃 Physical Activity, ⚕️ Clinical Methods)
- **Smart Filtering**: Removes 50+ low-quality items (book reviews, duplicates, opinion pieces)
- **Progressive Disclosure**: Summary → Areas → Complete catalog for optimal usability
- **File Overwrite Prevention**: Timestamp includes hour/minute (`_HHMM`)

#### **Gap Detection Algorithms (Optimized)**

**1. Citation Network Analysis** (Primary - Batch Optimized)
- Identifies papers frequently cited by your KB but missing from collection
- **Batch processing**: 500 papers per API call for 400x efficiency improvement
- Auto-organized by research areas for strategic decision-making
- Prioritizes gaps by citation frequency × confidence scores

**2. Author Network Analysis** (Secondary - Frequency Optimized)
- Finds recent work from your KB's **top 10 most prolific authors** (vs 50 random)
- **Smart selection**: Authors prioritized by paper count in your KB for maximum ROI
- **Controlled pacing**: 2-second delays prevent API throttling
- Emphasizes recency and topical relevance

**REQUIREMENTS:**
- KB version 4.0+ (no legacy support)
- Enhanced quality scoring enabled in KB (preferred for optimal results)
- Minimum 20 papers in knowledge base with complete metadata
- Internet connection for Semantic Scholar API
- Fail-fast validation with clear error messages

```bash
python src/analyze_gaps.py [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--min-citations` | INT | 0 | Citation threshold: 0=all, 20-50=moderate, 100+=influential |
| `--year-from` | INT | 2022 | Author recency: 2024=cutting-edge, 2022=balanced, 2020=comprehensive (range: 2015-2025) |
| `--limit` | INT | None | Results per algorithm: 50=focused, 100=balanced, 200+=comprehensive |
| `--kb-path` | PATH | kb_data | Custom KB directory (must be v4.0+ with ≥20 papers) |
| `--help` | FLAG | False | Show comprehensive help with usage patterns and troubleshooting |

#### Parameter Guide

**Citation Thresholds (`--min-citations N`)**:
- `0` (default): Include all papers regardless of citation count
- `20-50`: Focus on moderately well-cited papers
- `100+`: Only highly influential papers
- Note: Recent papers (last 2-3 years) naturally have fewer citations

**Recency Settings (`--year-from YYYY`)**:
- `2024`: Only very recent work (emphasizes cutting-edge research)
- `2022` (default): Recent work (past ~3 years, balanced approach)
- `2020`: Broader timeframe (past ~5 years, more comprehensive)
- `2018`: Very broad (past ~7 years, maximum coverage)
- Range: 2015-2025 (Semantic Scholar coverage limitations)

**Result Limits (`--limit N`)**:
- `None` (default): Return all qualifying gaps (subject to hard limits)
- `50`: Focused analysis with top recommendations only
- `100`: Balanced approach for most use cases
- `200+`: Comprehensive results for large-scale gap analysis
- Note: Each algorithm type (citation/author) gets N results independently

#### Examples (Updated for v4.7)

```bash
# Comprehensive analysis (recommended - completes in ~66 seconds with executive dashboard)
python src/analyze_gaps.py

# High-impact papers with smart filtering and research area clustering
python src/analyze_gaps.py --min-citations 50

# Recent cutting-edge work with batch processing and controlled pacing
python src/analyze_gaps.py --year-from 2024 --limit 50

# Balanced approach with author frequency prioritization
python src/analyze_gaps.py --min-citations 20 --year-from 2020 --limit 100

# Custom KB with all new features
python src/analyze_gaps.py --kb-path /custom/path/kb_data --limit 200
```

#### Output & Reports (Enhanced v4.7)

**Executive Dashboard Reports**: Generated as `exports/gap_analysis_YYYY_MM_DD_HHMM.md` with production-ready format:

**New Dashboard Structure (v4.7)**:
- **🎯 Immediate Action Required**: Top 5 critical gaps with quick import DOIs
- **📊 Research Area Breakdown**: Auto-clustered by domain with statistics
- **🚀 Power User Import**: Pre-formatted DOI lists for bulk Zotero workflows
- **🔧 Import Workflows**: Step-by-step instructions (5min → 15min → 30min approaches)
- **📋 Complete Catalog**: Progressive disclosure with expandable sections
- **Smart Filtering Indicators**: Shows count of removed low-quality items

**Key Improvements**:
- **File overwrite prevention**: Timestamp includes hour/minute (`_1612.md`)
- **Research area clustering**: Automatic organization by domain (AI, Physical Activity, etc.)
- **Progressive disclosure**: Executive summary → details on demand
- **Smart filtering results**: Transparent reporting of quality control actions

**Priority Classification** (Unchanged):
- **HIGH Priority**: Strong relevance evidence (confidence ≥0.8)
- **MEDIUM Priority**: Moderate confidence (0.6-0.8)
- **LOW Priority**: Potentially valuable (0.4-0.6)

**Example Report:**
```
exports/gap_analysis_2024_08_22.md
├── Executive Summary (62 total gaps: 47 citation + 15 author)
├── HIGH Priority Citation Gaps (15 papers, confidence ≥0.8)
├── MEDIUM Priority Citation Gaps (20 papers, confidence 0.6-0.8)
├── LOW Priority Citation Gaps (12 papers, confidence 0.4-0.6)
├── Author Network Gaps (15 recent papers from known authors)
├── Complete DOI Lists (organized by type for Zotero import)
└── How to Import These Papers (step-by-step workflow)
```

#### Performance Characteristics

- **Duration**: 15-25 minutes for 2000-paper KB (varies by citation density)
- **API Efficiency**: ~1 request per KB paper + ~1 per 10 unique authors
- **Memory Usage**: <2GB during analysis, results streamed to prevent OOM
- **Rate Limiting**: Adaptive delays (1.0s baseline, 2.0s+ after 400 requests)
- **Resumable**: Safe interruption with progress preservation via 7-day cache
- **Cache Management**: Automatic progress saves every 50 papers

#### Integration & Workflow

**Automatic Integration:**
Gap analysis is automatically prompted after successful KB builds when conditions are met:
- ✅ KB version 4.0+ with enhanced quality scoring
- ✅ ≥20 papers in knowledge base
- ✅ Internet connection available for Semantic Scholar API

**Workflow Integration:**
- Auto-prompted after successful KB builds (requires ≥20 papers)
- Results complement research-driven discovery via `/research` and `/discover` commands
- DOI lists formatted for direct Zotero bulk import workflow
- Can be re-run with different parameters for refined analysis

**User Workflow:**
1. **Build/Update KB**: `python src/build_kb.py`
2. **Gap Analysis**: Auto-prompted or `python src/analyze_gaps.py`
3. **Review Report**: Check `exports/gap_analysis_YYYY_MM_DD.md`
4. **Import Papers**: Copy DOI lists to Zotero for bulk import
5. **Expand KB**: Re-run build_kb.py to include new papers

#### Error Handling & Troubleshooting

**Common Issues (Updated for v4.7)**:
- **"KB not found"**: Run `python src/build_kb.py --demo` for new setup
- **"Version mismatch"**: Delete kb_data/ and rebuild for compatibility
- **"Insufficient papers"**: Build larger KB or wait until 20+ papers imported
- **"Gap detection module not found"**: Run from correct directory
- **Rate limiting/timeouts**: Fixed in v4.7 - batch processing completes in ~66 seconds
- **File overwrites**: Fixed in v4.7 - timestamp includes hour/minute (`_HHMM`)
- **Cache issues**: Delete `.gap_analysis_cache.json` and retry with new batch processing

**Performance Characteristics (v4.7)**:
- **Duration**: ~66 seconds for comprehensive analysis (vs 15-25 min timeout previously)
- **API Efficiency**: ~5 batch calls + 10 author searches (vs 2,180+ individual calls)
- **Success Rate**: 100% completion rate (vs frequent timeouts)
- **Memory Usage**: <2GB during analysis, results streamed
- **Rate Limiting**: Zero 429 errors with controlled pacing
- **Smart Filtering**: Removes 50+ low-quality items automatically

**Validation Requirements:**
- Fail-fast validation with clear error messages and remediation guidance
- Comprehensive argument validation with specific error explanations
- Safe interruption handling with progress preservation

### `discover.py`

Discover external papers using Semantic Scholar's comprehensive database (214M papers, 85% digital health research coverage).

**DISCOVERY STRATEGY:**
- External paper discovery via Semantic Scholar API
- KB coverage assessment with traffic light system (🟢🟡🔴)
- Basic quality scoring for fast results (no API delays)
- Population-specific term expansion
- DOI-based filtering and deduplication

**COVERAGE ASSESSMENT:**
- 🟢 **EXCELLENT** (1000+ KB papers): Comprehensive coverage detected
- 🟡 **GOOD** (100-999 KB papers): Solid coverage with potential gaps
- 🔴 **NEEDS IMPROVEMENT** (<100 KB papers): Significant gaps likely

**REQUIREMENTS:**
- Internet connection for Semantic Scholar API
- No KB requirements (works independently)

```bash
python src/discover.py [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--keywords` | STRING | Required | Comma-separated search keywords (e.g., "diabetes,mobile health") |
| `--quality-threshold` | CHOICE | None | Minimum quality level (HIGH, MEDIUM, LOW) |
| `--population-focus` | CHOICE | None | Target population (elderly, pediatric, adult, women, men) |
| `--year-from` | INT | None | Only papers published from this year onwards |
| `--year-to` | INT | None | Only papers published up to this year |
| `--study-types` | MULTI | None | Filter by study types (rct, systematic_review, cohort, etc.) |
| `--author` | STRING | None | Filter papers by author name (partial match) |
| `--min-citations` | INT | 0 | Minimum citation count required |
| `--limit` | INT | 1000 | Maximum papers to process |
| `--include-kb-papers` | FLAG | False | Include existing KB papers in results (normally filtered out) |
| `--coverage-info` | FLAG | False | Show database coverage information and exit |

#### Quality Threshold Levels

- **HIGH**: Score ≥80 (A+ and A grades)
- **MEDIUM**: Score ≥60 (B+ and above)
- **LOW**: Score ≥40 (C+ and above)

#### Population Focus Terms

When `--population-focus` is specified, keywords are automatically expanded:

- **elderly**: "elderly", "older adults", "seniors", "geriatric"
- **pediatric**: "pediatric", "children", "adolescent", "youth"
- **adult**: "adult", "adults", "grown-up"
- **women**: "women", "female", "maternal"
- **men**: "men", "male", "paternal"

#### Study Type Filters

- `systematic_review` - Systematic reviews and meta-analyses
- `rct` - Randomized controlled trials
- `cohort` - Cohort studies
- `case_control` - Case-control studies
- `cross_sectional` - Cross-sectional studies
- `case_report` - Case reports and series

#### Examples

```bash
# Basic discovery with traffic light assessment
python src/discover.py --keywords "diabetes,mobile health"

# High-quality research for specific population
python src/discover.py --keywords "AI,diagnostics" \
                      --quality-threshold HIGH \
                      --population-focus pediatric \
                      --year-from 2020

# Systematic reviews and RCTs only
python src/discover.py --keywords "telemedicine" \
                      --study-types systematic_review \
                      --study-types rct \
                      --min-citations 10

# Recent work by specific author
python src/discover.py --keywords "digital health" \
                      --author "Smith" \
                      --year-from 2022 \
                      --limit 50

# Coverage assessment and database information
python src/discover.py --coverage-info

# Include existing KB papers in analysis
python src/discover.py --keywords "treatment" --include-kb-papers

# Comprehensive discovery with all filters
python src/discover.py --keywords "AI,healthcare,machine learning" \
                      --quality-threshold MEDIUM \
                      --population-focus elderly \
                      --year-from 2020 \
                      --year-to 2024 \
                      --min-citations 5 \
                      --limit 200
```

#### Output

Discovery generates comprehensive markdown reports saved to `exports/discovery_YYYY_MM_DD.md`:

**Report Structure:**
```
## 🟢 EXCELLENT (or 🟡 GOOD / 🔴 NEEDS IMPROVEMENT)
- Current KB: X relevant papers found
- External Papers: Y discovered
- Assessment: Coverage evaluation
- Recommendation: Actionable guidance

## Search Parameters
- All search criteria and filters used

## Coverage Information
- Database coverage explanation
- Manual access recommendations for specialized needs

## High Confidence Results (Score 80+)
- Detailed paper information with scores
- Abstract previews and relevance explanations

## Search Performance
- Discovery statistics and filtering results

## DOI Lists for Zotero Import
- High confidence papers (formatted list)
- All papers combined (formatted list)
```

#### Performance

- **Discovery Time**: 3-10 seconds depending on result count
- **Rate Limiting**: 1 RPS to respect Semantic Scholar API limits
- **Coverage**: 214M papers across all academic disciplines
- **Specialization**: 85% coverage of digital health research

#### Integration Workflow

1. **Discovery**: `python src/discover.py --keywords "topic"`
2. **Import**: Copy DOI lists to Zotero for bulk import
3. **Update KB**: `python src/build_kb.py` to add new papers
4. **Search**: Use existing CLI commands on expanded knowledge base

## Slash Commands

### `/research` Slash Command

Comprehensive literature research and review generation using the local knowledge base with intelligent analysis and report generation.

```bash
/research <your research question or topic>
```

#### Key Features

**Comprehensive Analysis:**
- Semantic search using Multi-QA MPNet embeddings across ~2,100 academic papers
- Quality-based paper selection with enhanced scoring (0-100 scale)
- Adaptive search strategies based on query type and available literature
- Cross-paper synthesis and evidence analysis

**Intelligent Processing:**
- **Subagent Integration**: Research-helper for complex data retrieval, Literature-analyzer for deep methodological assessment
- **Performance Optimization**: Batch operations (10-20x faster), smart search for 20+ papers
- **Quality Assessment**: Visual indicators (A+ through F grades) with enhanced scoring markers
- **Flexible Approach**: Adapts methodology based on research question and available evidence

**Report Generation:**
- Comprehensive literature review reports saved to `reviews/` directory
- IEEE citation format with quality-prioritized references
- Evidence synthesis with methodological assessment
- Knowledge gap identification for future research

#### Output Structure

Reports are saved as `reviews/<topic>_YYYY-MM-DD.md` and typically include:
- **Executive Summary**: Key findings and conclusions
- **Methodology Assessment**: Study quality and evidence levels
- **Synthesis**: Cross-study analysis and pattern identification
- **Evidence Gaps**: Areas needing additional research
- **References**: IEEE-formatted citations prioritizing high-quality papers (>70 score)

#### Integration with External Discovery

The `/research` command integrates with external discovery capabilities:
- Can recommend follow-up `/discover` commands for gap analysis
- Supports coverage assessment using Semantic Scholar discovery
- Provides workflow guidance for expanding knowledge base coverage

#### Examples

```bash
# Comprehensive topic research
/research barriers to digital health adoption in elderly populations

# Clinical research question
/research effectiveness of telemedicine for diabetes management

# Methodological inquiry
/research implementation science approaches in mobile health interventions

# Technology assessment
/research AI applications in medical diagnosis accuracy
```

#### Performance Features

- **Smart Caching**: Reuses search results and paper content for faster iterations
- **Batch Processing**: Efficient multi-query execution with single model load
- **Quality Filtering**: Automatic focus on higher-quality evidence when available
- **Section Prioritization**: Intelligent content selection based on research question type

### `/discover` Slash Command

Gap-based external paper discovery using Semantic Scholar with intelligent web research integration.

```bash
/discover [report_name.md] or ["search topic"]
```

#### Usage Patterns

| Input | Behavior |
|-------|----------|
| No arguments | Analyzes latest `reports/research_*.md` file for research gaps |
| Quoted topic | Direct external search on specified topic |
| `report_name.md` | Gap analysis of specific research report |

#### Key Features

**Primary Discovery:**
- Semantic Scholar comprehensive search (214M papers, 85% digital health coverage)
- Gap analysis from research reports to identify missing literature
- Traffic light coverage assessment (🟢🟡🔴)
- Population-specific term expansion and study type filtering

**Web Research Integration:**
- Supplements Semantic Scholar when <10 relevant papers found
- Targets recent developments (6-12 months) and specialized repositories
- Accesses regulatory documents, clinical trial protocols, grey literature
- Avoids web search when Semantic Scholar provides sufficient results

**Output:**
- Comprehensive report saved to `exports/discovery_YYYY_MM_DD.md`
- DOI lists formatted for Zotero bulk import
- Coverage assessment with actionable recommendations
- Integration guidance for knowledge base expansion

#### Examples

```bash
# Gap analysis from latest research report
/discover

# Direct topic search
/discover "AI medical diagnosis"

# Specific report analysis
/discover diabetes_review_2024.md
```

#### Integration with CLI Tools

The slash command uses the underlying `discover.py` tool but adds:
- Intelligent gap analysis from research reports
- Adaptive search strategy based on research context
- Web research when specialized sources needed
- Consistent reporting format with other research workflows

## KB Data Directory Structure

The `kb_data/` directory contains all knowledge base files:

```
kb_data/                          # Main knowledge base directory (~352MB for 2,150 papers)
│
├── papers/                       # Individual paper files (~152MB)
│   ├── paper_0001.md            # Paper in markdown format
│   ├── paper_0002.md            # Each file contains full text + metadata
│   └── ...                      # Files named with 4-digit IDs
│
├── index.faiss                  # FAISS vector search index (~15MB)
│                                # Contains 768-dimensional Multi-QA MPNet embeddings
│
├── metadata.json                # Paper metadata and mappings (~4MB)
│                                # Maps paper IDs to metadata and FAISS indices
│
├── sections_index.json          # Extracted sections mapping (~7KB)
│                                # Maps paper IDs to their sections
│
├── .pdf_text_cache.json         # Cached PDF text (~149MB)
│                                # Avoids re-extracting unchanged PDFs
│
├── .embedding_cache.json        # Embedding metadata (~500B)
│                                # Tracks cached embeddings for reuse
│
├── .embedding_data.npy          # Cached embedding vectors (~6.3MB)
│                                # NumPy array of embedding vectors
│
├── .search_cache.json           # Search results cache (optional)
│                                # LRU cache of recent search results
│
└── (reports moved to separate directories - see below)
```

## Output Directory Structure

The system creates organized directories for different types of outputs:

```
exports/                         # User-valuable files (flat with prefixes)
├── analysis_pdf_quality.md     # PDF quality analysis report
├── discovery_2025_08_23.md     # External paper discovery reports
├── search_diabetes.csv         # Search result exports (auto-prefixed)
├── search_ai_healthcare.csv    # Additional search exports
├── paper_0001_methods.md       # Individual paper exports (auto-prefixed)
└── paper_0234_abstract.md      # More paper exports

reviews/                         # Literature review reports (flat)
├── ai_healthcare_2025-08-20.md # Research command outputs
├── diabetes_2025-08-19.md      # Date-stamped reviews
└── digital_health_2025-08-18.md # Topic-based reviews

system/                          # System and development files (flat with prefixes)
├── dev_test_results.csv         # Development test outputs
├── command_usage_20250821.jsonl  # Command usage logs (daily rotation)
├── log_build_2025-08-20.txt     # Build logs (future)
└── diag_kb_health.json          # Diagnostic reports (future)
```

### Output File Naming

| Directory | Prefix | Purpose | Example |
|-----------|--------|---------|---------|
| `exports/` | `analysis_` | System analysis reports | `analysis_pdf_quality.md` |
| `exports/` | `discovery_` | External paper discovery reports | `discovery_2025_08_23.md` |
| `exports/` | `search_` | Search result exports | `search_diabetes.csv` |
| `exports/` | `paper_` | Individual paper exports | `paper_0001_methods.md` |
| `reviews/` | *(none)* | Literature reviews | `topic_2025-08-20.md` |
| `system/` | `dev_` | Development artifacts | `dev_test_results.csv` |
| `system/` | `command_usage_` | Command usage logs | `command_usage_20250821.jsonl` |
| `system/` | `log_` | Build/system logs | `log_build_2025-08-20.txt` |
| `system/` | `diag_` | Diagnostic reports | `diag_kb_health.json` |

### File Descriptions

#### Core Files

**`papers/paper_XXXX.md`**

- Individual paper files in markdown format
- Contains title, authors, abstract, and full text (if available)
- Named with 4-digit zero-padded IDs (0001-9999)
- Average size: ~70KB per paper with full text

**`index.faiss`**

- Facebook AI Similarity Search (FAISS) index
- Contains 768-dimensional Multi-QA MPNet embeddings for each paper
- Enables fast k-nearest neighbor search
- Size scales with number of papers (~7KB per 1000 papers)

**`metadata.json`**

- Central metadata file containing:
  - Paper list with all metadata fields
  - Total paper count
  - Last update timestamp
  - Embedding model information
  - KB version (4.0)

**`sections_index.json`**

- Maps paper IDs to extracted sections
- Enables section-specific retrieval
- Sections: abstract, introduction, methods, results, discussion, conclusion

#### Cache Files

**`.pdf_text_cache.json`**

- Caches extracted PDF text to avoid re-processing
- Includes file size and modification time for validation
- Significantly speeds up incremental updates
- Largest cache file due to full text storage

**`.embedding_cache.json` + `.embedding_data.npy`**

- Two-file cache system for embeddings
- JSON file contains metadata and hashes
- NPY file contains actual embedding vectors
- Enables reuse of embeddings for unchanged papers

**`.search_cache.json`**

- Optional LRU cache for search results
- Expires after 7 days
- Maximum 100 cached queries
- Improves performance for repeated searches

#### Optional Files

**`missing_pdfs_report.md`**

- Generated when papers lack PDF attachments
- Lists papers without full text
- Includes recommendations for adding PDFs
- Only created if user requests during build

## Data Formats

### metadata.json Structure

```json
{
  "papers": [
    {
      "id": "0001",                    // 4-digit zero-padded ID
      "doi": "10.1234/example",        // DOI if available
      "title": "Paper Title",          // Full paper title
      "authors": ["Smith J", "Doe A"], // Author list
      "year": 2023,                    // Publication year
      "journal": "Nature",             // Journal name
      "volume": "500",                 // Volume number
      "issue": "7461",                 // Issue number
      "pages": "190-195",              // Page range
      "abstract": "Abstract text...",  // Paper abstract
      "study_type": "rct",             // Detected study type
      "sample_size": 487,              // For RCTs, extracted n
      "has_full_text": true,           // Whether PDF was extracted
      "filename": "paper_0001.md",     // Markdown file name
      "embedding_index": 0,            // Index in FAISS
      "zotero_key": "ABC123",          // Zotero reference key
      "pdf_info": {                    // PDF metadata for change detection
        "size": 2451234,
        "mtime": 1693344000.0
      }
    }
  ],
  "total_papers": 2150,
  "last_updated": "2025-08-19T19:42:19.834831+00:00",
  "embedding_model": "sentence-transformers/multi-qa-mpnet-base-dot-v1",
  "embedding_dimensions": 768,
  "model_version": "Multi-QA MPNet",
  "version": "4.0"                     // KB format version
}
```

### Paper Markdown Format

Each paper in `papers/` follows this structure:

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
[Abstract text from paper]

## Full Text
[Complete paper content extracted from PDF, if available]
```

### sections_index.json Structure

```json
{
  "0001": {
    "abstract": "Abstract text...",
    "introduction": "Introduction text...",
    "methods": "Methods section...",
    "results": "Results section...",
    "discussion": "Discussion section...",
    "conclusion": "Conclusion text...",
    "references": "Bibliography...",
    "supplementary": "Supplementary materials..."
  },
  "0002": {
    ...
  }
}
```

## Cache Files

### PDF Text Cache

`.pdf_text_cache.json` structure:

```json
{
  "ZOTERO_KEY_123": {
    "text": "Extracted PDF text content...",
    "file_size": 2451234,
    "file_mtime": 1693344000.0,
    "cached_at": "2025-08-19T10:30:00Z"
  }
}
```

### Embedding Cache

`.embedding_cache.json` structure:

```json
{
  "hashes": ["hash1", "hash2", ...],
  "model_name": "Multi-QA MPNet",
  "created_at": "2025-08-19T10:30:00Z"
}
```

`.embedding_data.npy`: Binary NumPy array of shape (n_papers, 768)

### Search Cache

`.search_cache.json` structure:

```json
{
  "version": "4.0",
  "kb_hash": "abc123def456",
  "queries": {
    "query_hash_123": {
      "timestamp": "2025-08-19T10:30:00Z",
      "results": [...]
    }
  }
}
```

## Error Codes

| Code | Message | Solution |
|------|---------|----------|
| KB001 | Knowledge base not found | Run `python src/build_kb.py` first |
| KB002 | Index file corrupted | Rebuild with `python src/build_kb.py --rebuild` |
| KB003 | Metadata mismatch | Version incompatible, rebuild required |
| KB004 | Papers directory missing | Check KB integrity with `diagnose` |
| API001 | Zotero not accessible | Ensure Zotero is running |
| API002 | API not enabled | Enable in Zotero Settings → Advanced |
| API003 | Connection timeout | Check firewall/network settings |
| PDF001 | PDF extraction failed | Check PDF file integrity in Zotero |
| PDF002 | No PDFs found | Add PDFs to Zotero library |
| EMB001 | Model loading failed | Run `pip install sentence-transformers` |
| EMB002 | CUDA out of memory | Reduce batch size or use CPU |
| ID001 | Invalid paper ID format | Use 4-digit format (e.g., 0001) |
| ID002 | Paper ID not found | Check available IDs with `info` command |
| GAP001 | Gap analysis not available | Requires enhanced quality scoring and ≥20 papers |
| GAP002 | Semantic Scholar API failure | Check internet connection and API availability |
| GAP003 | Insufficient KB data | Need enhanced scoring metadata for analysis |

## Command Usage Analytics

The Research Assistant automatically logs command usage analytics to help improve script functionality. All logs are stored locally and never transmitted.

### Log Files

- **Location**: `system/command_usage_YYYYMMDD.jsonl`
- **Format**: Newline-delimited JSON (one event per line)
- **Rotation**: Daily (new file each day)
- **Privacy**: Local only, automatically disabled during testing

### Data Captured

Each CLI command execution logs:

- **Start events**: Command name, parameters, filters, session ID
- **Success events**: Execution time, results count, performance metrics
- **Error events**: Error type, error message, execution time

### Example Log Entries

```json
{"timestamp": "2025-08-21T16:26:00.428088+00:00", "session_id": "089ddbb4", "level": "INFO", "message": "", "event_type": "command_start", "command": "search", "query_length": 8, "top_k": 1, "has_additional_queries": false, "additional_queries_count": 0, "has_after_filter": false, "after_year": null, "has_study_type_filter": false, "study_types": [], "has_year_range_filter": false, "has_contains_filter": false, "has_exclude_filter": false, "full_text_search": false, "min_quality": null, "show_quality": true, "output_json": false, "group_by": null, "export_requested": false}

{"timestamp": "2025-08-21T16:26:08.907754+00:00", "session_id": "089ddbb4", "level": "INFO", "message": "", "event_type": "command_success", "command": "search", "execution_time_ms": 8479, "results_found": 1, "exported_to_csv": false}
```

### Configuration

Command usage analytics can be configured in `src/config.py`:

```python
COMMAND_USAGE_LOG_ENABLED = True         # Enable/disable logging
COMMAND_USAGE_LOG_PATH = Path("system")  # Log directory
COMMAND_USAGE_LOG_PREFIX = "command_usage_" # Log file prefix
COMMAND_USAGE_LOG_LEVEL = "INFO"         # Log level
```

### Privacy & Testing

- **Test Environment**: Automatically disabled when pytest is running
- **Error Handling**: Setup failures don't break core CLI functionality
- **Local Only**: Logs never leave your machine
- **Session Tracking**: 8-character session IDs for user journey analysis

## Formatting System

The Research Assistant v4.6 includes a unified formatting system that provides consistent user experience across all modules.

### Error Formatting (`src/error_formatting.py`)

Standardized error messages with context-aware suggestions and actionable guidance:

```python
from src.error_formatting import ErrorFormatter, safe_exit, get_common_error

# Create formatted errors with module context
formatter = ErrorFormatter(module="cli", command="search")
result = formatter.format_error(
    "Knowledge base not found",
    context="Attempting to load search index",
    suggestion="Run 'python src/build_kb.py --demo' to create demo KB",
    technical_details="Missing kb_data/ directory"
)

# Quick exit with consistent formatting
safe_exit(
    "Fatal error occurred",
    "Restart the application",
    module="build_kb",
    exit_code=1
)

# Pre-configured common errors
get_common_error("kb_not_found", module="cli")
get_common_error("zotero_connection", module="build_kb")
get_common_error("faiss_import", module="cli")
```

**Features:**
- Context-aware error messages with module identification
- Actionable suggestions with specific commands to run
- Technical details for debugging while keeping user messages clear
- Consistent exit codes and formatting patterns
- Pre-configured common error templates

### Help Formatting (`src/help_formatting.py`)

Unified help text templates with examples, notes, and cross-references:

```python
from src.help_formatting import get_command_help, format_command_help

# Get pre-configured help for commands
search_help = get_command_help("search")
build_help = get_command_help("build_kb")
discover_help = get_command_help("discover")

# Create custom help with consistent formatting
custom_help = format_command_help(
    "Search papers by similarity",
    examples=[
        'python src/cli.py search "diabetes"',
        'python src/cli.py search "AI" --quality-min 70'
    ],
    notes=[
        "Results ranked by semantic similarity",
        "Quality scores range from 0-100"
    ],
    see_also=[
        "smart-search: For large result sets",
        "author: Search by specific author"
    ]
)
```

**Features:**
- Pre-configured templates for all major commands
- Consistent examples with proper command syntax
- Helpful notes explaining key concepts
- Cross-references to related functionality
- Automatic indentation and formatting

### Output Formatting (`src/output_formatting.py`)

Consistent progress indicators, result displays, and status formatting:

```python
from src.output_formatting import (
    ProgressTracker, OutputFormatter,
    print_status, print_results
)

# Progress tracking for long operations
progress = ProgressTracker("Building knowledge base", total=100)
progress.update(25, "Quality scoring")
progress.complete("KB ready")

# Consistent status messages
print_status("Enhanced quality scoring available", "success")
print_status("API rate limit exceeded", "error")
print_status("Using fallback basic scoring", "warning")

# Standardized result formatting
formatter = OutputFormatter()
formatter.print_results("Search Results", results, show_quality=True)
formatter.print_summary({"total_papers": 2180, "build_time": 1023.5})
```

**Features:**
- Progress bars with ETA calculations and visual indicators
- Status icons (✅ ❌ ⚠️ 🔄 ℹ️) for immediate visual feedback
- Quality grade formatting (A+, A, B, C, D, F)
- Large number formatting with commas for readability
- Time formatting (seconds → MM:SS for durations)

### Integration Examples

The formatting system works seamlessly across modules:

```bash
# Consistent error handling
❌ cli.search: Knowledge base not found
   Context: Attempting to load search index
   Solution: Run 'python src/build_kb.py --demo' to create demo KB

# Unified progress indicators
🔄 Building knowledge base: [████████████░░░░░] 65.0% (650/1000) (ETA: 2:30)

# Standardized help text
Examples:
  python src/cli.py search "diabetes"
  python src/cli.py search "AI" --quality-min 70

Notes:
  • Results ranked by semantic similarity using Multi-QA MPNet
  • Quality scores range from 0-100 with confidence indicators
```

## Performance Tips

1. **Use incremental updates**: Default mode only processes changes
2. **Enable caching**: PDF and embedding caches speed up rebuilds by 10x
3. **Batch operations**: Use `get-batch` for multiple papers
4. **Smart search**: Use for 20+ papers to avoid context overflow
5. **GPU acceleration**: CUDA speeds up embedding generation by 5-10x
6. **Export/Import**: Use for quick KB transfer between machines
