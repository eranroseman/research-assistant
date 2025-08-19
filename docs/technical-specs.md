# Technical Specifications

> **Navigation**: [Home](../README.md) | [API Reference](api-reference.md) | [Advanced Usage](advanced-usage.md)

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [v4.0 Features](#new-features-in-v40)
- [Implementation Details](#implementation)
- [Data Formats](#data-formats)
- [Performance](#technical-specifications-1)
- [Dependencies](#dependencies)

---

## Overview

A streamlined academic literature search tool with 70% less code than v3. Features smart incremental updates, integrity checking, and Claude Code integration for evidence-based research using SPECTER embeddings.

## New Features in v4.0

### Performance & Security
- **40-50% Faster Searches**: O(1) cache lookups and dynamic batch sizing
- **Enhanced Security**: Command injection prevention, path traversal protection, safe JSON/NPY serialization
- **Optimized Batch Processing**: Dynamic sizing based on available memory (64-256 batch size)
- **Instant Cache Lookups**: Hash-based dictionary for O(1) embedding retrieval

### SPECTER Intelligence
- **Smart Search Modes**: Auto-detects query intent (question, similar, explore)
- **Query Preprocessing**: Optimizes embeddings based on search type
- **Scientific Paper Optimization**: SPECTER model specifically trained on academic literature

### Quality Assessment
- **Paper Quality Scores**: 0-100 scoring based on study type, recency, sample size
- **Quality Filtering**: `--quality-min` parameter to filter low-quality papers
- **Visual Quality Indicators**: ⭐ (80-100), ● (60-79), ○ (40-59), · (<40)

### Enhanced Features
- **Study Type Classification**: Automatically identifies systematic reviews, RCTs, cohort studies, etc.
- **RCT Sample Size Extraction**: Shows participant counts (n=487) for randomized controlled trials
- **Advanced Filtering**: Filter by publication year and study type
- **Evidence Hierarchy**: Visual markers showing study quality
- **Smart Incremental Updates**: Automatic change detection, 10x faster than full rebuild
- **Smart Section Retrieval**: 70% context reduction with intelligent section chunking
- **Sections Index**: O(1) section retrieval for instant access to paper sections
- **Integrity Checking**: Automatic detection of corrupted or duplicate paper IDs
- **Export/Import**: Portable knowledge base with tar.gz export/import

## Architecture

```
Setup Phase (once):     Zotero → Build Script → Portable KB
Runtime Phase (always): /research command → Search → Analyze → Report
```

## Data Structure

```
kb_data/
├── index.faiss              # Semantic search index (~6.5MB for 2000 papers)
├── metadata.json            # Paper metadata with model version (~4MB)
├── sections_index.json      # Section locations for smart retrieval (~36MB)
├── .pdf_text_cache.json     # PDF extraction cache (metadata-based, ~156MB)
├── .embedding_cache.json    # Embedding metadata (hashes, model info) - NEW in v3.1
├── .embedding_data.npy      # Embedding vectors (safe NPY format) - NEW in v3.1
├── .fingerprint_cache.json  # Content fingerprints for change detection
└── papers/
    ├── paper_0001.md        # Full text in markdown (4-digit IDs)
    ├── paper_0002.md        # One file per paper
    └── ...                  # 2000+ files
```

**Security Note**: v3.1 uses safe JSON/NPY format instead of pickle serialization

## Implementation

### 1. Knowledge Base Builder (`build_kb.py`)

**Purpose**: One-time conversion of Zotero library to portable format

**Process**:

1. Extract papers from Zotero (local API)
2. Convert PDFs to markdown files (with caching)
3. Build FAISS index from title+abstract embeddings using SPECTER
4. Save metadata as JSON

**Features**:
- SPECTER embeddings for superior scientific paper retrieval (sentence-transformers/allenai-specter)
- Automatic study type classification (RCTs, systematic reviews, cohort studies, etc.)
- RCT sample size extraction (n=487)
- PyMuPDF for fast PDF text extraction (estimated ~13 papers/second with cache)
- Metadata-based caching with automatic backups
- `--clear-cache` flag for fresh extraction

**Usage**:

```bash
python build_kb.py              # Smart incremental update (default)
python build_kb.py --rebuild    # Force complete rebuild
python build_kb.py --clear-cache # Clear caches and rebuild
python build_kb.py --demo       # Quick demo with 5 papers
python build_kb.py --export kb_backup.tar.gz  # Export knowledge base
python build_kb.py --import kb_backup.tar.gz  # Import knowledge base
```

### 2. CLI Tool (`cli.py`)

**Commands**:

```bash
python cli.py search "query"              # Basic search with SPECTER embeddings
python cli.py search "query" --after 2020  # Filter by year
python cli.py search "query" --type rct --type systematic_review  # Filter by study type
python cli.py search "query" --show-quality --quality-min 70  # Quality filtering
python cli.py search "query" --mode question  # Optimize for research questions
python cli.py get <paper_id>              # Returns full paper text
python cli.py smart-get <paper_id> "question"  # Smart section retrieval (70% less text)
python cli.py get <paper_id> --sections abstract methods results  # Specific sections
python cli.py info                        # Check knowledge base status
python cli.py cite "query"                # Generate IEEE citations
```

**Study Type Categories:**
- `systematic_review` - Systematic reviews and meta-analyses (⭐)
- `rct` - Randomized controlled trials (●)
- `cohort` - Cohort studies (◐)
- `case_control` - Case-control studies (○)
- `cross_sectional` - Cross-sectional studies (◔)
- `case_report` - Case reports and series (·)
- `study` - Generic/unclassified studies (·)

### 3. Claude Slash Command

#### How Slash Commands Work in Claude Code

Slash commands are custom commands that extend Claude's capabilities. They are defined as markdown files in the `.claude/commands/` directory and are automatically discovered by Claude Code.

**Key Concepts:**

- **Location**: Place command files in `.claude/commands/` (project-level) or `~/.claude/commands/` (user-level)
- **Format**: Markdown files with optional YAML frontmatter
- **Variables**: `$ARGUMENTS` contains everything typed after the command
- **Execution**: Lines starting with `!` run as bash commands
- **File Access**: `@filename` reads file contents into context

#### Creating the Research Command

**File**: `.claude/commands/research.md`

```markdown
---
description: Research literature using local knowledge base
argument-hint: <topic>
---

Research the topic: $ARGUMENTS

Use the CLI to search papers, analyze the most relevant ones, and generate a comprehensive report with IEEE-style citations.
```

**How It Works:**

1. User types: `/research digital health barriers`
2. Claude Code loads the command file
3. Replaces `$ARGUMENTS` with "digital health barriers"
4. Claude executes the instructions
5. Claude uses available tools (Bash, Read, Write) to complete the task

## Data Formats

### metadata.json

```json
{
  "papers": [
    {
      "id": "0001",                    // 4-digit format (v3.1)
      "doi": "10.1234/example",
      "title": "Paper Title",
      "authors": ["Smith J", "Doe A"],
      "year": 2023,
      "journal": "Nature",
      "volume": "500",
      "issue": "7461",
      "pages": "190-195",
      "abstract": "Abstract text...",
      "study_type": "rct",
      "sample_size": 487,
      "has_full_text": true,
      "filename": "paper_0001.md",      // 4-digit format
      "embedding_index": 0,
      "zotero_key": "ABC123",           // For cache tracking
      "quality_score": 85,              // NEW in v3.1 (0-100)
      "quality_factors": {              // NEW in v3.1
        "study_type_score": 25,
        "recency_score": 10,
        "sample_size_score": 5,
        "full_text_bonus": 5
      }
    }
  ],
  "total_papers": 2000,
  "last_updated": "2024-01-15T10:30:00Z",
  "embedding_model": "sentence-transformers/allenai-specter", // Scientific paper embeddings
  "model_version": "SPECTER",               // Optimized for academic literature
  "embedding_dimensions": 768
}
```

### papers/paper_0001.md

```markdown
# Paper Title

**Authors:** Smith J, Doe A
**Year:** 2023
**Journal:** Nature
**Volume:** 500
**Issue:** 7461
**Pages:** 190-195
**DOI:** 10.1234/example

## Abstract
[Abstract text]

## Full Text
[Complete paper content converted from PDF]
```

## Workflow

### User Experience

1. User types: `/research digital health interventions`
2. Claude searches knowledge base
3. Claude analyzes top 10-20 relevant papers
4. Claude generates research report with findings

### Technical Flow

1. **Search Phase**: Query → FAISS → Relevant paper IDs
2. **Retrieval Phase**: Read markdown files for selected papers
3. **Analysis Phase**: Claude evaluates evidence quality and extracts findings
4. **Report Phase**: Generate structured report with citations

## Research Report Format

```markdown
# Research Report: [Topic]
Date: [YYYY-MM-DD]

## Executive Summary
[Brief overview of findings]

## Key Findings
1. [Finding] [1], [2]
2. [Finding] [3]-[5]
3. [Finding] [6]

## Evidence Quality
- High confidence: [Topics with strong evidence]
- Medium confidence: [Topics with moderate evidence]
- Low confidence: [Topics needing more research]

## References (IEEE Style)
[1] J. Smith and A. Doe, "Paper Title," Nature, vol. 500, no. 7461, pp. 190-195, 2023.
[2] M. Johnson et al., "Another Paper," Science, vol. 380, no. 6641, pp. 123-128, 2024.
[3] L. Williams, "Study Title," IEEE Trans. Med. Imaging, vol. 42, no. 3, pp. 678-690, Mar. 2023.
```

### IEEE Citation Format

The system should format citations as:

```
[#] Author(s), "Title," Journal, vol. X, no. Y, pp. ZZZ-ZZZ, Month Year.
```

**In-text citations**: Use bracketed numbers [1], [2], [3]
**Multiple citations**: Use ranges [1]-[3] or lists [1], [4], [7]

## Technical Specifications

### Dependencies

- `faiss-cpu`: Semantic search
- `sentence-transformers`: SPECTER embeddings for scientific papers
- `transformers`: Required by sentence-transformers
- `torch`: Deep learning framework for SPECTER (GPU support if available)
- `PyMuPDF`: Fast PDF text extraction (significantly faster than pdfplumber)
- `click`: CLI framework
- `tqdm`: Progress bars
- `requests`: Zotero API access

### Performance Targets (Estimated)

- KB build:
  - With SPECTER: Approximately 30 minutes on CPU, 10 minutes on GPU for 2000 papers (varies by hardware)
  - Rebuild with caches: 1-2 minutes (both PDF and embedding caches)
  - PDF extraction: Estimated ~13 papers/second with cache
  - Embedding generation: ~1 paper/sec (CPU) or ~8 papers/sec (GPU)
- Search: <100ms for filtered searches
- Full analysis: 1-6 minutes
- Storage: ~2GB total
- Cache: ~2-3MB per 100 papers

### Embedding Model

- **Model**: sentence-transformers/allenai-specter (current implementation)
- **Dimensions**: 768
- **Context**: 512 tokens (processes title + abstract)
- **Advantages**: Specifically trained on scientific papers, outperforms general models
- **GPU Support**: Automatic detection, 10x speedup when available
- **Note**: CLI help may show "SciNCL" but the implementation uses SPECTER model

## Advantages of This Approach

1. **Portable**: Copy kb_data/ folder anywhere
2. **Evidence-Based**: Automatic study type classification and quality indicators
3. **No Runtime Dependencies**: Doesn't need Zotero after setup
4. **Fast**: Direct file access with advanced filtering
5. **Offline**: Works without internet
6. **Version Control**: Text files can be tracked in git
7. **Visual Hierarchy**: Clear markers showing evidence quality (⭐ for reviews, ● for RCTs)
8. **Debuggable**: Can manually read/edit papers

## Error Handling

- **Missing KB**: "Knowledge base not found. Run build_kb.py first."
- **No results**: "No relevant papers found. Try broader search terms."
- **File errors**: Gracefully skip corrupted files, log issues
