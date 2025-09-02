# Incremental Processing Design for V5 Pipeline

## Date: December 3, 2024

## Core Principle

**By default, each stage should only process NEW papers that haven't been processed yet.**

When you add 5 new papers to Zotero, the pipeline should:
1. Extract only those 5 new papers
2. Enrich only those 5 papers at each stage
3. Preserve all existing processed data

## Current State Analysis

### Stages That Already Support Incremental Processing

1. **arXiv Enrichment** ✅
   - Skips papers with `arxiv_checked=True`
   - Skips papers with existing `arxiv_url` or `arxiv_categories`
   - Only processes truly new papers

2. **TEI Extraction** ⚠️ Partial
   - Has checkpoint system
   - Checks `output_file.exists()`
   - BUT: No `--force` flag to override

3. **Zotero Recovery** ⚠️ Partial
   - Has checkpoint system
   - Processes all files in input directory
   - No skip logic for already-processed papers

### Stages That Need Updates

4. **CrossRef Enrichment** ❌
   - Always processes all input papers
   - No check for existing `crossref_*` fields

5. **S2 Enrichment** ❌
   - Always processes all input papers
   - No check for existing `s2_*` fields

6. **OpenAlex Enrichment** ❌
   - Always processes all input papers
   - No check for existing `openalex_*` fields

7. **Unpaywall Enrichment** ❌
   - Always processes all input papers
   - No check for existing `unpaywall_*` fields

8. **PubMed Enrichment** ❌
   - Always processes all input papers
   - No check for existing `pubmed_*` fields

## Proposed Implementation

### 1. Standard Skip Logic Pattern

Each enrichment stage should follow this pattern:

```python
def load_papers_to_process(input_dir, force=False):
    """Load only papers that need processing."""
    papers_to_process = []
    already_processed = []

    for paper_file in input_dir.glob("*.json"):
        with open(paper_file) as f:
            paper = json.load(f)

        # Skip if already enriched (unless --force)
        if not force:
            # Check for stage-specific markers
            if paper.get(f"{STAGE_NAME}_enriched"):
                already_processed.append(paper_file.stem)
                continue

            # Check for stage-specific data
            if has_stage_data(paper):
                already_processed.append(paper_file.stem)
                continue

        papers_to_process.append((paper_file.stem, paper))

    if already_processed:
        print(f"Skipping {len(already_processed)} already enriched papers")

    return papers_to_process
```

### 2. Stage-Specific Markers

Each stage should add a marker when it processes a paper:

```python
# CrossRef
paper["crossref_enriched"] = True
paper["crossref_enriched_date"] = datetime.now(UTC).isoformat()

# S2
paper["s2_enriched"] = True
paper["s2_enriched_date"] = datetime.now(UTC).isoformat()

# OpenAlex
paper["openalex_enriched"] = True
paper["openalex_enriched_date"] = datetime.now(UTC).isoformat()

# Unpaywall
paper["unpaywall_enriched"] = True
paper["unpaywall_enriched_date"] = datetime.now(UTC).isoformat()

# PubMed
paper["pubmed_enriched"] = True
paper["pubmed_enriched_date"] = datetime.now(UTC).isoformat()
```

### 3. Detection Functions

Each stage needs a function to detect existing enrichment:

```python
def has_crossref_data(paper):
    """Check if paper already has CrossRef enrichment."""
    return any(key.startswith("crossref_") for key in paper.keys())

def has_s2_data(paper):
    """Check if paper already has S2 enrichment."""
    return any(key.startswith("s2_") for key in paper.keys())

def has_openalex_data(paper):
    """Check if paper already has OpenAlex enrichment."""
    return any(key.startswith("openalex_") for key in paper.keys())

def has_unpaywall_data(paper):
    """Check if paper already has Unpaywall enrichment."""
    return any(key.startswith("unpaywall_") for key in paper.keys())

def has_pubmed_data(paper):
    """Check if paper already has PubMed enrichment."""
    return any(key.startswith("pubmed_") for key in paper.keys())
```

### 4. Command-Line Flags

All enrichment scripts should support:

```python
parser.add_argument(
    "--force",
    action="store_true",
    help="Force re-enrichment even if already processed"
)

parser.add_argument(
    "--force-paper",
    action="append",
    help="Force re-enrichment for specific paper ID (can be used multiple times)"
)
```

### 5. Incremental TEI/GROBID Processing

For TEI extraction from PDFs:

```python
def get_new_pdfs(pdf_dir, tei_dir, force=False):
    """Get only PDFs that haven't been processed."""
    new_pdfs = []

    for pdf_file in pdf_dir.glob("*.pdf"):
        tei_file = tei_dir / f"{pdf_file.stem}.tei.xml"

        if not force and tei_file.exists():
            continue  # Skip already processed

        new_pdfs.append(pdf_file)

    return new_pdfs
```

## Usage Examples

### Scenario 1: Adding 5 New Papers

```bash
# Extract new papers from Zotero
python src/extract_zotero_library.py
# Output: 5 new PDFs extracted

# Process only new PDFs with GROBID
python src/grobid_processor.py
# Output: Processing 5 new PDFs (skipping 2,200 existing)

# Extract only new TEI files
python src/tei_extractor.py
# Output: Processing 5 new TEI files (skipping 2,200 existing)

# Enrich only new papers
python src/crossref_enricher.py
# Output: Enriching 5 new papers (skipping 2,200 already enriched)
```

### Scenario 2: Force Re-enrichment

```bash
# Re-enrich everything with CrossRef
python src/crossref_enricher.py --force
# Output: Processing all 2,205 papers (force mode)

# Re-enrich specific paper
python src/s2_enricher.py --force-paper paper_12345
# Output: Processing 1 paper (forced)
```

### Scenario 3: Partial Re-enrichment

```bash
# Re-enrich papers missing S2 data
python src/s2_enricher.py --missing-only
# Output: Processing 150 papers without S2 data (skipping 2,055 with data)
```

## Benefits

1. **Efficiency**: Don't waste API calls on already-enriched papers
2. **Speed**: Adding 5 papers takes minutes, not hours
3. **Safety**: Won't accidentally overwrite existing enrichments
4. **Flexibility**: Can force re-enrichment when needed
5. **Transparency**: Clear reporting of what's being skipped

## Implementation Priority

1. **HIGH**: CrossRef, S2, OpenAlex (expensive API calls)
2. **MEDIUM**: Unpaywall, PubMed (moderate API usage)
3. **LOW**: TEI extraction (already has some skip logic)

## Migration Path

To upgrade existing pipeline:

```python
# Add enrichment markers to existing papers
def add_enrichment_markers(directory):
    """Add markers to papers that already have enrichment."""
    for paper_file in directory.glob("*.json"):
        with open(paper_file) as f:
            paper = json.load(f)

        modified = False

        # Check and add markers for each stage
        if has_crossref_data(paper) and not paper.get("crossref_enriched"):
            paper["crossref_enriched"] = True
            paper["crossref_enriched_date"] = "2024-12-01T00:00:00Z"  # Approximate
            modified = True

        # ... similar for other stages ...

        if modified:
            with open(paper_file, "w") as f:
                json.dump(paper, f, indent=2)
```

## Expected Time Savings

### Current (Process Everything)
- Adding 5 papers: ~15 hours (same as 2,200 papers!)

### With Incremental Processing
- Adding 5 papers: ~2 minutes
- Adding 50 papers: ~20 minutes
- Adding 500 papers: ~3 hours

### Speedup Factor
- 5 papers: **450x faster**
- 50 papers: **45x faster**
- 500 papers: **5x faster**
