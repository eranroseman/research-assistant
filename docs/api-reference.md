# API Reference

> **📚 Back to main docs**: [README.md](../README.md) | [Technical Specs](technical-specs.md) | [Advanced Usage](advanced-usage.md)

## CLI Commands

### `cli.py search`

Search the knowledge base for relevant papers with SPECTER embeddings (note: CLI help may show "SciNCL" but uses SPECTER model).

```bash
python src/cli.py search [OPTIONS] QUERY
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--k` | `-k` | INT | 10 | Number of results to return |
| `--verbose` | `-v` | FLAG | False | Show abstracts in results |
| `--json` | | FLAG | False | Output results as JSON |
| `--after` | | INT | None | Filter papers published after this year |
| `--type` | | MULTI | None | Filter by study type (can specify multiple) |
| **`--mode`** | | CHOICE | auto | **NEW v3.0**: Search mode (auto/question/similar/explore) |
| **`--show-quality`** | | FLAG | False | **NEW v3.0**: Display quality scores (0-100) |
| **`--quality-min`** | | INT | None | **NEW v3.0**: Minimum quality score filter |

#### Search Modes (NEW in v3.0)

- `auto` - Automatically detect search intent (default)
- `question` - Optimized for answering research questions
- `similar` - Find papers similar to a topic/concept
- `explore` - Broad exploration of research areas

#### Study Type Filters

- `systematic_review` - Systematic reviews and meta-analyses (⭐)
- `rct` - Randomized controlled trials (●)
- `cohort` - Cohort studies (◐)
- `case_control` - Case-control studies (○)
- `cross_sectional` - Cross-sectional studies (◔)
- `case_report` - Case reports and series (·)
- `study` - Generic/unclassified studies (·)

#### Quality Scores (NEW in v3.0)

Papers are scored 0-100 based on:
- Study type hierarchy (35 points max)
- Recency (10 points for 2022+)
- Sample size (10 points for n>1000)
- Full text availability (5 points)

Visual indicators:
- ⭐ Excellent (80-100)
- ● Good (60-79)
- ○ Moderate (40-59)
- · Lower (<40)

#### Examples

```bash
# Basic search (auto-detects mode)
python src/cli.py search "digital health"

# Research question (auto-detects question mode)
python src/cli.py search "What causes diabetes complications?"

# Find similar papers
python src/cli.py search "papers similar to telemedicine interventions" --mode similar

# High-quality evidence only
python src/cli.py search "metabolic syndrome" --quality-min 70 --show-quality

# Comprehensive review with quality scores
python src/cli.py search "AI diagnosis" -k 30 --show-quality --after 2020

# Filter by study type and quality
python src/cli.py search "diabetes" --type systematic_review --type rct --quality-min 60

# JSON output with quality scores
python src/cli.py search "wearables" --json --show-quality > results.json
```

### `cli.py get`

Retrieve the full text of a specific paper.

```bash
python src/cli.py get [OPTIONS] PAPER_ID
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | PATH | None | Save output to file |

#### Paper ID Format

**v3.0 Security**: Paper IDs must be exactly 4 digits (e.g., 0001, 0234, 1999)
- Path traversal attempts are blocked
- Invalid formats raise clear error messages

#### Examples

```bash
# Display paper in terminal
python src/cli.py get 0001

# Save to file
python src/cli.py get 0001 -o paper.md

# View specific paper
python src/cli.py get 1234

# Invalid formats (blocked in v3.0)
python src/cli.py get 1        # Error: Must be 4 digits
python src/cli.py get abc      # Error: Must be 4 digits
python src/cli.py get ../etc   # Error: Invalid format
```

### `cli.py cite`

Generate IEEE-style citations for papers matching a query.

```bash
python src/cli.py cite [OPTIONS] QUERY
```

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--k` | `-k` | INT | 5 | Number of citations to generate |

#### Examples

```bash
# Generate 5 citations
python src/cli.py cite "machine learning healthcare"

# Generate 10 citations
python src/cli.py cite "digital therapeutics" -k 10
```

### `cli.py info`

Display information about the knowledge base.

```bash
python src/cli.py info
```

#### Output includes:
- Total number of papers
- Last update date
- Storage location
- Index status
- Cache sizes
- Embedding model used

#### Example

```bash
$ python src/cli.py info

Knowledge Base Information:
- Papers: 2147
- Last updated: 2024-08-18
- Location: kb_data/
- Index: kb_data/index.faiss (150MB)
- PDF Cache: kb_data/.pdf_text_cache.json (148MB)
- Embedding Cache: kb_data/.embedding_cache.json + .embedding_data.npy (500MB)
- Model: sentence-transformers/allenai-specter
- Performance: 40-50% faster with v3.0 optimizations (cache built at runtime)
```

## Build Script

### `build_kb.py`

Build or update the knowledge base from Zotero library.

```bash
python src/build_kb.py [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--demo` | FLAG | False | Build demo database with 5 sample papers |
| `--api-url` | STRING | Auto | Custom Zotero API URL |
| `--knowledge-base-path` | PATH | kb_data | Path to knowledge base directory |
| `--zotero-data-dir` | PATH | ~/Zotero | Path to Zotero data directory |
| `--clear-cache` | FLAG | False | Clear both PDF and embedding caches |
| `--update` | FLAG | False | Incremental update - only add new papers (10x faster) |
| `--export` | PATH | None | Export knowledge base to portable tar.gz archive |
| `--import` | PATH | None | Import knowledge base from tar.gz archive |

#### Examples

```bash
# Build from Zotero (interactive)
python src/build_kb.py

# Build demo database
python src/build_kb.py --demo

# Force full rebuild
python src/build_kb.py --clear-cache

# WSL with Windows Zotero
python src/build_kb.py --api-url http://172.20.1.1:23119/api

# Custom paths
python src/build_kb.py --knowledge-base-path /data/kb --zotero-data-dir /mnt/c/Users/name/Zotero

# Incremental update (10x faster)
python src/build_kb.py --update

# Export knowledge base
python src/build_kb.py --export kb_backup.tar.gz

# Import knowledge base
python src/build_kb.py --import kb_backup.tar.gz
```

#### Interactive Options

When running without flags, the script presents options:

1. **Quick Update** (Y/Enter): Add only new papers, uses caches (1-2 minutes)
2. **Full Rebuild** (C): Clear everything and rebuild from scratch (30 minutes)
3. **Exit** (N): Cancel without changes

## Python API

### Using the Knowledge Base Programmatically

```python
from pathlib import Path
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class KnowledgeBase:
    def __init__(self, kb_path="kb_data"):
        self.kb_path = Path(kb_path)
        self.index = faiss.read_index(str(self.kb_path / "index.faiss"))
        with open(self.kb_path / "metadata.json") as f:
            self.metadata = json.load(f)
        self.model = SentenceTransformer('sentence-transformers/allenai-specter')

    def search(self, query, k=10, after_year=None, study_types=None):
        # Encode query
        query_embedding = self.model.encode([query])

        # Search index (search more to account for filtering)
        search_k = min(k * 3, len(self.metadata['papers']))
        distances, indices = self.index.search(query_embedding.astype('float32'), search_k)

        # Filter results
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(self.metadata['papers']) and idx != -1:
                paper = self.metadata['papers'][idx]

                # Apply filters
                if after_year and paper.get('year', 0) < after_year:
                    continue
                if study_types and paper.get('study_type') not in study_types:
                    continue

                results.append((idx, float(dist), paper))
                if len(results) >= k:
                    break

        return results

    def get_paper(self, paper_id):
        paper_file = self.kb_path / "papers" / f"paper_{paper_id}.md"
        if paper_file.exists():
            return paper_file.read_text()
        return None
```

### Example Usage

```python
# Initialize
kb = KnowledgeBase()

# Search
results = kb.search("diabetes interventions", k=5, after_year=2020)
for paper in results:
    print(f"[{paper['year']}] {paper['title']}")

# Get full text
full_text = kb.get_paper("0001")
print(full_text)

# Advanced filtering
rct_results = kb.search(
    "telemedicine",
    k=10,
    study_types=['rct', 'systematic_review']
)
```

## Slash Command Integration

The `/research` command is defined in `.claude/commands/research.md`:

```markdown
---
description: Research literature using local knowledge base
argument-hint: <topic>
---

Research the topic: $ARGUMENTS

Use the CLI to search papers, analyze the most relevant ones, and generate a comprehensive report with IEEE-style citations.
```

### Variables Available

- `$ARGUMENTS`: Everything typed after the command
- `$USER`: Current username
- `$PWD`: Current working directory

### Customizing the Command

Edit `.claude/commands/research.md` to modify behavior:

```markdown
Research "$ARGUMENTS" focusing on papers from the last 5 years.
Include a section on methodology quality.
```

## Data Formats

### metadata.json Structure

```json
{
  "papers": [
    {
      "id": "0001",
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
      "filename": "paper_0001.md",
      "embedding_index": 0
    }
  ],
  "total_papers": 2147,
  "last_updated": "2024-08-18T10:30:00Z",
  "embedding_model": "allenai-specter",
  "embedding_dimensions": 768
}
```

### Paper Markdown Format

Each paper in `papers/` follows this structure:

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

## Error Codes

| Code | Message | Solution |
|------|---------|----------|
| KB001 | Knowledge base not found | Run `src/build_kb.py` first |
| KB002 | Index file corrupted | Rebuild with `--clear-cache` |
| KB003 | Metadata mismatch | Rebuild knowledge base |
| API001 | Zotero not accessible | Check Zotero is running |
| API002 | API not enabled | Enable in Zotero settings |
| PDF001 | PDF extraction failed | Check PDF file integrity |
| EMB001 | Model loading failed | Reinstall sentence-transformers |
