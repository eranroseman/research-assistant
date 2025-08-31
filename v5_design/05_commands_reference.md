# Commands Reference

## Script Name Changes (v4.6 → v5.0)

| Old Name | New Name | Purpose | Rationale |
|----------|----------|---------|-----------|
| `cli.py` | `kbq.py` | Knowledge Base Query | Reflects entity-aware search |
| `analyze_gaps.py` | `gaps.py` | Gap Analysis | Shorter, cleaner |
| `build_kb.py` | `build.py` | Build Knowledge Base | Simplified |
| `discover.py` | `discover.py` | External Discovery | Unchanged |

## build.py - Knowledge Base Building

### Core Operation Flags

```bash
--rebuild          # Full rebuild instead of incremental
--demo             # Test with 5 papers only
--export FILE      # Export KB and exit
--import FILE      # Import KB and exit
--no-gaps          # Skip gap analysis (saves 15-25 min)
--collection NAME  # Process only specific Zotero collection
```

### Information Flags

```bash
--estimate         # Show time estimate and exit
--progress         # Show current build status and exit
```

### Examples

```bash
# Prerequisites: Start Grobid locally
sudo docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full

# Default: entire library + reports + gaps
python src/build.py

# Process specific collection
python src/build.py --collection "PhD Thesis"

# Full rebuild with two-pass extraction
python src/build.py --rebuild

# Quick test
python src/build.py --demo

# Skip gap analysis for faster completion
python src/build.py --no-gaps

# Check timing before starting (9.5 hours for 2,200 papers)
python src/build.py --estimate

# Specific collection without gaps
python src/build.py --collection "ML Papers" --no-gaps
```

### Automatic Reports

After each build, these reports are generated:

1. **PDF Quality Report** → `exports/analysis_pdf_quality.md`
   - Only if issues found
   - Papers missing PDFs
   - Papers with small PDFs
   - Papers without DOIs
   - Papers that failed extraction (books, corrupted PDFs)

2. **Gap Analysis** → `exports/gap_analysis_*.md`
   - Unless `--no-gaps` specified
   - Takes 15-25 minutes
   - Comprehensive citation analysis

## kbq.py - Knowledge Base Query

### Search Commands

```bash
# Basic search with quality filtering
search "diabetes treatment" [--show-quality] [--quality-min 70]

# Entity-aware search with explicit filters
search "diabetes" \
  --min-sample 500 \
  --study-type RCT \
  --software Python \
  --year-from 2020 \
  --has-data \
  --max-p-value 0.05

# Advanced filtering
search "machine learning" \
  --exclude "deep learning" \
  --include "random forest" \
  --journal "Nature" \
  --group-by year \
  --export-csv results.csv

# Smart search (AI-enhanced)
smart-search "diabetes treatment" -k 30

# Author search
author "Smith J" [--exact]
```

### Retrieval Commands

```bash
# Get single paper
get 0001 [--sections abstract methods results] [--add-citation]

# Get multiple papers (10-20x faster)
get-batch 0001 0002 0003 [--sections abstract]

# Generate citations
cite 0001 0002 0003
```

### Batch Operations

```bash
# Use preset configurations
batch --preset research    # Top papers for research
batch --preset review      # Papers for literature review
batch --preset author-scan # Papers by specific authors

# Run commands from file
batch --file commands.txt
```

### Analysis Commands

```bash
# Show KB statistics
info

# Diagnose issues
diagnose
```

## discover.py - External Paper Discovery

### Basic Discovery

```bash
# Search by keywords
discover --keywords "machine learning, diabetes"

# With quality threshold
discover --keywords "AI diagnostics" \
  --quality-threshold HIGH \
  --year-from 2020 \
  --min-citations 50

# Filter by study type
discover --keywords "treatment" \
  --study-types "rct,cohort" \
  --limit 100
```

### v5.0 NEW: SPECTER2 Similarity

```bash
# Find papers similar to existing KB papers
discover --similar-to 0001,0002,0003 \
  --similarity-mode specter2 \
  --min-similarity 0.7

# Use local MPNet embeddings instead
discover --similar-to 0001 \
  --similarity-mode mpnet
```

### Advanced Filtering

```bash
# Focus on specific populations
discover --keywords "diabetes" \
  --population-focus pediatric

# Filter by author
discover --keywords "neural networks" \
  --author-filter "LeCun,Hinton,Bengio"

# Include quality explanations
discover --keywords "covid treatment" \
  --explain-quality

# Filter by reproducibility
discover --keywords "machine learning" \
  --min-reproducibility 60
```

### Coverage Information

```bash
# Show database coverage guide
discover --coverage-info

# Include existing KB papers in results
discover --keywords "diabetes" --include-kb-papers
```

## gaps.py - Gap Analysis

### Default Behavior (No Flags)

```bash
python src/gaps.py
# Runs comprehensive analysis:
# - min-citations: 10
# - year-from: all years
# - limit: unlimited
# - gap-type: citation
# - Runtime: 15-25 minutes
```

### Basic Filtering

```bash
# Focus on high-impact gaps
gaps --min-citations 100 --year-from 2020

# Quick analysis
gaps --limit 50 --min-citations 50

# Custom KB location
gaps --kb-path /path/to/kb_data/
```

### Gap Type Selection

```bash
# Citation gaps (default)
gaps --gap-type citation

# Papers by your KB authors
gaps --gap-type author

# Papers with same methods/tools
gaps --gap-type entity --show-missing software:Python

# Reproducible papers
gaps --gap-type reproducibility
```

### Entity Gap Analysis

```bash
# Find papers using same software
gaps --gap-type entity \
  --show-missing software:TensorFlow,dataset:MIMIC

# Generate entity coverage statistics
gaps --gap-type entity --entity-coverage
```

### Reproducibility Gaps

```bash
# Papers with available code/data
gaps --reproducibility-gaps --requires both

# Set minimum reproducibility score
gaps --reproducibility-gaps \
  --min-reproducibility-score 80
```

### Sample Size Gaps

```bash
# Find large studies
gaps --sample-size-gaps \
  --min-sample 5000 \
  --study-type RCT
```

### Common Patterns

```bash
# Quick check (5-10 min)
gaps --limit 50 --min-citations 100

# Recent high-impact only
gaps --year-from 2023 --min-citations 50

# Reproducible ML research
gaps --gap-type entity \
  --show-missing software:PyTorch \
  --reproducibility-gaps
```

## Migration from v4.6

### Removed Flags (No Longer Needed)

These flags were removed because v5.0 handles them automatically:

- `--api-url`, `--knowledge-base-path`, `--zotero-data-dir` - Uses standard paths
- `--yes`, `--auto-start` - Always automatic
- `--continue` - Auto-resumes from checkpoint
- `--skip-quality` - Auto-fallback if S2 unavailable
- `--quiet`, `--verbose` - Single optimized output mode
- `--phase`, `--features` - Always uses all features

### New v5.0 Features

- **Collection processing**: `--collection NAME`
- **Entity filters**: `--study-type`, `--min-sample`, etc.
- **SPECTER2 similarity**: `--similar-to`, `--similarity-mode`
- **Quality explanations**: `--explain-quality`
- **Reproducibility focus**: `--reproducibility-gaps`

### Migration Steps

```bash
# 1. Export current KB (optional backup)
python src/build.py --export kb_v4_backup.json

# 2. Clean slate for v5
rm -rf kb_data/

# 3. Update and rebuild
git pull
pip install -r requirements.txt
python src/build.py --rebuild
```

## Daily Workflow Examples

### Morning: Check for New Papers

```bash
# Incremental update (fast, automatic)
python src/build.py

# Update specific collection only
python src/build.py --collection "Current Research"

# Skip gap analysis for speed
python src/build.py --no-gaps
```

### Research Tasks

```bash
# Search with entity filters
python src/kbq.py search "diabetes" \
  --min-sample 500 \
  --study-type RCT \
  --year-from 2020

# Discover external papers
python src/discover.py \
  --keywords "diabetes, insulin" \
  --quality-threshold HIGH

# Find gaps in literature
python src/gaps.py --min-citations 50
```

### Weekly Maintenance

```bash
# Full rebuild (if needed)
python src/build.py --rebuild

# Export for backup
python src/build.py --export kb_backup_$(date +%Y%m%d).json
```

## Command Usage Patterns

### For Quick Results

```bash
# Fast KB update
build.py --no-gaps

# Quick search
kbq.py search "topic" --limit 10

# Fast gap check
gaps.py --limit 50
```

### For Comprehensive Analysis

```bash
# Full build with all reports
build.py --rebuild

# Detailed search with exports
kbq.py search "topic" --show-quality --export-csv

# Complete gap analysis
gaps.py
```

### For Specific Research

```bash
# Collection-focused build
build.py --collection "Project X"

# Method-specific discovery
discover.py --similar-to 0001,0002

# Tool-specific gaps
gaps.py --gap-type entity --show-missing software:R
```
