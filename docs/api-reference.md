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
- [`analyze_gaps.py`](#analyze_gapspy) - Discover missing papers (auto-prompted after builds)

### Data Structure

- [KB Data Directory](#kb-data-directory-structure) - Complete folder structure
- [Data Formats](#data-formats) - File specifications
- [Cache Files](#cache-files) - Performance optimization files
- [Error Codes](#error-codes) - Troubleshooting

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

#### Process Flow

1. **Connection**: Connects to Zotero via local API (port 23119)
2. **Detection**: Identifies new, updated, and deleted papers
3. **Extraction**: Extracts text from PDFs using PyMuPDF
4. **Caching**: Uses persistent caches for PDF text and embeddings
5. **Embedding**: Generates Multi-QA MPNet embeddings (768-dimensional)
6. **Indexing**: Builds FAISS index for similarity search
7. **Validation**: Verifies integrity and reports statistics

### `analyze_gaps.py`

Discover missing papers in your knowledge base through comprehensive gap analysis (auto-prompted after successful builds).

**GAP TYPES IDENTIFIED:**
- Papers cited by your KB but missing from your collection
- Recent work from authors already in your KB
- Papers frequently co-cited with your collection
- Recent developments in your research areas
- Semantically similar papers you don't have

**REQUIREMENTS:**
- Enhanced quality scoring enabled in KB
- Minimum 20 papers in knowledge base
- Internet connection for Semantic Scholar API

```bash
python src/analyze_gaps.py [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--min-citations` | INT | 0 | Only suggest papers with ≥N citations |
| `--year-from` | INT | 2022 | Author networks: only papers from year onwards |
| `--limit` | INT | None | Return top N gaps by priority |
| `--help` | FLAG | False | Show help message |

#### Examples

```bash
# Comprehensive analysis (all gap types, no filters)
python src/analyze_gaps.py

# High-impact gaps only
python src/analyze_gaps.py --min-citations 50

# Recent work from your authors
python src/analyze_gaps.py --year-from 2024 --limit 30

# Conservative analysis with combined filters
python src/analyze_gaps.py --min-citations 50 --year-from 2020 --limit 100
```

#### Output

Gap analysis generates a comprehensive report saved to `exports/gap_analysis_YYYY_MM_DD.md`:

- **Executive Summary**: Total gaps found by type and confidence level
- **Citation Network Gaps**: Papers heavily cited by your KB but missing
- **Author Network Gaps**: Recent work from researchers already in your collection
- **Complete DOI Lists**: Organized for bulk Zotero import
- **Priority Rankings**: Confidence scoring for actionable results

**Report Structure:**
```
exports/gap_analysis_2024_08_22.md
├── Executive Summary (counts by gap type)
├── Citation Network Gaps (highest confidence)
├── Author Network Gaps (recent work)
├── Complete DOI Lists (for Zotero import)
└── Methodology and confidence indicators
```

#### Integration

Gap analysis is automatically prompted after successful KB builds when conditions are met:
- ✅ Enhanced quality scoring available
- ✅ ≥20 papers in knowledge base
- ✅ Internet connection available

User can accept (Y) for immediate comprehensive analysis or decline (n) to run manually later with custom filters.

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
├── ux_analytics_20250821.jsonl  # UX analytics logs (daily rotation)
├── log_build_2025-08-20.txt     # Build logs (future)
└── diag_kb_health.json          # Diagnostic reports (future)
```

### Output File Naming

| Directory | Prefix | Purpose | Example |
|-----------|--------|---------|---------|
| `exports/` | `analysis_` | System analysis reports | `analysis_pdf_quality.md` |
| `exports/` | `search_` | Search result exports | `search_diabetes.csv` |
| `exports/` | `paper_` | Individual paper exports | `paper_0001_methods.md` |
| `reviews/` | *(none)* | Literature reviews | `topic_2025-08-20.md` |
| `system/` | `dev_` | Development artifacts | `dev_test_results.csv` |
| `system/` | `ux_analytics_` | UX analytics logs | `ux_analytics_20250821.jsonl` |
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

## UX Analytics

The Research Assistant automatically logs usage analytics to help improve user experience. All logs are stored locally and never transmitted.

### Log Files

- **Location**: `system/ux_analytics_YYYYMMDD.jsonl`
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

UX analytics can be configured in `src/config.py`:

```python
UX_LOG_ENABLED = True                    # Enable/disable logging
UX_LOG_PATH = Path("system")             # Log directory
UX_LOG_PREFIX = "ux_analytics_"          # Log file prefix
UX_LOG_LEVEL = "INFO"                    # Log level
```

### Privacy & Testing

- **Test Environment**: Automatically disabled when pytest is running
- **Error Handling**: Setup failures don't break core CLI functionality
- **Local Only**: Logs never leave your machine
- **Session Tracking**: 8-character session IDs for user journey analysis

## Performance Tips

1. **Use incremental updates**: Default mode only processes changes
2. **Enable caching**: PDF and embedding caches speed up rebuilds by 10x
3. **Batch operations**: Use `get-batch` for multiple papers
4. **Smart search**: Use for 20+ papers to avoid context overflow
5. **GPU acceleration**: CUDA speeds up embedding generation by 5-10x
6. **Export/Import**: Use for quick KB transfer between machines
