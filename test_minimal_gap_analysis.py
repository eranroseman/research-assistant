#!/usr/bin/env python3
"""Minimal test to verify gap analysis data handling fixes."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gap_detection import GapAnalyzer


async def test_minimal_gap_analysis():
    """Test gap analysis with minimal setup."""
    try:
        print("🔍 Testing gap analysis data handling fixes...")

        analyzer = GapAnalyzer("kb_data")

        if not analyzer.papers:
            print("❌ No papers found in KB")
            return

        print(f"✅ Loaded {len(analyzer.papers)} papers")

        # Test just one paper for citation gaps
        print("Testing citation gap detection with limit=1...")
        citation_gaps = await analyzer.find_citation_gaps(min_citations=0, limit=1)
        print(f"✅ Citation gaps found: {len(citation_gaps)}")

        # Test author gaps with limit=1
        print("Testing author gap detection with limit=1...")
        author_gaps = await analyzer.find_author_gaps(year_from=2020, limit=1)
        print(f"✅ Author gaps found: {len(author_gaps)}")

        print("🎉 All tests passed!")

    except Exception as e:
        import traceback

        print("❌ Error occurred:")
        print(f"Exception: {e}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_minimal_gap_analysis())
