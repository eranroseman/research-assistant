# Paper Filtering Strategy for v5

## Document Type Classification

v5.0 focuses exclusively on **research papers** and explicitly excludes books and conference proceedings. This decision is based on empirical analysis of 2,221 documents.

### What We Extract (Research Papers)

- Journal articles
- Conference papers
- Preprints (arXiv, bioRxiv, medRxiv)
- Clinical trial reports
- Systematic reviews and meta-analyses
- Brief communications
- Letters to the editor (if containing research)

### What We Exclude (Books/Proceedings)

- Books and book chapters
- Handbooks and textbooks
- Conference proceedings (entire volumes)
- Technical reports
- White papers
- Dissertations/theses
- Workshop proceedings

## Empirical Evidence

Analysis of 11 failed extractions from 2,221 documents:

```
Failed Documents (10 were books/proceedings):
- Human-Computer Interaction INTERACT 2023 (65.2 MB) - Conference proceedings
- Digital Phenotyping and Mobile Sensing (7.9 MB) - Book
- The Handbook of Health Behavior Change (50.4 MB) - Handbook
- Health behavior and health education (3.3 MB) - Textbook
- Human-Computer Interaction HCI 2023 (65.2 MB) - Conference proceedings
- Planning, implementing, and evaluating programs (7.9 MB) - Textbook
- Mobile Health Sensors, Analytic Methods (11.5 MB) - Book
- Theoretical foundations of health education (2.5 MB) - Textbook
- Heart Disease and Stroke Statistics 2021 (24.7 MB) - Statistical report
- An interactive voice response software (1.9 MB) - Research paper (corrupted PDF)

Only 1 actual research paper failed (corrupted PDF)
```

### Success Rate by Document Type

| Document Type | Success Rate | Processing Time |
|--------------|--------------|-----------------|
| Research Papers | 99.95% (2,210/2,211) | 14.8s average |
| Books/Proceedings | 0% (0/10) | Timeout/fail |

## Why Books Fail

### Structural Differences

**Research Papers** (IMRAD structure):
- Predictable sections: Abstract, Introduction, Methods, Results, Discussion
- Single continuous narrative
- 10-50 pages typical
- Clear bibliography section

**Books** (Complex structure):
- Multiple chapters with different authors
- Table of contents, indices, appendices
- 100-500+ pages
- Bibliography per chapter or at end
- Footnotes vs inline citations

### Processing Challenges

1. **Size**: Books average 20-65 MB vs 1-2 MB for papers
2. **Timeout**: Books need 125+ seconds vs 15s for papers
3. **Memory**: Books require 10+ GB RAM for processing
4. **Structure parsing**: Chapter detection fails with IMRAD-optimized parser
5. **Entity extraction**: Multiple author/affiliation formats break extraction

## Implementation: Automatic Filtering

### Size-Based Pre-Filter

```python
def is_likely_book(pdf_path: Path) -> bool:
    """Pre-filter obvious books based on size."""
    size_mb = pdf_path.stat().st_size / (1024 * 1024)

    # Papers rarely exceed 10MB
    if size_mb > 15:
        return True

    return False
```

### Title-Based Detection

```python
BOOK_INDICATORS = [
    'handbook', 'textbook', 'manual', 'guide',
    'proceedings', 'conference', 'workshop',
    'volume', 'edition', 'chapter'
]

def is_book_by_title(title: str) -> bool:
    """Detect books by title patterns."""
    title_lower = title.lower()
    return any(indicator in title_lower for indicator in BOOK_INDICATORS)
```

### Page Count Detection

```python
def check_page_count(pdf_path: Path) -> int:
    """Books typically have >100 pages."""
    with fitz.open(pdf_path) as pdf:
        return len(pdf)

def is_book_by_pages(pdf_path: Path) -> bool:
    """Research papers rarely exceed 50 pages."""
    return check_page_count(pdf_path) > 75
```

## Quality Filtering Workflow (Updated Aug 31, 2025 - Final)

### Stage 1: Grobid Extraction
- Extract all PDFs with TEI XML output
- ~99.5% success rate for research papers

### Stage 2: Full Text Recovery
- Re-process TEI XML to extract section text (bug fix)
- Recovers ~85.9M characters of research content

### Stage 3: Quality Filtering
Papers are EXCLUDED only if they:
- Have abstract-only (no full text) - 3 papers
- Have no content at all (failed extraction) - 6 papers
- Have insufficient text (<1000 chars) - 3 papers
- Missing BOTH title AND DOI (unidentifiable) - 30 papers

**IMPORTANT**: Papers missing ONLY title are INCLUDED if they have DOI + content.
Titles can be recovered in post-processing via CrossRef/S2 lookup.

### Stage 4: CrossRef Enrichment
- Recovered 74/82 missing titles (90.2% success)
- Found 144/179 missing DOIs (80.4% success)
- Cleaned 4 malformed DOIs
- Total: 222 papers enriched

### Stage 5: Non-Article Filtering
Papers EXCLUDED as non-articles:
- Supplemental materials (2 items) - PNAS supplements
- Datasets (7 items) - FigShare, OSF, Zenodo
- Editorials/Comments (10 items) - Not primary research
- **NOT excluded**: Papers with malformed DOIs (they have valid content)

### Stage 6: Final DOI Cleaning
- Fixed malformed DOIs (removed appended text, trailing periods)
- Recovered 4/5 remaining titles (80% success)
- Result: 99.95% title coverage (1 paper still missing)

### Stage 7: Final Cleanup
- Removed 1 article without title (paper ID: 6IP6AXAI)
- Paper had 21K chars of content but title unrecoverable
- Added to PDF quality report for transparency
- Final: 100% title coverage (2,150 articles)

## PDF Quality Report Integration

Papers that fail extraction or quality filtering are added to the PDF quality report:

```python
def add_to_quality_report(failed_papers: List[Dict]):
    """Add failed extractions to PDF quality report."""

    report = []
    for paper in failed_papers:
        # Classify failure reason
        if is_likely_book(paper['path']):
            reason = "Book/Proceedings (not supported)"
        elif paper['error'] == 'HTTP_500':
            reason = "Corrupted PDF"
        else:
            reason = "Unknown extraction failure"

        report.append({
            'title': paper['title'],
            'size_mb': paper['size_mb'],
            'reason': reason,
            'recommendation': get_recommendation(reason)
        })

    save_quality_report(report)
```

## User Guidance

### Pre-Build Recommendation

```
Before running extraction:
1. Review your Zotero library for books/proceedings
2. Move them to a separate collection (optional)
3. Focus on research papers for v5 extraction
```

### Build Output

```
Starting v5 extraction...
✓ Detected 2,221 documents in Zotero
✓ Filtered out 10 books/proceedings (moved to skip list)
✓ Processing 2,211 research papers

Progress: [████████████████████] 2,211/2,211 (100%)
Time: 9.5 hours

Results:
- Successfully extracted: 2,210 papers (99.95%)
- Failed extraction: 1 paper (corrupted PDF)
- Skipped (books): 10 documents

See pdf_quality_report.md for details on skipped/failed documents
```

## Future Considerations

### Book Support (v6.0?)

If book extraction becomes necessary:

1. **Different extraction pipeline**: Book-specific Grobid configuration
2. **Chapter segmentation**: Custom logic for multi-author works
3. **Extended timeouts**: 5-10 minutes per book
4. **Separate storage**: Books in different KB due to size
5. **Different search strategy**: Chapter-level vs paper-level search

### Current Workaround

For essential book content:
1. Extract key chapters as separate PDFs
2. Treat chapters as individual "papers"
3. Process through standard pipeline
4. Manually link related chapters in metadata

## Key Takeaways

1. **v5 is optimized for research papers** - 99.95% success rate
2. **Books require different processing** - Not a simple timeout fix
3. **Clear scope improves reliability** - No ambiguous failures
4. **Failed papers go to quality report** - Transparent failure tracking
5. **Future book support needs v6** - Separate pipeline required
