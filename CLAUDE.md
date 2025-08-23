# Research Assistant v4.6

Literature search with Multi-QA MPNet embeddings and enhanced quality scoring. KB: ~2,000+ papers, ~305MB.

## Key Features

- **Adaptive Rate Limiting**: Smart delays (100ms → 500ms+) with checkpoint recovery every 50 papers
- **Zero Data Loss**: All work preserved during process interruptions
- **Enhanced Quality Scoring**: API-powered scoring with Semantic Scholar integration
- **GPU Auto-Detection**: 10x speedup when CUDA available, graceful CPU fallback
- **Smart Caching**: Quality upgrades don't invalidate embeddings (30x faster incremental)

## Commands

```bash
# KB Management
python src/build_kb.py                    # Safe update only (NEVER auto-rebuilds)
python src/build_kb.py --rebuild          # Explicit rebuild with confirmation
python src/build_kb.py --demo             # 5-paper demo
python src/build_kb.py --export file      # Export KB for backup
python src/build_kb.py --import file      # Import KB from backup

# Gap Analysis (Post-Build Integration)
python src/analyze_gaps.py               # Comprehensive gap analysis (auto-prompted after builds)
python src/analyze_gaps.py --min-citations 50 --year-from 2020 --limit 100  # Filtered analysis

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

- **build_kb.py**: Zotero→PDF→Full content extraction (no truncation)→Multi-QA MPNet embeddings→Concurrent enhanced quality scoring (Semantic Scholar API)→FAISS index with smart caching
- **cli.py**: Search, enhanced quality indicators, smart chunking
- **cli_kb_index.py**: O(1) lookups, author search, quality filtering
- **.claude/commands/**: Slash commands

```text
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
- **Enhanced Quality Score** (0-100): Citation impact (25), Venue prestige (15), Author authority (10), Cross-validation (10), Core factors (40)
  - **API-powered**: Semantic Scholar integration for citations, venue rankings, h-index
  - **Core factors**: Study type (20), Recency (10), Sample size (5), Full text (5)
  - **Visual indicators**: A+ (85-100) A (70-84) B (60-69) C (45-59) D (30-44) F (0-29)
- **Full Content Preservation**: Complete paper sections with zero information loss
  - **No truncation**: Methods, results, and discussion sections preserved in full
  - **Complete interventions**: Digital health descriptions never cut mid-sentence
  - **Generous limits**: 50KB safety limit per section (10x increase from v4.0)
- **Multi-QA MPNet**: 768-dim embeddings, GPU auto-detect (10x faster)
- **Sequential Processing** (v4.6): Adaptive rate limiting with checkpoint recovery
  - **Reliable builds**: Fixed v4.4 parallel processing issues causing HTTP 429 errors
  - **Smart delays**: 100ms baseline, increases to 500ms+ after 400 papers
  - **Checkpoint system**: Progress saved every 50 papers for interruption recovery
  - **Embedding cache optimization**: Quality upgrades don't invalidate embeddings

## Workflows

```bash
# Setup
pip install -r requirements.txt
python src/build_kb.py --demo  # 5-paper test

# Daily Usage (Safe - Never Auto-Rebuilds)
python src/build_kb.py         # Update only: adds new papers, preserves existing data
python src/build_kb.py         # Parallel quality upgrades + smart embedding cache (17x faster)
                               # Auto-prompts for gap analysis after successful builds

# When Rebuild Needed (Explicit Only)
python src/build_kb.py --rebuild  # Full rebuild with sequential quality scoring (reliable in v4.5)

# Gap Analysis Workflow (New in v4.2)
# After successful KB build/update, prompted to discover literature gaps:
# - Papers cited by your KB but missing from your collection
# - Recent work from authors already in your KB
# - Papers frequently co-cited with your collection
# - Recent developments in your research areas
# - Semantically similar papers you don't have

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
- **"Gap analysis not available"**: Requires enhanced quality scoring and ≥20 papers
- **"API test failed"**: Enhanced scoring unavailable - prompted to use basic scoring with upgrade path
- **"Enhanced scoring requires valid API data"**: Paper has basic score - will upgrade when API available

### Quality Score Recovery
- **"Found X papers with basic quality scores"**: Papers have `quality_score: None` or failed explanations
  - **Cause**: Previous API failures, interrupted builds, or network issues
  - **Solution**: Run `python src/build_kb.py` and accept quality score upgrade when prompted
  - **Safe**: Quality scores are saved before embeddings, so interruptions won't lose progress
- **"Embedding generation failed"**: Quality scores were saved successfully before failure
  - **Recovery**: Re-run `python src/build_kb.py` - will skip quality upgrades and only update embeddings
  - **No data loss**: All quality score improvements are preserved
- **Process interrupted during quality upgrades**: All completed upgrades are saved automatically
  - **Resume**: Next run will continue from where it left off

## System Requirements (v4.0+)

- **Internet Connection Preferred**: Enhanced quality scoring requires Semantic Scholar API access
- **Enhanced Quality Scoring**: API-based scoring is standard, with intelligent fallback to basic scoring if needed
- **User Consent Flow**: If API unavailable, user can choose to proceed with basic scoring and upgrade later
- **Automatic Upgrades**: When API becomes available, basic scores are automatically upgraded to enhanced
- **Breaking Changes**: Incompatible with v3.x knowledge bases - complete rebuild required
- **Data Preservation**: Incremental updates preserve existing papers and cache files

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

```text
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

## Performance & Error Recovery

### Performance & Reliability (v4.6)

- **Adaptive Rate Limiting**: Smart delays adjust to API throttling (100ms → 500ms+)
- **Real Checkpoint Recovery**: Quality scores saved to disk every 50 papers, resume from exact point of interruption
- **Smart Embedding Cache**: Quality upgrades don't invalidate embeddings (30x faster incremental)
- **GPU Auto-Detection**: 10x speedup when CUDA available, graceful CPU fallback

### Error Recovery & Data Integrity

- **Rate Limit Recovery**: Exponential backoff with automatic delay adjustments
- **Quality Score Persistence**: Scores saved immediately before embedding generation
- **Zero Data Loss**: Quality scores persisted to disk immediately, no work lost during interruptions

### Performance Results

- **v4.4**: Parallel → HTTP 429 errors → 0% success rate
- **v4.5**: Sequential → stalled after ~400 papers
- **v4.6**: Adaptive delays → 100% success for any dataset size
- **Timing**: Initial build ~17 minutes for 2,000+ papers, incremental updates ~2 minutes

## Notes

- **Performance**: O(1) lookups, 17x faster incremental updates, GPU 10x speedup
- **Security**: No pickle, path validation, input sanitization
- **Priorities**: Data integrity > Performance > Features
