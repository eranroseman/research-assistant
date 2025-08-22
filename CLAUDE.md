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
pytest tests/e2e/test_e2e_cli_commands.py::TestCriticalE2EFunctionality -v  # 3 critical tests
pytest tests/unit/ -v              # Unit tests (123 tests, fast)
pytest tests/integration/ -v       # Integration tests (workflow validation)
pytest tests/e2e/ -v               # End-to-end tests (critical functionality)
pytest tests/performance/ -v       # Performance benchmarks
pytest tests/ -v                   # All tests (193 total)
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
├── dev_*.csv                  # Development artifacts (flat with prefix)
└── ux_analytics_*.jsonl       # UX analytics logs (daily rotation)
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
- **Test Organization**: Consistent naming scheme `test_{type}_{component}.py`
  - **unit/** (7 files): `test_unit_*.py` - Component-focused unit tests
  - **integration/** (5 files): `test_integration_*.py` - Workflow validation tests
  - **e2e/** (2 files): `test_e2e_*.py` - End-to-end functionality tests
  - **performance/** (1 file): `test_performance_*.py` - Benchmark and timing tests
- **Critical tests**: `pytest tests/e2e/test_e2e_cli_commands.py::TestCriticalE2EFunctionality -v`

## Test Structure

```
tests/
├── unit/                           # Component-focused unit tests (123 tests)
│   ├── test_unit_citation_system.py      # IEEE citation formatting
│   ├── test_unit_cli_batch_commands.py   # CLI batch operations
│   ├── test_unit_cli_interface.py        # CLI utility functions
│   ├── test_unit_knowledge_base.py       # KB building, indexing, caching
│   ├── test_unit_quality_scoring.py      # Paper quality algorithms
│   ├── test_unit_search_engine.py        # Search, embedding, ranking
│   └── test_unit_ux_analytics.py         # Analytics logging
├── integration/                    # Workflow validation tests (40 tests)
│   ├── test_integration_batch_operations.py    # Batch command workflows
│   ├── test_integration_incremental_updates.py # KB update workflows
│   ├── test_integration_kb_building.py         # KB building processes
│   ├── test_integration_reports.py             # Report generation
│   └── test_integration_search_workflow.py     # Search workflows
├── e2e/                           # End-to-end functionality tests (23 tests)
│   ├── test_e2e_cite_command.py          # Citation command E2E
│   └── test_e2e_cli_commands.py          # Core CLI commands E2E
├── performance/                   # Performance benchmarks (7 tests)
│   └── test_performance_benchmarks.py    # Speed and memory tests
├── conftest.py                    # Shared pytest fixtures
└── utils.py                       # Test utilities and helpers
```

**Test Naming Convention**: `test_{type}_{component/feature}.py`
- Makes test purpose immediately clear from filename
- Enables easy filtering by test type (`pytest tests/unit/test_unit_*.py`)
- Supports scalable organization as codebase grows

## UX Analytics

- **Purpose**: Tracks user behavior patterns for CLI improvement (not debugging)
- **Location**: `system/ux_analytics_YYYYMMDD.jsonl` (daily rotation)
- **Format**: Newline-delimited JSON with timestamps, session IDs, and detailed metrics
- **Data Captured**: Command usage, parameters, execution time, results, errors
- **Privacy**: Local logs only, automatically disabled during testing
- **Configuration**: Controlled via `src/config.py` (UX_LOG_ENABLED, UX_LOG_PATH)

Example log entry:
```json
{"timestamp": "2025-08-21T16:26:08.907754+00:00", "session_id": "089ddbb4", "level": "INFO", "message": "", "event_type": "command_success", "command": "search", "execution_time_ms": 8479, "results_found": 1, "exported_to_csv": false}
```

## Notes

- **Performance**: O(1) lookups, 10x faster incremental updates, GPU 10x speedup
- **Security**: No pickle, path validation, input sanitization
- **Priorities**: Data integrity > Performance > Features
