#!/usr/bin/env python3
"""Network Gap Analysis CLI for Research Assistant v4.0.

Command-line interface for identifying missing papers in a knowledge base through
systematic analysis of citation networks and author networks. Part of the two-phase
gap analysis workflow designed for comprehensive literature discovery.

**Phase 1 Implementation**: Citation networks (highest ROI) + simplified author networks
**Future Phases**: Co-citation clustering, temporal gaps, semantic similarity

## Two-Part Workflow

### Part 1: One-Time Setup (build_kb → analyze_gaps)
Run once after KB building to establish foundational gap analysis. This script
provides the comprehensive baseline discovery of literature gaps.

### Part 2: Research-Driven Discovery (/research → /doi)
On-demand discovery during active research via Claude Code slash commands.

## Core Algorithms

1. **Citation Network Analysis** (Primary): Identifies papers frequently cited by
   your KB papers but missing from your collection. Highest confidence due to
   clear relevance signals from your existing research.

2. **Simplified Author Networks** (Secondary): Finds recent publications from
   authors already in your KB. No author disambiguation needed - uses existing
   Semantic Scholar IDs from KB metadata.

## Output

Generates structured markdown reports in `exports/gap_analysis_YYYY_MM_DD_HHMM.md` with:
- Executive summary with gap counts and priority breakdown
- Detailed gap descriptions with confidence scores and relevance explanations
- Complete DOI lists organized by gap type for bulk Zotero import
- Step-by-step import instructions and workflow integration guidance

Usage Examples:
    python src/analyze_gaps.py                          # Comprehensive analysis
    python src/analyze_gaps.py --min-citations 50      # High-impact papers only
    python src/analyze_gaps.py --year-from 2020        # Recent author work
    python src/analyze_gaps.py --limit 100             # Top 100 gaps by priority
    python src/analyze_gaps.py --min-citations 20 --year-from 2020 --limit 50  # Conservative

Performance Notes:
- Analysis duration: 15-25 minutes for 2000-paper KB (depends on citation density)
- API requests: ~1 per KB paper + ~1 per 10 unique authors (with rate limiting)
- Memory usage: <2GB during analysis, results streamed to prevent OOM
- Caching: 7-day API response cache for rapid re-analysis and development
"""

import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

# Configuration imports
try:
    # For module imports (from tests)
    from .config import KB_VERSION, KB_DATA_PATH
except ImportError:
    # For direct script execution
    try:
        from config import KB_VERSION, KB_DATA_PATH
    except ImportError:
        # Fallback values
        KB_VERSION = "4.0+"
        KB_DATA_PATH = "kb_data"


def validate_kb_requirements(kb_path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate knowledge base meets all requirements for gap analysis.

    Performs comprehensive validation of KB structure, version compatibility,
    and minimum data requirements. Implements fail-fast error handling with
    actionable error messages for common failure scenarios.

    Args:
        kb_path (str): Path to knowledge base directory containing metadata.json
                      and required KB infrastructure files.

    Returns:
        tuple[dict[str, Any], list[dict[str, Any]]]: Validated (metadata, papers)
            if all requirements pass. Metadata contains KB version and statistics,
            papers contains list of paper metadata objects.

    Raises:
        SystemExit: If any validation requirement fails. Exit codes:
            - 1: KB not found, corrupted metadata, or insufficient papers
            - Error messages include specific remediation instructions

    Validation Requirements:
        - KB directory and metadata.json exist
        - KB version matches current system version (no legacy support)
        - Minimum 20 papers with complete metadata (title, authors)
        - Enhanced quality scoring available for confidence calculations

    Common Failure Scenarios:
        - "KB not found": Run `python src/build_kb.py --demo` for new setup
        - "Version mismatch": Delete kb_data/ and rebuild for compatibility
        - "Insufficient papers": Build larger KB or wait until 20+ papers imported
        - "Missing metadata": Run `python src/build_kb.py` to update metadata
    """
    kb_data_path = Path(kb_path)
    metadata_file = kb_data_path / "metadata.json"

    # Check KB exists
    if not kb_data_path.exists() or not metadata_file.exists():
        from error_formatting import safe_exit

        safe_exit(
            "Knowledge base not found",
            "Run: python src/build_kb.py --demo",
            "KB validation during gap analysis",
            module="analyze_gaps",
        )

    # Load metadata
    try:
        with open(metadata_file) as f:
            metadata = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        from error_formatting import safe_exit

        safe_exit(
            "Failed to load KB metadata",
            "Run: python src/build_kb.py --rebuild",
            "KB metadata loading during gap analysis",
            technical_details=str(e),
            module="analyze_gaps",
        )

    # Check KB version
    if metadata.get("version") != KB_VERSION:
        from error_formatting import safe_exit

        safe_exit(
            f"KB v{KB_VERSION}+ required. Found v{metadata.get('version', 'unknown')}",
            "Delete kb_data/ and rebuild: python src/build_kb.py",
            "KB version compatibility check",
            module="analyze_gaps",
        )

    # Check minimum papers
    papers = metadata.get("papers", [])
    if len(papers) < 20:
        from error_formatting import safe_exit

        safe_exit(
            "Minimum 20 papers required for gap analysis",
            f"Found {len(papers)} papers. Build larger knowledge base.",
            "Paper count validation",
            module="analyze_gaps",
        )

    # Check for basic metadata required for gap detection
    papers_with_metadata = [p for p in papers if p.get("title") and p.get("authors")]
    if len(papers_with_metadata) < 20:
        from error_formatting import safe_exit

        safe_exit(
            "KB lacks sufficient metadata for gap analysis",
            "Run: python src/build_kb.py",
            "Paper metadata validation",
            module="analyze_gaps",
        )

    return metadata, papers


def _setup_gap_analysis_environment(kb_path: str) -> tuple[dict[str, Any], list[dict[str, Any]], 'ProgressTracker']:
    """Setup gap analysis environment and initialize components."""
    from output_formatting import ProgressTracker

    # Validate KB requirements
    metadata, papers = validate_kb_requirements(kb_path)
    progress = ProgressTracker("Gap Analysis Workflow", total=4, show_eta=False)

    return metadata, papers, progress


def _import_gap_analyzer() -> type:
    """Import gap detection module with fallback handling."""
    try:
        from .gap_detection import GapAnalyzer

        return GapAnalyzer
    except ImportError:
        try:
            from gap_detection import GapAnalyzer

            return GapAnalyzer
        except ImportError:
            from error_formatting import safe_exit

            safe_exit(
                "Gap detection module not found",
                "Implementation in progress.",
                "Gap detection module import",
                module="analyze_gaps",
            )
            return None  # This line will never be reached due to safe_exit


def _print_analysis_header(
    total_papers: int, metadata: dict[str, Any], min_citations: int, year_from: int, limit: int | None
) -> None:
    """Print analysis setup information."""
    from output_formatting import print_status, print_header

    print_header("🔍 Running Network Gap Analysis")
    print_status(f"Knowledge Base: {total_papers:,} papers", "info")
    print_status(f"KB Version: v{metadata.get('version')}", "info")
    print_status("Analysis Settings:", "info")
    print(f"  • Min citations: {min_citations}")
    print(f"  • Author papers from: {year_from}")
    print(f"  • Result limit: {limit or 'unlimited'}")
    print()


async def run_gap_analysis(kb_path: str, min_citations: int, year_from: int, limit: int | None) -> None:
    """Run comprehensive gap analysis workflow and generate structured report.

    Orchestrates the complete gap analysis process including KB validation,
    gap detection algorithm execution, confidence scoring, and report generation.
    Implements sequential processing with rate limiting for API compliance.

    The analysis proceeds in phases:
    1. KB validation and requirement checking
    2. Citation network analysis (primary algorithm)
    3. Author network analysis (secondary algorithm)
    4. Confidence scoring and priority classification
    5. Structured report generation with DOI lists

    Args:
        kb_path (str): Path to knowledge base directory containing required files
        min_citations (int): Minimum citation count threshold for gap candidates.
                           Higher values focus on well-established papers.
        year_from (int): Include author network papers from this year onwards.
                        Controls recency vs comprehensiveness tradeoff.
        limit (int | None): Maximum gaps to return per algorithm type. None for
                          unlimited results (subject to hard limits in config).

    Raises:
        SystemExit: If KB validation fails, gap detection module missing,
                   or critical errors during analysis prevent completion.
        KeyboardInterrupt: User can safely interrupt analysis at any point.

    Performance Notes:
        - Duration: 15-25 minutes for 2000-paper KB (varies by citation density)
        - API requests: ~1 per KB paper + ~1 per 10 unique authors
        - Memory usage: <2GB during processing, results streamed to prevent OOM
        - Progress indicators: Updates every 50 papers processed
    """
    # Setup analysis environment
    metadata, papers, progress = _setup_gap_analysis_environment(kb_path)
    total_papers = len(papers)
    _print_analysis_header(total_papers, metadata, min_citations, year_from, limit)

    from output_formatting import print_status
    
    # Import and initialize gap analyzer
    gap_analyzer_class = _import_gap_analyzer()

    # Initialize gap analyzer
    progress.update(1, "Initializing gap analyzer")
    analyzer = gap_analyzer_class(kb_path)

    # Run citation network analysis
    progress.update(2, "Analyzing citation networks")
    start_time = time.time()

    citation_gaps = await analyzer.find_citation_gaps(min_citations=min_citations, limit=limit)

    citation_time = time.time() - start_time
    print_status(f"Found {len(citation_gaps)} citation gaps in {citation_time:.1f}s", "success")

    # Run author network analysis
    progress.update(3, "Analyzing author networks")
    start_time = time.time()

    author_gaps = await analyzer.find_author_gaps(year_from=year_from, limit=limit)

    author_time = time.time() - start_time
    print_status(f"Found {len(author_gaps)} author gaps in {author_time:.1f}s", "success")

    # Generate comprehensive report
    progress.update(4, "Generating report")
    total_gaps = len(citation_gaps) + len(author_gaps)

    # Create exports directory if needed
    exports_dir = Path("exports")
    exports_dir.mkdir(exist_ok=True)

    # Generate report filename with hour/minute to prevent same-day overwrites
    timestamp = datetime.now(UTC).strftime("%Y_%m_%d_%H%M")
    report_path = exports_dir / f"gap_analysis_{timestamp}.md"

    await analyzer.generate_report(
        citation_gaps=citation_gaps,
        author_gaps=author_gaps,
        output_path=str(report_path),
        kb_metadata=metadata,
    )

    progress.complete("Analysis complete")

    # Summary
    print()
    print_status("Gap Analysis Complete!", "success")
    print_status(f"Total gaps identified: {total_gaps}", "info")
    print_status(f"Citation network gaps: {len(citation_gaps)}", "info")
    print_status(f"Author network gaps: {len(author_gaps)}", "info")
    print_status(f"Report saved to: {report_path}", "info")
    print()
    print_status("Import DOIs into Zotero:", "info")
    print(f"   1. Open report: {report_path}")
    print("   2. Copy DOI lists from 'Complete DOI Lists' section")
    print("   3. Import into Zotero using Add Item by Identifier")


@click.command()
@click.option(
    "--min-citations",
    type=int,
    default=0,
    metavar="N",
    help="""Minimum citation count threshold for gap candidates.

    Only papers with N or more citations will be suggested. Higher values
    focus on well-established, influential papers but may miss recent work.

    • 0 (default): Include all papers regardless of citation count
    • 20-50: Focus on moderately well-cited papers
    • 100+: Only highly influential papers

    Note: Recent papers (last 2-3 years) naturally have fewer citations.""",
)
@click.option(
    "--year-from",
    type=int,
    default=2022,
    metavar="YYYY",
    help="""Recency threshold for author network analysis.

    For author gaps, only include papers published from this year onwards.
    Controls the recency vs comprehensiveness tradeoff for author networks.

    • 2024: Only very recent work (emphasizes cutting-edge research)
    • 2022 (default): Recent work (past ~3 years, balanced approach)
    • 2020: Broader timeframe (past ~5 years, more comprehensive)
    • 2018: Very broad (past ~7 years, maximum coverage)

    Range: 2015-2025 (Semantic Scholar coverage limitations)""",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    metavar="N",
    help="""Maximum number of gaps to return per algorithm type.

    Limits results to top N highest-priority gaps for each algorithm
    (citation networks and author networks). Useful for focused analysis
    or when working with very large knowledge bases.

    • None (default): Return all qualifying gaps (subject to hard limits)
    • 50: Focused analysis with top recommendations only
    • 100: Balanced approach for most use cases
    • 200+: Comprehensive results for large-scale gap analysis

    Note: Each algorithm type (citation/author) gets N results independently.""",
)
@click.option(
    "--kb-path",
    type=str,
    default=KB_DATA_PATH,
    metavar="PATH",
    help=f"""Path to knowledge base directory.

    Directory must contain a valid Research Assistant v4.0+ knowledge base
    with metadata.json, paper files, and required infrastructure.

    Default: {KB_DATA_PATH}

    Requirements:
    • KB version 4.0 or higher (no legacy support)
    • Minimum 20 papers with complete metadata
    • Enhanced quality scoring preferred for optimal results""",
)
def main(min_citations: int, year_from: int, limit: int | None, kb_path: str) -> None:
    r"""Network Gap Analysis - Identify missing papers in your knowledge base.

    \b
    OVERVIEW:
    Discovers literature gaps using citation networks and author networks.
    Generates structured reports with DOI lists for easy Zotero import.

    \b
    GAP TYPES:
    • Citation Gaps: Papers cited by your KB but missing from collection
    • Author Gaps: Recent work from researchers already in your KB

    \b
    WORKFLOW:
    1. Validates KB (requires v4.0+, 20+ papers)
    2. Analyzes citation networks (primary algorithm, highest confidence)
    3. Analyzes author networks (secondary algorithm, recency focused)
    4. Generates prioritized report in exports/gap_analysis_YYYY_MM_DD.md

    \b
    COMMON USAGE PATTERNS:

    # First-time comprehensive analysis (recommended)
    python src/analyze_gaps.py

    # High-impact papers only (well-established research)
    python src/analyze_gaps.py --min-citations 50

    # Recent focus with limits (cutting-edge + manageable results)
    python src/analyze_gaps.py --year-from 2024 --limit 50

    # Conservative balanced approach
    python src/analyze_gaps.py --min-citations 20 --year-from 2020 --limit 100

    \b
    PERFORMANCE:
    • Duration: 15-25 minutes for 2000-paper KB (varies by citation density)
    • Memory: <2GB RAM regardless of KB size
    • Network: Requires stable internet (Semantic Scholar API)
    • Resumable: Safe interruption with cache preservation

    \b
    OUTPUT:
    Structured markdown report with executive summary, detailed gaps by priority,
    and complete DOI lists organized by type for bulk Zotero import.

    \b
    TROUBLESHOOTING:
    • "KB not found": Run 'python src/build_kb.py --demo'
    • "Version mismatch": Delete kb_data/ and rebuild
    • "Insufficient papers": Build larger KB (need 20+ papers)
    • Analysis fails: Check network, delete .gap_analysis_cache.json and retry
    """
    # Validate command-line arguments with comprehensive error messages
    # Each validation provides specific remediation guidance
    from error_formatting import safe_exit

    if year_from < 2015:
        safe_exit(
            "--year-from must be 2015 or later",
            "Semantic Scholar coverage is limited before 2015",
            "Command-line argument validation",
            module="analyze_gaps",
        )

    if year_from > 2025:
        safe_exit(
            "--year-from cannot be in the future",
            "Use current year or earlier for realistic results",
            "Command-line argument validation",
            module="analyze_gaps",
        )

    if limit is not None and limit <= 0:
        safe_exit(
            "--limit must be positive",
            "Use positive integer or omit for unlimited results",
            "Command-line argument validation",
            module="analyze_gaps",
        )

    if min_citations < 0:
        safe_exit(
            "--min-citations cannot be negative",
            "Use 0 for all papers or positive integer for citation threshold",
            "Command-line argument validation",
            module="analyze_gaps",
        )

    # Run gap analysis with comprehensive error handling
    try:
        asyncio.run(run_gap_analysis(kb_path, min_citations, year_from, limit))
    except KeyboardInterrupt:
        # User interruption is safe - cache and progress are preserved
        safe_exit(
            "Analysis interrupted by user",
            "Progress saved. Re-run to continue from checkpoint.",
            "User interruption during gap analysis",
            module="analyze_gaps",
        )
    except ImportError as e:
        # Gap detection module missing - development/installation issue
        safe_exit(
            "Gap detection module not available",
            "Check installation or run from correct directory.",
            "Gap detection module import during execution",
            technical_details=str(e),
            module="analyze_gaps",
        )
    except Exception as e:
        # Catch-all for unexpected errors with diagnostic information
        safe_exit(
            "Analysis failed",
            "Check KB integrity, network connection, and try again. For persistent issues, delete .gap_analysis_cache.json and retry.",
            "Unexpected error during gap analysis",
            technical_details=str(e),
            module="analyze_gaps",
        )


if __name__ == "__main__":
    main()
