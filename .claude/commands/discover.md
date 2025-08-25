---
description: Discover external papers via comprehensive Semantic Scholar search based on research gaps
argument-hint: [report_name.md] or ["search topic"] (optional - uses latest report if empty)
allowed-tools: Read, Bash(python src/discover.py:*), WebSearch, Glob, LS
model: claude-3-5-sonnet-20241022
---

# External Paper Discovery: $ARGUMENTS

I'll discover relevant external papers using Semantic Scholar's comprehensive database (214M papers, 85% digital health coverage), adapting my approach based on what will be most useful for your research.

## Input Options

- **No arguments**: I'll find the most recent `reports/research_*.md` file for gap analysis
- **Quoted topic**: Direct search on your specified topic (e.g., `"diabetes management"`)
- **report_name.md**: Analysis of a specific research report from the `reports/` directory

## Discovery Approach

I'll use my judgment to analyze your research needs and discover relevant external papers by:

### For Research Reports (Gap Analysis)

- Reading the report to identify research limitations and methodological gaps
- Extracting relevant keywords, population focus, and study requirements from gap descriptions
- Determining appropriate search parameters based on the research context and gap urgency
- Looking for cross-domain opportunities (medical + technical + behavioral research)

### For Direct Topics

- Conducting comprehensive external search using appropriate keywords and filters
- Assessing knowledge base coverage to understand what's already available vs. what's missing
- Providing recommendations for search strategy and quality thresholds

### Web Research Integration

I can supplement Semantic Scholar discovery with targeted web research **when appropriate**:

**Use WebSearch when:**

- Semantic Scholar returns fewer than 10 relevant papers
- Very recent topics (last 6-12 months) needing latest developments
- Specialized domains requiring regulatory/technical documents
- Clinical trial protocols or grey literature specifically needed

**Avoid WebSearch when:**

- Semantic Scholar provides sufficient comprehensive results
- Academic literature is the primary need (Semantic Scholar's strength)
- Time-sensitive queries where speed is prioritized

Web research targets specialized repositories (PubMed clinical trials, IEEE standards, arXiv preprints) and regulatory sources that complement Semantic Scholar's academic coverage.

## Discovery Tool

I use the comprehensive discovery tool via `python src/discover.py` with various filters and options. For complete usage details, see @docs/api-reference.md under the `discover.py` section.

Key capabilities include:

- Quality thresholding (HIGH: 80+, MEDIUM: 60+, LOW: 40+)
- Population-specific term expansion (pediatric, elderly, women, developing countries)
- Study type filtering (RCT, systematic reviews, conference papers, etc.)
- Citation impact and year range controls
- DOI-based KB filtering to focus on external papers

## Coverage Assessment

I'll provide traffic light status for knowledge base completeness:

- 🟢 **EXCELLENT** (1000+ KB papers): Comprehensive coverage detected
- 🟡 **GOOD** (100-999 KB papers): Solid coverage with potential gaps
- 🔴 **NEEDS IMPROVEMENT** (<100 KB papers): Significant gaps likely

## Output

I'll generate a comprehensive discovery report saved to `exports/discovery_<topic>_<timestamp>.md` that includes:

- Clear explanation of search strategy and rationale
- External papers grouped by relevance and quality
- Coverage assessment with actionable guidance
- DOI lists ready for Zotero import
- Next steps tailored to your research workflow
- Web research findings when applicable

The report follows the same structure as other discovery reports for consistency and includes all necessary information for reproducing the search and importing the results.

## Usage Examples

```bash
/discover                           # Uses latest research report for gap analysis
/discover "AI medical diagnosis"    # Direct topic search
/discover diabetes_review_2024.md   # Analysis of specific report
```

Let me analyze your input and discover what external research is available to complement your knowledge base.
