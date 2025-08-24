#!/usr/bin/env python3
"""Test gap analysis step by step with detailed debugging."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gap_detection import GapAnalyzer


async def test_gap_step_by_step():
    """Test gap analysis with detailed step-by-step debugging."""
    try:
        print("🔍 Step-by-step gap analysis test...")

        print("Step 1: Initialize analyzer...")
        analyzer = GapAnalyzer("kb_data")
        print(f"✅ Loaded {len(analyzer.papers)} papers")

        if len(analyzer.papers) == 0:
            print("❌ No papers in KB!")
            return

        # Get first paper for testing
        test_paper = analyzer.papers[0]
        print(f"Step 2: Testing with paper: {test_paper.get('title', 'Unknown')[:50]}...")

        # Try to get references for just this one paper
        semantic_scholar_id = test_paper.get("semantic_scholar_id")
        if not semantic_scholar_id:
            print("❌ No semantic_scholar_id found!")
            return

        print(f"Step 3: Looking up references for S2 ID: {semantic_scholar_id}")

        url = f"https://api.semanticscholar.org/graph/v1/paper/{semantic_scholar_id}"
        params = {
            "fields": "references.title,references.authors,references.year,references.citationCount,references.externalIds,references.venue"
        }

        print(f"URL: {url}")
        print(f"Params: {params}")

        print("Step 4: Making API request (with rate limiting)...")
        response = await analyzer._api_request(url, params)

        if not response:
            print("❌ No response from API")
            return

        print(f"✅ Got API response with keys: {list(response.keys())}")

        if "references" in response:
            references = response.get("references", []) or []
            print(f"Step 5: Found {len(references)} references")

            if references:
                first_ref = references[0]
                print(f"Sample reference: {first_ref.get('title', 'No title')[:50]}...")
                print(f"Citation count: {first_ref.get('citationCount', 0)}")
        else:
            print("Step 5: No references field in response")

        print("🎉 Step-by-step test completed successfully!")

    except Exception as e:
        import traceback

        print("❌ Error occurred:")
        print(f"Exception: {e}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_gap_step_by_step())
