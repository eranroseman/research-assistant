# API Reference

> **Navigation**: [Home](../README.md) | [Technical Specs](technical-specs.md) | [Advanced Usage](advanced-usage.md)

## Table of Contents

### Search & Analysis

- [`search`](#clipy-search) - Semantic search with SPECTER embeddings
- [`smart-search`](#clipy-smart-search) - Smart search with automatic section chunking
- [`get`](#clipy-get) - Retrieve full papers or sections
- [`get-batch`](#clipy-get-batch) - Retrieve multiple papers efficiently
- [`cite`](#clipy-cite) - Generate IEEE citations
- [`author`](#clipy-author) - Search papers by author name

### Knowledge Base

- [`info`](#clipy-info) - Display KB information
- [`diagnose`](#clipy-diagnose) - Check KB health and integrity
- [`build_kb.py`](#build_kbpy) - Build/update knowledge base

### Data Structure

- [KB Data Directory](#kb-data-directory-structure) - Complete folder structure
- [Data Formats](#data-formats) - File specifications
- [Cache Files](#cache-files) - Performance optimization files
- [Error Codes](#error-codes) - Troubleshooting

---

## CLI Commands

### `cli.py search`

Search the knowledge base for relevant papers with SPECTER embeddings.

```bash
python src/cli.py search [OPTIONS] QUERY
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--top-k` | `-k` | INT | 10 | Number of results to return |
| `--verbose` | `-v` | FLAG | False | Show abstracts in results |
| `--show-quality` | | FLAG | False | Display quality scores (0-100) |
| `--quality-min` | | INT | None | Minimum quality score filter (deprecated, use --min-quality) |
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

#### Quality Scores

Papers are scored 0-100 based on:

- Base score: 50 points
- Study type hierarchy: Up to 35 points
- Recency: Up to 10 points (papers from 2022+)
- Sample size: Up to 10 points (RCTs with n>1000)
- Full text availability: 5 points

Visual indicators:

- ⭐ Excellent (80-100)
- ● Good (60-79)
- ○ Moderate (40-59)
- · Lower (<40)

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

Retrieve the full text of a specific paper or specific sections.

```bash
python src/cli.py get [OPTIONS] PAPER_ID
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | PATH | None | Save output to file (saves to reports/ directory) |
| `--sections` | `-s` | MULTI | all | Specific sections to retrieve |

#### Available Sections

- `abstract` - Paper abstract
- `introduction` - Introduction/background
- `methods` - Methods/methodology
- `results` - Results/findings
- `discussion` - Discussion section
- `conclusion` - Conclusions
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

#### Examples

```bash
# Get multiple papers
python src/cli.py get-batch 0001 0002 0003

# Get specific papers
python src/cli.py get-batch 0234 1426 0888

# JSON output for processing
python src/cli.py get-batch 0001 0002 --format json

# Many papers at once
python src/cli.py get-batch 0010 0020 0030 0040 0050
```

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

Output is saved to `reports/smart_search_results.json` for further processing.

### `cli.py cite`

Generate IEEE-style citations for papers matching a query.

```bash
python src/cli.py cite [OPTIONS] QUERY
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--top-k` | `-k` | INT | 5 | Number of citations to generate |

#### Examples

```bash
# Generate 5 citations (default)
python src/cli.py cite "machine learning healthcare"

# Generate 10 citations
python src/cli.py cite "digital therapeutics" -k 10

# Generate citations for specific topic
python src/cli.py cite "diabetes management" -k 15
```

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
Total papers: 2146
Last updated: 2025-08-19T19:42:19.834831+00:00
Version: 4.0
Location: /home/user/research-assistant/kb_data
Index size: 15.2 MB
Papers: 2146 files, 147.9 MB

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
✓ Papers: 2146
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

Build or update the knowledge base from Zotero library.

```bash
python src/build_kb.py [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--demo` | FLAG | False | Build demo database with 5 sample papers |
| `--rebuild` | FLAG | False | Force complete rebuild (ignore existing KB) |
| `--api-url` | STRING | <http://127.0.0.1:23119/api> | Custom Zotero API URL |
| `--knowledge-base-path` | PATH | kb_data | Path to knowledge base directory |
| `--zotero-data-dir` | PATH | ~/Zotero | Path to Zotero data directory |
| `--export` | PATH | None | Export knowledge base to portable tar.gz archive |
| `--import` | PATH | None | Import knowledge base from tar.gz archive |

#### Build Modes

1. **Default (Smart Incremental)**: Detects changes and only processes new/updated papers
2. **Rebuild**: Forces complete reconstruction of the knowledge base
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
5. **Embedding**: Generates SPECTER embeddings (768-dimensional)
6. **Indexing**: Builds FAISS index for similarity search
7. **Validation**: Verifies integrity and reports statistics

## KB Data Directory Structure

The `kb_data/` directory contains all knowledge base files:

```
kb_data/                          # Main knowledge base directory (~305MB for 2,146 papers)
│
├── papers/                       # Individual paper files (~148MB)
│   ├── paper_0001.md            # Paper in markdown format
│   ├── paper_0002.md            # Each file contains full text + metadata
│   └── ...                      # Files named with 4-digit IDs
│
├── index.faiss                  # FAISS vector search index (~15MB)
│                                # Contains 768-dimensional SPECTER embeddings
│
├── metadata.json                # Paper metadata and mappings (~4MB)
│                                # Maps paper IDs to metadata and FAISS indices
│
├── sections_index.json          # Extracted sections mapping (~7KB)
│                                # Maps paper IDs to their sections
│
├── .pdf_text_cache.json         # Cached PDF text (~156MB)
│                                # Avoids re-extracting unchanged PDFs
│
├── .embedding_cache.json        # Embedding metadata (~500B)
│                                # Tracks cached embeddings for reuse
│
├── .embedding_data.npy          # Cached embedding vectors (~15MB)
│                                # NumPy array of embedding vectors
│
├── .search_cache.json           # Search results cache (optional)
│                                # LRU cache of recent search results
│
└── missing_pdfs_report.md       # Report of papers without PDFs (optional)
                                 # Generated when PDFs are missing
```

### File Descriptions

#### Core Files

**`papers/paper_XXXX.md`**

- Individual paper files in markdown format
- Contains title, authors, abstract, and full text (if available)
- Named with 4-digit zero-padded IDs (0001-9999)
- Average size: ~70KB per paper with full text

**`index.faiss`**

- Facebook AI Similarity Search (FAISS) index
- Contains 768-dimensional SPECTER embeddings for each paper
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
  "total_papers": 2146,
  "last_updated": "2025-08-19T19:42:19.834831+00:00",
  "embedding_model": "sentence-transformers/allenai-specter",
  "embedding_dimensions": 768,
  "model_version": "SPECTER",
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
  "model_name": "SPECTER",
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

## Performance Tips

1. **Use incremental updates**: Default mode only processes changes
2. **Enable caching**: PDF and embedding caches speed up rebuilds by 10x
3. **Batch operations**: Use `get-batch` for multiple papers
4. **Smart search**: Use for 20+ papers to avoid context overflow
5. **GPU acceleration**: CUDA speeds up embedding generation by 5-10x
6. **Export/Import**: Use for quick KB transfer between machines
