# Research Assistant v4.0

**⚠️ BREAKING CHANGES IN v4.0 - Complete rebuild required**

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

## v4.0 Breaking Changes

**IMPORTANT**: v4.0 requires rebuilding your knowledge base:

```bash
rm -rf kb_data/
python src/build_kb.py
```

### What Changed
| Change | Impact |
|--------|--------|
| **Simplified architecture** | Only 4 core modules (was 7+) with improved maintainability |
| **O(1) paper lookups** | Instant access via optimized `cli_kb_index.py` |
| **Smart incremental by default** | Automatic change detection and updates |
| **Integrity checking** | Detects and prevents corruption |
| **Improved UX** | Cleaner prompts, better defaults |
| **Better testing** | 50 comprehensive tests covering all functionality |


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
```

**That's it!** You're ready to search academic literature. Continue to the [Usage Guide](#usage-guide) for more examples.

## Quick Reference

### Essential Commands

```bash
# Build/Update KB
python src/build_kb.py --demo        # 5-paper demo
python src/build_kb.py               # Safe incremental update
python src/build_kb.py --rebuild     # Force complete rebuild

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

### Claude Code Command

```
/research <your research question or topic>
```

Literature review reports are saved to the `reviews/` directory.

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

#### Quality Filters
```bash
# High-quality evidence only (score >70)
python src/cli.py search "metabolic syndrome" --quality-min 70 --show-quality

# Recent RCTs and systematic reviews
python src/cli.py search "diabetes" --after 2020 --type rct --type systematic_review

# Get more results for comprehensive review
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

   Choose from:
   - **Quick Update** (Y) - Add new papers only (1-2 minutes)
   - **Full Rebuild** (C) - Rebuild everything (30 minutes)
   - **Exit** (N) - Cancel

3. **Performance** (v4.0 optimized)
   - Initial build: Time varies by hardware and library size
   - Smart incremental updates: ~10x faster than full rebuild
   - Storage: ~305MB for ~2,000 papers (~150MB per 1000 papers)

## Key Features

### Intelligent Search
- **Multi-QA MPNet Embeddings** - Optimized for healthcare and scientific literature
- **Smart Search Modes** - Auto-detects questions vs. exploration
- **Query Expansion** - Automatic synonym expansion
- **Quality Scoring** - 0-100 based on study type, recency, sample size

### Performance
- **O(1) Paper Lookups** - Instant access via optimized index
- **Smart Section Chunking** - Significantly reduces text to process
- **Smart Incremental Updates** - 10x faster than full rebuild
- **GPU Acceleration** - Faster embedding generation when available

### Productivity
- **KB Export/Import** - Sync between computers
- **Claude Integration** - `/research` slash command
- **Offline Operation** - No internet needed after setup
- **Report Generation** - Automatic reports for missing/small PDFs

## Documentation

- **[API Reference](docs/api-reference.md)** - Complete CLI command reference
- **[Technical Specs](docs/technical-specs.md)** - Architecture, modules, and implementation
- **[Advanced Usage](docs/advanced-usage.md)** - GPU setup, custom models, performance tuning
- **[Changelog](CHANGELOG.md)** - Version history and updates

### Project Structure

```
src/
├── build_kb.py         # Knowledge base builder from Zotero
├── cli.py              # Command-line interface for search
├── cli_kb_index.py     # O(1) paper lookups and index operations
└── config.py           # Configuration constants

exports/                # User-valuable analysis and exports
├── analysis_pdf_quality.md    # KB quality analysis
├── search_*.csv               # Search result exports
└── paper_*.md                 # Individual paper exports

reviews/                # Literature review reports
└── *.md               # Generated by /research command

system/                 # Development and system artifacts
└── dev_*.csv          # Test results and system data

tests/
├── test_critical.py    # Core functionality tests (14 tests)
├── test_incremental_updates.py # Smart update tests (4 tests)
├── test_kb_index.py    # O(1) lookup tests (8 tests)
├── test_reports.py     # Report generation tests (5 tests)
└── test_v4_features.py # v4.0 specific tests (19 tests)
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

3. **Run tests** (50 tests covering all functionality)
   ```bash
   pytest tests/ -v              # All tests
   pytest tests/test_critical.py # Core functionality only
   pytest tests/ --cov=src       # With coverage report
   ```

4. **Quality checks**
   ```bash
   ruff check src/ tests/        # Linting
   ruff check src/ tests/ --fix  # Auto-fix issues
   mypy src/                     # Type checking
   ```

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
