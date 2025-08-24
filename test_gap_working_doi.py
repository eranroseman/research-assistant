#!/usr/bin/env python3
"""Test gap analysis with a working DOI."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gap_detection import GapAnalyzer


async def test_gap_working_doi():
    """Test gap analysis with a DOI that works in Semantic Scholar."""
    try:
        print("🔍 Testing gap analysis with working DOI...")

        analyzer = GapAnalyzer("kb_data")
        print(f"✅ Loaded {len(analyzer.papers)} papers")

        # Use the working DOI from previous test
        working_doi = "10.2196/15707"

        # Find the paper with this DOI
        test_paper = None
        for paper in analyzer.papers:
            if paper.get("doi") == working_doi:
                test_paper = paper
                break

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

        if "references" in response:
            references = response.get("references", []) or []
            print(f"Found {len(references)} references")

            if references:
                print("\nProcessing references like real gap analysis:")
                valid_refs = 0
                citation_candidates = {}

                for ref in references[:10]:  # Just first 10
                    if not ref or not ref.get("title"):
                        continue

                    # Check citation count filter
                    citation_count = ref.get("citationCount", 0) or 0
                    print(f"  Ref: {ref.get('title', 'No title')[:40]}... (cites: {citation_count})")

                    if citation_count >= 10:  # Use low threshold for testing
                        # Get DOI if available
                        ref_doi = None
                        external_ids = ref.get("externalIds")
                        if external_ids and isinstance(external_ids, dict) and external_ids.get("DOI"):
                            ref_doi = external_ids["DOI"]

                        ref_key = ref_doi or ref["title"]
                        citation_candidates[ref_key] = {
                            "title": ref["title"],
                            "authors": [
                                a.get("name", "") if isinstance(a, dict) else str(a)
                                for a in (ref.get("authors", []) or [])
                            ],
                            "year": ref.get("year"),
                            "citation_count": citation_count,
                            "venue": ref.get("venue", {}).get("name")
                            if isinstance(ref.get("venue"), dict)
                            else ref.get("venue"),
                            "doi": ref_doi,
                            "citing_papers": [],
                            "gap_type": "citation_network",
                        }
                        valid_refs += 1

                        if valid_refs <= 3:  # Show first 3 candidates
                            print(f"    ✅ Valid candidate: {ref['title'][:40]}...")
                            print(f"       Citations: {citation_count}, DOI: {ref_doi}")

                print(f"\nFound {valid_refs} citation gap candidates (with ≥10 citations)")
                print("🎉 Gap analysis test completed successfully!")

            else:
                print("No references found")
        else:
            print("No references field in response")

    except Exception as e:
        import traceback

        print("❌ Error occurred:")
        print(f"Exception: {e}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_gap_working_doi())
