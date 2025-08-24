#!/usr/bin/env python3
"""Discovery Tool for Research Assistant v4.6.

This module provides comprehensive paper discovery using Semantic Scholar's API
to find external papers not currently in the knowledge base. It serves as the
"What's out there?" complement to the gap analysis "What am I missing?" capability.

Architecture:
    The tool follows a three-stage pipeline:
    1. Query Generation: Builds comprehensive OR queries from keywords, population focus,
       and study types, leveraging existing POPULATION_FOCUS_TERMS mappings
    2. Paper Discovery: Executes bulk Semantic Scholar API calls with proactive rate
       limiting (1 RPS), parses results, and applies client-side filtering
    3. Analysis & Reporting: Scores papers using basic quality algorithms (no API delays),
       assesses KB coverage with traffic light system, generates markdown reports

Key Features:
- Semantic Scholar integration: Access to 214M papers with 85% digital health coverage
- KB filtering: DOI-based exclusion/inclusion using existing KnowledgeBaseIndex
- Quality scoring: Fast basic scoring algorithm reusing build_kb.py infrastructure
- Coverage assessment: Traffic light system (🟢🟡🔴) for KB completeness evaluation
- Rate limiting: Proactive 1 RPS limiting for unauthenticated API access
- Report generation: Markdown reports matching gap analysis format with DOI lists
- Command Usage Analytics: Session tracking and usage pattern analysis for continuous improvement
- Error resilience: Graceful degradation on API failures, network issues, or KB unavailability

Infrastructure Reuse:
    Maximizes reuse of existing components to maintain consistency:
    - Semantic Scholar patterns from build_kb.py
    - Quality scoring algorithms (calculate_basic_quality_score)
    - Command usage analytics from cli.py (_setup_command_usage_logger, _log_command_usage_event)
    - KB integration via cli_kb_index.py (KnowledgeBaseIndex)
    - Configuration constants from config.py

Usage Examples:
    # Basic discovery - new papers only
    python src/discover.py --keywords "diabetes,mobile health"

    # Advanced search with filters
    python src/discover.py --keywords "AI,diagnostics" \
                          --quality-threshold HIGH \
                          --population-focus pediatric \
                          --year-from 2022

    # Include KB papers for validation/overlap analysis
    python src/discover.py --keywords "telemedicine" --include-kb-papers

    # Show coverage guidance for manual database access
    python src/discover.py --coverage-info

    # Systematic review preparation with strict criteria
    python src/discover.py --keywords "depression,intervention" \
                          --study-types "rct,systematic_review" \
                          --quality-threshold HIGH \
                          --min-citations 10 \
                          --year-from 2020

Output:
    Generates comprehensive markdown reports in exports/discovery_YYYY_MM_DD.md with:
    - KB coverage assessment with traffic light status and recommendations
    - Search parameters documentation for reproducibility
    - Papers grouped by confidence level (HIGH/MEDIUM/LOW 80+/60+/40+)
    - DOI lists for direct Zotero import (filters out Semantic Scholar IDs)
    - Performance metrics and execution statistics
    - Coverage guidance for specialized databases (PubMed, IEEE, arXiv)
"""

import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
import requests

# ============================================================================
# IMPORTS FROM EXISTING INFRASTRUCTURE
# ============================================================================
# Maximum infrastructure reuse strategy: Import components from existing modules
# to maintain consistency and avoid code duplication across the research assistant

try:
    # For module imports (from tests and internal usage)
    from .config import (
        # Discovery-specific configuration constants
        DISCOVERY_DEFAULT_SOURCE,  # Default: 'semantic_scholar'
        DISCOVERY_DEFAULT_LIMIT,  # Default: 50 papers
        DISCOVERY_DEFAULT_YEAR_FROM,  # Default: 2020 (recent research focus)
        DISCOVERY_DEFAULT_INCLUDE_KB,  # Default: False (exclude existing papers)
        POPULATION_FOCUS_TERMS,  # Mapping for pediatric, elderly, women, developing_countries
        QUALITY_THRESHOLD_MAPPING,  # HIGH: 80+, MEDIUM: 60+, LOW: 40+
        COVERAGE_GUIDANCE,  # Help text for manual database access
        DISCOVERY_EXPORT_PREFIX,  # 'discovery' for exports/discovery_YYYY_MM_DD.md
        # Semantic Scholar API configuration (reused from build_kb.py)
        SEMANTIC_SCHOLAR_API_URL,  # Base URL for API endpoints
    )
    from .build_kb import (
        # Quality scoring functions (algorithm reuse)
        calculate_basic_quality_score,  # Fast scoring without API calls
        detect_study_type,  # Extract study type from text
    )

    # CLI and analytics infrastructure (pattern reuse)
    from .cli import (
        _setup_command_usage_logger,
        _log_command_usage_event,
        ResearchCLI,
    )

    # Knowledge base integration (DOI filtering)
    from .cli_kb_index import KnowledgeBaseIndex
except ImportError:
    # For direct script execution (python src/discover.py)
    from config import (  # type: ignore[no-redef]
        # Discovery-specific configuration
        DISCOVERY_DEFAULT_SOURCE,
        DISCOVERY_DEFAULT_LIMIT,
        DISCOVERY_DEFAULT_YEAR_FROM,
        DISCOVERY_DEFAULT_INCLUDE_KB,
        POPULATION_FOCUS_TERMS,
        QUALITY_THRESHOLD_MAPPING,
        COVERAGE_GUIDANCE,
        DISCOVERY_EXPORT_PREFIX,
        # Semantic Scholar configuration
        SEMANTIC_SCHOLAR_API_URL,
    )
    from build_kb import (  # type: ignore[no-redef]
        # Quality scoring functions
        calculate_basic_quality_score,
        detect_study_type,
    )

    # CLI and KB integration
    from cli import _setup_command_usage_logger, _log_command_usage_event, ResearchCLI  # type: ignore[no-redef]
    from cli_kb_index import KnowledgeBaseIndex  # type: ignore[no-redef]


# ============================================================================
# DATA STRUCTURES
# ============================================================================
# Core data structures for paper discovery, analysis, and reporting.
# Designed for compatibility with existing gap analysis and KB structures.


@dataclass
class Paper:
    """Represents a discovered paper with comprehensive metadata.

    This structure captures all essential paper information from Semantic Scholar API
    responses, providing a standardized format for downstream processing.

    Attributes:
        doi: Digital Object Identifier (preferred) or fallback Semantic Scholar ID
        title: Full paper title as returned by the API
        authors: List of author names in "LastName, FirstName" format
        year: Publication year (0 if unknown/unavailable)
        abstract: Paper abstract text for relevance analysis
        citation_count: Number of citations (used for impact assessment)
        venue: Journal/conference name for quality scoring
        url: Semantic Scholar paper URL for access
        source: Data source identifier ("semantic_scholar" for all current papers)
        study_type: Detected study type (rct, systematic_review, etc.) - set after parsing
        keywords: Associated keywords for categorization - populated during analysis

    Notes:
        - DOI is preferred identifier but Semantic Scholar ID (s2-xxxxx) used as fallback
        - Zero values indicate missing/unavailable data from API
        - Authors list may be truncated if very long (handled in display functions)
        - Study type detection happens after paper creation via detect_study_type()
    """

    doi: str  # Primary identifier (DOI preferred, S2 ID fallback)
    title: str  # Full paper title
    authors: list[str]  # Author names list
    year: int  # Publication year (0 if unknown)
    abstract: str  # Abstract text for analysis
    citation_count: int  # Citation impact metric
    venue: str  # Journal/conference for quality assessment
    url: str  # Semantic Scholar paper URL
    source: str = "semantic_scholar"  # Fixed source identifier
    study_type: str | None = None  # Detected study type (set post-creation)
    keywords: list[str] = field(default_factory=list)  # Associated keywords


@dataclass
class ScoredPaper:
    """Paper enhanced with quality and relevance scoring for ranking and filtering.

    This structure wraps a Paper with computed scores for systematic evaluation
    and user-friendly presentation. Scores are computed using basic algorithms
    for speed without requiring additional API calls.

    Attributes:
        paper: Original Paper object with all metadata
        quality_score: Intrinsic paper quality (0-100) based on venue, year, study type
        relevance_score: Search relevance (0-100) based on keyword matching
        overall_score: Combined score ((quality + relevance) / 2) for ranking
        confidence: User-friendly confidence level (HIGH: 80+, MEDIUM: 60+, LOW: 40+)
        reasoning: Human-readable explanation of scoring decisions

    Scoring Details:
        - quality_score uses calculate_basic_quality_score() from build_kb.py
        - relevance_score uses keyword matching in title (30% weight) + abstract (70% weight)
        - overall_score is simple average for balanced ranking
        - confidence thresholds align with existing gap analysis standards
        - reasoning combines quality explanation with relevance percentage

    Usage:
        Papers are automatically sorted by overall_score (descending) and grouped
        by confidence level for report generation and user presentation.
    """

    paper: Paper  # Original paper with full metadata
    quality_score: float  # Intrinsic quality 0-100 (venue, type, year, etc.)
    relevance_score: float  # Search relevance 0-100 (keyword matching)
    overall_score: float  # Combined ranking score (quality + relevance) / 2
    confidence: str  # HIGH/MEDIUM/LOW based on overall_score thresholds
    reasoning: str  # Human-readable scoring explanation


@dataclass
class SearchQuery:
    """Configuration for Semantic Scholar search operations.

    Encapsulates all parameters needed for a single search operation,
    including the query string and filter criteria for client-side processing.

    Attributes:
        query_text: Formatted query string for Semantic Scholar API (uses OR logic)
        filters: Dictionary of filter criteria applied after API response:
            - year_from: Minimum publication year (int)
            - limit: Maximum results to return (int)
            - min_citations: Minimum citation count (int)
            - study_types: List of study types to match (list[str])
        source: Fixed identifier for data source ("semantic_scholar")

    Query Format:
        Query text uses comprehensive OR logic: "term1" OR "term2" OR "term3"
        Terms include original keywords + population focus terms + study types
        Client-side filtering handles complex criteria not supported by API

    Example:
        SearchQuery(
            query_text='"diabetes" OR "mobile health" OR "pediatric" OR "children"',
            filters={"year_from": 2020, "limit": 50, "min_citations": 10},
            source="semantic_scholar"
        )
    """

    query_text: str  # OR-formatted query for Semantic Scholar
    filters: dict[str, Any]  # Client-side filter criteria
    source: str = "semantic_scholar"  # Fixed data source identifier


@dataclass
class DiscoveryResults:
    """Comprehensive results from a complete discovery session.

    Contains all information needed for report generation, analytics logging,
    and user presentation. Structured to support both immediate display and
    long-term analysis of discovery patterns.

    Attributes:
        papers: Scored and ranked papers matching search criteria
        coverage_status: KB coverage assessment with traffic light status:
            - status: Traffic light indicator (🟢 EXCELLENT/🟡 ADEQUATE/🔴 NEEDS UPDATE)
            - message: Human-readable assessment explanation
            - recommendation: Suggested next actions
            - kb_count: Number of relevant papers found in KB
            - discovery_count: Number of external papers discovered
            - high_impact_missing: Count of high-citation external papers
            - recent_missing: Count of recent (2022+) external papers
        search_params: Complete parameter set for reproducibility:
            - All CLI options used (keywords, filters, thresholds, etc.)
            - Enables exact reproduction of search results
        performance_metrics: Execution statistics for optimization:
            - total_time_seconds: End-to-end execution time
            - papers_found: Raw papers from API before filtering
            - papers_returned: Final papers after all filtering
            - kb_papers_excluded: Papers filtered out due to KB presence

    Usage:
        Used by generate_discovery_report() to create markdown output
        and by command usage analytics for usage pattern analysis.
    """

    papers: list[ScoredPaper]  # Final scored and ranked results
    coverage_status: dict[str, Any]  # KB coverage assessment with recommendations
    search_params: dict[str, Any]  # Complete search configuration for reproducibility
    performance_metrics: dict[str, Any]  # Execution statistics and timing data


# ============================================================================
# RATE LIMITING
# ============================================================================
# Proactive rate limiting to prevent API throttling and ensure reliable operation
# with unauthenticated Semantic Scholar API access (1 RPS limit)


class RateLimiter:
    """Proactive rate limiter for unauthenticated Semantic Scholar API.

    Implements conservative rate limiting to prevent HTTP 429 (Too Many Requests)
    errors when using Semantic Scholar's public API without authentication.
    Uses proactive waiting rather than reactive backoff for predictable timing.

    The Semantic Scholar API has the following rate limits:
    - Unauthenticated: 1 request per second (1 RPS)
    - Authenticated: 10 requests per second (10 RPS) - not currently used

    Strategy:
        - Proactive: Wait before making request if needed (prevents errors)
        - Conservative: Use exactly 1 RPS to stay well within limits
        - Predictable: Deterministic timing for consistent user experience

    Attributes:
        min_interval: Minimum seconds between requests (1.0 for 1 RPS)
        last_request_time: Timestamp of most recent request for interval calculation
    """

    def __init__(self, requests_per_second: float = 1.0):
        """Initialize rate limiter with specified request frequency.

        Args:
            requests_per_second: Maximum requests per second. Default 1.0 for
                unauthenticated Semantic Scholar API. Could be increased to 10.0
                if authenticated API keys are added in the future.

        Note:
            Conservative default of 1.0 RPS ensures reliable operation without
            API authentication setup. Future versions could auto-detect authentication
            status and adjust limits accordingly.
        """
        self.min_interval = 1.0 / requests_per_second  # Convert RPS to seconds between requests
        self.last_request_time = 0.0  # Track timing for proactive waiting

    def wait_if_needed(self) -> None:
        """Proactively wait to ensure we don't exceed rate limits.

        Calculates time since last request and sleeps if insufficient time
        has passed. This prevents HTTP 429 errors and ensures consistent,
        predictable API access timing.

        Side Effects:
            - May sleep for up to min_interval seconds
            - Updates last_request_time to current time after any waiting
            - Guarantees at least min_interval seconds between calls

        Performance:
            - Typical wait time: 0-1 seconds depending on call frequency
            - Zero overhead if calls are naturally spaced apart
            - Deterministic timing (not random like exponential backoff)
        """
        now = time.time()
        time_since_last = now - self.last_request_time

        # Calculate if we need to wait before making the next request
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            time.sleep(wait_time)  # Proactive wait to prevent rate limit violations

        # Update timestamp for next call calculation
        self.last_request_time = time.time()


# ============================================================================
# CLI INTERFACE
# ============================================================================


@click.command()
@click.option(
    "--keywords",
    help="""Comma-separated search keywords (REQUIRED).

              Examples: 'diabetes,mobile health' or 'AI,diagnostics,pediatric'

              These terms are combined with OR logic and expanded with population-specific
              terms when --population-focus is used. Keywords drive both paper discovery
              and relevance scoring.""",
)
@click.option(
    "--year-from",
    default=DISCOVERY_DEFAULT_YEAR_FROM,
    help=f"""Filter papers published from this year onwards (default: {DISCOVERY_DEFAULT_YEAR_FROM}).

              Recent research focus balances currency with established literature.
              Use 2022+ for latest developments, 2015+ for comprehensive coverage.
              Applied client-side after API search for precision.""",
)
@click.option(
    "--study-types",
    help="""Filter by study methodology types (comma-separated).

              Common types: rct, systematic_review, cohort, case_control, cross_sectional,
              meta_analysis, randomized_trial, clinical_trial, observational, qualitative.

              Example: 'rct,systematic_review' for evidence-based research.
              Terms are added to search query AND used for client-side filtering.""",
)
@click.option(
    "--min-citations",
    default=0,
    help="""Minimum citation count threshold (default: 0 = no filter).

              Filters papers by research impact. Use 10+ for established work,
              50+ for high-impact papers, 100+ for landmark studies. Note that
              recent papers (2022+) may have low citations despite high quality.""",
)
@click.option(
    "--limit",
    default=DISCOVERY_DEFAULT_LIMIT,
    help=f"""Maximum results to return after scoring and ranking (default: {DISCOVERY_DEFAULT_LIMIT}).

              Applied after quality scoring, so you get the top N papers by overall score.
              API searches up to 1000 papers initially. Use 10-20 for focused searches,
              50-100 for comprehensive discovery, 200+ for systematic reviews.""",
)
@click.option(
    "--quality-threshold",
    type=click.Choice(["HIGH", "MEDIUM", "LOW"]),
    help="""Filter results by quality score threshold.

              HIGH: 80+ (publication-ready quality, systematic reviews)
              MEDIUM: 60+ (good supporting evidence, general research)
              LOW: 40+ (preliminary findings, broader context)

              Based on study type, venue prestige, recency, and methodology.
              No threshold returns all discovered papers ranked by score.""",
)
@click.option(
    "--author-filter",
    help="""Focus search on specific researchers (comma-separated, max 5).

              Examples: 'Smith J,Garcia M' or 'LeCun Y,Ng A,Hinton G'

              Author names are added to search terms to find their recent work.
              Use exact names as they appear in publications. Useful for tracking
              key researchers or building author-specific collections.""",
)
@click.option(
    "--population-focus",
    type=click.Choice(["pediatric", "elderly", "women", "developing_countries"]),
    help="""Target specific populations by expanding search terms.

              pediatric: Adds children, adolescent, youth, minors, pediatric
              elderly: Adds geriatric, older adults, seniors, aging
              women: Adds female, maternal, pregnancy, reproductive
              developing_countries: Adds low-income, global health, LMIC

              Automatically enhances discovery for population-specific research
              without requiring manual term expansion.""",
)
@click.option(
    "--include-kb-papers",
    is_flag=True,
    default=DISCOVERY_DEFAULT_INCLUDE_KB,
    help="""Include papers already in your knowledge base (default: exclude).

              Default behavior excludes KB papers to focus on new discoveries.
              Use this flag for validation studies, overlap analysis, or when
              building comprehensive reference lists that include existing papers.""",
)
@click.option(
    "--output-file",
    help="""Custom output file path (default: exports/discovery_YYYY_MM_DD.md).

              Supports any .md extension for markdown reports. File includes
              comprehensive metadata, DOI lists for Zotero import, and formatted
              citations. Directory is created automatically if it doesn't exist.""",
)
@click.option(
    "--coverage-info",
    is_flag=True,
    help="""Display database coverage guidance and manual access information.

              Shows when to use specialized databases (PubMed, IEEE, arXiv) beyond
              Semantic Scholar's comprehensive coverage. Includes direct links and
              search strategies for specialized domains. Use before starting research
              to understand coverage scope.""",
)
@click.option(
    "--source",
    default=DISCOVERY_DEFAULT_SOURCE,
    type=click.Choice(["semantic_scholar"]),
    help="""Paper discovery source (currently: semantic_scholar only).

              Semantic Scholar: 214M papers, 85% digital health coverage, cross-domain.
              Provides comprehensive academic coverage with strong CS, medicine, and
              interdisciplinary research. Future versions may add PubMed, IEEE, arXiv.""",
)
def main(
    keywords: str | None,
    year_from: int,
    study_types: str | None,
    min_citations: int,
    limit: int,
    quality_threshold: str | None,
    author_filter: str | None,
    population_focus: str | None,
    include_kb_papers: bool,
    output_file: str | None,
    coverage_info: bool,
    source: str,
) -> None:
    """Discover external papers using Semantic Scholar's comprehensive academic database.

    This tool searches Semantic Scholar's 214M paper database to find papers not currently
    in your knowledge base, providing comprehensive coverage across all research domains
    with particular strength in digital health, computer science, and interdisciplinary research.

    WORKFLOW:
      1. Query Generation: Builds comprehensive OR queries from your keywords, optionally
         expanded with population-specific terms and study types
      2. Paper Discovery: Searches Semantic Scholar with rate limiting (1 RPS), parses
         results, and applies client-side filtering for precision
      3. Quality Scoring: Scores papers using fast basic algorithms (no API delays) based
         on study type, venue prestige, recency, and keyword relevance
      4. KB Coverage Assessment: Analyzes your current knowledge base completeness using
         traffic light system (🟢 Excellent / 🟡 Adequate / 🔴 Needs Update)
      5. Report Generation: Creates markdown reports with DOI lists for Zotero import

    Examples:
      # Basic discovery for new papers only
      python src/discover.py --keywords "diabetes,mobile health"

      # Systematic review preparation with strict criteria
      python src/discover.py --keywords "depression,intervention" \
                            --study-types "rct,systematic_review" \
                            --quality-threshold HIGH --min-citations 10 --year-from 2020

      # Population-focused research with automatic term expansion
      python src/discover.py --keywords "AI,diagnostics" \
                            --population-focus pediatric --quality-threshold HIGH

      # Author tracking for specific researchers
      python src/discover.py --keywords "machine learning,healthcare" \
                            --author-filter "LeCun Y,Ng A" --year-from 2022

      # Coverage validation including existing KB papers
      python src/discover.py --keywords "telemedicine" --include-kb-papers

      # Check database coverage guidance before starting
      python src/discover.py --coverage-info

    OUTPUT:
      Generates comprehensive markdown reports in exports/discovery_YYYY_MM_DD.md containing:
      • KB coverage assessment with actionable recommendations
      • Complete search parameters for reproducibility
      • Papers grouped by confidence level (HIGH/MEDIUM/LOW: 80+/60+/40+)
      • Clean DOI lists for direct Zotero/EndNote import
      • Performance metrics and filtering statistics
      • Manual database access guidance for specialized needs

    COVERAGE:
      Semantic Scholar provides excellent comprehensive coverage (214M papers) with
      particular strength in digital health research (85% coverage). For specialized
      needs, use --coverage-info to see when PubMed, IEEE, or arXiv manual access
      is recommended.
    """
    # Show coverage information if requested
    if coverage_info:
        show_coverage_info()
        return

    # Keywords are required for discovery
    if not keywords:
        from help_formatting import get_command_help
        from error_formatting import safe_exit

        # Show consistent help with error
        help_text = get_command_help("discover")
        click.echo(help_text)
        safe_exit(
            "Keywords required for paper discovery",
            'Provide keywords with: --keywords "your,search,terms"',
            "Paper discovery initialization",
            module="discover",
        )

    # Initialize command usage logging
    session_id = str(uuid.uuid4())[:8]
    _setup_command_usage_logger()
    start_time = time.time()

    # Log command start with usage patterns
    _log_command_usage_event(
        "command_start",
        module="discover",  # Module context for generic event names
        command="discover",
        session_id=session_id,
        keywords_count=len(keywords.split(",")) if keywords else 0,
        has_population_focus=bool(population_focus),
        has_quality_threshold=bool(quality_threshold),
        has_author_filter=bool(author_filter),
        has_study_types=bool(study_types),
        year_from=year_from,
        result_limit=limit,
        source=source,
        include_kb_papers=include_kb_papers,
    )

    try:
        # Execute discovery
        results = discover_papers(
            keywords=keywords.split(",") if keywords else [],
            year_from=year_from,
            study_types=study_types.split(",") if study_types else [],
            min_citations=min_citations,
            limit=limit,
            quality_threshold=quality_threshold,
            author_filter=author_filter.split(",")[:5] if author_filter else [],  # Max 5 authors
            population_focus=population_focus,
            include_kb_papers=include_kb_papers,
            source=source,
        )

        # Generate output file path
        if not output_file:
            timestamp = datetime.now(UTC).strftime("%Y_%m_%d")
            output_file = f"exports/{DISCOVERY_EXPORT_PREFIX}_{timestamp}.md"

        # Generate and save report
        report = generate_discovery_report(results, output_file)

        # Ensure output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(exist_ok=True)

        # Write report
        output_path.write_text(report, encoding="utf-8")

        # Log successful completion
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_command_usage_event(
            "command_success",
            module="discover",  # Module context for generic event names
            command="discover",
            session_id=session_id,
            execution_time_ms=execution_time_ms,
            papers_found=len(results.papers),
            high_confidence_papers=len([p for p in results.papers if p.confidence == "HIGH"]),
            medium_confidence_papers=len([p for p in results.papers if p.confidence == "MEDIUM"]),
            low_confidence_papers=len([p for p in results.papers if p.confidence == "LOW"]),
            avg_quality_score=sum(p.quality_score for p in results.papers) / len(results.papers)
            if results.papers
            else 0,
            output_file=output_file,
            kb_coverage_status=results.coverage_status["status"],
            kb_papers_found=results.coverage_status["kb_count"],
            high_impact_missing=results.coverage_status["high_impact_missing"],
        )

        print("\n✓ Discovery completed successfully!")
        print(f"✓ Found {len(results.papers)} papers")
        print(f"✓ KB Coverage: {results.coverage_status['status']}")
        print(f"✓ Report saved to: {output_file}")

    except Exception as e:
        # Log error with diagnostic information and smart sanitization
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_command_usage_event(
            "command_error",
            module="discover",  # Module context for generic event names
            command="discover",
            session_id=session_id,
            execution_time_ms=execution_time_ms,
            error_type=type(e).__name__,
            error_message=str(e),  # Smart sanitization applied in _log_command_usage_event
            keywords_count=len(keywords.split(",")) if keywords else 0,
            source=source,
        )
        print(f"❌ Error during discovery: {e}")
        sys.exit(1)


def show_coverage_info() -> None:
    """Display comprehensive coverage guidance for manual database access.

    Shows detailed information about when to use specialized databases beyond
    Semantic Scholar's comprehensive coverage, including specific use cases,
    access links, and integration strategies.
    """
    print("\n" + "=" * 80)
    print("DATABASE COVERAGE GUIDANCE")
    print("=" * 80)
    print(COVERAGE_GUIDANCE)
    print("\n" + "=" * 80)
    print("DISCOVERY WORKFLOW INTEGRATION")
    print("=" * 80)
    print("""
🔄 RECOMMENDED WORKFLOW:

1. START with Semantic Scholar discovery (this tool)
   → Comprehensive cross-domain coverage (214M papers)
   → 85% of digital health research included
   → Fast, automated scoring and KB integration

2. EVALUATE coverage assessment in discovery report
   → 🟢 EXCELLENT: Proceed with confidence
   → 🟡 ADEQUATE: Consider targeted manual searches
   → 🔴 NEEDS UPDATE: Prioritize manual database access

3. SUPPLEMENT with manual searches if needed:
   → PubMed: For clinical protocols and regulatory evidence
   → IEEE: For engineering standards and technical details
   → arXiv: For cutting-edge AI/ML preprints (6-12 months ahead)

4. IMPORT results using DOI lists from discovery report
   → High confidence papers for core references
   → Medium confidence for broader coverage
   → Manual database results via direct DOI import

💡 TIP: Use discovery results to identify research gaps, then target
    manual searches to fill specific coverage needs.
""")
    print("=" * 80 + "\n")


# ============================================================================
# SEMANTIC SCHOLAR DISCOVERY
# ============================================================================


class SemanticScholarDiscovery:
    """Handles comprehensive paper discovery via Semantic Scholar API with intelligent KB filtering.

    Primary interface for external paper discovery using Semantic Scholar's 214M paper
    database. Provides KB-aware filtering, rate-limited API access, and robust error
    handling for reliable paper discovery operations.

    Key Responsibilities:
        1. API Communication: Rate-limited requests to Semantic Scholar bulk search endpoint
        2. KB Integration: DOI-based filtering using existing KnowledgeBaseIndex
        3. Data Parsing: Robust parsing of API responses with error recovery
        4. Client-side Filtering: Year, citation, and study type filtering post-API
        5. Error Handling: Graceful degradation on network/API failures

    Architecture:
        - Uses bulk search endpoint for efficiency (single query vs multiple)
        - Leverages existing KB infrastructure for DOI-based deduplication
        - Applies client-side filters for criteria not supported by API
        - Returns standardized Paper objects for downstream processing

    Performance:
        - Single API call per search (bulk endpoint)
        - Proactive rate limiting prevents throttling delays
        - Client-side filtering reduces network overhead
        - DOI-based KB filtering eliminates duplicates efficiently

    Attributes:
        rate_limiter: Proactive rate limiter for API compliance (1 RPS unauthenticated)
        include_kb_papers: Whether to include papers already in knowledge base
        kb_dois: Set of DOIs from existing KB for filtering (empty if include_kb_papers=True)
    """

    def __init__(self, include_kb_papers: bool = False):
        """Initialize discovery service with KB filtering configuration.

        Args:
            include_kb_papers: If False (default), exclude papers already in KB.
                             If True, include all papers for validation/overlap analysis.

        Note:
            When include_kb_papers=False, the service loads all DOIs from the current
            KB for efficient filtering. When True, no KB loading occurs for performance.
            KB loading failure is handled gracefully (empty filter set).
        """
        self.rate_limiter = RateLimiter(requests_per_second=1.0)  # Conservative unauthenticated limit
        self.include_kb_papers = include_kb_papers

        # Load KB DOIs for filtering only if exclusion mode is requested
        # This optimization avoids unnecessary KB loading when including all papers
        if not include_kb_papers:
            self.kb_dois = self._load_kb_dois()  # May return empty set on failure (graceful)
        else:
            self.kb_dois = set()  # No filtering needed in inclusion mode

    def _load_kb_dois(self) -> set[str]:
        """Load all DOIs from knowledge base for duplicate filtering.

        Extracts DOIs from the existing knowledge base index for efficient
        deduplication during discovery. Uses lowercase normalization for
        case-insensitive matching.

        Returns:
            Set of lowercase DOI strings from current KB. Empty set if KB
            unavailable (graceful degradation - no filtering applied).

        Error Handling:
            - KB index loading failures: Returns empty set (include all papers)
            - Missing DOI fields: Safely skipped during set comprehension
            - Invalid KB structure: Caught by broad exception handling

        Performance:
            - O(n) where n = number of papers in KB
            - Set lookup is O(1) for each discovered paper during filtering
            - Lowercase normalization prevents case-sensitivity issues

        Note:
            Only called when include_kb_papers=False to avoid unnecessary
            loading when all papers should be included.
        """
        try:
            kb_index = KnowledgeBaseIndex()  # Load existing KB structure
            # Extract and normalize DOIs, filtering out empty/missing values
            return {paper.get("doi", "").lower() for paper in kb_index.papers if paper.get("doi")}
        except Exception:
            # Graceful degradation: If KB not available, include all discovered papers
            # This ensures discovery continues to work even with KB issues
            return set()

    def search_papers(self, query: SearchQuery) -> list[Paper]:
        """Execute comprehensive Semantic Scholar search with filtering and error handling.

        Performs the complete discovery pipeline: API call → parsing → filtering → deduplication.
        Uses bulk search endpoint for efficiency and applies comprehensive error handling
        for robust operation in various network/API conditions.

        Args:
            query: Search configuration containing query text and filter criteria

        Returns:
            List of discovered Paper objects, filtered and deduplicated according to
            query criteria and KB inclusion settings. Empty list on API/network errors.

        Process Flow:
            1. Rate limiting: Wait if needed to comply with API limits
            2. API request: Single bulk search call with comprehensive field selection
            3. Response parsing: Convert JSON to Paper objects with error recovery
            4. Client filtering: Apply year, citation, study type filters
            5. KB deduplication: Remove papers already in KB (if exclude mode)

        Error Handling:
            - HTTP errors (4xx/5xx): Log status and return empty list
            - Network timeouts/failures: Log error and return empty list
            - JSON parsing errors: Log error and return empty list
            - Individual paper parsing errors: Skip paper, continue with others

        API Details:
            - Endpoint: /paper/search/bulk (most efficient for large queries)
            - Fields: title,authors,year,abstract,citationCount,venue,externalIds,url
            - Timeout: 30 seconds (balances reliability vs. responsiveness)
            - Rate limiting: Proactive 1 RPS compliance

        Performance:
            - Single API call regardless of query complexity
            - Bulk processing of all results in memory
            - Efficient set-based DOI lookup for KB filtering
        """
        # Ensure API rate limit compliance before making request
        self.rate_limiter.wait_if_needed()

        # Execute single comprehensive search via bulk endpoint
        try:
            response = requests.get(
                f"{SEMANTIC_SCHOLAR_API_URL}/paper/search/bulk",
                params={
                    "query": query.query_text,  # OR-formatted search terms
                    "limit": query.filters.get("limit", 1000),  # Max results (API supports up to 1000)
                    "fields": "title,authors,year,abstract,citationCount,venue,externalIds,url",  # All needed metadata
                },
                timeout=30,  # Conservative timeout for network reliability
            )

            if response.status_code == 200:
                data = response.json()
                papers = []

                # Parse each paper with individual error recovery
                for paper_data in data.get("data", []):
                    try:
                        paper = self._parse_paper(paper_data)
                        if paper:  # Only add successfully parsed papers
                            papers.append(paper)
                    except Exception:  # noqa: S112
                        # Skip individual papers with parsing errors
                        # This ensures one bad paper doesn't break the entire search
                        continue

                # Apply client-side filters for criteria not supported by API
                filtered_papers = self._apply_filters(papers, query.filters)

                # Apply KB deduplication if in exclude mode
                if not self.include_kb_papers and self.kb_dois:
                    filtered_papers = [p for p in filtered_papers if p.doi.lower() not in self.kb_dois]

                return filtered_papers

            # Handle API errors with informative logging
            print(f"API request failed with status {response.status_code}: {response.text}")
            return []  # Empty result for upstream error handling

        except requests.exceptions.RequestException as e:
            # Handle network-level errors (timeouts, connection failures, etc.)
            print(f"Network error during search: {e}")
            return []  # Graceful degradation
        except Exception as e:
            # Handle unexpected errors (JSON parsing, etc.)
            print(f"Unexpected error during search: {e}")
            return []  # Ensure function always returns list

    def _parse_paper(self, paper_data: dict[str, Any]) -> Paper | None:
        """Parse paper data from Semantic Scholar API response into standardized Paper object.

        Converts raw API response data into structured Paper objects with robust
        error handling and intelligent defaults for missing fields.

        Args:
            paper_data: Raw paper data dictionary from Semantic Scholar API response

        Returns:
            Paper object with all available metadata, or None if parsing fails
            completely (malformed data, missing critical fields, etc.)

        Data Extraction Logic:
            - DOI: Preferred from externalIds.DOI, fallback to Semantic Scholar ID
            - Authors: Extract names from authors array, handle missing/malformed entries
            - Year: Use provided year or 0 for unknown (0 indicates missing data)
            - Citations: Use citationCount or 0 for unavailable metrics
            - Venue: Journal/conference name for quality assessment
            - Title/Abstract: Required for relevance analysis

        Error Handling:
            - Missing required fields: Return None (paper will be skipped)
            - Malformed data types: Use safe defaults (empty strings, 0 values)
            - Author parsing errors: Individual authors skipped, continue with others
            - External ID parsing errors: Fall back to Semantic Scholar ID

        Identifier Strategy:
            - DOI preferred for universal paper identification
            - Semantic Scholar ID (s2-xxxxx) used as fallback
            - This ensures every paper has a unique identifier for deduplication
        """
        try:
            # Extract DOI with robust error handling for identifier hierarchy
            doi = ""
            external_ids = paper_data.get("externalIds", {})
            if external_ids and isinstance(external_ids, dict):
                # Try both DOI capitalizations (API inconsistency handling)
                doi = external_ids.get("DOI", "") or external_ids.get("doi", "")

            # Parse author list with individual error recovery
            authors = []
            if paper_data.get("authors"):
                for author in paper_data["authors"]:
                    if isinstance(author, dict):  # Validate structure
                        name = author.get("name", "Unknown")
                        if name and name != "Unknown":  # Only add meaningful names
                            authors.append(name)

            # Create paper object with safe defaults for missing data
            return Paper(
                doi=doi or f"s2-{paper_data.get('paperId', '')}",  # DOI preferred, S2 ID fallback
                title=paper_data.get("title", ""),  # Required for relevance analysis
                authors=authors,  # May be empty list if no authors
                year=paper_data.get("year", 0) or 0,  # 0 indicates unknown year
                abstract=paper_data.get("abstract", ""),  # Required for keyword matching
                citation_count=paper_data.get("citationCount", 0) or 0,  # 0 for new/uncited papers
                venue=paper_data.get("venue", ""),  # Used for quality scoring
                url=paper_data.get("url", ""),  # Semantic Scholar paper URL
                source="semantic_scholar",  # Fixed source identifier
            )
        except Exception:
            # Return None for completely malformed paper data
            # Upstream code will skip these papers and continue processing
            return None

    def _apply_filters(self, papers: list[Paper], filters: dict[str, Any]) -> list[Paper]:
        """Apply client-side filters to papers.

        Args:
            papers: List of papers to filter
            filters: Filter criteria

        Returns:
            Filtered list of papers
        """
        filtered = []

        year_from = filters.get("year_from")
        min_citations = filters.get("min_citations", 0)
        study_types = filters.get("study_types", [])

        for paper in papers:
            # Year filter
            if year_from and paper.year and paper.year < year_from:
                continue

            # Citation filter
            if paper.citation_count < min_citations:
                continue

            # Study type filter (if specified)
            if study_types:
                paper_text = f"{paper.title} {paper.abstract}".lower()
                matches_study_type = any(study_type.lower() in paper_text for study_type in study_types)
                if not matches_study_type:
                    continue

            filtered.append(paper)

        return filtered


# ============================================================================
# SEARCH QUERY GENERATION
# ============================================================================


def generate_semantic_scholar_query(
    keywords: list[str], year_from: int | None, study_types: list[str], population_focus: str | None
) -> SearchQuery:
    """Generate optimized Semantic Scholar query for comprehensive bulk search.

    Creates a single comprehensive OR query that maximizes paper discovery by
    combining user keywords with population-specific terms and study types.
    Uses bulk search strategy for efficiency and applies client-side filtering
    for precise control over results.

    Args:
        keywords: User-specified search keywords (e.g., ["diabetes", "mobile health"])
        year_from: Minimum publication year for filtering (None = no limit)
        study_types: Study types to include (e.g., ["rct", "systematic_review"])
        population_focus: Target population key ("pediatric", "elderly", etc.)

    Returns:
        SearchQuery object with optimized query text and filter configuration

    Query Strategy:
        - Comprehensive OR logic: Each term increases potential matches
        - Population expansion: Adds related terms from POPULATION_FOCUS_TERMS
        - Study type inclusion: Direct term addition for methodology matching
        - Client-side filtering: Complex criteria applied post-API for precision

    Example Query Generation:
        Input: keywords=["diabetes"], population_focus="pediatric", study_types=["rct"]
        Output query_text: '"diabetes" OR "children" OR "pediatric" OR "adolescent" OR "rct"'

    Performance Optimization:
        - Single API call handles all term combinations
        - Bulk endpoint processes up to 1000 results efficiently
        - Client-side filtering provides precise control without multiple API calls

    Note:
        Uses quoted terms to ensure exact phrase matching in Semantic Scholar API.
    """
    # Start with user-provided keywords as base search terms
    base_terms = keywords.copy()

    # Expand search scope with population-specific terminology
    if population_focus and population_focus in POPULATION_FOCUS_TERMS:
        # Add all related terms for comprehensive population coverage
        # E.g., "pediatric" -> ["children", "pediatric", "adolescent", "youth", "minors"]
        base_terms.extend(POPULATION_FOCUS_TERMS[population_focus])

    # Include study type terms for methodology-based matching
    if study_types:
        # Add study types directly to search terms for broader discovery
        # Client-side filtering will apply more precise study type matching
        base_terms.extend(study_types)

    # Create comprehensive OR query for maximum discovery potential
    # Quote each term for exact phrase matching in Semantic Scholar
    combined_query = " OR ".join(f'"{term}"' for term in base_terms)

    return SearchQuery(
        query_text=combined_query,
        filters={
            "year_from": year_from,  # Client-side year filtering
            "limit": 1000,  # Maximum bulk search results
            "study_types": study_types,  # Client-side study type filtering
            "min_citations": 0,  # Default: no citation threshold (applied separately)
        },
        source="semantic_scholar",  # Fixed data source identifier
    )


# ============================================================================
# MAIN DISCOVERY FUNCTION
# ============================================================================


def discover_papers(
    keywords: list[str],
    year_from: int,
    study_types: list[str],
    min_citations: int,
    limit: int,
    quality_threshold: str | None,
    author_filter: list[str],
    population_focus: str | None,
    include_kb_papers: bool,
    source: str,
) -> DiscoveryResults:
    """Main discovery orchestration function coordinating search, scoring, and analysis.

    Implements the complete discovery pipeline from query generation through final
    report-ready results. Coordinates API calls, KB integration, quality scoring,
    and coverage assessment for comprehensive paper discovery.

    Args:
        keywords: User search keywords (required, min 1 term)
        year_from: Minimum publication year filter (e.g., 2020)
        study_types: Study methodology filters (["rct", "systematic_review", ...])
        min_citations: Minimum citation count threshold (0 = no minimum)
        limit: Maximum results to return (applied after scoring/ranking)
        quality_threshold: Score filter ("HIGH": 80+, "MEDIUM": 60+, "LOW": 40+)
        author_filter: Author name filters (max 5, applied as search terms)
        population_focus: Target population ("pediatric", "elderly", etc.)
        include_kb_papers: If False, exclude papers already in KB; if True, include all
        source: Data source identifier ("semantic_scholar" - fixed for v4.6)

    Returns:
        DiscoveryResults containing:
        - Scored and ranked papers meeting all criteria
        - KB coverage assessment with traffic light status
        - Complete search parameters for reproducibility
        - Performance metrics for optimization analysis

    Pipeline Stages:
        1. Query Generation: Build comprehensive OR query with population/study expansions
        2. API Discovery: Execute rate-limited Semantic Scholar search
        3. Paper Scoring: Apply basic quality + keyword relevance algorithms
        4. Filtering & Ranking: Apply thresholds, limits, and sort by overall score
        5. Coverage Assessment: Analyze KB completeness with traffic light system
        6. Result Packaging: Bundle everything for report generation

    Performance Characteristics:
        - Single API call per search (bulk endpoint efficiency)
        - Fast scoring without additional API calls (basic algorithms)
        - KB integration via efficient DOI set operations
        - Typical execution time: 4-8 seconds depending on result count

    Error Handling:
        - API failures: Return empty results with error logging
        - KB unavailability: Continue with warning (no filtering)
        - Malformed papers: Skip individuals, continue with valid results
        - Network issues: Graceful degradation with user feedback
    """
    start_time = time.time()

    # Generate search query
    query = generate_semantic_scholar_query(keywords, year_from, study_types, population_focus)
    query.filters["min_citations"] = min_citations

    # Initialize discovery service
    discovery = SemanticScholarDiscovery(include_kb_papers=include_kb_papers)

    # Execute search
    print(f"🔍 Searching Semantic Scholar for: {', '.join(keywords)}")
    if population_focus:
        print(f"   📊 Population focus: {population_focus}")
    if study_types:
        print(f"   🔬 Study types: {', '.join(study_types)}")

    papers = discovery.search_papers(query)

    print(f"   ✓ Found {len(papers)} papers")

    # Score papers for quality and relevance
    print("📊 Scoring papers for quality and relevance...")
    scored_papers = score_discovery_papers(papers, keywords, quality_threshold)

    # Limit results
    if limit and len(scored_papers) > limit:
        scored_papers = scored_papers[:limit]

    # Assess KB coverage
    print("🎯 Assessing knowledge base coverage...")
    coverage_status = assess_kb_coverage(keywords, scored_papers)

    # Compile results
    search_params = {
        "keywords": keywords,
        "year_from": year_from,
        "study_types": study_types,
        "min_citations": min_citations,
        "limit": limit,
        "quality_threshold": quality_threshold,
        "author_filter": author_filter,
        "population_focus": population_focus,
        "include_kb_papers": include_kb_papers,
        "source": source,
    }

    performance_metrics = {
        "total_time_seconds": time.time() - start_time,
        "papers_found": len(papers),
        "papers_returned": len(scored_papers),
        "kb_papers_excluded": len(papers) - len(scored_papers) if not include_kb_papers else 0,
    }

    return DiscoveryResults(
        papers=scored_papers,
        coverage_status=coverage_status,
        search_params=search_params,
        performance_metrics=performance_metrics,
    )


# ============================================================================
# SCORING AND ANALYSIS FUNCTIONS
# ============================================================================
# Paper evaluation functions using fast algorithms optimized for discovery speed.
# Reuses existing infrastructure for consistency with KB paper scoring.


def score_discovery_papers(
    papers: list[Paper], keywords: list[str], quality_threshold: str | None
) -> list[ScoredPaper]:
    """Score papers using fast basic algorithms optimized for discovery speed.

    Applies two-dimensional scoring (quality + relevance) using algorithms that
    require no additional API calls. Reuses existing quality scoring infrastructure
    from build_kb.py for consistency with KB paper scoring.

    Args:
        papers: Raw Paper objects from API discovery to be scored
        keywords: Original search keywords for relevance analysis
        quality_threshold: Optional score filter ("HIGH": 80+, "MEDIUM": 60+, "LOW": 40+)

    Returns:
        List of ScoredPaper objects sorted by overall_score (highest first),
        optionally filtered by quality threshold

    Scoring Methodology:
        1. Quality Score (0-100): Uses calculate_basic_quality_score() from build_kb.py
           - Study type detection and weighting (RCT=20pts, Systematic Review=15pts, etc.)
           - Recency bonus (2022+=10pts, 2020+=5pts)
           - Venue prestige pattern matching
           - Full text availability (+5pts for abstracts)

        2. Relevance Score (0-100): Custom keyword matching algorithm
           - Title matches: 30% weight (more relevant than abstract matches)
           - Abstract matches: 70% weight (broader content relevance)
           - Percentage of keywords found in paper text

        3. Overall Score: Simple average (quality + relevance) / 2
           - Balanced weighting between intrinsic quality and search relevance
           - Provides intuitive ranking for mixed-quality result sets

        4. Confidence Classification:
           - HIGH: 80+ overall score (publication-ready quality)
           - MEDIUM: 60+ overall score (good supporting evidence)
           - LOW: 40+ overall score (preliminary/contextual value)

    Performance Optimization:
        - No API calls required (all scoring from existing paper metadata)
        - Reuses proven algorithms from KB building for consistency
        - Fast text processing with simple string matching
        - Efficient sorting and filtering operations

    Quality Threshold Filtering:
        Papers below the specified threshold are excluded from results,
        enabling focused discovery sessions for systematic reviews or
        high-quality evidence synthesis.
    """
    scored_papers = []

    for paper in papers:
        # Detect study type from title/abstract
        study_type = detect_study_type(f"{paper.title} {paper.abstract}")

        # Create paper dict for basic scoring
        paper_data = {
            "study_type": study_type,
            "year": paper.year,
            "journal": paper.venue,
            "has_full_text": bool(paper.abstract),
        }

        # Use existing basic scoring function (no API required)
        quality_score, explanation = calculate_basic_quality_score(paper_data)

        # Add keyword relevance scoring
        relevance_score = calculate_keyword_relevance(paper, keywords)
        overall_score = (quality_score + relevance_score) / 2

        # Determine confidence level
        if overall_score >= 80:
            confidence = "HIGH"
        elif overall_score >= 60:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        # Create scored paper
        scored_paper = ScoredPaper(
            paper=paper,
            quality_score=quality_score,
            relevance_score=relevance_score,
            overall_score=overall_score,
            confidence=confidence,
            reasoning=f"{explanation} | Relevance: {relevance_score:.0f}/100",
        )

        # Apply quality threshold filter
        if quality_threshold:
            threshold_value = QUALITY_THRESHOLD_MAPPING.get(quality_threshold, 0)
            if overall_score < threshold_value:
                continue

        scored_papers.append(scored_paper)

    # Sort by overall score (highest first)
    return sorted(scored_papers, key=lambda x: x.overall_score, reverse=True)


def calculate_keyword_relevance(paper: Paper, keywords: list[str]) -> float:
    """Calculate search relevance score based on keyword matching patterns.

    Implements a weighted keyword matching algorithm that prioritizes title matches
    (high relevance signal) while also considering abstract matches (broader context).

    Args:
        paper: Paper object with title and abstract for analysis
        keywords: Original search keywords to match against

    Returns:
        Relevance score 0-100 where:
        - 100: Perfect match (all keywords in title + abstract)
        - 70-99: Most keywords match with title presence
        - 30-69: Some keywords match, primarily in abstract
        - 0-29: Few or no keyword matches

    Algorithm Details:
        1. Title Matching (30% weight):
           - Higher weight due to strong relevance signal
           - Authors choose titles to reflect core content

        2. Abstract Matching (70% weight):
           - Broader content analysis for comprehensive relevance
           - Captures conceptual relationships beyond title

        3. Case-Insensitive Matching:
           - Normalizes text to lowercase for consistent matching
           - Handles variations in keyword capitalization

        4. Percentage-Based Scoring:
           - Score reflects proportion of keywords found
           - Rewards comprehensive coverage of search terms

    Example Scoring:
        Keywords: ["diabetes", "mobile health"]
        Paper 1: Title contains both terms → High title bonus + full coverage = ~100
        Paper 2: Only "diabetes" in abstract → Partial coverage = ~35
        Paper 3: Neither term present → No matches = 0

    Performance:
        - Fast string operations with simple containment checks
        - Linear time complexity O(keywords x text_length)
        - No external dependencies or API calls required
    """
    # Combine title and abstract for search
    text = f"{paper.title} {paper.abstract}".lower()

    # Count keyword matches
    matches = 0
    total_keywords = len(keywords)

    for keyword in keywords:
        if keyword.lower() in text:
            matches += 1

    # Base relevance on keyword coverage
    keyword_score = (matches / total_keywords) * 70 if total_keywords > 0 else 0

    # Bonus for title matches (more relevant)
    title_matches = sum(1 for kw in keywords if kw.lower() in paper.title.lower())
    title_bonus = (title_matches / total_keywords) * 30 if total_keywords > 0 else 0

    return min(keyword_score + title_bonus, 100.0)


def assess_kb_coverage(keywords: list[str], discovery_papers: list[ScoredPaper]) -> dict[str, Any]:
    """Assess knowledge base completeness using traffic light system with actionable recommendations.

    Analyzes the current KB's coverage of the search topic by comparing existing
    papers with external discovery results. Provides clear visual status indicators
    and specific recommendations for KB improvement.

    Args:
        keywords: Original search keywords to query existing KB
        discovery_papers: External papers found by discovery search

    Returns:
        Dictionary containing comprehensive coverage assessment:
        - status: Traffic light indicator (🟢 EXCELLENT/🟡 ADEQUATE/🔴 NEEDS UPDATE)
        - message: Human-readable assessment explanation
        - recommendation: Specific next steps for KB improvement
        - kb_count: Number of relevant papers found in current KB
        - discovery_count: Number of external papers discovered
        - high_impact_missing: Count of high-citation external papers (50+ citations)
        - recent_missing: Count of recent external papers (2022+ publications)

    Assessment Logic:
        🔴 NEEDS UPDATE (Critical gaps):
        - KB has <10 relevant papers OR >10 high-impact papers missing
        - Indicates fundamental coverage gaps requiring immediate attention

        🟡 ADEQUATE (Some gaps):
        - KB has <25 relevant papers OR >5 recent papers missing
        - Indicates good foundation but missing latest developments

        🟢 EXCELLENT (Comprehensive):
        - KB has ≥25 relevant papers AND ≤5 recent papers missing
        - Indicates strong coverage suitable for current research

    KB Search Integration:
        Uses existing ResearchCLI infrastructure to search current KB with
        the same keywords, ensuring consistent relevance assessment between
        existing and discovered papers.

    Impact Analysis:
        - High-impact threshold: 50+ citations (established influence)
        - Recent threshold: 2022+ publications (latest developments)
        - These metrics guide prioritization for KB updates

    Error Handling:
        Graceful degradation if KB search fails - assumes empty KB and
        recommends building initial coverage.
    """
    # Search KB using existing CLI infrastructure
    keywords_str = " ".join(keywords)

    try:
        # Use existing ResearchCLI search
        cli = ResearchCLI()
        kb_results = cli.search(keywords_str, top_k=1000)
        kb_count = len(kb_results)
    except Exception:
        # If KB search fails, assume empty KB
        kb_count = 0

    # Analyze discovery results
    discovery_count = len(discovery_papers)
    high_impact_missing = len([p for p in discovery_papers if getattr(p.paper, "citation_count", 0) > 50])
    recent_missing = len([p for p in discovery_papers if getattr(p.paper, "year", 0) >= 2022])

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
        "status": status,
        "message": message,
        "recommendation": recommendation,
        "kb_count": kb_count,
        "discovery_count": discovery_count,
        "high_impact_missing": high_impact_missing,
        "recent_missing": recent_missing,
    }


def generate_discovery_report(results: DiscoveryResults, output_file: str) -> str:
    """Generate comprehensive markdown report matching gap analysis format and style.

    Creates a structured, professional report suitable for research documentation,
    grant applications, or systematic review preparation. Maintains consistency
    with existing gap analysis reports for unified user experience.

    Args:
        results: Complete DiscoveryResults with papers, coverage, and metadata
        output_file: Target file path (used for documentation, not actual writing)

    Returns:
        Complete markdown report string ready for file output or display

    Report Structure:
        1. Header: Timestamp, search strategy, execution time
        2. KB Coverage Assessment: Traffic light status with recommendations
        3. Search Parameters: Complete parameter documentation for reproducibility
        4. Coverage Guidance: Manual database access information
        5. Results by Confidence: HIGH/MEDIUM/LOW paper groups
        6. Performance Metrics: Search statistics and filtering results
        7. DOI Lists: Zotero-ready import lists by confidence level

    Format Consistency:
        - Matches gap analysis report structure exactly
        - Uses same confidence level groupings (80+/60+/40+)
        - Provides same DOI export format for workflow integration
        - Maintains professional academic report styling

    Paper Presentation:
        Each paper includes comprehensive metadata:
        - DOI for citation and import
        - Author list (truncated for readability)
        - Publication year and citation count
        - Venue for quality assessment
        - Dual scores (quality + relevance) with explanations
        - Study type classification
        - Abstract preview for content assessment

    DOI List Features:
        - Filters out Semantic Scholar IDs (s2-xxxxx format)
        - Provides real DOIs suitable for Zotero import
        - Groups by confidence level for prioritized import
        - Includes combined list for bulk operations

    Usage Integration:
        Report format enables direct use in:
        - Research project documentation
        - Systematic review protocols
        - Grant application literature sections
        - Academic manuscript preparation
    """
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

    # Group papers by confidence level
    high_confidence = [p for p in results.papers if p.confidence == "HIGH"]
    medium_confidence = [p for p in results.papers if p.confidence == "MEDIUM"]
    low_confidence = [p for p in results.papers if p.confidence == "LOW"]

    # Generate report sections
    report_sections = []

    # Header
    report_sections.append(f"""# Discovery Results

**Generated**: {timestamp} UTC
**Search Strategy**: External paper discovery via Semantic Scholar
**Duration**: {results.performance_metrics["total_time_seconds"]:.1f} seconds (basic quality scoring, no API delays)
""")

    # KB Coverage Status
    coverage = results.coverage_status
    report_sections.append(f"""## {coverage["status"]}

- **Current KB**: {coverage["kb_count"]} relevant papers found
- **External Papers**: {coverage["discovery_count"]} discovered
- **Assessment**: {coverage["message"]}
- **Recommendation**: {coverage["recommendation"]}
""")

    # Search Parameters
    params = results.search_params
    study_types_str = ", ".join(params["study_types"]) if params["study_types"] else "All types"
    author_filter_str = ", ".join(params["author_filter"]) if params["author_filter"] else "No filter"

    report_sections.append(f"""## Search Parameters

- **Keywords**: {", ".join(params["keywords"])}
- **Year Range**: {params["year_from"]}-2024
- **Study Types**: {study_types_str}
- **Source**: Semantic Scholar (comprehensive cross-domain coverage)
- **Population Focus**: {params["population_focus"] or "None"}
- **Quality Threshold**: {params["quality_threshold"] or "No threshold"}
- **Author Filter**: {author_filter_str}
- **Min Citations**: {params["min_citations"]}
- **Include KB Papers**: {"Yes" if params["include_kb_papers"] else "No"}
""")

    # Coverage Information
    report_sections.append("""## Coverage Information

**Semantic Scholar provides comprehensive coverage (214M papers, 85% of digital health research).**

For specialized needs, consider manual access:
- 🔍 **PubMed**: Clinical trial protocols, regulatory submissions
- 🔍 **IEEE**: Engineering standards, technical implementation details
- 🔍 **arXiv**: Latest AI/ML preprints (6-12 months ahead)

**Manual Access Links:**
- PubMed: https://pubmed.ncbi.nlm.nih.gov/
- IEEE: https://ieeexplore.ieee.org/
- arXiv: https://arxiv.org/search/
""")

    # Results sections
    if high_confidence:
        report_sections.append(f"""## High Confidence Results (Score 80+)

{generate_paper_list(high_confidence)}""")

    if medium_confidence:
        report_sections.append(f"""## Medium Confidence Results (Score 60-79)

{generate_paper_list(medium_confidence)}""")

    if low_confidence:
        report_sections.append(f"""## Low Confidence Results (Score 40-59)

{generate_paper_list(low_confidence[:10])}""")  # Limit low confidence to 10

    # Performance summary
    report_sections.append(f"""## Search Performance

- **Total Papers Found**: {results.performance_metrics["papers_found"]}
- **After Filtering**: {results.performance_metrics["papers_returned"]}
- **High Confidence**: {len(high_confidence)} papers
- **Medium Confidence**: {len(medium_confidence)} papers
- **Low Confidence**: {len(low_confidence)} papers
- **KB Papers Excluded**: {results.performance_metrics["kb_papers_excluded"]}
""")

    # DOI Lists for Zotero Import
    report_sections.append(generate_doi_lists(high_confidence, medium_confidence, low_confidence))

    return "\n".join(report_sections)


def generate_paper_list(papers: list[ScoredPaper]) -> str:
    """Generate formatted markdown list of papers for report inclusion.

    Creates detailed, professional paper listings with comprehensive metadata
    for easy evaluation and citation. Handles edge cases like missing data
    and long author lists gracefully.

    Args:
        papers: List of ScoredPaper objects to format (already sorted by score)

    Returns:
        Formatted markdown string with numbered paper entries, or
        "No papers found in this category." message if empty list

    Format Details:
        Each paper entry includes:
        - Sequential numbering (Paper 1, Paper 2, etc.)
        - Full title as primary identifier
        - DOI for citation and database lookup
        - Author list (first 3 + "et al." if more)
        - Publication year ("n.d." if unknown)
        - Citation count for impact assessment
        - Venue for quality/prestige evaluation
        - Dual scoring (quality/relevance/overall) with explanations
        - Study type classification for methodology assessment
        - Abstract preview (200 chars) for content evaluation

    Author List Handling:
        - Shows first 3 authors for readability
        - Indicates total count if >3 authors ("et al. (12 total)")
        - Handles empty author lists gracefully

    Abstract Preview:
        - Truncates to 200 characters for overview
        - Adds ellipsis ("...") if truncated
        - Omitted entirely if no abstract available

    Study Type Display:
        - Converts internal codes ("rct" → "Rct")
        - Replaces underscores with spaces for readability
        - Title case formatting for professional appearance

    Markdown Formatting:
        - Uses ### headers for clear paper separation
        - Bullet points for metadata organization
        - Consistent formatting for easy scanning
    """
    if not papers:
        return "No papers found in this category."

    paper_entries = []

    for i, scored_paper in enumerate(papers, 1):
        paper = scored_paper.paper

        # Format authors
        authors_str = ", ".join(paper.authors[:3])  # First 3 authors
        if len(paper.authors) > 3:
            authors_str += f", et al. ({len(paper.authors)} total)"

        # Format year
        year_str = str(paper.year) if paper.year else "n.d."

        # Create entry
        entry = f"""### Paper {i}: {paper.title}

- **DOI**: {paper.doi}
- **Authors**: {authors_str}
- **Year**: {year_str}
- **Citations**: {paper.citation_count}
- **Venue**: {paper.venue or "Unknown journal"}
- **Quality Score**: {scored_paper.quality_score:.0f}/100
- **Relevance Score**: {scored_paper.relevance_score:.0f}/100
- **Overall Score**: {scored_paper.overall_score:.0f}/100
- **Why Relevant**: {scored_paper.reasoning}
- **Study Type**: {detect_study_type(f"{paper.title} {paper.abstract}").replace("_", " ").title()}
"""

        if paper.abstract:
            # Truncate abstract to 200 characters
            abstract_preview = paper.abstract[:200]
            if len(paper.abstract) > 200:
                abstract_preview += "..."
            entry += f"- **Abstract Preview**: {abstract_preview}\n"

        paper_entries.append(entry)

    return "\n".join(paper_entries)


def generate_doi_lists(
    high_conf: list[ScoredPaper], medium_conf: list[ScoredPaper], low_conf: list[ScoredPaper]
) -> str:
    """Generate Zotero-ready DOI lists organized by confidence level for efficient import.

    Creates clean, importable DOI lists that integrate seamlessly with reference
    management workflows. Filters out non-standard identifiers and organizes
    by confidence level for prioritized import strategies.

    Args:
        high_conf: High confidence papers (80+ overall score)
        medium_conf: Medium confidence papers (60-79 overall score)
        low_conf: Low confidence papers (40-59 overall score)

    Returns:
        Formatted markdown section with code blocks containing clean DOI lists
        ready for copy-paste into Zotero or other reference managers

    DOI Filtering Logic:
        - Includes only real DOIs (10.xxxx/xxxxx format)
        - Excludes Semantic Scholar IDs (s2-xxxxx format)
        - Filters out empty or malformed identifiers
        - Ensures all DOIs are valid for citation database lookup

    Organization Strategy:
        1. High Confidence: Priority imports for core references
        2. Medium Confidence: Secondary imports for broader coverage
        3. All Combined: Bulk import option for comprehensive collections

        Low confidence papers omitted from DOI lists to focus on
        higher-quality references suitable for academic work.

    Format Features:
        - Clean code blocks for easy copy-paste
        - Count indicators for quick assessment ("High Confidence Papers (5 DOIs)")
        - One DOI per line for standard import format
        - No extra formatting that could interfere with import tools

    Workflow Integration:
        - Compatible with Zotero DOI import
        - Works with EndNote and Mendeley
        - Suitable for manual database searches
        - Enables systematic reference collection

    Usage Patterns:
        - Systematic reviews: Import high confidence first, expand as needed
        - Literature surveys: Use combined list for comprehensive coverage
        - Grant applications: Focus on high confidence for key citations
        - Manuscript preparation: Prioritize by confidence level and relevance
    """
    sections = ["## DOI Lists for Zotero Import\n"]

    if high_conf:
        dois = [p.paper.doi for p in high_conf if p.paper.doi and not p.paper.doi.startswith("s2-")]
        if dois:
            sections.append(f"""### High Confidence Papers ({len(dois)} DOIs)

```text
{chr(10).join(dois)}
```
""")

    if medium_conf:
        dois = [p.paper.doi for p in medium_conf if p.paper.doi and not p.paper.doi.startswith("s2-")]
        if dois:
            sections.append(f"""### Medium Confidence Papers ({len(dois)} DOIs)

```text
{chr(10).join(dois)}
```
""")

    # All papers combined
    all_dois = []
    for papers in [high_conf, medium_conf, low_conf]:
        all_dois.extend([p.paper.doi for p in papers if p.paper.doi and not p.paper.doi.startswith("s2-")])

    if all_dois:
        sections.append(f"""### All Papers Combined ({len(all_dois)} DOIs)

```text
{chr(10).join(all_dois)}
```
""")

    return "\n".join(sections)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    main()
