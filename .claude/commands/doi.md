---
description: Search for peer-reviewed articles and return DOIs
argument-hint: <research topic or keywords> (optional - uses previous /research topic if empty)
allowed-tools: WebSearch, WebFetch, Read, Write
model: claude-3-5-sonnet-20241022
---

# DOI Finder for Academic Articles

## Search Topic: $ARGUMENTS

I'll find DOIs for recent peer-reviewed articles on this topic.

## Process

### 1. Determine Topic

If no arguments provided:
- Check for recent research reports in `reviews/` folder
- Look for identified gaps or DOI recommendations from previous /research commands
- Extract specific missing areas or suggested searches
- Use the most relevant gap as the search topic

If arguments provided:
- Use the provided topic directly

### 2. Web Search Strategy

I'll search for academic articles across these priority sources:

- **PubMed/PubMed Central**: pubmed.ncbi.nlm.nih.gov
- **Google Scholar**: scholar.google.com
- **Semantic Scholar**: semanticscholar.org
- **CrossRef**: search.crossref.org
- **CORE**: core.ac.uk
- **arXiv**: arxiv.org (for CS/physics/math papers)
- **bioRxiv**: biorxiv.org (for biology preprints)
- **PLOS ONE**: journals.plos.org/plosone
- **Nature**: nature.com/search
- **Science**: science.org
- **The Lancet**: thelancet.com
- **JAMA Network**: jamanetwork.com
- **BMJ**: bmj.com
- **Wiley Online**: onlinelibrary.wiley.com
- **ScienceDirect**: sciencedirect.com
- **Springer**: link.springer.com
- **Taylor & Francis**: tandfonline.com
- **IEEE Xplore**: ieeexplore.ieee.org (for engineering/CS)
- **ACM Digital Library**: dl.acm.org (for computer science)

### 3. Extract & Format DOIs

I'll extract DOIs (pattern: `10.\d{4,}/[-._;()/:\w]+`) and present them in a clean list.

### 4. Output

**Found DOIs for "$ARGUMENTS":**

```text
10.xxxx/xxxxx
10.xxxx/xxxxx
10.xxxx/xxxxx
10.xxxx/xxxxx
10.xxxx/xxxxx
```

Results saved to: `reviews/external_dois_<topic>_<timestamp>.txt`

## Notes

- Focuses on papers from 2020-2025 unless specified otherwise
- Prioritizes systematic reviews and RCTs when available
- Returns 10-15 DOIs by default
