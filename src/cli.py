#!/usr/bin/env python3
"""
Command-line interface for Research Assistant v4.0.

Provides comprehensive literature search and retrieval capabilities with:
- Semantic search using Multi-QA MPNet embeddings and FAISS
- Quality scoring (0-100) based on study type and metadata
- Smart chunking for processing large result sets
- Multiple output formats (IEEE citations, CSV export)
- Author-based and year-based filtering
- Batch operations for efficient retrieval

Commands:
    search: Semantic similarity search with quality filtering
    get: Retrieve specific papers by ID
    get-batch: Retrieve multiple papers efficiently
    batch: Execute multiple commands with single model load (10-20x faster)
    author: Search papers by author name
    cite: Generate IEEE-format citations
    info: Display knowledge base statistics
    smart-search: Intelligent chunking for large queries
    diagnose: Health check and integrity validation

Usage:
    python src/cli.py search "machine learning healthcare"
    python src/cli.py get 0042 --sections methods results
    python src/cli.py cite 0001 0002 0003
"""

import json
import logging
import re
import sys
import time
import uuid
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Any, Optional

import click

try:
    import faiss
except ImportError as e:
    print("Error: faiss-cpu is not installed.", file=sys.stderr)
    print("Please install it with: pip install faiss-cpu", file=sys.stderr)
    print(f"Details: {e}", file=sys.stderr)
    sys.exit(1)

# Global model cache to avoid reloading
_model_cache = {}

# ============================================================================
# CONFIGURATION - Import from centralized config.py
# ============================================================================

try:
    # For module imports (from tests)
    from .config import (
        # Paths
        KB_DATA_PATH,
        # Model
        EMBEDDING_MODEL,
        # Search
        DEFAULT_K as DEFAULT_SEARCH_RESULTS,
        DEFAULT_CITATION_COUNT,
        DEFAULT_SMART_SEARCH_RESULTS,
        DEFAULT_MAX_TOKENS,
        # Quality scoring
        QUALITY_BASE_SCORE,
        QUALITY_STUDY_TYPE_WEIGHTS,
        # Sample size
        SAMPLE_SIZE_LARGE_THRESHOLD,
        SAMPLE_SIZE_MEDIUM_THRESHOLD,
        SAMPLE_SIZE_SMALL_THRESHOLD,
        BONUS_LARGE_SAMPLE,
        BONUS_MEDIUM_SAMPLE,
        # Recency
        YEAR_VERY_RECENT,
        YEAR_RECENT,
        BONUS_VERY_RECENT,
        BONUS_RECENT,
        # Other bonuses
        BONUS_FULL_TEXT,
        # Display
        STUDY_TYPE_MARKERS,
        QUALITY_EXCELLENT,
        QUALITY_GOOD,
        QUALITY_MODERATE,
        QUALITY_LOW,
        # UX Analytics
        UX_LOG_PATH,
        UX_LOG_PREFIX,
        UX_LOG_LEVEL,
        UX_LOG_ENABLED,
    )
except ImportError:
    # For direct script execution
    from config import (
        # Paths
        KB_DATA_PATH,
        # Model
        EMBEDDING_MODEL,
        # Search
        DEFAULT_K as DEFAULT_SEARCH_RESULTS,
        DEFAULT_CITATION_COUNT,
        DEFAULT_SMART_SEARCH_RESULTS,
        DEFAULT_MAX_TOKENS,
        # Quality scoring
        QUALITY_BASE_SCORE,
        QUALITY_STUDY_TYPE_WEIGHTS,
        # Sample size
        SAMPLE_SIZE_LARGE_THRESHOLD,
        SAMPLE_SIZE_MEDIUM_THRESHOLD,
        SAMPLE_SIZE_SMALL_THRESHOLD,
        BONUS_LARGE_SAMPLE,
        BONUS_MEDIUM_SAMPLE,
        # Recency
        YEAR_VERY_RECENT,
        YEAR_RECENT,
        BONUS_VERY_RECENT,
        BONUS_RECENT,
        # Other bonuses
        BONUS_FULL_TEXT,
        # Display
        STUDY_TYPE_MARKERS,
        QUALITY_EXCELLENT,
        QUALITY_GOOD,
        QUALITY_MODERATE,
        QUALITY_LOW,
        # UX Analytics
        UX_LOG_PATH,
        UX_LOG_PREFIX,
        UX_LOG_LEVEL,
        UX_LOG_ENABLED,
    )


# Import additional constants from config
try:
    # For module imports (from tests)
    from .config import (
        KB_VERSION,
        PAPER_ID_DIGITS,
        VALID_PAPER_ID_PATTERN,
        # Quality scoring constants
        QUALITY_EXCELLENT,
        QUALITY_VERY_GOOD,
        QUALITY_GOOD,
        QUALITY_MODERATE,
        QUALITY_LOW,
        QUALITY_INDICATORS,
        STUDY_TYPE_MARKERS,
    )
except ImportError:
    # For direct script execution
    from config import (
        KB_VERSION,
        PAPER_ID_DIGITS,
        VALID_PAPER_ID_PATTERN,
        # Quality scoring constants
        QUALITY_EXCELLENT,
        QUALITY_VERY_GOOD,
        QUALITY_GOOD,
        QUALITY_MODERATE,
        QUALITY_LOW,
        QUALITY_INDICATORS,
        STUDY_TYPE_MARKERS,
    )

# Display Configuration
MAX_QUALITY_SCORE = 100
PAPER_ID_FORMAT = VALID_PAPER_ID_PATTERN.pattern

# ============================================================================
# UX ANALYTICS SETUP
# ============================================================================

# Global session ID for tracking user sessions
_session_id = str(uuid.uuid4())[:8]


def _setup_ux_logger() -> logging.Logger | None:
    """Set up UX analytics logger with JSON formatting."""
    try:
        # Disable logging in test environment
        if not UX_LOG_ENABLED or "pytest" in sys.modules:
            return None

        # Ensure logs directory exists
        UX_LOG_PATH.mkdir(exist_ok=True)

        # Create log filename with date
        log_date = datetime.now(UTC).strftime("%Y%m%d")
        log_file = UX_LOG_PATH / f"{UX_LOG_PREFIX}{log_date}.jsonl"

        # Create logger
        logger = logging.getLogger("ux_analytics")
        logger.setLevel(getattr(logging, UX_LOG_LEVEL))

        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()

        # Create file handler
        handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        handler.setLevel(getattr(logging, UX_LOG_LEVEL))

        # Create JSON formatter
        class JSONFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_data = {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "session_id": _session_id,
                    "level": record.levelname,
                    "message": record.getMessage(),
                }
                # Add any extra data from the record
                if hasattr(record, "extra_data"):
                    log_data.update(record.extra_data)
                return json.dumps(log_data)

        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False  # Don't propagate to root logger

        return logger
    except Exception:
        # If logging setup fails, silently continue without logging
        # This prevents UX analytics from breaking core functionality
        return None


# Initialize UX analytics logger
_ux_logger = _setup_ux_logger()


def _log_ux_event(event_type: str, **kwargs: Any) -> None:
    """Log a UX analytics event."""
    if not _ux_logger or not UX_LOG_ENABLED:
        return

    extra_data = {"event_type": event_type, **kwargs}

    # Create a LogRecord with extra_data
    record = logging.LogRecord(
        name="ux_analytics", level=logging.INFO, pathname="", lineno=0, msg="", args=(), exc_info=None
    )
    record.extra_data = extra_data

    _ux_logger.handle(record)


# ============================================================================
# QUALITY ESTIMATION
# ============================================================================




def format_quality_indicator(quality_score: int) -> str:
    """Get visual indicator for quality score.
    
    Args:
        quality_score: Quality score 0-100
        
    Returns:
        Visual indicator emoji/symbol for the quality level
    """
    if quality_score >= QUALITY_EXCELLENT:
        return QUALITY_INDICATORS["excellent"]  # 🌟
    elif quality_score >= QUALITY_VERY_GOOD:
        return QUALITY_INDICATORS["very_good"]  # ⭐
    elif quality_score >= QUALITY_GOOD:
        return QUALITY_INDICATORS["good"]  # ●
    elif quality_score >= QUALITY_MODERATE:
        return QUALITY_INDICATORS["moderate"]  # ◐
    elif quality_score >= QUALITY_LOW:
        return QUALITY_INDICATORS["low"]  # ○
    else:
        return QUALITY_INDICATORS["very_low"]  # ·


def format_paper_with_enhanced_quality(
    paper: dict[str, Any], score: float, show_quality: bool = False
) -> str:
    """Format paper display with enhanced quality information.
    
    Args:
        paper: Paper metadata dictionary
        score: Relevance score
        show_quality: Whether to show detailed quality explanation
        
    Returns:
        Formatted paper display string with quality indicators
    """
    # Get quality indicator - all papers should have quality scores
    quality_score = paper.get("quality_score", 0)
    quality_indicator = format_quality_indicator(quality_score)
    
    # Get study type marker  
    type_marker = STUDY_TYPE_MARKERS.get(paper.get("study_type", "study"), "·")
    
    # Format authors display
    authors_display = ", ".join(paper.get("authors", [])[:2])
    if len(paper.get("authors", [])) > 2:
        authors_display += " et al."
    
    # Build main result line
    year = paper.get("year", "????")
    result = f"{paper['id']} {quality_indicator} {type_marker} {paper['title']} ({authors_display}, {year})"

    # Add detailed quality explanation if requested
    if show_quality:
        quality_explanation = paper.get("quality_explanation", "No explanation available")
        result += f"\n    Quality: {quality_score}/100 ({quality_explanation})"

    # Add relevance score
    result += f" [{score:.3f}]"
    
    return result


def format_search_results_with_enhanced_quality(results: list, show_quality: bool = False) -> str:
    """Format search results with enhanced quality scoring.
    
    Args:
        results: List of search result tuples (idx, score, paper)
        show_quality: Whether to show detailed quality explanations
        
    Returns:
        Formatted string with enhanced quality indicators
    """
    if not results:
        return "No papers found."

    formatted_results = []
    for idx, score, paper in results:
        formatted_paper = format_paper_with_enhanced_quality(paper, score, show_quality)
        formatted_results.append(formatted_paper)

    return "\n".join(formatted_results)


class ResearchCLI:
    """Main class for CLI operations on the knowledge base.

    Handles search queries, paper retrieval, and result formatting.
    Uses FAISS for similarity search and Multi-QA MPNet for embeddings.
    """

    def __init__(self, knowledge_base_path: str = "kb_data"):
        """Initialize CLI with knowledge base.

        Args:
            knowledge_base_path: Path to KB directory (default: kb_data)

        Raises:
            FileNotFoundError: If knowledge base doesn't exist
            ValueError: If KB version is incompatible
        """
        self.knowledge_base_path = Path(knowledge_base_path)
        self.papers_path = self.knowledge_base_path / "papers"
        self.index_file_path = self.knowledge_base_path / "index.faiss"
        self.metadata_file_path = self.knowledge_base_path / "metadata.json"

        if not self.knowledge_base_path.exists():
            raise FileNotFoundError(
                f"Knowledge base not found at {knowledge_base_path}. Run build_kb.py first."
            )

        # Use cli_kb_index for O(1) lookups
        try:
            from .cli_kb_index import KnowledgeBaseIndex
        except ImportError:
            from cli_kb_index import KnowledgeBaseIndex
        self.kb_index = KnowledgeBaseIndex(str(self.knowledge_base_path))
        self.metadata = self.kb_index.metadata

        # Version must be 4.0
        if self.metadata.get("version") != KB_VERSION:
            print("\nERROR: Knowledge base must be rebuilt")
            print("  Delete kb_data/ and run: python src/build_kb.py")
            sys.exit(1)

        # Load Multi-QA MPNet model for search
        self.embedding_model = self._load_embedding_model()
        self.search_index = faiss.read_index(str(self.index_file_path))

    def search(
        self,
        query_text: str,
        top_k: int = 10,
        min_year: int | None = None,
        study_types: list[str] | None = None,
    ) -> list[tuple[int, float, dict[str, Any]]]:
        """Search for relevant papers using semantic similarity.

        Uses Multi-QA MPNet embeddings to find semantically similar papers,
        with optional filtering by year and study type.

        Args:
            query_text: Natural language search query
            top_k: Number of results to return
            min_year: Filter papers published after this year
            study_types: List of study types to include

        Returns:
            List of tuples (index, distance, paper_dict) sorted by relevance
        """
        query_embedding = self.embedding_model.encode([query_text])

        # Search more than needed to account for filtering
        available_papers = len(self.metadata["papers"])
        search_k = min(top_k * 3, available_papers)  # Search 3x to allow for filtering

        distances, indices = self.search_index.search(query_embedding.astype("float32"), search_k)

        results = []
        for idx, dist in zip(indices[0], distances[0], strict=False):
            if idx != -1:  # -1 is returned for invalid indices
                # Use kb_index for O(1) paper lookup
                paper = self.kb_index.get_paper_by_index(idx)
                if not paper:
                    continue

                # Apply filters
                paper_year = paper.get("year")
                if min_year and paper_year and paper_year < min_year:
                    continue
                if study_types and paper.get("study_type", "study") not in study_types:
                    continue

                results.append((idx, float(dist), paper))

                # Stop when we have enough filtered results
                if len(results) >= top_k:
                    break

        return results

    def get_paper(self, paper_id: str) -> str:
        """Retrieve full text of a paper by ID.

        Args:
            paper_id: 4-digit paper ID (e.g., '0001')

        Returns:
            Paper content as markdown string

        Raises:
            ValueError: If paper ID format is invalid
        """

        # Use kb_index for O(1) validation and lookup
        paper = self.kb_index.get_paper_by_id(paper_id)
        if not paper:
            raise ValueError(f"Paper {paper_id} not found in knowledge base")

        # Construct safe path
        paper_file_path = self.papers_path / f"paper_{paper_id}.md"

        # Additional safety: ensure resolved path is within papers directory
        try:
            resolved_path = paper_file_path.resolve()
            papers_dir = self.papers_path.resolve()

            # Check if resolved path is within papers directory
            if not str(resolved_path).startswith(str(papers_dir)):
                raise ValueError("Invalid paper path")
        except Exception:
            raise ValueError(f"Paper {paper_id} not found") from None

        if not paper_file_path.exists():
            for paper in self.metadata["papers"]:
                if paper["id"] == paper_id:
                    paper_file_path = self.papers_path / paper["filename"]
                    break

        if paper_file_path.exists():
            with paper_file_path.open(encoding="utf-8") as f:
                return f.read()
        else:
            return f"Paper {paper_id} not found. Valid format: 4 digits (e.g., 0001)"

    def format_search_results(
        self,
        search_results: list[tuple[int, float, dict[str, Any]]],
        show_abstracts: bool = False,
        show_quality: bool = False,
    ) -> str:
        """Format search results with enhanced quality indicators.

        Args:
            search_results: List of (index, distance, paper) tuples
            show_abstracts: Whether to include abstract previews
            show_quality: Whether to show detailed quality explanations

        Returns:
            Formatted string for display with enhanced quality indicators
        """
        if not search_results:
            return "No papers found."

        output = []
        
        for i, (idx, dist, paper) in enumerate(search_results, 1):
            # Convert distance to similarity score for display
            relevance_score = 1 / (1 + dist)
            
            # Use enhanced quality formatting
            formatted_paper = format_paper_with_enhanced_quality(paper, relevance_score, show_quality)
            
            # Add index number
            output.append(f"{i}. {formatted_paper}")
            
            # Add abstract if requested
            if show_abstracts and paper.get("abstract"):
                abstract = (
                    paper["abstract"][:200] + "..." if len(paper["abstract"]) > 200 else paper["abstract"]
                )
                output.append(f"    Abstract: {abstract}")

        return "\n".join(output)

    def _load_embedding_model(self) -> Any:
        """Load the Multi-QA MPNet embedding model.

        Multi-QA MPNet is optimized for diverse question-answering including
        healthcare and scientific papers. Produces 768-dimensional vectors.

        Returns:
            SentenceTransformer model configured for Multi-QA MPNet
        """
        if EMBEDDING_MODEL not in _model_cache:
            print("Loading Multi-QA MPNet model for search...")
            from sentence_transformers import SentenceTransformer

            _model_cache[EMBEDDING_MODEL] = SentenceTransformer(EMBEDDING_MODEL)

        return _model_cache[EMBEDDING_MODEL]

    def smart_search(self, query_text: str, k: int = 20) -> list[tuple[int, float, dict[str, Any]]]:
        """Smart search with section chunking.

        Args:
            query_text: Search query
            k: Number of results to return

        Returns:
            List of search results from multiple section queries
        """
        # Perform initial search
        initial_results = self.search(query_text, k)

        # Always search within sections for comprehensive results
        method_results = self.search(f"{query_text} methods", k)
        result_results = self.search(f"{query_text} results", k)

        # Combine and deduplicate results
        all_results = initial_results + method_results + result_results
        seen = set()
        unique_results = []
        for result in all_results:
            paper_id = result[2].get("id")
            if paper_id not in seen:
                seen.add(paper_id)
                unique_results.append(result)

        return unique_results[:k]

    def format_ieee_citation(self, paper_metadata: dict[str, Any], citation_number: int) -> str:
        """Format paper metadata as IEEE citation.

        Args:
            paper_metadata: Paper metadata dictionary
            citation_number: Citation number for reference

        Returns:
            Formatted IEEE citation string
        """
        citation_text = f"[{citation_number}] "

        if paper_metadata.get("authors"):
            if len(paper_metadata["authors"]) <= 3:
                citation_text += ", ".join(paper_metadata["authors"])
            else:
                citation_text += f"{paper_metadata['authors'][0]} et al."
            citation_text += ", "

        citation_text += f'"{paper_metadata["title"]}", '

        if paper_metadata.get("journal"):
            citation_text += f"{paper_metadata['journal']}, "

        if paper_metadata.get("volume"):
            citation_text += f"vol. {paper_metadata['volume']}, "

        if paper_metadata.get("issue"):
            citation_text += f"no. {paper_metadata['issue']}, "

        if paper_metadata.get("pages"):
            citation_text += f"pp. {paper_metadata['pages']}, "

        if paper_metadata.get("year"):
            citation_text += f"{paper_metadata['year']}."

        return citation_text


@click.group()
def cli() -> None:
    """Research Assistant v4.0 - Semantic literature search and analysis.

    Advanced semantic search using Multi-QA MPNet embeddings with enhanced quality scoring,
    smart chunking, and comprehensive filtering options.

    \b
    SEARCH & DISCOVERY:
      search        Find papers by semantic similarity with filtering
      smart-search  Handle 20+ papers with automatic chunking
      author        Find all papers by specific author
      cite          Generate IEEE-style citations

    \b
    RETRIEVAL:
      get           Get specific paper by ID (with section options and citations)
      get-batch     Retrieve multiple papers at once (with citation support)

    \b
    BATCH OPERATIONS:
      batch         Execute multiple commands efficiently (10-20x faster)
                    Supports presets: research, review, author-scan

    \b
    SYSTEM:
      info          Show KB statistics and metadata
      diagnose      Run health checks on knowledge base

    \b
    KEY FEATURES:
      • Multi-QA MPNet embeddings optimized for healthcare & scientific papers
      • Enhanced quality scoring (0-100) with Semantic Scholar API integration
      • Visual quality indicators: 🌟⭐●◐○· for instant quality assessment
      • Comprehensive scoring: Citations, venue prestige, author authority, validation
      • Full content preservation - no truncation of paper sections
      • Complete methodology & results sections for thorough analysis
      • Advanced filters: year ranges, term inclusion/exclusion, quality thresholds
      • Multi-query search for comprehensive results
      • Group results by year, journal, or study type
      • Export to CSV for analysis
      • Smart section extraction from PDFs with zero information loss
      • IEEE citation generation and embedding in paper content

    \b
    QUICK START:
      python src/cli.py search "diabetes treatment" --show-quality
      python src/cli.py get 0001 --sections abstract methods
      python src/cli.py get 0001 --add-citation         # Paper with citation
      python src/cli.py cite 0001 0002 0003
      python src/cli.py smart-search "digital health" -k 30

    \b
    BUILD/UPDATE KB:
      python src/build_kb.py --demo     # Quick 5-paper demo
      python src/build_kb.py            # From Zotero library
    """


@cli.command()
@click.argument("query_text")
@click.option(
    "--top-k",
    "-k",
    default=10,
    help="Number of results to return (default: 10)",
)
@click.option("--verbose", "-v", is_flag=True, help="Show abstracts in results")
@click.option("--show-quality", is_flag=True, help="Show quality scores in results")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON for processing")
@click.option(
    "--after",
    type=int,
    help="Only papers published after this year (e.g., --after 2020)",
)
@click.option(
    "--type",
    "study_type",
    multiple=True,
    type=click.Choice(
        [
            "systematic_review",
            "rct",
            "cohort",
            "case_control",
            "cross_sectional",
            "case_report",
            "study",
        ]
    ),
    help="Filter by study type (can specify multiple, e.g., --type rct --type systematic_review)",
)
@click.option(
    "--group-by", type=click.Choice(["year", "journal", "study_type"]), help="Group results by field"
)
@click.option("--years", help="Filter by year range (e.g., 2020-2024 or 2023)")
@click.option("--contains", help="Filter by term in title/abstract")
@click.option("--exclude", help="Exclude papers with this term")
@click.option("--full-text", is_flag=True, help="Search in full text (slower)")
@click.option("--queries", multiple=True, help="Additional search queries")
@click.option("--min-quality", type=int, help="Minimum quality score (0-100)")
@click.option("--export", help="Export results to CSV file")
def search(
    query_text: str,
    top_k: int,
    verbose: bool,
    show_quality: bool,
    output_json: bool,
    after: int | None,
    study_type: tuple[str, ...],
    group_by: str | None,
    years: str | None,
    contains: str | None,
    exclude: str | None,
    full_text: bool,
    queries: tuple[str, ...],
    min_quality: int | None,
    export: str | None,
) -> None:
    """Search papers using Multi-QA MPNet semantic embeddings with enhanced quality scoring.

    \b
    ENHANCED QUALITY INDICATORS (0-100):
      🌟 90-100: Exceptional quality (high-impact systematic reviews/meta-analyses)
      ⭐ 80-89:  Excellent quality (top-tier venues, highly cited)
      ● 70-79:   Very good quality (quality RCTs, established venues)
      ◐ 60-69:   Good quality (solid studies, decent citations)
      ○ 50-59:   Moderate quality (cohort studies, emerging work)
      · 0-49:    Basic quality (case reports, limited validation)

    \b
    QUALITY FACTORS:
      • Citation Impact (25pts): Based on citation count and growth
      • Venue Prestige (15pts): Journal ranking and reputation
      • Author Authority (10pts): H-index and research standing
      • Cross-validation (10pts): DOI, PubMed, publication types
      • Study Type (20pts): Evidence hierarchy (systematic review > RCT > cohort)
      • Recency (10pts): Publication year relevance
      • Sample Size (5pts): Statistical power indicator
      • Full Text (5pts): Complete content availability

    \b
    FILTERING OPTIONS:
      --years        Year range (2020-2024) or single year (2023)
      --after        Papers after year (e.g., --after 2020)
      --type         Study type filter (can use multiple)
      --contains     Must contain term in title/abstract
      --exclude      Exclude papers with term
      --full-text    Search full text (slower but comprehensive)
      --min-quality  Minimum quality score threshold (use --show-quality to see scores)

    \b
    ADVANCED FEATURES:
      --queries      Add multiple search queries for comprehensive results
      --group-by     Group by year/journal/study_type for organized view
      --export       Save results to CSV in exports/ directory

    \b
    EXAMPLES:
      # Basic semantic search
      python src/cli.py search "diabetes treatment"

      # High-quality papers only
      python src/cli.py search "AI diagnosis" --min-quality 70

      # Recent RCTs
      python src/cli.py search "telemedicine" --after 2020 --type rct

      # Year range with term filtering
      python src/cli.py search "cancer" --years 2020-2024 --contains "immunotherapy"

      # Multi-query comprehensive search
      python src/cli.py search "diabetes" --queries "glucose monitoring" --queries "insulin"

      # Export results for Excel
      python src/cli.py search "hypertension" --export results.csv
    """
    start_time = time.time()

    # Log search command start
    _log_ux_event(
        "command_start",
        command="search",
        query_length=len(query_text),
        top_k=top_k,
        has_additional_queries=len(queries) > 0,
        additional_queries_count=len(queries),
        has_after_filter=after is not None,
        after_year=after,
        has_study_type_filter=len(study_type) > 0,
        study_types=list(study_type),
        has_year_range_filter=years is not None,
        has_contains_filter=contains is not None,
        has_exclude_filter=exclude is not None,
        full_text_search=full_text,
        min_quality=min_quality,
        show_quality=show_quality,
        output_json=output_json,
        group_by=group_by,
        export_requested=export is not None,
    )

    try:
        research_cli = ResearchCLI()

        # Handle multi-query search
        all_queries = [query_text]
        if queries:
            all_queries.extend(queries)

        # Collect results from all queries
        seen_ids = set()
        combined_results = []

        for q in all_queries:
            # Perform search
            study_types = list(study_type) if study_type else None
            # Get more results to allow for filtering
            search_k = top_k * 3 if (min_quality or years or contains or exclude) else top_k
            query_results = research_cli.search(q, search_k, min_year=after, study_types=study_types)

            # Add unique results
            for idx, dist, paper in query_results:
                if paper["id"] not in seen_ids:
                    seen_ids.add(paper["id"])
                    combined_results.append((idx, dist, paper))

        search_results = combined_results

        # Apply year filtering if specified
        if years:
            # Parse year range
            if "-" in years:
                start_year, end_year = map(int, years.split("-"))
            else:
                # Single year
                start_year = end_year = int(years)

            filtered = []
            for idx, dist, paper in search_results:
                year = paper.get("year")
                if year and start_year <= year <= end_year:
                    filtered.append((idx, dist, paper))
            search_results = filtered

        # Apply term filtering if specified
        if contains or exclude:
            import subprocess

            filtered = []
            for idx, dist, paper in search_results:
                if full_text:
                    # Search in full text using grep
                    paper_file = f"kb_data/papers/paper_{paper['id']}.md"

                    # Check contains
                    if contains:
                        ret = subprocess.run(
                            ["grep", "-qi", contains, paper_file], check=False, capture_output=True
                        )
                        if ret.returncode != 0:  # Not found
                            continue

                    # Check exclude
                    if exclude:
                        ret = subprocess.run(
                            ["grep", "-qi", exclude, paper_file], check=False, capture_output=True
                        )
                        if ret.returncode == 0:  # Found (exclude it)
                            continue
                else:
                    # Just check title + abstract (fast)
                    text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()

                    if contains and contains.lower() not in text:
                        continue
                    if exclude and exclude.lower() in text:
                        continue

                filtered.append((idx, dist, paper))
            search_results = filtered

        # Apply quality filtering if requested
        if min_quality:
            filtered_results = []
            for idx, dist, paper in search_results:
                # All papers should already have quality scores from enhanced scoring
                quality = paper.get("quality_score", 0)
                
                # Filter by minimum quality
                if quality >= min_quality:
                    filtered_results.append((idx, dist, paper))
            
            search_results = filtered_results[:top_k]
        else:
            search_results = search_results[:top_k]

        # Export to CSV if requested
        if export:
            import csv

            # Ensure exports directory exists
            exports_dir = Path("exports")
            exports_dir.mkdir(exist_ok=True)

            # Save with search prefix
            if not export.startswith("search_"):
                export = f"search_{export}"
            export_path = exports_dir / export
            with export_path.open("w", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "id",
                    "title",
                    "authors",
                    "year",
                    "journal",
                    "study_type",
                    "quality_score",
                    "doi",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                writer.writeheader()
                for _idx, dist, paper in search_results:
                    writer.writerow(
                        {
                            "id": paper["id"],
                            "title": paper.get("title", ""),
                            "authors": "; ".join(paper.get("authors", [])),
                            "year": paper.get("year", ""),
                            "journal": paper.get("journal", ""),
                            "study_type": paper.get("study_type", ""),
                            "quality_score": paper.get("quality_score", 0),
                            "doi": paper.get("doi", ""),
                        }
                    )

            print(f"✓ Exported {len(search_results)} results to {export_path}")

        # Handle grouping if requested
        if group_by:
            grouped: dict[str, list[tuple[int, float, dict[str, Any]]]] = {}
            for idx, dist, paper in search_results:
                key = paper.get(group_by, "Unknown")
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append((idx, dist, paper))

            # Display grouped results
            print(f"\nSearch results for: '{query_text}'")
            if queries:
                print(f"Additional queries: {', '.join(queries)}")
            print("=" * 50)

            # Sort keys, handling None values
            keys = list(grouped.keys())
            if group_by == "year":
                # Sort years in descending order, putting None at the end
                # Cast to int since years are always integers when not None
                keys.sort(key=lambda x: (x is None, -int(x) if x is not None else 0), reverse=False)
            else:
                # Sort other fields alphabetically, putting None/Unknown at the end
                keys.sort(key=lambda x: (x == "Unknown", x))

            for key in keys:
                print(f"\n{group_by.replace('_', ' ').title()}: {key} ({len(grouped[key])} papers)")
                for idx, dist, paper in grouped[key]:
                    relevance = 1 / (1 + dist)
                    quality_str = ""
                    if show_quality or min_quality:
                        quality = paper.get("quality_score", 0)
                        quality_str = f" [Q:{quality}]"
                    print(f"  [{paper['id']}] {paper['title'][:80]}...{quality_str} (R:{relevance:.2f})")
            return  # Skip normal display

        if output_json:
            output = []
            for _idx, dist, paper in search_results:
                result = {
                    "id": paper["id"],
                    "title": paper["title"],
                    "authors": paper.get("authors", []),
                    "year": paper.get("year"),
                    "journal": paper.get("journal"),
                    "study_type": paper.get("study_type", "study"),
                    "sample_size": paper.get("sample_size"),
                    "has_full_text": paper.get("has_full_text", False),
                    "similarity_score": float(1 / (1 + dist)),
                }
                if show_quality:
                    result["quality_score"] = paper.get("quality_score", 0)
                    result["quality_explanation"] = paper.get("quality_explanation", "")
                output.append(result)
            print(json.dumps(output, indent=2))
        else:
            print(f"\nSearch results for: '{query_text}'")
            print("=" * 50)

            # Use enhanced quality formatting for all results
            formatted_results = research_cli.format_search_results(
                search_results, 
                show_abstracts=verbose, 
                show_quality=show_quality
            )
            print(formatted_results)

        # Log successful search completion
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_success",
            command="search",
            execution_time_ms=execution_time_ms,
            results_found=len(search_results),
            exported_to_csv=export is not None,
        )

    except FileNotFoundError:
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_error",
            command="search",
            execution_time_ms=execution_time_ms,
            error_type="FileNotFoundError",
            error_message="Knowledge base not found",
        )
        print(
            "\n❌ Knowledge base not found.\n"
            "   Quick fix: python src/build_kb.py --demo\n"
            "   Full setup: python src/build_kb.py (requires Zotero)",
            file=sys.stderr,
        )
        sys.exit(1)
    except ImportError as error:
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_error",
            command="search",
            execution_time_ms=execution_time_ms,
            error_type="ImportError",
            error_message=str(error),
        )
        print(
            f"\n❌ Missing dependency: {error}\n   Fix: pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as error:
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_error",
            command="search",
            execution_time_ms=execution_time_ms,
            error_type=type(error).__name__,
            error_message=str(error),
        )
        print(
            f"\n❌ Search failed: {error}\n"
            "   Possible fixes:\n"
            "   1. Rebuild knowledge base: python src/build_kb.py\n"
            "   2. Check if model matches index: python src/cli.py info\n"
            "   3. Clear cache and rebuild: python src/build_kb.py --full",
            file=sys.stderr,
        )
        sys.exit(1)


@cli.command()
@click.argument("paper_id")
@click.option("--output", "-o", help="Output file path (saves as markdown)")
@click.option(
    "--sections",
    "-s",
    multiple=True,
    type=click.Choice(
        ["abstract", "introduction", "methods", "results", "discussion", "conclusion", "references", "all"]
    ),
    help="Retrieve only specific sections (default: all)",
)
@click.option("--add-citation", is_flag=True, help="Append IEEE citation to paper content")
def get(paper_id: str, output: str | None, sections: tuple[str, ...], add_citation: bool) -> None:
    """Get a specific paper by its 4-digit ID.

    Retrieve the full content of a paper or specific sections only.
    Paper IDs are always 4-digit zero-padded (e.g., 0001, 0234, 1426).

    \b
    Examples:
      python src/cli.py get 0001                        # Full paper
      python src/cli.py get 0234 --sections abstract    # Abstract only
      python src/cli.py get 1426 --sections methods results  # Multiple sections
      python src/cli.py get 0005 --output paper.md      # Save to file
      python src/cli.py get 0001 --add-citation         # Include IEEE citation
      python src/cli.py get 0234 --sections abstract --add-citation  # Sections + citation

    \b
    Available sections: abstract, introduction, methods, results, discussion,
                       conclusion, references, all
    """
    start_time = time.time()

    # Log get command start
    _log_ux_event(
        "command_start",
        command="get",
        paper_id=paper_id,
        has_sections_filter=len(sections) > 0,
        sections_requested=list(sections),
        sections_count=len(sections),
        output_to_file=output is not None,
    )

    try:
        research_cli = ResearchCLI()

        # Handle section-specific retrieval
        if sections and "all" not in sections:
            # Load sections index
            sections_index_path = Path("kb_data") / "sections_index.json"
            if sections_index_path.exists():
                with sections_index_path.open() as f:
                    sections_index = json.load(f)

                if paper_id in sections_index:
                    paper_sections = sections_index[paper_id]

                    # Get paper metadata for header
                    paper_metadata = None
                    for paper in research_cli.metadata.get("papers", []):
                        if paper["id"] == paper_id:
                            paper_metadata = paper
                            break

                    if paper_metadata:
                        # Build content with only requested sections
                        content = f"# {paper_metadata['title']}\n\n"
                        content += f"**Authors:** {', '.join(paper_metadata.get('authors', []))}  \n"
                        content += f"**Year:** {paper_metadata.get('year', 'Unknown')}  \n"
                        content += f"**Journal:** {paper_metadata.get('journal', 'Unknown')}  \n"
                        if paper_metadata.get("doi"):
                            content += f"**DOI:** {paper_metadata['doi']}  \n"
                        content += "\n---\n\n"

                        # Add requested sections
                        for section_name in sections:
                            section_content = paper_sections.get(section_name, "")
                            if section_content:
                                # Capitalize section name for display
                                display_name = section_name.replace("_", " ").title()
                                content += f"## {display_name}\n\n{section_content}\n\n"
                            else:
                                content += f"## {section_name.title()}\n\n*[Section not available]*\n\n"

                        content += f"\n---\n*Sections retrieved: {', '.join(sections)}*"

                        # Add citation if requested
                        if add_citation:
                            citation = research_cli.format_ieee_citation(paper_metadata, 1)
                            content += f"\n\n**Citation:** {citation}"
                    else:
                        # Fallback to regular get if metadata not found
                        content = research_cli.get_paper(paper_id)
                else:
                    print(f"⚠️  No section index found for paper {paper_id}")
                    content = research_cli.get_paper(paper_id)
            else:
                print("⚠️  Section index not found. Rebuild KB to enable section retrieval.")
                content = research_cli.get_paper(paper_id)
        else:
            # Get full paper
            content = research_cli.get_paper(paper_id)

        # Add citation if requested
        if add_citation:
            # Get paper metadata for citation
            paper_metadata = research_cli.kb_index.get_paper_by_id(paper_id)
            if paper_metadata:
                citation = research_cli.format_ieee_citation(paper_metadata, 1)
                content += f"\n\n---\n**Citation:** {citation}"

        if output:
            exports_dir = Path("exports")
            exports_dir.mkdir(exist_ok=True)
            # Add paper prefix if not already present
            if not output.startswith("paper_"):
                output = f"paper_{output}"
            output_path = exports_dir / output
            with output_path.open("w", encoding="utf-8") as f:
                f.write(content)
            print(f"Paper saved to {output_path}")
        else:
            print(content)

        # Log successful get completion
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_success",
            command="get",
            execution_time_ms=execution_time_ms,
            paper_retrieved=True,
            saved_to_file=output is not None,
        )

    except FileNotFoundError:
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_error",
            command="get",
            execution_time_ms=execution_time_ms,
            error_type="FileNotFoundError",
            error_message="Knowledge base not found",
        )
        print(
            "\n❌ Knowledge base not found.\n"
            "   Quick fix: python src/build_kb.py --demo\n"
            "   Full setup: python src/build_kb.py (requires Zotero)",
            file=sys.stderr,
        )
        sys.exit(1)
    except ValueError as error:
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_error",
            command="get",
            execution_time_ms=execution_time_ms,
            error_type="ValueError",
            error_message=str(error),
        )
        print(
            f"\n❌ Invalid paper ID: {error}\n"
            "   Paper IDs must be exactly 4 digits (e.g., 0001, 0234, 1234)\n"
            "   Use 'python src/cli.py search <query>' to find paper IDs",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as error:
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_error",
            command="get",
            execution_time_ms=execution_time_ms,
            error_type=type(error).__name__,
            error_message=str(error),
        )
        print(
            f"\n❌ Failed to retrieve paper: {error}\n"
            "   Make sure the paper ID is correct (4 digits, e.g., 0001)\n"
            "   Check available papers: python src/cli.py info",
            file=sys.stderr,
        )
        sys.exit(1)


@cli.command(name="get-batch")
@click.argument("paper_ids", nargs=-1, required=True)
@click.option("--format", type=click.Choice(["text", "json"]), default="text", help="Output format")
@click.option("--add-citation", is_flag=True, help="Append IEEE citation to each paper")
def get_batch(paper_ids: tuple[str, ...], format: str, add_citation: bool) -> None:
    """Get multiple papers by their IDs in a single batch.

    Efficiently retrieve multiple papers at once. Useful for reviewing
    search results or specific paper collections.

    \b
    Examples:
      python src/cli.py get-batch 0001 0002 0003        # Get three papers
      python src/cli.py get-batch 0234 1426             # Get specific papers
      python src/cli.py get-batch 0001 0002 --format json  # JSON output
      python src/cli.py get-batch 0001 0002 --add-citation  # Include numbered citations
      python src/cli.py get-batch 0001 0002 --format json --add-citation  # JSON + citations

    Paper IDs are always 4-digit zero-padded.
    Output formats: text (default) or json.
    """
    results: list[dict[str, str]] = []
    errors: list[str] = []

    try:
        research_cli = ResearchCLI()

        for paper_id in paper_ids:
            try:
                # Normalize ID to 4 digits
                if paper_id.isdigit():
                    paper_id = paper_id.zfill(4)

                # Validate paper ID format
                if not re.match(PAPER_ID_FORMAT, paper_id):
                    errors.append(f"Invalid paper ID format: {paper_id}")
                    continue

                # Get paper content
                content = research_cli.get_paper(paper_id)

                # Check if paper was found
                if "not found" in content.lower():
                    errors.append(f"Paper {paper_id} not found")
                    continue

                # Add citation if requested
                if add_citation:
                    # Get paper metadata for citation (use len(results) + 1 for citation number)
                    paper_metadata = research_cli.kb_index.get_paper_by_id(paper_id)
                    if paper_metadata:
                        citation_number = len(results) + 1
                        citation = research_cli.format_ieee_citation(paper_metadata, citation_number)
                        content += f"\n\n---\n**Citation:** {citation}"

                results.append({"id": paper_id, "content": content})

            except Exception as error:
                errors.append(f"Error reading {paper_id}: {error}")

        # Display results
        if format == "json":
            output = {"papers": results, "errors": errors, "count": len(results)}
            print(json.dumps(output, indent=2))
        else:
            # Text format
            for paper in results:
                print(f"\n{'=' * 50}")
                print(f"Paper {paper['id']}")
                print("=" * 50)
                print(paper["content"])

            if errors:
                print("\n⚠️ Errors encountered:", file=sys.stderr)
                for err_msg in errors:
                    print(f"  - {err_msg}", file=sys.stderr)

            # Summary
            print(f"\n✓ Retrieved {len(results)} papers successfully")
            if errors:
                print(f"✗ Failed to retrieve {len(errors)} papers")

    except FileNotFoundError:
        print(
            "\n❌ Knowledge base not found.\n"
            "   Quick fix: python src/build_kb.py --demo\n"
            "   Full setup: python src/build_kb.py (requires Zotero)",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as error:
        print(
            f"\n❌ Failed to retrieve papers: {error}\n"
            "   Check that paper IDs are correct (4 digits, e.g., 0001)",
            file=sys.stderr,
        )
        sys.exit(1)


@cli.command()
@click.argument("paper_ids", nargs=-1, required=True)
@click.option("--format", type=click.Choice(["text", "json"]), default="text", help="Output format")
def cite(paper_ids: tuple[str, ...], format: str) -> None:
    """Generate IEEE-style citations for specific papers by their IDs.

    Retrieve papers by ID and format them as ready-to-use IEEE citations.
    Perfect for creating reference lists from known papers.

    \b
    Examples:
      python src/cli.py cite 0001 0002 0003        # Cite three papers
      python src/cli.py cite 0234 1426             # Cite specific papers
      python src/cli.py cite 0001 0002 --format json  # JSON output

    Paper IDs are always 4-digit zero-padded.
    Output formats: text (default) or json.
    """
    start_time = time.time()

    # Log cite command start
    _log_ux_event(
        "command_start", command="cite", paper_count=len(paper_ids), paper_ids=list(paper_ids), format=format
    )

    results = []
    errors = []

    try:
        research_cli = ResearchCLI()

        for idx, paper_id in enumerate(paper_ids, 1):
            try:
                # Normalize ID to 4 digits
                if paper_id.isdigit():
                    paper_id = paper_id.zfill(4)

                # Validate paper ID format
                if not re.match(PAPER_ID_FORMAT, paper_id):
                    errors.append(f"Invalid paper ID format: {paper_id}")
                    continue

                # Get paper metadata
                paper = research_cli.kb_index.get_paper_by_id(paper_id)
                if not paper:
                    errors.append(f"Paper {paper_id} not found")
                    continue

                # Format as IEEE citation
                citation_text = research_cli.format_ieee_citation(paper, idx)
                results.append({"id": paper_id, "citation": citation_text, "number": idx})

            except Exception as error:
                errors.append(f"Error processing {paper_id}: {error}")

        # Display results
        if format == "json":
            output = {"citations": results, "errors": errors, "count": len(results)}
            print(json.dumps(output, indent=2))
        else:
            # Text format
            if results:
                print("\nIEEE Citations")
                print("=" * 50)
                for item in results:
                    print(f"\n{item['citation']}")

            if errors:
                print("\n⚠️ Errors encountered:", file=sys.stderr)
                for err_msg in errors:
                    print(f"  - {err_msg}", file=sys.stderr)

        # Log successful cite completion
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_success",
            command="cite",
            execution_time_ms=execution_time_ms,
            citations_generated=len(results),
            errors_encountered=len(errors),
        )

    except FileNotFoundError:
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_error",
            command="cite",
            execution_time_ms=execution_time_ms,
            error_type="FileNotFoundError",
            error_message="Knowledge base not found",
        )
        print(
            "Knowledge base not found. Run 'python src/build_kb.py --demo' to create one.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as error:
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_error",
            command="cite",
            execution_time_ms=execution_time_ms,
            error_type=type(error).__name__,
            error_message=str(error),
        )
        print(
            f"Citation generation failed: {error}. Try rebuilding with 'python src/build_kb.py'",
            file=sys.stderr,
        )
        sys.exit(1)


@cli.command(name="author")
@click.argument("author_name")
@click.option("--exact", is_flag=True, help="Exact match only")
def author_search(author_name: str, exact: bool) -> None:
    """Find all papers by a specific author.

    Search for papers authored by a specific person. Supports partial
    name matching by default, or exact matching with --exact flag.

    \b
    Examples:
      python src/cli.py author "Smith"                  # All papers by Smith
      python src/cli.py author "John Smith"             # Specific author
      python src/cli.py author "Zhang" --exact          # Exact match only
      python src/cli.py author "Lee"                    # Partial match

    Note: Author search is case-insensitive for partial matches.
    Results are sorted by year (most recent first).
    """
    try:
        metadata_path = Path("kb_data/metadata.json")
        with metadata_path.open(encoding="utf-8") as f:
            metadata = json.load(f)
            papers = metadata["papers"]

        matches = []
        author_lower = author_name.lower()

        for paper in papers:
            authors = paper.get("authors", [])

            if exact:
                # Exact match
                if author_name in authors:
                    matches.append(paper)
            # Partial match (case-insensitive)
            elif any(author_lower in auth.lower() for auth in authors):
                matches.append(paper)

        # Display results
        print(f"\nFound {len(matches)} papers by '{author_name}':")
        print("=" * 50)

        # Sort by year (most recent first)
        for paper in sorted(matches, key=lambda p: p.get("year", 0), reverse=True):
            year = paper.get("year", "N/A")
            journal = paper.get("journal", "Unknown journal")

            # Study type marker
            study_type = paper.get("study_type", "study")
            marker = {
                "systematic_review": "⭐",
                "meta_analysis": "⭐",
                "rct": "●",
                "cohort": "◐",
                "case_control": "○",
                "cross_sectional": "◔",
                "case_report": "·",
                "study": "·",
            }.get(study_type, "·")

            print(f"\n{marker} [{paper['id']}] {paper['title']}")
            print(f"   Year: {year} | Journal: {journal[:50]}")

            # Show all authors for context
            authors_str = ", ".join(paper.get("authors", []))
            if len(authors_str) > 100:
                authors_str = authors_str[:97] + "..."
            print(f"   Authors: {authors_str}")

    except FileNotFoundError:
        print(
            "\n❌ Knowledge base not found.\n"
            "   Quick fix: python src/build_kb.py --demo\n"
            "   Full setup: python src/build_kb.py (requires Zotero)",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as error:
        print(
            f"\n❌ Failed to search by author: {error}",
            file=sys.stderr,
        )
        sys.exit(1)


@cli.command()
def info() -> None:
    """Show comprehensive knowledge base statistics and metadata.

    Display detailed information about the current knowledge base including:
    - Total number of papers and size on disk
    - Last update time and version
    - Index and paper file statistics
    - Enhanced quality score statistics and distribution
    - Visual quality indicator breakdown (🌟⭐●◐○·)
    - Sample of available papers with quality indicators

    \b
    Example:
      python src/cli.py info

    Use this to verify KB health and understand your paper collection quality.
    """
    start_time = time.time()

    # Log info command start
    _log_ux_event("command_start", command="info")

    try:
        knowledge_base_path = Path("kb_data")
        metadata_file_path = knowledge_base_path / "metadata.json"

        if not metadata_file_path.exists():
            print("Knowledge base not found. Run build_kb.py first.")
            sys.exit(1)

        with metadata_file_path.open(encoding="utf-8") as file:
            metadata = json.load(file)

        print("\nKnowledge Base Information")
        print("=" * 50)
        print(f"Total papers: {metadata['total_papers']}")
        print(f"Last updated: {metadata.get('last_updated', 'Unknown')}")
        print(f"Version: {metadata.get('version', 'Unknown')}")
        print(f"Location: {knowledge_base_path.absolute()}")

        index_file_path = knowledge_base_path / "index.faiss"
        if index_file_path.exists():
            index_size_mb = index_file_path.stat().st_size / (1024 * 1024)
            print(f"Index size: {index_size_mb:.1f} MB")

        papers_path = knowledge_base_path / "papers"
        if papers_path.exists():
            paper_files = list(papers_path.glob("*.md"))
            paper_count = len(paper_files)
            total_size_bytes = sum(paper_file.stat().st_size for paper_file in paper_files)
            papers_size_mb = total_size_bytes / (1024 * 1024)
            print(f"Papers: {paper_count} files, {papers_size_mb:.1f} MB")

        # Show enhanced quality statistics if available
        try:
            from .cli_kb_index import KnowledgeBaseIndex
        except ImportError:
            from cli_kb_index import KnowledgeBaseIndex
            
        try:
            kb_index = KnowledgeBaseIndex(str(knowledge_base_path))
            enhanced_stats = kb_index.stats()
            
            # Display quality statistics if papers have quality scores
            if "quality_stats" in enhanced_stats and enhanced_stats["quality_stats"].get("papers_with_quality", 0) > 0:
                quality_stats = enhanced_stats["quality_stats"]
                print("\nEnhanced Quality Scoring:")
                print(f"  Average quality: {quality_stats['average_quality']:.1f}/100")
                print(f"  Highest quality: {quality_stats['highest_quality']}/100")
                print(f"  Lowest quality: {quality_stats['lowest_quality']}/100")
                
                # Display quality distribution
                if "quality_distribution" in enhanced_stats:
                    distribution = enhanced_stats["quality_distribution"]
                    print("\nQuality Distribution:")
                    print(f"  🌟 Excellent (85+): {distribution['excellent']} papers")
                    print(f"  ⭐ Very Good (70-84): {distribution['very_good']} papers")
                    print(f"  ● Good (60-69): {distribution['good']} papers")
                    print(f"  ◐ Moderate (45-59): {distribution['moderate']} papers")
                    print(f"  ○ Low (30-44): {distribution['low']} papers")
                    print(f"  · Very Low (0-29): {distribution['very_low']} papers")
        except (FileNotFoundError, KeyError, ImportError):
            # If enhanced stats aren't available, continue with basic info
            pass

        print("\nSample papers:")
        for paper in metadata["papers"][:5]:
            # Show quality indicator if available
            quality = paper.get("quality_score", 0)
            if quality > 0:
                indicator = format_quality_indicator(quality)
                print(f"  - [{paper['id']}] {indicator} {paper['title'][:60]}... ({quality}/100)")
            else:
                print(f"  - [{paper['id']}] {paper['title'][:60]}...")

        # Log successful info completion
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_success",
            command="info",
            execution_time_ms=execution_time_ms,
            total_papers=metadata.get("total_papers", 0),
        )

    except Exception as error:
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_error",
            command="info",
            execution_time_ms=execution_time_ms,
            error_type=type(error).__name__,
            error_message=str(error),
        )
        print(
            f"Failed to get knowledge base info: {error}. Run 'python src/build_kb.py --demo' to create one.",
            file=sys.stderr,
        )
        sys.exit(1)


@cli.command()
@click.argument("query_text")
@click.option(
    "--top-k",
    "-k",
    default=DEFAULT_SMART_SEARCH_RESULTS,
    help=f"Number of papers to retrieve (default: {DEFAULT_SMART_SEARCH_RESULTS})",
)
@click.option(
    "--max-tokens",
    default=DEFAULT_MAX_TOKENS,
    help=f"Max tokens to load (default: {DEFAULT_MAX_TOKENS}, ~40k chars)",
)
@click.option(
    "--sections",
    "-s",
    multiple=True,
    type=click.Choice(["abstract", "introduction", "methods", "results", "discussion", "conclusion"]),
    help="Sections to prioritize (default: abstract, introduction, conclusion)",
)
def smart_search(query_text: str, top_k: int, max_tokens: int, sections: tuple[str, ...]) -> None:
    """Smart search with automatic section chunking for large result sets.

    Intelligently handles large numbers of papers by chunking them into
    sections (Introduction, Methods, Results) for better readability.
    Ideal for comprehensive literature reviews.

    \b
    Examples:
      python src/cli.py smart-search "digital health" -k 30  # Auto-chunks
      python src/cli.py smart-search "AI" -k 50 --max-tokens 20000
      python src/cli.py smart-search "cancer" --sections results conclusion
      python src/cli.py smart-search "methods" -k 40  # Prioritizes methods

    \b
    Features:
      - Automatically chunks results >20 papers into logical sections
      - Groups papers by relevance and topic similarity
      - Outputs results as JSON to stdout for processing
      - Intelligently selects sections based on query terms
    """
    start_time = time.time()

    # Log smart_search command start
    _log_ux_event(
        "command_start",
        command="smart_search",
        query_length=len(query_text),
        top_k=top_k,
        max_tokens=max_tokens,
        has_sections_filter=len(sections) > 0,
        sections_requested=list(sections),
    )

    try:
        research_cli = ResearchCLI()

        # Search for papers
        search_results = research_cli.search(query_text, top_k)

        if not search_results:
            print("No papers found matching query")
            return

        # Determine section priorities based on query
        query_lower = query_text.lower()
        if not sections:
            if any(word in query_lower for word in ["method", "how", "approach", "technique"]):
                sections = ("methods", "abstract")
            elif any(word in query_lower for word in ["result", "outcome", "finding", "effect"]):
                sections = ("results", "conclusion", "abstract")
            elif any(word in query_lower for word in ["review", "systematic", "meta"]):
                sections = ("abstract", "conclusion", "discussion")
            else:
                sections = ("abstract", "introduction", "conclusion")

        print(f"\n🔍 Smart search for: '{query_text}'")
        print(f"📚 Found {len(search_results)} papers")
        print(f"📄 Prioritizing sections: {', '.join(sections)}")
        print("=" * 50)

        # Load sections with smart chunking
        max_chars = max_tokens * 4  # Rough token to char conversion
        loaded_papers = []
        total_chars = 0
        sections_index_path = Path("kb_data") / "sections_index.json"

        if sections_index_path.exists():
            with open(sections_index_path) as f:
                sections_index = json.load(f)
        else:
            sections_index = {}

        for _idx, dist, paper in search_results:
            paper_id = paper["id"]
            paper_loaded = False

            # Try to load prioritized sections
            if paper_id in sections_index:
                paper_sections = sections_index[paper_id]
                for section in sections:
                    if section in paper_sections:
                        section_text = paper_sections[section]
                        if section_text and total_chars + len(section_text) < max_chars:
                            loaded_papers.append(
                                {
                                    "id": paper_id,
                                    "title": paper["title"],
                                    "year": paper.get("year", ""),
                                    "section": section,
                                    "text": section_text[:5000],  # Cap section length
                                    "relevance": 1 / (1 + dist),
                                }
                            )
                            total_chars += len(section_text)
                            paper_loaded = True
                            break

            # Fallback to abstract from metadata if no sections loaded
            if not paper_loaded and paper.get("abstract"):
                abstract = paper["abstract"]
                if total_chars + len(abstract) < max_chars:
                    loaded_papers.append(
                        {
                            "id": paper_id,
                            "title": paper["title"],
                            "year": paper.get("year", ""),
                            "section": "abstract",
                            "text": abstract,
                            "relevance": 1 / (1 + dist),
                        }
                    )
                    total_chars += len(abstract)
                    paper_loaded = True

            # Stop if we've hit the limit
            if total_chars >= max_chars * 0.9:
                break

        # Display results
        print(
            f"\n✅ Loaded {len(loaded_papers)} papers ({total_chars:,} chars, ~{total_chars // 4:,} tokens)"
        )
        print("\nPapers loaded:")

        for i, paper_data in enumerate(loaded_papers, 1):
            print(f"\n{i}. [{paper_data['id']}] {paper_data['title'][:60]}...")
            print(
                f"   Year: {paper_data['year']} | Section: {paper_data['section']} | Relevance: {paper_data['relevance']:.2f}"
            )

            # Show preview of text
            preview = (
                paper_data["text"][:200] + "..." if len(paper_data["text"]) > 200 else paper_data["text"]
            )
            print(f"   Preview: {preview}")

        # Output results as JSON to stdout for processing
        output_data = {
            "query": query_text,
            "sections_priority": list(sections),
            "papers_found": len(search_results),
            "papers_loaded": len(loaded_papers),
            "total_chars": total_chars,
            "papers": loaded_papers,
        }

        print("\n" + json.dumps(output_data, indent=2))

        # Log successful smart_search completion
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_success",
            command="smart_search",
            execution_time_ms=execution_time_ms,
            papers_found=len(search_results),
            papers_loaded=len(loaded_papers),
            total_chars=total_chars,
        )

    except FileNotFoundError:
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_error",
            command="smart_search",
            execution_time_ms=execution_time_ms,
            error_type="FileNotFoundError",
            error_message="Knowledge base not found",
        )
        print(
            "\n❌ Knowledge base not found.\n"
            "   Quick fix: python src/build_kb.py --demo\n"
            "   Full setup: python src/build_kb.py (requires Zotero)",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as error:
        execution_time_ms = int((time.time() - start_time) * 1000)
        _log_ux_event(
            "command_error",
            command="smart_search",
            execution_time_ms=execution_time_ms,
            error_type=type(error).__name__,
            error_message=str(error),
        )
        print(f"\n❌ Smart search failed: {error}", file=sys.stderr)
        sys.exit(1)


@cli.command()
def diagnose() -> None:
    """Run comprehensive health checks on the knowledge base.

    Performs diagnostic tests to verify KB integrity:
    - Checks all required files exist
    - Validates metadata structure
    - Verifies FAISS index consistency
    - Tests version compatibility (v4.0)
    - Checks for sequential paper IDs
    - Reports total paper count

    \b
    Example:
      python src/cli.py diagnose

    Run this if you experience search errors or unexpected behavior.
    Returns detailed report with any issues found and recommendations.
    """
    kb_path = Path("kb_data")

    checks = [
        ("KB exists", kb_path.exists()),
        ("Metadata present", (kb_path / "metadata.json").exists()),
        ("Index present", (kb_path / "index.faiss").exists()),
        ("Papers directory", (kb_path / "papers").exists()),
    ]

    if (kb_path / "metadata.json").exists():
        with open(kb_path / "metadata.json") as f:
            meta = json.load(f)
            checks.append(("Version 4.0", meta.get("version") == "4.0"))
            checks.append((f"Papers: {meta['total_papers']}", True))

            # Check for sequential IDs
            paper_ids = sorted([p["id"] for p in meta["papers"]])
            expected_ids = [f"{i:04d}" for i in range(1, len(meta["papers"]) + 1)]
            sequential = paper_ids == expected_ids
            if not sequential:
                # Count gaps
                gaps = []
                for i in range(1, len(meta["papers"]) + 1):
                    if f"{i:04d}" not in paper_ids:
                        gaps.append(f"{i:04d}")
                checks.append((f"Sequential IDs (gaps: {len(gaps)})", False))
            else:
                checks.append(("Sequential IDs", True))

    print("\nKnowledge Base Diagnostics")
    print("=" * 50)
    for label, passed in checks:
        print(f"{'✓' if passed else '✗'} {label}")

    if not all(check[1] for check in checks[:4]):
        print("\n⚠️  Knowledge base not found or incomplete")
        print("   Run: python src/build_kb.py")
    elif checks[4][1] if len(checks) > 4 else False:
        # Check if we have ID gaps warning
        has_id_gaps = any("Sequential IDs" in check[0] and not check[1] for check in checks)
        if has_id_gaps:
            print("\n✅ Knowledge base is healthy")
            print("   Note: ID gaps are normal when papers are deleted")
        else:
            print("\n✅ Knowledge base is healthy")
    else:
        print("\n⚠️  Knowledge base version mismatch")
        print("   Run: python src/build_kb.py --rebuild")


@cli.command()
@click.argument("input", default="-", type=str)
@click.option(
    "--preset", type=click.Choice(["research", "review", "author-scan"]), help="Use workflow preset"
)
@click.option("--output", type=click.Choice(["json", "text"]), default="json", help="Output format")
def batch(input: str, preset: str | None, output: str) -> None:
    """Execute batch commands for efficient multi-operation workflows.

    Supports both custom command batches and preset workflows for common tasks.
    This dramatically improves performance by loading the model only once.

    \b
    INPUT FORMATS:
      - JSON file: python src/cli.py batch commands.json
      - Stdin: echo '[{"cmd":"search","query":"test"}]' | python src/cli.py batch -
      - Preset: python src/cli.py batch --preset research "diabetes"

    \b
    PRESET WORKFLOWS:
      research: Comprehensive topic analysis (multiple searches + top papers)
      review: Focus on systematic reviews and meta-analyses
      author-scan: Get all papers by author with abstracts

    \b
    COMMAND STRUCTURE:
      {"cmd": "search", "query": "topic", "k": 10, "show_quality": true}
      {"cmd": "get", "id": "0001", "sections": ["abstract", "methods"]}
      {"cmd": "smart-search", "query": "topic", "k": 30}
      {"cmd": "cite", "ids": ["0001", "0002", "0003"]}
      {"cmd": "author", "name": "Smith J", "exact": true}

    \b
    META-COMMANDS:
      {"cmd": "auto-get-top", "limit": 10, "min_quality": 70}
      {"cmd": "filter", "min_quality": 80}
      {"cmd": "merge"}  # Merges and deduplicates all previous search results

    \b
    Examples:
      # Research preset for comprehensive analysis
      python src/cli.py batch --preset research "diabetes management"

      # Custom batch from file
      python src/cli.py batch my_commands.json

      # Pipe commands from another process
      echo '[{"cmd":"search","query":"AI healthcare","k":20}]' | python src/cli.py batch -
    """
    try:
        # Initialize ResearchCLI once
        research_cli = ResearchCLI()

        # Handle preset workflows
        if preset:
            if input == "-":
                click.echo("Error: Please provide a topic when using presets", err=True)
                sys.exit(1)
            commands = _generate_preset_commands(preset, input)
        elif input == "-":
            # Load commands from stdin
            commands = json.load(sys.stdin)
        else:
            # Load commands from file
            with open(input) as f:
                commands = json.load(f)

        # Execute batch with shared context
        results = _execute_batch(research_cli, commands)

        # Output results
        if output == "json":
            print(json.dumps(results, indent=2))
        else:
            _format_batch_text(results)

    except FileNotFoundError:
        click.echo(f"Error: File '{input}' not found", err=True)
        sys.exit(1)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON - {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _generate_preset_commands(preset_name: str, topic: str) -> list[dict[str, Any]]:
    """Generate batch commands for workflow presets."""

    presets: dict[str, list[dict[str, Any]]] = {
        "research": [
            {"cmd": "search", "query": topic, "k": 30, "show_quality": True},
            {"cmd": "search", "query": f"{topic} systematic review", "k": 15, "show_quality": True},
            {"cmd": "search", "query": f"{topic} meta-analysis", "k": 15, "show_quality": True},
            {"cmd": "search", "query": f"mobile health {topic}", "k": 20},
            {"cmd": "search", "query": f"digital {topic}", "k": 20},
            {"cmd": "merge"},  # Merge all search results
            {"cmd": "filter", "min_quality": 70},  # Keep high quality papers
            {"cmd": "auto-get-top", "limit": 10},  # Get top 10 papers
        ],
        "review": [
            {"cmd": "search", "query": f"{topic} systematic review", "k": 25, "show_quality": True},
            {"cmd": "search", "query": f"{topic} meta-analysis", "k": 25, "show_quality": True},
            {"cmd": "merge"},
            {"cmd": "filter", "min_quality": 80},
            {"cmd": "auto-get-top", "limit": 5},
        ],
        "author-scan": [
            {"cmd": "author", "name": topic, "exact": True},
            {"cmd": "auto-get-all", "sections": ["abstract"]},
        ],
    }

    if preset_name not in presets:
        raise ValueError(f"Unknown preset: {preset_name}")

    return presets[preset_name]


def _execute_batch(research_cli: ResearchCLI, commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Execute batch commands with shared context."""

    results: list[dict[str, Any]] = []
    context: dict[str, Any] = {
        "searches": [],  # All search results
        "papers": {},  # Retrieved papers by ID
        "last_result": None,  # Last command result
    }

    for i, cmd in enumerate(commands):
        try:
            cmd_type = cmd.get("cmd")

            if cmd_type == "search":
                # Standard search
                result = research_cli.search(
                    query_text=cmd["query"],
                    top_k=cmd.get("k", 10),
                    min_year=cmd.get("min_year"),
                    study_types=cmd.get("study_types"),
                )

                # Format results
                formatted = []
                for idx, score, paper in result:
                    paper_data = {
                        "id": paper["id"],
                        "title": paper["title"],
                        "authors": paper.get("authors", []),
                        "year": paper.get("year"),
                        "score": float(score),
                        "quality": paper.get("quality_score", 0),
                    }
                    if cmd.get("show_quality"):
                        paper_data["study_type"] = paper.get("study_type", "UNKNOWN")
                    formatted.append(paper_data)

                context["searches"].append(formatted)
                context["last_result"] = formatted
                results.append(
                    {
                        "success": True,
                        "command": cmd,
                        "type": "search",
                        "count": len(formatted),
                        "data": formatted,
                    }
                )

            elif cmd_type == "smart-search":
                # Smart search with chunking
                result = research_cli.search(query_text=cmd["query"], top_k=cmd.get("k", 30))

                formatted = []
                for idx, score, paper in result:
                    formatted.append(
                        {
                            "id": paper["id"],
                            "title": paper["title"],
                            "score": float(score),
                            "quality": paper.get("quality_score", 0),
                        }
                    )

                context["searches"].append(formatted)
                context["last_result"] = formatted
                results.append(
                    {
                        "success": True,
                        "command": cmd,
                        "type": "smart-search",
                        "count": len(formatted),
                        "data": formatted,
                    }
                )

            elif cmd_type == "get":
                # Get specific paper
                paper_id = cmd["id"]
                sections = cmd.get("sections")

                # Get paper metadata
                paper = None
                for p in research_cli.metadata["papers"]:
                    if p["id"] == paper_id:
                        paper = p
                        break

                if not paper:
                    raise ValueError(f"Paper {paper_id} not found")

                # Get content if sections requested
                if sections:
                    paper_path = Path(KB_DATA_PATH) / "papers" / f"paper_{paper_id}.md"
                    if paper_path.exists():
                        with open(paper_path) as f:
                            content = f.read()
                        paper["content"] = content

                context["papers"][paper_id] = paper
                context["last_result"] = paper
                results.append({"success": True, "command": cmd, "type": "get", "data": paper})

            elif cmd_type == "cite":
                # Generate citations
                result = research_cli.search(query_text=cmd["query"], top_k=cmd.get("k", 10))

                citations = []
                for i, (idx, score, paper) in enumerate(result, 1):
                    citation = research_cli.format_ieee_citation(paper, i)
                    citations.append(citation)

                context["last_result"] = citations
                results.append({"success": True, "command": cmd, "type": "cite", "data": citations})

            elif cmd_type == "author":
                # Author search
                author_name = cmd["name"]
                exact = cmd.get("exact", False)

                matches = []
                for paper in research_cli.metadata["papers"]:
                    authors = paper.get("authors", [])
                    if exact:
                        if author_name in authors:
                            matches.append(paper)
                    else:
                        for author in authors:
                            if author_name.lower() in author.lower():
                                matches.append(paper)
                                break

                context["last_result"] = matches
                results.append(
                    {
                        "success": True,
                        "command": cmd,
                        "type": "author",
                        "count": len(matches),
                        "data": matches,
                    }
                )

            elif cmd_type == "merge":
                # Meta-command: Merge all search results
                merged: dict[str, dict[str, Any]] = {}
                for search_results in context["searches"]:
                    for paper in search_results:
                        paper_id = paper["id"]
                        if paper_id not in merged or paper["score"] > merged[paper_id]["score"]:
                            merged[paper_id] = paper

                merged_list = list(merged.values())
                merged_list.sort(key=lambda x: x.get("quality", 0), reverse=True)

                context["last_result"] = merged_list
                results.append(
                    {
                        "success": True,
                        "command": cmd,
                        "type": "merge",
                        "count": len(merged_list),
                        "data": merged_list,
                    }
                )

            elif cmd_type == "filter":
                # Meta-command: Filter last results
                if context["last_result"]:
                    min_quality = cmd.get("min_quality", 0)
                    min_year = cmd.get("min_year")

                    filtered = []
                    for item in context["last_result"]:
                        if (
                            isinstance(item, dict)
                            and item.get("quality", 0) >= min_quality
                            and (not min_year or item.get("year", 0) >= min_year)
                        ):
                            filtered.append(item)

                    context["last_result"] = filtered
                    results.append(
                        {
                            "success": True,
                            "command": cmd,
                            "type": "filter",
                            "count": len(filtered),
                            "data": filtered,
                        }
                    )
                else:
                    results.append({"success": False, "command": cmd, "error": "No results to filter"})

            elif cmd_type == "auto-get-top":
                # Meta-command: Get top papers from last results
                if context["last_result"]:
                    limit = cmd.get("limit", 10)
                    min_quality = cmd.get("min_quality", 0)
                    sections = cmd.get("sections", ["abstract"])

                    # Sort by quality
                    papers = context["last_result"]
                    if isinstance(papers, list) and papers and isinstance(papers[0], dict):
                        sorted_papers = sorted(papers, key=lambda x: x.get("quality", 0), reverse=True)

                        # Filter by min quality and limit
                        top_papers = []
                        for paper in sorted_papers:
                            if paper.get("quality", 0) >= min_quality:
                                top_papers.append(paper)
                                if len(top_papers) >= limit:
                                    break

                        # Fetch full paper data
                        fetched = []
                        for paper in top_papers:
                            paper_id = paper["id"]

                            # Get full metadata
                            full_paper = None
                            for p in research_cli.metadata["papers"]:
                                if p["id"] == paper_id:
                                    full_paper = p.copy()
                                    full_paper["search_score"] = paper.get("score", 0)
                                    break

                            if full_paper and sections:
                                paper_path = Path(KB_DATA_PATH) / "papers" / f"paper_{paper_id}.md"
                                if paper_path.exists():
                                    with open(paper_path) as f:
                                        full_paper["content"] = f.read()

                            if full_paper:
                                fetched.append(full_paper)
                                context["papers"][paper_id] = full_paper

                        context["last_result"] = fetched
                        results.append(
                            {
                                "success": True,
                                "command": cmd,
                                "type": "auto-get-top",
                                "count": len(fetched),
                                "data": fetched,
                            }
                        )
                    else:
                        results.append(
                            {"success": False, "command": cmd, "error": "No valid results to process"}
                        )
                else:
                    results.append(
                        {"success": False, "command": cmd, "error": "No results to get papers from"}
                    )

            elif cmd_type == "auto-get-all":
                # Meta-command: Get all papers from last author search
                if context["last_result"] and isinstance(context["last_result"], list):
                    sections = cmd.get("sections", ["abstract"])

                    fetched = []
                    for paper in context["last_result"]:
                        if isinstance(paper, dict):
                            paper_id = paper["id"]
                            if sections:
                                paper_path = Path(KB_DATA_PATH) / "papers" / f"paper_{paper_id}.md"
                                if paper_path.exists():
                                    with open(paper_path) as f:
                                        paper["content"] = f.read()
                            fetched.append(paper)
                            context["papers"][paper_id] = paper

                    context["last_result"] = fetched
                    results.append(
                        {
                            "success": True,
                            "command": cmd,
                            "type": "auto-get-all",
                            "count": len(fetched),
                            "data": fetched,
                        }
                    )
                else:
                    results.append(
                        {"success": False, "command": cmd, "error": "No results to get papers from"}
                    )

            else:
                results.append({"success": False, "command": cmd, "error": f"Unknown command: {cmd_type}"})

        except Exception as e:
            results.append({"success": False, "command": cmd, "error": str(e)})

    return results


def _format_batch_text(results: list[dict[str, Any]]) -> None:
    """Format batch results as human-readable text."""

    for i, result in enumerate(results, 1):
        if result["success"]:
            cmd_type = result.get("type", "unknown")

            print(f"\n{'='*60}")
            print(f"Command {i}: {cmd_type}")
            print(f"{'='*60}")

            if cmd_type in ["search", "smart-search", "merge", "filter"]:
                papers = result.get("data", [])
                print(f"Found {result.get('count', 0)} papers\n")

                for j, paper in enumerate(papers[:10], 1):  # Show top 10
                    quality = paper.get("quality", 0)
                    quality_marker = "⭐ " if quality >= 80 else ""
                    print(f"{j}. {quality_marker}[{paper['id']}] {paper['title']}")
                    if paper.get("authors"):
                        authors = paper["authors"][:3]
                        if len(paper["authors"]) > 3:
                            authors.append("et al.")
                        print(f"   {', '.join(authors)} ({paper.get('year', 'N/A')})")
                    if paper.get("study_type"):
                        print(f"   Type: {paper['study_type']} | Quality: {quality}")
                    print(f"   Score: {paper.get('score', 0):.3f}")

            elif cmd_type == "get":
                paper = result.get("data", {})
                print(f"Paper {paper.get('id', 'N/A')}: {paper.get('title', 'N/A')}")
                if paper.get("content"):
                    print("\nContent retrieved (use JSON output to see full text)")

            elif cmd_type == "cite":
                citations = result.get("data", [])
                for citation in citations:
                    print(citation)

            elif cmd_type == "author":
                papers = result.get("data", [])
                print(f"Found {result.get('count', 0)} papers by author\n")
                for paper in papers:
                    print(f"- [{paper['id']}] {paper['title']} ({paper.get('year', 'N/A')})")

            elif cmd_type in ["auto-get-top", "auto-get-all"]:
                papers = result.get("data", [])
                print(f"Retrieved {result.get('count', 0)} papers\n")
                for paper in papers:
                    print(f"- [{paper['id']}] {paper['title']}")
                    if paper.get("content"):
                        print("  (content retrieved)")

        else:
            print(f"\n❌ Command {i} failed: {result.get('error', 'Unknown error')}")
            print(f"   Command: {result.get('command', {})}")


def generate_ieee_citation(paper_metadata: dict[str, Any], citation_number: int) -> str:
    """Generate IEEE-style citation for a paper.

    Standalone function for compatibility with tests.

    Args:
        paper_metadata: Paper metadata dictionary
        citation_number: Citation number for reference

    Returns:
        Formatted IEEE citation string
    """
    citation_text = f"[{citation_number}] "

    if paper_metadata.get("authors"):
        if len(paper_metadata["authors"]) <= 3:
            citation_text += ", ".join(paper_metadata["authors"])
        else:
            citation_text += f"{paper_metadata['authors'][0]} et al."
        citation_text += ", "

    citation_text += f'"{paper_metadata["title"]}", '

    if paper_metadata.get("journal"):
        citation_text += f"{paper_metadata['journal']}, "

    if paper_metadata.get("volume"):
        citation_text += f"vol. {paper_metadata['volume']}, "

    if paper_metadata.get("issue"):
        citation_text += f"no. {paper_metadata['issue']}, "

    if paper_metadata.get("pages"):
        citation_text += f"pp. {paper_metadata['pages']}, "

    if paper_metadata.get("year"):
        citation_text += f"{paper_metadata['year']}."

    return citation_text


if __name__ == "__main__":
    cli()
