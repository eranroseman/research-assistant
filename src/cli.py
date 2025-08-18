#!/usr/bin/env python3
"""
CLI tool for searching and retrieving papers from the knowledge base
Enhanced with SPECTER2 query preprocessing and quality scoring
"""

import json
import sys
from pathlib import Path

import click
import faiss

# SPECTER2 enhancement functions integrated directly


def detect_search_mode(query_text):
    """Detect search intent from query text."""
    query_lower = query_text.lower()

    # Question patterns
    if any(
        marker in query_lower
        for marker in ["?", "what ", "how ", "why ", "when ", "which "]
    ):
        return "question"

    # Similarity patterns
    if any(
        phrase in query_lower for phrase in ["similar to", "papers like", "related to"]
    ):
        return "similar"

    # Exploration patterns
    if any(
        word in query_lower for word in ["overview", "landscape", "trends", "review of"]
    ):
        return "explore"

    # Default to standard search
    return "standard"


def preprocess_query(query_text, mode="auto"):
    """Preprocess query based on search mode for better SPECTER2 results."""

    # Auto-detect mode if needed
    if mode == "auto":
        mode = detect_search_mode(query_text)

    # Apply mode-specific preprocessing
    if mode == "question":
        # Frame as Q&A for better embeddings
        enhanced_query = f"Question: {query_text} Research findings:"

    elif mode == "similar":
        # Repetition emphasizes key terms in SPECTER2
        enhanced_query = f"{query_text} {query_text}"

    elif mode == "explore":
        # Broader context for exploration
        enhanced_query = f"research overview: {query_text} studies analysis"

    else:
        # Standard search - no preprocessing
        enhanced_query = query_text

    return enhanced_query, mode


def estimate_paper_quality(paper):
    """Estimate paper quality based on metadata (0-100 score)."""
    score = 50  # Base score
    factors = []

    # Study type hierarchy (most important factor)
    study_type = paper.get("study_type", "unknown")
    study_scores = {
        "systematic_review": 35,
        "meta_analysis": 35,
        "rct": 25,
        "cohort": 15,
        "case_control": 10,
        "cross_sectional": 5,
        "case_report": 0,
    }

    if study_type in study_scores:
        score += study_scores[study_type]
        factors.append(study_type.replace("_", " "))

    # Sample size bonus (for applicable studies)
    sample_size = paper.get("sample_size")
    if sample_size and sample_size > 0:
        if sample_size > 1000 and study_type in ["rct", "cohort"]:
            score += 10
            factors.append(f"n={sample_size}")
        elif sample_size > 500:
            score += 5
            factors.append(f"n={sample_size}")
        elif sample_size > 100:
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

        # Load SPECTER2 model for search
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

        distances, indices = self.search_index.search(
            query_embedding.astype("float32"), search_k
        )

        results = []
        for idx, dist in zip(indices[0], distances[0], strict=False):
            if (
                idx < len(self.metadata["papers"]) and idx != -1
            ):  # -1 is returned for invalid indices
                paper = self.metadata["papers"][idx]

                # Apply filters
                if min_year and paper.get("year", 0) < min_year:
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
        import re

        # Validate paper_id format (4 digits only)
        if not re.match(r"^[0-9]{4}$", paper_id):
            raise ValueError(
                f"Invalid paper ID format: {paper_id}. Must be 4 digits (e.g., 0001, 0234)"
            )

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
            sample_str = (
                f" (n={paper['sample_size']})" if paper.get("sample_size") else ""
            )
            has_full = "✓" if paper.get("has_full_text") else "✗"
            relevance = 1 / (1 + dist)

            output.append(
                f"   Type: {type_str}{sample_str} | Full Text: {has_full} | Score: {relevance:.2f}"
            )

            # Authors and journal
            if paper.get("authors"):
                first_author = (
                    paper["authors"][0].split()[-1] if paper["authors"] else "Unknown"
                )
                journal = paper.get("journal", "Unknown journal")
                if len(paper["authors"]) > 1:
                    output.append(f"   {first_author} et al., {journal}")
                else:
                    output.append(f"   {first_author}, {journal}")

            if show_abstracts and paper.get("abstract"):
                abstract = (
                    paper["abstract"][:200] + "..."
                    if len(paper["abstract"]) > 200
                    else paper["abstract"]
                )
                output.append(f"   {abstract}")

        return "\n".join(output)

    def _load_embedding_model(self):
        """Load the SPECTER embedding model to match the KB index."""
        # Check metadata to see which model was used for the index
        model_name = self.metadata.get("embedding_model", "allenai-specter")
        print(f"Loading {model_name} model for search...")

        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name)

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
def cli():
    """Research Assistant CLI v3.0 - Enhanced with SPECTER2 and smart search.

    Features:
    - SPECTER2 embeddings with fallback to SPECTER
    - Smart search modes (question, similar, explore)
    - Paper quality scoring (0-100 based on study type, recency, sample size)
    - Study type classification (systematic reviews, RCTs, cohort studies, etc.)
    - RCT sample size extraction (shown as n=XXX)
    - Year-based filtering for recent literature
    - Visual evidence hierarchy markers (⭐ high quality, ● good, ○ moderate)

    Knowledge base contains 2000+ papers with full text.
    """


@cli.command()
@click.argument("query_text")
@click.option(
    "--mode",
    type=click.Choice(["auto", "question", "similar", "explore"]),
    default="auto",
    help="Search mode: auto-detect, question, similar papers, or explore topic",
)
@click.option(
    "--top-k",
    "-k",
    default=10,
    help="Number of results to return (default: 10, use 30-50 for comprehensive reviews)",
)
@click.option("--verbose", "-v", is_flag=True, help="Show abstracts in results")
@click.option("--show-quality", is_flag=True, help="Show quality scores in results")
@click.option("--quality-min", type=int, help="Minimum quality score (0-100)")
@click.option(
    "--json", "output_json", is_flag=True, help="Output as JSON for processing"
)
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
    query_text,
    mode,
    top_k,
    verbose,
    show_quality,
    quality_min,
    output_json,
    after,
    study_type,
):
    """Enhanced search with SPECTER2 query preprocessing.

    Search modes optimize results for different intents:
    - auto: Automatically detect intent from query
    - question: Optimize for answering specific questions
    - similar: Find papers similar to a topic/paper
    - explore: Broad exploration of a research area

    Results show evidence quality with visual markers:
    ⭐ = systematic review / high quality (80+), ● = RCT / good quality (60-79),
    ○ = moderate quality (40-59), · = lower quality (<40)

    Examples:
        cli.py search "What causes diabetes?" --mode question
        cli.py search "papers similar to telemedicine" --mode similar
        cli.py search "AI in healthcare" --show-quality --quality-min 70
    """
    try:
        research_cli = ResearchCLI()

        # Preprocess query for better SPECTER2 results
        enhanced_query, detected_mode = preprocess_query(query_text, mode)

        if verbose:
            print(f"Search mode: {detected_mode}")

        # Perform search with enhanced query (get extra results for quality filtering)
        study_types = list(study_type) if study_type else None
        search_k = top_k * 2 if quality_min else top_k
        search_results = research_cli.search(
            enhanced_query, search_k, min_year=after, study_types=study_types
        )

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
            print(f"Mode: {detected_mode}")
            print("=" * 50)

            # Custom formatting with quality scores
            if show_quality:
                for i, (_idx, dist, paper) in enumerate(search_results, 1):
                    quality = paper.get("quality_score", 0)
                    explanation = paper.get("quality_explanation", "")

                    # Quality-based marker
                    marker = "⭐" if quality >= 80 else "●" if quality >= 60 else "○"

                    print(
                        f"\n{i}. {marker} [{paper.get('year', '????')}] {paper['title']}"
                    )
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
            "Knowledge base not found. Run 'python src/build_kb.py --demo' to create one.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(
            f"Search failed: {e}. Try rebuilding with 'python src/build_kb.py'",
            file=sys.stderr,
        )
        sys.exit(1)


@cli.command()
@click.argument("paper_id")
@click.option("--output", "-o", help="Output file path (saves as markdown)")
def get(paper_id, output):
    """Get full text of a paper by ID.

    Paper IDs are 4-digit numbers (e.g., 0001, 0234) shown in search results.
    Full text includes title, authors, abstract, and complete paper content.
    """
    try:
        research_cli = ResearchCLI()
        content = research_cli.get_paper(paper_id)

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Paper saved to {output}")
        else:
            print(content)

    except FileNotFoundError:
        print(
            "Knowledge base not found. Run 'python src/build_kb.py --demo' to create one.",
            file=sys.stderr,
        )
        sys.exit(1)
    except ValueError as e:
        print(f"Invalid paper ID: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(
            f"Failed to retrieve paper: {e}. Paper ID must be 4 digits (e.g., 0001)",
            file=sys.stderr,
        )
        sys.exit(1)


@cli.command()
@click.argument("query_text")
@click.option("--top-k", "-k", default=5, help="Number of papers to cite (default: 5)")
def cite(query_text, top_k):
    """Generate IEEE-style citations for papers matching query.

    Creates properly formatted references for academic writing.
    Format: [#] Author(s), "Title," Journal, vol. X, no. Y, pp. ZZZ-ZZZ, Year.
    """
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
def info():
    """Show information about the knowledge base.

    Displays total papers, last update time, index size, and storage details.
    Also shows which embedding model was used (SPECTER for scientific papers).
    """
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
        print(f"Location: {knowledge_base_path.absolute()}")

        index_file_path = knowledge_base_path / "index.faiss"
        if index_file_path.exists():
            index_size_mb = index_file_path.stat().st_size / (1024 * 1024)
            print(f"Index size: {index_size_mb:.1f} MB")

        papers_path = knowledge_base_path / "papers"
        if papers_path.exists():
            paper_files = list(papers_path.glob("*.md"))
            paper_count = len(paper_files)
            total_size_bytes = sum(
                paper_file.stat().st_size for paper_file in paper_files
            )
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


if __name__ == "__main__":
    cli()
