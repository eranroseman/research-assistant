#!/usr/bin/env python3
"""
CLI tool for searching and retrieving papers from the knowledge base
"""

import json
import sys
from pathlib import Path

import click
import faiss
from sentence_transformers import SentenceTransformer


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

        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.search_index = faiss.read_index(str(self.index_file_path))

        with open(self.metadata_file_path, encoding="utf-8") as f:
            self.metadata = json.load(f)

    def search(self, query_text: str, top_k: int = 10) -> list[tuple[int, float, dict]]:
        """Search for relevant papers using semantic similarity."""
        query_embedding = self.embedding_model.encode([query_text])

        # Limit top_k to the number of available papers
        available_papers = len(self.metadata["papers"])
        actual_k = min(top_k, available_papers)

        distances, indices = self.search_index.search(
            query_embedding.astype("float32"), actual_k
        )

        results = []
        for idx, dist in zip(indices[0], distances[0], strict=False):
            if idx < len(self.metadata["papers"]) and idx != -1:  # -1 is returned for invalid indices
                paper = self.metadata["papers"][idx]
                results.append((idx, float(dist), paper))

        return results

    def get_paper(self, paper_id: str) -> str:
        """Retrieve full text of a paper by ID."""
        paper_file_path = self.papers_path / f"paper_{paper_id}.md"

        if not paper_file_path.exists():
            for paper in self.metadata["papers"]:
                if paper["id"] == paper_id:
                    paper_file_path = self.papers_path / paper["filename"]
                    break

        if paper_file_path.exists():
            with open(paper_file_path, encoding="utf-8") as f:
                return f.read()
        else:
            return f"Paper {paper_id} not found"

    def format_search_results(
        self,
        search_results: list[tuple[int, float, dict]],
        show_abstracts: bool = False,
    ) -> str:
        """Format search results for display."""
        output = []

        for i, (_idx, dist, paper) in enumerate(search_results, 1):
            output.append(f"\n{i}. [{paper['id']}] {paper['title']}")

            if paper.get("authors"):
                authors_str = ", ".join(paper["authors"][:3])
                if len(paper["authors"]) > 3:
                    authors_str += " et al."
                output.append(f"   Authors: {authors_str}")

            if paper.get("year"):
                output.append(f"   Year: {paper['year']}")

            if paper.get("journal"):
                output.append(f"   Journal: {paper['journal']}")

            if show_abstracts and paper.get("abstract"):
                abstract = (
                    paper["abstract"][:200] + "..."
                    if len(paper["abstract"]) > 200
                    else paper["abstract"]
                )
                output.append(f"   Abstract: {abstract}")

            output.append(f"   Relevance score: {1 / (1 + dist):.3f}")

        return "\n".join(output)

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
    """Research Assistant CLI - Search and retrieve academic papers."""
    pass


@cli.command()
@click.argument("query_text")
@click.option("--top-k", "-k", default=10, help="Number of results to return")
@click.option("--verbose", "-v", is_flag=True, help="Show abstracts in results")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def search(query_text, top_k, verbose, output_json):
    """Search for relevant papers."""
    try:
        research_cli = ResearchCLI()
        search_results = research_cli.search(query_text, top_k)

        if output_json:
            output = []
            for _idx, dist, paper in search_results:
                output.append(
                    {
                        "id": paper["id"],
                        "title": paper["title"],
                        "authors": paper.get("authors", []),
                        "year": paper.get("year"),
                        "journal": paper.get("journal"),
                        "similarity_score": float(1 / (1 + dist)),
                    }
                )
            print(json.dumps(output, indent=2))
        else:
            print(f"\nSearch results for: '{query_text}'")
            print("=" * 50)
            print(research_cli.format_search_results(search_results, verbose))

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Search failed: {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.argument("paper_id")
@click.option("--output", "-o", help="Output file path")
def get(paper_id, output):
    """Get full text of a paper by ID."""
    try:
        research_cli = ResearchCLI()
        content = research_cli.get_paper(paper_id)

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Paper saved to {output}")
        else:
            print(content)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Failed to retrieve paper: {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.argument("query_text")
@click.option("--top-k", "-k", default=5, help="Number of papers to cite")
def cite(query_text, top_k):
    """Generate IEEE-style citations for papers matching query."""
    try:
        research_cli = ResearchCLI()
        search_results = research_cli.search(query_text, top_k)

        print(f"\nIEEE Citations for: '{query_text}'")
        print("=" * 50)

        for i, (_idx, _dist, paper) in enumerate(search_results, 1):
            citation_text = research_cli.format_ieee_citation(paper, i)
            print(f"\n{citation_text}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Citation generation failed: {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
def info():
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
        print(f"Failed to get info: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
