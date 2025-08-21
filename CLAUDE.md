# Research Assistant v4.0

**v4.0 requires KB rebuild**: `rm -rf kb_data/ && python src/build_kb.py`

Literature search with Multi-QA MPNet embeddings. KB: ~2,000+ papers, ~305MB.

## Commands

```bash
# KB Management
python src/build_kb.py                    # Safe update only (NEVER auto-rebuilds)
python src/build_kb.py --rebuild          # Explicit rebuild with confirmation
python src/build_kb.py --demo             # 5-paper demo
python src/build_kb.py --export file      # Export KB for backup
python src/build_kb.py --import file      # Import KB from backup

# Search
python src/cli.py search "topic" [--show-quality] [--quality-min N]
python src/cli.py smart-search "topic" -k 30
python src/cli.py get 0001 [--sections abstract methods]
python src/cli.py cite 0001 0002 0003  # Generate IEEE citations for specific papers
python src/cli.py [info|diagnose]

# Claude Code
/research <topic>  # Full search workflow
/doi <topic>       # Web discovery
```

## Pre-commit Checks

```bash
mypy src/
ruff check src/ tests/ [--fix]
pytest tests/e2e/test_cli_commands.py::TestCriticalE2EFunctionality -v  # 3 critical tests
pytest tests/unit/ -v              # Unit tests (fast)
pytest tests/e2e/ -v               # End-to-end tests (critical functionality)
pytest tests/ -v                   # All tests (~193 total)
```

## Architecture

- **build_kb.py**: Zotero→PDF→Multi-QA MPNet embeddings→FAISS index
- **cli.py**: Search, quality scoring, smart chunking
- **cli_kb_index.py**: O(1) lookups, author search
- **.claude/commands/**: Slash commands

```
kb_data/
├── index.faiss, metadata.json, sections_index.json
├── .pdf_text_cache.json, .embedding_cache.json, .embedding_data.npy
└── papers/paper_XXXX.md  # 4-digit IDs

exports/
├── analysis_pdf_quality.md    # KB quality analysis
├── search_*.csv               # Search result exports
└── paper_*.md                 # Individual paper exports

reviews/
└── *.md                       # Literature review reports

system/
└── dev_*.csv                  # Development artifacts (flat with prefix)
```

## Key Details

- **Paper IDs**: 4-digit (0001-XXXX), path-validated
- **Quality Score** (0-100): Study type (35), recency (10), sample size (10), full text (5)
  - Systematic/meta: 35, RCT: 25, Cohort: 15, Case-control: 10, Cross-sectional: 5
- **Multi-QA MPNet**: 768-dim embeddings, GPU auto-detect (10x faster)
- **Caching**: PDF text, embeddings, incremental updates

## Workflows

```bash
# Setup
pip install -r requirements.txt
python src/build_kb.py --demo  # 5-paper test

# Daily Usage (Safe - Never Auto-Rebuilds)
python src/build_kb.py         # Update only: adds new papers, preserves existing data
python src/build_kb.py         # Safe exit with clear guidance if issues occur

# When Rebuild Needed (Explicit Only)
python src/build_kb.py --rebuild  # Full rebuild with user confirmation

# Search Examples
python src/cli.py search "diabetes" --quality-min 70 --show-quality
python src/cli.py smart-search "digital health" -k 30
python src/cli.py author "Smith J" --exact
python src/cli.py cite 0001 0234 1426  # Generate citations for specific papers
```

## Troubleshooting

- **KB not found**: `python src/build_kb.py --demo`
- **Invalid ID**: Use 4-digit format (0001)
- **"Cannot connect to Zotero local API"**: Start Zotero, enable API in Preferences → Advanced
- **"Incremental update failed"**: Script exits safely, run `python src/build_kb.py --rebuild` if needed
- **Corruption**: `python src/build_kb.py --rebuild`
- **GPU check**: `python -c "import torch; print(torch.cuda.is_available())"`

## Safety Features (New in v4.1)

- **Safe by Default**: Default operation NEVER automatically deletes or rebuilds your data
- **Update Only**: `python src/build_kb.py` only adds new papers and updates changed ones
- **Explicit Rebuilds**: Destructive operations require `--rebuild` flag with user confirmation
- **Data Preservation**: All cache files and existing papers preserved during failures
- **Clear Guidance**: Detailed error messages with specific solutions when issues occur

## Development

- Python 3.11+, type hints required
- `ruff format src/` for formatting
- Test organization: unit/ (7 files), integration/ (5 files), e2e/ (2 files), performance/ (1 file)
- Critical tests: `pytest tests/e2e/test_cli_commands.py::TestCriticalE2EFunctionality -v`

## Notes

- **Performance**: O(1) lookups, 10x faster incremental updates, GPU 10x speedup
- **Security**: No pickle, path validation, input sanitization
- **Priorities**: Data integrity > Performance > Features
