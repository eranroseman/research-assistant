#!/usr/bin/env python3
"""Analyze which papers failed OpenAlex enrichment and why."""

import json
from pathlib import Path
from collections import defaultdict
from typing import Any


def analyze_failures() -> None:
    """Analyze papers that failed OpenAlex enrichment."""
    input_dir = Path("s2_enriched_20250901_small")
    output_dir = Path("openalex_test_output")

    # Get all input papers
    input_papers: set[str] = set()
    papers_with_dois: dict[str, dict[str, Any]] = {}
    papers_without_dois: list[str] = []

    for paper_file in input_dir.glob("*.json"):
        if paper_file.name == "s2_batch_report.json":
            continue

        paper_id = paper_file.stem
        input_papers.add(paper_id)

        with open(paper_file) as f:
            paper = json.load(f)
            doi = paper.get("doi")
            if doi:
                papers_with_dois[paper_id] = {
                    "doi": doi,
                    "title": paper.get("title", "Unknown"),
                    "year": paper.get("year"),
                    "journal": paper.get("journal"),
                }
            else:
                papers_without_dois.append(paper_id)

    # Check which papers were enriched
    enriched_papers: set[str] = set()
    failed_papers: list[tuple[str, dict[str, Any]]] = []

    for paper_id, info in papers_with_dois.items():
        output_file = output_dir / f"{paper_id}.json"
        if output_file.exists():
            with open(output_file) as f:
                paper = json.load(f)
                if "openalex_id" in paper:
                    enriched_papers.add(paper_id)
                else:
                    failed_papers.append((paper_id, info))
        else:
            failed_papers.append((paper_id, info))

    # Analyze failures
    print("=" * 80)
    print("OPENALEX FAILURE ANALYSIS")
    print("=" * 80)
    print(f"\nTotal papers: {len(input_papers)}")
    print(f"Papers with DOIs: {len(papers_with_dois)}")
    print(f"Papers without DOIs: {len(papers_without_dois)}")
    print(f"Successfully enriched: {len(enriched_papers)}")
    print(f"Failed enrichment: {len(failed_papers)}")
    print(f"Failure rate: {len(failed_papers) / len(papers_with_dois) * 100:.1f}%")

    if failed_papers:
        print("\n" + "-" * 40)
        print("FAILED PAPERS (Not found in OpenAlex):")
        print("-" * 40)

        # Group by characteristics
        by_year: dict[Any, list[str]] = defaultdict(list)
        by_journal: dict[str, list[str]] = defaultdict(list)

        for paper_id, info in failed_papers:
            print(f"\nPaper ID: {paper_id}")
            print(f"  DOI: {info['doi']}")
            print(f"  Title: {info['title'][:80]}...")
            print(f"  Year: {info['year']}")
            print(f"  Journal: {info['journal']}")

            if info["year"]:
                by_year[info["year"]].append(paper_id)
            if info["journal"]:
                by_journal[info["journal"]].append(paper_id)

        # Analyze patterns
        print("\n" + "-" * 40)
        print("FAILURE PATTERNS:")
        print("-" * 40)

        if by_year:
            print("\nBy Year:")
            # Convert all years to strings for consistent sorting
            year_items = [(str(year), papers) for year, papers in by_year.items()]
            for year, papers in sorted(year_items):
                print(f"  {year}: {len(papers)} papers")

        if by_journal:
            print("\nBy Journal (top sources):")
            journal_counts = [(j, len(ids)) for j, ids in by_journal.items()]
            for journal, count in sorted(journal_counts, key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {journal}: {count} papers")

        # Check DOI patterns
        print("\nDOI Patterns:")
        doi_prefixes: dict[str, int] = defaultdict(int)
        for _, info in failed_papers:
            doi = info["doi"]
            if doi:
                # Extract publisher prefix
                prefix = doi.split("/")[0] if "/" in doi else doi[:15]
                doi_prefixes[prefix] += 1

        for prefix, count in sorted(doi_prefixes.items(), key=lambda x: x[1], reverse=True):
            print(f"  {prefix}: {count} papers")

    # Potential reasons for failures
    print("\n" + "-" * 40)
    print("POTENTIAL REASONS FOR FAILURES:")
    print("-" * 40)
    print("1. Papers too recent (2025) - OpenAlex may not have indexed them yet")
    print("2. Preprints or conference papers - may have different DOIs")
    print("3. DOI formatting issues (malformed or non-standard)")
    print("4. Papers from smaller publishers not indexed by OpenAlex")
    print("5. Books or book chapters (OpenAlex focuses on articles)")

    # Recommendations
    print("\n" + "-" * 40)
    print("RECOMMENDATIONS:")
    print("-" * 40)
    print("1. Use email for polite pool access (better rate limits)")
    print("2. Try alternative identifiers (title search, arXiv ID)")
    print("3. Implement retry logic with exponential backoff")
    print("4. Consider fallback to other APIs for failed papers")


if __name__ == "__main__":
    analyze_failures()
