# Research Assistant v4.0

**v4.0 requires KB rebuild**: `rm -rf kb_data/ && python src/build_kb.py`

Literature search with SPECTER embeddings. KB: 2,146 papers, ~305MB.

## Commands

```bash
# KB Management
python src/build_kb.py [--demo|--rebuild|--export file|--import file]

# Search
python src/cli.py search "topic" [--show-quality] [--quality-min N]
python src/cli.py smart-search "topic" -k 30
python src/cli.py get 0001 [--sections abstract methods]
python src/cli.py cite "topic"
python src/cli.py [info|diagnose]

# Claude Code
/research <topic>  # Full search workflow
/doi <topic>       # Web discovery
```

## Pre-commit Checks

```bash
mypy src/
ruff check src/ tests/ [--fix]
pytest tests/test_critical.py -v  # 14 core tests
pytest tests/ -v                   # 50 total tests
```

## Architecture

- **build_kb.py**: Zotero→PDF→SPECTER embeddings→FAISS index
- **cli.py**: Search, quality scoring, smart chunking
- **cli_kb_index.py**: O(1) lookups, author search
- **.claude/commands/**: Slash commands

```
kb_data/
├── index.faiss, metadata.json, sections_index.json
├── .pdf_text_cache.json, .embedding_cache.json, .embedding_data.npy
├── papers/paper_XXXX.md  # 4-digit IDs
└── reports/*.md/*.json
```

## Key Details

- **Paper IDs**: 4-digit (0001-2146), path-validated
- **Quality Score** (0-100): Study type (35), recency (10), sample size (10), full text (5)
  - Systematic/meta: 35, RCT: 25, Cohort: 15, Case-control: 10, Cross-sectional: 5
- **SPECTER**: 768-dim embeddings, GPU auto-detect (10x faster)
- **Caching**: PDF text, embeddings, incremental updates

## Workflows

```bash
# Setup
pip install -r requirements.txt
python src/build_kb.py --demo  # 5-paper test

# Search Examples
python src/cli.py search "diabetes" --quality-min 70 --show-quality
python src/cli.py smart-search "digital health" -k 30
python src/cli.py author "Smith J" --exact
python src/cli.py cite "telemedicine" -k 10
```

## Troubleshooting

- **KB not found**: `python src/build_kb.py --demo`
- **Invalid ID**: Use 4-digit format (0001)
- **Zotero error**: Start Zotero, enable API
- **Corruption**: `python src/build_kb.py --rebuild`
- **GPU check**: `python -c "import torch; print(torch.cuda.is_available())"`

## Development

- Python 3.11+, type hints required
- `ruff format src/` for formatting
- Test modules: critical (14), incremental (4), kb_index (8), reports (5), v4 (19)

## Notes

- **Performance**: O(1) lookups, 10x faster incremental updates, GPU 10x speedup
- **Security**: No pickle, path validation, input sanitization
- **Priorities**: Data integrity > Performance > Features
