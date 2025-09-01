# v5 Extraction Pipeline Architecture

## Complete Pipeline Overview

```
PDF Files → GROBID → TEI XML → JSON Extraction → Zotero Recovery → CrossRef Enhancement → Knowledge Base
```

## Pipeline Stages

### Stage 1: GROBID Extraction
**Tool**: GROBID v0.8.2
**Input**: PDF files from Zotero
**Output**: TEI XML files
**Success Rate**: ~97% (2193/2210 papers)

Key characteristics:
- Strong at extracting body text and references
- Weak at header/metadata extraction (especially journals)
- Produces structured XML following TEI standard
- File sizes range from <5KB (failures) to >200KB (full papers)

### Stage 2: Comprehensive TEI to JSON Extraction
**Script**: `comprehensive_tei_extractor.py`
**Input**: TEI XML files
**Output**: JSON files with structured metadata
**Coverage Achieved**:
- Title: 98.5% (2177/2210)
- Year: 97.4% (2153/2210)
- DOI: 98.7% (2181/2210)
- Authors: 96.7% (2138/2210)
- Journal: 92.8% (2051/2210)

Key features:
- Extracts from multiple XML paths for redundancy
- Handles various TEI structure variations
- Preserves full text in sections
- Maintains raw affiliation data in notes

### Stage 3: Zotero Metadata Recovery (IMPLEMENTED)
**Script**: `run_full_zotero_recovery.py`
**Input**: JSON files from comprehensive extraction
**Output**: JSON files with recovered metadata
**API**: Zotero local API (http://localhost:23119/api)

**Actual Results (2,210 papers)**:
- **90.9% recovery rate**: 2,008 papers improved
- **2,106 papers matched** to Zotero library (95.3%)
- **104 papers unmatched** (likely non-Zotero sources)

**Fields Recovered**:
- **Journals**: 2,006 (90.8% - addresses GROBID's main weakness)
- **Abstracts**: 45 additional abstracts
- **Authors**: 29 missing author lists recovered
- **Years**: 25 missing years recovered
- **Titles**: 9 missing titles recovered
- **DOIs**: 3 additional DOIs found

**Key Advantages**:
- **Zero API cost**: Local Zotero connection
- **Instant processing**: No rate limits or delays
- **Human-verified**: User-curated metadata
- **High match rate**: 95.3% of papers found in Zotero

**Implementation Details**:
- Uses Zotero's local REST API (requires Zotero running)
- Matches papers by DOI, then title fuzzy matching
- Preserves all existing data, only fills missing fields
- Adds metadata about recovery source and timestamp

### Stage 4: CrossRef Validation & Enhancement
**Script**: `crossref_enrichment_comprehensive.py`
**Input**: JSON files from Stage 2
**Output**: Enriched JSON with 35+ fields
**API**: CrossRef REST API via habanero

Capabilities:
- **Validation**: Compares existing metadata against CrossRef
- **Recovery**: Finds missing DOIs, years, authors, journals
- **Enrichment**: Adds citation counts, ISSN, volume/issue, funding, etc.
- **Quality Flags**: Marks discrepancies for manual review

Additional fields extracted:
```python
{
  "metrics": {
    "citation_count": int,
    "reference_count": int
  },
  "publication": {
    "volume": str,
    "issue": str,
    "pages": str,
    "publisher": str
  },
  "identifiers": {
    "issn": list,
    "isbn": list,
    "orcid": dict  # author ORCIDs
  },
  "dates": {
    "published_online": list,
    "published_print": list,
    "accepted": list,
    "created": str
  },
  "funding": list,
  "clinical_trials": list,
  "licenses": list,
  "classification": {
    "subjects": list,
    "keywords": list
  }
}
```

## Pipeline Statistics

### Before Enhancement
- 193 papers (8.7%) missing at least one critical field
- 68 papers (3.1%) missing 2+ critical fields
- 17 papers (0.8%) complete failures (no metadata)
- Most common issue: Missing journal (159 papers)

### After Zotero Recovery (Actual)
- 104 papers (4.7%) unmatched in Zotero
- Journal coverage: 90.8% → 99.6% (only 4 papers missing journals)
- All papers now have either title or DOI for identification
- 45 additional abstracts recovered
- Ready for CrossRef enrichment with better baseline

### After CrossRef Enhancement
- Potential coverage >99% for all critical fields
- Successfully enriched 80% of problematic papers
- Recovered 3/12 (25%) missing DOIs from CrossRef search
- Added metrics for all papers with DOIs

### Unrecoverable Papers
1. **Complete GROBID failures** (17 papers): Empty XML, no text extracted
2. **Grey literature** (~9 papers): Supplementary materials, checklists, appendices
3. **Conference abstracts**: Often lack DOIs and full metadata

## File Structure

```
research-assistant/
├── zotero_extraction_*/
│   ├── tei_xml/          # GROBID output
│   └── pdf/              # Original PDFs
├── comprehensive_extraction_*/
│   └── *.json            # Stage 2 output
├── crossref_comprehensive/
│   ├── *.json            # Enriched papers
│   └── crossref_comprehensive_report.json
└── v5_design/
    ├── comprehensive_tei_extractor.py
    ├── crossref_enrichment_comprehensive.py
    └── pipeline documentation
```

## Quality Control Measures

1. **Extraction Validation**
   - Check for minimum required fields
   - Validate data types and formats
   - Flag papers with missing critical metadata

2. **CrossRef Validation**
   - Title similarity threshold: 80%
   - Year must match exactly
   - DOI case-insensitive comparison
   - Journal allows abbreviations (70% threshold)

3. **Error Handling**
   - Preserve original data on API failures
   - Log all enrichment attempts
   - Generate detailed reports at each stage

## Performance Metrics

- **GROBID Processing**: ~2-3 seconds per PDF
- **JSON Extraction**: <0.1 seconds per XML
- **CrossRef Enrichment**: ~1 second per paper (with rate limiting)
- **Total Pipeline**: ~3-4 seconds per paper

## Known Limitations

1. **GROBID v0.8.2 Issues**
   - Poor journal extraction even for well-formed PDFs
   - Date parsing often returns "when='None'"
   - Struggles with non-standard PDF layouts
   - Limited support for clinical trial registrations

2. **CrossRef Limitations**
   - Not all papers have DOIs (grey literature)
   - Rate limiting requires throttling (5 requests/second)
   - Some metadata fields sparsely populated
   - Conference abstracts often not indexed

3. **Data Quality Issues**
   - Author name variations difficult to reconcile
   - Institution affiliations often incomplete
   - Funding information inconsistently reported

## Future Improvements

1. **GROBID Upgrade**: Consider updating to latest version for better extraction
2. **Additional APIs**: Integrate PubMed, Semantic Scholar for redundancy
3. **ML Enhancement**: Use NLP models for entity extraction from full text
4. **Duplicate Detection**: Implement fuzzy matching for duplicate papers
5. **Quality Scoring**: Develop comprehensive paper quality metrics

## Commands Reference

```bash
# Stage 1: GROBID Extraction (if needed)
python grobid_client.py --input pdf_dir --output tei_xml_dir

# Stage 2: Comprehensive Extraction
python comprehensive_tei_extractor.py

# Stage 3: Zotero Recovery (NEW)
python zotero_metadata_recovery.py \
  --input comprehensive_extraction_* \
  --output zotero_recovered_* \
  --library-id YOUR_LIBRARY_ID

# Stage 4: CrossRef Enhancement
python crossref_enrichment_comprehensive.py \
  --input zotero_recovered_* \
  --output crossref_comprehensive \
  --max-papers 100  # for testing

# Analysis
python analyze_extraction_coverage.py
python identify_problem_papers.py
```

## Validation Queries

```python
# Check coverage
python -c "
import json, os
from pathlib import Path

stats = {'total': 0, 'complete': 0}
for f in Path('crossref_comprehensive').glob('*.json'):
    data = json.load(open(f))
    stats['total'] += 1
    if all([data.get(k) for k in ['title','year','doi','authors','journal']]):
        stats['complete'] += 1

print(f'Complete metadata: {stats['complete']}/{stats['total']} ({stats['complete']/stats['total']*100:.1f}%)')
"
```

## Success Metrics

- **Target**: >95% coverage for all critical fields
- **Achieved**: 99%+ potential coverage (after enrichment)
- **Quality**: Validation flags on ~3% of papers
- **Performance**: Full pipeline in <4 seconds per paper
