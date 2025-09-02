# Stage 4: Quality Filtering and Non-Research Paper Removal

## Overview

The quality filtering stage systematically removes problematic and non-research papers from the extracted dataset, ensuring only high-quality research articles remain in the knowledge base.

## Pipeline Position

```
Stage 1: GROBID Extraction (PDF → TEI XML)
Stage 2: TEI to JSON Extraction
Stage 3: CrossRef Validation & Enhancement
→ Stage 4: Quality Filtering & Paper Classification ←
Stage 5: Final Knowledge Base Construction
```

## Filtering Stages (7 Sequential Filters)

### 1. PDF Quality Assessment
**Script**: `pdf_quality_filter.py`
**Purpose**: Remove corrupted or problematic PDFs before processing
**Criteria**:
- File corruption detection
- Size validation (too small/too large)
- Format verification

### 2. GROBID Success Validation
**Script**: Integrated in extraction pipeline
**Purpose**: Identify complete extraction failures
**Criteria**:
- TEI XML file size < 5KB indicates failure
- Empty body text
- No extractable content

**Results**: 11 complete failures (10 books/proceedings, 1 corrupted)

### 3. Document Type Classification
**Script**: `filter_non_articles.py`
**Purpose**: Remove non-research documents
**Filters**:
- Books and proceedings (detected by size, structure, metadata)
- Supplementary materials (DOI patterns like "DCSupplemental")
- Datasets (FigShare, Zenodo, OSF repositories)
- Editorials, comments, letters

**Results**: 19 non-articles removed

### 4. Content Sufficiency Check
**Script**: Integrated validation
**Purpose**: Ensure adequate content for analysis
**Criteria**:
- Minimum text length: 1,000 characters
- Required sections present
- Abstract availability

**Results**: 42 papers with insufficient content removed

### 5. Metadata Completeness
**Script**: Part of extraction validation
**Purpose**: Ensure papers have identifiable metadata
**Requirements (at least one):
- Valid DOI
- Complete title
- Author information

**Results**: 30 papers without DOI or title removed

### 6. Malformed DOI Cleanup
**Script**: `fix_malformed_dois.py`
**Purpose**: Clean and validate DOI formats
**Actions**:
- Remove URL prefixes
- Standardize format
- Validate structure

### 7. Final Title Recovery
**Script**: `final_cleanup_no_title.py`
**Purpose**: Last attempt to recover missing titles
**Methods**:
- CrossRef lookup by DOI
- Filename parsing
- Manual patterns

**Results**: All but 1 paper recovered

## Statistics

### Input
- **Total PDFs**: 2,221
- **From Zotero**: Digital health collection

### Filtering Results
| Stage | Papers Removed | Reason |
|-------|---------------|---------|
| GROBID Failures | 11 | 10 books/proceedings, 1 corrupted |
| Non-Articles | 19 | Supplements, datasets, editorials |
| Insufficient Content | 42 | No text, abstracts only, fragments |
| No Identifiers | 30 | Missing both DOI and title |
| Final Cleanup | 1 | Unrecoverable title |
| **Total Removed** | **71** | **3.2% of input** |

### Output
- **Clean Articles**: 2,150
- **Success Rate**: 96.8%
- **All have**: Title, full text, identifiers
- **Character count**: 83.8M total

## Implementation Scripts

### Primary Filtering Script
```python
# filter_non_articles.py
def classify_document(metadata):
    """Classify document type based on multiple signals"""

    # Check DOI patterns
    if "DCSupplemental" in doi:
        return "supplement"
    if "figshare" in doi or "zenodo" in doi:
        return "dataset"

    # Check file size (books typically >5MB)
    if file_size > 5_000_000:
        return "book"

    # Check title patterns
    if title and any(word in title.lower() for word in
                     ["editorial", "erratum", "correction"]):
        return "editorial"

    # Check structure
    if not abstract and full_text_length < 1000:
        return "fragment"

    return "article"
```

### Quality Validation
```python
# validate_extraction_quality.py
def validate_paper(paper_data):
    """Comprehensive quality validation"""

    issues = []

    # Critical metadata
    if not paper_data.get("title"):
        issues.append("missing_title")
    if not paper_data.get("doi"):
        issues.append("missing_doi")

    # Content validation
    full_text = paper_data.get("full_text", "")
    if len(full_text) < 1000:
        issues.append("insufficient_text")

    # Classify severity
    if len(issues) >= 2:
        return "exclude", issues
    elif issues:
        return "review", issues
    else:
        return "include", []
```

## Quality Reports

### Generated Reports
1. **PDF Quality Report** (`pdf_quality_report_YYYYMMDD.json`)
   - Lists all extraction failures
   - Provides failure reasons
   - Suggests remediation

2. **Non-Article Report** (`non_articles_YYYYMMDD.txt`)
   - Documents excluded content
   - Categorizes by type
   - Preserves for audit trail

3. **Final Statistics** (`kb_final_stats_YYYYMMDD.json`)
   - Complete filtering metrics
   - Stage-by-stage breakdown
   - Success rates by category

## Key Insights

### Document Type Distribution
- **Research Articles**: 96.8% (2,150)
- **Books/Proceedings**: 0.5% (10)
- **Supplementary**: 0.9% (19)
- **Failed Extractions**: 1.9% (42)

### Common Failure Patterns
1. **Books**: Large multi-author works break GROBID's IMRAD parser
2. **Supplements**: Often lack proper metadata
3. **Conference Abstracts**: Insufficient content for full extraction
4. **Grey Literature**: No DOIs, limited metadata

### Success Factors
- GROBID v0.8.2 handles 99.5% of research papers successfully
- CrossRef recovers ~25% of missing DOIs
- Title recovery achieves 99.95% success (only 1 failure)

## Commands

```bash
# Run complete filtering pipeline
python filter_non_articles.py \
  --input comprehensive_extraction_* \
  --output kb_articles_only_*

# Generate quality report
python generate_pdf_quality_report.py \
  --failed-papers failed_papers.json \
  --output pdf_quality_report.json

# Validate final dataset
python validate_kb_quality.py \
  --input kb_final_* \
  --min-text-length 1000 \
  --require-doi
```

## Best Practices

1. **Preserve Audit Trail**: Keep records of all excluded papers
2. **Manual Review**: Papers with content but missing titles may be recoverable
3. **Iterative Refinement**: Adjust thresholds based on domain requirements
4. **Quality Over Quantity**: Better to exclude questionable content
5. **Document Decisions**: Record filtering criteria for reproducibility

## Future Improvements

1. **Machine Learning Classification**
   - Train classifier on document types
   - Improve accuracy of article vs non-article detection

2. **Enhanced Title Recovery**
   - OCR for image-based titles
   - Pattern matching from citations

3. **Selective Inclusion**
   - Allow certain high-value grey literature
   - Domain-specific inclusion rules

4. **Automated Remediation**
   - Re-process failed papers with different settings
   - Alternative extraction tools for books

## Integration with Pipeline

This filtering stage is critical for ensuring knowledge base quality. It:
- Prevents contamination with non-research content
- Ensures all papers meet minimum quality standards
- Provides transparency through detailed reporting
- Enables confident downstream analysis

The filtered output serves as the foundation for the final knowledge base construction in Stage 5.
