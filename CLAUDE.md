# Research Assistant v4.0 - Claude Code Guide

**BREAKING CHANGE: v4.0 requires complete KB rebuild (rm -rf kb_data/ && python src/build_kb.py)**

Streamlined academic literature search with 70% less code. Features smart incremental updates, integrity checking, and Claude Code integration.

## Quick Reference

```bash
# Build KB
python src/build_kb.py --demo        # 5-paper demo
python src/build_kb.py               # Smart incremental (default)
python src/build_kb.py --rebuild     # Force complete rebuild
python src/build_kb.py --export/--import kb.tar.gz

# Search & Retrieve
python src/cli.py search "topic" [--show-quality]
python src/cli.py smart-search "topic" -k 30  # Handle 20+ papers
python src/cli.py get 0001 [--sections abstract methods]
python src/cli.py info

# Claude Code Commands
/research <topic>     # Smart search with chunking
/doi <topic>         # Find papers via web

# Quality Checks (ALWAYS before commits)
mypy src/ && ruff check src/ tests/ && pytest tests/test_critical.py -v
```

## Architecture

**Components:**
- `build_kb.py`: Zotero→PDF→SPECTER→FAISS, smart incremental updates, integrity checking
- `cli.py`: 4-digit IDs, quality scoring (0-100), smart chunking
- `.claude/commands/`: `/research` (smart search), `/doi` (web search)

**Security:** Path validation, JSON/NPY only (no pickle), 4-digit IDs (0001 format)

**Performance:** O(1) lookups, 70% context reduction, 10x faster updates, GPU auto-detect

**v4.0 Changes:** 70% code reduction, integrity checking, improved UX, smart incremental by default


## Key Patterns

- **Paper IDs:** Always 4-digit (`0001`, not `1` or `001`)
- **Model:** SPECTER (sentence-transformers/allenai-specter)
- **Caching:** `.embedding_cache.json` + `.embedding_data.npy`
- **Quality Score:** study_type(35) + recency(10) + sample_size(10) + full_text(5), scaled 0-100
- **Incremental:** Smart change detection by default, `--rebuild` for full rebuild

## Files

```
kb_data/
├── index.faiss            # Vector index
├── metadata.json          # Paper info + scores
├── .embedding_cache.json  # Cache index
├── .embedding_data.npy    # Cache vectors
├── .pdf_text_cache.json   # PDF text
└── papers/*.md            # Full papers
```

## Troubleshooting

- **KB not found:** `python src/build_kb.py --demo`
- **Corruption detected:** `python src/build_kb.py --rebuild`
- **SPECTER fails:** `pip install peft`
- **Type errors:** `mypy src/ --no-incremental`
- **Zotero:** Enable API in Settings→Advanced→"Allow other applications"



## Requirements

Python 3.11+, faiss-cpu, sentence-transformers, PyMuPDF (AGPL license)
