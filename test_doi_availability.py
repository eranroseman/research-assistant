#!/usr/bin/env python3
"""Check DOI availability in KB papers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gap_detection import GapAnalyzer


def check_doi_availability():
    """Check DOI availability in KB papers."""
    try:
        print("🔍 Checking DOI availability in KB papers...")

        analyzer = GapAnalyzer("kb_data")
        print(f"✅ Loaded {len(analyzer.papers)} papers")

        papers_with_doi = 0
        papers_with_s2_id = 0
        papers_with_either = 0

        sample_papers = []

        for paper in analyzer.papers:
            has_doi = bool(paper.get("doi"))
            has_s2_id = bool(paper.get("semantic_scholar_id"))

            if has_doi:
                papers_with_doi += 1
            if has_s2_id:
                papers_with_s2_id += 1
            if has_doi or has_s2_id:
                papers_with_either += 1
                if len(sample_papers) < 3:
                    sample_papers.append(
                        {
                            "title": paper.get("title", "No title")[:50],
                            "doi": paper.get("doi"),
                            "semantic_scholar_id": paper.get("semantic_scholar_id"),
                            "id": paper.get("id"),
                        }
                    )

        print("\nID Statistics:")
        print(
            f"  Papers with DOI: {papers_with_doi}/{len(analyzer.papers)} ({papers_with_doi / len(analyzer.papers) * 100:.1f}%)"
        )
        print(
            f"  Papers with S2 ID: {papers_with_s2_id}/{len(analyzer.papers)} ({papers_with_s2_id / len(analyzer.papers) * 100:.1f}%)"
        )
        print(
            f"  Papers with either: {papers_with_either}/{len(analyzer.papers)} ({papers_with_either / len(analyzer.papers) * 100:.1f}%)"
        )

        print("\nSample papers:")
        for paper in sample_papers:
            print(f"  Title: {paper['title']}...")
            print(f"    DOI: {paper['doi']}")
            print(f"    S2 ID: {paper['semantic_scholar_id']}")
            print(f"    KB ID: {paper['id']}")
            print()

    except Exception as e:
        import traceback

        print("❌ Error occurred:")
        print(f"Exception: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    check_doi_availability()
