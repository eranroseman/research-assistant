# Research Assistant v4.0

**⚠️ BREAKING CHANGES IN v4.0 - Complete rebuild required**

A streamlined academic literature search tool with 70% less code. Features SPECTER embeddings for semantic search, smart incremental updates, and Claude Code integration.

## Table of Contents

- [Quick Start](#quick-start) - Get up and running in 5 minutes
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
| **70% code reduction** | Simplified architecture, faster performance |
| **Smart incremental by default** | Automatic change detection and updates |
| **Integrity checking** | Detects and prevents corruption |
| **Improved UX** | Cleaner prompts, better defaults |


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

# Option B: From your Zotero library (incremental by default)
python src/build_kb.py          # Smart incremental update
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

**That's it!** You're ready to search academic literature. Continue to the [Usage Guide](#-usage-guide) for more examples.

## Usage Guide

### Searching Papers

#### Basic Search
```bash
# Simple, direct search with SPECTER embeddings
python src/cli.py search "telemedicine"
python src/cli.py search "diabetes complications"
python src/cli.py search "digital therapeutics" -k 20
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

### Managing Your Knowledge Base

```bash
# Updates (v4.0 - incremental by default)
python src/build_kb.py                     # Smart incremental update
python src/build_kb.py --rebuild           # Force complete rebuild

# Sync between computers
python src/build_kb.py --export kb_backup.tar.gz
python src/build_kb.py --import kb_backup.tar.gz
```

### Generating Citations

```bash
python src/cli.py cite "wearable devices" -k 5
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

3. **Performance** (v3.0 optimized)
   - Initial build: ~20 min (CPU) or ~10 min (GPU)
   - Updates: 2-3 minutes with O(1) cache
   - Storage: ~300MB per 1000 papers

## Key Features

### Intelligent Search
- **SPECTER Embeddings** - Optimized for scientific literature
- **Smart Search Modes** - Auto-detects questions vs. exploration
- **Query Expansion** - Automatic synonym expansion
- **Quality Scoring** - 0-100 based on study type, recency, sample size

### Performance
- **Smart Section Chunking** - 70% less text to process
- **O(1) Cache Lookups** - Instant repeated searches
- **Incremental Updates** - 10x faster for new papers
- **GPU Acceleration** - 2x speedup when available

### Productivity
- **KB Export/Import** - Sync between computers
- **Claude Integration** - `/research` slash command
- **Offline Operation** - No internet needed after setup

## Documentation

- **[API Reference](docs/api-reference.md)** - Complete CLI command reference
- **[Technical Specs](docs/technical-specs.md)** - Architecture and implementation details
- **[Advanced Usage](docs/advanced-usage.md)** - GPU setup, custom models, performance tuning
- **[Changelog](CHANGELOG.md)** - Version history and updates

## System Requirements

- **Python**: 3.11+ required
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 1GB + ~300MB per 1000 papers
- **GPU**: Optional (2x speedup for embeddings)

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

3. **Run tests**
   ```bash
   pytest tests/
   ```

4. **Manual linting**
   ```bash
   ruff check src/ tests/  # Linting
   ruff format src/ tests/ # Formatting
   mypy src/               # Type checking (optional)
   ```

Contributions welcome! Priority areas:
- Additional citation formats (APA, MLA)
- Web UI for knowledge base management
- Integration with other reference managers
- Multi-language support

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
