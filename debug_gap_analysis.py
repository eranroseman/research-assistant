#!/usr/bin/env python3
"""Debug script to identify the exact source of the gap analysis error."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gap_detection import GapAnalyzer


async def debug_gap_analysis():
    """Debug the gap analysis to find the exact error source."""
    try:
        analyzer = GapAnalyzer("kb_data")

        # Test just the first few papers
        print(f"Testing with {len(analyzer.papers)} papers")
        print(f"First paper: {analyzer.papers[0]}")
        print(f"First paper type: {type(analyzer.papers[0])}")

        # Try to process just one paper
        test_paper = analyzer.papers[0]
        print(f"Test paper ID: {test_paper.get('id')}")
        print(f"Test paper DOI: {test_paper.get('doi')}")
        print(f"Test paper semantic_scholar_id: {test_paper.get('semantic_scholar_id')}")

        # Try citation gaps with a very small subset
        print("Testing citation gap detection...")
        citation_gaps = await analyzer.find_citation_gaps(min_citations=100, limit=1)
        print(f"Citation gaps found: {len(citation_gaps)}")

    except Exception as e:
        import traceback

        print("Error occurred:")
        print(f"Exception: {e}")
        print(f"Exception type: {type(e)}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_gap_analysis())
