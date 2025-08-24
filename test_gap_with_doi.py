#!/usr/bin/env python3
"""Test gap analysis using DOI."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gap_detection import GapAnalyzer


async def test_gap_with_doi():
    """Test gap analysis using DOI for API calls."""
    try:
        print("🔍 Testing gap analysis with DOI...")

        analyzer = GapAnalyzer("kb_data")
        print(f"✅ Loaded {len(analyzer.papers)} papers")

        # Find a paper with DOI
        test_paper = None
        for paper in analyzer.papers:
            if paper.get("doi"):
                test_paper = paper
                break

        if not test_paper:
            print("❌ No paper with DOI found!")
            return

        print(f"Testing with paper: {test_paper.get('title', 'Unknown')[:50]}...")
        print(f"DOI: {test_paper.get('doi')}")

        # Test the paper_id logic from the gap detection
        paper_id = test_paper.get("semantic_scholar_id") or test_paper.get("doi")
        print(f"Using paper_id: {paper_id}")

        # Make API call
        url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
        params = {
            "fields": "references.title,references.authors,references.year,references.citationCount,references.externalIds,references.venue"
        }

        print("Making API request with rate limiting...")
        response = await analyzer._api_request(url, params)

        if not response:
            print("❌ No response from API")
            return

        print(f"✅ Got API response with keys: {list(response.keys())}")

        if "references" in response:
            references = response.get("references", []) or []
            print(f"Found {len(references)} references")

            # Process like the real gap analysis does
            for i, ref in enumerate(references[:3]):  # Just first 3
                if not ref or not ref.get("title"):
                    continue
                print(f"  Reference {i + 1}: {ref.get('title', 'No title')[:40]}...")
                print(f"    Citations: {ref.get('citationCount', 0)}")

                external_ids = ref.get("externalIds")
                if external_ids and isinstance(external_ids, dict) and external_ids.get("DOI"):
                    print(f"    DOI: {external_ids['DOI']}")
        else:
            print("No references field in response")

        print("🎉 DOI test completed successfully!")

    except Exception as e:
        import traceback

        print("❌ Error occurred:")
        print(f"Exception: {e}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_gap_with_doi())
