# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Research Assistant v3.1 - A semantic search system for academic literature that integrates with Claude Code through slash commands. Uses SPECTER embeddings with smart section chunking for 70% context reduction and 10x faster incremental updates.

## Critical Commands

### Building & Running

```bash
# Build knowledge base (required before first use)
python src/build_kb.py --demo      # Quick demo with 5 papers
python src/build_kb.py             # Full build from Zotero library
python src/build_kb.py --update    # Incremental update (10x faster)

# Export/Import for syncing
python src/build_kb.py --export kb_backup.tar.gz
python src/build_kb.py --import kb_backup.tar.gz

# Search papers with v3.1 features
python src/cli.py search "topic" --show-quality --mode auto
python src/cli.py search "topic" --analyze-gaps  # Evidence gap analysis
python src/cli.py shortcut diabetes              # Use personal shortcuts
python src/cli.py info                           # Check knowledge base status

# Smart paper retrieval (70% less text)
python src/cli.py smart-get 0001 "what methods"  # Context-aware sections
python src/cli.py get 0001 --sections abstract methods results
python src/cli.py get 0001                       # Full paper (4-digit ID)

# Knowledge base management
python src/cli.py duplicates       # Find duplicate papers
python src/cli.py duplicates --fix # Remove duplicates

# Slash commands in Claude Code
/research <topic>                   # Enhanced v3.1 with smart chunking
/doi <topic>                       # Find DOIs for additional papers
```

### Testing & Quality

```bash
# Run tests
pytest tests/test_critical.py -v
pytest tests/ --cov=src       # With coverage

# Type checking & linting (ALWAYS run before commits)
mypy src/                     # Type checking
ruff check src/ tests/        # Linting
ruff format src/ tests/       # Formatting
pre-commit run --all-files    # All pre-commit hooks
```

## Architecture & Key Design Patterns

### Core Components

**KnowledgeBaseBuilder** (`src/build_kb.py`):

- Manages Zotero integration and PDF extraction
- Implements O(1) cache lookup using dictionary
- Section extraction for smart chunking (`extract_sections()`)
- Incremental updates with `update_incremental()`
- Export/import functionality for KB portability
- Security: Path validation for all file operations
- Cache format: `.embedding_cache.json` + `.embedding_data.npy` (no pickle)
- Dynamic batch sizing based on GPU memory

**ResearchCLI** (`src/cli.py`):

- Security: 4-digit paper ID validation
- Quality scoring system (0-100) based on study type, recency, sample size
- Query expansion with medical/research synonyms
- Smart section retrieval (`smart-get` command)
- Personal shortcuts system (`shortcut` command)
- Duplicate detection (`duplicates` command)
- Evidence gap analysis (`--analyze-gaps`)
- SPECTER search modes: auto, question, similar, explore

**Slash Commands** (`.claude/commands/`):

- `/research`: Multi-phase search with quality-driven reading strategy
- `/doi`: Web search for additional papers beyond knowledge base
- Commands use temporary files in `/tmp/` for intermediate results

### Data Flow

1. **Build Phase**: Zotero → PDF extraction → SPECTER2 embeddings → FAISS index
2. **Search Phase**: Query → mode detection → embedding → FAISS search → quality scoring → ranked results
3. **Cache Strategy**: Two-level caching (PDF text + embeddings) for 40-50% performance gain

### Security Considerations

- **Command Injection**: Whitelist-based execution in `demo.py` (ALLOWED_COMMANDS)
- **Path Traversal**: Strict validation in `cli.py` get command
- **Serialization**: JSON/NPY only, no pickle (CVE prevention)
- **Input Validation**: All paper IDs must be 4-digit format (0001, not 1)

## Performance Optimizations

- **O(1) cache lookups**: Hash-based dict replaces linear search
- **O(1) section retrieval**: Sections index for instant access to paper sections
- **70% context reduction**: Smart section chunking reduces text processing
- **10x faster updates**: Incremental indexing for new papers only
- **Dynamic batching**: 64-256 batch size based on available memory
- **GPU detection**: Automatic with fallback to CPU
- **Lazy imports**: Heavy libraries loaded only when needed
- **NPY format**: Faster than pickle for numpy arrays
- **Query expansion**: Automatic synonym expansion for better recall
- **Fingerprint caching**: Content-based change detection

## Common Development Patterns

### Adding New Search Features

1. Modify `_search_papers()` in `cli.py` for new parameters
2. Update query preprocessing in mode-specific blocks
3. Add quality scoring factors if relevant
4. Update `/research` command in `.claude/commands/research.md`

### Debugging Search Issues

```python
# Check embeddings match
python src/cli.py info  # Shows model used
# Force rebuild if model mismatch
python src/build_kb.py --clear-cache
```

### Paper ID Format

Always use 4-digit format: `0001`, `0042`, `0999`, `1234`
Never accept: `1`, `01`, `001`, `paper_1`, etc.

## Knowledge Base Structure

```
kb_data/
├── index.faiss              # FAISS vector index
├── metadata.json            # Paper metadata + quality scores
├── .embedding_cache.json    # Cache metadata (hash → index)
├── .embedding_data.npy      # Cache vectors (numpy array)
├── .pdf_text_cache.json     # Extracted PDF text
└── papers/                  # Full-text markdown files
    ├── paper_0001.md
    └── ...
```

## Error Recovery

### "Knowledge base not found"

```bash
python src/build_kb.py --demo  # Quick fix
```

### "SPECTER2 not available"

System auto-falls back to SPECTER. To enable SPECTER2:

```bash
pip install peft
```

### Type errors after changes

```bash
mypy src/ --no-incremental  # Clear mypy cache
```

### Zotero connection issues

1. Ensure Zotero is running
2. Enable API in Zotero: Edit → Settings → Advanced → "Allow other applications"
3. Restart Zotero

## Quality Scoring Formula

```python
score = 0
score += study_type_score  # 35 max (systematic review=35, RCT=30, etc.)
score += 10 if year >= 2022 else 5 if year >= 2018 else 0
score += 10 if sample_size > 1000 else 5 if sample_size > 100 else 0
score += 5 if has_full_text else 0
score = min(100, score * 2.5)  # Scale to 0-100
```

## Testing Requirements

Before committing:

1. Run `mypy src/` - must pass with no errors
2. Run `ruff check src/ tests/` - must pass
3. Run `pytest tests/test_critical.py` - all tests must pass
4. For significant changes: `pre-commit run --all-files`

## Project Metadata

- Python 3.11+ required
- Main dependencies: faiss-cpu, sentence-transformers, PyMuPDF
- License: MIT (Note: PyMuPDF is AGPL - consider for commercial use)
- Version: 3.0.0 (see CHANGELOG.md for history)
