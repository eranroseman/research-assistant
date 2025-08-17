# Research Assistant - Simplified Specifications

## Overview

A Claude Code slash command that performs literature research using a pre-built, portable knowledge base of 2000+ academic papers.

## Architecture

```
Setup Phase (once):     Zotero → Build Script → Portable KB
Runtime Phase (always): /research command → Search → Analyze → Report
```

## Data Structure

```
kb_data/
├── index.faiss          # Semantic search index (150MB)
├── metadata.json        # Paper metadata for all articles
├── .pdf_text_cache.json # PDF extraction cache (metadata-based, JSON format)
└── papers/              
    ├── paper_001.md     # Full text in markdown
    ├── paper_002.md     # One file per paper
    └── ...              # 2000+ files
```

## Implementation

### 1. Knowledge Base Builder (`build_kb.py`)

**Purpose**: One-time conversion of Zotero library to portable format

**Process**:

1. Extract papers from Zotero (local API)
2. Convert PDFs to markdown files (with caching)
3. Build FAISS index from abstracts
4. Save metadata as JSON

**Features**:
- PyMuPDF for fast PDF text extraction (~13 papers/second)
- Metadata-based caching (file size + modification time)
- `--clear-cache` flag for fresh extraction

**Usage**:

```bash
python build_kb.py              # Creates kb_data/ folder
python build_kb.py --clear-cache # Force fresh extraction
```

### 2. CLI Tool (`cli.py`)

**Commands**:

```bash
python cli.py search "query"    # Returns relevant paper IDs
python cli.py get <paper_id>    # Returns full paper text
```

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
      "id": "001",
      "doi": "10.1234/example",
      "title": "Paper Title",
      "authors": ["Smith J", "Doe A"],
      "year": 2023,
      "journal": "Nature",
      "volume": "500",
      "issue": "7461",
      "pages": "190-195",
      "abstract": "Abstract text...",
      "filename": "paper_001.md",
      "embedding_index": 0
    }
  ],
  "total_papers": 2000,
  "last_updated": "2024-01-15"
}
```

### papers/paper_001.md

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
- `sentence-transformers`: Embeddings (model: all-MiniLM-L6-v2)
- `PyMuPDF`: Fast PDF text extraction (37x faster than pdfplumber)
- `click`: CLI framework
- `tqdm`: Progress bars
- `requests`: Zotero API access

### Performance Targets

- KB build: 
  - First build: ~5 minutes for 2000 papers
  - Cached rebuild: <1 minute
- Search: <1 second
- Full analysis: 1-6 minutes
- Storage: ~2GB total
- Cache: ~2-3MB per 100 papers

### Embedding Model

- **Model**: sentence-transformers/all-MiniLM-L6-v2
- **Dimensions**: 384
- **Context**: 256 tokens (sufficient for abstracts)

## Advantages of This Approach

1. **Portable**: Copy kb_data/ folder anywhere
2. **No Runtime Dependencies**: Doesn't need Zotero after setup
3. **Fast**: Direct file access, no API calls
4. **Offline**: Works without internet
5. **Version Control**: Text files can be tracked in git
6. **Debuggable**: Can manually read/edit papers

## Error Handling

- **Missing KB**: "Knowledge base not found. Run build_kb.py first."
- **No results**: "No relevant papers found. Try broader search terms."
- **File errors**: Gracefully skip corrupted files, log issues
