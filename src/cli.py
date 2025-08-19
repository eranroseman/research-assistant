#!/usr/bin/env python3
"""
CLI tool for searching and retrieving papers from the knowledge base
Simplified version 4.0 - removed complex features for maintainability
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

import click
import faiss

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Paths
DEFAULT_KB_PATH = "kb_data"

# Search Defaults
DEFAULT_SEARCH_RESULTS = 10
DEFAULT_CITATION_COUNT = 5
DEFAULT_SMART_SEARCH_RESULTS = 20
DEFAULT_MAX_TOKENS = 10000  # ~40k characters

# Quality Scoring Constants
QUALITY_BASE_SCORE = 50

# Study Type Scores
SCORE_SYSTEMATIC_REVIEW = 35
SCORE_META_ANALYSIS = 35
SCORE_RCT = 25
SCORE_COHORT = 15
SCORE_CASE_CONTROL = 10
SCORE_CROSS_SECTIONAL = 5
SCORE_CASE_REPORT = 0

# Sample Size Thresholds and Bonuses
SAMPLE_SIZE_LARGE_THRESHOLD = 1000
SAMPLE_SIZE_MEDIUM_THRESHOLD = 500
SAMPLE_SIZE_SMALL_THRESHOLD = 100
BONUS_LARGE_SAMPLE = 10
BONUS_MEDIUM_SAMPLE = 5

# Recency Bonuses
YEAR_VERY_RECENT = 2022
YEAR_RECENT = 2020
BONUS_VERY_RECENT = 10
BONUS_RECENT = 5

# Other Bonuses
BONUS_FULL_TEXT = 5

# Display Configuration
MAX_QUALITY_SCORE = 100
PAPER_ID_FORMAT = r"^\d{4}$"  # Regex for validation
PAPER_ID_DIGITS = 4

# Version
KB_VERSION = "4.0"


def estimate_paper_quality(paper: dict) -> tuple[int, str]:
    """Estimate paper quality based on metadata (0-100 score)."""
    score = QUALITY_BASE_SCORE  # Base score
    factors = []

    # Study type hierarchy (most important factor)
    study_type = paper.get("study_type", "unknown")
    study_scores = {
        "systematic_review": SCORE_SYSTEMATIC_REVIEW,
        "meta_analysis": SCORE_META_ANALYSIS,
        "rct": SCORE_RCT,
        "cohort": SCORE_COHORT,
        "case_control": SCORE_CASE_CONTROL,
        "cross_sectional": SCORE_CROSS_SECTIONAL,
        "case_report": SCORE_CASE_REPORT,
    }

    if study_type in study_scores:
        score += study_scores[study_type]
        factors.append(study_type.replace("_", " "))

    # Sample size bonus (for applicable studies)
    sample_size = paper.get("sample_size")
    if sample_size and sample_size > 0:
        if sample_size > SAMPLE_SIZE_LARGE_THRESHOLD and study_type in ["rct", "cohort"]:
            score += BONUS_LARGE_SAMPLE
            factors.append(f"n={sample_size}")
        elif sample_size > SAMPLE_SIZE_MEDIUM_THRESHOLD:
            score += BONUS_MEDIUM_SAMPLE
            factors.append(f"n={sample_size}")
        elif sample_size > SAMPLE_SIZE_SMALL_THRESHOLD:
            factors.append(f"n={sample_size}")

    # Recency bonus
    year = paper.get("year")
    if year and year > 0:
        if year >= 2022:
            score += 10
            factors.append(str(year))
        elif year >= 2020:
            score += 5
            factors.append(str(year))
        else:
            factors.append(str(year))

    # Full text availability
    if paper.get("has_full_text"):
        score += 5
        factors.append("full-text")

    # Create explanation
    explanation = " | ".join(factors) if factors else "standard"

    return min(score, 100), explanation


class ResearchCLI:
    def __init__(self, knowledge_base_path: str = "kb_data"):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.papers_path = self.knowledge_base_path / "papers"
        self.index_file_path = self.knowledge_base_path / "index.faiss"
        self.metadata_file_path = self.knowledge_base_path / "metadata.json"

        if not self.knowledge_base_path.exists():
            raise FileNotFoundError(
                f"Knowledge base not found at {knowledge_base_path}. Run build_kb.py first."
            )

        with open(self.metadata_file_path, encoding="utf-8") as f:
            self.metadata = json.load(f)

        # Check version compatibility
        if self.metadata.get("version") != KB_VERSION:
            print(
                f"\nERROR: Knowledge base version incompatible\n"
                f"  Current version: v{self.metadata.get('version', '3.x')}\n"
                f"  Required version: v{KB_VERSION}\n"
                f"\n  How to fix:\n"
                f"  Run: python src/build_kb.py --rebuild\n"
            )
            sys.exit(1)

        # Load SPECTER model for search
        self.embedding_model = self._load_embedding_model()
        self.search_index = faiss.read_index(str(self.index_file_path))

    def search(
        self,
        query_text: str,
        top_k: int = 10,
        min_year: int | None = None,
        study_types: list | None = None,
    ) -> list[tuple[int, float, dict]]:
        """Search for relevant papers using semantic similarity with optional filters."""
        query_embedding = self.embedding_model.encode([query_text])

        # Search more than needed to account for filtering
        available_papers = len(self.metadata["papers"])
        search_k = min(top_k * 3, available_papers)  # Search 3x to allow for filtering

        distances, indices = self.search_index.search(query_embedding.astype("float32"), search_k)

        results = []
        for idx, dist in zip(indices[0], distances[0], strict=False):
            if idx < len(self.metadata["papers"]) and idx != -1:  # -1 is returned for invalid indices
                paper = self.metadata["papers"][idx]

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
        """Retrieve full text of a paper by ID with validation."""

        # Validate paper_id format (4 digits only)
        if not re.match(PAPER_ID_FORMAT, paper_id):
            raise ValueError(f"Invalid paper ID format: {paper_id}. Must be 4 digits (e.g., 0001, 0234)")

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
            with open(paper_file_path, encoding="utf-8") as f:
                return f.read()
        else:
            return f"Paper {paper_id} not found. Valid format: 4 digits (e.g., 0001)"

    def format_search_results(
        self,
        search_results: list[tuple[int, float, dict]],
        show_abstracts: bool = False,
    ) -> str:
        """Format search results for display with study type and sample size."""
        output = []

        # Define study type markers for visual hierarchy
        type_markers = {
            "systematic_review": "⭐",  # Best evidence
            "rct": "●",  # High quality
            "cohort": "◐",  # Good evidence
            "case_control": "○",  # Moderate evidence
            "cross_sectional": "◔",  # Lower evidence
            "case_report": "·",  # Case level
            "study": "·",  # Generic
        }

        for i, (_idx, dist, paper) in enumerate(search_results, 1):
            # Build header with study type marker
            year = paper.get("year", "????")
            study_type = paper.get("study_type", "study")
            marker = type_markers.get(study_type, "·")

            output.append(f"\n{i}. {marker} [{year}] {paper['title']}")

            # Build info line with study type and sample size
            type_str = study_type.upper().replace("_", " ")
            sample_str = f" (n={paper['sample_size']})" if paper.get("sample_size") else ""
            has_full = "✓" if paper.get("has_full_text") else "✗"
            relevance = 1 / (1 + dist)

            output.append(f"   Type: {type_str}{sample_str} | Full Text: {has_full} | Score: {relevance:.2f}")

            # Authors and journal
            if paper.get("authors"):
                first_author = paper["authors"][0].split()[-1] if paper["authors"] else "Unknown"
                journal = paper.get("journal", "Unknown journal")
                if len(paper["authors"]) > 1:
                    output.append(f"   {first_author} et al., {journal}")
                else:
                    output.append(f"   {first_author}, {journal}")

            if show_abstracts and paper.get("abstract"):
                abstract = (
                    paper["abstract"][:200] + "..." if len(paper["abstract"]) > 200 else paper["abstract"]
                )
                output.append(f"   {abstract}")

        return "\n".join(output)

    def _load_embedding_model(self) -> Any:
        """Load the SPECTER embedding model for scientific paper search."""
        print("Loading SPECTER model for search...")

        from sentence_transformers import SentenceTransformer

        return SentenceTransformer("sentence-transformers/allenai-specter")

    def format_ieee_citation(self, paper_metadata: dict, citation_number: int) -> str:
        """Format paper metadata as IEEE citation."""
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
    """Research Assistant CLI v4.0 - Search and analyze academic papers.

    \b
    Common commands:
      search      Search papers by topic with quality scores
      get         Retrieve full text of a specific paper
      info        Show knowledge base status
      cite        Generate IEEE citations

    \b
    Features:
      • SPECTER embeddings for semantic search
      • Quality scoring (0-100) based on study type and recency
      • Study type detection (RCTs, systematic reviews, etc.)
      • Smart incremental updates from Zotero

    \b
    Quick start:
      python src/cli.py info                    # Check KB status
      python src/cli.py search "diabetes"       # Search papers
      python src/cli.py get 0001                # Get full paper
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
@click.option("--quality-min", type=int, help="Minimum quality score (0-100)")
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
def search(
    query_text: str,
    top_k: int,
    verbose: bool,
    show_quality: bool,
    quality_min: int | None,
    output_json: bool,
    after: int | None,
    study_type: tuple[str, ...],
) -> None:
    """Search for relevant papers using SPECTER embeddings.

    \b
    Quality markers:
      ⭐ Excellent (80-100): Systematic reviews, meta-analyses
      ● Good (60-79): RCTs, recent high-quality studies
      ○ Moderate (40-59): Cohort studies, older papers
      · Lower (<40): Case reports, generic studies

    \b
    Examples:
      python src/cli.py search "diabetes"                    # Basic search
      python src/cli.py search "diabetes" --show-quality     # With scores
      python src/cli.py search "AI" --quality-min 70        # High quality only
      python src/cli.py search "COVID" --after 2020 --type rct  # Recent RCTs
    """
    try:
        research_cli = ResearchCLI()

        # Perform search
        study_types = list(study_type) if study_type else None
        search_k = top_k * 2 if quality_min else top_k
        search_results = research_cli.search(query_text, search_k, min_year=after, study_types=study_types)

        # Apply quality filtering if requested
        if quality_min or show_quality:
            enhanced_results = []
            for idx, dist, paper in search_results:
                quality, explanation = estimate_paper_quality(paper)

                # Filter by minimum quality
                if quality_min and quality < quality_min:
                    continue

                # Add quality info to paper
                paper["quality_score"] = quality
                paper["quality_explanation"] = explanation
                enhanced_results.append((idx, dist, paper))

            search_results = enhanced_results[:top_k]
        else:
            search_results = search_results[:top_k]

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

            # Custom formatting with quality scores
            if show_quality:
                for i, (_idx, dist, paper) in enumerate(search_results, 1):
                    quality = paper.get("quality_score", 0)
                    explanation = paper.get("quality_explanation", "")

                    # Quality-based marker
                    marker = "⭐" if quality >= 80 else "●" if quality >= 60 else "○"

                    print(f"\n{i}. {marker} [{paper.get('year', '????')}] {paper['title']}")
                    print(f"   Quality: {quality}/100 ({explanation})")

                    # Additional info
                    relevance = 1 / (1 + dist)
                    print(f"   Relevance: {relevance:.2f}")

                    if verbose and paper.get("abstract"):
                        abstract = (
                            paper["abstract"][:200] + "..."
                            if len(paper["abstract"]) > 200
                            else paper["abstract"]
                        )
                        print(f"   {abstract}")
            else:
                # Use existing formatting
                print(research_cli.format_search_results(search_results, verbose))

    except FileNotFoundError:
        print(
            "\n❌ Knowledge base not found.\n"
            "   Quick fix: python src/build_kb.py --demo\n"
            "   Full setup: python src/build_kb.py (requires Zotero)",
            file=sys.stderr,
        )
        sys.exit(1)
    except ImportError as e:
        print(
            f"\n❌ Missing dependency: {e}\n" "   Fix: pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(
            f"\n❌ Search failed: {e}\n"
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
def get(paper_id: str, output: str | None, sections: tuple[str, ...]) -> None:
    """Get full text of a paper by ID.

    Paper IDs are 4-digit numbers (e.g., 0001, 0234) shown in search results.
    """
    try:
        research_cli = ResearchCLI()

        # Handle section-specific retrieval
        if sections and "all" not in sections:
            # Load sections index
            sections_index_path = Path("kb_data") / "sections_index.json"
            if sections_index_path.exists():
                with open(sections_index_path) as f:
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

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Paper saved to {output}")
        else:
            print(content)

    except FileNotFoundError:
        print(
            "\n❌ Knowledge base not found.\n"
            "   Quick fix: python src/build_kb.py --demo\n"
            "   Full setup: python src/build_kb.py (requires Zotero)",
            file=sys.stderr,
        )
        sys.exit(1)
    except ValueError as e:
        print(
            f"\n❌ Invalid paper ID: {e}\n"
            "   Paper IDs must be exactly 4 digits (e.g., 0001, 0234, 1234)\n"
            "   Use 'python src/cli.py search <query>' to find paper IDs",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(
            f"\n❌ Failed to retrieve paper: {e}\n"
            "   Make sure the paper ID is correct (4 digits, e.g., 0001)\n"
            "   Check available papers: python src/cli.py info",
            file=sys.stderr,
        )
        sys.exit(1)


@cli.command()
@click.argument("query_text")
@click.option(
    "--top-k",
    "-k",
    default=DEFAULT_CITATION_COUNT,
    help=f"Number of citations to generate (default: {DEFAULT_CITATION_COUNT})",
)
def cite(query_text: str, top_k: int) -> None:
    """Generate IEEE-style citations for papers matching query."""
    try:
        research_cli = ResearchCLI()
        search_results = research_cli.search(query_text, top_k)

        print(f"\nIEEE Citations for: '{query_text}'")
        print("=" * 50)

        for i, (_idx, _dist, paper) in enumerate(search_results, 1):
            citation_text = research_cli.format_ieee_citation(paper, i)
            print(f"\n{citation_text}")

    except FileNotFoundError:
        print(
            "Knowledge base not found. Run 'python src/build_kb.py --demo' to create one.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(
            f"Citation generation failed: {e}. Try rebuilding with 'python src/build_kb.py'",
            file=sys.stderr,
        )
        sys.exit(1)


@cli.command()
def info() -> None:
    """Show information about the knowledge base."""
    try:
        knowledge_base_path = Path("kb_data")
        metadata_file_path = knowledge_base_path / "metadata.json"

        if not metadata_file_path.exists():
            print("Knowledge base not found. Run build_kb.py first.")
            sys.exit(1)

        with open(metadata_file_path, encoding="utf-8") as file:
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

        print("\nSample papers:")
        for paper in metadata["papers"][:5]:
            print(f"  - [{paper['id']}] {paper['title'][:60]}...")

    except Exception as e:
        print(
            f"Failed to get knowledge base info: {e}. Run 'python src/build_kb.py --demo' to create one.",
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
    """Smart search with automatic section chunking to handle 20+ papers.

    Automatically selects relevant sections based on query to maximize
    the number of papers that can be analyzed without context overflow.

    Examples:
        cli.py smart-search "diabetes treatment methods" -k 30
        cli.py smart-search "clinical outcomes" --sections results conclusion
    """
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
        print(f"\n✅ Loaded {len(loaded_papers)} papers ({total_chars:,} chars, ~{total_chars//4:,} tokens)")
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

        # Save to file for further processing
        output_file = Path("smart_search_results.json")
        with open(output_file, "w") as f:
            json.dump(
                {
                    "query": query_text,
                    "sections_priority": list(sections),
                    "papers_found": len(search_results),
                    "papers_loaded": len(loaded_papers),
                    "total_chars": total_chars,
                    "papers": loaded_papers,
                },
                f,
                indent=2,
            )

        print(f"\n💾 Results saved to {output_file}")
        print("   Use this file for further analysis without context overflow")

    except FileNotFoundError:
        print(
            "\n❌ Knowledge base not found.\n"
            "   Quick fix: python src/build_kb.py --demo\n"
            "   Full setup: python src/build_kb.py (requires Zotero)",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Smart search failed: {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
def diagnose() -> None:
    """Check knowledge base health and integrity.

    \b
    Performs comprehensive diagnostics:
      • Verifies KB exists and is complete
      • Checks version compatibility (v4.0)
      • Validates metadata and index files
      • Reports total paper count
      • Identifies any missing components

    \b
    Example:
      python src/cli.py diagnose

    \b
    Use this command if you encounter errors or want to verify
    your knowledge base is properly configured.
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

    print("\nKnowledge Base Diagnostics")
    print("=" * 50)
    for label, passed in checks:
        print(f"{'✓' if passed else '✗'} {label}")

    if not all(check[1] for check in checks[:4]):
        print("\n⚠️  Knowledge base not found or incomplete")
        print("   Run: python src/build_kb.py")
    elif checks[4][1] if len(checks) > 4 else False:
        print("\n✅ Knowledge base is healthy")
    else:
        print("\n⚠️  Knowledge base version mismatch")
        print("   Run: python src/build_kb.py --full")


if __name__ == "__main__":
    cli()
