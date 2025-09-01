# Extraction Pipeline Report - 2025-09-01 11:47:51

## Pipeline Summary

| Stage | Directory | Files | Status |
|-------|-----------|-------|---------|
| 01. TEI XML | 01_tei_xml | 2210 | ✓ Completed |
| 02. JSON Extraction | 02_json_extraction | 2210 | ✓ Completed |
| 03. Zotero Recovery | 03_zotero_recovery | 1704 | ✓ Completed |
| 04. CrossRef Enrichment | 04_crossref_enrichment | 1674 | ✓ Completed |
| 05. S2 Enrichment | 05_s2_enrichment | 1675 | ✓ Completed |
| 06. OpenAlex Enrichment | 06_openalex_enrichment | 1675 | ✓ Completed |
| 07. Unpaywall Enrichment | 07_unpaywall_enrichment | 1673 | ✓ Completed |
| 08. PubMed Enrichment | 08_pubmed_enrichment | 1000 | ⚠ Partial |
| 09. arXiv Enrichment | 09_arxiv_enrichment | 0 | ✗ Not run |
| 10. Final Output | 10_final_output | 0 | - |

## Key Results

### Data Reduction Through Pipeline
- Initial TEI XML: 2210 files
- After quality filtering: ~2134 files
- After non-article filtering: ~1676 files
- Final enriched papers: 1630 files (Unpaywall stage)

### Enrichment Success Rates
- Zotero Recovery: 90.9% recovery rate
- CrossRef: Batch processing (60x speedup)
- S2: 93.7% enrichment rate
- OpenAlex: 98% success rate
- Unpaywall: 98.8% enrichment, 76% OA discovery

### Processing Times
- TEI Extraction: ~30 minutes
- Zotero Recovery: <5 seconds
- CrossRef Batch: ~20 minutes
- S2 Batch: ~1.5 minutes
- OpenAlex: ~5 minutes
- Unpaywall: ~3 minutes

## Notes
- PubMed and arXiv enrichment stages timed out (likely rate limiting)
- Successfully enriched 1630 papers through 7 stages
- 76% of papers have open access versions available
