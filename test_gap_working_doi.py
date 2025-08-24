#!/usr/bin/env python3
"""Test gap analysis with a working DOI."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gap_detection import GapAnalyzer


def _find_test_paper(analyzer, working_doi: str):
    """Find test paper by DOI."""
    for paper in analyzer.papers:
        if paper.get("doi") == working_doi:
            return paper
    return None


def _process_reference(ref):
    """Process a single reference for gap analysis."""
    if not ref or not ref.get("title"):
        return None, None

    citation_count = ref.get("citationCount", 0) or 0
    print(f"  Ref: {ref.get('title', 'No title')[:40]}... (cites: {citation_count})")

    if citation_count < 10:  # Use low threshold for testing
        return None, None

    # Get DOI if available
    ref_doi = None
    external_ids = ref.get("externalIds")
    if external_ids and isinstance(external_ids, dict) and external_ids.get("DOI"):
        ref_doi = external_ids["DOI"]

    ref_key = ref_doi or ref["title"]
    candidate = {
        "title": ref["title"],
        "authors": [
            a.get("name", "") if isinstance(a, dict) else str(a) for a in (ref.get("authors", []) or [])
        ],
        "year": ref.get("year"),
        "citation_count": citation_count,
        "venue": ref.get("venue", {}).get("name") if isinstance(ref.get("venue"), dict) else ref.get("venue"),
        "doi": ref_doi,
        "citing_papers": [],
        "gap_type": "citation_network",
    }

    return ref_key, candidate


def _process_references(references):
    """Process all references and extract valid candidates."""
    print("\nProcessing references like real gap analysis:")
    valid_refs = 0
    citation_candidates = {}

    for ref in references[:10]:  # Just first 10
        ref_key, candidate = _process_reference(ref)
        if candidate:
            citation_candidates[ref_key] = candidate
            valid_refs += 1

            if valid_refs <= 3:  # Show first 3 candidates
                print(f"    ✅ Valid candidate: {ref['title'][:40]}...")
                print(f"       Citations: {candidate['citation_count']}, DOI: {candidate['doi']}")

    return valid_refs, citation_candidates


async def test_gap_working_doi():
    """Test gap analysis with a DOI that works in Semantic Scholar."""
    try:
        print("🔍 Testing gap analysis with working DOI...")

        analyzer = GapAnalyzer("kb_data")
        print(f"✅ Loaded {len(analyzer.papers)} papers")

        # Use the working DOI from previous test
        working_doi = "10.2196/15707"

        # Find the paper with this DOI
        test_paper = _find_test_paper(analyzer, working_doi)
        if not test_paper:
            print(f"❌ Paper with DOI {working_doi} not found in KB!")
            return

        print(f"Testing with paper: {test_paper.get('title', 'Unknown')[:50]}...")
        print(f"DOI: {working_doi}")

        # Make API call for references
        url = f"https://api.semanticscholar.org/graph/v1/paper/{working_doi}"
        params = {
            "fields": "references.title,references.authors,references.year,references.citationCount,references.externalIds,references.venue"
        }

        print("Making API request with rate limiting...")
        response = await analyzer._api_request(url, params)

        if not response:
            print("❌ No response from API")
            return

        print("✅ Got API response")

        if "references" not in response:
            print("No references field in response")
            return

        references = response.get("references", []) or []
        print(f"Found {len(references)} references")

        if not references:
            print("No references found")
            return

        valid_refs, _ = _process_references(references)
        print(f"\nFound {valid_refs} citation gap candidates (with ≥10 citations)")
        print("🎉 Gap analysis test completed successfully!")

    except Exception as e:
        import traceback

        print("❌ Error occurred:")
        print(f"Exception: {e}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_gap_working_doi())
