#!/usr/bin/env python3
"""
CLI tool for searching and retrieving papers from the knowledge base
Enhanced with SPECTER query preprocessing and quality scoring
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
import faiss

# SPECTER enhancement functions integrated directly

# Medical and research term expansions for better recall
TERM_EXPANSIONS = {
    # Medical conditions
    "diabetes": ["diabetes", "diabetic", "glucose intolerance", "hyperglycemia", "T2DM", "T1DM"],
    "heart": ["heart", "cardiac", "cardiovascular", "coronary", "myocardial"],
    "cancer": ["cancer", "tumor", "tumour", "neoplasm", "malignancy", "carcinoma", "oncology"],
    "stroke": ["stroke", "cerebrovascular", "CVA", "cerebral infarction"],
    "hypertension": ["hypertension", "high blood pressure", "HTN", "elevated blood pressure"],
    "dementia": ["dementia", "Alzheimer", "cognitive decline", "cognitive impairment", "AD"],
    "depression": ["depression", "depressive", "MDD", "major depressive disorder"],
    "anxiety": ["anxiety", "anxious", "GAD", "generalized anxiety disorder"],
    # Research methodology
    "RCT": ["RCT", "randomized controlled trial", "randomised controlled trial", "randomized trial"],
    "systematic review": [
        "systematic review",
        "meta-analysis",
        "meta analysis",
        "systematic literature review",
    ],
    "cohort": ["cohort", "longitudinal", "prospective", "retrospective"],
    # Technology/digital health
    "AI": ["AI", "artificial intelligence", "machine learning", "ML", "deep learning", "neural network"],
    "telemedicine": ["telemedicine", "telehealth", "remote care", "virtual care", "digital health"],
    "mHealth": ["mHealth", "mobile health", "smartphone", "mobile app", "mobile application"],
    "EHR": ["EHR", "electronic health record", "EMR", "electronic medical record"],
    "wearable": ["wearable", "fitness tracker", "smartwatch", "activity monitor"],
}


def expand_query(query_text: str) -> tuple[str, bool]:
    """Expand query with synonyms and related terms for better recall."""
    query_lower = query_text.lower()
    expanded_terms = []

    # Check each term expansion
    for key, expansions in TERM_EXPANSIONS.items():
        if key.lower() in query_lower:
            # Add expansions that aren't already in the query
            for expansion in expansions:
                if expansion.lower() not in query_lower:
                    expanded_terms.append(expansion)

    # If we found expansions, add them to the query
    if expanded_terms:
        # Limit to top 3 expansions to avoid query dilution
        top_expansions = expanded_terms[:3]
        expanded_query = f"{query_text} {' '.join(top_expansions)}"
        return expanded_query, True

    return query_text, False


def detect_search_mode(query_text: str) -> str:
    """Detect search intent from query text."""
    query_lower = query_text.lower()

    # Question patterns
    if any(marker in query_lower for marker in ["?", "what ", "how ", "why ", "when ", "which "]):
        return "question"

    # Similarity patterns
    if any(phrase in query_lower for phrase in ["similar to", "papers like", "related to"]):
        return "similar"

    # Exploration patterns
    if any(word in query_lower for word in ["overview", "landscape", "trends", "review of"]):
        return "explore"

    # Default to standard search
    return "standard"


def analyze_evidence_gaps(search_results: list[dict]) -> tuple[list[str], list[str]]:
    """Analyze search results to identify missing evidence types."""
    from collections import Counter

    gaps = []
    recommendations = []

    if not search_results:
        return ["No search results to analyze"], []

    # Extract paper metadata
    papers = [paper for _, _, paper in search_results]

    # Count study types
    study_types = [p.get("study_type", "Unknown") for p in papers]
    type_counts = Counter(study_types)

    # Check for missing high-quality evidence
    if not type_counts.get("SYSTEMATIC REVIEW") and not type_counts.get("systematic_review"):
        gaps.append("No systematic reviews found - may lack comprehensive evidence synthesis")
        recommendations.append("Search for: systematic review OR meta-analysis")

    if not type_counts.get("RCT") and not type_counts.get("rct"):
        gaps.append("No RCTs found - limited experimental evidence")
        recommendations.append("Search for: randomized controlled trial OR RCT")

    # Check temporal coverage
    years = [p.get("year") for p in papers if p.get("year")]
    if years:
        latest_year = max(years)
        oldest_year = min(years)
        current_year = datetime.now(UTC).year

        if latest_year < current_year - 2:
            gaps.append(f"No recent studies (latest: {latest_year}) - may miss current developments")
            recommendations.append(f"Add filter: --after {current_year - 2}")

        if latest_year - oldest_year < 5 and len(papers) > 5:
            gaps.append(f"Narrow time range ({oldest_year}-{latest_year}) - may miss historical context")
            recommendations.append("Consider broader time range for comprehensive review")

    # Check sample sizes for RCTs
    rct_papers = [p for p in papers if p.get("study_type") == "RCT"]
    if rct_papers:
        sample_sizes = [p.get("sample_size") for p in rct_papers if p.get("sample_size")]
        if sample_sizes and max(sample_sizes) < 100:
            gaps.append("Only small RCTs found (n<100) - limited statistical power")
            recommendations.append("Search for: large RCT OR multicenter trial")

    # Check quality distribution
    qualities = []
    for _, _, paper in search_results:
        if "quality_score" in paper:
            qualities.append(paper["quality_score"])
        else:
            quality, _ = estimate_paper_quality(paper)
            qualities.append(quality)

    if qualities:
        avg_quality = sum(qualities) / len(qualities)
        high_quality = sum(1 for q in qualities if q >= 80)

        if avg_quality < 60:
            gaps.append(f"Low average quality ({avg_quality:.0f}/100) - consider stricter filters")
            recommendations.append("Add filter: --quality-min 70")

        if high_quality == 0:
            gaps.append("No high-quality papers (80+) found")
            recommendations.append("Expand search or check different databases")

    # Check for diversity of evidence
    if len(type_counts) < 3 and len(papers) > 5:
        gaps.append("Limited diversity of study types - may have narrow perspective")
        recommendations.append("Remove study type filters for broader evidence")

    return gaps, recommendations


def preprocess_query(query_text: str, mode: str = "auto") -> tuple[str, str]:
    """Preprocess query based on search mode for better SPECTER results."""

    # Auto-detect mode if needed
    if mode == "auto":
        mode = detect_search_mode(query_text)

    # Apply mode-specific preprocessing
    if mode == "question":
        # Frame as Q&A for better embeddings
        enhanced_query = f"Question: {query_text} Research findings:"

    elif mode == "similar":
        # Repetition emphasizes key terms in SPECTER
        enhanced_query = f"{query_text} {query_text}"

    elif mode == "explore":
        # Broader context for exploration
        enhanced_query = f"research overview: {query_text} studies analysis"

    else:
        # Standard search - no preprocessing
        enhanced_query = query_text

    return enhanced_query, mode


def estimate_paper_quality(paper: dict) -> tuple[int, str]:
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
        import re

        # Validate paper_id format (4 digits only)
        if not re.match(r"^[0-9]{4}$", paper_id):
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
    """Research Assistant CLI v3.0 - Enhanced with SPECTER embeddings and smart search.

    Features:
    - SPECTER embeddings (optimized for scientific papers)
    - Smart search modes with query expansion
    - Paper quality scoring (0-100 based on study type, recency, sample size)
    - Study type classification (systematic reviews, RCTs, cohort studies, etc.)
    - RCT sample size extraction (shown as n=XXX)
    - Year-based filtering for recent literature
    - Visual evidence hierarchy markers (⭐ high quality, ● good, ○ moderate)
    - Automatic synonym expansion for medical/research terms

    Knowledge base supports papers from your Zotero library.
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
@click.option("--json", "output_json", is_flag=True, help="Output as JSON for processing")
@click.option(
    "--after",
    type=int,
    help="Only papers published after this year (e.g., --after 2020)",
)
@click.option(
    "--analyze-gaps",
    is_flag=True,
    help="Analyze evidence gaps and provide research recommendations",
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
    mode: str,
    top_k: int,
    verbose: bool,
    show_quality: bool,
    quality_min: int | None,
    output_json: bool,
    after: int | None,
    analyze_gaps: bool,
    study_type: tuple[str, ...],
) -> None:
    """Enhanced search with SPECTER embeddings and query expansion.

    Search modes optimize results for different intents:
    - auto: Automatically detect intent from query
    - question: Optimize for answering specific questions
    - similar: Find papers similar to a topic/paper
    - explore: Broad exploration of a research area

    Query expansion automatically adds synonyms for medical/research terms.

    Results show evidence quality with visual markers:
    ⭐ = systematic review / high quality (80+), ● = RCT / good quality (60-79),
    ○ = moderate quality (40-59), · = lower quality (<40)

    Examples:
        cli.py search "diabetes" --show-quality  # Auto-expands to diabetic, T2DM, etc.
        cli.py search "What causes diabetes?" --mode question
        cli.py search "papers similar to telemedicine" --mode similar
        cli.py search "AI in healthcare" --show-quality --quality-min 70
    """
    try:
        research_cli = ResearchCLI()

        # Expand query with synonyms for better recall
        expanded_query, was_expanded = expand_query(query_text)

        # Preprocess query for better SPECTER results
        enhanced_query, detected_mode = preprocess_query(expanded_query, mode)

        if verbose:
            print(f"Search mode: {detected_mode}")
            if was_expanded:
                print(f"Query expanded: {expanded_query}")

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

        # Analyze evidence gaps if requested
        if analyze_gaps and not output_json:
            # Extract just the paper dicts from search results
            papers_only = [paper for _, _, paper in search_results]
            gaps, recommendations = analyze_evidence_gaps(papers_only)

            if gaps:
                print("\n📊 Evidence Gap Analysis:")
                print("=" * 50)
                print("\n⚠️  Gaps Identified:")
                for gap in gaps:
                    print(f"  • {gap}")

                if recommendations:
                    print("\n💡 Recommendations:")
                    for rec in recommendations:
                        print(f"  → {rec}")
            else:
                print("\n✅ Evidence coverage appears comprehensive!")

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
            "   3. Clear cache and rebuild: python src/build_kb.py --clear-cache",
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
    Full text includes title, authors, abstract, and complete paper content.

    Use --sections to retrieve only specific sections for faster reading:
        cli.py get 0001 --sections abstract conclusion
        cli.py get 0001 -s methods -s results
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
@click.option("--top-k", "-k", default=5, help="Number of papers to cite (default: 5)")
def cite(query_text: str, top_k: int) -> None:
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
@click.argument("shortcut_name", required=False)
@click.option("--list", "list_shortcuts", is_flag=True, help="List all available shortcuts")
@click.option("--edit", is_flag=True, help="Open shortcuts file for editing")
def shortcut(shortcut_name: str | None, list_shortcuts: bool, edit: bool) -> None:
    """Run predefined search shortcuts for common research queries.

    Examples:
        cli.py shortcut diabetes  # Run diabetes research shortcut
        cli.py shortcut --list     # Show all shortcuts
        cli.py shortcut --edit     # Edit shortcuts file
    """
    import os
    from pathlib import Path

    import yaml

    # Load shortcuts configuration
    shortcuts_file = Path.home() / ".research_shortcuts.yaml"
    if not shortcuts_file.exists():
        # Copy default shortcuts file
        default_shortcuts = Path(__file__).parent.parent / ".research_shortcuts.yaml"
        if default_shortcuts.exists():
            shortcuts_file.write_text(default_shortcuts.read_text())
        else:
            print("No shortcuts configured. Create ~/.research_shortcuts.yaml")
            sys.exit(1)

    if edit:
        # Open shortcuts file in default editor
        editor = os.environ.get("EDITOR", "nano")
        # Use subprocess for safer execution
        import subprocess

        subprocess.run([editor, str(shortcuts_file)], check=False)  # noqa: S603
        return

    try:
        with open(shortcuts_file) as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading shortcuts: {e}", file=sys.stderr)
        sys.exit(1)

    if list_shortcuts or not shortcut_name:
        # List all available shortcuts
        print("\nAvailable Research Shortcuts:")
        print("=" * 50)

        if "favorite_searches" in config:
            print("\n📚 Favorite Searches:")
            for name, settings in config["favorite_searches"].items():
                desc = settings.get("description", "No description")
                print(f"  {name:15} - {desc}")

        if "research_topics" in config:
            print("\n🔬 Research Topics:")
            for name, settings in config["research_topics"].items():
                num_searches = len(settings.get("searches", []))
                print(f"  {name:15} - {num_searches} related searches")

        print("\nUsage: python src/cli.py shortcut <name>")
        return

    # Execute the shortcut
    if shortcut_name in config.get("favorite_searches", {}):
        settings = config["favorite_searches"][shortcut_name]

        # Build command
        query = settings.get("query", shortcut_name)

        # Import and run search directly
        try:
            research_cli = ResearchCLI()

            # Apply query expansion if enabled
            expanded_query, was_expanded = expand_query(query)

            # Apply mode preprocessing
            mode = settings.get("mode", "auto")
            enhanced_query, detected_mode = preprocess_query(expanded_query, mode)

            # Perform search with settings
            top_k = settings.get("top_k", 10)
            min_year = settings.get("after")
            study_types = settings.get("type")
            quality_min = settings.get("quality_min")
            show_quality = settings.get("show_quality", False)
            verbose = settings.get("verbose", False)

            # Get extra results if quality filtering
            search_k = top_k * 2 if quality_min else top_k
            search_results = research_cli.search(
                enhanced_query, search_k, min_year=min_year, study_types=study_types
            )

            # Apply quality filtering if requested
            if quality_min or show_quality:
                enhanced_results = []
                for idx, dist, paper in search_results:
                    quality, explanation = estimate_paper_quality(paper)

                    if quality_min and quality < quality_min:
                        continue

                    paper["quality_score"] = quality
                    paper["quality_explanation"] = explanation
                    enhanced_results.append((idx, dist, paper))

                search_results = enhanced_results[:top_k]
            else:
                search_results = search_results[:top_k]

            # Display results
            print(f"\n🔍 Shortcut: '{shortcut_name}'")
            if settings.get("description"):
                print(f"📝 {settings['description']}")
            print(f"\nSearch results for: '{query}'")
            print(f"Mode: {detected_mode}")
            if was_expanded:
                print(f"Query expanded: {expanded_query}")
            print("=" * 50)

            # Format and display results
            if show_quality:
                for i, (_idx, dist, paper) in enumerate(search_results, 1):
                    quality = paper.get("quality_score", 0)
                    explanation = paper.get("quality_explanation", "")

                    marker = "⭐" if quality >= 80 else "●" if quality >= 60 else "○"

                    print(f"\n{i}. {marker} [{paper.get('year', '????')}] {paper['title']}")
                    print(f"   Quality: {quality}/100 ({explanation})")

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
                print(research_cli.format_search_results(search_results, verbose))

        except Exception as e:
            print(f"Error executing shortcut: {e}", file=sys.stderr)
            sys.exit(1)

    elif shortcut_name in config.get("research_topics", {}):
        # Execute research topic (multiple searches)
        topic = config["research_topics"][shortcut_name]
        searches = topic.get("searches", [])
        topic.get("filters", {})

        print(f"\n🔬 Research Topic: '{shortcut_name}'")
        print(f"Running {len(searches)} related searches...")
        print("=" * 50)

        for search_query in searches:
            print(f"\n➤ Searching: {search_query}")
            # NOTE: Multi-search execution not implemented yet
            # Currently just displays what would be searched

    else:
        print(f"Shortcut '{shortcut_name}' not found. Use --list to see available shortcuts.")
        sys.exit(1)


@cli.command()
@click.option("--fix", is_flag=True, help="Remove duplicates (creates backup first)")
@click.option("--threshold", default=0.9, help="Similarity threshold for title matching (0-1)")
def duplicates(fix: bool, threshold: float) -> None:
    """Find and optionally remove duplicate papers in the knowledge base.

    Detects duplicates using:
    - Exact DOI matches
    - Fuzzy title matching (>90% similarity)
    - Same first author + year + journal
    """
    import difflib
    from collections import defaultdict

    try:
        # Load metadata
        kb_path = Path("kb_data")
        metadata_file = kb_path / "metadata.json"

        if not metadata_file.exists():
            print("❌ Knowledge base not found. Run build_kb.py first.")
            sys.exit(1)

        with open(metadata_file) as f:
            metadata = json.load(f)

        papers = metadata.get("papers", [])
        print(f"🔍 Checking {len(papers)} papers for duplicates...")

        # Show progress for large collections
        if len(papers) > 500:
            print("  ⏳ This may take a moment for large collections...")

        # Strategy 1: Find exact DOI matches
        doi_groups = defaultdict(list)
        for i, paper in enumerate(papers):
            doi = paper.get("doi", "").strip().lower()
            if doi:
                doi_groups[doi].append(i)

        # Strategy 2: Find similar titles (highly optimized)
        title_duplicates = []

        # For very large collections, use a faster approximate method
        if len(papers) > 1000:
            print("  📋 Using fast duplicate detection for large collection...")

            # Group by normalized title start (first 30 chars)
            title_groups = defaultdict(list)
            for i, paper in enumerate(papers):
                title = paper.get("title", "").lower().strip()
                if title:
                    # Normalize: remove punctuation, take first 30 chars
                    normalized = "".join(c for c in title[:30] if c.isalnum() or c.isspace())
                    key = " ".join(normalized.split()[:4])  # First 4 words
                    if key:
                        title_groups[key].append((i, title))

            # Only compare within groups with exact prefix match
            for _key, group in title_groups.items():
                if len(group) > 1:
                    # Compare within small groups only
                    for i in range(len(group)):
                        for j in range(i + 1, len(group)):
                            idx1, title1 = group[i]
                            idx2, title2 = group[j]

                            # Very quick similarity check using set overlap
                            words1 = set(title1.split())
                            words2 = set(title2.split())
                            if len(words1) > 0 and len(words2) > 0:
                                overlap = len(words1 & words2) / min(len(words1), len(words2))
                                if overlap >= threshold:
                                    # Do precise check only for high overlap
                                    similarity = difflib.SequenceMatcher(None, title1, title2).ratio()
                                    if similarity >= threshold:
                                        title_duplicates.append((idx1, idx2, similarity))
        else:
            # For smaller collections, use more thorough comparison
            for i in range(len(papers)):
                for j in range(i + 1, len(papers)):
                    title1 = papers[i].get("title", "").lower().strip()
                    title2 = papers[j].get("title", "").lower().strip()

                    if title1 and title2:
                        # Quick length check
                        if abs(len(title1) - len(title2)) / max(len(title1), len(title2)) > 0.3:
                            continue

                        # Calculate similarity
                        similarity = difflib.SequenceMatcher(None, title1, title2).ratio()
                        if similarity >= threshold:
                            title_duplicates.append((i, j, similarity))

        # Strategy 3: Same first author + year + journal
        author_year_groups = defaultdict(list)
        for i, paper in enumerate(papers):
            authors = paper.get("authors", [])
            if authors:
                first_author = authors[0].split()[-1].lower()  # Last name
                year = paper.get("year", "")
                journal = paper.get("journal", "").lower()[:20]  # First 20 chars

                if first_author and year:
                    key = f"{first_author}_{year}_{journal}"
                    author_year_groups[key].append(i)

        # Collect all duplicate groups
        duplicate_groups = []

        # Add DOI duplicates
        for doi, indices in doi_groups.items():
            if len(indices) > 1:
                duplicate_groups.append({"type": "DOI match", "indices": indices, "key": doi})

        # Add title duplicates
        for i, j, sim in title_duplicates:
            # Check if not already in a DOI group
            in_doi_group = False
            for group in duplicate_groups:
                if group["type"] == "DOI match" and i in group["indices"] and j in group["indices"]:
                    in_doi_group = True
                    break

            if not in_doi_group:
                duplicate_groups.append(
                    {
                        "type": f"Title similarity ({sim:.0%})",
                        "indices": [i, j],
                        "key": papers[i]["title"][:50],
                    }
                )

        # Add author/year duplicates
        for key, indices in author_year_groups.items():
            if len(indices) > 1:
                # Check if not already detected
                new_group = True
                for group in duplicate_groups:
                    if set(indices).issubset(set(group["indices"])):
                        new_group = False
                        break

                if new_group:
                    duplicate_groups.append({"type": "Author+Year+Journal", "indices": indices, "key": key})

        # Display results
        if not duplicate_groups:
            print("✅ No duplicates found!")
            return

        print(f"\n📊 Found {len(duplicate_groups)} duplicate groups:")
        print("=" * 70)

        papers_to_remove = set()

        for i, group in enumerate(duplicate_groups, 1):
            print(f"\n{i}. {group['type']}: {group['key'][:50]}...")

            # Show papers in this group
            for idx in group["indices"]:
                paper = papers[idx]
                mark = "  ❌" if idx in papers_to_remove else "  →"
                print(f"{mark} [{paper['id']}] {paper.get('title', 'Unknown')[:60]}...")
                print(f"      {paper.get('authors', ['Unknown'])[0]}, {paper.get('year', '?')}")

            # Keep the first paper, mark others for removal
            for idx in group["indices"][1:]:
                papers_to_remove.add(idx)

        print("\n📈 Summary:")
        print(f"   Total papers: {len(papers)}")
        print(f"   Duplicates found: {len(papers_to_remove)}")
        print(f"   Papers after cleanup: {len(papers) - len(papers_to_remove)}")

        if fix:
            print("\n⚠️  Removing duplicates...")

            # Backup first
            import shutil

            backup_dir = kb_path.parent / f"kb_data_backup_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
            shutil.copytree(kb_path, backup_dir)
            print(f"📁 Created backup at {backup_dir}")

            # Remove duplicate papers from metadata
            cleaned_papers = [p for i, p in enumerate(papers) if i not in papers_to_remove]

            # Reindex papers
            for i, paper in enumerate(cleaned_papers):
                paper["id"] = f"{i + 1:04d}"
                paper["embedding_index"] = i
                paper["filename"] = f"paper_{paper['id']}.md"

            # Update metadata
            metadata["papers"] = cleaned_papers
            metadata["total_papers"] = len(cleaned_papers)
            metadata["last_updated"] = datetime.now(UTC).isoformat()

            # Save updated metadata
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            # Note: We should also rebuild the FAISS index, but that requires embeddings
            print(f"✅ Removed {len(papers_to_remove)} duplicate papers")
            print("⚠️  Note: You should rebuild the index for optimal performance:")
            print("   python src/build_kb.py")
        else:
            print("\n💡 To remove duplicates, run:")
            print("   python src/cli.py duplicates --fix")

    except Exception as e:
        print(f"❌ Error checking duplicates: {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.argument("paper_id")
@click.argument("query", required=False)
def smart_get(paper_id: str, query: str) -> None:
    """Intelligently retrieve relevant sections based on query context.

    Automatically selects which sections to retrieve based on your query:
    - Methods queries → methods section
    - Results queries → results + conclusion
    - General queries → abstract + conclusion

    Examples:
        cli.py smart-get 0001 "how did they measure"
        cli.py smart-get 0001 "what were the findings"
        cli.py smart-get 0001  # Returns abstract + conclusion
    """
    # Determine which sections to retrieve based on query
    if query:
        query_lower = query.lower()
        sections = []

        # Always include abstract for context
        sections.append("abstract")

        # Add sections based on query content
        if any(word in query_lower for word in ["method", "how", "approach", "technique", "design"]):
            sections.append("methods")

        if any(word in query_lower for word in ["result", "finding", "outcome", "effect", "impact"]):
            sections.append("results")

        if any(word in query_lower for word in ["discuss", "limitation", "implication", "interpret"]):
            sections.append("discussion")

        if any(word in query_lower for word in ["introduc", "background", "literature", "review"]):
            sections.append("introduction")

        # Always add conclusion for summary
        if "conclusion" not in sections:
            sections.append("conclusion")

        print(f"🎯 Smart retrieval for query: '{query}'")
        print(f"   Retrieving sections: {', '.join(sections)}\n")
    else:
        # Default to abstract and conclusion
        sections = ["abstract", "conclusion"]
        print("📖 Default retrieval: abstract + conclusion\n")

    # Use the get command with selected sections
    ctx = click.get_current_context()
    ctx.invoke(get, paper_id=paper_id, output=None, sections=sections)


@cli.command()
def info() -> None:
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


if __name__ == "__main__":
    cli()
