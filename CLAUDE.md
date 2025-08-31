# Research Assistant v4.6

Literature search with Multi-QA MPNet embeddings and enhanced quality scoring. KB: ~2,000+ papers, ~305MB.

## Quick Start

```bash
# Setup
pip install -r requirements.txt
python src/build_kb.py --demo  # 5-paper test

# Build KB
python src/build_kb.py         # Safe incremental update (adds new papers only)
python src/build_kb.py --rebuild  # Full rebuild (requires confirmation)

# Search
python src/cli.py search "diabetes" --quality-min 70 --show-quality
python src/cli.py smart-search "digital health" -k 30
python src/cli.py cite 0001 0234 1426  # Generate IEEE citations

# Gap Analysis
python src/analyze_gaps.py  # Auto-prompted after builds

# External Discovery
python src/discover.py --keywords "diabetes,mobile health"
```

## Architecture Overview

```text
Zotero → PyMuPDF → Full Text → Multi-QA MPNet → FAISS Index
                ↓
        Semantic Scholar API → Quality Scores → Gap Analysis

kb_data/
├── index.faiss, metadata.json, sections_index.json
├── .pdf_text_cache.json, .embedding_cache.json, .embedding_data.npy
└── papers/paper_XXXX.md  # 4-digit IDs (0001-XXXX)
```

## Key Features

| Feature | Description |
|---------|------------|
| **External Discovery** | 214M papers via Semantic Scholar (85% digital health coverage) |
| **Quality Scoring** | 0-100 score with API enrichment (citations, venues, h-index) |
| **Smart Caching** | Quality upgrades preserve embeddings (30x faster) |
| **Checkpoint Recovery** | Saves every 50 papers, resume from interruption |
| **GPU Auto-Detection** | 10x speedup when CUDA available |
| **Full Content** | No truncation, 50KB per section limit |

## Commands Reference

### KB Management

```bash
python src/build_kb.py [--rebuild|--demo|--export FILE|--import FILE]
```

### Search & Discovery

```bash
python src/cli.py search "topic" [--show-quality] [--quality-min N]
python src/cli.py smart-search "topic" -k 30
python src/cli.py author "Smith J" --exact
python src/cli.py get 0001 [--sections abstract methods]
python src/cli.py cite 0001 0002 0003
python src/discover.py --keywords "AI,diagnostics" --year-from 2022
```

### Development

```bash
mypy src/
ruff check src/ tests/ --fix
pytest tests/unit/ -v              # Fast unit tests
pytest tests/integration/ -v       # Workflow tests
pytest tests/e2e/test_e2e_cli_commands.py::TestCriticalE2EFunctionality -v
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| KB not found | `python src/build_kb.py --demo` |
| Zotero connection | Start Zotero, enable API in Preferences → Advanced |
| Invalid paper ID | Use 4-digit format (0001) |
| GPU check | `python -c "import torch; print(torch.cuda.is_available())"` |
| API failures | Run `python src/build_kb.py` to upgrade basic scores |
| Corrupted KB | `python src/build_kb.py --rebuild` |

## Quality Score System

**Score Composition (0-100)**:

- Citation impact: 25 points
- Venue prestige: 15 points
- Author authority: 10 points
- Cross-validation: 10 points
- Core factors: 40 points (study type, recency, sample size, full text)

**Visual Indicators**: A+ (85-100) A (70-84) B (60-69) C (45-59) D (30-44) F (0-29)

## Performance Specs

- **Processing**: ~17 min for 2,000 papers initial, ~2 min incremental
- **Embeddings**: 768-dim Multi-QA MPNet vectors
- **Rate Limiting**: Adaptive 100ms → 500ms+ delays
- **Cache**: Preserves embeddings during quality upgrades
- **Recovery**: Checkpoint every 50 papers

## Test Organization

```text
tests/              # 193 total tests
├── unit/           # 123 tests - Component testing
├── integration/    # 40 tests - Workflow validation
├── e2e/           # 23 tests - End-to-end functionality
└── performance/    # 7 tests - Speed benchmarks
```

## System Requirements

- Python 3.11+
- Internet for Semantic Scholar API
- 4GB RAM minimum (8GB recommended)
- Optional: CUDA GPU for 10x embedding speedup

## Notes

- **v4.6 Improvements**: Fixed parallel processing HTTP 429 errors, added checkpoint recovery
- **Breaking Change**: v3.x KBs incompatible, rebuild required
- **Security**: No pickle, path validation, input sanitization
- **Priorities**: Data integrity > Performance > Features
