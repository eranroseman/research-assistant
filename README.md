# Research Assistant v3.0 for Claude Code

A powerful, secure, and fast literature research tool that integrates with Claude Code through slash commands, enabling intelligent semantic search across a local knowledge base of academic papers with SPECTER2 embeddings.

## 🆕 Version 3.0 Highlights

- **40-50% Faster** - O(1) cache lookups, dynamic batch sizing
- **Enhanced Security** - Command injection & path traversal protection
- **SPECTER2 Intelligence** - Smart search modes with query optimization
- **Quality Scoring** - 0-100 paper quality assessment system
- **Better UX** - Clear, actionable error messages

## 📚 Documentation

- **[API Reference](docs/api-reference.md)** - Complete CLI command reference
- **[Technical Specs](docs/technical-specs.md)** - Architecture and implementation details
- **[Advanced Usage](docs/advanced-usage.md)** - GPU, custom models, performance tuning
- **[Changelog](docs/CHANGELOG.md)** - Version history and updates

## ✨ Features

### Core Capabilities
- **SPECTER2 Embeddings** - State-of-the-art scientific paper embeddings with SPECTER fallback
- **Smart Search Modes** - Auto-detects intent (question, similar, explore)
- **Study Classification** - Automatic detection of RCTs, systematic reviews, cohort studies
- **Quality Assessment** - 0-100 scoring based on study type, recency, sample size
- **Evidence Hierarchy** - Visual markers (⭐ 80-100, ● 60-79, ○ 40-59, · <40)
- **Full-Text Analysis** - Complete paper content extraction from PDFs
- **Smart Caching** - JSON/NPY format for secure, fast rebuilds (10-12 min vs 20+ min)
- **GPU Acceleration** - Dynamic batch sizing based on available memory
- **Claude Integration** - Enhanced `/research` v3.0 slash command
- **Offline Operation** - No internet required after setup

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Build Knowledge Base

```bash
# Option A: Demo database (5 sample papers)
python src/build_kb.py --demo

# Option B: From your Zotero library
python src/build_kb.py  # Requires Zotero running
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

## 📖 Basic Usage

### Search Papers with v3.0 Features

```bash
# Basic search (auto-detects search mode)
python src/cli.py search "telemedicine"

# Research question (optimized for Q&A)
python src/cli.py search "What causes diabetes complications?" --mode question

# Find similar papers
python src/cli.py search "papers similar to digital therapeutics" --mode similar

# High-quality evidence only
python src/cli.py search "metabolic syndrome" --quality-min 70 --show-quality

# Filter by year and study type
python src/cli.py search "diabetes" --after 2020 --type rct --type systematic_review

# Comprehensive review with quality scores
python src/cli.py search "AI diagnosis" -k 30 --show-quality --after 2019
```

### View Full Papers (with Security)

```bash
python src/cli.py get 0001              # Display in terminal (4-digit ID required)
python src/cli.py get 0001 -o paper.md  # Save to file
```

### Generate Citations

```bash
python src/cli.py cite "wearable devices" -k 5
```

## 🔧 Building Your Knowledge Base

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

## 📁 Project Structure

```
research-assistant/
├── .claude/commands/        # Slash command definitions
│   ├── research.md         # v3.0 enhanced research command
│   └── doi.md              # DOI lookup command
├── kb_data/                 # Knowledge base (git-ignored)
│   ├── index.faiss         # FAISS search index
│   ├── metadata.json       # Paper metadata + quality scores
│   ├── .embedding_cache.json  # Cache metadata (v3.0)
│   ├── .embedding_data.npy    # Cache vectors (v3.0)
│   ├── .pdf_text_cache.json   # PDF extraction cache
│   └── papers/             # Full text markdown files
├── docs/                   # Documentation
│   ├── api-reference.md   # CLI commands with v3.0 features
│   ├── technical-specs.md # Architecture details
│   ├── advanced-usage.md  # GPU, models, performance
│   └── CHANGELOG.md       # Version history
├── src/                    # Source code
│   ├── build_kb.py        # Knowledge base builder
│   ├── cli.py             # CLI with quality scoring
│   └── demo.py            # Demo script (secure)
├── tests/                  # Test suite
│   ├── test_critical.py   # Core functionality tests
│   └── conftest.py        # Test configuration
├── pyproject.toml          # Project configuration
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## ⚡ Performance Benchmarks

### v3.0 Improvements
- **Embedding Generation**: 10-12 min (vs 20+ min in v2.0) for 2000 papers
- **Cache Lookups**: O(1) instant (vs O(n) linear search)
- **Batch Processing**: Dynamic 64-256 batch size (vs fixed 64)
- **Search Speed**: <1s for most queries after model loading
- **Rebuild Time**: 2-3 min with full cache (vs 20+ min without)

### System Requirements
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 1GB for code + knowledge base size
- **GPU**: Optional but provides 10x speedup for embeddings
- **Python**: 3.11+ required

## 🐛 Troubleshooting

### Common Issues & Solutions

**"Knowledge base not found"**
```bash
# v3.0 provides clear error messages with solutions
python src/build_kb.py --demo  # Quick fix: Create demo database
```

**"Invalid paper ID format"**
- v3.0 requires 4-digit IDs (e.g., 0001, not 1 or 001)
- Path traversal attempts are blocked for security

**Zotero connection failed**
- Error message now tells you exactly what to do
- Ensure Zotero is running
- Check API is enabled in Settings → Advanced
- For WSL users, see [Advanced Usage](docs/advanced-usage.md#wsl-specific-setup-zotero-on-windows-host)

**SPECTER2 loading issues**
- System automatically falls back to SPECTER
- Install peft for full SPECTER2 support: `pip install peft`

**Performance optimization**
- v3.0 automatically detects GPU and adjusts batch size
- Check GPU: `python -c "import torch; print(torch.cuda.is_available())"`
- Cache is now O(1) - rebuilds are much faster

## 🤝 Contributing

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

## 📄 License

MIT License - See LICENSE file for details

**Note**: PyMuPDF (PDF extraction) is AGPL-licensed. For commercial use, consider purchasing a PyMuPDF license or using alternative libraries.

## 🙏 Acknowledgments

- [FAISS](https://github.com/facebookresearch/faiss) by Facebook Research
- [Sentence Transformers](https://www.sbert.net/) by UKPLab
- [Claude Code](https://claude.ai/code) by Anthropic

## 💬 Support

1. Check [troubleshooting](#-troubleshooting) above
2. Review [API Reference](docs/api-reference.md) for command details
3. See [Advanced Usage](docs/advanced-usage.md) for complex scenarios
4. Open an issue with error messages and steps to reproduce
