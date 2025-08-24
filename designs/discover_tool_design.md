# Discovery Tool Design v3.1 (Semantic Scholar First)

**Created**: 2024-08-21
**Updated**: 2024-08-21
**Status**: Design Phase - Semantic Scholar Foundation with Coverage Documentation
**Purpose**: Comprehensive external paper discovery using Semantic Scholar with maximum infrastructure reuse
**Dependencies**: Basic Quality Scoring (from build_kb.py)
**Logging**: Command Usage Analytics for usage pattern analysis and usability improvement

## Overview

The `src/discover.py` tool provides comprehensive academic paper discovery using Semantic Scholar's 214M paper database with maximum infrastructure reuse. It leverages existing Semantic Scholar API patterns from build_kb.py for consistent API usage, basic quality scoring, and caching while delivering superior "What's out there?" coverage.

**Key Design Principles:**
- **Comprehensive Single Source**: Semantic Scholar's cross-domain coverage (85% of digital health research)
- **Maximum Infrastructure Reuse**: Reuse existing Semantic Scholar API patterns from build_kb.py
- **Output Consistency**: Match gap analysis report structure exactly
- **Coverage Transparency**: Clear documentation of when specialized sources are needed
- **User Flexibility**: Manual access to specialized sources + future slash commands
- **Command Usage Analytics**: Track user patterns for continuous usability improvements

## Core Architecture

### Command-Line Interface (Semantic Scholar Optimized)
```bash
python src/discover.py [OPTIONS]

Required:
  --keywords TEXT             Comma-separated search keywords

Optional:
  --year-from INTEGER         Only papers from this year onwards (default: 2020)
  --study-types TEXT          Study types: rct,systematic_review,cohort,case_study,etc.
  --min-citations INTEGER     Minimum citation count (default: 0)
  --limit INTEGER             Maximum results (default: 50)
  --quality-threshold TEXT    HIGH (80+), MEDIUM (60+), LOW (40+)
  --author-filter TEXT        Focus on specific researchers (max 5)
  --population-focus TEXT     Target populations: pediatric, elderly, women, etc.
  --include-kb-papers         Include papers already in knowledge base (default: exclude)
  --output-file TEXT          Output path (default: exports/discovery_YYYY_MM_DD.md)
  --help                      Show help message

Source (fixed):
  --source semantic_scholar   (Primary source in v3.0, leverages existing infrastructure)

Total: 10 manageable options with professional capability

**Coverage Documentation Built-in:**
  --coverage-info             Show when to use specialized databases (PubMed, IEEE, arXiv)

Total: 11 manageable options including KB filtering and coverage guidance
```

### Usage Examples (Comprehensive)
```bash
# Basic cross-domain search - only new papers (default)
python src/discover.py --keywords "diabetes,mobile health" --year-from 2020

# High-quality recent studies across all disciplines - new papers only
python src/discover.py --keywords "telemedicine,rural health" --quality-threshold HIGH --year-from 2022

# Include KB papers for validation and overlap analysis
python src/discover.py --keywords "AI,diagnostics" --include-kb-papers --quality-threshold HIGH

# Check coverage guidance for specialized needs
python src/discover.py --coverage-info

# Clinical population targeting - new discoveries only
python src/discover.py --keywords "depression,intervention" --population-focus "adolescents" --study-types "rct,systematic_review"

# Author-focused discovery with KB overlap check
python src/discover.py --keywords "AI,healthcare" --author-filter "LeCun Y,Ng A" --include-kb-papers --quality-threshold MEDIUM

# Advanced digital health research
python src/discover.py \
  --keywords "digital therapeutics,depression" \
  --quality-threshold HIGH \
  --population-focus "pediatric" \
  --year-from 2022 \
  --limit 30
```

## Core Functions (Simplified)

### 1. Search Query Generation
```python
@dataclass
class SearchQuery:
    query_text: str
    filters: Dict[str, Any]
    source: str = "semantic_scholar"  # Fixed to Semantic Scholar in v3.0

def generate_semantic_scholar_query(keywords: List[str],
                                   year_from: Optional[int],
                                   study_types: List[str],
                                   population_focus: Optional[str]) -> SearchQuery:
    """Generate single comprehensive Semantic Scholar query for bulk search."""
    # Combine all keywords into comprehensive OR query
    base_terms = keywords.copy()

    # Add population-specific terms
    if population_focus:
        base_terms.extend(POPULATION_FOCUS_TERMS.get(population_focus, []))

    # Add study type terms
    if study_types:
        base_terms.extend(study_types)

    # Create single comprehensive query for bulk search endpoint
    combined_query = " OR ".join(base_terms)

    return SearchQuery(
        query_text=combined_query,
        filters={'year_from': year_from, 'limit': 1000},  # Use bulk search
        source="semantic_scholar"
    )
```

### 2. Semantic Scholar Academic Search (Comprehensive)
```python
class SemanticScholarDiscovery:
    def __init__(self, include_kb_papers=False):
        # Reuse existing Semantic Scholar API patterns from build_kb.py
        from src.build_kb import (
            get_semantic_scholar_data_sync,
            get_semantic_scholar_data_batch
        )
        from src.cli import _setup_command_usage_logger, _log_command_usage_event
        from src.cli_kb_index import load_kb_index

        self.api_sync = get_semantic_scholar_data_sync
        self.api_batch = get_semantic_scholar_data_batch
        self.rate_limiter = RateLimiter(requests_per_second=1.0)  # Unauthenticated limit
        self.command_usage_logger = _setup_command_usage_logger()
        self.log_ux_event = _log_ux_event
        self.include_kb_papers = include_kb_papers

        # Load KB DOIs for filtering (if exclude mode)
        if not include_kb_papers:
            self.kb_dois = self._load_kb_dois()
        else:
            self.kb_dois = set()

    def _load_kb_dois(self) -> Set[str]:
        """Load all DOIs from knowledge base for filtering."""
        try:
            kb_index = load_kb_index()
            return {paper.get('doi', '').lower() for paper in kb_index.values() if paper.get('doi')}
        except Exception:
            # If KB not available, don't filter
            return set()

    async def search_papers(self, query: SearchQuery) -> List[Paper]:
        """Execute single comprehensive Semantic Scholar search."""
        # Log search performance for optimization
        start_time = time.time()

        # Single bulk search instead of multiple queries
        papers = await self._execute_bulk_search(query)

        # Assess KB coverage before filtering (always performed)
        coverage_status = self._assess_kb_coverage(queries, papers)

        # Filter out KB papers unless explicitly included
        if not self.include_kb_papers:
            kb_papers_found = len([p for p in papers if p.doi.lower() in self.kb_dois])
            papers = [p for p in papers if p.doi.lower() not in self.kb_dois]

            # Log filtering results
            self.log_ux_event("discover_kb_filtering",
                            total_papers_found=len(papers) + kb_papers_found,
                            kb_papers_filtered=kb_papers_found,
                            new_papers_returned=len(papers),
                            kb_overlap_percentage=kb_papers_found / (len(papers) + kb_papers_found) * 100 if papers or kb_papers_found else 0)

        # Log API performance metrics
        api_time = time.time() - start_time
        self.log_ux_event("discover_api_performance",
                         response_time_ms=int(api_time * 1000),
                         query_count=len(queries),
                         include_kb_papers=self.include_kb_papers)

        return papers, coverage_status

    def _assess_kb_coverage(self, queries: List[SearchQuery], discovery_papers: List[Paper]) -> Dict[str, Any]:
        """Assess KB coverage and return traffic light status."""
        from src.cli import search_papers  # Reuse existing search infrastructure

        # Extract keywords from queries for KB search
        all_keywords = []
        for query in queries:
            all_keywords.extend(query.query_text.split())
        keywords_str = " ".join(set(all_keywords))

        # Search KB using existing CLI infrastructure
        try:
            kb_results = search_papers(keywords_str, limit=1000)  # Get comprehensive KB results
            kb_count = len(kb_results)
        except Exception:
            kb_count = 0

        # Analyze discovery results
        discovery_count = len(discovery_papers)
        high_impact_missing = len([p for p in discovery_papers if getattr(p, 'citation_count', 0) > 50])
        recent_missing = len([p for p in discovery_papers if getattr(p, 'year', 0) >= 2022])

        # Traffic light assessment logic
        if kb_count < 10 or high_impact_missing > 10:
            status = "🔴 NEEDS UPDATE"
            message = f"Only {kb_count} KB papers found. Missing {high_impact_missing} high-impact papers."
            recommendation = "Import priority papers before research"
        elif kb_count < 25 or recent_missing > 5:
            status = "🟡 ADEQUATE"
            message = f"{kb_count} KB papers found. Consider adding {recent_missing} recent papers."
            recommendation = "Consider updating for latest developments"
        else:
            status = "🟢 EXCELLENT"
            message = f"{kb_count} KB papers found. Comprehensive coverage detected."
            recommendation = "Proceed with research confidently"

        return {
            'status': status,
            'message': message,
            'recommendation': recommendation,
            'kb_count': kb_count,
            'discovery_count': discovery_count,
            'high_impact_missing': high_impact_missing,
            'recent_missing': recent_missing
        }
```

### 3. Paper Quality Scoring (Basic Scoring - Fast & API-Free)
```python
def score_discovery_papers(papers: List[Paper],
                          keywords: List[str]) -> List[ScoredPaper]:
    """Score papers using basic quality scoring - no API calls required."""
    # Import from build_kb.py (actual existing functions)
    from src.build_kb import calculate_basic_quality_score, detect_study_type

    scored_papers = []
    for paper in papers:
        # Detect study type from title/abstract (existing function)
        study_type = detect_study_type(f"{paper.title} {paper.abstract}")

        # Create paper dict for basic scoring
        paper_data = {
            'study_type': study_type,
            'year': paper.year,
            'journal': paper.venue,
            'has_full_text': bool(paper.abstract)
        }

        # Use existing basic scoring function (no API required)
        quality_score, explanation = calculate_basic_quality_score(paper_data)

        # Add keyword relevance scoring
        relevance_score = calculate_keyword_relevance(paper, keywords)
        overall_score = (quality_score + relevance_score) / 2

        confidence = "HIGH" if overall_score >= 80 else "MEDIUM" if overall_score >= 60 else "LOW"

        scored_papers.append(ScoredPaper(
            paper=paper,
            quality_score=quality_score,
            relevance_score=relevance_score,
            overall_score=overall_score,
            confidence=confidence,
            reasoning=explanation
        ))

    return sorted(scored_papers, key=lambda x: x.overall_score, reverse=True)
```

### 4. Report Generation (Aligned with Gap Analysis)
```python
def generate_discovery_report(scored_papers: List[ScoredPaper],
                             search_params: Dict[str, Any],
                             coverage_status: Dict[str, Any]) -> str:
    """Create discovery report matching gap analysis structure with KB coverage assessment."""
    # KB Coverage Status section (new)
    coverage_section = format_coverage_status(coverage_status)

    # Use gap analysis report template
    # Same confidence grouping (HIGH/MEDIUM/LOW)
    # Same DOI list format for Zotero import
    # Consistent metadata and search documentation
    # Match exports/ directory structure

    return f"""
{coverage_section}

## Discovery Results
{standard_discovery_content}
"""

def format_coverage_status(coverage_status: Dict[str, Any]) -> str:
    """Format KB coverage assessment for report output."""
    return f"""
## {coverage_status['status']}
- **Current KB**: {coverage_status['kb_count']} relevant papers found
- **External Papers**: {coverage_status['discovery_count']} discovered
- **Assessment**: {coverage_status['message']}
- **Recommendation**: {coverage_status['recommendation']}
"""
```

## Data Structures

### Paper Object
```python
@dataclass
class Paper:
    doi: str
    title: str
    authors: List[str]
    year: int
    abstract: str
    citation_count: int
    venue: str
    source: str  # Which database found it
    url: str
    study_type: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
```

### Scored Paper
```python
@dataclass
class ScoredPaper:
    paper: Paper
    relevance_score: float  # 0-100: How well it addresses the gap
    quality_score: float    # 0-100: Overall paper quality
    overall_score: float    # Combined relevance + quality
    confidence: str         # HIGH/MEDIUM/LOW
    reasoning: str          # Why this paper is relevant
    gap_alignment: float    # How well it fits the gap context
```

### Search Configuration
```python
@dataclass
class SearchConfig:
    sources: List[str]
    max_results_per_source: int
    rate_limits: Dict[str, Dict[str, int]]
    quality_thresholds: Dict[str, float]
    cache_expiry_days: int
```

## Semantic Scholar Integration (Complete Infrastructure Reuse)

### Maximum Infrastructure Reuse
```python
class SemanticScholarDiscovery:
    def __init__(self):
        # Import components from build_kb.py (actual existing functions)
        from src.build_kb import (
            get_semantic_scholar_data_sync,
            get_semantic_scholar_data_batch,
            calculate_basic_quality_score,
            detect_study_type
        )
        from src.config import (
            CONFIDENCE_HIGH_THRESHOLD,
            CONFIDENCE_MEDIUM_THRESHOLD
        )

        self.api_sync = get_semantic_scholar_data_sync
        self.api_batch = get_semantic_scholar_data_batch
        self.rate_limiter = RateLimiter(requests_per_second=1.0)
        self.quality_scorer = calculate_basic_quality_score
        self.study_type_detector = detect_study_type

    async def search_papers(self, query: SearchQuery) -> List[Paper]:
        """Search using bulk endpoint with rate limiting."""
        # Use bulk search endpoint for efficiency
        await self.rate_limiter.wait_if_needed()

        # Single comprehensive search via bulk endpoint
        response = requests.get(
            f"{SEMANTIC_SCHOLAR_API_URL}/paper/search/bulk",
            params={
                'query': query.query_text,
                'limit': query.filters.get('limit', 1000),
                'fields': 'title,authors,year,abstract,citationCount,venue,externalIds'
            }
        )

        if response.status_code == 200:
            data = response.json()
            papers = [self._parse_paper(p) for p in data.get('data', [])]

            # Apply client-side filters (year, study type, etc.)
            filtered_papers = self._apply_filters(papers, query.filters)

            return filtered_papers
        else:
            raise APIConnectionError(f"Search failed: {response.status_code}")
```

### Manual Access Strategy (Phase 1)
```python
# Users access other sources manually when needed:
# - PubMed: https://pubmed.ncbi.nlm.nih.gov/
# - IEEE: https://ieeexplore.ieee.org/
# - arXiv: https://arxiv.org/search/
# - Direct DOI import to Zotero

# Future slash command integration (Phase 2):
# /pubmed "clinical diabetes trials"
# /ieee "wearable health sensors"
# /arxiv "healthcare AI 2024"
```

## Output Structure

### Markdown Report Format
```markdown
# Discovery Results
**Generated**: 2024-08-21 10:30:00
**Search Strategy**: Cross-domain discovery for mobile health interventions
**Duration**: 2-5 seconds (basic quality scoring, no API delays)

## 🟡 KB Coverage Status: ADEQUATE
- **Current KB**: 34 relevant papers found
- **External Papers**: 89 discovered
- **Assessment**: Good historical coverage, missing recent developments
- **Recommendation**: Consider updating for latest developments

## Search Parameters
- **Keywords**: diabetes, mobile health, pediatric
- **Year Range**: 2020-2024
- **Study Types**: RCT, intervention
- **Source**: Semantic Scholar (comprehensive cross-domain coverage)
- **Population Focus**: pediatric
- **Quality Threshold**: HIGH (80+ score)

## Coverage Information
**Semantic Scholar provides comprehensive coverage (85% of digital health research).**

For specialized needs, consider manual access:
- 🔍 **PubMed**: Clinical trial protocols, regulatory submissions
- 🔍 **IEEE**: Engineering standards, technical implementation details
- 🔍 **arXiv**: Latest AI/ML preprints (6-12 months ahead)

**Manual Access Links:**
- PubMed: https://pubmed.ncbi.nlm.nih.gov/
- IEEE: https://ieeexplore.ieee.org/
- arXiv: https://arxiv.org/search/

## High Confidence Results (Score 80+)

### Paper 1: Mobile Health Apps for Pediatric Diabetes Management
- **DOI**: 10.1038/s41591-2023-12345
- **Authors**: Smith J, Garcia M, Johnson L, et al.
- **Year**: 2023
- **Citations**: 145
- **Venue**: Nature Medicine
- **Relevance Score**: 92/100
- **Quality Score**: 87/100
- **Why Relevant**: Directly addresses mobile health gap in pediatric diabetes populations, includes intervention study with 500+ participants
- **Study Type**: Randomized Controlled Trial

### Paper 2: Digital Health Interventions in Developing Countries
- **DOI**: 10.1016/j.ijmedinf.2023.67890
- **Authors**: Patel R, Williams K, et al.
- **Year**: 2023
- **Citations**: 78
- **Venue**: International Journal of Medical Informatics
- **Relevance Score**: 88/100
- **Quality Score**: 82/100
- **Why Relevant**: Addresses geographic gap with focus on developing countries, systematic review of mobile health interventions
- **Study Type**: Systematic Review

## Medium Confidence Results (Score 60-79)
[Similar format for medium confidence papers]

## Low Confidence Results (Score 40-59)
[Similar format for low confidence papers]

## Search Performance
- **Total Papers Found**: 127
- **After Deduplication**: 89
- **High Confidence**: 12 papers
- **Medium Confidence**: 23 papers
- **Low Confidence**: 54 papers

## DOI Lists for Zotero Import

### High Confidence Papers (12 DOIs)
```text
10.1038/s41591-2023-12345
10.1016/j.ijmedinf.2023.67890
10.1001/jama.2023.11111
10.1056/NEJMoa2023456
10.1371/journal.pone.0298765
10.1186/s12911-023-02134-5
10.2196/43210
10.1038/s41746-023-00876-4
10.1016/j.diabres.2023.110123
10.1093/jamia/ocad098
10.1177/20552076231234567
10.1089/dia.2023.0234
```

### Medium Confidence Papers (23 DOIs)
[DOI list for medium confidence papers]

### All Papers Combined (89 DOIs)
[Complete DOI list for bulk import]
```

### JSON Export Format
```json
{
  "discovery_session": {
    "timestamp": "2024-08-21T10:30:00Z",
    "duration_seconds": 3.8,
    "search_params": {
      "keywords": ["diabetes", "mobile health", "pediatric"],
      "authors": [],
      "year_from": 2020,
      "study_types": ["rct", "intervention"],
      "min_citations": 0,
      "limit": 100,
      "gap_context": "coverage_gap",
      "search_strategy": "underserved_populations"
    },
    "performance": {
      "total_found": 127,
      "after_dedup": 89,
      "high_confidence": 12,
      "medium_confidence": 23,
      "low_confidence": 54
    },
    "papers": [
      {
        "doi": "10.1038/s41591-2023-12345",
        "title": "Mobile Health Apps for Pediatric Diabetes Management",
        "authors": ["Smith J", "Garcia M", "Johnson L"],
        "year": 2023,
        "citation_count": 145,
        "venue": "Nature Medicine",
        "relevance_score": 92,
        "quality_score": 87,
        "overall_score": 89.5,
        "confidence": "HIGH",
        "reasoning": "Directly addresses mobile health gap in pediatric diabetes populations"
      }
    ],
    "search_queries_used": [
      {
        "query_text": "diabetes mobile health pediatric intervention",
        "source": "pubmed",
        "filters": {"year_from": 2020, "study_type": "rct"}
      }
    ]
  }
}
```

## UX Analytics Integration

### Logging Infrastructure (Reused from cli.py)
```python
# Import existing logging infrastructure
from src.cli import _setup_command_usage_logger, _log_command_usage_event
import time
import uuid

# Initialize logging in main discover function
_session_id = str(uuid.uuid4())[:8]
_command_usage_logger = _setup_command_usage_logger()

def main():
    """Main discover function with comprehensive UX logging."""
    start_time = time.time()

    # Parse command line arguments
    args = parse_arguments()

    # Log command start with usage pattern details
    _log_ux_event(
        "discover_command_start",
        session_id=_session_id,
        keywords_count=len(args.keywords.split(',')),
        has_population_focus=bool(args.population_focus),
        has_quality_threshold=bool(args.quality_threshold),
        has_author_filter=bool(args.author_filter),
        has_study_types=bool(args.study_types),
        year_from=args.year_from,
        result_limit=args.limit,
        source=args.source,
        include_kb_papers=args.include_kb_papers
    )

    try:
        # Execute discovery
        results = discover_papers(args)

        # Log successful completion with results metrics
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "discover_command_success",
            session_id=_session_id,
            execution_time_ms=execution_time_ms,
            papers_found=len(results.papers),
            high_confidence_papers=len([p for p in results.papers if p.confidence == 'HIGH']),
            medium_confidence_papers=len([p for p in results.papers if p.confidence == 'MEDIUM']),
            low_confidence_papers=len([p for p in results.papers if p.confidence == 'LOW']),
            avg_quality_score=sum(p.quality_score for p in results.papers) / len(results.papers) if results.papers else 0,
            cross_domain_papers=len([p for p in results.papers if is_cross_domain(p)]),
            output_file=args.output_file,
            kb_coverage_status=results.coverage_status['status'],
            kb_papers_found=results.coverage_status['kb_count'],
            high_impact_missing=results.coverage_status['high_impact_missing']
        )

    except Exception as e:
        # Log error with diagnostic information
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "discover_command_error",
            session_id=_session_id,
            execution_time_ms=execution_time_ms,
            error_type=type(e).__name__,
            error_message=str(e)[:200],  # Truncate for privacy
            keywords_count=len(args.keywords.split(',')),
            source=args.source
        )
        raise
```

### Key Metrics for Usability Analysis

**Feature Adoption Tracking:**
```python
def log_feature_usage(args):
    """Track which CLI options are actually used."""
    _log_ux_event(
        "discover_feature_usage",
        option_population_focus=bool(args.population_focus),
        option_quality_threshold=bool(args.quality_threshold),
        option_author_filter=bool(args.author_filter),
        option_study_types=bool(args.study_types),
        option_min_citations=bool(args.min_citations),
        option_year_from=args.year_from != DEFAULT_YEAR_FROM,
        option_custom_limit=args.limit != DEFAULT_LIMIT,
        option_custom_output=bool(args.output_file),
        option_include_kb_papers=args.include_kb_papers,
        advanced_options_used=count_advanced_options(args)
    )
```

**Search Performance Metrics:**
```python
def log_search_performance(query_metrics):
    """Track API performance for optimization."""
    _log_ux_event(
        "discover_search_performance",
        semantic_scholar_response_time=query_metrics.api_response_time,
        query_complexity_score=query_metrics.complexity,
        rate_limit_delays=query_metrics.delays,
        cache_hit_rate=query_metrics.cache_hits / query_metrics.total_queries,
        failed_requests=query_metrics.failures,
        papers_per_query=query_metrics.avg_results_per_query
    )
```

**User Journey Analysis:**
```python
def log_result_interaction(results, user_actions):
    """Track what users do with discovery results."""
    _log_ux_event(
        "discover_result_usage",
        papers_exported=len(user_actions.exported_papers),
        doi_lists_generated=user_actions.doi_exports,
        report_sections_viewed=user_actions.sections_accessed,
        follow_up_searches=user_actions.refinement_attempts,
        zotero_import_indicated=user_actions.zotero_usage,
        coverage_info_requested=user_actions.coverage_help_used
    )
```

**Usability Pain Point Detection:**
```python
def log_usability_indicators(session_data):
    """Identify common user difficulties."""
    _log_ux_event(
        "discover_usability_metrics",
        command_retry_attempts=session_data.retry_count,
        help_flag_used=session_data.help_accessed,
        coverage_info_accessed=session_data.coverage_guidance_used,
        error_recovery_time=session_data.error_to_success_time,
        option_modification_count=session_data.parameter_changes,
        session_duration_minutes=session_data.total_session_time / 60
    )
```

### Analytics-Driven Improvements

**Data-Driven UX Optimization:**
1. **CLI Simplification**: Remove options with <5% usage rate
2. **Default Value Tuning**: Set defaults based on 90th percentile usage
3. **Error Prevention**: Warn about combinations that fail >20% of time
4. **Performance Focus**: Optimize operations taking >90th percentile time
5. **Feature Prioritization**: Develop most-requested missing capabilities

**Success Metrics to Track:**
- Command completion rate (success vs. abandonment)
- Time from command start to actionable results
- User satisfaction proxy (follow-up usage, result export rates)
- Feature adoption curves for new capabilities
- Error recovery patterns and user resilience

## Technical Implementation

### Rate Limiting Strategy (Proactive for Unauthenticated Access)
```python
class RateLimiter:
    def __init__(self, requests_per_second: float = 1.0):
        """Proactive rate limiter for unauthenticated Semantic Scholar API."""
        self.min_interval = 1.0 / requests_per_second  # 1 second for 1 RPS
        self.last_request_time = 0.0

    async def wait_if_needed(self):
        """Proactively wait to ensure we don't exceed rate limits."""
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            await asyncio.sleep(wait_time)

        self.last_request_time = time.time()

    def wait_sync(self):
        """Synchronous version for requests library."""
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            time.sleep(wait_time)

        self.last_request_time = time.time()
```

### Caching System
```python
class SearchCache:
    def __init__(self):
        self.cache_dir = Path("system/discovery_cache")
        self.expiry_days = 7

    def get_cached_results(self, query_hash: str) -> Optional[List[Paper]]:
        """Load cached search results if still valid."""
        # Generate query hash from parameters
        # Check cache file existence and age
        # Return cached results or None

    def save_results(self, query_hash: str, papers: List[Paper]):
        """Save search results to cache."""
        # Create cache directory if needed
        # Save with timestamp for expiry checking
```

### Error Handling
```python
class DiscoveryError(Exception):
    """Base exception for discovery tool errors."""
    pass

class APIRateLimitError(DiscoveryError):
    """Raised when API rate limits are exceeded."""
    pass

class APIConnectionError(DiscoveryError):
    """Raised when API connection fails."""
    pass

def with_retry(max_retries: int = 3, delay: float = 1.0):
    """Decorator for robust error handling with exponential backoff."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except APIRateLimitError:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (2 ** attempt))
                    else:
                        raise
                except APIConnectionError:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                    else:
                        raise
        return wrapper
    return decorator
```

### Quality Scoring Algorithm
```python
def calculate_basic_discovery_quality_score(paper: Paper) -> tuple[int, str]:
    """Calculate basic quality score using only search result data (no API calls)."""
    score = 50  # Base score
    components = []

    # Study type scoring (20 points max) - from abstract text analysis
    study_type = detect_study_type(f"{paper.title} {paper.abstract}")
    if study_type == "rct":
        score += 20
        components.append("RCT (+20)")
    elif study_type == "systematic_review":
        score += 15
        components.append("Systematic Review (+15)")
    elif study_type == "cohort":
        score += 10
        components.append("Cohort Study (+10)")

    # Recency bonus (10 points max)
    if paper.year and paper.year >= 2022:
        score += 10
        components.append("Recent (2022+) (+10)")
    elif paper.year and paper.year >= 2020:
        score += 5
        components.append("Recent (2020+) (+5)")

    # Venue prestige (15 points max) - pattern matching
    if paper.venue:
        venue_lower = paper.venue.lower()
        if any(prestige in venue_lower for prestige in ["nature", "science", "nejm", "lancet"]):
            score += 15
            components.append("Top Venue (+15)")
        elif "journal" in venue_lower:
            score += 5
            components.append("Journal (+5)")

    # Full text availability (5 points)
    if paper.abstract:
        score += 5
        components.append("Abstract Available (+5)")

    score = min(score, 100)
    explanation = f"Basic scoring: {', '.join(components)}" if components else "Basic scoring applied"

    return score, explanation

def calculate_relevance_score(paper: Paper, keywords: List[str], gap_context: str) -> float:
    """Calculate how well paper addresses the specific gap."""
    # Keyword overlap in title/abstract
    # Gap context alignment
    # Search strategy fit
    # Return 0-100 score
```

## Configuration Integration (Maximum Reuse)

### Add to `src/config.py`
```python
# ============================================================================
# DISCOVERY TOOL CONFIGURATION (SEMANTIC SCHOLAR FOUNDATION)
# ============================================================================

# Discovery-specific settings (reuse everything else from enhanced scoring)
DISCOVERY_DEFAULT_SOURCE = 'semantic_scholar'  # Leverage existing infrastructure
DISCOVERY_DEFAULT_LIMIT = 50                   # Conservative default
DISCOVERY_MAX_KEYWORDS = 10                    # Prevent overly complex queries
DISCOVERY_DEFAULT_YEAR_FROM = 2020             # Recent research focus
DISCOVERY_DEFAULT_INCLUDE_KB = False           # Exclude KB papers by default

# UX Analytics Configuration (reuse cli.py logging infrastructure)
DISCOVERY_COMMAND_USAGE_LOG_ENABLED = True     # Enable usage pattern tracking
DISCOVERY_SESSION_TIMEOUT_MINUTES = 30         # Session boundary for analytics

# Coverage guidance text
COVERAGE_GUIDANCE = """
## When to Use Manual Database Access

**Semantic Scholar provides excellent comprehensive coverage (214M papers, 85% of digital health research).**

**Consider manual access for specialized needs:**

🔍 **PubMed** - When you need:
  • Clinical trial protocols and regulatory submissions
  • Medical Subject Heading (MeSH) precision
  • FDA/NIH regulatory evidence
  • Systematic review PRISMA compliance

🔍 **IEEE Xplore** - When you need:
  • Engineering implementation details
  • Technical standards and specifications
  • Conference proceedings in engineering/CS
  • Industry best practices and benchmarks

🔍 **arXiv** - When you need:
  • Latest AI/ML preprints (6-12 months ahead of journals)
  • Cutting-edge algorithm developments
  • Reproducible research with code availability
  • Early access to breakthrough methods

**Manual Access Links:**
• PubMed: https://pubmed.ncbi.nlm.nih.gov/
• IEEE: https://ieeexplore.ieee.org/
• arXiv: https://arxiv.org/search/

**Future Enhancement:** Specialized slash commands planned (/pubmed, /ieee, /arxiv)
"""

# Population focus mappings for enhanced search
POPULATION_FOCUS_TERMS = {
    'pediatric': ['children', 'pediatric', 'adolescent', 'youth', 'minors'],
    'elderly': ['elderly', 'geriatric', 'older adults', 'seniors', 'aging'],
    'women': ['women', 'female', 'maternal', 'pregnancy', 'reproductive'],
    'developing_countries': ['developing countries', 'low-income', 'global health', 'LMIC']
}

# Quality threshold mappings (reuse enhanced scoring thresholds)
QUALITY_THRESHOLD_MAPPING = {
    'HIGH': 80,      # CONFIDENCE_HIGH_THRESHOLD from enhanced scoring
    'MEDIUM': 60,    # CONFIDENCE_MEDIUM_THRESHOLD from enhanced scoring
    'LOW': 40        # CONFIDENCE_LOW_THRESHOLD from enhanced scoring
}

# Reuse ALL enhanced scoring configuration:
# - SEMANTIC_SCHOLAR_API_URL
# - SEMANTIC_SCHOLAR_RATE_LIMIT (1 RPS unauthenticated)
# - API_CACHE_EXPIRY_DAYS (7 days)
# - ENHANCED_QUALITY_* constants (citation impact, venue prestige, etc.)
# - All confidence thresholds and scoring weights

# Output alignment with gap analysis
DISCOVERY_OUTPUT_FORMAT = 'markdown'  # Match gap analysis exactly
DISCOVERY_EXPORT_PREFIX = 'discovery' # exports/discovery_YYYY_MM_DD.md

# Coverage documentation function
def show_coverage_info():
    """Display coverage guidance to users."""
    print(COVERAGE_GUIDANCE)
```

## CLI Surface Design Analysis

### Pros of Hybrid 11-Option Approach

**User Experience Benefits:**
- **Graduated complexity**: Core users get simple interface, power users get essential advanced options
- **80/20 principle**: Covers 80% of advanced use cases with minimal complexity increase
- **Manageable learning curve**: 11 options still learnable vs. 27 overwhelming options
- **Professional capability**: Addresses systematic review and clinical research needs

**Advanced Use Case Support:**
```bash
# Systematic review preparation
python src/discover.py --keywords "diabetes,AI" --quality-threshold HIGH --study-types "systematic_review,rct"

# Clinical population research
python src/discover.py --keywords "depression,therapy" --population-focus "adolescents" --author-filter "Smith J"

# High-impact author tracking
python src/discover.py --keywords "machine learning,healthcare" --author-filter "LeCun Y,Ng A" --quality-threshold HIGH
```

### Mitigation of Complexity

**Smart Defaults and Validation:**
```python
# Auto-application of intelligent defaults
def apply_smart_defaults(args):
    # If no quality threshold specified but high min-citations, auto-set HIGH
    if args.min_citations >= 50 and not args.quality_threshold:
        args.quality_threshold = 'HIGH'

    # If population focus specified, adjust study type preferences
    if args.population_focus == 'pediatric' and not args.study_types:
        args.study_types = ['rct', 'cohort', 'systematic_review']

    # Limit author filter to prevent query complexity
    if args.author_filter:
        authors = args.author_filter.split(',')[:5]  # Max 5 authors
        args.author_filter = ','.join(authors)
```

## External Integration

### Python API (Enhanced)
```python
# Direct Python usage with power features
from src.discover import discover_papers

# Basic usage
results = discover_papers(
    keywords=["diabetes", "mobile health"],
    year_from=2020,
    study_types=["rct"]
)

# Advanced usage
results = discover_papers(
    keywords=["AI", "diagnostics"],
    author_filter=["Smith J", "Garcia M"],
    quality_threshold="HIGH",
    population_focus="pediatric",
    year_from=2022,
    limit=30
)
```

### Command-Line Integration (Enhanced)
```bash
# Slash command integration with power features
/discover "machine learning healthcare" --quality-threshold HIGH

# Batch processing for different quality levels
for quality in HIGH MEDIUM; do
    python src/discover.py --keywords "telemedicine" --quality-threshold "$quality" --output-file "telemedicine_${quality,,}.md"
done

# Research workflow integration
python src/discover.py --keywords "digital therapeutics" --population-focus "elderly" --author-filter "$(cat high_impact_authors.txt)"
```

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_discover.py
def test_query_generation():
    """Test search query generation with various parameters."""

def test_paper_scoring():
    """Test quality and relevance scoring algorithms."""

def test_deduplication():
    """Test DOI-based paper deduplication."""

def test_rate_limiting():
    """Test token bucket rate limiting."""
```

### Integration Tests
```python
# tests/integration/test_discover_sources.py
def test_pubmed_search():
    """Test actual PubMed API integration."""

def test_semantic_scholar_search():
    """Test Semantic Scholar API integration."""

def test_multi_source_search():
    """Test parallel search across multiple sources."""
```

### Performance Tests
```python
# tests/performance/test_discover_performance.py
def test_search_performance():
    """Benchmark search performance with different query sizes."""

def test_concurrent_searches():
    """Test performance with multiple concurrent searches."""
```

## Expansion Roadmap

### Phase 2: Additional Sources (Months 2-3)
- **arXiv integration**: Add preprint search following same infrastructure patterns
- **Semantic Scholar integration**: Leverage existing enhanced scoring client
- **Multi-source deduplication**: DOI-based deduplication across sources

### Phase 3: Advanced Features (Months 4-6)
- **Semantic search**: Use existing KB embeddings for similarity matching
- **Citation network analysis**: Integrate with gap analysis citation data
- **Machine learning scoring**: User feedback integration for relevance improvement

### Phase 4: Intelligence Features (Months 7-9)
- **Cross-domain discovery**: Connect disparate research areas
- **Predictive discovery**: Identify emerging influential papers
- **Author network expansion**: Follow researcher collaboration patterns

## Implementation Benefits (Semantic Scholar Foundation)

### Development Efficiency
- **Realistic timeline**: 4-6 weeks development time (accounting for proper API integration)
- **Moderate new code**: ~600 lines new code (including bulk search, basic scoring, rate limiting)
- **60% infrastructure reuse**: Reuse existing API patterns from build_kb.py, adapt for search workflows
- **No deduplication complexity**: Single comprehensive source eliminates multi-source coordination
- **Shared analytics**: UX logging infrastructure already implemented and tested

### Superior Coverage
- **85% digital health coverage**: Semantic Scholar's 214M papers across all domains
- **Cross-domain by design**: Medical + engineering + CS + behavioral research
- **Real-time updates**: Latest research before traditional databases
- **Citation network analysis**: Built-in influence metrics and paper recommendations

### Quality Consistency
- **Consistent quality scoring**: Basic scoring using same patterns as build_kb.py
- **Same output format**: Familiar user experience across tools
- **Same API patterns**: Reuse proven request patterns from build_kb.py with proper rate limiting
- **Same confidence thresholds**: HIGH/MEDIUM/LOW scoring alignment

### User Flexibility
- **Comprehensive default**: Most users get complete coverage from one source
- **Manual specialization**: Advanced users access PubMed/IEEE/arXiv directly when needed
- **Future expansion**: Slash commands for specialized sources (/pubmed, /ieee, /arxiv)
- **Natural workflow**: Discovery → manual validation → DOI import to Zotero

### Clear Value Proposition
- **"What's out there?" capability**: External comprehensive search vs. "What am I missing?" gap analysis
- **Cross-domain discovery**: Bridges clinical, technical, and behavioral research
- **Infrastructure efficiency**: Maximum reuse of existing enhanced scoring investment
- **Professional credibility**: 214M papers provides authoritative comprehensive coverage

---

**This Semantic Scholar foundation delivers maximum discovery value with minimum development effort by leveraging existing infrastructure completely. Users get comprehensive cross-domain coverage with the flexibility to access specialized sources manually when needed.**
